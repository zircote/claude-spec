---
document_type: requirements
project_id: SPEC-2025-12-24-001
version: 1.0.0
last_updated: 2025-12-24T16:50:00Z
status: draft
---

# GitHub Issues Worktree Workflow - Product Requirements Document

## Executive Summary

This feature extends the `/claude-spec:plan` command to fetch GitHub issues when invoked without arguments, present them to users for selection via AskUserQuestion, create isolated git worktrees for each selected issue, and initiate planning with AI-evaluated issue completeness checks. When issues lack sufficient detail for confident planning, users can request Claude to draft and post professional clarification comments directly to GitHub.

The goal is to streamline the workflow from "I want to work on something" to "I'm in an isolated worktree with Claude ready to plan" by leveraging GitHub's issue tracker as the source of truth for project backlog.

## Problem Statement

### The Problem

Developers currently face a fragmented workflow when starting work on GitHub issues:
1. Navigate to GitHub to find issues
2. Mentally evaluate which issues are ready for implementation
3. Manually create a worktree with an appropriate branch name
4. Start a new Claude session in that worktree
5. Copy/paste issue details into Claude for context
6. If the issue lacks details, switch contexts to write a comment requesting clarification

This multi-step, multi-context workflow creates friction and cognitive overhead.

### Impact

- **Time lost**: 5-10 minutes per issue to set up proper development environment
- **Context switching**: Moving between GitHub UI, terminal, and Claude Code
- **Inconsistency**: Branch naming varies, some issues started without proper planning
- **Delayed feedback**: When issues need clarification, developers either proceed with assumptions or leave the flow entirely

### Current State

The `/claude-spec:plan` command currently:
- Requires a project idea/seed as an argument
- Creates a worktree when on protected branches
- Guides through Socratic elicitation for requirements

There is no integration with GitHub issues - all planning starts from scratch with user-provided context.

## Goals and Success Criteria

### Primary Goal

Enable developers to go from "I want to work on an issue" to "Claude is planning my implementation in an isolated worktree" in under 60 seconds, with intelligent handling of incomplete issues.

### Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Time to worktree creation | < 60s from command to terminal | Manual timing |
| Issue selection UX | < 3 interactions to select | Count AskUserQuestion rounds |
| Completeness detection accuracy | > 80% alignment with user judgment | User feedback sampling |
| Clarification comment quality | Professional, actionable | User approval rate before posting |

### Non-Goals (Explicit Exclusions)

- Creating issues from the CLI (use `gh issue create`)
- Editing issue labels, milestones, or metadata
- Cross-repository issue aggregation in a single view
- Automatic issue assignment
- Integration with other platforms (Jira, Linear, etc.)

## User Analysis

### Primary Users

- **Who**: Developers using Claude Code with GitHub-hosted repositories
- **Needs**: Quick setup of isolated environments for issue-based work
- **Context**: Starting a new work session, triaging their backlog, or responding to newly filed issues

### User Stories

1. As a developer, I want to run `/plan` with no arguments and see my assigned issues so that I can quickly pick something to work on.

2. As a developer, I want to filter issues by labels (bug, enhancement, docs) so that I can focus on a specific type of work.

3. As a developer, I want to select multiple issues and have worktrees created for each so that I can context-switch between tasks efficiently.

4. As a developer, I want Claude to evaluate if an issue has enough detail before I commit to working on it so that I don't waste time on underspecified work.

5. As a developer, I want the option to have Claude post a clarification request to GitHub so that I don't have to leave my terminal to request more information.

6. As a developer, I want branch names to match conventional commit prefixes (feat/, bug/, docs/, chore/) so that my workflow stays consistent.

## Functional Requirements

