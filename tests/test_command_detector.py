"""Tests for command_detector hook."""

import builtins
import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
from command_detector import (
    SESSION_STATE_FILE,
    detect_command,
    main,
    pass_through,
    read_input,
    run_pre_steps,
    run_step,
    save_session_state,
    write_output,
)


class TestReadInput:
    """Tests for read_input function."""

    def test_valid_json(self, monkeypatch):
        """Test reading valid JSON input."""
        input_data = {"prompt": "/p test", "cwd": "/test"}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))
        result = read_input()
        assert result == input_data

    def test_invalid_json(self, monkeypatch):
        """Test handling of invalid JSON."""
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        result = read_input()
        assert result is None


class TestWriteOutput:
    """Tests for write_output function."""

    def test_writes_json(self, capsys):
        """Test writing JSON output."""
        write_output({"decision": "approve"})
        captured = capsys.readouterr()
        assert json.loads(captured.out) == {"decision": "approve"}


class TestPassThrough:
    """Tests for pass_through function."""

    def test_returns_approve(self):
        """Test pass_through returns approve decision."""
        result = pass_through()
        assert result == {"decision": "approve"}


class TestDetectCommand:
    """Tests for detect_command function."""

    def test_detects_plan(self):
        """Test detection of /claude-spec:plan command."""
        assert detect_command("/claude-spec:plan my project") == "claude-spec:plan"

    def test_detects_complete(self):
        """Test detection of /claude-spec:complete command."""
        assert (
            detect_command("/claude-spec:complete project-slug")
            == "claude-spec:complete"
        )

    def test_detects_implement(self):
        """Test detection of /claude-spec:implement command."""
        assert detect_command("/claude-spec:implement") == "claude-spec:implement"

    def test_detects_status(self):
        """Test detection of /claude-spec:status command."""
        assert detect_command("/claude-spec:status --list") == "claude-spec:status"

    def test_detects_log(self):
        """Test detection of /claude-spec:log command."""
        assert detect_command("/claude-spec:log on") == "claude-spec:log"

    def test_detects_worktree(self):
        """Test detection of /claude-spec:worktree commands."""
        assert (
            detect_command("/claude-spec:worktree-create branch")
            == "claude-spec:worktree"
        )
        assert detect_command("/claude-spec:worktree-status") == "claude-spec:worktree"

    def test_detects_memory_commands(self):
        """Test detection of memory commands."""
        assert (
            detect_command("/claude-spec:memory-remember decision")
            == "claude-spec:memory-remember"
        )
        assert (
            detect_command("/claude-spec:memory-recall query")
            == "claude-spec:memory-recall"
        )
        assert (
            detect_command("/claude-spec:memory-context spec")
            == "claude-spec:memory-context"
        )
        assert detect_command("/claude-spec:memory status") == "claude-spec:memory"

    def test_detects_code_review_commands(self):
        """Test detection of code review commands."""
        assert (
            detect_command("/claude-spec:code-review path") == "claude-spec:code-review"
        )
        assert detect_command("/claude-spec:code-fix --quick") == "claude-spec:code-fix"

    def test_no_command(self):
        """Test no detection for regular prompts."""
        assert detect_command("hello world") is None
        assert detect_command("What is /claude-spec:plan?") is None

    def test_whitespace_handling(self):
        """Test whitespace handling."""
        assert detect_command("  /claude-spec:plan project  ") == "claude-spec:plan"


class TestSaveSessionState:
    """Tests for save_session_state function."""

    def test_saves_state_file(self, tmp_path):
        """Test saving session state to file."""
        state = {"command": "claude-spec:complete", "session_id": "test123"}
        save_session_state(str(tmp_path), state)

        state_file = tmp_path / SESSION_STATE_FILE
        assert state_file.exists()

        loaded = json.loads(state_file.read_text())
        assert loaded["command"] == "claude-spec:complete"
        assert loaded["session_id"] == "test123"


