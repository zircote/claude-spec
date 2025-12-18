"""Tests for learnings/models.py - Data models for tool learning capture.

Tests cover:
- LearningCategory enum values and behavior
- LearningSeverity enum values and behavior
- ToolLearning dataclass validation and immutability
- DetectionSignal dataclass defaults and immutability
- VALID_CATEGORIES and VALID_SEVERITIES sets
- ToolLearning.to_memory_args() method
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from learnings.models import (
    VALID_CATEGORIES,
    VALID_SEVERITIES,
    DetectionSignal,
    LearningCategory,
    LearningSeverity,
    ToolLearning,
)

# =============================================================================
# Tests for LearningCategory Enum
# =============================================================================


class TestLearningCategory:
    """Tests for LearningCategory enum."""

    def test_error_value(self):
        """Test ERROR category has correct value."""
        assert LearningCategory.ERROR.value == "error"

    def test_workaround_value(self):
        """Test WORKAROUND category has correct value."""
        assert LearningCategory.WORKAROUND.value == "workaround"

    def test_discovery_value(self):
        """Test DISCOVERY category has correct value."""
        assert LearningCategory.DISCOVERY.value == "discovery"

    def test_warning_value(self):
        """Test WARNING category has correct value."""
        assert LearningCategory.WARNING.value == "warning"

    def test_all_categories_have_unique_values(self):
        """Test all category values are unique."""
        values = [c.value for c in LearningCategory]
        assert len(values) == len(set(values))

    def test_category_count(self):
        """Test expected number of categories exist."""
        assert len(LearningCategory) == 4


# =============================================================================
# Tests for LearningSeverity Enum
# =============================================================================


class TestLearningSeverity:
    """Tests for LearningSeverity enum."""

    def test_sev_0_value(self):
        """Test SEV_0 (silent failure) has correct value."""
        assert LearningSeverity.SEV_0.value == "sev-0"

    def test_sev_1_value(self):
        """Test SEV_1 (hard failure) has correct value."""
        assert LearningSeverity.SEV_1.value == "sev-1"

    def test_sev_2_value(self):
        """Test SEV_2 (recoverable) has correct value."""
        assert LearningSeverity.SEV_2.value == "sev-2"

    def test_sev_3_value(self):
        """Test SEV_3 (informational) has correct value."""
        assert LearningSeverity.SEV_3.value == "sev-3"

    def test_all_severities_have_unique_values(self):
        """Test all severity values are unique."""
        values = [s.value for s in LearningSeverity]
        assert len(values) == len(set(values))

    def test_severity_count(self):
        """Test expected number of severities exist."""
        assert len(LearningSeverity) == 4


# =============================================================================
# Tests for VALID_CATEGORIES and VALID_SEVERITIES
# =============================================================================


class TestValidSets:
    """Tests for validation sets."""

    def test_valid_categories_contains_all_category_values(self):
        """Test VALID_CATEGORIES contains all LearningCategory values."""
        for category in LearningCategory:
            assert category.value in VALID_CATEGORIES

    def test_valid_severities_contains_all_severity_values(self):
        """Test VALID_SEVERITIES contains all LearningSeverity values."""
        for severity in LearningSeverity:
            assert severity.value in VALID_SEVERITIES

    def test_valid_categories_is_frozenset(self):
        """Test VALID_CATEGORIES is immutable."""
        assert isinstance(VALID_CATEGORIES, frozenset)

    def test_valid_severities_is_frozenset(self):
        """Test VALID_SEVERITIES is immutable."""
        assert isinstance(VALID_SEVERITIES, frozenset)


# =============================================================================
# Tests for ToolLearning Dataclass
# =============================================================================


class TestToolLearning:
    """Tests for ToolLearning frozen dataclass."""

    def test_basic_creation(self):
        """Test creating a ToolLearning with required fields."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Test summary",
            context="Running a test command",
            observation="Command failed with exit code 1",
        )

        assert learning.tool_name == "Bash"
        assert learning.category == "error"
        assert learning.severity == "sev-1"
        assert learning.summary == "Test summary"
        assert learning.context == "Running a test command"
        assert learning.observation == "Command failed with exit code 1"

    def test_optional_fields_defaults(self):
        """Test optional fields have correct defaults."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Test summary",
            context="Test context",
            observation="Test observation",
        )

        assert learning.exit_code is None
        assert learning.output_excerpt == ""
        assert learning.tags == ()
        assert learning.spec is None

    def test_optional_fields_custom_values(self):
        """Test setting optional fields."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Test summary",
            context="Test context",
            observation="Test observation",
            exit_code=127,
            output_excerpt="command not found",
            tags=("bash", "error"),
            spec="my-project",
        )

        assert learning.exit_code == 127
        assert learning.output_excerpt == "command not found"
        assert learning.tags == ("bash", "error")
        assert learning.spec == "my-project"

    def test_timestamp_is_set_automatically(self):
        """Test timestamp is set to current time by default."""
        before = datetime.now(UTC)
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Test summary",
            context="Test context",
            observation="Test observation",
        )
        after = datetime.now(UTC)

        assert before <= learning.timestamp <= after

    def test_frozen_immutability(self):
        """Test ToolLearning is immutable (frozen dataclass)."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Test summary",
            context="Test context",
            observation="Test observation",
        )

        with pytest.raises(AttributeError):
            learning.tool_name = "Read"  # type: ignore

    def test_invalid_category_raises_error(self):
        """Test invalid category value raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ToolLearning(
                tool_name="Bash",
                category="invalid_category",
                severity="sev-1",
                summary="Test summary",
                context="Test context",
                observation="Test observation",
            )

        assert "Invalid category" in str(exc_info.value)
        assert "invalid_category" in str(exc_info.value)

    def test_invalid_severity_raises_error(self):
        """Test invalid severity value raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ToolLearning(
                tool_name="Bash",
                category="error",
                severity="invalid_severity",
                summary="Test summary",
                context="Test context",
                observation="Test observation",
            )

        assert "Invalid severity" in str(exc_info.value)
        assert "invalid_severity" in str(exc_info.value)

    def test_summary_too_long_raises_error(self):
        """Test summary over 100 chars raises ValueError."""
        long_summary = "x" * 101

        with pytest.raises(ValueError) as exc_info:
            ToolLearning(
                tool_name="Bash",
                category="error",
                severity="sev-1",
                summary=long_summary,
                context="Test context",
                observation="Test observation",
            )

        assert "Summary too long" in str(exc_info.value)
        assert "101 chars" in str(exc_info.value)

    def test_summary_exactly_100_chars_is_valid(self):
        """Test summary exactly 100 chars is accepted."""
        summary_100 = "x" * 100

        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary=summary_100,
            context="Test context",
            observation="Test observation",
        )

        assert len(learning.summary) == 100

    def test_all_valid_categories(self):
        """Test all valid category values are accepted."""
        for category in VALID_CATEGORIES:
            learning = ToolLearning(
                tool_name="Bash",
                category=category,
                severity="sev-1",
                summary="Test",
                context="Test context",
                observation="Test observation",
            )
            assert learning.category == category

    def test_all_valid_severities(self):
        """Test all valid severity values are accepted."""
        for severity in VALID_SEVERITIES:
            learning = ToolLearning(
                tool_name="Bash",
                category="error",
                severity=severity,
                summary="Test",
                context="Test context",
                observation="Test observation",
            )
            assert learning.severity == severity


# =============================================================================
# Tests for ToolLearning.to_memory_args()
# =============================================================================


class TestToolLearningToMemoryArgs:
    """Tests for ToolLearning.to_memory_args() method."""

    def test_basic_memory_args(self):
        """Test to_memory_args returns expected structure."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Command failed",
            context="Running git push",
            observation="Permission denied error",
        )

        args = learning.to_memory_args()

        assert args["summary"] == "Command failed"
        assert args["spec"] is None
        assert "When using Bash tool" in args["applicability"]

    def test_memory_args_insight_content(self):
        """Test insight content includes tool, category, severity."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Command failed",
            context="Running git push",
            observation="Permission denied error",
        )

        args = learning.to_memory_args()
        insight = args["insight"]

        assert "**Tool**: Bash" in insight
        assert "**Category**: error" in insight
        assert "**Severity**: sev-1" in insight
        assert "## Context" in insight
        assert "Running git push" in insight
        assert "## Observation" in insight
        assert "Permission denied error" in insight

    def test_memory_args_with_exit_code(self):
        """Test insight includes exit code when present."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Command failed",
            context="Running git push",
            observation="Permission denied",
            exit_code=128,
        )

        args = learning.to_memory_args()
        insight = args["insight"]

        assert "**Exit Code**: 128" in insight

    def test_memory_args_without_exit_code(self):
        """Test insight excludes exit code when None."""
        learning = ToolLearning(
            tool_name="Read",
            category="error",
            severity="sev-1",
            summary="File not found",
            context="Reading config file",
            observation="File does not exist",
            exit_code=None,
        )

        args = learning.to_memory_args()
        insight = args["insight"]

        assert "Exit Code" not in insight

    def test_memory_args_with_output_excerpt(self):
        """Test insight includes output excerpt when present."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Test failed",
            context="Running tests",
            observation="Test assertion failed",
            output_excerpt="AssertionError: expected 5, got 3",
        )

        args = learning.to_memory_args()
        insight = args["insight"]

        assert "## Output Excerpt" in insight
        assert "```" in insight
        assert "AssertionError: expected 5, got 3" in insight

    def test_memory_args_without_output_excerpt(self):
        """Test insight excludes output excerpt when empty."""
        learning = ToolLearning(
            tool_name="Read",
            category="error",
            severity="sev-1",
            summary="Error",
            context="Context",
            observation="Observation",
            output_excerpt="",
        )

        args = learning.to_memory_args()
        insight = args["insight"]

        assert "Output Excerpt" not in insight

    def test_memory_args_tags_include_tool_category_severity(self):
        """Test tags include tool name, category, and severity."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Test",
            context="Context",
            observation="Observation",
        )

        args = learning.to_memory_args()
        tags = args["tags"]

        assert "bash" in tags
        assert "error" in tags
        assert "sev-1" in tags

    def test_memory_args_tags_include_custom_tags(self):
        """Test tags include custom tags plus auto-generated ones."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Test",
            context="Context",
            observation="Observation",
            tags=("git", "network"),
        )

        args = learning.to_memory_args()
        tags = args["tags"]

        # Custom tags
        assert "git" in tags
        assert "network" in tags
        # Auto-generated tags
        assert "bash" in tags
        assert "error" in tags
        assert "sev-1" in tags

    def test_memory_args_with_spec(self):
        """Test spec is passed through to memory args."""
        learning = ToolLearning(
            tool_name="Bash",
            category="error",
            severity="sev-1",
            summary="Test",
            context="Context",
            observation="Observation",
            spec="my-feature-project",
        )

        args = learning.to_memory_args()

        assert args["spec"] == "my-feature-project"

    def test_memory_args_applicability_format(self):
        """Test applicability message format."""
        learning = ToolLearning(
            tool_name="Write",
            category="error",
            severity="sev-1",
            summary="Test",
            context="Context",
            observation="Observation",
        )

        args = learning.to_memory_args()

        assert args["applicability"] == "When using Write tool"


# =============================================================================
# Tests for DetectionSignal Dataclass
# =============================================================================


class TestDetectionSignal:
    """Tests for DetectionSignal frozen dataclass."""

    def test_basic_creation(self):
        """Test creating a DetectionSignal with required fields."""
        signal = DetectionSignal(
            pattern_name="error_keyword",
            weight=0.5,
        )

        assert signal.pattern_name == "error_keyword"
        assert signal.weight == 0.5

    def test_default_values(self):
        """Test DetectionSignal default values."""
        signal = DetectionSignal(
            pattern_name="test",
            weight=0.3,
        )

        assert signal.matched_text == ""
        assert signal.category_hint == LearningCategory.ERROR.value
        assert signal.severity_hint == LearningSeverity.SEV_2.value

    def test_custom_values(self):
        """Test DetectionSignal with custom values."""
        signal = DetectionSignal(
            pattern_name="warning_keyword",
            weight=0.25,
            matched_text="WARNING: deprecated",
            category_hint=LearningCategory.WARNING.value,
            severity_hint=LearningSeverity.SEV_3.value,
        )

        assert signal.pattern_name == "warning_keyword"
        assert signal.weight == 0.25
        assert signal.matched_text == "WARNING: deprecated"
        assert signal.category_hint == "warning"
        assert signal.severity_hint == "sev-3"

    def test_frozen_immutability(self):
        """Test DetectionSignal is immutable (frozen dataclass)."""
        signal = DetectionSignal(
            pattern_name="test",
            weight=0.5,
        )

        with pytest.raises(AttributeError):
            signal.weight = 0.8  # type: ignore

    def test_weight_boundaries(self):
        """Test weight can be at boundary values."""
        signal_zero = DetectionSignal(pattern_name="test", weight=0.0)
        signal_one = DetectionSignal(pattern_name="test", weight=1.0)

        assert signal_zero.weight == 0.0
        assert signal_one.weight == 1.0

    def test_all_category_hints(self):
        """Test all valid category hints are accepted."""
        for category in LearningCategory:
            signal = DetectionSignal(
                pattern_name="test",
                weight=0.5,
                category_hint=category.value,
            )
            assert signal.category_hint == category.value

    def test_all_severity_hints(self):
        """Test all valid severity hints are accepted."""
        for severity in LearningSeverity:
            signal = DetectionSignal(
                pattern_name="test",
                weight=0.5,
                severity_hint=severity.value,
            )
            assert signal.severity_hint == severity.value
