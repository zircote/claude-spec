"""
Tests for the prompt capture hook.
"""

import os
import shutil
import sys
import tempfile
import unittest

# Add parent directory for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

# Import after path setup
from hooks.prompt_capture import (
    find_enabled_project_dir,
    is_logging_enabled,
    truncate_content,
    detect_command,
    generate_session_id,
    pass_through,
    MAX_LOG_ENTRY_SIZE
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
        """Should find project with .prompt-log-enabled marker."""
        project_dir = os.path.join(self.active_dir, "2025-01-01-test-project")
        os.makedirs(project_dir)

        # Create the marker file
        marker_path = os.path.join(project_dir, ".prompt-log-enabled")
        open(marker_path, "w").close()

        result = find_enabled_project_dir(self.temp_dir)
        self.assertEqual(result, project_dir)

    def test_empty_cwd(self):
        """Should return None for empty cwd."""
        result = find_enabled_project_dir("")
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
        """Should return True when marker file exists."""
        project_dir = os.path.join(self.active_dir, "test-project")
        os.makedirs(project_dir)
        open(os.path.join(project_dir, ".prompt-log-enabled"), "w").close()

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


if __name__ == "__main__":
    unittest.main()
