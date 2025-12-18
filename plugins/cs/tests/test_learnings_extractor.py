"""Tests for learnings/extractor.py - Learning extractor for PostToolUse hook.

Tests cover:
- sanitize_paths() function
- truncate_output() function
- generate_summary() function
- extract_learning() function
- Secret filtering integration
- Deduplication integration
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from learnings.deduplicator import DeduplicationResult, SessionDeduplicator
from learnings.detector import DetectionResult, LearningDetector
from learnings.extractor import (
    MAX_OUTPUT_EXCERPT,
    extract_learning,
    generate_summary,
    sanitize_paths,
    truncate_output,
)
from learnings.models import DetectionSignal, ToolLearning

# =============================================================================
# Tests for sanitize_paths()
# =============================================================================


class TestSanitizePaths:
    """Tests for sanitize_paths function."""

    def test_redacts_home_directory(self):
        """Test home directory paths are redacted."""
        content = "File at /Users/johndoe/project/config.json"
        result = sanitize_paths(content)
        assert "/Users/johndoe" not in result
        assert "/Users/[USER]" in result

    def test_redacts_multiple_home_paths(self):
        """Test multiple home directory paths are redacted."""
        content = "Found /Users/alice/file.txt and /Users/bob/file.txt"
        result = sanitize_paths(content)
        assert "/Users/alice" not in result
        assert "/Users/bob" not in result
        assert result.count("/Users/[USER]") == 2

    def test_redacts_env_files(self):
        """Test .env file references are marked."""
        content = "Loading configuration from .env"
        result = sanitize_paths(content)
        assert "[.env-REDACTED]" in result

    def test_redacts_credentials_path(self):
        """Test credentials paths are marked."""
        content = "Found credentials at ~/.credentials/api_key"
        result = sanitize_paths(content)
        assert "[credentials-REDACTED]" in result

    def test_redacts_secrets_path(self):
        """Test secrets paths are marked."""
        content = "Loading from /var/secrets/password"
        result = sanitize_paths(content)
        assert "[secrets-REDACTED]" in result

    def test_redacts_aws_config(self):
        """Test .aws directory paths are marked."""
        content = "Reading from ~/.aws/credentials"
        result = sanitize_paths(content)
        assert "[.aws-REDACTED]" in result

    def test_redacts_ssh_config(self):
        """Test .ssh directory paths are marked."""
        content = "Using key from ~/.ssh/id_rsa"
        result = sanitize_paths(content)
        assert "[.ssh-REDACTED]" in result

    def test_preserves_other_paths(self):
        """Test non-sensitive paths are preserved."""
        content = "File at /var/log/app.log"
        result = sanitize_paths(content)
        assert "/var/log/app.log" in result

    def test_handles_empty_string(self):
        """Test empty string is handled."""
        result = sanitize_paths("")
        assert result == ""

    def test_handles_no_paths(self):
        """Test content without paths is unchanged."""
        content = "This has no paths at all"
        result = sanitize_paths(content)
        assert result == content

    def test_case_insensitive_credentials(self):
        """Test credentials pattern is case insensitive."""
        content = "Using CREDENTIALS from file"
        result = sanitize_paths(content)
        assert "[CREDENTIALS-REDACTED]" in result

    def test_combined_home_and_credentials(self):
        """Test combined home path and credentials redaction."""
        content = "Found /Users/admin/.aws/credentials"
        result = sanitize_paths(content)
        assert "/Users/admin" not in result
        assert "/Users/[USER]" in result
        assert "[.aws-REDACTED]" in result


# =============================================================================
# Tests for truncate_output()
# =============================================================================


class TestTruncateOutput:
    """Tests for truncate_output function."""

    def test_short_output_unchanged(self):
        """Test output shorter than max is unchanged."""
        output = "Short output"
        result = truncate_output(output, max_length=100)
        assert result == output

    def test_output_at_max_unchanged(self):
        """Test output exactly at max length is unchanged."""
        output = "x" * 100
        result = truncate_output(output, max_length=100)
        assert result == output

    def test_long_output_truncated(self):
        """Test output longer than max is truncated."""
        output = "x" * 2000
        result = truncate_output(output, max_length=1024)
        assert len(result) <= 1024
        assert "TRUNCATED" in result

    def test_truncation_notice_shows_chars_removed(self):
        """Test truncation notice shows character count."""
        output = "x" * 2000
        result = truncate_output(output, max_length=1000)
        assert "TRUNCATED" in result
        assert "chars" in result

    def test_prioritizes_error_lines(self):
        """Test error lines are prioritized in truncation."""
        lines = ["normal line " + str(i) for i in range(100)]
        lines[50] = "Error: critical failure occurred"
        output = "\n".join(lines)

        result = truncate_output(output, max_length=500)

        # Error line should be preserved
        assert "Error: critical failure" in result

    def test_prioritizes_warning_lines(self):
        """Test warning lines are prioritized."""
        lines = ["normal line " + str(i) for i in range(100)]
        lines[50] = "WARNING: deprecated feature"
        output = "\n".join(lines)

        result = truncate_output(output, max_length=500)

        assert "WARNING: deprecated" in result

    def test_prioritizes_exception_lines(self):
        """Test exception lines are prioritized."""
        lines = ["normal line " + str(i) for i in range(100)]
        lines[50] = "Traceback (most recent call last):"
        output = "\n".join(lines)

        result = truncate_output(output, max_length=500)

        assert "Traceback" in result

    def test_default_max_length(self):
        """Test default max length is MAX_OUTPUT_EXCERPT."""
        output = "x" * (MAX_OUTPUT_EXCERPT + 100)
        result = truncate_output(output)
        assert len(result) <= MAX_OUTPUT_EXCERPT

    def test_handles_empty_output(self):
        """Test empty output is handled."""
        result = truncate_output("")
        assert result == ""

    def test_prioritizes_failed_lines(self):
        """Test FAILED lines are prioritized."""
        lines = ["normal line " + str(i) for i in range(100)]
        lines[50] = "FAILED test_something - assertion error"
        output = "\n".join(lines)

        result = truncate_output(output, max_length=500)

        assert "FAILED" in result


# =============================================================================
# Tests for generate_summary()
# =============================================================================


class TestGenerateSummary:
    """Tests for generate_summary function."""

    def test_error_category_summary(self):
        """Test summary for error category."""
        detection = DetectionResult(
            score=0.7,
            signals=[
                DetectionSignal(
                    pattern_name="error_keyword",
                    weight=0.5,
                    matched_text="command not found",
                )
            ],
        )

        summary = generate_summary("Bash", "error", detection)

        assert "Bash" in summary
        assert "error" in summary.lower()

    def test_warning_category_summary(self):
        """Test summary for warning category."""
        detection = DetectionResult(
            score=0.5,
            signals=[
                DetectionSignal(
                    pattern_name="warning_keyword",
                    weight=0.3,
                    matched_text="deprecated",
                )
            ],
        )

        summary = generate_summary("Bash", "warning", detection)

        assert "Bash" in summary
        assert "warning" in summary.lower()

    def test_workaround_category_summary(self):
        """Test summary for workaround category."""
        detection = DetectionResult(
            score=0.5,
            signals=[
                DetectionSignal(
                    pattern_name="retry_success",
                    weight=0.3,
                    matched_text="retrying",
                )
            ],
        )

        summary = generate_summary("Bash", "workaround", detection)

        assert "Bash" in summary
        assert "workaround" in summary.lower() or "recovery" in summary.lower()

    def test_discovery_category_summary(self):
        """Test summary for discovery category."""
        detection = DetectionResult(
            score=0.3,
            signals=[
                DetectionSignal(
                    pattern_name="version_info",
                    weight=0.2,
                    matched_text="Python 3.11",
                )
            ],
        )

        summary = generate_summary("Bash", "discovery", detection)

        assert "Bash" in summary
        assert "discovery" in summary.lower() or "observation" in summary.lower()

    def test_summary_includes_signal_text(self):
        """Test summary includes matched signal text."""
        detection = DetectionResult(
            score=0.7,
            signals=[
                DetectionSignal(
                    pattern_name="error_keyword",
                    weight=0.5,
                    matched_text="permission denied",
                )
            ],
        )

        summary = generate_summary("Bash", "error", detection)

        assert "permission denied" in summary

    def test_summary_truncated_to_100_chars(self):
        """Test summary is truncated to max 100 chars."""
        detection = DetectionResult(
            score=0.7,
            signals=[
                DetectionSignal(
                    pattern_name="error_keyword",
                    weight=0.5,
                    matched_text="x" * 100,  # Very long match
                )
            ],
        )

        summary = generate_summary("Bash", "error", detection)

        assert len(summary) <= 100

    def test_summary_with_no_signals(self):
        """Test summary generation with no signals."""
        detection = DetectionResult(score=0.0, signals=[])

        summary = generate_summary("Bash", "error", detection)

        assert "Bash" in summary

    def test_summary_unknown_category(self):
        """Test summary with unknown category falls back gracefully."""
        detection = DetectionResult(
            score=0.5,
            signals=[
                DetectionSignal(
                    pattern_name="test",
                    weight=0.5,
                    matched_text="test match",
                )
            ],
        )

        summary = generate_summary("Bash", "unknown", detection)

        assert "Bash" in summary

    def test_summary_with_empty_matched_text(self):
        """Test summary when matched_text is empty."""
        detection = DetectionResult(
            score=0.5,
            signals=[
                DetectionSignal(
                    pattern_name="test",
                    weight=0.5,
                    matched_text="",
                )
            ],
        )

        summary = generate_summary("Bash", "error", detection)

        assert "Bash" in summary
        assert "failed" in summary.lower() or "error" in summary.lower()


# =============================================================================
# Tests for extract_learning()
# =============================================================================


class TestExtractLearning:
    """Tests for extract_learning function."""

    def test_returns_none_below_threshold(self):
        """Test returns None when score is below threshold."""
        # Mock detector that returns low score
        mock_detector = MagicMock(spec=LearningDetector)
        mock_detector.detect.return_value = DetectionResult(score=0.3)

        response = {"stdout": "success"}

        result = extract_learning("Bash", response, detector=mock_detector)

        assert result is None

    def test_returns_none_for_duplicate(self):
        """Test returns None when content is a duplicate."""
        # Mock detector that returns high score
        mock_detector = MagicMock(spec=LearningDetector)
        mock_detector.detect.return_value = DetectionResult(
            score=0.8,
            signals=[
                DetectionSignal(pattern_name="error", weight=0.5, matched_text="error")
            ],
        )

        # Mock deduplicator that says it's a duplicate
        mock_dedup = MagicMock(spec=SessionDeduplicator)
        mock_dedup.check_learning.return_value = DeduplicationResult(
            is_duplicate=True, content_hash="abc123"
        )

        response = {"stderr": "error occurred"}

        result = extract_learning(
            "Bash", response, detector=mock_detector, deduplicator=mock_dedup
        )

        assert result is None

    def test_returns_tool_learning_for_valid_input(self):
        """Test returns ToolLearning for valid learnable input."""
        # Create a real detector to avoid mocking complexity
        detector = LearningDetector()

        # Create fresh deduplicator
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: command not found",
            "exit_code": 127,
        }

        result = extract_learning(
            "Bash",
            response,
            context="Running git push",
            detector=detector,
            deduplicator=dedup,
        )

        assert result is not None
        assert isinstance(result, ToolLearning)
        assert result.tool_name == "Bash"

    def test_tool_learning_has_correct_category(self):
        """Test extracted learning has correct category."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: permission denied",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert result.category == "error"

    def test_tool_learning_has_exit_code(self):
        """Test extracted learning includes exit code."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: failed",
            "exit_code": 127,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert result.exit_code == 127

    def test_tool_learning_with_spec(self):
        """Test extracted learning includes spec."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: test failed",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash",
            response,
            spec="my-feature",
            detector=detector,
            deduplicator=dedup,
        )

        assert result is not None
        assert result.spec == "my-feature"

    def test_tool_learning_with_context(self):
        """Test extracted learning includes context."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: connection refused",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash",
            response,
            context="Connecting to database",
            detector=detector,
            deduplicator=dedup,
        )

        assert result is not None
        assert result.context == "Connecting to database"

    def test_default_context_when_none_provided(self):
        """Test default context when none provided."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: failed",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert "Bash" in result.context

    def test_extracts_output_from_multiple_fields(self):
        """Test output extraction from multiple response fields."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: part 1",
            "stdout": "More info",
            "output": "Additional output",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        # Output excerpt should contain parts of the response
        # (May be filtered/truncated)

    def test_filters_secrets_from_output(self):
        """Test secrets are filtered from output."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: invalid token ghp_1234567890abcdef1234567890abcdef12345678",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        # The GitHub PAT should be filtered
        assert "ghp_1234567890" not in result.output_excerpt

    def test_sanitizes_paths_in_output(self):
        """Test paths are sanitized in output."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: file not found at /Users/johndoe/project/config.json",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert "/Users/johndoe" not in result.output_excerpt
        assert "/Users/[USER]" in result.output_excerpt

    def test_truncates_long_output(self):
        """Test long output is truncated."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        long_output = "Error: " + "x" * 3000

        response = {
            "stderr": long_output,
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert len(result.output_excerpt) <= MAX_OUTPUT_EXCERPT

    def test_tags_include_tool_and_category(self):
        """Test tags include tool name and category."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: connection failed",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert "bash" in result.tags
        assert result.category in result.tags

    def test_tags_include_secrets_filtered_when_secrets_found(self):
        """Test 'secrets-filtered' tag added when secrets filtered."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: invalid key AKIAIOSFODNN7EXAMPLE",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert "secrets-filtered" in result.tags

    def test_uses_default_detector_when_none_provided(self):
        """Test uses default detector when none provided."""
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: test failed",
            "exit_code": 1,
        }

        # Should not raise - uses default detector
        _ = extract_learning("Bash", response, deduplicator=dedup)

        # May or may not return a result depending on threshold
        # Main thing is no exception

    def test_observation_includes_signal_descriptions(self):
        """Test observation includes detected signal descriptions."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: permission denied",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert "Detected signals" in result.observation

    def test_summary_max_100_chars(self):
        """Test generated summary is max 100 chars."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: " + "x" * 200,
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert len(result.summary) <= 100


