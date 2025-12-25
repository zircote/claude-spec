---
document_type: architecture
project_id: SPEC-2025-12-25-001
version: 1.0.0
last_updated: 2025-12-25T18:40:00Z
status: draft
---

# Implement Command UX Improvements - Technical Architecture

## System Overview

This feature enhances two aspects of claude-spec commands:

1. **Checkbox Sync Engine**: Real-time synchronization of task completion state between PROGRESS.md and IMPLEMENTATION_PLAN.md
2. **Argument Schema System**: Extended metadata for command arguments with dynamic help generation and validation

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Command Execution                            │
│                                                                      │
│  ┌──────────────────┐     ┌──────────────────┐                      │
│  │  Argument Parser │────▶│  Help Generator  │────▶ --help output   │
│  │                  │     │                  │                      │
│  │  - Schema loader │     │  - Man page fmt  │                      │
│  │  - Type validator│     │  - Example gen   │                      │
│  │  - Suggestion gen│     └──────────────────┘                      │
│  └────────┬─────────┘                                               │
│           │ valid args                                              │
│           ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    /claude-spec:implement                     │   │
│  │                                                               │   │
│  │  Phase 1-4: Task Execution                                    │   │
│  │           │                                                   │   │
│  │           ▼ task marked done                                  │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │              Checkbox Sync Engine                        │  │   │
│  │  │                                                          │  │   │
│  │  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │  │   │
│  │  │  │ Task Finder │───▶│ Checkbox    │───▶│ Atomic      │  │  │   │
│  │  │  │             │    │ Locator     │    │ Writer      │  │  │   │
│  │  │  │ - Regex     │    │             │    │             │  │  │   │
│  │  │  │   patterns  │    │ - AC section│    │ - Backup    │  │  │   │
│  │  │  │ - ID extract│    │   finder    │    │ - Verify    │  │  │   │
│  │  │  └─────────────┘    └─────────────┘    └─────────────┘  │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

                    Document Layer
  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
  │   PROGRESS.md   │  │ IMPLEMENTATION_ │  │   README.md     │
  │                 │  │ PLAN.md         │  │                 │
  │ Source of truth │  │                 │  │ Frontmatter     │
  │ for task status │◀─┤ Acceptance      │  │ sync            │
  │                 │  │ criteria boxes  │  │                 │
  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sync direction | PROGRESS.md → IMPLEMENTATION_PLAN.md | PROGRESS.md is source of truth |
| Sync trigger | Immediate on task update | Prevents drift, matches user expectations |
| Argument schema location | Command frontmatter (YAML) | Colocated with command, no external files |
| Help generation | Dynamic from schema | Single source of truth for arg docs |
| Validation approach | Levenshtein suggestions | Friendly UX, matches git/npm patterns |

## Component Design

### Component 1: Checkbox Sync Engine

**Purpose**: Synchronize task completion state from PROGRESS.md to IMPLEMENTATION_PLAN.md

**Responsibilities**:
- Parse PROGRESS.md for task status changes
- Locate corresponding task sections in IMPLEMENTATION_PLAN.md
- Update acceptance criteria checkboxes
- Verify sync completed correctly

**Interfaces**:
```
Input: Task ID (e.g., "2.3"), new status ("done"|"skipped"|"pending")
Output: List of files modified, checkboxes updated count
```

**Dependencies**: Read/Write tools, regex patterns

**Technology**: Bash patterns embedded in command markdown

#### Task Finder Sub-component

**Pattern Matching for Task IDs**:

```regex
# In PROGRESS.md - extract task ID and status
^\[([x ])\]\s+(\d+\.\d+)\s+(.*)$

# Groups:
# 1: Checkbox state (x or space)
# 2: Task ID (e.g., "1.2")
# 3: Task description
```

```regex
# In IMPLEMENTATION_PLAN.md - find task heading
^####\s+Task\s+(\d+\.\d+):\s+(.*)$

# Groups:
# 1: Task ID
# 2: Task title
```

#### Checkbox Locator Sub-component

**Algorithm for finding acceptance criteria**:

```
FUNCTION find_acceptance_criteria(file_content, task_id):
    1. Find line matching "#### Task {task_id}:"
    2. Start scanning from that line
    3. Look for "- **Acceptance Criteria**:" pattern
    4. Collect all lines starting with "  - [ ]" or "  - [x]"
       until next heading (####) or blank line
    5. Return list of (line_number, checkbox_state) tuples
```

**Regex for acceptance criteria checkboxes**:

