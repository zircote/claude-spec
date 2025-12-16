"""Memory lifecycle management module for cs-memory.

This module provides:
- Memory aging with decay scores
- Summarization of old memories
- Archival of completed spec memories
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from .models import Memory, MemoryResult


class MemoryState(Enum):
    """Lifecycle state of a memory."""

    ACTIVE = "active"  # Recent and highly relevant
    AGING = "aging"  # Starting to lose relevance
    STALE = "stale"  # Old but still searchable
    ARCHIVED = "archived"  # Compressed/summarized
    TOMBSTONE = "tombstone"  # Marked for deletion


@dataclass(frozen=True)
class AgingConfig:
    """Configuration for memory aging."""

    # Time thresholds (in days)
    active_threshold_days: float = 7.0  # Under 7 days = active
    aging_threshold_days: float = 30.0  # 7-30 days = aging
    stale_threshold_days: float = 90.0  # 30-90 days = stale

    # Decay parameters
    half_life_days: float = 30.0  # Time for 50% decay
    min_decay_score: float = 0.1  # Minimum score after decay

    # Summarization triggers
    summarize_after_days: float = 90.0
    max_memories_before_summarize: int = 100


@dataclass
class AgedMemory:
    """A memory with aging metadata."""

    memory: Memory | MemoryResult
    state: MemoryState
    decay_score: float  # 0.0 - 1.0, higher = more relevant
    age_days: float
    last_accessed: datetime | None = None
    access_count: int = 0


@dataclass
class MemorySummary:
    """A summarized collection of memories."""

    spec: str
    namespace: str
    memory_ids: tuple[str, ...]
    summary: str
    created: datetime
    original_count: int
    time_range_start: datetime
    time_range_end: datetime
    tags: tuple[str, ...] = field(default_factory=tuple)


class MemoryAger:
    """Calculates aging and decay for memories."""

    def __init__(self, config: AgingConfig | None = None) -> None:
        """Initialize the memory ager.

        Args:
            config: Aging configuration.
        """
        self._config = config or AgingConfig()

    def calculate_decay(self, timestamp: datetime | None) -> float:
        """Calculate decay score for a memory.

        Args:
            timestamp: The memory timestamp.

        Returns:
            Decay score between 0.1 and 1.0.
        """
        if timestamp is None:
            return 0.5  # Default for unknown timestamps

        now = datetime.now(UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        age = now - timestamp
        age_days = age.total_seconds() / 86400

        # Exponential decay: score = 2^(-age/half_life)
        decay = math.pow(2, -age_days / self._config.half_life_days)

        # Clamp to minimum
        return max(self._config.min_decay_score, decay)

    def determine_state(self, timestamp: datetime | None) -> MemoryState:
        """Determine the lifecycle state of a memory.

        Args:
            timestamp: The memory timestamp.

        Returns:
            The lifecycle state.
        """
        if timestamp is None:
            return MemoryState.AGING

        now = datetime.now(UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        age = now - timestamp
        age_days = age.total_seconds() / 86400

        if age_days < self._config.active_threshold_days:
            return MemoryState.ACTIVE
        elif age_days < self._config.aging_threshold_days:
            return MemoryState.AGING
        elif age_days < self._config.stale_threshold_days:
            return MemoryState.STALE
        else:
            return MemoryState.ARCHIVED

    def age_memory(self, memory: Memory | MemoryResult) -> AgedMemory:
        """Calculate aging for a single memory.

        Args:
            memory: The memory to age.

        Returns:
            AgedMemory with decay and state.
        """
        timestamp = memory.timestamp
        decay = self.calculate_decay(timestamp)
        state = self.determine_state(timestamp)

        now = datetime.now(UTC)
        if timestamp:
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            age_days = (now - timestamp).total_seconds() / 86400
        else:
            age_days = 0.0

        return AgedMemory(
            memory=memory,
            state=state,
            decay_score=decay,
            age_days=age_days,
        )

    def age_memories(self, memories: list[Memory | MemoryResult]) -> list[AgedMemory]:
        """Calculate aging for a list of memories.

        Args:
            memories: List of memories to age.

        Returns:
            List of AgedMemory objects.
        """
        return [self.age_memory(m) for m in memories]

    def filter_by_state(
        self,
        aged: list[AgedMemory],
        states: set[MemoryState],
    ) -> list[AgedMemory]:
        """Filter aged memories by state.

        Args:
            aged: List of aged memories.
            states: States to include.

        Returns:
            Filtered list.
        """
        return [a for a in aged if a.state in states]

    def sort_by_relevance(
        self,
        aged: list[AgedMemory],
        descending: bool = True,
    ) -> list[AgedMemory]:
        """Sort aged memories by decay score.

        Args:
            aged: List of aged memories.
            descending: If True, most relevant first.

        Returns:
            Sorted list.
        """
        return sorted(aged, key=lambda a: a.decay_score, reverse=descending)


class MemorySummarizer:
    """Creates summaries of memory collections."""

    def __init__(
        self,
        max_memories_per_summary: int = 50,
        min_memories_for_summary: int = 5,
    ) -> None:
        """Initialize the summarizer.

        Args:
            max_memories_per_summary: Maximum memories to include in one summary.
            min_memories_for_summary: Minimum memories needed to create a summary.
        """
        self._max_per_summary = max_memories_per_summary
        self._min_for_summary = min_memories_for_summary

    def should_summarize(
        self,
        memories: list[Memory | MemoryResult],
        threshold_days: float = 90.0,
    ) -> bool:
        """Determine if a set of memories should be summarized.

        Args:
            memories: Memories to check.
            threshold_days: Age threshold for summarization.

        Returns:
            True if summarization is recommended.
        """
        if len(memories) < self._min_for_summary:
            return False

        now = datetime.now(UTC)
        old_count = 0

        for mem in memories:
            if mem.timestamp:
                ts = mem.timestamp
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                age_days = (now - ts).total_seconds() / 86400
                if age_days > threshold_days:
                    old_count += 1

        # Summarize if more than half are old
        return old_count > len(memories) / 2

    def create_summary(
        self,
        spec: str,
        namespace: str,
        memories: list[Memory | MemoryResult],
    ) -> MemorySummary:
        """Create a summary from a collection of memories.

        Args:
            spec: The spec these memories belong to.
            namespace: The namespace of the memories.
            memories: Memories to summarize.

        Returns:
            MemorySummary object.
        """
        if not memories:
            raise ValueError("Cannot summarize empty memory list")

        # Collect metadata
        memory_ids = tuple(m.id for m in memories)
        all_tags: set[str] = set()
        timestamps: list[datetime] = []

        for mem in memories:
            if mem.tags:
                all_tags.update(mem.tags)
            if mem.timestamp:
                timestamps.append(mem.timestamp)

        # Determine time range
        if timestamps:
            time_start = min(timestamps)
            time_end = max(timestamps)
        else:
            now = datetime.now(UTC)
            time_start = now
            time_end = now

        # Generate summary text
        summary_text = self._generate_summary_text(namespace, memories)

        return MemorySummary(
            spec=spec,
            namespace=namespace,
            memory_ids=memory_ids,
            summary=summary_text,
            created=datetime.now(UTC),
            original_count=len(memories),
            time_range_start=time_start,
            time_range_end=time_end,
            tags=tuple(sorted(all_tags)),
        )

    def _generate_summary_text(
        self,
        namespace: str,
        memories: list[Memory | MemoryResult],
    ) -> str:
        """Generate summary text for memories.

        Args:
            namespace: The memory namespace.
            memories: Memories to summarize.

        Returns:
            Summary text.
        """
        lines = [f"Summary of {len(memories)} {namespace} memories:\n"]

        # Group by key themes/tags
        tag_counts: dict[str, int] = {}
        for mem in memories:
            for tag in mem.tags or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if tag_counts:
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            lines.append(f"Key themes: {', '.join(t[0] for t in top_tags)}\n")

        # Include abbreviated summaries
        lines.append("\nHighlights:")
        for mem in memories[:10]:  # Top 10 only
            summary = mem.summary[:80] + "..." if len(mem.summary) > 80 else mem.summary
            lines.append(f"  - {summary}")

        if len(memories) > 10:
            lines.append(f"  ... and {len(memories) - 10} more")

        return "\n".join(lines)


class ArchiveManager:
    """Manages archival of completed spec memories."""

    def __init__(
        self,
        ager: MemoryAger | None = None,
        summarizer: MemorySummarizer | None = None,
    ) -> None:
        """Initialize the archive manager.

        Args:
            ager: Memory ager instance.
            summarizer: Memory summarizer instance.
        """
        self._ager = ager or MemoryAger()
        self._summarizer = summarizer or MemorySummarizer()
        self._archived_specs: set[str] = set()

    def archive_spec(
        self,
        spec: str,
        memories: list[Memory | MemoryResult],
    ) -> dict[str, MemorySummary]:
        """Archive all memories for a completed spec.

        Args:
            spec: The spec to archive.
            memories: All memories for the spec.

        Returns:
            Dictionary of namespace -> summary.
        """
        summaries: dict[str, MemorySummary] = {}

        # Group by namespace
        by_namespace: dict[str, list[Memory | MemoryResult]] = {}
        for mem in memories:
            ns = mem.namespace
            if ns not in by_namespace:
                by_namespace[ns] = []
            by_namespace[ns].append(mem)

        # Create summary for each namespace
        for namespace, ns_memories in by_namespace.items():
            if ns_memories:
                summary = self._summarizer.create_summary(spec, namespace, ns_memories)
                summaries[namespace] = summary

        self._archived_specs.add(spec)
        return summaries

    def is_archived(self, spec: str) -> bool:
        """Check if a spec has been archived."""
        return spec in self._archived_specs

    def get_archived_specs(self) -> set[str]:
        """Get all archived specs."""
        return self._archived_specs.copy()


class LifecycleManager:
    """High-level lifecycle management coordinator."""

    def __init__(
        self,
        ager: MemoryAger | None = None,
        summarizer: MemorySummarizer | None = None,
        archive_manager: ArchiveManager | None = None,
        config: AgingConfig | None = None,
    ) -> None:
        """Initialize the lifecycle manager.

        Args:
            ager: Memory ager instance.
            summarizer: Memory summarizer instance.
            archive_manager: Archive manager instance.
            config: Aging configuration.
        """
        self._config = config or AgingConfig()
        self._ager = ager or MemoryAger(self._config)
        self._summarizer = summarizer or MemorySummarizer()
        self._archive = archive_manager or ArchiveManager(self._ager, self._summarizer)

    def process_memories(
        self,
        memories: list[Memory | MemoryResult],
    ) -> dict[str, Any]:
        """Process memories through the lifecycle.

        Args:
            memories: Memories to process.

        Returns:
            Processing results with statistics.
        """
        # Age all memories
        aged = self._ager.age_memories(memories)

        # Count by state
        state_counts: dict[str, int] = {}
        for a in aged:
            state_name = a.state.value
            state_counts[state_name] = state_counts.get(state_name, 0) + 1

        # Identify candidates for summarization
        stale = self._ager.filter_by_state(
            aged, {MemoryState.STALE, MemoryState.ARCHIVED}
        )
        needs_summarization = self._summarizer.should_summarize(
            [a.memory for a in stale]
        )

        # Calculate average decay
        avg_decay = sum(a.decay_score for a in aged) / len(aged) if aged else 0.0

        return {
            "total": len(memories),
            "by_state": state_counts,
            "average_decay": round(avg_decay, 3),
            "needs_summarization": needs_summarization,
            "stale_count": len(stale),
        }

    def get_relevant_memories(
        self,
        memories: list[Memory | MemoryResult],
        min_decay: float = 0.3,
    ) -> list[Memory | MemoryResult]:
        """Get memories that are still relevant (above decay threshold).

        Args:
            memories: Memories to filter.
            min_decay: Minimum decay score to include.

        Returns:
            List of relevant memories.
        """
        aged = self._ager.age_memories(memories)
        relevant = [a for a in aged if a.decay_score >= min_decay]
        return [a.memory for a in relevant]

    def archive_spec(
        self,
        spec: str,
        memories: list[Memory | MemoryResult],
    ) -> dict[str, MemorySummary]:
        """Archive a completed spec's memories."""
        return self._archive.archive_spec(spec, memories)

    def calculate_memory_score(
        self,
        memory: Memory | MemoryResult,
        base_score: float,
    ) -> float:
        """Calculate final relevance score with decay applied.

        Args:
            memory: The memory.
            base_score: The base similarity/relevance score.

        Returns:
            Adjusted score.
        """
        decay = self._ager.calculate_decay(memory.timestamp)
        # Lower base score is better (similarity), decay reduces the score further
        # But we want fresh memories to rank higher, so we subtract decay benefit
        return base_score * (2 - decay)


# Module-level singleton
_lifecycle_manager: LifecycleManager | None = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get or create the lifecycle manager singleton."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


def reset_lifecycle_manager() -> None:
    """Reset the lifecycle manager singleton for testing (ARCH-001).

    This function allows tests to reset the module-level singleton
    to ensure test isolation.
    """
    global _lifecycle_manager
    _lifecycle_manager = None
