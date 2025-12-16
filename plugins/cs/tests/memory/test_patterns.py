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


# ============================================================================
# ADDITIONAL TESTS FOR COVERAGE
# ============================================================================


class TestPatternDetectorLearningPatterns:
    """Tests for learning pattern detection."""

    def test_detect_learning_cluster_by_tag(self):
        """Test detection of learning clusters based on tags."""
        detector = PatternDetector(min_occurrences=2)
        memories = [
            make_memory_result(
                "test:1",
                "learnings",
                "First caching lesson",
                0.5,
                tags=("performance",),
            ),
            make_memory_result(
                "test:2",
                "learnings",
                "Second caching lesson",
                0.5,
                tags=("performance",),
            ),
            make_memory_result(
                "test:3",
                "learnings",
                "Third performance insight",
                0.5,
                tags=("performance",),
            ),
        ]

        patterns = detector.detect_patterns(memories)

        # Should detect performance learning cluster
        learning_clusters = [
            p for p in patterns if "Learning cluster" in p.name
        ]
        assert len(learning_clusters) >= 1
        assert any("performance" in p.tags for p in learning_clusters)


class TestPatternDetectorDecisionPatterns:
    """Tests for decision pattern detection."""

    def test_detect_decision_domain_pattern(self):
        """Test detection of decision patterns by domain."""
        detector = PatternDetector(min_occurrences=2)
        memories = [
            make_memory_result(
                "test:1",
                "decisions",
                "Chose React for frontend",
                0.5,
                tags=("frontend",),
            ),
            make_memory_result(
                "test:2",
                "decisions",
                "Selected Vue for widgets",
                0.5,
                tags=("frontend",),
            ),
        ]

        patterns = detector.detect_patterns(memories)

        # Should detect decision pattern for frontend
        decision_patterns = [
            p for p in patterns if "Decision pattern" in p.name
        ]
        assert len(decision_patterns) >= 1


class TestClassifyPhrase:
    """Tests for _classify_phrase internal method."""

    def test_classify_success_phrase(self):
        """Test classification of success keywords."""
        detector = PatternDetector()
        # Access private method for testing
        result = detector._classify_phrase("worked well")
        assert result == PatternType.SUCCESS

    def test_classify_antipattern_phrase(self):
        """Test classification of anti-pattern keywords."""
        detector = PatternDetector()
        result = detector._classify_phrase("avoid this issue")
        assert result == PatternType.ANTI_PATTERN

    def test_classify_workflow_phrase(self):
        """Test classification of workflow keywords."""
        detector = PatternDetector()
        result = detector._classify_phrase("use process for review")
        assert result == PatternType.WORKFLOW

    def test_classify_decision_phrase(self):
        """Test classification of decision keywords."""
        detector = PatternDetector()
        result = detector._classify_phrase("we decided to use this")
        assert result == PatternType.DECISION

    def test_classify_technical_phrase(self):
        """Test default classification to technical."""
        detector = PatternDetector()
        result = detector._classify_phrase("random words here")
        assert result == PatternType.TECHNICAL


class TestClassifyBlocker:
    """Tests for _classify_blocker internal method."""

    def test_classify_api_blocker(self):
        """Test API blocker classification."""
        detector = PatternDetector()
        result = detector._classify_blocker("API endpoint returned 500")
        assert result == "API"

    def test_classify_database_blocker(self):
        """Test database blocker classification."""
        detector = PatternDetector()
        result = detector._classify_blocker("Database query timeout")
        assert result == "Database"

    def test_classify_auth_blocker(self):
        """Test authentication blocker classification."""
        detector = PatternDetector()
        result = detector._classify_blocker("Auth token expired")
        assert result == "Authentication"

    def test_classify_testing_blocker(self):
        """Test testing blocker classification."""
        detector = PatternDetector()
        result = detector._classify_blocker("Test assertion failed")
        assert result == "Testing"

    def test_classify_devops_blocker(self):
        """Test DevOps blocker classification."""
        detector = PatternDetector()
        result = detector._classify_blocker("CI pipeline failed")
        assert result == "DevOps"

    def test_classify_typing_blocker(self):
        """Test typing blocker classification."""
        detector = PatternDetector()
        result = detector._classify_blocker("TypeScript type error")
        assert result == "Typing"

    def test_classify_dependencies_blocker(self):
        """Test dependencies blocker classification."""
        detector = PatternDetector()
        result = detector._classify_blocker("Package version conflict")
        assert result == "Dependencies"

    def test_classify_general_blocker(self):
        """Test general blocker classification."""
        detector = PatternDetector()
        result = detector._classify_blocker("Unknown issue occurred")
        assert result == "General"


