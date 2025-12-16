"""Tests for the git operations module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from memory.exceptions import StorageError
from memory.git_ops import GitOps, validate_git_ref, validate_path


class TestValidateGitRef:
    """Tests for validate_git_ref function (SEC-001)."""

    def test_valid_refs(self):
        """Test that valid refs pass validation."""
        valid_refs = [
            "HEAD",
            "main",
            "feature/new-feature",
            "v1.0.0",
            "abc123def456",
            "HEAD~1",
            "HEAD^2",
            "origin/main",
            "refs/heads/main",
            "my-branch",
            "my_branch",
            "branch.name",
            "feature@latest",
        ]
        for ref in valid_refs:
            validate_git_ref(ref)  # Should not raise

    def test_empty_ref_raises_error(self):
        """Test that empty ref raises StorageError."""
        with pytest.raises(StorageError) as exc_info:
            validate_git_ref("")
        assert "cannot be empty" in str(exc_info.value)

    def test_dash_prefix_raises_error(self):
        """Test that refs starting with dash are rejected (command injection)."""
        with pytest.raises(StorageError) as exc_info:
            validate_git_ref("-malicious")
        assert "cannot start with dash" in str(exc_info.value)

        with pytest.raises(StorageError) as exc_info:
            validate_git_ref("--exec=evil")
        assert "cannot start with dash" in str(exc_info.value)

    def test_illegal_characters_raise_error(self):
        """Test that refs with shell metacharacters are rejected."""
        dangerous_refs = [
            "ref;rm -rf",
            "ref$(whoami)",
            "ref`id`",
            "ref|cat",
            "ref>file",
            "ref<file",
            "ref&background",
            "ref\ninjection",
            "ref\x00null",
        ]
        for ref in dangerous_refs:
            with pytest.raises(StorageError) as exc_info:
                validate_git_ref(ref)
            assert "illegal characters" in str(exc_info.value).lower()


class TestValidatePath:
    """Tests for validate_path function (SEC-001)."""

    def test_valid_paths(self):
        """Test that valid paths pass validation."""
        valid_paths = [
            "README.md",
            "src/main.py",
            "docs/api/index.html",
            "file-with-dash.txt",
            "file_with_underscore.txt",
            "file.multiple.dots.txt",
            "path/with spaces/file.txt",
            "CamelCase/Path.py",
        ]
        for path in valid_paths:
            validate_path(path)  # Should not raise

    def test_empty_path_raises_error(self):
        """Test that empty path raises StorageError."""
        with pytest.raises(StorageError) as exc_info:
            validate_path("")
        assert "cannot be empty" in str(exc_info.value)

    def test_dash_prefix_raises_error(self):
        """Test that paths starting with dash are rejected."""
        with pytest.raises(StorageError) as exc_info:
            validate_path("-malicious")
        assert "cannot start with dash" in str(exc_info.value)

    def test_absolute_path_raises_error(self):
        """Test that absolute paths are rejected."""
        with pytest.raises(StorageError) as exc_info:
            validate_path("/etc/passwd")
        assert "absolute paths" in str(exc_info.value).lower()

    def test_null_byte_raises_error(self):
        """Test that paths with null bytes are rejected."""
        with pytest.raises(StorageError) as exc_info:
            validate_path("file\x00.txt")
        assert "null bytes" in str(exc_info.value).lower()

    def test_illegal_characters_raise_error(self):
        """Test that paths with shell metacharacters are rejected."""
        dangerous_paths = [
            "file;rm -rf",
            "file$(whoami)",
            "file`id`",
            "file|cat",
            "file>out",
            "file<in",
            "file&bg",
        ]
        for path in dangerous_paths:
            with pytest.raises(StorageError) as exc_info:
                validate_path(path)
            assert "illegal characters" in str(exc_info.value).lower()


class TestGitOpsInit:
    """Tests for GitOps initialization."""

    def test_init_with_path(self, tmp_path):
        """Test initialization with explicit path."""
        git_ops = GitOps(repo_path=tmp_path)
        assert git_ops.repo_path == tmp_path

    def test_init_with_string_path(self, tmp_path):
        """Test initialization with string path."""
        git_ops = GitOps(repo_path=str(tmp_path))
        assert git_ops.repo_path == tmp_path

    def test_init_without_path(self):
        """Test initialization defaults to cwd."""
        git_ops = GitOps()
        assert git_ops.repo_path == Path.cwd()


class TestRunGit:
    """Tests for _run_git method."""

    def test_successful_command(self):
        """Test successful git command execution."""
        git_ops = GitOps(repo_path="/tmp")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="output", stderr=""
            )
            result = git_ops._run_git(["status"])

            assert result.returncode == 0
            assert result.stdout == "output"
            mock_run.assert_called_once()

    def test_not_a_git_repository_error(self):
        """Test error handling for non-git directory."""
        git_ops = GitOps(repo_path="/tmp")

        with patch("subprocess.run") as mock_run:
            error = subprocess.CalledProcessError(
                128, ["git"], stderr="fatal: not a git repository"
            )
            mock_run.side_effect = error

            with pytest.raises(StorageError) as exc_info:
                git_ops._run_git(["status"])

            assert "Not in a Git repository" in str(exc_info.value)

    def test_permission_denied_error(self):
        """Test error handling for permission denied."""
        git_ops = GitOps(repo_path="/tmp")

        with patch("subprocess.run") as mock_run:
            error = subprocess.CalledProcessError(
                128, ["git"], stderr="fatal: permission denied"
            )
            mock_run.side_effect = error

            with pytest.raises(StorageError) as exc_info:
                git_ops._run_git(["status"])

            assert "Permission denied" in str(exc_info.value)

    def test_no_commits_error(self):
        """Test error handling for repository with no commits."""
        git_ops = GitOps(repo_path="/tmp")

        with patch("subprocess.run") as mock_run:
            error = subprocess.CalledProcessError(
                128, ["git"], stderr="does not have any commits yet"
            )
            mock_run.side_effect = error

            with pytest.raises(StorageError) as exc_info:
                git_ops._run_git(["status"])

            assert "Repository has no commits" in str(exc_info.value)

    def test_generic_git_error(self):
        """Test handling of generic git errors."""
        git_ops = GitOps(repo_path="/tmp")

        with patch("subprocess.run") as mock_run:
            error = subprocess.CalledProcessError(1, ["git"], stderr="some other error")
            mock_run.side_effect = error

            with pytest.raises(StorageError) as exc_info:
                git_ops._run_git(["status"])

            assert "Git command failed" in str(exc_info.value)


class TestNoteRef:
    """Tests for _note_ref method."""

    def test_generates_correct_ref(self):
        """Test that note ref is correctly formatted."""
        git_ops = GitOps()
        assert git_ops._note_ref("decisions") == "cs/decisions"
        assert git_ops._note_ref("learnings") == "cs/learnings"
        assert git_ops._note_ref("blockers") == "cs/blockers"


class TestAddNote:
    """Tests for add_note method."""

    def test_add_note_success(self):
        """Test successful note addition."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.add_note("decisions", "Test content", "HEAD")

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "notes" in args
            assert "--ref=cs/decisions" in args
            assert "add" in args

    def test_add_note_with_force(self):
        """Test note addition with force flag."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.add_note("decisions", "Test", force=True)

            args = mock_run.call_args[0][0]
            assert "-f" in args

    def test_add_note_invalid_namespace(self):
        """Test error for invalid namespace."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.add_note("invalid_namespace", "content")

        assert "Invalid namespace" in str(exc_info.value)

    def test_add_note_invalid_ref(self):
        """Test error for invalid ref (SEC-001)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.add_note("decisions", "content", "-malicious")

        assert "cannot start with dash" in str(exc_info.value)


class TestAppendNote:
    """Tests for append_note method."""

    def test_append_note_success(self):
        """Test successful note append."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.append_note("learnings", "New learning")

            args = mock_run.call_args[0][0]
            assert "append" in args
            assert "--ref=cs/learnings" in args

    def test_append_note_invalid_namespace(self):
        """Test error for invalid namespace."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.append_note("invalid", "content")

        assert "Invalid namespace" in str(exc_info.value)

    def test_append_note_invalid_ref(self):
        """Test error for invalid ref (SEC-001)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.append_note("learnings", "content", "$(whoami)")

        assert "illegal characters" in str(exc_info.value).lower()