# =============================================================================
# Tests for Integration with filter_pipeline
# =============================================================================


class TestFilterPipelineIntegration:
    """Tests for integration with filters/pipeline.py."""

    def test_filters_aws_keys(self):
        """Test AWS keys are filtered."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: bad credentials AKIAIOSFODNN7EXAMPLE",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert "AKIAIOSFODNN7EXAMPLE" not in result.output_excerpt

    def test_filters_github_tokens(self):
        """Test GitHub tokens are filtered."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: invalid token ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert "ghp_" not in result.output_excerpt

    def test_filters_connection_strings(self):
        """Test database connection strings are filtered."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: postgres://user:pass@host/db",
            "exit_code": 1,
        }

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        assert result is not None
        assert "postgres://user:pass" not in result.output_excerpt


# =============================================================================
# Tests for Edge Cases
# =============================================================================


class TestExtractLearningEdgeCases:
    """Tests for edge cases in extract_learning."""

    def test_empty_response(self):
        """Test handling of empty response."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {}

        result = extract_learning(
            "Bash", response, detector=detector, deduplicator=dedup
        )

        # Empty response should not trigger learning
        assert result is None

    def test_none_values_in_response(self):
        """Test handling of None values in response."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": None,
            "stdout": None,
            "exit_code": 0,
        }

        _ = extract_learning("Bash", response, detector=detector, deduplicator=dedup)

        # Should not crash, likely returns None
        # (no error content to detect)

    def test_different_tool_names(self):
        """Test different tool names are handled."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        tools = ["Bash", "Read", "Write", "Task", "WebFetch"]

        for tool in tools:
            response = {
                "stderr": "Error: something failed",
                "exit_code": 1,
            }

            result = extract_learning(
                tool, response, detector=detector, deduplicator=dedup
            )

            if result is not None:
                assert result.tool_name == tool

            # Reset deduplicator for next iteration
            dedup.clear()

    def test_response_with_only_stdout(self):
        """Test response with only stdout."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stdout": "Warning: deprecated function used",
        }

        _ = extract_learning("Bash", response, detector=detector, deduplicator=dedup)

        # May or may not return learning depending on score

    def test_response_with_content_field(self):
        """Test response with content field (Read tool)."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "content": "Error: file not found",
            "error": "File does not exist",
        }

        _ = extract_learning("Read", response, detector=detector, deduplicator=dedup)

        # Should detect error

    def test_unicode_in_output(self):
        """Test Unicode characters in output."""
        detector = LearningDetector()
        dedup = SessionDeduplicator()

        response = {
            "stderr": "Error: file not found /path/to/file.txt",
            "exit_code": 1,
        }

        _ = extract_learning("Bash", response, detector=detector, deduplicator=dedup)

        # Should handle without crashing
