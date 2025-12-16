"""Tests for the sync service module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from memory.config import EMBEDDING_DIMENSIONS, NAMESPACES
from memory.exceptions import ParseError
from memory.models import IndexStats, Memory
from memory.sync import SyncService


def make_note_content(
    summary: str = "Test summary",
    spec: str | None = "test-spec",
    note_type: str = "decision",
    tags: list[str] | None = None,
) -> str:
    """Create test note content in YAML front matter format."""
    tags_line = f"tags: {tags}" if tags else "tags: []"
    return f"""---
type: {note_type}
summary: {summary}
spec: {spec}
{tags_line}
timestamp: 2025-01-15T10:00:00Z
---

Test body content
"""


def make_memory(
    memory_id: str = "decisions:abc123",
    namespace: str = "decisions",
    summary: str = "Test summary",
    content: str = "Test content",
) -> Memory:
    """Create a test Memory object."""
    return Memory(
        id=memory_id,
        commit_sha=memory_id.split(":")[1] if ":" in memory_id else "abc123",
        namespace=namespace,
        spec="test-spec",
        phase=None,
        summary=summary,
        content=content,
        tags=(),
        timestamp=datetime.now(UTC),
        status=None,
    )


def make_embedding(fill: float = 0.0) -> list[float]:
    """Create a test embedding vector."""
    return [fill] * EMBEDDING_DIMENSIONS


@pytest.fixture
def mock_git_ops():
    """Create mock GitOps."""
    mock = MagicMock()
    mock.show_note.return_value = make_note_content()
    mock.list_notes.return_value = []
    return mock


@pytest.fixture
def mock_embedding_service():
    """Create mock EmbeddingService."""
    mock = MagicMock()
    mock.embed.return_value = make_embedding()
    return mock


@pytest.fixture
def mock_index_service():
    """Create mock IndexService."""
    mock = MagicMock()
    mock.initialize.return_value = None
    mock.insert.return_value = None
    mock.clear.return_value = None
    mock.delete.return_value = True
    mock.get_stats.return_value = IndexStats(
        total_memories=0,
        by_namespace={},
        by_spec={},
        last_sync=None,
        index_size_bytes=0,
    )
    # Default empty set for get_all_ids (public method for ARCH-002 fix)
    mock.get_all_ids.return_value = set()

    return mock


@pytest.fixture
def sync_service(mock_git_ops, mock_embedding_service, mock_index_service):
    """Create SyncService with mocked dependencies."""
    return SyncService(
        git_ops=mock_git_ops,
        embedding_service=mock_embedding_service,
        index_service=mock_index_service,
    )


class TestSyncServiceInit:
    """Tests for SyncService initialization."""

    def test_init_with_dependencies(
        self, mock_git_ops, mock_embedding_service, mock_index_service
    ):
        """Test initialization with provided dependencies."""
        service = SyncService(
            git_ops=mock_git_ops,
            embedding_service=mock_embedding_service,
            index_service=mock_index_service,
        )

        assert service.git_ops is mock_git_ops
        assert service.embedding_service is mock_embedding_service
        assert service.index_service is mock_index_service

    def test_init_creates_defaults(self):
        """Test initialization creates default services."""
        with patch("memory.sync.GitOps") as mock_git:
            with patch("memory.sync.EmbeddingService") as mock_embed:
                with patch("memory.sync.IndexService") as mock_index:
                    _service = SyncService()

                    assert mock_git.called
                    assert mock_embed.called
                    assert mock_index.called


class TestSyncNoteToIndex:
    """Tests for sync_note_to_index method."""

    def test_sync_note_success(
        self, sync_service, mock_git_ops, mock_embedding_service, mock_index_service
    ):
        """Test successful single note sync."""
        result = sync_service.sync_note_to_index("decisions", "abc123")

        assert result is True
        mock_git_ops.show_note.assert_called_once_with("decisions", "abc123")
        mock_embedding_service.embed.assert_called_once()
        mock_index_service.initialize.assert_called_once()
        mock_index_service.insert.assert_called_once()

    def test_sync_note_not_found(self, sync_service, mock_git_ops):
        """Test sync when note doesn't exist."""
        mock_git_ops.show_note.return_value = None

        result = sync_service.sync_note_to_index("decisions", "nonexistent")

        assert result is False

    def test_sync_note_parse_error(self, sync_service, mock_git_ops):
        """Test sync when note parsing fails."""
        mock_git_ops.show_note.return_value = "invalid content without front matter"

        with patch(
            "memory.sync.parse_note",
            side_effect=ParseError("Parse failed", "Check format"),
        ):
            result = sync_service.sync_note_to_index("decisions", "abc123")

        assert result is False

    def test_sync_note_creates_correct_memory(
        self, sync_service, mock_git_ops, mock_index_service
    ):
        """Test that sync creates Memory with correct fields."""
        mock_git_ops.show_note.return_value = make_note_content(
            summary="Important decision",
            spec="my-spec",
            tags=["architecture", "approved"],
        )

        sync_service.sync_note_to_index("decisions", "def456")

        # Check the Memory object passed to insert
        call_args = mock_index_service.insert.call_args
        memory = call_args[0][0]

        # New ID format: namespace:short_sha:timestamp_ms
        assert memory.id.startswith("decisions:def456:")
        assert memory.namespace == "decisions"
        assert memory.commit_sha == "def456"
        assert memory.summary == "Important decision"
        assert memory.spec == "my-spec"

    def test_sync_note_embeds_summary_and_body(
        self, sync_service, mock_git_ops, mock_embedding_service
    ):
        """Test that embedding includes summary and body."""
        mock_git_ops.show_note.return_value = make_note_content(summary="Test summary")

        sync_service.sync_note_to_index("decisions", "abc123")

        # Check embedding text includes summary
        embed_call = mock_embedding_service.embed.call_args[0][0]
        assert "Test summary" in embed_call


