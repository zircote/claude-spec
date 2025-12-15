# Requirements Specification: cs-memory

## 1. User Stories

### 1.1 Memory Capture

**US-001: Explicit Memory Capture**
> As a developer, I want to explicitly capture a decision, learning, or blocker so that it persists across sessions and can be recalled later.

Acceptance Criteria:
- [ ] `/cs:remember decision "summary"` creates a structured note in refs/notes/cs/decisions
- [ ] User is prompted for context, rationale, and alternatives
- [ ] Note attaches to HEAD commit (or specified commit)
- [ ] Note is indexed in SQLite immediately after creation
- [ ] Confirmation message shows note ID and attached commit

**US-002: Auto-Capture During Planning**
> As a developer using /cs:p, I want memories to be automatically captured without manual intervention so that the planning phase is fully documented.

Acceptance Criteria:
- [ ] Inception memory captured when spec is initialized
- [ ] Elicitation memories captured for each significant clarification
- [ ] Research memories captured for findings from parallel agents
- [ ] Decision memories captured for each architectural choice
- [ ] All memories attach to appropriate phase commits

**US-003: Auto-Capture During Implementation**
> As a developer using /cs:i, I want progress, blockers, and learnings to be automatically captured so that implementation knowledge persists.

Acceptance Criteria:
- [ ] Progress memory captured on task completion
- [ ] Blocker memory captured when obstacle encountered
- [ ] Blocker updated with resolution when resolved
- [ ] Learning memory captured for technical discoveries
- [ ] Deviation memory captured when plan changes

**US-004: Auto-Capture During Close-out**
> As a developer using /cs:c, I want retrospective insights and patterns to be automatically extracted and stored.

Acceptance Criteria:
- [ ] Retrospective memory synthesizes all spec memories
- [ ] Learnings extracted and stored separately
- [ ] Patterns identified for cross-spec applicability
- [ ] All close-out memories attach to archive commit

### 1.2 Memory Recall

**US-005: Semantic Search**
> As a developer, I want to search memories using natural language so that I can find relevant context without knowing exact keywords.

Acceptance Criteria:
- [ ] `/cs:recall "query"` returns semantically similar memories
- [ ] Results ranked by relevance (distance score)
- [ ] Results include commit SHA, type, summary
- [ ] Search completes in <500ms for typical repositories

**US-006: Filtered Recall**
> As a developer, I want to filter memory searches by spec, namespace, or time range.

Acceptance Criteria:
- [ ] `--spec=<slug>` filters to specific specification
- [ ] `--type=<namespace>` filters to memory type
- [ ] `--since=<date>` and `--until=<date>` provide temporal bounds
- [ ] Filters combine with semantic search

**US-007: Progressive Hydration**
> As a developer, I want to control how much detail is loaded for recalled memories.

Acceptance Criteria:
- [ ] Default returns summaries only (Level 1)
- [ ] `--full` flag returns complete note content (Level 2)
- [ ] `--files` flag includes file snapshots from commit (Level 3)
- [ ] Level 3 uses `git show <sha>:<path>` for file content

**US-008: Context Bootstrap**
> As a developer resuming work on a spec, I want to quickly load all relevant context.

Acceptance Criteria:
- [ ] `/cs:context <spec>` loads all memories for specification
- [ ] Memories presented in chronological order
- [ ] Grouped by namespace for clarity
- [ ] Total token estimate displayed

### 1.3 Memory Management

**US-009: Index Rebuild**
> As a developer, I want to rebuild the vector index from Git notes if it becomes corrupted or outdated.