class TestMain:
    """Tests for main function."""

    def test_detects_and_saves_command(self, tmp_path, monkeypatch, capsys):
        """Test command detection and state saving."""
        input_data = {
            "prompt": "/claude-spec:complete my-project",
            "cwd": str(tmp_path),
            "session_id": "sess123",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        # Check output
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"decision": "approve"}

        # Check state file
        state_file = tmp_path / SESSION_STATE_FILE
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["command"] == "claude-spec:complete"

    def test_no_state_for_non_command(self, tmp_path, monkeypatch, capsys):
        """Test no state file for non-command prompts."""
        input_data = {
            "prompt": "hello world",
            "cwd": str(tmp_path),
            "session_id": "sess123",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        # Check output still approves
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"decision": "approve"}

        # Check no state file
        state_file = tmp_path / SESSION_STATE_FILE
        assert not state_file.exists()

    def test_handles_malformed_input(self, monkeypatch, capsys):
        """Test handling of malformed input."""
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"decision": "approve"}

    def test_always_approves(self, tmp_path, monkeypatch, capsys):
        """Test that main always returns approve."""
        test_cases = [
            "/claude-spec:plan test",
            "/claude-spec:complete project",
            "regular text",
            "",
        ]

        for prompt in test_cases:
            input_data = {"prompt": prompt, "cwd": str(tmp_path)}
            monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

            main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {"decision": "approve"}, f"Failed for prompt: {prompt}"


class TestReadInputErrors:
    """Tests for error handling in read_input."""

    def test_generic_exception(self, monkeypatch, capsys):
        """Test handling of generic exception in read_input."""
        mock_stdin = MagicMock()
        mock_stdin.read.side_effect = OSError("Read error")
        monkeypatch.setattr("sys.stdin", mock_stdin)

        result = read_input()
        assert result is None

        captured = capsys.readouterr()
        assert "I/O error reading input" in captured.err


class TestWriteOutputErrors:
    """Tests for error handling in write_output."""

    def test_json_encode_error(self, monkeypatch, capsys):
        """Test handling of JSON encode error."""

        # Create an object that can't be serialized
        class Unserializable:
            pass

        # This should fall back to the hardcoded approve response
        write_output({"bad": Unserializable()})

        captured = capsys.readouterr()
        # Should still output valid JSON
        assert '{"decision": "approve"}' in captured.out


class TestSaveSessionStateErrors:
    """Tests for error handling in save_session_state."""

    def test_write_error(self, tmp_path, capsys):
        """Test handling of write error."""
        # Make directory read-only
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)

        save_session_state(str(readonly_dir), {"command": "claude-spec:plan"})

        captured = capsys.readouterr()
        assert "Error saving state" in captured.err

        # Cleanup
        readonly_dir.chmod(0o755)


class TestRunPreSteps:
    """Tests for run_pre_steps function."""

    def test_returns_early_when_config_unavailable(self, tmp_path, monkeypatch):
        """Test early return when CONFIG_AVAILABLE is False."""
        import command_detector

        original = command_detector.CONFIG_AVAILABLE
        command_detector.CONFIG_AVAILABLE = False

        # Should not raise
        run_pre_steps(str(tmp_path), "claude-spec:plan")

        command_detector.CONFIG_AVAILABLE = original

    def test_handles_step_exception(self, tmp_path, monkeypatch, capsys):
        """Test handling of exception in step execution."""
        import command_detector

        original = command_detector.CONFIG_AVAILABLE
        command_detector.CONFIG_AVAILABLE = True

        # Mock get_enabled_steps to return a step that will fail
        def mock_get_steps(cmd, step_type):
            return [{"name": "nonexistent-step"}]

        # Use raising=False in case the original import failed
        monkeypatch.setattr(
            "command_detector.get_enabled_steps", mock_get_steps, raising=False
        )

        run_pre_steps(str(tmp_path), "claude-spec:plan")

        captured = capsys.readouterr()
        assert "Unknown step" in captured.err

        command_detector.CONFIG_AVAILABLE = original


class TestRunStep:
    """Tests for run_step function."""

    def test_unknown_step_name(self, tmp_path, capsys):
        """Test handling of unknown step name."""
        run_step(str(tmp_path), "unknown-step", {})

        captured = capsys.readouterr()
        assert "Unknown step" in captured.err

    def test_import_error(self, tmp_path, monkeypatch, capsys):
        """Test handling of import error."""
        # Save reference to real import before patching
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                raise ImportError("Module not found")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        run_step(str(tmp_path), "context-loader", {})

        captured = capsys.readouterr()
        assert "Could not import step" in captured.err

    def test_module_with_run_function(self, tmp_path, monkeypatch):
        """Test running a step module with run function."""
        # Create a mock module with a run function
        mock_module = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_module.run.return_value = mock_result

        # Save reference to real import before patching
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        run_step(str(tmp_path), "context-loader", {"some": "config"})

        mock_module.run.assert_called_once()

    def test_module_run_returns_failure(self, tmp_path, monkeypatch, capsys):
        """Test handling of failed step result."""
        mock_module = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "Step failed"
        mock_module.run.return_value = mock_result

        # Save reference to real import before patching
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        run_step(str(tmp_path), "context-loader", {})

        captured = capsys.readouterr()
        assert "Step failed" in captured.err


