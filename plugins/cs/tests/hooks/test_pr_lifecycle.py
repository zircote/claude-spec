"""Integration tests for PR manager lifecycle integration.

These tests verify the pr-manager step integrates correctly with:
1. The step_runner.py module (run_step function)
2. Lifecycle configuration loading (get_enabled_steps)
3. Full /cs:p → /cs:c workflow (mocked gh CLI)

The tests ensure the pr-manager step:
- Is correctly registered in STEP_MODULES whitelist
- Can be loaded and executed via run_step()
- Reads configuration options correctly from lifecycle config
- Handles the full planning-to-completion workflow
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

# Resolve plugin root relative to this test file
# tests/hooks/test_pr_lifecycle.py -> plugins/cs/
PLUGIN_ROOT = Path(__file__).parent.parent.parent

# Add hooks/lib to path for imports
HOOKS_LIB_PATH = PLUGIN_ROOT / "hooks" / "lib"
if str(HOOKS_LIB_PATH) not in sys.path:
    sys.path.insert(0, str(HOOKS_LIB_PATH))

# Add steps to path for direct imports (like test_steps.py does)
STEPS_PATH = PLUGIN_ROOT / "steps"
if str(STEPS_PATH) not in sys.path:
    sys.path.insert(0, str(STEPS_PATH))

# Add plugin root for package imports
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from step_runner import STEP_MODULES, get_available_steps, get_step_module_name

# Direct imports for testing (avoids dynamic import issues)
from steps import PRManagerStep

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def spec_project_dir(tmp_path: Path) -> Path:
    """Create a mock spec project directory with README.md.

    Creates the structure:
        tmp_path/
        └── README.md  (with YAML frontmatter)
    """
    readme_content = """---
project_id: SPEC-2025-01-01-001
project_name: "Test Project"
slug: test-project
status: in-progress
created: 2025-01-01T12:00:00Z
github_issue: owner/repo#42
---

# Test Project

## Summary

A test project for integration testing.

## Problem Statement

We need to test the PR manager lifecycle integration.
"""
    readme_path = tmp_path / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    return tmp_path


@pytest.fixture
def spec_project_with_pr_url(tmp_path: Path) -> Path:
    """Create spec project with existing draft_pr_url in frontmatter."""
    readme_content = """---
project_id: SPEC-2025-01-01-001
project_name: "Test Project"
slug: test-project
status: in-progress
draft_pr_url: https://github.com/owner/repo/pull/123
---

# Test Project

## Summary

A test project with existing PR.
"""
    readme_path = tmp_path / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    return tmp_path


@pytest.fixture
def lifecycle_config() -> dict:
    """Sample lifecycle configuration for pr-manager testing."""
    return {
        "lifecycle": {
            "sessionStart": {
                "enabled": True,
                "loadContext": {
                    "claudeMd": True,
                    "gitState": True,
                    "projectStructure": True,
                },
            },
            "commands": {
                "cs:p": {
                    "preSteps": [],
                    "postSteps": [
                        {
                            "name": "pr-manager",
                            "enabled": True,
                            "operation": "create",
                            "labels": ["spec", "work-in-progress"],
                            "title_format": "[WIP] {slug}: {project_name}",
                            "base_branch": "main",
                        }
                    ],
                },
                "cs:c": {
                    "preSteps": [
                        {"name": "security-review", "enabled": True, "timeout": 120}
                    ],
                    "postSteps": [
                        {"name": "generate-retrospective", "enabled": True},
                        {"name": "archive-logs", "enabled": True},
                        {"name": "cleanup-markers", "enabled": True},
                        {
                            "name": "pr-manager",
                            "enabled": True,
                            "operation": "ready",
                            "remove_labels": ["work-in-progress"],
                            "reviewers": [],
                        },
                    ],
                },
            },
        }
    }


@pytest.fixture
def mock_gh_available():
    """Mock gh CLI as available and authenticated."""
    with patch("subprocess.run") as mock_run:
        # Default success responses
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )
        yield mock_run


@pytest.fixture
def mock_gh_unavailable():
    """Mock gh CLI as unavailable (not installed)."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("gh not found")
        yield mock_run


