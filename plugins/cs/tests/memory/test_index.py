"""Tests for the index service module."""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from memory.config import EMBEDDING_DIMENSIONS
from memory.exceptions import MemoryIndexError
from memory.index import IndexService
from memory.models import Memory


def make_memory(
    memory_id: str = "test:abc123",
    commit_sha: str = "abc123",
    namespace: str = "decisions",
    spec: str | None = "test-spec",
    phase: str | None = "planning",
    summary: str = "Test summary",
    content: str = "Test content",
    tags: tuple[str, ...] = ("tag1", "tag2"),
    timestamp: datetime | None = None,
    status: str | None = "active",
    relates_to: tuple[str, ...] = (),
) -> Memory:
    """Create a test Memory object."""
    return Memory(
        id=memory_id,
        commit_sha=commit_sha,
        namespace=namespace,
        spec=spec,
        phase=phase,
        summary=summary,
        content=content,
        tags=tags,
        timestamp=timestamp or datetime.now(),
        status=status,
        relates_to=relates_to,
    )


def make_embedding(dim: int = EMBEDDING_DIMENSIONS, fill: float = 0.0) -> list[float]:
    """Create a test embedding vector."""
    return [fill] * dim


@pytest.fixture
def index_service(tmp_path):
    """Create an IndexService for testing."""
    db_path = tmp_path / "test.db"
    service = IndexService(db_path=db_path)
    yield service
    service.close()


class TestIndexServiceInit:
    """Tests for IndexService initialization."""

    def test_init_with_default_path(self):
        """Test initialization uses default path."""
        service = IndexService()
        assert service.db_path is not None
        assert service._conn is None

    def test_init_with_custom_path(self, tmp_path):
        """Test initialization with custom path."""
        db_path = tmp_path / "test.db"
        service = IndexService(db_path=db_path)
        assert service.db_path == db_path

    def test_init_with_string_path(self, tmp_path):
        """Test initialization with string path."""
        db_path = str(tmp_path / "test.db")
        service = IndexService(db_path=db_path)
        assert service.db_path == Path(db_path)


class TestConnectionManagement:
    """Tests for database connection management."""

    def test_get_connection_creates_new(self, index_service):
        """Test get_connection creates new connection."""
        conn = index_service._get_connection()
        assert conn is not None
        assert index_service._conn is conn

    def test_get_connection_returns_existing(self, index_service):
        """Test get_connection returns cached connection."""
        conn1 = index_service._get_connection()
        conn2 = index_service._get_connection()
        assert conn1 is conn2

    def test_close_clears_connection(self, index_service):
        """Test close clears the connection."""
        index_service._get_connection()
        assert index_service._conn is not None

        index_service.close()
        assert index_service._conn is None


class TestConnectionErrors:
    """Tests for connection error handling."""

    def test_missing_sqlite_vec_raises_error(self, tmp_path):
        """Test error when sqlite-vec not installed."""
        db_path = tmp_path / "test_missing.db"
        service = IndexService(db_path=db_path)

        # Simulate missing sqlite_vec by patching the import
        original_modules = sys.modules.copy()
        try:
            # Remove sqlite_vec from modules
            if "sqlite_vec" in sys.modules:
                del sys.modules["sqlite_vec"]

            with patch.dict(sys.modules, {"sqlite_vec": None}):
                with pytest.raises(MemoryIndexError) as exc_info:
                    service._create_connection()

                assert "sqlite-vec" in str(exc_info.value).lower()
        finally:
            sys.modules.update(original_modules)

    def test_sqlite_connect_error(self, tmp_path):
        """Test error when SQLite connection fails."""
        import sqlite3

        db_path = tmp_path / "test_connect_error.db"
        service = IndexService(db_path=db_path)

        with patch("sqlite3.connect") as mock_connect:
            mock_connect.side_effect = sqlite3.Error("connection refused")
            with pytest.raises(MemoryIndexError) as exc_info:
                service._create_connection()

            assert "Failed to open database" in str(exc_info.value)

    def test_sqlite_vec_load_error(self, tmp_path):
        """Test error when sqlite-vec fails to load."""
        from unittest.mock import MagicMock

        db_path = tmp_path / "test_vec_load.db"
        service = IndexService(db_path=db_path)

        mock_conn = MagicMock()
        mock_vec = MagicMock()
        mock_vec.load.side_effect = Exception("extension load failed")

        with patch("sqlite3.connect", return_value=mock_conn):
            with patch.dict(sys.modules, {"sqlite_vec": mock_vec}):
                with pytest.raises(MemoryIndexError) as exc_info:
                    service._create_connection()

                assert "Failed to load sqlite-vec" in str(exc_info.value)

    def test_directory_path_raises_error(self, tmp_path):
        """Test error when db_path is a directory instead of a file."""
        # Pass directory path instead of file path
        service = IndexService(db_path=tmp_path)

        with pytest.raises(MemoryIndexError) as exc_info:
            service._create_connection()

        assert "Database path is a directory" in str(exc_info.value)
        assert "Pass a file path" in exc_info.value.recovery_action