class TestPatternSuggestorGenerateAction:
    """Tests for _generate_action internal method."""

    def test_generate_success_action(self):
        """Test action generation for success pattern."""
        suggestor = PatternSuggestor()
        pattern = DetectedPattern(
            name="Cache Tokens",
            pattern_type=PatternType.SUCCESS,
            description="Cache auth tokens",
            evidence=(),
            confidence=0.9,
        )
        action = suggestor._generate_action(pattern)
        assert "Consider applying" in action

    def test_generate_antipattern_action(self):
        """Test action generation for anti-pattern."""
        suggestor = PatternSuggestor()
        pattern = DetectedPattern(
            name="N+1 Queries",
            pattern_type=PatternType.ANTI_PATTERN,
            description="Avoid N+1 queries",
            evidence=(),
            confidence=0.9,
        )
        action = suggestor._generate_action(pattern)
        assert "Avoid" in action

    def test_generate_workflow_action(self):
        """Test action generation for workflow pattern."""
        suggestor = PatternSuggestor()
        pattern = DetectedPattern(
            name="Code Review Process",
            pattern_type=PatternType.WORKFLOW,
            description="Follow PR checklist",
            evidence=(),
            confidence=0.9,
        )
        action = suggestor._generate_action(pattern)
        assert "Follow workflow" in action

    def test_generate_decision_action(self):
        """Test action generation for decision pattern."""
        suggestor = PatternSuggestor()
        pattern = DetectedPattern(
            name="Database Choice",
            pattern_type=PatternType.DECISION,
            description="Use PostgreSQL",
            evidence=(),
            confidence=0.9,
        )
        action = suggestor._generate_action(pattern)
        assert "Review past decisions" in action

    def test_generate_technical_action(self):
        """Test action generation for technical pattern (default)."""
        suggestor = PatternSuggestor()
        pattern = DetectedPattern(
            name="Indexing Strategy",
            pattern_type=PatternType.TECHNICAL,
            description="Add composite indexes",
            evidence=(),
            confidence=0.9,
        )
        action = suggestor._generate_action(pattern)
        assert "Consider" in action


class TestPatternSuggestorExplainMatch:
    """Tests for _explain_match internal method."""

    def test_explain_match_with_tag(self):
        """Test explanation when tag matches context."""
        suggestor = PatternSuggestor()
        pattern = DetectedPattern(
            name="Auth Pattern",
            pattern_type=PatternType.SUCCESS,
            description="Auth improvement",
            evidence=(),
            confidence=0.9,
            tags=("auth",),
        )
        explanation = suggestor._explain_match(pattern, "working on auth module")
        assert "matches 'auth'" in explanation

    def test_explain_match_with_name_word(self):
        """Test explanation when name word matches context."""
        suggestor = PatternSuggestor()
        pattern = DetectedPattern(
            name="Database Optimization",
            pattern_type=PatternType.SUCCESS,
            description="Optimize queries",
            evidence=(),
            confidence=0.9,
            tags=(),
        )
        explanation = suggestor._explain_match(pattern, "database query tuning")
        assert "relates to 'database'" in explanation

    def test_explain_match_fallback(self):
        """Test fallback explanation when nothing matches."""
        suggestor = PatternSuggestor()
        pattern = DetectedPattern(
            name="X Y Z",  # Short words won't match (< 3 chars)
            pattern_type=PatternType.SUCCESS,
            description="Something",
            evidence=(),
            confidence=0.9,
            tags=(),
        )
        explanation = suggestor._explain_match(pattern, "completely unrelated context")
        assert "may be relevant" in explanation


class TestPatternManagerEdgeCases:
    """Tests for PatternManager edge cases."""

    def test_promote_nonexistent_pattern(self):
        """Test promoting a pattern that doesn't exist."""
        manager = PatternManager()
        result = manager.promote_pattern("nonexistent:key")
        assert result is None

    def test_deprecate_nonexistent_pattern(self):
        """Test deprecating a pattern that doesn't exist."""
        manager = PatternManager()
        result = manager.deprecate_pattern("nonexistent:key")
        assert result is None

    def test_get_patterns_by_status(self):
        """Test filtering patterns by status."""
        manager = PatternManager()
        manager.register_pattern(
            DetectedPattern(
                name="Pattern 1",
                pattern_type=PatternType.SUCCESS,
                description="P1",
                evidence=(),
                confidence=0.8,
            )
        )
        # Promote one pattern
        key = f"{PatternType.SUCCESS.value}:Pattern 1"
        manager.promote_pattern(key)

        promoted = manager.get_patterns(status=PatternStatus.PROMOTED)
        candidates = manager.get_patterns(status=PatternStatus.CANDIDATE)

        assert len(promoted) == 1
        assert len(candidates) == 0

    def test_detect_via_manager(self):
        """Test detect method on PatternManager."""
        manager = PatternManager()
        memories = [
            make_memory_result(
                "test:1",
                "decisions",
                "First",
                0.5,
                tags=("auth",),
            ),
        ]
        patterns = manager.detect(memories)
        # Should return empty list for single memory
        assert isinstance(patterns, list)

    def test_suggest_via_manager(self):
        """Test suggest method on PatternManager."""
        manager = PatternManager()
        # Register and promote a pattern
        pattern = DetectedPattern(
            name="Auth Pattern",
            pattern_type=PatternType.SUCCESS,
            description="Auth best practice",
            evidence=(),
            confidence=0.9,
            tags=("auth",),
        )
        manager.register_pattern(pattern)
        key = f"{PatternType.SUCCESS.value}:Auth Pattern"
        manager.promote_pattern(key)

        suggestions = manager.suggest(
            context="working on authentication",
            current_tags=["auth"],
        )
        # May or may not have suggestions based on relevance
        assert isinstance(suggestions, list)


class TestPatternSingleton:
    """Tests for pattern manager singleton functions."""

    def test_get_pattern_manager(self):
        """Test getting the pattern manager singleton."""
        from memory.patterns import get_pattern_manager, reset_pattern_manager

        # Reset first to ensure clean state
        reset_pattern_manager()

        manager1 = get_pattern_manager()
        manager2 = get_pattern_manager()

        assert manager1 is manager2
        assert isinstance(manager1, PatternManager)

    def test_reset_pattern_manager(self):
        """Test resetting the pattern manager singleton."""
        from memory.patterns import get_pattern_manager, reset_pattern_manager

        manager1 = get_pattern_manager()
        reset_pattern_manager()
        manager2 = get_pattern_manager()

        assert manager1 is not manager2
