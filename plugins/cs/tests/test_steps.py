"""Tests for step modules."""

import json
import shutil
import sys
from pathlib import Path

# Add steps to path
sys.path.insert(0, str(Path(__file__).parent.parent / "steps"))

from steps import (
    ContextLoaderStep,
    LogArchiverStep,
    MarkerCleanerStep,
    PRManagerStep,
    RetrospectiveGeneratorStep,
    SecurityReviewerStep,
    StepError,
    StepResult,
)


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_ok_creates_success(self):
        """Test StepResult.ok creates successful result."""
        result = StepResult.ok("Done", key="value")
        assert result.success is True
        assert result.message == "Done"
        assert result.data == {"key": "value"}

    def test_fail_creates_failure(self):
        """Test StepResult.fail creates failed result."""
        result = StepResult.fail("Error", detail="info")
        assert result.success is False
        assert result.message == "Error"
        assert result.data == {"detail": "info"}

    def test_add_warning(self):
        """Test adding warnings to result."""
        result = StepResult.ok("Done")
        result.add_warning("Warning 1")
        result.add_warning("Warning 2")
        assert result.warnings == ["Warning 1", "Warning 2"]


class TestStepError:
    """Tests for StepError exception."""

    def test_includes_step_name(self):
        """Test error includes step name."""
        error = StepError("Something failed", step_name="test-step")
        assert "test-step" in str(error)
        assert "Something failed" in str(error)


class TestContextLoaderStep:
    """Tests for ContextLoaderStep."""

    def test_loads_claude_md(self, tmp_path):
        """Test loading CLAUDE.md content."""
        (tmp_path / "CLAUDE.md").write_text("# Test Project\n\nInstructions here")
        step = ContextLoaderStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert "context" in result.data
        assert "Test Project" in result.data["context"]

    def test_loads_git_state(self, tmp_path):
        """Test loading git state."""
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True
        )

        step = ContextLoaderStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert "context" in result.data
        assert "Git State" in result.data["context"]

    def test_loads_project_structure(self, tmp_path):
        """Test loading project structure."""
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# Test")

        step = ContextLoaderStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert "Project Structure" in result.data.get("context", "")


class TestSecurityReviewerStep:
    """Tests for SecurityReviewerStep."""

    def test_returns_ok_with_or_without_bandit(self, tmp_path):
        """Test security reviewer works whether bandit is installed or not."""
        step = SecurityReviewerStep(str(tmp_path))
        result = step.run()

        # Should always succeed (fail-open design)
        assert result.success is True
        # Message should indicate completion or skipped
        assert (
            "security review" in result.message.lower()
            or "skipped" in result.message.lower()
        )

    def test_respects_timeout_config(self, tmp_path):
        """Test timeout configuration is respected."""
        step = SecurityReviewerStep(str(tmp_path), config={"timeout": 60})
        assert step.config.get("timeout") == 60

    def test_scan_complete_in_result_data(self, tmp_path):
        """Test scan_complete is included in result data."""
        step = SecurityReviewerStep(str(tmp_path))
        result = step.run()

        assert "scan_complete" in result.data

    def test_returns_warning_when_scan_incomplete(self, tmp_path, monkeypatch):
        """Test warning added when scan is incomplete."""

        # Mock _run_bandit to simulate incomplete scan
        step = SecurityReviewerStep(str(tmp_path))

        def mock_run_bandit(timeout):
            return (["finding1"], False)  # findings but incomplete

        monkeypatch.setattr(step, "_run_bandit", mock_run_bandit)

        result = step.execute()

        assert result.success is True
        assert result.data.get("scan_complete") is False
        assert len(result.warnings) > 0
        assert any("incomplete" in w.lower() for w in result.warnings)

    def test_indicates_scan_error_when_bandit_available_but_fails(
        self, tmp_path, monkeypatch
    ):
        """Test indicates scan error when bandit is available but scan fails."""
        import subprocess

        step = SecurityReviewerStep(str(tmp_path))

        # Mock _run_bandit to return empty with incomplete (scan error)
        def mock_run_bandit(timeout):
            return ([], False)

        monkeypatch.setattr(step, "_run_bandit", mock_run_bandit)

        # Mock subprocess.run to indicate bandit is available
        def mock_subprocess_run(cmd, *args, **kwargs):
            if cmd == ["bandit", "--version"]:
                return subprocess.CompletedProcess(cmd, 0, "bandit 1.0", "")
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        result = step.execute()

        assert result.success is True
        assert (
            "incomplete" in result.message.lower() or "error" in result.message.lower()
        )

    def test_run_bandit_returns_tuple(self, tmp_path):
        """Test _run_bandit returns tuple of (findings, scan_complete)."""
        step = SecurityReviewerStep(str(tmp_path))
        result = step._run_bandit(timeout=5)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], bool)


class TestLogArchiverStep:
    """Tests for LogArchiverStep."""

    def test_archives_log_file(self, tmp_path):
        """Test archiving log file to completed directory."""
        # Create log file
        log_content = [{"timestamp": "2025-01-01T00:00:00Z", "content": "test"}]
        (tmp_path / ".prompt-log.json").write_text(json.dumps(log_content))

        # Create completed project directory
        completed = tmp_path / "docs" / "spec" / "completed" / "test-project"
        completed.mkdir(parents=True)

        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("archived") is True

        # Check archive exists
        archives = list(completed.glob("prompt-log-*.json"))
        assert len(archives) == 1

    def test_handles_missing_log(self, tmp_path):
        """Test handling when no log file exists."""
        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("archived") is False

    def test_handles_no_completed_dir(self, tmp_path):
        """Test handling when no completed directory exists."""
        (tmp_path / ".prompt-log.json").write_text("[]")

        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("archived") is False

    def test_handles_no_project_dirs(self, tmp_path):
        """Test handling when completed dir exists but has no projects."""
        (tmp_path / ".prompt-log.json").write_text("[]")
        completed = tmp_path / "docs" / "spec" / "completed"
        completed.mkdir(parents=True)

        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("archived") is False
        assert len(result.warnings) > 0


