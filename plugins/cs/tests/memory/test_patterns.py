"""Tests for the pattern extraction module."""

from datetime import UTC, datetime

import pytest

from memory.models import Memory, MemoryResult
from memory.patterns import (
    DetectedPattern,
    PatternDetector,
    PatternManager,
    PatternStatus,
    PatternSuggestor,
    PatternType,
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


class TestPatternDetector:
    """Tests for PatternDetector."""

    def test_detect_tag_patterns(self):
        """Test detection of tag co-occurrence patterns."""
        detector = PatternDetector(min_occurrences=2)
        memories = [
            make_memory_result(
                "test:1", "decisions", "First", 0.5, tags=("auth", "security")
            ),
            make_memory_result(
                "test:2", "decisions", "Second", 0.5, tags=("auth", "security")
            ),
            make_memory_result(
                "test:3", "decisions", "Third", 0.5, tags=("auth", "security")
            ),
        ]

        patterns = detector.detect_patterns(memories)

        # Should detect auth+security pattern
        tag_patterns = [
            p for p in patterns if "auth" in p.tags and "security" in p.tags
        ]
        assert len(tag_patterns) >= 1

    def test_detect_content_patterns(self):
        """Test detection of content patterns."""
        # Use lower min_confidence since with 3 occurrences, confidence = 3/5 = 0.6
        detector = PatternDetector(min_occurrences=2, min_confidence=0.5)
        memories = [
            make_memory_result(
                "test:1",
                "learnings",
                "Learned about caching strategies",
                0.5,
                content="Caching strategies are important",
            ),
            make_memory_result(
                "test:2",
                "learnings",
                "Discovered caching strategies work well",
                0.5,
                content="Caching strategies work well",
            ),
            make_memory_result(
                "test:3",
                "learnings",
                "Improved caching strategies further",
                0.5,
                content="Caching strategies improved performance",
            ),
        ]

        patterns = detector.detect_patterns(memories)

        # Should detect "caching strategies" pattern
        content_patterns = [p for p in patterns if "caching" in p.name.lower()]
        assert len(content_patterns) >= 1

    def test_no_patterns_when_below_threshold(self):
        """Test that patterns aren't detected below threshold."""
        detector = PatternDetector(min_occurrences=5, min_confidence=0.8)
        memories = [
            make_memory_result("test:1", "decisions", "Test", 0.5, tags=("unique",)),
        ]

        patterns = detector.detect_patterns(memories)

        assert len(patterns) == 0

    def test_detect_blocker_patterns(self):
        """Test detection of blocker patterns."""
        detector = PatternDetector(min_occurrences=2)
        memories = [
            make_memory_result(
                "test:1",
                "blockers",
                "API rate limit issue",
                0.5,
                content="API rate limit hit",
            ),
            make_memory_result(
                "test:2",
                "blockers",
                "API endpoint timeout",
                0.5,
                content="API endpoint timeout error",
            ),
        ]

        patterns = detector.detect_patterns(memories)

        # Should detect API-related blocker pattern
        api_patterns = [
            p
            for p in patterns
            if p.pattern_type == PatternType.ANTI_PATTERN and "API" in str(p.tags)
        ]
        assert len(api_patterns) >= 1


class TestDetectedPattern:
    """Tests for DetectedPattern dataclass."""

    def test_pattern_creation(self):
        """Test creating a DetectedPattern."""
        pattern = DetectedPattern(
            name="Test Pattern",
            pattern_type=PatternType.SUCCESS,
            description="A test pattern",
            evidence=("mem:1", "mem:2"),
            confidence=0.8,
            tags=("test",),
        )

        assert pattern.name == "Test Pattern"
        assert pattern.pattern_type == PatternType.SUCCESS
        assert pattern.confidence == 0.8
        assert len(pattern.evidence) == 2
        assert pattern.status == PatternStatus.CANDIDATE

    def test_pattern_is_frozen(self):
        """Test that DetectedPattern is immutable."""
        pattern = DetectedPattern(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            description="Test",
            evidence=(),
            confidence=0.5,
        )

        with pytest.raises(AttributeError):
            pattern.name = "Changed"


class TestPatternSuggestor:
    """Tests for PatternSuggestor."""

    def test_suggest_relevant_patterns(self):
        """Test suggesting relevant patterns."""
        suggestor = PatternSuggestor()
        patterns = [
            DetectedPattern(
                name="Auth caching",
                pattern_type=PatternType.SUCCESS,
                description="Cache auth tokens",
                evidence=("m:1",),
                confidence=0.9,
                tags=("auth", "caching"),
                status=PatternStatus.PROMOTED,
            ),
            DetectedPattern(
                name="Database indexing",
                pattern_type=PatternType.SUCCESS,
                description="Add indexes",
                evidence=("m:2",),
                confidence=0.9,
                tags=("database",),
                status=PatternStatus.PROMOTED,
            ),
        ]

        suggestions = suggestor.suggest(
            context="working on authentication caching",
            available_patterns=patterns,
            current_tags=["auth"],
        )

        # Auth caching pattern should be suggested
        assert len(suggestions) > 0
        assert any("auth" in s.pattern.name.lower() for s in suggestions)

    def test_no_suggestions_for_unrelated_context(self):
        """Test that unrelated patterns aren't suggested."""
        suggestor = PatternSuggestor()
        patterns = [
            DetectedPattern(
                name="Database sharding",
                pattern_type=PatternType.TECHNICAL,
                description="Shard the database",
                evidence=("m:1",),
                confidence=0.5,
                tags=("database",),
                status=PatternStatus.CANDIDATE,  # Not promoted
            ),
        ]

        suggestions = suggestor.suggest(
            context="frontend ui styling",
            available_patterns=patterns,
            current_tags=["frontend"],
        )

        # Low confidence + not promoted + unrelated = no suggestions
        assert len(suggestions) == 0


class TestPatternManager:
    """Tests for PatternManager."""

    def test_register_and_get_patterns(self):
        """Test registering and retrieving patterns."""
        manager = PatternManager()
        pattern = DetectedPattern(
            name="Test Pattern",
            pattern_type=PatternType.SUCCESS,
            description="Test",
            evidence=(),
            confidence=0.8,
        )

        manager.register_pattern(pattern)
        patterns = manager.get_patterns()

        assert len(patterns) == 1
        assert patterns[0].name == "Test Pattern"

    def test_promote_pattern(self):
        """Test promoting a pattern."""
        manager = PatternManager()
        pattern = DetectedPattern(
            name="Test Pattern",
            pattern_type=PatternType.SUCCESS,
            description="Test",
            evidence=(),
            confidence=0.8,
        )

        manager.register_pattern(pattern)
        key = f"{pattern.pattern_type.value}:{pattern.name}"
        promoted = manager.promote_pattern(key)

        assert promoted is not None
        assert promoted.status == PatternStatus.PROMOTED

    def test_deprecate_pattern(self):
        """Test deprecating a pattern."""
        manager = PatternManager()
        pattern = DetectedPattern(
            name="Old Pattern",
            pattern_type=PatternType.ANTI_PATTERN,
            description="Old",
            evidence=(),
            confidence=0.8,
        )

        manager.register_pattern(pattern)
        key = f"{pattern.pattern_type.value}:{pattern.name}"
        deprecated = manager.deprecate_pattern(key)

        assert deprecated is not None
        assert deprecated.status == PatternStatus.DEPRECATED

    def test_filter_patterns_by_type(self):
        """Test filtering patterns by type."""
        manager = PatternManager()
        manager.register_pattern(
            DetectedPattern(
                name="Success 1",
                pattern_type=PatternType.SUCCESS,
                description="S1",
                evidence=(),
                confidence=0.8,
            )
        )
        manager.register_pattern(
            DetectedPattern(
                name="Anti 1",
                pattern_type=PatternType.ANTI_PATTERN,
                description="A1",
                evidence=(),
                confidence=0.8,
            )
        )

        success_patterns = manager.get_patterns(pattern_type=PatternType.SUCCESS)
        anti_patterns = manager.get_patterns(pattern_type=PatternType.ANTI_PATTERN)

        assert len(success_patterns) == 1
        assert len(anti_patterns) == 1
        assert success_patterns[0].name == "Success 1"
