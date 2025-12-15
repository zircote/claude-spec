# cs-memory User Guide

A Git-native memory system for capturing and recalling project context across Claude sessions.

## Overview

The cs-memory system captures project context as Git notes, enabling:
- **Semantic search** across past decisions, learnings, and blockers
- **Progressive hydration** for token-efficient context loading
- **Pattern detection** to surface recurring themes
- **Memory lifecycle** to age and archive old context

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

1. Check namespace filter: `--namespace all`
2. Verify spec exists: `/cs:s --list`
3. Check index: `/cs:memory verify`

### Slow searches

1. Check cache: `/cs:memory status`
2. Run GC: `/cs:memory gc`
3. Consider archiving old specs

### Missing context

1. Verify hydration level: `--level full`
2. Check if memory was captured: `/cs:memory status`
3. Re-index: `/cs:memory reindex`
