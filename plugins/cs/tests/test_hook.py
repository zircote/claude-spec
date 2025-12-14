"""
Tests for the prompt capture hook.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

# Add parent directory for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

# Import after path setup
from hooks.prompt_capture import (
    MAX_LOG_ENTRY_SIZE,
    MAX_PROMPT_LENGTH,
    detect_command,
    find_enabled_project_dir,
    generate_session_id,
    is_logging_enabled,
    main,
    pass_through,
    read_input,
    truncate_content,
    write_output,
)


class TestFindEnabledProjectDir(unittest.TestCase):
    """Tests for find_enabled_project_dir function."""

    def setUp(self):
        """Create temporary directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.active_dir = os.path.join(self.temp_dir, "docs", "spec", "active")
        os.makedirs(self.active_dir)

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_no_active_dir(self):
        """Should return None if active dir doesn't exist."""
        empty_dir = tempfile.mkdtemp()
        try:
            result = find_enabled_project_dir(empty_dir)
            self.assertIsNone(result)
        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)

    def test_no_enabled_projects(self):
        """Should return None if no projects have logging enabled."""
        # Create a project without the marker
        project_dir = os.path.join(self.active_dir, "2025-01-01-test-project")
        os.makedirs(project_dir)

        result = find_enabled_project_dir(self.temp_dir)
        self.assertIsNone(result)

    def test_finds_enabled_project(self):
        """Should find project when .prompt-log-enabled marker exists at project root."""
        # Create the marker file at project root (temp_dir)
        marker_path = os.path.join(self.temp_dir, ".prompt-log-enabled")
        open(marker_path, "w").close()

        result = find_enabled_project_dir(self.temp_dir)
        self.assertEqual(result, self.temp_dir)

    def test_empty_cwd(self):
        """Should return None for empty cwd."""
        result = find_enabled_project_dir("")
        self.assertIsNone(result)

    def test_oserror_in_listdir(self):
        """Should return None on OSError during directory listing."""
        with patch("os.listdir", side_effect=OSError("Permission denied")):
            result = find_enabled_project_dir(self.temp_dir)
            self.assertIsNone(result)


