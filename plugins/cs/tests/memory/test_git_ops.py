"""Tests for the git operations module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from memory.exceptions import StorageError
from memory.git_ops import GitOps


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


class TestConfigureSync:
    """Tests for configure_sync method."""

    def test_configure_sync(self):
        """Test that configure_sync sets up remote config."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.configure_sync()

            # Should be called 3 times: push, fetch, merge strategy
            assert mock_run.call_count == 3


class TestGetCommitSha:
    """Tests for get_commit_sha method."""

    def test_get_commit_sha(self):
        """Test getting commit SHA."""
        git_ops = GitOps(repo_path="/tmp")

        with patch.object(git_ops, "_run_git") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="abc123def456789\n")
            result = git_ops.get_commit_sha("HEAD")

            assert result == "abc123def456789"


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
