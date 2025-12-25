---
document_type: implementation_plan
project_id: SPEC-2025-12-25-001
version: 1.0.0
last_updated: 2025-12-25T18:45:00Z
status: draft
---

# Implement Command UX Improvements - Implementation Plan

## Overview

This plan covers two related features:
1. **Checkbox Sync Engine** for `/claude-spec:implement` (Issue #25)
2. **Argument Schema System** for `/claude-spec:plan` and `/claude-spec:implement`

## Phase Summary

| Phase | Description | Key Deliverables |
|-------|-------------|------------------|
| Phase 1: Checkbox Sync | Document sync algorithm in implement.md | Regex patterns, algorithm documentation |
| Phase 2: Argument Schema | Define extended YAML schema for arguments | Schema definition, validation rules |
| Phase 3: Help Generator | Dynamic --help from schema | Generated help output, deprecate hardcoded |
| Phase 4: Validation & Errors | Implement suggestion engine | Error messages with "Did you mean..." |
| Phase 5: Testing & Docs | Verify and document | Test cases, CLAUDE.md updates |

---

## Phase 1: Checkbox Sync Engine
**Goal**: Document and implement real-time checkbox sync in `/claude-spec:implement`

### Task 1.1: Document Task ID Regex Pattern
- **Description**: Add explicit regex pattern for matching task IDs in PROGRESS.md
- **Files**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Pattern documented: `^\[([x ])\]\s+(\d+\.\d+)\s+(.*)$`
  - [ ] Examples provided for each capture group
  - [ ] Edge cases documented (multi-digit phases, special characters)

### Task 1.2: Document IMPLEMENTATION_PLAN.md Task Heading Pattern
- **Description**: Add regex for finding task sections in IMPLEMENTATION_PLAN.md
- **Files**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Pattern documented: `^####\s+Task\s+(\d+\.\d+):\s+(.*)$`
  - [ ] Explain how to correlate with PROGRESS.md task IDs

### Task 1.3: Document Acceptance Criteria Section Discovery
- **Description**: Add algorithm for locating acceptance criteria under task headings
- **Files**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Algorithm steps documented in pseudocode
  - [ ] Pattern for checkbox lines: `^(\s+-\s+)\[([ x])\]\s+(.*)$`
  - [ ] Termination conditions documented (next heading or blank line)

### Task 1.4: Document Atomic Write Protocol
- **Description**: Specify safe file modification process with backup
- **Files**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Backup creation step documented
  - [ ] Atomic rename strategy explained
  - [ ] Rollback procedure on failure documented

### Task 1.5: Add Sync Output Format
- **Description**: Define output message format after sync completes
- **Files**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Format: "Updated N checkboxes in IMPLEMENTATION_PLAN.md"
  - [ ] Warning format for missing tasks defined
  - [ ] Example output block added

### Phase 1 Deliverables
- [ ] Updated Phase 5 section in commands/implement.md with all patterns
- [ ] Algorithm documentation with pseudocode
- [ ] Sync output examples

---

## Phase 2: Argument Schema Definition
**Goal**: Create extended YAML schema for argument metadata

### Task 2.1: Define Schema Structure
- **Description**: Create YAML schema specification for argument-hint
- **Files**: New section in commands/plan.md, commands/implement.md
- **Acceptance Criteria**:
  - [ ] Schema supports: positional args, flags, types, descriptions, examples
  - [ ] Required vs optional args distinguished
  - [ ] Pattern validation supported for string args

### Task 2.2: Update /plan Frontmatter
- **Description**: Convert plan.md to use extended argument-hint schema
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] New schema replaces single-line argument-hint
  - [ ] All existing flags documented (--inline, --no-worktree, --no-branch)
  - [ ] Positional project-seed documented with examples

### Task 2.3: Update /implement Frontmatter
- **Description**: Convert implement.md to use extended argument-hint schema
- **Files**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Schema documents project-ref positional arg
  - [ ] Pattern for SPEC-ID format included
  - [ ] Examples of valid project references

### Task 2.4: Define Backward Compatibility Rules
- **Description**: Ensure old single-line format continues working
- **Files**: Commands documentation
- **Acceptance Criteria**:
  - [ ] Both formats documented as valid
  - [ ] Upgrade path from old to new format explained
  - [ ] No breaking changes for existing commands

### Phase 2 Deliverables
- [ ] Schema specification document
- [ ] Updated frontmatter in plan.md and implement.md
- [ ] Backward compatibility documentation

---

## Phase 3: Dynamic Help Generator
**Goal**: Generate --help output from argument schema instead of hardcoded blocks

### Task 3.1: Document Help Generation Algorithm
- **Description**: Specify how to construct man-page output from schema
- **Files**: Commands documentation section
- **Acceptance Criteria**:
  - [ ] Algorithm produces NAME, SYNOPSIS, DESCRIPTION sections
  - [ ] ARGUMENTS section generated from positional args
  - [ ] OPTIONS section generated from flags
  - [ ] EXAMPLES section includes schema examples

### Task 3.2: Update /plan Help Block
- **Description**: Replace hardcoded help with schema-driven generation instructions
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] `<help_output>` block references schema generation
  - [ ] Output format matches current man-page style
  - [ ] All arguments documented in output

### Task 3.3: Update /implement Help Block
- **Description**: Replace hardcoded help in implement.md
- **Files**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Help output generated from schema
  - [ ] Project reference format explained in help
  - [ ] Examples section includes realistic examples

### Phase 3 Deliverables
- [ ] Help generation algorithm documented
- [ ] Updated help blocks in plan.md and implement.md
- [ ] Generated help matches expected format

---

## Phase 4: Validation and Error Messages
**Goal**: Implement argument validation with helpful suggestions

