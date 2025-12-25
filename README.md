# Claude Spec Plugin

A comprehensive Claude Code plugin for project specification and implementation lifecycle management.

## Features

- **Deep Analysis Commands** - Opus 4.5 optimized, parallel agent orchestration
  - `/claude-spec:deep-clean` - Comprehensive code review and remediation (6-12+ specialists)
    - Focus modes: `--focus=security`, `--focus=performance`, `--focus=maintainability`
    - Maximum coverage: `--focus=MAX` / `--focus=MAXALL`
  - `/claude-spec:deep-explore` - Exhaustive codebase exploration
  - `/claude-spec:deep-research` - Multi-phase investigation

- **Specification Lifecycle Commands** - Full project planning lifecycle
  - `/claude-spec:plan` - Strategic project planning with Socratic requirements elicitation
    - Flags: `--inline`, `--no-worktree`, `--no-branch`
  - `/claude-spec:approve` - Review and approve/reject specs before implementation
  - `/claude-spec:implement` - Implementation progress tracking with document sync
  - `/claude-spec:status` - Portfolio and project status monitoring
  - `/claude-spec:complete` - Project close-out and archival
  - `/claude-spec:report-issue` - Investigate and create AI-actionable GitHub issues
    - Flags: `--type bug|feat|docs|chore|perf`, `--repo owner/repo`

- **Worktree Commands** - Git worktree automation
  - `/claude-spec:worktree-create` - Create worktrees with Claude agents
  - `/claude-spec:worktree-status` - View worktree status
  - `/claude-spec:worktree-cleanup` - Clean up worktrees

- **Approval Workflow** - Governance controls
  - PreToolUse hook blocks implementation without approved spec
  - Audit trail with approver identity and timestamps
  - Rejection workflow with spec preservation

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
/claude-spec:plan my new feature idea
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

#### Plan Flags

| Flag | Description |
|------|-------------|
| `--inline` | Skip worktree and branch creation, work in current directory |
| `--no-worktree` | Skip worktree creation only |
| `--no-branch` | Skip branch creation only |

### Approve the Specification

```
/claude-spec:approve project-slug
```

Reviews the spec and records approval decision:
- **Approve**: Updates status, records approver and timestamp
- **Request Changes**: Adds feedback, keeps in review status
- **Reject**: Moves spec to `docs/spec/rejected/`

### Track Implementation Progress

```
/claude-spec:implement project-slug
```

Creates and maintains PROGRESS.md, syncs checkboxes across documents.
Shows warning if spec not approved (advisory, non-blocking).

### Check Project Status

```
/claude-spec:status              # Current project status
/claude-spec:status --list       # List all active projects
/claude-spec:status --expired    # Find expired plans
```

### Close Out Project

```
/claude-spec:complete project-slug
```

Generates RETROSPECTIVE.md, archives to `docs/spec/completed/`.

### Report an Issue

```
/claude-spec:report-issue
/claude-spec:report-issue --type bug
/claude-spec:report-issue --type feat --repo zircote/claude-spec
```

Investigates the codebase before filing, producing GitHub issues with rich technical context that AI tools can immediately leverage for resolution.

#### Issue Types

| Type | Label | Investigation Focus |
|------|-------|---------------------|
| `bug` | bug | Error traces, affected code paths, reproduction context |
| `feat` | enhancement | Related existing code, integration points, patterns to follow |
| `docs` | documentation | Current doc state, code it should reflect |
| `chore` | chore | Files to change, dependencies, scope of work |
| `perf` | performance | Bottleneck locations, metrics, optimization targets |

#### Workflow

1. **Input Gathering** - Collect issue type, title, description
2. **Investigation** - Explore codebase (30-60 seconds) to gather file paths, code snippets, and context
3. **Findings Review** - Present investigation results for user confirmation
4. **Repository Selection** - Detect target repo from context, confirm with user
5. **Issue Creation** - Preview and create GitHub issue with AI-actionable findings

#### Key Differentiator

Issues created by this command include investigatory findings with enough detail that an AI can immediately begin working on a fix:
- File paths with line numbers
- Code snippets showing the problem area
- Related code references (callers, tests, config)
- Root cause hypothesis
- Suggested approach (when apparent)

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

### Code Review & Remediation

