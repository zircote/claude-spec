#!/usr/bin/env python3
"""
Session Start Hook for claude-spec Plugin

This hook fires on Claude Code session start and loads project context
into Claude's memory. Context includes CLAUDE.md files, git state,
and project structure.

Usage:
    Registered as a SessionStart hook via hooks.json.
    Receives JSON via stdin, outputs text context to stdout.

Input format:
    {
        "hook_event_name": "SessionStart",
        "session_id": "string",
        "cwd": "string"
    }

Output:
    Text content added to Claude's initial context (via stdout)
    Errors go to stderr (never block)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Add hooks directory to path for lib imports
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent

if str(SCRIPT_DIR / "lib") not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR / "lib"))
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

try:
    from config_loader import (
        get_memory_injection_config,
        is_memory_injection_enabled,
        is_session_context_enabled,
        is_session_start_enabled,
    )

    CONFIG_AVAILABLE = True
except ImportError as e:
    CONFIG_AVAILABLE = False
    sys.stderr.write(f"claude-spec session_start: Config import error: {e}\n")

# Import shared context utilities
try:
    from utils.context_utils import (
        load_claude_md,
        load_git_state,
        load_project_structure,
    )

    CONTEXT_UTILS_AVAILABLE = True
except ImportError as e:
    CONTEXT_UTILS_AVAILABLE = False
    sys.stderr.write(f"claude-spec session_start: Context utils import error: {e}\n")

# Import memory injection components
try:
    from memory_injector import MemoryInjector
    from spec_detector import detect_active_spec

    MEMORY_INJECTION_AVAILABLE = True
except ImportError as e:
    MEMORY_INJECTION_AVAILABLE = False
    sys.stderr.write(f"claude-spec session_start: Memory injection import error: {e}\n")

# Import embedding service for pre-warming (PERF-001)
try:
    from memory.embedding import preload_model as preload_embedding_model

    EMBEDDING_AVAILABLE = True
except ImportError as e:
    EMBEDDING_AVAILABLE = False
    # Log the failure so developers know why embedding pre-warming is skipped
    sys.stderr.write(f"claude-spec session_start: Embedding import unavailable: {e}\n")

LOG_PREFIX = "claude-spec session_start"


def read_input() -> dict[str, Any] | None:
    """Read and parse JSON input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"{LOG_PREFIX}: JSON decode error: {e}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"{LOG_PREFIX}: Error reading input: {e}\n")
        return None


def is_cs_project(cwd: str) -> bool:
    """Check if this appears to be a claude-spec managed project.

    A project is considered cs-managed if it has:
    - docs/spec/ directory, OR
    - .prompt-log-enabled marker, OR
    - CLAUDE.md with 'claude-spec' references
    """
    cwd_path = Path(cwd)

    # Check for docs/spec directory
    if (cwd_path / "docs" / "spec").is_dir():
        return True

    # Check for prompt log marker
    if (cwd_path / ".prompt-log-enabled").is_file():
        return True

    # Check CLAUDE.md for cs references
    claude_md = cwd_path / "CLAUDE.md"
    if claude_md.is_file():
        try:
            content = claude_md.read_text(encoding="utf-8")
            if "claude-spec" in content.lower() or "/cs:" in content:
                return True
        except Exception as e:
            sys.stderr.write(f"{LOG_PREFIX}: Error reading {claude_md}: {e}\n")

    return False


def load_session_memories(cwd: str, log_prefix: str = LOG_PREFIX) -> str | None:
    """Load relevant memories for the session.

    Queries the memory system for memories relevant to the current project
    and active specification (if any).

    Args:
        cwd: Current working directory
        log_prefix: Prefix for log messages

    Returns:
        Formatted markdown string with memories, or None if no memories
    """
    if not MEMORY_INJECTION_AVAILABLE:
        return None

    # Check if memory injection is enabled
    if CONFIG_AVAILABLE and not is_memory_injection_enabled():
        return None

    # Get memory injection config
    if CONFIG_AVAILABLE:
        config = get_memory_injection_config()
    else:
        config = {"enabled": True, "limit": 10, "includeContent": False}

    if not config.get("enabled", True):
        return None

    try:
        # Detect active spec
        active_spec = detect_active_spec(cwd)
        spec_slug = active_spec.slug if active_spec else None

        # Create injector and get memories
        injector = MemoryInjector(limit=config.get("limit", 10))

        memories = injector.get_session_memories(
            spec=spec_slug,
            limit=config.get("limit", 10),
        )

        if not memories:
            return None

        # Format for context
        include_content = config.get("includeContent", False)
        formatted = injector.format_for_context(
            memories,
            include_content=include_content,
        )

        if formatted:
            sys.stderr.write(
                f"{log_prefix}: Injected {len(memories)} memories"
                f"{f' for spec {spec_slug}' if spec_slug else ''}\n"
            )

        return formatted

    except Exception as e:
        sys.stderr.write(f"{log_prefix}: Error loading memories: {e}\n")
        return None


def main() -> None:
    """Main entry point for the session start hook."""
    # Read input
    input_data = read_input()

    if input_data is None:
        # Malformed input - silent exit
        return

    cwd = input_data.get("cwd", "")

    if not cwd:
        return

    # Check if session start is enabled
    if CONFIG_AVAILABLE and not is_session_start_enabled():
        return

    # Check if this is a cs project
    if not is_cs_project(cwd):
        return

    # PERF-001: Pre-warm embedding model during SessionStart (500ms budget)
    # This eliminates 2-5 second cold start latency in later hooks (<100ms budget)
    if EMBEDDING_AVAILABLE and MEMORY_INJECTION_AVAILABLE:
        try:
            preload_embedding_model()
        except Exception as e:
            # Graceful degradation - don't fail session start for embedding issues
            sys.stderr.write(
                f"{LOG_PREFIX}: Embedding pre-warm failed (non-fatal): {e}\n"
            )

    # Check if context utils are available
    if not CONTEXT_UTILS_AVAILABLE:
        sys.stderr.write(f"{LOG_PREFIX}: Context utils not available, skipping\n")
        return

    # Build context parts based on config
    context_parts = []

    context_parts.append("# Claude Spec Session Context\n")
    context_parts.append("_Loaded by claude-spec plugin on session start_\n")

    # Load each context type if enabled
    if not CONFIG_AVAILABLE or is_session_context_enabled("claudeMd"):
        claude_md = load_claude_md(cwd, log_prefix=LOG_PREFIX)
        if claude_md:
            context_parts.append(claude_md)

    if not CONFIG_AVAILABLE or is_session_context_enabled("gitState"):
        git_state = load_git_state(cwd, log_prefix=LOG_PREFIX)
        if git_state:
            context_parts.append(git_state)

    if not CONFIG_AVAILABLE or is_session_context_enabled("projectStructure"):
        structure = load_project_structure(cwd, log_prefix=LOG_PREFIX)
        if structure:
            context_parts.append(structure)

    # Load session memories (if available and enabled)
    memories = load_session_memories(cwd, log_prefix=LOG_PREFIX)
    if memories:
        context_parts.append(memories)

    # Output context (stdout is added to Claude's initial context)
    if len(context_parts) > 2:  # More than just header
        print("\n\n".join(context_parts))


if __name__ == "__main__":
    main()
