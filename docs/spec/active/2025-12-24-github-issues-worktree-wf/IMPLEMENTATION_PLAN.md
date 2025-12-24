---
document_type: implementation_plan
project_id: SPEC-2025-12-24-001
version: 1.0.0
last_updated: 2025-12-24T17:15:00Z
status: draft
estimated_effort: 16-24 hours
---

# GitHub Issues Worktree Workflow - Implementation Plan

## Overview

Implementation proceeds in 4 phases:
1. **Foundation**: Prerequisites and basic issue fetching
2. **Core Workflow**: Issue selection, worktree creation, branch naming
3. **Completeness & Comments**: AI evaluation and GitHub comment posting
4. **Polish**: Error handling, edge cases, documentation

## Team & Resources

| Role | Responsibility | Allocation |
|------|---------------|------------|
| Developer | All implementation | 100% |
| User | Testing, feedback | As needed |

## Phase Summary

| Phase | Description | Key Deliverables |
|-------|-------------|------------------|
| Phase 1: Foundation | Prerequisites check, gh CLI integration | Working issue fetch |
| Phase 2: Core | Selection UI, worktree creation, branch naming | End-to-end single issue flow |
| Phase 3: Completeness | AI evaluation, comment drafting/posting | Full feature with clarification |
| Phase 4: Polish | Error handling, tests, documentation | Production-ready |

---

## Phase 1: Foundation

**Goal**: Establish gh CLI integration and prerequisite checking

**Prerequisites**: gh CLI installed on development machine

### Tasks

#### Task 1.1: Add Argument Type Detection for No-Args Case

- **Description**: Extend Step 0 in plan.md to detect when no arguments are provided and route to a new `github_issues_workflow` path
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] When `/plan` run with no args, ARG_TYPE is set to `no_args`
  - [ ] Existing argument types (existing_file, project_reference, new_seed) continue to work
  - [ ] Decision gate routes no_args to new workflow section

#### Task 1.2: Implement Prerequisites Checker

- **Description**: Create bash function to verify gh CLI is installed, authenticated, and in a GitHub repo
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Function checks `gh` CLI is in PATH
  - [ ] Function verifies `gh auth status` returns success
  - [ ] Function extracts repo name via `gh repo view`
  - [ ] Clear error messages for each failure case

#### Task 1.3: Implement Basic Issue Fetcher

- **Description**: Create bash function to fetch open issues from current repo with JSON output
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Function calls `gh issue list --state open --json number,title,labels,body,url`
  - [ ] Output is valid JSON array
  - [ ] Handles empty issue list gracefully

#### Task 1.4: Add Label Filter Support

- **Description**: Extend issue fetcher to support filtering by labels
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Accepts comma-separated label list
  - [ ] Correctly passes `--label` flags to gh CLI
  - [ ] Default labels: enhancement, bug, documentation

#### Task 1.5: Add Assignee Filter Support

- **Description**: Extend issue fetcher to support filtering by assignee
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Accepts assignee string (including `@me`)
  - [ ] Correctly passes `--assignee` flag to gh CLI

### Phase 1 Deliverables
- [ ] Argument detection working for no-args case
- [ ] Prerequisites checker functional
- [ ] Issue fetcher returning valid JSON
- [ ] Label and assignee filtering working

### Phase 1 Exit Criteria
- [ ] Can run `/plan` with no args and see JSON output of issues in terminal

---

## Phase 2: Core Workflow

**Goal**: Implement issue selection and worktree creation with conventional branch naming

**Prerequisites**: Phase 1 complete

### Tasks

#### Task 2.1: Design Filter Selection UI

- **Description**: Create AskUserQuestion interaction for users to choose which filters to apply before fetching issues
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] AskUserQuestion with multiSelect for labels (enhancement, bug, documentation)
  - [ ] AskUserQuestion with option for "Assigned to me" filter
  - [ ] Handles "Other" response for custom labels

#### Task 2.2: Implement Issue Selection UI

- **Description**: Transform fetched issues into AskUserQuestion format for multi-select
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Each issue shown as option with "#N - Title" format
  - [ ] Description includes labels and assignee info
  - [ ] MultiSelect enabled for choosing multiple issues
  - [ ] Max 4 issues per question (pagination if more)

#### Task 2.3: Implement Label-to-Prefix Mapper

- **Description**: Create function that maps issue labels to conventional commit branch prefixes
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] bug label → `bug/` prefix
  - [ ] documentation/docs label → `docs/` prefix
  - [ ] chore/maintenance label → `chore/` prefix
  - [ ] enhancement/feature (or default) → `feat/` prefix
  - [ ] Priority: bug > docs > chore > feat

#### Task 2.4: Implement Branch Name Generator

