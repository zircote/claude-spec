# Implementation Plan: cs-memory

## Overview

This implementation plan breaks the cs-memory system into three phases:
1. **Foundation** - Core infrastructure (storage, index, embedding)
2. **Integration** - Command implementation and auto-capture
3. **Intelligence** - Optimization and advanced features

Each phase builds on the previous, with clear milestones and testable deliverables.

---

## Phase 1: Foundation (Week 1-2)

### Milestone 1.1: Project Setup
**Goal**: Establish project structure and dependencies

- [ ] **T1.1.1**: Create memory module directory structure
  ```
  plugins/cs/memory/
  ├── __init__.py
  ├── models.py
  ├── config.py
  └── exceptions.py
  ```
  
- [ ] **T1.1.2**: Define configuration constants
  - Namespace definitions
  - Default embedding model
  - Index paths
  
- [ ] **T1.1.3**: Create data models
  ```python
  @dataclass
  class Memory:
      id: str
      commit_sha: str
      namespace: str
      spec: str | None
      phase: str | None
      summary: str
      content: str
      tags: list[str]
      timestamp: datetime
      status: str | None
      
  @dataclass
  class MemoryResult:
      memory: Memory
      distance: float
      
  class HydrationLevel(Enum):
      SUMMARY = 1
      FULL = 2
      FILES = 3
  ```

- [ ] **T1.1.4**: Add dependencies to requirements
  - sqlite-vec
  - sentence-transformers
  - pyyaml
  
**Acceptance**: Module importable, models instantiable

---

### Milestone 1.2: Note Parser
**Goal**: Parse and generate Git note content

- [ ] **T1.2.1**: Implement YAML front matter parser
  ```python
  def parse_note(content: str) -> tuple[dict, str]:
      """Parse note into (metadata, body)."""
  ```
  
- [ ] **T1.2.2**: Implement note formatter
  ```python
  def format_note(metadata: dict, body: str) -> str:
      """Format metadata and body into note content."""
  ```
  
- [ ] **T1.2.3**: Implement note validation
  - Required fields check
  - Type validation
  - Timestamp format validation
  
- [ ] **T1.2.4**: Write unit tests for parser
  - Valid notes parse correctly
  - Invalid notes raise appropriate errors
  - Round-trip (format → parse → format) preserves data

**Acceptance**: All parser tests pass

---

### Milestone 1.3: Git Operations
**Goal**: Wrapper for Git notes commands

- [ ] **T1.3.1**: Implement git_ops module
  ```python
  class GitOps:
      def add_note(self, namespace: str, content: str, 
                   commit: str = "HEAD") -> None
      def show_note(self, namespace: str, commit: str) -> str | None
      def list_notes(self, namespace: str) -> list[tuple[str, str]]
      def append_note(self, namespace: str, content: str, 
                      commit: str) -> None
      def configure_sync(self) -> None
  ```
  
- [ ] **T1.3.2**: Handle subprocess execution
  - Capture stdout/stderr
  - Raise on non-zero exit
  - Parse output appropriately
  
- [ ] **T1.3.3**: Write integration tests
  - Create temp git repo
  - Add/show/list notes
  - Verify note content

**Acceptance**: All git operations tests pass in isolated repo

---

### Milestone 1.4: Embedding Service
**Goal**: Local embedding generation

- [ ] **T1.4.1**: Implement EmbeddingService
  ```python
  class EmbeddingService:
      def __init__(self, model_name: str = "all-MiniLM-L6-v2")
      def embed(self, text: str) -> list[float]
      def embed_batch(self, texts: list[str]) -> list[list[float]]
  ```
  
- [ ] **T1.4.2**: Implement lazy model loading
  - Load on first use
  - Cache in memory
  
- [ ] **T1.4.3**: Handle model download
  - First-run experience
  - Progress indication
  
- [ ] **T1.4.4**: Write tests
  - Embedding dimension correct (384)
  - Similar texts have similar embeddings
  - Batch matches individual

- [ ] **T1.4.5**: Establish performance baselines (per NFR-001, NFR-002)
  - Measure cold-start latency (first embedding after model load)
  - Measure warm embedding latency (subsequent embeddings)
  - Document hardware assumptions (CPU model, RAM)
  - Compare against NFR targets, adjust if needed

**Acceptance**: Embeddings generated locally, correct dimensions, performance documented

