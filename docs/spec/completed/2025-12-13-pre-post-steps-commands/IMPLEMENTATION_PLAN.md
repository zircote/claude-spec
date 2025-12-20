---
document_type: implementation_plan
project_id: SPEC-2025-12-13-001
version: 1.0.0
last_updated: 2025-12-13T00:00:00Z
status: draft
---

# Pre and Post Steps for cs:* Commands - Implementation Plan

## Overview

This plan implements a hook-based pre/post step system for the claude-spec plugin across 4 phases: Foundation (bug fixes + infrastructure), Core Hooks, Step Modules, and Integration/Testing.

## Phase Summary

| Phase | Key Deliverables |
|-------|------------------|
| Phase 1: Foundation | Bug fixes, hook registration, config schema |
| Phase 2: Core Hooks | SessionStart, UserPromptSubmit, Stop hooks |
| Phase 3: Step Modules | Context loader, security reviewer, post-step actions |
| Phase 4: Integration | End-to-end testing, documentation, release |

---

## Phase 1: Foundation

**Goal**: Fix blocking bugs and establish infrastructure for hook system.

**Prerequisites**: None

### Task 1.1: Fix Hook Registration in plugin.json

- **Description**: Add hooks reference to plugin.json so Claude Code discovers and registers hooks
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] plugin.json includes hooks field
  - [ ] UserPromptSubmit hook fires (verified via test prompt)
  - [ ] No errors in stderr

**Implementation**:
```json
// .claude-plugin/plugin.json
{
  "name": "cs",
  "version": "1.1.0",
  "description": "Project specification and implementation lifecycle management with pre/post steps",
  "hooks": "./hooks/hooks.json"
}
```

### Task 1.2: Fix iTerm2-tab Launch Script Bug

- **Description**: Differentiate iterm2 (new window) from iterm2-tab (new tab) behavior
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] `iterm2` config creates new window
  - [ ] `iterm2-tab` config creates new tab in current window
  - [ ] Both execute Claude command correctly

**Implementation**: Update `skills/worktree-manager/scripts/launch-agent.sh` lines 182-206.

### Task 1.3: Create Lifecycle Config Schema

- **Description**: Define and validate configuration schema for pre/post steps
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] Schema documented in config.template.json
  - [ ] `get_lifecycle_config()` function added to lib/config.sh
  - [ ] Python config loader created

**Files to create/modify**:
- `skills/worktree-manager/config.template.json` - Add lifecycle section
- `skills/worktree-manager/scripts/lib/config.sh` - Add lifecycle helpers
- `hooks/lib/config_loader.py` - Python config reader

### Task 1.4: Create Steps Module Structure

- **Description**: Set up the steps/ directory with __init__.py and base class
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] `steps/__init__.py` exports all step modules
  - [ ] `steps/base.py` defines StepResult dataclass
  - [ ] Directory structure matches architecture doc

**Files to create**:
```
plugins/cs/steps/
├── __init__.py
├── base.py          # StepResult, StepError classes
├── context_loader.py
├── security_reviewer.py
├── log_archiver.py
├── marker_cleaner.py
└── retrospective_gen.py
```

### Task 1.5: Enforce Strict Phase Separation in Command Files (CRITICAL)

- **Description**: Modify p.md and i.md to enforce that `/cs:p` NEVER implements and `/cs:i` is the ONLY implementation entry point
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] p.md includes `<post_approval_halt>` section that HALTS after spec approval
  - [ ] p.md explicitly states "Run `/cs:i` to implement" after approval
  - [ ] p.md does NOT call ExitPlanMode with implementation intent
  - [ ] i.md includes `<implementation_gate>` section requiring explicit user confirmation
  - [ ] i.md is documented as the ONLY implementation entry point

**Files to modify**:
- `commands/p.md` - Add post_approval_halt section, remove any auto-implement logic
- `commands/i.md` - Add implementation_gate section with explicit confirmation

