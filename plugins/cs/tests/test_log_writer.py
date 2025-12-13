"""Tests for log_writer module."""

import json
import os
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

from filters.log_entry import LogEntry
from filters.log_writer import (
    PROMPT_LOG_FILENAME,
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
        self.assertEqual(result, "/some/project/dir/.prompt-log.json")

    def test_uses_constant(self):
        """Should use PROMPT_LOG_FILENAME constant."""
        result = get_log_path("/test")
        self.assertTrue(result.endswith(PROMPT_LOG_FILENAME))


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
        self.assertTrue(os.path.exists(get_log_path(self.temp_dir)))

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
            command="/cs:p",
        )
        append_to_log(self.temp_dir, entry)

        log_path = get_log_path(self.temp_dir)
        with open(log_path) as f:
            line = f.readline()

        data = json.loads(line)
        self.assertEqual(data["session_id"], "test-123")
        self.assertEqual(data["content"], "test content")
        self.assertEqual(data["command"], "/cs:p")

    def test_returns_false_on_error(self):
        """Should return False on write error."""
        entry = LogEntry.create(
            session_id="test-123",
            entry_type="user_input",
            content="test",
        )

        # Try to write to a directory that doesn't exist and can't be created
        with patch("os.makedirs", side_effect=OSError("Permission denied")):
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
        self.assertFalse(os.path.exists(log_path))

    def test_returns_false_on_error(self):
        """Should return False on removal error."""
        log_path = get_log_path(self.temp_dir)
        with open(log_path, "w") as f:
            f.write("content\n")

        with patch("os.remove", side_effect=OSError("Permission denied")):
            with patch("sys.stderr", new_callable=StringIO):
                result = clear_log(self.temp_dir)

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
