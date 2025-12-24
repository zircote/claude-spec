"""Analyzers for claude-spec Prompt Capture Hook.

This package provides log analysis and retrospective insight generation
from prompt capture logs.

Modules:
    log_analyzer: Core analysis logic and data structures (LogAnalysis, SessionStats)
    analyze_cli: Command-line interface for running analysis

Usage:
    from analyzers.log_analyzer import analyze_log, generate_interaction_analysis

    analysis = analyze_log("/path/to/project")
    if analysis:
        markdown = generate_interaction_analysis(analysis)
"""

from .log_analyzer import (
    LogAnalysis,
    SessionStats,
    analyze_log,
    generate_interaction_analysis,
)

__all__ = [
    "LogAnalysis",
    "SessionStats",
    "analyze_log",
    "generate_interaction_analysis",
]
