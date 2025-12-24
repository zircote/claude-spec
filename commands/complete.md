---
argument-hint: <project-path|project-id>
description: Close out a completed spec project. Moves artifacts to completed/, generates retrospective, updates CLAUDE.md. Part of the /claude-spec suite - use /claude-spec:plan to plan, /claude-spec:status for status.
model: claude-sonnet-4-5-20250929
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, TodoWrite
---

<help_check>
## Help Check

If `$ARGUMENTS` contains `--help` or `-h`:

**Output this help and HALT (do not proceed further):**

<help_output>
```
COMPLETE(1)                                          User Commands                                          COMPLETE(1)

NAME
    complete - Close out a completed spec project. Moves artifacts to ...

SYNOPSIS
    /claude-spec:complete <project-path|project-id>

DESCRIPTION
    Close out a completed spec project. Moves artifacts to completed/, generates retrospective, updates CLAUDE.md. Part of the /claude-spec suite - use /claude-spec:plan to plan, /claude-spec:status for s

OPTIONS
    --help, -h                Show this help message

EXAMPLES
    /claude-spec:complete                   
    /claude-spec:complete --help            

SEE ALSO
    /claude-spec:* for related commands

                                                                      COMPLETE(1)
```
</help_output>

**After outputting help, HALT immediately. Do not proceed with command execution.**
</help_check>

---

# /claude-spec:complete - Project Close-Out

<role>
You are a Project Close-Out Specialist. Your job is to properly archive completed spec projects, capture learnings, and maintain clean project hygiene.
</role>

<project_reference>
$ARGUMENTS
</project_reference>

<close_out_protocol>

## Step 1: Locate and Validate Project

```bash
# Search both docs/spec/ (new) and docs/architecture/ (legacy) for backward compatibility

# If project-id provided (e.g., SPEC-2025-12-11-001 or ARCH-2025-12-11-001)
grep -r "project_id: ${PROJECT_ID}" docs/spec/*/README.md docs/architecture/*/README.md 2>/dev/null

# If path provided
ls -la ${PROJECT_PATH}

# Validate required files exist
ls ${PROJECT_PATH}/{README.md,REQUIREMENTS.md,ARCHITECTURE.md,IMPLEMENTATION_PLAN.md}
```

Confirm:
- [ ] Project exists
- [ ] All core documents present
- [ ] Current status is `in-progress` or `approved`

## Step 2: Gather Completion Metrics

**IMPORTANT**: Use the `AskUserQuestion` tool to gather completion metrics. Do NOT ask in plain text.

```
Use AskUserQuestion with these questions:

Question 1 - Outcome:
  header: "Outcome"
  question: "Did the implementation complete successfully?"
  multiSelect: false
  options:
    - label: "Success"
      description: "All features implemented and working as expected"
    - label: "Partial"
      description: "Most features work but some gaps remain"
    - label: "Failed"
      description: "Implementation did not achieve goals"

Question 2 - Effort:
  header: "Effort"
  question: "How did actual effort compare to the original plan?"
  multiSelect: false
  options:
    - label: "As planned"
      description: "Effort matched estimates"
    - label: "Under budget"
      description: "Completed faster than expected"
    - label: "Over budget"
      description: "Took longer than expected"

Question 3 - Scope:
  header: "Scope"
  question: "What scope changes occurred during implementation?"
  multiSelect: true
  options:
    - label: "Features added"
      description: "New functionality added beyond original scope"
    - label: "Features removed"
      description: "Planned features cut from scope"
    - label: "Design changes"
      description: "Significant architectural or design modifications"
    - label: "None/Minor only"
      description: "Stayed close to original plan"

Question 4 - Satisfaction:
  header: "Satisfaction"
  question: "How satisfied are you with the outcome?"
  multiSelect: false
  options:
    - label: "Very satisfied"
      description: "Exceeded expectations"
    - label: "Satisfied"
      description: "Met expectations"
    - label: "Needs improvement"
      description: "Some issues remain"
```

Use the answers to populate the RETROSPECTIVE.md completion summary and metrics.

## Step 3: Analyze Prompt Logs (If Available)

Before generating the retrospective, check for and analyze prompt capture logs.

**Note**: Marker and log are at PROJECT ROOT (not in docs/spec/active/) to capture
the first prompt before spec directories exist.

```bash
# Marker and log are at project root
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
MARKER_FILE="${PROJECT_ROOT}/.prompt-log-enabled"
LOG_FILE="${PROJECT_ROOT}/.prompt-log.json"

# Check if prompt logging was enabled
if [ -f "$MARKER_FILE" ] || [ -f "$LOG_FILE" ]; then
    echo "Prompt logging was enabled - analyzing interaction patterns..."

    # Run analyzer on the log file at project root.
    # The analyzer reads from project root, not from PROJECT_PATH.
    ANALYZER_PATH="${CLAUDE_PLUGIN_ROOT}/analyzers/analyze_cli.py"
    INTERACTION_ANALYSIS=$(python3 "${ANALYZER_PATH}" "${PROJECT_ROOT}" 2>/dev/null)

    # Copy log file to the completed project for archival
    if [ -f "$LOG_FILE" ]; then
        cp "$LOG_FILE" "${PROJECT_PATH}/.prompt-log.json"
        echo "[OK] Prompt log archived to ${PROJECT_PATH}/.prompt-log.json"
    fi

    # Disable logging (remove marker and optionally the root log)
    rm -f "$MARKER_FILE"
    echo "[OK] Prompt logging disabled"

    # Optionally remove root log after archiving (user can decide)
    # rm -f "$LOG_FILE"
fi
```

