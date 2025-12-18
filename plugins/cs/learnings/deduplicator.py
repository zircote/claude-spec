"""
Content deduplication for learning capture.

Prevents capturing the same learning multiple times within a session
using content hashing and an LRU cache.
"""

import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


def get_content_hash(content: str, max_length: int = 1000) -> str:
    """
    Generate a content hash for deduplication.

    Uses SHA256 and takes the first 16 characters for a compact
    but collision-resistant identifier.

    Args:
        content: Text content to hash
        max_length: Maximum content length to consider (truncates longer)

    Returns:
        16-character hex hash string
    """
    # Normalize content: lowercase, strip whitespace, truncate
    normalized = content.lower().strip()[:max_length]
    # Hash the normalized content
    hash_bytes = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return hash_bytes[:16]


def get_learning_hash(
    tool_name: str,
    exit_code: int | None,
    output_excerpt: str,
) -> str:
    """
    Generate a hash specific to a learning event.

    Combines tool name, exit code, and output to create a unique
    identifier for deduplication purposes.

    Args:
        tool_name: Name of the tool (Bash, Read, etc.)
        exit_code: Exit code if applicable
        output_excerpt: Relevant output text

    Returns:
        16-character hex hash string
    """
    # Build content string for hashing
    parts = [
        tool_name.lower(),
        str(exit_code) if exit_code is not None else "none",
        output_excerpt.strip()[:500],  # First 500 chars of output
    ]
    content = "|".join(parts)
    return get_content_hash(content)


@dataclass
class DeduplicationResult:
    """Result of a deduplication check."""

    is_duplicate: bool
    content_hash: str
    hit_count: int = 0  # How many times this hash was seen


class SessionDeduplicator:
    """
    Session-scoped deduplication using LRU cache.

    Tracks content hashes seen during a session to prevent
    capturing the same learning multiple times.
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize the deduplicator.

        Args:
            max_size: Maximum number of hashes to track (LRU eviction)
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, int] = OrderedDict()

    def is_duplicate(self, content_hash: str) -> bool:
        """
        Check if content has been seen this session.

        Args:
            content_hash: Hash from get_content_hash() or get_learning_hash()

        Returns:
            True if this hash was seen before
        """
        return content_hash in self._cache

    def check(self, content_hash: str) -> DeduplicationResult:
        """
        Check and register a content hash.

        If not a duplicate, registers the hash in the cache.
        If already seen, increments the hit count.

        Args:
            content_hash: Hash to check/register

        Returns:
            DeduplicationResult with duplicate status and hit count
        """
        if content_hash in self._cache:
            # Move to end (most recently used) and increment count
            self._cache.move_to_end(content_hash)
            self._cache[content_hash] += 1
            return DeduplicationResult(
                is_duplicate=True,
                content_hash=content_hash,
                hit_count=self._cache[content_hash],
            )

        # New hash - add to cache
        self._cache[content_hash] = 1

        # Evict oldest if over capacity
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

        return DeduplicationResult(
            is_duplicate=False,
            content_hash=content_hash,
            hit_count=1,
        )

    def check_learning(
        self,
        tool_name: str,
        exit_code: int | None,
        output_excerpt: str,
    ) -> DeduplicationResult:
        """
        Convenience method to check a learning event for duplication.

        Args:
            tool_name: Name of the tool
            exit_code: Exit code if applicable
            output_excerpt: Relevant output text

        Returns:
            DeduplicationResult
        """
        content_hash = get_learning_hash(tool_name, exit_code, output_excerpt)
        return self.check(content_hash)

    def clear(self) -> None:
        """Clear all cached hashes."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Current number of tracked hashes."""
        return len(self._cache)

    def get_stats(self) -> dict[str, Any]:
        """Get deduplication statistics."""
        total_hits = sum(count for count in self._cache.values() if count > 1)
        duplicates = sum(1 for count in self._cache.values() if count > 1)
        return {
            "cache_size": len(self._cache),
            "max_size": self.max_size,
            "unique_hashes": len(self._cache),
            "duplicate_hits": total_hits,
            "duplicate_patterns": duplicates,
        }


# Thread-safe singleton for module-level caching
# This is reset on session start and shared across hook invocations
_session_deduplicator: SessionDeduplicator | None = None
_deduplicator_lock = threading.Lock()


def get_session_deduplicator() -> SessionDeduplicator:
    """
    Get or create the session-scoped deduplicator.

    Thread-safe lazy initialization with double-checked locking.

    Returns:
        SessionDeduplicator instance for this session
    """
    global _session_deduplicator

    if _session_deduplicator is None:
        with _deduplicator_lock:
            # Double-checked locking
            if _session_deduplicator is None:
                _session_deduplicator = SessionDeduplicator()
    return _session_deduplicator


def reset_session_deduplicator() -> None:
    """Reset the session deduplicator (call on session start)."""
    global _session_deduplicator
    with _deduplicator_lock:
        _session_deduplicator = None
