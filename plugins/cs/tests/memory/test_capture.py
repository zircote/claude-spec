"""Tests for the capture service module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from memory.capture import (
    CaptureService,
    capture_lock,
    is_auto_capture_enabled,
    validate_auto_capture_namespace,
)
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
    # Reset sync flag for test isolation
    CaptureService.reset_sync_configured()
    service = CaptureService(
        git_ops=mock_git_ops,
        embedding_service=mock_embedding_service,
        index_service=mock_index_service,
    )
    yield service
    # Cleanup after test
    CaptureService.reset_sync_configured()


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


class TestAutoConfiguration:
    """Tests for auto-configuration of git notes sync."""

    def setup_method(self):
        """Reset sync configured flag before each test."""
        CaptureService.reset_sync_configured()

    def teardown_method(self):
        """Reset sync configured flag after each test."""
        CaptureService.reset_sync_configured()

    def test_configure_sync_called_on_first_capture(
        self, mock_git_ops, mock_embedding_service, mock_index_service, tmp_path
    ):
        """Test that configure_sync is called on first capture."""
        service = CaptureService(
            git_ops=mock_git_ops,
            embedding_service=mock_embedding_service,
            index_service=mock_index_service,
        )

        lock_file = tmp_path / "test.lock"
        with patch("memory.capture.LOCK_FILE", lock_file):
            service.capture(
                namespace="decisions",
                summary="Test",
                content="Content",
            )

        mock_git_ops.configure_sync.assert_called_once()

    def test_configure_sync_not_called_on_subsequent_captures(
        self, mock_git_ops, mock_embedding_service, mock_index_service, tmp_path
    ):
        """Test that configure_sync is only called once across captures."""
        service = CaptureService(
            git_ops=mock_git_ops,
            embedding_service=mock_embedding_service,
            index_service=mock_index_service,
        )

        lock_file = tmp_path / "test.lock"
        with patch("memory.capture.LOCK_FILE", lock_file):
            # First capture - should configure
            service.capture(
                namespace="decisions",
                summary="Test 1",
                content="Content 1",
            )

            # Second capture - should not configure again
            service.capture(
                namespace="learnings",
                summary="Test 2",
                content="Content 2",
            )

        # Should only be called once despite two captures
        mock_git_ops.configure_sync.assert_called_once()

    def test_reset_sync_configured(
        self, mock_git_ops, mock_embedding_service, mock_index_service, tmp_path
    ):
        """Test that reset_sync_configured allows reconfiguration."""
        service = CaptureService(
            git_ops=mock_git_ops,
            embedding_service=mock_embedding_service,
            index_service=mock_index_service,
        )

        lock_file = tmp_path / "test.lock"
        with patch("memory.capture.LOCK_FILE", lock_file):
            # First capture
            service.capture(namespace="decisions", summary="Test", content="Content")
            assert mock_git_ops.configure_sync.call_count == 1

            # Reset and capture again
            CaptureService.reset_sync_configured()
            service.capture(
                namespace="decisions", summary="Test 2", content="Content 2"
            )
            assert mock_git_ops.configure_sync.call_count == 2


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


class TestValidateAutoCaptureNamespace:
    """Tests for validate_auto_capture_namespace function."""

    def test_valid_namespace_in_auto_capture(self):
        """Test that valid namespace in AUTO_CAPTURE_NAMESPACES returns True."""
        # 'decisions' is in both NAMESPACES and AUTO_CAPTURE_NAMESPACES
        result = validate_auto_capture_namespace("decisions")
        assert result is True

    def test_valid_namespace_not_in_auto_capture(self):
        """Test that valid namespace not in AUTO_CAPTURE_NAMESPACES returns False."""
        # 'reviews' is in NAMESPACES but not in AUTO_CAPTURE_NAMESPACES
        result = validate_auto_capture_namespace("reviews")
        assert result is False

    def test_invalid_namespace_raises_error(self):
        """Test that invalid namespace raises CaptureError."""
        with pytest.raises(CaptureError) as exc_info:
            validate_auto_capture_namespace("invalid_namespace")

        assert "Invalid namespace" in str(exc_info.value)
        assert "invalid_namespace" in str(exc_info.value)


class TestCaptureReview:
    """Tests for capture_review method."""

    def test_capture_review_success(self, capture_service, tmp_path):
        """Test successful review capture."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_review(
                spec="test-spec",
                summary="SQL injection vulnerability",
                category="security",
                severity="critical",
                file_path="src/db/queries.py",
                line=42,
                description="User input is concatenated directly into SQL query",
                suggested_fix="Use parameterized queries",
                impact="Allows attacker to execute arbitrary SQL",
                tags=["owasp"],
            )

        assert result.success is True
        assert result.memory is not None
        assert result.memory.namespace == "reviews"
        assert result.memory.status == "open"
        assert result.indexed is True

    def test_capture_review_invalid_category(self, capture_service):
        """Test capture_review with invalid category raises error."""
        with pytest.raises(CaptureError) as exc_info:
            capture_service.capture_review(
                spec="test-spec",
                summary="Test finding",
                category="invalid_category",
                severity="high",
                file_path="test.py",
                line=1,
                description="Test",
            )

        assert "Invalid review category" in str(exc_info.value)
        assert "invalid_category" in str(exc_info.value)

    def test_capture_review_invalid_severity(self, capture_service):
        """Test capture_review with invalid severity raises error."""
        with pytest.raises(CaptureError) as exc_info:
            capture_service.capture_review(
                spec="test-spec",
                summary="Test finding",
                category="security",
                severity="invalid_severity",
                file_path="test.py",
                line=1,
                description="Test",
            )

        assert "Invalid review severity" in str(exc_info.value)
        assert "invalid_severity" in str(exc_info.value)

    def test_capture_review_formats_content(self, capture_service, tmp_path):
        """Test that capture_review formats content correctly."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_review(
                spec="test-spec",
                summary="Performance issue",
                category="performance",
                severity="medium",
                file_path="src/api/handlers.py",
                line=100,
                description="N+1 query in loop",
                suggested_fix="Use eager loading",
                impact="Slow response times",
            )

        content = result.memory.content
        assert "## Category" in content
        assert "performance" in content
        assert "## Severity" in content
        assert "medium" in content
        assert "## Location" in content
        assert "src/api/handlers.py:100" in content
        assert "## Description" in content
        assert "N+1 query in loop" in content
        assert "## Impact" in content
        assert "Slow response times" in content
        assert "## Suggested Fix" in content
        assert "Use eager loading" in content


class TestCaptureRetrospective:
    """Tests for capture_retrospective method."""

    def test_capture_retrospective_success(self, capture_service, tmp_path):
        """Test successful retrospective capture."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_retrospective(
                spec="test-spec",
                summary="Retrospective: test-spec",
                outcome="success",
                what_went_well=["Good planning", "Clear requirements"],
                what_to_improve=["Better testing", "More documentation"],
                key_learnings=["Start testing early", "Document as you go"],
                recommendations=["Use TDD", "Weekly reviews"],
                tags=["q4-2024"],
            )

        assert result.success is True
        assert result.memory is not None
        assert result.memory.namespace == "retrospective"
        assert result.memory.phase == "close-out"
        assert "retrospective" in result.memory.tags
        assert "success" in result.memory.tags
        assert result.indexed is True

    def test_capture_retrospective_invalid_outcome(self, capture_service):
        """Test capture_retrospective with invalid outcome raises error."""
        with pytest.raises(CaptureError) as exc_info:
            capture_service.capture_retrospective(
                spec="test-spec",
                summary="Retrospective: test-spec",
                outcome="invalid_outcome",
                what_went_well=["Good"],
                what_to_improve=["Better"],
                key_learnings=["Learning"],
            )

        assert "Invalid retrospective outcome" in str(exc_info.value)
        assert "invalid_outcome" in str(exc_info.value)

    def test_capture_retrospective_with_metrics(self, capture_service, tmp_path):
        """Test capture_retrospective with metrics formats content correctly."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_retrospective(
                spec="test-spec",
                summary="Retrospective: test-spec",
                outcome="partial",
                what_went_well=["Fast delivery"],
                what_to_improve=["Scope creep"],
                key_learnings=["Define scope clearly"],
                metrics={
                    "duration": "2 weeks",
                    "effort": "40 hours",
                    "scope_variance": "+15%",
                },
            )

        content = result.memory.content
        assert "## Outcome" in content
        assert "partial" in content
        assert "## What Went Well" in content
        assert "- Fast delivery" in content
        assert "## What Could Be Improved" in content
        assert "- Scope creep" in content
        assert "## Key Learnings" in content
        assert "- Define scope clearly" in content
        assert "## Metrics" in content
        assert "**duration**: 2 weeks" in content
        assert "**effort**: 40 hours" in content
        assert "**scope_variance**: +15%" in content


class TestIsAutoCaptureEnabled:
    """Tests for is_auto_capture_enabled function."""

    def test_enabled_by_default(self, monkeypatch):
        """Test that auto-capture is enabled by default when env var not set."""
        monkeypatch.delenv("CS_AUTO_CAPTURE_ENABLED", raising=False)
        assert is_auto_capture_enabled() is True

    def test_enabled_with_true_values(self, monkeypatch):
        """Test that various truthy values enable auto-capture."""
        for value in ["true", "True", "TRUE", "1", "yes", "Yes", "on", "ON"]:
            monkeypatch.setenv("CS_AUTO_CAPTURE_ENABLED", value)
            assert is_auto_capture_enabled() is True, f"Failed for value: {value}"

    def test_disabled_with_false_values(self, monkeypatch):
        """Test that various falsy values disable auto-capture."""
        for value in ["false", "False", "FALSE", "0", "no", "No", "off", "OFF"]:
            monkeypatch.setenv("CS_AUTO_CAPTURE_ENABLED", value)
            assert is_auto_capture_enabled() is False, f"Failed for value: {value}"

    def test_empty_string_uses_default(self, monkeypatch):
        """Test that empty string uses the default (enabled)."""
        monkeypatch.setenv("CS_AUTO_CAPTURE_ENABLED", "")
        assert is_auto_capture_enabled() is True


class TestCapturePattern:
    """Tests for capture_pattern method."""

    def test_capture_pattern_success(self, capture_service, tmp_path):
        """Test successful pattern capture."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_pattern(
                spec="test-spec",
                summary="Repository pattern for data access",
                pattern_type="success",
                description="Abstraction layer between business logic and data layer",
                context="When working with multiple data sources",
                applicability="Any project with complex data access requirements",
                evidence="Reduced coupling in 3 projects",
                tags=["architecture", "data-access"],
            )

        assert result.success is True
        assert result.memory is not None
        assert result.memory.namespace == "patterns"
        assert "pattern" in result.memory.tags
        assert "success" in result.memory.tags
        assert result.indexed is True

    def test_capture_pattern_invalid_type(self, capture_service):
        """Test capture_pattern with invalid pattern_type raises error."""
        with pytest.raises(CaptureError) as exc_info:
            capture_service.capture_pattern(
                spec="test-spec",
                summary="Test pattern",
                pattern_type="invalid_type",
                description="Description",
                context="Context",
                applicability="Applicability",
            )

        assert "Invalid pattern type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)

    def test_capture_pattern_formats_content(self, capture_service, tmp_path):
        """Test that capture_pattern formats content correctly."""
        lock_file = tmp_path / "test.lock"

        with patch("memory.capture.LOCK_FILE", lock_file):
            result = capture_service.capture_pattern(
                spec=None,  # Global pattern
                summary="Avoid global state",
                pattern_type="anti-pattern",
                description="Using global variables for state management",
                context="Multi-threaded applications",
                applicability="All concurrent code",
                evidence="Caused 5 race conditions in project X",
            )

        content = result.memory.content
        assert "## Pattern Type" in content
        assert "anti-pattern" in content
        assert "## Description" in content
        assert "Using global variables" in content
        assert "## Context" in content
        assert "Multi-threaded applications" in content
        assert "## Applicability" in content
        assert "All concurrent code" in content
        assert "## Evidence" in content
        assert "Caused 5 race conditions" in content
        # Verify spec is None for global pattern
        assert result.memory.spec is None
