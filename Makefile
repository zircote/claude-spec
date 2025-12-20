.PHONY: install format format-check lint lint-fix typecheck security test shellcheck ci clean help version bump-patch bump-minor bump-major

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install dependencies with uv"
	@echo "  format       - Format code with ruff"
	@echo "  format-check - Check formatting (CI mode)"
	@echo "  lint         - Lint code with ruff"
	@echo "  lint-fix     - Lint and auto-fix issues"
	@echo "  typecheck    - Type check with mypy"
	@echo "  security     - Security scan with bandit"
	@echo "  test         - Run tests with coverage"
	@echo "  shellcheck   - Lint shell scripts"
	@echo "  ci           - Run all CI checks (mirrors GitHub Actions)"
	@echo "  clean        - Clean generated files"
	@echo ""
	@echo "Version Management:"
	@echo "  version      - Show current version and version files"
	@echo "  bump-patch   - Bump patch version (0.0.X)"
	@echo "  bump-minor   - Bump minor version (0.X.0)"
	@echo "  bump-major   - Bump major version (X.0.0)"

# Install dependencies (including dev tools: ruff, mypy, pytest, etc.)
install:
	uv sync --extra dev

# Format code
format:
	uv run ruff format .

# Check formatting (CI mode - fails if unformatted)
format-check:
	uv run ruff format --check .

# Lint code
lint:
	uv run ruff check .

# Lint and auto-fix
lint-fix:
	uv run ruff check --fix .

# Type check
typecheck:
	uv run mypy filters/ analyzers/ steps/

# Security scan
security:
	uv run bandit -r filters/ analyzers/ steps/ -ll

# Run tests with coverage
test:
	uv run pytest --cov=filters --cov=analyzers --cov=steps --cov-report=term-missing -v

# Shell script linting (exclude SC1091: can't follow dynamic $SCRIPT_DIR sources)
shellcheck:
	shellcheck -x -e SC1091 skills/worktree-manager/scripts/*.sh skills/worktree-manager/scripts/lib/*.sh

# Run all CI checks (mirrors GitHub Actions workflow)
ci: format-check lint typecheck security shellcheck test
	@echo ""
	@echo "=========================================="
	@echo "All CI checks passed!"
	@echo "=========================================="

# Clean generated files
clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Show current version and version files
version:
	@VERSION=$$(grep -m1 'current_version' pyproject.toml | cut -d'"' -f2) && \
	echo "Version: $$VERSION" && \
	echo "" && \
	echo "Locations:" && \
	echo "  pyproject.toml:3   - version = \"$$VERSION\"" && \
	echo "  pyproject.toml:79  - current_version = \"$$VERSION\" (bump-my-version)"

# Version management with bump-my-version
bump-patch:
	uv run bump-my-version bump patch

bump-minor:
	uv run bump-my-version bump minor

bump-major:
	uv run bump-my-version bump major
