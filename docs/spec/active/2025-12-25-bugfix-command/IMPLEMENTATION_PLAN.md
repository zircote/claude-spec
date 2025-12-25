# Implementation Plan: Issue Reporter Command

## Overview

| Attribute | Value |
|-----------|-------|
| Spec ID | SPEC-2025-12-25-002 |
| Phases | 2 |
| Priority | P1 |
| Complexity | Medium |

## Phase 1: Core Command

**Goal**: Create `/report-issue` command with investigation and issue creation

### Tasks

- [ ] 1.1 Create `commands/report-issue.md` with YAML frontmatter
- [ ] 1.2 Implement type selection (bug, feat, docs, chore, perf)
- [ ] 1.3 Implement input gathering (description via AskUserQuestion)
- [ ] 1.4 Implement investigation phase:
  - [ ] 1.4.1 Bug investigation (error trace → source → callers → tests)
  - [ ] 1.4.2 Feature investigation (similar code → patterns → integration points)
  - [ ] 1.4.3 Docs investigation (doc files → source → discrepancies)
  - [ ] 1.4.4 Chore investigation (affected files → dependencies → scope)
- [ ] 1.5 Implement findings review with user confirmation
- [ ] 1.6 Implement repository detection from error context
- [ ] 1.7 Implement repository confirmation with user
- [ ] 1.8 Implement issue preview display
- [ ] 1.9 Implement issue creation via `gh issue create`
- [ ] 1.10 Implement cancel/opt-out at every step
- [ ] 1.11 Document command in plugin README.md

### Acceptance Criteria
- Command invokable as `/claude-spec:report-issue`
- Investigation runs in 30-60 seconds
- Findings include file:line references and code snippets
- User can cancel at any step
- Issues created with AI-actionable format

## Phase 2: Command Integration

**Goal**: Add error detection and report offer to `/plan` and `/implement`

### Tasks

- [ ] 2.1 Add `<error_recovery>` section to `commands/plan.md`
- [ ] 2.2 Add `<error_recovery>` section to `commands/implement.md`
- [ ] 2.3 Implement unexpected behavior detection:
  - [ ] 2.3.1 Exceptions/tracebacks
  - [ ] 2.3.2 Command failures
  - [ ] 2.3.3 Unexpected patterns
  - [ ] 2.3.4 Empty results
- [ ] 2.4 Implement low-friction offer prompt:
  - [ ] 2.4.1 "Yes, report it"
  - [ ] 2.4.2 "No, continue"
  - [ ] 2.4.3 "Don't ask again (session)"
  - [ ] 2.4.4 "Never ask"
- [ ] 2.5 Implement session-level suppression
- [ ] 2.6 Implement permanent opt-out (settings storage)
- [ ] 2.7 Implement context handoff to `/report-issue`
- [ ] 2.8 Test integration with both commands

### Acceptance Criteria
- `/plan` and `/implement` detect unexpected behavior
- Offer appears once per issue (not spammy)
- "Don't ask again" works for session
- "Never ask" persists across sessions
- Context pre-fills `/report-issue` when invoked

## Dependencies

| Dependency | Required For |
|------------|--------------|
| `gh` CLI | Issue creation |
| Grep/Glob/Read tools | Investigation |

## Risks

| Risk | Mitigation |
|------|------------|
| Investigation too slow | Cap at 60 seconds, show progress |
| Too many false triggers | Tune detection, easy opt-out |
| Annoying prompts | Session/permanent suppression options |

## Success Metrics

- Issues filed contain sufficient context for AI resolution
- Low user opt-out rate (indicates value)
- Investigation completes within time budget
