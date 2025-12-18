"""Pattern extraction module for cs-memory.

This module provides:
- Pattern detection across memories
- Pattern suggestions based on context
- Pattern lifecycle management (promotion, deprecation)
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from .models import Memory, MemoryResult


class PatternType(Enum):
    """Types of patterns that can be detected."""

    SUCCESS = "success"  # Things that worked well
    ANTI_PATTERN = "anti-pattern"  # Things to avoid
    WORKFLOW = "workflow"  # Process patterns
    DECISION = "decision"  # Decision-making patterns
    TECHNICAL = "technical"  # Technical implementation patterns


class PatternStatus(Enum):
    """Lifecycle status of a pattern."""

    CANDIDATE = "candidate"  # Newly detected, needs validation
    VALIDATED = "validated"  # Confirmed by user or multiple occurrences
    PROMOTED = "promoted"  # Actively suggested to users
    DEPRECATED = "deprecated"  # No longer relevant


@dataclass(frozen=True)
class DetectedPattern:
    """Represents a detected pattern."""

    name: str
    pattern_type: PatternType
    description: str
    evidence: tuple[str, ...]  # Memory IDs that support this pattern
    confidence: float  # 0.0 - 1.0
    tags: tuple[str, ...] = field(default_factory=tuple)
    status: PatternStatus = PatternStatus.CANDIDATE
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    occurrence_count: int = 1


@dataclass
class PatternSuggestion:
    """A pattern suggestion for a given context."""

    pattern: DetectedPattern
    relevance_score: float  # 0.0 - 1.0
    context_match: str  # Why this pattern is relevant
    action: str  # What the user should do


class PatternDetector:
    """Detects patterns in memories."""

    def __init__(
        self,
        min_occurrences: int = 2,
        min_confidence: float = 0.6,
    ) -> None:
        """Initialize the pattern detector.

        Args:
            min_occurrences: Minimum occurrences to consider a pattern.
            min_confidence: Minimum confidence score for patterns.
        """
        self._min_occurrences = min_occurrences
        self._min_confidence = min_confidence

        # Keyword patterns for different pattern types
        self._success_keywords = frozenset(
            {
                "worked",
                "success",
                "solved",
                "fixed",
                "improved",
                "faster",
                "better",
                "clean",
                "elegant",
                "efficient",
            }
        )
        self._antipattern_keywords = frozenset(
            {
                "failed",
                "problem",
                "issue",
                "avoid",
                "mistake",
                "wrong",
                "bad",
                "slow",
                "complex",
                "brittle",
            }
        )
        self._workflow_keywords = frozenset(
            {
                "process",
                "workflow",
                "step",
                "first",
                "then",
                "approach",
                "method",
                "technique",
                "practice",
            }
        )
        self._decision_keywords = frozenset(
            {
                "decided",
                "chose",
                "selected",
                "opted",
                "because",
                "reason",
                "trade-off",
                "alternative",
                "vs",
            }
        )

    def detect_patterns(
        self,
        memories: list[Memory | MemoryResult],
        context: str | None = None,
    ) -> list[DetectedPattern]:
        """Detect patterns in a set of memories.

        Args:
            memories: List of memories to analyze.
            context: Optional context for pattern relevance.

        Returns:
            List of detected patterns.
        """
        patterns: list[DetectedPattern] = []

        # Group memories by namespace
        by_namespace: dict[str, list[Memory | MemoryResult]] = defaultdict(list)
        for mem in memories:
            by_namespace[mem.namespace].append(mem)

        # Detect tag co-occurrence patterns
        tag_patterns = self._detect_tag_patterns(memories)
        patterns.extend(tag_patterns)

        # Detect content patterns
        content_patterns = self._detect_content_patterns(memories)
        patterns.extend(content_patterns)

        # Detect namespace patterns
        if "learnings" in by_namespace:
            learning_patterns = self._detect_learning_patterns(
                by_namespace["learnings"]
            )
            patterns.extend(learning_patterns)

        if "blockers" in by_namespace:
            blocker_patterns = self._detect_blocker_patterns(by_namespace["blockers"])
            patterns.extend(blocker_patterns)

        if "decisions" in by_namespace:
            decision_patterns = self._detect_decision_patterns(
                by_namespace["decisions"]
            )
            patterns.extend(decision_patterns)

        # Filter by minimum confidence
        patterns = [p for p in patterns if p.confidence >= self._min_confidence]

        return patterns

    def _detect_tag_patterns(
        self, memories: list[Memory | MemoryResult]
    ) -> list[DetectedPattern]:
        """Detect patterns from tag co-occurrences."""
        patterns: list[DetectedPattern] = []

        # Count tag pairs
        tag_pairs: Counter[tuple[str, str]] = Counter()
        for mem in memories:
            tags = list(mem.tags) if mem.tags else []
            for i, tag1 in enumerate(tags):
                for tag2 in tags[i + 1 :]:
                    sorted_tags = sorted([tag1, tag2])
                    pair: tuple[str, str] = (sorted_tags[0], sorted_tags[1])
                    tag_pairs[pair] += 1

        # Find significant pairs
        for (tag1, tag2), count in tag_pairs.most_common(10):
            if count >= self._min_occurrences:
                patterns.append(
                    DetectedPattern(
                        name=f"Tag association: {tag1} + {tag2}",
                        pattern_type=PatternType.TECHNICAL,
                        description=f"Tags '{tag1}' and '{tag2}' frequently appear together",
                        evidence=tuple(
                            m.id
                            for m in memories
                            if m.tags and tag1 in m.tags and tag2 in m.tags
                        )[:5],
                        confidence=min(count / 5, 1.0),
                        tags=(tag1, tag2),
                        occurrence_count=count,
                    )
                )

        return patterns

    def _detect_content_patterns(
        self, memories: list[Memory | MemoryResult]
    ) -> list[DetectedPattern]:
        """Detect patterns from content analysis."""
        patterns: list[DetectedPattern] = []

        # Extract common phrases
        phrase_counter: Counter[str] = Counter()
        for mem in memories:
            content = mem.content if hasattr(mem, "content") else mem.summary
            phrases = self._extract_phrases(content)
            phrase_counter.update(phrases)

        # Find significant phrases
        for phrase, count in phrase_counter.most_common(10):
            if count >= self._min_occurrences and len(phrase.split()) >= 2:
                pattern_type = self._classify_phrase(phrase)
                patterns.append(
                    DetectedPattern(
                        name=f"Common phrase: {phrase}",
                        pattern_type=pattern_type,
                        description=f"The phrase '{phrase}' appears frequently",
                        evidence=tuple(
                            m.id
                            for m in memories
                            if phrase.lower()
                            in (
                                m.content.lower()
                                if hasattr(m, "content")
                                else m.summary.lower()
                            )
                        )[:5],
                        confidence=min(count / 5, 1.0),
                        occurrence_count=count,
                    )
                )

        return patterns

    def _detect_learning_patterns(
        self, learnings: list[Memory | MemoryResult]
    ) -> list[DetectedPattern]:
        """Detect patterns from learning memories."""
        patterns: list[DetectedPattern] = []

        # Group learnings by tags
        by_tag: dict[str, list[Memory | MemoryResult]] = defaultdict(list)
        for learning in learnings:
            for tag in learning.tags or []:
                by_tag[tag].append(learning)

        # Find domains with multiple learnings
        for tag, tagged_learnings in by_tag.items():
            if len(tagged_learnings) >= self._min_occurrences:
                patterns.append(
                    DetectedPattern(
                        name=f"Learning cluster: {tag}",
                        pattern_type=PatternType.SUCCESS,
                        description=f"Multiple learnings related to '{tag}'",
                        evidence=tuple(mem.id for mem in tagged_learnings[:5]),
                        confidence=min(len(tagged_learnings) / 5, 1.0),
                        tags=(tag,),
                        occurrence_count=len(tagged_learnings),
                    )
                )

        return patterns

    def _detect_blocker_patterns(
        self, blockers: list[Memory | MemoryResult]
    ) -> list[DetectedPattern]:
        """Detect patterns from blocker memories."""
        patterns: list[DetectedPattern] = []

        # Look for recurring blocker types
        blocker_types: Counter[str] = Counter()
        for blocker in blockers:
            content = (
                blocker.content if hasattr(blocker, "content") else blocker.summary
            )
            blocker_type = self._classify_blocker(content)
            blocker_types[blocker_type] += 1

        for blocker_type, count in blocker_types.most_common(5):
            if count >= self._min_occurrences:
                patterns.append(
                    DetectedPattern(
                        name=f"Recurring blocker: {blocker_type}",
                        pattern_type=PatternType.ANTI_PATTERN,
                        description=f"'{blocker_type}' blockers occur frequently",
                        evidence=tuple(
                            b.id
                            for b in blockers
                            if self._classify_blocker(
                                b.content if hasattr(b, "content") else b.summary
                            )
                            == blocker_type
                        )[:5],
                        confidence=min(count / 3, 1.0),
                        tags=("blocker", blocker_type),
                        occurrence_count=count,
                    )
                )

        return patterns

    def _detect_decision_patterns(
        self, decisions: list[Memory | MemoryResult]
    ) -> list[DetectedPattern]:
        """Detect patterns from decision memories."""
        patterns: list[DetectedPattern] = []

        # Look for decision domains with multiple entries
        decision_domains: dict[str, list[Memory | MemoryResult]] = defaultdict(list)
        for decision in decisions:
            for tag in decision.tags or []:
                decision_domains[tag].append(decision)

        for domain, domain_decisions in decision_domains.items():
            if len(domain_decisions) >= self._min_occurrences:
                patterns.append(
                    DetectedPattern(
                        name=f"Decision pattern: {domain}",
                        pattern_type=PatternType.DECISION,
                        description=f"Multiple decisions made in '{domain}' area",
                        evidence=tuple(d.id for d in domain_decisions[:5]),
                        confidence=min(len(domain_decisions) / 3, 1.0),
                        tags=(domain, "decision"),
                        occurrence_count=len(domain_decisions),
                    )
                )

        return patterns

    def _extract_phrases(self, text: str) -> list[str]:
        """Extract meaningful phrases from text."""
        # Normalize text
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)

        # Extract 2-3 word phrases
        words = text.split()
        phrases: list[str] = []

        for i in range(len(words)):
            if i < len(words) - 1:
                phrases.append(f"{words[i]} {words[i + 1]}")
            if i < len(words) - 2:
                phrases.append(f"{words[i]} {words[i + 1]} {words[i + 2]}")

        return phrases

    def _classify_phrase(self, phrase: str) -> PatternType:
        """Classify a phrase into a pattern type."""
        phrase_lower = phrase.lower()

        if any(kw in phrase_lower for kw in self._success_keywords):
            return PatternType.SUCCESS
        if any(kw in phrase_lower for kw in self._antipattern_keywords):
            return PatternType.ANTI_PATTERN
        if any(kw in phrase_lower for kw in self._workflow_keywords):
            return PatternType.WORKFLOW
        if any(kw in phrase_lower for kw in self._decision_keywords):
            return PatternType.DECISION

        return PatternType.TECHNICAL

    def _classify_blocker(self, content: str) -> str:
        """Classify a blocker into a type."""
        content_lower = content.lower()

        if any(
            kw in content_lower for kw in ["api", "endpoint", "request", "response"]
        ):
            return "API"
        if any(kw in content_lower for kw in ["database", "query", "sql", "migration"]):
            return "Database"
        if any(kw in content_lower for kw in ["auth", "permission", "access", "token"]):
            return "Authentication"
        if any(kw in content_lower for kw in ["test", "spec", "assertion", "mock"]):
            return "Testing"
        if any(kw in content_lower for kw in ["deploy", "ci", "pipeline", "build"]):
            return "DevOps"
        if any(
            kw in content_lower for kw in ["type", "typescript", "typing", "interface"]
        ):
            return "Typing"
        if any(kw in content_lower for kw in ["dependency", "package", "version"]):
            return "Dependencies"

        return "General"


class PatternSuggestor:
    """Suggests patterns based on context."""

    def __init__(
        self,
        detector: PatternDetector | None = None,
        max_suggestions: int = 3,
    ) -> None:
        """Initialize the pattern suggestor.

        Args:
            detector: Pattern detector instance.
            max_suggestions: Maximum suggestions to return.
        """
        self._detector = detector or PatternDetector()
        self._max_suggestions = max_suggestions

    def suggest(
        self,
        context: str,
        available_patterns: list[DetectedPattern],
        current_spec: str | None = None,
        current_tags: list[str] | None = None,
    ) -> list[PatternSuggestion]:
        """Suggest patterns based on context.

        Args:
            context: The current context (task description, etc.).
            available_patterns: Patterns that could be suggested.
            current_spec: The current spec being worked on.
            current_tags: Tags relevant to the current work.

        Returns:
            List of pattern suggestions.
        """
        suggestions: list[PatternSuggestion] = []
        context_lower = context.lower()

        for pattern in available_patterns:
            # Skip non-promoted patterns unless they're highly confident
            if (
                pattern.status not in (PatternStatus.PROMOTED, PatternStatus.VALIDATED)
                and pattern.confidence < 0.8
            ):
                continue

            # Calculate relevance
            relevance = self._calculate_relevance(
                pattern, context_lower, current_tags or []
            )

            if relevance > 0.3:  # Minimum relevance threshold
                action = self._generate_action(pattern)
                context_match = self._explain_match(pattern, context_lower)

                suggestions.append(
                    PatternSuggestion(
                        pattern=pattern,
                        relevance_score=relevance,
                        context_match=context_match,
                        action=action,
                    )
                )

        # Sort by relevance and limit
        suggestions.sort(key=lambda s: s.relevance_score, reverse=True)
        return suggestions[: self._max_suggestions]

    def _calculate_relevance(
        self,
        pattern: DetectedPattern,
        context: str,
        tags: list[str],
    ) -> float:
        """Calculate relevance score for a pattern."""
        score = 0.0

        # Tag overlap
        pattern_tags = set(pattern.tags)
        tag_overlap = len(pattern_tags & set(tags))
        if tag_overlap > 0:
            score += 0.3 * (tag_overlap / max(len(pattern_tags), 1))

        # Keyword match in context
        name_words = set(pattern.name.lower().split())
        context_words = set(context.split())
        word_overlap = len(name_words & context_words)
        if word_overlap > 0:
            score += 0.3 * (word_overlap / len(name_words))

        # Pattern confidence contributes
        score += 0.2 * pattern.confidence

        # Occurrence count matters
        score += 0.2 * min(pattern.occurrence_count / 10, 1.0)

        return min(score, 1.0)

    def _generate_action(self, pattern: DetectedPattern) -> str:
        """Generate an action recommendation for a pattern."""
        if pattern.pattern_type == PatternType.SUCCESS:
            return f"Consider applying: {pattern.name}"
        elif pattern.pattern_type == PatternType.ANTI_PATTERN:
            return f"Avoid: {pattern.description}"
        elif pattern.pattern_type == PatternType.WORKFLOW:
            return f"Follow workflow: {pattern.description}"
        elif pattern.pattern_type == PatternType.DECISION:
            return f"Review past decisions: {pattern.description}"
        else:
            return f"Consider: {pattern.name}"

    def _explain_match(self, pattern: DetectedPattern, context: str) -> str:
        """Explain why a pattern matches the context."""
        reasons: list[str] = []

        # Check tag matches
        for tag in pattern.tags:
            if tag.lower() in context:
                reasons.append(f"matches '{tag}'")

        # Check name words
        for word in pattern.name.lower().split():
            if len(word) > 3 and word in context:
                reasons.append(f"relates to '{word}'")

        if reasons:
            return "Pattern " + " and ".join(reasons[:2])
        return "Pattern may be relevant to this context"


class PatternManager:
    """Manages pattern lifecycle."""

    def __init__(
        self,
        detector: PatternDetector | None = None,
        suggestor: PatternSuggestor | None = None,
    ) -> None:
        """Initialize the pattern manager.

        Args:
            detector: Pattern detector instance.
            suggestor: Pattern suggestor instance.
        """
        self._detector = detector or PatternDetector()
        self._suggestor = suggestor or PatternSuggestor(self._detector)
        self._patterns: dict[str, DetectedPattern] = {}

    def detect(self, memories: list[Memory | MemoryResult]) -> list[DetectedPattern]:
        """Detect patterns in memories."""
        return self._detector.detect_patterns(memories)

    def suggest(self, context: str, **kwargs: Any) -> list[PatternSuggestion]:
        """Get pattern suggestions for a context."""
        return self._suggestor.suggest(
            context,
            list(self._patterns.values()),
            **kwargs,
        )

    def register_pattern(self, pattern: DetectedPattern) -> None:
        """Register a detected pattern."""
        key = f"{pattern.pattern_type.value}:{pattern.name}"
        self._patterns[key] = pattern

    def promote_pattern(self, pattern_key: str) -> DetectedPattern | None:
        """Promote a pattern to be actively suggested."""
        if pattern_key in self._patterns:
            old = self._patterns[pattern_key]
            new = DetectedPattern(
                name=old.name,
                pattern_type=old.pattern_type,
                description=old.description,
                evidence=old.evidence,
                confidence=old.confidence,
                tags=old.tags,
                status=PatternStatus.PROMOTED,
                first_seen=old.first_seen,
                last_seen=datetime.now(UTC),
                occurrence_count=old.occurrence_count,
            )
            self._patterns[pattern_key] = new
            return new
        return None

    def deprecate_pattern(self, pattern_key: str) -> DetectedPattern | None:
        """Deprecate a pattern (no longer suggest it)."""
        if pattern_key in self._patterns:
            old = self._patterns[pattern_key]
            new = DetectedPattern(
                name=old.name,
                pattern_type=old.pattern_type,
                description=old.description,
                evidence=old.evidence,
                confidence=old.confidence,
                tags=old.tags,
                status=PatternStatus.DEPRECATED,
                first_seen=old.first_seen,
                last_seen=old.last_seen,
                occurrence_count=old.occurrence_count,
            )
            self._patterns[pattern_key] = new
            return new
        return None

    def get_patterns(
        self,
        pattern_type: PatternType | None = None,
        status: PatternStatus | None = None,
    ) -> list[DetectedPattern]:
        """Get registered patterns, optionally filtered."""
        patterns = list(self._patterns.values())

        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        if status:
            patterns = [p for p in patterns if p.status == status]

        return patterns


# Module-level singleton
_pattern_manager: PatternManager | None = None


def get_pattern_manager() -> PatternManager:
    """Get or create the pattern manager singleton."""
    global _pattern_manager
    if _pattern_manager is None:
        _pattern_manager = PatternManager()
    return _pattern_manager


def reset_pattern_manager() -> None:
    """Reset the pattern manager singleton for testing (ARCH-001).

    This function allows tests to reset the module-level singleton
    to ensure test isolation.
    """
    global _pattern_manager
    _pattern_manager = None
