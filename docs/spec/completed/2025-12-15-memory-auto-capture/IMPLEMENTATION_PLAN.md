---
document_type: implementation_plan
project_id: SPEC-2025-12-15-001
version: 1.0.0
last_updated: 2025-12-15T20:15:00Z
status: draft
---

# Memory Auto-Capture Implementation - Implementation Plan

## Overview

This plan implements automatic memory capture during `/cs:*` command execution in four phases:
1. Foundation: Add missing capture methods and wire configuration
2. Core: Integrate auto-capture into command execution flows
3. Polish: Add summary display and graceful degradation
4. Documentation: Update command files and user guides

## Phase Summary

| Phase | Name | Key Deliverables |
|-------|------|------------------|
| Phase 1 | Foundation | 3 new capture methods, validation helper, constants |
| Phase 2 | Core Integration | Auto-capture in /cs:p, /cs:i, /cs:c, /cs:review |
| Phase 3 | Polish | Capture summary display, error handling |
| Phase 4 | Documentation | Update command files, USER_GUIDE.md |

---

## Phase 1: Foundation

**Goal**: Add infrastructure for auto-capture (methods, validation, constants)

**Prerequisites**: None

### Task 1.1: Add Review Constants to config.py

- **Description**: Add category, severity, outcome, and pattern type constants
- **Files**: `memory/config.py`
- **Acceptance Criteria**:
  - [x] Add `REVIEW_CATEGORIES` frozenset
  - [x] Add `REVIEW_SEVERITIES` frozenset
  - [x] Add `RETROSPECTIVE_OUTCOMES` frozenset
  - [x] Add `PATTERN_TYPES` frozenset

### Task 1.2: Add capture_review() Method

- **Description**: Implement specialized capture method for code review findings
- **Files**: `memory/capture.py`
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - [x] Method accepts category, severity, file_path, line, description parameters
  - [x] Validates category against REVIEW_CATEGORIES
  - [x] Validates severity against REVIEW_SEVERITIES
  - [x] Formats structured content with ## sections
  - [x] Returns CaptureResult with indexed=True on success
  - [x] Unit tests cover all parameters and validation

### Task 1.3: Add capture_retrospective() Method

- **Description**: Implement specialized capture method for project retrospectives
- **Files**: `memory/capture.py`
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - [x] Method accepts outcome, what_went_well, what_to_improve, key_learnings, metrics
  - [x] Validates outcome against RETROSPECTIVE_OUTCOMES
  - [x] Formats structured content with ## sections and bullet lists
  - [x] Returns CaptureResult with indexed=True on success
  - [x] Unit tests cover all parameters and validation

### Task 1.4: Add capture_pattern() Method

- **Description**: Implement specialized capture method for patterns/anti-patterns
- **Files**: `memory/capture.py`
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - [x] Method accepts pattern_type, description, context, applicability, evidence
  - [x] Validates pattern_type against PATTERN_TYPES
  - [x] Formats structured content with ## sections
  - [x] Returns CaptureResult with indexed=True on success
  - [x] Unit tests cover all parameters and validation

### Task 1.5: Wire AUTO_CAPTURE_NAMESPACES Validation

- **Description**: Import and use AUTO_CAPTURE_NAMESPACES for validation
- **Files**: `memory/capture.py`, `memory/config.py`
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] Import AUTO_CAPTURE_NAMESPACES in capture.py
  - [x] Add `validate_auto_capture_namespace()` helper function
  - [x] Function returns True if namespace in AUTO_CAPTURE_NAMESPACES
  - [x] Function raises CaptureError if namespace not in NAMESPACES
  - [x] Unit tests cover valid, invalid, and disabled namespace cases

### Task 1.6: Add CaptureAccumulator Model

- **Description**: Create dataclass for tracking captures during command execution
- **Files**: `memory/models.py`
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] CaptureAccumulator dataclass with captures list
  - [x] add() method to append CaptureResult
  - [x] summary() method to generate display string
  - [x] count property returns number of captures
  - [x] by_namespace property returns dict of counts
  - [x] Unit tests cover all methods and properties

### Phase 1 Deliverables

- [x] Three new capture methods in capture.py
- [x] Four new constant sets in config.py
- [x] Validation helper for AUTO_CAPTURE_NAMESPACES
- [x] CaptureAccumulator model
- [x] 100% test coverage for new code

### Phase 1 Exit Criteria

- [x] `make ci` passes with new code
- [x] All new methods have docstrings and type hints
- [x] No regressions in existing capture functionality

---

## Phase 2: Core Integration

**Goal**: Integrate auto-capture triggers into command execution flows

