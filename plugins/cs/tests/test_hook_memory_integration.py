"""Integration tests for hook-based memory system.

Tests the end-to-end workflow of:
- PostToolUse learning capture
- SessionStart memory injection
- Trigger phrase memory injection
- Queue flushing

These tests verify components work together correctly.
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
# Integration Tests: PostToolUse + Learning Detection
# =============================================================================


class TestPostToolUseLearningIntegration:
    """Integration tests for PostToolUse hook with learning detection."""

    def test_learning_detection_end_to_end(self):
        """Test full learning detection pipeline."""
        from learnings import LearningDetector, extract_learning

        detector = LearningDetector(threshold=0.5)

        # Simulate a bash command with error
        response = {
            "exit_code": 1,
            "stderr": "Error: command not found: foobar\n",
            "stdout": "",
        }

        learning = extract_learning(
            tool_name="Bash",
            response=response,
            context="Running foobar command",
            spec="test-spec",
            detector=detector,
        )

        assert learning is not None
        assert learning.tool_name == "Bash"
        assert learning.exit_code == 1
        assert "error" in learning.category

    def test_learning_deduplication(self):
        """Test that duplicate learnings are filtered."""
        from learnings import LearningDetector, SessionDeduplicator, extract_learning

        detector = LearningDetector(threshold=0.5)
        deduplicator = SessionDeduplicator(max_size=100)

        response = {
            "exit_code": 1,
            "stderr": "Error: same error message\n",
            "stdout": "",
        }

        # First extraction should succeed
        learning1 = extract_learning(
            tool_name="Bash",
            response=response,
            detector=detector,
            deduplicator=deduplicator,
        )
        assert learning1 is not None

        # Second extraction of same error should be deduplicated
        learning2 = extract_learning(
            tool_name="Bash",
            response=response,
            detector=detector,
            deduplicator=deduplicator,
        )
        assert learning2 is None  # Filtered as duplicate

    def test_secret_filtering_in_learning(self):
        """Test that secrets are filtered from learnings."""
        from learnings import LearningDetector, extract_learning

        detector = LearningDetector(threshold=0.3)  # Lower threshold for test

        # Response containing a real secret pattern (GitHub PAT format: ghp_ + 36 chars)
        github_pat = "ghp_abcdefghij1234567890ABCDEFGHIJ123456"
        response = {
            "exit_code": 1,
            "stderr": f"Error: authentication failed with token: {github_pat}\n",
            "stdout": "",
        }

        learning = extract_learning(
            tool_name="Bash",
            response=response,
            detector=detector,
        )

        if learning:
            # Secret should be filtered and replaced with placeholder
            assert github_pat not in learning.output_excerpt
            assert "[SECRET:github_pat]" in learning.output_excerpt


# =============================================================================
# Integration Tests: SessionStart + Memory Injection
# =============================================================================


class TestSessionStartMemoryIntegration:
    """Integration tests for SessionStart with memory injection."""

    def test_session_start_full_workflow(self, tmp_path, monkeypatch, capsys):
        """Test complete session start workflow."""
        import session_start

        # Set up CS project
        (tmp_path / "docs" / "spec").mkdir(parents=True)
        (tmp_path / "CLAUDE.md").write_text("# Test Project\n")

        input_data = {
            "hook_event_name": "SessionStart",
            "cwd": str(tmp_path),
            "session_id": "test-session",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        session_start.main()

        captured = capsys.readouterr()
        # Should output context header
        assert "Claude Spec Session Context" in captured.out

    def test_session_start_detects_active_spec(self, tmp_path):
        """Test that session start can detect active specs."""
        from spec_detector import detect_active_spec

        # Create active spec
        spec_dir = tmp_path / "docs" / "spec" / "active" / "2025-12-17-test-feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "README.md").write_text("# Test Feature\n")

        result = detect_active_spec(tmp_path)

        assert result is not None
        assert result.slug == "test-feature"

    def test_memory_injection_config_integration(self, tmp_path, monkeypatch):
        """Test memory injection respects configuration."""
        from config_loader import (
            get_memory_injection_config,
            is_memory_injection_enabled,
            reset_config_cache,
        )

        reset_config_cache()

        # Create config with custom settings
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "sessionStart": {
                            "memoryInjection": {
                                "enabled": True,
                                "limit": 15,
                                "includeContent": True,
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config_file)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        assert is_memory_injection_enabled() is True
        config = get_memory_injection_config()
        assert config["limit"] == 15
        assert config["includeContent"] is True


# =============================================================================
# Integration Tests: Trigger Detection + Memory Injection
# =============================================================================


class TestTriggerMemoryIntegration:
    """Integration tests for trigger detection with memory injection."""

    def test_trigger_detection_full_workflow(self, tmp_path, monkeypatch, capsys):
        """Test complete trigger detection workflow."""
        import trigger_memory

        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Why did we choose hooks for memory?",
            "cwd": str(tmp_path),
            "session_id": "test-session",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock the injector to return some memories
        mock_memory = MagicMock()
        mock_memory.memory.namespace = "decisions"
        mock_memory.memory.summary = "Chose hooks for memory capture"
        mock_memory.memory.timestamp = datetime.now(UTC)
        mock_memory.memory.content = "We decided because..."

        mock_injector = MagicMock()
        mock_injector.process_prompt.return_value = [mock_memory]
        mock_injector.format_for_additional_context.return_value = (
            "## Relevant Memories\n\nTest content"
        )

        with patch("trigger_memory.TriggerMemoryInjector", return_value=mock_injector):
            trigger_memory.main()

        captured = capsys.readouterr()
        # Take first JSON line
        first_line = captured.out.strip().split("\n")[0]
        output = json.loads(first_line)

        assert output["decision"] == "approve"
        assert "additionalContext" in output
        assert "Relevant Memories" in output["additionalContext"]

    def test_trigger_patterns_coverage(self):
        """Test that all trigger patterns work correctly."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()

        # Test all patterns
        trigger_phrases = [
            "Why did we choose this approach?",
            "What was the decision about the API?",
            "Remind me what we discussed",
            "Let's continue from where we left off",
            "Continue where we stopped",
            "Last time we talked about X",
            "We previously decided to use hooks",
            "What was the blocker again?",
            "What happened with the refactor?",
            "What was the issue?",
            "Where were we in the implementation?",
            "Let me pick up where I left off",
            "What did we learn from that?",
            "What went wrong last time?",
            "What was blocking us?",
            "Recall the decision about caching",
        ]

        for phrase in trigger_phrases:
            assert detector.should_inject(phrase), f"Failed for: {phrase}"

    def test_no_trigger_for_normal_prompts(self):
        """Test that normal prompts don't trigger injection."""
        from trigger_detector import TriggerDetector

        detector = TriggerDetector()

        normal_prompts = [
            "Write a function to sort an array",
            "Fix the bug in the login page",
            "Add error handling to the API",
            "Create a new component",
            "Run the tests",
            "Deploy to staging",
        ]

        for prompt in normal_prompts:
            assert not detector.should_inject(prompt), f"False positive: {prompt}"


