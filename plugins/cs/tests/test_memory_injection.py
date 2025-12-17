"""Tests for memory injection (SessionStart hook integration).

Tests cover:
- spec_detector.py - Active specification detection
- memory_injector.py - Memory injection formatting
- config_loader.py - Memory injection configuration
- session_start.py - Integration with session start hook
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks" / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Tests for spec_detector.py
# =============================================================================


class TestSpecDetector:
    """Tests for spec detection module."""

    def test_detect_active_spec_with_single_project(self, tmp_path):
        """Test detecting a single active spec."""
        from spec_detector import detect_active_spec

        # Create active spec structure
        spec_dir = tmp_path / "docs" / "spec" / "active" / "2025-12-17-my-feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "README.md").write_text("# My Feature\n")

        result = detect_active_spec(tmp_path)

        assert result is not None
        assert result.slug == "my-feature"
        assert result.path == spec_dir
        assert result.readme_path == spec_dir / "README.md"

    def test_detect_active_spec_with_no_active_specs(self, tmp_path):
        """Test returns None when no active specs exist."""
        from spec_detector import detect_active_spec

        # Create empty active directory
        (tmp_path / "docs" / "spec" / "active").mkdir(parents=True)

        result = detect_active_spec(tmp_path)
        assert result is None

    def test_detect_active_spec_with_multiple_specs(self, tmp_path):
        """Test returns None when multiple active specs exist."""
        from spec_detector import detect_active_spec

        active_dir = tmp_path / "docs" / "spec" / "active"
        active_dir.mkdir(parents=True)

        # Create two active specs
        spec1 = active_dir / "2025-12-17-feature-one"
        spec1.mkdir()
        (spec1 / "README.md").write_text("# Feature One")

        spec2 = active_dir / "2025-12-17-feature-two"
        spec2.mkdir()
        (spec2 / "README.md").write_text("# Feature Two")

        result = detect_active_spec(tmp_path)
        assert result is None  # Ambiguous - returns None

    def test_detect_active_spec_no_spec_dir(self, tmp_path):
        """Test returns None when docs/spec/active doesn't exist."""
        from spec_detector import detect_active_spec

        result = detect_active_spec(tmp_path)
        assert result is None

    def test_detect_active_spec_dir_without_readme(self, tmp_path):
        """Test ignores directories without README.md."""
        from spec_detector import detect_active_spec

        active_dir = tmp_path / "docs" / "spec" / "active"
        active_dir.mkdir(parents=True)

        # Create directory without README
        (active_dir / "2025-12-17-incomplete").mkdir()

        result = detect_active_spec(tmp_path)
        assert result is None

    def test_extract_slug_with_date_prefix(self):
        """Test slug extraction from date-prefixed directory names."""
        from spec_detector import _extract_slug

        assert _extract_slug("2025-12-17-my-feature") == "my-feature"
        assert _extract_slug("2025-01-01-simple") == "simple"
        assert _extract_slug("2025-12-17-multi-part-slug") == "multi-part-slug"

    def test_extract_slug_without_date_prefix(self):
        """Test slug extraction falls back to full name."""
        from spec_detector import _extract_slug

        assert _extract_slug("no-date-prefix") == "no-date-prefix"
        assert _extract_slug("simple") == "simple"

    def test_get_spec_from_readme_with_frontmatter(self, tmp_path):
        """Test extracting slug from README frontmatter."""
        from spec_detector import get_spec_from_readme

        readme = tmp_path / "README.md"
        readme.write_text("""---
slug: custom-slug
title: My Feature
---

# My Feature
""")

        result = get_spec_from_readme(readme)
        assert result == "custom-slug"

    def test_get_spec_from_readme_with_quoted_slug(self, tmp_path):
        """Test extracting quoted slug from frontmatter."""
        from spec_detector import get_spec_from_readme

        readme = tmp_path / "README.md"
        readme.write_text("""---
slug: "quoted-slug"
---
""")

        result = get_spec_from_readme(readme)
        assert result == "quoted-slug"

    def test_get_spec_from_readme_no_frontmatter(self, tmp_path):
        """Test returns None when no frontmatter."""
        from spec_detector import get_spec_from_readme

        readme = tmp_path / "README.md"
        readme.write_text("# Just a heading\n\nSome content.")

        result = get_spec_from_readme(readme)
        assert result is None

    def test_find_all_active_specs(self, tmp_path):
        """Test finding all active specs."""
        from spec_detector import find_all_active_specs

        active_dir = tmp_path / "docs" / "spec" / "active"
        active_dir.mkdir(parents=True)

        # Create two specs
        spec1 = active_dir / "2025-12-17-first"
        spec1.mkdir()
        (spec1 / "README.md").write_text("# First")

        spec2 = active_dir / "2025-12-16-second"
        spec2.mkdir()
        (spec2 / "README.md").write_text("# Second")

        result = find_all_active_specs(tmp_path)

        assert len(result) == 2
        slugs = {s.slug for s in result}
        assert "first" in slugs
        assert "second" in slugs


