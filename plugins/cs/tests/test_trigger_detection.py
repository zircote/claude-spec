"""Tests for trigger phrase detection and memory injection.

Tests cover:
- trigger_detector.py - Trigger phrase pattern matching
- trigger_memory.py - UserPromptSubmit hook integration
"""

import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks" / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Tests for trigger_detector.py - TriggerDetector
# =============================================================================


class TestTriggerDetector:
    """Tests for TriggerDetector class."""

    def test_should_inject_with_why_did_we(self):
        """Test trigger detection with 'why did we' phrase."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("Why did we choose this approach?") is True

    def test_should_inject_with_what_was_the_decision(self):
        """Test trigger detection with 'what was the decision' phrase."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert (
            detector.should_inject("What was the decision about the database?") is True
        )

    def test_should_inject_with_remind_me(self):
        """Test trigger detection with 'remind me' phrase."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("Remind me what we discussed") is True

    def test_should_inject_with_continue_from(self):
        """Test trigger detection with 'continue from' phrase."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("Let's continue from where we left off") is True

    def test_should_inject_with_last_time(self):
        """Test trigger detection with 'last time' phrase."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("Last time we talked about X") is True

    def test_should_inject_with_previously(self):
        """Test trigger detection with 'previously' phrase."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("We previously decided to use hooks") is True

    def test_should_inject_with_the_blocker(self):
        """Test trigger detection with 'the blocker' phrase."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("What was the blocker again?") is True

    def test_should_inject_with_what_happened_with(self):
        """Test trigger detection with 'what happened with' phrase."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("What happened with the API refactor?") is True

    def test_should_inject_with_what_did_we_learn(self):
        """Test trigger detection with 'what did we learn' phrase."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("What did we learn from the last sprint?") is True

    def test_should_inject_case_insensitive(self):
        """Test trigger detection is case insensitive."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("WHY DID WE do that?") is True
        assert detector.should_inject("REMIND ME about the issue") is True

    def test_should_not_inject_normal_prompt(self):
        """Test no trigger detection for normal prompts."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("Write a function to calculate sum") is False
        assert detector.should_inject("Fix the bug in the login page") is False
        assert detector.should_inject("Add a new test for the API") is False

    def test_should_not_inject_empty_prompt(self):
        """Test no trigger detection for empty prompts."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("") is False
        assert detector.should_inject(None) is False  # type: ignore

    def test_get_matched_pattern(self):
        """Test getting the matched pattern."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.get_matched_pattern("Why did we choose Python?") == "Why did we"
        assert detector.get_matched_pattern("Remind me of the issue") == "Remind me"
        assert detector.get_matched_pattern("Write some code") is None

    def test_get_trigger_context(self):
        """Test getting trigger context from prompt."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        prompt = "Why did we choose hooks?"
        assert detector.get_trigger_context(prompt) == prompt
        assert detector.get_trigger_context("") is None

    def test_custom_patterns(self):
        """Test using custom trigger patterns."""
        import re

        from trigger_detector import TriggerDetector

        custom_patterns = [
            re.compile(r"custom trigger", re.IGNORECASE),
        ]
        detector = TriggerDetector(patterns=custom_patterns)

        assert detector.should_inject("This has custom trigger phrase") is True
        assert detector.should_inject("Why did we") is False  # Default not included


# =============================================================================
# Tests for trigger_detector.py - TriggerMemoryInjector
# =============================================================================


