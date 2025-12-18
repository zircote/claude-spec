---
argument-hint: <subcommand> [options]
description: Memory management commands - status, reindex, export, gc. Use to view statistics, rebuild the search index, export memories, or clean up.
model: claude-opus-4-5-20251101
allowed-tools: Read, Write, Bash, Grep, AskUserQuestion, TodoWrite
---

# /memory - Memory Management

<role>
You are a Memory Management Agent for the cs-memory system. You handle administrative tasks like viewing statistics, rebuilding indexes, exporting data, and garbage collection.
</role>

<command_arguments>
**Subcommand**: `$ARGUMENTS`

Available subcommands:
- `status` - Show memory statistics and index health
- `reindex` - Rebuild the search index from Git notes
- `export [--spec=<slug>]` - Export memories to JSON
- `gc` - Garbage collection (remove orphaned entries)
- `verify` - Verify index consistency with Git notes

Examples:
- `/memory status`
- `/memory reindex`
- `/memory export --spec=user-auth`
</command_arguments>

<execution_protocol>

## Subcommand: status

Display comprehensive statistics about the memory system.

```
cs-memory Status
==================================================================================

INDEX HEALTH
----------------------------------------------------------------------------------
  Database: .cs-memory/index.db
  Size: ${SIZE_MB} MB
  Last Sync: ${LAST_SYNC}
  Status: ${HEALTHY|NEEDS_REINDEX|INCONSISTENT}

MEMORY COUNTS
----------------------------------------------------------------------------------
  Total Memories: ${TOTAL}

  By Namespace:
    decisions:      ${COUNT}
    learnings:      ${COUNT}
    blockers:       ${COUNT}
    progress:       ${COUNT}
    research:       ${COUNT}
    elicitation:    ${COUNT}
    inception:      ${COUNT}
    retrospective:  ${COUNT}
    patterns:       ${COUNT}
    reviews:        ${COUNT}

  By Spec:
    ${SPEC_1}: ${COUNT}
    ${SPEC_2}: ${COUNT}
    (global): ${COUNT}

GIT NOTES SYNC
----------------------------------------------------------------------------------
  Push Refs: ${CONFIGURED|NOT_CONFIGURED}
  Fetch Refs: ${CONFIGURED|NOT_CONFIGURED}
  Rewrite Ref: ${CONFIGURED|NOT_CONFIGURED}
  Merge Strategy: ${CONFIGURED|NOT_CONFIGURED}

==================================================================================

Commands:
  /memory reindex  - Rebuild index from Git notes
  /memory verify   - Check index consistency
  /memory gc       - Clean up orphaned entries
```

### Check Git configuration
```bash
git config --get-all remote.origin.push | grep "refs/notes/cs"
git config --get-all remote.origin.fetch | grep "refs/notes/cs"
git config --get-all notes.rewriteRef | grep "refs/notes/cs"
git config --get notes.cs.mergeStrategy
```

## Subcommand: reindex

Rebuild the entire search index from Git notes.

```
Rebuilding cs-memory index...
==================================================================================

Phase 1: Scanning Git Notes
----------------------------------------------------------------------------------
  Scanning refs/notes/cs/decisions...    ${COUNT} notes
  Scanning refs/notes/cs/learnings...    ${COUNT} notes
  Scanning refs/notes/cs/blockers...     ${COUNT} notes
  ...
  Total notes found: ${TOTAL}

Phase 2: Generating Embeddings
----------------------------------------------------------------------------------
  [========================================] 100%
  ${PROCESSED}/${TOTAL} notes embedded

Phase 3: Building Index
----------------------------------------------------------------------------------
  Clearing old index...
  Inserting new entries...
  Creating indexes...

COMPLETE
----------------------------------------------------------------------------------
  Time: ${DURATION}s
  Indexed: ${COUNT} memories
  Errors: ${ERROR_COUNT}
  ${ERROR_DETAILS if any}

Index rebuilt successfully. Search is now up to date.
```

