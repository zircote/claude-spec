"""
Memory injection for SessionStart hook.

Queries RecallService for relevant memories and formats them for
injection into Claude's context at session start.
"""

from __future__ import annotations

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

LOG_PREFIX = "memory_injector"

# Default limits for injection
DEFAULT_MEMORY_LIMIT = 10
DEFAULT_RELEVANCE_THRESHOLD = 0.7  # Euclidean distance threshold


class MemoryInjector:
    """
    Inject relevant memories at session start.

    Queries RecallService for memories matching the current context
    and formats them for injection into Claude's context.
    """

    def __init__(
        self,
        recall_service: RecallService | None = None,
        limit: int = DEFAULT_MEMORY_LIMIT,
    ):
        """
        Initialize the memory injector.

        Args:
            recall_service: RecallService instance (lazy-created if None)
            limit: Maximum number of memories to inject
        """
        self._recall_service = recall_service
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

    def get_session_memories(
        self,
        spec: str | None = None,
        limit: int | None = None,
        namespace: str | None = None,
    ) -> list[MemoryResult]:
        """
        Query relevant memories for session injection.

        Args:
            spec: Specification slug to filter by (optional)
            limit: Maximum memories to return (uses default if None)
            namespace: Specific namespace to query (optional)

        Returns:
            List of MemoryResult objects sorted by relevance
        """
        if self.recall_service is None:
            return []

        limit = limit or self.limit
        memories: list[MemoryResult] = []

        try:
            # Build query based on context
            if spec:
                # Search for memories related to this spec
                query = f"spec:{spec} recent decisions learnings blockers"
            else:
                # General recent memories
                query = "recent important decisions learnings"

            # Query RecallService
            results = self.recall_service.search(
                query=query,
                namespace=namespace,
                spec=spec,
                limit=limit * 2,  # Get more to filter
            )

            # Filter by relevance (lower distance = more relevant)
            for result in results:
                if result.distance <= DEFAULT_RELEVANCE_THRESHOLD:
                    memories.append(result)
                if len(memories) >= limit:
                    break

            # If not enough from semantic search, get recent
            if len(memories) < limit:
                recent = self.recall_service.recent(
                    spec=spec,
                    namespace=namespace,
                    limit=limit - len(memories),
                )
                # Dedupe by ID
                seen_ids = {m.id for m in memories}
                for mem in recent:
                    if mem.id not in seen_ids:
                        # Wrap in MemoryResult if needed
                        from memory.models import MemoryResult

                        if isinstance(mem, MemoryResult):
                            memories.append(mem)
                        else:
                            # Create MemoryResult with neutral distance
                            memories.append(MemoryResult(memory=mem, distance=0.5))
                        seen_ids.add(mem.id)
                        if len(memories) >= limit:
                            break

        except Exception as e:
            sys.stderr.write(f"{LOG_PREFIX}: Error querying memories: {e}\n")

        return memories

    def format_for_context(
        self,
        memories: list[MemoryResult],
        include_content: bool = False,
    ) -> str:
        """
        Format memories as markdown for context injection.

        Args:
            memories: List of MemoryResult objects
            include_content: Whether to include full content (vs summary only)

        Returns:
            Markdown-formatted string for injection
        """
        if not memories:
            return ""

        lines = [
            "## Session Memories",
            "",
            "_Relevant context from previous sessions:_",
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
                content = memory.content[:500]
                if len(memory.content) > 500:
                    content += "..."
                lines.append("")
                lines.append(content)

            lines.append("")

        lines.append(
            "_Use `/cs:recall <query>` for more context or `/cs:context` to load all memories._"
        )

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


def get_memory_injector(
    recall_service: RecallService | None = None,
    limit: int = DEFAULT_MEMORY_LIMIT,
) -> MemoryInjector:
    """
    Factory function for MemoryInjector.

    Args:
        recall_service: Optional RecallService instance
        limit: Maximum memories to inject

    Returns:
        Configured MemoryInjector instance
    """
    return MemoryInjector(recall_service=recall_service, limit=limit)
