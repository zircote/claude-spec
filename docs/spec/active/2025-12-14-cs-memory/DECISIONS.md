 # Technical Decisions: cs-memory

This document records key architectural and technical decisions made for the cs-memory system.

---

## ADR-001: Git Notes for Canonical Storage

### Status
Accepted

### Context
We need persistent storage for AI-generated memories that:
- Survives across Claude Code sessions
- Travels with the repository
- Attaches to specific commits
- Is version-controlled
- Doesn't pollute commit history

### Decision
Use Git notes as the canonical storage layer for all memories.

### Alternatives Considered

1. **Separate files (DECISIONS.md, LEARNINGS.md)**
   - Pros: Human-readable, familiar
   - Cons: Manual maintenance, no commit coupling, merge conflicts

2. **SQLite database (committed)**
   - Pros: Structured, queryable
   - Cons: Binary file conflicts, no commit coupling

3. **External database (e.g., PostgreSQL)**
   - Pros: Full query power, scales well
   - Cons: External dependency, sync complexity, not distributed

4. **Commit message metadata (trailers)**
   - Pros: Native to commits
   - Cons: Immutable after push, limited size

### Consequences
- Memories are inherently distributed with repo
- Each memory attaches to exactly one commit
- Note namespaces provide logical separation
- Requires Git notes sync configuration
- Limited UI support in GitHub/GitLab (notes not displayed)

---

## ADR-002: SQLite + sqlite-vec for Index Layer

### Status
Accepted

### Context
Semantic search requires vector similarity operations. Options:
- Cloud vector databases (Pinecone, Weaviate)
- Self-hosted vector databases (Milvus, Qdrant)
- Embedded solutions (FAISS, sqlite-vec)

### Decision
Use SQLite with the sqlite-vec extension for the vector index.

### Rationale
- **Local-first**: No external dependencies or API calls
- **Portable**: Single file, cross-platform
- **Rebuildable**: Index is derived data, can regenerate from notes
- **Sufficient scale**: Handles thousands of vectors efficiently
- **SQL familiarity**: Standard query patterns for metadata filtering

### Alternatives Considered

1. **FAISS**
   - Pros: Very fast, battle-tested
   - Cons: Separate from metadata, no SQL integration

2. **ChromaDB**
   - Pros: Purpose-built for AI, nice API
   - Cons: Heavier dependency, less mature

3. **sqlite-vss**
   - Pros: Similar to sqlite-vec
   - Cons: Older, less maintained, requires training for some indexes

### Consequences
- Index lives in `.cs-memory/index.db` (gitignored)
- Rebuild mechanism required for recovery
- Limited to ~100k vectors before performance degrades
- sqlite-vec extension must be installed

---

## ADR-003: Local Embedding Model

### Status
Accepted

### Context
Semantic search requires text embeddings. Options:
- Cloud APIs (OpenAI, Cohere, Voyage)
- Local models (sentence-transformers, Ollama)

### Decision
Use local embedding generation via sentence-transformers, defaulting to `all-MiniLM-L6-v2` (384 dimensions).

### Rationale
- **Privacy**: No project data leaves the machine
- **Offline capable**: Works without internet
- **Free**: No API costs
- **Fast enough**: ~50ms per embedding on CPU
- **Quality**: Sufficient for our semantic similarity needs

### Alternatives Considered

1. **OpenAI text-embedding-3-small**
   - Pros: Higher quality, 1536 dimensions
   - Cons: API cost, privacy concerns, requires internet

2. **Ollama with embedding model**
   - Pros: Local, flexible
   - Cons: Heavier setup, slower

3. **Larger local models (e5-large, bge-large)**
   - Pros: Better quality
   - Cons: Slower, more memory

### Consequences
- First run downloads ~90MB model
- 384-dimension embeddings (balance of quality/size)
- Model cached in `.cs-memory/models/`
- Can be configured to use different model

---

## ADR-004: YAML Front Matter + Markdown Body

### Status
Accepted

### Context
Notes need both machine-parseable metadata and human-readable content.

### Decision
Use YAML front matter (delimited by `---`) for structured metadata, followed by Markdown body for content.

### Rationale
- **Familiar format**: Common in static site generators, docs
- **Machine parseable**: YAML is structured, typed
- **Human readable**: Markdown renders nicely
- **Flexible**: Body can contain any Markdown structure
- **Tooling**: Many parsers available

### Format
```yaml
---
type: decision
spec: user-auth
phase: architecture
timestamp: 2025-12-14T10:30:00Z
tags: [jwt, security]
summary: Chose RS256 over HS256 for JWT signing
---

## Context
[Human-readable context]

## Decision
[Human-readable decision]
```

### Consequences
- Parser needed for extraction
- Validation rules for required fields
- Round-trip preservation important

---

## ADR-005: Namespace-per-Type Organization