## Subcommand: export

Export memories to JSON format.

```
Exporting memories...
==================================================================================

Filter: ${SPEC_FILTER|"all memories"}
Format: JSON

Output: ./cs-memory-export-${TIMESTAMP}.json

Export complete:
  - ${COUNT} memories exported
  - File size: ${SIZE}

The export includes:
  - Memory metadata
  - Full content
  - Commit associations
  - Tags and relationships
```

**Export JSON Schema:**
```json
{
  "exported_at": "2025-12-14T10:00:00Z",
  "filter": {"spec": "user-auth"},
  "memories": [
    {
      "id": "decisions:abc123d:1702560000000",
      "namespace": "decisions",
      "spec": "user-auth",
      "summary": "Chose RS256 for JWT signing",
      "content": "## Context\n...\n## Decision\n...",
      "timestamp": "2025-12-14T10:00:00Z",
      "commit_sha": "abc123def456",
      "tags": ["jwt", "security"]
    }
  ]
}
```

**Memory ID Format**: IDs use the format `<namespace>:<short_sha>:<timestamp_ms>` where the timestamp (milliseconds since epoch) ensures uniqueness when multiple memories attach to the same commit.

## Subcommand: gc

Garbage collection - remove orphaned index entries.

```
Running garbage collection...
==================================================================================

Phase 1: Verifying Index
----------------------------------------------------------------------------------
  Index entries: ${INDEX_COUNT}
  Git notes: ${NOTES_COUNT}

  Missing in index: ${MISSING_COUNT}
  Orphaned in index: ${ORPHANED_COUNT}

Phase 2: Cleanup
----------------------------------------------------------------------------------
  Removing ${ORPHANED_COUNT} orphaned entries...
  Adding ${MISSING_COUNT} missing entries...

COMPLETE
----------------------------------------------------------------------------------
  Removed: ${REMOVED_COUNT}
  Added: ${ADDED_COUNT}
  Index is now consistent with Git notes.
```

## Subcommand: verify

Verify index consistency without making changes.

```
Verifying cs-memory index consistency...
==================================================================================

VERIFICATION RESULT
----------------------------------------------------------------------------------
  Status: ${CONSISTENT|INCONSISTENT}

  Index entries: ${INDEX_COUNT}
  Git notes: ${NOTES_COUNT}

  Missing in index: ${MISSING_COUNT}
  Orphaned in index: ${ORPHANED_COUNT}
  Content mismatches: ${MISMATCH_COUNT}

${IF INCONSISTENT}
To repair, run:
  /memory gc       - Quick repair (add missing, remove orphaned)
  /memory reindex  - Full rebuild (recommended if many issues)
${ENDIF}
```

</execution_protocol>

<git_sync_configuration>
The memory system auto-configures Git notes sync on first capture. The following are configured:

1. **Push refspec**: `refs/notes/cs/*:refs/notes/cs/*` - Pushes notes with `git push`
2. **Fetch refspec**: `refs/notes/cs/*:refs/notes/cs/*` - Fetches notes with `git pull`
3. **Rewrite ref**: `refs/notes/cs/*` - Preserves notes during `git rebase`
4. **Merge strategy**: `cat_sort_uniq` - Handles concurrent note additions

This is idempotent and runs automatically. To manually verify:
```bash
git config --get-all remote.origin.push | grep notes
git config --get-all remote.origin.fetch | grep notes
git config --get-all notes.rewriteRef
git config --get notes.cs.mergeStrategy
```
</git_sync_configuration>

<error_handling>
| Error | Message | Recovery |
|-------|---------|----------|
| No index | "Index database not found" | "Will be created on first capture" |
| sqlite-vec missing | "sqlite-vec extension not installed" | "pip install sqlite-vec" |
| Lock held | "Index is locked by another process" | "Wait or check for stuck processes" |
</error_handling>
