# cs-memory User Guide

A Git-native memory system for capturing and recalling project context across Claude sessions.

## Overview

The cs-memory system captures project context as Git notes, enabling:
- **Semantic search** across past decisions, learnings, and blockers
- **Progressive hydration** for token-efficient context loading
- **Pattern detection** to surface recurring themes
- **Memory lifecycle** to age and archive old context

## The Problem This Solves

**Without cs-memory**: After 2-3 context compactions, Claude loses track of earlier decisions, repeats mistakes, and asks questions that were already answered.

**With cs-memory**: Decisions, learnings, and blockers persist across sessions and are automatically surfaced when relevant.

```
Session 1: "Let's use PostgreSQL for ACID compliance"
           -> Memory captured automatically

Session 5: *Claude starts suggesting MySQL*
           -> cs-memory proactively surfaces: "Previously decided PostgreSQL for ACID"
           -> Claude remembers and stays consistent
```

---

## Quick Start Tutorial

### Step 1: Verify Memory System is Active

```bash
/memory status
```

**Expected output:**
```
Memory System Status
--------------------
Total memories: 0
Index size: 24 KB
Last sync: never

Breakdown by namespace:
  (none yet)
```

### Step 2: Capture Your First Memory

Let's capture a decision about your project:

```bash
/remember decision "Using TypeScript over JavaScript for type safety"
```

Claude will prompt for additional context:
```
Capturing decision...

What alternatives were considered?
> JavaScript, Flow

What's the rationale for this choice?
> TypeScript catches bugs at compile time, better IDE support, team already familiar

Any relevant tags?
> typescript, tooling, frontend

Memory captured successfully:
+----------------------------------------------------------------+
| TYPE: decision                                                  |
| ID: decisions:abc123d:1702560000000                             |
| COMMIT: abc123de - "feat: add user authentication"              |
| SPEC: (global)                                                  |
+----------------------------------------------------------------+
| SUMMARY: Using TypeScript over JavaScript for type safety       |
+----------------------------------------------------------------+
```

**Note about Memory IDs**: The ID format is `<namespace>:<short_sha>:<timestamp_ms>`. The timestamp ensures uniqueness when multiple memories attach to the same commit.

### Step 3: Search Your Memories

```bash
/recall "type safety"
```

**Output:**
```
Found 1 relevant memory:

[1] decisions:abc123d:1702560000000 (0.89 relevance)
    "Using TypeScript over JavaScript for type safety"
    Tags: typescript, tooling, frontend
    Captured: 2 minutes ago
```

### Step 4: Load Full Context

```bash
/recall --level full "type safety"
```

**Output:**
```
[1] decisions:abc123d:1702560000000 ----------------------------------------

Using TypeScript over JavaScript for type safety

## Alternatives Considered
- JavaScript
- Flow

## Rationale
TypeScript catches bugs at compile time, better IDE support,
team already familiar

Tags: typescript, tooling, frontend
Captured: 2 minutes ago
```

---

## Real-World Workflows

### Workflow 1: Starting a New Feature

When beginning work on a new feature, recall relevant past decisions:

```bash
# Search for related decisions
/recall --namespace decisions "authentication"

# Load all context for current spec
/context

# If starting a new spec, memories are auto-recalled
/p "Add OAuth2 login support"
# -> Claude automatically searches for: "OAuth authentication login security"
# -> Surfaces past decisions about auth, security, user management
```

**Why this helps**: Claude immediately knows about past authentication decisions without you having to re-explain them.

### Workflow 2: Hitting a Blocker

When you encounter an obstacle:

```bash
/remember blocker "Rate limit on GitHub API causing CI failures"
```

Claude prompts:
```
What type of blocker is this?
> external_api

What's the current impact?
> CI pipeline fails on PRs with many commits

Any workarounds being considered?
> Caching API responses, reducing API calls per build

Memory captured:
ID: blockers:def456a:1702563600000
```

Later, when facing similar issues:
```bash
/recall "API rate limit"
# -> Surfaces the blocker and any learnings from resolving it
```

### Workflow 3: Capturing a Learning

After solving a tricky problem:

```bash
/remember learning "Connection pooling with PgBouncer reduces latency by 40%"
```

Claude prompts:
```
What was the context for this learning?
> Database connections were being exhausted under load

How was this discovered?
> Load testing revealed connection limit, PgBouncer solved it

Any code or config involved?
> Added pgbouncer.ini with pool_mode=transaction

Tags?
> database, performance, postgres

Memory captured:
ID: learnings:ghi789b:1702567200000
```

