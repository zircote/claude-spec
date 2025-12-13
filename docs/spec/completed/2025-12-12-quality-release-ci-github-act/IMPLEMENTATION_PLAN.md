---
document_type: implementation_plan
project_id: SPEC-2025-12-12-005
version: 1.0.0
last_updated: 2025-12-12T22:30:00Z
status: draft
---

# Quality and Release CI with GitHub Actions - Implementation Plan

## Overview

Implementation follows a phased approach: foundation (pyproject.toml), CI workflow, release workflow, then ecosystem files. Each phase builds on the previous and can be validated independently.

## Phase Summary

| Phase | Focus | Key Deliverables |
|-------|-------|------------------|
| Phase 1: Foundation | Python tooling setup | pyproject.toml, Makefile, tool configs |
| Phase 2: CI Workflow | Quality checks & tests | .github/workflows/ci.yml |
| Phase 3: Release Workflow | Automated releases | .github/workflows/release.yml |
| Phase 4: Ecosystem | Templates & maintenance | Issue templates, dependabot, etc. |

---

## Phase 1: Foundation

**Goal**: Set up Python project configuration with modern tooling

**Prerequisites**: None

### Tasks

#### Task 1.1: Create pyproject.toml

- **Description**: Create pyproject.toml in plugins/cs/ with project metadata, dev dependencies, and tool configurations
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] File created at `plugins/cs/pyproject.toml`
  - [x] Project metadata defined (name, version, description)
  - [x] Dev dependencies: ruff, mypy, bandit, pytest, pytest-cov
  - [x] Tool configurations: ruff, mypy, pytest, coverage, bandit
  - [x] `uv sync` works locally

**Implementation Notes**:
```toml
# Key sections needed:
[project]
name = "claude-spec-plugin"
version = "1.0.0"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = ["ruff>=0.8.0", "mypy>=1.13.0", "bandit>=1.8.0", "pytest>=8.0.0", "pytest-cov>=6.0.0"]

[tool.ruff]
target-version = "py311"
line-length = 88

[tool.mypy]
python_version = "3.11"
# Start non-strict, tighten later

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["filters", "hooks", "analyzers"]

[tool.bandit]
exclude_dirs = ["tests"]
```

#### Task 1.2: Create Makefile for local CI

- **Description**: Create Makefile in plugins/cs/ with targets that mirror GitHub Actions workflow steps
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - [x] File created at `plugins/cs/Makefile`
  - [x] `make install` - Install dependencies with uv
  - [x] `make format` - Run ruff format
  - [x] `make lint` - Run ruff check
  - [x] `make typecheck` - Run mypy
  - [x] `make security` - Run bandit
  - [x] `make test` - Run pytest with coverage
  - [x] `make shellcheck` - Run shellcheck on scripts
  - [x] `make ci` - Run all checks (mirrors CI workflow)
  - [x] `make clean` - Clean generated files

**Implementation Notes**:
```makefile
.PHONY: install format lint typecheck security test shellcheck ci clean

# Install dependencies
install:
	uv sync

# Format code
format:
	uv run ruff format .

# Check formatting (CI mode)
format-check:
	uv run ruff format --check .

# Lint code
lint:
	uv run ruff check .

# Lint and fix
lint-fix:
	uv run ruff check --fix .

# Type check
typecheck:
	uv run mypy .

# Security scan
security:
	uv run bandit -r filters/ hooks/ analyzers/ -ll

# Run tests with coverage
test:
	uv run pytest --cov=filters --cov=hooks --cov=analyzers --cov-report=term-missing -v

# Shell script linting
shellcheck:
	shellcheck skills/worktree-manager/scripts/*.sh

# Run all CI checks (mirrors GitHub Actions)
ci: format-check lint typecheck security shellcheck test
	@echo "All CI checks passed!"

# Clean generated files
clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__ .coverage coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
```

#### Task 1.3: Verify existing tests pass

- **Description**: Run existing tests with pytest to establish baseline
- **Dependencies**: Task 1.1, Task 1.2
- **Acceptance Criteria**:
  - [x] `uv run pytest` executes successfully
  - [x] All existing tests pass
  - [x] Coverage report generated

#### Task 1.4: Fix any initial linting issues

- **Description**: Run ruff and fix formatting/linting issues in Python code
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [x] `uv run ruff format --check .` passes
  - [x] `uv run ruff check .` passes (or issues documented)

#### Task 1.5: Address mypy type issues (initial pass)

- **Description**: Run mypy and address critical type errors
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [x] `uv run mypy .` runs without crash
  - [x] Critical errors addressed or ignored with comments
  - [x] Configuration tuned for gradual adoption