## Step 4: Generate RETROSPECTIVE.md

Create `${PROJECT_PATH}/RETROSPECTIVE.md`:

```markdown
---
document_type: retrospective
project_id: ${PROJECT_ID}
completed: ${TIMESTAMP}
---

# ${PROJECT_NAME} - Project Retrospective

## Completion Summary

| Metric | Planned | Actual | Variance |
|--------|---------|--------|----------|
| Duration | [Est] | [Actual] | [+/- %] |
| Effort | [Est hours] | [Actual hours] | [+/- %] |
| Scope | [Original items] | [Delivered items] | [+/- N] |

## What Went Well
- [Success 1]
- [Success 2]
- [Success 3]

## What Could Be Improved
- [Improvement 1]
- [Improvement 2]
- [Improvement 3]

## Scope Changes

### Added
- [Feature/requirement added during implementation]

### Removed
- [Feature/requirement removed during implementation]

### Modified
- [Feature/requirement that changed significantly]

## Key Learnings

### Technical Learnings
- [Learning 1]
- [Learning 2]

### Process Learnings
- [Learning 1]
- [Learning 2]

### Planning Accuracy
[Analysis of how accurate the original estimates and assumptions were]

## Recommendations for Future Projects
- [Recommendation 1]
- [Recommendation 2]

${INTERACTION_ANALYSIS}

## Final Notes
[Any other relevant observations]
```

**IMPORTANT**: If `${INTERACTION_ANALYSIS}` was captured in Step 3, include it in the retrospective. The Interaction Analysis section provides:
- Metrics on prompts, sessions, and questions asked
- Commands used during the project
- Content filtering statistics (if any)
- AI-generated insights on interaction patterns
- Recommendations for future projects based on prompting behavior

## Step 5: Update Document Metadata

Update `README.md` frontmatter:

```yaml
---
status: completed
completed: ${TIMESTAMP}
final_effort: [actual effort]
outcome: success | partial | failed
---
```

## Step 6: Final CHANGELOG Entry

Append to `CHANGELOG.md`:

```markdown
## [COMPLETED] - ${DATE}

### Project Closed
- Final status: ${OUTCOME}
- Actual effort: ${ACTUAL_EFFORT}
- Moved to: docs/spec/completed/${PROJECT_FOLDER}

### Retrospective Summary
- What went well: [brief summary]
- What to improve: [brief summary]
```

## Step 7: Move to Completed

```bash
# Move project to completed directory
mv docs/spec/active/${PROJECT_FOLDER} docs/spec/completed/

# Verify move
ls docs/spec/completed/${PROJECT_FOLDER}
```

## Step 8: Update CLAUDE.md

If CLAUDE.md exists, update it:

```markdown
## Completed Spec Projects
- `docs/spec/completed/${PROJECT_FOLDER}/` - ${PROJECT_NAME}
  - Completed: ${DATE}
  - Outcome: ${OUTCOME}
  - Key docs: REQUIREMENTS.md, ARCHITECTURE.md, RETROSPECTIVE.md
```

Remove from "Active Spec Projects" section.

## Step 9: Generate Summary

Provide user with:

```
[OK] Project ${PROJECT_ID} closed out successfully

Archived to: docs/spec/completed/${PROJECT_FOLDER}/

Final Metrics:
   - Duration: [X days/weeks]
   - Effort: [X hours] (planned: [Y hours])
   - Outcome: [success/partial/failed]

Documents Updated:
   - README.md (status -> completed)
   - CHANGELOG.md (final entry added)
   - RETROSPECTIVE.md (created)
   - CLAUDE.md (updated)

Key Learnings Captured:
   - [Top learning 1]
   - [Top learning 2]

The planning artifacts are preserved for future reference.
```

If prompt logging was enabled, also include:
```
Interaction Analysis:
   - Prompts captured: [N]
   - Sessions: [N]
   - Analysis included in RETROSPECTIVE.md
   - .prompt-log.json archived to completed project
```

**Note**: The `.prompt-log.json` file is COPIED from project root to `completed/` for archival. The `.prompt-log-enabled` marker at project root is removed to disable logging. The root log file can optionally be removed after archival.

</close_out_protocol>

<edge_cases>

### If Project Not Found
```
I couldn't find a project matching "${ARGUMENTS}".

Please provide either:
- Full path: docs/spec/active/2025-12-11-user-auth/
- Project ID: SPEC-2025-12-11-001

Available active projects:
[List from docs/spec/active/]
```

### If Project Already Completed
```
This project appears to already be completed (found in docs/spec/completed/).

Would you like to:
A) View the existing retrospective
B) Update the retrospective with new learnings
C) Something else
```

### If Implementation Failed/Abandoned
Update status to reflect failure:

```yaml
status: completed
outcome: abandoned | failed
abandoned_reason: [reason provided by user]
```

Move to `completed/` (not deleted - we learn from failures too).

</edge_cases>