- **Description**: Create function that generates branch names from issue number, title, and labels
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Format: `{prefix}/{issue_number}-{slugified_title}`
  - [ ] Title slugified: lowercase, non-alphanumeric → hyphen, max 40 chars
  - [ ] No double hyphens, no trailing hyphens
  - [ ] Example: `feat/42-add-dark-mode-support`

#### Task 2.5: Implement Single-Issue Worktree Creation

- **Description**: Create worktree for a single selected issue with appropriate branch
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Branch created with generated name
  - [ ] Worktree created at standard location
  - [ ] Ports allocated via existing script
  - [ ] Registered in global registry
  - [ ] `.issue-context.json` created with issue metadata

#### Task 2.6: Implement Parallel Worktree Creation

- **Description**: Create worktrees for multiple selected issues in parallel
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Ports allocated upfront for all worktrees
  - [ ] Worktrees created (can be sequential for safety)
  - [ ] All registered in global registry
  - [ ] Summary displayed with paths

#### Task 2.7: Implement Parallel Agent Launch

- **Description**: Launch Claude agents in new terminals for each created worktree
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Calls `launch-agent.sh` for each worktree
  - [ ] Initial prompt includes issue context
  - [ ] Multiple terminals opened simultaneously
  - [ ] User informed of all launched sessions

### Phase 2 Deliverables
- [ ] Filter selection UI working
- [ ] Issue selection UI working
- [ ] Branch naming following conventions
- [ ] Single and multi-issue worktree creation
- [ ] Agents launching in new terminals

### Phase 2 Exit Criteria
- [ ] Can select 2 issues and have 2 worktrees created with correctly named branches
- [ ] Can see 2 new terminal windows with Claude ready

---

## Phase 3: Completeness & Comments

**Goal**: Add AI-powered issue completeness evaluation and GitHub comment posting

**Prerequisites**: Phase 2 complete

### Tasks

#### Task 3.1: Design Completeness Evaluation Protocol

- **Description**: Define the AI evaluation criteria and output format for issue completeness
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Evaluation criteria documented (problem statement, context, scope, acceptance criteria, reproduction steps)
  - [ ] Three verdict types: SUFFICIENT, NEEDS_CLARIFICATION, MINIMAL
  - [ ] Reasoning included with verdict
  - [ ] Missing elements listed specifically

#### Task 3.2: Implement Completeness Check Flow

- **Description**: After worktree creation (but before agent launch), evaluate issue and present options
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Issue body analyzed for completeness
  - [ ] Verdict and reasoning shown to user
  - [ ] AskUserQuestion presented with 4 options:
    - Post clarifying comment
    - Add details now (inline)
    - Proceed anyway
    - Skip this issue

#### Task 3.3: Implement Comment Draft Generator

- **Description**: Generate professional clarification request based on what's missing
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Draft is professional and actionable
  - [ ] Specifically mentions what's missing (from evaluation)
  - [ ] Uses markdown formatting
  - [ ] Not accusatory or demanding

#### Task 3.4: Implement Comment Confirmation UI

- **Description**: Show draft comment and get explicit user confirmation before posting
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Full draft shown to user
  - [ ] Issue number and title shown for context
  - [ ] AskUserQuestion: "Post this comment?" with Yes/Edit/Cancel
  - [ ] If Edit, allow user to provide modified version

#### Task 3.5: Implement Comment Poster

- **Description**: Post approved comment to GitHub via gh CLI
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Calls `gh issue comment {number} --body "{text}"`
  - [ ] Confirms success to user
  - [ ] Handles failure gracefully with error message

#### Task 3.6: Implement Inline Details Flow

- **Description**: When user chooses "Add details now", allow them to provide context that enriches the issue understanding
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] User can provide additional context via free text (or AskUserQuestion with Other)
  - [ ] Context appended to `.issue-context.json`
  - [ ] Proceed to agent launch with enriched context

### Phase 3 Deliverables
- [ ] Completeness evaluation working
- [ ] Comment drafting working
- [ ] Comment posting with confirmation
- [ ] Inline details option working

### Phase 3 Exit Criteria
- [ ] Can evaluate an issue, see what's missing, draft a comment, and post it
- [ ] Can add details inline and proceed with enriched context

---

## Phase 4: Polish

**Goal**: Error handling, edge cases, testing, and documentation

**Prerequisites**: Phase 3 complete

### Tasks

#### Task 4.1: Add Comprehensive Error Handling

- **Description**: Handle all error cases with clear user messaging
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] gh CLI not installed → install instructions
  - [ ] Not authenticated → auth instructions
  - [ ] No GitHub remote → explain requirement
  - [ ] No open issues → suggest filters or manual /plan
  - [ ] Branch already exists → offer alternative name
  - [ ] Rate limiting → explain and suggest waiting

#### Task 4.2: Add Issue Pagination

- **Description**: Handle cases where more than 4 issues need to be shown
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] If > 4 issues, present in batches of 4
  - [ ] "Show more issues" option available
  - [ ] User can select across multiple pages

