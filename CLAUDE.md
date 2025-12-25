# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**claude-spec** is a Claude Code plugin for project specification and implementation lifecycle management. It provides slash commands (`/*`) for strategic planning, progress tracking, and project close-out with retrospectives.

## Build & Test Commands

```bash
# Install dependencies
make install          # or: uv sync

# Run all CI checks (recommended before commits)
make ci               # format-check + lint + typecheck + security + test

# Individual checks
make format           # Format code with ruff
make format-check     # Check formatting (CI mode)
make lint             # Lint with ruff
make lint-fix         # Lint and auto-fix
make typecheck        # Type check with mypy
make security         # Security scan with bandit
make test             # Run tests with coverage

# Run single test
uv run pytest tests/test_pipeline.py -v

# Clean generated files
make clean
```

## Architecture

### Plugin Structure

```
.claude-plugin/
├── plugin.json         # Plugin manifest
├── hooks.json          # PreToolUse hook configuration
commands/
├── plan.md             # /plan - Strategic project planning
├── approve.md          # /approve - Review and approve specs before implementation
├── implement.md        # /implement - Implementation progress tracking
├── status.md           # /status - Status monitoring
├── complete.md         # /complete - Project close-out
├── deep-clean.md       # /deep-clean - Comprehensive code review and remediation
├── deep-explore.md     # /deep-explore - Exhaustive codebase exploration (Opus 4.5)
├── deep-research.md    # /deep-research - Multi-phase investigation (Opus 4.5)
├── worktree-setup.md   # /worktree-setup - Configuration wizard
├── worktree-create.md  # /worktree-create - Create worktrees
├── worktree-status.md  # /worktree-status - Worktree status
└── worktree-cleanup.md # /worktree-cleanup - Clean up worktrees
filters/
├── pipeline.py         # Secret detection + truncation
├── log_entry.py        # Log entry schema (dataclass)
└── log_writer.py       # Atomic JSON file writer
analyzers/
├── log_analyzer.py     # Log file analysis
└── analyze_cli.py      # CLI for retrospective analysis
steps/
├── base.py             # StepResult, BaseStep classes
├── context_loader.py   # Load CLAUDE.md, git state, structure
├── security_reviewer.py # Run bandit security scan
├── log_archiver.py     # Archive prompt logs to completed/
├── marker_cleaner.py   # Clean up temp files
└── retrospective_gen.py # Generate RETROSPECTIVE.md
skills/worktree-manager/ # Worktree automation skill
hooks/
└── check-approved-spec.sh  # PreToolUse hook - blocks impl without approved spec
tests/                   # Pytest test suite
```

### Data Flow

1. **Filter Pipeline** (`filters/pipeline.py`):
   - Pre-compiled regex patterns for 15+ secret types (AWS, GitHub, API keys, etc.)
   - Order: secrets -> truncation
   - Returns `FilterResult` with statistics

2. **Log Writer** (`filters/log_writer.py`):
   - Atomic writes with file locking (`fcntl.flock`)
   - Creates backup before modifications
   - JSON array format with `LogEntry` schema

### Project Artifact Structure

```
project-root/
└── docs/spec/
    ├── active/           # In-progress projects (draft, in-review, approved)
    │   └── YYYY-MM-DD-slug/
    │       ├── README.md, REQUIREMENTS.md, ARCHITECTURE.md
    │       └── IMPLEMENTATION_PLAN.md, PROGRESS.md, DECISIONS.md
    ├── completed/        # Archived with RETROSPECTIVE.md
    └── rejected/         # Rejected specs (preserved for reference)
```

## Key Patterns

### Secret Detection

Patterns in `filters/pipeline.py::SECRET_PATTERNS` - add new patterns there for additional secret types. Secrets are replaced with `[SECRET:type]` placeholders.

### Test Patterns

Tests use fixtures and mocking extensively:

```python
@pytest.fixture
def temp_project_dir(tmp_path):
    """Create mock spec project structure."""
    project = tmp_path / "docs" / "spec" / "active" / "test-project"
    project.mkdir(parents=True)
    return project

def test_something(temp_project_dir, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))
    # ...
```

## CI/CD

- **GitHub Actions** in `.github/workflows/ci.yml`
- Tests run on Python 3.11, 3.12, 3.13
- Code coverage uploaded to Codecov
- Release workflow in `.github/workflows/release.yml`

## Plugin Command Workflow