class TestInitialize:
    """Tests for database initialization."""

    def test_initialize_creates_tables(self, index_service):
        """Test initialize creates required tables."""
        index_service.initialize()

        # Verify tables exist
        conn = index_service._get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor}

        assert "memories" in tables
        assert "vec_memories" in tables


class TestInsertAndGet:
    """Tests for insert and get operations."""

    def test_insert_and_get_memory(self, index_service):
        """Test inserting and retrieving a memory."""
        index_service.initialize()

        memory = make_memory()
        embedding = make_embedding()

        index_service.insert(memory, embedding)
        retrieved = index_service.get(memory.id)

        assert retrieved is not None
        assert retrieved.id == memory.id
        assert retrieved.summary == memory.summary
        assert retrieved.namespace == memory.namespace

    def test_get_nonexistent_returns_none(self, index_service):
        """Test getting nonexistent memory returns None."""
        index_service.initialize()

        result = index_service.get("nonexistent:id")
        assert result is None

    def test_insert_replaces_existing(self, index_service):
        """Test insert replaces existing memory with same ID."""
        index_service.initialize()

        memory1 = make_memory(summary="Original")
        memory2 = make_memory(summary="Updated")
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)

        retrieved = index_service.get(memory1.id)
        assert retrieved is not None
        assert retrieved.summary == "Updated"


class TestDelete:
    """Tests for delete operation."""

    def test_delete_existing_memory(self, index_service):
        """Test deleting an existing memory."""
        index_service.initialize()

        memory = make_memory()
        embedding = make_embedding()
        index_service.insert(memory, embedding)

        result = index_service.delete(memory.id)

        assert result is True
        assert index_service.get(memory.id) is None

    def test_delete_nonexistent_returns_false(self, index_service):
        """Test deleting nonexistent memory returns False."""
        index_service.initialize()

        result = index_service.delete("nonexistent:id")
        assert result is False


class TestUpdate:
    """Tests for update operation."""

    def test_update_memory_metadata(self, index_service):
        """Test updating memory metadata."""
        index_service.initialize()

        memory = make_memory(summary="Original", status="active")
        embedding = make_embedding()
        index_service.insert(memory, embedding)

        # Update the memory
        updated = make_memory(
            memory_id=memory.id,
            commit_sha=memory.commit_sha,
            summary="Updated summary",
            status="resolved",
        )
        index_service.update(updated)

        retrieved = index_service.get(memory.id)
        assert retrieved is not None
        assert retrieved.summary == "Updated summary"
        assert retrieved.status == "resolved"


