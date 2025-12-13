"""Tests for command_detector hook."""

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
        input_data = {"prompt": "/cs:p test", "cwd": "/test"}
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

    def test_detects_cs_p(self):
        """Test detection of /cs:p command."""
        assert detect_command("/cs:p my project") == "cs:p"

    def test_detects_cs_c(self):
        """Test detection of /cs:c command."""
        assert detect_command("/cs:c project-slug") == "cs:c"

    def test_detects_cs_i(self):
        """Test detection of /cs:i command."""
        assert detect_command("/cs:i") == "cs:i"

    def test_detects_cs_s(self):
        """Test detection of /cs:s command."""
        assert detect_command("/cs:s --list") == "cs:s"

    def test_detects_cs_log(self):
        """Test detection of /cs:log command."""
        assert detect_command("/cs:log on") == "cs:log"

    def test_detects_cs_wt(self):
        """Test detection of /cs:wt: commands."""
        assert detect_command("/cs:wt:create branch") == "cs:wt"
        assert detect_command("/cs:wt:status") == "cs:wt"

    def test_no_command(self):
        """Test no detection for regular prompts."""
        assert detect_command("hello world") is None
        assert detect_command("What is /cs:p?") is None

    def test_whitespace_handling(self):
        """Test whitespace handling."""
        assert detect_command("  /cs:p project  ") == "cs:p"


class TestSaveSessionState:
    """Tests for save_session_state function."""

    def test_saves_state_file(self, tmp_path):
        """Test saving session state to file."""
        state = {"command": "cs:c", "session_id": "test123"}
        save_session_state(str(tmp_path), state)

        state_file = tmp_path / SESSION_STATE_FILE
        assert state_file.exists()

        loaded = json.loads(state_file.read_text())
        assert loaded["command"] == "cs:c"
        assert loaded["session_id"] == "test123"


class TestMain:
    """Tests for main function."""

    def test_detects_and_saves_command(self, tmp_path, monkeypatch, capsys):
        """Test command detection and state saving."""
        input_data = {
            "prompt": "/cs:c my-project",
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
        assert state["command"] == "cs:c"

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
            "/cs:p test",
            "/cs:c project",
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
        assert "Error reading input" in captured.err


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

        save_session_state(str(readonly_dir), {"command": "cs:p"})

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
        run_pre_steps(str(tmp_path), "cs:p")

        command_detector.CONFIG_AVAILABLE = original

    def test_handles_step_exception(self, tmp_path, monkeypatch, capsys):
        """Test handling of exception in step execution."""
        import command_detector

        original = command_detector.CONFIG_AVAILABLE
        command_detector.CONFIG_AVAILABLE = True

        # Mock get_enabled_steps to return a step that will fail
        def mock_get_steps(cmd, step_type):
            return [{"name": "nonexistent-step"}]

        monkeypatch.setattr("command_detector.get_enabled_steps", mock_get_steps)

        run_pre_steps(str(tmp_path), "cs:p")

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
        # Mock __import__ to raise ImportError
        original_import = __builtins__["__import__"]

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                raise ImportError("Module not found")
            return original_import(name, *args, **kwargs)

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

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                return mock_module
            return __builtins__["__import__"](name, *args, **kwargs)

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

        def mock_import(name, *args, **kwargs):
            if name == "context_loader":
                return mock_module
            return __builtins__["__import__"](name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        run_step(str(tmp_path), "context-loader", {})

        captured = capsys.readouterr()
        assert "Step failed" in captured.err