**Implementation for p.md**:
```markdown
<post_approval_halt>
## MANDATORY HALT AFTER APPROVAL

When user approves the specification (e.g., "approve", "looks good", "proceed"):

1. **DO NOT** call ExitPlanMode with intent to implement
2. **DO NOT** start any implementation tasks
3. **DO NOT** create or modify code files

**REQUIRED RESPONSE:**

✅ Specification approved and complete.

📁 Artifacts: `docs/spec/active/{project}/`

⏭️ **Next step**: Run `/cs:i {project-slug}` when ready to implement.

**HALT HERE. Do not proceed further.**
</post_approval_halt>
```

**Implementation for i.md**:
```markdown
<implementation_gate>
## Implementation Authorization Check

This command (`/cs:i`) is the ONLY authorized entry point for implementation.

Before proceeding:
1. Verify spec exists in `docs/spec/active/` or `docs/spec/approved/`
2. Verify spec status is `approved` or `in-review`
3. Confirm with user: "Ready to begin implementation of {project}?"

Only after explicit user confirmation, proceed with implementation.
</implementation_gate>
```

### Phase 1 Deliverables

- [x] Hook registration working
- [x] iTerm2-tab bug fixed
- [x] Config schema defined
- [x] Steps directory structure created
- [x] **Strict phase separation enforced in p.md and i.md**

### Phase 1 Exit Criteria

- [x] `prompt_capture.py` hook fires on user prompts
- [x] Test config loads without errors
- [x] Steps module imports without errors
- [x] **p.md HALTS after spec approval (does not auto-implement)**
- [x] **i.md requires explicit user confirmation before implementing**

---

## Phase 2: Core Hooks

**Goal**: Implement the three main hooks that orchestrate pre/post steps.

**Prerequisites**: Phase 1 complete

### Task 2.1: Implement SessionStart Hook

- **Description**: Hook that loads project context on session start
- **Dependencies**: Task 1.3, Task 1.4
- **Acceptance Criteria**:
  - [ ] Hook fires on session start
  - [ ] Context output appears in Claude's memory
  - [ ] Respects config (can disable context types)
  - [ ] Fails open on errors

**Files to create**:
- `hooks/session_start.py`

**Implementation outline**:
```python
def main():
    input_data = read_input()
    cwd = input_data.get("cwd", "")

    # Check if this is a cs project
    if not is_cs_project(cwd):
        return  # Silent exit, no context needed

    # Load context based on config
    config = load_lifecycle_config(cwd)
    context_parts = []

    if config.get("loadContext", {}).get("claudeMd", True):
        context_parts.append(load_claude_md(cwd))

    if config.get("loadContext", {}).get("gitState", True):
        context_parts.append(load_git_state(cwd))

    if config.get("loadContext", {}).get("projectStructure", True):
        context_parts.append(load_project_structure(cwd))

    # Output context (stdout is added to Claude's context)
    print("\n".join(context_parts))
```

### Task 2.2: Implement Command Detector Hook

- **Description**: UserPromptSubmit hook that detects /cs:* commands and triggers pre-steps
- **Dependencies**: Task 1.3, Task 1.4
- **Acceptance Criteria**:
  - [ ] Detects `/cs:p`, `/cs:c`, `/cs:i`, `/cs:s` commands
  - [ ] Triggers security review for `/cs:c`
  - [ ] Stores command in session state file
  - [ ] Always returns approve decision

**Files to create**:
- `hooks/command_detector.py`

**Implementation outline**:
```python
COMMAND_PATTERNS = {
    r"^/cs:p\b": "cs:p",
    r"^/cs:c\b": "cs:c",
    r"^/cs:i\b": "cs:i",
    r"^/cs:s\b": "cs:s",
    r"^/cs:log\b": "cs:log",
}

def main():
    input_data = read_input()
    prompt = input_data.get("prompt", "")
    cwd = input_data.get("cwd", "")

    command = detect_command(prompt)
    if command:
        save_session_state(cwd, {"command": command})
        run_pre_steps(cwd, command)

    write_output({"decision": "approve"})
```

### Task 2.3: Implement Post-Command Hook

- **Description**: Stop hook that executes post-steps after command completes
- **Dependencies**: Task 1.3, Task 1.4, Task 2.2
- **Acceptance Criteria**:
  - [ ] Reads command from session state
  - [ ] Executes appropriate post-steps
  - [ ] Cleans up session state file
  - [ ] Returns continue: false to signal completion