class TestSearchVector:
    """Tests for vector search."""

    def test_search_returns_results(self, index_service):
        """Test vector search returns matching results."""
        index_service.initialize()

        # Insert test memories
        memory1 = make_memory(memory_id="test:001", summary="First")
        memory2 = make_memory(memory_id="test:002", summary="Second")
        embedding1 = make_embedding(fill=0.1)
        embedding2 = make_embedding(fill=0.2)

        index_service.insert(memory1, embedding1)
        index_service.insert(memory2, embedding2)

        # Search with similar embedding
        query_embedding = make_embedding(fill=0.15)
        results = index_service.search_vector(query_embedding, limit=5)

        assert len(results) <= 2
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    def test_search_with_namespace_filter(self, index_service):
        """Test vector search with namespace filter."""
        index_service.initialize()

        # Insert memories in different namespaces
        memory1 = make_memory(memory_id="test:001", namespace="decisions")
        memory2 = make_memory(memory_id="test:002", namespace="learnings")
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)

        # Search with namespace filter
        results = index_service.search_vector(
            embedding, filters={"namespace": "decisions"}, limit=5
        )

        # Should only return decisions namespace
        for memory_id, _ in results:
            retrieved = index_service.get(memory_id)
            assert retrieved is not None
            assert retrieved.namespace == "decisions"

    def test_search_with_spec_filter(self, index_service):
        """Test vector search with spec filter."""
        index_service.initialize()

        # Insert memories with different specs
        memory1 = make_memory(memory_id="test:001", spec="spec-a")
        memory2 = make_memory(memory_id="test:002", spec="spec-b")
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)

        # Search with spec filter
        results = index_service.search_vector(
            embedding, filters={"spec": "spec-a"}, limit=5
        )

        # Should only return spec-a
        for memory_id, _ in results:
            retrieved = index_service.get(memory_id)
            assert retrieved is not None
            assert retrieved.spec == "spec-a"


class TestGetStats:
    """Tests for statistics."""

    def test_get_stats_empty_db(self, index_service):
        """Test stats on empty database."""
        index_service.initialize()

        stats = index_service.get_stats()

        assert stats.total_memories == 0
        assert stats.by_namespace == {}
        assert stats.by_spec == {}

    def test_get_stats_with_data(self, index_service):
        """Test stats with data."""
        index_service.initialize()

        # Insert memories
        memory1 = make_memory(
            memory_id="test:001", namespace="decisions", spec="spec-a"
        )
        memory2 = make_memory(
            memory_id="test:002", namespace="learnings", spec="spec-a"
        )
        memory3 = make_memory(
            memory_id="test:003", namespace="decisions", spec="spec-b"
        )
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)
        index_service.insert(memory3, embedding)

        stats = index_service.get_stats()

        assert stats.total_memories == 3
        assert stats.by_namespace == {"decisions": 2, "learnings": 1}
        assert stats.by_spec == {"spec-a": 2, "spec-b": 1}


class TestClear:
    """Tests for clear operation."""

    def test_clear_removes_all_data(self, index_service):
        """Test clear removes all memories."""
        index_service.initialize()

        # Insert some data
        memory = make_memory()
        embedding = make_embedding()
        index_service.insert(memory, embedding)

        # Clear
        index_service.clear()

        stats = index_service.get_stats()
        assert stats.total_memories == 0


class TestRowToMemory:
    """Tests for row conversion."""

    def test_row_to_memory_handles_all_fields(self, index_service):
        """Test _row_to_memory correctly converts all fields."""
        index_service.initialize()

        memory = make_memory(
            tags=("tag1", "tag2", "tag3"),
            relates_to=("rel1", "rel2"),
        )
        embedding = make_embedding()
        index_service.insert(memory, embedding)

        retrieved = index_service.get(memory.id)

        assert retrieved is not None
        assert retrieved.tags == ("tag1", "tag2", "tag3")
        assert retrieved.relates_to == ("rel1", "rel2")

    def test_row_to_memory_handles_null_fields(self, index_service):
        """Test _row_to_memory handles null optional fields."""
        index_service.initialize()

        memory = make_memory(
            spec=None,
            phase=None,
            tags=(),
            status=None,
            relates_to=(),
        )
        embedding = make_embedding()
        index_service.insert(memory, embedding)

        retrieved = index_service.get(memory.id)

        assert retrieved is not None
        assert retrieved.spec is None
        assert retrieved.phase is None
        assert retrieved.tags == ()
        assert retrieved.status is None
        assert retrieved.relates_to == ()


