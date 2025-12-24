"""Tests for log_analyzer module."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from analyzers.log_analyzer import (
    LogAnalysis,
    analyze_log,
    generate_interaction_analysis,
)
from filters.log_entry import LogEntry
from filters.log_writer import append_to_log


class TestLogAnalysis(unittest.TestCase):
    """Tests for LogAnalysis dataclass."""

    def test_duration_minutes_no_timestamps(self):
        """Should return None when no timestamps."""
        analysis = LogAnalysis()
        self.assertIsNone(analysis.duration_minutes())

    def test_duration_minutes_valid_timestamps(self):
        """Should calculate duration correctly."""
        analysis = LogAnalysis(
            first_entry_time="2025-01-01T10:00:00+00:00",
            last_entry_time="2025-01-01T10:30:00+00:00",
        )
        self.assertEqual(analysis.duration_minutes(), 30.0)

    def test_duration_minutes_invalid_timestamps(self):
        """Should return None for invalid timestamps."""
        analysis = LogAnalysis(
            first_entry_time="not-a-timestamp",
            last_entry_time="also-invalid",
        )
        self.assertIsNone(analysis.duration_minutes())


class TestAnalyzeLog(unittest.TestCase):
    """Tests for analyze_log function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_no_log_returns_none(self):
        """Should return None if no log exists."""
        result = analyze_log(self.temp_dir)
        self.assertIsNone(result)

    def test_empty_log_returns_none(self):
        """Should return None for empty log."""
        # Create empty log file
        log_path = Path(self.temp_dir) / ".prompt-log.json"
        log_path.touch()
        result = analyze_log(self.temp_dir)
        self.assertIsNone(result)

    def test_counts_user_inputs(self):
        """Should correctly count user inputs."""
        for i in range(3):
            entry = LogEntry.create(
                session_id="test-session",
                entry_type="user_input",
                content=f"prompt {i}",
            )
            append_to_log(self.temp_dir, entry)

        analysis = analyze_log(self.temp_dir)
        self.assertEqual(analysis.user_inputs, 3)

    def test_counts_expanded_prompts(self):
        """Should correctly count expanded prompts."""
        entry = LogEntry.create(
            session_id="test-session",
            entry_type="expanded_prompt",
            content="expanded content",
        )
        append_to_log(self.temp_dir, entry)

        analysis = analyze_log(self.temp_dir)
        self.assertEqual(analysis.expanded_prompts, 1)

    def test_counts_response_summaries(self):
        """Should correctly count response summaries."""
        entry = LogEntry.create(
            session_id="test-session",
            entry_type="response_summary",
            content="summary content",
        )
        append_to_log(self.temp_dir, entry)

        analysis = analyze_log(self.temp_dir)
        self.assertEqual(analysis.response_summaries, 1)

    def test_counts_questions(self):
        """Should count prompts containing ?."""
        entry1 = LogEntry.create(
            session_id="test-session",
            entry_type="user_input",
            content="Is this a question?",
        )
        entry2 = LogEntry.create(
            session_id="test-session",
            entry_type="user_input",
            content="This is not a question",
        )
        append_to_log(self.temp_dir, entry1)
        append_to_log(self.temp_dir, entry2)

        analysis = analyze_log(self.temp_dir)
        self.assertEqual(analysis.total_questions, 1)

    def test_tracks_commands(self):
        """Should track command usage."""
        entry = LogEntry.create(
            session_id="test-session",
            entry_type="user_input",
            content="/p test",
            command="/p",
        )
        append_to_log(self.temp_dir, entry)

        analysis = analyze_log(self.temp_dir)
        self.assertEqual(analysis.commands_used["/p"], 1)

    def test_clarification_heavy_session(self):
        """Should detect sessions with >10 questions."""
        for i in range(12):
            entry = LogEntry.create(
                session_id="test-session",
                entry_type="user_input",
                content=f"Question {i}?",
            )
            append_to_log(self.temp_dir, entry)

        analysis = analyze_log(self.temp_dir)
        self.assertEqual(analysis.clarification_heavy_sessions, 1)

    def test_multiple_sessions(self):
        """Should track multiple sessions."""
        for session in ["session-1", "session-2", "session-3"]:
            entry = LogEntry.create(
                session_id=session,
                entry_type="user_input",
                content="test prompt",
            )
            append_to_log(self.temp_dir, entry)

        analysis = analyze_log(self.temp_dir)
        self.assertEqual(analysis.session_count, 3)


