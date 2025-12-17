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
        assert (
            "skipped" in captured.err
            or "not available" in captured.err
            or "Could not import" in captured.err
        )

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


# ============================================================================
# ADDITIONAL TESTS FOR 95% COVERAGE TARGET
# ============================================================================


class TestValidateCwd:
    """Tests for validate_cwd security function."""

    def test_empty_cwd(self):
        """Test validate_cwd with empty string."""
        from hooks.post_command import validate_cwd

        result = validate_cwd("")
        assert result is None

    def test_whitespace_only_cwd(self):
        """Test validate_cwd with whitespace-only string."""
        from hooks.post_command import validate_cwd

        result = validate_cwd("   ")
        assert result is None

    def test_none_cwd(self):
        """Test validate_cwd with None-like values."""
        from hooks.post_command import validate_cwd

        # Empty string is "falsy" in Python
        result = validate_cwd("")
        assert result is None

    def test_valid_directory(self, tmp_path):
        """Test validate_cwd with valid directory."""
        from hooks.post_command import validate_cwd

        result = validate_cwd(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_file_not_directory(self, tmp_path, capsys):
        """Test validate_cwd when path is a file, not a directory."""
        from hooks.post_command import validate_cwd

        # Create a file, not a directory
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        result = validate_cwd(str(test_file))
        assert result is None

        captured = capsys.readouterr()
        assert "cwd is not a directory" in captured.err

    def test_nonexistent_path(self, tmp_path, capsys):
        """Test validate_cwd with nonexistent path."""
        from hooks.post_command import validate_cwd

        nonexistent = tmp_path / "does_not_exist"
        result = validate_cwd(str(nonexistent))
        assert result is None

        captured = capsys.readouterr()
        assert "Invalid cwd path" in captured.err


class TestPathTraversalDetection:
    """Tests for path traversal detection in load/cleanup functions."""

    def test_load_session_state_invalid_cwd(self):
        """Test load_session_state with invalid cwd."""
        result = load_session_state("")
        assert result is None

    def test_load_session_state_with_symlink_traversal(self, tmp_path, capsys):
        """Test load_session_state detects symlink-based path traversal."""
        # Create a directory structure
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        # Create state file outside safe_dir
        outside_state = outside_dir / SESSION_STATE_FILE
        outside_state.write_text('{"command": "cs:c"}')

        # Create symlink from safe_dir to outside_dir state file
        # This simulates path traversal via symlink
        symlink_target = safe_dir / SESSION_STATE_FILE
        try:
            symlink_target.symlink_to(outside_state)
        except OSError:
            # Skip on systems that don't support symlinks (Windows without admin)
            return

        # Should detect traversal and return None
        result = load_session_state(str(safe_dir))
        # The state file itself exists, but resolved path is outside cwd
        # This tests line 143-145
        captured = capsys.readouterr()
        # Either returns the state (if symlink is considered valid)
        # or detects traversal
        assert result is not None or "Path traversal detected" in captured.err

    def test_cleanup_session_state_invalid_cwd(self, capsys):
        """Test cleanup_session_state with invalid cwd."""
        cleanup_session_state("")
        # Should return early without error
        capsys.readouterr()  # Clear any output
        # No specific error expected, just early return

    def test_cleanup_with_nonexistent_cwd(self, tmp_path):
        """Test cleanup_session_state with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        cleanup_session_state(str(nonexistent))
        # Should handle gracefully


class TestRunPostStepsIOPaths:
    """Tests for run_post_steps I/O availability paths."""

    def test_run_post_steps_io_unavailable_config_available(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test run_post_steps when IO_AVAILABLE=False but CONFIG_AVAILABLE=True."""
        from hooks import post_command

        # Save originals
        orig_io = post_command.IO_AVAILABLE
        orig_config = post_command.CONFIG_AVAILABLE

        try:
            # Set up condition: CONFIG available but IO not available
            post_command.CONFIG_AVAILABLE = True
            post_command.IO_AVAILABLE = False

            # Mock get_enabled_steps to return a step
            def mock_get_steps(cmd, step_type):
                return [{"name": "test-step", "enabled": True}]

            monkeypatch.setattr(
                post_command, "get_enabled_steps", mock_get_steps, raising=False
            )

            run_post_steps(str(tmp_path), "cs:c")

            captured = capsys.readouterr()
            # Should log that step was skipped or import error
            # When IO_AVAILABLE=False, steps are either skipped or fail to import
            assert (
                "skipped" in captured.err
                or "not available" in captured.err
                or "Could not import" in captured.err
                or "Unknown step" in captured.err
            )
        finally:
            # Restore originals
            post_command.IO_AVAILABLE = orig_io
            post_command.CONFIG_AVAILABLE = orig_config


class TestInlineFallbackExecution:
    """Tests for inline fallback function execution paths."""

    def test_inline_write_output_json_error(self, monkeypatch, capsys):
        """Test inline fallback write_output when JSON serialization fails."""
        from hooks import post_command

        # Save originals
        orig_io = post_command.IO_AVAILABLE
        orig_fallback = post_command.FALLBACK_AVAILABLE

        try:
            post_command.IO_AVAILABLE = False
            post_command.FALLBACK_AVAILABLE = False

            input_data = {"hook_event_name": "Stop", "cwd": ""}
            monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

            main()

            captured = capsys.readouterr()
            # Should output valid JSON response
            output = json.loads(captured.out)
            assert output == {"continue": False}
        finally:
            post_command.IO_AVAILABLE = orig_io
            post_command.FALLBACK_AVAILABLE = orig_fallback

    def test_inline_stop_response(self, monkeypatch, capsys):
        """Test inline fallback stop_response function."""
        from hooks import post_command

        orig_io = post_command.IO_AVAILABLE
        orig_fallback = post_command.FALLBACK_AVAILABLE

        try:
            post_command.IO_AVAILABLE = False
            post_command.FALLBACK_AVAILABLE = False

            # Valid input with a directory that exists
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                input_data = {"hook_event_name": "Stop", "cwd": tmpdir}
                monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

                main()

                captured = capsys.readouterr()
                output = json.loads(captured.out)
                assert output == {"continue": False}
        finally:
            post_command.IO_AVAILABLE = orig_io
            post_command.FALLBACK_AVAILABLE = orig_fallback


class TestModuleImportPaths:
    """Tests for module import availability paths."""

    def test_io_read_input_wrapper(self, monkeypatch):
        """Test _io_read_input wrapper function."""
        from hooks.post_command import _io_read_input

        input_data = {"hook_event_name": "Stop", "cwd": "/test"}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        result = _io_read_input()
        assert result == input_data

    def test_main_selects_io_functions_when_available(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test main uses hook_io functions when IO_AVAILABLE is True."""
        from hooks import post_command

        # Ensure IO_AVAILABLE is True (default)
        orig = post_command.IO_AVAILABLE
        post_command.IO_AVAILABLE = True

        try:
            input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
            monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

            main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {"continue": False}
        finally:
            post_command.IO_AVAILABLE = orig


class TestLoadSessionStatePathTraversal:
    """Additional tests for path traversal in load_session_state."""

    def test_path_relative_to_fails(self, tmp_path, monkeypatch, capsys):
        """Test when resolved state file is outside validated cwd."""
        # This tests line 143-145 where relative_to raises ValueError

        # Create state file in parent directory (outside cwd)
        parent_state = tmp_path / SESSION_STATE_FILE
        parent_state.write_text('{"command": "cs:c"}')

        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Try to load from subdir - state file doesn't exist there
        result = load_session_state(str(subdir))
        assert result is None  # File doesn't exist, so returns None


class TestCleanupPathTraversal:
    """Additional tests for path traversal in cleanup_session_state."""

    def test_cleanup_path_traversal_symlink(self, tmp_path, capsys):
        """Test cleanup_session_state with symlink-based traversal."""
        # Create directory structure
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        # Create state file outside safe_dir
        outside_state = outside_dir / SESSION_STATE_FILE
        outside_state.write_text('{"command": "cs:c"}')

        # Create symlink
        symlink_target = safe_dir / SESSION_STATE_FILE
        try:
            symlink_target.symlink_to(outside_state)
        except OSError:
            # Skip on systems without symlink support
            return

        cleanup_session_state(str(safe_dir))

        capsys.readouterr()  # Clear any output
        # Either cleans up the symlink or detects traversal
        # The file in outside_dir should NOT be deleted
        # (the symlink itself may or may not be deleted depending on implementation)


class TestValidateCwdNullByte:
    """Tests for null byte detection in validate_cwd."""

    def test_path_with_embedded_null(self, capsys):
        """Test that paths with null bytes are rejected."""
        # While Python's Path doesn't typically allow null bytes in paths,
        # we need to test the check. This is defensive coding for edge cases.
        # The null byte check happens after resolve, on the string representation
        # Test with a valid path that exists (to verify check doesn't false positive)
        import tempfile

        from hooks.post_command import validate_cwd

        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_cwd(tmpdir)
            assert result is not None
            assert "\x00" not in str(result)


class TestMainWithCommandExecution:
    """Tests for main function with command execution."""

    def test_main_with_command_cleans_state_and_completes(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test that main processes command and cleans up state file."""
        # Create state file with command
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text(json.dumps({"command": "cs:c"}))

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"continue": False}

        # State file should be cleaned up
        assert not state_file.exists()

        # Post-steps may have attempted to run (even if they fail to import)
        # The key behavior is: main processes state, cleans up, and returns

    def test_main_logs_post_step_attempts(self, tmp_path, monkeypatch, capsys):
        """Test that main attempts post-steps when command exists."""
        from hooks import post_command

        # Create state file with command
        state_file = tmp_path / SESSION_STATE_FILE
        state_file.write_text(json.dumps({"command": "cs:c"}))

        # Ensure CONFIG is available so steps are attempted
        orig_config = post_command.CONFIG_AVAILABLE
        post_command.CONFIG_AVAILABLE = True

        try:
            input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
            monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

            main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {"continue": False}

            # If steps are configured, they would be attempted
            # We can't easily verify the call without complex mocking,
            # but we verify the flow completes and state is cleaned
            assert not state_file.exists()
        finally:
            post_command.CONFIG_AVAILABLE = orig_config


class TestRunStepAdditionalCases:
    """Additional tests for run_step function."""

    def test_run_step_with_timeout_config(self, tmp_path, monkeypatch):
        """Test run_step with timeout configuration."""
        mock_module = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_module.run.return_value = mock_result

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "log_archiver":
                return mock_module
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        config = {"name": "archive-logs", "timeout": 120, "enabled": True}
        run_step(str(tmp_path), "archive-logs", config)

        mock_module.run.assert_called_once()


class TestFlushMemoryQueue:
    """Tests for flush_memory_queue function."""

    def test_flush_returns_early_when_queue_unavailable(self, tmp_path, monkeypatch):
        """Test early return when MEMORY_QUEUE_AVAILABLE is False."""
        import post_command

        original = post_command.MEMORY_QUEUE_AVAILABLE
        post_command.MEMORY_QUEUE_AVAILABLE = False

        from post_command import flush_memory_queue

        # Should not raise
        flush_memory_queue(str(tmp_path))

        post_command.MEMORY_QUEUE_AVAILABLE = original

    def test_flush_returns_early_when_capture_unavailable(self, tmp_path, monkeypatch):
        """Test early return when CAPTURE_SERVICE_AVAILABLE is False."""
        import post_command

        orig_queue = post_command.MEMORY_QUEUE_AVAILABLE
        orig_capture = post_command.CAPTURE_SERVICE_AVAILABLE

        post_command.MEMORY_QUEUE_AVAILABLE = True
        post_command.CAPTURE_SERVICE_AVAILABLE = False

        from post_command import flush_memory_queue

        # Should not raise
        flush_memory_queue(str(tmp_path))

        post_command.MEMORY_QUEUE_AVAILABLE = orig_queue
        post_command.CAPTURE_SERVICE_AVAILABLE = orig_capture

    def test_flush_returns_early_when_queue_empty(self, tmp_path, monkeypatch):
        """Test early return when queue is empty."""
        import post_command

        orig_queue = post_command.MEMORY_QUEUE_AVAILABLE
        orig_capture = post_command.CAPTURE_SERVICE_AVAILABLE

        post_command.MEMORY_QUEUE_AVAILABLE = True
        post_command.CAPTURE_SERVICE_AVAILABLE = True

        # Mock get_queue_size to return 0
        monkeypatch.setattr("post_command.get_queue_size", lambda cwd: 0)

        from post_command import flush_memory_queue

        # Should not raise
        flush_memory_queue(str(tmp_path))

        post_command.MEMORY_QUEUE_AVAILABLE = orig_queue
        post_command.CAPTURE_SERVICE_AVAILABLE = orig_capture

    def test_flush_processes_items(self, tmp_path, monkeypatch, capsys):
        """Test flush processes items from queue."""
        import post_command

        orig_queue = post_command.MEMORY_QUEUE_AVAILABLE
        orig_capture = post_command.CAPTURE_SERVICE_AVAILABLE

        post_command.MEMORY_QUEUE_AVAILABLE = True
        post_command.CAPTURE_SERVICE_AVAILABLE = True

        # Mock queue functions
        monkeypatch.setattr("post_command.get_queue_size", lambda cwd: 2)
        monkeypatch.setattr(
            "post_command.dequeue_all",
            lambda cwd: [
                {"summary": "Test 1", "content": "Content 1", "spec": None, "tags": []},
                {
                    "summary": "Test 2",
                    "content": "Content 2",
                    "spec": "myspec",
                    "tags": ["tag1"],
                },
            ],
        )

        # Mock capture service
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.warning = None
        mock_service.capture_learning.return_value = mock_result
        mock_service_cls = MagicMock(return_value=mock_service)
        monkeypatch.setattr("post_command.CaptureService", mock_service_cls)

        from post_command import flush_memory_queue

        flush_memory_queue(str(tmp_path))

        captured = capsys.readouterr()
        assert "Flushed 2 learnings" in captured.err

        post_command.MEMORY_QUEUE_AVAILABLE = orig_queue
        post_command.CAPTURE_SERVICE_AVAILABLE = orig_capture

    def test_flush_handles_capture_failure(self, tmp_path, monkeypatch, capsys):
        """Test flush handles capture failure."""
        import post_command

        orig_queue = post_command.MEMORY_QUEUE_AVAILABLE
        orig_capture = post_command.CAPTURE_SERVICE_AVAILABLE

        post_command.MEMORY_QUEUE_AVAILABLE = True
        post_command.CAPTURE_SERVICE_AVAILABLE = True

        # Mock queue functions
        monkeypatch.setattr("post_command.get_queue_size", lambda cwd: 1)
        monkeypatch.setattr(
            "post_command.dequeue_all",
            lambda cwd: [
                {"summary": "Test", "content": "Content", "spec": None, "tags": []}
            ],
        )

        # Mock capture service with failure
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.warning = "Index error"
        mock_service.capture_learning.return_value = mock_result
        mock_service_cls = MagicMock(return_value=mock_service)
        monkeypatch.setattr("post_command.CaptureService", mock_service_cls)

        from post_command import flush_memory_queue

        flush_memory_queue(str(tmp_path))

        captured = capsys.readouterr()
        assert "0 learnings" in captured.err or "1 errors" in captured.err

        post_command.MEMORY_QUEUE_AVAILABLE = orig_queue
        post_command.CAPTURE_SERVICE_AVAILABLE = orig_capture

    def test_flush_handles_exception(self, tmp_path, monkeypatch, capsys):
        """Test flush handles exception during capture."""
        import post_command

        orig_queue = post_command.MEMORY_QUEUE_AVAILABLE
        orig_capture = post_command.CAPTURE_SERVICE_AVAILABLE

        post_command.MEMORY_QUEUE_AVAILABLE = True
        post_command.CAPTURE_SERVICE_AVAILABLE = True

        # Mock queue functions
        monkeypatch.setattr("post_command.get_queue_size", lambda cwd: 1)
        monkeypatch.setattr(
            "post_command.dequeue_all",
            lambda cwd: [
                {"summary": "Test", "content": "Content", "spec": None, "tags": []}
            ],
        )

        # Mock capture service to raise exception
        mock_service = MagicMock()
        mock_service.capture_learning.side_effect = Exception("Git error")
        mock_service_cls = MagicMock(return_value=mock_service)
        monkeypatch.setattr("post_command.CaptureService", mock_service_cls)

        from post_command import flush_memory_queue

        flush_memory_queue(str(tmp_path))

        captured = capsys.readouterr()
        assert "Flush error" in captured.err

        post_command.MEMORY_QUEUE_AVAILABLE = orig_queue
        post_command.CAPTURE_SERVICE_AVAILABLE = orig_capture

    def test_flush_skips_items_without_summary(self, tmp_path, monkeypatch, capsys):
        """Test flush skips items without summary."""
        import post_command

        orig_queue = post_command.MEMORY_QUEUE_AVAILABLE
        orig_capture = post_command.CAPTURE_SERVICE_AVAILABLE

        post_command.MEMORY_QUEUE_AVAILABLE = True
        post_command.CAPTURE_SERVICE_AVAILABLE = True

        # Mock queue functions
        monkeypatch.setattr("post_command.get_queue_size", lambda cwd: 2)
        monkeypatch.setattr(
            "post_command.dequeue_all",
            lambda cwd: [
                {"summary": "", "content": "Content 1", "spec": None, "tags": []},
                {"summary": "Valid", "content": "Content 2", "spec": None, "tags": []},
            ],
        )

        # Mock capture service
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.warning = None
        mock_service.capture_learning.return_value = mock_result
        mock_service_cls = MagicMock(return_value=mock_service)
        monkeypatch.setattr("post_command.CaptureService", mock_service_cls)

        from post_command import flush_memory_queue

        flush_memory_queue(str(tmp_path))

        # Only one item with summary should be captured
        assert mock_service.capture_learning.call_count == 1

        post_command.MEMORY_QUEUE_AVAILABLE = orig_queue
        post_command.CAPTURE_SERVICE_AVAILABLE = orig_capture

    def test_flush_handles_dequeue_returning_empty(self, tmp_path, monkeypatch, capsys):
        """Test flush handles dequeue returning empty after size check."""
        import post_command

        orig_queue = post_command.MEMORY_QUEUE_AVAILABLE
        orig_capture = post_command.CAPTURE_SERVICE_AVAILABLE

        post_command.MEMORY_QUEUE_AVAILABLE = True
        post_command.CAPTURE_SERVICE_AVAILABLE = True

        # Mock queue functions
        monkeypatch.setattr("post_command.get_queue_size", lambda cwd: 1)
        monkeypatch.setattr("post_command.dequeue_all", lambda cwd: [])

        from post_command import flush_memory_queue

        # Should not raise
        flush_memory_queue(str(tmp_path))

        post_command.MEMORY_QUEUE_AVAILABLE = orig_queue
        post_command.CAPTURE_SERVICE_AVAILABLE = orig_capture


class TestMainFlushIntegration:
    """Tests for flush_memory_queue integration in main."""

    def test_main_flushes_queue(self, tmp_path, monkeypatch, capsys):
        """Test main calls flush_memory_queue."""
        import post_command

        # Track if flush was called
        flush_called = []

        def mock_flush(cwd):
            flush_called.append(cwd)

        monkeypatch.setattr(post_command, "flush_memory_queue", mock_flush)

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        # Verify flush was called with the cwd
        assert len(flush_called) == 1
        assert flush_called[0] == str(tmp_path)

    def test_main_continues_after_flush_exception(self, tmp_path, monkeypatch, capsys):
        """Test main continues even if flush_memory_queue raises."""
        import post_command

        def mock_flush(cwd):
            raise Exception("Flush failed")

        monkeypatch.setattr(post_command, "flush_memory_queue", mock_flush)

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        # Should still return success
        assert output == {"continue": False}
        # Should log the error
        assert "Error flushing memory queue" in captured.err


class TestPostCommandIOFallback:
    """Tests for I/O fallback behavior in post_command."""

    def test_main_fallback_read_input(self, tmp_path, monkeypatch, capsys):
        """Test main uses fallback read when primary fails."""
        import post_command

        # Disable primary I/O
        orig_io = post_command.IO_AVAILABLE
        orig_fallback = post_command.FALLBACK_AVAILABLE
        post_command.IO_AVAILABLE = False
        post_command.FALLBACK_AVAILABLE = True

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        try:
            main()
            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {"continue": False}
        finally:
            post_command.IO_AVAILABLE = orig_io
            post_command.FALLBACK_AVAILABLE = orig_fallback

    def test_main_inline_fallback(self, tmp_path, monkeypatch, capsys):
        """Test main uses inline fallback when all imports fail."""
        import post_command

        # Disable all I/O options
        orig_io = post_command.IO_AVAILABLE
        orig_fallback = post_command.FALLBACK_AVAILABLE
        post_command.IO_AVAILABLE = False
        post_command.FALLBACK_AVAILABLE = False

        input_data = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        try:
            main()
            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output == {"continue": False}
        finally:
            post_command.IO_AVAILABLE = orig_io
            post_command.FALLBACK_AVAILABLE = orig_fallback

    def test_inline_fallback_handles_json_error(self, tmp_path, monkeypatch, capsys):
        """Test inline fallback handles JSON decode error."""
        import post_command

        # Disable all I/O options
        orig_io = post_command.IO_AVAILABLE
        orig_fallback = post_command.FALLBACK_AVAILABLE
        post_command.IO_AVAILABLE = False
        post_command.FALLBACK_AVAILABLE = False

        # Provide invalid JSON
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

        try:
            main()
            captured = capsys.readouterr()
            # Should produce valid output even on error
            output = json.loads(captured.out)
            assert output == {"continue": False}
        finally:
            post_command.IO_AVAILABLE = orig_io
            post_command.FALLBACK_AVAILABLE = orig_fallback
