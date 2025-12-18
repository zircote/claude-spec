"""Tests for the recall service module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from memory.config import EMBEDDING_DIMENSIONS, MAX_RECALL_LIMIT
from memory.models import HydrationLevel, Memory, MemoryResult
from memory.recall import RecallService


def make_memory(
    memory_id: str = "test:abc123",
    namespace: str = "decisions",
    summary: str = "Test summary",
    content: str = "Test content",
    spec: str | None = "test-spec",
    timestamp: datetime | None = None,
) -> Memory:
    """Create a test Memory object."""
    return Memory(
        id=memory_id,
        commit_sha=memory_id.split(":")[1] if ":" in memory_id else "abc123",
        namespace=namespace,
        spec=spec,
        phase=None,
        summary=summary,
        content=content,
        tags=(),
        timestamp=timestamp or datetime.now(UTC),
        status=None,
    )


def make_embedding(fill: float = 0.0) -> list[float]:
    """Create a test embedding vector."""
    return [fill] * EMBEDDING_DIMENSIONS


@pytest.fixture
def mock_git_ops():
    """Create mock GitOps."""
    mock = MagicMock()
    mock.show_note.return_value = "Full note content"
    mock.get_commit_info.return_value = {
        "sha": "abc123",
        "author_name": "Test Author",
        "author_email": "test@example.com",
        "date": "2025-01-01",
        "message": "Test commit",
    }
    mock.get_changed_files.return_value = ["file1.py", "file2.py"]
    mock.get_file_at_commit.return_value = "file content"
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
    mock.search_vector.return_value = []
    mock.get.return_value = None
    mock.get_batch.return_value = {}  # Default empty batch
    mock.get_by_spec.return_value = {}  # Default empty spec context
    mock.list_recent.return_value = []  # Default empty recent
    mock.get_by_commit.return_value = []  # Default empty by_commit

    return mock


@pytest.fixture
def recall_service(mock_git_ops, mock_embedding_service, mock_index_service):
    """Create RecallService with mocked dependencies."""
    return RecallService(
        git_ops=mock_git_ops,
        embedding_service=mock_embedding_service,
        index_service=mock_index_service,
    )


class TestRecallServiceInit:
    """Tests for RecallService initialization."""

    def test_init_with_dependencies(
        self, mock_git_ops, mock_embedding_service, mock_index_service
    ):
        """Test initialization with provided dependencies."""
        service = RecallService(
            git_ops=mock_git_ops,
            embedding_service=mock_embedding_service,
            index_service=mock_index_service,
        )

        assert service.git_ops is mock_git_ops
        assert service.embedding_service is mock_embedding_service
        assert service.index_service is mock_index_service


class TestSearch:
    """Tests for search method."""

    def test_search_returns_results(
        self, recall_service, mock_embedding_service, mock_index_service
    ):
        """Test search returns memory results."""
        memory = make_memory()
        mock_index_service.search_vector.return_value = [("test:abc123", 0.5)]
        mock_index_service.get_batch.return_value = {"test:abc123": memory}

        results = recall_service.search("test query")

        assert len(results) == 1
        assert results[0].memory.id == "test:abc123"
        assert results[0].distance == 0.5
        mock_embedding_service.embed.assert_called_once_with("test query")

    def test_search_with_filters(self, recall_service, mock_index_service):
        """Test search passes filters to index."""
        mock_index_service.search_vector.return_value = []

        recall_service.search(
            query="test",
            spec="my-spec",
            namespace="decisions",
        )

        call_args = mock_index_service.search_vector.call_args
        filters = call_args[1]["filters"]
        assert filters["spec"] == "my-spec"
        assert filters["namespace"] == "decisions"

    def test_search_respects_limit(self, recall_service, mock_index_service):
        """Test search respects limit parameter."""
        mock_index_service.search_vector.return_value = []

        recall_service.search("test", limit=5)

        call_args = mock_index_service.search_vector.call_args
        assert call_args[1]["limit"] == 5

    def test_search_caps_limit(self, recall_service, mock_index_service):
        """Test search caps limit at MAX_RECALL_LIMIT."""
        mock_index_service.search_vector.return_value = []

        recall_service.search("test", limit=1000)

        call_args = mock_index_service.search_vector.call_args
        assert call_args[1]["limit"] == MAX_RECALL_LIMIT

    def test_search_handles_missing_memories(self, recall_service, mock_index_service):
        """Test search handles case where memory not found in batch."""
        mock_index_service.search_vector.return_value = [("test:missing", 0.5)]
        mock_index_service.get_batch.return_value = {}  # Empty batch - memory not found

        results = recall_service.search("test")

        assert len(results) == 0


class TestHydrate:
    """Tests for hydrate method."""

    def test_hydrate_level_1(self, recall_service):
        """Test Level 1 hydration (summary only)."""
        memory = make_memory()
        result = MemoryResult(memory=memory, distance=0.5)

        hydrated = recall_service.hydrate(result, HydrationLevel.SUMMARY)

        assert hydrated.result is result
        assert hydrated.full_content is None
        # files defaults to empty dict, not None
        assert hydrated.files == {}

    def test_hydrate_level_2(self, recall_service, mock_git_ops):
        """Test Level 2 hydration (full content)."""
        memory = make_memory()
        result = MemoryResult(memory=memory, distance=0.5)

        hydrated = recall_service.hydrate(result, HydrationLevel.FULL)

        assert hydrated.full_content == "Full note content"
        mock_git_ops.show_note.assert_called_once()

    def test_hydrate_level_3(self, recall_service, mock_git_ops):
        """Test Level 3 hydration (full content + files)."""
        memory = make_memory()
        result = MemoryResult(memory=memory, distance=0.5)

        hydrated = recall_service.hydrate(result, HydrationLevel.FILES)

        assert hydrated.full_content is not None
        assert hydrated.files is not None
        assert len(hydrated.files) == 2
        assert hydrated.commit_info is not None
        mock_git_ops.get_changed_files.assert_called_once()
        assert mock_git_ops.get_file_at_commit.call_count == 2


class TestContext:
    """Tests for context method."""

    def test_context_loads_all_namespaces(
        self, recall_service, mock_embedding_service, mock_index_service
    ):
        """Test context loads memories from all namespaces using get_by_spec."""
        # Return memories for some namespaces (now using get_by_spec)
        memory1 = make_memory(memory_id="decisions:abc", namespace="decisions")
        memory2 = make_memory(memory_id="learnings:def", namespace="learnings")

        mock_index_service.get_by_spec.return_value = {
            "decisions": [memory1],
            "learnings": [memory2],
        }

        context = recall_service.context("test-spec")

        assert context.spec == "test-spec"
        assert context.total_count == 2
        mock_index_service.get_by_spec.assert_called_once_with("test-spec")

    def test_context_returns_empty_for_no_memories(
        self, recall_service, mock_index_service
    ):
        """Test context returns empty context when no memories found."""
        mock_index_service.get_by_spec.return_value = {}

        context = recall_service.context("nonexistent-spec")

        assert context.spec == "nonexistent-spec"
        assert context.total_count == 0
        assert context.memories == {}


class TestRecent:
    """Tests for recent method."""

    def test_recent_returns_memories(self, recall_service, mock_index_service):
        """Test recent returns memories from index using public list_recent method."""
        memory = make_memory(memory_id="test:recent1")
        mock_index_service.list_recent.return_value = [memory]

        results = recall_service.recent(limit=5)

        assert len(results) == 1
        assert results[0].id == "test:recent1"
        mock_index_service.list_recent.assert_called_once_with(
            spec=None, namespace=None, limit=5
        )

    def test_recent_with_filters(self, recall_service, mock_index_service):
        """Test recent applies filters via public list_recent method."""
        mock_index_service.list_recent.return_value = []

        recall_service.recent(spec="test-spec", namespace="decisions", limit=5)

        mock_index_service.list_recent.assert_called_once_with(
            spec="test-spec", namespace="decisions", limit=5
        )


class TestSimilar:
    """Tests for similar method."""

    def test_similar_excludes_input_memory(
        self, recall_service, mock_embedding_service, mock_index_service
    ):
        """Test similar excludes the input memory from results."""
        input_memory = make_memory(memory_id="test:input")
        similar_memory = make_memory(memory_id="test:similar")

        mock_index_service.search_vector.return_value = [
            ("test:input", 0.0),  # Input memory itself
            ("test:similar", 0.5),
        ]

        # Use get_batch instead of get (PERF-001 fix)
        mock_index_service.get_batch.return_value = {
            "test:input": input_memory,
            "test:similar": similar_memory,
        }

        results = recall_service.similar(input_memory, limit=5)

        # Should not include the input memory
        assert len(results) == 1
        assert results[0].memory.id == "test:similar"


class TestByCommit:
    """Tests for by_commit method."""

    def test_by_commit_returns_memories(self, recall_service, mock_index_service):
        """Test by_commit returns memories using public get_by_commit method."""
        memory = make_memory(memory_id="test:abc123")
        mock_index_service.get_by_commit.return_value = [memory]

        results = recall_service.by_commit("abc123")

        assert len(results) == 1
        assert results[0].id == "test:abc123"
        mock_index_service.get_by_commit.assert_called_once_with("abc123")
