---
document_type: implementation_plan
project_id: SPEC-2025-12-17-001
version: 1.0.0
last_updated: 2025-12-17T17:15:00Z
status: draft
---

# Draft PR Creation for /cs:p Workflow - Implementation Plan

## Overview

This document outlines the phased implementation plan for adding GitHub draft PR creation to the `/cs:p` planning workflow. The implementation is structured into 4 phases with clear dependencies and verification gates.

## Phase Summary

| Phase | Name | Tasks | Dependencies |
|-------|------|-------|--------------|
| 1 | Foundation | 5 | None |
| 2 | PR Manager Step | 6 | Phase 1 |
| 3 | Lifecycle Integration | 5 | Phase 2 |
| 4 | Testing & Polish | 5 | Phase 3 |

**Total Tasks**: 21

---

## Phase 1: Foundation (Core Infrastructure)

**Objective**: Establish the infrastructure needed for PR operations.

### Tasks

- [ ] **1.1** Create `pr_manager.py` module skeleton in `plugins/cs/steps/`
  - Create file with class definition extending `BaseStep`
  - Implement `name = "pr-manager"` class attribute
  - Add placeholder `execute()` method returning `StepResult.ok()`
  - Add module-level `run(cwd, config)` function
  - **Verification**: Module imports without error

- [ ] **1.2** Add `pr-manager` to step whitelist
  - Edit `plugins/cs/hooks/lib/step_runner.py`
  - Add `"pr-manager": "pr_manager"` to `STEP_MODULES` dict
  - **Verification**: `get_available_steps()` includes "pr-manager"

- [ ] **1.3** Implement `_check_gh_available()` helper method
  - Check `gh --version` for installation
  - Check `gh auth status` for authentication
  - Return tuple `(available: bool, reason: str)`
  - Handle `FileNotFoundError`, `TimeoutExpired`
  - **Verification**: Returns appropriate values for installed/uninstalled scenarios

- [ ] **1.4** Implement `validate()` method with graceful degradation
  - Call `_check_gh_available()`
  - Store skip reason if unavailable (do not fail validation)
  - Always return `True` (fail-open)
  - **Verification**: Validation passes when gh unavailable

- [ ] **1.5** Add unit tests for foundation
  - Test module import
  - Test whitelist registration
  - Test gh availability check (mocked)
  - Test graceful degradation
  - **Verification**: All tests pass, coverage > 90% for new code

### Phase 1 Deliverables

- `plugins/cs/steps/pr_manager.py` (skeleton)
- Updated `step_runner.py` with whitelist entry
- `tests/steps/test_pr_manager.py` (foundation tests)

---

## Phase 2: PR Manager Step (Core Operations)

**Objective**: Implement the core PR operations: create, update, ready.

**Dependencies**: Phase 1 complete

### Tasks

- [ ] **2.1** Implement `_create_draft_pr()` method
  - Build PR title from config template: `[WIP] {slug}: {project_name}`
  - Build PR body from spec README.md summary
  - Execute `gh pr create --draft --title "..." --body "..." --base <base_branch>`
  - Parse PR URL from stdout
  - Handle existing PR scenario (check `gh pr view` first)
  - **Verification**: Draft PR created in test repo

- [ ] **2.2** Implement `_store_pr_url()` method
  - Parse README.md YAML frontmatter
  - Add or update `draft_pr_url` field
  - Write back with preserved formatting
  - Use safe YAML library (ruamel.yaml or equivalent)
  - **Verification**: URL persisted in frontmatter

- [ ] **2.3** Implement `_update_pr_body()` method
  - Read current PR number from stored URL
  - Build updated body with phase progress checklist
  - Execute `gh pr edit <number> --body "..."`
  - **Verification**: PR body updated in test repo

- [ ] **2.4** Implement `_mark_pr_ready()` method
  - Read PR number from stored URL
  - Execute `gh pr ready <number>`
  - Execute `gh pr edit <number> --remove-label "work-in-progress"`
  - Optionally add reviewers: `gh pr edit <number> --add-reviewer <user>`
  - **Verification**: Draft converted to ready in test repo

- [ ] **2.5** Implement `_add_labels()` method
  - Accept list of labels from config
  - Execute `gh pr edit --add-label` for each label
  - Handle label-not-found gracefully
  - **Verification**: Labels applied to PR

