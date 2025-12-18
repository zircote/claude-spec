"""
Performance benchmarks for cs-memory search.

These tests validate search performance meets requirements:
- Search latency: <100ms for typical queries (target: 50ms p95)
- Index operations: Insert/update should complete quickly
- Embedding generation: Batch processing should be efficient

Run with: uv run pytest tests/memory/test_benchmark.py -v -s
"""

import os
import statistics
import time
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from memory.config import EMBEDDING_DIMENSIONS
from memory.index import IndexService
from memory.models import Memory

# Detect CI environment (GitHub Actions, GitLab CI, etc.)
IS_CI = any(
    os.environ.get(var)
    for var in ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "TRAVIS")
)

# CI multiplier for performance targets (CI runners are often slower/variable)
CI_MULTIPLIER = 5 if IS_CI else 1

# Performance targets (milliseconds)
SEARCH_P95_TARGET_MS = 100 * CI_MULTIPLIER  # 95th percentile search latency
INSERT_P95_TARGET_MS = 50 * CI_MULTIPLIER  # 95th percentile insert latency
BATCH_INSERT_TARGET_MS = 500 * CI_MULTIPLIER  # 100 memories batch insert


def make_memory(idx: int, namespace: str = "decisions") -> Memory:
    """Create a test Memory object with unique ID."""
    return Memory(
        id=f"{namespace}:commit{idx:06d}",
        commit_sha=f"commit{idx:06d}",
        namespace=namespace,
        spec=f"spec-{idx % 10}",  # 10 different specs
        phase="planning" if idx % 2 == 0 else "implementation",
        summary=f"Test memory summary number {idx} with searchable content",
        content=f"Full content for memory {idx}. This includes detailed description "
        f"of the decision, context, and rationale. Keywords: auth, api, db, cache.",
        tags=(f"tag{idx % 5}", f"category{idx % 3}"),
        timestamp=datetime.now(UTC),
        status="active" if idx % 3 != 0 else None,
    )


def make_embedding(idx: int) -> list[float]:
    """Create deterministic test embedding vector."""
    # Create varied but deterministic embeddings
    base = (idx % 100) / 100.0
    return [base + (i % 10) / 1000.0 for i in range(EMBEDDING_DIMENSIONS)]


def measure_latency(func: Callable, iterations: int = 100) -> dict:
    """
    Measure latency statistics for a function.

    Returns dict with min, max, mean, p50, p95, p99 in milliseconds.
    """
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # Convert to ms

    latencies_sorted = sorted(latencies)
    return {
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "mean_ms": statistics.mean(latencies),
        "p50_ms": latencies_sorted[int(len(latencies) * 0.50)],
        "p95_ms": latencies_sorted[int(len(latencies) * 0.95)],
        "p99_ms": latencies_sorted[int(len(latencies) * 0.99)],
    }


@pytest.fixture
def populated_index(tmp_path):
    """Create an IndexService with 100 memories for benchmarking."""
    db_path = tmp_path / "benchmark.db"
    service = IndexService(db_path=db_path)
    service.initialize()

    # Insert 100 memories
    for i in range(100):
        memory = make_memory(i)
        embedding = make_embedding(i)
        service.insert(memory, embedding)

    yield service
    service.close()


@pytest.fixture
def large_index(tmp_path):
    """Create an IndexService with 500 memories for stress testing."""
    db_path = tmp_path / "benchmark_large.db"
    service = IndexService(db_path=db_path)
    service.initialize()

    # Insert 500 memories
    for i in range(500):
        memory = make_memory(i)
        embedding = make_embedding(i)
        service.insert(memory, embedding)

    yield service
    service.close()


