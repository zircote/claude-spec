# cs-memory Developer Guide

Technical documentation for extending and integrating with the memory system.

## Architecture Overview

```
+-------------------------------------------------------------+
|                    Command Layer                            |
|  /cs:remember  /cs:recall  /cs:context  /cs:memory         |
+--------------------------+----------------------------------+
                           |
+--------------------------v----------------------------------+
|                   Service Layer                             |
|  CaptureService  RecallService  SyncService                |
+--------------------------+----------------------------------+
                           |
+--------------------------v----------------------------------+
|                 Intelligence Layer                          |
|  SearchOptimizer  PatternManager  LifecycleManager         |
+--------------------------+----------------------------------+
                           |
+--------------------------v----------------------------------+
|                   Storage Layer                             |
|  GitOps (notes)    IndexService (sqlite-vec)               |
+-------------------------------------------------------------+
```

## Module Reference

### models.py

Frozen dataclasses for all domain objects:

```python
from memory.models import (
    Memory,           # Core memory object
    MemoryResult,     # Memory + distance score
    HydratedMemory,   # Memory + full content + files
    HydrationLevel,   # SUMMARY, FULL, FILES
    CaptureResult,    # Result of capture operation
    SpecContext,      # All memories for a spec
    IndexStats,       # Index statistics
    VerificationResult,
    ReviewFinding,
)
```

**Key Pattern**: All models are `frozen=True` for thread-safety and immutability.

### Memory ID Format

Memory IDs use the format `<namespace>:<short_sha>:<timestamp_ms>`:

```python
from memory.note_parser import extract_memory_id, parse_memory_id

# Generate ID
memory_id = extract_memory_id("decisions", "abc123def", timestamp)
# Result: "decisions:abc123d:1702560000000"

# Parse ID back into components
namespace, short_sha, ts_ms = parse_memory_id("decisions:abc123d:1702560000000")
# Result: ("decisions", "abc123d", 1702560000000)

# Legacy format (without timestamp) also supported for backwards compatibility
namespace, short_sha, ts_ms = parse_memory_id("decisions:abc123d")
# Result: ("decisions", "abc123d", None)
```

**Why timestamps?** Multiple memories can attach to the same commit (e.g., batch ADR capture). The millisecond timestamp ensures uniqueness without distributed coordination.

### config.py

All configuration constants:

```python
from memory.config import (
    # Namespaces
    NAMESPACES,              # All valid memory types (frozenset)
    AUTO_CAPTURE_NAMESPACES, # Namespaces enabled for auto-capture

    # Git refs
    # Notes are stored in refs/notes/cs/<namespace>

    # Index
    INDEX_DIR,               # Path(".cs-memory")
    INDEX_PATH,              # INDEX_DIR / "index.db"
    MODELS_DIR,              # INDEX_DIR / "models"

    # Embedding
    DEFAULT_EMBEDDING_MODEL, # "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS,    # 384

    # Search
    SEARCH_CACHE_TTL_SECONDS,  # 300.0 (5 minutes)
    DEFAULT_SEARCH_LIMIT,      # 10
    MAX_RECALL_LIMIT,          # 100

    # Lifecycle
    SECONDS_PER_DAY,           # 86400

    # Concurrency
    LOCK_FILE,                 # INDEX_DIR / ".capture.lock"
    LOCK_TIMEOUT,              # 5 seconds

    # Limits
    MAX_SUMMARY_LENGTH,        # 100 characters
    MAX_CONTENT_LENGTH,        # 100_000 bytes
    MAX_FILES_PER_HYDRATION,   # 20
    MAX_FILE_SIZE_BYTES,       # 100_000 bytes
)
```

### exceptions.py

Typed exception hierarchy:

```python
from memory.exceptions import (
    MemoryError,          # Base class
    CaptureError,         # Capture failures
    RecallError,          # Search/recall failures
    SyncError,            # Sync failures
    IndexError,           # Index operations
    StorageError,         # Git command failures
    ParseError,           # Input validation / note parsing
    EmbeddingError,       # Embedding generation failures
)
```

