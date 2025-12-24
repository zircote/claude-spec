---
document_type: architecture
project_id: SPEC-2025-12-24-001
version: 1.0.0
last_updated: 2025-12-24T17:00:00Z
status: draft
---

# GitHub Issues Worktree Workflow - Technical Architecture

## System Overview

This feature integrates GitHub Issues into the `/claude-spec:plan` command workflow by:

1. Detecting when the command is run without arguments
2. Fetching issues from GitHub via the `gh` CLI
3. Presenting issues for user selection via AskUserQuestion
4. Creating worktrees with conventional branch naming
5. Evaluating issue completeness before planning
6. Enabling clarification comments to be posted back to GitHub

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User Invocation                                │
│                    /claude-spec:plan (no args)                          │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Argument Detection                                │
│                                                                         │
│  Step 0 Extended:                                                       │
│  - existing_file → migration_protocol                                   │
│  - project_reference → redirect                                         │
│  - new_seed → standard planning                                         │
│  - NO_ARGS → github_issues_workflow ★ NEW                               │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     GitHub Issues Workflow                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│   │  Prerequisites  │───►│  Fetch Issues   │───►│ Present Options │     │
│   │  Check          │    │  via gh CLI     │    │ AskUserQuestion │     │
│   └─────────────────┘    └─────────────────┘    └────────┬────────┘     │
│                                                          │              │
│         ┌────────────────────────────────────────────────┘              │
│         │                                                               │
│         ▼                                                               │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│   │  User Selects   │───►│ Create          │───►│ Evaluate        │     │
│   │  Issues         │    │ Worktrees       │    │ Completeness    │     │
│   └─────────────────┘    └─────────────────┘    └────────┬────────┘     │
│                                                          │              │
│         ┌────────────────────────────────────────────────┘              │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Completeness Decision                        │   │
│  │                                                                  │   │
│  │  ┌───────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────┐ │   │
│  │  │Post Comment   │ │Add Details   │ │Proceed       │ │Skip     │ │   │
│  │  │(Draft+Confirm)│ │Inline        │ │Anyway        │ │Issue    │ │   │
│  │  └──────┬────────┘ └──────┬───────┘ └──────┬───────┘ └────┬────┘ │   │
│  │         │                 │                │              │      │   │
│  │         ▼                 ▼                ▼              ▼      │   │
│  │  ┌───────────────┐ ┌──────────────┐ ┌──────────────┐  (remove    │   │
│  │  │gh issue       │ │User provides │ │Launch Agent  │  from       │   │
│  │  │comment        │ │context, then │ │with issue    │  queue)     │   │
│  │  │--body "..."   │ │Launch Agent  │ │context       │             │   │
│  │  └───────────────┘ └──────────────┘ └──────────────┘             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision           | Choice                                  | Rationale                                           |
| ------------------ | --------------------------------------- | --------------------------------------------------- |
| Argument detection | Add `no_args` case to Step 0            | Minimal change to existing flow                     |
| GitHub integration | `gh` CLI subprocess                     | Leverages user's existing auth, no token management |
| Issue presentation | AskUserQuestion multi-select            | Consistent with plugin UX patterns                  |
| Branch naming      | Auto-detect from labels                 | Aligns with conventional commits                    |
| Parallel worktrees | Port pre-allocation, parallel terminals | Reuses existing infrastructure                      |
| Completeness check | AI evaluation                           | Flexible, context-aware assessment                  |
| Comment posting    | Draft → confirm → post                  | Prevents accidental posts                           |

## Component Design

### Component 1: Argument Parser Extension (plan.md)

- **Purpose**: Detect when no arguments provided and route to GitHub workflow
- **Responsibilities**:
  - Parse command arguments
  - Classify argument type (existing_file, project_reference, new_seed, **no_args**)
  - Route to appropriate workflow
- **Interfaces**: Standard bash argument parsing
- **Dependencies**: None (entry point)
- **Technology**: Bash in markdown command file

```bash
# Extended Step 0: Parse Argument Type
ARG="${1:-}"

if [ -z "$ARG" ]; then
  ARG_TYPE="no_args"
  echo "ARG_TYPE=no_args"
elif [ -f "$ARG" ]; then
  ARG_TYPE="existing_file"
  # ... existing logic
fi
```

### Component 2: Prerequisites Checker

- **Purpose**: Verify `gh` CLI is available and authenticated
- **Responsibilities**:
  - Check `gh` CLI installed
  - Verify authentication status
  - Detect current repository's GitHub remote