---

### Milestone 1.5: Index Service
**Goal**: SQLite + sqlite-vec database operations

- [ ] **T1.5.1**: Implement database initialization
  ```python
  def initialize(self) -> None:
      """Create tables and load sqlite-vec extension."""
  ```
  
- [ ] **T1.5.2**: Implement CRUD operations
  ```python
  def insert(self, memory: Memory, embedding: list[float]) -> None
  def get(self, memory_id: str) -> Memory | None
  def delete(self, memory_id: str) -> None
  def update(self, memory: Memory) -> None
  ```
  
- [ ] **T1.5.3**: Implement vector search
  ```python
  def search_vector(
      self,
      embedding: list[float],
      filters: dict | None = None,
      limit: int = 10
  ) -> list[tuple[str, float]]:
      """Return (id, distance) pairs."""
  ```
  
- [ ] **T1.5.4**: Implement filtered queries
  - By spec
  - By namespace
  - By time range
  - Combined filters
  
- [ ] **T1.5.5**: Write tests
  - Table creation
  - Insert/retrieve
  - Vector search returns nearest
  - Filters work correctly

**Acceptance**: Vector search returns semantically similar results

---

### Milestone 1.6: Capture Service
**Goal**: Memory capture orchestration

- [ ] **T1.6.1**: Implement CaptureService
  ```python
  class CaptureService:
      def capture(
          self,
          namespace: str,
          summary: str,
          content: str,
          spec: str | None = None,
          commit: str = "HEAD",
          tags: list[str] | None = None,
          phase: str | None = None,
      ) -> Memory
  ```
  
- [ ] **T1.6.2**: Orchestrate capture flow
  1. Format note content
  2. Add git note
  3. Generate embedding
  4. Index in SQLite
  5. Return Memory object
  
- [ ] **T1.6.3**: Implement specialized capture methods
  ```python
  def capture_decision(self, spec, summary, context, 
                       rationale, alternatives) -> Memory
  def capture_blocker(self, spec, summary, problem) -> Memory
  def resolve_blocker(self, memory_id, resolution) -> Memory
  def capture_learning(self, spec, summary, insight) -> Memory
  ```
  
- [ ] **T1.6.4**: Write integration tests
  - Capture creates git note
  - Capture indexes memory
  - Memory retrievable after capture

**Acceptance**: End-to-end capture works, note visible in git

---

### Milestone 1.7: Recall Service
**Goal**: Memory retrieval orchestration

- [ ] **T1.7.1**: Implement RecallService
  ```python
  class RecallService:
      def search(
          self,
          query: str,
          spec: str | None = None,
          namespace: str | None = None,
          since: datetime | None = None,
          until: datetime | None = None,
          limit: int = 10,
      ) -> list[MemoryResult]
  ```
  
- [ ] **T1.7.2**: Implement progressive hydration
  ```python
  def hydrate(
      self,
      memory: MemoryResult,
      level: HydrationLevel,
  ) -> HydratedMemory
  ```
  
- [ ] **T1.7.3**: Implement context loading
  ```python
  def context(self, spec: str) -> SpecContext
  ```
  
- [ ] **T1.7.4**: Write tests
  - Search returns relevant results
  - Filters reduce result set
  - Hydration loads appropriate detail
  - Context loads all spec memories

**Acceptance**: Semantic search returns relevant memories

---

### Milestone 1.8: Sync Service
**Goal**: Index synchronization with git notes

- [ ] **T1.8.1**: Implement SyncService
  ```python
  class SyncService:
      def sync_note_to_index(self, namespace: str, 
                             commit_sha: str) -> None
      def full_reindex(self) -> IndexStats
      def verify_index(self) -> VerificationResult
  ```
  
- [ ] **T1.8.2**: Implement incremental sync
  - Single note indexing after capture
  
- [ ] **T1.8.3**: Implement full rebuild
  - Iterate all namespaces
  - Clear and repopulate index
  - Progress reporting
  
- [ ] **T1.8.4**: Write tests
  - Sync adds note to index
  - Reindex rebuilds from scratch
  - Verification detects drift

**Acceptance**: Index stays in sync with notes

---

## Phase 2: Integration (Week 3-4)

### Milestone 2.1: Command - /cs:remember
**Goal**: Explicit memory capture command

