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

NAMESPACE_PRIORITY = {
    "decisions": 1.0,
    "learnings": 0.9,
    "blockers": 0.85,
    "patterns": 0.8,
    "progress": 0.7,
    "retrospective": 0.75,
    "reviews": 0.7,
    "experiments": 0.65,  # NEW: Medium priority
    "research": 0.6,
    "elicitation": 0.5,
    "inception": 0.5,
}
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
    tags: tuple[str, ...] = (),
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
        >>> capture = get_capture_service()
        >>> result = capture.capture_experiment(
        ...     hypothesis="Dark mode toggle increases engagement",
        ...     result="Confirmed: +12% session duration",
        ...     metrics={"session_duration_delta": 0.12, "p_value": 0.03},
        ...     spec="ui-refresh",
        ...     tags=("ui", "engagement", "a/b-test"),
        ... )
        >>> print(result.memory_id)
        experiments:abc123
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
        tags=("experiment",) + tags,
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
from memory import get_capture_service
from memory.capture import reset_capture_service


@pytest.fixture
def capture_service(tmp_path, monkeypatch):
    """Create isolated capture service for testing."""
    reset_capture_service()
    monkeypatch.chdir(tmp_path)
    # Initialize git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, check=True)
    return get_capture_service()


def test_capture_experiment_basic(capture_service):
    """Test basic experiment capture."""
    result = capture_service.capture_experiment(
        hypothesis="Users prefer dark mode",
        spec="ui-refresh",
    )

    assert result.success
    assert result.memory_id.startswith("experiments:")
    assert result.namespace == "experiments"


def test_capture_experiment_with_result(capture_service):
    """Test experiment capture with result and metrics."""
    result = capture_service.capture_experiment(
        hypothesis="Caching improves API latency",
        result="Confirmed: 40% latency reduction",
        metrics={"latency_p50_ms": 45, "latency_p99_ms": 120},
        tags=("performance", "api"),
    )

    assert result.success
    assert "performance" in result.tags
    # Verify content was formatted
    assert "## Hypothesis" in result.content
    assert "## Result" in result.content
    assert "## Metrics" in result.content


def test_capture_experiment_long_hypothesis(capture_service):
    """Test that long hypotheses are truncated in summary."""
    long_hypothesis = "A" * 200  # 200 chars

    result = capture_service.capture_experiment(hypothesis=long_hypothesis)

    assert result.success
    assert len(result.summary) <= 103  # 100 + "..."