#### Task 4.3: Add Configuration Support

- **Description**: Allow customization via `.claude/` files
- **Files**: `commands/plan.md`, new config file
- **Acceptance Criteria**:
  - [ ] Custom label-to-prefix mappings
  - [ ] Default filters (labels, assignee)
  - [ ] Completeness strictness level

#### Task 4.4: Update CLAUDE.md Integration

- **Description**: Add documentation about the feature and update Active Projects tracking
- **Files**: `CLAUDE.md`, project `README.md`
- **Acceptance Criteria**:
  - [ ] Feature documented in CLAUDE.md
  - [ ] Usage examples provided
  - [ ] Worktree created with issue# shown in status

#### Task 4.5: Add Unit Tests for Helpers

- **Description**: Test label-to-prefix mapping and branch name generation
- **Files**: `tests/test_github_workflow.py` (if Python tests needed)
- **Acceptance Criteria**:
  - [ ] Label mapping tests for all cases
  - [ ] Branch name generation edge cases
  - [ ] Special character handling

#### Task 4.6: Update README and Documentation

- **Description**: Document the new feature for users
- **Files**: `README.md`, `commands/plan.md` help section
- **Acceptance Criteria**:
  - [ ] Feature documented with examples
  - [ ] Prerequisites listed (gh CLI)
  - [ ] Workflow explained step by step
  - [ ] Help output updated

#### Task 4.7: Update CHANGELOG

- **Description**: Document the new feature in CHANGELOG.md
- **Files**: `CHANGELOG.md`
- **Acceptance Criteria**:
  - [ ] Version bump (minor)
  - [ ] Feature described
  - [ ] Any breaking changes noted (none expected)

### Phase 4 Deliverables
- [ ] Robust error handling
- [ ] Pagination working
- [ ] Configuration support
- [ ] Documentation updated
- [ ] Tests passing

### Phase 4 Exit Criteria
- [ ] Feature is production-ready
- [ ] All edge cases handled
- [ ] Documentation complete

---

## Dependency Graph

```
Phase 1: Foundation
  Task 1.1 (arg detection)
       │
       ├──► Task 1.2 (prerequisites) ──► Task 1.3 (issue fetch)
       │                                       │
       │                                       ├──► Task 1.4 (labels)
       │                                       └──► Task 1.5 (assignee)
       │
       ▼
Phase 2: Core
  Task 2.1 (filter UI) ──► Task 2.2 (issue select UI)
                                  │
  Task 2.3 (label mapper) ──┬──► Task 2.4 (branch gen)
                            │           │
                            │           ▼
                            └───► Task 2.5 (single worktree)
                                        │
                                        ▼
                                  Task 2.6 (parallel worktrees)
                                        │
                                        ▼
                                  Task 2.7 (parallel agents)
                                        │
                                        ▼
Phase 3: Completeness
  Task 3.1 (eval protocol) ──► Task 3.2 (check flow)
                                      │
                                      ├──► Task 3.3 (draft gen)
                                      │         │
                                      │         ▼
                                      │   Task 3.4 (confirm UI)
                                      │         │
                                      │         ▼
                                      │   Task 3.5 (post comment)
                                      │
                                      └──► Task 3.6 (inline details)
                                                │
                                                ▼
Phase 4: Polish
  Task 4.1 (error handling)
  Task 4.2 (pagination)        ──► (can parallelize)
  Task 4.3 (configuration)
  Task 4.4 (CLAUDE.md)
  Task 4.5 (tests)
  Task 4.6 (docs)
  Task 4.7 (CHANGELOG)
```

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| gh CLI not installed | Task 4.1 - Clear install instructions | 4 |
| Rate limiting | Task 4.1 - Detect and advise waiting | 4 |
| Large issue count | Task 4.2 - Pagination | 4 |
| Branch conflicts | Task 4.1 - Offer alternative names | 4 |

## Testing Checklist

- [ ] Prerequisites check - all failure modes
- [ ] Issue fetch - empty list, large list, filtered
- [ ] Branch naming - all label types, special chars
- [ ] Worktree creation - single, multiple
- [ ] Agent launch - single, parallel
- [ ] Completeness - sufficient, needs clarification, minimal
- [ ] Comment posting - success, failure
- [ ] Inline details - context appending

## Documentation Tasks

- [ ] Update CLAUDE.md with feature docs
- [ ] Update README.md with usage examples
- [ ] Update help output in plan.md

## Launch Checklist

- [ ] All P0 requirements implemented
- [ ] Error handling comprehensive
- [ ] Documentation complete
- [ ] Manual testing passed
- [ ] CHANGELOG updated

## Post-Launch

- [ ] Monitor for issues
- [ ] Gather user feedback
- [ ] Consider P1/P2 features
- [ ] Archive planning documents
