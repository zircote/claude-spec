"""Log Analyzer for claude-spec Prompt Capture Hook.

Analyzes .prompt-log.json to generate insights for retrospectives.
Calculates metrics, identifies patterns, and generates recommendations.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# SEC-MED-003: sys.path manipulation for standalone execution
# See analyze_cli.py for detailed security documentation.
_SCRIPT_DIR = Path(__file__).parent.resolve()
_PLUGIN_ROOT = _SCRIPT_DIR.parent
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from filters.log_entry import LogEntry
from filters.log_writer import read_log

# QUAL-MED-002: Named constants for analysis thresholds
# These thresholds define when insights and recommendations are triggered

# Session is considered "clarification-heavy" if it has more than this many questions
CLARIFICATION_HEAVY_THRESHOLD = 10

# Ratio thresholds for question analysis
HIGH_QUESTION_RATIO = 0.5  # >50% questions triggers insight
EXCESSIVE_QUESTIONS_RATIO = 0.3  # >30% questions triggers recommendation

# Session count thresholds
MULTI_SESSION_THRESHOLD = 3  # More than 3 sessions triggers insight
MANY_SESSIONS_THRESHOLD = 5  # More than 5 sessions triggers recommendation

# Prompt length thresholds (in characters)
SHORT_PROMPT_THRESHOLD = 50  # Below this suggests prompts are too brief
DETAILED_PROMPT_THRESHOLD = 500  # Above this suggests detailed prompting


@dataclass
class SessionStats:
    """Statistics for a single Claude Code session.

    Tracks interaction patterns within a single session, including
    prompt types, questions asked, and content filtering events.

    Attributes:
        session_id: Unique identifier for the session (from CLAUDE_SESSION_ID).
        entry_count: Total number of log entries in this session.
        user_inputs: Count of user-initiated prompts (entry_type="user_input").
        expanded_prompts: Count of expanded slash command prompts.
        response_summaries: Count of response summary entries.
        questions_asked: Number of user inputs containing "?" (indicates clarification).
        filtered_content: Number of entries with secrets filtered out.
        start_time: ISO timestamp of first entry in session (if available).
        end_time: ISO timestamp of last entry in session (if available).
    """

    session_id: str
    entry_count: int
    user_inputs: int
    expanded_prompts: int
    response_summaries: int
    questions_asked: int  # Entries containing "?"
    filtered_content: int
    start_time: str | None = None
    end_time: str | None = None


@dataclass
class LogAnalysis:
    """Complete analysis of a prompt log for retrospective generation.

    Aggregates metrics across all sessions in a prompt log, providing
    insights for project retrospectives and interaction pattern analysis.

    Attributes:
        total_entries: Total log entries across all sessions.
        user_inputs: Total user-initiated prompts.
        expanded_prompts: Total expanded slash command prompts.
        response_summaries: Total response summary entries.
        session_count: Number of unique sessions in the log.
        avg_entries_per_session: Mean entries per session for efficiency metrics.
        total_questions: Prompts containing "?" (clarification indicators).
        clarification_heavy_sessions: Sessions exceeding CLARIFICATION_HEAVY_THRESHOLD.
        total_filtered_content: Entries with any content filtered.
        secrets_filtered: Total secret instances filtered (may be >1 per entry).
        prompt_length_min: Shortest user prompt in characters.
        prompt_length_max: Longest user prompt in characters.
        prompt_length_avg: Mean user prompt length for detail metrics.
        commands_used: Frequency map of slash commands used.
        session_stats: Per-session statistics for detailed analysis.
        first_entry_time: ISO timestamp of earliest log entry.
        last_entry_time: ISO timestamp of latest log entry.
    """

    total_entries: int = 0
    user_inputs: int = 0
    expanded_prompts: int = 0
    response_summaries: int = 0

    session_count: int = 0
    avg_entries_per_session: float = 0.0

    total_questions: int = 0  # Prompts containing "?"
    clarification_heavy_sessions: int = (
        0  # Sessions exceeding CLARIFICATION_HEAVY_THRESHOLD
    )

    total_filtered_content: int = 0
    secrets_filtered: int = 0

    prompt_length_min: int = 0
    prompt_length_max: int = 0
    prompt_length_avg: float = 0.0

    commands_used: dict[str, int] = field(default_factory=dict)
    session_stats: list[SessionStats] = field(default_factory=list)

    first_entry_time: str | None = None
    last_entry_time: str | None = None

    def duration_minutes(self) -> float | None:
        """Calculate total duration in minutes if timestamps available."""
        if not self.first_entry_time or not self.last_entry_time:
            return None
        try:
            start = datetime.fromisoformat(self.first_entry_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(self.last_entry_time.replace("Z", "+00:00"))
            return (end - start).total_seconds() / 60
        except (ValueError, TypeError):
            return None


def analyze_log(project_dir: str) -> LogAnalysis | None:
    """
    Analyze the prompt log for a project.

    Args:
        project_dir: Path to the spec project directory

    Returns:
        LogAnalysis with computed metrics, or None if no log exists
    """
    entries = read_log(project_dir)

    if not entries:
        return None

    analysis = LogAnalysis()
    analysis.total_entries = len(entries)

    # Track sessions
    sessions: dict[str, list[LogEntry]] = {}

    # Track prompt lengths for user inputs
    prompt_lengths: list[int] = []

    # Process each entry
    for entry in entries:
        # Count by type
        if entry.entry_type == "user_input":
            analysis.user_inputs += 1
            prompt_lengths.append(len(entry.content))

            # Count questions
            if "?" in entry.content:
                analysis.total_questions += 1

        elif entry.entry_type == "expanded_prompt":
            analysis.expanded_prompts += 1
        elif entry.entry_type == "response_summary":
            analysis.response_summaries += 1

        # Track commands
        if entry.command:
            analysis.commands_used[entry.command] = (
                analysis.commands_used.get(entry.command, 0) + 1
            )

        # Track filtered content (secrets only - no profanity filtering in this plugin)
        if entry.filter_applied and entry.filter_applied.secret_count > 0:
            analysis.secrets_filtered += entry.filter_applied.secret_count
            analysis.total_filtered_content += 1

        # Group by session, use "unknown" for missing/empty session_id
        session_key = entry.session_id if entry.session_id else "unknown"
        if session_key not in sessions:
            sessions[session_key] = []
        sessions[session_key].append(entry)

    # Calculate prompt length stats
    if prompt_lengths:
        analysis.prompt_length_min = min(prompt_lengths)
        analysis.prompt_length_max = max(prompt_lengths)
        analysis.prompt_length_avg = sum(prompt_lengths) / len(prompt_lengths)

    # Analyze sessions
    analysis.session_count = len(sessions)
    if analysis.session_count > 0:
        analysis.avg_entries_per_session = (
            analysis.total_entries / analysis.session_count
        )

    for session_id, session_entries in sessions.items():
        session_questions = sum(
            1
            for e in session_entries
            if "?" in e.content and e.entry_type == "user_input"
        )
        session_filtered = len(
            [
                e
                for e in session_entries
                if e.filter_applied and e.filter_applied.secret_count > 0
            ],
        )

        stats = SessionStats(
            session_id=session_id,
            entry_count=len(session_entries),
            user_inputs=sum(1 for e in session_entries if e.entry_type == "user_input"),
            expanded_prompts=sum(
                1 for e in session_entries if e.entry_type == "expanded_prompt"
            ),
            response_summaries=sum(
                1 for e in session_entries if e.entry_type == "response_summary"
            ),
            questions_asked=session_questions,
            filtered_content=session_filtered,
            start_time=session_entries[0].timestamp if session_entries else None,
            end_time=session_entries[-1].timestamp if session_entries else None,
        )
        analysis.session_stats.append(stats)

        if session_questions > CLARIFICATION_HEAVY_THRESHOLD:
            analysis.clarification_heavy_sessions += 1

    # Set time bounds
    if entries:
        analysis.first_entry_time = entries[0].timestamp
        analysis.last_entry_time = entries[-1].timestamp

    return analysis


def generate_interaction_analysis(analysis: LogAnalysis) -> str:
    """
    Generate markdown content for the Interaction Analysis section of RETROSPECTIVE.md.

    Args:
        analysis: LogAnalysis from analyze_log()

    Returns:
        Markdown string for the retrospective
    """
    lines = []
    lines.append("## Interaction Analysis")
    lines.append("")
    lines.append("*Auto-generated from prompt capture logs*")
    lines.append("")

    # Metrics table
    lines.append("### Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Prompts | {analysis.total_entries} |")
    lines.append(f"| User Inputs | {analysis.user_inputs} |")
    lines.append(f"| Sessions | {analysis.session_count} |")
    lines.append(f"| Avg Prompts/Session | {analysis.avg_entries_per_session:.1f} |")
    lines.append(f"| Questions Asked | {analysis.total_questions} |")

    duration = analysis.duration_minutes()
    if duration:
        lines.append(f"| Total Duration | {duration:.0f} minutes |")

    if analysis.prompt_length_avg > 0:
        lines.append(f"| Avg Prompt Length | {analysis.prompt_length_avg:.0f} chars |")

    lines.append("")

    # Commands used
    if analysis.commands_used:
        lines.append("### Commands Used")
        lines.append("")
        for cmd, count in sorted(analysis.commands_used.items(), key=lambda x: -x[1]):
            lines.append(f"- `{cmd}`: {count} times")
        lines.append("")

    # Filtering stats
    if analysis.total_filtered_content > 0:
        lines.append("### Content Filtering")
        lines.append("")
        lines.append(f"- Secrets filtered: {analysis.secrets_filtered} instances")
        lines.append("")

    # Insights
    lines.append("### Insights")
    lines.append("")

    insights = []

    # High clarification warning
    if analysis.clarification_heavy_sessions > 0:
        insights.append(
            f"**High clarification sessions**: {analysis.clarification_heavy_sessions} session(s) "
            f"had >10 questions, suggesting initial requirements may have been unclear.",
        )

    # Question ratio
    if analysis.user_inputs > 0:
        question_ratio = analysis.total_questions / analysis.user_inputs
        if question_ratio > HIGH_QUESTION_RATIO:
            insights.append(
                f"**Question-heavy interaction**: {question_ratio:.0%} of prompts were questions. "
                "Consider providing more upfront context in future projects.",
            )

    # Session efficiency
    if analysis.session_count > MULTI_SESSION_THRESHOLD:
        insights.append(
            f"**Multiple sessions**: Project required {analysis.session_count} sessions. "
            "Consider breaking down future projects into smaller chunks.",
        )

    # Prompt length
    if analysis.prompt_length_avg < SHORT_PROMPT_THRESHOLD:
        insights.append(
            f"**Short prompts**: Average prompt was under {SHORT_PROMPT_THRESHOLD} characters. "
            "More detailed prompts may reduce back-and-forth.",
        )
    elif analysis.prompt_length_avg > DETAILED_PROMPT_THRESHOLD:
        insights.append(
            f"**Detailed prompts**: Average prompt was over {DETAILED_PROMPT_THRESHOLD} characters. "
            "This level of detail likely improved Claude's understanding.",
        )

    if not insights:
        insights.append("No significant issues detected in interaction patterns.")

    for insight in insights:
        lines.append(f"- {insight}")

    lines.append("")

    # Recommendations
    lines.append("### Recommendations for Future Projects")
    lines.append("")

    recommendations = []

    if analysis.clarification_heavy_sessions > 0:
        recommendations.append(
            "Spend more time on initial requirements gathering before starting implementation.",
        )

    if analysis.total_questions > analysis.user_inputs * EXCESSIVE_QUESTIONS_RATIO:
        recommendations.append(
            "Provide more context in the initial project description.",
        )

    if analysis.session_count > MANY_SESSIONS_THRESHOLD:
        recommendations.append(
            "Consider using /p with more specific scope to reduce session count.",
        )

    if analysis.secrets_filtered > 0:
        recommendations.append(
            "Be mindful of including secrets in prompts - they were filtered but consider avoiding them entirely.",
        )

    if not recommendations:
        recommendations.append(
            "Interaction patterns were efficient. Continue current prompting practices.",
        )

    for rec in recommendations:
        lines.append(f"- {rec}")

    lines.append("")

    return "\n".join(lines)
