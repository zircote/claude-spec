"""Tests for log_writer module."""

import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# Add parent directory for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from filters.log_entry import LogEntry
from filters.log_writer import (
    PROMPT_LOG_FILENAME,
    PathTraversalError,
    _check_symlink_safety,
    _validate_path,
    append_to_log,
    clear_log,
    get_log_path,
    get_recent_entries,
    log_exists,
    read_log,
)


class TestGetLogPath(unittest.TestCase):
    """Tests for get_log_path function."""

    def test_returns_correct_path(self):
        """Should return path with .prompt-log.json filename."""
        result = get_log_path("/some/project/dir")
        self.assertEqual(str(result), "/some/project/dir/.prompt-log.json")

    def test_uses_constant(self):
        """Should use PROMPT_LOG_FILENAME constant."""
        result = get_log_path("/test")
        self.assertTrue(str(result).endswith(PROMPT_LOG_FILENAME))

    def test_returns_path_object(self):
        """Should return a Path object, not a string."""
        result = get_log_path("/test/path")
        self.assertIsInstance(result, Path)

    def test_accepts_path_object(self):
        """Should accept Path object as input."""
        result = get_log_path(Path("/test/path"))
        self.assertIsInstance(result, Path)
        self.assertEqual(str(result), "/test/path/.prompt-log.json")


class TestPathValidation(unittest.TestCase):
    """Tests for path traversal protection."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_path_allows_valid_subpath(self):
        """Should allow paths within base directory."""
        base = Path(self.temp_dir).resolve()
        target = base / "subdir" / "file.json"
        # Should not raise
        _validate_path(base, target)

    def test_validate_path_blocks_traversal(self):
        """Should block path traversal attempts."""
        base = Path(self.temp_dir).resolve()
        # Create a path that escapes the base
        target = (base / ".." / "etc" / "passwd").resolve()

        with self.assertRaises(PathTraversalError):
            _validate_path(base, target)

    def test_get_log_path_with_traversal_attempt(self):
        """get_log_path should handle paths safely."""
        # Normal path should work
        result = get_log_path(self.temp_dir)
        self.assertTrue(str(result).endswith(PROMPT_LOG_FILENAME))


class TestSymlinkSafety(unittest.TestCase):
    """Tests for symlink attack prevention."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_check_symlink_safety_normal_path(self):
        """Should return True for normal paths."""
        # Create a real file (not a symlink)
        normal_path = Path(self.temp_dir) / "normal_file.txt"
        normal_path.write_text("content")
        self.assertTrue(_check_symlink_safety(normal_path))

    def test_check_symlink_safety_nonexistent_path(self):
        """Should return True for non-existent paths (no symlink)."""
        nonexistent = Path(self.temp_dir) / "does_not_exist.txt"
        self.assertTrue(_check_symlink_safety(nonexistent))

    def test_check_symlink_safety_detects_symlink(self):
        """Should return False for symlinks."""
        # Create a file and a symlink to it
        real_file = Path(self.temp_dir) / "real_file.txt"
        real_file.write_text("content")

        symlink_path = Path(self.temp_dir) / "symlink_file.txt"
        symlink_path.symlink_to(real_file)

        self.assertFalse(_check_symlink_safety(symlink_path))

    def test_append_refuses_symlink_log_file(self):
        """append_to_log should refuse to write when log file is a symlink."""
        # Create a real file that the symlink will point to
        real_file = Path(self.temp_dir) / "other_file.json"
        real_file.write_text("")

        # Create a symlink with the log filename pointing to the real file
        # Both files are in the same directory (no path traversal)
        log_symlink = Path(self.temp_dir) / PROMPT_LOG_FILENAME
        log_symlink.symlink_to(real_file)

        entry = LogEntry.create(
            session_id="test-123",
            entry_type="user_input",
            content="test content",
        )

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            result = append_to_log(self.temp_dir, entry)

        self.assertFalse(result)
        # Should detect either as symlink in check or via O_NOFOLLOW
        stderr_output = mock_stderr.getvalue()
        self.assertTrue(
            "Symlink" in stderr_output or "symbolic link" in stderr_output.lower(),
            f"Expected symlink error, got: {stderr_output}",
        )


