"""Tests for the index service module."""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from memory.config import EMBEDDING_DIMENSIONS
from memory.exceptions import IndexError
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
                with pytest.raises(IndexError) as exc_info:
                    service._create_connection()

                assert "sqlite-vec" in str(exc_info.value).lower()
        finally:
            sys.modules.update(original_modules)


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