### Status
Accepted

### Context
Memories have different types (decisions, learnings, blockers). Options:
- Single namespace, type in metadata
- Separate namespace per type

### Decision
Use separate Git notes namespaces for each memory type.

### Rationale
- **Isolation**: Different sync/retention policies possible
- **Query efficiency**: Type filtering at storage level
- **Clarity**: `refs/notes/cs/decisions` is self-documenting
- **Git operations**: Can list/manage types independently

### Namespaces
```
refs/notes/cs/
├── inception
├── elicitation
├── research
├── decisions
├── progress
├── blockers
├── reviews
├── learnings
├── retrospective
└── patterns
```

### Consequences
- Multiple refs to sync
- Git config lists all namespaces
- Index must query across namespaces

---

## ADR-006: Progressive Hydration Strategy

### Status
Accepted

### Context
Context windows are limited. Loading all memory details is wasteful.

### Decision
Implement three-level progressive hydration:
1. **Summary**: ID, type, one-line summary, distance
2. **Full**: Complete note content
3. **Files**: File snapshots from associated commit

### Rationale
- **Efficiency**: Only load what's needed
- **Flexibility**: User controls detail level
- **Performance**: Summary search is fast
- **Completeness**: Full detail available when needed

### Implementation
```python
class HydrationLevel(Enum):
    SUMMARY = 1  # Default recall
    FULL = 2     # --full flag
    FILES = 3    # --files flag
```

### Consequences
- Multi-step retrieval possible
- Git operations only when needed
- Clear UX for detail level

---

## ADR-007: Commit Anchor Strategy

### Status
Accepted

### Context
Memories must attach to commits (per core principle). Pre-implementation memories have no natural commit.

### Decision
Use specification documents as commit anchors:
1. Scaffold spec directory early with templates
2. Commit scaffold immediately
3. Amend within phase as understanding develops
4. New commit at phase boundaries

### Rationale
- **Every memory has anchor**: No orphan memories
- **Clean history**: Phase-delineated commits
- **Document-as-anchor**: Spec docs serve dual purpose
- **Flexible**: Amend allows refinement

### Pattern
```
spec(slug): initialize specification     <- inception, elicitation memories
spec(slug): complete requirements        <- research memories
spec(slug): complete architecture        <- decision memories
feat(slug): implement feature X          <- progress, blocker, learning memories
spec(slug): complete, archived           <- retrospective, pattern memories
```

### Consequences
- Requires early scaffold commit
- Amend pattern during phases
- Clear phase transition commits

---

## ADR-008: Shared Team Memory

### Status
Accepted

### Context
Memories could be personal (per-developer) or shared (team knowledge).

### Decision
All memories are shared and sync with the repository via Git notes push/pull.

### Rationale
- **Knowledge preservation**: Team inherits institutional knowledge
- **Onboarding**: New members benefit from history
- **Consistency**: Decisions don't get relitigated
- **Collaboration**: Shared patterns emerge

### Git Configuration
```bash
git config --add remote.origin.push "refs/notes/cs/*:refs/notes/cs/*"
git config --add remote.origin.fetch "refs/notes/cs/*:refs/notes/cs/*"
```

### Consequences
- Note conflicts possible (use cat_sort_uniq merge)
- Privacy considerations for sensitive decisions
- Everyone sees everyone's memories

---

## ADR-009: Auto-Capture at 100%

### Status
Accepted

### Context
Memory capture could be manual (explicit command), semi-automatic (prompted), or fully automatic.

### Decision
Implement fully automatic capture during `/cs:p`, `/cs:i`, `/cs:c` workflows with zero manual intervention required.

### Rationale
- **Low friction**: Developers don't have to remember to capture
- **Comprehensive**: Nothing falls through the cracks
- **Consistent**: Standard capture points across projects
- **High signal**: Captures at meaningful moments

### Capture Points
| Command | Auto-Captures |
|---------|---------------|
| /cs:p | inception, elicitation, research, decisions |
| /cs:i | progress, blockers, learnings, deviations |
| /cs:c | retrospective, learnings, patterns |

### Consequences
- More memories generated (storage growth)
- Potential for noise (need quality filters)
- Must not slow down primary workflow

---

## ADR-010: Index as Derived Data

### Status
Accepted

### Context
The SQLite index could be:
- Source of truth (committed)
- Derived data (gitignored, rebuilt from notes)

### Decision
Treat the index as derived data that can be rebuilt from Git notes at any time.

### Rationale
- **No sync issues**: Notes are authoritative
- **Recovery**: Corruption is trivially fixable
- **Clean repo**: No binary files committed
- **Flexibility**: Index schema can evolve

### Implementation
```
.gitignore:
  .cs-memory/

Rebuild:
  /cs:memory reindex
```

### Consequences
- Index must be rebuilt on clone
- First-run experience needs rebuild
- Notes must contain all necessary data

