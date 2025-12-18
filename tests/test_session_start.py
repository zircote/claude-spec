"""Tests for session_start hook."""

import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
import session_start
from session_start import (
    is_cs_project,
    load_claude_md,
    load_git_state,
    load_project_structure,
    main,
    read_input,
)


class TestReadInput:
    """Tests for read_input function."""

    def test_valid_json(self, monkeypatch):
        """Test reading valid JSON input."""
        input_data = {"hook_event_name": "SessionStart", "cwd": "/test"}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))
        result = read_input()
        assert result == input_data

    def test_invalid_json(self, monkeypatch):
        """Test handling of invalid JSON."""
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        result = read_input()
        assert result is None


class TestIsCsProject:
    """Tests for is_cs_project function."""

    def test_with_docs_spec_dir(self, tmp_path):
        """Test detection via docs/spec directory."""
        (tmp_path / "docs" / "spec").mkdir(parents=True)
        assert is_cs_project(str(tmp_path)) is True

    def test_with_prompt_log_marker(self, tmp_path):
        """Test detection via .prompt-log-enabled marker."""
        (tmp_path / ".prompt-log-enabled").touch()
        assert is_cs_project(str(tmp_path)) is True

    def test_with_claude_md_reference(self, tmp_path):
        """Test detection via CLAUDE.md with claude-spec reference."""
        (tmp_path / "CLAUDE.md").write_text("This uses claude-spec plugin")
        assert is_cs_project(str(tmp_path)) is True

    def test_with_cs_command_reference(self, tmp_path):
        """Test detection via CLAUDE.md with / reference."""
        (tmp_path / "CLAUDE.md").write_text("Use /p to plan")
        assert is_cs_project(str(tmp_path)) is True

    def test_non_cs_project(self, tmp_path):
        """Test non-cs project returns False."""
        assert is_cs_project(str(tmp_path)) is False


class TestLoadClaudeMd:
    """Tests for load_claude_md function."""

    def test_loads_local_claude_md(self, tmp_path):
        """Test loading local CLAUDE.md."""
        content = "# Project Instructions"
        (tmp_path / "CLAUDE.md").write_text(content)
        result = load_claude_md(str(tmp_path))
        assert "Project Instructions" in result
        assert "Project CLAUDE.md" in result

    def test_limits_long_content(self, tmp_path, monkeypatch):
        """Test that long content is limited in size."""
        # Mock home to avoid loading real global CLAUDE.md
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")
        content = "x" * 15000
        (tmp_path / "CLAUDE.md").write_text(content)
        result = load_claude_md(str(tmp_path))
        # Result should be less than original content (truncated)
        # Original was 15000, limit is 10000 + header overhead
        assert len(result) < 12000

    def test_handles_missing_file(self, tmp_path):
        """Test handling of missing CLAUDE.md."""
        result = load_claude_md(str(tmp_path))
        assert result == "" or "Project CLAUDE.md" not in result


class TestLoadGitState:
    """Tests for load_git_state function."""

    def test_loads_git_info(self, tmp_path):
        """Test loading git state from a git repo."""
        # Initialize a git repo with at least one commit
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
        # Create a file and commit to establish branch
        (tmp_path / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"], cwd=tmp_path, capture_output=True
        )

        result = load_git_state(str(tmp_path))
        assert "Git State" in result
        assert "Branch" in result

    def test_handles_non_git_dir(self, tmp_path):
        """Test handling of non-git directory."""
        result = load_git_state(str(tmp_path))
        # Should return minimal or empty state
        assert isinstance(result, str)


class TestLoadProjectStructure:
    """Tests for load_project_structure function."""

    def test_loads_structure(self, tmp_path):
        """Test loading project structure."""
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs" / "spec" / "active").mkdir(parents=True)

        result = load_project_structure(str(tmp_path))
        assert "Project Structure" in result
        assert "src" in result or "tests" in result or "docs/spec/active" in result


