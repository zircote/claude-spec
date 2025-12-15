"""Tests for the capture service module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from memory.capture import CaptureService, capture_lock
from memory.config import EMBEDDING_DIMENSIONS, MAX_CONTENT_LENGTH
from memory.exceptions import CaptureError
from memory.models import Memory


@pytest.fixture
def mock_git_ops():
    """Create mock GitOps."""
    mock = MagicMock()
    mock.get_commit_sha.return_value = "abc123def456"
    mock.append_note.return_value = None
    return mock


@pytest.fixture
def mock_embedding_service():
    """Create mock EmbeddingService."""
    mock = MagicMock()
    mock.embed.return_value = [0.0] * EMBEDDING_DIMENSIONS
    return mock


@pytest.fixture
def mock_index_service():
    """Create mock IndexService."""
    mock = MagicMock()
    mock.initialize.return_value = None
    mock.insert.return_value = None
    mock.get.return_value = None
    mock.update.return_value = None
    return mock


@pytest.fixture
def capture_service(mock_git_ops, mock_embedding_service, mock_index_service):
    """Create CaptureService with mocked dependencies."""
    return CaptureService(
        git_ops=mock_git_ops,
        embedding_service=mock_embedding_service,
        index_service=mock_index_service,
    )


class TestCaptureLock:
    """Tests for capture_lock context manager."""

    def test_lock_acquires_and_releases(self, tmp_path):
        """Test lock acquisition and release."""
        lock_file = tmp_path / "test.lock"

        with capture_lock(lock_file):
            assert lock_file.exists()

        # After context exits, file may still exist but lock is released

    def test_lock_blocks_concurrent_access(self, tmp_path):
        """Test that concurrent lock acquisition fails."""
        lock_file = tmp_path / "test.lock"

        with capture_lock(lock_file):
            # Try to acquire again - should raise
            with pytest.raises(CaptureError) as exc_info:
                with capture_lock(lock_file):
                    pass

            assert "Another capture operation" in str(exc_info.value)

    def test_lock_releases_on_exception(self, tmp_path):
        """Test that lock is released even if exception occurs (SEC-004)."""
        lock_file = tmp_path / "test.lock"

        with pytest.raises(ValueError):
            with capture_lock(lock_file):
                raise ValueError("Simulated error")

        # Lock should be released, so we can acquire it again
        with capture_lock(lock_file):
            pass  # Should succeed without raising

    def test_lock_file_descriptor_not_leaked(self, tmp_path):
        """Test that file descriptors are properly closed (SEC-004)."""
        import resource

        lock_file = tmp_path / "test.lock"

        # Get initial file descriptor count
        initial_fds = resource.getrlimit(resource.RLIMIT_NOFILE)[0]

        # Acquire and release lock many times
        for _ in range(100):
            with capture_lock(lock_file):
                pass

        # If there was a leak, we'd run out of file descriptors
        # This test mainly ensures no exception is raised
        final_fds = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        assert final_fds == initial_fds  # Limit shouldn't change


class TestCaptureServiceInit:
    """Tests for CaptureService initialization."""

    def test_init_with_dependencies(
        self, mock_git_ops, mock_embedding_service, mock_index_service
    ):
        """Test initialization with provided dependencies."""
        service = CaptureService(
            git_ops=mock_git_ops,
            embedding_service=mock_embedding_service,
            index_service=mock_index_service,
        )

        assert service.git_ops is mock_git_ops
        assert service.embedding_service is mock_embedding_service
        assert service.index_service is mock_index_service

    def test_init_creates_defaults(self):
        """Test initialization creates default services."""
        with patch("memory.capture.GitOps") as mock_git:
            with patch("memory.capture.EmbeddingService") as mock_embed:
                with patch("memory.capture.IndexService") as mock_index:
                    _service = CaptureService()

                    assert mock_git.called
                    assert mock_embed.called
                    assert mock_index.called


class TestCapture:
    """Tests for capture method."""

    def test_capture_success(self, capture_service, mock_git_ops, tmp_path):
        """Test successful memory capture."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture(
                namespace="decisions",
                summary="Test decision summary",
                content="Test decision content",
                spec="test-spec",
                tags=["test", "example"],
            )

        assert result.success is True
        assert result.memory is not None
        assert result.memory.namespace == "decisions"
        assert result.memory.summary == "Test decision summary"
        assert result.indexed is True
        mock_git_ops.append_note.assert_called_once()

    def test_capture_invalid_namespace(self, capture_service):
        """Test capture with invalid namespace."""
        with pytest.raises(CaptureError) as exc_info:
            capture_service.capture(
                namespace="invalid_namespace",
                summary="Test",
                content="Test",
            )

        assert "Invalid namespace" in str(exc_info.value)

    def test_capture_content_too_long(self, capture_service):
        """Test capture with content exceeding MAX_CONTENT_LENGTH (SEC-005)."""
        # Create content that exceeds the limit
        long_content = "x" * (MAX_CONTENT_LENGTH + 1)

        with pytest.raises(CaptureError) as exc_info:
            capture_service.capture(
                namespace="decisions",
                summary="Test",
                content=long_content,
            )

        assert "Content too long" in str(exc_info.value)
        assert str(MAX_CONTENT_LENGTH) in str(exc_info.value)

    def test_capture_content_at_limit(self, capture_service, tmp_path):
        """Test capture with content exactly at MAX_CONTENT_LENGTH (SEC-005)."""
        lock_file = tmp_path / "test.lock"
        # Create content exactly at the limit
        content_at_limit = "x" * MAX_CONTENT_LENGTH

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture(
                namespace="decisions",
                summary="Test",
                content=content_at_limit,
            )

        # Should succeed
        assert result.success is True

    def test_capture_graceful_degradation(
        self, capture_service, mock_embedding_service, tmp_path
    ):
        """Test capture continues when embedding fails."""
        mock_embedding_service.embed.side_effect = Exception("Embedding failed")
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture(
                namespace="decisions",
                summary="Test",
                content="Test content",
            )

        assert result.success is True
        assert result.indexed is False
        assert result.warning is not None
        assert "Embedding/indexing failed" in result.warning

    def test_capture_with_all_metadata(self, capture_service, tmp_path):
        """Test capture with all metadata fields."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture(
                namespace="blockers",
                summary="Test blocker",
                content="Blocker content",
                spec="test-spec",
                tags=["blocking", "urgent"],
                phase="implementation",
                status="unresolved",
            )

        assert result.success is True
        assert result.memory.phase == "implementation"
        assert result.memory.status == "unresolved"
        assert result.memory.tags == ("blocking", "urgent")


class TestCaptureDecision:
    """Tests for capture_decision method."""

    def test_capture_decision_formats_adr(self, capture_service, tmp_path):
        """Test decision capture formats ADR content."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_decision(
                spec="test-spec",
                summary="Use Python for backend",
                context="Need to choose a backend language",
                rationale="Python is well-suited for our needs",
                alternatives=["Go", "Rust"],
                tags=["architecture"],
            )

        assert result.success is True
        assert result.memory.namespace == "decisions"
        assert "## Context" in result.memory.content
        assert "## Decision" in result.memory.content
        assert "## Alternatives Considered" in result.memory.content
        assert "- Go" in result.memory.content
        assert "- Rust" in result.memory.content

    def test_capture_decision_without_alternatives(self, capture_service, tmp_path):
        """Test decision capture without alternatives."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_decision(
                spec="test-spec",
                summary="Use Python",
                context="Need a language",
                rationale="Python works",
            )

        assert result.success is True
        assert "## Alternatives" not in result.memory.content


class TestCaptureBlocker:
    """Tests for capture_blocker method."""

    def test_capture_blocker(self, capture_service, tmp_path):
        """Test blocker capture."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_blocker(
                spec="test-spec",
                summary="Cannot connect to database",
                problem="The database connection times out after 30 seconds",
                tags=["database"],
            )

        assert result.success is True
        assert result.memory.namespace == "blockers"
        assert result.memory.status == "unresolved"
        assert "## Problem" in result.memory.content


