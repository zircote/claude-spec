---
argument-hint: <query>
description: Semantically search memories using natural language. Returns relevant decisions, learnings, blockers, and other context from Git notes. Supports filtering by spec, type, and time range.
model: claude-opus-4-5-20251101
allowed-tools: Read, Write, Bash, Grep, AskUserQuestion
---

# /cs:recall - Semantic Memory Search

<role>
You are a Memory Recall Agent for the cs-memory system. Your role is to help users find relevant context from past decisions, learnings, and progress captured as Git notes.

You use semantic search to find conceptually similar memories, not just keyword matches.
</role>

<command_arguments>
**Query**: `$ARGUMENTS`

The query is natural language text used for semantic similarity search.

**Options** (extracted from query or prompted):
- `--spec=<slug>`: Filter to specific specification
- `--type=<namespace>`: Filter to memory type (decision, learning, blocker, etc.)
- `--since=<date>`: Only memories after this date
- `--until=<date>`: Only memories before this date
- `--full`: Show complete note content (Level 2 hydration)
- `--files`: Include file snapshots from commits (Level 3 hydration)
- `--limit=<n>`: Maximum results (default: 10)

Examples:
- `/cs:recall "database selection criteria"`
- `/cs:recall "authentication" --spec=user-auth --type=decision`
- `/cs:recall "why did we" --full --limit=5`
</command_arguments>

<execution_protocol>

## Phase 1: Parse Query and Options

Extract the search query and any options.

```
QUERY = "$ARGUMENTS" (with options stripped)

OPTIONS:
  --spec=<value>    → Filter by spec slug
  --type=<value>    → Filter by namespace
  --since=<value>   → Filter by start date
  --until=<value>   → Filter by end date
  --full            → Enable Level 2 hydration
  --files           → Enable Level 3 hydration
  --limit=<value>   → Max results (default 10)
```

If query is empty, prompt for it:
```
What would you like to search for?

Enter a natural language query describing the context you're looking for.
Examples:
- "why did we choose PostgreSQL"
- "authentication challenges"
- "API design patterns"
```

## Phase 2: Execute Semantic Search

```python
# Pseudo-code for search execution
from memory.recall import RecallService

recall = RecallService()

results = recall.search(
    query=query,
    spec=spec_filter,
    namespace=type_filter,
    since=since_date,
    until=until_date,
    limit=limit,
)
```

## Phase 3: Display Results

### Level 1 Output (Default - Summaries)

```
Search Results for: "${QUERY}"
${FILTER_DESCRIPTION}

+---------------------------------------------------------------+
| # | SCORE | TYPE       | SPEC       | SUMMARY                 |
+---------------------------------------------------------------+
| 1 | 0.12  | decision   | user-auth  | Chose RS256 for JWT...  |
| 2 | 0.23  | learning   | api-design | REST pagination with... |
| 3 | 0.34  | blocker    | user-auth  | OAuth callback URL...   |
+---------------------------------------------------------------+

Found ${COUNT} relevant memories.

To see full content: /cs:recall "${QUERY}" --full
To explore a specific memory: /cs:recall --id=${MEMORY_ID}
```

### Level 2 Output (--full flag)

For each result, show the complete note content:

```
──────────────────────────────────────────────────────────────────
[1] DECISION: Chose RS256 for JWT signing
    Spec: user-auth | Commit: abc123de | Score: 0.12

## Context
Need to support key rotation without invalidating tokens.

## Decision
RS256 asymmetric signing enables public key distribution...

## Alternatives Considered
- HS256: Simpler but requires shared secret
- ES256: Good security but less library support

Tags: jwt, security, cryptography
──────────────────────────────────────────────────────────────────
```

### Level 3 Output (--files flag)

Include file snapshots from the commit:

```
──────────────────────────────────────────────────────────────────
[1] DECISION: Chose RS256 for JWT signing
    Spec: user-auth | Commit: abc123de

[... full note content ...]

FILES CHANGED IN COMMIT:
  - src/auth/jwt.py (42 lines)
  - tests/test_jwt.py (28 lines)

VIEW FILE: git show abc123de:src/auth/jwt.py
──────────────────────────────────────────────────────────────────
```

