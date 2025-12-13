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
  - [ ] File created at `plugins/cs/pyproject.toml`
  - [ ] Project metadata defined (name, version, description)
  - [ ] Dev dependencies: ruff, mypy, bandit, pytest, pytest-cov
  - [ ] Tool configurations: ruff, mypy, pytest, coverage, bandit
  - [ ] `uv sync` works locally

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
  - [ ] File created at `plugins/cs/Makefile`
  - [ ] `make install` - Install dependencies with uv
  - [ ] `make format` - Run ruff format
  - [ ] `make lint` - Run ruff check
  - [ ] `make typecheck` - Run mypy
  - [ ] `make security` - Run bandit
  - [ ] `make test` - Run pytest with coverage
  - [ ] `make shellcheck` - Run shellcheck on scripts
  - [ ] `make ci` - Run all checks (mirrors CI workflow)
  - [ ] `make clean` - Clean generated files

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
  - [ ] `uv run pytest` executes successfully
  - [ ] All existing tests pass
  - [ ] Coverage report generated

#### Task 1.4: Fix any initial linting issues

- **Description**: Run ruff and fix formatting/linting issues in Python code
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [ ] `uv run ruff format --check .` passes
  - [ ] `uv run ruff check .` passes (or issues documented)

#### Task 1.5: Address mypy type issues (initial pass)

- **Description**: Run mypy and address critical type errors
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [ ] `uv run mypy .` runs without crash
  - [ ] Critical errors addressed or ignored with comments
  - [ ] Configuration tuned for gradual adoption

### Phase 1 Deliverables

- [ ] `plugins/cs/pyproject.toml`
- [ ] `plugins/cs/Makefile`
- [ ] `plugins/cs/uv.lock` (generated)
- [ ] Working local quality checks via `make ci`

### Phase 1 Exit Criteria

- [ ] `uv sync` succeeds
- [ ] `make ci` passes (all local checks)
- [ ] `make test` passes with coverage
- [ ] Makefile targets mirror CI workflow steps

---

## Phase 2: CI Workflow

**Goal**: Automated quality checks and testing on PRs and pushes

**Prerequisites**: Phase 1 complete

### Tasks

#### Task 2.1: Create CI workflow file

- **Description**: Create .github/workflows/ci.yml with quality and test jobs
- **Dependencies**: Phase 1
- **Acceptance Criteria**:
  - [ ] Workflow triggers on push to main and pull_request
  - [ ] Quality job runs: ruff format, ruff check, mypy, bandit
  - [ ] Test job runs pytest with matrix (3.11, 3.12, 3.13)
  - [ ] Concurrency configured to cancel superseded runs
  - [ ] Permissions set to `contents: read`

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
  - [ ] shellcheck runs on all .sh files
  - [ ] Failures block CI
  - [ ] Any existing issues fixed or excluded with comments

#### Task 2.3: Test CI workflow on branch

- **Description**: Push to feature branch and verify workflow runs correctly
- **Dependencies**: Task 2.1, Task 2.2
- **Acceptance Criteria**:
  - [ ] Workflow triggers on push
  - [ ] All jobs pass
  - [ ] Matrix runs 3 Python versions
  - [ ] Duration under 5 minutes

#### Task 2.4: Fix shell script issues (if any)

- **Description**: Fix any shellcheck findings in existing scripts
- **Dependencies**: Task 2.2
- **Acceptance Criteria**:
  - [ ] All scripts pass shellcheck
  - [ ] OR issues excluded with inline comments explaining why

### Phase 2 Deliverables

- [ ] `.github/workflows/ci.yml`
- [ ] Shell scripts passing shellcheck

### Phase 2 Exit Criteria

- [ ] CI workflow runs successfully on feature branch
- [ ] All quality jobs pass
- [ ] All test matrix jobs pass
- [ ] shellcheck passes

---

## Phase 3: Release Workflow

**Goal**: Automated GitHub Release creation on version tags