# ============================================================================
# NEW TESTS ADDED FOR COVERAGE GAPS
# ============================================================================


class TestDetectCommandMemory:
    """Tests for memory command detection."""

    def test_detects_memory_remember(self):
        """Test detection of /claude-spec:memory-remember command."""
        assert (
            detect_command("/claude-spec:memory-remember decision")
            == "claude-spec:memory-remember"
        )

    def test_detects_memory_remember_with_args(self):
        """Test detection of /claude-spec:memory-remember with arguments."""
        assert (
            detect_command("/claude-spec:memory-remember learning Important insight")
            == "claude-spec:memory-remember"
        )

    def test_detects_memory_recall_with_whitespace(self):
        """Test detection of /claude-spec:memory-recall with leading/trailing whitespace."""
        assert (
            detect_command("  /claude-spec:memory-recall query  ")
            == "claude-spec:memory-recall"
        )


class TestRunStepGenericException:
    """Tests for generic exception handling in run_step."""

    def test_module_run_raises_generic_exception(self, tmp_path, monkeypatch, capsys):
        """Test handling of generic exception from module.run()."""
        mock_module = MagicMock()
        mock_module.run.side_effect = RuntimeError("Unexpected error during execution")

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        result = run_step(str(tmp_path), "context-loader", {})

        assert result is False
        captured = capsys.readouterr()
        assert "execution error" in captured.err or "Unexpected error" in captured.err

    def test_module_run_raises_oserror(self, tmp_path, monkeypatch, capsys):
        """Test handling of OSError from module.run()."""
        mock_module = MagicMock()
        mock_module.run.side_effect = OSError("Permission denied")

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        result = run_step(str(tmp_path), "context-loader", {})

        assert result is False
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_module_run_raises_valueerror(self, tmp_path, monkeypatch, capsys):
        """Test handling of ValueError from module.run()."""
        mock_module = MagicMock()
        mock_module.run.side_effect = ValueError("Invalid configuration")

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        result = run_step(str(tmp_path), "context-loader", {})

        assert result is False


class TestRunPreStepsGenericException:
    """Tests for generic exception handling in run_pre_steps."""

    def test_continues_after_step_exception(self, tmp_path, monkeypatch, capsys):
        """Test that pre-steps continue after one step raises an exception."""
        import command_detector

        original = command_detector.CONFIG_AVAILABLE
        command_detector.CONFIG_AVAILABLE = True

        # Mock get_enabled_steps to return multiple steps
        def mock_get_steps(cmd, step_type):
            return [
                {"name": "failing-step"},
                {"name": "another-step"},
            ]

        monkeypatch.setattr(
            "command_detector.get_enabled_steps", mock_get_steps, raising=False
        )

        # Mock run_step to track calls
        call_count = [0]

        def mock_run_step(cwd, step_name, config, log_prefix=""):
            call_count[0] += 1
            # First step raises, second should still be called
            raise RuntimeError(f"Step {step_name} failed")

        # Apply the mock via monkeypatch
        monkeypatch.setattr("command_detector.run_step", mock_run_step, raising=False)

        run_pre_steps(str(tmp_path), "claude-spec:plan")

        # Verify both steps were attempted (exception is caught per-step)
        captured = capsys.readouterr()
        # Should see error messages for both steps
        assert "error" in captured.err.lower()

        command_detector.CONFIG_AVAILABLE = original


class TestDetectCommandEdgeCases:
    """Additional edge case tests for detect_command."""

    def test_command_at_start_only(self):
        """Test that command must be at the start of the prompt."""
        # Command in middle of text should not be detected
        assert detect_command("I want to run /claude-spec:plan") is None

    def test_similar_but_not_command(self):
        """Test similar patterns that are not commands."""
        assert detect_command("/claude:plan") is None  # Missing -spec
        assert detect_command("claude-spec:plan") is None  # Missing leading slash
        assert detect_command("/claude-spec") is None  # Missing command name
        assert detect_command("/claude-specplan") is None  # Missing colon

    def test_empty_and_whitespace(self):
        """Test empty and whitespace-only prompts."""
        assert detect_command("") is None
        assert detect_command("   ") is None
        assert detect_command("\n\t") is None