Each exception includes:
- `message`: Human-readable description
- `recovery_action`: Suggested fix

## Service APIs

### CaptureService

```python
from memory.capture import CaptureService, is_auto_capture_enabled

capture = CaptureService()

# Check if auto-capture is enabled
if is_auto_capture_enabled():
    # Capture a memory
    result = capture.capture(
        namespace="decisions",
        summary="Chose PostgreSQL for ACID compliance",
        content="Full markdown content...",
        spec="auth-feature",
        tags=["database", "architecture"],
    )
    # result.memory.id: "decisions:abc123d:1702560000000"

# Specialized methods for different memory types
capture.capture_decision(spec, summary, context, rationale, alternatives, tags)
capture.capture_learning(spec, summary, insight, applicability, tags)
capture.capture_blocker(spec, summary, problem, tags)
capture.capture_progress(spec, summary, task_id, details)
capture.resolve_blocker(memory_id, resolution)

# New specialized methods for auto-capture
capture.capture_review(
    summary="Security: SQL injection vulnerability",
    category="security",      # security|performance|architecture|quality|tests|documentation
    severity="critical",       # critical|high|medium|low
    file_path="src/auth/login.py",
    line=42,
    description="User input not sanitized before SQL query",
    spec="auth-feature",
    suggested_fix="Use parameterized queries",
    impact="Allows arbitrary SQL execution",
)

capture.capture_retrospective(
    summary="Retrospective: auth-feature",
    outcome="success",         # success|partial|failed|abandoned
    what_went_well=["Early performance testing", "Good code reviews"],
    what_to_improve=["Documentation timing", "Test coverage"],
    key_learnings=["Connection pooling critical for >100 users"],
    spec="auth-feature",
    metrics={"duration_days": 14, "effort_hours": 40},
)

capture.capture_pattern(
    summary="Success: Early performance testing",
    pattern_type="success",    # success|anti-pattern|deviation
    description="Running load tests before feature freeze",
    context="auth-feature project",
    applicability="Apply when feature has >10 concurrent users",
    spec="auth-feature",
    evidence="Caught 3 performance issues before release",
)
```

**Auto-capture Configuration**: Control auto-capture via environment variable:
```bash
export CS_AUTO_CAPTURE_ENABLED=false  # Disable auto-capture
```

The `is_auto_capture_enabled()` function checks this variable (default: `true`).

**Auto-sync Configuration**: On first capture, `CaptureService` automatically configures git for notes sync:
- Push refspec: `refs/notes/cs/*:refs/notes/cs/*`
- Fetch refspec: `refs/notes/cs/*:refs/notes/cs/*`
- Rewrite ref for rebase: `refs/notes/cs/*`
- Merge strategy: `cat_sort_uniq`

This is idempotent - subsequent captures skip reconfiguration.

### CaptureAccumulator

Track multiple captures during command execution:

```python
from memory.models import CaptureAccumulator
from memory.capture import CaptureService, is_auto_capture_enabled

accumulator = CaptureAccumulator()
capture = CaptureService()

# During command execution, wrap each capture in try/except (fail-open design)
if is_auto_capture_enabled():
    try:
        result = capture.capture_decision(...)
        accumulator.add(result)
    except Exception:
        pass  # Log warning but don't block command

    try:
        result = capture.capture_learning(...)
        accumulator.add(result)
    except Exception:
        pass

# At end of command, display summary
print(accumulator.summary())
# Output:
# ────────────────────────────────────────────────────────────────
# Memory Capture Summary
# ────────────────────────────────────────────────────────────────
# Captured: 2 memories (0.5s)
#   ✓ decisions:abc123d:1702560000000 - Chose PostgreSQL
#   ✓ learnings:def456a:1702563600000 - Connection pooling
# ────────────────────────────────────────────────────────────────

# Access counts
print(accumulator.count)          # 2
print(accumulator.by_namespace)   # {"decisions": 1, "learnings": 1}
```

### Validation Helpers