class TestFullReindex:
    """Tests for full_reindex method."""

    def test_full_reindex_empty(self, sync_service, mock_git_ops, mock_index_service):
        """Test full reindex with no notes."""
        mock_git_ops.list_notes.return_value = []

        stats = sync_service.full_reindex()

        mock_index_service.initialize.assert_called()
        mock_index_service.clear.assert_called_once()
        assert stats.total_memories == 0

    def test_full_reindex_with_notes(
        self, sync_service, mock_git_ops, mock_index_service
    ):
        """Test full reindex processes all notes."""
        # Only return notes for first namespace call
        call_count = [0]

        def mock_list_notes(namespace):
            call_count[0] += 1
            if namespace == "decisions":
                return [("note1", "commit1"), ("note2", "commit2")]
            return []

        mock_git_ops.list_notes.side_effect = mock_list_notes

        # Make stats show 2 memories after reindex
        mock_index_service.get_stats.return_value = IndexStats(
            total_memories=2,
            by_namespace={"decisions": 2},
            by_spec={"test-spec": 2},
            last_sync=datetime.now(UTC),
            index_size_bytes=1024,
        )

        stats = sync_service.full_reindex()

        assert stats.total_memories == 2
        # list_notes should be called for each namespace
        assert mock_git_ops.list_notes.call_count == len(NAMESPACES)

    def test_full_reindex_with_progress_callback(
        self, sync_service, mock_git_ops, mock_index_service
    ):
        """Test full reindex calls progress callback."""

        def mock_list_notes(namespace):
            if namespace == "decisions":
                return [("note1", "commit1")]
            return []

        mock_git_ops.list_notes.side_effect = mock_list_notes

        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        sync_service.full_reindex(progress_callback=progress_callback)

        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1)

    def test_full_reindex_handles_errors(
        self, sync_service, mock_git_ops, mock_index_service
    ):
        """Test full reindex continues on individual note errors."""

        def mock_list_notes(namespace):
            if namespace == "decisions":
                return [("note1", "commit1"), ("note2", "commit2")]
            return []

        mock_git_ops.list_notes.side_effect = mock_list_notes

        # First note succeeds, second fails
        show_note_calls = [0]

        def mock_show_note(namespace, commit_sha):
            show_note_calls[0] += 1
            if show_note_calls[0] == 1:
                return make_note_content()
            return None  # Second note not found

        mock_git_ops.show_note.side_effect = mock_show_note

        # Should complete without raising
        stats = sync_service.full_reindex()
        assert stats is not None


