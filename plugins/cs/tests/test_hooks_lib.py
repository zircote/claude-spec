"""Tests for hooks/lib module."""

import sys
from pathlib import Path

# Add hooks to path so we can import from lib
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))


class TestHooksLibImports:
    """Tests for hooks/lib/__init__.py exports."""

    def test_imports_all_functions(self):
        """Test that all functions can be imported from lib."""
        from lib import (
            deep_merge,
            get_command_steps,
            get_lifecycle_config,
            get_template_config_path,
            get_user_config_path,
            is_session_context_enabled,
            load_config,
        )

        # Verify they are callable
        assert callable(get_user_config_path)
        assert callable(get_template_config_path)
        assert callable(load_config)
        assert callable(deep_merge)
        assert callable(get_lifecycle_config)
        assert callable(get_command_steps)
        assert callable(is_session_context_enabled)

    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        import lib

        expected = [
            "get_user_config_path",
            "get_template_config_path",
            "load_config",
            "deep_merge",
            "get_lifecycle_config",
            "get_command_steps",
            "is_session_context_enabled",
        ]

        for name in expected:
            assert name in lib.__all__
