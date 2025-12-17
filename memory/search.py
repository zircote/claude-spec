"""Search optimization module for cs-memory.

This module provides:
- Query expansion with synonyms and related terms
- Result re-ranking with multiple signals
- Search caching for performance
- Relevance feedback integration
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .config import (
    SEARCH_CACHE_TTL_SECONDS,
)
from .models import MemoryResult

# Query expansion synonyms for common terms
QUERY_SYNONYMS: dict[str, list[str]] = {
    # Decision-related
    "decision": ["chose", "selected", "decided", "picked", "opted"],
    "chose": ["decision", "selected", "picked"],
    "why": ["reason", "rationale", "because", "motivation"],
    # Problem-related
    "problem": ["issue", "bug", "error", "blocker", "obstacle"],
    "bug": ["problem", "issue", "error", "defect"],
    "blocker": ["obstacle", "impediment", "problem", "issue"],
    "error": ["bug", "problem", "issue", "failure"],
    # Learning-related
    "learned": ["discovered", "realized", "found", "understood"],
    "insight": ["learning", "discovery", "realization"],
    # Architecture-related
    "architecture": ["design", "structure", "pattern", "system"],
    "pattern": ["design", "approach", "architecture", "solution"],
    "api": ["endpoint", "interface", "service", "rest"],
    # Progress-related
    "progress": ["completed", "done", "finished", "implemented"],
    "implemented": ["built", "created", "developed", "completed"],
    # Common tech terms
    "database": ["db", "postgres", "sql", "storage", "persistence"],
    "authentication": ["auth", "login", "security", "credentials"],
    "cache": ["caching", "memoization", "storage"],
    "performance": ["speed", "latency", "optimization", "fast"],
    "test": ["testing", "spec", "unit", "integration"],
}

# Domain-specific term expansions
DOMAIN_EXPANSIONS: dict[str, list[str]] = {
    # Web development
    "frontend": ["react", "vue", "angular", "ui", "client"],
    "backend": ["server", "api", "service", "node", "python"],
    # Data
    "data": ["database", "storage", "persistence", "model"],
    # DevOps
    "deploy": ["deployment", "release", "ci", "cd", "pipeline"],
    "infra": ["infrastructure", "cloud", "aws", "gcp", "azure"],
}


@dataclass(frozen=True)
class SearchQuery:
    """Represents an expanded search query."""

    original: str
    expanded_terms: tuple[str, ...]
    filters: dict[str, Any] = field(default_factory=dict)

    def cache_key(self) -> str:
        """Generate a cache key for this query.

        SEC-002: Uses SHA-256 (truncated) instead of MD5 for cache key generation.
        While MD5 is not cryptographically broken for non-security use cases like
        cache keys, using SHA-256 avoids security scanner warnings and follows
        best practices. Truncated to 16 chars for reasonable key length.
        """
        key_parts = [
            self.original,
            ",".join(sorted(self.expanded_terms)),
            str(sorted(self.filters.items())),
        ]
        # Use SHA-256 truncated to 16 chars for cache key (not security-sensitive)
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:16]


@dataclass
class RankedResult:
    """A search result with ranking metadata."""

    result: MemoryResult
    original_score: float
    boosted_score: float
    rank_factors: dict[str, float] = field(default_factory=dict)

    @property
    def final_score(self) -> float:
        """Return the final ranking score."""
        return self.boosted_score


@dataclass
class SearchCache:
    """In-memory cache for search results with O(1) eviction (PERF-006)."""

    _cache: OrderedDict[str, tuple[list[MemoryResult], float]] = field(
        default_factory=OrderedDict
    )
    _ttl_seconds: float = SEARCH_CACHE_TTL_SECONDS
    _max_size: int = 100

    def get(self, key: str) -> list[MemoryResult] | None:
        """Get cached results if not expired."""
        if key in self._cache:
            results, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl_seconds:
                # Move to end to mark as recently used (LRU behavior)
                self._cache.move_to_end(key)
                return results
            # Expired, remove from cache
            del self._cache[key]
        return None

    def set(self, key: str, results: list[MemoryResult]) -> None:
        """Cache search results with O(1) eviction (PERF-006)."""
        # If key exists, update it
        if key in self._cache:
            del self._cache[key]

        # Evict oldest entry if cache is full - O(1) with OrderedDict
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)  # Remove oldest (first) item

        self._cache[key] = (results, time.time())

    def invalidate(self, pattern: str | None = None) -> int:
        """Invalidate cache entries matching pattern (or all if None)."""
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        keys_to_remove = [k for k in self._cache if pattern in k]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl_seconds,
        }


class QueryExpander:
    """Expands search queries with synonyms and related terms."""

    def __init__(
        self,
        synonyms: dict[str, list[str]] | None = None,
        domain_expansions: dict[str, list[str]] | None = None,
        max_expansions: int = 5,
    ) -> None:
        """Initialize the query expander.

        Args:
            synonyms: Dictionary mapping terms to their synonyms.
            domain_expansions: Dictionary mapping domain terms to related terms.
            max_expansions: Maximum number of expansion terms to add.
        """
        self._synonyms = synonyms or QUERY_SYNONYMS
        self._domain_expansions = domain_expansions or DOMAIN_EXPANSIONS
        self._max_expansions = max_expansions

    def expand(self, query: str) -> SearchQuery:
        """Expand a search query with related terms.

        Args:
            query: The original search query.

        Returns:
            SearchQuery with original and expanded terms.
        """
        # Tokenize query
        tokens = self._tokenize(query)

        # Collect expansions
        expansions: set[str] = set()

        for token in tokens:
            token_lower = token.lower()

            # Add synonyms
            if token_lower in self._synonyms:
                for synonym in self._synonyms[token_lower][: self._max_expansions]:
                    expansions.add(synonym)

            # Add domain expansions
            if token_lower in self._domain_expansions:
                for expansion in self._domain_expansions[token_lower][
                    : self._max_expansions
                ]:
                    expansions.add(expansion)

        # Remove tokens that are already in the query
        expansions -= {t.lower() for t in tokens}

        # Limit total expansions
        limited_expansions = list(expansions)[: self._max_expansions * 2]

        return SearchQuery(
            original=query,
            expanded_terms=tuple(limited_expansions),
        )

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization by splitting on whitespace and punctuation."""
        # Replace common punctuation with spaces
        for char in ".,;:!?()[]{}\"'":
            text = text.replace(char, " ")
        return [t for t in text.split() if len(t) > 1]


