# claude-spec

A comprehensive Claude Code plugin for project specification and implementation lifecycle management.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

**claude-spec** transforms AI-assisted development by providing structured project planning, implementation tracking, and retrospective analysis. It enforces the principle that *great planning is great prompting* — the quality of your plan determines the quality of execution.

### Key Features

- **Socratic Requirements Elicitation** — Guided questioning to achieve clarity before coding
- **Parallel Agent Orchestration** — Leverage specialist subagents for research and implementation
- **Document Synchronization** — Keep PROGRESS.md, IMPLEMENTATION_PLAN.md, and README.md in sync
- **Prompt Capture & Retrospectives** — Log interactions for learning and improvement
- **Git Worktree Automation** — Isolated development environments with Claude agents

## Installation

### From Local Marketplace

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/claude-spec.git
   cd claude-spec
   ```

2. **Install the plugin:**
   ```bash
   claude plugins install --marketplace ./.claude-plugin/marketplace.json cs
   ```

3. **Verify installation:**
   ```bash
   claude plugins list
   ```

### Manual Installation

1. Create local marketplace configuration:
   ```bash
   mkdir -p ~/.claude/marketplaces
   cat > ~/.claude/marketplaces/claude-spec.json << 'EOF'
   {
     "name": "claude-spec-marketplace",
     "plugins": [
       {
         "name": "cs",
         "path": "/path/to/claude-spec/plugins/cs"
       }
     ]
   }
   EOF
   ```

2. Install:
   ```bash
   claude plugins install --marketplace ~/.claude/marketplaces/claude-spec.json cs
   ```

## Quick Start

### 1. Start a New Project

```
/cs:p implement user authentication with OAuth
```

This initiates:
- Socratic requirements elicitation (3-4 questions at a time)
- Parallel research with specialist agents
- Generation of full artifact set in `docs/spec/active/`

### 2. Track Implementation

```
/cs:i user-auth
```

Creates/updates PROGRESS.md, tracks task completion, syncs checkboxes across documents.

### 3. Monitor Status

```
/cs:s --list        # List all active projects
/cs:s user-auth     # View specific project
/cs:s --expired     # Find stale plans
```

### 4. Close Out Project

```
/cs:c user-auth
```

Generates retrospective, archives to `docs/spec/completed/`, analyzes prompt logs.

## Commands Reference

| Command | Description |
|---------|-------------|
| `/cs:p <idea>` | Strategic project planning with Socratic requirements elicitation |
| `/cs:i [project]` | Implementation progress tracking with document sync |
| `/cs:s [options]` | Project status and portfolio management |
| `/cs:c <project>` | Project close-out with retrospective generation |
| `/cs:log <action>` | Toggle prompt capture logging (on/off/status/show) |
| `/cs:migrate` | Migrate from `docs/architecture/` to `docs/spec/` |
| `/cs:wt:create <branch>` | Create git worktree with Claude agent |
| `/cs:wt:status` | Show worktree status |
| `/cs:wt:cleanup` | Clean up stale worktrees |

## Project Structure

When you run `/cs:p`, the following structure is created:

```
docs/spec/
├── active/                           # In-progress projects
│   └── 2025-12-12-user-auth/
│       ├── README.md                 # Project metadata & quick links
│       ├── REQUIREMENTS.md           # Product Requirements Document
│       ├── ARCHITECTURE.md           # Technical design
│       ├── IMPLEMENTATION_PLAN.md    # Phased task breakdown
│       ├── PROGRESS.md               # Implementation tracking
│       ├── DECISIONS.md              # Architecture Decision Records
│       ├── RESEARCH_NOTES.md         # Research findings
│       ├── CHANGELOG.md              # Plan evolution history
│       └── .prompt-log-enabled       # Marker for prompt logging
│
├── approved/                         # Approved, awaiting implementation
├── completed/                        # Archived with retrospectives
└── superseded/                       # Replaced by newer plans
```

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  /cs:p "project idea"                                       │
│  ├── Worktree check (recommend isolation)                   │
│  ├── Socratic questioning (7 clarity checkpoints)           │
│  ├── Parallel research (4 specialist subagents)             │
│  └── Generate: REQUIREMENTS → ARCHITECTURE → IMPL_PLAN      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  /cs:i project-slug                                         │
│  ├── Create/load PROGRESS.md                                │
│  ├── Mark tasks in-progress → done                          │
│  ├── Sync checkboxes to IMPLEMENTATION_PLAN.md              │
│  └── Log divergences from original plan                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  /cs:s --list                                               │
│  ├── View portfolio health                                  │
│  ├── Find expired plans                                     │
│  └── Cleanup recommendations                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  /cs:c project-slug                                         │
│  ├── Generate RETROSPECTIVE.md                              │
│  ├── Analyze .prompt-log.json                               │
│  ├── Archive to docs/spec/completed/                        │
│  └── Update CLAUDE.md references                            │
└─────────────────────────────────────────────────────────────┘
```