class TestGetBatch:
    """Tests for batch retrieval."""

    def test_get_batch_returns_matching(self, index_service):
        """Test get_batch returns matching memories."""
        index_service.initialize()

        memory1 = make_memory(memory_id="test:001", summary="First")
        memory2 = make_memory(memory_id="test:002", summary="Second")
        memory3 = make_memory(memory_id="test:003", summary="Third")
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)
        index_service.insert(memory3, embedding)

        result = index_service.get_batch(["test:001", "test:003"])

        assert len(result) == 2
        assert "test:001" in result
        assert "test:003" in result
        assert result["test:001"].summary == "First"
        assert result["test:003"].summary == "Third"

    def test_get_batch_empty_list(self, index_service):
        """Test get_batch with empty list returns empty dict."""
        index_service.initialize()

        result = index_service.get_batch([])
        assert result == {}

    def test_get_batch_partial_match(self, index_service):
        """Test get_batch with some non-existent IDs."""
        index_service.initialize()

        memory1 = make_memory(memory_id="test:001", summary="First")
        embedding = make_embedding()
        index_service.insert(memory1, embedding)

        result = index_service.get_batch(["test:001", "nonexistent:id"])

        assert len(result) == 1
        assert "test:001" in result


class TestGetBySpec:
    """Tests for spec-based retrieval."""

    def test_get_by_spec_groups_by_namespace(self, index_service):
        """Test get_by_spec returns memories grouped by namespace."""
        index_service.initialize()

        # Insert memories with same spec but different namespaces
        memory1 = make_memory(
            memory_id="test:001", spec="my-spec", namespace="decisions"
        )
        memory2 = make_memory(
            memory_id="test:002", spec="my-spec", namespace="learnings"
        )
        memory3 = make_memory(
            memory_id="test:003", spec="my-spec", namespace="decisions"
        )
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)
        index_service.insert(memory3, embedding)

        result = index_service.get_by_spec("my-spec")

        assert "decisions" in result
        assert "learnings" in result
        assert len(result["decisions"]) == 2
        assert len(result["learnings"]) == 1

    def test_get_by_spec_no_matches(self, index_service):
        """Test get_by_spec with no matches returns empty dict."""
        index_service.initialize()

        result = index_service.get_by_spec("nonexistent-spec")
        assert result == {}


class TestListRecent:
    """Tests for listing recent memories."""

    def test_list_recent_ordered_by_timestamp(self, index_service):
        """Test list_recent returns memories in timestamp order."""
        index_service.initialize()

        from datetime import timedelta

        now = datetime.now()
        memory1 = make_memory(
            memory_id="test:001",
            summary="Oldest",
            timestamp=now - timedelta(days=2),
        )
        memory2 = make_memory(
            memory_id="test:002",
            summary="Middle",
            timestamp=now - timedelta(days=1),
        )
        memory3 = make_memory(
            memory_id="test:003",
            summary="Newest",
            timestamp=now,
        )
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)
        index_service.insert(memory3, embedding)

        result = index_service.list_recent(limit=3)

        assert len(result) == 3
        assert result[0].summary == "Newest"
        assert result[2].summary == "Oldest"

    def test_list_recent_with_spec_filter(self, index_service):
        """Test list_recent with spec filter."""
        index_service.initialize()

        memory1 = make_memory(memory_id="test:001", spec="spec-a")
        memory2 = make_memory(memory_id="test:002", spec="spec-b")
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)

        result = index_service.list_recent(spec="spec-a", limit=10)

        assert len(result) == 1
        assert result[0].spec == "spec-a"

    def test_list_recent_with_namespace_filter(self, index_service):
        """Test list_recent with namespace filter."""
        index_service.initialize()

        memory1 = make_memory(memory_id="test:001", namespace="decisions")
        memory2 = make_memory(memory_id="test:002", namespace="learnings")
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)

        result = index_service.list_recent(namespace="decisions", limit=10)

        assert len(result) == 1
        assert result[0].namespace == "decisions"

    def test_list_recent_respects_limit(self, index_service):
        """Test list_recent respects limit parameter."""
        index_service.initialize()

        for i in range(5):
            memory = make_memory(memory_id=f"test:{i:03d}", summary=f"Memory {i}")
            embedding = make_embedding()
            index_service.insert(memory, embedding)

        result = index_service.list_recent(limit=2)

        assert len(result) == 2