class TestShowNote:
    """Tests for show_note method."""

    def test_show_existing_note(self):
        """Test showing an existing note."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Note content")
            result = git_ops.show_note("decisions", "abc123")

            assert result == "Note content"

    def test_show_nonexistent_note(self):
        """Test showing a note that doesn't exist."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = git_ops.show_note("decisions", "abc123")

            assert result is None

    def test_show_note_invalid_namespace(self):
        """Test error for invalid namespace."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.show_note("invalid", "abc123")

        assert "Invalid namespace" in str(exc_info.value)

    def test_show_note_invalid_ref(self):
        """Test error for invalid ref (SEC-001)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.show_note("decisions", ";rm -rf /")

        assert "illegal characters" in str(exc_info.value).lower()


class TestListNotes:
    """Tests for list_notes method."""

    def test_list_notes_with_results(self):
        """Test listing notes that exist."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="abc123 def456\nghi789 jkl012\n"
            )
            result = git_ops.list_notes("decisions")

            assert len(result) == 2
            assert result[0] == ("abc123", "def456")
            assert result[1] == ("ghi789", "jkl012")

    def test_list_notes_empty(self):
        """Test listing when no notes exist."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            result = git_ops.list_notes("decisions")

            assert result == []

    def test_list_notes_error(self):
        """Test listing when git returns error."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = git_ops.list_notes("decisions")

            assert result == []

    def test_list_notes_invalid_namespace(self):
        """Test error for invalid namespace."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.list_notes("invalid")

        assert "Invalid namespace" in str(exc_info.value)