class TestGenerateInteractionAnalysis(unittest.TestCase):
    """Tests for generate_interaction_analysis function."""

    def test_basic_output(self):
        """Should generate markdown with basic metrics."""
        analysis = LogAnalysis(
            total_entries=10,
            user_inputs=8,
            session_count=2,
            avg_entries_per_session=5.0,
            total_questions=3,
        )
        result = generate_interaction_analysis(analysis)

        self.assertIn("## Interaction Analysis", result)
        self.assertIn("Total Prompts", result)
        self.assertIn("10", result)

    def test_includes_duration(self):
        """Should include duration when timestamps available."""
        analysis = LogAnalysis(
            total_entries=5,
            user_inputs=5,
            session_count=1,
            avg_entries_per_session=5.0,
            total_questions=0,
            first_entry_time="2025-01-01T10:00:00+00:00",
            last_entry_time="2025-01-01T10:30:00+00:00",
        )
        result = generate_interaction_analysis(analysis)
        self.assertIn("30 minutes", result)

    def test_clarification_heavy_insight(self):
        """Should include insight for clarification-heavy sessions."""
        analysis = LogAnalysis(
            total_entries=20,
            user_inputs=20,
            session_count=1,
            avg_entries_per_session=20.0,
            total_questions=15,
            clarification_heavy_sessions=1,
        )
        result = generate_interaction_analysis(analysis)
        self.assertIn("High clarification", result)

    def test_multiple_sessions_insight(self):
        """Should include insight for many sessions."""
        analysis = LogAnalysis(
            total_entries=10,
            user_inputs=10,
            session_count=5,
            avg_entries_per_session=2.0,
            total_questions=0,
        )
        result = generate_interaction_analysis(analysis)
        self.assertIn("Multiple sessions", result)

    def test_no_issues_insight(self):
        """Should include default insight when no issues."""
        analysis = LogAnalysis(
            total_entries=5,
            user_inputs=5,
            session_count=1,
            avg_entries_per_session=5.0,
            total_questions=0,
            prompt_length_avg=100.0,
        )
        result = generate_interaction_analysis(analysis)
        self.assertIn("No significant issues", result)

    def test_clarification_recommendation(self):
        """Should recommend better requirements for clarification-heavy."""
        analysis = LogAnalysis(
            total_entries=20,
            user_inputs=20,
            session_count=1,
            avg_entries_per_session=20.0,
            total_questions=15,
            clarification_heavy_sessions=1,
        )
        result = generate_interaction_analysis(analysis)
        self.assertIn("requirements gathering", result)

    def test_many_sessions_recommendation(self):
        """Should recommend smaller scope for many sessions."""
        analysis = LogAnalysis(
            total_entries=30,
            user_inputs=30,
            session_count=7,
            avg_entries_per_session=4.3,
            total_questions=5,
        )
        result = generate_interaction_analysis(analysis)
        self.assertIn("specific scope", result)

    def test_filtering_stats(self):
        """Should include filtering stats when present."""
        analysis = LogAnalysis(
            total_entries=5,
            user_inputs=5,
            session_count=1,
            avg_entries_per_session=5.0,
            total_questions=0,
            total_filtered_content=2,
            secrets_filtered=3,
        )
        result = generate_interaction_analysis(analysis)
        self.assertIn("Content Filtering", result)
        self.assertIn("Secrets filtered", result)


if __name__ == "__main__":
    unittest.main()