- [ ] **2.6** Implement `execute()` method with operation dispatch
  - Read `operation` from config (default: "create")
  - Check for skip reason from validate()
  - Dispatch to appropriate method based on operation
  - Return `StepResult` with PR URL in data
  - **Verification**: All operations work end-to-end

### Phase 2 Deliverables

- Complete `pr_manager.py` with all operations
- Updated test file with operation tests

---

## Phase 3: Lifecycle Integration (Configuration & Hooks)

**Objective**: Integrate PR manager into the `/cs:p` and `/cs:c` lifecycle.

**Dependencies**: Phase 2 complete

### Tasks

- [ ] **3.1** Update template configuration
  - Edit `plugins/cs/skills/worktree-manager/config.template.json`
  - Add `pr-manager` postStep for `cs:p` command
  - Add `pr-manager` postStep for `cs:c` command (operation: "ready")
  - Include default labels, title format, base branch
  - **Verification**: Config loads without error

- [ ] **3.2** Create helper function for README frontmatter parsing
  - Implement `_parse_readme_frontmatter(path)` in pr_manager.py
  - Extract `project_name`, `slug`, `draft_pr_url` fields
  - Handle missing fields gracefully
  - **Verification**: Parses sample README correctly

- [ ] **3.3** Create helper function for PR body generation
  - Implement `_build_pr_body(spec_path)` in pr_manager.py
  - Include problem statement from README
  - Include phase checklist with status
  - Include links to spec documents
  - **Verification**: Generated body is well-formatted

- [ ] **3.4** Implement existing PR detection
  - Before `gh pr create`, check `gh pr view --json url`
  - If PR exists for branch, switch to update operation
  - Log clear message about detection
  - **Verification**: No duplicate PRs created

- [ ] **3.5** Add integration tests with lifecycle config
  - Test step execution via `run_step()`
  - Test config loading and option parsing
  - Test full /cs:p → /cs:c flow (mocked)
  - **Verification**: Integration tests pass

### Phase 3 Deliverables

- Updated `config.template.json`
- Helper functions in pr_manager.py
- Integration tests in `tests/hooks/test_pr_lifecycle.py`

---

## Phase 4: Testing & Polish (Quality & Documentation)

**Objective**: Ensure production readiness with comprehensive testing and documentation.

**Dependencies**: Phase 3 complete

### Tasks

- [ ] **4.1** Add edge case tests
  - Test network timeout handling
  - Test malformed gh output
  - Test missing README frontmatter
  - Test PR URL already exists in README
  - Test empty labels list
  - **Verification**: All edge cases handled gracefully

- [ ] **4.2** Add manual test script
  - Create `scripts/test_pr_manager.sh` for manual verification
  - Include steps to test with real GitHub repo
  - Document expected outcomes
  - **Verification**: Manual test passes in real environment

- [ ] **4.3** Update plugin documentation
  - Add PR manager section to `plugins/cs/CLAUDE.md`
  - Document configuration options
  - Document prerequisites (gh CLI)
  - **Verification**: Documentation accurate and complete

- [ ] **4.4** Update USER_GUIDE.md
  - Add section on draft PR workflow
  - Include screenshots or examples
  - Document troubleshooting tips
  - **Verification**: User guide updated

- [ ] **4.5** Run full CI validation
  - Run `make ci` in plugins/cs/
  - Ensure all checks pass: lint, typecheck, security, tests
  - Ensure coverage threshold met
  - **Verification**: CI green, coverage > 85%

### Phase 4 Deliverables

- Comprehensive test suite
- Manual test script
- Updated documentation
- CI passing

---

## Implementation Notes

### File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `plugins/cs/steps/pr_manager.py` | New | Main step module |
| `plugins/cs/hooks/lib/step_runner.py` | Modify | Add whitelist entry |
| `plugins/cs/skills/worktree-manager/config.template.json` | Modify | Add lifecycle config |
| `plugins/cs/CLAUDE.md` | Modify | Add documentation |
| `tests/steps/test_pr_manager.py` | New | Unit tests |
| `tests/hooks/test_pr_lifecycle.py` | New | Integration tests |
| `scripts/test_pr_manager.sh` | New | Manual test script |

### Dependencies (Python)

No new Python dependencies required. The implementation uses:
- `subprocess` (stdlib) for gh CLI execution
- `json` (stdlib) for output parsing
- `pathlib` (stdlib) for file operations
- Existing `steps.base` for BaseStep, StepResult

### Dependencies (External)