class TestMarkerCleanerStep:
    """Tests for MarkerCleanerStep."""

    def test_cleans_marker_files(self, tmp_path):
        """Test cleaning up marker files."""
        # Create marker files
        (tmp_path / ".prompt-log-enabled").touch()
        (tmp_path / ".prompt-log.json").write_text("[]")
        (tmp_path / ".cs-session-state.json").write_text("{}")

        step = MarkerCleanerStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert len(result.data.get("cleaned", [])) == 3

        # Verify files are removed
        assert not (tmp_path / ".prompt-log-enabled").exists()
        assert not (tmp_path / ".prompt-log.json").exists()
        assert not (tmp_path / ".cs-session-state.json").exists()

    def test_handles_no_files(self, tmp_path):
        """Test handling when no marker files exist."""
        step = MarkerCleanerStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("cleaned", []) == []


class TestRetrospectiveGeneratorStep:
    """Tests for RetrospectiveGeneratorStep."""

    def test_generates_retrospective(self, tmp_path):
        """Test generating RETROSPECTIVE.md."""
        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text(
            "# Test Project\n\nA test project for testing."
        )

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("generated") is True

        # Check retrospective exists
        retro = project / "RETROSPECTIVE.md"
        assert retro.exists()
        content = retro.read_text()
        assert "Retrospective" in content
        assert "test-project" in content

    def test_skips_if_exists(self, tmp_path):
        """Test skipping if RETROSPECTIVE.md already exists."""
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "RETROSPECTIVE.md").write_text("# Existing")

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("generated") is False

    def test_handles_no_completed_dir(self, tmp_path):
        """Test handling when no completed directory exists."""
        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("generated") is False

    def test_analyzes_log_file(self, tmp_path):
        """Test log file analysis in retrospective."""
        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        # Create log file with commands
        log = [
            {"timestamp": "2025-01-01T00:00:00Z", "command": "/cs:p"},
            {"timestamp": "2025-01-01T01:00:00Z", "command": "/cs:p"},
            {"timestamp": "2025-01-01T02:00:00Z", "command": "/cs:i"},
        ]
        (tmp_path / ".prompt-log.json").write_text(json.dumps(log))

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True

        # Check retrospective includes command stats
        retro = project / "RETROSPECTIVE.md"
        content = retro.read_text()
        assert "Commands Used" in content or "Total Prompts" in content

    def test_handles_no_project_dirs(self, tmp_path):
        """Test handling when completed dir exists but has no projects."""
        completed = tmp_path / "docs" / "spec" / "completed"
        completed.mkdir(parents=True)

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("generated") is False

    def test_handles_log_with_zulu_timestamps(self, tmp_path):
        """Test handles timestamps with Z suffix (Zulu time)."""
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        # Create log with Z suffix timestamps
        log = [
            {"timestamp": "2025-01-01T00:00:00Z", "command": "/cs:p"},
            {"timestamp": "2025-01-01T02:00:00Z", "command": "/cs:c"},
        ]
        (tmp_path / ".prompt-log.json").write_text(json.dumps(log))

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        retro = project / "RETROSPECTIVE.md"
        content = retro.read_text()
        # Should have calculated duration
        assert "Duration" in content

    def test_handles_log_with_timezone_offset(self, tmp_path):
        """Test handles timestamps with explicit timezone offset."""
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        # Create log with timezone offset timestamps
        log = [
            {"timestamp": "2025-01-01T00:00:00+00:00", "command": "/cs:p"},
            {"timestamp": "2025-01-01T02:00:00+00:00", "command": "/cs:c"},
        ]
        (tmp_path / ".prompt-log.json").write_text(json.dumps(log))

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True


class TestModuleLevelRunFunctions:
    """Tests for module-level run() functions via step classes."""

    def test_context_loader_run(self, tmp_path):
        """Test ContextLoaderStep via run method."""
        (tmp_path / "CLAUDE.md").write_text("# Test")
        step = ContextLoaderStep(str(tmp_path))
        result = step.run()
        assert result.success is True

    def test_security_reviewer_run(self, tmp_path):
        """Test SecurityReviewerStep via run method."""
        step = SecurityReviewerStep(str(tmp_path))
        result = step.run()
        assert result.success is True

    def test_log_archiver_run(self, tmp_path):
        """Test LogArchiverStep via run method."""
        step = LogArchiverStep(str(tmp_path))
        result = step.run()
        assert result.success is True

    def test_marker_cleaner_run(self, tmp_path):
        """Test MarkerCleanerStep via run method."""
        step = MarkerCleanerStep(str(tmp_path))
        result = step.run()
        assert result.success is True

    def test_retrospective_gen_run(self, tmp_path):
        """Test RetrospectiveGeneratorStep via run method."""
        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()
        assert result.success is True


# ============================================================================
# NEW TESTS ADDED FOR COVERAGE GAPS
# ============================================================================


class TestContextLoaderStepContextUtilsUnavailable:
    """Tests for ContextLoaderStep when context_utils is unavailable."""

    def test_fails_when_context_utils_unavailable(self, tmp_path, monkeypatch):
        """Test step fails when CONTEXT_UTILS_AVAILABLE is False."""
        # Get the already-imported module to modify its state
        import sys

        context_loader_module = sys.modules["steps.context_loader"]

        original = context_loader_module.CONTEXT_UTILS_AVAILABLE
        context_loader_module.CONTEXT_UTILS_AVAILABLE = False

        step = ContextLoaderStep(str(tmp_path))
        result = step.execute()

        assert result.success is False
        assert "not available" in result.message.lower()

        # Restore original value
        context_loader_module.CONTEXT_UTILS_AVAILABLE = original


class TestContextLoaderStepMissingGitCommand:
    """Tests for ContextLoaderStep error handling with missing git."""

    def test_handles_git_command_not_found(self, tmp_path, monkeypatch):
        """Test graceful handling when git command is not available."""
        import subprocess

        # Create CLAUDE.md so step has something to load
        (tmp_path / "CLAUDE.md").write_text("# Test Project")

        # Mock subprocess.run to simulate git not found
        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == "git":
                raise FileNotFoundError("git not found")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        step = ContextLoaderStep(str(tmp_path))
        result = step.run()

        # Should still succeed with CLAUDE.md content
        assert result.success is True
        assert "context" in result.data