**Prerequisites**: Phase 1 complete

### Task 2.1: Design Auto-Capture Integration Pattern

- **Description**: Create reusable pattern for command markdown capture integration
- **Files**: Design document / code comments
- **Dependencies**: Phase 1
- **Acceptance Criteria**:
  - [ ] Define how commands invoke capture (pseudo-code convention)
  - [ ] Document error handling approach (fail-open)
  - [ ] Define accumulator usage pattern
  - [ ] Create template for capture trigger sections

### Task 2.2: Integrate Auto-Capture in /cs:p

- **Description**: Add capture triggers at phase transitions in planning command
- **Files**: `commands/p.md`
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - [ ] Capture inception after scaffold commit (namespace: inception)
  - [ ] Capture elicitation after each clarification round (namespace: elicitation)
  - [ ] Capture research findings after research phase (namespace: research)
  - [ ] Capture each ADR during architecture phase (use capture_decision)
  - [ ] Display capture summary at command end
  - [ ] Graceful degradation if capture fails

### Task 2.3: Integrate Auto-Capture in /cs:i

- **Description**: Add capture triggers for implementation events
- **Files**: `commands/i.md`
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - [ ] Capture progress on task completion (use capture_progress)
  - [ ] Capture blocker when user mentions blockers (use capture_blocker)
  - [ ] Capture learning when user mentions insights (use capture_learning)
  - [ ] Capture deviation when divergence logged (use capture_pattern)
  - [ ] Display capture summary at session end
  - [ ] Graceful degradation if capture fails

### Task 2.4: Integrate Auto-Capture in /cs:c

- **Description**: Add capture triggers for close-out events
- **Files**: `commands/c.md`
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - [ ] Capture retrospective summary (use capture_retrospective)
  - [ ] Extract and capture key learnings (use capture_learning)
  - [ ] Capture success patterns (use capture_pattern)
  - [ ] Capture anti-patterns (use capture_pattern)
  - [ ] Display capture summary at command end
  - [ ] Graceful degradation if capture fails

### Task 2.5: Integrate Auto-Capture in /cs:review

- **Description**: Add capture triggers for review findings
- **Files**: `commands/review.md`
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - [ ] Capture each finding in --capture mode (use capture_review)
  - [ ] Capture pattern when 2+ similar findings detected
  - [ ] Display capture summary after review
  - [ ] Graceful degradation if capture fails

### Phase 2 Deliverables

- [ ] Auto-capture integration in all four commands
- [ ] Consistent capture patterns across commands
- [ ] Fail-open error handling

### Phase 2 Exit Criteria

- [ ] Manual testing of each command with captures
- [ ] Capture summary displays correctly
- [ ] Commands continue even if capture fails

---

## Phase 3: Polish

**Goal**: Improve UX with capture summaries and robust error handling

**Prerequisites**: Phase 2 complete

### Task 3.1: Implement Capture Summary Display

- **Description**: Create consistent capture summary format for all commands
- **Files**: Design template in command files
- **Dependencies**: Phase 2
- **Acceptance Criteria**:
  - [ ] Summary shows count by namespace
  - [ ] Summary shows memory IDs for each capture
  - [ ] Summary shows warnings if any captures failed
  - [ ] Format is consistent across all commands

### Task 3.2: Implement Graceful Degradation

- **Description**: Ensure commands continue even when capture fails
- **Files**: Command files (p.md, i.md, c.md, review.md)
- **Dependencies**: Phase 2
- **Acceptance Criteria**:
  - [ ] Embedding service failure doesn't block command
  - [ ] Index service failure doesn't block command
  - [ ] Git notes failure doesn't block command
  - [ ] Warnings are logged and displayed
  - [ ] Partial success is clearly communicated

### Task 3.3: Add Capture Configuration (Optional)

- **Description**: Allow users to disable auto-capture if desired
- **Files**: `memory/config.py`, command files
- **Dependencies**: Phase 2
- **Acceptance Criteria**:
  - [ ] Environment variable CS_AUTO_CAPTURE_ENABLED (default: true)
  - [ ] Commands check config before capturing
  - [ ] Skip message when disabled

### Phase 3 Deliverables

- [ ] Polished capture summary display
- [ ] Robust error handling
- [ ] Optional disable mechanism

### Phase 3 Exit Criteria

- [ ] Manual testing with simulated failures
- [ ] Summary format is clear and informative
- [ ] No command failures due to capture issues

---

## Phase 4: Documentation

**Goal**: Update documentation to accurately reflect auto-capture functionality

**Prerequisites**: Phase 3 complete

### Task 4.1: Update USER_GUIDE.md

