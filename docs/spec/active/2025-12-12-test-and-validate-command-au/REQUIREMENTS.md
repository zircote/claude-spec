---
document_type: requirements
project_id: SPEC-2025-12-12-002
version: 1.0.0
last_updated: 2025-12-12T20:00:00Z
status: draft
---

# CS Plugin Test & Validation Suite - Requirements

## Executive Summary

This project validates that all `/cs` plugin commands function as advertised, identifies and fixes bugs, and establishes a test suite to prevent regressions. The validation covers 9 commands, prompt logging infrastructure, and the analyzer pipeline.

## Problem Statement

### The Problem
The CS plugin has accumulated inconsistencies and bugs over time:
- Template variable substitution failures (e.g., `{FEATURES}_RETROSPECTIVE.md`)
- Missing analyzer scripts preventing interaction analysis in retrospectives
- Malformed configuration files (hooks.json nested structure)
- Inconsistent file naming (`.prompt-log.json` vs `PROMPT_LOG.json`)
- Broken references to non-existent scripts

### Impact
Users lose confidence in the tooling when commands behave inconsistently. The advertised features don't work, leading to frustration and abandonment.

### Current State
Several bugs have been identified and fixed during initial analysis. A comprehensive test suite is needed to validate all functionality.

## Advertised Capabilities Inventory

### Core Commands

| Command | Description | Tested |
|---------|-------------|--------|
| `/cs:p` | Strategic project planning with Socratic elicitation | [ ] |
| `/cs:i` | Implementation progress tracking with PROGRESS.md | [ ] |
| `/cs:s` | Project status and portfolio management | [ ] |
| `/cs:c` | Project close-out with retrospective generation | [ ] |
| `/cs:log` | Prompt logging control (on/off/status/show) | [ ] |
| `/cs:migrate` | Legacy docs/architecture to docs/spec migration | [ ] |

### Worktree Commands

| Command | Description | Tested |
|---------|-------------|--------|
| `/cs:wt:create` | Create worktree with Claude agent | [ ] |
| `/cs:wt:status` | Show worktree status | [ ] |
| `/cs:wt:cleanup` | Clean up stale worktrees | [ ] |

### Infrastructure Components

| Component | Description | Tested |
|-----------|-------------|--------|
| Prompt capture hook | Intercepts UserPromptSubmit events | [ ] |
| Content filtering | Secret detection and redaction | [ ] |
| Log writer | Atomic NDJSON append with file locking | [ ] |
| Log analyzer | Generates interaction analysis for retrospectives | [ ] |
| Hook registration | hooks.json configuration | [ ] |

## Bugs Found & Fixed

### BUG-001: Malformed hooks.json (FIXED)
- **Location**: `plugins/cs/hooks/hooks.json`
- **Issue**: Extra nested `hooks` array prevented proper hook registration
- **Fix**: Flattened structure to correct format

### BUG-002: Wrong analyzer path in /cs:c (FIXED)
- **Location**: `plugins/cs/commands/c.md` line 60
- **Issue**: Referenced `~/.claude/hooks/analyzers/` which doesn't exist
- **Fix**: Changed to `${CLAUDE_PLUGIN_ROOT}/analyzers/analyze_cli.py`

### BUG-003: Missing analyzers directory (FIXED)
- **Location**: `plugins/cs/analyzers/`
- **Issue**: Directory and scripts didn't exist
- **Fix**: Created `analyze_cli.py` and `log_analyzer.py`

### BUG-004: Inconsistent log filename (FIXED)
- **Location**: Multiple files
- **Issue**: Mixed use of `PROMPT_LOG.json` and `.prompt-log.json`
- **Fix**: Standardized to `.prompt-log.json` everywhere

### BUG-005: FilterInfo attribute mismatch (FIXED)
- **Location**: `plugins/cs/analyzers/log_analyzer.py`
- **Issue**: Analyzer expected `profanity_count` but FilterInfo only has `secret_count`
- **Fix**: Removed profanity references, using secrets only

## Functional Requirements

### FR-001: /cs:p Command
**Priority**: P0
**Acceptance Criteria**:
- [ ] Creates project directory at `docs/spec/active/[YYYY-MM-DD]-[slug]/`
- [ ] Generates README.md with correct frontmatter and project ID
- [ ] Generates CHANGELOG.md with creation entry
- [ ] Creates `.prompt-log-enabled` marker when initialized
- [ ] Detects and warns about potential project collisions
- [ ] Updates CLAUDE.md with active project entry
- [ ] Handles worktree creation when on protected branch

### FR-002: /cs:i Command
**Priority**: P0
**Acceptance Criteria**:
- [ ] Creates/updates PROGRESS.md with task status
- [ ] Syncs checkbox state to IMPLEMENTATION_PLAN.md
- [ ] Updates README.md progress percentage
- [ ] Tracks divergences from original plan
- [ ] Persists state across Claude sessions

### FR-003: /cs:s Command
**Priority**: P1
**Acceptance Criteria**:
- [ ] Lists all active projects with status
- [ ] Shows project details when project-id provided
- [ ] Identifies expired plans with `--expired`
- [ ] Performs cleanup with `--cleanup`

### FR-004: /cs:c Command
**Priority**: P0
**Acceptance Criteria**:
- [ ] Generates RETROSPECTIVE.md with correct template
- [ ] Includes interaction analysis when logging was enabled
- [ ] Moves project to `docs/spec/completed/`
- [ ] Updates CLAUDE.md (removes from active, adds to completed)
- [ ] Removes `.prompt-log-enabled` marker
- [ ] Preserves `.prompt-log.json` in archive

### FR-005: /cs:log Command
**Priority**: P1
**Acceptance Criteria**:
- [ ] `on` creates `.prompt-log-enabled` marker
- [ ] `off` removes marker
- [ ] `status` shows current logging state and log size
- [ ] `show` displays recent log entries formatted

### FR-006: Prompt Capture Hook
**Priority**: P0
**Acceptance Criteria**:
- [ ] Captures all user prompts when logging enabled
- [ ] Filters secrets (AWS keys, API tokens, etc.)
- [ ] Truncates content over 50KB
- [ ] Uses atomic file locking for concurrent safety
- [ ] Never blocks user prompts (fail-open)
- [ ] Writes to `.prompt-log.json` in correct project directory

### FR-007: Log Analyzer
**Priority**: P1
**Acceptance Criteria**:
- [ ] Parses `.prompt-log.json` correctly
- [ ] Calculates session statistics
- [ ] Generates markdown interaction analysis
- [ ] Provides JSON output with `--format json`
- [ ] Provides text metrics with `--metrics-only`

## Non-Functional Requirements

### NFR-001: Configuration Consistency
All configuration files must use consistent naming and structure.

### NFR-002: Error Handling
Commands must fail gracefully with helpful error messages.

### NFR-003: Documentation Accuracy
Documentation must match actual behavior.

## Test Plan

### Unit Tests
- [ ] FilterInfo serialization/deserialization
- [ ] LogEntry creation and JSON conversion
- [ ] Secret detection regex patterns
- [ ] Log analyzer calculations

### Integration Tests
- [ ] Hook captures prompts correctly
- [ ] Analyzer processes real log files
- [ ] Close-out command includes interaction analysis

### End-to-End Tests
- [ ] Full project lifecycle: /cs:p → /cs:i → /cs:c
- [ ] Prompt logging through entire workflow

## Success Criteria

1. All P0 requirements pass acceptance criteria
2. All identified bugs are fixed
3. Automated test suite exists and passes
4. Validation checklist documents all tested functionality
5. No regressions introduced by fixes