```python
from memory.capture import validate_auto_capture_namespace
from memory.config import AUTO_CAPTURE_NAMESPACES

# Check if namespace is valid and enabled for auto-capture
try:
    is_enabled = validate_auto_capture_namespace("decisions")
    # Returns True if in AUTO_CAPTURE_NAMESPACES, False otherwise
except CaptureError:
    # Raised if namespace is not in NAMESPACES at all
    pass

# Currently enabled namespaces
print(AUTO_CAPTURE_NAMESPACES)
# frozenset({'decisions', 'learnings', 'blockers', 'progress', 'reviews', 'retrospective', 'patterns'})
```

### RecallService

```python
from memory.recall import RecallService
from memory.models import HydrationLevel

recall = RecallService()

# Semantic search
results = recall.search(
    query="database performance",
    limit=10,
    namespaces=["decisions", "learnings"],
    spec="auth-feature",
    tags=["database"],
)
# results[0].memory.id: "decisions:abc123d:1702560000000"
# results[0].distance: 0.25 (lower = more similar)

# Progressive hydration
hydrated = recall.hydrate(results[0], level=HydrationLevel.FULL)

# Full context loading
context = recall.load_context(spec="auth-feature")
```

### SyncService

```python
from memory.sync import SyncService

sync = SyncService()

# Incremental sync
added, updated = sync.sync_incremental()

# Full rebuild
sync.rebuild_index()

# Verify consistency
result = sync.verify()
if not result.is_consistent:
    print(f"Missing: {result.missing_in_index}")
    print(f"Orphaned: {result.orphaned_in_index}")
```

## Intelligence APIs

### SearchOptimizer

```python
from memory.search import SearchOptimizer

optimizer = SearchOptimizer()

# Query expansion
query = optimizer.expand_query("database decision")
# query.expanded_terms: ("db", "postgres", "chose", "selected", ...)

# Result re-ranking
ranked = optimizer.rerank_results(
    results,
    query,
    target_spec="auth-feature",
    target_tags=["database"],
)

# Caching
optimizer.cache_results(query.cache_key(), results)
cached = optimizer.get_cached(query.cache_key())
optimizer.invalidate_cache("auth")  # Pattern match
```

### PatternManager

```python
from memory.patterns import PatternManager, PatternType, PatternStatus

patterns = PatternManager()

# Detect patterns
detected = patterns.detect(memories)

# Register and promote
for pattern in detected:
    patterns.register_pattern(pattern)
    if pattern.confidence > 0.8:
        patterns.promote_pattern(f"{pattern.pattern_type.value}:{pattern.name}")

# Get suggestions
suggestions = patterns.suggest(
    context="working on authentication",
    current_spec="auth-feature",
    current_tags=["auth", "security"],
)

# Filter by type
success_patterns = patterns.get_patterns(
    pattern_type=PatternType.SUCCESS,
    status=PatternStatus.PROMOTED,
)
```

### LifecycleManager

```python
from memory.lifecycle import LifecycleManager, MemoryState

lifecycle = LifecycleManager()

# Process memories
stats = lifecycle.process_memories(memories)
# stats: {"total": 100, "by_state": {...}, "average_decay": 0.65}

# Filter relevant
relevant = lifecycle.get_relevant_memories(
    memories,
    min_decay=0.5,  # Only recent-ish memories
)

# Calculate adjusted score
score = lifecycle.calculate_memory_score(
    memory_result,
    original_distance=0.3,
)

# Archive a spec
summaries = lifecycle.archive_spec("completed-feature", memories)
```

## Storage Layer

### GitOps

```python
from memory.git_ops import GitOps

git = GitOps(repo_path="/path/to/repo")

# Write note (append is preferred for safety - FR-023)
git.append_note(
    namespace="decisions",
    content="---\nsummary: ...\n---\n\nContent...",
    commit="HEAD",
)

# Read note
content = git.show_note(namespace="decisions", commit="abc123")

# List all notes
notes = git.list_notes(namespace="decisions")
# notes: [("note_sha", "commit_sha"), ...]

# Remove note
git.remove_note(namespace="decisions", commit="abc123")

# Check sync configuration
status = git.is_sync_configured()
# status: {"push": True, "fetch": True, "rewrite": True, "merge": True}

# Configure sync (idempotent)
configured = git.configure_sync()
# configured: {"push": True, "fetch": False, ...} (True = newly configured)
```