### Workflow 4: Code Review Integration

After a code review session:

```bash
/review --recall
```

**Output:**
```
Past Review Patterns
--------------------
Pattern: Missing error handling (appeared 5 times)
  Most recent: 3 days ago in auth-feature
  Suggestion: Add try/catch for async operations

Pattern: Inconsistent naming (appeared 3 times)
  Most recent: 1 week ago in api-refactor
  Suggestion: Follow camelCase for functions

Recent Review Findings
----------------------
[1] reviews:jkl012c:1702570800000 - "Add input validation for user endpoints"
[2] reviews:mno345d:1702574400000 - "Missing unit tests for error paths"
```

### Workflow 5: Project Close-out

When completing a project:

```bash
/c my-feature
```

Claude automatically:
1. Recalls all memories for the spec
2. Extracts learnings and patterns
3. Captures retrospective notes
4. Archives memories with summaries

```
Project Close-out: my-feature
-----------------------------

Memories captured: 23
  - decisions: 8
  - learnings: 7
  - progress: 5
  - blockers: 3

Key Learnings Extracted:
1. "Connection pooling critical for >100 concurrent users"
2. "GitHub API requires exponential backoff for rate limits"
3. "TypeScript strict mode catches 30% more bugs"

Patterns Detected:
- SUCCESS: "Early performance testing" (3 occurrences)
- ANTI_PATTERN: "Skipping input validation" (2 occurrences)

Retrospective captured as retrospective:pqr678e:1702578000000
Memories archived with summaries
```

---

## Quick Start

### Capturing Context

Use `/remember` to capture memories:

```bash
# Capture a decision
/remember decision "Chose PostgreSQL over MySQL for ACID compliance"

# Capture a learning
/remember learning "Connection pooling reduces latency by 40%" --tags performance,database

# Capture a blocker
/remember blocker "Rate limit on external API" --tags api,integration
```

### Recalling Context

Use `/recall` to search memories:

```bash
# Semantic search
/recall "database performance decisions"

# Filter by namespace
/recall --namespace decisions "authentication"

# Filter by spec
/recall --spec auth-feature "security choices"
```

### Loading Full Context

Use `/context` to load all memories for a spec:

```bash
# Load context for current spec
/context

# Load context for specific spec
/context auth-feature
```

## Memory Types (Namespaces)

| Namespace | Purpose | When to Capture |
|-----------|---------|-----------------|
| `inception` | Initial project ideas | Start of planning |
| `elicitation` | Clarified requirements | After Q&A sessions |
| `research` | Technical research findings | During investigation |
| `decisions` | Key choices with rationale | When making trade-offs |
| `progress` | Implementation milestones | Task completion |
| `blockers` | Obstacles encountered | When blocked |
| `learnings` | Insights discovered | After solving problems |
| `reviews` | Code review findings | After review cycles |
| `retrospective` | Project retrospective | End of project |
| `patterns` | Recurring patterns | When patterns emerge |

## Auto-Capture Integration

Memories are automatically captured during spec workflows:

### During Planning (`/p`)
- Project inception notes
- Requirements elicitation
- Research findings
- Architecture decisions (via `capture_decision()`)

### During Implementation (`/i`)
- Progress milestones (via `capture_progress()`)
- Blockers encountered (via `capture_blocker()`)
- Learnings discovered (via `capture_learning()`)
- Plan deviations (via `capture_pattern()`)

### During Close-out (`/c`)
- Retrospective summary (via `capture_retrospective()`)
- Extracted learnings (via `capture_learning()`)
- Success patterns (via `capture_pattern()`)
- Anti-patterns (via `capture_pattern()`)

### During Code Review (`/review`)
- Review findings (via `capture_review()`)
- Recurring issue patterns (via `capture_pattern()`)

### Capture Summary Display

At the end of each command, a capture summary is displayed:
```
────────────────────────────────────────────────────────────────
Memory Capture Summary
────────────────────────────────────────────────────────────────
Captured: 3 memories
  ✓ decisions:abc123d:1702560000000 - Chose PostgreSQL for ACID
  ✓ learnings:def456a:1702563600000 - Connection pooling critical
  ✓ patterns:ghi789b:1702567200000 - Success: Early testing
────────────────────────────────────────────────────────────────
```

### Disabling Auto-Capture

To disable auto-capture, set the environment variable:
```bash
export CS_AUTO_CAPTURE_ENABLED=false
```

