# cs-memory Developer Guide

Technical documentation for extending and integrating with the memory system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Command Layer                            │
│  /cs:remember  /cs:recall  /cs:context  /cs:memory         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Service Layer                             │
│  CaptureService  RecallService  SyncService                │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                 Intelligence Layer                          │
│  SearchOptimizer  PatternManager  LifecycleManager         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Storage Layer                             │
│  GitOps (notes)    IndexService (sqlite-vec)               │
└─────────────────────────────────────────────────────────────┘
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

### config.py

All configuration constants:

```python
from memory.config import (
    # Namespaces
    VALID_NAMESPACES,       # All valid memory types
    NAMESPACE_PRIORITY,     # Priority ordering

    # Git refs
    GIT_NOTES_REF_PREFIX,   # refs/notes/cs/

    # Index
    INDEX_DB_PATH,          # .cs-memory/index.db
    EMBEDDING_MODEL,        # all-MiniLM-L6-v2
    EMBEDDING_DIM,          # 384

    # Search
    SEARCH_CACHE_TTL_SECONDS,
    DEFAULT_SEARCH_LIMIT,

    # Lifecycle
    MEMORY_HALF_LIFE_DAYS,
    AGING_THRESHOLD_DAYS,
    STALE_THRESHOLD_DAYS,
    ARCHIVE_THRESHOLD_DAYS,
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
    GitOpsError,          # Git command failures
    ValidationError,      # Input validation
)
```

Each exception includes:
- `message`: Human-readable description
- `cause`: Underlying exception (if any)
- `recovery_action`: Suggested fix

## Service APIs

### CaptureService

```python
from memory import get_capture_service

capture = get_capture_service()

# Capture a memory
result = capture.capture(
    namespace="decisions",
    summary="Chose PostgreSQL for ACID compliance",
    content="Full markdown content...",
    spec="auth-feature",
    tags=["database", "architecture"],
)

# Specialized methods
capture.capture_decision(summary, content, spec, tags)
capture.capture_learning(summary, content, spec, tags)
capture.capture_blocker(summary, content, spec, tags)
```

### RecallService

```python
from memory import get_recall_service
from memory.models import HydrationLevel

recall = get_recall_service()

# Semantic search
results = recall.search(
    query="database performance",
    limit=10,
    namespaces=["decisions", "learnings"],
    spec="auth-feature",
    tags=["database"],
)

# Progressive hydration
hydrated = recall.hydrate(results[0], level=HydrationLevel.FULL)

# Full context loading
context = recall.load_context(spec="auth-feature")
```

### SyncService

```python
from memory import get_sync_service

sync = get_sync_service()

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
from memory import get_search_optimizer

optimizer = get_search_optimizer()

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
from memory import get_pattern_manager
from memory.patterns import PatternType, PatternStatus

patterns = get_pattern_manager()

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
from memory import get_lifecycle_manager
from memory.lifecycle import MemoryState

lifecycle = get_lifecycle_manager()

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

# Write note
git.add_note(
    namespace="decisions",
    commit_sha="abc123",
    content="---\nsummary: ...\n---\n\nContent...",
)

# Read note
content = git.get_note(namespace="decisions", commit_sha="abc123")

# List all notes
notes = git.list_notes(namespace="decisions")
# notes: [{"sha": "abc123", "object": "def456"}, ...]

# Remove note
git.remove_note(namespace="decisions", commit_sha="abc123")
```

### IndexService

```python
from memory.index import IndexService

index = IndexService(db_path=".cs-memory/index.db")

# Insert with embedding
index.upsert(memory, embedding_vector)

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
from memory.embedding import get_embedding_service

embed = get_embedding_service()

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

### Adding a New Namespace

1. Add to `config.py`:

```python
VALID_NAMESPACES = frozenset({
    # ...existing...
    "experiments",  # New namespace
})

NAMESPACE_PRIORITY = {
    # ...existing...
    "experiments": 0.65,
}
```

2. Add specialized capture method to `capture.py`:

```python
def capture_experiment(
    self,
    hypothesis: str,
    result: str,
    spec: str | None = None,
    tags: tuple[str, ...] = (),
) -> CaptureResult:
    content = f"## Hypothesis\n{hypothesis}\n\n## Result\n{result}"
    return self.capture(
        namespace="experiments",
        summary=hypothesis[:100],
        content=content,
        spec=spec,
        tags=("experiment",) + tags,
    )
```

### Adding Search Synonyms

Update `search.py`:

```python
QUERY_SYNONYMS = {
    # ...existing...
    "experiment": ["test", "hypothesis", "trial", "a/b"],
    "hypothesis": ["theory", "assumption", "experiment"],
}
```

### Custom Pattern Detection

Extend `PatternDetector`:

```python
class CustomPatternDetector(PatternDetector):
    def detect_patterns(self, memories, context=None):
        patterns = super().detect_patterns(memories, context)

        # Add custom detection
        custom_patterns = self._detect_custom(memories)
        patterns.extend(custom_patterns)

        return patterns

    def _detect_custom(self, memories):
        # Your custom detection logic
        return []
```

### Integration with Commands

Commands access memory via lazy imports:

```python
# In command markdown, reference the service
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

## Testing

### Unit Tests

```python
from datetime import datetime, timezone
from memory.models import Memory, MemoryResult

def make_test_memory(
    memory_id: str,
    namespace: str,
    summary: str,
    score: float,
) -> MemoryResult:
    memory = Memory(
        id=memory_id,
        commit_sha="abc123",
        namespace=namespace,
        summary=summary,
        content="Test content",
        timestamp=datetime.now(timezone.utc),
    )
    return MemoryResult(memory=memory, distance=score)
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
    from memory import get_capture_service
    capture = get_capture_service()
```

### Memory Leaks

Embedding service holds model in memory. For long-running processes:

```python
from memory.embedding import clear_embedding_service
clear_embedding_service()  # Releases model memory
```

### Index Corruption

```bash
# Verify
/cs:memory verify

# Rebuild if needed
/cs:memory reindex --full
```