Acceptance Criteria:
- [ ] `/cs:memory reindex` rebuilds entire index
- [ ] Rebuilds from all refs/notes/cs/* namespaces
- [ ] Progress indicator shows rebuild status
- [ ] Verification confirms index matches notes

**US-010: Memory Status**
> As a developer, I want to see statistics about stored memories.

Acceptance Criteria:
- [ ] `/cs:memory status` shows memory counts by namespace
- [ ] Shows index health (last sync, record count)
- [ ] Shows storage size (notes + index)

**US-011: Memory Export**
> As a developer, I want to export memories for a spec to a portable format.

Acceptance Criteria:
- [ ] `/cs:memory export --spec=<slug>` exports to JSON
- [ ] Export includes all namespaces
- [ ] Export preserves commit associations

### 1.4 Auto-Recall

**US-012: Recall on Planning Start**
> As a developer starting /cs:p, I want similar past work automatically surfaced.

Acceptance Criteria:
- [ ] System searches for similar inception memories
- [ ] Relevant learnings from past specs displayed
- [ ] Team patterns and preferences loaded
- [ ] User can proceed with or review findings

**US-013: Recall on Implementation Start**
> As a developer starting /cs:i, I want all planning context automatically loaded.

Acceptance Criteria:
- [ ] All decisions for the spec loaded
- [ ] Research findings loaded
- [ ] Blockers from similar implementations surfaced
- [ ] Context summary displayed

**US-014: Recall on Close-out**
> As a developer running /cs:c, I want comprehensive memory synthesis.

Acceptance Criteria:
- [ ] All memories across namespaces for spec loaded
- [ ] Original inception compared to outcome
- [ ] Chronological narrative constructed

### 1.5 Code Review Memory Integration

**US-017: Code Review Memory Capture**
> As a developer using /cs:review, I want code review findings automatically captured as searchable memories so that patterns and recurring issues can be identified across reviews.

Acceptance Criteria:
- [ ] `/cs:review` uses 6 parallel specialist agents (Security, Performance, Architecture, Quality, Tests, Documentation)
- [ ] Each finding is captured as a note in `cs/reviews` namespace attached to the reviewed commit
- [ ] Findings include severity (critical/high/medium/low), category, and remediation guidance
- [ ] Before review starts, system searches for similar past findings and surfaces patterns
- [ ] Produces CODE_REVIEW.md, REVIEW_SUMMARY.md, REMEDIATION_TASKS.md artifacts
- [ ] Summary of memories captured displayed on completion

**US-018: Code Review Remediation Tracking**
> As a developer using /cs:fix, I want remediation actions tracked with resolution notes so that we can learn from how issues were resolved.

Acceptance Criteria:
- [ ] `/cs:fix` reads findings from CODE_REVIEW.md or `cs/reviews` namespace
- [ ] Specialist agents routed by category (security-engineer, performance-engineer, etc.)
- [ ] On successful fix, original review note updated with `status: resolved` and resolution details
- [ ] Blockers encountered during fix captured to `cs/blockers`
- [ ] Learnings from fixes captured to `cs/learnings`
- [ ] Verification via pr-review-toolkit agents (silent-failure-hunter, code-simplifier, pr-test-analyzer)
- [ ] Supports `--quick` mode for non-interactive remediation

**US-019: Review Pattern Detection**
> As a developer, I want recurring review issues automatically identified so that systemic problems can be addressed.

Acceptance Criteria:
- [ ] System identifies findings that appear across multiple reviews
- [ ] Patterns surface during `/cs:review` invocation ("You've seen this 3 times before")
- [ ] High-frequency patterns can be promoted to `cs/patterns` namespace
- [ ] Pattern suggestions include links to related review memories

### 1.6 Proactive Memory Awareness

**US-015: Session Start Awareness**
> As Claude Code, at session start I want minimal notification that memories exist so I know to search when working on relevant topics.

Acceptance Criteria:
- [ ] SessionStart hook checks for `.cs-memory/index.db` existence
- [ ] If memories exist, outputs summary: "cs-memory: N memories available for this project"
- [ ] Summary includes counts by namespace (e.g., "12 decisions, 8 learnings, 3 blockers")
- [ ] Does NOT auto-load all memories (minimal awareness, not context flooding)

**US-016: Proactive Topic Search**
> As Claude Code, when working on a topic I want to proactively search for relevant memories without waiting for explicit /cs:recall.

Acceptance Criteria:
- [ ] When processing a task related to a known namespace topic, system suggests relevant memories
- [ ] Proactive search triggered by topic detection (e.g., working on auth → search "authentication" memories)
- [ ] Results presented as suggestions, not forced injection
- [ ] User can dismiss or explore suggested memories
- [ ] Search is non-blocking and background (doesn't slow primary work)

**Implementation Note**: Topic detection algorithm will be designed in Phase 3 (Intelligence) based on usage patterns observed during Phase 1-2. The algorithm is intentionally unspecified to avoid premature optimization. See NFR-013 for noise constraints.

## 2. Functional Requirements

### 2.1 Note Schema

**FR-001**: Notes MUST use YAML front matter with the following required fields:
- `type`: Memory type (decision, learning, blocker, etc.)
- `spec`: Specification slug
- `timestamp`: ISO 8601 datetime
- `summary`: One-line summary (≤100 characters)

**FR-002**: Notes MUST use YAML front matter with the following optional fields:
- `phase`: Lifecycle phase (planning, implementation, review, etc.)
- `tags`: Array of categorization tags
- `relates_to`: Array of related commit SHAs
- `status`: For blockers (unresolved, resolved)

**FR-003**: Note body MUST be valid Markdown with semantic sections.

### 2.2 Namespace Structure

**FR-004**: The system MUST support the following namespaces:
- `cs/inception` - Problem statements, scope, success criteria
- `cs/elicitation` - Requirements clarifications, constraints
- `cs/research` - External findings, technology evaluations
- `cs/decisions` - Architecture Decision Records
- `cs/progress` - Task completions, milestones
- `cs/blockers` - Obstacles and resolutions
- `cs/reviews` - Code review findings
- `cs/learnings` - Technical insights, patterns
- `cs/retrospective` - Post-mortems
- `cs/patterns` - Cross-spec generalizations

**FR-005**: Each namespace MUST map to a Git notes ref: `refs/notes/cs/<namespace>`

### 2.3 Storage Operations

**FR-006**: Memory capture MUST create a Git note attached to a commit:
```bash
git notes --ref=cs/<namespace> add -m "<content>" <commit>
```

**FR-007**: Memory update MUST append to existing note:
```bash
git notes --ref=cs/<namespace> append -m "<content>" <commit>
```

**FR-008**: Git configuration MUST be set for automatic note sync:
```bash
git config --add remote.origin.push "refs/notes/cs/*:refs/notes/cs/*"
git config --add remote.origin.fetch "refs/notes/cs/*:refs/notes/cs/*"
```

### 2.4 Index Operations

**FR-009**: Index MUST reside in `.cs-memory/index.db` (gitignored)

**FR-010**: Index schema MUST include:
- `memories` table with metadata columns
- `vec_memories` virtual table for embeddings (384 dimensions)

**FR-011**: Index sync MUST be triggered on:
- Memory capture
- Manual reindex command
- Repository clone (full rebuild)

### 2.5 Retrieval Operations

**FR-012**: Semantic search MUST use KNN against vec_memories:
```sql
SELECT m.*, v.distance
FROM memories m
JOIN vec_memories v ON m.rowid = v.rowid
WHERE v.embedding MATCH ?
ORDER BY distance
LIMIT ?
```

**FR-013**: Retrieval MUST support filtering by metadata columns before vector search.

### 2.6 Embedding Operations

**FR-014**: Embeddings MUST be generated locally using sentence-transformers or Ollama.

**FR-015**: Default model MUST be `all-MiniLM-L6-v2` (384 dimensions).

**FR-016**: Embedding generation MUST be synchronous during capture.

### 2.7 Code Review Operations

**FR-017**: `/cs:review` MUST deploy 6 parallel specialist agents:
- Security Analyst (OWASP, CVEs, secrets)
- Performance Engineer (N+1 queries, algorithms, caching)
- Architecture Reviewer (SOLID, patterns, complexity)
- Code Quality Analyst (naming, DRY, dead code)
- Test Coverage Analyst (coverage gaps, edge cases)
- Documentation Reviewer (docstrings, README, API docs)

**FR-018**: Review findings MUST capture to `cs/reviews` namespace as a **single JSON note per commit** containing an array of findings. This is required because Git notes allows only one note per object per namespace.

Schema for the note content:
```yaml
---
type: review_batch
spec: <active-spec-or-null>
timestamp: <iso-8601>
summary: "Code review: N findings (X critical, Y high)"
---

```json
{
  "findings": [
    {
      "id": "<uuid>",
      "severity": "critical|high|medium|low",
      "category": "security|performance|architecture|quality|tests|documentation",
      "file": "<file-path>",
      "line": <line-number>,
      "summary": "<one-line description>",
      "details": "<full finding with remediation guidance>",
      "status": "open|resolved",
      "resolution": null
    }
  ]
}
```

Each finding within the array is indexed separately for embedding-based search. The `id` field (UUID) enables individual finding references and resolution tracking.

**FR-019**: `/cs:fix` MUST route findings to specialist agents by category:
| Category | Agent Type |
|----------|------------|
| security | security-engineer |
| performance | performance-engineer |
| architecture | refactoring-specialist |
| quality | code-reviewer |
| tests | test-automator |
| documentation | documentation-engineer |

**FR-020**: `/cs:fix` MUST support interactive decision points unless `--quick` flag provided:
- Severity filter selection (which severities to address)
- Category selection (which finding types)
- Conflict resolution (how to handle fixes to same files)
- Verification depth (full/quick/tests-only/skip)
- Commit strategy (single/separate/review-first)

**FR-021**: Resolution of review findings MUST update the original note with `status: resolved` and `resolution` field.

### 2.8 Concurrency Safety

**FR-022**: Memory capture MUST be atomic within a single repository clone:
- File locking MUST be used to prevent concurrent note writes to the same commit
- Lock file location: `.cs-memory/.capture.lock`
- Lock acquisition timeout: 5 seconds
- On timeout, operation MUST fail with clear error message

**FR-023**: Note operations MUST use `git notes append` (not `add`) when a note may already exist for the target commit, to prevent data loss from overwrites.

## 3. Non-Functional Requirements

### 3.1 Performance

**NFR-001**: Semantic search MUST complete in <500ms for repositories with <10,000 memories.

**NFR-002**: Memory capture MUST complete in <2s including embedding generation.

**NFR-003**: Full index rebuild MUST complete in <60s for <10,000 memories.

### 3.2 Reliability

**NFR-004**: Index corruption MUST be recoverable via rebuild from notes.

**NFR-005**: Note conflicts MUST be resolvable via Git's merge strategies.

**NFR-006**: Partial failures MUST not corrupt existing notes or index.

### 3.3 Usability

**NFR-007**: Auto-capture MUST require zero manual intervention during normal workflow.

**NFR-008**: Recall results MUST clearly indicate relevance ranking.

**NFR-009**: Error messages MUST suggest corrective actions.

### 3.4 Compatibility

**NFR-010**: System MUST work with Git 2.20+.

**NFR-011**: System MUST work with Python 3.11+.

**NFR-012**: System MUST integrate with existing claude-spec plugin architecture.

**NFR-013**: Proactive memory suggestions (US-016) MUST surface ≤3 suggestions per detected topic to avoid noise.

## 4. Constraints

**C-001**: Must use sqlite-vec (not sqlite-vss) for vector operations.

**C-002**: Must not require external API calls for embedding generation.

**C-003**: Must preserve existing claude-spec command behavior.

**C-004**: Index must be gitignored (derived data).

**C-005**: Notes must be human-readable when viewed via `git notes show`.
