---
document_type: research
project_id: SPEC-2025-12-12-005
last_updated: 2025-12-12T22:30:00Z
---

# Quality and Release CI - Research Notes

## Research Summary

Comprehensive research was conducted on GitHub Actions versions, Python CI best practices, release automation patterns, and the github-ecosystem skill. Key findings inform the architecture decisions documented in DECISIONS.md.

## Codebase Analysis

### Relevant Files Examined

| File | Purpose | Relevance |
|------|---------|-----------|
| `plugins/cs/tests/test_pipeline.py` | Existing test suite | Must pass in CI |
| `plugins/cs/filters/pipeline.py` | Core filtering code | Target for mypy/bandit |
| `plugins/cs/hooks/prompt_capture.py` | Hook implementation | Target for testing |
| `plugins/cs/CHANGELOG.md` | Plugin changelog | Source for release notes |
| `plugins/cs/skills/worktree-manager/scripts/*.sh` | Shell scripts | Target for shellcheck |
| `CONTRIBUTING.md` | Contribution guide | Documents current workflow |

### Existing Patterns Identified

- **Testing**: Uses `unittest` module with test classes
- **Structure**: Proper Python package layout with `__init__.py`
- **Documentation**: Markdown files follow consistent format
- **Changelog**: Follows Keep-a-Changelog format

### Integration Points

- Tests in `plugins/cs/tests/` need to run via pytest
- Shell scripts need shellcheck validation
- CHANGELOG.md needs section extraction for releases

## Technical Research

### GitHub Actions Versions (December 2025)

| Action | Stable | Latest | Recommendation |
|--------|--------|--------|----------------|
| `actions/checkout` | v4 | v6 | Use v4 for stability |
| `actions/setup-python` | v5 | v6 | Use via setup-uv instead |
| `actions/upload-artifact` | v4 | v6 | Use v4 |
| `actions/download-artifact` | v4 | v7 | Use v4 |
| `actions/cache` | v4 | v5 | Use via setup-uv (built-in) |
| `astral-sh/setup-uv` | v4 | v7 | Use v4 for stability |
| `softprops/action-gh-release` | v2 | v2 | Use v2 |
| `codecov/codecov-action` | v4 | v4 | Use v4 |

**Key Finding**: v6 actions require runner v2.327.1+ (Node 24). v4 is stable and well-tested.

### uv in GitHub Actions

Best practices from research:

```yaml
- uses: astral-sh/setup-uv@v4
  with:
    enable-cache: true
    python-version: ${{ matrix.python-version }}
    cache-suffix: py${{ matrix.python-version }}
```

**Key Features**:
- Automatic caching (10x faster installs)
- Python version management
- Lock file support with `--frozen`

### Python Quality Tools

| Tool | Purpose | Command |
|------|---------|---------|
| ruff format | Code formatting | `uv run ruff format --check .` |
| ruff check | Linting | `uv run ruff check .` |
| mypy | Type checking | `uv run mypy .` |
| bandit | Security scanning | `uv run bandit -r src/ -ll` |
| pytest | Testing | `uv run pytest --cov` |

### Release Automation

**Tag Triggering**:
```yaml
on:
  push:
    tags:
      - 'v*'
```

**Changelog Extraction** (awk pattern):
```bash
awk -v ver="$VERSION" '
  /^## \[/ {
    if (found) exit
    if ($0 ~ "\\[" ver "\\]") found=1
    next
  }
  found { print }
' CHANGELOG.md
```

**Archive Creation**:
```bash
zip -r "plugin-${VERSION}.zip" plugin/ \
  -x "*/tests/*" \
  -x "*/__pycache__/*" \
  -x "*.pyc"
```

## Competitive Analysis

### Similar Solutions

| Solution | Strengths | Weaknesses | Applicability |
|----------|-----------|------------|---------------|
| GitHub's Python starter workflow | Official, simple | Basic, no uv | Partial |
| Astral's uv example workflows | Modern, fast | uv-specific | High |
| python-semantic-release | Automated versioning | Complex setup | Overkill |
| github-ecosystem skill | Comprehensive | Templates need customization | High |

### Lessons Learned from Others

- **uv adoption**: Growing rapidly, production-ready
- **Ruff adoption**: Replacing Black+flake8 across projects
- **Matrix testing**: fail-fast: false is standard for libraries
- **Permissions**: Explicit minimal permissions is security best practice

## Dependency Analysis

### Recommended Dev Dependencies

| Dependency | Version | Purpose | License |
|------------|---------|---------|---------|
| ruff | >=0.8.0 | Lint & format | MIT |
| mypy | >=1.13.0 | Type checking | MIT |
| bandit | >=1.8.0 | Security scan | Apache 2.0 |
| pytest | >=8.0.0 | Test runner | MIT |
| pytest-cov | >=6.0.0 | Coverage | MIT |

### Dependency Risks

- **uv**: New but rapidly maturing, backed by Astral
- **ruff**: Same, but now industry standard
- **Actions**: GitHub-maintained, very stable

## Sources

### Official Documentation
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [uv Documentation](https://docs.astral.sh/uv/)
- [ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [shellcheck Wiki](https://www.shellcheck.net/wiki/)

### Organizational Standards
- `~/.claude/includes/github-actions.md` - GitHub Actions standards
- `~/.claude/includes/python.md` - Python environment standards
- `~/.claude/includes/testing.md` - Testing standards
- `~/.claude/skills/github-ecosystem/` - GitHub config generator skill

### GitHub Releases
- [actions/checkout releases](https://github.com/actions/checkout/releases)
- [astral-sh/setup-uv releases](https://github.com/astral-sh/setup-uv/releases)
- [softprops/action-gh-release releases](https://github.com/softprops/action-gh-release/releases)

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| Which action versions to use? | v4 for stability |
| uv vs pip in CI? | uv for speed |
| ruff vs black+flake8? | ruff (single tool) |
| Changelog extraction method? | awk pattern for simplicity |
| Archive format? | zip with exclusions |

## Recommendations Applied

1. **Use github-ecosystem skill patterns** as foundation
2. **Update action versions** to current stable (v4)
3. **Add shellcheck** for shell script validation
4. **Keep mypy non-strict initially** for gradual adoption
5. **Extract changelog** rather than auto-generate for quality notes