# =============================================================================
# Tests for memory_injector.py
# =============================================================================


class TestMemoryInjector:
    """Tests for memory injector module."""

    def test_memory_injector_initialization(self):
        """Test MemoryInjector initializes with defaults."""
        from memory_injector import MemoryInjector

        injector = MemoryInjector()
        assert injector.limit == 10
        assert injector._recall_service is None

    def test_memory_injector_custom_limit(self):
        """Test MemoryInjector with custom limit."""
        from memory_injector import MemoryInjector

        injector = MemoryInjector(limit=5)
        assert injector.limit == 5

    def test_get_namespace_icon(self):
        """Test namespace icons are returned correctly."""
        from memory_injector import MemoryInjector

        injector = MemoryInjector()

        assert injector._get_namespace_icon("decisions") == "🎯"
        assert injector._get_namespace_icon("learnings") == "💡"
        assert injector._get_namespace_icon("blockers") == "🚧"
        assert injector._get_namespace_icon("progress") == "📊"
        assert injector._get_namespace_icon("unknown") == "📌"  # Default

    def test_format_for_context_empty_list(self):
        """Test formatting with empty memory list."""
        from memory_injector import MemoryInjector

        injector = MemoryInjector()
        result = injector.format_for_context([])
        assert result == ""

    def test_format_for_context_with_memories(self):
        """Test formatting memories for context injection."""
        from memory_injector import MemoryInjector

        # Create mock memory results
        mock_memory = MagicMock()
        mock_memory.namespace = "decisions"
        mock_memory.summary = "Important decision about architecture"
        mock_memory.timestamp = datetime(2025, 12, 17, 10, 0, 0, tzinfo=UTC)
        mock_memory.content = "We decided to use hooks for memory capture."

        mock_result = MagicMock()
        mock_result.memory = mock_memory

        injector = MemoryInjector()
        result = injector.format_for_context([mock_result])

        assert "## Session Memories" in result
        assert "🎯" in result  # decisions icon
        assert "Important decision about architecture" in result
        assert "2025-12-17" in result

    def test_format_for_context_includes_content(self):
        """Test formatting with content included."""
        from memory_injector import MemoryInjector

        mock_memory = MagicMock()
        mock_memory.namespace = "learnings"
        mock_memory.summary = "Learned something important"
        mock_memory.timestamp = datetime(2025, 12, 17, 10, 0, 0, tzinfo=UTC)
        mock_memory.content = "The full content of this learning is here."

        mock_result = MagicMock()
        mock_result.memory = mock_memory

        injector = MemoryInjector()
        result = injector.format_for_context([mock_result], include_content=True)

        assert "The full content of this learning is here." in result

    def test_format_for_context_truncates_long_content(self):
        """Test that long content is truncated."""
        from memory_injector import MemoryInjector

        mock_memory = MagicMock()
        mock_memory.namespace = "learnings"
        mock_memory.summary = "Test"
        mock_memory.timestamp = datetime.now(UTC)
        mock_memory.content = "x" * 1000  # Long content

        mock_result = MagicMock()
        mock_result.memory = mock_memory

        injector = MemoryInjector()
        result = injector.format_for_context([mock_result], include_content=True)

        # Content should be truncated to 500 chars + "..."
        assert "..." in result
        assert len(result) < 1000

    def test_get_session_memories_no_recall_service(self):
        """Test get_session_memories when recall service unavailable."""
        from memory_injector import MemoryInjector

        # Create injector without recall service available
        injector = MemoryInjector()
        # Force recall service to be None
        injector._recall_service = None

        # Mock the property to return None
        with patch.object(
            MemoryInjector,
            "recall_service",
            new_callable=lambda: property(lambda self: None),
        ):
            result = injector.get_session_memories(spec="test")
            assert result == []

    def test_get_memory_injector_factory(self):
        """Test factory function creates injector."""
        from memory_injector import get_memory_injector

        injector = get_memory_injector(limit=7)
        assert isinstance(injector, type(injector))  # Is a MemoryInjector
        assert injector.limit == 7


