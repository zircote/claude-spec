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
           → Memory captured automatically

Session 5: *Claude starts suggesting MySQL*
           → cs-memory proactively surfaces: "Previously decided PostgreSQL for ACID"
           → Claude remembers and stays consistent
```

---

## Quick Start Tutorial

### Step 1: Verify Memory System is Active

```bash
/cs:memory status
```

**Expected output:**
```
Memory System Status
────────────────────
Total memories: 0
Index size: 24 KB
Last sync: never

Breakdown by namespace:
  (none yet)
```

### Step 2: Capture Your First Memory

Let's capture a decision about your project:

```bash
/cs:remember decision "Using TypeScript over JavaScript for type safety"
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

✓ Decision captured as decisions:abc123
```

### Step 3: Search Your Memories

```bash
/cs:recall "type safety"
```

**Output:**
```
Found 1 relevant memory:

[1] decisions:abc123 (0.89 relevance)
    "Using TypeScript over JavaScript for type safety"
    Tags: typescript, tooling, frontend
    Captured: 2 minutes ago
```

### Step 4: Load Full Context

```bash
/cs:recall --level full "type safety"
```

**Output:**
```
[1] decisions:abc123 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
/cs:recall --namespace decisions "authentication"

# Load all context for current spec
/cs:context

# If starting a new spec, memories are auto-recalled
/cs:p "Add OAuth2 login support"
# → Claude automatically searches for: "OAuth authentication login security"
# → Surfaces past decisions about auth, security, user management
```

**Why this helps**: Claude immediately knows about past authentication decisions without you having to re-explain them.

### Workflow 2: Hitting a Blocker

When you encounter an obstacle:

```bash
/cs:remember blocker "Rate limit on GitHub API causing CI failures"
```

Claude prompts:
```
What type of blocker is this?
> external_api

What's the current impact?
> CI pipeline fails on PRs with many commits

Any workarounds being considered?
> Caching API responses, reducing API calls per build

✓ Blocker captured as blockers:def456
```

Later, when facing similar issues:
```bash
/cs:recall "API rate limit"
# → Surfaces the blocker and any learnings from resolving it
```

### Workflow 3: Capturing a Learning

After solving a tricky problem:

```bash
/cs:remember learning "Connection pooling with PgBouncer reduces latency by 40%"
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

✓ Learning captured as learnings:ghi789
```

### Workflow 4: Code Review Integration

After a code review session:

```bash
/cs:review --recall
```

**Output:**
```
Past Review Patterns
────────────────────
Pattern: Missing error handling (appeared 5 times)
  Most recent: 3 days ago in auth-feature
  Suggestion: Add try/catch for async operations

Pattern: Inconsistent naming (appeared 3 times)
  Most recent: 1 week ago in api-refactor
  Suggestion: Follow camelCase for functions

Recent Review Findings
──────────────────────
[1] reviews:jkl012 - "Add input validation for user endpoints"
[2] reviews:mno345 - "Missing unit tests for error paths"
```

### Workflow 5: Project Close-out

When completing a project:

```bash
/cs:c my-feature
```

Claude automatically:
1. Recalls all memories for the spec
2. Extracts learnings and patterns
3. Captures retrospective notes
4. Archives memories with summaries

```
Project Close-out: my-feature
─────────────────────────────

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

✓ Retrospective captured as retrospective:pqr678
✓ Memories archived with summaries
```

---

## Quick Start

### Capturing Context

Use `/cs:remember` to capture memories:

```bash
# Capture a decision
/cs:remember decision "Chose PostgreSQL over MySQL for ACID compliance"

# Capture a learning
/cs:remember learning "Connection pooling reduces latency by 40%" --tags performance,database

# Capture a blocker
/cs:remember blocker "Rate limit on external API" --tags api,integration
```

### Recalling Context

Use `/cs:recall` to search memories:

```bash
# Semantic search
/cs:recall "database performance decisions"

# Filter by namespace
/cs:recall --namespace decisions "authentication"

# Filter by spec
/cs:recall --spec auth-feature "security choices"
```

### Loading Full Context

Use `/cs:context` to load all memories for a spec:

```bash
# Load context for current spec
/cs:context

# Load context for specific spec
/cs:context auth-feature
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

### During Planning (`/cs:p`)
- Project inception notes
- Requirements elicitation
- Research findings
- Architecture decisions

### During Implementation (`/cs:i`)
- Progress milestones
- Blockers encountered
- Learnings discovered
- Plan deviations

### During Close-out (`/cs:c`)
- Retrospective summary
- Extracted learnings
- Detected patterns

## Hydration Levels

Control how much detail is loaded:

| Level | Content | Use Case |
|-------|---------|----------|
| **SUMMARY** (1) | ID, summary, timestamp | Quick overview |
| **FULL** (2) | Complete note content | Detailed context |
| **FILES** (3) | Content + file snapshots | Full reconstruction |