class TestVerifyIndex:
    """Tests for verify_index method."""

    def test_verify_consistent_index(
        self, sync_service, mock_git_ops, mock_index_service
    ):
        """Test verification when index is consistent."""
        # Set up notes and index to match
        mock_git_ops.list_notes.return_value = []
        mock_index_service.get_all_ids.return_value = set()

        result = sync_service.verify_index()

        assert result.is_consistent is True
        assert len(result.missing_in_index) == 0
        assert len(result.orphaned_in_index) == 0

    def test_verify_missing_in_index(
        self, sync_service, mock_git_ops, mock_index_service
    ):
        """Test verification detects missing entries."""

        def mock_list_notes(namespace):
            if namespace == "decisions":
                return [("note1", "commit1")]
            return []

        mock_git_ops.list_notes.side_effect = mock_list_notes

        # Index is empty (using public get_all_ids method)
        mock_index_service.get_all_ids.return_value = set()

        result = sync_service.verify_index()

        assert result.is_consistent is False
        # New ID format includes timestamp, check prefix
        missing_ids = list(result.missing_in_index)
        assert len(missing_ids) == 1
        assert missing_ids[0].startswith("decisions:commit1:")

    def test_verify_orphaned_in_index(
        self, sync_service, mock_git_ops, mock_index_service
    ):
        """Test verification detects orphaned entries."""
        # No notes
        mock_git_ops.list_notes.return_value = []

        # But index has entries (using public get_all_ids method)
        mock_index_service.get_all_ids.return_value = {"decisions:orphan1"}

        result = sync_service.verify_index()

        assert result.is_consistent is False
        assert "decisions:orphan1" in result.orphaned_in_index


class TestRepairIndex:
    """Tests for repair_index method."""

    def test_repair_adds_missing(self, sync_service, mock_git_ops, mock_index_service):
        """Test repair adds missing entries."""

        def mock_list_notes(namespace):
            if namespace == "decisions":
                return [("note1", "missing1")]
            return []

        mock_git_ops.list_notes.side_effect = mock_list_notes

        # Index is empty (so missing1 is missing) - using public get_all_ids method
        mock_index_service.get_all_ids.return_value = set()

        added, removed = sync_service.repair_index()

        assert added == 1
        assert removed == 0

    def test_repair_removes_orphaned(
        self, sync_service, mock_git_ops, mock_index_service
    ):
        """Test repair removes orphaned entries."""
        # No notes
        mock_git_ops.list_notes.return_value = []

        # Index has orphaned entry - using public get_all_ids method
        mock_index_service.get_all_ids.return_value = {"decisions:orphan1"}
        mock_index_service.delete.return_value = True

        added, removed = sync_service.repair_index()

        assert added == 0
        assert removed == 1
        mock_index_service.delete.assert_called_with("decisions:orphan1")

    def test_repair_handles_both(self, sync_service, mock_git_ops, mock_index_service):
        """Test repair handles both missing and orphaned."""

        def mock_list_notes(namespace):
            if namespace == "decisions":
                return [("note1", "missing1")]
            return []

        mock_git_ops.list_notes.side_effect = mock_list_notes

        # Index has different entry (orphaned) - using public get_all_ids method
        mock_index_service.get_all_ids.return_value = {"decisions:orphan1"}

        added, removed = sync_service.repair_index()

        assert added == 1  # missing1 added
        assert removed == 1  # orphan1 removed


class TestGetSyncStatus:
    """Tests for get_sync_status method."""

    def test_get_sync_status(self, sync_service, mock_git_ops, mock_index_service):
        """Test getting sync status."""
        mock_git_ops.list_notes.return_value = []
        mock_index_service.get_all_ids.return_value = set()

        mock_index_service.get_stats.return_value = IndexStats(
            total_memories=5,
            by_namespace={"decisions": 3, "learnings": 2},
            by_spec={"spec-a": 5},
            last_sync=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            index_size_bytes=2048,
        )

        status = sync_service.get_sync_status()

        assert status["total_indexed"] == 5
        assert status["by_namespace"] == {"decisions": 3, "learnings": 2}
        assert status["index_size_bytes"] == 2048
        assert status["is_consistent"] is True

    def test_get_sync_status_without_last_sync(
        self, sync_service, mock_git_ops, mock_index_service
    ):
        """Test status when last_sync is None."""
        mock_git_ops.list_notes.return_value = []
        mock_index_service.get_all_ids.return_value = set()

        mock_index_service.get_stats.return_value = IndexStats(
            total_memories=0,
            by_namespace={},
            by_spec={},
            last_sync=None,
            index_size_bytes=0,
        )

        status = sync_service.get_sync_status()

        assert status["last_sync"] is None