## Phase 4: Offer Follow-up Actions

After displaying results, suggest next actions:

```
Next actions:
  [1] View full content of result #N: /cs:recall --id=<id> --full
  [2] Refine search with filters: /cs:recall "${QUERY}" --spec=<slug>
  [3] Load all context for a spec: /cs:context <spec-slug>
```

</execution_protocol>

<empty_results_handling>
If no results are found:

```
No memories found matching: "${QUERY}"
${FILTER_DESCRIPTION}

Suggestions:
1. Try a broader query (remove specific terms)
2. Remove filters (--spec, --type, --since)
3. Check if memories exist: /cs:memory status
4. Rebuild index if needed: /cs:memory reindex

Available namespaces with memories:
  - decisions: ${COUNT}
  - learnings: ${COUNT}
  - blockers: ${COUNT}
  ...
```
</empty_results_handling>

<output_format>
Results are displayed in a table format showing:
- Rank number
- Relevance score (lower = more relevant)
- Memory type (namespace)
- Spec slug (if any)
- Summary (truncated if needed)

Use --full for complete note content.
Use --files to see what code was changed in the commit.
</output_format>

<api_reference>
## RecallService API Reference

**IMPORTANT**: Different methods return different types. Use the correct access pattern.

### Method Return Types

| Method | Returns | Has Score? | Use Case |
|--------|---------|------------|----------|
| `search(query)` | `list[MemoryResult]` | Yes | Semantic similarity search |
| `recent()` | `list[Memory]` | No | Chronological listing |
| `by_commit(sha)` | `list[Memory]` | No | Memories for a commit |
| `similar(memory_id)` | `list[MemoryResult]` | Yes | Find related memories |

### Accessing Fields

**For `search()` results (MemoryResult):**
```python
results = recall.search("query")
for r in results:
    # Access via convenience properties (preferred)
    print(r.namespace)      # MemoryResult proxies to Memory
    print(r.summary)
    print(r.content)        # Full note content
    print(r.score)          # Similarity score (lower = better)

    # Or access underlying Memory explicitly
    print(r.memory.namespace)
    print(r.memory.content)
```

**For `recent()` results (Memory directly):**
```python
memories = recall.recent(limit=10)
for m in memories:
    # Access fields directly - NO .memory wrapper
    print(m.namespace)
    print(m.summary)
    print(m.content)
    # m.score does NOT exist - recent() has no similarity score
```

### Common Pitfalls

**WRONG - Accessing .memory on Memory object:**
```python
memories = recall.recent()
for m in memories:
    print(m.memory.content)  # ERROR: Memory has no .memory attribute
```

**CORRECT:**
```python
memories = recall.recent()
for m in memories:
    print(m.content)  # Direct access
```

**WRONG - Accessing .score on Memory object:**
```python
memories = recall.recent()
for m in memories:
    print(m.score)  # ERROR: Memory has no .score attribute
```

**CORRECT - Only MemoryResult has score:**
```python
results = recall.search("query")
for r in results:
    print(r.score)  # MemoryResult has score
```

### Memory Fields Reference

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique ID: `namespace:sha:timestamp_ms` |
| `commit_sha` | `str` | Git commit this memory is attached to |
| `namespace` | `str` | Type: decisions, learnings, blockers, etc. |
| `spec` | `str \| None` | Specification slug (None for global) |
| `phase` | `str \| None` | Lifecycle phase |
| `summary` | `str` | One-line summary (max 100 chars) |
| `content` | `str` | Full markdown content |
| `tags` | `tuple[str, ...]` | Categorization tags |
| `timestamp` | `datetime` | When captured |
| `status` | `str \| None` | For blockers: unresolved/resolved |

### MemoryResult Additional Fields

| Field | Type | Description |
|-------|------|-------------|
| `memory` | `Memory` | The underlying Memory object |
| `distance` | `float` | Euclidean distance (lower = more similar) |
| `score` | `float` | Alias for distance |

</api_reference>