class TestTriggerMemoryInjector:
    """Tests for TriggerMemoryInjector class."""

    def test_initialization(self):
        """Test TriggerMemoryInjector initializes with defaults."""
        from trigger_detector import TriggerMemoryInjector

        injector = TriggerMemoryInjector()
        assert injector.limit == 5
        assert injector._recall_service is None
        assert injector.detector is not None

    def test_initialization_custom_limit(self):
        """Test TriggerMemoryInjector with custom limit."""
        from trigger_detector import TriggerMemoryInjector

        injector = TriggerMemoryInjector(limit=3)
        assert injector.limit == 3

    def test_process_prompt_no_trigger(self):
        """Test process_prompt returns empty when no trigger."""
        from trigger_detector import TriggerMemoryInjector

        injector = TriggerMemoryInjector()
        result = injector.process_prompt("Write a function")
        assert result == []

    def test_process_prompt_no_recall_service(self):
        """Test process_prompt when recall service unavailable."""
        from trigger_detector import TriggerMemoryInjector

        injector = TriggerMemoryInjector()
        injector._recall_service = None

        with patch.object(
            type(injector),
            "recall_service",
            new_callable=lambda: property(lambda self: None),
        ):
            result = injector.process_prompt("Why did we choose this?")
            assert result == []

    def test_format_for_additional_context_empty(self):
        """Test formatting with empty memory list."""
        from trigger_detector import TriggerMemoryInjector

        injector = TriggerMemoryInjector()
        result = injector.format_for_additional_context([])
        assert result == ""

    def test_format_for_additional_context_with_memories(self):
        """Test formatting memories for additional context."""
        from trigger_detector import TriggerMemoryInjector

        mock_memory = MagicMock()
        mock_memory.namespace = "decisions"
        mock_memory.summary = "Chose hooks for memory capture"
        mock_memory.timestamp = datetime(2025, 12, 17, 10, 0, 0, tzinfo=UTC)
        mock_memory.content = "We decided to use hooks because..."

        mock_result = MagicMock()
        mock_result.memory = mock_memory

        injector = TriggerMemoryInjector()
        result = injector.format_for_additional_context([mock_result])

        assert "## Relevant Memories" in result
        assert "🎯" in result  # decisions icon
        assert "Chose hooks for memory capture" in result
        assert "We decided to use hooks because..." in result

    def test_format_truncates_long_content(self):
        """Test that long content is truncated."""
        from trigger_detector import TriggerMemoryInjector

        mock_memory = MagicMock()
        mock_memory.namespace = "learnings"
        mock_memory.summary = "Test"
        mock_memory.timestamp = datetime.now(UTC)
        mock_memory.content = "x" * 2000  # Long content

        mock_result = MagicMock()
        mock_result.memory = mock_memory

        injector = TriggerMemoryInjector()
        result = injector.format_for_additional_context([mock_result])

        # Content should be truncated to 1000 chars + "..."
        assert "..." in result
        # Should not have full 2000 chars
        assert len(result) < 2000

    def test_get_namespace_icon(self):
        """Test namespace icons are returned correctly."""
        from trigger_detector import TriggerMemoryInjector

        injector = TriggerMemoryInjector()

        assert injector._get_namespace_icon("decisions") == "🎯"
        assert injector._get_namespace_icon("learnings") == "💡"
        assert injector._get_namespace_icon("blockers") == "🚧"
        assert injector._get_namespace_icon("unknown") == "📌"


# =============================================================================
# Tests for trigger_detector.py - Factory Functions
# =============================================================================


class TestTriggerDetectorFactories:
    """Tests for factory functions."""

    def test_get_trigger_detector(self):
        """Test get_trigger_detector factory."""
        from trigger_detector import TriggerDetector, get_trigger_detector

        detector = get_trigger_detector()
        assert isinstance(detector, TriggerDetector)

    def test_get_trigger_memory_injector(self):
        """Test get_trigger_memory_injector factory."""
        from trigger_detector import TriggerMemoryInjector, get_trigger_memory_injector

        injector = get_trigger_memory_injector(limit=7)
        assert isinstance(injector, TriggerMemoryInjector)
        assert injector.limit == 7


# =============================================================================
# Tests for trigger_memory.py - Hook Integration
# =============================================================================


