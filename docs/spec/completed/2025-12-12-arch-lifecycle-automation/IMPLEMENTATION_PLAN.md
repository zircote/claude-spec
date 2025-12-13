---
document_type: implementation_plan
project_id: ARCH-2025-12-12-001
version: 1.0.0
last_updated: 2025-12-12T20:10:00Z
status: in-review
estimated_effort: 8-12 hours
---

# Architecture Lifecycle Automation - Implementation Plan

## Overview

This plan implements the `/arch:i` command and supporting infrastructure in 4 phases: Foundation (command skeleton + PROGRESS.md), Core Logic (state management + sync), Integration (cross-document updates), and Polish (edge cases + documentation).

## Phase Summary

| Phase | Focus | Key Deliverables |
|-------|-------|------------------|
| Phase 1 | Foundation | `/arch:i` command file, PROGRESS.md template, project detection |
| Phase 2 | Core Logic | Task tracking, status transitions, hierarchical rollup |
| Phase 3 | Integration | Document sync engine, CHANGELOG automation |
| Phase 4 | Polish | Edge case handling, error recovery, documentation |

---

## Phase 1: Foundation

**Goal**: Create the basic `/arch:i` command structure and PROGRESS.md checkpoint system
**Prerequisites**: Understanding of existing `/arch` command patterns

### Tasks

#### Task 1.1: Create `/arch:i` command skeleton

- **Description**: Create `commands/arch/i.md` with YAML frontmatter, role definition, and basic structure following existing `/arch` command patterns
- **Acceptance Criteria**:
  - [x] File created at `commands/arch/i.md`
  - [x] YAML frontmatter includes: argument-hint, description, model (opus), allowed-tools
  - [x] Role section defines Implementation Manager persona
  - [x] Basic execution protocol structure in place

#### Task 1.2: Implement project detection logic

- **Description**: Add logic to detect the target architecture project from the current git branch name
- **Acceptance Criteria**:
  - [x] Parse current branch name via `git branch --show-current`
  - [x] Search `docs/architecture/active/*/README.md` for matching slug
  - [x] Handle no-match case with helpful error message
  - [x] Handle multiple-match case with interactive selection prompt
  - [x] Support explicit project ID/slug argument override

#### Task 1.3: Define PROGRESS.md template structure

- **Description**: Design and document the PROGRESS.md checkpoint file format
- **Acceptance Criteria**:
  - [x] YAML frontmatter schema defined (project_id, format_version, timestamps, current_phase, status)
  - [x] Task Status table format defined (ID, Description, Status, Started, Completed, Notes)
  - [x] Phase Status table format defined
  - [x] Divergence Log table format defined
  - [x] Session Notes section defined

#### Task 1.4: Implement PROGRESS.md initialization

- **Description**: Add logic to create PROGRESS.md on first `/arch:i` run for a project
- **Acceptance Criteria**:
  - [x] Check if PROGRESS.md exists in project directory
  - [x] If missing, create from template with tasks populated from IMPLEMENTATION_PLAN.md
  - [x] Parse IMPLEMENTATION_PLAN.md to extract task IDs and descriptions
  - [x] Initialize all tasks as `pending`
  - [x] Set `implementation_started` timestamp

### Phase 1 Deliverables

- [x] `commands/arch/i.md` file with basic structure
- [x] Project detection working
- [x] PROGRESS.md template defined
- [x] PROGRESS.md auto-creation from IMPLEMENTATION_PLAN.md

### Phase 1 Exit Criteria

- [x] Running `/arch:i` in a project worktree creates PROGRESS.md
- [x] PROGRESS.md contains all tasks from IMPLEMENTATION_PLAN.md in pending state

---

## Phase 2: Core Logic

**Goal**: Implement task status management, hierarchical rollup, and session persistence
**Prerequisites**: Phase 1 complete

### Tasks

#### Task 2.1: Implement task status update logic

- **Description**: Add capability to mark tasks as in-progress, done, or skipped
- **Acceptance Criteria**:
  - [x] When Claude completes work matching a task, update PROGRESS.md
  - [x] Set `Started` timestamp when task moves from pending → in-progress
  - [x] Set `Completed` timestamp when task moves to done
  - [x] Support explicit "skip task X" instruction with reason
  - [x] Update task status in PROGRESS.md Task Status table

#### Task 2.2: Implement phase status calculation

