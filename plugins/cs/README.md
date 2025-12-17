# Claude Spec Plugin

A comprehensive Claude Code plugin for project specification and implementation lifecycle management.

## Features

- **`/cs:*` Commands** - Full project planning lifecycle
  - `/cs:p` - Strategic project planning with Socratic requirements elicitation
  - `/cs:i` - Implementation progress tracking with document sync
  - `/cs:s` - Portfolio and project status monitoring
  - `/cs:c` - Project close-out and archival
  - `/cs:log` - Prompt capture toggle
  - `/cs:migrate` - Migration from legacy `/arch:*` commands

- **`/cs:wt:*` Worktree Commands** - Git worktree automation
  - `/cs:wt:create` - Create worktrees with Claude agents
  - `/cs:wt:status` - View worktree status
  - `/cs:wt:cleanup` - Clean up worktrees

- **Prompt Capture** - Session logging for traceability and retrospectives

- **Automatic PR Management** - Draft PR creation on `/cs:p`, ready-for-review on `/cs:c`

- **Parallel Agent Orchestration** - Built-in directives for parallel specialist agent usage

## Installation

### From GitHub (Recommended)

```
/plugin marketplace add zircote/claude-spec
/plugin install cs@claude-spec-marketplace
```

### From Local Clone (Development)

```bash
git clone https://github.com/zircote/claude-spec.git
cd claude-spec
claude plugins install --marketplace ./.claude-plugin/marketplace.json cs
```

## Usage

### Start a New Project

```
/cs:p my new feature idea
```

This initiates Socratic requirements elicitation, parallel research, and generates:
- `docs/spec/active/YYYY-MM-DD-project-slug/`
  - README.md
  - REQUIREMENTS.md
  - ARCHITECTURE.md
  - IMPLEMENTATION_PLAN.md
  - DECISIONS.md
  - RESEARCH_NOTES.md
  - CHANGELOG.md

### Track Implementation Progress

```
/cs:i project-slug
```

Creates and maintains PROGRESS.md, syncs checkboxes across documents.

### Check Project Status

```
/cs:s              # Current project status
/cs:s --list       # List all active projects
/cs:s --expired    # Find expired plans
```

### Close Out Project

```
/cs:c project-slug
```

Generates RETROSPECTIVE.md, archives to `docs/spec/completed/`.

### Worktree Management

```
# Natural language triggers
"spin up worktrees for feature/auth, feature/payments"
"worktree status"
"cleanup the auth worktree"

# Or explicit commands
/cs:wt:create feature/auth feature/payments
/cs:wt:status
/cs:wt:cleanup feature/auth
```

### Prompt Capture

```
/cs:log on      # Enable prompt capture
/cs:log off     # Disable prompt capture
/cs:log status  # Check status
/cs:log show    # View captured prompts
```

### Automatic PR Management

When enabled in lifecycle configuration, PRs are automatically managed:

**On `/cs:p` (planning):**
- Creates draft PR with `[WIP]` title prefix
- Adds `spec` and `work-in-progress` labels
- Links PR to project branch

**On `/cs:c` (close-out):**
- Converts draft to ready-for-review
- Removes `[WIP]` prefix from title
- Removes `work-in-progress` label
- Optionally requests reviewers

**Requirements:**
- `gh` CLI installed and authenticated
- Git repository with remote configured
- Branch pushed to remote

**Configuration** (in `~/.claude/worktree-manager.config.json`):
```json
{
  "lifecycle": {
    "commands": {
      "cs:p": {
        "postSteps": [{
          "name": "pr-manager",
          "enabled": true,
          "operation": "create",
          "labels": ["spec", "work-in-progress"],
          "title_format": "[WIP] {slug}: {project_name}",
          "base_branch": "main"
        }]
      },
      "cs:c": {
        "postSteps": [{
          "name": "pr-manager",
          "enabled": true,
          "operation": "ready",
          "remove_labels": ["work-in-progress"],
          "reviewers": []
        }]
      }
    }
  }
}
```

**Fail-open design:** If `gh` CLI is unavailable, the step warns but doesn't block the command.

### Migration from /arch:*

```
/cs:migrate
```

Moves `docs/architecture/` to `docs/spec/` and updates CLAUDE.md references.

## Configuration

### Worktree Configuration

Your worktree settings are stored at `~/.claude/worktree-manager.config.json`.

Run `/cs:wt:setup` to configure, or see `~/.claude/plugins/skills/worktree-manager/SKILL.md` for first-time setup instructions.

```json
{
  "terminal": "iterm2-tab",
  "shell": "zsh",
  "claudeCommand": "cc",
  "portPool": { "start": 8100, "end": 8199 },
  "portsPerWorktree": 2,
  "worktreeBase": "~/Projects/worktrees"
}
```

Config lookup: user config → `~/.claude/plugins/skills/worktree-manager/config.template.json` → defaults

## Project Structure

```
docs/spec/
├── active/           # In-progress projects
│   └── YYYY-MM-DD-slug/
│       ├── README.md
│       ├── REQUIREMENTS.md
│       ├── ARCHITECTURE.md
│       ├── IMPLEMENTATION_PLAN.md
│       ├── PROGRESS.md
│       ├── DECISIONS.md
│       ├── RESEARCH_NOTES.md
│       ├── CHANGELOG.md
│       └── .prompt-log-enabled
└── completed/        # Archived projects
    └── YYYY-MM-DD-slug/
        └── (same + RETROSPECTIVE.md)
```

## Requirements

- Claude Code CLI
- Git (for worktree operations)
- Python 3 (for hooks)
- jq (for registry operations)
- Terminal app (iTerm2, Ghostty, tmux, etc.)
- gh CLI (optional, for automatic PR management)

## Attribution

The worktree management functionality is based on the original `worktree-manager` skill.

## License

MIT