class TestAppendToLog(unittest.TestCase):
    """Tests for append_to_log function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creates_file_if_not_exists(self):
        """Should create log file if it doesn't exist."""
        entry = LogEntry.create(
            session_id="test-123",
            entry_type="user_input",
            content="test content",
        )
        result = append_to_log(self.temp_dir, entry)

        self.assertTrue(result)
        self.assertTrue(get_log_path(self.temp_dir).exists())

    def test_appends_to_existing_file(self):
        """Should append to existing log file."""
        entry1 = LogEntry.create(
            session_id="test-123",
            entry_type="user_input",
            content="first entry",
        )
        entry2 = LogEntry.create(
            session_id="test-123",
            entry_type="user_input",
            content="second entry",
        )

        append_to_log(self.temp_dir, entry1)
        append_to_log(self.temp_dir, entry2)

        log_path = get_log_path(self.temp_dir)
        with open(log_path) as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 2)

    def test_writes_valid_json(self):
        """Should write valid NDJSON format."""
        entry = LogEntry.create(
            session_id="test-123",
            entry_type="user_input",
            content="test content",
            command="/p",
        )
        append_to_log(self.temp_dir, entry)

        log_path = get_log_path(self.temp_dir)
        with open(log_path) as f:
            line = f.readline()

        data = json.loads(line)
        self.assertEqual(data["session_id"], "test-123")
        self.assertEqual(data["content"], "test content")
        self.assertEqual(data["command"], "/p")

    def test_returns_false_on_error(self):
        """Should return False on write error."""
        entry = LogEntry.create(
            session_id="test-123",
            entry_type="user_input",
            content="test",
        )

        # Try to write to a directory that doesn't exist and can't be created
        with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            with patch("sys.stderr", new_callable=StringIO):
                result = append_to_log("/nonexistent/readonly/path", entry)
                self.assertFalse(result)


class TestReadLog(unittest.TestCase):
    """Tests for read_log function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_empty_list_if_no_file(self):
        """Should return empty list if log file doesn't exist."""
        result = read_log(self.temp_dir)
        self.assertEqual(result, [])

    def test_reads_entries(self):
        """Should read all entries from log file."""
        entry1 = LogEntry.create(
            session_id="test-1",
            entry_type="user_input",
            content="first",
        )
        entry2 = LogEntry.create(
            session_id="test-2",
            entry_type="user_input",
            content="second",
        )

        append_to_log(self.temp_dir, entry1)
        append_to_log(self.temp_dir, entry2)

        entries = read_log(self.temp_dir)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].content, "first")
        self.assertEqual(entries[1].content, "second")

    def test_skips_empty_lines(self):
        """Should skip empty lines in log file."""
        log_path = get_log_path(self.temp_dir)
        entry = LogEntry.create(
            session_id="test-123",
            entry_type="user_input",
            content="test",
        )

        with open(log_path, "w") as f:
            f.write("\n")
            f.write(entry.to_json() + "\n")
            f.write("\n")
            f.write("   \n")

        entries = read_log(self.temp_dir)
        self.assertEqual(len(entries), 1)

    def test_skips_corrupted_lines(self):
        """Should skip corrupted JSON lines with warning."""
        log_path = get_log_path(self.temp_dir)
        entry = LogEntry.create(
            session_id="test-123",
            entry_type="user_input",
            content="valid entry",
        )

        with open(log_path, "w") as f:
            f.write("this is not json\n")
            f.write(entry.to_json() + "\n")
            f.write("{invalid json}\n")

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            entries = read_log(self.temp_dir)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].content, "valid entry")
        self.assertIn("Skipping corrupted", mock_stderr.getvalue())

    def test_handles_read_error(self):
        """Should handle file read errors gracefully."""
        log_path = get_log_path(self.temp_dir)

        # Create file then make it unreadable
        with open(log_path, "w") as f:
            f.write('{"test": "data"}\n')

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                entries = read_log(self.temp_dir)

        self.assertEqual(entries, [])
        self.assertIn("Error reading", mock_stderr.getvalue())

    def test_refuses_symlink_log_file(self):
        """read_log should refuse to read when log file is a symlink."""
        # Create a real file with log content
        real_file = Path(self.temp_dir) / "other_log.json"
        real_file.write_text('{"session_id":"test","entry_type":"user_input"}\n')

        # Create symlink for the log file pointing to the real file
        log_symlink = Path(self.temp_dir) / PROMPT_LOG_FILENAME
        log_symlink.symlink_to(real_file)

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            entries = read_log(self.temp_dir)

        self.assertEqual(entries, [])
        self.assertIn("Symlink", mock_stderr.getvalue())