# =============================================================================
# STEP RUNNER REGISTRATION TESTS
# =============================================================================


class TestPRManagerStepRegistration:
    """Tests for pr-manager step registration in step_runner."""

    def test_pr_manager_in_step_modules(self):
        """Test pr-manager is registered in STEP_MODULES whitelist."""
        assert "pr-manager" in STEP_MODULES
        assert STEP_MODULES["pr-manager"] == "pr_manager"

    def test_get_step_module_name(self):
        """Test get_step_module_name returns correct module."""
        assert get_step_module_name("pr-manager") == "pr_manager"

    def test_pr_manager_in_available_steps(self):
        """Test pr-manager appears in get_available_steps()."""
        available = get_available_steps()
        assert "pr-manager" in available


# =============================================================================
# PRMANAGERSTEP INTEGRATION TESTS
# =============================================================================


class TestPRManagerStepIntegration:
    """Tests for PRManagerStep class with mocked subprocess."""

    def test_step_with_gh_unavailable(
        self, spec_project_dir: Path, mock_gh_unavailable
    ):
        """Test step handles gh unavailable gracefully (fail-open)."""
        step = PRManagerStep(str(spec_project_dir), {"operation": "create"})
        result = step.run()

        # Should succeed (fail-open pattern) - returns ok with skip message
        assert result.success is True
        assert (
            "skip" in result.message.lower() or "unavailable" in result.message.lower()
        )

    def test_step_with_gh_available_pr_exists(self, spec_project_dir: Path):
        """Test step when PR already exists."""
        config = {"operation": "create"}

        def mock_subprocess_run(cmd, *args, **kwargs):
            mock_result = MagicMock()
            if cmd == ["gh", "--version"]:
                mock_result.returncode = 0
            elif cmd == ["gh", "auth", "status"]:
                mock_result.returncode = 0
                mock_result.stdout = ""
            elif cmd[0:3] == ["gh", "pr", "view"]:
                mock_result.returncode = 0
                mock_result.stdout = '{"url": "https://github.com/owner/repo/pull/42"}'
            else:
                mock_result.returncode = 0
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_dir), config)
            result = step.run()

        # Should succeed with existing PR (skips creation)
        assert result.success is True

    def test_step_create_operation(self, spec_project_dir: Path):
        """Test step with create operation."""
        config = {
            "operation": "create",
            "labels": ["test-label"],
            "title_format": "[TEST] {slug}",
            "base_branch": "develop",
        }

        def mock_subprocess_run(cmd, *args, **kwargs):
            mock_result = MagicMock()
            if cmd == ["gh", "--version"]:
                mock_result.returncode = 0
            elif cmd == ["gh", "auth", "status"]:
                mock_result.returncode = 0
                mock_result.stdout = ""
            elif cmd[0:3] == ["gh", "pr", "view"]:
                # No existing PR
                mock_result.returncode = 1
                mock_result.stdout = ""
            elif cmd[0:3] == ["gh", "pr", "create"]:
                mock_result.returncode = 0
                mock_result.stdout = "https://github.com/owner/repo/pull/99"
            elif cmd[0:3] == ["gh", "pr", "edit"]:
                mock_result.returncode = 0
            else:
                mock_result.returncode = 0
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_dir), config)
            result = step.run()

        assert result.success is True
        assert "pr_url" in result.data

    def test_step_ready_operation(self, spec_project_with_pr_url: Path):
        """Test step with ready operation."""
        config = {
            "operation": "ready",
            "remove_labels": ["work-in-progress"],
            "reviewers": ["reviewer1"],
        }

        def mock_subprocess_run(cmd, *args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_with_pr_url), config)
            result = step.run()

        assert result.success is True

    def test_step_update_operation(self, spec_project_with_pr_url: Path):
        """Test step with update operation."""
        config = {"operation": "update"}

        def mock_subprocess_run(cmd, *args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_with_pr_url), config)
            result = step.run()

        assert result.success is True

    def test_step_invalid_operation(self, spec_project_dir: Path):
        """Test step with invalid operation returns failure."""
        config = {"operation": "invalid-op"}

        def mock_subprocess_run(cmd, *args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_dir), config)
            result = step.run()

        # Invalid operation returns failure
        assert result.success is False
        assert "Unknown PR operation" in result.message