```bash
# Interactive mode (asks for confirmation at each step)
/claude-spec:deep-clean

# Quick mode (Critical+High, no prompts)
/claude-spec:deep-clean --quick

# Fix everything (all severities, full verification)
/claude-spec:deep-clean --all

# Focus on specific dimension
/claude-spec:deep-clean --focus=security
/claude-spec:deep-clean --focus=performance
/claude-spec:deep-clean --focus=maintainability

# Maximum coverage (11+ agents)
/claude-spec:deep-clean --focus=MAX

# Maximum coverage + auto-remediate everything (nuclear option)
/claude-spec:deep-clean --focus=MAXALL
```

#### Focus Modes

| Mode | Agents | Behavior |
|------|--------|----------|
| (none) | 6 base | Interactive - asks for confirmation |
| `--quick` | 6 base | Critical+High only, quick verification |
| `--all` | 6 base | All severities, full verification, no prompts |
| `--focus=security` | 6 base | Enhanced security (OWASP, CVE scan, secrets) |
| `--focus=performance` | 6 base | Enhanced perf (benchmarks, query analysis) |
| `--focus=maintainability` | 6 base | Enhanced maint (tech debt, complexity) |
| `--focus=MAX` | 12+ | All enhancements, all specialists, interactive |
| `--focus=MAXALL` | 12+ | All enhancements, all specialists, auto-fix all |

#### Base Agents (6)

1. **Security Analyst** - Vulnerabilities, auth, secrets, OWASP
2. **Performance Engineer** - N+1, caching, algorithms
3. **Architecture Reviewer** - SOLID, patterns, complexity
4. **Code Quality Analyst** - DRY, dead code, naming
5. **Test Coverage Analyst** - Coverage gaps, edge cases
6. **Documentation Reviewer** - Docstrings, README, API docs

#### Additional Specialists (MAX/MAXALL modes)

- **Database Expert** - Query optimization, index analysis
- **Penetration Tester** - Deep security beyond OWASP
- **Compliance Auditor** - Regulatory patterns
- **Chaos Engineer** - Resilience, fault tolerance
- **Accessibility Tester** - WCAG compliance (if UI code)
- **Prompt Engineer** - Anthropic best practices, Claude patterns (if prompts)

## Workflow

The recommended workflow with governance controls:

```
/claude-spec:plan "idea"     Create spec in draft status
          |
/claude-spec:approve slug    Review and approve plan
          |
/claude-spec:implement slug  Track implementation (warns if not approved)
          |
/claude-spec:complete slug   Close out with retrospective
```

### Prevention Mechanisms

1. **`<never_implement>` section in plan.md** - Prevents jumping to implementation during planning
2. **`/implement` warning** - Shows advisory if spec not approved
3. **PreToolUse hook** - Optional blocking of Write/Edit without approved spec

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

Config lookup: user config -> `./claude-spec.config.json` (plugin root) -> defaults

### Hook Configuration

The PreToolUse hook that blocks implementation without approved specs is configured in `.claude-plugin/hooks.json`:

```json
{
  "hooks": [
    {
      "event": "PreToolUse",
      "matcher": { "tool_name": ["Write", "Edit"] },
      "command": "${CLAUDE_PLUGIN_ROOT}/../hooks/check-approved-spec.sh",
      "enabled": true
    }
  ]
}
```

To disable the hook, set `"enabled": false`.

## Project Structure

```
docs/spec/
+-- active/           # In-progress projects (draft, in-review, approved)
|   +-- YYYY-MM-DD-slug/
|       +-- README.md
|       +-- REQUIREMENTS.md
|       +-- ARCHITECTURE.md
|       +-- IMPLEMENTATION_PLAN.md
|       +-- PROGRESS.md
|       +-- DECISIONS.md
|       +-- RESEARCH_NOTES.md
|       +-- CHANGELOG.md
+-- completed/        # Archived projects (with RETROSPECTIVE.md)
+-- rejected/         # Rejected specs (preserved for reference)
```

## Requirements

- Claude Code CLI
- Git (for worktree operations)
- Python 3 (for filters and analyzers)
- jq (for registry operations)
- Terminal app (iTerm2, Ghostty, tmux, etc.)

## Attribution

The worktree management functionality is based on the original `worktree-manager` skill.

## License

MIT
