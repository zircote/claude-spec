---
document_type: decisions
project_id: SPEC-2025-12-12-005
---

# Quality and Release CI - Architecture Decision Records

## ADR-001: Use uv for Python Package Management

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

The CI pipeline needs to install Python dependencies quickly and reliably. Options include pip, poetry, pipenv, and uv.

### Decision

Use **uv** (by Astral) for package management in CI and local development.

### Consequences

**Positive:**
- 10-100x faster than pip for dependency installation
- Handles Python version management via `uv python install`
- Built-in caching with `astral-sh/setup-uv` action
- Active development and community support
- Consistent with organizational Python standards

**Negative:**
- Newer tool, less widespread adoption (but growing rapidly)
- Requires pyproject.toml (not setup.py) - this is actually a positive

**Neutral:**
- Lock file format differs from pip-tools/poetry

### Alternatives Considered

1. **pip + pip-tools**: Slower, more established
2. **poetry**: Feature-rich but slower, heavier
3. **pipenv**: Less actively maintained, slower

---

## ADR-002: Use ruff for Linting and Formatting

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

Python code needs formatting and linting. Traditional tools include Black, isort, flake8, pylint.

### Decision

Use **ruff** for both formatting and linting.

### Consequences

**Positive:**
- Single tool replaces Black, isort, flake8, and many others
- 10-100x faster than traditional tools
- Includes bandit-equivalent security rules (optional)
- Active development by Astral (same as uv)
- Consistent with organizational standards

**Negative:**
- Some edge-case formatting differences from Black
- Plugin ecosystem smaller than flake8

**Neutral:**
- Configuration in pyproject.toml

### Alternatives Considered

1. **Black + isort + flake8**: More tools to configure and run
2. **Black + pylint**: pylint very slow
3. **autopep8**: Less opinionated, more permissive

---

## ADR-003: Use Stable Action Versions (v4 over v6)

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

GitHub Actions like `actions/checkout` have multiple major versions available. v6 is latest but requires runner v2.327.1+.

### Decision

Use **v4** versions of core actions for stability.

```yaml
actions/checkout@v4
actions/setup-python@v4  # Note: We use astral-sh/setup-uv instead
actions/upload-artifact@v4
actions/download-artifact@v4
```

Use `astral-sh/setup-uv@v4` for Python setup (includes uv and Python).

### Consequences

**Positive:**
- Widely tested and stable
- Works on all GitHub-hosted runners
- Dependabot will notify when updates available

**Negative:**
- Missing latest features in v5/v6
- Will need to update eventually

**Neutral:**
- Node 20 runtime (v6 uses Node 24)

### Alternatives Considered

1. **v6 (latest)**: Requires newer runners, less tested
2. **Pin to SHA**: More secure but harder to maintain
3. **Use latest tag**: Risky, can break unexpectedly

---

## ADR-004: Matrix Testing with fail-fast: false

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

Testing across Python 3.11, 3.12, 3.13 requires a strategy matrix. Default behavior cancels other jobs if one fails.

### Decision

Use `fail-fast: false` to see all failures.

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
```

### Consequences

**Positive:**
- See all version-specific failures in one run
- Don't have to re-run to discover additional failures
- Better debugging information

**Negative:**
- Uses more CI minutes on failing PRs
- Takes longer to get "all failed" result

**Neutral:**
- Standard practice for library testing

### Alternatives Considered

1. **fail-fast: true (default)**: Faster to fail, but hides other failures
2. **Single version**: Misses compatibility issues

---

## ADR-005: Separate Quality and Test Jobs

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

Quality checks (lint, format, type check) and tests could be in one job or separate jobs.

### Decision

Keep quality checks and tests as **separate jobs** that run in parallel.

```yaml
jobs:
  quality:
    # formatting, linting, type checking, security
  test:
    # pytest with matrix
