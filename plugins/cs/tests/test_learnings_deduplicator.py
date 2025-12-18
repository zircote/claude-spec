"""Tests for learnings/deduplicator.py - Content deduplication for learning capture.

Tests cover:
- get_content_hash() function
- get_learning_hash() function
- DeduplicationResult dataclass
- SessionDeduplicator class
- LRU cache behavior
- Global session deduplicator management
"""

import sys
from pathlib import Path

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from learnings.deduplicator import (
    DeduplicationResult,
    SessionDeduplicator,
    get_content_hash,
    get_learning_hash,
    get_session_deduplicator,
    reset_session_deduplicator,
)

# =============================================================================
# Tests for get_content_hash()
# =============================================================================


class TestGetContentHash:
    """Tests for get_content_hash function."""

    def test_returns_16_char_hex_string(self):
        """Test hash is 16-character hex string."""
        result = get_content_hash("test content")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_content_same_hash(self):
        """Test same content produces same hash."""
        hash1 = get_content_hash("identical content")
        hash2 = get_content_hash("identical content")
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Test different content produces different hash."""
        hash1 = get_content_hash("content one")
        hash2 = get_content_hash("content two")
        assert hash1 != hash2

    def test_case_insensitive_normalization(self):
        """Test content is normalized to lowercase."""
        hash1 = get_content_hash("TEST CONTENT")
        hash2 = get_content_hash("test content")
        assert hash1 == hash2

    def test_whitespace_normalized(self):
        """Test whitespace is stripped."""
        hash1 = get_content_hash("  content  ")
        hash2 = get_content_hash("content")
        assert hash1 == hash2

    def test_truncates_long_content(self):
        """Test long content is truncated."""
        short = "x" * 1000
        long = "x" * 2000

        hash_short = get_content_hash(short)
        hash_long = get_content_hash(long)

        # Both should produce same hash since truncated at 1000
        assert hash_short == hash_long

    def test_custom_max_length(self):
        """Test custom max_length is respected."""
        content = "a" * 100 + "b" * 100

        hash_50 = get_content_hash(content, max_length=50)
        hash_150 = get_content_hash(content, max_length=150)

        # Different truncation points should produce different hashes
        assert hash_50 != hash_150

    def test_empty_string(self):
        """Test empty string produces valid hash."""
        result = get_content_hash("")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_unicode_content(self):
        """Test Unicode content is handled."""
        result = get_content_hash("Unicode: \u00e9\u00e8\u00ea")
        assert len(result) == 16


# =============================================================================
# Tests for get_learning_hash()
# =============================================================================


class TestGetLearningHash:
    """Tests for get_learning_hash function."""

    def test_returns_16_char_hex_string(self):
        """Test hash is 16-character hex string."""
        result = get_learning_hash("Bash", 1, "error output")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_inputs_same_hash(self):
        """Test same inputs produce same hash."""
        hash1 = get_learning_hash("Bash", 127, "command not found")
        hash2 = get_learning_hash("Bash", 127, "command not found")
        assert hash1 == hash2

    def test_different_tool_different_hash(self):
        """Test different tool produces different hash."""
        hash1 = get_learning_hash("Bash", 1, "error")
        hash2 = get_learning_hash("Read", 1, "error")
        assert hash1 != hash2

    def test_different_exit_code_different_hash(self):
        """Test different exit code produces different hash."""
        hash1 = get_learning_hash("Bash", 1, "error")
        hash2 = get_learning_hash("Bash", 2, "error")
        assert hash1 != hash2

    def test_different_output_different_hash(self):
        """Test different output produces different hash."""
        hash1 = get_learning_hash("Bash", 1, "error one")
        hash2 = get_learning_hash("Bash", 1, "error two")
        assert hash1 != hash2

    def test_none_exit_code(self):
        """Test None exit code is handled."""
        hash1 = get_learning_hash("Bash", None, "error")
        hash2 = get_learning_hash("Bash", None, "error")
        assert hash1 == hash2

    def test_none_vs_zero_exit_code(self):
        """Test None exit code differs from zero."""
        hash1 = get_learning_hash("Bash", None, "output")
        hash2 = get_learning_hash("Bash", 0, "output")
        assert hash1 != hash2

    def test_tool_name_case_insensitive(self):
        """Test tool name is case-normalized."""
        hash1 = get_learning_hash("BASH", 1, "error")
        hash2 = get_learning_hash("bash", 1, "error")
        assert hash1 == hash2

    def test_output_truncated_to_500(self):
        """Test output is truncated to first 500 chars."""
        short = "x" * 500
        long = "x" * 1000

        hash_short = get_learning_hash("Bash", 1, short)
        hash_long = get_learning_hash("Bash", 1, long)

        assert hash_short == hash_long

    def test_empty_output(self):
        """Test empty output produces valid hash."""
        result = get_learning_hash("Bash", 1, "")
        assert len(result) == 16


# =============================================================================
# Tests for DeduplicationResult Dataclass
# =============================================================================


class TestDeduplicationResult:
    """Tests for DeduplicationResult dataclass."""

    def test_basic_creation(self):
        """Test creating a DeduplicationResult."""
        result = DeduplicationResult(
            is_duplicate=False,
            content_hash="abc123def456789a",
        )

        assert result.is_duplicate is False
        assert result.content_hash == "abc123def456789a"
        assert result.hit_count == 0  # Default

    def test_with_hit_count(self):
        """Test DeduplicationResult with hit_count."""
        result = DeduplicationResult(
            is_duplicate=True,
            content_hash="abc123",
            hit_count=3,
        )

        assert result.is_duplicate is True
        assert result.hit_count == 3


# =============================================================================
# Tests for SessionDeduplicator Class
# =============================================================================


class TestSessionDeduplicator:
    """Tests for SessionDeduplicator class."""

    def test_initialization_default_size(self):
        """Test deduplicator initializes with default max_size."""
        dedup = SessionDeduplicator()
        assert dedup.max_size == 100

    def test_initialization_custom_size(self):
        """Test deduplicator with custom max_size."""
        dedup = SessionDeduplicator(max_size=50)
        assert dedup.max_size == 50

    def test_is_duplicate_new_hash(self):
        """Test is_duplicate returns False for new hash."""
        dedup = SessionDeduplicator()
        result = dedup.is_duplicate("abc123")
        assert result is False

    def test_is_duplicate_seen_hash(self):
        """Test is_duplicate returns True for seen hash."""
        dedup = SessionDeduplicator()
        dedup.check("abc123")  # Register hash
        result = dedup.is_duplicate("abc123")
        assert result is True

    def test_check_new_hash(self):
        """Test check() registers new hash."""
        dedup = SessionDeduplicator()
        result = dedup.check("abc123")

        assert result.is_duplicate is False
        assert result.content_hash == "abc123"
        assert result.hit_count == 1

    def test_check_duplicate_hash(self):
        """Test check() detects duplicate hash."""
        dedup = SessionDeduplicator()
        dedup.check("abc123")  # First time
        result = dedup.check("abc123")  # Second time

        assert result.is_duplicate is True
        assert result.hit_count == 2

    def test_check_increments_hit_count(self):
        """Test hit count increments on each check."""
        dedup = SessionDeduplicator()
        dedup.check("abc123")
        dedup.check("abc123")
        result = dedup.check("abc123")

        assert result.hit_count == 3

    def test_check_learning_convenience_method(self):
        """Test check_learning() convenience method."""
        dedup = SessionDeduplicator()
        result = dedup.check_learning(
            tool_name="Bash",
            exit_code=1,
            output_excerpt="error output",
        )

        assert result.is_duplicate is False
        assert len(result.content_hash) == 16

    def test_check_learning_detects_duplicates(self):
        """Test check_learning() detects duplicate learnings."""
        dedup = SessionDeduplicator()
        dedup.check_learning("Bash", 1, "error output")
        result = dedup.check_learning("Bash", 1, "error output")

        assert result.is_duplicate is True

    def test_clear_removes_all(self):
        """Test clear() removes all cached hashes."""
        dedup = SessionDeduplicator()
        dedup.check("hash1")
        dedup.check("hash2")
        dedup.check("hash3")

        dedup.clear()

        assert dedup.size == 0
        assert not dedup.is_duplicate("hash1")
        assert not dedup.is_duplicate("hash2")

    def test_size_property(self):
        """Test size property returns cache size."""
        dedup = SessionDeduplicator()
        assert dedup.size == 0

        dedup.check("hash1")
        assert dedup.size == 1

        dedup.check("hash2")
        assert dedup.size == 2

        dedup.check("hash1")  # Duplicate - no size increase
        assert dedup.size == 2


# =============================================================================
# Tests for LRU Cache Behavior
# =============================================================================


class TestLRUCacheBehavior:
    """Tests for LRU cache eviction behavior."""

    def test_lru_eviction_when_over_max_size(self):
        """Test oldest entries are evicted when over max size."""
        dedup = SessionDeduplicator(max_size=3)

        dedup.check("hash1")
        dedup.check("hash2")
        dedup.check("hash3")
        dedup.check("hash4")  # Should evict hash1

        assert dedup.size == 3
        assert not dedup.is_duplicate("hash1")  # Was evicted
        assert dedup.is_duplicate("hash2")
        assert dedup.is_duplicate("hash3")
        assert dedup.is_duplicate("hash4")

    def test_lru_moves_accessed_to_end(self):
        """Test accessed entries move to end (most recent)."""
        dedup = SessionDeduplicator(max_size=3)

        dedup.check("hash1")
        dedup.check("hash2")
        dedup.check("hash3")
        dedup.check("hash1")  # Access hash1 - moves to end
        dedup.check("hash4")  # Should evict hash2 (now oldest)

        assert dedup.is_duplicate("hash1")  # Was accessed, not evicted
        assert not dedup.is_duplicate("hash2")  # Was evicted
        assert dedup.is_duplicate("hash3")
        assert dedup.is_duplicate("hash4")

    def test_max_size_one(self):
        """Test cache with max_size=1."""
        dedup = SessionDeduplicator(max_size=1)

        dedup.check("hash1")
        assert dedup.is_duplicate("hash1")

        dedup.check("hash2")
        assert not dedup.is_duplicate("hash1")  # Evicted
        assert dedup.is_duplicate("hash2")

    def test_large_max_size(self):
        """Test cache with large max_size."""
        dedup = SessionDeduplicator(max_size=1000)

        for i in range(500):
            dedup.check(f"hash{i}")

        assert dedup.size == 500

        # All hashes should still be present
        for i in range(500):
            assert dedup.is_duplicate(f"hash{i}")


# =============================================================================
# Tests for get_stats()
# =============================================================================


class TestGetStats:
    """Tests for get_stats() method."""

    def test_stats_empty_cache(self):
        """Test stats for empty cache."""
        dedup = SessionDeduplicator()
        stats = dedup.get_stats()

        assert stats["cache_size"] == 0
        assert stats["max_size"] == 100
        assert stats["unique_hashes"] == 0
        assert stats["duplicate_hits"] == 0
        assert stats["duplicate_patterns"] == 0

    def test_stats_with_unique_hashes(self):
        """Test stats with unique hashes only."""
        dedup = SessionDeduplicator()
        dedup.check("hash1")
        dedup.check("hash2")
        dedup.check("hash3")

        stats = dedup.get_stats()

        assert stats["cache_size"] == 3
        assert stats["unique_hashes"] == 3
        assert stats["duplicate_hits"] == 0
        assert stats["duplicate_patterns"] == 0

    def test_stats_with_duplicates(self):
        """Test stats with duplicate hits."""
        dedup = SessionDeduplicator()
        dedup.check("hash1")
        dedup.check("hash1")  # Duplicate
        dedup.check("hash1")  # Duplicate
        dedup.check("hash2")
        dedup.check("hash2")  # Duplicate

        stats = dedup.get_stats()

        assert stats["cache_size"] == 2
        assert stats["unique_hashes"] == 2
        # hash1 has count 3, hash2 has count 2 - sum of counts for patterns with count > 1
        assert (
            stats["duplicate_hits"] == 5
        )  # 3 + 2 = 5 total hits for duplicated patterns
        assert stats["duplicate_patterns"] == 2  # Both have count > 1


# =============================================================================
# Tests for Global Session Deduplicator
# =============================================================================


class TestGlobalSessionDeduplicator:
    """Tests for global session deduplicator management."""

    def test_get_session_deduplicator_creates_instance(self):
        """Test get_session_deduplicator creates new instance."""
        reset_session_deduplicator()
        dedup = get_session_deduplicator()

        assert dedup is not None
        assert isinstance(dedup, SessionDeduplicator)

    def test_get_session_deduplicator_returns_same_instance(self):
        """Test get_session_deduplicator returns same instance."""
        reset_session_deduplicator()
        dedup1 = get_session_deduplicator()
        dedup2 = get_session_deduplicator()

        assert dedup1 is dedup2

    def test_reset_session_deduplicator(self):
        """Test reset creates fresh instance."""
        reset_session_deduplicator()
        dedup1 = get_session_deduplicator()
        dedup1.check("hash1")

        reset_session_deduplicator()
        dedup2 = get_session_deduplicator()

        assert dedup1 is not dedup2
        assert not dedup2.is_duplicate("hash1")

    def test_session_deduplicator_persists_state(self):
        """Test session deduplicator maintains state between calls."""
        reset_session_deduplicator()

        dedup1 = get_session_deduplicator()
        dedup1.check("hash1")

        dedup2 = get_session_deduplicator()
        assert dedup2.is_duplicate("hash1")


# =============================================================================
# Tests for Edge Cases
# =============================================================================


class TestDeduplicatorEdgeCases:
    """Tests for edge cases in deduplication."""

    def test_empty_output_excerpt(self):
        """Test handling of empty output excerpt."""
        dedup = SessionDeduplicator()
        result = dedup.check_learning("Bash", 1, "")

        assert result.is_duplicate is False
        assert len(result.content_hash) == 16

    def test_very_long_output_excerpt(self):
        """Test handling of very long output."""
        dedup = SessionDeduplicator()
        long_output = "x" * 10000

        result = dedup.check_learning("Bash", 1, long_output)

        assert result.is_duplicate is False
        assert len(result.content_hash) == 16

    def test_special_characters_in_output(self):
        """Test handling of special characters."""
        dedup = SessionDeduplicator()

        result = dedup.check_learning("Bash", 1, "Error: \n\t\r\0 special chars \u00e9")

        assert result.is_duplicate is False

    def test_negative_exit_code(self):
        """Test handling of negative exit code."""
        dedup = SessionDeduplicator()

        result = dedup.check_learning("Bash", -1, "signal received")

        assert result.is_duplicate is False

    def test_hash_collision_unlikely(self):
        """Test hash collisions are unlikely for different content."""
        hashes = set()

        # Generate 1000 different hashes
        for i in range(1000):
            hash_val = get_content_hash(f"unique content {i}")
            hashes.add(hash_val)

        # All should be unique (collision probability very low)
        assert len(hashes) == 1000

    def test_whitespace_variations(self):
        """Test different whitespace produces different hashes after strip."""
        # After strip(), leading/trailing whitespace is removed
        hash1 = get_content_hash("  content  ")
        hash2 = get_content_hash("content")
        assert hash1 == hash2

        # But internal whitespace differs
        hash3 = get_content_hash("content with spaces")
        hash4 = get_content_hash("content  with  spaces")
        assert hash3 != hash4