class TestRemoveNote:
    """Tests for remove_note method."""

    def test_remove_existing_note(self):
        """Test removing an existing note."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = git_ops.remove_note("decisions", "abc123")

            assert result is True

    def test_remove_nonexistent_note(self):
        """Test removing a note that doesn't exist."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = git_ops.remove_note("decisions", "abc123")

            assert result is False

    def test_remove_note_invalid_namespace(self):
        """Test error for invalid namespace (SEC-003)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.remove_note("invalid_namespace", "abc123")

        assert "Invalid namespace" in str(exc_info.value)

    def test_remove_note_invalid_ref(self):
        """Test error for invalid ref (SEC-001)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.remove_note("decisions", "-malicious")

        assert "cannot start with dash" in str(exc_info.value)


class TestIsSyncConfigured:
    """Tests for is_sync_configured method."""

    def test_is_sync_configured_all_configured(self):
        """Test detection when all sync options are configured."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            # All checks return configured values
            mock_run.return_value = MagicMock(
                returncode=0, stdout="refs/notes/cs/*:refs/notes/cs/*\ncat_sort_uniq"
            )
            result = git_ops.is_sync_configured()

            assert result["push"] is True
            assert result["fetch"] is True
            assert result["rewrite"] is True
            assert result["merge"] is True

    def test_is_sync_configured_none_configured(self):
        """Test detection when no sync options are configured."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            # All checks return nothing
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = git_ops.is_sync_configured()

            assert result["push"] is False
            assert result["fetch"] is False
            assert result["rewrite"] is False
            assert result["merge"] is False


