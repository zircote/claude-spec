---
document_type: implementation_plan
project_id: SPEC-2025-12-25-001
version: 1.0.0
last_updated: 2025-12-25T17:00:00Z
status: draft
estimated_effort: 4-6 hours
---

# Add /approve Command - Implementation Plan

## Overview

This plan implements the approval gate feature in 5 phases:
1. **Foundation** - Create /approve command
2. **/plan Extensions** - Add workflow flexibility flags
3. **/implement Gate** - Add approval status warning
4. **Prevention Hook** - Block implementation without spec
5. **Documentation** - Update CLAUDE.md and testing

## Phase Summary

| Phase | Name | Key Deliverables |
|-------|------|------------------|
| 1 | Foundation | /approve command, plugin registration |
| 2 | /plan Extensions | --no-worktree, --no-branch, --inline flags, never_implement section |
| 3 | /implement Gate | Approval status check and warning |
| 4 | Prevention Hook | PreToolUse hook for enforcement |
| 5 | Documentation | CLAUDE.md updates, /status updates, testing |

---

## Phase 1: Foundation

**Goal**: Create the core /approve command

### Task 1.1: Create /approve Command File

- **Description**: Create `commands/approve.md` with full command implementation
- **File**: `commands/approve.md`
- **Acceptance Criteria**:
  - [ ] Frontmatter with argument-hint, description, model, allowed-tools
  - [ ] Help check section with man page format
  - [ ] Project location logic (same as /implement)
  - [ ] Document completeness validation
  - [ ] Plan summary display
  - [ ] AskUserQuestion for approval decision (Approve/Request Changes/Reject)
  - [ ] Approval flow: update README.md frontmatter
  - [ ] Rejection flow: move to docs/spec/rejected/
  - [ ] Git user extraction for approver identity

### Task 1.2: Register Command in plugin.json

- **Description**: Add /approve to commands array in plugin manifest
- **File**: `.claude-plugin/plugin.json`
- **Acceptance Criteria**:
  - [ ] `"./commands/approve.md"` added to commands array
  - [ ] Alphabetical ordering maintained

### Task 1.3: Create rejected/ Directory Support

- **Description**: Ensure rejection flow creates and uses rejected/ directory
- **File**: Part of `commands/approve.md`
- **Acceptance Criteria**:
  - [ ] Creates `docs/spec/rejected/` if not exists
  - [ ] Moves rejected spec to rejected/ preserving structure
  - [ ] Updates README.md with rejection metadata

---

## Phase 2: /plan Extensions

**Goal**: Add workflow flexibility flags and implementation prevention

### Task 2.1: Add Flag Parsing to /plan

- **Description**: Parse --no-worktree, --no-branch, --inline flags
- **File**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Flag parsing logic in Step 0 or before branch check
  - [ ] `--no-worktree` sets NO_WORKTREE=true
  - [ ] `--no-branch` sets NO_BRANCH=true
  - [ ] `--inline` sets both flags
  - [ ] Remaining arguments passed as project seed
  - [ ] Help text updated with new flags

### Task 2.2: Modify Branch Decision Gate

- **Description**: Honor flags in worktree/branch creation decision
- **File**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Skip worktree creation if NO_WORKTREE=true
  - [ ] Skip branch creation if NO_BRANCH=true
  - [ ] Existing behavior preserved when flags not set
  - [ ] Clear messaging when skipping due to flags

### Task 2.3: Add Never Implement Section

- **Description**: Add explicit prohibition against implementing during /plan
- **File**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] `<never_implement>` section with strong warnings
  - [ ] Clear list of prohibited actions
  - [ ] Clear list of allowed outputs (documents only)
  - [ ] Reference to /approve workflow

### Task 2.4: Update Plan Help Text

- **Description**: Update help_check section with new flags
- **File**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] OPTIONS section includes --no-worktree, --no-branch, --inline
  - [ ] SYNOPSIS shows optional flags
  - [ ] EXAMPLES include flag usage

---

## Phase 3: /implement Gate

**Goal**: Add approval status warning to /implement

### Task 3.1: Add Approval Status Check

- **Description**: Check spec status after project detection
- **File**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Status extracted from README.md frontmatter
  - [ ] Check runs after project location, before implementation

### Task 3.2: Display Status Warning

- **Description**: Show warning for draft/in-review specs
- **File**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Warning shown for status: draft
  - [ ] Warning shown for status: in-review
  - [ ] No warning for status: approved
  - [ ] Warning recommends running /approve
  - [ ] Workflow proceeds after warning (not blocking)

---

## Phase 4: Prevention Hook

**Goal**: Block implementation without approved spec

### Task 4.1: Create Hook Script

- **Description**: Create shell script for hook enforcement
- **File**: `hooks/check-approved-spec.sh`
- **Acceptance Criteria**:
  - [ ] Script checks for approved specs in docs/spec/active/
  - [ ] Returns exit code 0 if approved spec exists
  - [ ] Returns exit code 1 if no approved spec
  - [ ] Script is executable (chmod +x)