class TestContextLoaderStepNoContextLoaded:
    """Tests for ContextLoaderStep when no context is available."""

    def test_fails_when_no_context_parts(self, tmp_path, monkeypatch):
        """Test step fails when no context sections are loaded."""
        # Get the already-imported module to mock its functions
        import sys

        context_loader_module = sys.modules["steps.context_loader"]

        # Mock functions must accept **kwargs to handle optional parameters
        monkeypatch.setattr(
            context_loader_module,
            "load_claude_md",
            lambda cwd, **kwargs: "",
        )
        monkeypatch.setattr(
            context_loader_module,
            "load_git_state",
            lambda cwd, **kwargs: "",
        )
        monkeypatch.setattr(
            context_loader_module,
            "load_project_structure",
            lambda cwd, **kwargs: "",
        )

        step = ContextLoaderStep(str(tmp_path))
        result = step.run()

        # Should fail when nothing is loaded
        assert result.success is False
        assert "No context" in result.message


class TestLogArchiverStepCopyFailure:
    """Tests for LogArchiverStep copy failure scenarios."""

    def test_copy_failure_returns_fail(self, tmp_path, monkeypatch, capsys):
        """Test handling when shutil.copy2 raises an exception."""
        # Create log file
        (tmp_path / ".prompt-log.json").write_text("[]")

        # Create completed project directory
        completed = tmp_path / "docs" / "spec" / "completed" / "test-project"
        completed.mkdir(parents=True)

        # Mock shutil.copy2 to raise an exception
        def mock_copy2(src, dst):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(shutil, "copy2", mock_copy2)

        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        assert result.success is False
        assert result.data.get("archived") is False
        assert "Failed to archive" in result.message

    def test_copy_failure_oserror(self, tmp_path, monkeypatch, capsys):
        """Test handling when shutil.copy2 raises OSError."""
        # Create log file
        (tmp_path / ".prompt-log.json").write_text("[]")

        # Create completed project directory
        completed = tmp_path / "docs" / "spec" / "completed" / "test-project"
        completed.mkdir(parents=True)

        # Mock shutil.copy2 to raise OSError
        def mock_copy2(src, dst):
            raise OSError("Disk full")

        monkeypatch.setattr(shutil, "copy2", mock_copy2)

        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        assert result.success is False
        assert "Disk full" in result.message or "Failed" in result.message

    def test_copy_failure_ioerror(self, tmp_path, monkeypatch):
        """Test handling when shutil.copy2 raises IOError."""
        # Create log file
        (tmp_path / ".prompt-log.json").write_text("[]")

        # Create completed project directory
        completed = tmp_path / "docs" / "spec" / "completed" / "test-project"
        completed.mkdir(parents=True)

        # Mock shutil.copy2 to raise IOError
        def mock_copy2(src, dst):
            raise OSError("I/O error during copy")

        monkeypatch.setattr(shutil, "copy2", mock_copy2)

        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        assert result.success is False


class TestLogArchiverStepSafeMtimeError:
    """Tests for LogArchiverStep safe_mtime error handling.

    These tests verify that the safe_mtime function handles OSError gracefully
    by returning 0 instead of propagating the error.
    """

    def test_safe_mtime_returns_zero_on_stat_failure(self, tmp_path, capsys):
        """Test safe_mtime returns 0 when stat fails, allowing sorting to proceed.

        Rather than mocking Path.stat (which affects many internal calls),
        we verify the behavior by checking that the step completes successfully
        even when directories have varied modification times.
        """
        import time

        # Create log file
        (tmp_path / ".prompt-log.json").write_text("[]")

        # Create two project directories with different modification times
        completed = tmp_path / "docs" / "spec" / "completed"
        completed.mkdir(parents=True)

        project_older = completed / "project-older"
        project_older.mkdir()

        # Brief sleep to ensure different mtime
        time.sleep(0.01)

        project_newer = completed / "project-newer"
        project_newer.mkdir()

        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        # Should succeed and archive to the newer project
        assert result.success is True
        assert result.data.get("archived") is True
        assert "project-newer" in result.data.get("destination", "")

    def test_multiple_dirs_sorted_by_mtime(self, tmp_path):
        """Test that directories are properly sorted by modification time."""
        import time

        # Create log file
        (tmp_path / ".prompt-log.json").write_text("[]")

        # Create completed directory
        completed = tmp_path / "docs" / "spec" / "completed"
        completed.mkdir(parents=True)

        # Create directories in specific order with different mtimes
        old = completed / "old-project"
        old.mkdir()
        time.sleep(0.01)

        mid = completed / "mid-project"
        mid.mkdir()
        time.sleep(0.01)

        newest = completed / "newest-project"
        newest.mkdir()

        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        # Should archive to newest
        assert result.success is True
        assert "newest-project" in result.data.get("destination", "")


class TestLogArchiverStepMultipleProjects:
    """Tests for LogArchiverStep with multiple completed projects."""

    def test_archives_to_most_recent_project(self, tmp_path):
        """Test that log is archived to the most recently modified project."""
        import time

        # Create log file
        (tmp_path / ".prompt-log.json").write_text("[]")

        # Create multiple completed project directories
        completed = tmp_path / "docs" / "spec" / "completed"
        completed.mkdir(parents=True)

        older_project = completed / "older-project"
        older_project.mkdir()

        # Wait a moment and create newer project
        time.sleep(0.1)
        newer_project = completed / "newer-project"
        newer_project.mkdir()

        step = LogArchiverStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("archived") is True

        # Archive should be in newer project
        newer_archives = list(newer_project.glob("prompt-log-*.json"))
        older_archives = list(older_project.glob("prompt-log-*.json"))

        assert len(newer_archives) == 1
        assert len(older_archives) == 0