- **Interfaces**: Bash functions returning exit codes
- **Dependencies**: `gh` CLI
- **Technology**: Bash

```bash
check_gh_prerequisites() {
  # Check gh installed
  if ! command -v gh &>/dev/null; then
    echo "ERROR: gh CLI not installed. Install from https://cli.github.com/"
    return 1
  fi

  # Check authenticated
  if ! gh auth status &>/dev/null; then
    echo "ERROR: Not authenticated. Run: gh auth login"
    return 1
  fi

  # Get repo
  REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null)
  if [ -z "$REPO" ]; then
    echo "ERROR: Not in a GitHub repository"
    return 1
  fi

  echo "REPO=$REPO"
  return 0
}
```

### Component 3: Issue Fetcher

- **Purpose**: Retrieve issues from GitHub based on filters
- **Responsibilities**:
  - Build `gh issue list` command with appropriate filters
  - Parse JSON output into usable format
  - Handle pagination for large issue counts
- **Interfaces**: Returns JSON array of issues
- **Dependencies**: `gh` CLI, `jq`
- **Technology**: Bash + jq

```bash
fetch_issues() {
  local repo="$1"
  local labels="${2:-}"       # Comma-separated: "enhancement,bug"
  local assignee="${3:-}"     # "@me" or username
  local limit="${4:-30}"

  local cmd="gh issue list --repo $repo --state open --json number,title,labels,assignees,body,url --limit $limit"

  if [ -n "$labels" ]; then
    IFS=',' read -ra LABELS <<< "$labels"
    for label in "${LABELS[@]}"; do
      cmd+=" --label \"$label\""
    done
  fi

  if [ -n "$assignee" ]; then
    cmd+=" --assignee \"$assignee\""
  fi

  eval "$cmd"
}
```

### Component 4: Issue Selector (AskUserQuestion Integration)

- **Purpose**: Present issues to user for selection
- **Responsibilities**:
  - Transform issue JSON into AskUserQuestion format
  - Support multi-select
  - Handle pagination (max 4 options per question, multiple questions)
  - Parse user selections
- **Interfaces**: AskUserQuestion tool invocation
- **Dependencies**: Claude tool system
- **Technology**: Prompt engineering within plan.md

**Question Schema**:

```yaml
header: "Issues"
question: "Select issues to work on (multi-select):"
multiSelect: true
options:
  - label: "#42 - Fix authentication bug"
    description: "Labels: bug, security | Assignee: @me"
  - label: "#38 - Add dark mode support"
    description: "Labels: enhancement | No assignee"
  - label: "#35 - Update API documentation"
    description: "Labels: documentation | Assignee: @other"
```

### Component 5: Label-to-Prefix Mapper

- **Purpose**: Convert GitHub issue labels to conventional commit branch prefixes
- **Responsibilities**:
  - Map known labels to prefixes
  - Handle multiple labels (priority order)
  - Default to `feat/` when uncertain
- **Interfaces**: Function taking labels, returning prefix
- **Dependencies**: None
- **Technology**: Bash

```bash
get_branch_prefix() {
  local labels="$1"  # JSON array: ["bug", "security"]

  # Priority order: bug > docs > chore > feat
  if echo "$labels" | jq -e 'index("bug")' >/dev/null 2>&1; then
    echo "bug"
    return
  fi

  if echo "$labels" | jq -e 'any(. == "documentation" or . == "docs")' >/dev/null 2>&1; then
    echo "docs"
    return
  fi

  if echo "$labels" | jq -e 'any(. == "chore" or . == "maintenance")' >/dev/null 2>&1; then
    echo "chore"
    return
  fi

  # Default: enhancement → feat
  echo "feat"
}

generate_branch_name() {
  local issue_number="$1"
  local title="$2"
  local labels="$3"

  local prefix=$(get_branch_prefix "$labels")
  local slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40)

  echo "${prefix}/${issue_number}-${slug}"
}
```

### Component 6: Worktree Creator

- **Purpose**: Create git worktrees for selected issues
- **Responsibilities**:
  - Allocate ports for all worktrees
  - Create worktrees with appropriate branches
  - Register in global registry
  - Store issue metadata in worktree
- **Interfaces**: Calls existing worktree scripts
- **Dependencies**:
  - `skills/worktree-manager/scripts/allocate-ports.sh`
  - `skills/worktree-manager/scripts/register.sh`
- **Technology**: Bash

