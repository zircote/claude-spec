"""
Git operations wrapper for cs-memory.

Provides a clean interface to Git notes commands with proper error handling.
All operations use subprocess and parse Git output appropriately.
"""

import re
import subprocess
from pathlib import Path
from typing import Any

from .config import NAMESPACES
from .exceptions import StorageError


def validate_git_ref(ref: str) -> None:
    """
    Validate a Git reference to prevent command injection.

    Args:
        ref: Git reference (commit SHA, branch, tag)

    Raises:
        StorageError: If ref is invalid or potentially dangerous
    """
    if not ref:
        raise StorageError("Git ref cannot be empty", "Provide a valid reference")
    if ref.startswith("-"):
        raise StorageError("Invalid ref: cannot start with dash", "Check ref format")
    # Allow alphanumeric, dots, underscores, slashes, dashes, and tilde/caret for relative refs
    if not re.match(r"^[a-zA-Z0-9_./@^~-]+$", ref):
        raise StorageError(
            "Invalid ref format: contains illegal characters",
            "Use alphanumeric characters, dots, underscores, slashes, and dashes only",
        )


def validate_path(path: str) -> None:
    """
    Validate a file path to prevent command injection and path traversal.

    Args:
        path: File path relative to repo root

    Raises:
        StorageError: If path is invalid or potentially dangerous
    """
    if not path:
        raise StorageError("Path cannot be empty", "Provide a valid file path")
    if path.startswith("-"):
        raise StorageError("Invalid path: cannot start with dash", "Check path format")
    # Prevent absolute paths and null bytes
    if path.startswith("/") or "\x00" in path:
        raise StorageError(
            "Invalid path: absolute paths and null bytes not allowed",
            "Use relative paths from repository root",
        )
    # Allow common path characters but prevent shell metacharacters
    if not re.match(r"^[a-zA-Z0-9_./@-][a-zA-Z0-9_./@ -]*$", path):
        raise StorageError(
            "Invalid path format: contains illegal characters",
            "Use alphanumeric characters, dots, underscores, slashes, spaces, and dashes only",
        )