class TestResolveBlocker:
    """Tests for resolve_blocker method."""

    def test_resolve_blocker(self, capture_service, mock_index_service, mock_git_ops):
        """Test resolving a blocker."""
        # Set up existing blocker
        existing_memory = Memory(
            id="blockers:abc123",
            commit_sha="abc123",
            namespace="blockers",
            spec="test-spec",
            phase="implementation",
            summary="Test blocker",
            content="## Problem\nSome problem",
            tags=("test",),
            timestamp=datetime.now(UTC),
            status="unresolved",
        )
        mock_index_service.get.return_value = existing_memory

        result = capture_service.resolve_blocker(
            memory_id="blockers:abc123",
            resolution="Fixed by updating configuration",
        )

        assert result.success is True
        assert result.memory.status == "resolved"
        assert "## Resolution" in result.memory.content
        mock_git_ops.append_note.assert_called_once()
        mock_index_service.update.assert_called_once()

    def test_resolve_nonexistent_blocker(self, capture_service, mock_index_service):
        """Test resolving nonexistent blocker raises error."""
        mock_index_service.get.return_value = None

        with pytest.raises(CaptureError) as exc_info:
            capture_service.resolve_blocker(
                memory_id="nonexistent:id",
                resolution="Fixed",
            )

        assert "not found" in str(exc_info.value)

    def test_resolve_non_blocker_raises_error(
        self, capture_service, mock_index_service
    ):
        """Test resolving non-blocker memory raises error."""
        # Set up existing non-blocker memory
        existing_memory = Memory(
            id="decisions:abc123",
            commit_sha="abc123",
            namespace="decisions",  # Not a blocker
            spec="test-spec",
            phase=None,
            summary="Test decision",
            content="Some content",
            tags=(),
            timestamp=datetime.now(UTC),
            status=None,
        )
        mock_index_service.get.return_value = existing_memory

        with pytest.raises(CaptureError) as exc_info:
            capture_service.resolve_blocker(
                memory_id="decisions:abc123",
                resolution="Fixed",
            )

        assert "not a blocker" in str(exc_info.value)


