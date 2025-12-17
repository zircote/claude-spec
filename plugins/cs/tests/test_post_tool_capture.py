"""Tests for post_tool_capture hook."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestIsToolCaptureEnabled:
    """Tests for is_tool_capture_enabled function."""

    def test_enabled_by_default(self):
        """Test capture is enabled when no env vars set."""
        from hooks.post_tool_capture import is_tool_capture_enabled

        with patch.dict("os.environ", {}, clear=True):
            with (
                patch("hooks.post_tool_capture.MEMORY_AVAILABLE", True),
                patch(
                    "hooks.post_tool_capture.is_auto_capture_enabled", return_value=True
                ),
            ):
                assert is_tool_capture_enabled() is True

    def test_disabled_by_tool_env_var(self):
        """Test capture disabled by CS_TOOL_CAPTURE_ENABLED=false."""
        from hooks.post_tool_capture import is_tool_capture_enabled

        for value in ["false", "0", "no", "off", "FALSE", "NO"]:
            with patch.dict("os.environ", {"CS_TOOL_CAPTURE_ENABLED": value}):
                assert is_tool_capture_enabled() is False

    def test_disabled_when_auto_capture_disabled(self):
        """Test capture disabled when auto-capture is off."""
        from hooks.post_tool_capture import is_tool_capture_enabled

        with patch.dict("os.environ", {}, clear=True):
            with (
                patch("hooks.post_tool_capture.MEMORY_AVAILABLE", True),
                patch(
                    "hooks.post_tool_capture.is_auto_capture_enabled",
                    return_value=False,
                ),
            ):
                assert is_tool_capture_enabled() is False

    def test_enabled_when_memory_not_available(self):
        """Test capture enabled even if memory module unavailable (fallback)."""
        from hooks.post_tool_capture import is_tool_capture_enabled

        with patch.dict("os.environ", {}, clear=True):
            with patch("hooks.post_tool_capture.MEMORY_AVAILABLE", False):
                # When memory not available, we can't check auto_capture
                # so default to enabled
                assert is_tool_capture_enabled() is True


class TestGetCaptureThreshold:
    """Tests for get_capture_threshold function."""

    def test_default_threshold(self):
        """Test default threshold is returned."""
        from hooks.post_tool_capture import get_capture_threshold

        with patch.dict("os.environ", {}, clear=True):
            assert get_capture_threshold() == 0.6

    def test_custom_threshold(self):
        """Test custom threshold from env var."""
        from hooks.post_tool_capture import get_capture_threshold

        with patch.dict("os.environ", {"CS_CAPTURE_THRESHOLD": "0.8"}):
            assert get_capture_threshold() == 0.8

    def test_invalid_threshold_returns_default(self):
        """Test invalid threshold falls back to default."""
        from hooks.post_tool_capture import get_capture_threshold

        with patch.dict("os.environ", {"CS_CAPTURE_THRESHOLD": "invalid"}):
            assert get_capture_threshold() == 0.6


class TestReadInput:
    """Tests for read_input function."""

    def test_valid_json(self):
        """Test reading valid JSON input."""
        from hooks.post_tool_capture import read_input

        input_data = {"tool_name": "Bash", "cwd": "/tmp"}
        with patch("sys.stdin", io.StringIO(json.dumps(input_data))):
            result = read_input()
            assert result == input_data

    def test_invalid_json_returns_none(self):
        """Test invalid JSON returns None."""
        from hooks.post_tool_capture import read_input

        with patch("sys.stdin", io.StringIO("not json")):
            result = read_input()
            assert result is None

    def test_empty_input_returns_none(self):
        """Test empty input returns None."""
        from hooks.post_tool_capture import read_input

        with patch("sys.stdin", io.StringIO("")):
            result = read_input()
            assert result is None

    def test_io_error_returns_none(self):
        """Test I/O error returns None."""
        from hooks.post_tool_capture import read_input

        mock_stdin = MagicMock()
        mock_stdin.read.side_effect = OSError("read error")
        with patch("sys.stdin", mock_stdin):
            with patch("json.load", side_effect=Exception("load error")):
                result = read_input()
                assert result is None


class TestDetectActiveSpec:
    """Tests for detect_active_spec function."""

    def test_no_spec_dir(self, tmp_path):
        """Test returns None when no spec directory."""
        from hooks.post_tool_capture import detect_active_spec

        result = detect_active_spec(str(tmp_path))
        assert result is None

    def test_empty_spec_dir(self, tmp_path):
        """Test returns None when spec directory is empty."""
        from hooks.post_tool_capture import detect_active_spec

        spec_dir = tmp_path / "docs" / "spec" / "active"
        spec_dir.mkdir(parents=True)

        result = detect_active_spec(str(tmp_path))
        assert result is None

    def test_single_active_spec(self, tmp_path):
        """Test returns slug for single active spec."""
        from hooks.post_tool_capture import detect_active_spec

        spec_dir = tmp_path / "docs" / "spec" / "active" / "2025-12-17-test-feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "README.md").write_text("# Test")

        result = detect_active_spec(str(tmp_path))
        assert result == "test-feature"

    def test_multiple_active_specs_returns_none(self, tmp_path):
        """Test returns None when multiple active specs."""
        from hooks.post_tool_capture import detect_active_spec

        active_dir = tmp_path / "docs" / "spec" / "active"
        for name in ["2025-12-17-spec1", "2025-12-17-spec2"]:
            spec_dir = active_dir / name
            spec_dir.mkdir(parents=True)
            (spec_dir / "README.md").write_text("# Test")

        result = detect_active_spec(str(tmp_path))
        assert result is None

    def test_spec_without_date_prefix(self, tmp_path):
        """Test returns dirname when no date prefix."""
        from hooks.post_tool_capture import detect_active_spec

        spec_dir = tmp_path / "docs" / "spec" / "active" / "my-feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "README.md").write_text("# Test")

        result = detect_active_spec(str(tmp_path))
        assert result == "my-feature"

    def test_permission_error(self, tmp_path):
        """Test handles permission error gracefully."""
        from hooks.post_tool_capture import detect_active_spec

        spec_dir = tmp_path / "docs" / "spec" / "active"
        spec_dir.mkdir(parents=True)

        with patch.object(Path, "iterdir", side_effect=PermissionError("denied")):
            result = detect_active_spec(str(tmp_path))
            assert result is None


class TestGetSessionQueue:
    """Tests for get_session_queue function."""

    def test_creates_queue_when_memory_available(self):
        """Test creates CaptureAccumulator when memory available."""
        import hooks.post_tool_capture as module

        # Reset global state
        module._session_queue = None

        with patch.object(module, "MEMORY_AVAILABLE", True):
            queue = module.get_session_queue()
            assert queue is not None

    def test_returns_none_when_memory_unavailable(self):
        """Test returns None when memory not available."""
        import hooks.post_tool_capture as module

        # Reset global state
        module._session_queue = None

        with patch.object(module, "MEMORY_AVAILABLE", False):
            queue = module.get_session_queue()
            assert queue is None

    def test_returns_same_queue_on_subsequent_calls(self):
        """Test returns same queue instance."""
        import hooks.post_tool_capture as module

        # Reset global state
        module._session_queue = None

        with patch.object(module, "MEMORY_AVAILABLE", True):
            queue1 = module.get_session_queue()
            queue2 = module.get_session_queue()
            assert queue1 is queue2


class TestQueueLearning:
    """Tests for queue_learning function."""

    def test_queue_not_available(self):
        """Test returns False when queue not available."""
        import hooks.post_tool_capture as module

        module._session_queue = None

        with patch.object(module, "MEMORY_AVAILABLE", False):
            mock_learning = MagicMock()
            result = module.queue_learning(mock_learning, "test-spec")
            assert result is False

    def test_successful_queue(self):
        """Test successful learning queue."""
        import hooks.post_tool_capture as module
        from memory.models import CaptureAccumulator

        module._session_queue = CaptureAccumulator()

        mock_learning = MagicMock()
        mock_learning.timestamp = datetime.now(UTC)
        mock_learning.summary = "Test summary"
        mock_learning.to_memory_args.return_value = {
            "insight": "Test insight",
            "tags": ["test"],
        }

        with patch.object(module, "MEMORY_AVAILABLE", True):
            result = module.queue_learning(mock_learning, "test-spec")
            assert result is True
            assert module._session_queue.count == 1

    def test_queue_exception(self):
        """Test handles exception during queue."""
        import hooks.post_tool_capture as module
        from memory.models import CaptureAccumulator

        module._session_queue = CaptureAccumulator()

        mock_learning = MagicMock()
        mock_learning.to_memory_args.side_effect = Exception("fail")

        with patch.object(module, "MEMORY_AVAILABLE", True):
            result = module.queue_learning(mock_learning, "test-spec")
            assert result is False


class TestProcessToolResponse:
    """Tests for process_tool_response function."""

    def test_bash_context(self, tmp_path):
        """Test Bash tool context building."""
        from hooks.post_tool_capture import process_tool_response

        with (
            patch("hooks.post_tool_capture.LearningDetector") as mock_detector_cls,
            patch("hooks.post_tool_capture.extract_learning", return_value=None),
        ):
            mock_detector = MagicMock()
            mock_detector_cls.return_value = mock_detector

            process_tool_response(
                tool_name="Bash",
                tool_input={"command": "ls -la"},
                tool_response={"stdout": "file.txt", "exit_code": 0},
                cwd=str(tmp_path),
            )

            # Verify extract_learning was called
            from hooks.post_tool_capture import extract_learning

            extract_learning.assert_called_once()

    def test_read_context(self, tmp_path):
        """Test Read tool context building."""
        from hooks.post_tool_capture import process_tool_response

        with (
            patch("hooks.post_tool_capture.LearningDetector"),
            patch("hooks.post_tool_capture.extract_learning", return_value=None),
        ):
            process_tool_response(
                tool_name="Read",
                tool_input={"file_path": "/path/to/file.py"},
                tool_response={"content": "file content"},
                cwd=str(tmp_path),
            )

    def test_write_context(self, tmp_path):
        """Test Write tool context building."""
        from hooks.post_tool_capture import process_tool_response

        with (
            patch("hooks.post_tool_capture.LearningDetector"),
            patch("hooks.post_tool_capture.extract_learning", return_value=None),
        ):
            process_tool_response(
                tool_name="Write",
                tool_input={"file_path": "/path/to/file.py"},
                tool_response={"success": True},
                cwd=str(tmp_path),
            )

    def test_edit_context(self, tmp_path):
        """Test Edit tool context building."""
        from hooks.post_tool_capture import process_tool_response

        with (
            patch("hooks.post_tool_capture.LearningDetector"),
            patch("hooks.post_tool_capture.extract_learning", return_value=None),
        ):
            process_tool_response(
                tool_name="Edit",
                tool_input={"file_path": "/path/to/file.py"},
                tool_response={"success": True},
                cwd=str(tmp_path),
            )

    def test_webfetch_context(self, tmp_path):
        """Test WebFetch tool context building."""
        from hooks.post_tool_capture import process_tool_response

        with (
            patch("hooks.post_tool_capture.LearningDetector"),
            patch("hooks.post_tool_capture.extract_learning", return_value=None),
        ):
            process_tool_response(
                tool_name="WebFetch",
                tool_input={"url": "https://example.com/api"},
                tool_response={"content": "response"},
                cwd=str(tmp_path),
            )

    def test_learning_detected_and_queued(self, tmp_path):
        """Test learning is detected and queued."""
        import hooks.post_tool_capture as module
        from memory.models import CaptureAccumulator

        module._session_queue = CaptureAccumulator()

        mock_learning = MagicMock()
        mock_learning.timestamp = datetime.now(UTC)
        mock_learning.summary = "Test"
        mock_learning.category = "error"
        mock_learning.to_memory_args.return_value = {"insight": "x", "tags": []}

        with (
            patch("hooks.post_tool_capture.LearningDetector") as mock_detector_cls,
            patch(
                "hooks.post_tool_capture.extract_learning", return_value=mock_learning
            ),
            patch.object(module, "MEMORY_AVAILABLE", True),
        ):
            mock_detector = MagicMock()
            mock_detector.calculate_score.return_value = 0.8
            mock_detector_cls.return_value = mock_detector

            module.process_tool_response(
                tool_name="Bash",
                tool_input={"command": "make test"},
                tool_response={"stderr": "Error", "exit_code": 1},
                cwd=str(tmp_path),
            )

            assert module._session_queue.count == 1

    def test_slow_detection_logs_warning(self, tmp_path):
        """Test slow detection logs a warning."""
        from hooks.post_tool_capture import process_tool_response

        with (
            patch("hooks.post_tool_capture.LearningDetector"),
            patch("hooks.post_tool_capture.extract_learning", return_value=None),
            patch("time.time") as mock_time,
        ):
            # Simulate 60ms elapsed time
            mock_time.side_effect = [0, 0.06]

            stderr_output = io.StringIO()
            with patch("sys.stderr", stderr_output):
                process_tool_response(
                    tool_name="Bash",
                    tool_input={"command": "ls"},
                    tool_response={},
                    cwd=str(tmp_path),
                )

            # Should log because >50ms
            assert "No learning detected" in stderr_output.getvalue()


class TestMain:
    """Tests for main function."""

    def test_capture_disabled(self):
        """Test exits early when capture disabled."""
        import hooks.post_tool_capture as module

        stderr_output = io.StringIO()
        with (
            patch.object(module, "is_tool_capture_enabled", return_value=False),
            patch("sys.stderr", stderr_output),
        ):
            module.main()

        assert "Tool capture disabled" in stderr_output.getvalue()

    def test_learnings_not_available(self):
        """Test exits early when learnings module unavailable."""
        import hooks.post_tool_capture as module

        stderr_output = io.StringIO()
        with (
            patch.object(module, "is_tool_capture_enabled", return_value=True),
            patch.object(module, "LEARNINGS_AVAILABLE", False),
            patch("sys.stderr", stderr_output),
        ):
            module.main()

        assert "Learnings module not available" in stderr_output.getvalue()

    def test_memory_not_available(self):
        """Test exits early when memory module unavailable."""
        import hooks.post_tool_capture as module

        stderr_output = io.StringIO()
        with (
            patch.object(module, "is_tool_capture_enabled", return_value=True),
            patch.object(module, "LEARNINGS_AVAILABLE", True),
            patch.object(module, "MEMORY_AVAILABLE", False),
            patch("sys.stderr", stderr_output),
        ):
            module.main()

        assert "Memory module not available" in stderr_output.getvalue()

    def test_invalid_input(self):
        """Test handles invalid input gracefully."""
        import hooks.post_tool_capture as module

        with (
            patch.object(module, "is_tool_capture_enabled", return_value=True),
            patch.object(module, "LEARNINGS_AVAILABLE", True),
            patch.object(module, "MEMORY_AVAILABLE", True),
            patch.object(module, "read_input", return_value=None),
        ):
            # Should not raise
            module.main()

    def test_missing_tool_name(self):
        """Test handles missing tool_name."""
        import hooks.post_tool_capture as module

        stderr_output = io.StringIO()
        with (
            patch.object(module, "is_tool_capture_enabled", return_value=True),
            patch.object(module, "LEARNINGS_AVAILABLE", True),
            patch.object(module, "MEMORY_AVAILABLE", True),
            patch.object(module, "read_input", return_value={"cwd": "/tmp"}),
            patch("sys.stderr", stderr_output),
        ):
            module.main()

        assert "Missing tool_name or cwd" in stderr_output.getvalue()

    def test_missing_cwd(self):
        """Test handles missing cwd."""
        import hooks.post_tool_capture as module

        stderr_output = io.StringIO()
        with (
            patch.object(module, "is_tool_capture_enabled", return_value=True),
            patch.object(module, "LEARNINGS_AVAILABLE", True),
            patch.object(module, "MEMORY_AVAILABLE", True),
            patch.object(module, "read_input", return_value={"tool_name": "Bash"}),
            patch("sys.stderr", stderr_output),
        ):
            module.main()

        assert "Missing tool_name or cwd" in stderr_output.getvalue()

    def test_unexpected_exception(self):
        """Test handles unexpected exception gracefully."""
        import hooks.post_tool_capture as module

        stderr_output = io.StringIO()
        with (
            patch.object(module, "is_tool_capture_enabled", return_value=True),
            patch.object(module, "LEARNINGS_AVAILABLE", True),
            patch.object(module, "MEMORY_AVAILABLE", True),
            patch.object(module, "read_input", side_effect=RuntimeError("unexpected")),
            patch("sys.stderr", stderr_output),
        ):
            # Should not raise
            module.main()

        assert "Unexpected error" in stderr_output.getvalue()

    def test_slow_execution_warning(self):
        """Test warns when execution exceeds 100ms."""
        import hooks.post_tool_capture as module

        stderr_output = io.StringIO()
        with (
            patch.object(module, "is_tool_capture_enabled", return_value=False),
            patch("time.time") as mock_time,
            patch("sys.stderr", stderr_output),
        ):
            # Simulate 150ms elapsed time
            mock_time.side_effect = [0, 0.15]
            module.main()

        assert "WARN: Hook took" in stderr_output.getvalue()

    def test_successful_processing(self, tmp_path):
        """Test successful end-to-end processing."""
        import hooks.post_tool_capture as module

        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": {"stdout": "file.txt", "exit_code": 0},
            "cwd": str(tmp_path),
        }

        with (
            patch.object(module, "is_tool_capture_enabled", return_value=True),
            patch.object(module, "LEARNINGS_AVAILABLE", True),
            patch.object(module, "MEMORY_AVAILABLE", True),
            patch.object(module, "read_input", return_value=input_data),
            patch.object(module, "process_tool_response") as mock_process,
        ):
            module.main()

            mock_process.assert_called_once_with(
                tool_name="Bash",
                tool_input={"command": "ls"},
                tool_response={"stdout": "file.txt", "exit_code": 0},
                cwd=str(tmp_path),
            )
