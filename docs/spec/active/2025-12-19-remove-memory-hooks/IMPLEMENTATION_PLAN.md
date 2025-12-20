---
document_type: implementation_plan
project_id: SPEC-2025-12-19-001
version: 1.0.0
last_updated: 2025-12-19T19:00:00Z
status: approved
---

# Remove Memory and Hook Components - Implementation Plan

## Overview

Immediate removal of memory and hook components in 4 phases.

## Phase Summary

| Phase | Description | Files Affected |
|-------|-------------|----------------|
| 1 | Remove code directories | ~42 files |
| 2 | Remove test files | ~20 files |
| 3 | Update configuration and commands | ~15 files |
| 4 | Remove documentation and spec projects | ~10+ directories |

---

## Phase 1: Remove Code Directories

### Task 1.1: Remove memory/ directory
```bash
rm -rf plugins/cs/memory/
```
Files removed: 17

### Task 1.2: Remove hooks/ directory
```bash
rm -rf plugins/cs/hooks/
```
Files removed: 10

### Task 1.3: Remove memory command files
```bash
rm -f plugins/cs/commands/memory-remember.md
rm -f plugins/cs/commands/memory-recall.md
rm -f plugins/cs/commands/memory-context.md
rm -f plugins/cs/commands/memory.md
```
Files removed: 4

### Task 1.4: Remove artifact files
```bash
rm -f .prompt-log-enabled .cs-session-state.json .prompt-log.json
```

---

## Phase 2: Remove Test Files

### Task 2.1: Remove memory tests
```bash
rm -rf plugins/cs/tests/memory/
```
Files removed: 15

### Task 2.2: Remove hook tests
```bash
rm -f plugins/cs/tests/hooks/test_fallback.py
rm -f plugins/cs/tests/test_hook.py
rm -f plugins/cs/tests/test_command_detector.py
rm -f plugins/cs/tests/test_session_start.py
rm -f plugins/cs/tests/test_post_command.py
rm -f plugins/cs/tests/test_config_loader.py
```
Files removed: 6

### Task 2.3: Run remaining tests
```bash
cd plugins/cs && make test
```
Fix any import errors before proceeding.

---

## Phase 3: Update Configuration and Commands

### Task 3.1: Update plugin.json
- Remove memory command entries (memory-context, memory-recall, memory-remember, memory)
- Remove hooks registration if present

### Task 3.2: Update commands/plan.md
- Remove `<memory_integration>` section
- Remove memory capture instructions

### Task 3.3: Update commands/implement.md
- Remove memory capture sections

### Task 3.4: Update commands/complete.md
- Remove memory capture sections

### Task 3.5: Update commands/log.md
- Evaluate if still needed; remove if hook-dependent

### Task 3.6: Update commands/code-review.md
- Remove memory capture references

### Task 3.7: Update commands/code-fix.md
- Remove memory capture references

### Task 3.8: Update CLAUDE.md
- Remove "cs-memory Module" section
- Remove "Memory Commands" table
- Remove memory entries from completed specs list
- Remove hook architecture descriptions
- Remove auto-capture documentation

### Task 3.9: Update pyproject.toml
- Remove memory-related dependencies if any (sentence-transformers, sqlite-vec)

---

## Phase 4: Remove Documentation and Spec Projects

### Task 4.1: Remove memory spec projects
```bash
rm -rf docs/spec/completed/2025-12-15-memory-auto-capture/
rm -rf docs/spec/completed/2025-12-14-cs-memory/
```

### Task 4.2: Remove hook spec projects
```bash
rm -rf docs/spec/completed/2025-12-13-pre-post-steps-commands/
rm -rf docs/spec/completed/2025-12-12-prompt-capture-log/
```

### Task 4.3: Remove V1 docs
```bash
rm -rf docs/V1/
```

### Task 4.4: Update docs/ARCHITECTURE.md
- Remove memory system architecture sections
- Remove hook flow diagrams

### Task 4.5: Update docs/CONFIG_REFERENCE.md
- Remove memory command entries
- Remove hook configuration sections

### Task 4.6: Final verification
```bash
# Search for any remaining memory/hook references
grep -r "memory" plugins/cs/ --include="*.py" | grep -v ".pyc"
grep -r "hook" plugins/cs/ --include="*.py" | grep -v ".pyc"

# Run full test suite
cd plugins/cs && make ci
```

---

## Verification Checklist

- [x] All memory/ files removed
- [x] All hooks/ files removed
- [x] All memory command files removed
- [x] All memory tests removed
- [x] All hook tests removed
- [x] plugin.json updated
- [x] CLAUDE.md updated
- [x] All command files updated
- [x] Spec projects removed
- [x] Tests pass (216 passing)
- [x] No orphaned imports
- [x] Linting passes