```
/plan "idea"     ->  Create specification documents (Socratic elicitation)
       |             Flags: --inline (no worktree/branch), --no-worktree, --no-branch
       |
/approve slug    ->  Review and approve/reject spec (records audit trail)
       |             Records: approver identity, timestamp, decision
       |
/implement slug  ->  Track implementation (PROGRESS.md checkpoint)
       |             Warns if spec not approved (advisory, non-blocking)
       |
/status          ->  Monitor project status across all specs
       |
/complete slug   ->  Close out with retrospective, move to completed/
```

### Approval Workflow

The `/approve` command provides governance controls:

| Decision | Action |
|----------|--------|
| Approve | Updates status to `approved`, records approver and timestamp |
| Request Changes | Adds feedback notes, keeps in `in-review` status |
| Reject | Moves spec to `docs/spec/rejected/`, preserves for reference |

**Prevention Mechanisms:**
1. `/plan` has `<never_implement>` section - prevents jumping to implementation
2. `/implement` shows warning for unapproved specs
3. `hooks/check-approved-spec.sh` - optional PreToolUse hook that blocks Write/Edit without approved spec

### Worktree Commands

| Command | Description |
|---------|-------------|
| `/claude-spec:worktree-setup` | Interactive configuration wizard (creates ~/.claude/claude-spec.config.json) |
| `/claude-spec:worktree-create` | Create git worktree with Claude agent |
| `/claude-spec:worktree-status` | Show worktree status |
| `/claude-spec:worktree-cleanup` | Clean up stale worktrees |

### Code Review & Exploration Commands

| Command | Description |
|---------|-------------|
| `/claude-spec:deep-clean` | Comprehensive code review and remediation with parallel specialist agents |
| `/claude-spec:deep-explore` | Exhaustive codebase exploration (Opus 4.5 optimized) |
| `/claude-spec:deep-research` | Multi-phase investigation with structured analysis workflows |

## Active Spec Projects

- `docs/spec/active/2025-12-24-github-issues-worktree-wf/` - GitHub Issues Worktree Workflow
  - Status: Implementation complete, in review
  - Branch: plan/github-issues-worktree-wf
  - Features: Issue-to-worktree automation, `/claude-spec:plan` without arguments
  - Scripts: `scripts/github-issues/` (6 scripts, 47 tests)

## Recent Completed Spec Projects

- `docs/spec/completed/2025-12-25-approve-command/` - Add /approve Command for Explicit Plan Acceptance
  - Completed: 2025-12-25
  - Outcome: success
  - Duration: 15 minutes (planned: 4-6 hours)
  - GitHub Issue: #26
  - Deliverables: `/approve` command, `/plan` flags (--inline, --no-worktree, --no-branch), PreToolUse hook, `<never_implement>` section
  - Impact: Closes workflow gap, provides governance/audit trail, prevents jumping to implementation
  - Key docs: REQUIREMENTS.md (13 P0, 4 P1, 3 P2), ARCHITECTURE.md (5 components), RETROSPECTIVE.md (5 ADRs)

- `docs/spec/completed/2025-12-19-remove-memory-hooks/` - Remove Memory and Hook Components
  - Completed: 2025-12-19
  - Outcome: success
  - Branch: plan/remove-memory-hooks
  - Key changes: Removed memory/, hooks/, memory commands, hook tests, updated all documentation

## Code Intelligence (LSP)

### Navigation & Understanding
- Use LSP `goToDefinition` before modifying unfamiliar functions, classes, or modules
- Use LSP `findReferences` before refactoring any symbol to understand full impact
- Use LSP `documentSymbol` to get file structure overview before major edits
- Prefer LSP navigation over grep--it resolves through imports and re-exports

### Verification Workflow
- Check LSP diagnostics after each edit to catch type errors immediately
- Run `mypy .` for project-wide type verification (this project uses mypy)
- Verify imports resolve correctly via LSP after adding new dependencies

### Pre-Edit Checklist
- [ ] Navigate to definition to understand implementation
- [ ] Find all references to assess change impact
- [ ] Review type annotations via hover before modifying function signatures
- [ ] Check class/protocol definitions before implementing

### Error Handling
- If LSP reports errors, fix them before proceeding to next task
- Treat type errors as blocking--this project enforces strict type checking
- Use LSP diagnostics output to guide fixes, not guesswork

### LSP Hooks Installed
The `.claude/hooks.json` file configures automatic quality checks:
- `format-on-edit`: Runs `ruff format` after Python file edits
- `lint-check-on-edit`: Runs `ruff check` to show lint errors
- `typecheck-on-edit`: Runs `mypy` to catch type errors
- `pre-commit-quality-gate`: Runs full `make ci` before git commits (blocking)