```regex
^(\s+-\s+)\[([ x])\]\s+(.*)$

# Groups:
# 1: Indentation and bullet (preserved for replacement)
# 2: Checkbox state
# 3: Criteria text
```

#### Atomic Writer Sub-component

**Safe file modification protocol**:

```
FUNCTION update_checkboxes_atomically(file_path, updates):
    1. Read entire file into memory
    2. Create backup: {file_path}.bak
    3. Apply updates in memory (no I/O yet)
    4. Write to temp file: {file_path}.tmp
    5. Verify temp file is valid markdown
    6. Atomic rename: {file_path}.tmp → {file_path}
    7. Delete backup on success
    8. On any failure: restore from backup
```

### Component 2: Argument Schema System

**Purpose**: Define, validate, and document command arguments

**Responsibilities**:
- Define argument schema in YAML frontmatter
- Validate arguments on command invocation
- Generate --help output from schema
- Suggest corrections for typos

**Interfaces**:
```
Schema Input: YAML object in command frontmatter
Validation Output: (valid: bool, errors: list, suggestions: list)
Help Output: Formatted man-page string
```

**Dependencies**: YAML parsing (native to command loader)

**Technology**: YAML in frontmatter, bash pattern matching for validation

#### Schema Definition

**Extended argument-hint format**:

```yaml
---
argument-hint:
  positional:
    - name: project-ref
      type: string
      required: false
      description: Project ID (SPEC-YYYY-MM-DD-NNN) or slug
      examples:
        - "2025-12-25-implement-ux"
        - "SPEC-2025-12-25-001"
      pattern: "^(SPEC-\\d{4}-\\d{2}-\\d{2}-\\d{3}|[a-z0-9-]+)$"
  flags:
    - name: --inline
      aliases: []
      type: boolean
      description: Skip worktree and branch creation
    - name: --no-worktree
      type: boolean
      description: Work in current directory instead of creating worktree
    - name: --no-branch
      type: boolean
      description: Stay on current branch instead of creating plan/ branch
    - name: --help
      aliases: [-h]
      type: boolean
      description: Show this help message
---
```

#### Validation Logic

**Argument validation algorithm**:

```
FUNCTION validate_arguments(args, schema):
    errors = []
    suggestions = []

    FOR each arg in args:
        IF arg starts with "--" or "-":
            flag = find_flag_in_schema(arg, schema.flags)
            IF flag is None:
                # Try to suggest similar flag
                closest = find_closest_flag(arg, schema.flags)
                IF levenshtein(arg, closest) <= 3:
                    suggestions.append(f"Did you mean '{closest}'?")
                errors.append(f"Unknown flag: {arg}")
            ELSE IF flag.type == "boolean" AND arg has value:
                errors.append(f"Flag {arg} doesn't take a value")
        ELSE:
            # Positional argument
            IF schema has positional with pattern:
                IF NOT regex_match(arg, pattern):
                    errors.append(f"Invalid format for {name}: {arg}")

    # Check required positional args
    FOR each positional in schema.positional:
        IF positional.required AND NOT provided:
            errors.append(f"Missing required argument: {positional.name}")

    RETURN (len(errors) == 0, errors, suggestions)
```

#### Help Generator

**Dynamic help generation from schema**:

```
FUNCTION generate_help(command_name, description, schema):
    output = []

    # Header
    output.append(f"{command_name.upper()}(1)")
    output.append("")
    output.append("NAME")
    output.append(f"    {command_name} - {description[:50]}...")
    output.append("")

    # Synopsis
    output.append("SYNOPSIS")
    synopsis = f"    /claude-spec:{command_name}"
    FOR flag in schema.flags:
        IF flag.type == "boolean":
            synopsis += f" [{flag.name}]"
        ELSE:
            synopsis += f" [{flag.name} <value>]"
    FOR pos in schema.positional:
        IF pos.required:
            synopsis += f" <{pos.name}>"
        ELSE:
            synopsis += f" [{pos.name}]"
    output.append(synopsis)
    output.append("")

    # Description
    output.append("DESCRIPTION")
    output.append(f"    {description}")
    output.append("")

    # Arguments
    IF schema.positional:
        output.append("ARGUMENTS")
        FOR pos in schema.positional:
            req = "(required)" IF pos.required ELSE "(optional)"
            output.append(f"    {pos.name} {req}")
            output.append(f"        {pos.description}")
            IF pos.examples:
                output.append(f"        Examples: {', '.join(pos.examples)}")
        output.append("")

    # Options
    output.append("OPTIONS")
    FOR flag in schema.flags:
        aliases = f", {', '.join(flag.aliases)}" IF flag.aliases ELSE ""
        output.append(f"    {flag.name}{aliases}")
        output.append(f"        {flag.description}")
    output.append("")

    # Examples
    output.append("EXAMPLES")
    output.append(f"    /claude-spec:{command_name}")
    IF schema.positional:
        example_arg = schema.positional[0].examples[0] IF schema.positional[0].examples ELSE "example"
        output.append(f"    /claude-spec:{command_name} {example_arg}")
    output.append(f"    /claude-spec:{command_name} --help")
    output.append("")

    # Footer
    output.append("SEE ALSO")
    output.append("    /claude-spec:* for related commands")

    RETURN "\n".join(output)
```