class ResultReranker:
    """Re-ranks search results using multiple signals."""

    def __init__(
        self,
        recency_weight: float = 0.2,
        namespace_weight: float = 0.1,
        tag_weight: float = 0.1,
        spec_weight: float = 0.15,
    ) -> None:
        """Initialize the re-ranker.

        Args:
            recency_weight: Weight for recency boost (0-1).
            namespace_weight: Weight for namespace relevance (0-1).
            tag_weight: Weight for tag matching (0-1).
            spec_weight: Weight for spec matching (0-1).
        """
        self._recency_weight = recency_weight
        self._namespace_weight = namespace_weight
        self._tag_weight = tag_weight
        self._spec_weight = spec_weight

        # Namespace priority (higher = more important)
        self._namespace_priority: dict[str, float] = {
            "decisions": 1.0,
            "learnings": 0.9,
            "blockers": 0.85,
            "patterns": 0.8,
            "progress": 0.7,
            "retrospective": 0.75,
            "research": 0.6,
            "elicitation": 0.5,
            "inception": 0.5,
            "reviews": 0.7,
        }

    def rerank(
        self,
        results: list[MemoryResult],
        query: SearchQuery,
        target_spec: str | None = None,
        target_namespace: str | None = None,
        target_tags: list[str] | None = None,
    ) -> list[RankedResult]:
        """Re-rank search results with boosting factors.

        Args:
            results: Original search results.
            query: The search query (for context).
            target_spec: Boost results from this spec.
            target_namespace: Boost results from this namespace.
            target_tags: Boost results with these tags.

        Returns:
            Re-ranked results with ranking metadata.
        """
        ranked: list[RankedResult] = []

        for result in results:
            rank_factors: dict[str, float] = {}

            # Recency boost (exponential decay over 30 days)
            recency_boost = self._calculate_recency_boost(result.timestamp)
            rank_factors["recency"] = recency_boost

            # Namespace relevance
            namespace_boost = self._namespace_priority.get(result.namespace, 0.5)
            if target_namespace and result.namespace == target_namespace:
                namespace_boost += 0.2  # Extra boost for exact match
            rank_factors["namespace"] = namespace_boost

            # Spec match boost
            spec_boost = 0.0
            if target_spec and result.spec == target_spec:
                spec_boost = 1.0
            rank_factors["spec"] = spec_boost

            # Tag match boost
            tag_boost = 0.0
            if target_tags and result.tags:
                matching_tags = set(target_tags) & set(result.tags)
                tag_boost = len(matching_tags) / max(len(target_tags), 1)
            rank_factors["tags"] = tag_boost

            # Calculate final boosted score
            original_score = result.score
            boost = (
                self._recency_weight * recency_boost
                + self._namespace_weight * namespace_boost
                + self._spec_weight * spec_boost
                + self._tag_weight * tag_boost
            )

            # Lower score is better for similarity, so we subtract the boost
            boosted_score = max(0.0, original_score - boost * 0.1)

            ranked.append(
                RankedResult(
                    result=result,
                    original_score=original_score,
                    boosted_score=boosted_score,
                    rank_factors=rank_factors,
                )
            )

        # Sort by boosted score (ascending - lower is better)
        ranked.sort(key=lambda r: r.boosted_score)

        return ranked

    def _calculate_recency_boost(
        self,
        timestamp: datetime | None,
        half_life_days: float = 30.0,
    ) -> float:
        """Calculate recency boost using exponential decay.

        Args:
            timestamp: The timestamp of the memory.
            half_life_days: Days until boost is halved.

        Returns:
            Recency boost value between 0 and 1.
        """
        # Use shared utility to avoid DRY violation (QUAL-002)
        from .utils import calculate_temporal_decay

        return calculate_temporal_decay(timestamp, half_life_days)


