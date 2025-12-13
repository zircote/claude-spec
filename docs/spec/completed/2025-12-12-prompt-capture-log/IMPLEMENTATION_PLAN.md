---
document_type: implementation_plan
project_id: ARCH-2025-12-12-002
version: 1.0.0
last_updated: 2025-12-12T22:15:00Z
status: completed
estimated_effort: 25 tasks across 4 phases
---

# Prompt Capture Log - Implementation Plan

## Overview

This plan breaks down the implementation into four phases: Foundation (hook infrastructure), Core (filter pipeline and logging), Integration (/arch:* commands), and Polish (testing and documentation). Each task includes clear acceptance criteria and dependencies.

## Phase Summary

| Phase | Key Deliverables |
|-------|------------------|
| Phase 1: Foundation | Hook skeleton, project structure, basic toggle |
| Phase 2: Core | Filter pipeline, log writer, entry schema |
| Phase 3: Integration | /arch:log command, /arch:c analyzer, retrospective section |
| Phase 4: Polish | Test suite, documentation, edge case handling |

---

## Phase 1: Foundation

**Goal**: Establish hook infrastructure and project structure

### Tasks

#### Task 1.1: Create hook directory structure

- **Description**: Set up the directory layout for hook files, filters, and analyzers
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] `~/.claude/hooks/` directory exists
  - [x] `~/.claude/hooks/filters/` subdirectory created
  - [x] `~/.claude/hooks/analyzers/` subdirectory created
  - [x] `__init__.py` files in place for Python imports

#### Task 1.2: Create prompt_capture_hook.py skeleton

- **Description**: Implement basic hook that reads stdin, returns pass-through response
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - [x] Hook reads JSON from stdin
  - [x] Hook outputs valid JSON to stdout
  - [x] Hook returns `{"decision": "approve"}` (pass-through)
  - [x] Hook handles malformed input gracefully

#### Task 1.3: Register hook in hookify hooks.json

- **Description**: Add UserPromptSubmit hook registration
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [x] Hook registered in `~/.claude/plugins/cache/claude-code-plugins/hookify/*/hooks/hooks.json`
  - [x] Hook fires on UserPromptSubmit event
  - [x] Hook timeout set to 5000ms

#### Task 1.4: Implement toggle check function

- **Description**: Create function to check if logging is enabled for a project
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [x] `is_logging_enabled(cwd)` function implemented
  - [x] Returns True if `.prompt-log-enabled` exists in project dir
  - [x] Returns False if file doesn't exist
  - [x] Handles missing project directory gracefully

#### Task 1.5: Implement arch context detection

- **Description**: Detect if current session is within /arch:* command context
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [x] `is_arch_context(input_data)` function implemented
  - [x] Detects /arch:p, /arch:i, /arch:s, /arch:c contexts
  - [x] Returns False for non-arch sessions
  - [x] Uses transcript_path or prompt content for detection

### Phase 1 Deliverables

- [x] Hook directory structure created
- [x] Basic hook skeleton working
- [x] Hook registered and firing
- [x] Toggle and context detection functions

### Phase 1 Exit Criteria

- [x] `echo '{"user_prompt":"test"}' | python3 ~/.claude/hooks/prompt_capture_hook.py` returns valid JSON
- [x] Hook appears in Claude Code hook logs

---

## Phase 2: Core Implementation

**Goal**: Implement filter pipeline and log writing

### Tasks

#### Task 2.1: Create profanity word list

- **Description**: Compile profanity word list for filtering
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] `filters/profanity_words.txt` created
  - [x] Contains common profanity terms (50+ words)
  - [x] One word per line, lowercase
  - [x] Includes common variations

#### Task 2.2: Implement profanity filter module

- **Description**: Create profanity detection and replacement
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - [x] `filters/profanity.py` module created
  - [x] `detect_profanity(text)` returns list of matches
  - [x] `filter_profanity(text)` replaces with `[FILTERED]`
  - [x] Case-insensitive matching
  - [x] Word boundary detection (avoid false positives)

#### Task 2.3: Implement secret patterns module

- **Description**: Create regex patterns for secret detection
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] `filters/secrets.py` module created
  - [x] Patterns for: AWS keys, GitHub tokens, API keys, passwords
  - [x] `detect_secrets(text)` returns list of (type, match)
  - [x] `filter_secrets(text)` replaces with `[SECRET:type]`
  - [x] Patterns pre-compiled for performance

#### Task 2.4: Implement filter pipeline

- **Description**: Chain filters together in correct order
- **Dependencies**: Task 2.2, Task 2.3
- **Acceptance Criteria**:
  - [x] `filters/pipeline.py` module created
  - [x] `filter_pipeline(text)` returns FilterResult
  - [x] Secrets filtered before profanity (avoid masking secrets as profanity)
  - [x] Returns original length, filtered text, counts

#### Task 2.5: Define log entry schema

