"""Tests for the search optimization module."""

import time
from datetime import UTC, datetime

from memory.models import Memory, MemoryResult
from memory.search import (
    QueryExpander,
    RankedResult,
    ResultReranker,
    SearchCache,
    SearchOptimizer,
    SearchQuery,
)


def make_memory_result(
    memory_id: str,
    namespace: str,
    summary: str,
    score: float,
    content: str = "Test content",
    timestamp: datetime | None = None,
    spec: str | None = None,
    tags: tuple[str, ...] = (),
) -> MemoryResult:
    """Helper to create MemoryResult with proper Memory wrapper."""
    commit_sha = memory_id.split(":")[-1] if ":" in memory_id else "abc123"
    memory = Memory(
        id=memory_id,
        commit_sha=commit_sha,
        namespace=namespace,
        summary=summary,
        content=content,
        timestamp=timestamp or datetime.now(UTC),
        spec=spec,
        tags=tags,
    )
    return MemoryResult(memory=memory, distance=score)


class TestQueryExpander:
    """Tests for QueryExpander."""

    def test_expand_basic_query(self):
        """Test basic query expansion."""
        expander = QueryExpander()
        result = expander.expand("database selection")

        assert result.original == "database selection"
        assert isinstance(result.expanded_terms, tuple)
        # Should expand "database" with synonyms
        assert any(
            term in result.expanded_terms
            for term in ["db", "postgres", "sql", "storage"]
        )

    def test_expand_decision_query(self):
        """Test expansion of decision-related query."""
        expander = QueryExpander()
        result = expander.expand("why did we decide")

        # Should expand "why" and "decide"
        assert "decision" in result.expanded_terms or "reason" in result.expanded_terms

    def test_expand_empty_query(self):
        """Test expansion of empty query."""
        expander = QueryExpander()
        result = expander.expand("")

        assert result.original == ""
        assert len(result.expanded_terms) == 0

    def test_max_expansions_limit(self):
        """Test that expansions are limited."""
        expander = QueryExpander(max_expansions=2)
        result = expander.expand("database authentication performance")

        # Should be limited
        assert len(result.expanded_terms) <= 2 * 2  # max_expansions * 2


class TestSearchCache:
    """Tests for SearchCache."""

    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        cache = SearchCache()
        results = [make_memory_result("test:123", "decisions", "Test result", 0.5)]

        cache.set("key1", results)
        retrieved = cache.get("key1")

        assert retrieved is not None
        assert len(retrieved) == 1
        assert retrieved[0].id == "test:123"

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = SearchCache()
        assert cache.get("nonexistent") is None

    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = SearchCache()
        cache._ttl_seconds = 0.01  # 10ms TTL

        results = [make_memory_result("test:123", "decisions", "Test", 0.5)]
        cache.set("key1", results)

        # Wait for expiration
        time.sleep(0.02)

        assert cache.get("key1") is None

    def test_cache_invalidate_all(self):
        """Test invalidating all cache entries."""
        cache = SearchCache()
        results = [make_memory_result("test:123", "decisions", "Test", 0.5)]

        cache.set("key1", results)
        cache.set("key2", results)

        count = cache.invalidate()

        assert count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_invalidate_pattern(self):
        """Test invalidating cache entries by pattern."""
        cache = SearchCache()
        results = [make_memory_result("test:123", "decisions", "Test", 0.5)]

        cache.set("auth:key1", results)
        cache.set("auth:key2", results)
        cache.set("other:key3", results)

        count = cache.invalidate("auth")

        assert count == 2
        assert cache.get("auth:key1") is None
        assert cache.get("other:key3") is not None

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = SearchCache()
        stats = cache.stats()

        assert "size" in stats
        assert "max_size" in stats
        assert "ttl_seconds" in stats


class TestResultReranker:
    """Tests for ResultReranker."""

    def test_rerank_basic(self):
        """Test basic re-ranking."""
        reranker = ResultReranker()
        results = [
            make_memory_result("test:1", "decisions", "First result", 0.5),
            make_memory_result("test:2", "learnings", "Second result", 0.3),
        ]
        query = SearchQuery(original="test", expanded_terms=())

        ranked = reranker.rerank(results, query)

        assert len(ranked) == 2
        assert all(isinstance(r, RankedResult) for r in ranked)

    def test_rerank_with_spec_boost(self):
        """Test re-ranking with spec boost."""
        reranker = ResultReranker()
        # Use same original score to isolate spec boost effect
        results = [
            make_memory_result(
                "test:1", "decisions", "First result", 0.5, spec="other-spec"
            ),
            make_memory_result(
                "test:2", "decisions", "Second result", 0.5, spec="target-spec"
            ),
        ]
        query = SearchQuery(original="test", expanded_terms=())

        ranked = reranker.rerank(results, query, target_spec="target-spec")

        # The one with matching spec should have better rank (lower boosted score)
        assert ranked[0].result.spec == "target-spec"

    def test_rerank_factors_recorded(self):
        """Test that ranking factors are recorded."""
        reranker = ResultReranker()
        results = [
            make_memory_result(
                "test:1", "decisions", "Test", 0.5, tags=("auth", "security")
            )
        ]
        query = SearchQuery(original="test", expanded_terms=())

        ranked = reranker.rerank(results, query, target_tags=["auth"])

        assert "recency" in ranked[0].rank_factors
        assert "namespace" in ranked[0].rank_factors
        assert "tags" in ranked[0].rank_factors


class TestSearchOptimizer:
    """Tests for SearchOptimizer."""

    def test_optimizer_expand_query(self):
        """Test query expansion through optimizer."""
        optimizer = SearchOptimizer()
        query = optimizer.expand_query("database decision")

        assert query.original == "database decision"
        assert len(query.expanded_terms) > 0

    def test_optimizer_cache_operations(self):
        """Test cache operations through optimizer."""
        optimizer = SearchOptimizer()
        results = [make_memory_result("test:1", "decisions", "Test", 0.5)]

        optimizer.cache_results("key1", results)
        retrieved = optimizer.get_cached("key1")

        assert retrieved is not None
        assert len(retrieved) == 1

    def test_optimizer_cache_invalidate(self):
        """Test cache invalidation through optimizer."""
        optimizer = SearchOptimizer()
        results = [make_memory_result("test:1", "decisions", "Test", 0.5)]

        optimizer.cache_results("key1", results)
        count = optimizer.invalidate_cache()

        assert count == 1
        assert optimizer.get_cached("key1") is None


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_cache_key_generation(self):
        """Test cache key generation."""
        query1 = SearchQuery(original="test", expanded_terms=("a", "b"))
        query2 = SearchQuery(original="test", expanded_terms=("a", "b"))
        query3 = SearchQuery(original="test", expanded_terms=("b", "a"))

        # Same query should produce same key
        assert query1.cache_key() == query2.cache_key()
        # Different order should produce same key (sorted)
        assert query1.cache_key() == query3.cache_key()

    def test_cache_key_different_queries(self):
        """Test different queries produce different keys."""
        query1 = SearchQuery(original="test", expanded_terms=("a",))
        query2 = SearchQuery(original="other", expanded_terms=("a",))

        assert query1.cache_key() != query2.cache_key()
