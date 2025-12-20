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
commands/
├── plan.md             # /plan - Strategic project planning
├── implement.md        # /implement - Implementation progress tracking
├── status.md           # /status - Status monitoring
├── complete.md         # /complete - Project close-out
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
    ├── active/           # In-progress projects
    │   └── YYYY-MM-DD-slug/
    │       ├── README.md, REQUIREMENTS.md, ARCHITECTURE.md
    │       └── IMPLEMENTATION_PLAN.md, PROGRESS.md
    └── completed/        # Archived with RETROSPECTIVE.md
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
/plan "idea"  ->  Plan with Socratic elicitation
       |
/implement slug ->  Track implementation (PROGRESS.md)
       |
/status        ->  Monitor status
       |
/complete slug ->  Close out with retrospective
```

### Worktree Commands

| Command | Description |
|---------|-------------|
| `/claude-spec:worktree-setup` | Interactive configuration wizard (creates ~/.claude/claude-spec.config.json) |
| `/claude-spec:worktree-create` | Create git worktree with Claude agent |
| `/claude-spec:worktree-status` | Show worktree status |
| `/claude-spec:worktree-cleanup` | Clean up stale worktrees |

## Active Spec Projects

(None - project completed)

## Recent Completed Spec Project

- `docs/spec/active/2025-12-19-remove-memory-hooks/` - Remove Memory and Hook Components
  - Completed: 2025-12-19
  - Outcome: success
  - Branch: plan/remove-memory-hooks
  - Key changes: Removed memory/, hooks/, memory commands, hook tests, updated all documentation
