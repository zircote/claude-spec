"""Tests for the memory lifecycle module."""

from datetime import UTC, datetime, timedelta

import pytest

from memory.lifecycle import (
    ArchiveManager,
    LifecycleManager,
    MemoryAger,
    MemoryState,
    MemorySummarizer,
)
from memory.models import Memory, MemoryResult


def make_memory_result(
    memory_id: str,
    namespace: str,
    summary: str,
    score: float,
    content: str = "Test content",
    timestamp: datetime | None = None,
    spec: str | None = None,
    tags: tuple[str, ...] = (),
) -> MemoryResult:
    """Helper to create MemoryResult with proper Memory wrapper."""
    commit_sha = memory_id.split(":")[-1] if ":" in memory_id else "abc123"
    memory = Memory(
        id=memory_id,
        commit_sha=commit_sha,
        namespace=namespace,
        summary=summary,
        content=content,
        timestamp=timestamp or datetime.now(UTC),
        spec=spec,
        tags=tags,
    )
    return MemoryResult(memory=memory, distance=score)


class TestMemoryAger:
    """Tests for MemoryAger."""

    def test_active_memory_state(self):
        """Test that recent memories are marked active."""
        ager = MemoryAger()
        recent = datetime.now(UTC) - timedelta(days=1)
        memory = make_memory_result(
            "test:1", "decisions", "Recent memory", 0.5, timestamp=recent
        )

        aged = ager.age_memory(memory)

        assert aged.state == MemoryState.ACTIVE
        assert aged.decay_score > 0.9  # Should be high for recent

    def test_aging_memory_state(self):
        """Test that older memories are marked aging."""
        ager = MemoryAger()
        older = datetime.now(UTC) - timedelta(days=15)
        memory = make_memory_result(
            "test:1", "decisions", "Older memory", 0.5, timestamp=older
        )

        aged = ager.age_memory(memory)

        assert aged.state == MemoryState.AGING

    def test_stale_memory_state(self):
        """Test that old memories are marked stale."""
        ager = MemoryAger()
        old = datetime.now(UTC) - timedelta(days=60)
        memory = make_memory_result(
            "test:1", "decisions", "Old memory", 0.5, timestamp=old
        )

        aged = ager.age_memory(memory)

        assert aged.state == MemoryState.STALE

    def test_archived_memory_state(self):
        """Test that very old memories are marked archived."""
        ager = MemoryAger()
        very_old = datetime.now(UTC) - timedelta(days=120)
        memory = make_memory_result(
            "test:1", "decisions", "Very old memory", 0.5, timestamp=very_old
        )

        aged = ager.age_memory(memory)

        assert aged.state == MemoryState.ARCHIVED

    def test_decay_score_decreases_with_age(self):
        """Test that decay score decreases with age."""
        ager = MemoryAger()
        now = datetime.now(UTC)

        recent = make_memory_result(
            "test:1", "decisions", "Recent", 0.5, timestamp=now - timedelta(days=1)
        )
        older = make_memory_result(
            "test:2", "decisions", "Older", 0.5, timestamp=now - timedelta(days=60)
        )

        recent_aged = ager.age_memory(recent)
        older_aged = ager.age_memory(older)

        assert recent_aged.decay_score > older_aged.decay_score

    def test_min_decay_score(self):
        """Test that decay score has a minimum."""
        ager = MemoryAger()
        ancient = datetime.now(UTC) - timedelta(days=365)
        memory = make_memory_result(
            "test:1", "decisions", "Ancient", 0.5, timestamp=ancient
        )

        aged = ager.age_memory(memory)

        assert aged.decay_score >= 0.1  # Configured minimum

    def test_filter_by_state(self):
        """Test filtering memories by state."""
        ager = MemoryAger()
        now = datetime.now(UTC)
        memories = [
            make_memory_result(
                "test:1", "decisions", "Recent", 0.5, timestamp=now - timedelta(days=1)
            ),
            make_memory_result(
                "test:2", "decisions", "Old", 0.5, timestamp=now - timedelta(days=60)
            ),
        ]

        aged = ager.age_memories(memories)
        active_only = ager.filter_by_state(aged, {MemoryState.ACTIVE})

        assert len(active_only) == 1
        assert active_only[0].state == MemoryState.ACTIVE

    def test_sort_by_relevance(self):
        """Test sorting memories by decay score."""
        ager = MemoryAger()
        now = datetime.now(UTC)
        memories = [
            make_memory_result(
                "test:1", "decisions", "Old", 0.5, timestamp=now - timedelta(days=60)
            ),
            make_memory_result(
                "test:2", "decisions", "Recent", 0.5, timestamp=now - timedelta(days=1)
            ),
        ]

        aged = ager.age_memories(memories)
        sorted_aged = ager.sort_by_relevance(aged)

        # Most relevant (recent) should be first
        assert sorted_aged[0].memory.summary == "Recent"


