"""Tests for the memory models module."""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Add memory module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memory.models import (
    CaptureResult,
    HydratedMemory,
    HydrationLevel,
    IndexStats,
    Memory,
    MemoryResult,
    ReviewFinding,
    SpecContext,
    VerificationResult,
)


class TestMemory:
    """Tests for Memory dataclass."""

    def test_memory_creation(self):
        """Test basic Memory creation."""
        timestamp = datetime.now(UTC)
        memory = Memory(
            id="decisions:abc123",
            commit_sha="abc123",
            namespace="decisions",
            summary="Test decision",
            content="Full content here.",
            timestamp=timestamp,
        )

        assert memory.id == "decisions:abc123"
        assert memory.commit_sha == "abc123"
        assert memory.namespace == "decisions"
        assert memory.summary == "Test decision"
        assert memory.content == "Full content here."
        assert memory.timestamp == timestamp
        assert memory.spec is None
        assert memory.tags == ()

    def test_memory_with_all_fields(self):
        """Test Memory with all optional fields."""
        timestamp = datetime.now(UTC)
        memory = Memory(
            id="blockers:def456",
            commit_sha="def456",
            namespace="blockers",
            summary="Blocked on API",
            content="Cannot proceed.",
            timestamp=timestamp,
            spec="user-auth",
            phase="implementation",
            tags=("api", "blocking"),
            status="unresolved",
            relates_to=("abc123",),
        )

        assert memory.spec == "user-auth"
        assert memory.phase == "implementation"
        assert memory.tags == ("api", "blocking")
        assert memory.status == "unresolved"
        assert memory.relates_to == ("abc123",)

    def test_memory_is_frozen(self):
        """Test that Memory is immutable."""
        memory = Memory(
            id="test:123",
            commit_sha="123",
            namespace="test",
            summary="Test",
            content="Content",
            timestamp=datetime.now(UTC),
        )

        with pytest.raises(AttributeError):
            memory.summary = "New summary"


class TestMemoryResult:
    """Tests for MemoryResult dataclass."""

    def test_memory_result_creation(self):
        """Test MemoryResult creation."""
        memory = Memory(
            id="test:123",
            commit_sha="123",
            namespace="decisions",
            summary="Test",
            content="Content",
            timestamp=datetime.now(UTC),
        )

        result = MemoryResult(memory=memory, distance=0.123)

        assert result.memory == memory
        assert result.distance == 0.123

    def test_memory_result_is_frozen(self):
        """Test that MemoryResult is immutable."""
        memory = Memory(
            id="test:123",
            commit_sha="123",
            namespace="decisions",
            summary="Test",
            content="Content",
            timestamp=datetime.now(UTC),
        )
        result = MemoryResult(memory=memory, distance=0.5)

        with pytest.raises(AttributeError):
            result.distance = 0.1


class TestHydrationLevel:
    """Tests for HydrationLevel enum."""

    def test_hydration_level_values(self):
        """Test hydration level ordering."""
        assert HydrationLevel.SUMMARY.value == 1
        assert HydrationLevel.FULL.value == 2
        assert HydrationLevel.FILES.value == 3

    def test_hydration_level_comparison(self):
        """Test that levels can be compared."""
        assert HydrationLevel.SUMMARY.value < HydrationLevel.FULL.value
        assert HydrationLevel.FULL.value < HydrationLevel.FILES.value


class TestHydratedMemory:
    """Tests for HydratedMemory dataclass."""

    def test_hydrated_memory_level1(self):
        """Test Level 1 hydration (summary only)."""
        memory = Memory(
            id="test:123",
            commit_sha="123",
            namespace="decisions",
            summary="Test",
            content="Content",
            timestamp=datetime.now(UTC),
        )
        result = MemoryResult(memory=memory, distance=0.1)

        hydrated = HydratedMemory(result=result)

        assert hydrated.result == result
        assert hydrated.full_content is None
        assert hydrated.files == {}
        assert hydrated.commit_info == {}

    def test_hydrated_memory_level2(self):
        """Test Level 2 hydration (with full content)."""
        memory = Memory(
            id="test:123",
            commit_sha="123",
            namespace="decisions",
            summary="Test",
            content="Content",
            timestamp=datetime.now(UTC),
        )
        result = MemoryResult(memory=memory, distance=0.1)

        hydrated = HydratedMemory(
            result=result,
            full_content="---\ntype: decision\n---\nFull note content.",
        )

        assert hydrated.full_content is not None
        assert "Full note content" in hydrated.full_content

    def test_hydrated_memory_level3(self):
        """Test Level 3 hydration (with files)."""
        memory = Memory(
            id="test:123",
            commit_sha="123",
            namespace="decisions",
            summary="Test",
            content="Content",
            timestamp=datetime.now(UTC),
        )
        result = MemoryResult(memory=memory, distance=0.1)

        hydrated = HydratedMemory(
            result=result,
            full_content="Full content",
            files={"src/main.py": "print('hello')"},
            commit_info={"author": "Test", "message": "Test commit"},
        )

        assert "src/main.py" in hydrated.files
        assert hydrated.commit_info["author"] == "Test"