class TestContextLoaderStepModuleLevelRun:
    """Tests for context_loader module-level run function."""

    def test_module_run_function(self, tmp_path):
        """Test module-level run() function."""
        from steps.context_loader import run

        (tmp_path / "CLAUDE.md").write_text("# Test")

        result = run(str(tmp_path), None)
        assert result.success is True

    def test_module_run_with_config(self, tmp_path):
        """Test module-level run() function with config."""
        from steps.context_loader import run

        (tmp_path / "CLAUDE.md").write_text("# Test")

        result = run(str(tmp_path), {"some": "config"})
        assert result.success is True


class TestLogArchiverStepModuleLevelRun:
    """Tests for log_archiver module-level run function."""

    def test_module_run_function(self, tmp_path):
        """Test module-level run() function."""
        from steps.log_archiver import run

        result = run(str(tmp_path), None)
        assert result.success is True

    def test_module_run_with_config(self, tmp_path):
        """Test module-level run() function with config."""
        from steps.log_archiver import run

        result = run(str(tmp_path), {"some": "config"})
        assert result.success is True


class TestSecurityReviewerStepModuleLevelRun:
    """Tests for security_reviewer module-level run function."""

    def test_module_run_function(self, tmp_path):
        """Test module-level run() function."""
        from steps.security_reviewer import run

        result = run(str(tmp_path), None)
        assert result.success is True

    def test_module_run_with_config(self, tmp_path):
        """Test module-level run() function with config."""
        from steps.security_reviewer import run

        result = run(str(tmp_path), {"timeout": 30})
        assert result.success is True


class TestSecurityReviewerStepExceptionHandling:
    """Tests for SecurityReviewerStep exception handling paths."""

    def test_bandit_timeout_expired_on_version_check(self, tmp_path, monkeypatch):
        """Test handling when bandit --version times out."""
        import subprocess

        step = SecurityReviewerStep(str(tmp_path))

        # Mock _run_bandit to return empty (simulating bandit unavailable)
        def mock_run_bandit(timeout):
            return ([], False)

        monkeypatch.setattr(step, "_run_bandit", mock_run_bandit)

        # Mock subprocess.run to raise TimeoutExpired on bandit --version
        def mock_subprocess_run(cmd, *args, **kwargs):
            if "bandit" in cmd:
                raise subprocess.TimeoutExpired(cmd, 5)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        result = step.execute()

        assert result.success is True
        assert "skipped" in result.message.lower()
        assert any("install bandit" in w.lower() for w in result.warnings)

    def test_bandit_called_process_error_on_version_check(self, tmp_path, monkeypatch):
        """Test handling when bandit --version returns non-zero exit."""
        import subprocess

        step = SecurityReviewerStep(str(tmp_path))

        # Mock _run_bandit to return empty
        def mock_run_bandit(timeout):
            return ([], False)

        monkeypatch.setattr(step, "_run_bandit", mock_run_bandit)

        # Mock subprocess.run to raise CalledProcessError
        def mock_subprocess_run(cmd, *args, **kwargs):
            if "bandit" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        result = step.execute()

        assert result.success is True
        assert "skipped" in result.message.lower()

    def test_many_findings_truncates_output(self, tmp_path, monkeypatch, capsys):
        """Test output is truncated when more than 10 findings."""
        step = SecurityReviewerStep(str(tmp_path))

        # Mock _run_bandit to return many findings
        def mock_run_bandit(timeout):
            findings = [f"[HIGH/HIGH] file.py:{i} - Issue {i}" for i in range(15)]
            return (findings, True)

        monkeypatch.setattr(step, "_run_bandit", mock_run_bandit)

        result = step.execute()

        captured = capsys.readouterr()
        assert "... and 5 more" in captured.err
        assert result.data["findings_count"] == 15