- [ ] **T2.1.1**: Create command markdown
  ```
  plugins/cs/commands/remember.md
  ```
  
- [ ] **T2.1.2**: Define command interface
  - Arguments: `<type> <summary>`
  - Options: `--commit`, `--spec`, `--tags`
  
- [ ] **T2.1.3**: Implement elicitation prompts
  - Decision: context, rationale, alternatives
  - Blocker: problem description
  - Learning: insight, applicability
  
- [ ] **T2.1.4**: Implement command handler
  - Parse arguments
  - Prompt for details
  - Call CaptureService
  - Display confirmation

**Acceptance**: `/cs:remember decision "summary"` creates indexed note

---

### Milestone 2.2: Command - /cs:recall
**Goal**: Semantic search command

- [ ] **T2.2.1**: Create command markdown
  ```
  plugins/cs/commands/recall.md
  ```
  
- [ ] **T2.2.2**: Define command interface
  - Arguments: `<query>`
  - Options: `--spec`, `--type`, `--since`, `--until`, `--full`, `--files`, `--limit`
  
- [ ] **T2.2.3**: Implement result formatting
  - Summary view (default)
  - Full view (--full)
  - With files (--files)
  
- [ ] **T2.2.4**: Implement command handler
  - Parse arguments and options
  - Call RecallService
  - Format and display results

**Acceptance**: `/cs:recall "query"` returns relevant memories

---

### Milestone 2.3: Command - /cs:context
**Goal**: Context bootstrap command

- [ ] **T2.3.1**: Create command markdown
  ```
  plugins/cs/commands/context.md
  ```
  
- [ ] **T2.3.2**: Define command interface
  - Arguments: `<spec-slug>`
  - Options: `--recent`
  
- [ ] **T2.3.3**: Implement context formatting
  - Chronological ordering
  - Namespace grouping
  - Token estimation
  
- [ ] **T2.3.4**: Implement command handler

**Acceptance**: `/cs:context user-auth` loads all spec memories

---

### Milestone 2.4: Command - /cs:memory
**Goal**: Memory management command

- [ ] **T2.4.1**: Create command markdown
  ```
  plugins/cs/commands/memory.md
  ```
  
- [ ] **T2.4.2**: Implement subcommands
  - `status` - Show statistics
  - `reindex` - Rebuild index
  - `export` - Export to JSON
  - `gc` - Garbage collection
  
- [ ] **T2.4.3**: Implement each subcommand handler

**Acceptance**: All memory management subcommands functional

---

### Milestone 2.5: Auto-Capture - /cs:p Integration
**Goal**: Automatic memory capture during planning

- [ ] **T2.5.1**: Add auto-recall on invocation
  - Search for similar specs
  - Search for relevant learnings
  - Display findings
  
- [ ] **T2.5.2**: Add inception capture
  - After scaffold commit
  - Capture problem statement
  
- [ ] **T2.5.3**: Add elicitation capture
  - After each significant clarification
  - Extract key constraints
  
- [ ] **T2.5.4**: Add research capture
  - After parallel agent research
  - Summarize findings
  
- [ ] **T2.5.5**: Add decision capture
  - After architecture generation
  - One note per ADR
  
- [ ] **T2.5.6**: Update /cs:p command markdown

**Acceptance**: `/cs:p` automatically captures all planning memories

---

### Milestone 2.6: Auto-Capture - /cs:i Integration
**Goal**: Automatic memory capture during implementation

- [ ] **T2.6.1**: Add auto-recall on invocation
  - Load all spec decisions
  - Load research findings
  - Search for similar blockers
  
- [ ] **T2.6.2**: Add progress capture
  - On task completion
  - Track completion percentage
  
- [ ] **T2.6.3**: Add blocker capture
  - On obstacle encounter
  - Update on resolution
  
- [ ] **T2.6.4**: Add learning capture
  - On technical discovery
  - Extract reusable insight
  
- [ ] **T2.6.5**: Add deviation capture
  - When plan changes
  - Document rationale
  
- [ ] **T2.6.6**: Update /cs:i command markdown

**Acceptance**: `/cs:i` automatically captures all implementation memories

---

### Milestone 2.7: Auto-Capture - /cs:c Integration
**Goal**: Automatic memory capture during close-out

- [ ] **T2.7.1**: Add comprehensive recall
  - Load all memories for spec
  - Build chronological narrative
  