```

---

### Example 2: Custom Pattern Detection

Let's create a pattern detector that identifies performance regression patterns.

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


@dataclass(frozen=True)
class PerformancePattern(DetectedPattern):
    """Pattern specific to performance issues."""

    affected_component: str
    regression_type: str  # "latency", "throughput", "memory"
    severity: str  # "minor", "moderate", "severe"


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
        "throughput": ["throughput", "requests per second", "rps", "qps", "capacity"],
        "memory": ["memory", "oom", "leak", "heap", "garbage collection", "gc"],
    }

    # Known anti-patterns
    ANTI_PATTERNS = {
        "n+1": ["n+1", "n plus 1", "query per", "loop query"],
        "missing_index": ["full scan", "missing index", "no index", "table scan"],
        "no_caching": ["no cache", "uncached", "cache miss", "repeated fetch"],
        "sync_blocking": ["blocking", "synchronous", "await in loop"],
    }

    def detect_patterns(
        self,
        memories: list[Memory | MemoryResult],
        context: str | None = None,
    ) -> list[DetectedPattern]:
        """Detect performance patterns from memories.

        Args:
            memories: List of memories to analyze
            context: Optional context string for relevance

        Returns:
            List of detected performance patterns
        """
        # Get base patterns from parent
        patterns = super().detect_patterns(memories, context)

        # Filter to performance-related memories
        perf_memories = self._filter_performance_memories(memories)

        if not perf_memories:
            return patterns

        # Detect anti-patterns
        anti_patterns = self._detect_anti_patterns(perf_memories)
        patterns.extend(anti_patterns)

        # Detect success patterns (optimizations that worked)
        success_patterns = self._detect_success_patterns(perf_memories)
        patterns.extend(success_patterns)

        # Detect component-specific patterns
        component_patterns = self._detect_component_patterns(perf_memories)
        patterns.extend(component_patterns)

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

    def _detect_anti_patterns(
        self,
        memories: list[Memory | MemoryResult],
    ) -> list[DetectedPattern]:
        """Detect known performance anti-patterns."""
        patterns = []

        for pattern_name, keywords in self.ANTI_PATTERNS.items():
            matching = []
            for mem in memories:
                content = self._get_content(mem).lower()
                if any(kw in content for kw in keywords):
                    matching.append(mem)

            if len(matching) >= 2:  # Need at least 2 occurrences
                confidence = min(0.95, 0.5 + (len(matching) * 0.15))
                patterns.append(
                    DetectedPattern(
                        pattern_type=PatternType.ANTI_PATTERN,
                        name=pattern_name.replace("_", " ").title(),
                        description=f"Performance anti-pattern detected {len(matching)} times",
                        confidence=confidence,
                        evidence=tuple(m.id for m in matching[:5]),
                        tags=("performance", "anti-pattern"),
                    )
                )

        return patterns

    def _detect_success_patterns(
        self,
        memories: list[Memory | MemoryResult],
    ) -> list[DetectedPattern]:
        """Detect successful optimization patterns."""
        patterns = []

        # Look for learnings about performance improvements
        success_keywords = [
            ("caching", ["cache", "caching", "memoization"]),
            ("connection_pooling", ["pool", "pooling", "connection pool"]),
            ("indexing", ["index", "indexed", "add index"]),
            ("batching", ["batch", "batching", "bulk"]),
            ("async", ["async", "concurrent", "parallel"]),
        ]

        for pattern_name, keywords in success_keywords:
            matching = []
            for mem in memories:
                content = self._get_content(mem).lower()
                namespace = getattr(mem, "namespace", "")

                # Only count learnings and decisions as success evidence
                if namespace in ("learnings", "decisions"):
                    if any(kw in content for kw in keywords):
                        # Check for positive outcome indicators
                        if any(word in content for word in ["improved", "reduced", "faster", "better", "solved"]):
                            matching.append(mem)

            if matching:
                confidence = min(0.95, 0.6 + (len(matching) * 0.1))
                patterns.append(
                    DetectedPattern(
                        pattern_type=PatternType.SUCCESS,
                        name=pattern_name.replace("_", " ").title(),
                        description=f"Successful optimization pattern ({len(matching)} occurrences)",
                        confidence=confidence,
                        evidence=tuple(m.id for m in matching[:5]),
                        tags=("performance", "optimization"),
                    )
                )

        return patterns

    def _detect_component_patterns(
        self,
        memories: list[Memory | MemoryResult],
    ) -> list[DetectedPattern]:
        """Detect patterns specific to components (db, api, cache, etc.)."""
        # Group by component
        components: dict[str, list[Memory | MemoryResult]] = {}

        component_keywords = {
            "database": ["database", "db", "postgres", "mysql", "sql", "query"],
            "api": ["api", "endpoint", "rest", "graphql", "request"],
            "cache": ["cache", "redis", "memcached"],
            "frontend": ["frontend", "react", "render", "dom", "browser"],
        }

        for mem in memories:
            content = self._get_content(mem).lower()
            for component, keywords in component_keywords.items():
                if any(kw in content for kw in keywords):
                    components.setdefault(component, []).append(mem)

        # Create pattern for components with multiple issues
        patterns = []
        for component, mems in components.items():
            if len(mems) >= 3:
                patterns.append(
                    DetectedPattern(
                        pattern_type=PatternType.TECHNICAL,
                        name=f"{component.title()} Performance Hotspot",
                        description=f"{len(mems)} performance-related memories for {component}",
                        confidence=min(0.9, 0.5 + (len(mems) * 0.1)),
                        evidence=tuple(m.id for m in mems[:5]),
                        tags=("performance", component),
                    )
                )

        return patterns

    def _get_content(self, memory: Memory | MemoryResult) -> str:
        """Extract content from memory, falling back to summary."""
        if hasattr(memory, "content") and memory.content:
            return memory.content
        return memory.summary


# Usage example
def analyze_performance_patterns(spec: str | None = None) -> list[DetectedPattern]:
    """Analyze performance patterns for a spec.

    Example:
        >>> patterns = analyze_performance_patterns("api-refactor")
        >>> anti_patterns = [p for p in patterns if p.pattern_type == PatternType.ANTI_PATTERN]
        >>> if anti_patterns:
        ...     print("Warning: Anti-patterns detected!")
        ...     for p in anti_patterns:
        ...         print(f"  - {p.name}: {p.description}")
    """
    from . import get_recall_service

    recall = get_recall_service()
    memories = recall.search(
        query="performance latency optimization",
        limit=100,
        spec=spec,
    )

    detector = PerformancePatternDetector()
    return detector.detect_patterns([m.memory for m in memories])
```