## Data Design

### Data Models

**Task Status Model (PROGRESS.md)**:

```markdown
## Phase 1: Foundation
[x] 1.1 Task one description
[ ] 1.2 Task two description
[~] 1.3 Task three (skipped)
```

**Acceptance Criteria Model (IMPLEMENTATION_PLAN.md)**:

```markdown
#### Task 1.1: Task one description
- **Description**: What this task does
- **Files**: path/to/file.py
- **Acceptance Criteria**:
  - [x] First criterion met
  - [x] Second criterion met
  - [ ] Third criterion pending
```

### Data Flow

```
Task Completion Event
        │
        ▼
┌───────────────────┐
│ PROGRESS.md       │
│ [x] 1.1 Task one  │ ◀─── User marks task done
└────────┬──────────┘
         │
         ▼ Sync Engine reads task ID "1.1", status "done"
         │
┌────────┴──────────┐
│ Task Finder       │
│ - Regex: ^#### Task 1.1:
└────────┬──────────┘
         │
         ▼ Located at line 45 in IMPLEMENTATION_PLAN.md
         │
┌────────┴──────────┐
│ Checkbox Locator  │
│ - Find AC section │
│ - Collect boxes   │
└────────┬──────────┘
         │
         ▼ Found 3 checkboxes at lines 48, 49, 50
         │
┌────────┴──────────┐
│ Atomic Writer     │
│ - Backup file     │
│ - Update in memory│
│ - Write atomically│
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ IMPLEMENTATION_   │
│ PLAN.md           │
│ - [x] First       │ ◀─── All boxes checked
│ - [x] Second      │
│ - [x] Third       │
└───────────────────┘
```

## Integration Points

### Internal Integrations

| Component | Integration Type | Purpose |
|-----------|-----------------|---------|
| commands/implement.md | Embedded | Checkbox sync runs within Phase 5 |
| commands/plan.md | Embedded | Argument schema in frontmatter |
| All commands | Frontmatter | Adopt argument-hint schema |

## Security Design

### Data Protection

- Atomic writes prevent partial file corruption
- Backup created before any modification
- No sensitive data in argument schemas

### Validation Considerations

- Regex patterns are pre-compiled and tested
- No user input directly executed (all pattern matching)
- Path arguments validated to exist before use

## Performance Considerations

### Expected Load

- Single file at a time (no concurrent syncs)
- Files typically <500 lines
- Sync operations: <10 per implementation session

### Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| Sync latency | <100ms | Imperceptible to user |
| Validation time | <10ms | Don't slow command startup |
| Memory usage | <5MB | Fit in command context |

### Optimization Strategies

- Read file once, apply all updates in memory
- Pre-compile regex patterns
- Cache Levenshtein calculations for common typos

## Testing Strategy

### Unit Testing

- Regex pattern matching for all documented formats
- Levenshtein distance calculations
- Schema parsing from YAML

### Integration Testing

- Full sync cycle from PROGRESS.md update to IMPLEMENTATION_PLAN.md verification
- --help output generation matches expected format
- Error messages include valid suggestions

### Edge Case Testing

- Task in PROGRESS.md but not in IMPLEMENTATION_PLAN.md
- Acceptance criteria section missing
- Malformed YAML in frontmatter
- Very long task descriptions (line wrapping)

## Deployment Considerations

### Rollout Strategy

1. Update commands/implement.md with sync engine documentation
2. Update commands/plan.md with new argument-hint schema
3. Keep legacy `argument-hint: <string>` working (backward compatible)
4. Migrate other commands to new schema incrementally

### Rollback Plan

- Revert to previous command file versions
- Legacy format remains functional
- No database or external state to restore

## Future Considerations

- **Bidirectional sync**: Allow editing checkboxes in IMPLEMENTATION_PLAN.md
- **Shell completion**: Generate completions for shells that support it
- **Schema sharing**: Define common argument types in shared file
- **Validation plugins**: Allow custom validators for complex args
