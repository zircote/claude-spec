---
document_type: requirements
project_id: SPEC-2025-12-25-001
version: 1.0.0
last_updated: 2025-12-25T17:00:00Z
status: draft
---

# Add /approve Command - Product Requirements Document

## Executive Summary

This project introduces an explicit approval gate between `/claude-spec:plan` and `/claude-spec:implement` to enforce proper governance and prevent premature implementation. The current workflow allows jumping directly from planning to implementation without formal review, approval recording, or audit trail.

Additionally, this project adds flexibility flags to `/claude-spec:plan` and implements comprehensive safeguards to prevent Claude from ever skipping the planning phase and jumping directly to implementation.

## Problem Statement

### The Problem

1. **No Approval Gate**: Plans can be implemented immediately without explicit stakeholder sign-off
2. **No Audit Trail**: No record of who approved a plan or when
3. **Planning Skip Risk**: Claude can accidentally skip planning and jump to implementation (as demonstrated in this very session)
4. **Workflow Friction**: `/plan` always creates worktrees/branches even when not desired

### Impact

- Governance gaps in enterprise workflows
- No accountability for plan approval decisions
- Risk of implementing unapproved or draft specifications
- Wasted effort from implementing poorly-specified features
- User frustration when worktree creation is unnecessary

### Current State

```
/plan "idea"  -->  Creates spec (draft/in-review)
      |
      v
/implement slug  -->  Tracks implementation (no approval check)
      |
      v
/complete slug  -->  Close out with retrospective
```

## Goals and Success Criteria

### Primary Goal

Create an explicit, auditable approval gate that ensures all specifications are formally reviewed and approved before implementation begins.

### Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Approval rate | 100% of implemented specs have approval record | Query README.md frontmatter |
| Planning compliance | 0 instances of implementation without spec | Hook enforcement logs |
| User satisfaction | No worktree/branch complaints | User feedback |

### Non-Goals (Explicit Exclusions)

- Multi-approver workflows (future enhancement)
- Approval expiration/re-approval (future enhancement)
- Integration with external approval systems (Jira, etc.)
- Automated approval based on criteria

## User Analysis

### Primary Users

- **Plugin users**: Developers using claude-spec for project planning
- **Claude Code**: The AI agent executing commands (must follow workflow)

### User Stories

1. As a user, I want to formally approve a plan before implementation so that I have a record of the decision
2. As a user, I want to reject a plan with notes so that I can iterate on the specification
3. As a user, I want Claude to warn me if I try to implement an unapproved spec so that I don't skip governance
4. As a user, I want to skip worktree/branch creation when running `/plan` so that I have workflow flexibility
5. As a user, I want Claude to NEVER skip planning and jump to implementation so that all work is properly specified

## Functional Requirements

### Must Have (P0)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-001 | `/approve` command exists | Core feature | Command file at `commands/approve.md` |
| FR-002 | Validate spec completeness | Ensure quality | Checks for README.md, REQUIREMENTS.md, ARCHITECTURE.md, IMPLEMENTATION_PLAN.md |
| FR-003 | Display plan summary | Enable informed decision | Shows document stats, scope overview, key metrics |
| FR-004 | Record approval in metadata | Audit trail | Updates README.md frontmatter with `status: approved`, `approved_date`, `approved_by` |
| FR-005 | Use git user for approver | Identity capture | Reads `git config user.name` and `git config user.email` |
| FR-006 | Rejection moves to rejected/ | Clean separation | Creates `docs/spec/rejected/` and moves spec there |
| FR-007 | `/implement` warns on unapproved | Prevent oversight | Displays warning but allows proceeding |
| FR-008 | `/plan --no-worktree` flag | Workflow flexibility | Skips worktree creation, works in current directory |
| FR-009 | `/plan --no-branch` flag | Workflow flexibility | Skips branch creation, works on current branch |
| FR-010 | `/plan --inline` flag | Convenience | Shorthand for both --no-worktree and --no-branch |
| FR-011 | PreToolUse hook enforcement | Prevent planning skip | Blocks Write/Edit to implementation files without approved spec |
| FR-012 | Command instruction hardening | Prevent planning skip | Add explicit NEVER IMPLEMENT warnings to /plan |
| FR-013 | Workflow documentation | Prevent planning skip | Update CLAUDE.md with workflow diagrams and guidance |