**Files to create**:
- `hooks/post_command.py`

**Implementation outline**:
```python
def main():
    input_data = read_input()
    cwd = input_data.get("cwd", "")

    state = load_session_state(cwd)
    command = state.get("command")

    if command:
        run_post_steps(cwd, command)
        cleanup_session_state(cwd)

    write_output({"continue": False})
```

### Task 2.4: Update hooks.json with All Hooks

- **Description**: Register all three hooks in hooks.json
- **Dependencies**: Tasks 2.1, 2.2, 2.3
- **Acceptance Criteria**:
  - [ ] All hooks registered
  - [ ] Correct timeouts set
  - [ ] Order preserved (detector before prompt_capture)

### Phase 2 Deliverables

- [x] session_start.py hook
- [x] command_detector.py hook
- [x] post_command.py hook
- [x] Updated hooks.json

### Phase 2 Exit Criteria

- [x] SessionStart fires and injects context
- [x] Command detector identifies /cs:c
- [x] Post-command hook executes after Stop

---

## Phase 3: Step Modules

**Goal**: Implement individual step modules for pre and post actions.

**Prerequisites**: Phase 2 complete

### Task 3.1: Implement Context Loader Step

- **Description**: Load CLAUDE.md, git state, and project structure
- **Dependencies**: Task 1.4
- **Acceptance Criteria**:
  - [ ] Loads ~/.claude/CLAUDE.md and ./CLAUDE.md
  - [ ] Extracts current branch, recent commits, uncommitted changes
  - [ ] Generates project structure summary
  - [ ] Handles missing files gracefully

**Files to create/modify**:
- `steps/context_loader.py`

### Task 3.2: Implement Security Reviewer Step

