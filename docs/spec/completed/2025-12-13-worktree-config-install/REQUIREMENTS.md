---
document_type: requirements
project_id: SPEC-2025-12-13-001
version: 1.0.0
last_updated: 2025-12-13T14:30:00Z
status: draft
---

# Worktree Manager Configuration Installation - Product Requirements Document

## Executive Summary

The worktree-manager skill currently stores its configuration (`config.json`) within the plugin directory structure. This causes user preferences to be overwritten when the plugin is updated. This project moves configuration to a stable user-level location (`~/.claude/worktree-manager.config.json`) with an interactive setup flow using Claude's `AskUserQuestion` tool. Additionally, this fixes a bug where prompt logging isn't enabled early enough to capture the first prompt when a worktree is created.

## Problem Statement

### The Problem

1. **Config Overwrite**: User-customized `config.json` is located at `plugins/cs/skills/worktree-manager/config.json`. When the plugin updates, this file is overwritten, losing user preferences (terminal, shell, claude command alias, etc.).

2. **First-Prompt Loss**: When `/cs:p` creates a worktree and launches a new Claude agent, the `.prompt-log-enabled` marker isn't created until after the first prompt is processed in the new session, causing the first prompt to not be captured.

### Impact

- Users lose custom settings on every plugin update
- Manual re-configuration is tedious and error-prone
- Incomplete prompt logs miss valuable context for retrospectives

### Current State

- `config.json` lives at `plugins/cs/skills/worktree-manager/config.json`
- Scripts find it via relative path: `$SCRIPT_DIR/../config.json`
- No interactive setup exists; users must manually edit the JSON file
- Prompt log marker is created after worktree agent receives its first prompt

## Goals and Success Criteria

### Primary Goal

Persist user configuration across plugin updates via a stable user-level config file with interactive first-time setup.

### Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Config persistence | 100% | User config survives plugin update |
| Setup completion | First-run | Interactive questions complete successfully |
| First prompt capture | 100% | All prompts captured including first |

### Non-Goals (Explicit Exclusions)

- Multiple OS-specific templates (single default template for now)
- Migration of existing user configs (fresh setup only)
- GUI configuration interface

## User Analysis

### Primary Users

- **Who**: Developers using the worktree-manager skill for parallel development
- **Needs**: Personalized terminal/shell preferences that persist
- **Context**: First-time setup or after clean install

### User Stories

1. As a user, I want my worktree-manager preferences to persist across plugin updates so I don't have to reconfigure my terminal, shell, and claude command alias each time.

2. As a new user, I want to be guided through initial configuration with sensible defaults so I can get started quickly without editing JSON files.

3. As a user using `/cs:p`, I want all my prompts captured in the log (including the first one) so I have complete context for retrospectives.

## Functional Requirements

### Must Have (P0)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-001 | Move bundled `config.json` to `config.template.json` | Distinguish template from user config | Template file exists in plugin, original removed |
| FR-002 | User config location at `~/.claude/worktree-manager.config.json` | Stable location outside plugin | Scripts look for config at this path first |
| FR-003 | Config lookup precedence: user config → template fallback | Allow customization while providing defaults | Scripts work with either or both configs |
| FR-004 | Interactive setup via `AskUserQuestion` | User-friendly first-time experience | Questions presented for terminal, shell, claudeCommand, worktreeBase |
| FR-005 | Auto-detect shell from `$SHELL` environment | Reduce user friction | Shell defaults to detected value |
| FR-006 | Setup triggers when user config doesn't exist | Automatic onboarding | Setup runs on first worktree command |
| FR-007 | Fix prompt log timing for worktree creation | Capture first prompt | `.prompt-log-enabled` created in worktree before agent launch |

### Should Have (P1)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-101 | Explicit setup command (e.g., `/cs:wt:setup`) | Allow re-configuration | Command triggers interactive setup |
| FR-102 | Validate config on load | Catch invalid configs early | Missing fields use template defaults |

### Nice to Have (P2)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-201 | Show current config summary | User visibility | Display current values before questions |

## Non-Functional Requirements

### Performance

- Config loading adds < 50ms to script execution
- Setup flow completes in single Claude conversation turn

### Security

- Config file permissions match Claude's default (user-readable only)
- No secrets stored in config (ports, paths only)

### Reliability

- Scripts function with missing or partial config (use defaults)
- Atomic config file writes to prevent corruption

### Maintainability

- Config schema documented in SKILL.md
- Single source of truth for default values (template file)

## Technical Constraints

- Scripts written in bash (existing pattern)
- Config is JSON (requires `jq` for parsing)
- Interactive setup must use Claude's `AskUserQuestion` tool
- Must maintain backwards compatibility with existing worktree operations

## Dependencies

### Internal Dependencies

- `plugins/cs/skills/worktree-manager/scripts/*.sh` - Need modification
- `plugins/cs/commands/p.md` - Needs prompt log timing fix

### External Dependencies

- `jq` - JSON processing (already required)
- Claude Code's `AskUserQuestion` tool

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Script changes break existing workflows | Medium | High | Comprehensive testing, fallback to defaults |
| Users confused by setup questions | Low | Medium | Clear question descriptions, sensible defaults |
| Config file corruption | Low | Medium | Atomic writes, template fallback |

## Open Questions

- [x] Which fields to ask interactively? → terminal, shell, claudeCommand, worktreeBase
- [x] Config lookup precedence? → User config first, template fallback
- [x] Where to fix prompt log timing? → In `/cs:p` before launching agent

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| Worktree | Git feature for multiple working directories from one repo |
| Template | Default config shipped with plugin |
| User config | Personalized config at `~/.claude/` |

### Current Config Schema

```json
{
  "terminal": "iterm2-tab",           // Interactive: terminal choice
  "shell": "bash",                     // Interactive: detect from $SHELL
  "claudeCommand": "cc",               // Interactive: user's alias
  "portPool": {
    "start": 8100,
    "end": 8199
  },                                   // Default: sensible range
  "portsPerWorktree": 2,               // Default: 2
  "worktreeBase": "~/Projects/worktrees",  // Interactive: user preference
  "registryPath": "~/.claude/worktree-registry.json",  // Default: fixed
  "defaultCopyDirs": [".agents", ".env.example", ".env"],  // Default
  "healthCheckTimeout": 30,            // Default
  "healthCheckRetries": 6              // Default
}
```

### References

- Existing SKILL.md: `plugins/cs/skills/worktree-manager/SKILL.md`
- Launch agent script: `plugins/cs/skills/worktree-manager/scripts/launch-agent.sh`
- Allocate ports script: `plugins/cs/skills/worktree-manager/scripts/allocate-ports.sh`