---

### Example 3: Custom Hydration Behavior

Create a custom hydrator that enriches memories with external data.

```python
# memory/hydration_custom.py

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from .models import HydratedMemory, HydrationLevel, MemoryResult

if TYPE_CHECKING:
    from .recall import RecallService


@dataclass(frozen=True)
class EnrichedMemory(HydratedMemory):
    """Memory enriched with external context."""

    related_issues: tuple[str, ...] = ()  # GitHub issue URLs
    related_prs: tuple[str, ...] = ()  # GitHub PR URLs
    related_docs: tuple[str, ...] = ()  # Documentation links


class EnrichingHydrator:
    """Hydrates memories with additional external context.

    This hydrator adds:
    - Related GitHub issues/PRs based on commit SHA
    - Documentation links based on tags
    - Cross-references to other memories

    Example:
        >>> hydrator = EnrichingHydrator(recall_service)
        >>> result = recall.search("authentication decision", limit=1)[0]
        >>> enriched = hydrator.hydrate(result)
        >>> print(f"Related PRs: {enriched.related_prs}")
        Related PRs: ('https://github.com/org/repo/pull/123',)
    """

    # Map tags to documentation URLs
    DOC_LINKS: dict[str, str] = {
        "authentication": "https://docs.example.com/auth",
        "database": "https://docs.example.com/db",
        "api": "https://docs.example.com/api",
    }

    def __init__(
        self,
        recall_service: RecallService,
        github_repo: str | None = None,
    ) -> None:
        """Initialize the enriching hydrator.

        Args:
            recall_service: Service for cross-reference lookups
            github_repo: GitHub repo in "owner/repo" format for issue linking
        """
        self._recall = recall_service
        self._github_repo = github_repo

    def hydrate(
        self,
        result: MemoryResult,
        level: HydrationLevel = HydrationLevel.FULL,
    ) -> EnrichedMemory:
        """Hydrate a memory result with enriched context.

        Args:
            result: Memory result to hydrate
            level: Base hydration level

        Returns:
            EnrichedMemory with additional context
        """
        # First, do standard hydration
        base_hydrated = self._recall.hydrate(result, level)

        # Find related issues/PRs from commit
        related_issues, related_prs = self._find_github_references(
            result.memory.commit_sha
        )

        # Find documentation links from tags
        related_docs = self._find_doc_links(result.memory.tags or ())

        # Create enriched memory
        return EnrichedMemory(
            memory=base_hydrated.memory,
            content=base_hydrated.content,
            files=base_hydrated.files,
            related_issues=related_issues,
            related_prs=related_prs,
            related_docs=related_docs,
        )

    def _find_github_references(
        self,
        commit_sha: str,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Find GitHub issues and PRs referencing a commit."""
        if not self._github_repo:
            return (), ()

        issues: list[str] = []
        prs: list[str] = []

        # In real implementation, this would call GitHub API
        # For now, check if there's a cached mapping
        cache_file = Path(".cs-memory/github-refs.json")
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    refs = json.load(f)
                    commit_refs = refs.get(commit_sha, {})
                    issues = commit_refs.get("issues", [])
                    prs = commit_refs.get("prs", [])
            except (json.JSONDecodeError, OSError):
                pass

        return tuple(issues), tuple(prs)

    def _find_doc_links(self, tags: tuple[str, ...]) -> tuple[str, ...]:
        """Find documentation links based on tags."""
        links = []
        for tag in tags:
            if tag.lower() in self.DOC_LINKS:
                links.append(self.DOC_LINKS[tag.lower()])
        return tuple(links)


# Convenience function for common use case
def hydrate_with_enrichment(
    result: MemoryResult,
    github_repo: str | None = None,
) -> EnrichedMemory:
    """Hydrate a memory with full enrichment.

    Example:
        >>> from memory import get_recall_service
        >>> recall = get_recall_service()
        >>> results = recall.search("database decision")
        >>> enriched = hydrate_with_enrichment(results[0], github_repo="org/repo")
        >>> print(enriched.related_docs)
        ('https://docs.example.com/db',)
    """
    from . import get_recall_service

    recall = get_recall_service()
    hydrator = EnrichingHydrator(recall, github_repo)
    return hydrator.hydrate(result, HydrationLevel.FULL)
```

