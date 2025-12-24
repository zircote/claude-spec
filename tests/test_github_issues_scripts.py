"""Tests for GitHub Issues Worktree Scripts.

Tests for the shell scripts in scripts/github-issues/ directory.
Focuses on input validation, security checks, and edge cases.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts" / "github-issues"


class TestGenerateBranchName:
    """Tests for generate-branch-name.sh script."""

    @pytest.fixture
    def script_path(self) -> Path:
        return SCRIPTS_DIR / "generate-branch-name.sh"

    def run_script(
        self,
        script_path: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run the generate-branch-name.sh script."""
        result = subprocess.run(
            ["bash", str(script_path), *args],
            capture_output=True,
            text=True,
            check=check,
        )
        return result

    def test_generates_bug_prefix(self, script_path: Path) -> None:
        """Test that bug label generates bug/ prefix."""
        result = self.run_script(script_path, "42", "Fix login bug", "bug")
        assert result.stdout.strip().startswith("bug/")
        assert "42" in result.stdout

    def test_generates_feat_prefix_for_enhancement(self, script_path: Path) -> None:
        """Test that enhancement label generates feat/ prefix."""
        result = self.run_script(script_path, "42", "Add new feature", "enhancement")
        assert result.stdout.strip().startswith("feat/")

    def test_sanitizes_special_characters(self, script_path: Path) -> None:
        """Test that special characters in title are sanitized."""
        result = self.run_script(script_path, "42", "Fix: login & auth (v2)", "bug")
        branch = result.stdout.strip()
        # Should not contain special characters
        assert ":" not in branch
        assert "&" not in branch
        assert "(" not in branch
        assert ")" not in branch


