"""Tests for the file-based queue module."""

import io
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks" / "lib"))


class TestFileQueue:
    """Tests for file_queue module."""

    def test_enqueue_creates_file(self, tmp_path):
        """Test enqueue creates queue file."""
        from file_queue import QUEUE_FILE, enqueue_learning

        result = enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="Test summary",
            content="Test content",
            category="error",
            severity="sev-1",
            spec="test-spec",
            tags=["test"],
        )

        assert result is True
        assert (tmp_path / QUEUE_FILE).exists()

    def test_enqueue_appends_to_existing(self, tmp_path):
        """Test enqueue appends to existing queue."""
        from file_queue import enqueue_learning, get_queue_size

        # Add first item
        enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="First",
            content="Content 1",
            category="error",
            severity="sev-1",
        )

        # Add second item
        enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Read",
            summary="Second",
            content="Content 2",
            category="warning",
            severity="sev-2",
        )

        assert get_queue_size(str(tmp_path)) == 2

    def test_dequeue_all_returns_items(self, tmp_path):
        """Test dequeue_all returns all items."""
        from file_queue import dequeue_all, enqueue_learning

        enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="Test",
            content="Content",
            category="error",
            severity="sev-1",
        )

        items = dequeue_all(str(tmp_path))

        assert len(items) == 1
        assert items[0]["summary"] == "Test"
        assert items[0]["tool_name"] == "Bash"

    def test_dequeue_all_clears_file(self, tmp_path):
        """Test dequeue_all deletes the queue file."""
        from file_queue import QUEUE_FILE, dequeue_all, enqueue_learning

        enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="Test",
            content="Content",
            category="error",
            severity="sev-1",
        )

        dequeue_all(str(tmp_path))

        # File should be deleted
        assert not (tmp_path / QUEUE_FILE).exists()

    def test_get_queue_size_empty(self, tmp_path):
        """Test get_queue_size returns 0 for empty queue."""
        from file_queue import get_queue_size

        assert get_queue_size(str(tmp_path)) == 0

    def test_get_queue_size_with_items(self, tmp_path):
        """Test get_queue_size returns correct count."""
        from file_queue import enqueue_learning, get_queue_size

        for i in range(3):
            enqueue_learning(
                cwd=str(tmp_path),
                tool_name="Bash",
                summary=f"Test {i}",
                content=f"Content {i}",
                category="error",
                severity="sev-1",
            )

        assert get_queue_size(str(tmp_path)) == 3

    def test_clear_queue(self, tmp_path):
        """Test clear_queue removes file."""
        from file_queue import QUEUE_FILE, clear_queue, enqueue_learning

        enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="Test",
            content="Content",
            category="error",
            severity="sev-1",
        )

        assert (tmp_path / QUEUE_FILE).exists()

        result = clear_queue(str(tmp_path))

        assert result is True
        assert not (tmp_path / QUEUE_FILE).exists()

    def test_clear_queue_nonexistent(self, tmp_path):
        """Test clear_queue on non-existent file."""
        from file_queue import clear_queue

        result = clear_queue(str(tmp_path))
        assert result is True

    def test_stale_queue_discarded(self, tmp_path):
        """Test stale queue is discarded."""
        from file_queue import QUEUE_FILE, _read_queue

        # Create a stale queue (older than 24 hours)
        queue_path = tmp_path / QUEUE_FILE
        old_time = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        queue_data = {"created": old_time, "items": [{"summary": "old"}]}

        with open(queue_path, "w") as f:
            json.dump(queue_data, f)

        # Read should return empty queue
        result = _read_queue(queue_path)
        assert result["items"] == []

    def test_corrupted_queue_handled(self, tmp_path):
        """Test corrupted queue file is handled."""
        from file_queue import QUEUE_FILE, _read_queue

        queue_path = tmp_path / QUEUE_FILE
        with open(queue_path, "w") as f:
            f.write("not valid json")

        result = _read_queue(queue_path)
        assert "items" in result
        assert result["items"] == []

    def test_max_queue_size_enforced(self, tmp_path):
        """Test queue respects max size."""
        from file_queue import MAX_QUEUE_SIZE, enqueue_learning, get_queue_size

        # Add more than max items
        for i in range(MAX_QUEUE_SIZE + 10):
            enqueue_learning(
                cwd=str(tmp_path),
                tool_name="Bash",
                summary=f"Test {i}",
                content=f"Content {i}",
                category="error",
                severity="sev-1",
            )

        # Should be capped at max
        assert get_queue_size(str(tmp_path)) == MAX_QUEUE_SIZE

    def test_dequeue_empty_returns_empty_list(self, tmp_path):
        """Test dequeue on empty returns empty list."""
        from file_queue import dequeue_all

        items = dequeue_all(str(tmp_path))
        assert items == []

    def test_enqueue_preserves_all_fields(self, tmp_path):
        """Test all fields are preserved in queue."""
        from file_queue import dequeue_all, enqueue_learning

        enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="Test summary",
            content="Test content",
            category="error",
            severity="sev-1",
            spec="my-spec",
            tags=["tag1", "tag2"],
        )

        items = dequeue_all(str(tmp_path))
        item = items[0]

        assert item["tool_name"] == "Bash"
        assert item["summary"] == "Test summary"
        assert item["content"] == "Test content"
        assert item["category"] == "error"
        assert item["severity"] == "sev-1"
        assert item["spec"] == "my-spec"
        assert item["tags"] == ["tag1", "tag2"]
        assert "timestamp" in item
        assert "id" in item

    def test_is_queue_stale_no_created_field(self, tmp_path):
        """Test stale check when created field is missing."""
        from file_queue import _is_queue_stale

        assert _is_queue_stale({}) is True
        assert _is_queue_stale({"items": []}) is True

    def test_is_queue_stale_invalid_created(self, tmp_path):
        """Test stale check with invalid created timestamp."""
        from file_queue import _is_queue_stale

        assert _is_queue_stale({"created": "not-a-date"}) is True
        assert _is_queue_stale({"created": 12345}) is True

    def test_write_queue_oserror(self, tmp_path):
        """Test write queue handles OS errors."""
        from file_queue import _write_queue

        # Make directory read-only to cause write error
        queue_path = tmp_path / "readonly" / ".cs-learning-queue.json"
        queue_path.parent.mkdir()
        queue_path.parent.chmod(0o444)

        try:
            _write_queue(queue_path, {"items": []})
            # On some systems this might succeed if run as root
            # Just verify it doesn't raise
        finally:
            queue_path.parent.chmod(0o755)

    def test_dequeue_oserror_on_unlink(self, tmp_path):
        """Test dequeue handles error during file deletion."""
        from file_queue import dequeue_all, enqueue_learning

        enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="Test",
            content="Content",
            category="error",
            severity="sev-1",
        )

        # Mock unlink to raise
        stderr_capture = io.StringIO()
        with (
            patch.object(Path, "unlink", side_effect=OSError("permission denied")),
            patch("sys.stderr", stderr_capture),
        ):
            items = dequeue_all(str(tmp_path))

            # Items should still be returned
            assert len(items) == 1
            # Error should be logged
            assert "Error deleting" in stderr_capture.getvalue()

    def test_clear_queue_oserror(self, tmp_path):
        """Test clear_queue handles OS error."""
        from file_queue import clear_queue, enqueue_learning

        enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="Test",
            content="Content",
            category="error",
            severity="sev-1",
        )

        # Mock unlink to raise
        stderr_capture = io.StringIO()
        with (
            patch.object(Path, "unlink", side_effect=OSError("permission denied")),
            patch("sys.stderr", stderr_capture),
        ):
            result = clear_queue(str(tmp_path))
            assert result is False
            assert "Error clearing" in stderr_capture.getvalue()

    def test_read_queue_oserror(self, tmp_path):
        """Test read queue handles OS error."""
        from file_queue import QUEUE_FILE, _read_queue

        queue_path = tmp_path / QUEUE_FILE

        # Create a file then mock open to fail
        with patch("builtins.open", side_effect=OSError("read error")):
            with patch.object(Path, "is_file", return_value=True):
                result = _read_queue(queue_path)
                assert result["items"] == []


class TestFileQueueEdgeCases:
    """Edge case tests for file_queue module."""

    def test_enqueue_with_none_tags(self, tmp_path):
        """Test enqueue with None tags."""
        from file_queue import dequeue_all, enqueue_learning

        result = enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="Test",
            content="Content",
            category="error",
            severity="sev-1",
            tags=None,
        )

        assert result is True
        items = dequeue_all(str(tmp_path))
        assert items[0]["tags"] == []

    def test_enqueue_with_none_spec(self, tmp_path):
        """Test enqueue with None spec."""
        from file_queue import dequeue_all, enqueue_learning

        enqueue_learning(
            cwd=str(tmp_path),
            tool_name="Bash",
            summary="Test",
            content="Content",
            category="error",
            severity="sev-1",
            spec=None,
        )

        items = dequeue_all(str(tmp_path))
        assert items[0]["spec"] is None

    def test_get_queue_path(self, tmp_path):
        """Test _get_queue_path returns correct path."""
        from file_queue import QUEUE_FILE, _get_queue_path

        path = _get_queue_path(str(tmp_path))
        assert path == tmp_path / QUEUE_FILE
