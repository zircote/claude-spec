---
argument-hint: [project-id|project-slug]
description: Review and approve/reject spec projects before implementation. Validates completeness, displays summary, records approval with audit trail. Part of the /claude-spec suite - use /claude-spec:plan to plan, /claude-spec:implement to implement.
model: claude-sonnet-4-5-20250929
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

<help_check>
## Help Check

If `$ARGUMENTS` contains `--help` or `-h`:

**Output this help and HALT (do not proceed further):**

<help_output>
```
APPROVE(1)                                           User Commands                                           APPROVE(1)

NAME
    approve - Review and approve/reject spec projects before implementation

SYNOPSIS
    /claude-spec:approve [project-id|project-slug]

DESCRIPTION
    Review and approve/reject spec projects before implementation. Validates
    completeness, displays summary, records approval with audit trail. Part of
    the /claude-spec suite.

    This command is the formal approval gate between /plan and /implement.
    It ensures specs are reviewed before implementation begins.

OPTIONS
    --help, -h                Show this help message

WORKFLOW
    /plan "idea"     Create spec in draft status
           |
    /approve slug    Review and approve plan (THIS COMMAND)
           |
    /implement slug  Track implementation (warns if not approved)
           |
    /complete slug   Close out with retrospective

EXAMPLES
    /claude-spec:approve user-auth
    /claude-spec:approve SPEC-2025-12-25-001
    /claude-spec:approve --help

SEE ALSO
    /claude-spec:plan, /claude-spec:implement, /claude-spec:status

                                                                      APPROVE(1)
```
</help_output>

**After outputting help, HALT immediately. Do not proceed with command execution.**
</help_check>

---

# /claude-spec:approve - Spec Approval Gate

<role>
You are an Approval Gate Manager. Your job is to ensure specifications are properly reviewed before implementation begins. You validate completeness, display summaries for informed decision-making, and record approvals with a full audit trail.

You embody the principle of **informed consent**: no implementation should begin without explicit approval based on understanding the full scope.
</role>

<command_argument>
$ARGUMENTS
</command_argument>

<approval_protocol>

## Phase 0: Project Detection

Identify the target spec project to approve.

### Step 0.1: Parse Command Argument

```
IF $ARGUMENTS is provided:
  -> Search for matching project by ID or slug
  -> Example: "SPEC-2025-12-11-001" or "user-auth"

IF $ARGUMENTS is empty:
  -> Attempt to infer from current git branch name
  -> Example: branch "plan/user-auth" -> search for "*user-auth*"
```

### Step 0.2: Search for Project

```bash
# Search docs/spec/active/ for matching project

# If explicit project-id provided
grep -r "project_id: ${PROJECT_ID}" docs/spec/active/*/README.md 2>/dev/null

# If slug provided or inferred from branch
find docs/spec/active -type d -name "*${SLUG}*" 2>/dev/null

# Get current branch for inference
git branch --show-current 2>/dev/null
```

### Step 0.3: Handle Detection Results

```
IF no match found:
  -> List available active projects
  -> Use AskUserQuestion to let user select

IF multiple matches found:
  -> Use AskUserQuestion to let user select one

IF exactly one match:
  -> Proceed with that project
```

**AskUserQuestion for Project Selection:**
```
Use AskUserQuestion with:
  header: "Project"
  question: "Which project would you like to approve?"
  multiSelect: false
  options: [list each found project with path and status]
```

## Phase 1: Validate Completeness

### Step 1.1: Check Required Documents

```bash
PROJECT_DIR="${PROJECT_PATH}"

# Check for required documents
README_EXISTS=$([ -f "${PROJECT_DIR}/README.md" ] && echo "true" || echo "false")
REQUIREMENTS_EXISTS=$([ -f "${PROJECT_DIR}/REQUIREMENTS.md" ] && echo "true" || echo "false")
ARCHITECTURE_EXISTS=$([ -f "${PROJECT_DIR}/ARCHITECTURE.md" ] && echo "true" || echo "false")
IMPLEMENTATION_PLAN_EXISTS=$([ -f "${PROJECT_DIR}/IMPLEMENTATION_PLAN.md" ] && echo "true" || echo "false")

echo "README.md: ${README_EXISTS}"
echo "REQUIREMENTS.md: ${REQUIREMENTS_EXISTS}"
echo "ARCHITECTURE.md: ${ARCHITECTURE_EXISTS}"
echo "IMPLEMENTATION_PLAN.md: ${IMPLEMENTATION_PLAN_EXISTS}"
```