class TestGetRecentEntries(unittest.TestCase):
    """Tests for get_recent_entries function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_recent_entries(self):
        """Should return most recent entries."""
        for i in range(5):
            entry = LogEntry.create(
                session_id=f"test-{i}",
                entry_type="user_input",
                content=f"entry {i}",
            )
            append_to_log(self.temp_dir, entry)

        recent = get_recent_entries(self.temp_dir, count=2)

        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0].content, "entry 3")
        self.assertEqual(recent[1].content, "entry 4")

    def test_returns_all_if_fewer_than_count(self):
        """Should return all entries if fewer than requested count."""
        entry = LogEntry.create(
            session_id="test-1",
            entry_type="user_input",
            content="only entry",
        )
        append_to_log(self.temp_dir, entry)

        recent = get_recent_entries(self.temp_dir, count=10)

        self.assertEqual(len(recent), 1)

    def test_returns_empty_for_no_log(self):
        """Should return empty list if no log file."""
        recent = get_recent_entries(self.temp_dir, count=5)
        self.assertEqual(recent, [])


class TestLogExists(unittest.TestCase):
    """Tests for log_exists function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_false_if_no_file(self):
        """Should return False if log file doesn't exist."""
        self.assertFalse(log_exists(self.temp_dir))

    def test_returns_true_if_file_exists(self):
        """Should return True if log file exists."""
        log_path = get_log_path(self.temp_dir)
        with open(log_path, "w") as f:
            f.write("")

        self.assertTrue(log_exists(self.temp_dir))


class TestClearLog(unittest.TestCase):
    """Tests for clear_log function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_true_if_no_file(self):
        """Should return True if log file doesn't exist."""
        result = clear_log(self.temp_dir)
        self.assertTrue(result)

    def test_removes_file(self):
        """Should remove existing log file."""
        log_path = get_log_path(self.temp_dir)
        with open(log_path, "w") as f:
            f.write("some content\n")

        result = clear_log(self.temp_dir)

        self.assertTrue(result)
        self.assertFalse(log_path.exists())

    def test_returns_false_on_error(self):
        """Should return False on removal error."""
        log_path = get_log_path(self.temp_dir)
        with open(log_path, "w") as f:
            f.write("content\n")

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            with patch("sys.stderr", new_callable=StringIO):
                result = clear_log(self.temp_dir)

        self.assertFalse(result)

    def test_refuses_symlink_log_file(self):
        """clear_log should refuse to delete when log file is a symlink."""
        # Create a real file
        real_file = Path(self.temp_dir) / "other_log.json"
        real_file.write_text("content\n")

        # Create symlink for the log file
        log_symlink = Path(self.temp_dir) / PROMPT_LOG_FILENAME
        log_symlink.symlink_to(real_file)

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            result = clear_log(self.temp_dir)

        self.assertFalse(result)
        self.assertIn("Symlink", mock_stderr.getvalue())
        # Both files should still exist
        self.assertTrue(real_file.exists())
        self.assertTrue(log_symlink.exists())


if __name__ == "__main__":
    unittest.main()
