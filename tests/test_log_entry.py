"""
Tests for LogEntry and FilterInfo classes.
"""

import json
import sys
import unittest
from pathlib import Path

# Add parent directory for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from filters.log_entry import EntryMetadata, FilterInfo, LogEntry


class TestFilterInfo(unittest.TestCase):
    """Tests for FilterInfo dataclass."""

    def test_default_values(self):
        """FilterInfo should have sensible defaults."""
        info = FilterInfo()
        self.assertEqual(info.secret_count, 0)
        self.assertEqual(info.secret_types, [])
        self.assertFalse(info.was_truncated)

    def test_to_dict(self):
        """FilterInfo should serialize to dictionary."""
        info = FilterInfo(
            secret_count=2,
            secret_types=["aws_key", "api_token"],
            was_truncated=True,
        )
        d = info.to_dict()
        self.assertEqual(d["secret_count"], 2)
        self.assertEqual(d["secret_types"], ["aws_key", "api_token"])
        self.assertTrue(d["was_truncated"])

    def test_from_dict(self):
        """FilterInfo should deserialize from dictionary."""
        data = {
            "secret_count": 1,
            "secret_types": ["github_token"],
            "was_truncated": False,
        }
        info = FilterInfo.from_dict(data)
        self.assertEqual(info.secret_count, 1)
        self.assertEqual(info.secret_types, ["github_token"])
        self.assertFalse(info.was_truncated)

    def test_from_dict_with_missing_keys(self):
        """FilterInfo should handle missing keys gracefully."""
        info = FilterInfo.from_dict({})
        self.assertEqual(info.secret_count, 0)
        self.assertEqual(info.secret_types, [])
        self.assertFalse(info.was_truncated)


class TestLogEntry(unittest.TestCase):
    """Tests for LogEntry dataclass."""

    def test_create_basic_entry(self):
        """LogEntry.create should generate valid entry with timestamp."""
        entry = LogEntry.create(
            session_id="test-session",
            entry_type="user_input",
            content="Hello, world!",
        )
        self.assertEqual(entry.session_id, "test-session")
        self.assertEqual(entry.entry_type, "user_input")
        self.assertEqual(entry.content, "Hello, world!")
        self.assertIsNone(entry.command)
        self.assertIsNotNone(entry.timestamp)
        self.assertTrue(entry.timestamp.endswith("+00:00"))

    def test_create_with_command(self):
        """LogEntry.create should capture command."""
        entry = LogEntry.create(
            session_id="s1",
            entry_type="user_input",
            content="/p test project",
            command="/p",
        )
        self.assertEqual(entry.command, "/p")

    def test_create_with_filter_info(self):
        """LogEntry.create should include filter info."""
        filter_info = FilterInfo(secret_count=1, secret_types=["aws_key"])
        entry = LogEntry.create(
            session_id="s1",
            entry_type="user_input",
            content="content",
            filter_info=filter_info,
        )
        self.assertEqual(entry.filter_applied.secret_count, 1)
        self.assertEqual(entry.filter_applied.secret_types, ["aws_key"])

    def test_to_json(self):
        """LogEntry should serialize to valid JSON."""
        entry = LogEntry.create(
            session_id="s1",
            entry_type="user_input",
            content="test",
        )
        json_str = entry.to_json()
        # Should be valid JSON
        data = json.loads(json_str)
        self.assertEqual(data["session_id"], "s1")
        self.assertEqual(data["type"], "user_input")
        self.assertEqual(data["content"], "test")

    def test_from_json(self):
        """LogEntry should deserialize from JSON."""
        json_str = '{"timestamp": "2025-01-01T00:00:00+00:00", "session_id": "s1", "type": "user_input", "command": null, "content": "test", "filter_applied": {}, "metadata": {}}'
        entry = LogEntry.from_json(json_str)
        self.assertEqual(entry.session_id, "s1")
        self.assertEqual(entry.entry_type, "user_input")
        self.assertEqual(entry.content, "test")

    def test_roundtrip(self):
        """LogEntry should survive JSON roundtrip."""
        original = LogEntry.create(
            session_id="roundtrip-test",
            entry_type="expanded_prompt",
            content="Full prompt text here",
            command="/i",
            cwd="/path/to/project",
            filter_info=FilterInfo(secret_count=2, secret_types=["a", "b"]),
        )

        json_str = original.to_json()
        restored = LogEntry.from_json(json_str)

        self.assertEqual(restored.session_id, original.session_id)
        self.assertEqual(restored.entry_type, original.entry_type)
        self.assertEqual(restored.content, original.content)
        self.assertEqual(restored.command, original.command)
        self.assertEqual(restored.filter_applied.secret_count, 2)

    def test_metadata_content_length(self):
        """LogEntry should track content length in metadata."""
        entry = LogEntry.create(
            session_id="s1",
            entry_type="user_input",
            content="12345",
        )
        self.assertEqual(entry.metadata.content_length, 5)


class TestEntryMetadata(unittest.TestCase):
    """Tests for EntryMetadata dataclass."""

    def test_default_values(self):
        """EntryMetadata should have sensible defaults."""
        meta = EntryMetadata()
        self.assertEqual(meta.content_length, 0)
        self.assertEqual(meta.cwd, "")

    def test_roundtrip(self):
        """EntryMetadata should survive dictionary roundtrip."""
        original = EntryMetadata(content_length=100, cwd="/test/path")
        restored = EntryMetadata.from_dict(original.to_dict())
        self.assertEqual(restored.content_length, 100)
        self.assertEqual(restored.cwd, "/test/path")


if __name__ == "__main__":
    unittest.main()