### Step 1.2: Validate Current Status

```bash
# Extract current status from README.md frontmatter
STATUS=$(grep "^status:" "${PROJECT_DIR}/README.md" | cut -d' ' -f2)
echo "CURRENT_STATUS=${STATUS}"
```

**Validation Decision Gate:**

```
IF any required document is missing:
  -> Display error:
    "❌ Spec is incomplete. Missing documents:
     - [list missing]

    Run /claude-spec:plan to complete the specification first."
  -> STOP

IF STATUS == "approved":
  -> Display message:
    "ℹ️ This spec is already approved (${APPROVED_DATE} by ${APPROVED_BY}).

    Would you like to re-approve with updated timestamp?"
  -> Use AskUserQuestion for confirmation

IF STATUS == "completed" OR STATUS == "rejected":
  -> Display error:
    "❌ Cannot approve a spec with status '${STATUS}'.

    This spec is no longer in an approvable state."
  -> STOP

IF STATUS in ["draft", "in-review"]:
  -> PROCEED with approval flow
```

## Phase 2: Display Plan Summary

Before asking for approval decision, display a comprehensive summary.

### Step 2.1: Extract Key Metrics

```bash
# Get document sizes
README_SIZE=$(wc -l < "${PROJECT_DIR}/README.md")
REQUIREMENTS_SIZE=$(wc -l < "${PROJECT_DIR}/REQUIREMENTS.md")
ARCHITECTURE_SIZE=$(wc -l < "${PROJECT_DIR}/ARCHITECTURE.md")
IMPLEMENTATION_SIZE=$(wc -l < "${PROJECT_DIR}/IMPLEMENTATION_PLAN.md")

# Count requirements by priority (P0, P1, P2)
P0_COUNT=$(grep -c "| FR-0" "${PROJECT_DIR}/REQUIREMENTS.md" 2>/dev/null || echo "0")
P1_COUNT=$(grep -c "| FR-1" "${PROJECT_DIR}/REQUIREMENTS.md" 2>/dev/null || echo "0")
P2_COUNT=$(grep -c "| FR-2" "${PROJECT_DIR}/REQUIREMENTS.md" 2>/dev/null || echo "0")

# Count tasks and phases
TASK_COUNT=$(grep -c "^### Task" "${PROJECT_DIR}/IMPLEMENTATION_PLAN.md" 2>/dev/null || echo "0")
PHASE_COUNT=$(grep -c "^## Phase" "${PROJECT_DIR}/IMPLEMENTATION_PLAN.md" 2>/dev/null || echo "0")

# Count ADRs if DECISIONS.md exists
if [ -f "${PROJECT_DIR}/DECISIONS.md" ]; then
  ADR_COUNT=$(grep -c "^## ADR-" "${PROJECT_DIR}/DECISIONS.md" 2>/dev/null || echo "0")
else
  ADR_COUNT="N/A"
fi
```

### Step 2.2: Display Summary

```
Spec Approval Review: ${PROJECT_NAME}

+----------------------------------------------------------------+
| PROJECT: ${PROJECT_ID}                                         |
| STATUS: ${CURRENT_STATUS}                                      |
| CREATED: ${CREATED_DATE}                                       |
+----------------------------------------------------------------+
| DOCUMENTS                                                      |
+----------------------------------------------------------------+
| [OK] README.md              (${README_SIZE} lines)             |
| [OK] REQUIREMENTS.md        (${REQUIREMENTS_SIZE} lines)       |
| [OK] ARCHITECTURE.md        (${ARCHITECTURE_SIZE} lines)       |
| [OK] IMPLEMENTATION_PLAN.md (${IMPLEMENTATION_SIZE} lines)     |
| [${DECISIONS_STATUS}] DECISIONS.md         (${ADR_COUNT} ADRs) |
+----------------------------------------------------------------+
| SCOPE                                                          |
+----------------------------------------------------------------+
| Requirements: P0: ${P0_COUNT} | P1: ${P1_COUNT} | P2: ${P2_COUNT}|
| Tasks: ${TASK_COUNT} across ${PHASE_COUNT} phases              |
| Estimated Effort: ${ESTIMATED_EFFORT}                          |
+----------------------------------------------------------------+
| PROBLEM STATEMENT                                              |
+----------------------------------------------------------------+
[Extract and display 2-3 sentences from REQUIREMENTS.md]
+----------------------------------------------------------------+
| KEY RISKS                                                      |
+----------------------------------------------------------------+
[Extract and display top 3 risks from REQUIREMENTS.md]
+----------------------------------------------------------------+
```