class TestSearchPerformance:
    """Benchmark search operation latency."""

    def test_search_latency_100_memories(self, populated_index):
        """Test search latency with 100 memories."""
        query_embedding = make_embedding(50)  # Middle embedding

        def search():
            populated_index.search_vector(query_embedding, limit=10)

        stats = measure_latency(search, iterations=50)

        print("\n[100 memories] Search latency stats:")
        print(f"  Min: {stats['min_ms']:.2f}ms")
        print(f"  P50: {stats['p50_ms']:.2f}ms")
        print(f"  P95: {stats['p95_ms']:.2f}ms")
        print(f"  Max: {stats['max_ms']:.2f}ms")

        assert stats["p95_ms"] < SEARCH_P95_TARGET_MS, (
            f"Search P95 ({stats['p95_ms']:.2f}ms) exceeds target ({SEARCH_P95_TARGET_MS}ms)"
        )

    def test_search_latency_500_memories(self, large_index):
        """Test search latency with 500 memories."""
        query_embedding = make_embedding(250)  # Middle embedding

        def search():
            large_index.search_vector(query_embedding, limit=10)

        stats = measure_latency(search, iterations=50)

        print("\n[500 memories] Search latency stats:")
        print(f"  Min: {stats['min_ms']:.2f}ms")
        print(f"  P50: {stats['p50_ms']:.2f}ms")
        print(f"  P95: {stats['p95_ms']:.2f}ms")
        print(f"  Max: {stats['max_ms']:.2f}ms")

        # Allow slightly higher latency for larger index
        assert stats["p95_ms"] < SEARCH_P95_TARGET_MS * 2, (
            f"Search P95 ({stats['p95_ms']:.2f}ms) exceeds target ({SEARCH_P95_TARGET_MS * 2}ms)"
        )

    def test_search_with_filters(self, populated_index):
        """Test search latency with namespace/spec filters."""
        query_embedding = make_embedding(50)

        def search_filtered():
            populated_index.search_vector(
                query_embedding,
                filters={"namespace": "decisions", "spec": "spec-5"},
                limit=10,
            )

        stats = measure_latency(search_filtered, iterations=50)

        print("\n[Filtered search] Latency stats:")
        print(f"  Min: {stats['min_ms']:.2f}ms")
        print(f"  P50: {stats['p50_ms']:.2f}ms")
        print(f"  P95: {stats['p95_ms']:.2f}ms")

        assert stats["p95_ms"] < SEARCH_P95_TARGET_MS


class TestInsertPerformance:
    """Benchmark insert operation latency."""

    def test_single_insert_latency(self, tmp_path):
        """Test single memory insert latency."""
        db_path = tmp_path / "insert_test.db"
        service = IndexService(db_path=db_path)
        service.initialize()

        latencies = []
        for i in range(100):
            memory = make_memory(i)
            embedding = make_embedding(i)

            start = time.perf_counter()
            service.insert(memory, embedding)
            end = time.perf_counter()

            latencies.append((end - start) * 1000)

        service.close()

        latencies_sorted = sorted(latencies)
        p95 = latencies_sorted[int(len(latencies) * 0.95)]

        print("\n[Single insert] Latency stats:")
        print(f"  Min: {min(latencies):.2f}ms")
        print(f"  P50: {latencies_sorted[50]:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")

        assert p95 < INSERT_P95_TARGET_MS, (
            f"Insert P95 ({p95:.2f}ms) exceeds target ({INSERT_P95_TARGET_MS}ms)"
        )

    def test_batch_insert_100_memories(self, tmp_path):
        """Test batch insert of 100 memories."""
        db_path = tmp_path / "batch_test.db"
        service = IndexService(db_path=db_path)
        service.initialize()

        memories = [make_memory(i) for i in range(100)]
        embeddings = [make_embedding(i) for i in range(100)]

        start = time.perf_counter()
        for memory, embedding in zip(memories, embeddings, strict=True):
            service.insert(memory, embedding)
        end = time.perf_counter()

        service.close()

        total_ms = (end - start) * 1000

        print(f"\n[Batch insert 100] Total time: {total_ms:.2f}ms")
        print(f"  Per-memory: {total_ms / 100:.2f}ms")

        assert total_ms < BATCH_INSERT_TARGET_MS, (
            f"Batch insert ({total_ms:.2f}ms) exceeds target ({BATCH_INSERT_TARGET_MS}ms)"
        )


class TestIndexScaling:
    """Test index performance at different scales."""

    @pytest.mark.parametrize("size", [50, 100, 200, 500])
    def test_search_scaling(self, tmp_path, size):
        """Test search performance scales well with index size."""
        db_path = tmp_path / f"scale_{size}.db"
        service = IndexService(db_path=db_path)
        service.initialize()

        # Populate index
        for i in range(size):
            service.insert(make_memory(i), make_embedding(i))

        # Measure search
        query_embedding = make_embedding(size // 2)

        def search():
            service.search_vector(query_embedding, limit=10)

        stats = measure_latency(search, iterations=30)
        service.close()

        print(f"\n[Scale {size}] P95: {stats['p95_ms']:.2f}ms")

        # Search should still be fast even with more data
        # Allow linear scaling: base 100ms + 0.2ms per memory
        max_allowed = 100 + (size * 0.2)
        assert stats["p95_ms"] < max_allowed


class TestStatisticsPerformance:
    """Benchmark stats operations."""

    def test_get_stats_performance(self, large_index):
        """Test get_stats latency."""

        def get_stats():
            large_index.get_stats()

        stats = measure_latency(get_stats, iterations=50)

        print("\n[get_stats] Latency stats:")
        print(f"  P50: {stats['p50_ms']:.2f}ms")
        print(f"  P95: {stats['p95_ms']:.2f}ms")

        # Stats should be very fast
        assert stats["p95_ms"] < 50  # 50ms max for stats