When disabled, commands display:
```
Memory auto-capture disabled (CS_AUTO_CAPTURE_ENABLED=false)
```

This is useful for:
- Debugging command behavior without memory side effects
- Running in environments where git notes aren't desired
- Testing without accumulating test memories

## Hydration Levels

Control how much detail is loaded:

| Level | Content | Use Case |
|-------|---------|----------|
| **SUMMARY** (1) | ID, summary, timestamp | Quick overview |
| **FULL** (2) | Complete note content | Detailed context |
| **FILES** (3) | Content + file snapshots | Full reconstruction |

```bash
# Quick summary view (default)
/recall "authentication"

# Full content
/recall --level full "authentication"

# With file context
/recall --level files "authentication"
```

## Pattern Detection

The system automatically detects patterns:

- **Tag co-occurrence**: Frequently paired tags
- **Content patterns**: Recurring phrases
- **Blocker patterns**: Types of obstacles (API, Database, Auth)
- **Learning clusters**: Related insights

View patterns with:

```bash
/review --recall
```

## Memory Lifecycle

Memories age over time:

| State | Age | Behavior |
|-------|-----|----------|
| **ACTIVE** | 0-7 days | Full relevance |
| **AGING** | 7-30 days | Decayed relevance |
| **STALE** | 30-90 days | Low relevance |
| **ARCHIVED** | 90+ days | Summarized |

### Decay Scoring

Recent memories rank higher in search results. The decay formula:
```
decay_score = 2^(-age_days / half_life)
```

Where `half_life = 30 days` by default.

## Administration

### Index Status

```bash
/memory status
```

Shows:
- Total memory count
- Breakdown by namespace
- Breakdown by spec
- Last sync timestamp
- Index size

### Re-indexing

```bash
# Full rebuild
/memory reindex --full

# Incremental sync
/memory reindex
```

### Verification

```bash
/memory verify
```

Checks index consistency against Git notes.

### Garbage Collection

```bash
/memory gc
```

Removes:
- Orphaned embeddings
- Archived memories (optional)
- Stale cache entries

### Export

```bash
# Export all
/memory export --output memories.json

# Export by spec
/memory export --spec auth-feature
```

## Search Tips

### Query Expansion

Queries are automatically expanded with synonyms:
- "database" -> db, postgres, sql, storage
- "decision" -> chose, selected, opted
- "problem" -> issue, bug, blocker

### Combining Filters

```bash
# Multiple filters
/recall --namespace decisions --spec auth-feature --tags security "token storage"

# Time-based
/recall --since 7d "recent changes"
```

### Re-ranking Signals

Results are re-ranked using:
1. **Recency** - Recent memories score higher
2. **Namespace priority** - Decisions > Learnings > Blockers
3. **Tag match** - Matching tags boost score
4. **Spec match** - Current spec context boost

## Best Practices

1. **Capture decisions immediately** - Don't wait, context fades
2. **Include rationale** - "Why" matters more than "what"
3. **Use consistent tags** - Enables pattern detection
4. **Review patterns** - Surface recurring themes weekly
5. **Archive completed specs** - Keep index performant

## Troubleshooting

### "No memories found"

**Symptoms**: `/recall` returns empty results

**Diagnosis**:
```bash
# Check if any memories exist
/memory status

# Verify index is synced with git notes
/memory verify
```

**Common causes and fixes**:

| Cause | Fix |
|-------|-----|
| Namespace filter too strict | Use `--namespace all` or omit filter |
| Spec filter doesn't match | Check exact spec name: `/s --list` |
| Index out of sync | Run `/memory reindex` |
| Query too specific | Try broader terms (semantic search expands automatically) |

**Example fix**:
```bash
# Instead of this (too specific):
/recall --namespace decisions --spec auth-v2 "JWT token expiration handling for refresh tokens"

# Try this (broader):
/recall "JWT tokens"
```

### Slow searches

**Symptoms**: Searches take >1 second

**Diagnosis**:
```bash
/memory status
# Look at: Index size, Cache stats
```

**Common causes and fixes**:

| Cause | Fix |
|-------|-----|
| Large index (>10k memories) | Run `/memory gc` to clean old entries |
| Many orphaned embeddings | Run `/memory reindex --full` |
| First search (cold cache) | Subsequent searches will be faster |
| Embedding model loading | First search loads model (~2s), then cached |

**Example fix**:
```bash
# Clean up and rebuild
/memory gc
/memory reindex --full
```