class TestTriggerMemoryHook:
    """Tests for trigger_memory.py hook."""

    def test_is_trigger_memory_enabled_default(self):
        """Test trigger memory is enabled by default."""
        # Clear any environment override
        import os

        import trigger_memory

        orig = os.environ.pop("CS_TRIGGER_MEMORY_ENABLED", None)

        assert trigger_memory.is_trigger_memory_enabled() is True

        if orig:
            os.environ["CS_TRIGGER_MEMORY_ENABLED"] = orig

    def test_is_trigger_memory_disabled_env(self, monkeypatch):
        """Test trigger memory can be disabled via environment."""
        import trigger_memory

        monkeypatch.setenv("CS_TRIGGER_MEMORY_ENABLED", "false")
        assert trigger_memory.is_trigger_memory_enabled() is False

        monkeypatch.setenv("CS_TRIGGER_MEMORY_ENABLED", "0")
        assert trigger_memory.is_trigger_memory_enabled() is False

    def test_read_input_valid_json(self, monkeypatch):
        """Test reading valid JSON input."""
        import trigger_memory

        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "test"}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        result = trigger_memory.read_input()
        assert result == input_data

    def test_read_input_invalid_json(self, monkeypatch, capsys):
        """Test handling of invalid JSON."""
        import trigger_memory

        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        result = trigger_memory.read_input()

        assert result is None
        captured = capsys.readouterr()
        assert "JSON decode error" in captured.err

    def test_main_approves_without_trigger(self, tmp_path, monkeypatch, capsys):
        """Test main approves prompts without triggers."""
        import trigger_memory

        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Write a function",
            "cwd": str(tmp_path),
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        trigger_memory.main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["decision"] == "approve"
        assert "additionalContext" not in output

    def test_main_approves_on_empty_prompt(self, tmp_path, monkeypatch, capsys):
        """Test main approves with empty prompt."""
        import trigger_memory

        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "",
            "cwd": str(tmp_path),
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        trigger_memory.main()

        captured = capsys.readouterr()
        # Take first JSON line (main may output twice via write_output)
        first_line = captured.out.strip().split("\n")[0]
        output = json.loads(first_line)
        assert output["decision"] == "approve"

    def test_main_approves_when_disabled(self, tmp_path, monkeypatch, capsys):
        """Test main approves when trigger memory disabled."""
        import trigger_memory

        monkeypatch.setenv("CS_TRIGGER_MEMORY_ENABLED", "false")

        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Why did we choose this?",
            "cwd": str(tmp_path),
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        trigger_memory.main()

        captured = capsys.readouterr()
        # Take first JSON line
        first_line = captured.out.strip().split("\n")[0]
        output = json.loads(first_line)
        assert output["decision"] == "approve"

    def test_main_handles_malformed_input(self, monkeypatch, capsys):
        """Test main handles malformed input gracefully."""
        import trigger_memory

        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

        trigger_memory.main()

        captured = capsys.readouterr()
        # Take first JSON line
        first_line = captured.out.strip().split("\n")[0]
        output = json.loads(first_line)
        assert output["decision"] == "approve"

    def test_process_prompt_with_trigger(self, tmp_path, monkeypatch):
        """Test process_prompt detects triggers."""
        import trigger_memory

        # Mock the injector to return memories
        mock_injector = MagicMock()
        mock_memory = MagicMock()
        mock_memory.memory.namespace = "decisions"
        mock_memory.memory.summary = "Test decision"
        mock_memory.memory.timestamp = datetime.now(UTC)
        mock_memory.memory.content = "Decision content"

        mock_injector.process_prompt.return_value = [mock_memory]
        mock_injector.format_for_additional_context.return_value = (
            "## Relevant Memories\nTest"
        )

        with patch("trigger_memory.TriggerMemoryInjector", return_value=mock_injector):
            result = trigger_memory.process_prompt(
                "Why did we choose this?", str(tmp_path)
            )

        assert result is not None
        assert "Relevant Memories" in result

    def test_process_prompt_no_trigger_module(self, tmp_path, monkeypatch):
        """Test process_prompt when trigger module unavailable."""
        import trigger_memory

        original = trigger_memory.TRIGGER_AVAILABLE
        trigger_memory.TRIGGER_AVAILABLE = False

        result = trigger_memory.process_prompt("Why did we?", str(tmp_path))

        trigger_memory.TRIGGER_AVAILABLE = original

        assert result is None


# =============================================================================
# Tests for edge cases
# =============================================================================


class TestTriggerDetectionEdgeCases:
    """Tests for edge cases in trigger detection."""

    def test_detector_handles_whitespace_prompts(self):
        """Test detector handles prompts with only whitespace."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        assert detector.should_inject("   ") is False
        assert detector.should_inject("\n\t") is False

    def test_detector_partial_match(self):
        """Test detector requires trigger phrase, not substring."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()
        # "previously" should match
        assert detector.should_inject("I previously said X") is True
        # But not random text containing the letters
        assert detector.should_inject("Something previo") is False

    def test_injector_handles_memory_without_content(self):
        """Test formatting handles memories without content."""
        from trigger_detector import TriggerMemoryInjector

        mock_memory = MagicMock()
        mock_memory.namespace = "decisions"
        mock_memory.summary = "No content decision"
        mock_memory.timestamp = datetime.now(UTC)
        mock_memory.content = None

        mock_result = MagicMock()
        mock_result.memory = mock_memory

        injector = TriggerMemoryInjector()
        result = injector.format_for_additional_context([mock_result])

        assert "No content decision" in result
        # Should not crash with None content

    def test_process_prompt_handles_exception(self, tmp_path, capsys):
        """Test process_prompt handles exceptions gracefully."""
        import trigger_memory

        with patch(
            "trigger_memory.TriggerMemoryInjector",
            side_effect=Exception("Test error"),
        ):
            result = trigger_memory.process_prompt(
                "Why did we choose this?", str(tmp_path)
            )

        captured = capsys.readouterr()
        assert result is None
        assert "Error processing trigger" in captured.err
