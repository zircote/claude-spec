# Claude Spec Plugin

A comprehensive Claude Code plugin for project specification and implementation lifecycle management.

## Features

- **`/*` Commands** - Full project planning lifecycle
  - `/p` - Strategic project planning with Socratic requirements elicitation
  - `/i` - Implementation progress tracking with document sync
  - `/s` - Portfolio and project status monitoring
  - `/c` - Project close-out and archival
  - `/log` - Prompt capture toggle
  - `/migrate` - Migration from legacy `/arch:*` commands

- **`/claude-spec:worktree-*` Worktree Commands** - Git worktree automation
  - `/claude-spec:worktree-create` - Create worktrees with Claude agents
  - `/claude-spec:worktree-status` - View worktree status
  - `/claude-spec:worktree-cleanup` - Clean up worktrees

- **Prompt Capture** - Session logging for traceability and retrospectives

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
/p my new feature idea
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
/i project-slug
```

Creates and maintains PROGRESS.md, syncs checkboxes across documents.

### Check Project Status

```
/s              # Current project status
/s --list       # List all active projects
/s --expired    # Find expired plans
```

### Close Out Project

```
/c project-slug
```

Generates RETROSPECTIVE.md, archives to `docs/spec/completed/`.

### Worktree Management

```
# Natural language triggers
"spin up worktrees for feature/auth, feature/payments"
"worktree status"
"cleanup the auth worktree"

# Or explicit commands
/claude-spec:worktree-create feature/auth feature/payments
/claude-spec:worktree-status
/claude-spec:worktree-cleanup feature/auth
```

### Prompt Capture

```
/log on      # Enable prompt capture
/log off     # Disable prompt capture
/log status  # Check status
/log show    # View captured prompts
```

### Migration from /arch:*

```
/migrate
```

Moves `docs/architecture/` to `docs/spec/` and updates CLAUDE.md references.

## Configuration

### Worktree Configuration

Your worktree settings are stored at `~/.claude/claude-spec.config.json`.

Run `/claude-spec:worktree-setup` to configure, or see `~/.claude/plugins/skills/worktree-manager/SKILL.md` for first-time setup instructions.

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

Config lookup: user config → `./claude-spec.config.json` (plugin root) → defaults

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

## Attribution

The worktree management functionality is based on the original `worktree-manager` skill.

## License

MIT