- **Description**: Calculate phase completion percentage and status from task states
- **Acceptance Criteria**:
  - [x] Phase progress = (done + skipped) / total tasks in phase
  - [x] Phase status transitions: pending → in-progress → done
  - [x] Phase transitions to in-progress when first task starts
  - [x] Phase transitions to done when all tasks done/skipped
  - [x] Update Phase Status table in PROGRESS.md

#### Task 2.3: Implement project status derivation

- **Description**: Derive overall project status from phase states
- **Acceptance Criteria**:
  - [x] Project status = derived from phase states
  - [x] draft → in-progress when any task starts
  - [x] in-progress → completed when all phases done
  - [x] Update `project_status` in PROGRESS.md frontmatter
  - [x] Update `current_phase` to reflect active phase

#### Task 2.4: Implement divergence tracking

- **Description**: Track and log deviations from the original plan
- **Acceptance Criteria**:
  - [x] Log when task is skipped (type: skipped)
  - [x] Log when task is added dynamically (type: added)
  - [x] Log when task scope changes (type: modified)
  - [x] Each entry includes: date, type, task ID, description, resolution
  - [x] Notify user of divergence with option to approve/flag

#### Task 2.5: Implement session persistence

- **Description**: Ensure state persists across Claude sessions
- **Acceptance Criteria**:
  - [x] On `/arch:i` startup, read existing PROGRESS.md
  - [x] Display current state summary (phase, completed tasks, pending tasks)
  - [x] Update `last_session` timestamp on each session start
  - [x] Support resume workflow (no re-initialization needed)

### Phase 2 Deliverables

- [x] Task status management working
- [x] Phase rollup calculation working
- [x] Project status derivation working
- [x] Divergence logging working
- [x] Multi-session resume working

### Phase 2 Exit Criteria

- [x] Can mark tasks complete and see PROGRESS.md update
- [x] Phase status auto-updates based on task completion
- [x] Can close and reopen Claude session with state preserved

---

## Phase 3: Integration

**Goal**: Synchronize PROGRESS.md state to all state-bearing documents
**Prerequisites**: Phase 2 complete

### Tasks

#### Task 3.1: Implement IMPLEMENTATION_PLAN.md checkbox sync

- **Description**: When task marked done in PROGRESS.md, update checkbox in IMPLEMENTATION_PLAN.md
- **Acceptance Criteria**:
  - [x] Find task in IMPLEMENTATION_PLAN.md by task ID pattern (e.g., "Task 1.1")
  - [x] Change `- [x]` to `- [x]` for completed tasks
  - [x] Add timestamp comment after checkbox (optional)
  - [x] Handle tasks that don't have checkboxes gracefully

#### Task 3.2: Implement README.md frontmatter sync

- **Description**: Keep README.md metadata synchronized with project state
- **Acceptance Criteria**:
  - [x] Update `status` field when project status changes
  - [x] Update `started` field when implementation begins
  - [x] Update `completed` field when project completes
  - [x] Update `last_updated` on every significant change

#### Task 3.3: Implement CHANGELOG.md auto-entries

- **Description**: Automatically append entries for significant transitions
- **Acceptance Criteria**:
  - [x] Entry when implementation starts (status → in-progress)
  - [x] Entry when phase completes
  - [x] Entry when project completes
  - [x] Entry for significant divergences (flagged items)
  - [x] Entries follow existing CHANGELOG format

#### Task 3.4: Implement REQUIREMENTS.md criteria sync

- **Description**: Update acceptance criteria checkboxes when verified during implementation
- **Acceptance Criteria**:
  - [x] Parse acceptance criteria checkboxes from REQUIREMENTS.md
  - [x] When task completion satisfies a criterion, update checkbox
  - [x] Link task completion to specific criteria (may require heuristics or explicit mapping)

#### Task 3.5: Implement sync orchestration

- **Description**: Coordinate all document updates after PROGRESS.md changes
- **Acceptance Criteria**:
  - [x] After any PROGRESS.md update, trigger sync to relevant documents
  - [x] Handle sync failures gracefully (log error, continue)
  - [x] Provide summary of documents updated
  - [x] Avoid redundant updates (only update if state actually changed)

### Phase 3 Deliverables

- [x] IMPLEMENTATION_PLAN.md checkboxes auto-update
- [x] README.md frontmatter stays current
- [x] CHANGELOG.md receives automatic entries
- [x] REQUIREMENTS.md criteria tracking (best effort)
- [x] Sync engine coordinates all updates

### Phase 3 Exit Criteria