---

### Example 4: Creating a Custom Service

Create a service that provides domain-specific memory operations.

```python
# memory/services/review_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..models import CaptureResult, MemoryResult

if TYPE_CHECKING:
    from ..capture import CaptureService
    from ..recall import RecallService


@dataclass(frozen=True)
class ReviewStats:
    """Statistics about code reviews."""

    total_findings: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    resolution_rate: float
    avg_resolution_days: float


@dataclass(frozen=True)
class ReviewFinding:
    """A single code review finding."""

    memory_id: str
    severity: str
    category: str
    summary: str
    file_path: str | None
    line_number: int | None
    resolved: bool
    resolution_commit: str | None


class ReviewService:
    """Service for code review memory operations.

    Provides specialized methods for:
    - Capturing review findings
    - Tracking resolution status
    - Analyzing review patterns
    - Generating review reports

    Example:
        >>> service = ReviewService.create()
        >>> # Capture a finding
        >>> finding = service.capture_finding(
        ...     severity="high",
        ...     category="security",
        ...     summary="SQL injection vulnerability in user input",
        ...     file_path="src/api/users.py",
        ...     line_number=42,
        ...     spec="api-refactor",
        ... )
        >>> # Later, mark as resolved
        >>> service.resolve_finding(finding.memory_id, resolution_commit="abc123")
        >>> # Analyze patterns
        >>> stats = service.get_review_stats(spec="api-refactor")
        >>> print(f"Resolution rate: {stats.resolution_rate:.0%}")
    """

    def __init__(
        self,
        capture_service: CaptureService,
        recall_service: RecallService,
    ) -> None:
        self._capture = capture_service
        self._recall = recall_service

    @classmethod
    def create(cls) -> ReviewService:
        """Factory method to create a ReviewService with dependencies."""
        from .. import get_capture_service, get_recall_service

        return cls(
            capture_service=get_capture_service(),
            recall_service=get_recall_service(),
        )

    def capture_finding(
        self,
        severity: str,
        category: str,
        summary: str,
        file_path: str | None = None,
        line_number: int | None = None,
        spec: str | None = None,
        details: str | None = None,
    ) -> CaptureResult:
        """Capture a code review finding.

        Args:
            severity: critical, high, medium, low
            category: security, performance, architecture, quality
            summary: Brief description of the finding
            file_path: Path to affected file
            line_number: Line number of issue
            spec: Associated spec slug
            details: Extended description

        Returns:
            CaptureResult with memory ID
        """
        # Build structured content
        content_parts = [
            f"## Finding: {summary}",
            f"\n**Severity**: {severity}",
            f"**Category**: {category}",
        ]

        if file_path:
            location = f"{file_path}:{line_number}" if line_number else file_path
            content_parts.append(f"**Location**: `{location}`")

        if details:
            content_parts.append(f"\n## Details\n{details}")

        content_parts.append("\n## Status\nUnresolved")

        return self._capture.capture(
            namespace="reviews",
            summary=summary,
            content="\n".join(content_parts),
            spec=spec,
            tags=(severity, category, "unresolved"),
        )

    def resolve_finding(
        self,
        memory_id: str,
        resolution_commit: str,
        resolution_notes: str | None = None,
    ) -> CaptureResult:
        """Mark a review finding as resolved.

        This captures a new memory linking to the original finding
        with resolution details.

        Args:
            memory_id: ID of the original finding
            resolution_commit: Commit that resolved the issue
            resolution_notes: Optional notes about the fix

        Returns:
            CaptureResult for the resolution memory
        """
        # Find the original finding
        original = self._recall.get_by_id(memory_id)
        if not original:
            raise ValueError(f"Finding not found: {memory_id}")

        content_parts = [
            f"## Resolution for {memory_id}",
            f"\n**Original Finding**: {original.summary}",
            f"**Resolved By**: {resolution_commit}",
            f"**Resolved At**: {datetime.now(timezone.utc).isoformat()}",
        ]

        if resolution_notes:
            content_parts.append(f"\n## Resolution Notes\n{resolution_notes}")

        return self._capture.capture(
            namespace="reviews",
            summary=f"Resolved: {original.summary[:50]}...",
            content="\n".join(content_parts),
            spec=original.spec,
            tags=("resolution", "resolved"),
        )

    def get_unresolved_findings(
        self,
        spec: str | None = None,
        severity: str | None = None,
    ) -> list[ReviewFinding]:
        """Get all unresolved review findings.

        Args:
            spec: Filter by spec slug
            severity: Filter by severity level

        Returns:
            List of unresolved findings
        """
        results = self._recall.search(
            query="unresolved review finding",
            namespaces=["reviews"],
            spec=spec,
            tags=["unresolved"] + ([severity] if severity else []),
            limit=100,
        )

        findings = []
        for result in results:
            # Parse finding details from content
            finding = self._parse_finding(result)
            if finding and not finding.resolved:
                findings.append(finding)

        return findings

    def get_review_stats(self, spec: str | None = None) -> ReviewStats:
        """Get statistics about code reviews.

        Args:
            spec: Filter by spec slug

        Returns:
            ReviewStats with aggregate metrics
        """
        all_findings = self._recall.search(
            query="review finding",
            namespaces=["reviews"],
            spec=spec,
            limit=500,
        )

        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        resolved_count = 0
        resolution_days: list[float] = []

        for result in all_findings:
            finding = self._parse_finding(result)
            if not finding:
                continue

            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
            by_category[finding.category] = by_category.get(finding.category, 0) + 1

            if finding.resolved:
                resolved_count += 1
                # Calculate resolution time if we have both timestamps
                # (In real impl, would parse timestamps from content)

        total = len(all_findings)
        resolution_rate = resolved_count / total if total > 0 else 0.0
        avg_days = sum(resolution_days) / len(resolution_days) if resolution_days else 0.0

        return ReviewStats(
            total_findings=total,
            by_severity=by_severity,
            by_category=by_category,
            resolution_rate=resolution_rate,
            avg_resolution_days=avg_days,
        )

    def _parse_finding(self, result: MemoryResult) -> ReviewFinding | None:
        """Parse a ReviewFinding from a memory result."""
        memory = result.memory
        tags = set(memory.tags or ())

        # Determine severity from tags
        severity = "medium"
        for sev in ("critical", "high", "medium", "low"):
            if sev in tags:
                severity = sev
                break

        # Determine category from tags
        category = "quality"
        for cat in ("security", "performance", "architecture", "quality"):
            if cat in tags:
                category = cat
                break

        # Check if resolved
        resolved = "resolved" in tags or "resolution" in tags

        # Parse file path and line from content (simplified)
        file_path = None
        line_number = None
        content = memory.content or ""
        if "**Location**:" in content:
            # Would parse location from markdown in real impl
            pass

        return ReviewFinding(
            memory_id=memory.id,
            severity=severity,
            category=category,
            summary=memory.summary,
            file_path=file_path,
            line_number=line_number,
            resolved=resolved,
            resolution_commit=None,
        )


# Module-level singleton
_review_service: ReviewService | None = None


def get_review_service() -> ReviewService:
    """Get or create the review service singleton."""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService.create()
    return _review_service


def reset_review_service() -> None:
    """Reset the review service singleton for testing."""
    global _review_service
    _review_service = None
```