class GitOps:
    """
    Wrapper for Git notes operations.

    Handles add, append, show, list, and configuration of Git notes
    for the cs-memory namespaces.
    """

    def __init__(self, repo_path: Path | str | None = None):
        """
        Initialize GitOps for a repository.

        Args:
            repo_path: Path to git repository root. If None, uses cwd.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

    def _run_git(
        self,
        args: list[str],
        check: bool = True,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """
        Run a git command in the repository.

        Args:
            args: Git command arguments (without 'git' prefix)
            check: Raise on non-zero exit
            capture_output: Capture stdout/stderr

        Returns:
            CompletedProcess result

        Raises:
            StorageError: If command fails and check=True
        """
        cmd = ["git", "-C", str(self.repo_path)] + args

        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            # Parse common git errors
            stderr = e.stderr or ""
            if "not a git repository" in stderr.lower():
                raise StorageError(
                    "Not in a Git repository",
                    f"Initialize a git repository: cd {self.repo_path} && git init",
                ) from e
            if "permission denied" in stderr.lower():
                raise StorageError(
                    "Permission denied for Git operation",
                    "Check repository permissions and ownership",
                ) from e
            if "does not have any commits" in stderr.lower():
                raise StorageError(
                    "Repository has no commits",
                    "Create at least one commit: git commit --allow-empty -m 'initial'",
                ) from e
            raise StorageError(
                f"Git command failed: {' '.join(args)}\n{stderr}",
                "Check git status and try again",
            ) from e

    def _note_ref(self, namespace: str) -> str:
        """Get the full ref name for a namespace."""
        return f"cs/{namespace}"

    def _validate_namespace(self, namespace: str) -> None:
        """
        Validate namespace against allowed values.

        Args:
            namespace: Memory namespace to validate

        Raises:
            StorageError: If namespace is invalid
        """
        if namespace not in NAMESPACES:
            raise StorageError(
                f"Invalid namespace: {namespace}",
                f"Use one of: {', '.join(sorted(NAMESPACES))}",
            )

    def add_note(
        self,
        namespace: str,
        content: str,
        commit: str = "HEAD",
        force: bool = False,
    ) -> None:
        """
        Add a note to a commit.

        WARNING: This overwrites any existing note. Use append_note() for safe
        concurrent operations (FR-023).

        Args:
            namespace: Memory namespace (e.g., "decisions")
            content: Note content
            commit: Commit to attach note to (default: HEAD)
            force: Overwrite existing note if present

        Raises:
            StorageError: If operation fails
        """
        self._validate_namespace(namespace)
        validate_git_ref(commit)

        args = ["notes", f"--ref={self._note_ref(namespace)}", "add"]
        if force:
            args.append("-f")
        args.extend(["-m", content, commit])

        self._run_git(args)

    def append_note(
        self,
        namespace: str,
        content: str,
        commit: str = "HEAD",
    ) -> None:
        """
        Append content to a note (creates if not exists).

        This is the preferred method for capture operations per FR-023,
        as it safely handles concurrent operations without data loss.

        Args:
            namespace: Memory namespace
            content: Content to append
            commit: Commit to attach to (default: HEAD)

        Raises:
            StorageError: If operation fails
        """
        self._validate_namespace(namespace)
        validate_git_ref(commit)

        args = [
            "notes",
            f"--ref={self._note_ref(namespace)}",
            "append",
            "-m",
            content,
            commit,
        ]

        self._run_git(args)

    def show_note(
        self,
        namespace: str,
        commit: str = "HEAD",
    ) -> str | None:
        """
        Show the note content for a commit.

        Args:
            namespace: Memory namespace
            commit: Commit to get note from

        Returns:
            Note content, or None if no note exists
        """
        self._validate_namespace(namespace)
        validate_git_ref(commit)

        result = self._run_git(
            ["notes", f"--ref={self._note_ref(namespace)}", "show", commit],
            check=False,
        )

        if result.returncode != 0:
            return None

        return result.stdout

    def list_notes(
        self,
        namespace: str,
    ) -> list[tuple[str, str]]:
        """
        List all notes in a namespace.

        Args:
            namespace: Memory namespace

        Returns:
            List of (note_object_sha, commit_sha) tuples
        """
        self._validate_namespace(namespace)

        result = self._run_git(
            ["notes", f"--ref={self._note_ref(namespace)}", "list"],
            check=False,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return []

        notes = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                note_sha, commit_sha = parts[0], parts[1]
                notes.append((note_sha, commit_sha))

        return notes

    def remove_note(
        self,
        namespace: str,
        commit: str = "HEAD",
    ) -> bool:
        """
        Remove a note from a commit.

        Args:
            namespace: Memory namespace
            commit: Commit to remove note from

        Returns:
            True if note was removed, False if no note existed
        """
        # SEC-003: Add namespace validation
        self._validate_namespace(namespace)
        validate_git_ref(commit)

        result = self._run_git(
            ["notes", f"--ref={self._note_ref(namespace)}", "remove", commit],
            check=False,
        )
        return result.returncode == 0

    def is_sync_configured(self) -> dict[str, bool]:
        """
        Check if Git notes sync is already configured.

        Returns:
            Dict with configuration status for each component:
            - push: True if push refspec is configured
            - fetch: True if fetch refspec is configured
            - rewrite: True if rewriteRef is configured
            - merge: True if merge strategy is configured
        """
        status = {"push": False, "fetch": False, "rewrite": False, "merge": False}

        # Check push refspec
        result = self._run_git(
            ["config", "--get-all", "remote.origin.push"], check=False
        )
        if result.returncode == 0 and "refs/notes/cs" in result.stdout:
            status["push"] = True

        # Check fetch refspec
        result = self._run_git(
            ["config", "--get-all", "remote.origin.fetch"], check=False
        )
        if result.returncode == 0 and "refs/notes/cs" in result.stdout:
            status["fetch"] = True

        # Check rewriteRef
        result = self._run_git(
            ["config", "--get-all", "notes.rewriteRef"], check=False
        )
        if result.returncode == 0 and "refs/notes/cs" in result.stdout:
            status["rewrite"] = True

        # Check merge strategy
        result = self._run_git(
            ["config", "--get", "notes.cs.mergeStrategy"], check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            status["merge"] = True

        return status

    def configure_sync(self, force: bool = False) -> dict[str, bool]:
        """
        Configure Git to sync notes with remote (idempotent).

        Sets up push/fetch refspecs, rewriteRef for rebases, and merge strategy.
        Safe to call multiple times - only adds missing configuration.

        Args:
            force: If True, reconfigure even if already set

        Returns:
            Dict indicating which components were configured (True = newly configured)
        """
        configured = {"push": False, "fetch": False, "rewrite": False, "merge": False}

        # Check existing configuration
        current = self.is_sync_configured()

        # Configure push for all cs/* refs
        if force or not current["push"]:
            result = self._run_git(
                [
                    "config",
                    "--add",
                    "remote.origin.push",
                    "refs/notes/cs/*:refs/notes/cs/*",
                ],
                check=False,
            )
            configured["push"] = result.returncode == 0

        # Configure fetch for all cs/* refs
        if force or not current["fetch"]:
            result = self._run_git(
                [
                    "config",
                    "--add",
                    "remote.origin.fetch",
                    "refs/notes/cs/*:refs/notes/cs/*",
                ],
                check=False,
            )
            configured["fetch"] = result.returncode == 0

        # Configure rewriteRef for rebase support (preserves notes during rebase)
        if force or not current["rewrite"]:
            result = self._run_git(
                [
                    "config",
                    "--add",
                    "notes.rewriteRef",
                    "refs/notes/cs/*",
                ],
                check=False,
            )
            configured["rewrite"] = result.returncode == 0

        # Set merge strategy for notes
        if force or not current["merge"]:
            result = self._run_git(
                ["config", "notes.cs.mergeStrategy", "cat_sort_uniq"], check=False
            )
            configured["merge"] = result.returncode == 0

        return configured

    def get_commit_sha(self, ref: str = "HEAD") -> str:
        """
        Get the full SHA for a commit reference.

        Args:
            ref: Git ref (branch, tag, HEAD, etc.)

        Returns:
            Full commit SHA

        Raises:
            StorageError: If ref is invalid
        """
        validate_git_ref(ref)
        result = self._run_git(["rev-parse", ref])
        return result.stdout.strip()

    def get_commit_info(self, commit: str = "HEAD") -> dict[str, Any]:
        """
        Get metadata about a commit.

        Args:
            commit: Commit ref

        Returns:
            Dict with author, date, message fields
        """
        validate_git_ref(commit)

        # Get commit metadata in one call
        result = self._run_git(
            [
                "log",
                "-1",
                "--format=%H%n%an%n%ae%n%ai%n%s",
                commit,
            ]
        )

        lines = result.stdout.strip().split("\n")
        if len(lines) < 5:
            return {}

        return {
            "sha": lines[0],
            "author_name": lines[1],
            "author_email": lines[2],
            "date": lines[3],
            "message": lines[4],
        }

    def get_file_at_commit(
        self,
        path: str,
        commit: str = "HEAD",
    ) -> str | None:
        """
        Get file content at a specific commit.

        Args:
            path: File path relative to repo root
            commit: Commit ref

        Returns:
            File content, or None if file doesn't exist at commit
        """
        validate_path(path)
        validate_git_ref(commit)

        result = self._run_git(
            ["show", f"{commit}:{path}"],
            check=False,
        )

        if result.returncode != 0:
            return None

        return result.stdout

    def get_changed_files(self, commit: str = "HEAD") -> list[str]:
        """
        Get list of files changed in a commit.

        Args:
            commit: Commit ref

        Returns:
            List of file paths
        """
        validate_git_ref(commit)
        result = self._run_git(["show", "--name-only", "--format=", commit])

        return [f for f in result.stdout.strip().split("\n") if f]
