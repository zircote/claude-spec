"""
Git operations wrapper for cs-memory.

Provides a clean interface to Git notes commands with proper error handling.
All operations use subprocess and parse Git output appropriately.
"""

import subprocess
from pathlib import Path
from typing import Any

from .config import NAMESPACES
from .exceptions import StorageError


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
        if namespace not in NAMESPACES:
            raise StorageError(
                f"Invalid namespace: {namespace}",
                f"Use one of: {', '.join(sorted(NAMESPACES))}",
            )

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
        if namespace not in NAMESPACES:
            raise StorageError(
                f"Invalid namespace: {namespace}",
                f"Use one of: {', '.join(sorted(NAMESPACES))}",
            )

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
        if namespace not in NAMESPACES:
            raise StorageError(
                f"Invalid namespace: {namespace}",
                f"Use one of: {', '.join(sorted(NAMESPACES))}",
            )

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
        if namespace not in NAMESPACES:
            raise StorageError(
                f"Invalid namespace: {namespace}",
                f"Use one of: {', '.join(sorted(NAMESPACES))}",
            )

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
        result = self._run_git(
            ["notes", f"--ref={self._note_ref(namespace)}", "remove", commit],
            check=False,
        )
        return result.returncode == 0

    def configure_sync(self) -> None:
        """
        Configure Git to sync notes with remote.

        Sets up push and fetch refspecs for all cs/* namespaces.
        This should be called once per repository setup.
        """
        # Configure push for all cs/* refs
        self._run_git(
            [
                "config",
                "--add",
                "remote.origin.push",
                "refs/notes/cs/*:refs/notes/cs/*",
            ],
            check=False,
        )

        # Configure fetch for all cs/* refs
        self._run_git(
            [
                "config",
                "--add",
                "remote.origin.fetch",
                "refs/notes/cs/*:refs/notes/cs/*",
            ],
            check=False,
        )

        # Set merge strategy for notes
        self._run_git(
            ["config", "notes.cs.mergeStrategy", "cat_sort_uniq"], check=False
        )

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
        result = self._run_git(["show", "--name-only", "--format=", commit])

        return [f for f in result.stdout.strip().split("\n") if f]
