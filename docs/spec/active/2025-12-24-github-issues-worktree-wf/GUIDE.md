# GitHub Issues Worktree Workflow - User Guide

## Overview

The GitHub Issues Worktree Workflow allows you to quickly spin up isolated development environments for GitHub issues directly from `/claude-spec:plan`. Instead of manually creating branches and worktrees, you can:

1. Select issues from your repository
2. Have worktrees automatically created with proper branch naming
3. Launch Claude agents pre-loaded with issue context
4. Get AI-assisted completeness evaluation of issue descriptions
5. Post clarification comments directly to GitHub

## Prerequisites

Before using this feature, ensure you have:

### 1. GitHub CLI (`gh`) Installed

```bash
# macOS
brew install gh

# Ubuntu/Debian
sudo apt install gh

# Windows
winget install GitHub.cli
```

### 2. Authenticated with GitHub

```bash
gh auth login
```

Follow the prompts to authenticate via browser or token.

### 3. In a GitHub Repository

Your current directory must be a git repository with a GitHub remote:

```bash
# Check your remotes
git remote -v

# If no GitHub remote exists, add one
git remote add origin https://github.com/owner/repo.git
```

## Basic Usage

### Triggering the Workflow

Simply run `/claude-spec:plan` with **no arguments**:

```
/claude-spec:plan
```

If you provide an argument (e.g., `/claude-spec:plan "Add dark mode"`), the standard planning workflow runs instead.

### Step-by-Step Flow

#### 1. Filter Selection

You'll be asked how to filter issues:

| Option | Description |
|--------|-------------|
| All open issues | Show all open issues (up to 30) |
| Filter by labels | Only issues with specific labels |
| Assigned to me | Only issues assigned to your account |
| Filter by labels + assigned to me | Combine both filters |

#### 2. Label Selection (if filtering)

If you chose to filter by labels, you'll see the repository's labels:

```
Select labels to filter by:
- bug (Bug reports)
- enhancement (Feature requests)
- documentation (Documentation changes)
- good first issue (Beginner-friendly)
```

Common labels appear first for convenience.

#### 3. Issue Selection

Issues are presented in batches of 4 (AskUserQuestion limit):

```
Select issues to work on (batch 1 of 3):
- #42 - Fix authentication bug on mobile dev...
  Labels: bug, security | Assignee: @johndoe
- #38 - Add dark mode support for user inter...
  Labels: enhancement | Assignee: Unassigned
```

Multi-select is enabled - choose as many as you want.

#### 4. Branch Name Preview

Before creating worktrees, you'll see the planned branches:

```
Planned worktrees:
1. bug/42-fix-authentication-bug-on-mobile
2. feat/38-add-dark-mode-support
3. docs/35-update-api-documentation

Create these worktrees? [Yes, create all / Modify selection / Cancel]
```

#### 5. Completeness Evaluation

For each issue, Claude evaluates if it has enough detail:

```
Completeness Assessment for Issue #42: Fix authentication bug

VERDICT: NEEDS_CLARIFICATION

PRESENT:
✓ Clear problem statement (authentication fails on mobile)
✓ Bug label indicates issue type

MISSING:
✗ Steps to reproduce
✗ Expected vs actual behavior
✗ Browser/device information
```

You can then choose to:
- **Proceed anyway** - Plan with available information
- **Post clarification request** - Draft and post a comment to GitHub
- **Add details inline** - Provide context yourself
- **Skip this issue** - Don't create a worktree

#### 6. Comment Posting (Optional)

If you chose to post a clarification request:

1. Claude drafts a professional comment
2. You review and can edit it
3. Confirm to post directly to GitHub

```
Thanks for opening this issue.

To help us plan an effective solution, could you please provide:

1. **Steps to reproduce**: What actions lead to the authentication failure?
2. **Expected behavior**: What should happen after login on mobile?
...
```

#### 7. Agent Launch

For each worktree, a new terminal opens with Claude pre-loaded:

```
GitHub Issues Workflow Complete!

Created 2 worktrees with Claude agents:

1. Issue #42: Fix authentication bug
   Branch: bug/42-fix-authentication-bug-on-mobile
   Location: ~/Projects/worktrees/my-repo/bug-42-fix-...
   Terminal: Launched ✓

2. Issue #38: Add dark mode support
   Branch: feat/38-add-dark-mode-support
   Location: ~/Projects/worktrees/my-repo/feat-38-add-...
   Terminal: Launched ✓
```

Switch to any terminal to begin planning for that issue.

## Branch Naming Convention

Branches are named following conventional commits based on issue labels:

| Label(s) | Branch Prefix | Example |
|----------|---------------|---------|
| `bug`, `defect`, `fix` | `bug/` | `bug/42-fix-auth-bug` |
| `documentation`, `docs` | `docs/` | `docs/35-update-readme` |
| `chore`, `maintenance`, `refactor` | `chore/` | `chore/99-cleanup-deps` |
| `enhancement`, `feature`, (default) | `feat/` | `feat/38-add-dark-mode` |

Priority order: bug > docs > chore > feat

## Issue Context File

Each worktree contains `.issue-context.json` with full issue details:

```json
{
  "number": 42,
  "title": "Fix authentication bug on mobile",
  "url": "https://github.com/owner/repo/issues/42",
  "body": "Full issue description...",
  "labels": ["bug", "security"],
  "fetched_at": "2025-12-24T17:00:00Z"
}
```

The agent reads this automatically when `/claude-spec:plan` runs in the worktree.

## Managing Worktrees

### Check Status

```
/claude-spec:worktree-status
```

### Cleanup

```
/claude-spec:worktree-cleanup
```

## Troubleshooting

### "gh CLI not installed"

Install the GitHub CLI from https://cli.github.com/

### "Not authenticated"

Run `gh auth login` and complete the authentication flow.

### "Not in a GitHub repository"

Ensure you're in a git repo with a GitHub remote:
```bash
git remote -v
```

### "No open issues found"

- Check if your repository has open issues
- Try different filters (remove label/assignee filters)
- Ensure you have read access to the repository

### Worktree creation fails

- Check for existing branches with the same name: `git branch -a`
- Remove conflicting worktrees: `git worktree prune`

## Tips

1. **Start fresh**: Use "All open issues" first to see what's available
2. **Prioritize**: Select 2-3 issues max per session for focus
3. **Use labels wisely**: Good labeling in GitHub = better branch names
4. **Review completeness**: The AI evaluation helps catch under-specified issues early
5. **Post comments**: Asking for clarification upfront saves implementation time later

## Related Commands

| Command | Purpose |
|---------|---------|
| `/claude-spec:plan <idea>` | Standard planning with a seed idea |
| `/claude-spec:implement <slug>` | Track implementation progress |
| `/claude-spec:status` | View project status |
| `/claude-spec:complete <slug>` | Close out a project |
| `/claude-spec:worktree-create` | Manual worktree creation |
