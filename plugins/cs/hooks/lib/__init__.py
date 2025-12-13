"""
Hooks library for lifecycle configuration and utilities.
"""

from .config_loader import (
    get_user_config_path,
    get_template_config_path,
    load_config,
    deep_merge,
    get_lifecycle_config,
    get_command_steps,
    is_session_context_enabled,
)

__all__ = [
    "get_user_config_path",
    "get_template_config_path",
    "load_config",
    "deep_merge",
    "get_lifecycle_config",
    "get_command_steps",
    "is_session_context_enabled",
]