- **Description**: Create dataclass for log entries
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] LogEntry dataclass defined
  - [x] Fields: timestamp, session_id, type, command, content, filter_applied, metadata
  - [x] `to_dict()` method for JSON serialization
  - [x] `from_dict()` class method for deserialization

#### Task 2.6: Implement log writer

- **Description**: Create atomic NDJSON append function
- **Dependencies**: Task 2.5
- **Acceptance Criteria**:
  - [x] `append_to_log(project_path, entry)` function
  - [x] Creates PROMPT_LOG.json if not exists
  - [x] Uses file locking for concurrent safety
  - [x] Appends single JSON line with newline
  - [x] Handles write errors gracefully

#### Task 2.7: Integrate filter and log in hook

- **Description**: Connect filter pipeline to hook and write logs
- **Dependencies**: Task 2.4, Task 2.6
- **Acceptance Criteria**:
  - [x] Hook calls filter_pipeline on user_prompt
  - [x] Hook builds LogEntry from input_data
  - [x] Hook calls append_to_log with filtered entry
  - [x] Hook returns success message in systemMessage

### Phase 2 Deliverables

- [x] Profanity filter module working
- [x] Secret detection module working
- [x] Filter pipeline chaining filters
- [x] Log writer with atomic append
- [x] Hook writing filtered logs

### Phase 2 Exit Criteria

- [x] Prompt with profanity logged with `[FILTERED]` replacement
- [x] Prompt with API key logged with `[SECRET:type]` replacement
- [x] PROMPT_LOG.json contains valid NDJSON entries

---

## Phase 3: Integration

**Goal**: Integrate with /arch:* commands and retrospective

### Tasks

#### Task 3.1: Create /arch:log command

- **Description**: Implement toggle command for logging control
- **Dependencies**: Phase 2 complete
- **Acceptance Criteria**:
  - [x] `~/.claude/commands/arch/log.md` created
  - [x] `/arch:log on` creates `.prompt-log-enabled` in project dir
  - [x] `/arch:log off` removes `.prompt-log-enabled`
  - [x] `/arch:log status` shows current state
  - [x] `/arch:log show` displays recent log entries

#### Task 3.2: Implement expanded prompt capture

- **Description**: Capture the full slash command expansion alongside user input
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [x] Detect when a slash command is being executed
  - [x] Log expanded prompt content with type "expanded_prompt"
  - [x] Link to user input via session_id
  - [x] Handle large expanded prompts (truncate if >50KB)

#### Task 3.3: Implement response summary capture

- **Description**: Generate and log summaries of Claude responses
- **Dependencies**: Task 2.6
- **Acceptance Criteria**:
  - [x] Hook captures response on subsequent prompt (via transcript)
  - [x] `summarize_response(text)` extracts key points
  - [x] Summary limited to 500 characters
  - [x] Logged with type "response_summary"

#### Task 3.4: Implement log analyzer

- **Description**: Create analysis module for retrospective generation
- **Dependencies**: Task 2.6
- **Acceptance Criteria**:
  - [x] `analyzers/log_analyzer.py` module created
  - [x] `analyze_log(log_path)` returns LogAnalysis
  - [x] Calculates: total prompts, session count, avg length, clarification count
  - [x] Identifies sessions with high clarification (>10 questions)

#### Task 3.5: Implement retrospective section generator

- **Description**: Generate markdown for RETROSPECTIVE.md
- **Dependencies**: Task 3.4
- **Acceptance Criteria**:
  - [x] `generate_interaction_analysis(analysis)` returns markdown
  - [x] Includes metrics table
  - [x] Includes insights (high clarification warning, etc.)
  - [x] Includes recommendations for improvement

#### Task 3.6: Integrate analyzer with /arch:c

- **Description**: Modify /arch:c to call analyzer and update retrospective
- **Dependencies**: Task 3.5
- **Acceptance Criteria**:
  - [x] /arch:c checks for PROMPT_LOG.json
  - [x] If exists, runs analyzer
  - [x] Appends "## Interaction Analysis" to RETROSPECTIVE.md
  - [x] Disables logging (removes .prompt-log-enabled)
  - [x] Moves PROMPT_LOG.json to completed/

#### Task 3.7: Handle log file lifecycle

- **Description**: Ensure log files move with project through lifecycle
- **Dependencies**: Task 3.6
- **Acceptance Criteria**:
  - [x] PROMPT_LOG.json included in /arch:c archive
  - [x] .prompt-log-enabled removed at close-out
  - [x] Log preserved in completed/ directory

### Phase 3 Deliverables

- [x] /arch:log command functional
- [x] Expanded prompts captured
- [x] Response summaries captured
- [x] Log analyzer generating insights
- [x] /arch:c integration complete

### Phase 3 Exit Criteria

- [x] Full /arch:p session logged with all entry types
- [x] /arch:c generates Interaction Analysis section
- [x] PROMPT_LOG.json in completed/ directory

---

## Phase 4: Polish