### Phase 1 Deliverables

- [x] `plugins/cs/pyproject.toml`
- [x] `plugins/cs/Makefile`
- [x] `plugins/cs/uv.lock` (generated)
- [x] Working local quality checks via `make ci`

### Phase 1 Exit Criteria

- [x] `uv sync` succeeds
- [x] `make ci` passes (all local checks)
- [x] `make test` passes with coverage
- [x] Makefile targets mirror CI workflow steps

---

## Phase 2: CI Workflow

**Goal**: Automated quality checks and testing on PRs and pushes

**Prerequisites**: Phase 1 complete

### Tasks

#### Task 2.1: Create CI workflow file

- **Description**: Create .github/workflows/ci.yml with quality and test jobs
- **Dependencies**: Phase 1
- **Acceptance Criteria**:
  - [x] Workflow triggers on push to main and pull_request
  - [x] Quality job runs: ruff format, ruff check, mypy, bandit
  - [x] Test job runs pytest with matrix (3.11, 3.12, 3.13)
  - [x] Concurrency configured to cancel superseded runs
  - [x] Permissions set to `contents: read`

**Implementation Notes**:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  quality:
    # ruff format, ruff check, mypy, bandit

  shellcheck:
    # Validate shell scripts

  test:
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    # pytest with coverage
```

#### Task 2.2: Add shellcheck job

- **Description**: Add job to validate shell scripts in skills/worktree-manager/scripts/
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - [x] shellcheck runs on all .sh files
  - [x] Failures block CI
  - [x] Any existing issues fixed or excluded with comments

#### Task 2.3: Test CI workflow on branch

- **Description**: Push to feature branch and verify workflow runs correctly
- **Dependencies**: Task 2.1, Task 2.2
- **Acceptance Criteria**:
  - [x] Workflow triggers on push
  - [x] All jobs pass
  - [x] Matrix runs 3 Python versions
  - [x] Duration under 5 minutes

#### Task 2.4: Fix shell script issues (if any)

- **Description**: Fix any shellcheck findings in existing scripts
- **Dependencies**: Task 2.2
- **Acceptance Criteria**:
  - [x] All scripts pass shellcheck
  - [x] OR issues excluded with inline comments explaining why

### Phase 2 Deliverables

- [x] `.github/workflows/ci.yml`
- [x] Shell scripts passing shellcheck

### Phase 2 Exit Criteria

- [x] CI workflow runs successfully on feature branch
- [x] All quality jobs pass
- [x] All test matrix jobs pass
- [x] shellcheck passes

---

## Phase 3: Release Workflow

**Goal**: Automated GitHub Release creation on version tags

**Prerequisites**: Phase 2 complete (CI passing)

### Tasks

#### Task 3.1: Create release workflow file

- **Description**: Create .github/workflows/release.yml triggered by v* tags
- **Dependencies**: Phase 2
- **Acceptance Criteria**:
  - [x] Triggers on push of tags matching `v*`
  - [x] Permissions set to `contents: write`
  - [x] Creates GitHub Release with softprops/action-gh-release

#### Task 3.2: Add changelog extraction

- **Description**: Extract version-specific changelog section for release notes
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - [x] Extracts section from plugins/cs/CHANGELOG.md
  - [x] Handles missing version gracefully
  - [x] Release body contains extracted notes

**Implementation Notes**:
```bash
VERSION="${GITHUB_REF_NAME#v}"
awk -v ver="$VERSION" '
  /^## \[/ {
    if (found) exit
    if ($0 ~ "\\[" ver "\\]") found=1
    next
  }
  found { print }
' plugins/cs/CHANGELOG.md
```

#### Task 3.3: Add plugin archive creation

- **Description**: Create zip of plugins/cs/ directory for release artifact
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - [x] Creates cs-plugin-vX.X.X.zip
  - [x] Excludes tests/, __pycache__/, .pyc files
  - [x] Attached to GitHub Release

**Implementation Notes**:
```bash
cd plugins
zip -r "../cs-plugin-${VERSION}.zip" cs/ \
  -x "cs/tests/*" \
  -x "cs/__pycache__/*" \
  -x "*.pyc"