# =============================================================================
# Integration Tests: Hook Chain
# =============================================================================


class TestHookChainIntegration:
    """Integration tests for hook execution chain."""

    def test_hooks_json_valid_structure(self):
        """Test that hooks.json has valid structure."""
        hooks_json_path = Path(__file__).parent.parent / "hooks" / "hooks.json"
        assert hooks_json_path.exists()

        with open(hooks_json_path) as f:
            hooks_config = json.load(f)

        assert "hooks" in hooks_config
        assert "SessionStart" in hooks_config["hooks"]
        assert "UserPromptSubmit" in hooks_config["hooks"]
        assert "PostToolUse" in hooks_config["hooks"]
        assert "Stop" in hooks_config["hooks"]

    def test_all_hook_scripts_exist(self):
        """Test that all registered hook scripts exist."""
        hooks_dir = Path(__file__).parent.parent / "hooks"
        hooks_json_path = hooks_dir / "hooks.json"

        with open(hooks_json_path) as f:
            hooks_config = json.load(f)

        for _event_name, event_hooks in hooks_config["hooks"].items():
            for hook_entry in event_hooks:
                for hook in hook_entry.get("hooks", []):
                    if hook.get("type") == "command":
                        command = hook["command"]
                        # Command format: ${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.sh <script>.py
                        # Extract the wrapper and script name
                        parts = command.split("/")[-1].split()
                        if len(parts) == 2 and parts[0] == "run-hook.sh":
                            # New format: run-hook.sh <script>.py
                            wrapper_path = hooks_dir / parts[0]
                            script_path = hooks_dir / parts[1]
                            assert wrapper_path.exists(), (
                                f"Missing wrapper: {wrapper_path}"
                            )
                            assert script_path.exists(), (
                                f"Missing script: {script_path}"
                            )
                        else:
                            # Legacy format: direct script name
                            script_name = parts[0]
                            script_path = hooks_dir / script_name
                            assert script_path.exists(), f"Missing: {script_path}"

    def test_user_prompt_submit_hook_order(self):
        """Test that UserPromptSubmit hooks are in correct order."""
        hooks_json_path = Path(__file__).parent.parent / "hooks" / "hooks.json"

        with open(hooks_json_path) as f:
            hooks_config = json.load(f)

        ups_hooks = hooks_config["hooks"]["UserPromptSubmit"]
        hook_names = []

        for entry in ups_hooks:
            for hook in entry.get("hooks", []):
                command = hook.get("command", "")
                # Command format: ${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.sh <script>.py
                # Extract the Python script name (last argument)
                parts = command.split()
                script_name = parts[
                    -1
                ]  # Get the last part (e.g., "command_detector.py")
                hook_names.append(script_name)

        # command_detector should be first
        assert hook_names[0] == "command_detector.py"
        # prompt_capture should be second
        assert hook_names[1] == "prompt_capture.py"
        # trigger_memory should be last (after prompt capture)
        assert hook_names[2] == "trigger_memory.py"