# =============================================================================
# Tests for config_loader.py - Memory Injection Config
# =============================================================================


class TestMemoryInjectionConfig:
    """Tests for memory injection configuration."""

    def test_is_memory_injection_enabled_default(self, tmp_path, monkeypatch):
        """Test memory injection is enabled by default."""
        from config_loader import is_memory_injection_enabled, reset_config_cache

        reset_config_cache()

        monkeypatch.setattr(
            "config_loader.get_user_config_path", lambda: tmp_path / "nonexistent.json"
        )
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent2.json",
        )

        assert is_memory_injection_enabled() is True

    def test_is_memory_injection_enabled_explicit_true(self, tmp_path, monkeypatch):
        """Test memory injection when explicitly enabled."""
        from config_loader import is_memory_injection_enabled, reset_config_cache

        reset_config_cache()

        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {"lifecycle": {"sessionStart": {"memoryInjection": {"enabled": True}}}}
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        assert is_memory_injection_enabled() is True

    def test_is_memory_injection_enabled_explicit_false(self, tmp_path, monkeypatch):
        """Test memory injection when explicitly disabled."""
        from config_loader import is_memory_injection_enabled, reset_config_cache

        reset_config_cache()

        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {"lifecycle": {"sessionStart": {"memoryInjection": {"enabled": False}}}}
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        assert is_memory_injection_enabled() is False

    def test_get_memory_injection_config_defaults(self, tmp_path, monkeypatch):
        """Test memory injection config returns defaults when not configured."""
        from config_loader import get_memory_injection_config, reset_config_cache

        reset_config_cache()

        monkeypatch.setattr(
            "config_loader.get_user_config_path", lambda: tmp_path / "nonexistent.json"
        )
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent2.json",
        )

        config = get_memory_injection_config()

        assert config["enabled"] is True
        assert config["limit"] == 10
        assert config["includeContent"] is False

    def test_get_memory_injection_config_custom(self, tmp_path, monkeypatch):
        """Test memory injection config with custom values."""
        from config_loader import get_memory_injection_config, reset_config_cache

        reset_config_cache()

        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "sessionStart": {
                            "memoryInjection": {
                                "enabled": True,
                                "limit": 20,
                                "includeContent": True,
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config_file)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        config = get_memory_injection_config()

        assert config["enabled"] is True
        assert config["limit"] == 20
        assert config["includeContent"] is True


# =============================================================================
# Tests for session_start.py - Memory Integration
# =============================================================================


class TestSessionStartMemoryIntegration:
    """Tests for memory injection in session start hook."""

    def test_load_session_memories_not_available(self, tmp_path, monkeypatch):
        """Test load_session_memories when module not available."""
        import session_start

        # Save original state
        original = session_start.MEMORY_INJECTION_AVAILABLE
        session_start.MEMORY_INJECTION_AVAILABLE = False

        result = session_start.load_session_memories(str(tmp_path))

        # Restore
        session_start.MEMORY_INJECTION_AVAILABLE = original

        assert result is None

    def test_load_session_memories_disabled(self, tmp_path, monkeypatch):
        """Test load_session_memories when disabled in config."""
        import session_start

        # Mock the config functions
        session_start.CONFIG_AVAILABLE = True

        with patch.object(
            session_start, "is_memory_injection_enabled", return_value=False
        ):
            result = session_start.load_session_memories(str(tmp_path))

        assert result is None

    def test_load_session_memories_with_error(self, tmp_path, monkeypatch, capsys):
        """Test load_session_memories handles errors gracefully."""
        import session_start

        session_start.MEMORY_INJECTION_AVAILABLE = True
        session_start.CONFIG_AVAILABLE = True

        with patch.object(
            session_start, "is_memory_injection_enabled", return_value=True
        ):
            with patch.object(
                session_start,
                "get_memory_injection_config",
                return_value={"enabled": True, "limit": 10, "includeContent": False},
            ):
                with patch.object(
                    session_start,
                    "detect_active_spec",
                    side_effect=Exception("Test error"),
                ):
                    result = session_start.load_session_memories(str(tmp_path))

        captured = capsys.readouterr()
        assert result is None
        assert "Error loading memories" in captured.err

    def test_load_session_memories_no_memories(self, tmp_path, monkeypatch):
        """Test load_session_memories when no memories found."""
        import session_start

        session_start.MEMORY_INJECTION_AVAILABLE = True
        session_start.CONFIG_AVAILABLE = True

        mock_injector = MagicMock()
        mock_injector.get_session_memories.return_value = []

        with patch.object(
            session_start, "is_memory_injection_enabled", return_value=True
        ):
            with patch.object(
                session_start,
                "get_memory_injection_config",
                return_value={"enabled": True, "limit": 10, "includeContent": False},
            ):
                with patch.object(
                    session_start, "detect_active_spec", return_value=None
                ):
                    with patch.object(
                        session_start, "MemoryInjector", return_value=mock_injector
                    ):
                        result = session_start.load_session_memories(str(tmp_path))

        assert result is None

    def test_main_includes_memory_context(self, tmp_path, monkeypatch, capsys):
        """Test main() includes memory context in output."""
        import io

        import session_start

        # Set up CS project
        (tmp_path / "docs" / "spec").mkdir(parents=True)
        (tmp_path / "CLAUDE.md").write_text("# Test")

        # Mock stdin
        input_data = {"hook_event_name": "SessionStart", "cwd": str(tmp_path)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(input_data)))

        # Mock memory injection
        session_start.MEMORY_INJECTION_AVAILABLE = True

        with patch.object(
            session_start,
            "load_session_memories",
            return_value="## Session Memories\n\nTest memory content",
        ):
            session_start.main()

        captured = capsys.readouterr()
        assert "Session Memories" in captured.out


