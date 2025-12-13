# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**claude-spec** is a Claude Code plugin for project specification and implementation lifecycle management. It provides slash commands (`/cs:*`) for strategic planning, progress tracking, and project close-out with retrospectives.

## Build & Test Commands

All commands run from `plugins/cs/` directory:

```bash
cd plugins/cs

# Install dependencies
make install          # or: uv sync

# Run all CI checks (recommended before commits)
make ci               # format-check + lint + typecheck + security + shellcheck + test

# Individual checks
make format           # Format code with ruff
make format-check     # Check formatting (CI mode)
make lint             # Lint with ruff
make lint-fix         # Lint and auto-fix
make typecheck        # Type check with mypy
make security         # Security scan with bandit
make test             # Run tests with coverage
make shellcheck       # Lint shell scripts

# Run single test
uv run pytest tests/test_pipeline.py -v
uv run pytest tests/test_hook.py::test_main_with_logging_enabled -v

# Clean generated files
make clean
```

## Architecture

### Plugin Structure

```
plugins/cs/
├── commands/           # Slash command definitions (markdown)
│   ├── p.md           # /cs:p - Strategic project planning
│   ├── i.md           # /cs:i - Implementation progress tracking
│   ├── s.md           # /cs:s - Status monitoring
│   ├── c.md           # /cs:c - Project close-out
│   ├── log.md         # /cs:log - Prompt capture toggle
│   └── wt/            # Worktree commands
├── filters/           # Content filtering pipeline
│   ├── pipeline.py    # Secret detection + truncation
│   ├── log_entry.py   # Log entry schema (dataclass)
│   └── log_writer.py  # Atomic JSON file writer
├── hooks/
│   └── prompt_capture.py  # UserPromptSubmit hook handler
├── analyzers/
│   ├── log_analyzer.py    # Log file analysis
│   └── analyze_cli.py     # CLI for retrospective analysis
├── skills/worktree-manager/  # Worktree automation
└── tests/             # Pytest test suite (97% coverage)
```

### Data Flow

1. **UserPromptSubmit Hook** (`hooks/prompt_capture.py`):
   - Receives JSON via stdin from Claude Code
   - Checks for `.prompt-log-enabled` marker in `docs/spec/active/*/`
   - Filters secrets via `filters/pipeline.py`
   - Appends to `.prompt-log.json` via `filters/log_writer.py`
   - Always returns `{"decision": "approve"}` (never blocks)

2. **Filter Pipeline** (`filters/pipeline.py`):
   - Pre-compiled regex patterns for 15+ secret types (AWS, GitHub, API keys, etc.)
   - Order: secrets → truncation
   - Returns `FilterResult` with statistics

3. **Log Writer** (`filters/log_writer.py`):
   - Atomic writes with file locking (`fcntl.flock`)
   - Creates backup before modifications
   - JSON array format with `LogEntry` schema

### Project Artifact Structure

```
docs/spec/
├── active/           # In-progress projects
│   └── YYYY-MM-DD-slug/
│       ├── README.md, REQUIREMENTS.md, ARCHITECTURE.md
│       ├── IMPLEMENTATION_PLAN.md, PROGRESS.md
│       ├── .prompt-log-enabled (marker)
│       └── .prompt-log.json (log file)
└── completed/        # Archived with RETROSPECTIVE.md
```

## Key Patterns

### Hook Input/Output Contract

```python
# Input (stdin JSON)
{
    "hook_event_name": "UserPromptSubmit",
    "prompt": "string",       # NOTE: "prompt", not "user_prompt"
    "session_id": "string",
    "cwd": "string"
}

# Output (stdout JSON)
{"decision": "approve"}  # Hook never blocks
```

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
/cs:p "idea"  →  Plan with Socratic elicitation
       ↓
/cs:i slug    →  Track implementation (PROGRESS.md)
       ↓
/cs:s         →  Monitor status
       ↓
/cs:c slug    →  Close out with retrospective
```

Enable logging with `/cs:log on` before `/cs:p` for prompt capture during planning.