### IndexService

```python
from memory.index import IndexService

index = IndexService(db_path=".cs-memory/index.db")

# Initialize tables
index.initialize()

# Insert with embedding
index.insert(memory, embedding_vector)

# Update existing
index.update(memory)

# Vector search
results = index.search(
    query_vector=embedding,
    limit=10,
    namespace="decisions",
    spec="auth-feature",
)

# Get stats
stats = index.stats()
```

### EmbeddingService

```python
from memory.embedding import EmbeddingService

embed = EmbeddingService()

# Single text
vector = embed.embed("database performance optimization")

# Batch
vectors = embed.embed_batch([
    "text one",
    "text two",
    "text three",
])

# Check model status
if not embed.is_loaded:
    embed.ensure_loaded()  # Downloads model if needed
```

## Extending the System

This section provides complete, working code examples for common extension patterns.

---

### Example 1: Adding a New Namespace (Complete Walkthrough)

Let's add an "experiments" namespace for tracking A/B tests and hypotheses.

**Step 1: Update `config.py`**

```python
# config.py - Add to existing frozenset and dict

NAMESPACES = frozenset({
    "inception",
    "elicitation",
    "research",
    "decisions",
    "progress",
    "blockers",
    "learnings",
    "reviews",
    "retrospective",
    "patterns",
    "experiments",  # NEW: For tracking A/B tests and hypotheses
})
```

**Step 2: Add specialized capture method to `capture.py`**

```python
# capture.py - Add this method to CaptureService class

def capture_experiment(
    self,
    hypothesis: str,
    result: str | None = None,
    metrics: dict[str, float] | None = None,
    spec: str | None = None,
    tags: list[str] | None = None,
) -> CaptureResult:
    """Capture an experiment or A/B test result.

    Args:
        hypothesis: What was being tested
        result: Outcome (None if experiment is ongoing)
        metrics: Quantitative results (e.g., {"conversion_rate": 0.15})
        spec: Associated spec slug
        tags: Additional categorization

    Returns:
        CaptureResult with memory ID

    Example:
        >>> capture = CaptureService()
        >>> result = capture.capture_experiment(
        ...     hypothesis="Dark mode toggle increases engagement",
        ...     result="Confirmed: +12% session duration",
        ...     metrics={"session_duration_delta": 0.12, "p_value": 0.03},
        ...     spec="ui-refresh",
        ...     tags=["ui", "engagement", "a/b-test"],
        ... )
        >>> print(result.memory.id)
        experiments:abc123d:1702560000000
    """
    # Build structured content
    content_parts = [f"## Hypothesis\n{hypothesis}"]

    if result:
        content_parts.append(f"\n## Result\n{result}")

    if metrics:
        metrics_str = "\n".join(f"- **{k}**: {v}" for k, v in metrics.items())
        content_parts.append(f"\n## Metrics\n{metrics_str}")

    content = "\n".join(content_parts)

    # Truncate hypothesis for summary
    summary = hypothesis[:100] + "..." if len(hypothesis) > 100 else hypothesis

    return self.capture(
        namespace="experiments",
        summary=summary,
        content=content,
        spec=spec,
        tags=["experiment"] + (tags or []),
    )
```

**Step 3: Add search synonyms to `search.py`**

```python
# search.py - Add to QUERY_SYNONYMS dict

QUERY_SYNONYMS: dict[str, list[str]] = {
    # ...existing entries...

    # Experiment-related (NEW)
    "experiment": ["test", "hypothesis", "trial", "a/b", "ab-test"],
    "hypothesis": ["theory", "assumption", "experiment", "prediction"],
    "a/b": ["ab-test", "experiment", "split-test", "variant"],
    "metrics": ["measurement", "kpi", "result", "outcome"],
}
```

