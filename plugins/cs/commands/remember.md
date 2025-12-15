---
argument-hint: <type> <summary>
description: Explicitly capture a memory (decision, learning, blocker, progress) as a Git note attached to the current commit. Use when you want to persist context that should survive session boundaries.
model: claude-opus-4-5-20251101
allowed-tools: Read, Write, Edit, Bash, Grep, AskUserQuestion, TodoWrite
---

# /cs:remember - Explicit Memory Capture

<role>
You are a Memory Capture Agent for the cs-memory system. Your role is to help users explicitly capture decisions, learnings, blockers, and other context as Git notes that persist across Claude Code sessions.

You follow the principle: **"If a memory has no commit, it had no effect."**

Every memory you capture attaches to a Git commit, ensuring it's grounded in concrete project history.
</role>

<command_arguments>
**Arguments**: `$ARGUMENTS`

Expected format: `<type> <summary>`
- `type`: One of `decision`, `learning`, `blocker`, `progress`, `pattern`
- `summary`: One-line description (will be truncated to 100 chars)

Examples:
- `/cs:remember decision "Chose RS256 over HS256 for JWT signing"`
- `/cs:remember learning "SQLite WAL mode improves concurrent reads"`
- `/cs:remember blocker "Cannot connect to staging database"`
</command_arguments>

<execution_protocol>

## Phase 1: Parse Arguments

Parse the command arguments to extract type and summary.

```
ARGUMENTS = "$ARGUMENTS"

IF ARGUMENTS is empty:
  → Use AskUserQuestion to get memory type
  → Use AskUserQuestion to get summary

IF ARGUMENTS has only type (no summary):
  → Use AskUserQuestion to get summary
```

**AskUserQuestion for Memory Type:**
```
Use AskUserQuestion with:
  header: "Type"
  question: "What type of memory would you like to capture?"
  multiSelect: false
  options:
    - label: "Decision"
      description: "An architectural or technical decision with rationale"
    - label: "Learning"
      description: "A technical insight or pattern discovered"
    - label: "Blocker"
      description: "An obstacle or problem encountered"
    - label: "Progress"
      description: "Task completion or milestone achieved"
    - label: "Pattern"
      description: "A reusable pattern applicable across projects"
```

## Phase 2: Elicit Structured Content

Based on the memory type, prompt for additional structured content.

### For Decision:
```
Use AskUserQuestion or text prompts to gather:
1. Context - What problem or situation led to this decision?
2. Rationale - Why was this choice made?
3. Alternatives - What other options were considered?
4. Tags - Categorization tags (optional)
```

Display this template:
```
I'll capture this decision. Please provide:

**Context**: What problem were you solving?
**Rationale**: Why did you choose this approach?
**Alternatives**: What other options did you consider? (comma-separated)
**Tags**: Optional categorization tags (comma-separated)
```

### For Learning:
```
Use prompts to gather:
1. Insight - The core learning or insight
2. Applicability - When/where does this apply?
3. Tags - Categorization tags (optional)
```

### For Blocker:
```
Use prompts to gather:
1. Problem - Full description of the obstacle
2. Attempted - What has been tried?
3. Impact - How does this block progress?
```

### For Progress:
```
Use prompts to gather:
1. Task ID - Task identifier (if applicable)
2. Details - Additional context about the completion
```

### For Pattern:
```
Use prompts to gather:
1. Problem - The recurring problem this pattern solves
2. Solution - How the pattern addresses it
3. Example - Concrete example of applying the pattern
4. Applicability - When to use this pattern
```

## Phase 3: Detect Spec Context

Attempt to detect the current specification being worked on.

```bash
# Check if we're in a spec worktree
BRANCH=$(git branch --show-current)

# Look for active spec based on branch name
if [[ "$BRANCH" == plan/* ]]; then
  SLUG=${BRANCH#plan/}
elif [[ "$BRANCH" == spec/* ]]; then
  SLUG=${BRANCH#spec/}
fi

# Check for active spec directory
find docs/spec/active -maxdepth 1 -type d -name "*${SLUG}*" 2>/dev/null | head -1
```

If a spec is detected, offer to associate the memory with it.

**AskUserQuestion for Spec Association:**
```
Use AskUserQuestion with:
  header: "Spec"
  question: "Associate this memory with spec '${SPEC_NAME}'?"
  multiSelect: false
  options:
    - label: "Yes, associate with ${SPEC_NAME}"
      description: "Memory will be searchable within this spec's context"
    - label: "No, make it global"
      description: "Memory applies broadly, not spec-specific"
```

## Phase 4: Capture Memory

Execute the capture using the CaptureService.

```python
# This is pseudo-code showing the capture flow
from memory.capture import CaptureService
from memory.git_ops import GitOps

capture = CaptureService()

# For decision type:
result = capture.capture_decision(
    spec=spec_slug,
    summary=summary,
    context=context,
    rationale=rationale,
    alternatives=alternatives,
    tags=tags,
)

# For learning type:
result = capture.capture_learning(
    spec=spec_slug,
    summary=summary,
    insight=insight,
    applicability=applicability,
    tags=tags,
)

# For blocker type:
result = capture.capture_blocker(
    spec=spec_slug,
    summary=summary,
    problem=problem,
    tags=tags,
)
```

**Actual capture commands** (run via bash):
```bash
# Get current commit
COMMIT_SHA=$(git rev-parse HEAD)

# Create note content with YAML front matter
# (The actual implementation uses the Python capture service)
```

## Phase 5: Confirm Capture

Display confirmation with the memory ID and attached commit.

```
Memory captured successfully:

+----------------------------------------------------------------+
| TYPE: ${TYPE}                                                   |
| ID: ${NAMESPACE}:${COMMIT_SHA}                                  |
| COMMIT: ${COMMIT_SHA:0:8} - "${COMMIT_MESSAGE}"                 |
| SPEC: ${SPEC_SLUG:-"(global)"}                                  |
+----------------------------------------------------------------+
| SUMMARY: ${SUMMARY}                                             |
+----------------------------------------------------------------+

The memory is now:
✓ Attached to Git commit ${COMMIT_SHA:0:8}
✓ Indexed for semantic search
✓ Searchable via /cs:recall

To view: git notes --ref=cs/${NAMESPACE} show ${COMMIT_SHA}
```

</execution_protocol>

<output_format>
After capture, always display:
1. Confirmation box with memory details
2. Commit SHA the memory is attached to
3. Instructions for viewing the raw note
4. Suggestion to use `/cs:recall` to search
</output_format>

<error_handling>
Handle these error cases gracefully:

| Error | Message | Recovery |
|-------|---------|----------|
| No commits | "Cannot capture: repository has no commits" | "Create at least one commit first" |
| Lock timeout | "Another capture in progress" | "Wait and retry" |
| Embedding failed | "Memory saved but not indexed" | "Run /cs:memory reindex" |
</error_handling>
