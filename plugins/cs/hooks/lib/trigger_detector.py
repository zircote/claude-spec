"""
Trigger phrase detection for memory injection.

Detects memory-related phrases in user prompts and returns matching
memories for context injection.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Add plugin root to path
PLUGIN_ROOT = Path(__file__).parent.parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

if TYPE_CHECKING:
    from memory.models import MemoryResult
    from memory.recall import RecallService

LOG_PREFIX = "trigger_detector"

# Trigger patterns that suggest the user wants memory context
TRIGGER_PATTERNS = [
    re.compile(r"why did we", re.IGNORECASE),
    re.compile(r"what was the decision", re.IGNORECASE),
    re.compile(r"what did we decide", re.IGNORECASE),
    re.compile(r"remind me", re.IGNORECASE),
    re.compile(r"continue (from|where)", re.IGNORECASE),
    re.compile(r"last time", re.IGNORECASE),
    re.compile(r"previous(ly)?", re.IGNORECASE),
    re.compile(r"the blocker", re.IGNORECASE),
    re.compile(r"what happened with", re.IGNORECASE),
    re.compile(r"what (was|were) the", re.IGNORECASE),
    re.compile(r"where (was|were) we", re.IGNORECASE),
    re.compile(r"pick up where", re.IGNORECASE),
    re.compile(r"what did (i|we) learn", re.IGNORECASE),
    re.compile(r"what went wrong", re.IGNORECASE),
    re.compile(r"what was blocking", re.IGNORECASE),
    re.compile(r"recall (the|what)", re.IGNORECASE),
]

# Default limits
DEFAULT_MEMORY_LIMIT = 5
DEFAULT_RELEVANCE_THRESHOLD = 0.8  # More strict than session injection


class TriggerDetector:
    """
    Detect memory trigger phrases in user prompts.

    Matches against predefined patterns that suggest the user wants
    to recall previous context or decisions.
    """

    def __init__(
        self,
        patterns: list[re.Pattern[str]] | None = None,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ):
        """
        Initialize the trigger detector.

        Args:
            patterns: Custom patterns (uses defaults if None)
            threshold: Relevance threshold for memory matching
        """
        self.patterns = patterns or TRIGGER_PATTERNS
        self.threshold = threshold

    def should_inject(self, prompt: str) -> bool:
        """
        Check if prompt contains a memory trigger phrase.

        Args:
            prompt: User's input prompt

        Returns:
            True if a trigger pattern matches
        """
        if not prompt:
            return False

        for pattern in self.patterns:
            if pattern.search(prompt):
                return True
        return False

    def get_trigger_context(self, prompt: str) -> str | None:
        """
        Extract context from the trigger phrase.

        Returns the portion of the prompt that could help with
        semantic search.

        Args:
            prompt: User's input prompt

        Returns:
            Context string for search, or None if no trigger
        """
        if not prompt:
            return None

        # For now, use the full prompt as context
        # Could be enhanced to extract specific entities
        return prompt

    def get_matched_pattern(self, prompt: str) -> str | None:
        """
        Get the pattern that matched (for debugging/logging).

        Args:
            prompt: User's input prompt

        Returns:
            Pattern string that matched, or None
        """
        for pattern in self.patterns:
            match = pattern.search(prompt)
            if match:
                return match.group()
        return None


class TriggerMemoryInjector:
    """
    Inject memories matching trigger phrases.

    Combines trigger detection with RecallService to provide
    relevant memory context.
    """

    def __init__(
        self,
        recall_service: RecallService | None = None,
        detector: TriggerDetector | None = None,
        limit: int = DEFAULT_MEMORY_LIMIT,
    ):
        """
        Initialize the trigger memory injector.

        Args:
            recall_service: RecallService instance (lazy-created if None)
            detector: TriggerDetector instance (uses default if None)
            limit: Maximum memories to return
        """
        self._recall_service = recall_service
        self.detector = detector or TriggerDetector()
        self.limit = limit

    @property
    def recall_service(self) -> RecallService | None:
        """Lazy-load RecallService."""
        if self._recall_service is None:
            try:
                from memory.recall import RecallService

                self._recall_service = RecallService()
            except ImportError as e:
                sys.stderr.write(f"{LOG_PREFIX}: RecallService import error: {e}\n")
                return None
        return self._recall_service

    def process_prompt(
        self,
        prompt: str,
        spec: str | None = None,
    ) -> list[MemoryResult]:
        """
        Process a prompt and return matching memories.

        Args:
            prompt: User's input prompt
            spec: Active specification slug (optional)

        Returns:
            List of matching MemoryResult objects
        """
        # Check for trigger phrase
        if not self.detector.should_inject(prompt):
            return []

        if self.recall_service is None:
            return []

        try:
            # Use prompt as semantic search query
            results = self.recall_service.search(
                query=prompt,
                spec=spec,
                limit=self.limit * 2,  # Get more to filter
            )

            # Filter by relevance threshold
            memories: list[MemoryResult] = []
            for result in results:
                if result.distance <= self.detector.threshold:
                    memories.append(result)
                if len(memories) >= self.limit:
                    break

            if memories:
                matched = self.detector.get_matched_pattern(prompt)
                sys.stderr.write(
                    f"{LOG_PREFIX}: Matched trigger '{matched}', "
                    f"returning {len(memories)} memories\n"
                )

            return memories

        except Exception as e:
            sys.stderr.write(f"{LOG_PREFIX}: Error querying memories: {e}\n")
            return []

    def format_for_additional_context(
        self,
        memories: list[MemoryResult],
        include_content: bool = True,
    ) -> str:
        """
        Format memories for additionalContext output.

        Args:
            memories: List of MemoryResult objects
            include_content: Whether to include full content

        Returns:
            Formatted string for additionalContext
        """
        if not memories:
            return ""

        lines = [
            "## Relevant Memories",
            "",
            "_Context from previous sessions matching your query:_",
            "",
        ]

        for result in memories:
            memory = result.memory if hasattr(result, "memory") else result

            # Format based on namespace
            icon = self._get_namespace_icon(memory.namespace)
            lines.append(f"### {icon} {memory.summary}")
            lines.append(
                f"_[{memory.namespace}] {memory.timestamp.strftime('%Y-%m-%d')}_"
            )

            if include_content and memory.content:
                # Truncate long content
                content = memory.content[:1000]
                if len(memory.content) > 1000:
                    content += "..."
                lines.append("")
                lines.append(content)

            lines.append("")

        return "\n".join(lines)

    def _get_namespace_icon(self, namespace: str) -> str:
        """Get emoji icon for namespace."""
        icons = {
            "decisions": "🎯",
            "learnings": "💡",
            "blockers": "🚧",
            "progress": "📊",
            "patterns": "🔄",
            "reviews": "📝",
            "retrospective": "🔍",
        }
        return icons.get(namespace, "📌")


def get_trigger_detector() -> TriggerDetector:
    """Factory function for TriggerDetector."""
    return TriggerDetector()


def get_trigger_memory_injector(
    recall_service: RecallService | None = None,
    limit: int = DEFAULT_MEMORY_LIMIT,
) -> TriggerMemoryInjector:
    """Factory function for TriggerMemoryInjector."""
    return TriggerMemoryInjector(recall_service=recall_service, limit=limit)
