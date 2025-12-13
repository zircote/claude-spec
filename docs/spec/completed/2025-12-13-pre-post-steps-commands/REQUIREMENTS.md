---
document_type: requirements
project_id: SPEC-2025-12-13-001
version: 1.0.0
last_updated: 2025-12-13T00:00:00Z
status: draft
---

# Pre and Post Steps for cs:* Commands - Product Requirements Document

## Executive Summary

Introduce a configurable pre/post step system for all `/cs:*` commands, leveraging Claude Code's native hook system (SessionStart, Stop, UserPromptSubmit) to automate best practices. Pre-steps load context and perform validation before command execution; post-steps handle cleanup, archival, and analysis after command completion.

## Problem Statement

### The Problem

When users launch `/cs:p` in a new worktree terminal, Claude starts with a cold context - no awareness of the project's CLAUDE.md files, git state, or existing conventions. Similarly, when closing projects with `/cs:c`, several cleanup and archival tasks must be performed manually.

### Impact

- **Developers** lose time explaining context to Claude at the start of each session
- **Quality suffers** when Claude makes decisions without full project understanding
- **Best practices are inconsistent** - some users forget cleanup steps, others skip security review
- **Prompt logs may not be archived** properly for retrospective analysis

### Current State

- `/cs:p` has a manual worktree check (in `<mandatory_first_actions>`)
- `/cs:c` has inline cleanup instructions but no automated security review
- No standardized pre/post step system exists
- Hook registration is incomplete (prompt_capture hook not firing)

## Goals and Success Criteria

### Primary Goal

Enable automated, configurable pre and post steps for all `/cs:*` commands using Claude Code's native hook system.

### Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Context loading | 100% of sessions start with project context | SessionStart hook fires |
| Security review | 100% of /cs:c runs include security pre-step | Pre-step execution logs |
| Prompt log archival | 100% of closed projects have archived logs | File presence check |
| User configuration adoption | >50% of users customize steps | Config file analysis |

### Non-Goals (Explicit Exclusions)

- Replacing Claude Code's native hook system with custom implementation
- Adding pre/post steps to non-/cs:* commands (out of scope)
- Real-time security scanning (use static analysis tools instead)
- Blocking hooks that prevent command execution (fail-open design)

## User Analysis

### Primary Users

- **Who**: Developers using the claude-spec plugin for project planning
- **Needs**: Consistent context loading, automated best practices, clean project close-out
- **Context**: Working in git worktrees, managing multiple spec projects

### User Stories

1. As a developer, I want Claude to automatically know my project's conventions when I start a planning session, so I don't have to re-explain them.
2. As a developer, I want a security review to run before I close out a project, so I catch vulnerabilities before marking it complete.
3. As a developer, I want prompt logs automatically archived when I close a project, so I can analyze them in retrospectives.
4. As a developer, I want to customize which pre/post steps run, so I can adapt the workflow to my team's needs.

## Functional Requirements

### Must Have (P0)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-001 | SessionStart hook loads context on session start | Ensures Claude has project awareness | Hook fires, context appears in Claude's memory |
| FR-002 | Pre-step for /cs:c runs security review | Catches vulnerabilities before close-out | Security agent invoked, findings reported |
| FR-003 | Post-step for /cs:c archives prompt logs | Preserves logs for retrospective | .prompt-log.json moved to completed/ |
| FR-004 | Post-step for /cs:c cleans up markers | Removes temporary files | .prompt-log-enabled deleted |
| FR-005 | Post-step for /cs:c generates retrospective | Automates RETROSPECTIVE.md creation | File created in completed/ |
| FR-006 | Configuration file allows step customization | Users can override defaults | Config schema validated, overrides work |
| FR-007 | Fix hook registration in plugin.json | Current hooks not firing | UserPromptSubmit hook executes |
| FR-008 | **Strict phase separation: /cs:p NEVER implements** | Prevents unauthorized implementation | p.md includes explicit HALT after spec approval, ExitPlanMode never triggers implementation |
| FR-009 | **Implementation ONLY via explicit /cs:i invocation** | Clear authorization boundary | i.md is the ONLY entry point to implementation, user must explicitly run /cs:i |
| FR-010 | **Plan approval !== implementation authorization** | Prevents scope creep | p.md post-step displays "Run /cs:i to implement" message, does NOT auto-proceed |

### Should Have (P1)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-101 | Pre-steps can be disabled per-command | Flexibility for advanced users | Config option disables step |
| FR-102 | Post-steps report execution summary | Transparency into what ran | Summary printed to console |
| FR-103 | Step execution is logged | Debugging and audit trail | Log entries in .prompt-log.json |
| FR-104 | Fail-open design for all hooks | Never block user workflow | Errors logged, command continues |

### Nice to Have (P2)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-201 | Custom user-defined steps | Extensibility | Config accepts arbitrary commands |
| FR-202 | Step timing metrics | Performance analysis | Execution time logged |
| FR-203 | Dry-run mode for steps | Testing without side effects | --dry-run flag supported |

## Non-Functional Requirements

### Performance

- SessionStart hook must complete within 5 seconds
- Pre/post steps must not add >10 seconds to command execution
- Security review may take longer but should show progress

### Security

- Hooks must not expose secrets in logs (use existing filter pipeline)
- Security review step must use established security-auditor agent
- No arbitrary code execution from untrusted config files

### Reliability

- Fail-open design: hook failures never block user commands
- All errors logged to stderr, not swallowed
- Graceful degradation if dependencies unavailable

### Maintainability

- Follow existing hook patterns (prompt_capture.py as template)
- Use existing filter pipeline for content processing
- Test coverage >90% for new hook code

## Technical Constraints

- Must use Claude Code's native hook system (SessionStart, Stop, UserPromptSubmit)
- Must integrate with existing worktree-manager.config.json
- Must work with current plugin architecture
- Python 3.11+ for hook implementations

## Dependencies

### Internal Dependencies

- `filters/` - Content filtering for logs
- `hooks/prompt_capture.py` - Template for new hooks
- `skills/worktree-manager/` - Config system
- `commands/*.md` - Command definitions

### External Dependencies

- Claude Code hook system (SessionStart, Stop events)
- security-auditor agent from ~/.claude/agents/
- jq for JSON processing in bash

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SessionStart hook not supported by Claude Code | Low | High | Verify hook exists before implementation |
| Security review takes too long | Medium | Medium | Add timeout, show progress indicator |
| Config schema changes break existing users | Medium | Medium | Version config schema, provide migration |
| Hooks interfere with each other | Low | Medium | Clear hook ordering, isolated execution |

## Open Questions

- [x] Should pre/post steps be configurable? → Yes, via config file override
- [x] What context should pre-steps load? → CLAUDE.md, Git state, Project structure
- [x] What should /cs:c post-steps do? → Retrospective, cleanup, archive
- [x] Should security review be pre or post? → Pre-step for /cs:c
- [ ] Should we support custom hooks beyond the defined steps?
- [ ] How to handle hook execution in headless mode?

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| Pre-step | Action that runs before a command's main logic |
| Post-step | Action that runs after a command completes |
| SessionStart hook | Claude Code hook that fires on session initialization |
| Fail-open | Design pattern where failures allow continuation rather than blocking |

### References

- Claude Code Hooks Documentation
- Existing hooks implementation: `plugins/cs/hooks/`
- Config system: `plugins/cs/skills/worktree-manager/scripts/lib/config.sh`
