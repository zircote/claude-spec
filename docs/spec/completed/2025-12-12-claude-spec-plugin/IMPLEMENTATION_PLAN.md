---
document_type: implementation_plan
project_id: SPEC-2025-12-12-002
version: 1.0.0
last_updated: 2025-12-12
status: draft
estimated_effort: 8-12 hours
---

# Claude Spec Plugin - Implementation Plan

## Overview

This plan implements the `claude-spec` plugin - a comprehensive Claude Code plugin bundling project specification workflows, worktree management, and prompt capture.

## Phase Summary

| Phase | Goal | Lead Agent | Parallel Agents | Key Deliverables |
|-------|------|------------|-----------------|------------------|
| Phase 1: Scaffold | Create plugin structure and manifest | mcp-developer | cli-developer | Plugin directory, manifest, basic README |
| Phase 2: Commands | Migrate and rename /arch:* commands | prompt-engineer | documentation-engineer | 9 command files in commands/cs/ |
| Phase 3: Hooks | Implement prompt capture as plugin hook | mcp-developer | python-pro | hooks.json, prompt_capture.py, filters/ |
| Phase 4: Worktree | Migrate worktree-manager scripts | cli-developer | devops-engineer | worktree/scripts/, config.json |
| Phase 5: Templates | Create enhanced artifact templates | documentation-engineer | prompt-engineer | templates/*.md with Agent fields |
| Phase 6: Integration | Wire everything together, test | test-automator | code-reviewer | Working plugin, installation verified |

---

## Agent Recommendations

### By Task Type

| Task Type | Primary Agent | Alternatives | Notes |
|-----------|--------------|--------------|-------|
| Plugin manifest | mcp-developer | cli-developer | MCP/plugin API expertise |
| Command prompts | prompt-engineer | documentation-engineer | Directive language |
| Python hooks | python-pro | mcp-developer | Hook implementation |
| Bash scripts | cli-developer | devops-engineer | Shell scripting |
| Templates | documentation-engineer | technical-writer | Structured docs |
| Testing | test-automator | qa-expert | Manual verification |
| Code review | code-reviewer | security-auditor | Quality gate |

### Parallel Execution Groups

| Group | Tasks | Agents | Rationale |
|-------|-------|--------|-----------|
| PG-1 | 1.1, 1.2 | mcp-developer, documentation-engineer | Independent: manifest vs README |
| PG-2 | 2.1, 2.2, 2.3 | prompt-engineer (x3) | Independent: spec, wt, migrate commands |
| PG-3 | 3.1, 3.2 | python-pro, mcp-developer | Independent: filters vs hook registration |
| PG-4 | 4.1, 4.2 | cli-developer (x2) | Independent: scripts vs config |
| PG-5 | 5.1, 5.2 | documentation-engineer, prompt-engineer | Independent: base templates vs enhanced |
| Sequential | 6.1 → 6.2 | test-automator → code-reviewer | Depends: test before review |

---

## Phase 1: Scaffold

**Goal**: Create plugin directory structure and manifest
**Prerequisites**: None
**Lead Agent**: mcp-developer
**Parallel Agents**: documentation-engineer

### Tasks

#### Task 1.1: Create Plugin Manifest
- **Description**: Create `.claude-plugin/plugin.json` with correct schema for hooks and commands registration
- **Estimated Effort**: 30 minutes
- **Dependencies**: None
- **Agent**: mcp-developer
- **Parallel Group**: PG-1
- **Acceptance Criteria**:
  - [x] `.claude-plugin/plugin.json` exists with valid schema
  - [x] `hooks` field points to `./hooks/hooks.json`
  - [x] `commands` field points to `./commands`
  - [x] Metadata (name, version, description) complete
- **Notes**: Reference claude-code-guide for exact schema

#### Task 1.2: Create Plugin README and Structure
- **Description**: Create directory structure and README with installation instructions
- **Estimated Effort**: 30 minutes
- **Dependencies**: None
- **Agent**: documentation-engineer
- **Parallel Group**: PG-1
- **Acceptance Criteria**:
  - [x] All directories created (commands/, hooks/, filters/, worktree/, templates/)
  - [x] README.md with overview, installation, usage
  - [x] CHANGELOG.md initialized
  - [x] LICENSE file (MIT)
- **Notes**: Include worktree-manager attribution

### Phase 1 Deliverables
- [x] Plugin scaffold with all directories
- [x] Valid plugin.json manifest
- [x] README with installation instructions

### Phase 1 Exit Criteria
- [x] Plugin directory structure matches ARCHITECTURE.md
- [x] Manifest validates against Claude Code schema

---

## Phase 2: Commands

**Goal**: Migrate and enhance all commands from /arch:* to /cs:*
**Prerequisites**: Phase 1 complete
**Lead Agent**: prompt-engineer
**Parallel Agents**: documentation-engineer

### Tasks

#### Task 2.1: Migrate Spec Commands (/cs:p, /cs:i, /cs:s, /cs:c, /cs:log)
- **Description**: Copy and transform commands/arch/*.md to commands/cs/*.md with:
  - Rename all `/arch:` references to `/cs:`
  - Change `docs/architecture/` to `docs/spec/`
  - Add `<parallel_execution_directive>` block
  - Add `<sync_enforcement>` block to /cs:i
  - Update templates to include Agent fields
- **Estimated Effort**: 2 hours
- **Dependencies**: Task 1.1 (manifest)
- **Agent**: prompt-engineer
- **Parallel Group**: PG-2
- **Acceptance Criteria**:
  - [x] commands/cs/p.md - Planning with parallel directives
  - [x] commands/cs/i.md - Implementation with sync enforcement
  - [x] commands/cs/s.md - Status command
  - [x] commands/cs/c.md - Close-out command
  - [x] commands/cs/log.md - Prompt toggle
  - [x] All references updated from /arch: to /cs:
  - [x] All paths updated from docs/architecture/ to docs/spec/
- **Notes**: Largest task - contains most of the prompt engineering

#### Task 2.2: Create Worktree Commands (/cs:wt:*)
- **Description**: Create new commands that wrap worktree scripts
  - /cs:wt:create - Delegates to worktree creation workflow
  - /cs:wt:status - Delegates to status.sh
  - /cs:wt:cleanup - Delegates to cleanup.sh
- **Estimated Effort**: 1 hour
- **Dependencies**: Task 1.1 (manifest)
- **Agent**: prompt-engineer
- **Parallel Group**: PG-2
- **Acceptance Criteria**:
  - [x] commands/cs/wt/create.md - Create worktrees with prompts
  - [x] commands/cs/wt/status.md - Show worktree status
  - [x] commands/cs/wt/cleanup.md - Clean up worktrees
  - [x] Commands reference ${CLAUDE_PLUGIN_ROOT}/worktree/scripts/
  - [x] Skill trigger phrases documented
- **Notes**: Commands are wrappers around existing scripts

#### Task 2.3: Create Migration Command (/cs:migrate)
- **Description**: Create command that moves docs/architecture/ to docs/spec/ and updates references
- **Estimated Effort**: 45 minutes
- **Dependencies**: Task 1.1 (manifest)
- **Agent**: prompt-engineer
- **Parallel Group**: PG-2
- **Acceptance Criteria**:
  - [x] commands/cs/migrate.md created
  - [x] Moves active/ and completed/ directories
  - [x] Updates CLAUDE.md references
  - [x] Reports migration summary
  - [x] Handles case where already migrated
- **Notes**: One-time migration, idempotent

### Phase 2 Deliverables
- [x] 9 command files in commands/cs/
- [x] All commands functional
- [x] Parallel execution directives embedded

### Phase 2 Exit Criteria
- [x] All /cs:* commands appear in /help
- [x] Commands reference correct paths (docs/spec/)

---

## Phase 3: Hooks

**Goal**: Implement prompt capture as standalone plugin hook
**Prerequisites**: Phase 1 complete
**Lead Agent**: mcp-developer
**Parallel Agents**: python-pro

### Tasks

#### Task 3.1: Create Filter Pipeline
- **Description**: Migrate filter modules from ~/.claude/hooks/ to plugin
  - filters/__init__.py
  - filters/pipeline.py - Filter orchestration
  - filters/log_entry.py - LogEntry dataclass
  - filters/log_writer.py - JSON file operations
- **Estimated Effort**: 45 minutes
- **Dependencies**: Task 1.2 (structure)
- **Agent**: python-pro
- **Parallel Group**: PG-3
- **Acceptance Criteria**:
  - [x] All filter modules in filters/
  - [x] Imports work from hook script
  - [x] Secret detection functional
  - [x] Log writing to .prompt-log.json
- **Notes**: Mostly copy with path adjustments

#### Task 3.2: Create Hook Registration
- **Description**: Create hooks/hooks.json and hooks/prompt_capture.py
  - Register UserPromptSubmit hook
  - Hook script finds docs/spec/active/*/.prompt-log-enabled
  - Writes to .prompt-log.json in project directory