### Task 4.2: Configure Hook

- **Description**: Add PreToolUse hook configuration
- **File**: `.claude/hooks.json` or hookify integration
- **Acceptance Criteria**:
  - [ ] Hook triggers on Write and Edit tools
  - [ ] Hook matches implementation file patterns (not docs/, tests/, .*)
  - [ ] Hook blocks with clear message on failure
  - [ ] Message references /plan and /approve commands

### Task 4.3: Create hooks/ Directory

- **Description**: Ensure hooks directory exists in plugin
- **File**: Directory creation
- **Acceptance Criteria**:
  - [ ] `hooks/` directory exists at plugin root
  - [ ] Contains check-approved-spec.sh

---

## Phase 5: Documentation & Polish

**Goal**: Update documentation and complete testing

### Task 5.1: Update CLAUDE.md

- **Description**: Add workflow documentation and guidance
- **File**: `CLAUDE.md`
- **Acceptance Criteria**:
  - [ ] Workflow diagram showing /plan → /approve → /implement
  - [ ] /approve command documented in command table
  - [ ] /plan flags documented
  - [ ] Prevention mechanism mentioned

### Task 5.2: Update /status Command

- **Description**: Show approval state in project status
- **File**: `commands/status.md`
- **Acceptance Criteria**:
  - [ ] Approval date shown in project details
  - [ ] Approved by shown in project details
  - [ ] Status differentiation (draft vs approved)

### Task 5.3: Update plugin.json Description

- **Description**: Add approval workflow to plugin description/keywords
- **File**: `.claude-plugin/plugin.json`
- **Acceptance Criteria**:
  - [ ] "approval" or "governance" in keywords
  - [ ] Description mentions approval workflow if space permits

### Task 5.4: Manual Testing

- **Description**: End-to-end workflow testing
- **Acceptance Criteria**:
  - [ ] /plan --inline creates spec without worktree/branch
  - [ ] /approve with approval updates frontmatter correctly
  - [ ] /approve with rejection moves to rejected/
  - [ ] /implement warns on unapproved spec
  - [ ] Hook blocks Write/Edit without approved spec (if enabled)
  - [ ] Full workflow: /plan → /approve → /implement → /complete

### Task 5.5: Update Spec CHANGELOG

- **Description**: Document completion in this spec's CHANGELOG
- **File**: `docs/spec/active/2025-12-25-approve-command/CHANGELOG.md`
- **Acceptance Criteria**:
  - [ ] Implementation completion entry
  - [ ] Summary of delivered features

---

## Dependency Graph

```
Phase 1 (Foundation):
  Task 1.1 ──────┬──────▶ Task 1.2
                 │
                 └──────▶ Task 1.3 ─────────────────────────────────┐
                                                                    │
Phase 2 (/plan):                                                    │
  Task 2.1 ──────┬──────▶ Task 2.2                                  │
                 │                                                  │
                 └──────▶ Task 2.3                                  │
                 │                                                  │
                 └──────▶ Task 2.4                                  │
                                                                    │
Phase 3 (/implement):                                               │
  Task 3.1 ────────────▶ Task 3.2                                   │
                                                                    │
Phase 4 (Hook):                                                     │
  Task 4.3 ──────┬──────▶ Task 4.1 ──────▶ Task 4.2                 │
                 │                                                  │
                 ▼                                                  │
Phase 5 (Docs):  ◀──────────────────────────────────────────────────┘
  Task 5.1, 5.2, 5.3 can run in parallel
  Task 5.4 (testing) depends on all above
  Task 5.5 is final
```

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| Hook too restrictive | Test hook with various file patterns | 4 |
| Breaking /plan workflow | Test all flag combinations | 2 |
| Git user not configured | Add fallback in approval capture | 1 |

## Testing Checklist

- [ ] /approve command loads without errors
- [ ] /approve locates spec by slug and project-id
- [ ] /approve validates document completeness
- [ ] /approve displays plan summary
- [ ] /approve updates frontmatter on approval
- [ ] /approve moves to rejected/ on rejection
- [ ] /plan --no-worktree skips worktree
- [ ] /plan --no-branch skips branch
- [ ] /plan --inline skips both
- [ ] /plan never_implement section present
- [ ] /implement warns on draft status
- [ ] /implement warns on in-review status
- [ ] /implement no warning on approved status
- [ ] Hook script exits 0 with approved spec
- [ ] Hook script exits 1 without approved spec
- [ ] Hook blocks Write/Edit to src/ without spec
- [ ] Hook allows Write/Edit to docs/
- [ ] Full workflow passes end-to-end

## Launch Checklist

- [ ] All tasks completed
- [ ] Manual testing passed
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] No regressions in existing commands