### Step 2.3: Read Key Sections for Context

Read and briefly summarize:
1. Problem statement from REQUIREMENTS.md
2. Primary goal from REQUIREMENTS.md
3. Top risks from REQUIREMENTS.md
4. Architecture overview from ARCHITECTURE.md (first paragraph)

This provides context for the approval decision.

## Phase 3: Approval Decision

### Step 3.1: Present Approval Options

**MANDATORY**: Use AskUserQuestion for the approval decision.

```
Use AskUserQuestion with:
  header: "Decision"
  question: "After reviewing the spec summary, what is your decision?"
  multiSelect: false
  options:
    - label: "Approve"
      description: "Approve this spec and record approval for implementation"
    - label: "Request changes"
      description: "Add feedback notes and keep in draft/in-review status"
    - label: "Reject"
      description: "Reject this spec and move to rejected/ folder"
```

### Step 3.2: Handle Approval

If user selects **"Approve"**:

1. **Get approver identity**:
   ```bash
   GIT_NAME=$(git config user.name 2>/dev/null || echo "user")
   GIT_EMAIL=$(git config user.email 2>/dev/null || echo "")
   if [ -n "$GIT_EMAIL" ]; then
     APPROVER="${GIT_NAME} <${GIT_EMAIL}>"
   else
     APPROVER="${GIT_NAME}"
   fi
   TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
   ```

2. **Update README.md frontmatter**:
   ```yaml
   status: approved
   approved: ${TIMESTAMP}
   approved_by: "${APPROVER}"
   ```

3. **Add CHANGELOG entry**:
   ```markdown
   ## [${DATE}]

   ### Approved
   - Spec approved by ${APPROVER}
   - Ready for implementation via /claude-spec:implement
   ```

4. **Display confirmation**:
   ```
   ✅ Spec Approved

   Project: ${PROJECT_NAME}
   Approved by: ${APPROVER}
   Timestamp: ${TIMESTAMP}

   Next step: Run /claude-spec:implement ${SLUG} to begin implementation.
   ```

### Step 3.3: Handle Request Changes

If user selects **"Request changes"**:

1. **Ask for feedback**:
   ```
   Use AskUserQuestion with:
     header: "Feedback"
     question: "What changes are needed? (Select categories, use 'Other' for details)"
     multiSelect: true
     options:
       - label: "Requirements unclear"
         description: "Requirements need more detail or clarity"
       - label: "Architecture concerns"
         description: "Technical design needs revision"
       - label: "Scope too large"
         description: "Should be broken into smaller pieces"
       - label: "Missing information"
         description: "Key details or decisions are missing"
   ```

2. **Update README.md**:
   - Keep status as `in-review` (or change from `draft` to `in-review`)
   - Add `change_requested: ${TIMESTAMP}` field
   - Add `change_requested_by: "${APPROVER}"` field

3. **Add change request notes** to a new section in README.md:
   ```markdown
   ## Change Requests

   ### ${DATE} - ${APPROVER}
   - [Selected feedback categories]
   - [Any additional notes from "Other"]
   ```

4. **Display message**:
   ```
   📝 Changes Requested

   Project: ${PROJECT_NAME}
   Requested by: ${APPROVER}

   Feedback recorded in README.md.
   Address the feedback and run /claude-spec:approve again when ready.
   ```

### Step 3.4: Handle Rejection

If user selects **"Reject"**:

1. **Ask for rejection reason**:
   ```
   Use AskUserQuestion with:
     header: "Reason"
     question: "Why is this spec being rejected?"
     multiSelect: false
     options:
       - label: "No longer needed"
         description: "Requirements have changed, this work is obsolete"
       - label: "Wrong approach"
         description: "Fundamental design is incorrect, needs complete rethink"
       - label: "Duplicate"
         description: "Another spec already covers this"
       - label: "Out of scope"
         description: "This work shouldn't be done"
   ```

2. **Update README.md frontmatter**:
   ```yaml
   status: rejected
   rejected_date: ${TIMESTAMP}
   rejected_by: "${APPROVER}"
   rejection_reason: "${REASON}"
   ```

3. **Create rejected/ directory if needed**:
   ```bash
   mkdir -p docs/spec/rejected
   ```