**Goal**: Testing, documentation, and edge case handling

### Tasks

#### Task 4.1: Create filter test suite

- **Description**: Unit tests for profanity and secret filters
- **Dependencies**: Phase 2 complete
- **Acceptance Criteria**:
  - [x] Test file `tests/test_filters.py`
  - [x] Tests for each secret pattern (true positives)
  - [x] Tests for false positive avoidance
  - [x] Tests for profanity detection
  - [x] >80% coverage on filter modules

#### Task 4.2: Create hook integration tests

- **Description**: End-to-end tests for hook functionality
- **Dependencies**: Phase 3 complete
- **Acceptance Criteria**:
  - [x] Test file `tests/test_hook.py`
  - [x] Tests hook input/output format
  - [x] Tests toggle behavior
  - [x] Tests log file creation
  - [x] Tests filter application

#### Task 4.3: Create analyzer tests

- **Description**: Unit tests for log analysis
- **Dependencies**: Task 3.4
- **Acceptance Criteria**:
  - [x] Test file `tests/test_analyzer.py`
  - [x] Tests metric calculations
  - [x] Tests with sample log files
  - [x] Tests edge cases (empty log, single entry)

#### Task 4.4: Handle edge cases

- **Description**: Implement graceful handling for error scenarios
- **Dependencies**: Phase 3 complete
- **Acceptance Criteria**:
  - [x] Handles missing project directory
  - [x] Handles corrupted log file (skip bad lines)
  - [x] Handles very long prompts (truncate)
  - [x] Handles hook timeout (fail-open)
  - [x] Handles concurrent writes

#### Task 4.5: Update CLAUDE.md with logging guidance

- **Description**: Document logging feature in project instructions
- **Dependencies**: Phase 3 complete
- **Acceptance Criteria**:
  - [x] Add section on prompt logging to CLAUDE.md
  - [x] Document /arch:log commands
  - [x] Explain what is captured and filtered
  - [x] Note privacy considerations

#### Task 4.6: Final review and cleanup

- **Description**: Code review, cleanup, final testing
- **Dependencies**: All previous tasks
- **Acceptance Criteria**:
  - [x] All code follows existing style conventions
  - [x] No TODO comments left in code
  - [x] All tests passing
  - [x] Documentation complete
  - [x] Ready for merge to main

### Phase 4 Deliverables

- [x] Test suite with >80% coverage
- [x] Edge cases handled gracefully
- [x] Documentation updated
- [x] Code reviewed and clean

### Phase 4 Exit Criteria

- [x] All tests passing
- [x] Manual end-to-end test successful
- [x] Documentation reviewed

---

## Dependency Graph

```
Phase 1:
  Task 1.1 ──┬──► Task 1.2 ──┬──► Task 1.3
             │               │
             │               └──► Task 1.4
             │               │
             │               └──► Task 1.5
             │
             └───────────────────► Phase 2

Phase 2:
  Task 2.1 ──► Task 2.2 ──┐
                          │
  Task 2.3 ──────────────┼──► Task 2.4 ──► Task 2.7
                          │                    │
  Task 2.5 ──► Task 2.6 ──┘                    │
                                               │
                                               └──► Phase 3

Phase 3:
  Task 3.1 ──────────────────────────────────────┐
                                                  │
  Task 3.2 ──────────────────────────────────────┼──► Phase 4
                                                  │
  Task 3.3 ──────────────────────────────────────┤
                                                  │
  Task 3.4 ──► Task 3.5 ──► Task 3.6 ──► Task 3.7┘

Phase 4:
  Task 4.1 ──┐
             │
  Task 4.2 ──┼──► Task 4.4 ──► Task 4.6
             │          │
  Task 4.3 ──┘          ▼
                   Task 4.5
```

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| Hook latency affects UX | Performance testing in Task 4.2 | 4 |
| False positive secret detection | Comprehensive test suite in Task 4.1 | 4 |
| Hook breaks on Claude Code update | Version check in Task 4.4 | 4 |
| Sensitive data leaks | Multiple filter passes in Task 2.4 | 2 |

## Testing Checklist

- [x] Unit tests for filter modules (Task 4.1)
- [x] Integration tests for hook (Task 4.2)
- [x] Unit tests for analyzer (Task 4.3)
- [x] Manual end-to-end test (Task 4.6)
- [x] Performance validation (<100ms latency)

## Documentation Tasks

- [x] Update CLAUDE.md (Task 4.5)
- [x] Inline code documentation (throughout)
- [x] README for hooks directory (Task 4.6)

## Launch Checklist

- [x] All tests passing
- [x] Documentation complete
- [x] Code reviewed
- [x] Manual testing successful
- [x] Merged to main branch
- [x] Feature announced/documented

## Post-Launch

- [x] Monitor for hook errors (first week)
- [x] Gather feedback on filter accuracy
- [x] Collect sample retrospective analyses
- [x] Consider enhancements based on usage
