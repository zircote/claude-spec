"""
Hooks library for lifecycle configuration and utilities.
"""

from .config_loader import (
    deep_merge,
    get_command_steps,
    get_enabled_steps,
    get_lifecycle_config,
    get_template_config_path,
    get_user_config_path,
    is_session_context_enabled,
    is_session_start_enabled,
    load_config,
    reset_config_cache,
)
from .fallback import (
    fallback_pass_through,
    fallback_read_input,
    fallback_stop_response,
    fallback_write_output,
)

__all__ = [
    # Config loader
    "get_user_config_path",
    "get_template_config_path",
    "load_config",
    "reset_config_cache",
    "deep_merge",
    "get_lifecycle_config",
    "get_command_steps",
    "get_enabled_steps",
    "is_session_context_enabled",
    "is_session_start_enabled",
    # Fallback functions
    "fallback_read_input",
    "fallback_write_output",
    "fallback_pass_through",
    "fallback_stop_response",
]