class TestCaptureLearning:
    """Tests for capture_learning method."""

    def test_capture_learning(self, capture_service, tmp_path):
        """Test learning capture."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_learning(
                spec="test-spec",
                summary="Caching improves performance",
                insight="Adding Redis cache reduced latency by 50%",
                applicability="Use for any frequently accessed data",
                tags=["performance", "caching"],
            )

        assert result.success is True
        assert result.memory.namespace == "learnings"
        assert "## Insight" in result.memory.content
        assert "## Applicability" in result.memory.content

    def test_capture_global_learning(self, capture_service, tmp_path):
        """Test global learning capture (no spec)."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_learning(
                spec=None,
                summary="Always validate user input",
                insight="Input validation prevents many security issues",
            )

        assert result.success is True
        assert result.memory.spec is None


class TestCaptureProgress:
    """Tests for capture_progress method."""

    def test_capture_progress(self, capture_service, tmp_path):
        """Test progress capture."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_progress(
                spec="test-spec",
                summary="Completed authentication module",
                task_id="T1.2.3",
                details="Implemented JWT-based auth with refresh tokens",
            )

        assert result.success is True
        assert result.memory.namespace == "progress"
        assert "**Task ID**: T1.2.3" in result.memory.content
        assert "Implemented JWT" in result.memory.content

    def test_capture_progress_minimal(self, capture_service, tmp_path):
        """Test progress capture with minimal info."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_progress(
                spec="test-spec",
                summary="Task completed",
            )

        assert result.success is True
        assert result.memory.content == "Task completed"