```

### Consequences

**Positive:**
- Fast feedback on formatting issues (no need to wait for tests)
- Clear separation of concerns
- Parallel execution saves time
- Can add `needs: [quality]` to test later if desired

**Negative:**
- Slightly more YAML configuration
- Two checkout/setup sequences

**Neutral:**
- Total CI time similar or faster due to parallelism

### Alternatives Considered

1. **Single job**: Sequential, slower feedback
2. **Quality as required, tests optional**: Too complex
3. **Test depends on quality**: Blocks tests on lint (could be useful)

---

## ADR-006: Use softprops/action-gh-release for Releases

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

GitHub Releases can be created via API directly or using community actions.

### Decision

Use **softprops/action-gh-release@v2** for release creation.

### Consequences

**Positive:**
- Well-maintained, widely used action
- Supports file uploads, release notes, pre-release detection
- Simple configuration
- Handles idempotency (can re-run)

**Negative:**
- Third-party dependency
- Could be abandoned (but very popular)

**Neutral:**
- Uses GITHUB_TOKEN, no additional secrets

### Alternatives Considered

1. **gh CLI directly**: More verbose, less features
2. **GitHub API via curl**: Complex, error-prone
3. **actions/create-release**: Deprecated

---

## ADR-007: Extract Changelog vs Generate Release Notes

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

Release notes can be auto-generated from commits or extracted from a maintained CHANGELOG.md.

### Decision

**Extract changelog section** from plugins/cs/CHANGELOG.md rather than auto-generate.

### Consequences

**Positive:**
- Human-curated, meaningful release notes
- Follows Keep-a-Changelog convention
- Enforces discipline of maintaining changelog
- Release notes match what users see in repo

**Negative:**
- Requires manual changelog updates before release
- More work per release

**Neutral:**
- Falls back to tag name if version not found in changelog

### Alternatives Considered

1. **generate_release_notes: true**: Auto from PRs, but noisy
2. **Conventional commits + changelog generator**: More tooling
3. **No release notes**: Poor user experience

---

## ADR-008: Minimal Workflow Permissions

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

GitHub Actions workflows can request various permission levels. Default can be quite permissive.

### Decision

Explicitly set **minimal permissions** per workflow.

```yaml
# CI workflow
permissions:
  contents: read

# Release workflow
permissions:
  contents: write
```

### Consequences

**Positive:**
- Principle of least privilege
- Reduces blast radius if action is compromised
- Security best practice
- Makes permissions auditable

**Negative:**
- Must remember to add permissions when adding new features

**Neutral:**
- Aligns with GitHub's security recommendations

### Alternatives Considered

1. **Default permissions**: Too permissive
2. **Job-level permissions**: More granular but verbose
3. **No explicit permissions**: Relies on repo settings

---

## ADR-009: Python 3.11+ Minimum Version

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

Need to choose minimum Python version for compatibility testing.

### Decision

Support **Python 3.11, 3.12, 3.13** (3.11+ minimum).

### Consequences

**Positive:**
- Broad compatibility (3.11 still widely used)
- Access to modern Python features (3.11+)
- 3 versions is manageable matrix

**Negative:**
- Can't use 3.12+ only features (like improved generics)
- 3.11 reaches EOL October 2027

**Neutral:**
- Consistent with organizational Python standards

### Alternatives Considered

1. **3.12+ only**: More modern but less compatible
2. **3.10+**: Older, more maintenance burden
3. **3.14 only**: Too cutting-edge

---

## ADR-010: shellcheck for Shell Script Validation

**Date**: 2025-12-12
**Status**: Accepted
**Deciders**: Project maintainer

### Context

The plugin includes shell scripts that should be validated for correctness and portability.

### Decision

Use **shellcheck** (pre-installed on ubuntu-latest) for shell script validation.

### Consequences

**Positive:**
- Industry standard shell linter
- Pre-installed on GitHub runners (no action needed)
- Catches common bugs and portability issues
- Inline directives for exceptions

**Negative:**
- May flag legitimate patterns as issues
- Some scripts may need fixes or exclusions

**Neutral:**
- Simple to run: `shellcheck scripts/*.sh`

### Alternatives Considered

1. **shfmt only**: Formatting but not linting
2. **bash -n**: Only syntax check, misses logic issues
3. **No validation**: Risk of shell bugs in production