```bash
create_issue_worktree() {
  local issue="$1"  # JSON object
  local worktree_base="$2"
  local repo_path="$3"

  local number=$(echo "$issue" | jq -r '.number')
  local title=$(echo "$issue" | jq -r '.title')
  local labels=$(echo "$issue" | jq -c '.labels[].name')
  local body=$(echo "$issue" | jq -r '.body')
  local url=$(echo "$issue" | jq -r '.url')

  # Generate branch name
  local branch=$(generate_branch_name "$number" "$title" "$labels")
  local slug=$(echo "$branch" | tr '/' '-')
  local worktree_path="${worktree_base}/${slug}"

  # Allocate ports
  local ports=$(./scripts/allocate-ports.sh 2)

  # Create worktree
  git worktree add -b "$branch" "$worktree_path" HEAD

  # Save issue metadata
  cat > "${worktree_path}/.issue-context.json" << EOF
{
  "number": $number,
  "title": "$title",
  "url": "$url",
  "body": $(echo "$body" | jq -Rs .),
  "labels": $labels
}
EOF

  # Register
  ./scripts/register.sh "$PROJECT" "$branch" "$slug" "$worktree_path" "$repo_path" "$ports" "Issue #$number"

  echo "$worktree_path"
}
```

### Component 7: Completeness Evaluator

- **Purpose**: Assess if an issue has sufficient detail for planning
- **Responsibilities**:
  - Analyze issue body content
  - Check for acceptance criteria, reproduction steps, context
  - Generate assessment with reasoning
- **Interfaces**: Claude reasoning (not a separate script)
- **Dependencies**: None (AI evaluation)
- **Technology**: Prompt within plan.md

**Evaluation Criteria** (AI assessment):