class SearchOptimizer:
    """High-level search optimization coordinator."""

    def __init__(
        self,
        expander: QueryExpander | None = None,
        reranker: ResultReranker | None = None,
        cache: SearchCache | None = None,
    ) -> None:
        """Initialize the search optimizer.

        Args:
            expander: Query expander instance.
            reranker: Result re-ranker instance.
            cache: Search cache instance.
        """
        self._expander = expander or QueryExpander()
        self._reranker = reranker or ResultReranker()
        self._cache = cache or SearchCache()

    def expand_query(self, query: str) -> SearchQuery:
        """Expand a search query with related terms."""
        return self._expander.expand(query)

    def rerank_results(
        self,
        results: list[MemoryResult],
        query: SearchQuery,
        **kwargs: Any,
    ) -> list[RankedResult]:
        """Re-rank search results."""
        return self._reranker.rerank(results, query, **kwargs)

    def get_cached(self, cache_key: str) -> list[MemoryResult] | None:
        """Get cached results."""
        return self._cache.get(cache_key)

    def cache_results(self, cache_key: str, results: list[MemoryResult]) -> None:
        """Cache search results."""
        self._cache.set(cache_key, results)

    def invalidate_cache(self, pattern: str | None = None) -> int:
        """Invalidate cache entries."""
        return self._cache.invalidate(pattern)

    def cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self._cache.stats()


# Module-level singleton for convenience
_optimizer: SearchOptimizer | None = None


def get_optimizer() -> SearchOptimizer:
    """Get or create the search optimizer singleton."""
    global _optimizer
    if _optimizer is None:
        _optimizer = SearchOptimizer()
    return _optimizer


def reset_optimizer() -> None:
    """Reset the optimizer singleton for testing (ARCH-001).

    This function allows tests to reset the module-level singleton
    to ensure test isolation.
    """
    global _optimizer
    _optimizer = None