## Prompt Capture

The plugin can log all user prompts during spec work for retrospective analysis.

### Enable/Disable

```
/cs:log on       # Enable for current active project
/cs:log off      # Disable logging
/cs:log status   # Check current status
/cs:log show     # View recent log entries
```

### What's Logged

- User prompts (with secrets automatically filtered)
- Session IDs and timestamps
- Commands used (`/cs:p`, `/cs:i`, etc.)

### Secret Filtering

The following are automatically detected and replaced with `[SECRET:type]`:
- AWS access keys and secrets
- GitHub tokens (PAT, OAuth, App)
- OpenAI and Anthropic API keys
- Database connection strings
- JWTs and bearer tokens
- Private key headers

## Worktree Management

Isolate spec work in git worktrees with automatic Claude agent launching.

### Create Worktree

```
/cs:wt:create user-auth                    # Creates plan/user-auth branch
/cs:wt:create user-auth --base develop     # Branch from develop
/cs:wt:create user-auth --prompt "/cs:p"   # Auto-run command in new terminal
```

### Natural Language Triggers

The included `worktree-manager` skill responds to:
- "spin up worktrees for feature/auth, feature/payments"
- "worktree status"
- "cleanup the auth worktree"

### Template Variables

When using `--prompt`, these variables are substituted:
- `{{service}}` / `{{branch_slug}}` — Branch slug (e.g., "feature-auth")
- `{{branch}}` — Full branch name (e.g., "feature/auth")
- `{{project}}` — Project name
- `{{port}}` / `{{ports}}` — Allocated ports

### Configuration

Edit `skills/worktree-manager/config.json`:

```json
{
  "terminal": "iterm2",
  "shell": "bash",
  "claudeCommand": "cc",
  "portPool": { "start": 8100, "end": 8199 },
  "portsPerWorktree": 2,
  "worktreeBase": "~/Projects/worktrees"
}
```

Supported terminals: `ghostty`, `iterm2`, `tmux`, `wezterm`, `kitty`, `alacritty`

## Document Synchronization

The `/cs:i` command enforces document synchronization:

```
ON TASK STATUS CHANGE:
  1. Update PROGRESS.md (source of truth)
  2. Sync IMPLEMENTATION_PLAN.md checkboxes
  3. Update README.md frontmatter
  4. Add CHANGELOG.md entry if significant
```

This prevents state drift across documents in long-running projects.

## Parallel Agent Orchestration

The `/cs:p` command mandates parallel specialist agent deployment:

```
PARALLEL RESEARCH PHASE:
  Task 1: "research-analyst" - External research
  Task 2: "code-reviewer" - Analyze existing codebase
  Task 3: "security-auditor" - Security assessment
  Task 4: "performance-engineer" - Performance considerations

Wait for all → Synthesize → Continue
```

### Agent Selection Guidelines

| Research Need | Recommended Agent(s) |
|--------------|---------------------|
| Codebase analysis | `code-reviewer`, `refactoring-specialist` |
| API design | `api-designer`, `backend-developer` |
| Security review | `security-auditor`, `penetration-tester` |
| Performance | `performance-engineer`, `sre-engineer` |
| Data modeling | `data-engineer`, `postgres-pro` |

## Requirements

- **Claude Code CLI** — The plugin host
- **Git** — For worktree operations
- **Python 3** — For prompt capture hooks
- **jq** — For worktree registry operations
- **gh CLI** — Optional, for PR status checks

## Plugin Structure

```
plugins/cs/
├── .claude-plugin/plugin.json    # Plugin metadata
├── hooks/
│   ├── hooks.json                # Hook registration
│   └── prompt_capture.py         # UserPromptSubmit handler
├── filters/                      # Content filtering
│   ├── pipeline.py               # Secret detection
│   ├── log_entry.py              # Log schema
│   └── log_writer.py             # Atomic file writer
├── commands/                     # Slash commands
│   ├── p.md                      # /cs:p
│   ├── i.md                      # /cs:i
│   ├── s.md                      # /cs:s
│   ├── c.md                      # /cs:c
│   ├── log.md                    # /cs:log
│   ├── migrate.md                # /cs:migrate
│   └── wt/                       # Worktree commands
├── skills/worktree-manager/      # Worktree automation
│   ├── SKILL.md
│   ├── config.json
│   └── scripts/
└── templates/                    # Project artifact templates
```

## Migration from /arch

If you have existing projects in `docs/architecture/`:

```
/cs:migrate              # Preview changes
/cs:migrate --backup     # Create backup first
/cs:migrate --force      # Skip confirmations
```

This migrates:
- `docs/architecture/` → `docs/spec/`
- Project IDs: `ARCH-*` → `SPEC-*`
- Command references: `/arch:*` → `/cs:*`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](plugins/cs/LICENSE) for details.

## Attribution

The worktree management functionality is based on the original `worktree-manager` skill from the Claude Code ecosystem.