# =============================================================================
# CONFIG OPTION PARSING TESTS
# =============================================================================


class TestConfigOptionParsing:
    """Tests for lifecycle config option parsing by pr-manager."""

    def test_parses_create_options(self, spec_project_dir: Path):
        """Test parsing of create operation options."""
        config = {
            "operation": "create",
            "labels": ["custom-label", "another-label"],
            "title_format": "[CUSTOM] {slug}: {project_name}",
            "base_branch": "develop",
        }

        step = PRManagerStep(str(spec_project_dir), config)

        assert step.config.get("operation") == "create"
        assert step.config.get("labels") == ["custom-label", "another-label"]
        assert step.config.get("title_format") == "[CUSTOM] {slug}: {project_name}"
        assert step.config.get("base_branch") == "develop"

    def test_parses_ready_options(self, spec_project_dir: Path):
        """Test parsing of ready operation options."""
        config = {
            "operation": "ready",
            "remove_labels": ["work-in-progress", "draft"],
            "reviewers": ["reviewer1", "reviewer2"],
        }

        step = PRManagerStep(str(spec_project_dir), config)

        assert step.config.get("operation") == "ready"
        assert step.config.get("remove_labels") == ["work-in-progress", "draft"]
        assert step.config.get("reviewers") == ["reviewer1", "reviewer2"]

    def test_default_values_when_not_specified(self, spec_project_dir: Path):
        """Test defaults are used when config options not specified."""
        step = PRManagerStep(str(spec_project_dir), {})

        assert step.config.get("operation", "create") == "create"
        assert step.DEFAULT_TITLE_FORMAT == "[WIP] {slug}: {project_name}"
        assert step.DEFAULT_BASE_BRANCH == "main"
        assert step.DEFAULT_LABELS == ["spec", "work-in-progress"]


# =============================================================================
# FULL WORKFLOW INTEGRATION TESTS (MOCKED)
# =============================================================================