- **Description**: Document auto-capture behavior for end users
- **Files**: `memory/USER_GUIDE.md`
- **Dependencies**: Phase 3
- **Acceptance Criteria**:
  - [ ] Explain what auto-capture does
  - [ ] List which commands have auto-capture
  - [ ] Document capture summary format
  - [ ] Explain how to disable (if implemented)
  - [ ] Add examples of captured memories

### Task 4.2: Update DEVELOPER_GUIDE.md

- **Description**: Document capture methods for developers
- **Files**: `memory/DEVELOPER_GUIDE.md`
- **Dependencies**: Phase 3
- **Acceptance Criteria**:
  - [ ] Document capture_review() API
  - [ ] Document capture_retrospective() API
  - [ ] Document capture_pattern() API
  - [ ] Document CaptureAccumulator usage
  - [ ] Document AUTO_CAPTURE_NAMESPACES validation

### Task 4.3: Clean Up Command File Pseudo-Code

- **Description**: Replace non-functional pseudo-code with working integration
- **Files**: Command files (p.md, i.md, c.md, review.md)
- **Dependencies**: Phase 3
- **Acceptance Criteria**:
  - [ ] Remove or update misleading comments
  - [ ] Ensure pseudo-code matches actual behavior
  - [ ] Add notes about what is auto-captured
  - [ ] Remove references to non-existent methods

### Task 4.4: Update CLAUDE.md

- **Description**: Document auto-capture in project CLAUDE.md
- **Files**: Root CLAUDE.md
- **Dependencies**: Phase 3
- **Acceptance Criteria**:
  - [ ] Add auto-capture section to cs-memory documentation
  - [ ] List commands with auto-capture
  - [ ] Document any configuration options

### Phase 4 Deliverables

- [ ] Updated USER_GUIDE.md
- [ ] Updated DEVELOPER_GUIDE.md
- [ ] Cleaned up command files
- [ ] Updated CLAUDE.md

### Phase 4 Exit Criteria

- [ ] Documentation matches implementation
- [ ] No references to non-existent functionality
- [ ] Clear explanation of auto-capture behavior

---

## Dependency Graph

```
Phase 1: Foundation
  Task 1.1 ──────┬──> Task 1.2 ──┐
                 ├──> Task 1.3 ──┼──> Phase 2
                 └──> Task 1.4 ──┘
  Task 1.5 ──────────────────────────> Phase 2
  Task 1.6 ──────────────────────────> Phase 2

Phase 2: Core Integration
  Task 2.1 ──┬──> Task 2.2 ──┐
             ├──> Task 2.3 ──┼──> Phase 3
             ├──> Task 2.4 ──┤
             └──> Task 2.5 ──┘

Phase 3: Polish
  Task 3.1 ──┬──> Task 3.2 ──> Phase 4
             └──> Task 3.3 ──> Phase 4

Phase 4: Documentation
  Task 4.1 ──┐
  Task 4.2 ──┼──> DONE
  Task 4.3 ──┤
  Task 4.4 ──┘
```

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| Capture volume overwhelms index | Add content length validation | Phase 1 |
| Hook failures break commands | Fail-open design in all captures | Phase 2 |
| Duplicate captures | ID uniqueness via timestamp | Phase 1 (existing) |
| Performance degradation | Monitor capture time, log warnings | Phase 3 |

## Testing Checklist

- [ ] Unit tests for capture_review()
- [ ] Unit tests for capture_retrospective()
- [ ] Unit tests for capture_pattern()
- [ ] Unit tests for validate_auto_capture_namespace()
- [ ] Unit tests for CaptureAccumulator
- [ ] Integration test: /cs:p with auto-capture
- [ ] Integration test: /cs:i with auto-capture
- [ ] Integration test: /cs:c with auto-capture
- [ ] Integration test: /cs:review with auto-capture
- [ ] Error handling test: capture failure
- [ ] Error handling test: embedding failure
- [ ] Error handling test: index failure

## Documentation Tasks

- [ ] Update USER_GUIDE.md with auto-capture section
- [ ] Update DEVELOPER_GUIDE.md with new methods
- [ ] Update command files with accurate pseudo-code
- [ ] Update CLAUDE.md with auto-capture documentation

## Launch Checklist

- [ ] All tests passing
- [ ] Documentation complete
- [ ] Manual testing of each command
- [ ] Capture summary displays correctly
- [ ] Graceful degradation verified
- [ ] `make ci` passes

## Post-Launch

- [ ] Monitor for issues during real usage
- [ ] Gather feedback on capture granularity
- [ ] Consider batch capture optimization (P2)
- [ ] Consider verbose preview mode (P2)
