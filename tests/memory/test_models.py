"""Tests for the memory models module."""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Add memory module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memory.models import (
    CaptureAccumulator,
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


class TestCaptureAccumulator:
    """Tests for CaptureAccumulator dataclass."""

    def _make_memory(
        self, id: str = "test:123", namespace: str = "decisions", summary: str = "Test"
    ) -> Memory:
        """Create a mock Memory object for testing."""
        return Memory(
            id=id,
            commit_sha=id.split(":")[1] if ":" in id else "123",
            namespace=namespace,
            summary=summary,
            content="Test content",
            timestamp=datetime.now(UTC),
        )

    def test_init_empty(self):
        """Verify initialization with empty captures list."""
        accumulator = CaptureAccumulator()

        assert accumulator.captures == []
        assert accumulator.start_time is not None
        assert isinstance(accumulator.start_time, datetime)

    def test_add_capture(self):
        """Verify add() method appends CaptureResult."""
        accumulator = CaptureAccumulator()
        memory = self._make_memory()
        result = CaptureResult(success=True, memory=memory, indexed=True)

        accumulator.add(result)

        assert len(accumulator.captures) == 1
        assert accumulator.captures[0] == result

        # Add another
        memory2 = self._make_memory(id="test:456", summary="Second test")
        result2 = CaptureResult(success=True, memory=memory2, indexed=True)
        accumulator.add(result2)

        assert len(accumulator.captures) == 2
        assert accumulator.captures[1] == result2

    def test_count_property(self):
        """Verify count returns number of captures."""
        accumulator = CaptureAccumulator()

        assert accumulator.count == 0

        # Add captures
        for i in range(5):
            memory = self._make_memory(id=f"test:{i}", summary=f"Test {i}")
            result = CaptureResult(success=True, memory=memory, indexed=True)
            accumulator.add(result)

        assert accumulator.count == 5

    def test_by_namespace_empty(self):
        """Verify by_namespace returns {} when empty."""
        accumulator = CaptureAccumulator()

        assert accumulator.by_namespace == {}

    def test_by_namespace_with_captures(self):
        """Verify by_namespace groups counts correctly."""
        accumulator = CaptureAccumulator()

        # Add 3 decisions
        for i in range(3):
            memory = self._make_memory(
                id=f"decisions:{i}", namespace="decisions", summary=f"Decision {i}"
            )
            result = CaptureResult(success=True, memory=memory, indexed=True)
            accumulator.add(result)

        # Add 2 learnings
        for i in range(2):
            memory = self._make_memory(
                id=f"learnings:{i}", namespace="learnings", summary=f"Learning {i}"
            )
            result = CaptureResult(success=True, memory=memory, indexed=True)
            accumulator.add(result)

        # Add 1 blocker
        memory = self._make_memory(
            id="blockers:0", namespace="blockers", summary="Blocker"
        )
        result = CaptureResult(success=True, memory=memory, indexed=True)
        accumulator.add(result)

        by_ns = accumulator.by_namespace

        assert by_ns["decisions"] == 3
        assert by_ns["learnings"] == 2
        assert by_ns["blockers"] == 1
        assert len(by_ns) == 3

    def test_summary_empty(self):
        """Verify summary() returns 'No memories captured' when empty."""
        accumulator = CaptureAccumulator()

        summary = accumulator.summary()

        assert summary == "No memories captured this session."

    def test_summary_with_captures(self):
        """Verify summary() formats correctly with captures."""
        accumulator = CaptureAccumulator()

        memory1 = self._make_memory(
            id="decisions:abc123",
            namespace="decisions",
            summary="Chose REST over GraphQL",
        )
        result1 = CaptureResult(success=True, memory=memory1, indexed=True)
        accumulator.add(result1)

        memory2 = self._make_memory(
            id="learnings:def456",
            namespace="learnings",
            summary="Pytest fixtures are powerful",
        )
        result2 = CaptureResult(success=True, memory=memory2, indexed=True)
        accumulator.add(result2)

        summary = accumulator.summary()

        # Verify structure
        assert "Memory Capture Summary" in summary
        assert "Captured: 2 memories" in summary
        assert "decisions:abc123" in summary
        assert "Chose REST over GraphQL" in summary
        assert "learnings:def456" in summary
        assert "Pytest fixtures are powerful" in summary
        # Check for success markers
        lines = summary.split("\n")
        capture_lines = [
            line for line in lines if "decisions:" in line or "learnings:" in line
        ]
        for line in capture_lines:
            assert line.strip().startswith("✓")

    def test_summary_with_warnings(self):
        """Verify summary() includes warnings for failed captures."""
        accumulator = CaptureAccumulator()

        # Add a successful capture
        memory1 = self._make_memory(
            id="decisions:abc123", namespace="decisions", summary="Good decision"
        )
        result1 = CaptureResult(success=True, memory=memory1, indexed=True)
        accumulator.add(result1)

        # Add a failed capture with warning (no memory)
        result2 = CaptureResult(
            success=False,
            memory=None,
            indexed=False,
            warning="Git notes failed: permission denied",
        )
        accumulator.add(result2)

        # Add a capture with warning but still has memory (degraded mode)
        memory3 = self._make_memory(
            id="learnings:ghi789", namespace="learnings", summary="Partial success"
        )
        result3 = CaptureResult(
            success=True,
            memory=memory3,
            indexed=False,
            warning="Embedding failed, memory saved to git only.",
        )
        accumulator.add(result3)

        summary = accumulator.summary()

        # Verify all entries present
        assert "Captured: 3 memories" in summary
        assert "decisions:abc123" in summary
        assert "Good decision" in summary
        assert "Git notes failed: permission denied" in summary
        assert "learnings:ghi789" in summary
        assert "Partial success" in summary
        # Check warning marker present
        assert "⚠" in summary
