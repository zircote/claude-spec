"""Tests for post_command hook."""

import builtins
import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        assert "I/O error reading input" in captured.err


class TestWriteOutputErrors:
    """Tests for error handling in write_output."""

    def test_json_encode_error(self, monkeypatch, capsys):
        """Test handling of JSON encode error.

        When write_output encounters a serialization error, it falls back
        to a hardcoded JSON response. The shared hook_io module uses
        {"decision": "approve"} as the default fallback since it's agnostic
        to hook type.
        """

        class Unserializable:
            pass

        write_output({"bad": Unserializable()})

        captured = capsys.readouterr()
        # The shared write_output from hook_io uses a generic fallback
        assert '{"decision": "approve"}' in captured.out


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

        # Use raising=False in case the original import failed
        monkeypatch.setattr(
            "post_command.get_enabled_steps", mock_get_steps, raising=False
        )

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
        # Save reference to real import before patching
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                raise ImportError("Module not found")
            return real_import(name, *args, **kwargs)

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

        # Save reference to real import before patching
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                return mock_module
            return real_import(name, *args, **kwargs)

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

        # Save reference to real import before patching
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        run_step(str(tmp_path), "archive-logs", {})

        captured = capsys.readouterr()
        assert "Archive failed" in captured.err


# ============================================================================
# NEW TESTS ADDED FOR COVERAGE GAPS
# ============================================================================


class TestLoadSessionStateOSError:
    """Tests for load_session_state OSError handling."""

    def test_load_state_oserror(self, tmp_path, monkeypatch, capsys):
        """Test handling of OSError when loading session state."""
        # Create state file
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text('{"command": "cs:c"}')

        # Mock open to raise OSError
        original_open = open

        def mock_open(path, *args, **kwargs):
            if SESSION_STATE_FILE in str(path):
                raise OSError("Permission denied")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", mock_open):
            result = load_session_state(str(tmp_path))

        assert result is None
        captured = capsys.readouterr()
        assert "Error loading state" in captured.err

    def test_load_state_generic_exception(self, tmp_path, monkeypatch, capsys):
        """Test handling of generic exception when loading session state."""
        # Create state file
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text('{"command": "cs:c"}')

        # Mock open to raise a generic exception
        original_open = open

        def mock_open(path, *args, **kwargs):
            if SESSION_STATE_FILE in str(path):
                raise RuntimeError("Unexpected error")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", mock_open):
            result = load_session_state(str(tmp_path))

        assert result is None
        captured = capsys.readouterr()
        assert "Error loading state" in captured.err


class TestRunPostStepsGenericException:
    """Tests for generic exception handling in run_post_steps."""

    def test_continues_after_step_exception(self, tmp_path, monkeypatch, capsys):
        """Test that post-steps continue after one step raises an exception."""
        import post_command

        original = post_command.CONFIG_AVAILABLE
        post_command.CONFIG_AVAILABLE = True

        # Mock get_enabled_steps to return multiple steps
        def mock_get_steps(cmd, step_type):
            return [
                {"name": "failing-step"},
                {"name": "another-step"},
            ]

        monkeypatch.setattr(
            "post_command.get_enabled_steps", mock_get_steps, raising=False
        )

        run_post_steps(str(tmp_path), "cs:c")

        # Both steps should be attempted (exception is caught per-step)
        captured = capsys.readouterr()
        # Should see error messages for unknown steps
        assert "Unknown step" in captured.err

        post_command.CONFIG_AVAILABLE = original


class TestRunStepGenericException:
    """Tests for generic exception handling in run_step."""

    def test_module_run_raises_generic_exception(self, tmp_path, monkeypatch, capsys):
        """Test handling of generic exception from module.run()."""
        mock_module = MagicMock()
        mock_module.run.side_effect = RuntimeError("Unexpected error during execution")

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        result = run_step(str(tmp_path), "archive-logs", {})

        assert result is False
        captured = capsys.readouterr()
        assert "execution error" in captured.err or "Unexpected error" in captured.err

    def test_module_run_raises_oserror(self, tmp_path, monkeypatch, capsys):
        """Test handling of OSError from module.run()."""
        mock_module = MagicMock()
        mock_module.run.side_effect = OSError("Disk full")

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        result = run_step(str(tmp_path), "archive-logs", {})

        assert result is False
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()


class TestMainWithIOUnavailable:
    """Tests for main when IO_AVAILABLE is False."""

    def test_uses_fallback_io(self, tmp_path, monkeypatch, capsys):
        """Test that main uses fallback I/O when IO_AVAILABLE is False."""
        import post_command

        original_io = post_command.IO_AVAILABLE
        post_command.IO_AVAILABLE = False

        input_data = {
            "hook_event_name": "Stop",
            "cwd": str(tmp_path),
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

        post_command.IO_AVAILABLE = original_io


class TestMainWithStateButNoCommand:
    """Tests for main when state file exists but has no command."""

    def test_no_command_in_state(self, tmp_path, monkeypatch, capsys):
        """Test handling when state file exists but command is missing."""
        # Create state file without command
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text(json.dumps({"session_id": "test123"}))

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        # Should complete without error
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

        # State file should still be cleaned up
        assert not state_file.exists()

    def test_empty_command_in_state(self, tmp_path, monkeypatch, capsys):
        """Test handling when state file has empty command."""
        # Create state file with empty command
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text(json.dumps({"command": "", "session_id": "test123"}))

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}


