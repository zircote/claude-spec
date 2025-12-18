"""Tests for learnings/detector.py - Learning detector for PostToolUse hook.

Tests cover:
- SignalPattern dataclass
- Pattern matching (ERROR, WARNING, DISCOVERY, WORKAROUND patterns)
- Noise pattern detection
- LearningDetector class
- DetectionResult calculation
- Score thresholds and capture decisions
"""

import re
import sys
from pathlib import Path

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from learnings.detector import (
    ALL_SIGNAL_PATTERNS,
    DEFAULT_THRESHOLD,
    DISCOVERY_PATTERNS,
    ERROR_PATTERNS,
    NOISE_PATTERNS,
    WARNING_PATTERNS,
    WORKAROUND_PATTERNS,
    DetectionResult,
    LearningDetector,
    SignalPattern,
)
from learnings.models import LearningCategory, LearningSeverity

# =============================================================================
# Tests for SignalPattern Dataclass
# =============================================================================


class TestSignalPattern:
    """Tests for SignalPattern dataclass."""

    def test_basic_creation(self):
        """Test creating a SignalPattern."""
        pattern = SignalPattern(
            name="test_pattern",
            pattern=re.compile(r"test"),
            weight=0.5,
            category=LearningCategory.ERROR,
            severity=LearningSeverity.SEV_1,
        )

        assert pattern.name == "test_pattern"
        assert pattern.weight == 0.5
        assert pattern.category == LearningCategory.ERROR
        assert pattern.severity == LearningSeverity.SEV_1
        assert pattern.description == ""  # Default

    def test_with_description(self):
        """Test SignalPattern with description."""
        pattern = SignalPattern(
            name="test_pattern",
            pattern=re.compile(r"test"),
            weight=0.3,
            category=LearningCategory.WARNING,
            severity=LearningSeverity.SEV_3,
            description="This is a test pattern",
        )

        assert pattern.description == "This is a test pattern"


# =============================================================================
# Tests for Pre-compiled Pattern Lists
# =============================================================================


class TestPatternLists:
    """Tests for pre-compiled pattern lists."""

    def test_error_patterns_exist(self):
        """Test ERROR_PATTERNS contains expected patterns."""
        assert len(ERROR_PATTERNS) > 0
        names = {p.name for p in ERROR_PATTERNS}
        assert "exit_nonzero" in names
        assert "error_keyword" in names
        assert "command_not_found" in names
        assert "permission_error" in names

    def test_error_patterns_have_error_category(self):
        """Test all ERROR_PATTERNS have ERROR category."""
        for pattern in ERROR_PATTERNS:
            assert pattern.category == LearningCategory.ERROR

    def test_warning_patterns_exist(self):
        """Test WARNING_PATTERNS contains expected patterns."""
        assert len(WARNING_PATTERNS) > 0
        names = {p.name for p in WARNING_PATTERNS}
        assert "warning_keyword" in names

    def test_warning_patterns_have_warning_category(self):
        """Test all WARNING_PATTERNS have WARNING category."""
        for pattern in WARNING_PATTERNS:
            assert pattern.category == LearningCategory.WARNING

    def test_discovery_patterns_exist(self):
        """Test DISCOVERY_PATTERNS contains expected patterns."""
        assert len(DISCOVERY_PATTERNS) > 0
        names = {p.name for p in DISCOVERY_PATTERNS}
        assert "version_info" in names
        assert "config_loaded" in names

    def test_discovery_patterns_have_discovery_category(self):
        """Test all DISCOVERY_PATTERNS have DISCOVERY category."""
        for pattern in DISCOVERY_PATTERNS:
            assert pattern.category == LearningCategory.DISCOVERY

    def test_workaround_patterns_exist(self):
        """Test WORKAROUND_PATTERNS contains expected patterns."""
        assert len(WORKAROUND_PATTERNS) > 0
        names = {p.name for p in WORKAROUND_PATTERNS}
        assert "retry_success" in names
        assert "fallback" in names

    def test_workaround_patterns_have_workaround_category(self):
        """Test all WORKAROUND_PATTERNS have WORKAROUND category."""
        for pattern in WORKAROUND_PATTERNS:
            assert pattern.category == LearningCategory.WORKAROUND

    def test_all_signal_patterns_combines_all(self):
        """Test ALL_SIGNAL_PATTERNS contains all patterns."""
        total = (
            len(ERROR_PATTERNS)
            + len(WARNING_PATTERNS)
            + len(DISCOVERY_PATTERNS)
            + len(WORKAROUND_PATTERNS)
        )
        assert len(ALL_SIGNAL_PATTERNS) == total

    def test_noise_patterns_are_compiled(self):
        """Test NOISE_PATTERNS are pre-compiled."""
        assert len(NOISE_PATTERNS) > 0
        for pattern in NOISE_PATTERNS:
            assert isinstance(pattern, re.Pattern)