---

## ADR-011: Proactive Memory Recall Strategy

### Status
Accepted

### Context
Claude Code suffers from context loss after compaction. Without intervention, Claude "strays from documented guidance" and forgets prior decisions, requiring developers to repeatedly reinforce context.

Two recall approaches were considered:
1. **Explicit only**: Memories only recalled via `/cs:recall` command
2. **Proactive**: System automatically searches for relevant memories during work

### Decision
Implement a **two-tier proactive recall** strategy:

1. **Session awareness** (minimal): At session start, notify Claude that memories exist with namespace counts. No content loaded.

2. **Topic-based proactive search** (on-demand): When Claude works on a topic, proactively search for relevant memories and suggest them. Non-blocking, dismissible.

### Rationale
- **Minimal awareness prevents drift**: Claude knows to search before making decisions
- **Proactive search reduces friction**: No need to remember to run `/cs:recall`
- **Non-blocking preserves flow**: Suggestions don't interrupt primary workflow
- **Progressive revelation**: Summary → full content only when needed

### Implementation
```
SessionStart Hook:
  → Check for .cs-memory/index.db
  → Output: "cs-memory: N memories available"
  → Remind: "Use /cs:recall when working on related topics"

During Work:
  → Topic detection triggers background search
  → Relevant memories surfaced as suggestions
  → User can dismiss or explore
```

### Consequences
- Additional hook integration required
- Topic detection logic needs careful tuning to avoid noise
- Must not slow down primary workflow
- Balances awareness with context window preservation

---

## ADR-012: SHA-Based Decision Identification (Revised)

### Status
Accepted (Revised from original "Monotonic ADR Numbering")

### Context
Architecture Decision Records (ADRs) need unique identifiers. Original options considered:
1. **Timestamp-based**: `ADR-2025-12-14-001`
2. **Sequential**: `ADR-001`, `ADR-002`, ...
3. **Content hash**: Random unique ID
4. **Commit SHA**: Use Git's native identifier

The original decision (sequential numbering) introduced a distributed synchronization problem: if two developers create decisions before syncing, both get the same number.

### Decision
Use **commit SHA as the unique identifier** for decisions, with the existing `timestamp` field for temporal ordering.

### Rationale
- **Zero coordination**: SHAs are globally unique by Git's design
- **No counter to sync**: Eliminates distributed consistency problem
- **Simpler implementation**: No counter table, no rebuild logic
- **Temporal ordering preserved**: `timestamp` field already required (FR-001)
- **Human references**: Use summary text or short SHA ("decision on JWT signing" or "decisions:abc123")

### Format
```yaml
---
type: decision
spec: user-auth
timestamp: 2025-12-14T10:30:00Z  # Used for ordering
summary: Chose RS256 over HS256 for JWT signing
---
```

Memory ID: `decisions:<commit-sha>` (e.g., `decisions:abc123def`)

### Display Convention
When listing decisions, show chronological index for human readability:
```
Decisions for user-auth:
  1. [2025-12-10] Chose PostgreSQL for JSONB support (decisions:abc123)
  2. [2025-12-12] Selected RS256 for JWT signing (decisions:def456)
  3. [2025-12-14] Implemented rate limiting at API gateway (decisions:ghi789)
```

The index (1, 2, 3) is **display-only**, not stored. It's computed from timestamp ordering.

### Consequences
- No distributed synchronization issues
- No counter rebuild during reindex
- References use short SHA or summary text instead of "ADR-007"
- Gaps cannot occur (no sequence to have gaps in)
- Simpler index schema (no `adr_counter` table)

---

## ADR-013: cs-memory Supplements (Not Replaces) Prompt Capture

### Status
Accepted

### Context
The claude-spec plugin has two mechanisms for preserving session context:
1. **Prompt capture** (`/cs:log`): Raw logging of all user prompts to `.prompt-log.json`
2. **cs-memory**: Structured capture of decisions, learnings, blockers, review findings as Git notes

These serve different purposes and the question arose: should cs-memory replace prompt capture?

### Decision
**cs-memory supplements prompt capture but does not fully replace it.** The two systems coexist with different scopes:

| System | Purpose | When to Use |
|--------|---------|-------------|
| cs-memory | Structured knowledge artifacts | Default, always enabled |
| Prompt capture | Debug/troubleshooting, interaction pattern analysis | Optional, enable when needed |

### Rationale

**cs-memory captures signal:**
- Decisions with context, rationale, alternatives
- Learnings with insight and applicability
- Review findings with severity, remediation, resolution tracking
- Blockers with problem description and resolution
- Patterns identified across projects

**Prompt capture captures noise + signal:**
- Complete transcript (including false starts, corrections)
- Chronological session narrative
- Interaction patterns between user and Claude
- Useful for debugging hooks, validating behavior

