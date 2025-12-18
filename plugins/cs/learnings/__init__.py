"""
Learning detection and extraction for PostToolUse hook.

This module provides automatic capture of learnable moments from tool execution:
- Error detection and categorization
- Workaround identification
- Discovery recognition
- Deduplication within a session
"""

from .deduplicator import SessionDeduplicator, get_content_hash
from .detector import LearningDetector
from .extractor import extract_learning
from .models import LearningCategory, LearningSeverity, ToolLearning

__all__ = [
    "LearningDetector",
    "ToolLearning",
    "LearningCategory",
    "LearningSeverity",
    "SessionDeduplicator",
    "get_content_hash",
    "extract_learning",
]