class TestMainWithIOUnavailable:
    """Tests for main when IO_AVAILABLE is False."""

    def test_uses_fallback_io(self, tmp_path, monkeypatch, capsys):
        """Test that main uses fallback I/O when IO_AVAILABLE is False."""
        import command_detector

        original_io = command_detector.IO_AVAILABLE
        command_detector.IO_AVAILABLE = False

        input_data = {
            "prompt": "/claude-spec:plan test",
            "cwd": str(tmp_path),
            "session_id": "test123",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"decision": "approve"}

        command_detector.IO_AVAILABLE = original_io


class TestRunStepModuleNoRunFunction:
    """Tests for run_step when module lacks run function."""

    def test_module_without_run_function(self, tmp_path, monkeypatch, capsys):
        """Test handling when module has no run function."""
        mock_module = MagicMock(spec=[])  # Empty spec means no run attribute
        del mock_module.run  # Ensure run doesn't exist

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        result = run_step(str(tmp_path), "context-loader", {})

        assert result is False
        captured = capsys.readouterr()
        assert "has no run function" in captured.err


class TestInlineFallbackPaths:
    """Tests for inline fallback I/O when both IO and FALLBACK are unavailable."""

    def test_main_with_inline_fallback(self, tmp_path, monkeypatch, capsys):
        """Test main uses inline fallback when both IO and FALLBACK unavailable."""
        import command_detector

        original_io = command_detector.IO_AVAILABLE
        original_fb = command_detector.FALLBACK_AVAILABLE

        command_detector.IO_AVAILABLE = False
        command_detector.FALLBACK_AVAILABLE = False

        input_data = {
            "prompt": "/claude-spec:plan test",
            "cwd": str(tmp_path),
            "session_id": "test123",
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"decision": "approve"}

        command_detector.IO_AVAILABLE = original_io
        command_detector.FALLBACK_AVAILABLE = original_fb

    def test_inline_fallback_with_malformed_input(self, monkeypatch, capsys):
        """Test inline fallback handles malformed input."""
        import command_detector

        original_io = command_detector.IO_AVAILABLE
        original_fb = command_detector.FALLBACK_AVAILABLE

        command_detector.IO_AVAILABLE = False
        command_detector.FALLBACK_AVAILABLE = False

        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"decision": "approve"}

        command_detector.IO_AVAILABLE = original_io
        command_detector.FALLBACK_AVAILABLE = original_fb

    def test_inline_fallback_pass_through(self, tmp_path, monkeypatch, capsys):
        """Test inline fallback pass_through function."""
        import command_detector

        original_io = command_detector.IO_AVAILABLE
        original_fb = command_detector.FALLBACK_AVAILABLE

        command_detector.IO_AVAILABLE = False
        command_detector.FALLBACK_AVAILABLE = False

        # Empty input triggers pass_through
        input_data = {"prompt": "", "cwd": "", "session_id": ""}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"decision": "approve"}

        command_detector.IO_AVAILABLE = original_io
        command_detector.FALLBACK_AVAILABLE = original_fb


class TestRunPreStepsIOUnavailable:
    """Tests for run_pre_steps when IO_AVAILABLE is False."""

    def test_skips_steps_when_io_unavailable(self, tmp_path, monkeypatch, capsys):
        """Test that steps are skipped when IO_AVAILABLE is False."""
        import command_detector

        original_io = command_detector.IO_AVAILABLE
        original_config = command_detector.CONFIG_AVAILABLE

        # Mock get_enabled_steps to return a step
        mock_steps = [{"name": "test-step", "enabled": True}]
        monkeypatch.setattr(
            command_detector, "get_enabled_steps", lambda cmd, phase: mock_steps
        )

        command_detector.IO_AVAILABLE = False
        command_detector.CONFIG_AVAILABLE = True

        run_pre_steps(str(tmp_path), "claude-spec:complete")

        captured = capsys.readouterr()
        assert "skipped" in captured.err or "not available" in captured.err

        command_detector.IO_AVAILABLE = original_io
        command_detector.CONFIG_AVAILABLE = original_config


class TestFallbackIOFunctions:
    """Tests for _fallback_io wrapper functions."""

    def test_fallback_io_read_input(self, monkeypatch):
        """Test _fallback_io_read_input wrapper."""
        from command_detector import _fallback_io_read_input

        input_data = {"prompt": "/claude-spec:plan", "cwd": "/test"}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        result = _fallback_io_read_input()
        assert result == input_data

    def test_fallback_io_write_output(self, capsys):
        """Test _fallback_io_write_output wrapper."""
        from command_detector import _fallback_io_write_output

        _fallback_io_write_output({"decision": "approve"})

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"decision": "approve"}