class TestConfigureSync:
    """Tests for configure_sync method."""

    def test_configure_sync_when_not_configured(self):
        """Test that configure_sync sets up all remote config."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            # First 4 calls: is_sync_configured checks (not configured)
            # Next 4 calls: configure operations
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            result = git_ops.configure_sync()

            # Should be called 8 times: 4 checks + 4 configs
            assert mock_run.call_count == 8

            # All should be configured
            assert result["push"] is True
            assert result["fetch"] is True
            assert result["rewrite"] is True
            assert result["merge"] is True

    def test_configure_sync_idempotent(self):
        """Test that configure_sync skips already-configured options."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            # All checks return already configured
            mock_run.return_value = MagicMock(
                returncode=0, stdout="refs/notes/cs/*:refs/notes/cs/*\ncat_sort_uniq"
            )
            result = git_ops.configure_sync()

            # Should only be called 4 times for checks, no config calls
            assert mock_run.call_count == 4

            # None newly configured (already existed)
            assert result["push"] is False
            assert result["fetch"] is False
            assert result["rewrite"] is False
            assert result["merge"] is False

    def test_configure_sync_force(self):
        """Test that configure_sync with force=True reconfigures."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            # All checks return already configured
            mock_run.return_value = MagicMock(
                returncode=0, stdout="refs/notes/cs/*:refs/notes/cs/*\ncat_sort_uniq"
            )
            result = git_ops.configure_sync(force=True)

            # Should be called 8 times: 4 checks + 4 forced configs
            assert mock_run.call_count == 8

            # All should be (re)configured
            assert result["push"] is True
            assert result["fetch"] is True
            assert result["rewrite"] is True
            assert result["merge"] is True


class TestGetCommitSha:
    """Tests for get_commit_sha method."""

    def test_get_commit_sha(self):
        """Test getting commit SHA."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="abc123def456789\n")
            result = git_ops.get_commit_sha("HEAD")

            assert result == "abc123def456789"

    def test_get_commit_sha_invalid_ref(self):
        """Test error for invalid ref (SEC-001)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.get_commit_sha("--exec=evil")

        assert "cannot start with dash" in str(exc_info.value)


class TestGetCommitInfo:
    """Tests for get_commit_info method."""

    def test_get_commit_info(self):
        """Test getting commit metadata."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc123\nJohn Doe\njohn@example.com\n2025-01-01\nInitial commit\n",
            )
            result = git_ops.get_commit_info("HEAD")

            assert result["sha"] == "abc123"
            assert result["author_name"] == "John Doe"
            assert result["author_email"] == "john@example.com"
            assert result["date"] == "2025-01-01"
            assert result["message"] == "Initial commit"

    def test_get_commit_info_incomplete(self):
        """Test handling of incomplete commit info."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
            result = git_ops.get_commit_info("HEAD")

            assert result == {}

    def test_get_commit_info_invalid_ref(self):
        """Test error for invalid ref (SEC-001)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.get_commit_info("`id`")

        assert "illegal characters" in str(exc_info.value).lower()


class TestGetFileAtCommit:
    """Tests for get_file_at_commit method."""

    def test_get_existing_file(self):
        """Test getting file content at commit."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="file content here")
            result = git_ops.get_file_at_commit("README.md", "HEAD")

            assert result == "file content here"

    def test_get_nonexistent_file(self):
        """Test getting file that doesn't exist."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = git_ops.get_file_at_commit("nonexistent.txt", "HEAD")

            assert result is None

    def test_get_file_invalid_path(self):
        """Test error for invalid path (SEC-001)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.get_file_at_commit("/etc/passwd", "HEAD")

        assert "absolute paths" in str(exc_info.value).lower()

    def test_get_file_invalid_ref(self):
        """Test error for invalid ref (SEC-001)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.get_file_at_commit("README.md", "-malicious")

        assert "cannot start with dash" in str(exc_info.value)


class TestGetChangedFiles:
    """Tests for get_changed_files method."""

    def test_get_changed_files(self):
        """Test getting list of changed files."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="file1.py\nfile2.py\nREADME.md\n"
            )
            result = git_ops.get_changed_files("HEAD")

            assert result == ["file1.py", "file2.py", "README.md"]

    def test_get_changed_files_empty(self):
        """Test getting empty list when no files changed."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="\n")
            result = git_ops.get_changed_files("HEAD")

            assert result == []

    def test_get_changed_files_invalid_ref(self):
        """Test error for invalid ref (SEC-001)."""
        git_ops = GitOps(repo_path="/tmp")

        with pytest.raises(StorageError) as exc_info:
            git_ops.get_changed_files("$(malicious)")

        assert "illegal characters" in str(exc_info.value).lower()