**Step 4: Write tests**

```python
# tests/memory/test_capture_experiment.py

import pytest
from memory.capture import CaptureService


@pytest.fixture
def capture_service(tmp_path, monkeypatch):
    """Create isolated capture service for testing."""
    CaptureService.reset_sync_configured()
    monkeypatch.chdir(tmp_path)
    # Initialize git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path, check=True
    )
    return CaptureService()


def test_capture_experiment_basic(capture_service):
    """Test basic experiment capture."""
    result = capture_service.capture_experiment(
        hypothesis="Users prefer dark mode",
        spec="ui-refresh",
    )

    assert result.success
    assert result.memory.id.startswith("experiments:")
    assert result.memory.namespace == "experiments"


def test_capture_experiment_with_result(capture_service):
    """Test experiment capture with result and metrics."""
    result = capture_service.capture_experiment(
        hypothesis="Caching improves API latency",
        result="Confirmed: 40% latency reduction",
        metrics={"latency_p50_ms": 45, "latency_p99_ms": 120},
        tags=["performance", "api"],
    )

    assert result.success
    assert "performance" in result.memory.tags
    # Verify content was formatted
    assert "## Hypothesis" in result.memory.content
    assert "## Result" in result.memory.content
    assert "## Metrics" in result.memory.content
```

---

### Example 2: Custom Pattern Detection

Create a pattern detector that identifies performance regression patterns.

```python
# memory/patterns_performance.py

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .patterns import (
    DetectedPattern,
    PatternDetector,
    PatternType,
)

if TYPE_CHECKING:
    from .models import Memory, MemoryResult


class PerformancePatternDetector(PatternDetector):
    """Detect patterns in performance-related memories.

    This detector identifies:
    - Repeated performance issues in the same component
    - Common causes of regressions
    - Successful optimization patterns

    Example:
        >>> detector = PerformancePatternDetector()
        >>> memories = recall.search("performance", limit=50)
        >>> patterns = detector.detect_patterns([m.memory for m in memories])
        >>> for p in patterns:
        ...     print(f"{p.pattern_type}: {p.name} ({p.confidence:.0%})")
        ANTI_PATTERN: Database N+1 queries (85%)
        SUCCESS: Connection pooling (90%)
    """

    # Keywords indicating performance issues
    PERFORMANCE_KEYWORDS = {
        "latency": ["slow", "latency", "response time", "delay", "timeout"],
        "throughput": ["throughput", "requests per second", "rps", "qps"],
        "memory": ["memory", "oom", "leak", "heap", "garbage collection"],
    }

    # Known anti-patterns
    ANTI_PATTERNS = {
        "n+1": ["n+1", "n plus 1", "query per", "loop query"],
        "missing_index": ["full scan", "missing index", "no index"],
        "no_caching": ["no cache", "uncached", "cache miss"],
    }

    def detect_patterns(
        self,
        memories: list[Memory | MemoryResult],
        context: str | None = None,
    ) -> list[DetectedPattern]:
        """Detect performance patterns from memories."""
        patterns = []

        # Filter to performance-related memories
        perf_memories = self._filter_performance_memories(memories)

        if not perf_memories:
            return patterns

        # Detect anti-patterns
        patterns.extend(self._detect_anti_patterns(perf_memories))

        # Detect success patterns
        patterns.extend(self._detect_success_patterns(perf_memories))

        return patterns

    def _filter_performance_memories(
        self,
        memories: list[Memory | MemoryResult],
    ) -> list[Memory | MemoryResult]:
        """Filter to only performance-related memories."""
        perf_memories = []

        for mem in memories:
            content = self._get_content(mem).lower()
            tags = set(getattr(mem, "tags", ()) or ())

            # Check tags
            if tags & {"performance", "latency", "optimization", "slow"}:
                perf_memories.append(mem)
                continue

            # Check content keywords
            for keywords in self.PERFORMANCE_KEYWORDS.values():
                if any(kw in content for kw in keywords):
                    perf_memories.append(mem)
                    break

        return perf_memories

    def _get_content(self, memory: Memory | MemoryResult) -> str:
        """Extract content from memory, falling back to summary."""
        if hasattr(memory, "content") and memory.content:
            return memory.content
        return memory.summary
```