- **Estimated Effort**: 1 hour
- **Dependencies**: Task 3.1 (filters)
- **Agent**: mcp-developer
- **Parallel Group**: PG-3
- **Acceptance Criteria**:
  - [x] hooks/hooks.json with UserPromptSubmit registration
  - [x] hooks/prompt_capture.py with correct stdin/stdout handling
  - [x] Uses ${CLAUDE_PLUGIN_ROOT} for filter imports
  - [x] Checks docs/spec/active/ (not docs/architecture/)
  - [x] Graceful failure (always approves)
- **Notes**: Critical for prompt capture functionality

### Phase 3 Deliverables
- [x] hooks/hooks.json with hook registration
- [x] hooks/prompt_capture.py
- [x] filters/*.py modules

### Phase 3 Exit Criteria
- [x] Hook fires on UserPromptSubmit
- [x] Prompts logged to .prompt-log.json when enabled

---

## Phase 4: Worktree

**Goal**: Migrate worktree-manager scripts and config
**Prerequisites**: Phase 1 complete
**Lead Agent**: cli-developer
**Parallel Agents**: devops-engineer

### Tasks

#### Task 4.1: Migrate Worktree Scripts
- **Description**: Copy scripts from ~/.claude/skills/worktree-manager/scripts/ to plugin
  - Update paths to use ${CLAUDE_PLUGIN_ROOT}
  - Ensure scripts are executable
  - Maintain backward compatibility with registry
- **Estimated Effort**: 1 hour
- **Dependencies**: Task 1.2 (structure)
- **Agent**: cli-developer
- **Parallel Group**: PG-4
- **Acceptance Criteria**:
  - [x] worktree/scripts/allocate-ports.sh
  - [x] worktree/scripts/cleanup.sh
  - [x] worktree/scripts/launch-agent.sh
  - [x] worktree/scripts/register.sh
  - [x] worktree/scripts/release-ports.sh
  - [x] worktree/scripts/status.sh
  - [x] All scripts executable (chmod +x)
  - [x] Scripts work with existing ~/.claude/worktree-registry.json
- **Notes**: Scripts should work identically to originals

#### Task 4.2: Migrate Worktree Config and Docs
- **Description**: Copy config.json and create SKILL.md documentation
  - Include default configuration
  - Document trigger phrases
  - Attribution to original worktree-manager
- **Estimated Effort**: 30 minutes
- **Dependencies**: Task 1.2 (structure)
- **Agent**: documentation-engineer
- **Parallel Group**: PG-4
- **Acceptance Criteria**:
  - [x] worktree/config.json with defaults
  - [x] worktree/SKILL.md with trigger phrases
  - [x] Attribution to original skill
  - [x] templates/worktree.json for project config
- **Notes**: SKILL.md enables natural language triggers

### Phase 4 Deliverables
- [x] All worktree scripts migrated
- [x] Configuration and documentation complete

### Phase 4 Exit Criteria
- [x] Scripts execute without errors
- [x] Config matches original functionality

---

## Phase 5: Templates

**Goal**: Create enhanced artifact templates with parallel agent support
**Prerequisites**: Phase 2 complete
**Lead Agent**: documentation-engineer
**Parallel Agents**: prompt-engineer

### Tasks

#### Task 5.1: Create Base Templates
- **Description**: Create standard project artifact templates
  - README.md with frontmatter
  - REQUIREMENTS.md
  - ARCHITECTURE.md
  - DECISIONS.md
  - RESEARCH_NOTES.md
  - CHANGELOG.md
  - RETROSPECTIVE.md
- **Estimated Effort**: 1 hour
- **Dependencies**: Phase 2 (commands define template usage)
- **Agent**: documentation-engineer
- **Parallel Group**: PG-5
- **Acceptance Criteria**:
  - [x] All 7 base templates created
  - [x] Frontmatter with project_id, status fields
  - [x] Consistent structure across templates
- **Notes**: Based on existing arch templates

#### Task 5.2: Create Enhanced Templates
- **Description**: Create IMPLEMENTATION_PLAN.md and PROGRESS.md with Agent fields
  - Phase Summary with Lead Agent, Parallel Agents
  - Task template with Agent, Parallel Group fields
  - Agent Recommendations section
  - PROGRESS.md with Agent column
- **Estimated Effort**: 1 hour
- **Dependencies**: Phase 2 (commands define template usage)
- **Agent**: prompt-engineer
- **Parallel Group**: PG-5
- **Acceptance Criteria**:
  - [x] IMPLEMENTATION_PLAN.md with all Agent fields
  - [x] PROGRESS.md with Agent tracking
  - [x] Parallel Execution Groups table
  - [x] Agent Recommendations section
- **Notes**: These templates enable parallel agent orchestration

### Phase 5 Deliverables
- [x] 9 templates in templates/
- [x] Agent fields in relevant templates

### Phase 5 Exit Criteria
- [x] Templates match ARCHITECTURE.md specification
- [x] /cs:p generates projects with correct templates

---

## Phase 6: Integration

**Goal**: Wire everything together and verify functionality
**Prerequisites**: Phases 1-5 complete
**Lead Agent**: test-automator
**Parallel Agents**: code-reviewer

### Tasks

#### Task 6.1: Integration Testing
- **Description**: Test complete plugin functionality
  - Install plugin locally
  - Verify all commands work
  - Test prompt capture
  - Test worktree operations
  - Test migration command
- **Estimated Effort**: 1.5 hours
- **Dependencies**: All previous phases
- **Agent**: test-automator
- **Parallel Group**: Sequential (6.1 → 6.2)
- **Acceptance Criteria**:
  - [x] Plugin installs via claude plugins install
  - [x] All 9 /cs:* commands available
  - [x] /cs:p creates project in docs/spec/active/
  - [x] Prompt capture logs to .prompt-log.json
  - [x] Worktree commands work with registry
  - [x] /cs:migrate moves docs/architecture/ to docs/spec/
- **Notes**: Manual testing - observe behavior

#### Task 6.2: Code Review and Documentation
- **Description**: Final review of all plugin code and documentation
  - Check for security issues
  - Verify consistent style
  - Update README with final instructions
  - Ensure all attribution present
- **Estimated Effort**: 1 hour
- **Dependencies**: Task 6.1 (testing)
- **Agent**: code-reviewer
- **Parallel Group**: Sequential (after 6.1)
- **Acceptance Criteria**:
  - [x] No security vulnerabilities
  - [x] Consistent code style
  - [x] README complete and accurate
  - [x] Worktree-manager attribution present
  - [x] All paths use docs/spec/ not docs/architecture/
- **Notes**: Final quality gate

### Phase 6 Deliverables
- [x] Working, tested plugin
- [x] Complete documentation
- [x] Code review approval

### Phase 6 Exit Criteria
- [x] All acceptance criteria met
- [x] Plugin ready for use

---

## Dependency Graph

```
Phase 1 (Scaffold):
  Task 1.1 (manifest) ──┐
                        ├──► Phase 2, Phase 3, Phase 4
  Task 1.2 (structure) ─┘

Phase 2 (Commands) - PARALLEL after Phase 1:
  Task 2.1 (spec cmds) ──┐
  Task 2.2 (wt cmds)  ───┼──► Phase 5
  Task 2.3 (migrate)  ───┘

Phase 3 (Hooks) - PARALLEL after Phase 1:
  Task 3.1 (filters) ──┐
                       ├──► Phase 6
  Task 3.2 (hook reg) ─┘

Phase 4 (Worktree) - PARALLEL after Phase 1:
  Task 4.1 (scripts) ──┐
                       ├──► Phase 6
  Task 4.2 (config)  ──┘

Phase 5 (Templates) - PARALLEL after Phase 2:
  Task 5.1 (base) ─────┐
                       ├──► Phase 6
  Task 5.2 (enhanced) ─┘

Phase 6 (Integration) - SEQUENTIAL:
  Task 6.1 (test) ──► Task 6.2 (review) ──► DONE
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Hook doesn't fire | Medium | High | Test hook registration early in Phase 3 |
| Path references broken | Medium | Medium | Search/replace all paths systematically |
| Scripts not executable | Low | Medium | Add chmod +x in install instructions |
| Template formatting issues | Low | Low | Test template generation in Phase 6 |

---

## Testing Checklist

- [x] Plugin installs: `claude plugins install`
- [x] Commands available: `/cs:p`, `/cs:i`, `/cs:s`, `/cs:c`, `/cs:log`
- [x] Worktree commands: `/cs:wt:create`, `/cs:wt:status`, `/cs:wt:cleanup`
- [x] Migration: `/cs:migrate` moves docs correctly
- [x] Prompt capture: `/cs:log on` enables logging
- [x] Project creation: `/cs:p test` creates in docs/spec/active/
- [x] Agent fields: IMPLEMENTATION_PLAN.md has Agent column
- [x] Parallel directives: Commands contain enforcement blocks

---

## Launch Checklist

- [x] All 6 phases complete
- [x] All tests pass
- [x] Code review approved
- [x] README complete
- [x] Attribution present
- [x] Ready for local installation

---

## Post-Launch

- [x] Install plugin in main ~/.claude
- [x] Run /cs:migrate to move existing projects
- [x] Update CLAUDE.md documentation
- [x] Remove original /arch:* commands
- [x] Remove worktree-manager skill (superseded)
- [x] Archive this planning project via /cs:c