1. **Clear problem statement**: Does the issue explain what needs to be done?
2. **Context**: Is there enough background to understand why this matters?
3. **Scope indicators**: Are boundaries mentioned (what's in/out of scope)?
4. **Acceptance criteria**: Are there success conditions or test cases?
5. **Reproducibility** (for bugs): Are reproduction steps provided?

**Assessment Output**:

```
Completeness Assessment for Issue #42:

VERDICT: NEEDS_CLARIFICATION

PRESENT:
- Clear problem statement (authentication fails on mobile)
- Bug label indicates type

MISSING:
- Steps to reproduce
- Expected vs actual behavior
- Browser/device information

RECOMMENDATION: Request reproduction steps and environment details.
```

### Component 8: Comment Drafter

- **Purpose**: Generate professional clarification requests
- **Responsibilities**:
  - Analyze what's missing from issue
  - Draft polite, actionable comment
  - Format with markdown
- **Interfaces**: Claude text generation
- **Dependencies**: None
- **Technology**: Prompt engineering

**Comment Template Style**:

```markdown
Thanks for opening this issue. To help us move forward efficiently, could you please provide:

1. **[Missing Item 1]**: [Specific question]
2. **[Missing Item 2]**: [Specific question]

This information will help us understand the scope and prioritize accordingly.
```

### Component 9: Comment Poster

- **Purpose**: Post comments to GitHub issues after user approval
- **Responsibilities**:
  - Show draft to user
  - Get explicit confirmation
  - Execute `gh issue comment`
  - Report success/failure
- **Interfaces**: Bash wrapper around `gh` CLI
- **Dependencies**: `gh` CLI
- **Technology**: Bash

```bash
post_issue_comment() {
  local repo="$1"
  local issue_number="$2"
  local comment_body="$3"

  gh issue comment "$issue_number" --repo "$repo" --body "$comment_body"
}
```

### Component 10: Agent Launcher

- **Purpose**: Launch Claude agents in new terminals for each worktree
- **Responsibilities**:
  - Build initial prompt with issue context
  - Launch agents in parallel
  - Report status
- **Interfaces**: Calls existing launch-agent.sh
- **Dependencies**:
  - `skills/worktree-manager/scripts/launch-agent.sh`
- **Technology**: Bash

```bash
launch_issue_agent() {
  local worktree_path="$1"
  local issue_number="$2"
  local issue_title="$3"

  # Build prompt that includes issue context
  local prompt="/claude-spec:plan Issue #${issue_number}: ${issue_title}"

  ./scripts/launch-agent.sh "$worktree_path" "" --prompt "$prompt"
}
```

## Data Design

### Data Models

**Issue Context File** (`.issue-context.json` in worktree):

```json
{
  "number": 42,
  "title": "Fix authentication bug on mobile",
  "url": "https://github.com/owner/repo/issues/42",
  "body": "Full issue body text...",
  "labels": ["bug", "security"],
  "fetched_at": "2025-12-24T17:00:00Z"
}
```

**Worktree Registry Entry** (extended):

```json
{
  "id": "uuid",
  "project": "my-project",
  "branch": "bug/42-fix-auth-mobile",
  "worktreePath": "/path/to/worktree",
  "ports": [8100, 8101],
  "createdAt": "2025-12-24T17:00:00Z",
  "task": "Issue #42",
  "issueNumber": 42,
  "issueUrl": "https://github.com/owner/repo/issues/42"
}
```

### Data Flow

```
GitHub API
    │
    ▼
gh issue list --json
    │
    ▼
┌───────────────┐
│ Issue JSON    │ ──► AskUserQuestion options
│ - number      │
│ - title       │
│ - labels      │
│ - body        │
│ - assignees   │
└───────────────┘
        │
        ▼ (user selection)
┌───────────────┐
│ Selected      │ ──► Branch naming
│ Issues        │ ──► Worktree creation
│               │ ──► .issue-context.json
└───────────────┘
        │
        ▼
┌───────────────┐
│ Worktree      │ ──► Registry update
│ Created       │ ──► Agent launch with context
└───────────────┘
```

## Integration Points

### Internal Integrations

| System                   | Integration Type | Purpose                                     |
| ------------------------ | ---------------- | ------------------------------------------- |
| plan.md                  | Extension        | Add no_args argument type handling          |
| worktree-manager scripts | Subprocess       | Port allocation, registration, agent launch |
| AskUserQuestion          | Tool invocation  | Issue selection UX                          |
| Global registry          | JSON update      | Track issue-linked worktrees                |

### External Integrations

| Service           | Integration Type    | Purpose                     |
| ----------------- | ------------------- | --------------------------- |
| GitHub API        | Via `gh` CLI        | Fetch issues, post comments |
| Terminal emulator | Via launch-agent.sh | Open new terminals          |

## Security Design

### Authentication

- Delegated to `gh` CLI (uses keychain/credential store)
- No token storage in plugin
- Auth status checked before any operation

### Authorization

- Read access: User must have read access to repository issues
- Write access: Only for posting comments (requires explicit confirmation)

### Data Protection

- Issue body may contain sensitive info - stays in worktree, not logged
- Comments only posted after user reviews draft
- Branch names sanitized to prevent command injection

### Security Considerations

| Threat                            | Mitigation                                              |
| --------------------------------- | ------------------------------------------------------- |
| Command injection via issue title | Sanitize all user input before shell commands           |
| Accidental comment posting        | Require explicit confirmation before `gh issue comment` |
| Token exposure                    | Never log or display tokens; delegate to `gh auth`      |
| Malicious issue body              | Treat body as untrusted; don't execute any code from it |

## Testing Strategy

### Unit Testing

- Label-to-prefix mapping (all known labels)
- Branch name generation (special characters, long titles)
- Issue JSON parsing

### Integration Testing

- Mock `gh` CLI responses
- Worktree creation end-to-end
- Registry updates

### End-to-End Testing

- Full flow with real GitHub repo (manual)
- Comment posting with test issue (manual, then delete comment)

## Deployment Considerations

### Environment Requirements

- `gh` CLI >= 2.0 installed
- Authenticated via `gh auth login`
- Git repository with GitHub remote
- macOS or Linux (bash scripts)

### Configuration

No additional configuration required. Uses existing:

- `~/.claude/claude-spec.config.json` for worktree settings
- `gh` CLI's authentication

### Rollout Strategy

1. Implement in plan.md as conditional logic
2. Test with single-issue flow
3. Enable multi-issue parallel flow
4. Add completeness evaluation
5. Add comment posting

### Rollback Plan

- Feature is additive (existing `/plan <seed>` flow unchanged)
- If issues detected, document workaround to use explicit seed
- No database migrations to revert

## Future Considerations

1. **Cross-repo issues**: Fetch from multiple repos the user contributes to
2. **Issue creation**: Allow creating new issues from `/plan` insights
3. **PR linkage**: Auto-link created worktree branches to issues
4. **Milestone filtering**: Focus on sprint-specific issues
5. **Custom label mappings**: Project-specific label-to-prefix rules
6. **Issue templates**: Detect if repo uses issue templates, guide users
