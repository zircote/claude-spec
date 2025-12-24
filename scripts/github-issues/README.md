# GitHub Issues Worktree Scripts

This directory contains shell scripts that integrate GitHub issues with Claude Code worktrees, enabling an issue-to-implementation workflow.

## Overview

These scripts support the `/claude-spec:plan` command's ability to automatically:
1. List open GitHub issues from the current repository
2. Create isolated git worktrees for issue implementation
3. Launch Claude agents with issue context
4. Post completion comments to GitHub issues

## Scripts

### Prerequisites & Validation

| Script | Purpose |
|--------|---------|
| `check-gh-prerequisites.sh` | Validates `gh` CLI authentication and repository access |

### Branch & Worktree Creation

| Script | Purpose |
|--------|---------|
| `get-branch-prefix.sh` | Maps issue labels to conventional commit prefixes (`bug/`, `feat/`, etc.) |
| `generate-branch-name.sh` | Generates safe branch names from issue title and number |
| `create-issue-worktree.sh` | Creates git worktree with `.issue-context.json` for issue |

### Prompt & Comment Generation

| Script | Purpose |
|--------|---------|
| `build-issue-prompt.sh` | Generates `/claude-spec:plan` prompt from issue data |
| `post-issue-comment.sh` | Posts completion status to GitHub issue |

## Data Flow

```
gh issue list --json ...
        │
        ▼
check-gh-prerequisites.sh  ─── Validate access
        │
        ▼
get-branch-prefix.sh  ◄─────── Map labels to prefix
        │
        ▼
generate-branch-name.sh  ──── Create branch name
        │
        ▼
create-issue-worktree.sh  ─── Create worktree + context file
        │
        ▼
build-issue-prompt.sh  ────── Generate /claude-spec:plan prompt
        │
        ▼
[Claude agent works...]
        │
        ▼
post-issue-comment.sh  ────── Report completion to GitHub
```

## Security Considerations

All scripts implement security measures:

- **Input validation**: JSON structure validated before parsing
- **Shell injection prevention**: All variables properly quoted
- **Path traversal protection**: Canonical path validation
- **Restrictive permissions**: Context files created with `chmod 600`

See `CODE_REVIEW.md` for security audit details.

## Usage

### Manual Testing

```bash
# Check prerequisites
./check-gh-prerequisites.sh

# Generate branch name
./generate-branch-name.sh 42 "Fix login bug" "bug"

# Create worktree for an issue
ISSUE_JSON=$(gh issue view 42 --json number,title,labels,body,url)
./create-issue-worktree.sh "$ISSUE_JSON"

# Build prompt for issue
./build-issue-prompt.sh "$ISSUE_JSON"
```

### Integration

These scripts are typically invoked by the `plan.md` command when run without arguments:

```bash
# Interactive issue selection
/claude-spec:plan
```

## Testing

Script tests are in `tests/test_github_issues_scripts.py`:

```bash
uv run pytest tests/test_github_issues_scripts.py -v
```

## Dependencies

- `gh` CLI (GitHub CLI) - authenticated with repo access
- `jq` - JSON parsing
- `git` - worktree operations
- Standard POSIX utilities (`tr`, `sed`, `head`, etc.)