class TestMemorySummarizer:
    """Tests for MemorySummarizer."""

    def test_should_summarize_old_memories(self):
        """Test that old memories trigger summarization."""
        summarizer = MemorySummarizer(min_memories_for_summary=2)
        now = datetime.now(UTC)
        memories = [
            make_memory_result(
                "test:1", "decisions", "Old 1", 0.5, timestamp=now - timedelta(days=100)
            ),
            make_memory_result(
                "test:2", "decisions", "Old 2", 0.5, timestamp=now - timedelta(days=100)
            ),
        ]

        assert summarizer.should_summarize(memories, threshold_days=90)

    def test_should_not_summarize_recent_memories(self):
        """Test that recent memories don't trigger summarization."""
        summarizer = MemorySummarizer(min_memories_for_summary=2)
        now = datetime.now(UTC)
        memories = [
            make_memory_result(
                "test:1",
                "decisions",
                "Recent 1",
                0.5,
                timestamp=now - timedelta(days=10),
            ),
            make_memory_result(
                "test:2",
                "decisions",
                "Recent 2",
                0.5,
                timestamp=now - timedelta(days=10),
            ),
        ]

        assert not summarizer.should_summarize(memories, threshold_days=90)

    def test_create_summary(self):
        """Test creating a summary."""
        summarizer = MemorySummarizer()
        now = datetime.now(UTC)
        memories = [
            make_memory_result(
                "test:1",
                "decisions",
                "Decision about auth",
                0.5,
                timestamp=now - timedelta(days=100),
                tags=("auth", "security"),
            ),
            make_memory_result(
                "test:2",
                "decisions",
                "Decision about tokens",
                0.5,
                timestamp=now - timedelta(days=95),
                tags=("auth", "jwt"),
            ),
        ]

        summary = summarizer.create_summary("test-spec", "decisions", memories)

        assert summary.spec == "test-spec"
        assert summary.namespace == "decisions"
        assert summary.original_count == 2
        assert len(summary.memory_ids) == 2
        assert "auth" in summary.tags

    def test_cannot_summarize_empty_list(self):
        """Test that empty list raises error."""
        summarizer = MemorySummarizer()

        with pytest.raises(ValueError):
            summarizer.create_summary("test-spec", "decisions", [])


class TestArchiveManager:
    """Tests for ArchiveManager."""

    def test_archive_spec(self):
        """Test archiving a spec's memories."""
        manager = ArchiveManager()
        now = datetime.now(UTC)
        memories = [
            make_memory_result("test:1", "decisions", "Decision 1", 0.5, timestamp=now),
            make_memory_result("test:2", "learnings", "Learning 1", 0.5, timestamp=now),
        ]

        summaries = manager.archive_spec("test-spec", memories)

        assert "decisions" in summaries
        assert "learnings" in summaries
        assert manager.is_archived("test-spec")

    def test_is_archived(self):
        """Test checking if spec is archived."""
        manager = ArchiveManager()

        assert not manager.is_archived("unarchived-spec")

        manager.archive_spec(
            "archived-spec", [make_memory_result("test:1", "decisions", "Test", 0.5)]
        )

        assert manager.is_archived("archived-spec")

    def test_get_archived_specs(self):
        """Test getting list of archived specs."""
        manager = ArchiveManager()
        now = datetime.now(UTC)

        manager.archive_spec(
            "spec1", [make_memory_result("t:1", "d", "T", 0.5, timestamp=now)]
        )
        manager.archive_spec(
            "spec2", [make_memory_result("t:2", "d", "T", 0.5, timestamp=now)]
        )

        archived = manager.get_archived_specs()

        assert "spec1" in archived
        assert "spec2" in archived


class TestLifecycleManager:
    """Tests for LifecycleManager."""

    def test_process_memories(self):
        """Test processing memories through lifecycle."""
        manager = LifecycleManager()
        now = datetime.now(UTC)
        memories = [
            make_memory_result(
                "test:1", "decisions", "Recent", 0.5, timestamp=now - timedelta(days=1)
            ),
            make_memory_result(
                "test:2", "decisions", "Old", 0.5, timestamp=now - timedelta(days=60)
            ),
        ]

        result = manager.process_memories(memories)

        assert result["total"] == 2
        assert "by_state" in result
        assert "average_decay" in result
        assert "needs_summarization" in result

    def test_get_relevant_memories(self):
        """Test filtering to relevant memories."""
        manager = LifecycleManager()
        now = datetime.now(UTC)
        memories = [
            make_memory_result(
                "test:1", "decisions", "Recent", 0.5, timestamp=now - timedelta(days=1)
            ),
            make_memory_result(
                "test:2",
                "decisions",
                "Ancient",
                0.5,
                timestamp=now - timedelta(days=365),
            ),
        ]

        relevant = manager.get_relevant_memories(memories, min_decay=0.5)

        # Only the recent one should pass the decay threshold
        assert len(relevant) == 1
        assert relevant[0].summary == "Recent"

    def test_calculate_memory_score(self):
        """Test calculating memory score with decay."""
        manager = LifecycleManager()
        now = datetime.now(UTC)

        recent = make_memory_result(
            "test:1", "decisions", "Recent", 0.5, timestamp=now - timedelta(days=1)
        )
        old = make_memory_result(
            "test:2", "decisions", "Old", 0.5, timestamp=now - timedelta(days=60)
        )

        recent_score = manager.calculate_memory_score(recent, 0.5)
        old_score = manager.calculate_memory_score(old, 0.5)

        # Recent should have better (lower) score
        assert recent_score < old_score