- **gh CLI** (optional): Version 2.x recommended
- **git**: Already required by plugin

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| gh CLI version incompatibility | Test with multiple versions; document minimum version |
| Network flakiness | Implement timeouts; use fail-open pattern |
| Race conditions on README update | Use atomic file writes |
| PR URL parsing errors | Validate URL format; handle edge cases |

### Rollback Plan

If issues discovered post-deployment:
1. Set `enabled: false` in lifecycle config
2. Step will be skipped, no PR operations attempted
3. Existing functionality unaffected

---

## Success Criteria

### Must Have (P0)

- [x] Spec documents created (REQUIREMENTS.md, ARCHITECTURE.md, IMPLEMENTATION_PLAN.md)
- [ ] Draft PR created after first artifact
- [ ] PR marked ready on /cs:c
- [ ] Graceful degradation when gh unavailable
- [ ] All tests passing

### Should Have (P1)

- [ ] PR body updated at phase transitions
- [ ] Labels applied: spec, work-in-progress
- [ ] Labels removed on completion

### Nice to Have (P2)

- [ ] Reviewer assignment on ready
- [ ] Issue linking via "Closes #N"
- [ ] Configurable base branch

---

## Verification Gates

Before proceeding to next phase, verify:

### Phase 1 → Phase 2
- [ ] `pr_manager.py` module imports successfully
- [ ] Step appears in `get_available_steps()` output
- [ ] `_check_gh_available()` returns correct values in both scenarios
- [ ] Foundation tests pass with >90% coverage

### Phase 2 → Phase 3
- [ ] `gh pr create --draft` succeeds in test repo
- [ ] PR URL stored in README frontmatter
- [ ] `gh pr ready` succeeds
- [ ] All operations handle errors gracefully

### Phase 3 → Phase 4
- [ ] Config template loads without error
- [ ] Step executes via lifecycle hooks
- [ ] No duplicate PRs created on re-run
- [ ] Integration tests pass

### Phase 4 → Complete
- [ ] `make ci` passes
- [ ] Coverage > 85%
- [ ] Documentation updated
- [ ] Manual test passes in real environment

---

## Appendix: Code Templates

### PR Manager Step Skeleton (Phase 1)

```python
"""
PR Manager Step - Creates and manages GitHub draft PRs for spec projects.

This step integrates with the gh CLI to create draft pull requests
at the start of planning (/cs:p) and convert them to ready on
completion (/cs:c).

Requirements:
    - gh CLI installed (optional - graceful degradation)
    - gh authenticated (gh auth login)
"""

from __future__ import annotations

import subprocess
from typing import Any

from .base import BaseStep, ErrorCode, StepResult


class PRManagerStep(BaseStep):
    """Manages GitHub draft PR operations for spec projects."""

    name = "pr-manager"

    def validate(self) -> bool:
        """Check gh CLI availability (non-blocking)."""
        available, reason = self._check_gh_available()
        if not available:
            self._skip_reason = reason
        return True  # Always pass - fail-open

    def execute(self) -> StepResult:
        """Execute the configured PR operation."""
        # TODO: Implement in Phase 2
        return StepResult.ok("PR manager placeholder")

    def _check_gh_available(self) -> tuple[bool, str]:
        """Check if gh CLI is available and authenticated."""
        try:
            # Check installation
            subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                timeout=5,
                check=True
            )
            # Check authentication
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return (False, "gh not authenticated")
            return (True, "")
        except FileNotFoundError:
            return (False, "gh CLI not installed")
        except subprocess.TimeoutExpired:
            return (False, "gh check timed out")
        except subprocess.CalledProcessError:
            return (False, "gh version check failed")


def run(cwd: str, config: dict[str, Any] | None = None) -> StepResult:
    """Module-level run function for hook integration."""
    step = PRManagerStep(cwd, config)
    return step.run()
```

### Configuration Template Addition (Phase 3)

```json
{
  "lifecycle": {
    "commands": {
      "cs:p": {
        "postSteps": [
          {
            "name": "pr-manager",
            "enabled": true,
            "operation": "create",
            "labels": ["spec", "work-in-progress"],
            "title_format": "[WIP] {slug}: {project_name}",
            "base_branch": "main"
          }
        ]
      },
      "cs:c": {
        "postSteps": [
          {
            "name": "pr-manager",
            "enabled": true,
            "operation": "ready",
            "remove_labels": ["work-in-progress"],
            "reviewers": []
          }
        ]
      }
    }
  }
}
```