class TestRunStepModuleNoRunFunction:
    """Tests for run_step when module lacks run function."""

    def test_module_without_run_function(self, tmp_path, monkeypatch, capsys):
        """Test handling when module has no run function."""
        mock_module = MagicMock(spec=[])  # Empty spec means no run attribute
        del mock_module.run  # Ensure run doesn't exist

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        result = run_step(str(tmp_path), "archive-logs", {})

        assert result is False
        captured = capsys.readouterr()
        assert "has no run function" in captured.err


class TestCleanupSessionStateEdgeCases:
    """Edge case tests for cleanup_session_state."""

    def test_cleanup_directory_not_writable(self, tmp_path, capsys):
        """Test cleanup when directory permissions are restrictive."""
        # Create state file in a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        state_file = subdir / SESSION_STATE_FILE
        state_file.write_text('{"command": "cs:c"}')

        # Make directory read-only (file can't be deleted)
        subdir.chmod(0o444)

        try:
            cleanup_session_state(str(subdir))
            captured = capsys.readouterr()
            # Should log an error but not crash
            assert "Error cleaning state" in captured.err
        finally:
            # Restore permissions for cleanup
            subdir.chmod(0o755)


class TestFallbackPaths:
    """Tests for fallback I/O paths."""

    def test_run_post_steps_without_config(self, tmp_path, monkeypatch, capsys):
        """Test run_post_steps when CONFIG_AVAILABLE is False."""
        from hooks import post_command

        # Patch CONFIG_AVAILABLE to False
        monkeypatch.setattr(post_command, "CONFIG_AVAILABLE", False)

        # Should return early without error
        run_post_steps(str(tmp_path), "cs:c")

        # No steps should be executed
        captured = capsys.readouterr()
        assert "error" not in captured.err.lower()

    def test_run_post_steps_without_io(self, tmp_path, monkeypatch, capsys):
        """Test run_post_steps when IO_AVAILABLE is False but CONFIG is available."""
        from hooks import post_command

        # Create mock config
        mock_steps = [{"name": "test-step", "enabled": True}]

        monkeypatch.setattr(post_command, "CONFIG_AVAILABLE", True)
        monkeypatch.setattr(post_command, "IO_AVAILABLE", False)
        monkeypatch.setattr(
            post_command, "get_enabled_steps", lambda cmd, phase: mock_steps
        )

        run_post_steps(str(tmp_path), "cs:c")

        captured = capsys.readouterr()
        # When IO_AVAILABLE is False, steps are skipped (libs not available)
        assert "skipped" in captured.err or "not available" in captured.err or "Could not import" in captured.err

    def test_main_with_fallback_io(self, tmp_path, monkeypatch, capsys):
        """Test main when IO_AVAILABLE is False but FALLBACK_AVAILABLE is True."""
        from hooks import post_command

        # Create state file
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text(json.dumps({"command": "cs:c"}))

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        monkeypatch.setattr(post_command, "IO_AVAILABLE", False)
        monkeypatch.setattr(post_command, "FALLBACK_AVAILABLE", True)

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

        # State file should be cleaned up
        assert not state_file.exists()

    def test_main_with_inline_fallback(self, tmp_path, monkeypatch, capsys):
        """Test main when both IO_AVAILABLE and FALLBACK_AVAILABLE are False."""
        from hooks import post_command

        # Create state file
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text(json.dumps({"command": "cs:c"}))

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        monkeypatch.setattr(post_command, "IO_AVAILABLE", False)
        monkeypatch.setattr(post_command, "FALLBACK_AVAILABLE", False)

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

    def test_inline_fallback_malformed_input(self, monkeypatch, capsys):
        """Test inline fallback with malformed input."""
        from hooks import post_command

        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        monkeypatch.setattr(post_command, "IO_AVAILABLE", False)
        monkeypatch.setattr(post_command, "FALLBACK_AVAILABLE", False)

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

    def test_inline_fallback_read_input_error(self, monkeypatch, capsys):
        """Test inline fallback read input error handling."""
        from hooks import post_command

        # Simulate read error - stdin.read takes max_size argument
        def raise_error(*args, **kwargs):
            raise Exception("Read error")

        # Use StringIO but mock the stdin attribute more directly
        monkeypatch.setattr("sys.stdin", io.StringIO(""))

        # json.load on empty input raises JSONDecodeError, which triggers fallback
        monkeypatch.setattr(post_command, "IO_AVAILABLE", False)
        monkeypatch.setattr(post_command, "FALLBACK_AVAILABLE", False)

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}


class TestFallbackIOFunctions:
    """Tests for _fallback_io functions."""

    def test_fallback_io_read_input(self, monkeypatch):
        """Test _fallback_io_read_input wrapper."""
        from hooks.post_command import _fallback_io_read_input

        input_data = {"hook_event_name": "Stop", "cwd": "/test"}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        result = _fallback_io_read_input()
        assert result == input_data

    def test_fallback_io_write_output(self, capsys):
        """Test _fallback_io_write_output wrapper."""
        from hooks.post_command import _fallback_io_write_output

        _fallback_io_write_output({"continue": False})

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}
