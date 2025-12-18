"""
Configuration loader for lifecycle hooks.

This module manages the configuration for the claude-spec plugin's lifecycle
system, including pre/post steps for commands and session start behavior.

Configuration Schema
--------------------

The configuration file is JSON with the following top-level structure:

.. code-block:: json

    {
        "lifecycle": {
            "sessionStart": { ... },
            "commands": { ... }
        }
    }

**lifecycle.sessionStart** - Controls session initialization:

    - ``enabled`` (bool): Whether session start hook runs. Default: ``true``
    - ``loadContext`` (object): Which context types to load:
        - ``claudeMd`` (bool): Load CLAUDE.md files. Default: ``true``
        - ``gitState`` (bool): Load git status/branch info. Default: ``true``
        - ``projectStructure`` (bool): Load project file tree. Default: ``true``

**lifecycle.commands** - Per-command step configuration:

    Each command (e.g., "claude-spec:complete", "claude-spec:plan") can have:

    - ``preSteps`` (array): Steps to run before command execution
    - ``postSteps`` (array): Steps to run after command completes

    Each step object has:

    - ``name`` (str): Step identifier (e.g., "security-review")
    - ``enabled`` (bool): Whether step runs. Default: ``true``
    - ``timeout`` (int): Execution timeout in seconds (step-specific)

Example Configuration
---------------------

.. code-block:: json

    {
        "lifecycle": {
            "sessionStart": {
                "enabled": true,
                "loadContext": {
                    "claudeMd": true,
                    "gitState": true,
                    "projectStructure": true
                }
            },
            "commands": {
                "claude-spec:complete": {
                    "preSteps": [
                        { "name": "security-review", "enabled": true, "timeout": 120 }
                    ],
                    "postSteps": [
                        { "name": "generate-retrospective", "enabled": true },
                        { "name": "archive-logs", "enabled": true },
                        { "name": "cleanup-markers", "enabled": true }
                    ]
                },
                "claude-spec:plan": {
                    "preSteps": [],
                    "postSteps": []
                }
            }
        }
    }

Configuration Precedence
------------------------

Configuration is loaded with the following precedence (highest to lowest):

1. User config: ``~/.claude/claude-spec.config.json``
2. Default config: ``claude-spec.config.json`` (plugin root)
3. Empty dict (if neither exists)

Note: Legacy ``~/.claude/worktree-manager.config.json`` is auto-migrated to the new path.

User configuration values are deep-merged over template values, allowing
partial overrides while inheriting defaults.

Available Step Names
--------------------

Pre-steps:
    - ``security-review``: Run bandit security scanner on Python code

Post-steps:
    - ``generate-retrospective``: Create RETROSPECTIVE.md from project artifacts
    - ``archive-logs``: Move .prompt-log.json to completed project directory
    - ``cleanup-markers``: Remove .prompt-log-enabled and .cs-session-state.json

Functions
---------

Reads from ~/.claude/claude-spec.config.json with fallback to plugin default.
Provides utilities for accessing lifecycle configuration for pre/post steps.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Module-level cache for config (ARCH-002)
_config_cache: dict[str, Any] | None = None
_config_mtime: float | None = None


def get_user_config_path() -> Path:
    """Get the path to the user's claude-spec config file.

    Includes auto-migration from legacy worktree-manager.config.json path.
    """
    import sys

    new_path = Path.home() / ".claude" / "claude-spec.config.json"
    old_path = Path.home() / ".claude" / "worktree-manager.config.json"

    # Auto-migrate if old exists and new doesn't
    if old_path.exists() and not new_path.exists():
        try:
            old_path.rename(new_path)
            sys.stderr.write(f"cs-config: Migrated {old_path} → {new_path}\n")
        except OSError as e:
            sys.stderr.write(f"cs-config: Migration failed: {e}\n")

    return new_path


def get_template_config_path() -> Path:
    """Get the path to the default config file.

    The default config is located at the plugin root.
    """
    plugin_root = Path(__file__).parent.parent.parent
    return plugin_root / "claude-spec.config.json"


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Values in override take precedence. Nested dicts are merged recursively.

    Args:
        base: The base dictionary to merge into
        override: The dictionary with values to override

    Returns:
        A new dictionary with merged values
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _get_config_mtime() -> float:
    """Get the most recent modification time of config files.

    Returns:
        Max mtime of user and template configs, or 0 if neither exists.
    """
    user_config = get_user_config_path()
    template_config = get_template_config_path()

    mtimes = []
    if user_config.exists():
        try:
            mtimes.append(user_config.stat().st_mtime)
        except OSError:
            pass
    if template_config.exists():
        try:
            mtimes.append(template_config.stat().st_mtime)
        except OSError:
            pass

    return max(mtimes) if mtimes else 0


def load_config(*, force_reload: bool = False) -> dict[str, Any]:
    """Load configuration with fallback chain and caching (ARCH-002).

    Order of precedence:
    1. User config (~/.claude/worktree-manager.config.json)
    2. Template config (skills/worktree-manager/config.template.json)
    3. Empty dict if neither exists

    User config values are deep-merged over template values.

    The configuration is cached in memory and only reloaded when:
    - force_reload=True is passed
    - The config files have been modified since last load

    Args:
        force_reload: If True, bypass cache and reload from disk.

    Returns:
        The merged configuration dictionary (empty dict on any error)
    """
    import sys

    global _config_cache, _config_mtime

    # Check if we can use cached config
    current_mtime = _get_config_mtime()
    if (
        not force_reload
        and _config_cache is not None
        and _config_mtime == current_mtime
    ):
        return _config_cache

    user_config = get_user_config_path()
    template_config = get_template_config_path()

    config: dict[str, Any] = {}

    # Load template first as base
    if template_config.exists():
        try:
            with open(template_config, encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"cs-config: Malformed template config JSON: {e}\n")
        except OSError as e:
            sys.stderr.write(f"cs-config: Error reading template config: {e}\n")

    # Override with user config if it exists
    if user_config.exists():
        try:
            with open(user_config, encoding="utf-8") as f:
                user = json.load(f)
                config = deep_merge(config, user)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"cs-config: Malformed user config JSON: {e}\n")
        except OSError as e:
            sys.stderr.write(f"cs-config: Error reading user config: {e}\n")

    # Update cache
    _config_cache = config
    _config_mtime = current_mtime

    return config


def reset_config_cache() -> None:
    """Reset the config cache for testing (ARCH-002).

    This function allows tests to reset the module-level cache
    to ensure test isolation.
    """
    global _config_cache, _config_mtime
    _config_cache = None
    _config_mtime = None


def get_lifecycle_config() -> dict[str, Any]:
    """Get the lifecycle configuration section.

    Returns:
        The lifecycle config dict, or empty dict if not configured
    """
    config = load_config()
    return config.get("lifecycle", {})


def get_command_steps(command: str, phase: str) -> list[dict[str, Any]]:
    """Get pre or post steps for a specific command.

    Args:
        command: The command name (e.g., "claude-spec:complete", "claude-spec:plan")
        phase: The phase to get steps for ("preSteps" or "postSteps")

    Returns:
        List of step configurations, or empty list if none configured
    """
    lifecycle = get_lifecycle_config()
    commands = lifecycle.get("commands", {})
    cmd_config = commands.get(command, {})
    return cmd_config.get(phase, [])


def get_enabled_steps(command: str, phase: str) -> list[dict[str, Any]]:
    """Get only enabled steps for a command and phase.

    Args:
        command: The command name (e.g., "claude-spec:complete", "claude-spec:plan")
        phase: The phase to get steps for ("preSteps" or "postSteps")

    Returns:
        List of enabled step configurations only
    """
    steps = get_command_steps(command, phase)
    return [step for step in steps if step.get("enabled", True)]


def is_session_context_enabled(context_type: str) -> bool:
    """Check if a session context type is enabled.

    Args:
        context_type: The context type to check ("claudeMd", "gitState", "projectStructure")

    Returns:
        True if the context type is enabled (defaults to True if not configured)
    """
    lifecycle = get_lifecycle_config()
    session_start = lifecycle.get("sessionStart", {})
    load_context = session_start.get("loadContext", {})
    return load_context.get(context_type, True)


def is_session_start_enabled() -> bool:
    """Check if session start lifecycle is globally enabled.

    Returns:
        True if session start is enabled (defaults to True if not configured)
    """
    lifecycle = get_lifecycle_config()
    session_start = lifecycle.get("sessionStart", {})
    return session_start.get("enabled", True)