---

### Example 5: Writing Comprehensive Tests

Complete test patterns for memory system extensions.

```python
# tests/memory/test_extension_patterns.py

"""
Test patterns for memory system extensions.

This file demonstrates:
- Fixture patterns for isolated testing
- Mocking strategies for services
- Integration test approaches
- Property-based testing ideas
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from memory.models import (
    CaptureResult,
    Memory,
    MemoryResult,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def isolated_git_repo(tmp_path):
    """Create an isolated git repository for testing.

    This fixture:
    - Creates a temp directory
    - Initializes a git repo
    - Creates an initial commit
    - Yields the path

    Example:
        def test_something(isolated_git_repo):
            # isolated_git_repo is a Path to a valid git repo
            pass
    """
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    yield tmp_path


@pytest.fixture
def mock_capture_service():
    """Create a mock capture service for unit testing.

    Example:
        def test_something(mock_capture_service):
            mock_capture_service.capture.return_value = CaptureResult(...)
    """
    service = MagicMock()

    def mock_capture(**kwargs):
        return CaptureResult(
            success=True,
            memory_id=f"{kwargs.get('namespace', 'test')}:mock123",
            namespace=kwargs.get("namespace", "test"),
            commit_sha="mock123",
        )

    service.capture.side_effect = mock_capture
    return service


@pytest.fixture
def mock_recall_service():
    """Create a mock recall service for unit testing."""
    service = MagicMock()

    # Default empty search results
    service.search.return_value = []

    return service


@pytest.fixture
def sample_memory():
    """Create a sample memory for testing."""
    return Memory(
        id="decisions:abc123",
        commit_sha="abc123",
        namespace="decisions",
        summary="Test decision about architecture",
        content="Full content here",
        timestamp=datetime.now(timezone.utc),
        spec="test-spec",
        tags=("architecture", "testing"),
    )


@pytest.fixture
def sample_memory_result(sample_memory):
    """Create a sample memory result for testing."""
    return MemoryResult(memory=sample_memory, distance=0.25)


# ============================================================================
# Unit Test Patterns
# ============================================================================

class TestCapturePatterns:
    """Test patterns for capture operations."""

    def test_capture_returns_success(self, mock_capture_service):
        """Basic capture success test pattern."""
        result = mock_capture_service.capture(
            namespace="decisions",
            summary="Test decision",
            content="Content",
        )

        assert result.success
        assert result.namespace == "decisions"
        mock_capture_service.capture.assert_called_once()

    def test_capture_validates_namespace(self, mock_capture_service):
        """Test that invalid namespaces are rejected."""
        mock_capture_service.capture.side_effect = ValueError("Invalid namespace")

        with pytest.raises(ValueError, match="Invalid namespace"):
            mock_capture_service.capture(namespace="invalid", summary="Test")

    def test_capture_truncates_long_summary(self, mock_capture_service):
        """Test that long summaries are truncated."""
        long_summary = "A" * 500

        mock_capture_service.capture(namespace="decisions", summary=long_summary)

        # Verify the call was made
        call_args = mock_capture_service.capture.call_args
        assert len(call_args.kwargs["summary"]) <= 500


class TestRecallPatterns:
    """Test patterns for recall operations."""

    def test_search_returns_results(self, mock_recall_service, sample_memory_result):
        """Basic search test pattern."""
        mock_recall_service.search.return_value = [sample_memory_result]

        results = mock_recall_service.search(query="test")

        assert len(results) == 1
        assert results[0].memory.namespace == "decisions"

    def test_search_with_filters(self, mock_recall_service):
        """Test search with namespace and spec filters."""
        mock_recall_service.search(
            query="test",
            namespaces=["decisions"],
            spec="my-spec",
            tags=["important"],
        )

        mock_recall_service.search.assert_called_with(
            query="test",
            namespaces=["decisions"],
            spec="my-spec",
            tags=["important"],
        )

    def test_empty_search_returns_empty_list(self, mock_recall_service):
        """Test that empty results return empty list, not None."""
        mock_recall_service.search.return_value = []

        results = mock_recall_service.search(query="nonexistent")

        assert results == []
        assert isinstance(results, list)


# ============================================================================
# Integration Test Patterns
# ============================================================================

class TestIntegrationPatterns:
    """Integration test patterns using real services."""

    @pytest.mark.integration
    def test_capture_and_recall_roundtrip(self, isolated_git_repo, monkeypatch):
        """Test full capture -> recall flow.

        This test:
        1. Sets up isolated environment
        2. Captures a memory
        3. Recalls it
        4. Verifies content matches
        """
        monkeypatch.chdir(isolated_git_repo)

        # Reset singletons for isolation
        from memory.capture import reset_capture_service
        from memory.recall import reset_recall_service

        reset_capture_service()
        reset_recall_service()

        # Skip if dependencies not available
        pytest.importorskip("sentence_transformers")

        from memory import get_capture_service, get_recall_service

        capture = get_capture_service()
        recall = get_recall_service()

        # Capture
        result = capture.capture(
            namespace="decisions",
            summary="Test decision for integration",
            content="Full content for test",
            tags=("integration-test",),
        )

        assert result.success

        # Recall
        results = recall.search(query="integration test decision")

        assert len(results) >= 1
        assert any("integration" in r.memory.summary.lower() for r in results)

    @pytest.mark.integration
    def test_git_notes_persistence(self, isolated_git_repo, monkeypatch):
        """Test that memories persist in git notes."""
        import subprocess

        monkeypatch.chdir(isolated_git_repo)

        from memory.capture import reset_capture_service
        from memory import get_capture_service

        reset_capture_service()

        capture = get_capture_service()
        capture.capture(
            namespace="decisions",
            summary="Persistent decision",
            content="Should be in git notes",
        )

        # Verify git note exists
        result = subprocess.run(
            ["git", "notes", "--ref=refs/notes/cs/decisions", "list"],
            cwd=isolated_git_repo,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0


# ============================================================================
# Error Handling Test Patterns
# ============================================================================

class TestErrorHandling:
    """Test patterns for error scenarios."""

    def test_graceful_degradation_on_git_error(self, mock_capture_service):
        """Test that git errors are handled gracefully."""
        mock_capture_service.capture.side_effect = RuntimeError("Git error")

        with pytest.raises(RuntimeError):
            mock_capture_service.capture(namespace="decisions", summary="Test")

    def test_capture_returns_failure_on_validation_error(self, mock_capture_service):
        """Test that validation errors return failure result."""

        def failing_capture(**kwargs):
            return CaptureResult(
                success=False,
                memory_id="",
                namespace=kwargs.get("namespace", ""),
                commit_sha="",
                error="Validation failed",
            )

        mock_capture_service.capture.side_effect = failing_capture

        result = mock_capture_service.capture(namespace="decisions", summary="")

        assert not result.success
        assert "Validation" in result.error


# ============================================================================
# Test Utilities
# ============================================================================

def make_memories(
    count: int,
    namespace: str = "decisions",
    spec: str | None = None,
) -> list[Memory]:
    """Factory function for creating test memories.

    Args:
        count: Number of memories to create
        namespace: Namespace for all memories
        spec: Optional spec slug

    Returns:
        List of Memory objects

    Example:
        >>> memories = make_memories(10, namespace="learnings", spec="my-spec")
        >>> assert len(memories) == 10
        >>> assert all(m.namespace == "learnings" for m in memories)
    """
    return [
        Memory(
            id=f"{namespace}:test{i:03d}",
            commit_sha=f"test{i:03d}",
            namespace=namespace,
            summary=f"Test memory {i}",
            content=f"Content for memory {i}",
            timestamp=datetime.now(timezone.utc),
            spec=spec,
            tags=("test",),
        )
        for i in range(count)
    ]


def make_memory_results(
    memories: list[Memory],
    distances: list[float] | None = None,
) -> list[MemoryResult]:
    """Wrap memories in MemoryResult with distances.

    Args:
        memories: List of memories
        distances: Optional list of distances (defaults to 0.1, 0.2, ...)

    Returns:
        List of MemoryResult objects
    """
    if distances is None:
        distances = [0.1 * (i + 1) for i in range(len(memories))]

    return [
        MemoryResult(memory=mem, distance=dist)
        for mem, dist in zip(memories, distances)
    ]
```

---

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
