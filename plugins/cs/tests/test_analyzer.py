"""
Tests for the log analyzer module.
"""

import json
import os
import sys
import tempfile
import unittest

# Add parent directory for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from analyzers.log_analyzer import analyze_log, generate_interaction_analysis, LogAnalysis
from filters.log_entry import LogEntry, FilterInfo
from filters.log_writer import PROMPT_LOG_FILENAME


class TestAnalyzeLog(unittest.TestCase):
    """Tests for the analyze_log function."""

    def setUp(self):
        """Create a temporary directory for test logs."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_log_entries(self, entries):
        """Helper to write log entries to temp directory."""
        log_path = os.path.join(self.temp_dir, PROMPT_LOG_FILENAME)
        with open(log_path, "w") as f:
            for entry in entries:
                f.write(entry.to_json() + "\n")

    def test_empty_log_returns_none(self):
        """analyze_log should return None for empty/missing log."""
        analysis = analyze_log(self.temp_dir)
        self.assertIsNone(analysis)

    def test_single_entry(self):
        """analyze_log should handle single entry."""
        entry = LogEntry.create(
            session_id="s1",
            entry_type="user_input",
            content="Hello"
        )
        self._write_log_entries([entry])

        analysis = analyze_log(self.temp_dir)

        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.total_entries, 1)
        self.assertEqual(analysis.user_inputs, 1)
        self.assertEqual(analysis.session_count, 1)

    def test_multiple_entries(self):
        """analyze_log should aggregate multiple entries."""
        entries = [
            LogEntry.create(session_id="s1", entry_type="user_input", content="First"),
            LogEntry.create(session_id="s1", entry_type="user_input", content="Second?"),
            LogEntry.create(session_id="s2", entry_type="user_input", content="Third"),
        ]
        self._write_log_entries(entries)

        analysis = analyze_log(self.temp_dir)

        self.assertEqual(analysis.total_entries, 3)
        self.assertEqual(analysis.user_inputs, 3)
        self.assertEqual(analysis.session_count, 2)
        self.assertEqual(analysis.total_questions, 1)  # Only "Second?" has ?

    def test_command_tracking(self):
        """analyze_log should track commands used."""
        entries = [
            LogEntry.create(session_id="s1", entry_type="user_input", content="test", command="/cs:p"),
            LogEntry.create(session_id="s1", entry_type="user_input", content="test", command="/cs:p"),
            LogEntry.create(session_id="s1", entry_type="user_input", content="test", command="/cs:i"),
        ]
        self._write_log_entries(entries)

        analysis = analyze_log(self.temp_dir)

        self.assertEqual(analysis.commands_used["/cs:p"], 2)
        self.assertEqual(analysis.commands_used["/cs:i"], 1)

    def test_secret_filtering_stats(self):
        """analyze_log should count filtered secrets."""
        filter_info = FilterInfo(secret_count=2, secret_types=["aws_key", "openai_key"])
        entries = [
            LogEntry.create(
                session_id="s1",
                entry_type="user_input",
                content="filtered",
                filter_info=filter_info
            ),
        ]
        self._write_log_entries(entries)

        analysis = analyze_log(self.temp_dir)

        self.assertEqual(analysis.total_filtered_content, 1)
        self.assertEqual(analysis.secrets_filtered, 2)

    def test_prompt_length_stats(self):
        """analyze_log should calculate prompt length statistics."""
        entries = [
            LogEntry.create(session_id="s1", entry_type="user_input", content="a" * 10),
            LogEntry.create(session_id="s1", entry_type="user_input", content="b" * 20),
            LogEntry.create(session_id="s1", entry_type="user_input", content="c" * 30),
        ]
        self._write_log_entries(entries)

        analysis = analyze_log(self.temp_dir)

        self.assertEqual(analysis.prompt_length_min, 10)
        self.assertEqual(analysis.prompt_length_max, 30)
        self.assertEqual(analysis.prompt_length_avg, 20.0)

    def test_clarification_heavy_sessions(self):
        """analyze_log should identify clarification-heavy sessions."""
        # Create a session with > 10 questions
        entries = [
            LogEntry.create(session_id="s1", entry_type="user_input", content=f"Question {i}?")
            for i in range(15)
        ]
        self._write_log_entries(entries)

        analysis = analyze_log(self.temp_dir)

        self.assertEqual(analysis.clarification_heavy_sessions, 1)


class TestGenerateInteractionAnalysis(unittest.TestCase):
    """Tests for markdown generation."""

    def test_generates_markdown(self):
        """generate_interaction_analysis should produce valid markdown."""
        analysis = LogAnalysis(
            total_entries=10,
            user_inputs=8,
            session_count=2,
            avg_entries_per_session=5.0,
            total_questions=3
        )

        markdown = generate_interaction_analysis(analysis)

        self.assertIn("## Interaction Analysis", markdown)
        self.assertIn("| Total Prompts | 10 |", markdown)
        self.assertIn("| Sessions | 2 |", markdown)
        self.assertIn("### Insights", markdown)
        self.assertIn("### Recommendations", markdown)

    def test_includes_commands(self):
        """generate_interaction_analysis should include commands used."""
        analysis = LogAnalysis(
            commands_used={"/cs:p": 5, "/cs:i": 3}
        )

        markdown = generate_interaction_analysis(analysis)

        self.assertIn("### Commands Used", markdown)
        self.assertIn("`/cs:p`: 5 times", markdown)
        self.assertIn("`/cs:i`: 3 times", markdown)

    def test_includes_filtering_stats(self):
        """generate_interaction_analysis should include filtering statistics."""
        analysis = LogAnalysis(
            total_filtered_content=3,
            secrets_filtered=5
        )

        markdown = generate_interaction_analysis(analysis)

        self.assertIn("### Content Filtering", markdown)
        self.assertIn("Secrets filtered: 5 instances", markdown)

    def test_short_prompt_insight(self):
        """Should flag short average prompts."""
        analysis = LogAnalysis(
            user_inputs=10,
            prompt_length_avg=30.0
        )

        markdown = generate_interaction_analysis(analysis)

        self.assertIn("Short prompts", markdown)

    def test_detailed_prompt_insight(self):
        """Should note detailed prompts positively."""
        analysis = LogAnalysis(
            user_inputs=10,
            prompt_length_avg=600.0
        )

        markdown = generate_interaction_analysis(analysis)

        self.assertIn("Detailed prompts", markdown)


if __name__ == "__main__":
    unittest.main()
