"""Tests for hooks/lib/config_loader.py"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

# Add hooks/lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks" / "lib"))

from config_loader import (
    deep_merge,
    get_command_steps,
    get_enabled_steps,
    get_lifecycle_config,
    get_template_config_path,
    get_user_config_path,
    is_session_context_enabled,
    is_session_start_enabled,
    load_config,
)


class TestGetUserConfigPath:
    """Tests for get_user_config_path."""

    def test_returns_path_in_home(self):
        """Test returns path in user's home directory."""
        path = get_user_config_path()
        assert path == Path.home() / ".claude" / "worktree-manager.config.json"


class TestGetTemplateConfigPath:
    """Tests for get_template_config_path."""

    def test_returns_path_to_template(self):
        """Test returns path to template config."""
        path = get_template_config_path()
        assert path.name == "config.template.json"
        assert "worktree-manager" in str(path)


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_merges_flat_dicts(self):
        """Test merging flat dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merges_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {"a": {"x": 1, "y": 2}, "b": 1}
        override = {"a": {"y": 3, "z": 4}}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}, "b": 1}

    def test_override_replaces_non_dict(self):
        """Test override replaces non-dict values."""
        base = {"a": {"x": 1}}
        override = {"a": "string"}
        result = deep_merge(base, override)
        assert result == {"a": "string"}

    def test_does_not_modify_original(self):
        """Test original dicts are not modified."""
        base = {"a": 1}
        override = {"b": 2}
        deep_merge(base, override)
        assert base == {"a": 1}


class TestLoadConfig:
    """Tests for load_config function."""

    def test_returns_empty_dict_when_no_configs(self, tmp_path, monkeypatch):
        """Test returns empty dict when no config files exist."""
        monkeypatch.setattr(
            "config_loader.get_user_config_path", lambda: tmp_path / "nonexistent.json"
        )
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent2.json",
        )
        result = load_config()
        assert result == {}

    def test_loads_template_config(self, tmp_path, monkeypatch):
        """Test loads template config when user config missing."""
        template = tmp_path / "template.json"
        template.write_text('{"key": "value"}')

        monkeypatch.setattr(
            "config_loader.get_user_config_path", lambda: tmp_path / "nonexistent.json"
        )
        monkeypatch.setattr("config_loader.get_template_config_path", lambda: template)

        result = load_config()
        assert result == {"key": "value"}

    def test_merges_user_over_template(self, tmp_path, monkeypatch):
        """Test user config overrides template."""
        template = tmp_path / "template.json"
        template.write_text('{"a": 1, "b": 2}')

        user = tmp_path / "user.json"
        user.write_text('{"b": 3, "c": 4}')

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: user)
        monkeypatch.setattr("config_loader.get_template_config_path", lambda: template)

        result = load_config()
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_handles_malformed_template_json(self, tmp_path, monkeypatch, capsys):
        """Test handles malformed template JSON gracefully."""
        template = tmp_path / "template.json"
        template.write_text("not valid json {")

        monkeypatch.setattr(
            "config_loader.get_user_config_path", lambda: tmp_path / "nonexistent.json"
        )
        monkeypatch.setattr("config_loader.get_template_config_path", lambda: template)

        result = load_config()
        assert result == {}  # Falls back to empty dict
        # Error should be logged to stderr
        captured = capsys.readouterr()
        assert "Malformed template config JSON" in captured.err

    def test_handles_malformed_user_json(self, tmp_path, monkeypatch, capsys):
        """Test handles malformed user JSON gracefully."""
        template = tmp_path / "template.json"
        template.write_text('{"key": "from_template"}')

        user = tmp_path / "user.json"
        user.write_text("not valid json {")

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: user)
        monkeypatch.setattr("config_loader.get_template_config_path", lambda: template)

        result = load_config()
        # Should return template config since user config failed
        assert result == {"key": "from_template"}
        captured = capsys.readouterr()
        assert "Malformed user config JSON" in captured.err

    def test_handles_template_read_error(self, tmp_path, monkeypatch, capsys):
        """Test handles template read OSError gracefully."""
        template = tmp_path / "template.json"
        template.write_text('{"key": "value"}')

        # Make the file unreadable
        monkeypatch.setattr(
            "config_loader.get_user_config_path", lambda: tmp_path / "nonexistent.json"
        )
        monkeypatch.setattr("config_loader.get_template_config_path", lambda: template)

        # Mock open to raise OSError
        original_open = open

        def mock_open(path, *args, **kwargs):
            if str(path) == str(template):
                raise OSError("Permission denied")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", mock_open):
            result = load_config()

        assert result == {}
        captured = capsys.readouterr()
        assert "Error reading template config" in captured.err

    def test_handles_user_read_error(self, tmp_path, monkeypatch, capsys):
        """Test handles user config read OSError gracefully."""
        template = tmp_path / "template.json"
        template.write_text('{"key": "from_template"}')

        user = tmp_path / "user.json"
        user.write_text('{"key": "from_user"}')

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: user)
        monkeypatch.setattr("config_loader.get_template_config_path", lambda: template)

        # Mock open to raise OSError only for user config
        original_open = open

        def mock_open(path, *args, **kwargs):
            if str(path) == str(user):
                raise OSError("Permission denied")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", mock_open):
            result = load_config()

        # Should still have template config
        assert result == {"key": "from_template"}
        captured = capsys.readouterr()
        assert "Error reading user config" in captured.err


class TestGetLifecycleConfig:
    """Tests for get_lifecycle_config."""

    def test_returns_lifecycle_section(self, tmp_path, monkeypatch):
        """Test returns lifecycle section from config."""
        config = tmp_path / "config.json"
        config.write_text('{"lifecycle": {"commands": {}}, "other": "value"}')

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        result = get_lifecycle_config()
        assert result == {"commands": {}}

    def test_returns_empty_dict_when_no_lifecycle(self, tmp_path, monkeypatch):
        """Test returns empty dict when no lifecycle section."""
        config = tmp_path / "config.json"
        config.write_text('{"other": "value"}')

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        result = get_lifecycle_config()
        assert result == {}


class TestGetCommandSteps:
    """Tests for get_command_steps."""

    def test_returns_steps_for_command(self, tmp_path, monkeypatch):
        """Test returns steps for a specific command."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "commands": {
                            "cs:c": {
                                "preSteps": [{"name": "security-review"}],
                                "postSteps": [{"name": "archive-logs"}],
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        result = get_command_steps("cs:c", "preSteps")
        assert result == [{"name": "security-review"}]

    def test_returns_empty_for_unknown_command(self, tmp_path, monkeypatch):
        """Test returns empty list for unknown command."""
        config = tmp_path / "config.json"
        config.write_text('{"lifecycle": {"commands": {}}}')

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        result = get_command_steps("unknown:cmd", "preSteps")
        assert result == []


class TestGetEnabledSteps:
    """Tests for get_enabled_steps."""

    def test_filters_disabled_steps(self, tmp_path, monkeypatch):
        """Test filters out disabled steps."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "commands": {
                            "cs:c": {
                                "preSteps": [
                                    {"name": "step1", "enabled": True},
                                    {"name": "step2", "enabled": False},
                                    {"name": "step3"},  # Default enabled
                                ]
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        result = get_enabled_steps("cs:c", "preSteps")
        assert len(result) == 2
        assert result[0]["name"] == "step1"
        assert result[1]["name"] == "step3"


class TestIsSessionContextEnabled:
    """Tests for is_session_context_enabled."""

    def test_returns_true_by_default(self, tmp_path, monkeypatch):
        """Test returns True when not configured."""
        monkeypatch.setattr(
            "config_loader.get_user_config_path", lambda: tmp_path / "nonexistent.json"
        )
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent2.json",
        )

        assert is_session_context_enabled("claudeMd") is True
        assert is_session_context_enabled("gitState") is True

    def test_respects_config_value(self, tmp_path, monkeypatch):
        """Test respects configured value."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "sessionStart": {
                            "loadContext": {"claudeMd": False, "gitState": True}
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        assert is_session_context_enabled("claudeMd") is False
        assert is_session_context_enabled("gitState") is True


class TestIsSessionStartEnabled:
    """Tests for is_session_start_enabled."""

    def test_returns_true_by_default(self, tmp_path, monkeypatch):
        """Test returns True when not configured."""
        monkeypatch.setattr(
            "config_loader.get_user_config_path", lambda: tmp_path / "nonexistent.json"
        )
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent2.json",
        )

        assert is_session_start_enabled() is True

    def test_respects_config_value(self, tmp_path, monkeypatch):
        """Test respects configured value."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps({"lifecycle": {"sessionStart": {"enabled": False}}})
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        assert is_session_start_enabled() is False


# ============================================================================
# NEW TESTS ADDED FOR COVERAGE GAPS
# ============================================================================


class TestGetEnabledStepsUnknownPhase:
    """Tests for get_enabled_steps with unknown phase handling."""

    def test_returns_empty_for_unknown_phase(self, tmp_path, monkeypatch):
        """Test returns empty list for unknown phase name."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "commands": {
                            "cs:c": {
                                "preSteps": [{"name": "step1", "enabled": True}],
                                "postSteps": [{"name": "step2", "enabled": True}],
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        # Test with unknown phase name
        result = get_enabled_steps("cs:c", "unknownPhase")
        assert result == []

    def test_returns_empty_for_invalid_phase_type(self, tmp_path, monkeypatch):
        """Test returns empty list for invalid phase types."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "commands": {
                            "cs:c": {
                                "preSteps": [{"name": "step1"}],
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        # Test with completely invalid phase names
        assert get_enabled_steps("cs:c", "during") == []
        assert get_enabled_steps("cs:c", "beforeSteps") == []
        assert get_enabled_steps("cs:c", "afterSteps") == []

    def test_returns_empty_for_nonexistent_command(self, tmp_path, monkeypatch):
        """Test returns empty list for nonexistent command."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "commands": {
                            "cs:c": {
                                "preSteps": [{"name": "step1"}],
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        # Test with nonexistent command
        result = get_enabled_steps("cs:nonexistent", "preSteps")
        assert result == []

    def test_handles_empty_steps_list(self, tmp_path, monkeypatch):
        """Test handles empty steps list correctly."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "commands": {
                            "cs:c": {
                                "preSteps": [],
                                "postSteps": [],
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        assert get_enabled_steps("cs:c", "preSteps") == []
        assert get_enabled_steps("cs:c", "postSteps") == []


class TestGetCommandStepsEdgeCases:
    """Additional edge case tests for get_command_steps."""

    def test_returns_empty_for_missing_phase(self, tmp_path, monkeypatch):
        """Test returns empty list when phase is missing from command config."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "commands": {
                            "cs:c": {
                                "preSteps": [{"name": "step1"}]
                                # postSteps is not defined
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        result = get_command_steps("cs:c", "postSteps")
        assert result == []

    def test_returns_steps_for_all_valid_phases(self, tmp_path, monkeypatch):
        """Test retrieves steps for all standard phase names."""
        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "lifecycle": {
                        "commands": {
                            "cs:c": {
                                "preSteps": [{"name": "pre-step"}],
                                "postSteps": [{"name": "post-step"}],
                            }
                        }
                    }
                }
            )
        )

        monkeypatch.setattr("config_loader.get_user_config_path", lambda: config)
        monkeypatch.setattr(
            "config_loader.get_template_config_path",
            lambda: tmp_path / "nonexistent.json",
        )

        pre_result = get_command_steps("cs:c", "preSteps")
        post_result = get_command_steps("cs:c", "postSteps")

        assert pre_result == [{"name": "pre-step"}]
        assert post_result == [{"name": "post-step"}]


class TestDeepMergeEdgeCases:
    """Additional edge case tests for deep_merge."""

    def test_merge_empty_base(self):
        """Test merging into empty base dict."""
        base = {}
        override = {"a": 1, "b": {"c": 2}}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": {"c": 2}}

    def test_merge_empty_override(self):
        """Test merging with empty override dict."""
        base = {"a": 1, "b": {"c": 2}}
        override = {}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": {"c": 2}}

    def test_merge_both_empty(self):
        """Test merging two empty dicts."""
        result = deep_merge({}, {})
        assert result == {}

    def test_merge_deeply_nested(self):
        """Test merging deeply nested structures."""
        base = {"a": {"b": {"c": {"d": 1}}}}
        override = {"a": {"b": {"c": {"e": 2}}}}
        result = deep_merge(base, override)
        assert result == {"a": {"b": {"c": {"d": 1, "e": 2}}}}
