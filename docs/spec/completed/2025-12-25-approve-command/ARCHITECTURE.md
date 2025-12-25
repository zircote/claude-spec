---
document_type: architecture
project_id: SPEC-2025-12-25-001
version: 1.0.0
last_updated: 2025-12-25T17:00:00Z
status: draft
---

# Add /approve Command - Technical Architecture

## System Overview

This feature adds an approval gate to the claude-spec workflow by introducing:

1. **`/approve` command** - New command for spec approval/rejection
2. **`/plan` flag extensions** - `--no-worktree`, `--no-branch`, `--inline` flags
3. **Prevention hooks** - PreToolUse hook to block implementation without approved spec
4. **Command hardening** - Explicit warnings in `/plan` to prevent workflow skip
5. **Status gate** - Warning in `/implement` for unapproved specs

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLAUDE-SPEC PLUGIN                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │   /plan     │───▶│  /approve   │───▶│      /implement         │  │
│  │  (creates)  │    │  (validates)│    │  (warns if unapproved)  │  │
│  └──────┬──────┘    └──────┬──────┘    └───────────┬─────────────┘  │
│         │                  │                       │                │
│         │    ┌─────────────┴───────────────┐       │                │
│         │    │     README.md Frontmatter   │       │                │
│         │    │  ┌─────────────────────────┐│       │                │
│         └───▶│  │ status: draft/approved  ││◀──────┘                │
│              │  │ approved_date: ...      ││                        │
│              │  │ approved_by: ...        ││                        │
│              │  └─────────────────────────┘│                        │
│              └─────────────────────────────┘                        │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                     PREVENTION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  PreToolUse Hook: spec-approval-enforcement                  │    │
│  │  ┌─────────────────────────────────────────────────────────┐│    │
│  │  │ IF tool in [Write, Edit] AND path matches src/**        ││    │
│  │  │ AND no approved spec exists in docs/spec/active/        ││    │
│  │  │ THEN block with: "No approved spec. Run /plan first"    ││    │
│  │  └─────────────────────────────────────────────────────────┘│    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Approval storage | README.md frontmatter | Consistent with existing metadata pattern |
| Approver identity | Git config | Reliable, no user input required |
| Enforcement level | Warn, not block | Avoid workflow disruption while providing governance |
| Rejection handling | Move to rejected/ | Clean separation, preserves work |
| Hook mechanism | PreToolUse | Catches implementation before it happens |

## Component Design

### Component 1: /approve Command (`commands/approve.md`)

- **Purpose**: Review and approve/reject specification plans
- **Responsibilities**:
  - Locate and validate spec project
  - Check document completeness
  - Display plan summary for review
  - Capture approval decision via AskUserQuestion
  - Update README.md frontmatter with approval metadata
  - Handle rejection (move to rejected/)
- **Interfaces**:
  - Input: `$ARGUMENTS` (project-id or slug)
  - Output: Updated spec status
- **Dependencies**: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
- **Technology**: Markdown command file with Claude instructions

#### Command Flow

```
1. Parse $ARGUMENTS (project-id or slug)
2. Locate spec in docs/spec/active/
3. Validate completeness:
   - [ ] README.md exists with valid frontmatter
   - [ ] REQUIREMENTS.md exists
   - [ ] ARCHITECTURE.md exists
   - [ ] IMPLEMENTATION_PLAN.md exists
4. Display summary:
   - Document stats (sizes, counts)
   - Scope overview (from REQUIREMENTS.md)
   - Risk summary (from REQUIREMENTS.md)
5. AskUserQuestion: Approve / Request Changes / Reject
6. Handle decision:
   - Approve: Update frontmatter, add CHANGELOG entry
   - Request Changes: Add notes to README, keep in active/
   - Reject: Move to rejected/, add rejection reason
```

### Component 2: /plan Flag Extensions

- **Purpose**: Add workflow flexibility flags
- **Responsibilities**:
  - Parse `--no-worktree`, `--no-branch`, `--inline` flags
  - Skip worktree/branch creation based on flags
  - Pass through remaining arguments as project seed
- **Interfaces**:
  - Input: `$ARGUMENTS` with optional flags
  - Output: Modified workflow behavior

#### Flag Parsing Logic

```bash
# Parse flags from $ARGUMENTS
NO_WORKTREE=false
NO_BRANCH=false
SEED=""

for arg in $ARGUMENTS; do
  case "$arg" in
    --no-worktree) NO_WORKTREE=true ;;
    --no-branch) NO_BRANCH=true ;;
    --inline) NO_WORKTREE=true; NO_BRANCH=true ;;
    *) SEED="$SEED $arg" ;;
  esac
done

# Trim leading space from SEED
SEED="${SEED# }"
```

#### Modified Branch Decision Gate

```
IF NO_WORKTREE == true AND NO_BRANCH == true:
  → Skip both worktree and branch creation
  → PROCEED directly to planning in current directory

IF NO_WORKTREE == true:
  → Skip worktree creation only
  → Still create branch if on protected branch

IF NO_BRANCH == true:
  → Skip branch creation only
  → Still recommend worktree if on protected branch

IF BRANCH in [main, master, develop] AND NO_WORKTREE == false:
  → Create worktree (existing behavior)
```

### Component 3: Prevention Hook

- **Purpose**: Block implementation without approved spec
- **Responsibilities**:
  - Intercept Write/Edit tool calls
  - Check if target path is implementation code
  - Verify approved spec exists
  - Block with guidance if no spec
- **Interfaces**:
  - Input: Tool call parameters (tool_name, file_path)
  - Output: Allow/Block decision
- **Technology**: Claude Code hook (PreToolUse)

#### Hook Configuration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "name": "spec-approval-enforcement",
        "matcher": {
          "tool_name": ["Write", "Edit"],
          "file_path_pattern": "^(?!docs/|tests/|\\.).*\\.(py|ts|js|go|rs|java)$"
        },
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/check-approved-spec.sh",
        "on_failure": "block",
        "message_on_block": "No approved spec found. Run /claude-spec:plan first to create a specification, then /claude-spec:approve to approve it."
      }
    ]
  }
}
```

#### Hook Script (`hooks/check-approved-spec.sh`)

```bash
#!/bin/bash
# Check if an approved spec exists in docs/spec/active/

APPROVED_SPECS=$(find docs/spec/active -name "README.md" -exec grep -l "status: approved" {} \; 2>/dev/null)

if [ -z "$APPROVED_SPECS" ]; then
  echo "NO_APPROVED_SPEC"
  exit 1
fi

echo "APPROVED_SPEC_FOUND"
exit 0
```

### Component 4: Command Instruction Hardening

- **Purpose**: Explicit warnings in /plan to prevent workflow skip
- **Location**: `commands/plan.md`
- **Changes**:
  - Add `<never_implement>` section with explicit prohibition
  - Add workflow reminder after spec creation
  - Reference approval requirement

#### Hardening Text

```markdown
<never_implement>
## ⛔ CRITICAL: NEVER IMPLEMENT WITHOUT APPROVED SPEC ⛔

**THIS IS A HARD CONSTRAINT. VIOLATION IS UNACCEPTABLE.**

After creating spec documents, you MUST:
1. STOP creating/modifying code files
2. Update spec status to `in-review`
3. Inform user to run `/claude-spec:approve` for approval
4. HALT and wait for explicit `/claude-spec:implement` invocation

You are PROHIBITED from:
- Writing implementation code during `/plan`
- Modifying source files (src/, lib/, etc.)
- Creating tests or scripts beyond spec documents
- Assuming approval without explicit `/approve` execution

The planning phase produces DOCUMENTS ONLY:
- README.md, REQUIREMENTS.md, ARCHITECTURE.md, IMPLEMENTATION_PLAN.md
- DECISIONS.md, RESEARCH_NOTES.md, CHANGELOG.md

**NO CODE. NO IMPLEMENTATION. DOCUMENTS ONLY.**
</never_implement>
```

### Component 5: Status Gate in /implement

- **Purpose**: Warn when implementing unapproved specs
- **Location**: `commands/implement.md`
- **Changes**:
  - Add status check after project detection
  - Display warning for draft/in-review status
  - Allow proceeding after warning

#### Status Check Logic

```markdown
### Step 0.5: Check Approval Status

After locating the project, check approval status:

```bash
STATUS=$(grep "^status:" "${PROJECT_DIR}/README.md" | cut -d' ' -f2)
echo "SPEC_STATUS=${STATUS}"
```

```
IF STATUS == "draft":
  → Display warning:
    "⚠️ WARNING: This spec is still in draft status.

    It has not been formally reviewed or approved.
    Consider running /claude-spec:approve first.

    Proceeding anyway..."

IF STATUS == "in-review":
  → Display warning:
    "⚠️ WARNING: This spec is in-review but not yet approved.

    Run /claude-spec:approve to formally approve before implementing.

    Proceeding anyway..."

IF STATUS == "approved":
  → Continue without warning
```
```

## Data Design

### Approval Metadata Schema

```yaml
# README.md frontmatter - after approval
---
project_id: SPEC-YYYY-MM-DD-NNN
project_name: "Project Name"
slug: project-slug
status: approved          # Changed from draft/in-review
created: YYYY-MM-DDTHH:MM:SSZ
approved_date: YYYY-MM-DDTHH:MM:SSZ    # NEW
approved_by: "Name <email>"             # NEW
started: null
completed: null
expires: YYYY-MM-DDTHH:MM:SSZ
superseded_by: null
tags: [...]
stakeholders: []
---
```

### Rejection Metadata

```yaml
# README.md frontmatter - after rejection
---
project_id: SPEC-YYYY-MM-DD-NNN
project_name: "Project Name"
slug: project-slug
status: rejected          # Changed
created: YYYY-MM-DDTHH:MM:SSZ
rejected_date: YYYY-MM-DDTHH:MM:SSZ    # NEW
rejected_by: "Name <email>"             # NEW
rejection_reason: "Brief reason"        # NEW
---
```

### Directory Structure Changes

```
docs/spec/
├── active/          # Existing - draft, in-review, approved, in-progress
├── approved/        # Existing - approved awaiting implementation
├── completed/       # Existing - finished projects
├── superseded/      # Existing - replaced projects
└── rejected/        # NEW - rejected specifications
    └── YYYY-MM-DD-slug/
        ├── README.md (with rejection metadata)
        ├── REQUIREMENTS.md
        ├── ARCHITECTURE.md
        └── IMPLEMENTATION_PLAN.md
```

## Integration Points

### Internal Integrations

| System | Integration Type | Purpose |
|--------|-----------------|---------|
| /plan | Command modification | Add flag parsing |
| /implement | Command modification | Add status warning |
| /status | Command modification | Show approval state |
| /complete | No change | Works with any approved spec |

### Hook Integration

| Hook Type | Location | Purpose |
|-----------|----------|---------|
| PreToolUse | .claude/hooks.json | Block implementation without spec |

## Security Design

### Approver Identity

- Source: `git config user.name` and `git config user.email`
- Format: `"Name <email>"`
- Fallback: `"user"` if git config empty

### Data Protection

- No secrets stored in approval metadata
- Git config already user-controlled
- No authentication required (local operation)

## Testing Strategy

### Unit Testing

- Flag parsing for /plan
- Approval metadata updates
- Rejection flow
- Hook script exit codes

### Integration Testing

- Full /plan → /approve → /implement workflow
- Rejection and move to rejected/
- Warning display in /implement
- Hook blocking behavior

### Manual Testing

- Run /plan with each flag combination
- Approve a spec and verify metadata
- Reject a spec and verify move
- Attempt implementation without spec (hook blocks)

## Deployment Considerations

### Files to Create

| File | Purpose |
|------|---------|
| `commands/approve.md` | New /approve command |
| `hooks/check-approved-spec.sh` | Hook enforcement script |

### Files to Modify

| File | Changes |
|------|---------|
| `.claude-plugin/plugin.json` | Register /approve command |
| `commands/plan.md` | Add flag parsing, never_implement section |
| `commands/implement.md` | Add approval status warning |
| `commands/status.md` | Show approval state |
| `.claude/hooks.json` OR hookify | Add PreToolUse hook |
| `CLAUDE.md` | Update workflow documentation |

### Rollout Strategy

1. Create /approve command
2. Update /plan with flags and hardening
3. Update /implement with status warning
4. Add hook (optional, can be enabled later)
5. Update documentation

### Rollback Plan

- Remove hook to restore permissive behavior
- /approve command is additive, doesn't break existing flow
- /plan flags are optional, existing usage unchanged