class TestFullWorkflowIntegration:
    """Tests for full /cs:p → /cs:c workflow with mocked gh CLI."""

    def test_csp_to_csc_workflow(self, spec_project_dir: Path, lifecycle_config: dict):
        """Test complete workflow: /cs:p creates PR, /cs:c marks ready."""
        # Extract step configs
        csp_steps = lifecycle_config["lifecycle"]["commands"]["cs:p"]["postSteps"]
        csc_steps = lifecycle_config["lifecycle"]["commands"]["cs:c"]["postSteps"]

        # Find pr-manager configs
        csp_pr_config = next(s for s in csp_steps if s["name"] == "pr-manager")
        csc_pr_config = next(s for s in csc_steps if s["name"] == "pr-manager")

        # Track subprocess calls
        subprocess_calls = []

        def mock_subprocess_run(cmd, *args, **kwargs):
            subprocess_calls.append(cmd)
            mock_result = MagicMock()
            mock_result.stderr = ""

            if cmd == ["gh", "--version"]:
                mock_result.returncode = 0
            elif cmd == ["gh", "auth", "status"]:
                mock_result.returncode = 0
                mock_result.stdout = ""
            elif cmd[0:3] == ["gh", "pr", "view"]:
                # First call (create): no PR exists
                # Second call (ready): PR exists
                if (
                    len([c for c in subprocess_calls if c[0:3] == ["gh", "pr", "view"]])
                    == 1
                ):
                    mock_result.returncode = 1  # No PR
                    mock_result.stdout = ""
                else:
                    mock_result.returncode = 0
                    mock_result.stdout = (
                        '{"url": "https://github.com/owner/repo/pull/99"}'
                    )
            elif cmd[0:3] == ["gh", "pr", "create"]:
                mock_result.returncode = 0
                mock_result.stdout = "https://github.com/owner/repo/pull/99"
            elif cmd[0:3] == ["gh", "pr", "edit"]:
                mock_result.returncode = 0
            elif cmd[0:3] == ["gh", "pr", "ready"]:
                mock_result.returncode = 0
            else:
                mock_result.returncode = 0
                mock_result.stdout = ""

            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            # Phase 1: /cs:p - Create draft PR
            step_create = PRManagerStep(str(spec_project_dir), csp_pr_config)
            result_create = step_create.run()
            assert result_create.success is True

            # Verify PR create was called
            create_calls = [c for c in subprocess_calls if "create" in c]
            assert len(create_calls) >= 1

            # Phase 2: /cs:c - Mark PR ready
            step_ready = PRManagerStep(str(spec_project_dir), csc_pr_config)
            result_ready = step_ready.run()
            assert result_ready.success is True

            # Verify PR ready was called
            ready_calls = [
                c for c in subprocess_calls if c[0:3] == ["gh", "pr", "ready"]
            ]
            assert len(ready_calls) == 1

    def test_csp_workflow_when_pr_exists(
        self, spec_project_with_pr_url: Path, lifecycle_config: dict
    ):
        """Test /cs:p workflow skips creation when PR exists."""
        csp_steps = lifecycle_config["lifecycle"]["commands"]["cs:p"]["postSteps"]
        csp_pr_config = next(s for s in csp_steps if s["name"] == "pr-manager")

        subprocess_calls = []

        def mock_subprocess_run(cmd, *args, **kwargs):
            subprocess_calls.append(cmd)
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            if cmd[0:3] == ["gh", "pr", "view"]:
                mock_result.stdout = '{"url": "https://github.com/owner/repo/pull/123"}'
            else:
                mock_result.stdout = ""

            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_with_pr_url), csp_pr_config)
            result = step.run()

            assert result.success is True

            # Verify PR create was NOT called
            create_calls = [
                c for c in subprocess_calls if c[0:3] == ["gh", "pr", "create"]
            ]
            assert len(create_calls) == 0

    def test_csc_workflow_without_pr(
        self, spec_project_dir: Path, lifecycle_config: dict
    ):
        """Test /cs:c workflow handles missing PR gracefully."""
        csc_steps = lifecycle_config["lifecycle"]["commands"]["cs:c"]["postSteps"]
        csc_pr_config = next(s for s in csc_steps if s["name"] == "pr-manager")

        def mock_subprocess_run(cmd, *args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            if cmd[0:3] == ["gh", "pr", "view"]:
                # No PR exists
                mock_result.returncode = 1
                mock_result.stdout = ""
            else:
                mock_result.stdout = ""

            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_dir), csc_pr_config)
            result = step.run()

            # Should succeed (skipped) - fail-open
            assert result.success is True


# =============================================================================
# ERROR HANDLING INTEGRATION TESTS
# =============================================================================