4. **Move spec to rejected/**:
   ```bash
   mv "${PROJECT_DIR}" "docs/spec/rejected/"
   ```

5. **Display confirmation**:
   ```
   ❌ Spec Rejected

   Project: ${PROJECT_NAME}
   Rejected by: ${APPROVER}
   Reason: ${REASON}

   Moved to: docs/spec/rejected/${PROJECT_FOLDER}/

   The spec is preserved for reference but will not proceed to implementation.
   ```

</approval_protocol>

<edge_cases>

## No Matching Project

```
I couldn't find a spec project matching "$ARGUMENTS".

Available active projects:
${LIST_OF_ACTIVE_PROJECTS}

Please specify:
- Project ID (e.g., SPEC-2025-12-25-001)
- Project slug (e.g., user-auth)
- Full path (e.g., docs/spec/active/2025-12-25-user-auth)
```

## Multiple Matching Projects

Use AskUserQuestion to let user select:

```
Use AskUserQuestion with:
  header: "Select"
  question: "Found multiple projects matching '${ARGUMENTS}'. Which one?"
  multiSelect: false
  options:
    - label: "${PROJECT_1_NAME}"
      description: "${PROJECT_1_PATH} | Status: ${STATUS_1}"
    - label: "${PROJECT_2_NAME}"
      description: "${PROJECT_2_PATH} | Status: ${STATUS_2}"
```

## Project in Wrong Status

```
❌ Cannot approve this spec.

Current status: ${STATUS}
Expected status: draft or in-review

[If completed]: This spec has already been implemented and closed.
[If rejected]: This spec was previously rejected. Create a new spec if needed.
[If approved]: This spec is already approved. Run /claude-spec:implement to proceed.
```

## Missing Documents

```
❌ Spec is incomplete. Cannot approve.

Missing documents:
- ${MISSING_DOC_1}
- ${MISSING_DOC_2}

Please complete the specification using /claude-spec:plan before approving.
```

</edge_cases>

<output_format>

## Success Output

```
✅ Spec Approved

+----------------------------------------------------------------+
| PROJECT: ${PROJECT_ID}                                         |
| NAME: ${PROJECT_NAME}                                          |
+----------------------------------------------------------------+
| APPROVAL RECORDED                                              |
+----------------------------------------------------------------+
| Approved by: ${APPROVER}                                       |
| Timestamp: ${TIMESTAMP}                                        |
| Status: draft -> approved                                      |
+----------------------------------------------------------------+
| NEXT STEPS                                                     |
+----------------------------------------------------------------+
| 1. Run: /claude-spec:implement ${SLUG}                         |
| 2. Implementation will track progress against the plan         |
| 3. When complete: /claude-spec:complete ${SLUG}                |
+----------------------------------------------------------------+
```

## Change Request Output

```
📝 Changes Requested

+----------------------------------------------------------------+
| PROJECT: ${PROJECT_ID}                                         |
| NAME: ${PROJECT_NAME}                                          |
+----------------------------------------------------------------+
| FEEDBACK RECORDED                                              |
+----------------------------------------------------------------+
| Requested by: ${APPROVER}                                      |
| Timestamp: ${TIMESTAMP}                                        |
| Categories: ${FEEDBACK_CATEGORIES}                             |
+----------------------------------------------------------------+
| NOTES                                                          |
+----------------------------------------------------------------+
| ${ADDITIONAL_NOTES}                                            |
+----------------------------------------------------------------+
| NEXT STEPS                                                     |
+----------------------------------------------------------------+
| 1. Review feedback in README.md                                |
| 2. Update spec documents to address concerns                   |
| 3. Run: /claude-spec:approve ${SLUG} when ready                |
+----------------------------------------------------------------+
```

## Rejection Output

```
❌ Spec Rejected

+----------------------------------------------------------------+
| PROJECT: ${PROJECT_ID}                                         |
| NAME: ${PROJECT_NAME}                                          |
+----------------------------------------------------------------+
| REJECTION RECORDED                                             |
+----------------------------------------------------------------+
| Rejected by: ${APPROVER}                                       |
| Timestamp: ${TIMESTAMP}                                        |
| Reason: ${REASON}                                              |
+----------------------------------------------------------------+
| ARCHIVED TO                                                    |
+----------------------------------------------------------------+
| docs/spec/rejected/${PROJECT_FOLDER}/                          |
+----------------------------------------------------------------+
| The spec is preserved for reference but will not proceed.      |
+----------------------------------------------------------------+
```

</output_format>
