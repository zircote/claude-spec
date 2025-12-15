# Architecture Specification: cs-memory

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           cs-memory Architecture                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        COMMAND LAYER                                │   │
│  │  /cs:remember  /cs:recall  /cs:context  /cs:memory                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        SERVICE LAYER                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │   Capture   │  │   Recall    │  │    Sync     │  │   Index    │  │   │
│  │  │   Service   │  │   Service   │  │   Service   │  │  Service   │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│              ┌───────────────┼───────────────┐                              │
│              │               │               │                              │
│              ▼               ▼               ▼                              │
│  ┌───────────────────┐  ┌─────────┐  ┌─────────────────────────────────┐   │
│  │   STORAGE LAYER   │  │EMBEDDING│  │         INDEX LAYER             │   │
│  │                   │  │  MODEL  │  │                                 │   │
│  │  Git Notes        │  │         │  │  SQLite + sqlite-vec            │   │
│  │  refs/notes/cs/*  │  │  Local  │  │  .cs-memory/index.db            │   │
│  │                   │  │  384-d  │  │                                 │   │
│  │  (Source of Truth)│  │         │  │  (Derived, Gitignored)          │   │
│  └───────────────────┘  └─────────┘  └─────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Component Design

### 2.1 Command Layer

Commands are implemented as claude-spec plugin commands in Markdown format.

#### /cs:remember
```
Location: plugins/cs/commands/remember.md
Purpose: Explicit memory capture
Arguments: <type> <summary>
Options: --commit=<sha>, --spec=<slug>
```

#### /cs:recall
```
Location: plugins/cs/commands/recall.md
Purpose: Semantic memory search
Arguments: <query>
Options: --spec, --type, --since, --until, --full, --files, --limit
```

#### /cs:context
```
Location: plugins/cs/commands/context.md
Purpose: Bootstrap full context for a spec
Arguments: <spec-slug>
Options: --recent=<n>
```

#### /cs:memory
```
Location: plugins/cs/commands/memory.md
Purpose: Memory management
Subcommands: status, reindex, export, gc
```

#### /cs:review
```
Location: plugins/cs/commands/review.md
Purpose: Code review with memory integration
Arguments: [path] (optional, defaults to current changes)
Options: --focus=security|performance|maintainability, --spec=<slug>
Agents: 6 parallel specialists (Security, Performance, Architecture, Quality, Tests, Docs)
Outputs: CODE_REVIEW.md, REVIEW_SUMMARY.md, REMEDIATION_TASKS.md
Memory: Findings captured to cs/reviews namespace
```

#### /cs:fix
```
Location: plugins/cs/commands/fix.md
Purpose: Remediate code review findings with tracking
Arguments: [CODE_REVIEW.md] (optional, or reads from cs/reviews)
Options: --quick, --severity=critical|high|medium|low, --category=<type>
Agents: Specialist per category + pr-review-toolkit verification
Memory: Updates findings with resolution, captures learnings
```

### 2.2 Service Layer

Services are implemented as Python modules under `plugins/cs/memory/`.

#### CaptureService
```python
# plugins/cs/memory/capture.py

import fcntl
from pathlib import Path
from contextlib import contextmanager

LOCK_FILE = Path(".cs-memory/.capture.lock")
LOCK_TIMEOUT = 5  # seconds

@contextmanager
def capture_lock():
    """Acquire exclusive lock for note operations (FR-022)."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError:
        raise CaptureError(
            "Another capture operation is in progress. "
            "Wait and retry, or check for stuck processes."
        )
    finally:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()

class CaptureService:
    """Handles memory capture operations with concurrency safety."""

    def capture(
        self,
        namespace: str,
        summary: str,
        content: str,
        spec: str | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
        phase: str | None = None,
    ) -> Memory:
        """
        Capture a memory as a Git note.

        1. Acquire capture lock (FR-022)
        2. Format note with YAML front matter
        3. Attach note to commit via git notes append (FR-023)
        4. Generate embedding
        5. Index in SQLite
        6. Release lock
        7. Return Memory object
        """
        
    def capture_decision(self, spec: str, summary: str, context: str, 
                        rationale: str, alternatives: list[str]) -> Memory:
        """Structured capture for ADRs."""
        
    def capture_blocker(self, spec: str, summary: str, 
                       problem: str) -> Memory:
        """Capture unresolved blocker."""
        
    def resolve_blocker(self, memory_id: str, resolution: str) -> Memory:
        """Update blocker with resolution."""
```

#### RecallService
```python
# plugins/cs/memory/recall.py

class RecallService:
    """Handles memory retrieval operations."""
    
    def search(
        self,
        query: str,
        spec: str | None = None,
        namespace: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 10,
    ) -> list[MemoryResult]:
        """
        Semantic search over memories.
        
        1. Generate query embedding
        2. Execute KNN search with filters
        3. Return ranked results with distance scores
        """
        
    def hydrate(
        self,
        memory: MemoryResult,
        level: HydrationLevel,
    ) -> HydratedMemory:
        """
        Progressive hydration.
        
        Level 1: Summary only (already present)
        Level 2: Full note content from git notes show
        Level 3: File snapshots from git show <sha>:<path>
        """
        
    def context(self, spec: str) -> SpecContext:
        """
        Load all memories for a spec.
        
        1. Query all namespaces for spec
        2. Sort chronologically
        3. Group by namespace
        4. Return structured context
        """
```

#### SyncService
```python
# plugins/cs/memory/sync.py

class SyncService:
    """Handles synchronization between Git notes and index."""
    
    def sync_note_to_index(self, namespace: str, commit_sha: str) -> None:
        """Index a single note after capture."""
        
    def full_reindex(self) -> IndexStats:
        """
        Rebuild entire index from Git notes.
        
        1. Clear existing index
        2. Iterate all namespaces
        3. Parse each note
        4. Generate embeddings
        5. Insert into index
        """
        
    def verify_index(self) -> VerificationResult:
        """Check index consistency against notes."""
```

#### IndexService
```python
# plugins/cs/memory/index.py

class IndexService:
    """Handles SQLite + sqlite-vec operations."""

    def __init__(self, db_path: str = ".cs-memory/index.db"):
        self.db_path = db_path

    def initialize(self) -> None:
        """Create tables if not exist."""

    def insert(self, memory: Memory, embedding: list[float]) -> None:
        """Insert memory with embedding."""

    def search_vector(
        self,
        embedding: list[float],
        filters: dict | None = None,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        """KNN search returning (id, distance) pairs."""

    def get_stats(self) -> IndexStats:
        """Return index statistics."""
```

#### ReviewService
```python
# plugins/cs/memory/review.py

class ReviewService:
    """Handles code review operations with memory integration."""

    def __init__(
        self,
        capture: CaptureService,
        recall: RecallService,
    ):
        self.capture = capture
        self.recall = recall

    async def execute_review(
        self,
        path: str | None = None,
        focus: str | None = None,
        spec: str | None = None,
    ) -> ReviewResult:
        """
        Execute code review with 6 parallel specialist agents.

        1. Recall similar past findings (pattern detection)
        2. Deploy 6 agents in parallel via Task tool
        3. Collect and deduplicate findings
        4. Capture each finding to cs/reviews namespace
        5. Generate CODE_REVIEW.md, REVIEW_SUMMARY.md, REMEDIATION_TASKS.md
        """

    async def execute_fix(
        self,
        source: str = "CODE_REVIEW.md",
        severity_filter: list[str] | None = None,
        category_filter: list[str] | None = None,
        quick: bool = False,
    ) -> FixResult:
        """
        Remediate review findings with specialist agents.

        1. Load findings from source (file or cs/reviews)
        2. If not quick: prompt for severity, category, conflict, verification decisions
        3. Route findings to appropriate specialist agents
        4. Execute fixes with verification (pr-review-toolkit)
        5. Update original notes with resolution
        6. Capture learnings and blockers encountered
        """

    def resolve_finding(
        self,
        finding_id: str,
        resolution: str,
    ) -> Memory:
        """Update review finding with resolution."""

    def detect_patterns(
        self,
        limit: int = 10,
    ) -> list[PatternSuggestion]:
        """
        Identify recurring review findings.

        1. Query cs/reviews for high-frequency summaries
        2. Cluster similar findings by embedding
        3. Return patterns with occurrence counts
        """

# Specialist agent routing
CATEGORY_AGENT_MAP = {
    "security": "security-engineer",
    "performance": "performance-engineer",
    "architecture": "refactoring-specialist",
    "quality": "code-reviewer",
    "tests": "test-automator",
    "documentation": "documentation-engineer",
}

# Verification agents
VERIFICATION_AGENTS = [
    "pr-review-toolkit:silent-failure-hunter",
    "pr-review-toolkit:code-simplifier",
    "pr-review-toolkit:pr-test-analyzer",
]
```

### 2.3 Storage Layer (Git Notes)

#### Namespace Structure
```
refs/notes/cs/
├── inception      # Problem statements, scope
├── elicitation    # Requirements clarifications
├── research       # External findings
├── decisions      # Architecture Decision Records
├── progress       # Task completions
├── blockers       # Obstacles and resolutions
├── reviews        # Code review findings
├── learnings      # Technical insights
├── retrospective  # Post-mortems
└── patterns       # Cross-spec patterns
```

#### Note Format
```yaml
---
type: decision
spec: user-auth
phase: architecture
timestamp: 2025-12-14T10:30:00Z
tags: [jwt, security, cryptography]
summary: Chose RS256 over HS256 for JWT signing
relates_to: [abc123, def456]
---

## Context
Need to support key rotation without invalidating existing tokens.

## Decision
RS256 asymmetric signing enables public key distribution for 
verification while keeping the signing key secure.

## Alternatives Considered
- **HS256**: Simpler but requires shared secret distribution
- **ES256**: Good security but less library support

## Consequences
- Need key management infrastructure
- Can publish JWKS endpoint for token verification
```

#### Git Operations
```bash
# Create or append note (FR-023: always use append to prevent overwrites)
# If note doesn't exist, append creates it
# If note exists, append adds to it (safe for concurrent operations)
git notes --ref=cs/decisions append -m "<content>" HEAD

# Read note
git notes --ref=cs/decisions show <commit>

# List all notes in namespace
git notes --ref=cs/decisions list

# Configure sync
git config --add remote.origin.push "refs/notes/cs/*:refs/notes/cs/*"
git config --add remote.origin.fetch "refs/notes/cs/*:refs/notes/cs/*"
```

**Note on Concurrency (FR-022, FR-023):**
- `git notes add` overwrites existing notes - NEVER use for capture
- `git notes append` safely adds to existing notes
- File locking (`.cs-memory/.capture.lock`) prevents race conditions within a clone

### 2.4 Index Layer (SQLite + sqlite-vec)

#### Schema
```sql
-- Metadata table
CREATE TABLE memories (
    id TEXT PRIMARY KEY,           -- Format: <namespace>:<commit_sha>
    commit_sha TEXT NOT NULL,
    namespace TEXT NOT NULL,
    spec TEXT,
    phase TEXT,
    summary TEXT NOT NULL,
    full_content TEXT NOT NULL,
    tags JSON,
    timestamp DATETIME NOT NULL,
    status TEXT,                   -- For blockers: unresolved/resolved
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_memories_spec ON memories(spec);
CREATE INDEX idx_memories_namespace ON memories(namespace);
CREATE INDEX idx_memories_timestamp ON memories(timestamp);

-- Vector index (sqlite-vec)
CREATE VIRTUAL TABLE vec_memories USING vec0(
    embedding float[384]
);
```

#### Query Patterns
```sql
-- Semantic search with filters
SELECT 
    m.id,
    m.commit_sha,
    m.namespace,
    m.spec,
    m.summary,
    v.distance
FROM memories m
JOIN vec_memories v ON m.rowid = v.rowid
WHERE v.embedding MATCH ?
  AND (m.spec = ? OR ? IS NULL)
  AND (m.namespace = ? OR ? IS NULL)
  AND (m.timestamp >= ? OR ? IS NULL)
  AND (m.timestamp <= ? OR ? IS NULL)
ORDER BY v.distance
LIMIT ?;
```

### 2.5 Embedding Model

#### Configuration
```python
# plugins/cs/memory/embedding.py

from sentence_transformers import SentenceTransformer

class EmbeddingService:
    """Local embedding generation."""
    
    MODEL_NAME = "all-MiniLM-L6-v2"
    DIMENSIONS = 384
    
    def __init__(self):
        self._model = None
        
    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.MODEL_NAME)
        return self._model
        
    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        return self.model.encode(text).tolist()
        
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding generation."""
        return self.model.encode(texts).tolist()
```

## 3. Data Flow

### 3.1 Memory Capture Flow

```
User: /cs:remember decision "Use PostgreSQL for JSONB support"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. ELICIT STRUCTURED DATA                                       │
│    - Prompt for context, rationale, alternatives                │
│    - User provides additional detail                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. FORMAT NOTE                                                  │
│    - Construct YAML front matter                                │
│    - Build Markdown body                                        │
│    - Generate note content string                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. ATTACH TO GIT                                                │
│    git notes --ref=cs/decisions add -m "<content>" HEAD         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. GENERATE EMBEDDING                                           │
│    embedding = model.encode(summary + " " + body)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. INDEX IN SQLITE                                              │
│    INSERT INTO memories (...) VALUES (...)                      │
│    INSERT INTO vec_memories (embedding) VALUES (?)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. CONFIRM                                                      │
│    "Memory captured: decisions:abc123def"                       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Memory Recall Flow

```
User: /cs:recall "what database for user preferences?"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. EMBED QUERY                                                  │
│    query_vec = model.encode("what database for user prefs")     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. KNN SEARCH                                                   │
│    SELECT m.*, v.distance                                       │
│    FROM memories m JOIN vec_memories v                          │
│    WHERE v.embedding MATCH ?                                    │
│    ORDER BY distance LIMIT 10                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. RETURN RESULTS (Level 1)                                     │
│    [0.12] decisions:abc123 - "Use PostgreSQL for JSONB"         │
│    [0.34] learnings:def456 - "JSONB indexes need GIN"           │
│    [0.45] blockers:ghi789 - "Connection pooling resolved"       │
└─────────────────────────────────────────────────────────────────┘
                              │
                   (if --full flag)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. HYDRATE (Level 2)                                            │
│    git notes --ref=cs/decisions show abc123                     │
│    → Full note content loaded                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                   (if --files flag)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. FILE INSPECTION (Level 3)                                    │
│    git show abc123 --name-only                                  │
│    git show abc123:src/db/models.py                             │
│    → File snapshots from commit loaded                          │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Auto-Capture Integration Flow

```
User: /cs:p implement user authentication
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AUTO-RECALL: Similar past specs                                 │
│    recall.search("user authentication", namespace="inception")  │
│    recall.search("authentication", namespace="learnings")       │
│    → Display relevant memories to user                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCAFFOLD: Create spec directory + templates                     │
│    git commit -m "spec(user-auth): initialize specification"    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AUTO-CAPTURE: Inception memory                                  │
│    capture.capture(                                             │
│        namespace="inception",                                   │
│        spec="user-auth",                                        │
│        summary="Initiated spec: user authentication",           │
│        content=<initial problem statement>,                     │
│        commit="HEAD"                                            │
│    )                                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SOCRATIC ELICITATION                                            │
│    ... questions and answers ...                                │
│    → Each significant clarification captured                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AUTO-CAPTURE: Elicitation memories                              │
│    For each clarification:                                      │
│        capture.capture(namespace="elicitation", ...)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                         ... continues through research,
                             architecture, implementation plan ...
```

### 3.4 Code Review Flow

```
User: /cs:review --focus=security
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. PATTERN DETECTION (PRE-REVIEW)                               │
│    recall.search("security vulnerabilities", namespace="reviews")│
│    → Surface: "Similar findings seen 3x in past reviews"        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. PARALLEL AGENT DEPLOYMENT                                    │
│    Launch 6 specialists via Task tool (simultaneous):           │
│    ┌─────────┬─────────┬──────────────┐                         │
│    │Security │Perform. │Architecture  │                         │
│    │Analyst  │Engineer │Reviewer      │                         │
│    └─────────┴─────────┴──────────────┘                         │
│    ┌─────────┬─────────┬──────────────┐                         │
│    │Quality  │Test     │Documentation │                         │
│    │Analyst  │Analyst  │Reviewer      │                         │
│    └─────────┴─────────┴──────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. FINDINGS COLLECTION                                          │
│    - Aggregate results from all agents                          │
│    - Deduplicate overlapping findings                           │
│    - Prioritize by severity                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. MEMORY CAPTURE (per finding)                                 │
│    capture.capture(                                             │
│        namespace="reviews",                                     │
│        summary="[HIGH] SQL injection in user_query()",          │
│        content=<full finding with remediation>,                 │
│        tags=["security", "sql-injection"],                      │
│        commit="HEAD"                                            │
│    )                                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. ARTIFACT GENERATION                                          │
│    → CODE_REVIEW.md (full report with health scores)            │
│    → REVIEW_SUMMARY.md (executive summary)                      │
│    → REMEDIATION_TASKS.md (actionable checklist)                │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5 Remediation Flow

```
User: /cs:fix CODE_REVIEW.md --quick
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. LOAD FINDINGS                                                │
│    - Parse CODE_REVIEW.md (or query cs/reviews)                 │
│    - Filter by severity (--quick: Critical + High)              │
│    - Group by category                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. SPECIALIST ROUTING (per category)                            │
│    security     → security-engineer                             │
│    performance  → performance-engineer                          │
│    architecture → refactoring-specialist                        │
│    quality      → code-reviewer                                 │
│    tests        → test-automator                                │
│    docs         → documentation-engineer                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. FIX EXECUTION                                                │
│    For each finding:                                            │
│    - Agent applies fix                                          │
│    - If blocker: capture.capture(namespace="blockers", ...)     │
│    - If learning: capture.capture(namespace="learnings", ...)   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. VERIFICATION (pr-review-toolkit)                             │
│    ┌────────────────────┬────────────────┬──────────────────┐   │
│    │silent-failure-     │code-simplifier │pr-test-analyzer  │   │
│    │hunter              │                │                  │   │
│    └────────────────────┴────────────────┴──────────────────┘   │
│    → Detect error swallowing, over-engineering, test gaps       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. RESOLUTION CAPTURE                                           │
│    For each fixed finding:                                      │
│    git notes --ref=cs/reviews append -m "                       │
│      status: resolved                                           │
│      resolved_at: 2025-12-14T15:30:00Z                          │
│      resolution: <description of fix>                           │
│    " <commit>                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. OUTPUT                                                       │
│    → REMEDIATION_REPORT.md                                      │
│    → Summary: "Fixed 12/15 findings, 2 blockers, 3 learnings"   │
└─────────────────────────────────────────────────────────────────┘
```

## 4. File Structure

```
plugins/cs/
├── commands/
│   ├── remember.md          # /cs:remember command
│   ├── recall.md            # /cs:recall command
│   ├── context.md           # /cs:context command
│   ├── memory.md            # /cs:memory management
│   ├── review.md            # /cs:review code review
│   └── fix.md               # /cs:fix remediation
│
├── memory/
│   ├── __init__.py
│   ├── capture.py           # CaptureService
│   ├── recall.py            # RecallService
│   ├── sync.py              # SyncService
│   ├── index.py             # IndexService
│   ├── embedding.py         # EmbeddingService
│   ├── review.py            # ReviewService (code review + remediation)
│   ├── models.py            # Data models (Memory, MemoryResult, etc.)
│   ├── note_parser.py       # YAML front matter parser
│   ├── git_ops.py           # Git notes operations wrapper
│   └── config.py            # Configuration constants
│
└── hooks/
    └── memory_hooks.py      # Auto-capture hooks for commands

.cs-memory/                   # Gitignored
├── index.db                 # SQLite + sqlite-vec database
├── models/                  # Cached embedding model
│   └── all-MiniLM-L6-v2/
└── config.yaml              # Local configuration
```

## 5. Integration Points

### 5.0 SessionStart Hook - Memory Awareness

**Purpose**: Provide Claude with minimal awareness that memories exist at session start.

**Integration**: Extends existing `hooks/session_start.py` in claude-spec plugin.

```python
# plugins/cs/hooks/session_start.py (additions)

def get_memory_awareness() -> str | None:
    """
    Generate minimal memory awareness summary for Claude.
    Called during SessionStart hook execution.
    """
    index_path = Path(".cs-memory/index.db")
    if not index_path.exists():
        return None

    # Query namespace counts
    conn = sqlite3.connect(index_path)
    cursor = conn.execute("""
        SELECT namespace, COUNT(*)
        FROM memories
        GROUP BY namespace
    """)
    counts = dict(cursor.fetchall())
    conn.close()

    if not counts:
        return None

    total = sum(counts.values())
    summary_parts = [f"{v} {k}" for k, v in counts.items() if v > 0]

    return f"cs-memory: {total} memories available ({', '.join(summary_parts)})"

# In main() function, add to context output:
# memory_awareness = get_memory_awareness()
# if memory_awareness:
#     print(f"<system-reminder>{memory_awareness}</system-reminder>")
```

**Output Example**:
```
<system-reminder>
cs-memory: 23 memories available (12 decisions, 5 learnings, 3 blockers, 2 progress, 1 retrospective)

Use /cs:recall "query" to search memories when working on related topics.
</system-reminder>
```

**Key Behaviors**:
- Non-blocking: Fails silently if index doesn't exist or is corrupted
- Minimal: Single line summary, not full content dump
- Actionable: Reminds Claude of the recall command

### 5.1 Existing Command Modifications

#### /cs:p (Planning)
```markdown
## Memory Integration

### On Invocation
1. Call `recall.search(idea, namespace="inception")` for similar specs
2. Call `recall.search(idea, namespace="learnings")` for relevant learnings
3. Display findings before proceeding

### During Execution
1. After scaffold commit: capture inception memory
2. After elicitation: capture elicitation memories
3. After research: capture research memories
4. After architecture: capture decision memories (one per ADR)

### On Completion
1. Summary of memories captured
```

#### /cs:i (Implementation)
```markdown
## Memory Integration

### On Invocation
1. Call `recall.context(spec)` to load all planning memories
2. Call `recall.search(spec, namespace="blockers")` for past obstacles
3. Inject context into Claude's prompt

### During Execution
1. On task completion: capture progress memory
2. On obstacle: capture blocker memory
3. On resolution: update blocker with resolution
4. On discovery: capture learning memory
5. On deviation: capture decision memory

### On Completion
1. Summary of memories captured
```

#### /cs:c (Close-out)
```markdown
## Memory Integration

### On Invocation
1. Call `recall.context(spec)` for comprehensive memory load
2. Compare inception to final state

### During Execution
1. Synthesize retrospective from all memories
2. Extract learnings
3. Identify patterns

### On Completion
1. Capture retrospective memory
2. Capture extracted learnings
3. Capture identified patterns
```

## 6. Configuration

### 6.1 Git Configuration
```bash
# .git/config additions (automated by cs:memory init)
[remote "origin"]
    push = refs/notes/cs/*:refs/notes/cs/*
    fetch = refs/notes/cs/*:refs/notes/cs/*

[notes "cs"]
    mergeStrategy = cat_sort_uniq
```

### 6.2 Memory Configuration
```yaml
# .cs-memory/config.yaml
embedding:
  model: all-MiniLM-L6-v2
  dimensions: 384
  
index:
  path: .cs-memory/index.db
  
recall:
  default_limit: 10
  max_limit: 100
  
auto_capture:
  enabled: true
  namespaces:
    - inception
    - elicitation
    - research
    - decisions
    - progress
    - blockers
    - learnings
    - retrospective
    - patterns
```

### 6.3 Gitignore Additions
```
# .gitignore additions
.cs-memory/
```

## 7. Error Handling

This section defines error categories, detection mechanisms, and recovery actions per NFR-009.

### 7.1 Error Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `StorageError` | Git notes operations failed | Permission denied, no commits, ref not found |
| `IndexError` | SQLite operations failed | Locked database, corrupted file, sqlite-vec missing |
| `EmbeddingError` | Embedding generation failed | Model OOM, corrupted cache, missing model |
| `ParseError` | Note content malformed | Invalid YAML, missing required fields, bad timestamp |

### 7.2 Error Handling Strategy

```python
from dataclasses import dataclass
from enum import Enum

class ErrorCategory(Enum):
    STORAGE = "storage"
    INDEX = "index"
    EMBEDDING = "embedding"
    PARSE = "parse"

@dataclass
class MemoryError(Exception):
    """Base exception for cs-memory errors."""
    category: ErrorCategory
    message: str
    recovery_action: str

    def __str__(self) -> str:
        return f"[{self.category.value}] {self.message}\n→ {self.recovery_action}"

# Specific error classes
class StorageError(MemoryError):
    """Git notes operation failed."""
    def __init__(self, message: str, recovery_action: str):
        super().__init__(ErrorCategory.STORAGE, message, recovery_action)

class IndexError(MemoryError):
    """SQLite/sqlite-vec operation failed."""
    def __init__(self, message: str, recovery_action: str):
        super().__init__(ErrorCategory.INDEX, message, recovery_action)

class EmbeddingError(MemoryError):
    """Embedding generation failed."""
    def __init__(self, message: str, recovery_action: str):
        super().__init__(ErrorCategory.EMBEDDING, message, recovery_action)

class ParseError(MemoryError):
    """Note parsing failed."""
    def __init__(self, message: str, recovery_action: str):
        super().__init__(ErrorCategory.PARSE, message, recovery_action)
```

### 7.3 Common Errors and Recovery Actions

| Error | Detection | User Message | Recovery Action |
|-------|-----------|--------------|-----------------|
| No commits in repo | `git rev-parse HEAD` fails | "Cannot capture memory: no commits exist" | "Create at least one commit first" |
| Permission denied | Git command returns 128 | "Cannot write to Git notes: permission denied" | "Check repository permissions" |
| SQLite locked | `sqlite3.OperationalError` | "Index database is locked by another process" | "Wait and retry, or check for stuck processes" |
| sqlite-vec missing | Extension load fails | "sqlite-vec extension not found" | "Run `pip install sqlite-vec` or check installation" |
| Model OOM | `torch.cuda.OutOfMemoryError` or `MemoryError` | "Insufficient memory to load embedding model" | "Close other applications or use smaller model" |
| Corrupted model cache | Model load fails with file error | "Embedding model cache corrupted" | "Delete `.cs-memory/models/` and retry" |
| Invalid YAML | `yaml.YAMLError` | "Note contains invalid YAML front matter" | "Check note format at commit {sha}" |
| Missing required field | Validation fails | "Note missing required field: {field}" | "Add {field} to note at commit {sha}" |

### 7.4 Graceful Degradation

When errors occur, the system should degrade gracefully:

1. **Index errors**: Fall back to Git notes-only mode (no semantic search)
2. **Embedding errors**: Capture note without embedding, mark for later indexing
3. **Parse errors**: Log warning, skip malformed note, continue processing others
4. **Storage errors**: Fail the operation with clear message, preserve existing state

```python
def capture_with_fallback(
    namespace: str,
    content: str,
    commit: str
) -> CaptureResult:
    """Capture memory with graceful degradation."""
    try:
        # Normal path: note + embedding + index
        note_id = git_ops.add_note(namespace, content, commit)
        embedding = embedding_service.embed(content)
        index_service.insert(note_id, embedding)
        return CaptureResult(success=True, indexed=True)
    except EmbeddingError:
        # Degraded path: note only, mark for later indexing
        note_id = git_ops.add_note(namespace, content, commit)
        pending_index.add(note_id)
        return CaptureResult(success=True, indexed=False,
                            warning="Embedding failed, will retry on next reindex")
    except StorageError as e:
        # Cannot proceed without storage
        raise e
```