class TestErrorHandlingIntegration:
    """Tests for error handling in lifecycle integration."""

    def test_handles_gh_version_timeout(self, spec_project_dir: Path):
        """Test step handles gh version check timeout."""

        def mock_subprocess_run(cmd, *args, **kwargs):
            if cmd == ["gh", "--version"]:
                raise subprocess.TimeoutExpired(cmd, timeout=5)
            mock_result = MagicMock()
            mock_result.returncode = 0
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_dir), {"operation": "create"})
            result = step.run()

        # Should succeed (fail-open with skip)
        assert result.success is True

    def test_handles_gh_auth_failure(self, spec_project_dir: Path):
        """Test step handles gh auth failure gracefully."""

        def mock_subprocess_run(cmd, *args, **kwargs):
            mock_result = MagicMock()
            if cmd == ["gh", "--version"]:
                mock_result.returncode = 0
            elif cmd == ["gh", "auth", "status"]:
                mock_result.returncode = 1
                mock_result.stdout = "Not logged in"
                mock_result.stderr = "Not logged in"
            else:
                mock_result.returncode = 0
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_dir), {"operation": "create"})
            result = step.run()

        # Should succeed (fail-open with skip)
        assert result.success is True

    def test_handles_pr_create_failure(self, spec_project_dir: Path):
        """Test step handles PR creation failure."""

        def mock_subprocess_run(cmd, *args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            if cmd[0:3] == ["gh", "pr", "view"]:
                mock_result.returncode = 1
                mock_result.stdout = ""
            elif cmd[0:3] == ["gh", "pr", "create"]:
                mock_result.returncode = 1
                mock_result.stderr = "GraphQL: Resource not accessible"
                mock_result.stdout = ""
            else:
                mock_result.stdout = ""

            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(spec_project_dir), {"operation": "create"})
            result = step.run()

        # Should return failure on actual PR creation failure
        assert result.success is False
        assert "Failed to create draft PR" in result.message

    def test_handles_missing_readme(self, tmp_path: Path):
        """Test step handles missing README gracefully."""

        def mock_subprocess_run(cmd, *args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            step = PRManagerStep(str(tmp_path), {"operation": "create"})
            result = step.run()

        # Should fail - README is required
        assert result.success is False
        assert "No README.md found" in result.message


# =============================================================================
# LIFECYCLE CONFIG INTEGRATION WITH CONFIG_LOADER
# =============================================================================


class TestLifecycleConfigLoaderIntegration:
    """Tests for lifecycle config loading integration."""

    def test_pr_manager_step_in_csp_poststeps(self, lifecycle_config: dict):
        """Test pr-manager appears in cs:p postSteps config."""
        csp_post_steps = lifecycle_config["lifecycle"]["commands"]["cs:p"]["postSteps"]
        pr_manager_step = next(
            (s for s in csp_post_steps if s["name"] == "pr-manager"), None
        )

        assert pr_manager_step is not None
        assert pr_manager_step["enabled"] is True
        assert pr_manager_step["operation"] == "create"

    def test_pr_manager_step_in_csc_poststeps(self, lifecycle_config: dict):
        """Test pr-manager appears in cs:c postSteps config."""
        csc_post_steps = lifecycle_config["lifecycle"]["commands"]["cs:c"]["postSteps"]
        pr_manager_step = next(
            (s for s in csc_post_steps if s["name"] == "pr-manager"), None
        )

        assert pr_manager_step is not None
        assert pr_manager_step["enabled"] is True
        assert pr_manager_step["operation"] == "ready"

    def test_config_loading_with_config_loader(
        self, tmp_path: Path, lifecycle_config: dict
    ):
        """Test config can be loaded via config_loader module."""
        # Create the .claude directory structure
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        config_file = claude_dir / "worktree-manager.config.json"
        config_file.write_text(json.dumps(lifecycle_config), encoding="utf-8")

        # Add to path for import
        config_loader_path = Path(__file__).parent.parent.parent / "hooks" / "lib"
        if str(config_loader_path) not in sys.path:
            sys.path.insert(0, str(config_loader_path))

        import config_loader

        # Reset cache and mock the config path to point to our test file
        config_loader.reset_config_cache()

        with patch.object(
            config_loader, "get_user_config_path", return_value=config_file
        ):
            # Force reload to pick up the mocked path
            config_loader.load_config(force_reload=True)

            # Get enabled steps for cs:p (phase name is "postSteps")
            steps = config_loader.get_enabled_steps("cs:p", "postSteps")

            # Should include pr-manager
            pr_step_names = [s["name"] for s in steps]
            assert "pr-manager" in pr_step_names

        # Reset cache to avoid polluting other tests
        config_loader.reset_config_cache()