```bash
# Quick summary view (default)
/cs:recall "authentication"

# Full content
/cs:recall --level full "authentication"

# With file context
/cs:recall --level files "authentication"
```

## Pattern Detection

The system automatically detects patterns:

- **Tag co-occurrence**: Frequently paired tags
- **Content patterns**: Recurring phrases
- **Blocker patterns**: Types of obstacles (API, Database, Auth)
- **Learning clusters**: Related insights

View patterns with:

```bash
/cs:review --recall
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
/cs:memory status
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
/cs:memory reindex --full

# Incremental sync
/cs:memory reindex
```

### Verification

```bash
/cs:memory verify
```

Checks index consistency against Git notes.

### Garbage Collection

```bash
/cs:memory gc
```

Removes:
- Orphaned embeddings
- Archived memories (optional)
- Stale cache entries

### Export

```bash
# Export all
/cs:memory export --output memories.json

# Export by spec
/cs:memory export --spec auth-feature
```

## Search Tips

### Query Expansion

Queries are automatically expanded with synonyms:
- "database" → db, postgres, sql, storage
- "decision" → chose, selected, opted
- "problem" → issue, bug, blocker

### Combining Filters

```bash
# Multiple filters
/cs:recall --namespace decisions --spec auth-feature --tags security "token storage"

# Time-based
/cs:recall --since 7d "recent changes"
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

**Symptoms**: `/cs:recall` returns empty results

**Diagnosis**:
```bash
# Check if any memories exist
/cs:memory status

# Verify index is synced with git notes
/cs:memory verify
```

**Common causes and fixes**:

| Cause | Fix |
|-------|-----|
| Namespace filter too strict | Use `--namespace all` or omit filter |
| Spec filter doesn't match | Check exact spec name: `/cs:s --list` |
| Index out of sync | Run `/cs:memory reindex` |
| Query too specific | Try broader terms (semantic search expands automatically) |

**Example fix**:
```bash
# Instead of this (too specific):
/cs:recall --namespace decisions --spec auth-v2 "JWT token expiration handling for refresh tokens"

# Try this (broader):
/cs:recall "JWT tokens"
```

### Slow searches

**Symptoms**: Searches take >1 second

**Diagnosis**:
```bash
/cs:memory status
# Look at: Index size, Cache stats
```

**Common causes and fixes**:

| Cause | Fix |
|-------|-----|
| Large index (>10k memories) | Run `/cs:memory gc` to clean old entries |
| Many orphaned embeddings | Run `/cs:memory reindex --full` |
| First search (cold cache) | Subsequent searches will be faster |
| Embedding model loading | First search loads model (~2s), then cached |

**Example fix**:
```bash
# Clean up and rebuild
/cs:memory gc
/cs:memory reindex --full
```

### Missing context after recall

**Symptoms**: Recall returns memory but content is truncated

**Diagnosis**:
```bash
# Check hydration level
/cs:recall --level full "your query"
```

**Hydration level guide**:
```bash
# Level 1 (SUMMARY) - Just metadata, fastest
/cs:recall "query"

# Level 2 (FULL) - Complete note content
/cs:recall --level full "query"

# Level 3 (FILES) - Content + file snapshots (slowest)
/cs:recall --level files "query"
```

### Memories not auto-captured during /cs:p or /cs:i

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
/cs:remember decision "Your decision summary" --spec your-spec
```

### Git notes not syncing

**Symptoms**: `/cs:memory verify` shows inconsistencies

**Diagnosis**:
```bash
/cs:memory verify

# Expected output for healthy state:
# ✓ Index consistent with git notes
# Total: 42 memories

# Problematic output:
# ✗ Index inconsistent
# Missing in index: 3
# Orphaned in index: 1
```

**Fix**:
```bash
# Full rebuild from git notes (source of truth)
/cs:memory reindex --full
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
/cs:c old-feature  # Close out completed projects

# 2. Run garbage collection
/cs:memory gc

# 3. Check index health
/cs:memory status
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

**Q: Can I share memories with my team?**
A: Yes! Git notes are distributed with `git push` / `git pull`. Team members get all memories. The system auto-configures push/fetch refspecs on first capture.

**Q: What happens during git rebase?**
A: Notes are automatically preserved during rebase. The system configures `notes.rewriteRef` on first use, which tells git to copy notes to the rebased commits. Run `/cs:memory verify` after rebase to confirm consistency.

**Q: Do I need to configure git manually?**
A: No! The memory system auto-configures git on first capture:
- Push/fetch refspecs for `refs/notes/cs/*`
- `notes.rewriteRef` for rebase support
- Merge strategy for conflict resolution

This is idempotent - safe to run multiple times without creating duplicates.

**Q: How do I backup my memories?**
A: Export to JSON: `/cs:memory export --output backup.json`

**Q: Can I edit a captured memory?**
A: Not directly. Capture a new memory with corrected information; old memories age out naturally.

**Q: How much disk space do memories use?**
A: ~1KB per memory in the index, plus ~100 bytes per note in git. 1000 memories ≈ 1MB total.