**Key insight:** The valuable artifacts (decisions, learnings, review findings) are now captured structurally in cs-memory. Prompt capture's raw logs become useful primarily for debugging and retrospective analysis of interaction patterns, not knowledge retrieval.

### Implementation

```yaml
# Recommended configuration
cs-memory:
  auto_capture: true     # Always capture structured artifacts

prompt-capture:
  default: off           # Optional debug mode
  enable_for:
    - hook_debugging
    - behavior_validation
    - retrospective_analysis
```

### Consequences
- cs-memory becomes the primary knowledge retrieval system
- Prompt capture becomes an optional debug tool
- Reduced storage requirements (structured notes << raw transcripts)
- `/cs:log` remains available for troubleshooting
- Retrospective analysis in `/cs:c` shifts from mining raw prompts to querying structured memories

---

## ADR-014: Code Review Findings as Commit-Anchored Notes

### Status
Accepted

### Context
The existing `/cr` command produces CODE_REVIEW.md, REVIEW_SUMMARY.md, and REMEDIATION_TASKS.md artifacts. These are markdown files that exist independently of Git history. Questions arose about how to integrate code review with cs-memory.

### Decision
**Code review findings are captured as Git notes in the `cs/reviews` namespace**, attached to the commit being reviewed. This provides:
1. Semantic searchability via embeddings
2. Pattern detection across reviews
3. Resolution tracking (status: open → resolved)
4. Team-wide knowledge sharing via Git notes sync

### Format
```yaml
---
type: review_finding
spec: <active-spec-or-null>
severity: critical|high|medium|low
category: security|performance|architecture|quality|tests|documentation
file: <file-path>
line: <line-number>
summary: <one-line description>
timestamp: <iso-8601>
status: open|resolved
resolution: <null-or-resolution-text>
resolved_at: <null-or-iso-8601>
---
<full finding details with remediation guidance>
```

### Rationale
- **Commit anchoring**: Findings attach to the code state that caused them
- **Pattern detection**: Searching `cs/reviews` reveals recurring issues (e.g., "SQL injection found 5 times in past 3 months")
- **Resolution tracking**: Status updates preserve remediation history
- **Supplements artifacts**: CODE_REVIEW.md still generated for human consumption; notes provide machine-queryable index

### Consequences
- Each finding becomes a separate note (may produce many notes per review)
- Resolution requires updating existing notes (git notes append)
- Markdown artifacts remain as human-readable summaries
- Review patterns can inform proactive suggestions ("You've seen this before")

---

## ADR-015: History Rewriting and Note Orphaning

### Status
Accepted

### Context
Git notes attach to specific commit SHAs. When developers rewrite history (rebase, squash, amend), the original commits are replaced with new commits having different SHAs. Notes attached to the original commits become "orphaned"—they still exist in `refs/notes/cs/*` but reference commits that no longer exist in the active branch history.

This is a known Git behavior, not a cs-memory bug. The question is: how should cs-memory handle this scenario?

### Decision
**Document and warn, but do not automatically migrate notes.** The system will:

1. **Detect orphaned notes** during `cs:memory status` by checking if referenced commits exist
2. **Warn users** when orphaned notes are detected
3. **Preserve orphaned notes** (they may reference commits in other branches or reflog)
4. **Defer automatic migration** to a future phase unless user demand emerges

### Rationale
- **Complexity vs. Frequency**: History rewriting after attaching memories is an edge case. Most teams push commits before memories accumulate.
- **Git's Philosophy**: Notes are loosely coupled to commits by design. Orphaned notes are expected Git behavior.
- **Safety**: Automatic migration could incorrectly reassign notes if the user intended the history change.
- **Reflog Preservation**: "Orphaned" commits often exist in reflog for 90 days; notes may still be useful.

### Alternatives Considered

1. **Automatic migration via `git notes copy`**
   - Pros: Seamless user experience
   - Cons: Complex SHA mapping, may incorrectly reassign, silent data movement

2. **Block history rewriting when notes exist**
   - Pros: Prevents orphaning
   - Cons: Overly restrictive, breaks common workflows

3. **Manual `cs:memory migrate` command**
   - Pros: User-controlled, explicit
   - Cons: Extra maintenance burden for infrequent scenario

### Consequences
- Users must understand that rebase/squash may orphan notes
- `cs:memory status` will show orphaned note count
- Documentation will include guidance on when to avoid history rewriting
- Future phase may add `cs:memory migrate` if demand emerges

### Detection Logic
```python
def find_orphaned_notes(repo_path: str) -> list[str]:
    """Find notes referencing commits not in any branch."""
    all_note_refs = git_notes_list_all()  # All commits with notes
    reachable_commits = git_rev_list("--all")  # All commits in branches
    return [sha for sha in all_note_refs if sha not in reachable_commits]
```