class TestGetByCommit:
    """Tests for commit-based retrieval."""

    def test_get_by_commit_returns_matching(self, index_service):
        """Test get_by_commit returns memories for a commit."""
        index_service.initialize()

        memory1 = make_memory(memory_id="test:001", commit_sha="abc123")
        memory2 = make_memory(memory_id="test:002", commit_sha="abc123")
        memory3 = make_memory(memory_id="test:003", commit_sha="def456")
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)
        index_service.insert(memory3, embedding)

        result = index_service.get_by_commit("abc123")

        assert len(result) == 2
        for memory in result:
            assert memory.commit_sha == "abc123"

    def test_get_by_commit_no_matches(self, index_service):
        """Test get_by_commit with no matches returns empty list."""
        index_service.initialize()

        result = index_service.get_by_commit("nonexistent")
        assert result == []


class TestGetAllIds:
    """Tests for getting all memory IDs."""

    def test_get_all_ids_returns_set(self, index_service):
        """Test get_all_ids returns set of all IDs."""
        index_service.initialize()

        memory1 = make_memory(memory_id="test:001")
        memory2 = make_memory(memory_id="test:002")
        embedding = make_embedding()

        index_service.insert(memory1, embedding)
        index_service.insert(memory2, embedding)

        result = index_service.get_all_ids()

        assert result == {"test:001", "test:002"}

    def test_get_all_ids_empty_db(self, index_service):
        """Test get_all_ids on empty database."""
        index_service.initialize()

        result = index_service.get_all_ids()
        assert result == set()


class TestSearchVectorDateFilters:
    """Tests for vector search with date filters."""

    def test_search_with_since_filter(self, index_service):
        """Test vector search with since filter."""
        index_service.initialize()

        from datetime import timedelta

        now = datetime.now()
        old = now - timedelta(days=7)
        recent = now - timedelta(days=1)

        memory_old = make_memory(memory_id="test:old", timestamp=old)
        memory_recent = make_memory(memory_id="test:recent", timestamp=recent)
        embedding = make_embedding()

        index_service.insert(memory_old, embedding)
        index_service.insert(memory_recent, embedding)

        # Search with since filter (last 3 days)
        since = now - timedelta(days=3)
        results = index_service.search_vector(
            embedding, filters={"since": since}, limit=5
        )

        # Should only find recent memory
        result_ids = [r[0] for r in results]
        assert "test:recent" in result_ids
        assert "test:old" not in result_ids

    def test_search_with_until_filter(self, index_service):
        """Test vector search with until filter."""
        index_service.initialize()

        from datetime import timedelta

        now = datetime.now()
        old = now - timedelta(days=7)
        recent = now - timedelta(days=1)

        memory_old = make_memory(memory_id="test:old", timestamp=old)
        memory_recent = make_memory(memory_id="test:recent", timestamp=recent)
        embedding = make_embedding()

        index_service.insert(memory_old, embedding)
        index_service.insert(memory_recent, embedding)

        # Search with until filter (before 3 days ago)
        until = now - timedelta(days=3)
        results = index_service.search_vector(
            embedding, filters={"until": until}, limit=5
        )

        # Should only find old memory
        result_ids = [r[0] for r in results]
        assert "test:old" in result_ids
        assert "test:recent" not in result_ids