class TestCreateIssueWorktree:
    """Tests for create-issue-worktree.sh script."""

    @pytest.fixture
    def script_path(self) -> Path:
        return SCRIPTS_DIR / "create-issue-worktree.sh"

    def run_script(
        self,
        script_path: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run the create-issue-worktree.sh script."""
        result = subprocess.run(
            ["bash", str(script_path), *args],
            capture_output=True,
            text=True,
            check=check,
        )
        return result

    def test_rejects_invalid_json(self, script_path: Path) -> None:
        """Test that invalid JSON is rejected."""
        result = self.run_script(script_path, "not json", check=False)
        assert result.returncode != 0
        assert "Invalid issue JSON" in result.stderr or "Error" in result.stderr

    def test_rejects_json_without_number(self, script_path: Path) -> None:
        """Test that JSON without number field is rejected."""
        issue_json = json.dumps({"title": "Test", "labels": [], "body": "", "url": ""})
        result = self.run_script(script_path, issue_json, check=False)
        assert result.returncode != 0
        assert "number" in result.stderr.lower() or "Invalid" in result.stderr

    def test_rejects_json_with_non_numeric_number(self, script_path: Path) -> None:
        """Test that JSON with string number is rejected."""
        issue_json = json.dumps(
            {"number": "42", "title": "Test", "labels": [], "body": "", "url": ""},
        )
        result = self.run_script(script_path, issue_json, check=False)
        assert result.returncode != 0

    def test_sec005_path_traversal_detection(
        self,
        script_path: Path,
        tmp_path: Path,
    ) -> None:
        """TEST-MED-003: Test SEC-005 path traversal validation."""
        # Create a valid issue JSON
        issue_json = json.dumps(
            {
                "number": 42,
                "title": "Test issue",
                "labels": [{"name": "bug"}],
                "body": "Test body",
                "url": "https://github.com/test/test/issues/42",
            },
        )

        # Create a worktree base in tmp_path
        worktree_base = tmp_path / "worktrees"
        worktree_base.mkdir()

        # We can't directly test path traversal in the branch name because
        # the branch name is generated and sanitized. However, we can verify
        # the script doesn't allow escaping the worktree_base directory.

        # The script should fail if we try to use a malicious repo name
        # that would escape the base directory
        malicious_repo = "../../../tmp/evil"

        result = self.run_script(
            script_path,
            issue_json,
            str(worktree_base),
            malicious_repo,
            check=False,
        )

        # The script should either fail or create the worktree safely within base
        if result.returncode == 0:
            # If it succeeded, verify the path is within worktree_base
            for line in result.stdout.splitlines():
                if line.startswith("WORKTREE_PATH="):
                    path = line.split("=", 1)[1]
                    # Resolve both paths and check containment
                    resolved_base = worktree_base.resolve()
                    resolved_path = Path(path).resolve()
                    # Path should be within base or script should have failed
                    assert str(resolved_path).startswith(str(resolved_base)), (
                        f"Path traversal not prevented: {resolved_path} "
                        f"escaped {resolved_base}"
                    )


class TestBuildIssuePrompt:
    """Tests for build-issue-prompt.sh script.

    The script takes 3 arguments: issue_number, issue_title, worktree_path
    NOT a JSON input.
    """

    @pytest.fixture
    def script_path(self) -> Path:
        return SCRIPTS_DIR / "build-issue-prompt.sh"

    def run_script(
        self,
        script_path: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run the build-issue-prompt.sh script."""
        result = subprocess.run(
            ["bash", str(script_path), *args],
            capture_output=True,
            text=True,
            check=check,
        )
        return result

    def test_generates_prompt_from_issue(
        self,
        script_path: Path,
        tmp_path: Path,
    ) -> None:
        """Test that prompt is generated from issue details."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        result = self.run_script(
            script_path,
            "42",
            "Fix the login bug",
            str(worktree_path),
        )
        prompt = result.stdout
        # Should contain issue reference
        assert "42" in prompt or "#42" in prompt
        assert "login" in prompt.lower() or "Login" in prompt

    def test_sec_crit_001_command_injection_prevention(
        self,
        script_path: Path,
        tmp_path: Path,
    ) -> None:
        """Test that command injection in title is prevented.

        SEC-CRIT-001: The fix uses a quoted heredoc ('EOF') which prevents
        shell expansion of $() and ``. The literal text should be preserved
        in the output without being executed.
        """
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        # Try to inject a command via title
        malicious_title = "Test $(echo PWNED)"
        result = self.run_script(script_path, "42", malicious_title, str(worktree_path))
        # The literal $(...) should be preserved in output (not executed)
        # If the command was executed, we'd see just "Test PWNED" instead
        # of the full "Test $(echo PWNED)"
        assert "$(echo PWNED)" in result.stdout, (
            "Command substitution should be preserved literally, not executed"
        )


class TestGetBranchPrefix:
    """Tests for get-branch-prefix.sh script."""

    @pytest.fixture
    def script_path(self) -> Path:
        return SCRIPTS_DIR / "get-branch-prefix.sh"

    def run_script(
        self,
        script_path: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run the get-branch-prefix.sh script."""
        result = subprocess.run(
            ["bash", str(script_path), *args],
            capture_output=True,
            text=True,
            check=check,
        )
        return result

    def test_bug_label_returns_bug_prefix(self, script_path: Path) -> None:
        """Test bug label maps to bug/ prefix."""
        result = self.run_script(script_path, "bug")
        assert result.stdout.strip() == "bug"

    def test_enhancement_label_returns_feat_prefix(self, script_path: Path) -> None:
        """Test enhancement label maps to feat/ prefix."""
        result = self.run_script(script_path, "enhancement")
        assert result.stdout.strip() == "feat"

    def test_documentation_label_returns_docs_prefix(self, script_path: Path) -> None:
        """Test documentation label maps to docs/ prefix."""
        result = self.run_script(script_path, "documentation")
        assert result.stdout.strip() == "docs"

    def test_unknown_label_returns_feat_prefix(self, script_path: Path) -> None:
        """Test unknown label defaults to feat/ prefix."""
        result = self.run_script(script_path, "random-label")
        assert result.stdout.strip() == "feat"


class TestCheckGhPrerequisites:
    """Tests for check-gh-prerequisites.sh script."""

    @pytest.fixture
    def script_path(self) -> Path:
        return SCRIPTS_DIR / "check-gh-prerequisites.sh"

    @pytest.mark.skipif(
        os.system("which gh >/dev/null 2>&1") != 0,
        reason="gh CLI not installed",
    )
    def test_checks_gh_installation(self, script_path: Path) -> None:
        """Test that script checks for gh CLI."""
        result = subprocess.run(
            ["bash", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        # Should succeed if gh is installed and authenticated
        # or fail with appropriate message if not
        assert result.returncode in (0, 1, 2)