**Prerequisites**: Phase 2 complete (CI passing)

### Tasks

#### Task 3.1: Create release workflow file

- **Description**: Create .github/workflows/release.yml triggered by v* tags
- **Dependencies**: Phase 2
- **Acceptance Criteria**:
  - [ ] Triggers on push of tags matching `v*`
  - [ ] Permissions set to `contents: write`
  - [ ] Creates GitHub Release with softprops/action-gh-release

#### Task 3.2: Add changelog extraction

- **Description**: Extract version-specific changelog section for release notes
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - [ ] Extracts section from plugins/cs/CHANGELOG.md
  - [ ] Handles missing version gracefully
  - [ ] Release body contains extracted notes

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
  - [ ] Creates cs-plugin-vX.X.X.zip
  - [ ] Excludes tests/, __pycache__/, .pyc files
  - [ ] Attached to GitHub Release

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
  - [ ] Tag push triggers workflow
  - [ ] GitHub Release created with correct name
  - [ ] Release notes contain changelog
  - [ ] Zip artifact attached
  - [ ] Pre-release flag works for -beta tags

### Phase 3 Deliverables

- [ ] `.github/workflows/release.yml`

### Phase 3 Exit Criteria

- [ ] Test release created successfully
- [ ] Changelog extracted correctly
- [ ] Zip artifact downloadable and correct
- [ ] Delete test release after verification

---

## Phase 4: Ecosystem Files

**Goal**: Standardize contributions with templates and automated maintenance

**Prerequisites**: Phase 2 complete (nice to have after Phase 3)

### Tasks

#### Task 4.1: Create dependabot.yml

- **Description**: Configure dependabot for GitHub Actions and pip updates
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] Updates github-actions weekly
  - [ ] Updates pip dependencies weekly
  - [ ] Labels applied to PRs

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
  - [ ] Template appears on new PRs
  - [ ] Includes change type checkboxes
  - [ ] Includes testing checklist

#### Task 4.3: Create issue templates

- **Description**: Add bug report and feature request templates
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] Templates appear in "New Issue" chooser
  - [ ] Bug template includes reproduction steps
  - [ ] Feature template includes use case

#### Task 4.4: Create CODEOWNERS

- **Description**: Define code ownership for reviews
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] File at .github/CODEOWNERS
  - [ ] Appropriate owners defined (adjust handles as needed)

### Phase 4 Deliverables

- [ ] `.github/dependabot.yml`
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] `.github/ISSUE_TEMPLATE/bug_report.md`
- [ ] `.github/ISSUE_TEMPLATE/feature_request.md`
- [ ] `.github/ISSUE_TEMPLATE/config.yml`
- [ ] `.github/CODEOWNERS`

### Phase 4 Exit Criteria

- [ ] All files created
- [ ] Templates render correctly in GitHub UI

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

- [ ] Local: `uv sync && uv run pytest` passes
- [ ] Local: `uv run ruff check .` passes
- [ ] Local: `uv run mypy .` passes
- [ ] Local: `shellcheck plugins/cs/skills/worktree-manager/scripts/*.sh` passes
- [ ] CI: Workflow runs on feature branch push
- [ ] CI: All matrix jobs pass
- [ ] Release: Test tag creates correct release

## Documentation Tasks

- [ ] Update repository README with CI badge (after stable)
- [ ] Update CONTRIBUTING.md with new workflow info
- [ ] Update plugins/cs/CHANGELOG.md with CI/CD addition

## Launch Checklist

- [ ] Phase 1: Foundation complete and verified
- [ ] Phase 2: CI workflow passing on main
- [ ] Phase 3: Release workflow tested with dummy tag
- [ ] Phase 4: All ecosystem files in place
- [ ] Branch protection: Consider requiring CI pass (optional)

## Post-Launch

- [ ] Monitor first few CI runs for issues
- [ ] Monitor first real release for issues
- [ ] Add coverage badge to README
- [ ] Consider branch protection rules