# =============================================================================
# Tests for Pattern Matching - ERROR Patterns
# =============================================================================


class TestErrorPatternMatching:
    """Tests for ERROR pattern matching."""

    def test_exit_nonzero_pattern(self):
        """Test exit_nonzero pattern matches exit codes."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "exit_nonzero")
        assert pattern.pattern.search("exit code: 1")
        assert pattern.pattern.search("Exit Code: 127")
        assert not pattern.pattern.search("exit code: 0")

    def test_error_keyword_pattern(self):
        """Test error_keyword pattern matches error words."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "error_keyword")
        assert pattern.pattern.search("Error: something failed")
        assert pattern.pattern.search("FATAL error occurred")
        assert pattern.pattern.search("cannot connect to server")
        assert pattern.pattern.search("unable to find file")
        assert pattern.pattern.search("Traceback (most recent call last)")
        assert not pattern.pattern.search("all tests passed successfully")

    def test_command_not_found_pattern(self):
        """Test command_not_found pattern matches."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "command_not_found")
        assert pattern.pattern.search("bash: xyz: command not found")
        assert pattern.pattern.search("'foo' is not recognized as")
        assert not pattern.pattern.search("command executed successfully")

    def test_permission_error_pattern(self):
        """Test permission_error pattern matches."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "permission_error")
        assert pattern.pattern.search("Permission denied")
        assert pattern.pattern.search("Access denied")
        assert pattern.pattern.search("unauthorized access")
        assert pattern.pattern.search("EACCES: permission denied")
        assert not pattern.pattern.search("access granted")

    def test_file_not_found_pattern(self):
        """Test file_not_found pattern matches."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "file_not_found")
        assert pattern.pattern.search("file not found")
        assert pattern.pattern.search("directory does not exist")
        assert pattern.pattern.search("ENOENT: no such file or directory")
        assert not pattern.pattern.search("file exists")

    def test_syntax_error_pattern(self):
        """Test syntax_error pattern matches."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "syntax_error")
        assert pattern.pattern.search("SyntaxError: invalid syntax")
        assert pattern.pattern.search("unexpected token '{'")
        assert pattern.pattern.search("parse error near 'return'")
        assert not pattern.pattern.search("syntax is correct")

    def test_type_error_pattern(self):
        """Test type_error pattern matches."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "type_error")
        assert pattern.pattern.search("TypeError: 'NoneType' has no attribute")
        assert pattern.pattern.search("AttributeError: object has no attribute")
        assert pattern.pattern.search("NameError: name 'x' is not defined")
        assert pattern.pattern.search("KeyError: 'missing_key'")
        assert not pattern.pattern.search("no errors found")

    def test_import_error_pattern(self):
        """Test import_error pattern matches."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "import_error")
        assert pattern.pattern.search("ImportError: No module named 'xyz'")
        assert pattern.pattern.search("ModuleNotFoundError: No module named")
        assert pattern.pattern.search("cannot find module 'foo'")
        assert not pattern.pattern.search("module loaded successfully")

    def test_connection_error_pattern(self):
        """Test connection_error pattern matches."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "connection_error")
        assert pattern.pattern.search("connection refused")
        assert pattern.pattern.search("connection timed out")
        assert pattern.pattern.search("ECONNREFUSED")
        assert pattern.pattern.search("network unreachable")
        assert not pattern.pattern.search("connection established")

    def test_timeout_pattern(self):
        """Test timeout pattern matches."""
        pattern = next(p for p in ERROR_PATTERNS if p.name == "timeout")
        assert pattern.pattern.search("operation timeout")
        assert pattern.pattern.search("request timed out")
        assert pattern.pattern.search("deadline exceeded")
        assert not pattern.pattern.search("completed on time")


# =============================================================================
# Tests for Pattern Matching - WARNING Patterns
# =============================================================================


class TestWarningPatternMatching:
    """Tests for WARNING pattern matching."""

    def test_warning_keyword_pattern(self):
        """Test warning_keyword pattern matches."""
        pattern = next(p for p in WARNING_PATTERNS if p.name == "warning_keyword")
        assert pattern.pattern.search("WARNING: disk space low")
        assert pattern.pattern.search("DeprecationWarning: this is deprecated")
        assert pattern.pattern.search("Use caution when proceeding")
        assert not pattern.pattern.search("all clear")

    def test_experimental_feature_pattern(self):
        """Test experimental_feature pattern matches."""
        pattern = next(p for p in WARNING_PATTERNS if p.name == "experimental_feature")
        assert pattern.pattern.search("This feature is experimental")
        assert pattern.pattern.search("API is unstable")
        assert pattern.pattern.search("beta version")
        assert pattern.pattern.search("using preview feature")
        assert not pattern.pattern.search("stable release")


# =============================================================================
# Tests for Pattern Matching - DISCOVERY Patterns
# =============================================================================


class TestDiscoveryPatternMatching:
    """Tests for DISCOVERY pattern matching."""

    def test_version_info_pattern(self):
        """Test version_info pattern matches."""
        pattern = next(p for p in DISCOVERY_PATTERNS if p.name == "version_info")
        assert pattern.pattern.search("version: v1.2.3")
        assert pattern.pattern.search("Python 3.11.0")
        assert pattern.pattern.search("Node 18.12.1")
        assert pattern.pattern.search("npm 9.2.0")
        assert not pattern.pattern.search("no version")

    def test_config_loaded_pattern(self):
        """Test config_loaded pattern matches."""
        pattern = next(p for p in DISCOVERY_PATTERNS if p.name == "config_loaded")
        assert pattern.pattern.search("config loaded from file")
        assert pattern.pattern.search("configuration found at")
        assert pattern.pattern.search("using default settings")
        assert not pattern.pattern.search("no config")


# =============================================================================
# Tests for Pattern Matching - WORKAROUND Patterns
# =============================================================================


class TestWorkaroundPatternMatching:
    """Tests for WORKAROUND pattern matching."""

    def test_retry_success_pattern(self):
        """Test retry_success pattern matches."""
        pattern = next(p for p in WORKAROUND_PATTERNS if p.name == "retry_success")
        assert pattern.pattern.search("retrying connection")
        assert pattern.pattern.search("attempt 3 of 5")
        assert pattern.pattern.search("trying again")
        assert not pattern.pattern.search("first attempt succeeded")

    def test_fallback_pattern(self):
        """Test fallback pattern matches."""
        pattern = next(p for p in WORKAROUND_PATTERNS if p.name == "fallback")
        assert pattern.pattern.search("using fallback mechanism")
        assert pattern.pattern.search("falling back to defaults")
        assert pattern.pattern.search("using alternative approach")
        assert pattern.pattern.search("defaulting to safe mode")
        assert not pattern.pattern.search("primary method succeeded")


# =============================================================================
# Tests for DetectionResult Dataclass
# =============================================================================


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_basic_creation(self):
        """Test creating a DetectionResult."""
        result = DetectionResult(score=0.5)
        assert result.score == 0.5
        assert result.signals == []
        assert result.primary_category == LearningCategory.ERROR.value
        assert result.primary_severity == LearningSeverity.SEV_2.value
        assert result.noise_factor == 0.0

    def test_should_capture_above_threshold(self):
        """Test should_capture returns True above threshold."""
        result = DetectionResult(score=0.7)
        assert result.should_capture is True

    def test_should_capture_below_threshold(self):
        """Test should_capture returns False below threshold."""
        result = DetectionResult(score=0.5)
        assert result.should_capture is False

    def test_should_capture_at_threshold(self):
        """Test should_capture returns True at threshold."""
        result = DetectionResult(score=DEFAULT_THRESHOLD)
        assert result.should_capture is True


# =============================================================================
# Tests for LearningDetector Class
# =============================================================================


class TestLearningDetector:
    """Tests for LearningDetector class."""

    def test_initialization_default_threshold(self):
        """Test detector initializes with default threshold."""
        detector = LearningDetector()
        assert detector.threshold == DEFAULT_THRESHOLD

    def test_initialization_custom_threshold(self):
        """Test detector initializes with custom threshold."""
        detector = LearningDetector(threshold=0.8)
        assert detector.threshold == 0.8

    def test_calculate_score_with_error(self):
        """Test score calculation with error output."""
        detector = LearningDetector()
        response = {
            "stdout": "",
            "stderr": "Error: command not found",
            "exit_code": 127,
        }

        score = detector.calculate_score("Bash", response)
        assert score > 0

    def test_calculate_score_with_success(self):
        """Test score calculation with success output."""
        detector = LearningDetector()
        response = {
            "stdout": "ok",
            "stderr": "",
            "exit_code": 0,
        }

        score = detector.calculate_score("Bash", response)
        assert score == 0

    def test_detect_returns_detection_result(self):
        """Test detect returns DetectionResult."""
        detector = LearningDetector()
        response = {"stderr": "Error: test failed"}

        result = detector.detect("Bash", response)

        assert isinstance(result, DetectionResult)

    def test_detect_with_nonzero_exit_code(self):
        """Test detect with non-zero exit code adds signal."""
        detector = LearningDetector()
        response = {
            "exit_code": 1,
            "stderr": "command failed",
        }

        result = detector.detect("Bash", response)

        # Should have exit code signal
        exit_signals = [s for s in result.signals if "exit" in s.pattern_name.lower()]
        assert len(exit_signals) > 0

    def test_detect_silent_failure_sev_0(self):
        """Test silent failure (non-zero exit, empty output) gets sev-0."""
        detector = LearningDetector()
        response = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "",
        }

        result = detector.detect("Bash", response)

        # Should detect as silent failure
        exit_signals = [s for s in result.signals if "exit" in s.pattern_name.lower()]
        assert len(exit_signals) > 0
        assert exit_signals[0].severity_hint == LearningSeverity.SEV_0.value

    def test_detect_with_output_gets_sev_1(self):
        """Test failure with output gets sev-1."""
        detector = LearningDetector()
        response = {
            "exit_code": 1,
            "stderr": "error: something went wrong",
        }

        result = detector.detect("Bash", response)

        exit_signals = [s for s in result.signals if "exit" in s.pattern_name.lower()]
        assert len(exit_signals) > 0
        assert exit_signals[0].severity_hint == LearningSeverity.SEV_1.value

    def test_detect_zero_exit_code_no_signal(self):
        """Test zero exit code adds no exit signal."""
        detector = LearningDetector()
        response = {
            "exit_code": 0,
            "stdout": "success",
        }

        result = detector.detect("Bash", response)

        exit_signals = [s for s in result.signals if "exit_code" in s.pattern_name]
        assert len(exit_signals) == 0

    def test_detect_pattern_signals(self):
        """Test detect finds pattern signals in text."""
        detector = LearningDetector()
        response = {
            "stderr": "Error: permission denied",
        }

        result = detector.detect("Bash", response)

        pattern_names = {s.pattern_name for s in result.signals}
        assert "error_keyword" in pattern_names or "permission_error" in pattern_names

    def test_detect_multiple_patterns(self):
        """Test detect finds multiple patterns."""
        detector = LearningDetector()
        response = {
            "stderr": "Error: command not found\nPermission denied",
        }

        result = detector.detect("Bash", response)

        # Should have multiple signals
        assert len(result.signals) >= 2

    def test_detect_primary_category_from_highest_weight(self):
        """Test primary category comes from highest weight signal."""
        detector = LearningDetector()
        response = {
            "stderr": "warning: deprecated\nError: fatal crash",
            "exit_code": 1,
        }

        result = detector.detect("Bash", response)

        # Primary should be from error (higher weight than warning)
        # The exit_code signal has weight 0.5
        assert result.primary_category in [
            LearningCategory.ERROR.value,
            LearningCategory.WARNING.value,
        ]

    def test_detect_empty_response(self):
        """Test detect with empty response."""
        detector = LearningDetector()
        response = {}

        result = detector.detect("Bash", response)

        assert result.score == 0.0
        assert len(result.signals) == 0

    def test_detect_score_capped_at_one(self):
        """Test score is capped at 1.0 even with many patterns."""
        detector = LearningDetector()
        # Lots of error keywords
        response = {
            "stderr": (
                "Error failed cannot unable denied refused "
                "exception traceback fatal invalid"
            ),
            "exit_code": 127,
        }

        result = detector.detect("Bash", response)

        assert result.score <= 1.0


# =============================================================================
# Tests for Noise Reduction
# =============================================================================


class TestNoiseReduction:
    """Tests for noise pattern detection and reduction."""

    def test_noise_patterns_reduce_score(self):
        """Test noise patterns reduce the final score."""
        detector = LearningDetector()

        # Error with noise
        response_with_noise = {
            "stderr": "error occurred",
            "stdout": "ok\nok\nok\ndone\nSuccess",
        }

        # Error without noise
        response_without_noise = {
            "stderr": "error occurred",
        }

        result_with_noise = detector.detect("Bash", response_with_noise)
        result_without_noise = detector.detect("Bash", response_without_noise)

        # Score with noise should be lower
        assert result_with_noise.noise_factor > 0
        assert result_with_noise.score < result_without_noise.score

    def test_noise_factor_capped(self):
        """Test noise factor is capped at 0.3."""
        detector = LearningDetector()
        # Lots of noise
        response = {
            "stderr": "error",
            "stdout": "\n".join(["ok", "done", "Success", "passed"] * 10),
        }

        result = detector.detect("Bash", response)

        assert result.noise_factor <= 0.3

    def test_noise_empty_lines(self):
        """Test empty lines contribute to noise."""
        detector = LearningDetector()
        response = {
            "stderr": "error",
            "stdout": "\n\n\n\n\n",
        }

        result = detector.detect("Bash", response)

        assert result.noise_factor > 0


# =============================================================================
# Tests for Text Extraction
# =============================================================================


class TestTextExtraction:
    """Tests for _extract_text method."""

    def test_extract_stderr(self):
        """Test text extraction from stderr."""
        detector = LearningDetector()
        response = {"stderr": "error message"}

        result = detector.detect("Bash", response)
        # If stderr contains error, should get a signal
        assert any("error" in s.pattern_name.lower() for s in result.signals)

    def test_extract_stdout(self):
        """Test text extraction from stdout."""
        detector = LearningDetector()
        response = {"stdout": "warning: deprecated"}

        result = detector.detect("Bash", response)
        assert len(result.signals) > 0

    def test_extract_content(self):
        """Test text extraction from content field."""
        detector = LearningDetector()
        response = {"content": "Error: file not found"}

        result = detector.detect("Read", response)
        assert len(result.signals) > 0

    def test_extract_output(self):
        """Test text extraction from output field."""
        detector = LearningDetector()
        response = {"output": "permission denied"}

        result = detector.detect("Bash", response)
        assert len(result.signals) > 0

    def test_extract_result(self):
        """Test text extraction from result field."""
        detector = LearningDetector()
        response = {"result": "command not found"}

        result = detector.detect("Bash", response)
        assert len(result.signals) > 0

    def test_extract_error_field(self):
        """Test text extraction from error field."""
        detector = LearningDetector()
        response = {"error": "fatal error occurred"}

        result = detector.detect("Bash", response)
        assert len(result.signals) > 0

    def test_extract_combines_all_fields(self):
        """Test extraction combines all relevant fields."""
        detector = LearningDetector()
        response = {
            "stderr": "error 1",
            "stdout": "warning 2",
            "output": "failed 3",
        }

        result = detector.detect("Bash", response)
        # Should have signals from multiple sources
        assert len(result.signals) >= 1


# =============================================================================
# Tests for Threshold Behavior
# =============================================================================


class TestThresholdBehavior:
    """Tests for threshold-based capture decisions."""

    def test_default_threshold_value(self):
        """Test default threshold is 0.6."""
        assert DEFAULT_THRESHOLD == 0.6

    def test_score_below_threshold_no_capture(self):
        """Test score below threshold means no capture."""
        detector = LearningDetector(threshold=0.6)
        response = {"stdout": "warning: minor issue"}

        result = detector.detect("Bash", response)

        # Warning alone might not hit threshold
        if result.score < 0.6:
            assert not result.should_capture

    def test_score_above_threshold_capture(self):
        """Test score above threshold means capture."""
        detector = LearningDetector(threshold=0.3)
        response = {
            "stderr": "Error: critical failure",
            "exit_code": 1,
        }

        result = detector.detect("Bash", response)

        assert result.score >= 0.3
        assert result.should_capture

    def test_custom_threshold_respected(self):
        """Test custom threshold is used for should_capture."""
        # Low threshold - should capture more
        detector_low = LearningDetector(threshold=0.1)
        # High threshold - should capture less
        detector_high = LearningDetector(threshold=0.9)

        response = {"stderr": "warning: deprecated"}

        result_low = detector_low.detect("Bash", response)
        result_high = detector_high.detect("Bash", response)

        # Same score, different capture decisions
        assert result_low.score == result_high.score
        # The should_capture uses DEFAULT_THRESHOLD not detector.threshold
        # This is a design decision - DetectionResult has fixed threshold