- **Description**: Run security audit before /cs:c close-out
- **Dependencies**: Task 1.4
- **Acceptance Criteria**:
  - [ ] Invokes security-auditor agent or semgrep/bandit
  - [ ] Reports findings in user-friendly format
  - [ ] Respects timeout configuration
  - [ ] Fails open (warns but doesn't block)

**Files to create/modify**:
- `steps/security_reviewer.py`

### Task 3.3: Implement Log Archiver Step

- **Description**: Archive .prompt-log.json to completed project directory
- **Dependencies**: Task 1.4
- **Acceptance Criteria**:
  - [ ] Moves file to docs/spec/completed/{project}/
  - [ ] Creates directory if needed
  - [ ] Handles missing log file gracefully

**Files to create/modify**:
- `steps/log_archiver.py`

### Task 3.4: Implement Marker Cleaner Step

- **Description**: Remove .prompt-log-enabled and other temp files
- **Dependencies**: Task 1.4
- **Acceptance Criteria**:
  - [ ] Removes .prompt-log-enabled
  - [ ] Removes .cs-session-state.json
  - [ ] Logs what was cleaned

**Files to create/modify**:
- `steps/marker_cleaner.py`

### Task 3.5: Implement Retrospective Generator Step

- **Description**: Generate RETROSPECTIVE.md from prompt log analysis
- **Dependencies**: Task 1.4, existing analyzers/
- **Acceptance Criteria**:
  - [ ] Uses existing analyze_cli.py
  - [ ] Creates RETROSPECTIVE.md template
  - [ ] Populates with project data and analysis

**Files to create/modify**:
- `steps/retrospective_gen.py`

### Phase 3 Deliverables

- [x] context_loader.py
- [x] security_reviewer.py
- [x] log_archiver.py
- [x] marker_cleaner.py
- [x] retrospective_gen.py

### Phase 3 Exit Criteria

- [ ] All step modules pass unit tests
- [x] Steps integrate with hooks
- [ ] Manual testing shows expected behavior

---

## Phase 4: Integration & Testing

**Goal**: End-to-end integration, comprehensive testing, and documentation.

**Prerequisites**: Phase 3 complete

### Task 4.1: Write Unit Tests for All Hooks

- **Description**: Test each hook in isolation
- **Dependencies**: Phase 2
- **Acceptance Criteria**:
  - [ ] >90% coverage for hook code
  - [ ] All edge cases tested
  - [ ] Mocking patterns established

**Files to create**:
- `tests/test_session_start.py`
- `tests/test_command_detector.py`
- `tests/test_post_command.py`

### Task 4.2: Write Unit Tests for All Steps

- **Description**: Test each step module in isolation
- **Dependencies**: Phase 3
- **Acceptance Criteria**:
  - [ ] >90% coverage for step code
  - [ ] File system operations mocked
  - [ ] Error handling tested

**Files to create**:
- `tests/test_context_loader.py`
- `tests/test_security_reviewer.py`
- `tests/test_log_archiver.py`
- `tests/test_marker_cleaner.py`
- `tests/test_retrospective_gen.py`

### Task 4.3: Integration Testing

- **Description**: Test full workflow with real Claude Code session
- **Dependencies**: Tasks 4.1, 4.2
- **Acceptance Criteria**:
  - [ ] SessionStart context appears in Claude's first response
  - [ ] /cs:c triggers security review
  - [ ] Post-steps execute and create expected files

### Task 4.4: Update Documentation

- **Description**: Update CLAUDE.md, README, and command docs
- **Dependencies**: All implementation complete
- **Acceptance Criteria**:
  - [ ] CLAUDE.md documents new hooks
  - [ ] README explains pre/post steps
  - [ ] Config options documented

**Files to update**:
- `CLAUDE.md`
- `README.md` (if exists)
- `commands/*.md` (reference new behavior)

### Task 4.5: Update CHANGELOG and Version

- **Description**: Prepare for release
- **Dependencies**: Task 4.4
- **Acceptance Criteria**:
  - [ ] CHANGELOG.md updated
  - [ ] Version bumped to 1.1.0
  - [ ] plugin.json version updated

### Phase 4 Deliverables

- [ ] Complete test suite
- [ ] Updated documentation
- [ ] Release-ready plugin

### Phase 4 Exit Criteria

- [ ] All tests pass
- [ ] `make ci` succeeds
- [ ] Manual E2E test successful

---

## Dependency Graph

```
Phase 1: Foundation
  Task 1.1 (hook reg) ─────┐
  Task 1.2 (iterm fix) ────┤
  Task 1.3 (config) ───────┼───▶ Phase 2
  Task 1.4 (steps dir) ────┘

Phase 2: Core Hooks
  Task 2.1 (session) ──────┐
  Task 2.2 (detector) ─────┼───▶ Phase 3
  Task 2.3 (post-cmd) ─────┤
  Task 2.4 (hooks.json) ───┘

Phase 3: Step Modules
  Task 3.1 (context) ──────┐
  Task 3.2 (security) ─────┤
  Task 3.3 (archiver) ─────┼───▶ Phase 4
  Task 3.4 (cleaner) ──────┤
  Task 3.5 (retro) ────────┘

Phase 4: Integration
  Task 4.1 (hook tests) ───┐
  Task 4.2 (step tests) ───┤
  Task 4.3 (E2E tests) ────┼───▶ Release
  Task 4.4 (docs) ─────────┤
  Task 4.5 (version) ──────┘
```

## Testing Checklist

- [ ] Unit tests for session_start.py
- [ ] Unit tests for command_detector.py
- [ ] Unit tests for post_command.py
- [ ] Unit tests for context_loader.py
- [ ] Unit tests for security_reviewer.py
- [ ] Unit tests for log_archiver.py
- [ ] Unit tests for marker_cleaner.py
- [ ] Unit tests for retrospective_gen.py
- [ ] Integration test: full /cs:c workflow
- [ ] E2E test: new session context loading
- [ ] E2E test: security review before close-out

## Documentation Tasks

- [ ] Update CLAUDE.md with hook documentation
- [ ] Update config.template.json with lifecycle options
- [ ] Add lifecycle configuration examples
- [ ] Document troubleshooting for hook issues

## Launch Checklist

- [ ] All tests passing (`make ci`)
- [ ] Documentation complete
- [ ] Version bumped in plugin.json
- [ ] CHANGELOG updated
- [ ] Manual E2E test successful
- [ ] PR created and reviewed