class TestIsLoggingEnabled(unittest.TestCase):
    """Tests for is_logging_enabled function."""

    def setUp(self):
        """Create temporary directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.active_dir = os.path.join(self.temp_dir, "docs", "spec", "active")
        os.makedirs(self.active_dir)

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enabled_when_marker_exists(self):
        """Should return True when marker file exists at project root."""
        # Create the marker at project root (temp_dir)
        open(os.path.join(self.temp_dir, ".prompt-log-enabled"), "w").close()

        self.assertTrue(is_logging_enabled(self.temp_dir))

    def test_disabled_when_no_marker(self):
        """Should return False when no marker file exists."""
        project_dir = os.path.join(self.active_dir, "test-project")
        os.makedirs(project_dir)

        self.assertFalse(is_logging_enabled(self.temp_dir))


class TestTruncateContent(unittest.TestCase):
    """Tests for truncate_content function."""

    def test_short_content_unchanged(self):
        """Short content should not be truncated."""
        content = "Short text"
        result = truncate_content(content)
        self.assertEqual(result, content)

    def test_long_content_truncated(self):
        """Long content should be truncated with notice."""
        content = "x" * (MAX_LOG_ENTRY_SIZE + 1000)
        result = truncate_content(content)

        self.assertLess(len(result), len(content))
        self.assertIn("TRUNCATED", result)

    def test_custom_max_length(self):
        """Should respect custom max length."""
        content = "a" * 200
        result = truncate_content(content, max_length=100)

        self.assertLessEqual(len(result), 100)
        self.assertIn("TRUNCATED", result)


class TestDetectCommand(unittest.TestCase):
    """Tests for detect_command function."""

    def test_detects_spec_command(self):
        """Should detect /spec: commands."""
        self.assertEqual(detect_command("/spec:p test"), "/spec:p")
        self.assertEqual(detect_command("/spec:i project-id"), "/spec:i")
        self.assertEqual(detect_command("/spec:c"), "/spec:c")

    def test_no_command(self):
        """Should return None for non-command prompts."""
        self.assertIsNone(detect_command("Just a regular prompt"))
        self.assertIsNone(detect_command(""))

    def test_other_commands_not_detected(self):
        """Should not detect non-spec commands."""
        self.assertIsNone(detect_command("/help"))
        self.assertIsNone(detect_command("/git:status"))

    def test_whitespace_handling(self):
        """Should handle leading/trailing whitespace."""
        self.assertEqual(detect_command("  /spec:p test  "), "/spec:p")


class TestGenerateSessionId(unittest.TestCase):
    """Tests for generate_session_id function."""

    def test_format(self):
        """Session ID should have correct format."""
        session_id = generate_session_id()
        self.assertTrue(session_id.startswith("hook-"))
        self.assertEqual(len(session_id), 17)  # "hook-" + 12 hex chars

    def test_uniqueness(self):
        """Session IDs should be unique."""
        ids = [generate_session_id() for _ in range(100)]
        self.assertEqual(len(ids), len(set(ids)))


class TestPassThrough(unittest.TestCase):
    """Tests for pass_through function."""

    def test_returns_approve(self):
        """Should always return approve decision."""
        result = pass_through()
        self.assertEqual(result["decision"], "approve")


class TestReadInput(unittest.TestCase):
    """Tests for read_input function."""

    def test_valid_json(self):
        """Should parse valid JSON from stdin."""
        input_data = {"prompt": "test", "cwd": "/test"}
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            result = read_input()
        self.assertEqual(result, input_data)

    def test_invalid_json(self):
        """Should return None for invalid JSON."""
        with patch("sys.stdin", StringIO("not valid json")):
            with patch("sys.stderr", new_callable=StringIO):
                result = read_input()
        self.assertIsNone(result)

    def test_read_error(self):
        """Should return None on read error."""
        with patch("sys.stdin.read", side_effect=OSError("Read error")):
            with patch("sys.stderr", new_callable=StringIO):
                result = read_input()
        self.assertIsNone(result)


class TestWriteOutput(unittest.TestCase):
    """Tests for write_output function."""

    def test_writes_json(self):
        """Should write JSON to stdout."""
        response = {"decision": "approve"}
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            write_output(response)
        self.assertEqual(json.loads(mock_stdout.getvalue().strip()), response)

    def test_handles_write_error(self):
        """Should handle write errors gracefully."""
        # Create an object that can't be serialized
        with patch("json.dumps", side_effect=Exception("Serialization error")):
            with patch("sys.stderr", new_callable=StringIO):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    write_output({"test": "data"})
        # Should fall back to hardcoded approve
        self.assertIn("approve", mock_stdout.getvalue())


class TestMain(unittest.TestCase):
    """Tests for main function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.active_dir = os.path.join(self.temp_dir, "docs", "spec", "active")
        self.project_dir = os.path.join(self.active_dir, "test-project")
        os.makedirs(self.project_dir)
        # Enable logging at project root (temp_dir), not in spec project dir
        open(os.path.join(self.temp_dir, ".prompt-log-enabled"), "w").close()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_malformed_input(self):
        """Should approve and return for malformed input."""
        with patch("sys.stdin", StringIO("not json")):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO):
                    main()
        output = json.loads(mock_stdout.getvalue().strip())
        self.assertEqual(output["decision"], "approve")

    def test_empty_prompt(self):
        """Should approve and return for empty prompt."""
        input_data = {"prompt": "", "cwd": self.temp_dir, "session_id": "test"}
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
        output = json.loads(mock_stdout.getvalue().strip())
        self.assertEqual(output["decision"], "approve")

    def test_whitespace_only_prompt(self):
        """Should approve and return for whitespace-only prompt."""
        input_data = {"prompt": "   \n\t  ", "cwd": self.temp_dir, "session_id": "test"}
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
        output = json.loads(mock_stdout.getvalue().strip())
        self.assertEqual(output["decision"], "approve")

    def test_logging_disabled(self):
        """Should approve without logging when disabled."""
        # Remove the marker to disable logging
        os.remove(os.path.join(self.temp_dir, ".prompt-log-enabled"))

        input_data = {
            "prompt": "test prompt",
            "cwd": self.temp_dir,
            "session_id": "test",
        }
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
        output = json.loads(mock_stdout.getvalue().strip())
        self.assertEqual(output["decision"], "approve")

    def test_very_long_prompt_truncated(self):
        """Should truncate extremely long prompts."""
        long_prompt = "x" * (MAX_PROMPT_LENGTH + 1000)
        input_data = {"prompt": long_prompt, "cwd": self.temp_dir, "session_id": "test"}
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
        output = json.loads(mock_stdout.getvalue().strip())
        self.assertEqual(output["decision"], "approve")

    def test_successful_logging(self):
        """Should log prompt when enabled."""
        input_data = {
            "prompt": "test prompt for logging",
            "cwd": self.temp_dir,
            "session_id": "test-session-123",
        }
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()

        output = json.loads(mock_stdout.getvalue().strip())
        self.assertEqual(output["decision"], "approve")

        # Check log file was created at project root (temp_dir)
        log_path = os.path.join(self.temp_dir, ".prompt-log.json")
        self.assertTrue(os.path.exists(log_path))

        with open(log_path) as f:
            log_entry = json.loads(f.readline())
        self.assertEqual(log_entry["content"], "test prompt for logging")
        self.assertEqual(log_entry["session_id"], "test-session-123")

    def test_generates_session_id_if_missing(self):
        """Should generate session ID if not provided."""
        input_data = {"prompt": "test", "cwd": self.temp_dir}
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        log_path = os.path.join(self.temp_dir, ".prompt-log.json")
        with open(log_path) as f:
            log_entry = json.loads(f.readline())
        self.assertTrue(log_entry["session_id"].startswith("hook-"))

    def test_detects_spec_command(self):
        """Should detect and log /spec: commands."""
        input_data = {
            "prompt": "/spec:p new project idea",
            "cwd": self.temp_dir,
            "session_id": "test",
        }
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        log_path = os.path.join(self.temp_dir, ".prompt-log.json")
        with open(log_path) as f:
            log_entry = json.loads(f.readline())
        self.assertEqual(log_entry["command"], "/spec:p")

    def test_uses_user_prompt_fallback(self):
        """Should fall back to user_prompt field if prompt not present."""
        input_data = {
            "user_prompt": "fallback test",
            "cwd": self.temp_dir,
            "session_id": "test",
        }
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        log_path = os.path.join(self.temp_dir, ".prompt-log.json")
        with open(log_path) as f:
            log_entry = json.loads(f.readline())
        self.assertEqual(log_entry["content"], "fallback test")

    def test_filters_not_available(self):
        """Should approve without logging when filters are not available."""
        input_data = {
            "prompt": "test prompt",
            "cwd": self.temp_dir,
            "session_id": "test",
        }
        # Patch FILTERS_AVAILABLE to False
        with patch("hooks.prompt_capture.FILTERS_AVAILABLE", False):
            with patch("sys.stdin", StringIO(json.dumps(input_data))):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    main()

        output = json.loads(mock_stdout.getvalue().strip())
        self.assertEqual(output["decision"], "approve")


if __name__ == "__main__":
    unittest.main()
