"""
Hooks library for lifecycle configuration and utilities.
"""

from .config_loader import (
    deep_merge,
    get_command_steps,
    get_lifecycle_config,
    get_template_config_path,
    get_user_config_path,
    is_session_context_enabled,
    load_config,
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