class TestSpecContext:
    """Tests for SpecContext dataclass."""

    def test_spec_context_creation(self):
        """Test SpecContext creation."""
        memories = {
            "decisions": [
                Memory(
                    id="d:1",
                    commit_sha="1",
                    namespace="decisions",
                    summary="Dec 1",
                    content="Content",
                    timestamp=datetime.now(UTC),
                )
            ],
            "learnings": [],
        }

        context = SpecContext(
            spec="user-auth",
            memories=memories,
            total_count=1,
            token_estimate=100,
        )

        assert context.spec == "user-auth"
        assert len(context.memories["decisions"]) == 1
        assert context.total_count == 1
        assert context.token_estimate == 100


class TestIndexStats:
    """Tests for IndexStats dataclass."""

    def test_index_stats_creation(self):
        """Test IndexStats creation."""
        stats = IndexStats(
            total_memories=42,
            by_namespace={"decisions": 20, "learnings": 22},
            by_spec={"user-auth": 30, "api-design": 12},
            last_sync=datetime.now(UTC),
            index_size_bytes=1024 * 1024,
        )

        assert stats.total_memories == 42
        assert stats.by_namespace["decisions"] == 20
        assert stats.by_spec["user-auth"] == 30
        assert stats.index_size_bytes == 1024 * 1024


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_consistent_result(self):
        """Test consistent verification result."""
        result = VerificationResult(
            is_consistent=True,
            missing_in_index=(),
            orphaned_in_index=(),
            mismatched=(),
        )

        assert result.is_consistent is True
        assert len(result.missing_in_index) == 0

    def test_inconsistent_result(self):
        """Test inconsistent verification result."""
        result = VerificationResult(
            is_consistent=False,
            missing_in_index=("d:123", "d:456"),
            orphaned_in_index=("l:789",),
            mismatched=(),
        )

        assert result.is_consistent is False
        assert len(result.missing_in_index) == 2
        assert len(result.orphaned_in_index) == 1


class TestCaptureResult:
    """Tests for CaptureResult dataclass."""

    def test_successful_capture(self):
        """Test successful capture result."""
        memory = Memory(
            id="test:123",
            commit_sha="123",
            namespace="decisions",
            summary="Test",
            content="Content",
            timestamp=datetime.now(UTC),
        )

        result = CaptureResult(
            success=True,
            memory=memory,
            indexed=True,
        )

        assert result.success is True
        assert result.memory is not None
        assert result.indexed is True
        assert result.warning is None

    def test_capture_with_warning(self):
        """Test capture with warning (degraded mode)."""
        memory = Memory(
            id="test:123",
            commit_sha="123",
            namespace="decisions",
            summary="Test",
            content="Content",
            timestamp=datetime.now(UTC),
        )

        result = CaptureResult(
            success=True,
            memory=memory,
            indexed=False,
            warning="Embedding failed, memory saved to git only.",
        )

        assert result.success is True
        assert result.indexed is False
        assert result.warning is not None


class TestReviewFinding:
    """Tests for ReviewFinding dataclass."""

    def test_review_finding_creation(self):
        """Test ReviewFinding creation."""
        finding = ReviewFinding(
            id="uuid-123",
            severity="high",
            category="security",
            file="src/auth.py",
            line=42,
            summary="SQL injection vulnerability",
            details="User input not sanitized in query.",
        )

        assert finding.id == "uuid-123"
        assert finding.severity == "high"
        assert finding.category == "security"
        assert finding.status == "open"
        assert finding.resolution is None

    def test_resolved_finding(self):
        """Test resolved ReviewFinding."""
        finding = ReviewFinding(
            id="uuid-123",
            severity="high",
            category="security",
            file="src/auth.py",
            line=42,
            summary="SQL injection",
            details="Details",
            status="resolved",
            resolution="Used parameterized queries.",
        )

        assert finding.status == "resolved"
        assert finding.resolution == "Used parameterized queries."