---

### Example 3: Integration with Commands

Commands access memory via the service layer. In command markdown files, reference integration points:

```markdown
<memory_integration>
auto_recall:
  trigger: on_invocation
  query: "{{ spec_slug }} {{ phase }}"
  limit: 5

auto_capture:
  decision:
    trigger: when_agent_makes_choice
    extract: summary, rationale, alternatives
</memory_integration>
```

The actual capture in Python:

```python
# During command execution
from memory.capture import CaptureService

capture = CaptureService()

# Memory ID will include timestamp for uniqueness
result = capture.capture_decision(
    spec="user-auth",
    summary="Chose RS256 for JWT signing",
    context="Need key rotation support",
    rationale="Asymmetric signing enables JWKS endpoint",
    alternatives=["HS256", "ES256"],
    tags=["jwt", "security"],
)

# result.memory.id: "decisions:abc123d:1702560000000"
```

## Testing

### Unit Tests

```python
from datetime import datetime, timezone
from memory.models import Memory, MemoryResult

def make_test_memory(
    namespace: str = "decisions",
    summary: str = "Test decision",
    commit_sha: str = "abc123d",
    timestamp_ms: int | None = None,
) -> Memory:
    """Create a test memory with realistic ID format."""
    if timestamp_ms is None:
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    return Memory(
        id=f"{namespace}:{commit_sha}:{timestamp_ms}",
        commit_sha=commit_sha,
        namespace=namespace,
        summary=summary,
        content="Test content",
        timestamp=datetime.now(timezone.utc),
    )

def make_test_result(memory: Memory, distance: float = 0.25) -> MemoryResult:
    """Wrap memory in result with distance score."""
    return MemoryResult(memory=memory, distance=distance)
```

### Run Tests

```bash
# All memory tests
uv run pytest tests/memory/ -v

# Specific test
uv run pytest tests/memory/test_search.py::TestQueryExpander -v

# With coverage
uv run pytest tests/memory/ --cov=memory --cov-report=html
```

## Performance Considerations

### Embedding Model

- **Model**: `all-MiniLM-L6-v2` (22M params, 384 dims)
- **Load time**: ~2s first load, then cached
- **Inference**: ~10ms per text

### Index Performance

- **SQLite + sqlite-vec**: Good for <100k memories
- **Search latency**: ~5ms for top-10
- **Index size**: ~1KB per memory

### Caching Strategy

- **Search cache**: 5 minute TTL, 100 entries max
- **Embedding cache**: LRU via sentence-transformers
- **Git ops**: No caching (always fresh)

## Troubleshooting

### Import Errors

```python
# Always use lazy imports to avoid pytorch overhead
def some_function():
    from memory.capture import CaptureService
    capture = CaptureService()
```

### Memory Leaks

Embedding service holds model in memory. For long-running processes:

```python
from memory.embedding import EmbeddingService

# Create new instance when needed
embed = EmbeddingService()
# Model is loaded on first embed() call
```

### Index Corruption

```bash
# Verify
/cs:memory verify

# Rebuild if needed
/cs:memory reindex --full
```

## Git Notes Sync Configuration

The system auto-configures git on first capture. To verify or manually configure:

```bash
# Check current configuration
git config --get-all remote.origin.push | grep notes
git config --get-all remote.origin.fetch | grep notes
git config --get-all notes.rewriteRef
git config --get notes.cs.mergeStrategy

# Manual configuration (if needed)
git config --add remote.origin.push "refs/notes/cs/*:refs/notes/cs/*"
git config --add remote.origin.fetch "refs/notes/cs/*:refs/notes/cs/*"
git config --add notes.rewriteRef "refs/notes/cs/*"
git config notes.cs.mergeStrategy "cat_sort_uniq"
```

**Note**: Manual configuration is rarely needed. The `CaptureService` handles this automatically and idempotently on first capture.
