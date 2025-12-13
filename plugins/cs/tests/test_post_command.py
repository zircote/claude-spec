"""Tests for post_command hook."""

import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
from post_command import (
    SESSION_STATE_FILE,
    cleanup_session_state,
    load_session_state,
    main,
    read_input,
    run_post_steps,
    run_step,
    write_output,
)


class TestReadInput:
    """Tests for read_input function."""

    def test_valid_json(self, monkeypatch):
        """Test reading valid JSON input."""
        input_data = {"hook_event_name": "Stop", "cwd": "/test"}
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
        write_output({"continue": False})
        captured = capsys.readouterr()
        assert json.loads(captured.out) == {"continue": False}


class TestLoadSessionState:
    """Tests for load_session_state function."""

    def test_loads_existing_state(self, tmp_path):
        """Test loading existing state file."""
        state = {"command": "cs:c", "session_id": "test123"}
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text(json.dumps(state))

        loaded = load_session_state(str(tmp_path))
        assert loaded == state

    def test_returns_none_if_missing(self, tmp_path):
        """Test returns None if state file missing."""
        result = load_session_state(str(tmp_path))
        assert result is None

    def test_returns_none_on_invalid_json(self, tmp_path):
        """Test returns None on invalid JSON."""
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text("not json")

        result = load_session_state(str(tmp_path))
        assert result is None


class TestCleanupSessionState:
    """Tests for cleanup_session_state function."""

    def test_removes_state_file(self, tmp_path):
        """Test removing state file."""
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text('{"command": "cs:c"}')
        assert state_file.exists()

        cleanup_session_state(str(tmp_path))
        assert not state_file.exists()

    def test_handles_missing_file(self, tmp_path):
        """Test handling missing file gracefully."""
        # Should not raise
        cleanup_session_state(str(tmp_path))


class TestMain:
    """Tests for main function."""

    def test_cleans_up_state_after_processing(self, tmp_path, monkeypatch, capsys):
        """Test that state file is cleaned up after processing."""
        # Create state file
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text(json.dumps({"command": "cs:c"}))

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        # Check output
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

        # State file should be cleaned up
        assert not state_file.exists()

    def test_handles_no_state(self, tmp_path, monkeypatch, capsys):
        """Test handling when no state file exists."""
        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

    def test_handles_empty_cwd(self, monkeypatch, capsys):
        """Test handling empty cwd."""
        input_data = {"hook_event_name": "Stop", "cwd": ""}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

    def test_handles_malformed_input(self, monkeypatch, capsys):
        """Test handling malformed input."""
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

    def test_always_returns_continue_false(self, tmp_path, monkeypatch, capsys):
        """Test that main always returns continue: false."""
        test_cases = [
            {"hook_event_name": "Stop", "cwd": str(tmp_path)},
            {"hook_event_name": "Stop", "cwd": ""},
            {},
        ]

        for input_data in test_cases:
            monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

            main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {"continue": False}


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

        class Unserializable:
            pass

        write_output({"bad": Unserializable()})

        captured = capsys.readouterr()
        assert '{"continue": false}' in captured.out


class TestCleanupSessionStateErrors:
    """Tests for error handling in cleanup_session_state."""

    def test_cleanup_error(self, tmp_path, monkeypatch, capsys):
        """Test handling of cleanup error."""
        # Create state file
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text('{"command": "cs:c"}')

        # Mock Path.unlink to raise an exception
        original_unlink = Path.unlink

        def mock_unlink(self, *args, **kwargs):
            if SESSION_STATE_FILE in str(self):
                raise PermissionError("Permission denied")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", mock_unlink)

        cleanup_session_state(str(tmp_path))

        captured = capsys.readouterr()
        assert "Error cleaning state" in captured.err


class TestRunPostSteps:
    """Tests for run_post_steps function."""

    def test_returns_early_when_config_unavailable(self, tmp_path, monkeypatch):
        """Test early return when CONFIG_AVAILABLE is False."""
        import post_command

        original = post_command.CONFIG_AVAILABLE
        post_command.CONFIG_AVAILABLE = False

        # Should not raise
        run_post_steps(str(tmp_path), "cs:c")

        post_command.CONFIG_AVAILABLE = original

    def test_handles_step_exception(self, tmp_path, monkeypatch, capsys):
        """Test handling of exception in step execution."""
        import post_command

        original = post_command.CONFIG_AVAILABLE
        post_command.CONFIG_AVAILABLE = True

        def mock_get_steps(cmd, step_type):
            return [{"name": "nonexistent-step"}]

        monkeypatch.setattr("post_command.get_enabled_steps", mock_get_steps)

        run_post_steps(str(tmp_path), "cs:c")

        captured = capsys.readouterr()
        assert "Unknown step" in captured.err

        post_command.CONFIG_AVAILABLE = original


class TestRunStepPost:
    """Tests for run_step function in post_command."""

    def test_unknown_step_name(self, tmp_path, capsys):
        """Test handling of unknown step name."""
        run_step(str(tmp_path), "unknown-step", {})

        captured = capsys.readouterr()
        assert "Unknown step" in captured.err

    def test_import_error(self, tmp_path, monkeypatch, capsys):
        """Test handling of import error."""
        original_import = __builtins__["__import__"]

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                raise ImportError("Module not found")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        run_step(str(tmp_path), "archive-logs", {})

        captured = capsys.readouterr()
        assert "Could not import step" in captured.err

    def test_module_with_run_function(self, tmp_path, monkeypatch):
        """Test running a step module with run function."""
        mock_module = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_module.run.return_value = mock_result

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                return mock_module
            return __builtins__["__import__"](name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        run_step(str(tmp_path), "archive-logs", {"some": "config"})

        mock_module.run.assert_called_once()

    def test_module_run_returns_failure(self, tmp_path, monkeypatch, capsys):
        """Test handling of failed step result."""
        mock_module = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "Archive failed"
        mock_module.run.return_value = mock_result

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                return mock_module
            return __builtins__["__import__"](name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        run_step(str(tmp_path), "archive-logs", {})

        captured = capsys.readouterr()
        assert "Archive failed" in captured.err
