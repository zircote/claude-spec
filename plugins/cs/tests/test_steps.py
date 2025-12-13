"""Tests for step modules."""

import json
import sys
from pathlib import Path

# Add steps to path
sys.path.insert(0, str(Path(__file__).parent.parent / "steps"))

from steps import (
    ContextLoaderStep,
    LogArchiverStep,
    MarkerCleanerStep,
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