- [ ] **T2.7.2**: Add retrospective capture
  - Compare inception to outcome
  - Document what worked/didn't
  
- [ ] **T2.7.3**: Add learning extraction
  - Identify reusable patterns
  - Document anti-patterns
  
- [ ] **T2.7.4**: Add pattern capture
  - Generalize for cross-spec use
  - Tag for broad applicability
  
- [ ] **T2.7.5**: Update /cs:c command markdown

**Acceptance**: `/cs:c` synthesizes and captures retrospective memories

---

## Phase 3: Intelligence (Week 5-6)

### Milestone 3.1: Search Optimization
**Goal**: Improve search relevance and performance

- [ ] **T3.1.1**: Implement query expansion
  - Synonym expansion
  - Acronym handling
  
- [ ] **T3.1.2**: Implement result re-ranking
  - Recency boost
  - Same-spec boost
  
- [ ] **T3.1.3**: Add search caching
  - Cache recent queries
  - Invalidate on new memories
  
- [ ] **T3.1.4**: Benchmark performance
  - Measure latency at scale
  - Identify bottlenecks

**Acceptance**: Search <500ms for 10k memories

---

### Milestone 3.2: Pattern Extraction
**Goal**: Automatic pattern identification

- [ ] **T3.2.1**: Implement pattern detection
  - Similar decisions across specs
  - Recurring blockers
  - Common learnings
  
- [ ] **T3.2.2**: Implement pattern suggestions
  - Surface during planning
  - Recommend based on context
  
- [ ] **T3.2.3**: Implement pattern lifecycle
  - Create from retrospective
  - Update with new evidence
  - Deprecate when outdated

**Acceptance**: Patterns automatically extracted from retrospectives

---

### Milestone 3.3: Memory Lifecycle
**Goal**: Long-term memory management

- [ ] **T3.3.1**: Implement memory aging
  - Track access frequency
  - Identify stale memories
  
- [ ] **T3.3.2**: Implement summarization
  - Compress old detailed memories
  - Preserve key insights
  
- [ ] **T3.3.3**: Implement archival
  - Archive completed spec memories
  - Retain patterns and learnings

**Acceptance**: Memory system scales to large histories

---

### Milestone 3.4: Code Review Integration
**Goal**: Capture code review findings

- [ ] **T3.4.1**: Create /cs:review command
  - Trigger review capture
  - Or integrate with PR hooks
  
- [ ] **T3.4.2**: Implement review memory capture
  - Findings categorized by severity
  - Resolution tracking
  
- [ ] **T3.4.3**: Surface review patterns
  - Common issues
  - Best practices

**Acceptance**: Code review knowledge captured and searchable

---

### Milestone 3.5: Documentation and Polish
**Goal**: Production readiness

- [ ] **T3.5.1**: Write user documentation
  - Command reference
  - Configuration guide
  - Troubleshooting
  
- [ ] **T3.5.2**: Write developer documentation
  - Architecture overview
  - Extension points
  - Contributing guide
  
- [ ] **T3.5.3**: Add telemetry
  - Memory capture counts
  - Search latency
  - Index health
  
- [ ] **T3.5.4**: Final testing
  - End-to-end scenarios
  - Edge cases
  - Performance benchmarks

**Acceptance**: System ready for release

---

## Dependencies

```
Phase 1:
  M1.1 → M1.2, M1.3, M1.4, M1.5
  M1.2 + M1.3 → M1.6
  M1.4 + M1.5 → M1.6
  M1.6 → M1.7
  M1.6 + M1.7 → M1.8

Phase 2:
  M1.6 → M2.1
  M1.7 → M2.2, M2.3
  M1.8 → M2.4
  M2.1 + M2.2 → M2.5, M2.6, M2.7

Phase 3:
  M2.5 + M2.6 + M2.7 → M3.1, M3.2, M3.3
  M2.* → M3.4, M3.5
```

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| sqlite-vec compatibility issues | Medium | High | Test early, have fallback to basic SQL |
| Embedding model too slow | Low | Medium | Use smaller model, batch operations |
| Git notes conflicts on team | Medium | Medium | Document merge strategies, test scenarios |
| Index corruption | Low | Low | Rebuild from notes is trivial |
| Context window overflow | Medium | Medium | Aggressive summarization, smart hydration |