### Task 4.1: Document Validation Algorithm
- **Description**: Specify how arguments are validated against schema
- **Files**: Commands documentation
- **Acceptance Criteria**:
  - [ ] Type checking documented (boolean flags, string positionals)
  - [ ] Pattern validation for string args
  - [ ] Required arg checking

### Task 4.2: Document Suggestion Algorithm
- **Description**: Specify Levenshtein-based typo suggestions
- **Files**: Commands documentation
- **Acceptance Criteria**:
  - [ ] Levenshtein distance threshold documented (≤3)
  - [ ] Suggestion format: "Did you mean '--inline'?"
  - [ ] Multiple suggestions handling (show closest)

### Task 4.3: Add Validation to /plan
- **Description**: Add validation check in plan.md before execution
- **Files**: `commands/plan.md`
- **Acceptance Criteria**:
  - [ ] Unknown flags produce error + suggestion
  - [ ] Invalid project-seed format produces error
  - [ ] Error output includes help hint

### Task 4.4: Add Validation to /implement
- **Description**: Add validation check in implement.md before execution
- **Files**: `commands/implement.md`
- **Acceptance Criteria**:
  - [ ] Unknown flags produce error + suggestion
  - [ ] Invalid project-ref format produces error
  - [ ] Missing project produces helpful message

### Phase 4 Deliverables
- [ ] Validation algorithm documentation
- [ ] Suggestion algorithm documentation
- [ ] Validation logic in plan.md and implement.md

---

## Phase 5: Testing and Documentation
**Goal**: Verify implementation and update project documentation

### Task 5.1: Add Test Cases for Checkbox Sync
- **Description**: Document test scenarios for sync engine
- **Files**: Test documentation or inline in implement.md
- **Acceptance Criteria**:
  - [ ] Test: Task in PROGRESS.md, found in IMPLEMENTATION_PLAN.md → sync
  - [ ] Test: Task in PROGRESS.md, NOT in IMPLEMENTATION_PLAN.md → warning
  - [ ] Test: Missing acceptance criteria section → info message
  - [ ] Test: Partial completion scenarios

### Task 5.2: Add Test Cases for Argument Validation
- **Description**: Document test scenarios for argument handling
- **Files**: Test documentation
- **Acceptance Criteria**:
  - [ ] Test: Valid args → proceed
  - [ ] Test: Unknown flag → error + suggestion
  - [ ] Test: Typo within 3 chars → suggest correct flag
  - [ ] Test: Typo beyond 3 chars → no suggestion

### Task 5.3: Update CLAUDE.md
- **Description**: Add new features to project documentation
- **Files**: `CLAUDE.md`
- **Acceptance Criteria**:
  - [ ] Checkbox sync behavior documented
  - [ ] New argument-hint schema referenced
  - [ ] Help output format noted

### Task 5.4: Update Plugin README
- **Description**: Document user-facing changes
- **Files**: `.claude-plugin/README.md` or root README
- **Acceptance Criteria**:
  - [ ] Checkbox sync feature listed
  - [ ] Improved argument hints mentioned
  - [ ] Better error messages noted

### Phase 5 Deliverables
- [ ] Test case documentation
- [ ] Updated CLAUDE.md
- [ ] Updated README

---

## Dependency Graph

```
Phase 1 (Checkbox Sync)
  Task 1.1 (regex) ──────────────────────────────────┐
  Task 1.2 (heading regex) ──────────────────────────┤
  Task 1.3 (AC discovery) ───────────────────────────┼──▶ Task 1.5 (output format)
  Task 1.4 (atomic write) ───────────────────────────┘

Phase 2 (Argument Schema) ─── can run in parallel with Phase 1 ───
  Task 2.1 (schema def) ──┬──▶ Task 2.2 (/plan frontmatter)
                          └──▶ Task 2.3 (/implement frontmatter)
  Task 2.4 (backward compat) ── depends on 2.1

Phase 3 (Help Generator) ─── depends on Phase 2 ───
  Task 3.1 (algorithm) ──┬──▶ Task 3.2 (/plan help)
                         └──▶ Task 3.3 (/implement help)

Phase 4 (Validation) ─── depends on Phase 2 ───
  Task 4.1 (validation algo) ──┬──▶ Task 4.3 (/plan validation)
  Task 4.2 (suggestion algo) ──┘    Task 4.4 (/implement validation)

Phase 5 (Testing & Docs) ─── depends on Phases 1-4 ───
  Task 5.1 (sync tests) ── depends on Phase 1
  Task 5.2 (arg tests) ── depends on Phase 4
  Task 5.3, 5.4 ── depends on all phases
```

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| Regex fails on edge cases | Task 5.1 - extensive test cases | 5 |
| YAML parse errors | Task 2.4 - backward compatibility | 2 |
| Help output formatting issues | Task 3.2/3.3 - verify format | 3 |
| Suggestion performance | Cache common typos in schema | 4 |

## Testing Checklist

- [ ] Unit tests for task ID regex extraction
- [ ] Unit tests for acceptance criteria checkbox pattern
- [ ] Unit tests for Levenshtein distance calculation
- [ ] Integration test for full sync cycle
- [ ] Integration test for --help generation
- [ ] Edge case tests per Task 5.1 and 5.2

## Documentation Tasks

- [ ] Update Phase 5 in commands/implement.md
- [ ] Update frontmatter in commands/plan.md
- [ ] Update frontmatter in commands/implement.md
- [ ] Update CLAUDE.md with new features
- [ ] Update README with user-facing changes

## Launch Checklist

- [ ] All phases complete
- [ ] Test cases pass
- [ ] Documentation updated
- [ ] Backward compatibility verified
- [ ] No regression in existing commands