class TestMain:
    """Tests for main function."""

    def test_no_output_for_non_cs_project(self, tmp_path, monkeypatch, capsys):
        """Test no output for non-cs project."""
        input_data = {"hook_event_name": "SessionStart", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        # Should produce no or minimal output for non-cs project
        assert "Claude Spec Session Context" not in captured.out or captured.out == ""

    def test_outputs_context_for_cs_project(self, tmp_path, monkeypatch, capsys):
        """Test context output for cs project."""
        (tmp_path / "docs" / "spec").mkdir(parents=True)
        (tmp_path / "CLAUDE.md").write_text("# Test Project")

        input_data = {"hook_event_name": "SessionStart", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        assert "Claude Spec Session Context" in captured.out

    def test_handles_empty_cwd(self, monkeypatch, capsys):
        """Test handling of empty cwd."""
        input_data = {"hook_event_name": "SessionStart", "cwd": ""}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        main()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_handles_malformed_input(self, monkeypatch, capsys):
        """Test handling of malformed input."""
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

        main()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_session_start_disabled(self, tmp_path, monkeypatch, capsys):
        """Test no output when session start is disabled."""
        (tmp_path / "docs" / "spec").mkdir(parents=True)

        input_data = {"hook_event_name": "SessionStart", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock is_session_start_enabled to return False
        # Use raising=False in case the original import failed in CI
        original_config = session_start.CONFIG_AVAILABLE
        session_start.CONFIG_AVAILABLE = True
        monkeypatch.setattr(
            "session_start.is_session_start_enabled", lambda: False, raising=False
        )

        main()

        captured = capsys.readouterr()
        assert captured.out == ""

        session_start.CONFIG_AVAILABLE = original_config


class TestReadInputErrors:
    """Tests for error handling in read_input."""

    def test_generic_exception(self, monkeypatch, capsys):
        """Test handling of generic exception in read_input."""
        mock_stdin = MagicMock()
        mock_stdin.read.side_effect = OSError("Read error")
        monkeypatch.setattr("sys.stdin", mock_stdin)

        result = read_input()
        assert result is None

        captured = capsys.readouterr()
        assert "Error reading input" in captured.err


class TestIsCsProjectErrors:
    """Tests for error handling in is_cs_project."""

    def test_handles_claude_md_read_error(self, tmp_path, monkeypatch):
        """Test handling of CLAUDE.md read error."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("test")
        claude_md.chmod(0o000)

        result = is_cs_project(str(tmp_path))
        assert result is False

        # Cleanup
        claude_md.chmod(0o644)


class TestLoadClaudeMdErrors:
    """Tests for error handling in load_claude_md."""

    def test_handles_global_read_error(self, tmp_path, monkeypatch, capsys):
        """Test handling of global CLAUDE.md read error."""
        # Create a fake home with unreadable CLAUDE.md
        fake_home = tmp_path / "fakehome" / ".claude"
        fake_home.mkdir(parents=True)
        global_claude = fake_home / "CLAUDE.md"
        global_claude.write_text("global content")
        global_claude.chmod(0o000)

        monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

        _ = load_claude_md(str(tmp_path))

        captured = capsys.readouterr()
        assert "Error reading global CLAUDE.md" in captured.err

        # Cleanup
        global_claude.chmod(0o644)

    def test_handles_local_read_error(self, tmp_path, monkeypatch, capsys):
        """Test handling of local CLAUDE.md read error."""
        # Mock home to avoid global CLAUDE.md
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")

        local_claude = tmp_path / "CLAUDE.md"
        local_claude.write_text("local content")
        local_claude.chmod(0o000)

        _ = load_claude_md(str(tmp_path))

        captured = capsys.readouterr()
        assert "Error reading local CLAUDE.md" in captured.err

        # Cleanup
        local_claude.chmod(0o644)


class TestLoadGitStateEdgeCases:
    """Tests for edge cases in load_git_state."""

    def test_handles_many_uncommitted_files(self, tmp_path):
        """Test handling of >10 uncommitted files."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True
        )

        # Create initial commit
        (tmp_path / "initial.txt").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"], cwd=tmp_path, capture_output=True
        )

        # Create 15 uncommitted files
        for i in range(15):
            (tmp_path / f"file{i}.txt").write_text(f"content {i}")

        result = load_git_state(str(tmp_path))
        assert "... and" in result
        assert "more" in result

    def test_handles_git_timeout(self, tmp_path, monkeypatch, capsys):
        """Test handling of git command timeout."""

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired("git", 5)

        monkeypatch.setattr(subprocess, "run", mock_run)

        _ = load_git_state(str(tmp_path))

        captured = capsys.readouterr()
        assert "timed out" in captured.err

    def test_handles_git_exception(self, tmp_path, monkeypatch, capsys):
        """Test handling of generic git exception."""

        def mock_run(*args, **kwargs):
            raise OSError("Git not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        _ = load_git_state(str(tmp_path))

        captured = capsys.readouterr()
        assert "Git error" in captured.err


class TestLoadProjectStructureEdgeCases:
    """Tests for edge cases in load_project_structure."""

    def test_handles_iterdir_exception(self, tmp_path, monkeypatch):
        """Test handling of exception during directory iteration."""
        # Create a directory that will cause an exception when iterated
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Mock iterdir to raise an exception
        original_iterdir = Path.iterdir

        def mock_iterdir(self):
            if "src" in str(self):
                raise PermissionError("Access denied")
            return original_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", mock_iterdir)

        result = load_project_structure(str(tmp_path))
        # Should still include src/ even without count
        assert "src" in result

    def test_handles_active_projects_exception(self, tmp_path, monkeypatch):
        """Test handling of exception when listing active projects."""
        active_specs = tmp_path / "docs" / "spec" / "active"
        active_specs.mkdir(parents=True)
        (active_specs / "project1").mkdir()

        original_iterdir = Path.iterdir

        call_count = [0]

        def mock_iterdir(self):
            if "active" in str(self) and call_count[0] > 0:
                raise PermissionError("Access denied")
            call_count[0] += 1
            return original_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", mock_iterdir)

        result = load_project_structure(str(tmp_path))
        # Should handle exception gracefully
        assert isinstance(result, str)