```

#### Task 3.4: Test release workflow

- **Description**: Push test tag and verify release creation
- **Dependencies**: Tasks 3.1-3.3
- **Acceptance Criteria**:
  - [x] Tag push triggers workflow
  - [x] GitHub Release created with correct name
  - [x] Release notes contain changelog
  - [x] Zip artifact attached
  - [x] Pre-release flag works for -beta tags

### Phase 3 Deliverables

- [x] `.github/workflows/release.yml`

### Phase 3 Exit Criteria

- [x] Test release created successfully
- [x] Changelog extracted correctly
- [x] Zip artifact downloadable and correct
- [x] Delete test release after verification

---

## Phase 4: Ecosystem Files

**Goal**: Standardize contributions with templates and automated maintenance

**Prerequisites**: Phase 2 complete (nice to have after Phase 3)

### Tasks

#### Task 4.1: Create dependabot.yml

- **Description**: Configure dependabot for GitHub Actions and pip updates
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] Updates github-actions weekly
  - [x] Updates pip dependencies weekly
  - [x] Labels applied to PRs

**Implementation Notes**:
```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "pip"
    directory: "/plugins/cs"
    schedule:
      interval: "weekly"
```

#### Task 4.2: Create PR template

- **Description**: Add PULL_REQUEST_TEMPLATE.md with checklist
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] Template appears on new PRs
  - [x] Includes change type checkboxes
  - [x] Includes testing checklist

#### Task 4.3: Create issue templates

- **Description**: Add bug report and feature request templates
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] Templates appear in "New Issue" chooser
  - [x] Bug template includes reproduction steps
  - [x] Feature template includes use case

#### Task 4.4: Create CODEOWNERS

- **Description**: Define code ownership for reviews
- **Dependencies**: None
- **Acceptance Criteria**:
  - [x] File at .github/CODEOWNERS
  - [x] Appropriate owners defined (adjust handles as needed)

### Phase 4 Deliverables

- [x] `.github/dependabot.yml`
- [x] `.github/PULL_REQUEST_TEMPLATE.md`
- [x] `.github/ISSUE_TEMPLATE/bug_report.md`
- [x] `.github/ISSUE_TEMPLATE/feature_request.md`
- [x] `.github/ISSUE_TEMPLATE/config.yml`
- [x] `.github/CODEOWNERS`

### Phase 4 Exit Criteria

- [x] All files created
- [x] Templates render correctly in GitHub UI

---

## Dependency Graph

```
Phase 1: Foundation
├── Task 1.1: pyproject.toml
├── Task 1.2: Makefile (depends on 1.1)
├── Task 1.3: Verify tests (depends on 1.1, 1.2)
├── Task 1.4: Fix linting (depends on 1.2)
└── Task 1.5: Address mypy (depends on 1.2)

Phase 2: CI Workflow (depends on Phase 1)
├── Task 2.1: ci.yml
├── Task 2.2: shellcheck job (depends on 2.1)
├── Task 2.3: Test workflow (depends on 2.1, 2.2)
└── Task 2.4: Fix shell issues (depends on 2.2)

Phase 3: Release Workflow (depends on Phase 2)
├── Task 3.1: release.yml
├── Task 3.2: Changelog extraction (depends on 3.1)
├── Task 3.3: Archive creation (depends on 3.1)
└── Task 3.4: Test release (depends on 3.1-3.3)

Phase 4: Ecosystem (can run parallel to Phase 3)
├── Task 4.1: dependabot.yml
├── Task 4.2: PR template
├── Task 4.3: Issue templates
└── Task 4.4: CODEOWNERS
```

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| Tests fail on CI | Task 1.2: Verify tests locally first | Phase 1 |
| mypy strict mode too aggressive | Task 1.4: Start non-strict | Phase 1 |
| shellcheck failures | Task 2.4: Fix or exclude with comments | Phase 2 |
| Missing changelog section | Task 3.2: Handle gracefully with fallback | Phase 3 |

## Testing Checklist

- [x] Local: `uv sync && uv run pytest` passes
- [x] Local: `uv run ruff check .` passes
- [x] Local: `uv run mypy .` passes
- [x] Local: `shellcheck plugins/cs/skills/worktree-manager/scripts/*.sh` passes
- [x] CI: Workflow runs on feature branch push
- [x] CI: All matrix jobs pass
- [x] Release: Test tag creates correct release

## Documentation Tasks

- [x] Update repository README with CI badge (after stable)
- [x] Update CONTRIBUTING.md with new workflow info
- [x] Update plugins/cs/CHANGELOG.md with CI/CD addition

## Launch Checklist

- [x] Phase 1: Foundation complete and verified
- [x] Phase 2: CI workflow passing on main
- [x] Phase 3: Release workflow tested with dummy tag
- [x] Phase 4: All ecosystem files in place
- [x] Branch protection: Consider requiring CI pass (optional)

## Post-Launch

- [x] Monitor first few CI runs for issues
- [x] Monitor first real release for issues
- [x] Add coverage badge to README
- [x] Consider branch protection rules
