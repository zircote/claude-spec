---
project_id: SPEC-2025-12-24-001
project_name: "GitHub Issues Worktree Workflow"
slug: github-issues-worktree-wf
status: in-review
created: 2025-12-24T16:48:00Z
approved: null
started: null
completed: null
expires: 2026-03-24T16:48:00Z
superseded_by: null
tags: [github, issues, worktree, workflow, automation]
stakeholders: []
worktree:
  branch: plan/github-issues-worktree-wf
  base_branch: main
---

# GitHub Issues Worktree Workflow

An extension to `/claude-spec:plan` that enables fetching GitHub issues, creating worktrees for selected issues, and managing issue completeness with interactive clarification workflows.

## Status

**Current Phase**: Specification Complete - Awaiting Review

## Summary

This feature enables developers to:
1. Run `/claude-spec:plan` with **no arguments** to trigger the GitHub issues workflow
2. **Fetch issues** from the current repository with optional label/assignee filters
3. **Select issues** via AskUserQuestion multi-select
4. **Create worktrees** with conventional commit branch naming (feat/, bug/, docs/, chore/)
5. **Launch Claude agents** in parallel terminals for each selected issue
6. **Evaluate issue completeness** using AI assessment
7. **Draft and post** professional clarification comments to GitHub

### Key Design Decisions

| Decision | Choice |
|----------|--------|
| Trigger | Auto-detect when `/plan` has no args |
| GitHub integration | `gh` CLI subprocess calls |
| Branch naming | Auto-map labels → conventional prefixes |
| Multi-issue | Parallel worktree creation + terminal launch |
| Completeness | AI evaluation with user override options |
| Comments | Draft → confirm → post workflow |

### Estimated Effort

16-24 hours across 4 phases

## Quick Links

- [Requirements](./REQUIREMENTS.md) - Full PRD with user stories and success criteria
- [Architecture](./ARCHITECTURE.md) - Component design and data flow
- [Implementation Plan](./IMPLEMENTATION_PLAN.md) - Phased task breakdown
- [Decisions](./DECISIONS.md) - Architecture Decision Records
