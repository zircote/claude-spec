---
project_id: SPEC-2025-12-19-001
project_name: "Remove Memory and Hook Components"
slug: remove-memory-hooks
status: complete
created: 2025-12-19T18:55:00Z
approved: 2025-12-19T19:00:00Z
started: 2025-12-19T19:05:00Z
completed: 2025-12-19T20:05:00Z
expires: 2026-03-19T18:55:00Z
superseded_by: null
tags: [cleanup, architecture, simplification]
stakeholders: []
worktree:
  branch: plan/remove-memory-hooks
  base_branch: main
  created_from_commit: 9de7f58
---

# Remove Memory and Hook Components

## Overview

This project removes the Memory System (Git-native persistent memory) and Hook System (lifecycle hooks) from the claude-spec plugin, simplifying the architecture.

## Status

**Current Phase**: Complete ✅

## Scope

### Components to Remove
- Memory module (`memory/`) - 17 files
- Hooks module (`hooks/`) - 10 files
- Memory commands (`/remember`, `/recall`, `/context`, `/memory`)
- Memory tests (`tests/memory/`) - 15 files
- Hook tests - 5 files
- Related documentation and spec projects

### Files Requiring Modification
- `plugin.json` - Remove memory command registrations
- `CLAUDE.md` - Remove memory/hook documentation
- `commands/*.md` - Remove memory capture integration
- Various documentation files

## Key Artifacts
- [REQUIREMENTS.md](./REQUIREMENTS.md) - Functional and non-functional requirements
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical design for removal
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Phased task breakdown

## Quick Stats
- Estimated files to remove: ~60+
- Estimated files to modify: ~13
- Test files affected: ~20

## Completed Tasks
- [x] Phase 1: Remove code directories (memory/, hooks/, memory commands)
- [x] Phase 2: Remove test files (memory tests, hook tests)
- [x] Phase 3: Update configuration and commands (plugin.json, CLAUDE.md, command files)
- [x] Phase 4: Remove documentation and spec projects
- [x] Final verification: 216 tests pass, no orphaned imports