### Missing context after recall

**Symptoms**: Recall returns memory but content is truncated

**Diagnosis**:
```bash
# Check hydration level
/recall --level full "your query"
```

**Hydration level guide**:
```bash
# Level 1 (SUMMARY) - Just metadata, fastest
/recall "query"

# Level 2 (FULL) - Complete note content
/recall --level full "query"

# Level 3 (FILES) - Content + file snapshots (slowest)
/recall --level files "query"
```

### Memories not auto-captured during /p or /i

**Symptoms**: Decisions made during planning don't appear in memory

**Diagnosis**:
```bash
# Check if auto-capture is enabled in command
# Look for <memory_integration> section in command output
```

**Common causes**:
- Spec not initialized (no PROGRESS.md yet)
- Claude didn't recognize the decision format
- Memory capture failed silently (check `--verbose`)

**Fix**: Manually capture important decisions:
```bash
/remember decision "Your decision summary" --spec your-spec
```

### Git notes not syncing

**Symptoms**: `/memory verify` shows inconsistencies

**Diagnosis**:
```bash
/memory verify

# Expected output for healthy state:
# Index consistent with git notes
# Total: 42 memories

# Problematic output:
# Index inconsistent
# Missing in index: 3
# Orphaned in index: 1
```

**Fix**:
```bash
# Full rebuild from git notes (source of truth)
/memory reindex --full
```

### "Model not found" or embedding errors

**Symptoms**: Capture or recall fails with embedding error

**Diagnosis**:
```bash
# Check if model can be loaded
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

**Common causes and fixes**:

| Cause | Fix |
|-------|-----|
| Model not downloaded | First run auto-downloads; ensure internet access |
| Disk space full | Free up space; model needs ~100MB |
| PyTorch not installed | Run `uv sync` to install dependencies |

### Performance tuning

**For repositories with many memories (500+)**:

```bash
# 1. Archive completed specs (reduces active index size)
/c old-feature  # Close out completed projects

# 2. Run garbage collection
/memory gc

# 3. Check index health
/memory status
# Ideal: <500 active memories, >80% cache hit rate
```

**For faster searches**:
- Use specific namespaces: `--namespace decisions` is faster than searching all
- Use spec filters: `--spec auth-feature` narrows search scope
- Recent queries are cached (5 minute TTL)

---

## Frequently Asked Questions

**Q: Where are memories stored?**
A: In Git notes attached to commits. Run `git notes --ref=refs/notes/cs/decisions list` to see raw notes.

**Q: What is the memory ID format?**
A: Memory IDs use the format `<namespace>:<short_sha>:<timestamp_ms>`. For example: `decisions:abc123d:1702560000000`. The timestamp component (milliseconds since epoch) ensures uniqueness when multiple memories attach to the same commit.

**Q: Can I share memories with my team?**
A: Yes! Git notes are distributed with `git push` / `git pull`. Team members get all memories. The system auto-configures push/fetch refspecs on first capture.

**Q: What happens during git rebase?**
A: Notes are automatically preserved during rebase. The system configures `notes.rewriteRef` on first use, which tells git to copy notes to the rebased commits. Run `/memory verify` after rebase to confirm consistency.

**Q: Do I need to configure git manually?**
A: No! The memory system auto-configures git on first capture:
- Push refspec: `refs/notes/cs/*:refs/notes/cs/*`
- Fetch refspec: `refs/notes/cs/*:refs/notes/cs/*`
- `notes.rewriteRef` for rebase support: `refs/notes/cs/*`
- Merge strategy: `cat_sort_uniq` for conflict resolution

This is idempotent - safe to run multiple times without creating duplicates. You can verify configuration with:
```bash
git config --get-all remote.origin.push | grep notes
git config --get-all remote.origin.fetch | grep notes
git config --get-all notes.rewriteRef
```

**Q: How do I backup my memories?**
A: Export to JSON: `/memory export --output backup.json`

**Q: Can I edit a captured memory?**
A: Not directly. Capture a new memory with corrected information; old memories age out naturally.

**Q: How much disk space do memories use?**
A: ~1KB per memory in the index, plus ~100 bytes per note in git. 1000 memories is approximately 1MB total.

**Q: Why does my memory ID have a timestamp?**
A: The timestamp ensures uniqueness when multiple memories are captured on the same commit. This commonly happens during batch operations like capturing multiple ADRs from a planning session. Without timestamps, IDs would collide.