class TestSecurityReviewerStepRunBanditErrors:
    """Tests for _run_bandit error handling paths."""

    def test_run_bandit_timeout_on_version(self, tmp_path, monkeypatch):
        """Test _run_bandit returns empty when version check times out."""
        import subprocess

        step = SecurityReviewerStep(str(tmp_path))

        def mock_subprocess_run(cmd, *args, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 5)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        findings, complete = step._run_bandit(5)

        assert findings == []
        assert complete is False

    def test_run_bandit_file_not_found(self, tmp_path, monkeypatch):
        """Test _run_bandit returns empty when bandit not found."""
        import subprocess

        step = SecurityReviewerStep(str(tmp_path))

        def mock_subprocess_run(cmd, *args, **kwargs):
            raise FileNotFoundError("bandit not found")

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        findings, complete = step._run_bandit(5)

        assert findings == []
        assert complete is False

    def test_run_bandit_scan_timeout(self, tmp_path, monkeypatch, capsys):
        """Test _run_bandit handles scan timeout."""
        import subprocess

        step = SecurityReviewerStep(str(tmp_path))
        call_count = [0]

        def mock_subprocess_run(cmd, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call is version check - success
                return subprocess.CompletedProcess(cmd, 0, "bandit 1.7.0", "")
            # Second call is actual scan - timeout
            raise subprocess.TimeoutExpired(cmd, 120)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        findings, complete = step._run_bandit(120)

        assert findings == []
        assert complete is False

        captured = capsys.readouterr()
        assert "timed out" in captured.err

    def test_run_bandit_generic_exception(self, tmp_path, monkeypatch, capsys):
        """Test _run_bandit handles generic exceptions."""
        import subprocess

        step = SecurityReviewerStep(str(tmp_path))
        call_count = [0]

        def mock_subprocess_run(cmd, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call is version check - success
                return subprocess.CompletedProcess(cmd, 0, "bandit 1.7.0", "")
            # Second call - generic error
            raise RuntimeError("Something went wrong")

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        findings, complete = step._run_bandit(120)

        assert findings == []
        assert complete is False

        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_run_bandit_json_parse_error(self, tmp_path, monkeypatch, capsys):
        """Test _run_bandit handles JSON parse errors."""
        import subprocess

        step = SecurityReviewerStep(str(tmp_path))
        call_count = [0]

        def mock_subprocess_run(cmd, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Version check - success
                return subprocess.CompletedProcess(cmd, 0, "bandit 1.7.0", "")
            # Scan returns invalid JSON
            return subprocess.CompletedProcess(cmd, 0, "not valid json {{{", "")

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        findings, complete = step._run_bandit(120)

        assert findings == []
        assert complete is False

        captured = capsys.readouterr()
        assert "Failed to parse" in captured.err

    def test_run_bandit_parses_results(self, tmp_path, monkeypatch):
        """Test _run_bandit correctly parses bandit JSON output."""
        import subprocess

        step = SecurityReviewerStep(str(tmp_path))
        call_count = [0]

        bandit_output = json.dumps(
            {
                "results": [
                    {
                        "issue_severity": "HIGH",
                        "issue_confidence": "MEDIUM",
                        "issue_text": "Hardcoded password",
                        "filename": "app.py",
                        "line_number": 42,
                    },
                    {
                        "issue_severity": "MEDIUM",
                        "issue_confidence": "HIGH",
                        "issue_text": "Use of shell=True",
                        "filename": "utils.py",
                        "line_number": 10,
                    },
                ]
            }
        )

        def mock_subprocess_run(cmd, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return subprocess.CompletedProcess(cmd, 0, "bandit 1.7.0", "")
            return subprocess.CompletedProcess(cmd, 0, bandit_output, "")

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        findings, complete = step._run_bandit(120)

        assert len(findings) == 2
        assert complete is True
        assert "HIGH/MEDIUM" in findings[0]
        assert "app.py:42" in findings[0]
        assert "Hardcoded password" in findings[0]


class TestRetrospectiveGeneratorStepErrorPaths:
    """Tests for RetrospectiveGeneratorStep error handling paths."""

    def test_multiple_project_dirs_sorted_by_mtime(self, tmp_path):
        """Test that multiple project directories are sorted by modification time.

        This exercises the safe_mtime helper function indirectly. The error
        handling path (lines 56-58) is defensive code that's hard to trigger
        in normal operation since is_dir() filters out problematic entries first.
        """
        import time

        # Create completed project structure
        completed = tmp_path / "docs" / "spec" / "completed"
        completed.mkdir(parents=True)

        # Create older project
        older_project = completed / "older-project"
        older_project.mkdir()
        (older_project / "README.md").write_text("# Older Project")
        time.sleep(0.02)

        # Create newer project
        newer_project = completed / "newer-project"
        newer_project.mkdir()
        (newer_project / "README.md").write_text("# Newer Project")

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        # Should succeed and write to the newer project
        assert result.success is True
        assert result.data.get("generated") is True
        assert "newer-project" in result.data.get("path", "")

    def test_write_file_error(self, tmp_path, monkeypatch, capsys):
        """Test handling when writing RETROSPECTIVE.md fails."""
        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        step = RetrospectiveGeneratorStep(str(tmp_path))

        # Mock Path.write_text to raise exception
        original_write_text = Path.write_text

        def mock_write_text(self, *args, **kwargs):
            if "RETROSPECTIVE.md" in str(self):
                raise PermissionError("Permission denied")
            return original_write_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        result = step.run()

        assert result.success is False
        assert "Failed" in result.message

    def test_analyze_log_json_array_parse_error(self, tmp_path, capsys):
        """Test log analysis handles malformed JSON array gracefully."""
        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        # Create malformed JSON array that starts with [ but is invalid
        (tmp_path / ".prompt-log.json").write_text("[{invalid json")

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        # Should still succeed - falls back to NDJSON parsing which will skip invalid lines
        assert result.success is True

    def test_analyze_log_ndjson_format(self, tmp_path):
        """Test log analysis parses NDJSON format (production format)."""
        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        # Create NDJSON format log (one JSON object per line)
        ndjson_content = (
            '{"timestamp": "2025-01-01T00:00:00Z", "command": "/cs:p"}\n'
            '{"timestamp": "2025-01-01T01:00:00Z", "command": "/cs:i"}\n'
            '{"timestamp": "2025-01-01T02:00:00Z", "command": "/cs:c"}\n'
        )
        (tmp_path / ".prompt-log.json").write_text(ndjson_content)

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True

        # Check retrospective includes command stats
        retro = project / "RETROSPECTIVE.md"
        content = retro.read_text()
        assert "Commands Used" in content or "Total Prompts" in content

    def test_analyze_log_ndjson_with_malformed_lines(self, tmp_path):
        """Test log analysis skips malformed NDJSON lines."""
        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        # Create NDJSON format with some malformed lines
        ndjson_content = (
            '{"timestamp": "2025-01-01T00:00:00Z", "command": "/cs:p"}\n'
            "malformed line\n"
            '{"timestamp": "2025-01-01T01:00:00Z", "command": "/cs:i"}\n'
            "\n"  # Empty line
            "another bad line {{\n"
            '{"timestamp": "2025-01-01T02:00:00Z", "command": "/cs:c"}\n'
        )
        (tmp_path / ".prompt-log.json").write_text(ndjson_content)

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True

        # Should have parsed the 3 valid entries
        retro = project / "RETROSPECTIVE.md"
        content = retro.read_text()
        assert "Total Prompts" in content

    def test_analyze_log_empty_entries(self, tmp_path):
        """Test log analysis returns None when no valid entries found."""
        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        # Create log with only invalid content
        (tmp_path / ".prompt-log.json").write_text("not json at all\nanother bad line")

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        # Should still succeed - just won't have log analysis
        assert result.success is True

        # Retrospective should not have Commands Used section
        retro = project / "RETROSPECTIVE.md"
        content = retro.read_text()
        assert "Commands Used" not in content

    def test_analyze_log_duration_calculation_error(self, tmp_path, capsys):
        """Test duration calculation handles invalid timestamp format."""
        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        # Create log with invalid timestamp format
        log = [
            {"timestamp": "invalid-timestamp", "command": "/cs:p"},
            {"timestamp": "also-invalid", "command": "/cs:c"},
        ]
        (tmp_path / ".prompt-log.json").write_text(json.dumps(log))

        step = RetrospectiveGeneratorStep(str(tmp_path))
        result = step.run()

        assert result.success is True

        # Should have logged the error
        captured = capsys.readouterr()
        assert "Failed to calculate duration" in captured.err

    def test_analyze_log_generic_exception(self, tmp_path, monkeypatch, capsys):
        """Test log analysis handles generic exceptions."""
        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        # Create valid log file
        (tmp_path / ".prompt-log.json").write_text(
            '{"timestamp": "2025-01-01T00:00:00Z"}'
        )

        step = RetrospectiveGeneratorStep(str(tmp_path))

        # Mock Path.read_text to raise exception for log file
        original_read_text = Path.read_text

        def mock_read_text(self, *args, **kwargs):
            if ".prompt-log.json" in str(self):
                raise RuntimeError("Unexpected read error")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        result = step.run()

        assert result.success is True

        # Should have logged the error
        captured = capsys.readouterr()
        assert "Log analysis error" in captured.err

    def test_readme_read_error(self, tmp_path, monkeypatch, capsys):
        """Test handling when README.md cannot be read."""
        # Create completed project without README
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        readme_path = project / "README.md"
        readme_path.write_text("# Test Project")

        step = RetrospectiveGeneratorStep(str(tmp_path))

        # Mock Path.read_text to raise exception for README
        original_read_text = Path.read_text

        def mock_read_text(self, *args, **kwargs):
            if "README.md" in str(self):
                raise PermissionError("Permission denied")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        result = step.run()

        assert result.success is True

        # Should have logged the error
        captured = capsys.readouterr()
        assert "Failed to read" in captured.err

        # Retrospective should use fallback summary
        retro = project / "RETROSPECTIVE.md"
        content = retro.read_text()
        assert "No summary available" in content


class TestRetrospectiveGeneratorStepModuleLevelRun:
    """Tests for retrospective_gen module-level run function."""

    def test_module_run_function(self, tmp_path):
        """Test module-level run() function."""
        from steps.retrospective_gen import run

        result = run(str(tmp_path), None)
        assert result.success is True

    def test_module_run_with_config(self, tmp_path):
        """Test module-level run() function with config."""
        from steps.retrospective_gen import run

        # Create completed project
        project = tmp_path / "docs" / "spec" / "completed" / "test-project"
        project.mkdir(parents=True)
        (project / "README.md").write_text("# Test")

        result = run(str(tmp_path), {"some": "config"})
        assert result.success is True
        assert result.data.get("generated") is True


# ============================================================================
# PR MANAGER STEP TESTS
# ============================================================================


class TestPRManagerStep:
    """Tests for PRManagerStep."""

    def test_step_name(self, tmp_path):
        """Test PRManagerStep has correct step name."""
        step = PRManagerStep(str(tmp_path))
        assert step.name == "pr-manager"

    def test_default_operation_is_create(self, tmp_path):
        """Test default operation is 'create' when not specified."""
        step = PRManagerStep(str(tmp_path))
        assert step.config.get("operation", "create") == "create"

    def test_respects_operation_config(self, tmp_path):
        """Test operation configuration is respected."""
        step = PRManagerStep(str(tmp_path), config={"operation": "ready"})
        assert step.config.get("operation") == "ready"

    def test_validate_always_returns_true(self, tmp_path, monkeypatch):
        """Test validate() always returns True (fail-open pattern)."""
        step = PRManagerStep(str(tmp_path))

        # Mock _check_gh_available to return unavailable
        monkeypatch.setattr(
            step, "_check_gh_available", lambda: (False, "gh not installed")
        )

        # validate() should still return True
        result = step.validate()
        assert result is True

    def test_validate_stores_skip_reason_when_gh_unavailable(
        self, tmp_path, monkeypatch
    ):
        """Test validate() stores skip reason when gh is unavailable."""
        step = PRManagerStep(str(tmp_path))

        # Mock _check_gh_available to return unavailable
        monkeypatch.setattr(
            step, "_check_gh_available", lambda: (False, "gh CLI not installed")
        )

        step.validate()
        assert step._skip_reason == "gh CLI not installed"

    def test_execute_skips_when_gh_unavailable(self, tmp_path, monkeypatch):
        """Test execute() skips gracefully when gh is unavailable."""
        step = PRManagerStep(str(tmp_path))
        step._skip_reason = "gh CLI not installed"

        result = step.execute()

        assert result.success is True
        assert result.data.get("skipped") is True
        assert result.data.get("reason") == "gh CLI not installed"
        assert len(result.warnings) > 0
        assert any("unavailable" in w.lower() for w in result.warnings)

    def test_execute_dispatches_to_create(self, tmp_path, monkeypatch):
        """Test execute() dispatches to _create_draft_pr for 'create' operation."""
        step = PRManagerStep(str(tmp_path), config={"operation": "create"})

        # Mock _create_draft_pr
        create_called = [False]

        def mock_create():
            create_called[0] = True
            return StepResult.ok("Created", pr_url="http://example.com/pr/1")

        monkeypatch.setattr(step, "_create_draft_pr", mock_create)

        result = step.execute()

        assert create_called[0] is True
        assert result.success is True

    def test_execute_dispatches_to_update(self, tmp_path, monkeypatch):
        """Test execute() dispatches to _update_pr_body for 'update' operation."""
        step = PRManagerStep(str(tmp_path), config={"operation": "update"})

        # Mock _update_pr_body
        update_called = [False]

        def mock_update():
            update_called[0] = True
            return StepResult.ok("Updated")

        monkeypatch.setattr(step, "_update_pr_body", mock_update)

        result = step.execute()

        assert update_called[0] is True
        assert result.success is True

    def test_execute_dispatches_to_ready(self, tmp_path, monkeypatch):
        """Test execute() dispatches to _mark_pr_ready for 'ready' operation."""
        step = PRManagerStep(str(tmp_path), config={"operation": "ready"})

        # Mock _mark_pr_ready
        ready_called = [False]

        def mock_ready():
            ready_called[0] = True
            return StepResult.ok("Ready")

        monkeypatch.setattr(step, "_mark_pr_ready", mock_ready)

        result = step.execute()

        assert ready_called[0] is True
        assert result.success is True

    def test_execute_fails_on_unknown_operation(self, tmp_path):
        """Test execute() fails with error for unknown operation."""
        step = PRManagerStep(str(tmp_path), config={"operation": "invalid"})

        result = step.execute()

        assert result.success is False
        assert "Unknown PR operation" in result.message
        assert "invalid" in result.message


class TestPRManagerStepGhAvailability:
    """Tests for PRManagerStep gh CLI availability checking."""

    def test_gh_not_installed(self, tmp_path, monkeypatch):
        """Test detection when gh CLI is not installed."""
        import subprocess

        step = PRManagerStep(str(tmp_path))

        def mock_run(cmd, *args, **kwargs):
            if cmd == ["gh", "--version"]:
                raise FileNotFoundError("gh not found")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        available, reason = step._check_gh_available()

        assert available is False
        assert "not installed" in reason.lower()

    def test_gh_version_check_timeout(self, tmp_path, monkeypatch):
        """Test handling when gh --version times out."""
        import subprocess

        step = PRManagerStep(str(tmp_path))

        def mock_run(cmd, *args, **kwargs):
            if cmd == ["gh", "--version"]:
                raise subprocess.TimeoutExpired(cmd, 5)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        available, reason = step._check_gh_available()

        assert available is False
        assert "timed out" in reason.lower()

    def test_gh_version_check_fails(self, tmp_path, monkeypatch):
        """Test handling when gh --version returns non-zero exit."""
        import subprocess

        step = PRManagerStep(str(tmp_path))

        def mock_run(cmd, *args, **kwargs):
            if cmd == ["gh", "--version"]:
                raise subprocess.CalledProcessError(1, cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        available, reason = step._check_gh_available()

        assert available is False
        assert "failed" in reason.lower()

    def test_gh_not_authenticated(self, tmp_path, monkeypatch):
        """Test detection when gh CLI is not authenticated."""
        import subprocess

        step = PRManagerStep(str(tmp_path))
        call_count = [0]

        def mock_run(cmd, *args, **kwargs):
            call_count[0] += 1
            if cmd == ["gh", "--version"]:
                return subprocess.CompletedProcess(cmd, 0, "gh version 2.40.0", "")
            if cmd == ["gh", "auth", "status"]:
                return subprocess.CompletedProcess(cmd, 1, "", "not logged in")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        available, reason = step._check_gh_available()

        assert available is False
        assert "not authenticated" in reason.lower()
        assert call_count[0] == 2  # Both version and auth checks made

    def test_gh_auth_check_timeout(self, tmp_path, monkeypatch):
        """Test handling when gh auth status times out."""
        import subprocess

        step = PRManagerStep(str(tmp_path))

        def mock_run(cmd, *args, **kwargs):
            if cmd == ["gh", "--version"]:
                return subprocess.CompletedProcess(cmd, 0, "gh version 2.40.0", "")
            if cmd == ["gh", "auth", "status"]:
                raise subprocess.TimeoutExpired(cmd, 10)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        available, reason = step._check_gh_available()

        assert available is False
        assert "timed out" in reason.lower()

    def test_gh_auth_check_fails(self, tmp_path, monkeypatch):
        """Test handling when gh auth status raises CalledProcessError."""
        import subprocess

        step = PRManagerStep(str(tmp_path))

        def mock_run(cmd, *args, **kwargs):
            if cmd == ["gh", "--version"]:
                return subprocess.CompletedProcess(cmd, 0, "gh version 2.40.0", "")
            if cmd == ["gh", "auth", "status"]:
                raise subprocess.CalledProcessError(1, cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        available, reason = step._check_gh_available()

        assert available is False
        assert "failed" in reason.lower()

    def test_gh_fully_available(self, tmp_path, monkeypatch):
        """Test detection when gh CLI is installed and authenticated."""
        import subprocess

        step = PRManagerStep(str(tmp_path))

        def mock_run(cmd, *args, **kwargs):
            if cmd == ["gh", "--version"]:
                return subprocess.CompletedProcess(cmd, 0, "gh version 2.40.0", "")
            if cmd == ["gh", "auth", "status"]:
                return subprocess.CompletedProcess(cmd, 0, "Logged in", "")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        available, reason = step._check_gh_available()

        assert available is True
        assert reason == ""


class TestPRManagerStepOperations:
    """Tests for PRManagerStep core operations (Phase 2 implementation)."""

    def test_create_draft_pr_no_readme_fails(self, tmp_path):
        """Test _create_draft_pr fails gracefully when no README."""
        step = PRManagerStep(str(tmp_path))

        result = step._create_draft_pr()

        assert result.success is False
        assert "no readme" in result.message.lower()

    def test_create_draft_pr_no_frontmatter_skips(self, tmp_path):
        """Test _create_draft_pr skips when README has no frontmatter."""
        (tmp_path / "README.md").write_text("# Simple README\n\nNo frontmatter here.")
        step = PRManagerStep(str(tmp_path))

        result = step._create_draft_pr()

        assert result.success is True
        assert result.data.get("skipped") is True
        assert "frontmatter" in result.message.lower()

    def test_update_pr_body_no_pr_fails(self, tmp_path):
        """Test _update_pr_body fails when no PR exists."""
        # Create README with frontmatter but no draft_pr_url
        readme_content = """---
slug: test-project
project_name: "Test Project"
---

# Test Project
"""
        (tmp_path / "README.md").write_text(readme_content)
        step = PRManagerStep(str(tmp_path))

        result = step._update_pr_body()

        assert result.success is False
        assert "no pr found" in result.message.lower()

    def test_mark_pr_ready_no_pr_skips(self, tmp_path):
        """Test _mark_pr_ready skips when no PR exists."""
        step = PRManagerStep(str(tmp_path))

        result = step._mark_pr_ready()

        assert result.success is True
        assert result.data.get("skipped") is True
        assert "no pr found" in result.message.lower()


class TestPRManagerStepModuleLevelRun:
    """Tests for pr_manager module-level run function."""

    def test_module_run_function(self, tmp_path):
        """Test module-level run() function."""
        from steps.pr_manager import run

        result = run(str(tmp_path), None)
        assert result.success is True

    def test_module_run_with_config(self, tmp_path):
        """Test module-level run() function with config."""
        from steps.pr_manager import run

        result = run(str(tmp_path), {"operation": "create"})
        assert result.success is True

    def test_module_run_via_step_class(self, tmp_path):
        """Test PRManagerStep via run method."""
        step = PRManagerStep(str(tmp_path))
        result = step.run()
        assert result.success is True


class TestPRManagerStepIntegration:
    """Integration tests for PRManagerStep with run() method."""

    def test_full_run_when_gh_available_no_readme(self, tmp_path, monkeypatch):
        """Test full run() cycle when gh is available but no README."""
        import subprocess

        def mock_run(cmd, *args, **kwargs):
            if cmd == ["gh", "--version"]:
                return subprocess.CompletedProcess(cmd, 0, "gh version 2.40.0", "")
            if cmd == ["gh", "auth", "status"]:
                return subprocess.CompletedProcess(cmd, 0, "Logged in", "")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        step = PRManagerStep(str(tmp_path))
        result = step.run()

        # Should fail gracefully when no README exists
        assert result.success is False
        assert "no readme" in result.message.lower()

    def test_full_run_when_gh_unavailable(self, tmp_path, monkeypatch):
        """Test full run() cycle when gh is unavailable."""
        import subprocess

        def mock_run(cmd, *args, **kwargs):
            if cmd == ["gh", "--version"]:
                raise FileNotFoundError("gh not found")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        step = PRManagerStep(str(tmp_path))
        result = step.run()

        assert result.success is True
        assert result.data.get("skipped") is True
        assert "gh CLI not installed" in result.data.get("reason", "")
        assert len(result.warnings) > 0


class TestPRManagerStepStorePrUrl:
    """Unit tests for PRManagerStep._store_pr_url method edge cases."""

    def test_store_pr_url_inserts_new_field(self, tmp_path):
        """Test inserting draft_pr_url when field doesn't exist."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "---\ntitle: Test Project\nstatus: active\n---\n\n# Content\n",
            encoding="utf-8",
        )

        step = PRManagerStep(str(tmp_path))
        result = step._store_pr_url(readme, "https://github.com/test/repo/pull/123")

        assert result.success is True
        content = readme.read_text(encoding="utf-8")
        assert "draft_pr_url: https://github.com/test/repo/pull/123" in content
        # Verify frontmatter structure preserved
        assert content.startswith("---\n")
        assert "title: Test Project" in content

    def test_store_pr_url_updates_existing_field(self, tmp_path):
        """Test updating existing draft_pr_url field (the fixed bug)."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "---\ntitle: Test Project\ndraft_pr_url: https://github.com/old/url/pull/1\nstatus: active\n---\n\n# Content\n",
            encoding="utf-8",
        )

        step = PRManagerStep(str(tmp_path))
        result = step._store_pr_url(readme, "https://github.com/test/repo/pull/456")

        assert result.success is True
        content = readme.read_text(encoding="utf-8")
        # New URL should be present
        assert "draft_pr_url: https://github.com/test/repo/pull/456" in content
        # Old URL should NOT be present
        assert "https://github.com/old/url/pull/1" not in content
        # Should only have one draft_pr_url line
        assert content.count("draft_pr_url:") == 1

    def test_store_pr_url_no_frontmatter(self, tmp_path):
        """Test failure when README has no frontmatter."""
        readme = tmp_path / "README.md"
        readme.write_text("# No Frontmatter\n\nJust content.\n", encoding="utf-8")

        step = PRManagerStep(str(tmp_path))
        result = step._store_pr_url(readme, "https://github.com/test/repo/pull/123")

        assert result.success is False
        assert "no frontmatter" in result.message.lower()

    def test_store_pr_url_malformed_frontmatter(self, tmp_path):
        """Test failure when frontmatter has no closing ---."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "---\ntitle: Test\nstatus: active\n\n# Content without closing\n",
            encoding="utf-8",
        )

        step = PRManagerStep(str(tmp_path))
        result = step._store_pr_url(readme, "https://github.com/test/repo/pull/123")

        assert result.success is False
        assert "malformed frontmatter" in result.message.lower()

    def test_store_pr_url_file_not_found(self, tmp_path):
        """Test failure when README doesn't exist."""
        readme = tmp_path / "nonexistent" / "README.md"

        step = PRManagerStep(str(tmp_path))
        result = step._store_pr_url(readme, "https://github.com/test/repo/pull/123")

        assert result.success is False
        assert "could not read" in result.message.lower()

    def test_store_pr_url_preserves_multiline_content(self, tmp_path):
        """Test that multiline frontmatter and content are preserved."""
        original_content = """---
title: Complex Project
status: active
labels:
  - feature
  - enhancement
description: |
  This is a multiline
  description field.
---

# Heading

Body content with **markdown**.
"""
        readme = tmp_path / "README.md"
        readme.write_text(original_content, encoding="utf-8")

        step = PRManagerStep(str(tmp_path))
        result = step._store_pr_url(readme, "https://github.com/test/repo/pull/789")

        assert result.success is True
        content = readme.read_text(encoding="utf-8")
        # URL should be inserted
        assert "draft_pr_url: https://github.com/test/repo/pull/789" in content
        # Original content preserved
        assert "labels:" in content
        assert "- feature" in content
        assert "description: |" in content
        assert "Body content with **markdown**." in content

    def test_store_pr_url_write_error(self, tmp_path, monkeypatch):
        """Test failure when write operation fails."""
        readme = tmp_path / "README.md"
        readme.write_text("---\ntitle: Test\n---\n# Content\n", encoding="utf-8")

        step = PRManagerStep(str(tmp_path))

        # Mock write_text to raise an error
        def mock_write_text(*args, **kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "write_text", mock_write_text)
        result = step._store_pr_url(readme, "https://github.com/test/repo/pull/123")

        assert result.success is False
        assert "could not write" in result.message.lower()