### Should Have (P1)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-101 | Create APPROVAL.md document | Formal decision record | Optional document with approval rationale |
| FR-102 | Approval notes field | Capture context | Allow approver to add notes during approval |
| FR-103 | `/status` shows approval state | Visibility | Approval status visible in portfolio view |
| FR-104 | Request changes flow | Iteration support | Option to request changes without rejecting |

### Nice to Have (P2)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-201 | Approval expiration | Governance | Re-approve if plan stale beyond threshold |
| FR-202 | Multi-approver support | Team workflows | Multiple approvers with quorum |
| FR-203 | Approval history | Full audit trail | Track all approval/rejection events |

## Non-Functional Requirements

### Performance

- `/approve` command completes in < 5 seconds
- Hook enforcement adds < 100ms latency

### Security

- Approver identity from git config (not user-supplied)
- No secrets in approval metadata

### Maintainability

- Follow existing command patterns (frontmatter, help_check, etc.)
- Hook rules use existing hookify infrastructure

## Technical Constraints

- Must work with existing spec directory structure (`docs/spec/active/`, etc.)
- Must use existing tools (AskUserQuestion, Edit, Bash, etc.)
- Hook must be compatible with Claude Code hook system
- Must not break existing `/plan`, `/implement`, `/complete` workflows

## Dependencies

### Internal Dependencies

- Existing command infrastructure (commands/*.md)
- Existing hook infrastructure (.claude/hooks.json or hookify)
- Existing spec directory structure

### External Dependencies

- Git (for user identity)
- Claude Code hook system

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Hook too restrictive | Medium | High | Warn-only mode, easy disable |
| Approval overhead slows velocity | Low | Medium | Streamlined single-command flow |
| Git user not configured | Low | Low | Fallback to "user" if git config empty |
| Breaking existing workflows | Medium | High | Thorough testing, backward compatibility |

## Open Questions

- [x] Should `/implement` enforce or warn? → **Warn but allow**
- [x] How to capture approver identity? → **Git user**
- [x] What happens on rejection? → **Move to rejected/**
- [x] Include `/plan` flags in this spec? → **Yes**
- [x] Prevention mechanisms? → **All four: hook, instruction hardening, status gate, documentation**

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| Spec | A specification project in docs/spec/ |
| Approval gate | Checkpoint requiring explicit approval before proceeding |
| Hook | Claude Code automation that runs before/after tool calls |

### References

- [GitHub Issue #26](https://github.com/zircote/claude-spec/issues/26)
- [Claude Code Hooks Documentation](https://docs.anthropic.com/claude-code/hooks)
- [Existing command files](../../../commands/)

### Workflow Diagram

```
                     ┌─────────────────┐
                     │  /plan "idea"   │
                     │  (creates spec) │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  status: draft  │
                     │  or in-review   │
                     └────────┬────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │        /approve slug          │
              │  (validates + records approval)│
              └───────────────┬───────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │   Approve    │  │   Request    │  │    Reject    │
   │              │  │   Changes    │  │              │
   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
          │                 │                 │
          ▼                 ▼                 ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │   status:    │  │   Iterate    │  │  Move to     │
   │   approved   │  │   on spec    │  │  rejected/   │
   └──────┬───────┘  └──────────────┘  └──────────────┘
          │
          ▼
   ┌─────────────────┐
   │ /implement slug │
   │ (warns if not   │
   │  approved)      │
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ /complete slug  │
   │ (retrospective) │
   └─────────────────┘
```

### README Frontmatter After Approval

```yaml
---
project_id: SPEC-2025-12-25-001
project_name: "Feature Name"
slug: feature-name
status: approved
created: 2025-12-25T10:00:00Z
approved_date: 2025-12-25T15:30:00Z
approved_by: "John Doe <john@example.com>"
started: null
completed: null
expires: 2026-03-25T10:00:00Z
---
```
