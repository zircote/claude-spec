"""
PR Manager Step - Creates and manages GitHub draft PRs for spec projects.

This step integrates with the gh CLI to create draft pull requests
at the start of planning (/cs:p) and convert them to ready on
completion (/cs:c).

Requirements
------------

**gh CLI Installation**:
    This step requires the GitHub CLI (``gh``) to be installed and authenticated::

        # macOS
        brew install gh
        gh auth login

        # Linux
        sudo apt install gh
        gh auth login

    If gh is not installed or not authenticated, the step completes with a
    warning and skips PR operations. This is intentional - the step follows
    the "fail-open" philosophy and does not block workflow if gh is unavailable.

Configuration Options
---------------------

The step accepts the following configuration options via lifecycle config:

.. code-block:: json

    {
        "name": "pr-manager",
        "enabled": true,
        "operation": "create",
        "labels": ["spec", "work-in-progress"],
        "title_format": "[WIP] {slug}: {project_name}",
        "base_branch": "main"
    }

Options:
    - ``enabled`` (bool): Whether to run the step. Default: ``true``
    - ``operation`` (str): PR operation to perform. Options: "create", "update", "ready"
    - ``labels`` (list[str]): Labels to add to the PR
    - ``title_format`` (str): Format string for PR title
    - ``base_branch`` (str): Base branch for PR. Default: "main"
    - ``remove_labels`` (list[str]): Labels to remove (for "ready" operation)
    - ``reviewers`` (list[str]): GitHub usernames to request reviews from

Operations
----------

**create**:
    Creates a new draft PR for the spec project. Checks for existing PR first
    to avoid duplicates. Stores PR URL in README.md frontmatter.

**update**:
    Updates the PR body with current phase progress. Used at phase transitions
    during /cs:p workflow.

**ready**:
    Converts draft PR to ready-for-review. Removes work-in-progress label,
    optionally adds reviewers. Used by /cs:c command.

Hook Integration
----------------

This step is typically configured as a post-step for ``/cs:p`` and ``/cs:c``::

    {
        "commands": {
            "cs:p": {
                "postSteps": [
                    { "name": "pr-manager", "enabled": true, "operation": "create" }
                ]
            },
            "cs:c": {
                "postSteps": [
                    { "name": "pr-manager", "enabled": true, "operation": "ready" }
                ]
            }
        }
    }
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .base import BaseStep, ErrorCode, StepResult


class PRManagerStep(BaseStep):
    """Manages GitHub draft PR operations for spec projects.

    Creates draft PRs at planning inception, updates PR body at phase
    transitions, and converts to ready-for-review on completion.
    Follows fail-open philosophy - gracefully degrades if gh unavailable.

    Attributes:
        name: Step identifier ("pr-manager").
        GH_VERSION_TIMEOUT: Timeout for gh version check (seconds).
        GH_AUTH_TIMEOUT: Timeout for gh auth status check (seconds).
    """

    name = "pr-manager"

    # Timeouts in seconds
    GH_VERSION_TIMEOUT = 5
    GH_AUTH_TIMEOUT = 10
    GH_PR_TIMEOUT = 30  # PR operations may take longer

    # Default configuration values
    DEFAULT_TITLE_FORMAT = "[WIP] {slug}: {project_name}"
    DEFAULT_BASE_BRANCH = "main"
    DEFAULT_LABELS = ["spec", "work-in-progress"]

    def __init__(self, cwd: str, config: dict[str, Any] | None = None):
        """Initialize the PR manager step.

        Args:
            cwd: Current working directory (spec project root).
            config: Optional configuration from lifecycle config.
        """
        super().__init__(cwd, config)
        self._skip_reason: str | None = None

    def validate(self) -> bool:
        """Check gh CLI availability (non-blocking).

        Validates that gh CLI is installed and authenticated. If not,
        stores the skip reason but still returns True (fail-open pattern).
        The execute() method will check _skip_reason and handle gracefully.

        Returns:
            Always True - validation never blocks (fail-open philosophy).
        """
        available, reason = self._check_gh_available()
        if not available:
            self._skip_reason = reason
        return True  # Always pass - fail-open

    def execute(self) -> StepResult:
        """Execute the configured PR operation.

        Checks for skip reason from validate(), then dispatches to the
        appropriate operation method based on config["operation"].

        Returns:
            StepResult indicating success/skip/failure with PR URL in data.
        """
        # Check if we should skip due to gh unavailability
        if self._skip_reason:
            result = StepResult.ok(
                f"PR manager skipped ({self._skip_reason})",
                skipped=True,
                reason=self._skip_reason,
            )
            result.add_warning(f"GitHub PR operations unavailable: {self._skip_reason}")
            return result

        # Get operation from config (default: create)
        operation = self.config.get("operation", "create")

        # Dispatch to appropriate operation method
        if operation == "create":
            return self._create_draft_pr()
        elif operation == "update":
            return self._update_pr_body()
        elif operation == "ready":
            return self._mark_pr_ready()
        else:
            return StepResult.fail(
                f"Unknown PR operation: {operation}",
                error_code=ErrorCode.CONFIG,
            )

    def _check_gh_available(self) -> tuple[bool, str]:
        """Check if gh CLI is available and authenticated.

        Performs two checks:
        1. gh --version: Verifies gh CLI is installed
        2. gh auth status: Verifies user is authenticated

        Returns:
            Tuple of (available: bool, reason: str).
            If available is True, reason is empty string.
            If available is False, reason describes why.
        """
        try:
            # Check installation
            subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                timeout=self.GH_VERSION_TIMEOUT,
                check=True,
            )
        except FileNotFoundError:
            return (False, "gh CLI not installed")
        except subprocess.TimeoutExpired:
            return (False, "gh version check timed out")
        except subprocess.CalledProcessError:
            return (False, "gh version check failed")

        try:
            # Check authentication
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=self.GH_AUTH_TIMEOUT,
            )
            if result.returncode != 0:
                return (False, "gh not authenticated (run: gh auth login)")
        except subprocess.TimeoutExpired:
            return (False, "gh auth check timed out")
        except subprocess.CalledProcessError:
            return (False, "gh auth check failed")

        return (True, "")

    def _find_spec_readme(self) -> Path | None:
        """Find the spec project README.md file.

        Looks for README.md in the current working directory, which should
        be the spec project directory (e.g., docs/spec/active/2025-01-01-slug/).

        Returns:
            Path to README.md if found, None otherwise.
        """
        readme_path = Path(self.cwd) / "README.md"
        if readme_path.exists():
            return readme_path
        return None

    def _parse_readme_frontmatter(self, readme_path: Path) -> dict[str, Any]:
        """Parse YAML frontmatter from spec README.md.

        Extracts frontmatter between --- markers at the start of the file.
        Uses simple parsing to avoid pyyaml dependency issues with multiline.

        Args:
            readme_path: Path to the README.md file.

        Returns:
            Dictionary of frontmatter fields. Empty dict if no frontmatter.
        """
        try:
            content = readme_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return {}

        # Check for frontmatter markers
        if not content.startswith("---"):
            return {}

        # Find closing marker
        lines = content.split("\n")
        end_idx = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_idx = i
                break

        if end_idx is None:
            return {}

        # Parse simple key: value pairs
        frontmatter: dict[str, Any] = {}
        for line in lines[1:end_idx]:
            if ":" in line and not line.strip().startswith("#"):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                # Handle arrays first (simple single-line)
                if value.startswith("[") and value.endswith("]"):
                    # Parse simple array: [item1, item2]
                    inner = value[1:-1]
                    if inner:
                        items = [item.strip().strip("\"'") for item in inner.split(",")]
                        frontmatter[key] = items
                    else:
                        frontmatter[key] = []
                # Handle quoted strings
                elif value.startswith('"') and value.endswith('"'):
                    frontmatter[key] = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    frontmatter[key] = value[1:-1]
                else:
                    frontmatter[key] = value

        return frontmatter

    def _get_existing_pr_url(self) -> str | None:
        """Check if a PR already exists for the current branch.

        Uses `gh pr view --json url` to check for existing PR.

        Returns:
            PR URL if exists, None otherwise.
        """
        try:
            result = subprocess.run(
                ["gh", "pr", "view", "--json", "url"],
                capture_output=True,
                text=True,
                timeout=self.GH_PR_TIMEOUT,
                cwd=self.cwd,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("url")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            # Fail-open: gh CLI errors should not block workflow
            pass
        return None

    def _build_pr_title(self, frontmatter: dict[str, Any]) -> str:
        """Build PR title from config template and frontmatter.

        Args:
            frontmatter: Parsed README frontmatter.

        Returns:
            Formatted PR title string.
        """
        title_format = self.config.get("title_format", self.DEFAULT_TITLE_FORMAT)
        slug = frontmatter.get("slug", "unknown")
        project_name = frontmatter.get("project_name", slug)
        return title_format.format(slug=slug, project_name=project_name)

    def _build_pr_body(self, readme_path: Path, frontmatter: dict[str, Any]) -> str:
        """Build PR body from spec README content.

        Includes problem statement, key documents table, and spec metadata.

        Args:
            readme_path: Path to spec README.md.
            frontmatter: Parsed README frontmatter.

        Returns:
            Formatted PR body string (Markdown).
        """
        try:
            content = readme_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            content = ""

        # Extract summary section if present
        summary = ""
        if "## Summary" in content:
            start = content.find("## Summary")
            end = content.find("\n## ", start + 1)
            if end == -1:
                end = len(content)
            summary = content[start:end].strip()

        # Extract problem statement if present
        problem = ""
        if "## Problem Statement" in content:
            start = content.find("## Problem Statement")
            end = content.find("\n## ", start + 1)
            if end == -1:
                end = len(content)
            problem = content[start:end].strip()

        # Build body
        parts = [
            "## Spec Project Draft PR",
            "",
            f"**Project**: {frontmatter.get('project_name', 'Unknown')}",
            f"**Slug**: `{frontmatter.get('slug', 'unknown')}`",
            f"**Status**: {frontmatter.get('status', 'in-progress')}",
            "",
        ]

        if frontmatter.get("github_issue"):
            parts.append(f"**Linked Issue**: {frontmatter['github_issue']}")
            parts.append("")

        if summary:
            parts.append(summary)
            parts.append("")

        if problem:
            parts.append(problem)
            parts.append("")

        parts.extend(
            [
                "---",
                "",
                "*This is a draft PR created by `/cs:p` for spec visibility.*",
                "*PR will be marked ready for review on `/cs:c` completion.*",
            ]
        )

        return "\n".join(parts)

    def _create_draft_pr(self) -> StepResult:
        """Create a draft PR for the spec project.

        Checks for existing PR first to avoid duplicates, builds title and
        body from spec README, then executes `gh pr create --draft`.

        Returns:
            StepResult with pr_url in data on success.
        """
        # Find spec README
        readme_path = self._find_spec_readme()
        if not readme_path:
            return StepResult.fail(
                "No README.md found in spec directory",
                error_code=ErrorCode.IO,
            )

        # Parse frontmatter
        frontmatter = self._parse_readme_frontmatter(readme_path)
        if not frontmatter:
            result = StepResult.ok(
                "README has no frontmatter, skipping PR creation",
                skipped=True,
                pr_url=None,
            )
            result.add_warning("README.md missing frontmatter - cannot build PR title")
            return result

        # Check for existing PR
        existing_url = self._get_existing_pr_url()
        if existing_url:
            result = StepResult.ok(
                f"PR already exists: {existing_url}",
                pr_url=existing_url,
                already_exists=True,
            )
            result.add_warning(f"Using existing PR: {existing_url}")
            return result

        # Build title and body
        title = self._build_pr_title(frontmatter)
        body = self._build_pr_body(readme_path, frontmatter)
        base_branch = self.config.get("base_branch", self.DEFAULT_BASE_BRANCH)

        # Create draft PR
        try:
            cmd = [
                "gh",
                "pr",
                "create",
                "--draft",
                "--title",
                title,
                "--body",
                body,
                "--base",
                base_branch,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.GH_PR_TIMEOUT,
                cwd=self.cwd,
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                return StepResult.fail(
                    f"Failed to create draft PR: {error_msg}",
                    error_code=ErrorCode.DEPENDENCY,
                )

            # Parse PR URL from output (gh outputs URL on success)
            pr_url = result.stdout.strip()
            if not pr_url.startswith("http"):
                # Try to extract URL from output
                url_match = re.search(r"https://github\.com/\S+", result.stdout)
                if url_match:
                    pr_url = url_match.group(0)
                else:
                    return StepResult.fail(
                        "Could not parse PR URL from gh output",
                        error_code=ErrorCode.PARSE,
                    )

            # Store PR URL in frontmatter
            store_result = self._store_pr_url(readme_path, pr_url)
            if not store_result.success:
                # PR created but URL storage failed - still return success with warning
                step_result = StepResult.ok(
                    f"Draft PR created: {pr_url}",
                    pr_url=pr_url,
                )
                step_result.add_warning(
                    f"PR URL not saved to README: {store_result.message}"
                )
                return step_result

            # Add labels if configured
            labels = self.config.get("labels", self.DEFAULT_LABELS)
            if labels:
                label_result = self._add_labels(pr_url, labels)
                if not label_result.success:
                    step_result = StepResult.ok(
                        f"Draft PR created: {pr_url}",
                        pr_url=pr_url,
                    )
                    step_result.add_warning(
                        f"Failed to add labels: {label_result.message}"
                    )
                    return step_result

            return StepResult.ok(
                f"Draft PR created: {pr_url}",
                pr_url=pr_url,
            )

        except subprocess.TimeoutExpired:
            return StepResult.fail(
                "PR creation timed out",
                error_code=ErrorCode.TIMEOUT,
            )
        except OSError as e:
            return StepResult.fail(
                f"Failed to execute gh: {e}",
                error_code=ErrorCode.DEPENDENCY,
            )

    def _store_pr_url(self, readme_path: Path, pr_url: str) -> StepResult:
        """Store PR URL in README frontmatter.

        Adds or updates the `draft_pr_url` field in the README frontmatter
        while preserving existing content and formatting.

        Args:
            readme_path: Path to the README.md file.
            pr_url: PR URL to store.

        Returns:
            StepResult indicating success or failure.
        """
        try:
            content = readme_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return StepResult.fail(
                f"Could not read README: {e}",
                error_code=ErrorCode.IO,
            )

        # Check for frontmatter
        if not content.startswith("---"):
            return StepResult.fail(
                "README has no frontmatter",
                error_code=ErrorCode.PARSE,
            )

        # Find end of frontmatter
        lines = content.split("\n")
        end_idx = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_idx = i
                break

        if end_idx is None:
            return StepResult.fail(
                "Malformed frontmatter - no closing ---",
                error_code=ErrorCode.PARSE,
            )

        # Check if draft_pr_url already exists
        has_pr_url = False
        for i in range(1, end_idx):
            if lines[i].startswith("draft_pr_url:"):
                # Update existing entry
                lines[i] = f"draft_pr_url: {pr_url}"
                has_pr_url = True
                break

        if not has_pr_url:
            # Insert new entry before closing ---
            lines.insert(end_idx, f"draft_pr_url: {pr_url}")

        # Write back
        try:
            readme_path.write_text("\n".join(lines), encoding="utf-8")
        except OSError as e:
            return StepResult.fail(
                f"Could not write README: {e}",
                error_code=ErrorCode.IO,
            )

        return StepResult.ok(
            f"PR URL stored in frontmatter: {pr_url}",
            pr_url=pr_url,
        )

    def _add_labels(self, pr_url: str, labels: list[str]) -> StepResult:
        """Add labels to a PR.

        Args:
            pr_url: PR URL to add labels to.
            labels: List of label names.

        Returns:
            StepResult indicating success or failure.
        """
        if not labels:
            return StepResult.ok("No labels to add")

        try:
            # gh pr edit accepts comma-separated labels
            labels_str = ",".join(labels)
            result = subprocess.run(
                ["gh", "pr", "edit", pr_url, "--add-label", labels_str],
                capture_output=True,
                text=True,
                timeout=self.GH_PR_TIMEOUT,
                cwd=self.cwd,
            )
            if result.returncode != 0:
                # Don't fail on label errors - labels might not exist
                return StepResult.ok(
                    f"Could not add labels: {result.stderr.strip()}",
                    labels_added=False,
                )
            return StepResult.ok(
                f"Labels added: {labels_str}",
                labels_added=True,
            )
        except subprocess.TimeoutExpired:
            return StepResult.ok(
                "Label operation timed out",
                labels_added=False,
            )
        except OSError as e:
            return StepResult.ok(
                f"Label operation failed: {e}",
                labels_added=False,
            )

    def _get_pr_number_from_url(self, pr_url: str) -> str | None:
        """Extract PR number from URL.

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

        Returns:
            PR number as string, or None if parsing fails.
        """
        match = re.search(r"/pull/(\d+)", pr_url)
        if match:
            return match.group(1)
        return None

    def _get_stored_pr_url(self) -> str | None:
        """Get PR URL from README frontmatter.

        Returns:
            PR URL if found in frontmatter, None otherwise.
        """
        readme_path = self._find_spec_readme()
        if not readme_path:
            return None
        frontmatter = self._parse_readme_frontmatter(readme_path)
        return frontmatter.get("draft_pr_url")

    def _update_pr_body(self) -> StepResult:
        """Update the PR body with current phase progress.

        Reads the spec README, rebuilds the PR body with current status,
        and updates the PR using `gh pr edit`.

        Returns:
            StepResult indicating update success.
        """
        # Get PR URL from frontmatter or existing PR
        pr_url = self._get_stored_pr_url() or self._get_existing_pr_url()
        if not pr_url:
            return StepResult.fail(
                "No PR found to update (check draft_pr_url in README or existing PR)",
                error_code=ErrorCode.VALIDATION,
            )

        # Find spec README and rebuild body
        readme_path = self._find_spec_readme()
        if not readme_path:
            return StepResult.fail(
                "No README.md found in spec directory",
                error_code=ErrorCode.IO,
            )

        frontmatter = self._parse_readme_frontmatter(readme_path)
        body = self._build_pr_body(readme_path, frontmatter)

        # Update PR body
        try:
            result = subprocess.run(
                ["gh", "pr", "edit", pr_url, "--body", body],
                capture_output=True,
                text=True,
                timeout=self.GH_PR_TIMEOUT,
                cwd=self.cwd,
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                return StepResult.fail(
                    f"Failed to update PR body: {error_msg}",
                    error_code=ErrorCode.DEPENDENCY,
                )
            return StepResult.ok(
                f"PR body updated: {pr_url}",
                pr_url=pr_url,
            )
        except subprocess.TimeoutExpired:
            return StepResult.fail(
                "PR update timed out",
                error_code=ErrorCode.TIMEOUT,
            )
        except OSError as e:
            return StepResult.fail(
                f"Failed to execute gh: {e}",
                error_code=ErrorCode.DEPENDENCY,
            )

    def _mark_pr_ready(self) -> StepResult:
        """Convert draft PR to ready-for-review.

        Reads the PR URL from frontmatter, executes `gh pr ready`,
        removes work-in-progress label, and optionally adds reviewers.

        Returns:
            StepResult indicating ready conversion success.
        """
        # Get PR URL from frontmatter or existing PR
        pr_url = self._get_stored_pr_url() or self._get_existing_pr_url()
        if not pr_url:
            result = StepResult.ok(
                "No PR found to mark ready",
                skipped=True,
            )
            result.add_warning("No draft PR URL found in README or existing PR")
            return result

        # Mark PR as ready
        try:
            result = subprocess.run(
                ["gh", "pr", "ready", pr_url],
                capture_output=True,
                text=True,
                timeout=self.GH_PR_TIMEOUT,
                cwd=self.cwd,
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                # PR might already be ready - not a failure
                if "already" in error_msg.lower():
                    step_result = StepResult.ok(
                        f"PR already ready: {pr_url}",
                        pr_url=pr_url,
                    )
                    step_result.add_warning("PR was already marked ready")
                    return step_result
                return StepResult.fail(
                    f"Failed to mark PR ready: {error_msg}",
                    error_code=ErrorCode.DEPENDENCY,
                )
        except subprocess.TimeoutExpired:
            return StepResult.fail(
                "PR ready operation timed out",
                error_code=ErrorCode.TIMEOUT,
            )
        except OSError as e:
            return StepResult.fail(
                f"Failed to execute gh: {e}",
                error_code=ErrorCode.DEPENDENCY,
            )

        # Remove work-in-progress label if configured
        remove_labels = self.config.get("remove_labels", ["work-in-progress"])
        if remove_labels:
            try:
                labels_str = ",".join(remove_labels)
                subprocess.run(
                    ["gh", "pr", "edit", pr_url, "--remove-label", labels_str],
                    capture_output=True,
                    text=True,
                    timeout=self.GH_PR_TIMEOUT,
                    cwd=self.cwd,
                )
                # Ignore errors - labels might not exist
            except (subprocess.TimeoutExpired, OSError):
                # Label removal is best-effort, don't fail if gh CLI errors
                pass

        # Add reviewers if configured
        reviewers = self.config.get("reviewers", [])
        if reviewers:
            try:
                reviewers_str = ",".join(reviewers)
                subprocess.run(
                    ["gh", "pr", "edit", pr_url, "--add-reviewer", reviewers_str],
                    capture_output=True,
                    text=True,
                    timeout=self.GH_PR_TIMEOUT,
                    cwd=self.cwd,
                )
                # Ignore errors - reviewers might not be valid
            except (subprocess.TimeoutExpired, OSError):
                # Reviewer assignment is best-effort, don't fail if gh CLI errors
                pass

        return StepResult.ok(
            f"PR marked ready for review: {pr_url}",
            pr_url=pr_url,
        )


def run(cwd: str, config: dict[str, Any] | None = None) -> StepResult:
    """Module-level run function for hook integration.

    This function is the entry point called by the hook system when
    executing the pr-manager step.

    Args:
        cwd: Current working directory (spec project root)
        config: Optional step configuration from lifecycle config

    Returns:
        StepResult from step execution
    """
    step = PRManagerStep(cwd, config)
    return step.run()
