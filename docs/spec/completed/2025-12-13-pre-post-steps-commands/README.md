---
project_id: SPEC-2025-12-13-001
project_name: "Pre and Post Steps for cs:* Commands"
slug: pre-post-steps-commands
status: completed
created: 2025-12-13T00:00:00Z
approved: 2025-12-13T22:40:00Z
started: 2025-12-13T22:40:00Z
completed: 2025-12-13T23:59:00Z
final_effort: "19 tasks, 230 tests, 96% coverage"
outcome: success
expires: 2026-03-13T00:00:00Z
superseded_by: null
tags: [plugin, commands, workflow, hooks, extensibility, security]
stakeholders: []
worktree:
  branch: plan/introduce-pre-and-post-steps-f
  base_branch: main
---

# Pre and Post Steps for cs:* Commands

## Overview

Introduce configurable pre and post steps for ALL `/cs:*` commands using Claude Code's native hook system (SessionStart, Stop, UserPromptSubmit). Pre-steps load context and perform validation; post-steps handle cleanup, archival, and analysis.

## Status

**Current**: In Progress - Implementation started

## Summary

| Aspect | Details |
|--------|---------|
| **Pre-steps for /cs:p** | Load CLAUDE.md, Git state, Project structure (via SessionStart) |
| **Pre-steps for /cs:c** | Security review/audit |
| **Post-steps for /cs:c** | Generate retrospective, Archive logs, Cleanup markers |
| **Configuration** | Defaults provided, user overrides via config file |
| **Architecture** | Pure hooks (SessionStart, UserPromptSubmit, Stop) |

## Critical: Strict Phase Separation (FR-008, FR-009, FR-010)

| Rule | Enforcement |
|------|-------------|
| **/cs:p NEVER implements** | p.md includes `<post_approval_halt>` - HALTS after spec approval |
| **Implementation ONLY via /cs:i** | i.md is the ONLY entry point, requires explicit confirmation |
| **Plan approval ≠ implementation** | Approval message directs user to run `/cs:i` separately |

## Bug Fixes Included

1. **Hook registration** - Fix plugin.json to register hooks properly
2. **iTerm2-tab** - Fix duplicate code in launch-agent.sh

## Quick Links

- [Requirements](./REQUIREMENTS.md) - Product requirements document
- [Architecture](./ARCHITECTURE.md) - Technical design
- [Implementation Plan](./IMPLEMENTATION_PLAN.md) - Phased task breakdown (4 phases, ~15 tasks)
- [Decisions](./DECISIONS.md) - 7 architecture decision records
- [Research Notes](./RESEARCH_NOTES.md) - Research findings

## Key Decisions

1. **Pure hooks approach** - Use Claude Code's native hook system
2. **SessionStart for context** - Load once on session start
3. **Security review before close-out** - Pre-step for /cs:c
4. **Fail-open design** - Hooks never block user workflow
5. **Config via worktree-manager.config.json** - Extend existing config
6. **Strict phase separation** - /cs:p ONLY produces specs, NEVER implements
7. **Explicit authorization boundary** - Implementation ONLY via /cs:i with user confirmation

## Implementation Phases

| Phase | Description |
|-------|-------------|
| Phase 1 | Foundation - Bug fixes, hook registration, config schema |
| Phase 2 | Core Hooks - SessionStart, UserPromptSubmit, Stop hooks |
| Phase 3 | Step Modules - Context loader, security reviewer, post-step actions |
| Phase 4 | Integration - Testing, documentation, release |

## Next Steps

1. Review and approve this specification
2. Begin Phase 1 implementation (bug fixes first)
3. Iterate through phases with testing
4. Release as plugin version 1.1.0