### Must Have (P0)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-001 | Detect when `/plan` is run without arguments | Entry point for issue-based workflow | Command triggers issue fetch instead of error |
| FR-002 | Fetch issues from current repository | Scope to relevant context | Uses `gh issue list --repo` with current repo |
| FR-003 | Filter issues by state (open by default) | Only actionable issues | `--state open` is default |
| FR-004 | Present issues via AskUserQuestion | Consistent UX pattern | Issues shown as selectable options with title/number |
| FR-005 | Create worktree per selected issue | Isolated environments | Branch created, worktree path generated |
| FR-006 | Map issue labels to branch prefixes | Conventional commit alignment | enhancement→feat/, bug→bug/, docs→docs/, chore→chore/ |
| FR-007 | Launch Claude agents in parallel terminals | Multi-issue support | Each worktree gets its own terminal |
| FR-008 | Evaluate issue completeness | Quality gate | Claude assesses if elicitation can start confidently |
| FR-009 | Present completeness options via AskUserQuestion | User control | Options: Post comment, Add details, Proceed, Skip |
| FR-010 | Draft professional clarification comments | Actionable output | Comment text shown to user before posting |
| FR-011 | Post comments via `gh issue comment` | GitHub integration | Comment appears on issue after user approval |

### Should Have (P1)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-101 | Filter by label (enhancement, bug, docs) | Focus work type | `--label` flags passed to gh CLI |
| FR-102 | Filter by assignee (`@me`) | Personal backlog | `--assignee @me` filter available |
| FR-103 | Show issue labels in selection UI | Context for decision | Label names visible in AskUserQuestion options |
| FR-104 | Limit issue count in selection | UX manageability | Max 10 issues per AskUserQuestion (paginate if more) |
| FR-105 | Pre-fill worktree with issue context | Planning acceleration | Issue body passed as initial context to plan |

### Nice to Have (P2)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-201 | Cache issue list for session | Reduce API calls | Issues stored in memory for re-filtering |
| FR-202 | Custom label-to-prefix mapping | Project flexibility | Configurable via .claude/ file |
| FR-203 | Show issue age/staleness | Prioritization help | Days since created/updated shown |
| FR-204 | Support milestone filtering | Sprint focus | `--milestone` flag support |

## Non-Functional Requirements

### Performance

- Issue list fetch: < 5 seconds for up to 100 issues
- Worktree creation: < 10 seconds per worktree
- Comment posting: < 3 seconds

### Security

- No storage of GitHub tokens (delegate to `gh` CLI auth)
- Clarification comments require explicit user approval before posting
- Branch names sanitized to prevent injection

### Reliability

- Graceful handling when `gh` CLI not installed or not authenticated
- Clear error messages when GitHub API rate-limited
- Worktree creation failures don't prevent other worktrees

### Maintainability

- All `gh` CLI calls abstracted to single module
- Unit tests for label-to-prefix mapping
- Integration tests with mocked `gh` responses

## Technical Constraints

- **gh CLI**: Must be installed and authenticated (`gh auth status` returns 0)
- **Git**: Repository must be a git repo with GitHub remote
- **Platform**: macOS/Linux (existing worktree scripts are bash-based)

## Dependencies

### Internal Dependencies

- `commands/plan.md`: Must modify argument parsing logic
- `skills/worktree-manager/scripts/launch-agent.sh`: For parallel terminal launches
- `skills/worktree-manager/scripts/allocate-ports.sh`: For port allocation

### External Dependencies

- `gh` CLI (GitHub CLI) >= 2.0
- Active GitHub authentication via `gh auth login`

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| gh CLI not installed | Medium | High | Detect at command start, show install instructions |
| GitHub API rate limiting | Low | Medium | Cache issue list, batch requests |
| Large number of issues overwhelms UI | Medium | Medium | Limit to 10 per AskUserQuestion, offer pagination |
| Clarification comment posted to wrong issue | Low | High | Show full context including issue number before confirmation |
| Branch name conflicts | Medium | Medium | Check for existing branch before creation, offer alternatives |

## Open Questions

- [x] How should labels map to branch prefixes? **Resolved: Auto-detect from labels**
- [x] Multi-select or single-select for issues? **Resolved: Multi-select with parallel worktree creation**
- [x] What determines "sufficient detail"? **Resolved: AI evaluation for elicitation readiness**
- [ ] Should we support cross-repo issue fetching? **Deferred to P2**

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| Worktree | Git feature allowing multiple working directories from one repo |
| Elicitation | Structured questioning to gather requirements |
| Completeness | Whether an issue has enough detail to begin planning |
| Conventional commits | Commit message convention with type prefixes (feat, fix, docs, etc.) |

### References

- [gh CLI Issue Commands](https://cli.github.com/manual/gh_issue)
- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Conventional Commits Spec](https://www.conventionalcommits.org/)
