"""
Data models for cs-memory.

These dataclasses define the core domain objects used throughout the memory system.
All models are immutable (frozen) to ensure thread-safety and prevent accidental mutation.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class HydrationLevel(Enum):
    """
    Progressive hydration levels for memory recall.

    SUMMARY: Only metadata and one-line summary (fast, minimal context)
    FULL: Complete note content from git notes show
    FILES: Full content plus file snapshots from the commit
    """

    SUMMARY = 1
    FULL = 2
    FILES = 3


@dataclass(frozen=True)
class Memory:
    """
    Core memory object representing a captured piece of context.

    Attributes:
        id: Unique identifier in format <namespace>:<commit_sha>
        commit_sha: Git commit this memory is attached to
        namespace: Memory type (decisions, learnings, blockers, etc.)
        spec: Specification slug this memory belongs to (may be None for global)
        phase: Lifecycle phase (planning, implementation, review, etc.)
        summary: One-line summary (max 100 chars)
        content: Full markdown content of the note
        tags: Categorization tags
        timestamp: When the memory was captured
        status: For blockers - unresolved/resolved; for reviews - open/resolved
    """

    id: str
    commit_sha: str
    namespace: str
    summary: str
    content: str
    timestamp: datetime
    spec: str | None = None
    phase: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    status: str | None = None
    relates_to: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MemoryResult:
    """
    A memory with its semantic similarity score from vector search.

    Attributes:
        memory: The recalled memory
        distance: Euclidean distance from query vector (lower = more similar)

    This class provides convenience properties to access the underlying Memory
    fields directly, allowing uniform access patterns across Memory and MemoryResult.
    """

    memory: Memory
    distance: float

    # Convenience properties for uniform access with Memory
    @property
    def id(self) -> str:
        return self.memory.id

    @property
    def commit_sha(self) -> str:
        return self.memory.commit_sha

    @property
    def namespace(self) -> str:
        return self.memory.namespace

    @property
    def summary(self) -> str:
        return self.memory.summary

    @property
    def content(self) -> str:
        return self.memory.content

    @property
    def timestamp(self) -> datetime:
        return self.memory.timestamp

    @property
    def spec(self) -> str | None:
        return self.memory.spec

    @property
    def phase(self) -> str | None:
        return self.memory.phase

    @property
    def tags(self) -> tuple[str, ...]:
        return self.memory.tags

    @property
    def status(self) -> str | None:
        return self.memory.status

    @property
    def relates_to(self) -> tuple[str, ...]:
        return self.memory.relates_to

    @property
    def score(self) -> float:
        """Alias for distance for semantic compatibility."""
        return self.distance


@dataclass(frozen=True)
class HydratedMemory:
    """
    A fully hydrated memory with additional context.

    Attributes:
        result: The base memory result
        full_content: Complete note content (Level 2+)
        files: Dict of file paths to content snapshots (Level 3)
        commit_info: Commit metadata (author, date, message)
    """

    result: MemoryResult
    full_content: str | None = None
    files: dict[str, str] = field(default_factory=dict)
    commit_info: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SpecContext:
    """
    All memories for a specification, organized for context loading.

    Attributes:
        spec: Specification slug
        memories: All memories grouped by namespace
        total_count: Total number of memories
        token_estimate: Estimated token count for all content
    """

    spec: str
    memories: dict[str, list[Memory]]
    total_count: int
    token_estimate: int


@dataclass(frozen=True)
class IndexStats:
    """
    Statistics about the memory index.

    Attributes:
        total_memories: Total number of indexed memories
        by_namespace: Count per namespace
        by_spec: Count per specification
        last_sync: Timestamp of last synchronization
        index_size_bytes: Size of the SQLite database
    """

    total_memories: int
    by_namespace: dict[str, int]
    by_spec: dict[str, int]
    last_sync: datetime | None
    index_size_bytes: int


@dataclass(frozen=True)
class VerificationResult:
    """
    Result of verifying index consistency against Git notes.

    Attributes:
        is_consistent: True if index matches notes
        missing_in_index: Memory IDs in notes but not in index
        orphaned_in_index: Memory IDs in index but not in notes
        mismatched: Memory IDs with different content
    """

    is_consistent: bool
    missing_in_index: tuple[str, ...]
    orphaned_in_index: tuple[str, ...]
    mismatched: tuple[str, ...]


@dataclass(frozen=True)
class CaptureResult:
    """
    Result of a memory capture operation.

    Attributes:
        success: Whether the capture completed
        memory: The captured memory (if successful)
        indexed: Whether the memory was added to the search index
        warning: Optional warning message (e.g., embedding failed)
    """

    success: bool
    memory: Memory | None = None
    indexed: bool = False
    warning: str | None = None


@dataclass(frozen=True)
class ReviewFinding:
    """
    A single code review finding.

    Attributes:
        id: UUID for the finding
        severity: critical/high/medium/low
        category: security/performance/architecture/quality/tests/documentation
        file: File path where issue was found
        line: Line number
        summary: One-line description
        details: Full finding with remediation guidance
        status: open/resolved
        resolution: How the issue was resolved (when status=resolved)
    """

    id: str
    severity: str
    category: str
    file: str
    line: int
    summary: str
    details: str
    status: str = "open"
    resolution: str | None = None


@dataclass
class CaptureAccumulator:
    """
    Tracks captures during a command execution for summary display.

    This is a mutable container (NOT frozen) that accumulates CaptureResults
    as they are captured during a command session.

    Attributes:
        captures: List of CaptureResult objects from this session
        start_time: When the accumulator was created
    """

    captures: list[CaptureResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))

    def add(self, result: CaptureResult) -> None:
        """Add a capture result to the accumulator."""
        self.captures.append(result)

    @property
    def count(self) -> int:
        """Return the number of captures."""
        return len(self.captures)

    @property
    def by_namespace(self) -> dict[str, int]:
        """Group capture counts by namespace."""
        counts: dict[str, int] = {}
        for capture in self.captures:
            if capture.memory:
                ns = capture.memory.namespace
                counts[ns] = counts.get(ns, 0) + 1
        return counts

    def summary(self) -> str:
        """Generate a summary string for display."""
        if not self.captures:
            return "No memories captured this session."

        lines = [
            "────────────────────────────────────────────────────────────────",
            "Memory Capture Summary",
            "────────────────────────────────────────────────────────────────",
            f"Captured: {self.count} memories",
        ]

        for capture in self.captures:
            if capture.memory:
                status = "✓" if capture.success else "✗"
                lines.append(
                    f"  {status} {capture.memory.id} - {capture.memory.summary}"
                )
            elif capture.warning:
                lines.append(f"  ⚠ {capture.warning}")

        lines.append("────────────────────────────────────────────────────────────────")
        return "\n".join(lines)
