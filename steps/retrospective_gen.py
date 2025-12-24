"""
Retrospective generator step - creates RETROSPECTIVE.md from logs.

This step is a post-step for /c that analyzes the prompt log and
generates a retrospective document summarizing the project lifecycle.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .base import LOG_FILE, BaseStep, StepResult, find_latest_completed_project


class RetrospectiveGeneratorStep(BaseStep):
    """Generates retrospective as post-step for /c."""

    name = "generate-retrospective"

    def execute(self) -> StepResult:
        """Execute the retrospective generation step.

        Returns:
            StepResult with retrospective info in data
        """
        cwd_path = Path(self.cwd)

        # ARCH-HIGH-002: Use shared utility for finding completed project
        target_dir = find_latest_completed_project(cwd_path, "retrospective_gen")

        if target_dir is None:
            return StepResult.ok(
                "No completed projects directory found",
                generated=False,
            )

        # Check if RETROSPECTIVE.md already exists
        retro_path = target_dir / "RETROSPECTIVE.md"
        if retro_path.is_file():
            return StepResult.ok(
                "RETROSPECTIVE.md already exists",
                generated=False,
                path=str(retro_path),
            )

        # Try to load and analyze prompt log
        log_file = cwd_path / LOG_FILE
        log_analysis = self._analyze_log(log_file) if log_file.is_file() else None

        # Generate retrospective content
        content = self._generate_retrospective(target_dir, log_analysis)

        try:
            retro_path.write_text(content, encoding="utf-8")
            return StepResult.ok(
                f"Generated RETROSPECTIVE.md in {target_dir.name}/",
                generated=True,
                path=str(retro_path),
            )
        except Exception as e:
            sys.stderr.write(f"retrospective_gen: Error writing file: {e}\n")
            return StepResult.fail(f"Failed to write RETROSPECTIVE.md: {e}")

    def _analyze_log(self, log_path: Path) -> dict[str, Any] | None:
        """Analyze prompt log for retrospective insights.

        Args:
            log_path: Path to the prompt log file
                      Supports both NDJSON format (one JSON object per line)
                      and JSON array format for backwards compatibility

        Returns:
            Analysis dict or None if analysis failed
        """
        try:
            content = log_path.read_text(encoding="utf-8")
            content_stripped = content.strip()

            entries: list[dict[str, Any]] = []

            # Try JSON array format first (backwards compatibility / test format)
            if content_stripped.startswith("["):
                try:
                    parsed = json.loads(content_stripped)
                    if isinstance(parsed, list):
                        entries = parsed
                except json.JSONDecodeError:
                    # If parsing as a JSON array fails, fall back to NDJSON format below.
                    pass

            # Fall back to NDJSON format (production format from log_writer)
            if not entries:
                for line in content.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip malformed lines but continue processing
                        continue

            if not entries:
                return None

            # Basic statistics
            total_entries = len(entries)
            commands_used: dict[str, int] = {}
            timestamps: list[str] = []

            for entry in entries:
                # Count commands
                cmd = entry.get("command")
                if cmd:
                    commands_used[cmd] = commands_used.get(cmd, 0) + 1

                # Collect timestamps
                ts = entry.get("timestamp")
                if ts:
                    timestamps.append(ts)

            # Calculate duration if we have timestamps
            duration = None
            if len(timestamps) >= 2:
                try:
                    # Handle both Zulu time (Z suffix) and explicit timezone offsets
                    first_ts = timestamps[0]
                    last_ts = timestamps[-1]
                    if first_ts.endswith("Z"):
                        first_ts = first_ts[:-1] + "+00:00"
                    if last_ts.endswith("Z"):
                        last_ts = last_ts[:-1] + "+00:00"
                    first = datetime.fromisoformat(first_ts)
                    last = datetime.fromisoformat(last_ts)
                    duration = str(last - first)
                except Exception as e:
                    sys.stderr.write(
                        f"retrospective_gen: Failed to calculate duration: {e}\n",
                    )

            return {
                "total_prompts": total_entries,
                "commands_used": commands_used,
                "duration": duration,
            }

        except Exception as e:
            sys.stderr.write(f"retrospective_gen: Log analysis error: {e}\n")
            return None

    def _generate_retrospective(
        self,
        project_dir: Path,
        log_analysis: dict[str, Any] | None,
    ) -> str:
        """Generate retrospective markdown content.

        Args:
            project_dir: Path to the completed project directory
            log_analysis: Optional log analysis results

        Returns:
            Retrospective markdown content
        """
        project_name = project_dir.name
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d")

        # Read project README for context
        readme_path = project_dir / "README.md"
        project_summary = "No summary available"
        if readme_path.is_file():
            try:
                readme = readme_path.read_text(encoding="utf-8")
                # Extract first paragraph after # heading
                lines = readme.split("\n")
                in_content = False
                for line in lines:
                    if line.startswith("# "):
                        in_content = True
                        continue
                    if in_content and line.strip() and not line.startswith("#"):
                        project_summary = line.strip()
                        break
            except Exception as e:
                sys.stderr.write(
                    f"retrospective_gen: Failed to read {readme_path}: {e}\n",
                )

        # Build retrospective content
        content = f"""---
document_type: retrospective
project: {project_name}
completed: {timestamp}
---

# {project_name} - Retrospective

## Project Summary

{project_summary}

## Timeline

- **Completed**: {timestamp}
"""

        if log_analysis:
            if log_analysis.get("duration"):
                content += f"- **Duration**: {log_analysis['duration']}\n"
            content += (
                f"- **Total Prompts**: {log_analysis.get('total_prompts', 'Unknown')}\n"
            )

        content += """
## What Went Well

<!-- Add items that worked well during this project -->
-

## What Could Be Improved

<!-- Add items that could be improved for future projects -->
-

## Lessons Learned

<!-- Add key insights and learnings from this project -->
-

## Technical Decisions

<!-- Document key technical decisions made during the project -->
"""

        if log_analysis and log_analysis.get("commands_used"):
            content += "\n## Commands Used\n\n"
            for cmd, count in sorted(log_analysis["commands_used"].items()):
                content += f"- `{cmd}`: {count} times\n"

        content += """
## Follow-up Items

<!-- List any follow-up work or related improvements -->
-

---

_This retrospective was auto-generated by claude-spec plugin._
"""

        return content


def run(cwd: str, config: dict[str, Any] | None = None) -> StepResult:
    """Module-level run function for hook integration.

    Args:
        cwd: Current working directory
        config: Optional step configuration

    Returns:
        StepResult from step execution
    """
    step = RetrospectiveGeneratorStep(cwd, config)
    return step.run()