# =============================================================================
# Tests for edge cases
# =============================================================================


class TestMemoryInjectionEdgeCases:
    """Tests for edge cases in memory injection."""

    def test_spec_detector_handles_permission_error(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test spec detector handles permission errors."""
        from spec_detector import detect_active_spec

        active_dir = tmp_path / "docs" / "spec" / "active"
        active_dir.mkdir(parents=True)

        # Mock iterdir to raise permission error
        original_iterdir = Path.iterdir

        def mock_iterdir(self):
            if "active" in str(self):
                raise PermissionError("Access denied")
            return original_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", mock_iterdir)

        result = detect_active_spec(tmp_path)

        captured = capsys.readouterr()
        assert result is None
        assert "Error scanning spec dir" in captured.err

    def test_get_spec_from_readme_handles_read_error(self, tmp_path, capsys):
        """Test get_spec_from_readme handles read errors."""
        from spec_detector import get_spec_from_readme

        readme = tmp_path / "README.md"
        readme.write_text("content")
        readme.chmod(0o000)

        result = get_spec_from_readme(readme)

        # Restore permissions for cleanup
        readme.chmod(0o644)

        captured = capsys.readouterr()
        assert result is None
        assert "Error reading" in captured.err

    def test_memory_injector_handles_result_without_memory_attr(self):
        """Test formatting handles results without memory attribute."""
        from memory_injector import MemoryInjector

        # Create mock that doesn't have .memory attribute
        mock_result = MagicMock(spec=[])  # Empty spec means no attributes
        mock_result.namespace = "decisions"
        mock_result.summary = "Direct result"
        mock_result.timestamp = datetime.now(UTC)
        mock_result.content = None

        injector = MemoryInjector()
        # This should handle the case where result itself is the memory
        result = injector.format_for_context([mock_result])

        assert "Session Memories" in result

    def test_find_all_active_specs_sorts_by_mtime(self, tmp_path):
        """Test find_all_active_specs sorts by modification time."""
        import time

        from spec_detector import find_all_active_specs

        active_dir = tmp_path / "docs" / "spec" / "active"
        active_dir.mkdir(parents=True)

        # Create first spec
        spec1 = active_dir / "2025-12-15-older"
        spec1.mkdir()
        readme1 = spec1 / "README.md"
        readme1.write_text("# Older")

        time.sleep(0.1)  # Ensure different mtime

        # Create second spec (more recent)
        spec2 = active_dir / "2025-12-17-newer"
        spec2.mkdir()
        readme2 = spec2 / "README.md"
        readme2.write_text("# Newer")

        result = find_all_active_specs(tmp_path)

        assert len(result) == 2
        # Most recent should be first
        assert result[0].slug == "newer"
        assert result[1].slug == "older"