class TestErrorHandling:
    """Tests for error handling paths."""

    def test_initialize_error(self, tmp_path):
        """Test error during database initialization."""
        import sqlite3
        from unittest.mock import MagicMock

        db_path = tmp_path / "test_init_error.db"
        service = IndexService(db_path=db_path)

        mock_conn = MagicMock()
        mock_conn.executescript.side_effect = sqlite3.Error("init failed")
        service._conn = mock_conn

        with pytest.raises(MemoryIndexError) as exc_info:
            service.initialize()

        assert "Failed to initialize database" in str(exc_info.value)

    def test_insert_rowid_not_found(self, tmp_path):
        """Test error when rowid not found after insert."""
        from unittest.mock import MagicMock

        db_path = tmp_path / "test_insert_rowid.db"
        service = IndexService(db_path=db_path)

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        service._conn = mock_conn

        memory = make_memory()
        embedding = make_embedding()

        with pytest.raises(MemoryIndexError) as exc_info:
            service.insert(memory, embedding)

        assert "Failed to get rowid" in str(exc_info.value)

    def test_insert_sqlite_error(self, index_service):
        """Test SQLite error during insert."""
        import sqlite3
        from unittest.mock import MagicMock

        index_service.initialize()

        # Replace connection with mock that raises error
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("insert failed")
        index_service._conn = mock_conn

        memory = make_memory()
        embedding = make_embedding()

        with pytest.raises(MemoryIndexError) as exc_info:
            index_service.insert(memory, embedding)

        assert "Failed to insert memory" in str(exc_info.value)

    def test_delete_sqlite_error(self, index_service):
        """Test SQLite error during delete."""
        import sqlite3
        from unittest.mock import MagicMock

        index_service.initialize()

        # Insert a memory first (with real connection)
        memory = make_memory()
        embedding = make_embedding()
        index_service.insert(memory, embedding)

        # Now mock the connection to raise error on delete
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # rowid exists

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = [mock_cursor, sqlite3.Error("delete failed")]
        index_service._conn = mock_conn

        with pytest.raises(MemoryIndexError) as exc_info:
            index_service.delete(memory.id)

        assert "Failed to delete memory" in str(exc_info.value)

    def test_update_sqlite_error(self, index_service):
        """Test SQLite error during update."""
        import sqlite3
        from unittest.mock import MagicMock

        index_service.initialize()

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("update failed")
        index_service._conn = mock_conn

        memory = make_memory()

        with pytest.raises(MemoryIndexError) as exc_info:
            index_service.update(memory)

        assert "Failed to update memory" in str(exc_info.value)

    def test_search_vector_error(self, index_service):
        """Test SQLite error during vector search."""
        import sqlite3
        from unittest.mock import MagicMock

        index_service.initialize()

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("search failed")
        index_service._conn = mock_conn

        embedding = make_embedding()

        with pytest.raises(MemoryIndexError) as exc_info:
            index_service.search_vector(embedding)

        assert "Vector search failed" in str(exc_info.value)

    def test_clear_sqlite_error(self, index_service):
        """Test SQLite error during clear."""
        import sqlite3
        from unittest.mock import MagicMock

        index_service.initialize()

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("clear failed")
        index_service._conn = mock_conn

        with pytest.raises(MemoryIndexError) as exc_info:
            index_service.clear()

        assert "Failed to clear index" in str(exc_info.value)

    def test_get_stats_oserror_on_size(self, index_service):
        """Test get_stats handles OSError when getting file size."""
        index_service.initialize()

        # Mock Path.stat at the class level
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.side_effect = OSError("permission denied")

            stats = index_service.get_stats()

            # Should return 0 for size but not raise
            assert stats.index_size_bytes == 0