- [x] Completing a task updates checkboxes in IMPLEMENTATION_PLAN.md
- [x] Project status change updates README.md frontmatter
- [x] Phase completion adds CHANGELOG entry

---

## Phase 4: Polish

**Goal**: Handle edge cases, improve error recovery, and document the feature
**Prerequisites**: Phase 3 complete

### Tasks

#### Task 4.1: Handle edge cases

- **Description**: Address known edge cases and unusual scenarios
- **Acceptance Criteria**:
  - [x] No matching project: Clear error message with guidance
  - [x] Multiple matching projects: Interactive selection
  - [x] Empty IMPLEMENTATION_PLAN.md: Graceful handling
  - [x] Manual checkbox edit: Reconciliation on startup
  - [x] PROGRESS.md format corruption: Recovery guidance

#### Task 4.2: Add implementation brief generation

- **Description**: Generate concise summary of current state on `/arch:i` startup
- **Acceptance Criteria**:
  - [x] Display project name and ID
  - [x] Show current phase and overall progress
  - [x] List recently completed tasks
  - [x] List next pending tasks
  - [x] Note any flagged divergences

#### Task 4.3: Update CLAUDE.md documentation

- **Description**: Document the new `/arch:i` command in project CLAUDE.md
- **Acceptance Criteria**:
  - [x] Add `/arch:i` to Architecture Planning command table
  - [x] Describe workflow: `/arch:p` → `/arch:i` → `/arch:s` → `/arch:c`
  - [x] Document PROGRESS.md checkpoint system
  - [x] Provide example usage

#### Task 4.4: Add validation and self-test

- **Description**: Implement basic validation to catch common issues
- **Acceptance Criteria**:
  - [x] Validate PROGRESS.md format on load
  - [x] Warn if task count doesn't match IMPLEMENTATION_PLAN.md
  - [x] Warn if project status seems inconsistent with task states
  - [x] Provide fix suggestions for detected issues

### Phase 4 Deliverables

- [x] Edge cases handled gracefully
- [x] Implementation brief displayed on startup
- [x] CLAUDE.md documentation updated
- [x] Validation and self-test in place

### Phase 4 Exit Criteria

- [x] `/arch:i` handles all documented edge cases
- [x] User has clear understanding of what's happening
- [x] Feature is self-documenting

---

## Dependency Graph

```
Phase 1:
  Task 1.1 ──┬──► Task 1.2 ──┬──► Task 1.4
             │               │
             └──► Task 1.3 ──┘

Phase 2 (depends on Phase 1):
  Task 2.1 ──┬──► Task 2.2 ──► Task 2.3
             │
             └──► Task 2.4

  Task 2.5 (parallel to above)

Phase 3 (depends on Phase 2):
  Task 3.1 ──┐
  Task 3.2 ──┼──► Task 3.5
  Task 3.3 ──┤
  Task 3.4 ──┘

Phase 4 (depends on Phase 3):
  Task 4.1 ──┐
  Task 4.2 ──┼──► (All can be parallelized)
  Task 4.3 ──┤
  Task 4.4 ──┘
```

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| PROGRESS.md format changes break parsing | Version format in frontmatter; add migration logic | Phase 1 |
| Branch name doesn't match project | Interactive fallback selection | Phase 1 |
| User manually edits checkboxes causing desync | Reconciliation on startup | Phase 4 |
| Large projects exceed context limits | Progressive loading (future) | Phase 4 |

## Testing Checklist

- [x] Unit test: Task status transitions
- [x] Unit test: Phase completion calculation
- [x] Unit test: Project status derivation
- [x] Integration test: PROGRESS.md → IMPLEMENTATION_PLAN.md sync
- [x] Integration test: Full lifecycle (start → complete)
- [x] Integration test: Multi-session resume
- [x] Edge case: No matching project
- [x] Edge case: Manual checkbox edit
- [x] Edge case: Skipped tasks

## Documentation Tasks

- [x] Update CLAUDE.md with `/arch:i` command
- [x] Add inline documentation in `i.md` command file
- [x] Document PROGRESS.md format for users who want to manually edit

## Launch Checklist

- [x] All Phase 1-4 tasks complete
- [x] Testing checklist complete
- [x] Documentation tasks complete
- [x] Tested with real project (this planning project!)
- [x] Ready for PR to main

## Post-Launch

- [x] Monitor for issues during first uses
- [x] Gather feedback on workflow
- [x] Consider `/arch:s` integration (P2)
- [x] Consider estimated vs actual effort tracking (P2)