# =============================================================================
# Integration Tests: Memory Formatting
# =============================================================================


class TestMemoryFormattingIntegration:
    """Integration tests for memory formatting consistency."""

    def test_session_and_trigger_formatting_consistency(self):
        """Test that session and trigger formatters produce consistent output."""
        from memory_injector import MemoryInjector
        from trigger_detector import TriggerMemoryInjector

        # Create same mock memory
        mock_memory = MagicMock()
        mock_memory.namespace = "decisions"
        mock_memory.summary = "Test decision"
        mock_memory.timestamp = datetime.now(UTC)
        mock_memory.content = "Decision content"

        mock_result = MagicMock()
        mock_result.memory = mock_memory

        session_injector = MemoryInjector()
        trigger_injector = TriggerMemoryInjector()

        session_output = session_injector.format_for_context([mock_result])
        trigger_output = trigger_injector.format_for_additional_context([mock_result])

        # Both should use same icon for decisions
        assert "🎯" in session_output
        assert "🎯" in trigger_output

        # Both should include summary
        assert "Test decision" in session_output
        assert "Test decision" in trigger_output

    def test_namespace_icons_consistency(self):
        """Test that namespace icons are consistent across modules."""
        from memory_injector import MemoryInjector
        from trigger_detector import TriggerMemoryInjector

        session_injector = MemoryInjector()
        trigger_injector = TriggerMemoryInjector()

        namespaces = [
            "decisions",
            "learnings",
            "blockers",
            "progress",
            "patterns",
            "reviews",
            "retrospective",
        ]

        for ns in namespaces:
            session_icon = session_injector._get_namespace_icon(ns)
            trigger_icon = trigger_injector._get_namespace_icon(ns)
            assert session_icon == trigger_icon, f"Icon mismatch for {ns}"


# =============================================================================
# Integration Tests: Environment Variables
# =============================================================================


class TestEnvironmentVariableIntegration:
    """Integration tests for environment variable controls."""

    def test_all_env_vars_can_disable_features(self, monkeypatch):
        """Test that environment variables can disable all features."""
        import post_tool_capture
        import trigger_memory

        from memory.capture import is_auto_capture_enabled

        # Test tool capture disable
        monkeypatch.setenv("CS_TOOL_CAPTURE_ENABLED", "false")
        assert post_tool_capture.is_tool_capture_enabled() is False

        # Test trigger memory disable
        monkeypatch.setenv("CS_TRIGGER_MEMORY_ENABLED", "false")
        assert trigger_memory.is_trigger_memory_enabled() is False

        # Test auto-capture disable
        monkeypatch.setenv("CS_AUTO_CAPTURE_ENABLED", "false")
        assert is_auto_capture_enabled() is False

    def test_default_env_var_values(self, monkeypatch):
        """Test default values when env vars not set."""

        import post_tool_capture
        import trigger_memory

        # Clear env vars
        for var in [
            "CS_TOOL_CAPTURE_ENABLED",
            "CS_TRIGGER_MEMORY_ENABLED",
            "CS_AUTO_CAPTURE_ENABLED",
        ]:
            monkeypatch.delenv(var, raising=False)

        # All should default to enabled
        assert post_tool_capture.is_tool_capture_enabled() is True
        assert trigger_memory.is_trigger_memory_enabled() is True
