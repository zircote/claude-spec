# Git-Native Memory Architecture: V1 Expansion Plan

## Overview

This specification defines the V1 expansion of the Git-Native Memory Architecture, building on the foundational implementation with advanced heuristics, quality scoring, cross-repository knowledge transfer, and deeper integration with the git-adr ecosystem.

**Prerequisites**: Completion of Phase 1-4 from the initial implementation plan.

**Version Target**: claude-spec v1.0.0

---

## Expansion Areas

| Area | Priority | Complexity | Value |
|------|----------|------------|-------|
| Learning Heuristics Engine | P0 | High | Critical for automatic capture quality |
| Memory Quality Scoring | P0 | Medium | Enables intelligent retrieval ranking |
| Blocker Detection & Resolution Tracking | P1 | Medium | High-value institutional knowledge |
| Pattern Extraction Pipeline | P1 | High | Cross-project knowledge reuse |
| git-adr Deep Integration | P1 | Medium | Unified decision management |
| Memory Lifecycle Management | P2 | Medium | Long-term sustainability |
| Cross-Repository Knowledge Transfer | P2 | High | Enterprise-scale value |
| Collaborative Memory Merging | P3 | High | Team workflows |

---

## Phase 5: Learning Heuristics Engine

### 5.1 Problem Statement

The initial implementation uses simple keyword matching to detect learnable moments. This produces low-precision results with many false positives (noise) and false negatives (missed insights). A sophisticated heuristics engine is needed to:

1. Accurately identify high-value learning moments
2. Classify learnings by type and severity
3. Extract structured information from unstructured output
4. Filter noise while preserving signal

### 5.2 Learning Taxonomy

Define a hierarchical taxonomy for captured learnings:

```python
# plugins/cs/memory/taxonomy.py
from enum import Enum
from dataclasses import dataclass

class LearningCategory(Enum):
    """Top-level learning categories."""
    ERROR_RESOLUTION = "error_resolution"      # How an error was fixed
    CONFIGURATION = "configuration"            # Config discoveries
    PERFORMANCE = "performance"                # Performance insights
    COMPATIBILITY = "compatibility"            # Version/platform issues
    SECURITY = "security"                      # Security considerations
    API_BEHAVIOR = "api_behavior"              # Undocumented API behaviors
    TOOLING = "tooling"                        # Tool usage patterns
    ARCHITECTURE = "architecture"              # Design insights
    PROCESS = "process"                        # Workflow improvements

class LearningSeverity(Enum):
    """Impact level of the learning."""
    CRITICAL = "critical"    # Would cause production issues
    IMPORTANT = "important"  # Significant time savings
    HELPFUL = "helpful"      # Nice to know
    TRIVIAL = "trivial"      # Minor convenience

@dataclass
class ClassifiedLearning:
    """A learning with full classification."""
    category: LearningCategory
    severity: LearningSeverity
    summary: str
    context: str
    resolution: str | None
    tags: list[str]
    confidence: float  # 0.0 - 1.0 classification confidence
    source_tool: str
    source_output: str
    related_files: list[str]
```

### 5.3 Heuristic Rules Engine

Implement a rule-based engine with weighted scoring:

```python
# plugins/cs/memory/heuristics/engine.py
from dataclasses import dataclass
from typing import Callable
import re

@dataclass
class HeuristicRule:
    """A single heuristic rule for learning detection."""
    name: str
    description: str
    pattern: re.Pattern | Callable[[str], bool]
    category: LearningCategory
    base_severity: LearningSeverity
    weight: float  # 0.0 - 1.0 contribution to confidence
    extract_context: Callable[[str, re.Match | None], dict] | None = None

class HeuristicsEngine:
    """Rule-based learning detection engine."""
    
    def __init__(self):
        self.rules = self._load_rules()
        self.context_extractors = self._load_extractors()
    
    def analyze(
        self,
        tool_name: str,
        tool_input: dict,
        tool_output: str,
        session_context: dict
    ) -> list[ClassifiedLearning]:
        """Analyze tool execution for learnable moments."""
        candidates = []
        
        for rule in self.rules:
            match = self._match_rule(rule, tool_output)
            if match:
                learning = self._extract_learning(
                    rule, match, tool_name, tool_input, tool_output, session_context
                )
                candidates.append(learning)
        
        # Deduplicate and merge overlapping learnings
        merged = self._merge_candidates(candidates)
        
        # Filter by confidence threshold
        return [l for l in merged if l.confidence >= 0.6]
    
    def _load_rules(self) -> list[HeuristicRule]:
        """Load heuristic rules from configuration."""
        return [
            # Error Resolution Rules
            HeuristicRule(
                name="error_fixed_by",
                description="Explicit statement of error resolution",
                pattern=re.compile(
                    r"(?:fixed|resolved|solved)\s+(?:by|with|using)\s+(.+?)(?:\.|$)",
                    re.IGNORECASE
                ),
                category=LearningCategory.ERROR_RESOLUTION,
                base_severity=LearningSeverity.IMPORTANT,
                weight=0.9,
                extract_context=self._extract_fix_context
            ),
            HeuristicRule(
                name="the_issue_was",
                description="Root cause identification",
                pattern=re.compile(
                    r"(?:the\s+)?(?:issue|problem|bug|error)\s+was\s+(.+?)(?:\.|$)",
                    re.IGNORECASE
                ),
                category=LearningCategory.ERROR_RESOLUTION,
                base_severity=LearningSeverity.IMPORTANT,
                weight=0.85
            ),
            HeuristicRule(
                name="turns_out",
                description="Discovery of unexpected behavior",
                pattern=re.compile(
                    r"turns?\s+out\s+(?:that\s+)?(.+?)(?:\.|$)",
                    re.IGNORECASE
                ),
                category=LearningCategory.API_BEHAVIOR,
                base_severity=LearningSeverity.HELPFUL,
                weight=0.7
            ),
            
            # Configuration Rules
            HeuristicRule(
                name="config_required",
                description="Required configuration discovery",
                pattern=re.compile(
                    r"(?:need|require|must)\s+(?:to\s+)?(?:set|configure|add|enable)\s+(.+?)(?:\.|$)",
                    re.IGNORECASE
                ),
                category=LearningCategory.CONFIGURATION,
                base_severity=LearningSeverity.IMPORTANT,
                weight=0.75
            ),
            HeuristicRule(
                name="env_var_required",
                description="Environment variable requirement",
                pattern=re.compile(
                    r"(?:set|export|requires?)\s+([A-Z_][A-Z0-9_]*)\s*=",
                    re.IGNORECASE
                ),
                category=LearningCategory.CONFIGURATION,
                base_severity=LearningSeverity.IMPORTANT,
                weight=0.8
            ),
            
            # Compatibility Rules
            HeuristicRule(
                name="version_requirement",
                description="Version-specific requirement",
                pattern=re.compile(
                    r"(?:requires?|needs?|only\s+works?\s+with)\s+(?:version\s+)?(\d+\.\d+(?:\.\d+)?)",
                    re.IGNORECASE
                ),
                category=LearningCategory.COMPATIBILITY,
                base_severity=LearningSeverity.IMPORTANT,
                weight=0.8
            ),
            HeuristicRule(
                name="deprecated_warning",
                description="Deprecation notice",
                pattern=re.compile(
                    r"(?:deprecated|will\s+be\s+removed|use\s+.+\s+instead)",
                    re.IGNORECASE
                ),
                category=LearningCategory.COMPATIBILITY,
                base_severity=LearningSeverity.IMPORTANT,
                weight=0.85
            ),
            
            # Performance Rules
            HeuristicRule(
                name="performance_improvement",
                description="Performance optimization discovery",
                pattern=re.compile(
                    r"(?:faster|slower|performance|latency|throughput)\s+(?:by|improved|degraded)\s+(.+?)(?:\.|$)",
                    re.IGNORECASE
                ),
                category=LearningCategory.PERFORMANCE,
                base_severity=LearningSeverity.HELPFUL,
                weight=0.7
            ),
            HeuristicRule(
                name="n_plus_one",
                description="N+1 query detection",
                pattern=re.compile(
                    r"n\+1|n \+ 1|multiple\s+queries|query\s+per\s+(?:row|item|record)",
                    re.IGNORECASE
                ),
                category=LearningCategory.PERFORMANCE,
                base_severity=LearningSeverity.IMPORTANT,
                weight=0.9
            ),
            
            # Security Rules
            HeuristicRule(
                name="security_consideration",
                description="Security-related discovery",
                pattern=re.compile(
                    r"(?:security|vulnerab|exploit|injection|xss|csrf|auth)",
                    re.IGNORECASE
                ),
                category=LearningCategory.SECURITY,
                base_severity=LearningSeverity.CRITICAL,
                weight=0.85
            ),
            
            # Workaround Rules
            HeuristicRule(
                name="workaround_found",
                description="Workaround for known issue",
                pattern=re.compile(
                    r"(?:workaround|hack|temporary\s+fix|until\s+.+\s+is\s+fixed)",
                    re.IGNORECASE
                ),
                category=LearningCategory.ERROR_RESOLUTION,
                base_severity=LearningSeverity.HELPFUL,
                weight=0.65
            ),
            
            # API Behavior Rules
            HeuristicRule(
                name="undocumented_behavior",
                description="Undocumented API behavior",
                pattern=re.compile(
                    r"(?:undocumented|not\s+(?:in\s+)?(?:the\s+)?docs?|actually\s+returns?|secretly)",
                    re.IGNORECASE
                ),
                category=LearningCategory.API_BEHAVIOR,
                base_severity=LearningSeverity.HELPFUL,
                weight=0.7
            ),
        ]
```

### 5.4 Context Extractors

Specialized extractors for different learning types:

```python
# plugins/cs/memory/heuristics/extractors.py

class ContextExtractors:
    """Extract structured context from unstructured output."""
    
    @staticmethod
    def extract_error_context(output: str, match: re.Match) -> dict:
        """Extract context around an error resolution."""
        lines = output.split('\n')
        match_line = None
        
        for i, line in enumerate(lines):
            if match.group(0) in line:
                match_line = i
                break
        
        if match_line is None:
            return {"resolution": match.group(1)}
        
        # Extract surrounding context
        start = max(0, match_line - 5)
        end = min(len(lines), match_line + 3)
        
        # Look for error message above
        error_msg = None
        for i in range(match_line - 1, start - 1, -1):
            if re.search(r'error|exception|failed|traceback', lines[i], re.I):
                error_msg = lines[i].strip()
                break
        
        return {
            "resolution": match.group(1),
            "error_message": error_msg,
            "context_lines": lines[start:end],
        }
    
    @staticmethod
    def extract_file_references(output: str) -> list[str]:
        """Extract file paths mentioned in output."""
        # Match common file path patterns
        patterns = [
            r'(?:^|\s)(/[\w\-./]+\.\w+)',           # Unix absolute
            r'(?:^|\s)(\.?\.?/[\w\-./]+\.\w+)',     # Unix relative
            r'(?:^|\s)([A-Z]:\\[\w\-.\\]+\.\w+)',   # Windows
            r'File\s+"([^"]+)"',                     # Python traceback
            r'at\s+([^\s:]+:\d+)',                   # Stack trace
        ]
        
        files = set()
        for pattern in patterns:
            for match in re.finditer(pattern, output):
                files.add(match.group(1))
        
        return list(files)
    
    @staticmethod
    def extract_command_context(tool_input: dict) -> dict:
        """Extract context from Bash tool input."""
        command = tool_input.get("command", "")
        
        return {
            "command": command,
            "is_install": any(pkg in command for pkg in ["pip", "npm", "apt", "brew"]),
            "is_git": command.startswith("git "),
            "is_test": any(t in command for t in ["pytest", "jest", "test", "spec"]),
            "is_build": any(b in command for b in ["make", "build", "compile"]),
        }
```

### 5.5 Confidence Scoring

Multi-factor confidence scoring:

```python
# plugins/cs/memory/heuristics/scoring.py

@dataclass
class ConfidenceFactors:
    """Factors that influence learning confidence."""
    rule_weight: float          # Base rule weight
    context_richness: float     # How much context was extracted
    specificity: float          # How specific vs generic
    actionability: float        # Can someone act on this?
    novelty: float              # Is this a new learning or duplicate?

def calculate_confidence(
    rule: HeuristicRule,
    extracted_context: dict,
    existing_learnings: list[ClassifiedLearning]
) -> float:
    """Calculate confidence score for a candidate learning."""
    
    factors = ConfidenceFactors(
        rule_weight=rule.weight,
        context_richness=_score_context_richness(extracted_context),
        specificity=_score_specificity(extracted_context),
        actionability=_score_actionability(extracted_context),
        novelty=_score_novelty(extracted_context, existing_learnings)
    )
    
    # Weighted combination
    weights = {
        "rule_weight": 0.3,
        "context_richness": 0.2,
        "specificity": 0.2,
        "actionability": 0.15,
        "novelty": 0.15,
    }
    
    score = sum(
        getattr(factors, name) * weight
        for name, weight in weights.items()
    )
    
    return min(1.0, max(0.0, score))

def _score_context_richness(context: dict) -> float:
    """Score based on extracted context completeness."""
    expected_keys = {"resolution", "error_message", "context_lines", "command"}
    present = sum(1 for k in expected_keys if context.get(k))
    return present / len(expected_keys)

def _score_specificity(context: dict) -> float:
    """Score based on how specific the learning is."""
    resolution = context.get("resolution", "")
    
    # Penalize vague resolutions
    vague_patterns = [
        r"^it$", r"^this$", r"^that$", r"^the\s+\w+$",
        r"^something$", r"^somehow$"
    ]
    
    for pattern in vague_patterns:
        if re.match(pattern, resolution, re.I):
            return 0.3
    
    # Reward specific technical terms
    specific_patterns = [
        r'\d+\.\d+',           # Version numbers
        r'[A-Z_]{2,}',         # Constants/env vars
        r'`[^`]+`',            # Code references
        r'--\w+',              # CLI flags
    ]
    
    specificity = 0.5
    for pattern in specific_patterns:
        if re.search(pattern, resolution):
            specificity += 0.15
    
    return min(1.0, specificity)

def _score_actionability(context: dict) -> float:
    """Score based on whether learning is actionable."""
    resolution = context.get("resolution", "")
    
    # Look for actionable verbs
    actionable = [
        r"^(?:add|set|use|change|update|install|remove|configure|enable|disable)",
        r"(?:should|must|need\s+to)",
        r"(?:run|execute|call)",
    ]
    
    for pattern in actionable:
        if re.search(pattern, resolution, re.I):
            return 0.9
    
    return 0.5

def _score_novelty(context: dict, existing: list[ClassifiedLearning]) -> float:
    """Score based on whether this is a new learning."""
    if not existing:
        return 1.0
    
    resolution = context.get("resolution", "").lower()
    
    # Check for semantic similarity with existing learnings
    for learning in existing:
        existing_res = learning.resolution or learning.summary
        if existing_res:
            # Simple overlap check (could use embeddings for better accuracy)
            overlap = len(set(resolution.split()) & set(existing_res.lower().split()))
            if overlap > 3:
                return 0.3
    
    return 1.0
```

### 5.6 Tool-Specific Heuristics

Specialized heuristics for different tool types:

```python
# plugins/cs/memory/heuristics/tools.py

class BashHeuristics:
    """Heuristics specific to Bash tool output."""
    
    EXIT_CODE_PATTERNS = {
        1: LearningCategory.ERROR_RESOLUTION,
        2: LearningCategory.CONFIGURATION,
        126: LearningCategory.COMPATIBILITY,  # Permission denied
        127: LearningCategory.CONFIGURATION,  # Command not found
        137: LearningCategory.PERFORMANCE,    # OOM killed
        139: LearningCategory.ERROR_RESOLUTION,  # Segfault
    }
    
    @classmethod
    def analyze(cls, input_data: dict, output: str, exit_code: int) -> list[dict]:
        """Analyze Bash execution for learnings."""
        learnings = []
        
        # Exit code analysis
        if exit_code != 0 and exit_code in cls.EXIT_CODE_PATTERNS:
            learnings.append({
                "category": cls.EXIT_CODE_PATTERNS[exit_code],
                "trigger": f"exit_code_{exit_code}",
                "context": {"exit_code": exit_code, "command": input_data.get("command")}
            })
        
        # Package installation tracking
        if cls._is_package_install(input_data.get("command", "")):
            learnings.extend(cls._analyze_package_install(input_data, output))
        
        # Test execution analysis
        if cls._is_test_execution(input_data.get("command", "")):
            learnings.extend(cls._analyze_test_output(output))
        
        return learnings
    
    @classmethod
    def _analyze_package_install(cls, input_data: dict, output: str) -> list[dict]:
        """Extract learnings from package installation."""
        learnings = []
        
        # Detect version conflicts
        if re.search(r"conflict|incompatible|requires", output, re.I):
            learnings.append({
                "category": LearningCategory.COMPATIBILITY,
                "severity": LearningSeverity.IMPORTANT,
                "summary": "Package version conflict detected",
                "context": {"output_snippet": output[:500]}
            })
        
        # Detect successful workarounds
        if re.search(r"--force|--legacy-peer-deps|--break-system-packages", input_data.get("command", "")):
            learnings.append({
                "category": LearningCategory.CONFIGURATION,
                "severity": LearningSeverity.HELPFUL,
                "summary": "Required force flag for package installation",
            })
        
        return learnings


class WriteHeuristics:
    """Heuristics specific to Write tool output."""
    
    CONFIG_FILE_PATTERNS = [
        r"\.env",
        r"config\.",
        r"\.ya?ml$",
        r"\.json$",
        r"\.toml$",
        r"settings",
    ]
    
    @classmethod
    def analyze(cls, input_data: dict, output: str) -> list[dict]:
        """Analyze file writes for learnings."""
        learnings = []
        file_path = input_data.get("file_path", "")
        content = input_data.get("content", "")
        
        # Configuration file creation
        if any(re.search(p, file_path, re.I) for p in cls.CONFIG_FILE_PATTERNS):
            learnings.append({
                "category": LearningCategory.CONFIGURATION,
                "severity": LearningSeverity.HELPFUL,
                "summary": f"Configuration established in {file_path}",
                "context": {"file_path": file_path, "content_preview": content[:200]}
            })
        
        # Detect workaround comments
        if re.search(r"#\s*(?:hack|workaround|todo|fixme|xxx)", content, re.I):
            match = re.search(r"#\s*((?:hack|workaround|todo|fixme|xxx)[^\n]*)", content, re.I)
            if match:
                learnings.append({
                    "category": LearningCategory.ERROR_RESOLUTION,
                    "severity": LearningSeverity.HELPFUL,
                    "summary": f"Workaround noted: {match.group(1)[:100]}",
                })
        
        return learnings


class TaskHeuristics:
    """Heuristics specific to Task (subagent) output."""
    
    @classmethod
    def analyze(cls, input_data: dict, output: str) -> list[dict]:
        """Analyze subagent task output for learnings."""
        learnings = []
        task_description = input_data.get("description", "")
        
        # Research task completions often contain valuable findings
        if "research" in task_description.lower():
            learnings.extend(cls._extract_research_findings(output))
        
        # Security audit findings
        if "security" in task_description.lower():
            learnings.extend(cls._extract_security_findings(output))
        
        return learnings
    
    @classmethod
    def _extract_research_findings(cls, output: str) -> list[dict]:
        """Extract learnings from research task output."""
        learnings = []
        
        # Look for recommendation patterns
        rec_patterns = [
            r"recommend(?:ed|ation)?[:\s]+([^\n.]+)",
            r"(?:should|could)\s+use\s+([^\n.]+)",
            r"best\s+(?:practice|approach)[:\s]+([^\n.]+)",
        ]
        
        for pattern in rec_patterns:
            for match in re.finditer(pattern, output, re.I):
                learnings.append({
                    "category": LearningCategory.ARCHITECTURE,
                    "severity": LearningSeverity.HELPFUL,
                    "summary": f"Research finding: {match.group(1)[:100]}",
                })
        
        return learnings
```

---

## Phase 6: Memory Quality Scoring

### 6.1 Quality Dimensions

```python
# plugins/cs/memory/quality.py

@dataclass
class MemoryQuality:
    """Quality assessment for a memory."""
    relevance: float      # How relevant to current context (0-1)
    freshness: float      # Time decay factor (0-1)
    confidence: float     # Extraction confidence (0-1)
    utility: float        # Usage-based score (0-1)
    specificity: float    # How specific vs generic (0-1)
    
    @property
    def composite_score(self) -> float:
        """Weighted composite quality score."""
        weights = {
            "relevance": 0.35,
            "freshness": 0.20,
            "confidence": 0.20,
            "utility": 0.15,
            "specificity": 0.10,
        }
        return sum(
            getattr(self, dim) * weight
            for dim, weight in weights.items()
        )
```

### 6.2 Relevance Decay

Implement time-based and context-based decay:

```python
# plugins/cs/memory/decay.py
import math
from datetime import datetime, timedelta

class RelevanceDecay:
    """Calculate relevance decay over time and context."""
    
    # Half-life in days by memory type
    HALF_LIFE = {
        "blocker": 30,      # Blockers decay quickly (may be resolved)
        "progress": 14,     # Progress is very temporal
        "learning": 180,    # Learnings persist longer
        "decision": 365,    # Decisions are durable
        "pattern": 730,     # Patterns are very durable
    }
    
    @classmethod
    def calculate_freshness(
        cls,
        memory_type: str,
        created_at: datetime,
        last_accessed: datetime | None = None
    ) -> float:
        """Calculate freshness score with exponential decay."""
        now = datetime.utcnow()
        age_days = (now - created_at).days
        
        half_life = cls.HALF_LIFE.get(memory_type, 90)
        
        # Exponential decay: score = 0.5^(age/half_life)
        base_freshness = math.pow(0.5, age_days / half_life)
        
        # Boost if recently accessed
        if last_accessed:
            access_age = (now - last_accessed).days
            if access_age < 7:
                base_freshness = min(1.0, base_freshness * 1.3)
        
        return base_freshness
    
    @classmethod
    def calculate_contextual_relevance(
        cls,
        memory: Memory,
        current_spec: str | None,
        current_files: list[str],
        current_technologies: list[str]
    ) -> float:
        """Calculate relevance based on current context."""
        score = 0.3  # Base relevance
        
        # Same specification boost
        if current_spec and memory.spec == current_spec:
            score += 0.4
        
        # File overlap
        memory_files = set(getattr(memory, 'related_files', []))
        if memory_files & set(current_files):
            score += 0.2
        
        # Technology overlap (from tags)
        memory_tech = set(t.lower() for t in memory.tags)
        if memory_tech & set(t.lower() for t in current_technologies):
            score += 0.1
        
        return min(1.0, score)
```

### 6.3 Utility Tracking

Track memory access patterns:

```python
# plugins/cs/memory/utility.py

class UtilityTracker:
    """Track memory access and usefulness."""
    
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memory_access (
                memory_id TEXT NOT NULL,
                accessed_at DATETIME NOT NULL,
                context TEXT,  -- JSON: what query retrieved this
                was_useful INTEGER DEFAULT NULL,  -- User feedback
                PRIMARY KEY (memory_id, accessed_at)
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memory_utility (
                memory_id TEXT PRIMARY KEY,
                access_count INTEGER DEFAULT 0,
                useful_count INTEGER DEFAULT 0,
                last_accessed DATETIME,
                utility_score REAL DEFAULT 0.5
            )
        """)
    
    def record_access(self, memory_id: str, query: str):
        """Record that a memory was retrieved."""
        self.db.execute(
            "INSERT INTO memory_access (memory_id, accessed_at, context) VALUES (?, ?, ?)",
            (memory_id, datetime.utcnow(), json.dumps({"query": query}))
        )
        self.db.execute("""
            INSERT INTO memory_utility (memory_id, access_count, last_accessed)
            VALUES (?, 1, ?)
            ON CONFLICT(memory_id) DO UPDATE SET
                access_count = access_count + 1,
                last_accessed = excluded.last_accessed
        """, (memory_id, datetime.utcnow()))
        self.db.commit()
    
    def record_usefulness(self, memory_id: str, was_useful: bool):
        """Record user feedback on memory usefulness."""
        self.db.execute("""
            UPDATE memory_access
            SET was_useful = ?
            WHERE memory_id = ? AND accessed_at = (
                SELECT MAX(accessed_at) FROM memory_access WHERE memory_id = ?
            )
        """, (1 if was_useful else 0, memory_id, memory_id))
        
        if was_useful:
            self.db.execute("""
                UPDATE memory_utility
                SET useful_count = useful_count + 1,
                    utility_score = CAST(useful_count + 1 AS REAL) / (access_count + 1)
                WHERE memory_id = ?
            """, (memory_id,))
        
        self.db.commit()
    
    def get_utility_score(self, memory_id: str) -> float:
        """Get utility score for a memory."""
        row = self.db.execute(
            "SELECT utility_score FROM memory_utility WHERE memory_id = ?",
            (memory_id,)
        ).fetchone()
        return row[0] if row else 0.5
```

---

## Phase 7: Blocker Detection & Resolution Tracking

### 7.1 Blocker Lifecycle

```python
# plugins/cs/memory/blockers.py
from enum import Enum

class BlockerStatus(Enum):
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    WORKAROUND_FOUND = "workaround_found"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"

@dataclass
class Blocker:
    """A tracked blocker with full lifecycle."""
    id: str
    spec: str
    summary: str
    description: str
    status: BlockerStatus
    created_at: datetime
    updated_at: datetime
    
    # Investigation history
    attempts: list[dict]  # {"timestamp": ..., "approach": ..., "result": ...}
    
    # Resolution
    resolution: str | None
    resolution_commit: str | None
    workaround: str | None
    
    # Relationships
    related_files: list[str]
    related_errors: list[str]
    blocking_tasks: list[str]

class BlockerTracker:
    """Track blockers through their lifecycle."""
    
    def __init__(self, storage: GitNotesStorage, index: MemoryIndex):
        self.storage = storage
        self.index = index
    
    def detect_blocker(self, tool_output: str, context: dict) -> Blocker | None:
        """Detect a new blocker from tool output."""
        # Look for blocker indicators
        indicators = [
            r"(?:blocked|stuck|can't|cannot|unable to)\s+(?:proceed|continue|complete)",
            r"(?:fatal|critical)\s+error",
            r"(?:dependency|requirement)\s+(?:missing|not found|failed)",
            r"(?:permission|access)\s+denied",
            r"(?:timeout|timed out)",
            r"(?:out of|insufficient)\s+(?:memory|disk|space)",
        ]
        
        for pattern in indicators:
            if re.search(pattern, tool_output, re.I):
                return self._create_blocker(tool_output, pattern, context)
        
        return None
    
    def record_investigation(self, blocker_id: str, approach: str, result: str):
        """Record an investigation attempt."""
        blocker = self._get_blocker(blocker_id)
        blocker.attempts.append({
            "timestamp": datetime.utcnow().isoformat(),
            "approach": approach,
            "result": result,
        })
        blocker.status = BlockerStatus.INVESTIGATING
        blocker.updated_at = datetime.utcnow()
        self._save_blocker(blocker)
    
    def resolve_blocker(
        self,
        blocker_id: str,
        resolution: str,
        commit: str,
        is_workaround: bool = False
    ):
        """Mark a blocker as resolved."""
        blocker = self._get_blocker(blocker_id)
        
        if is_workaround:
            blocker.status = BlockerStatus.WORKAROUND_FOUND
            blocker.workaround = resolution
        else:
            blocker.status = BlockerStatus.RESOLVED
            blocker.resolution = resolution
            blocker.resolution_commit = commit
        
        blocker.updated_at = datetime.utcnow()
        self._save_blocker(blocker)
        
        # Create a learning from the resolution
        self._create_resolution_learning(blocker)
    
    def find_similar_blockers(self, description: str) -> list[Blocker]:
        """Find similar past blockers that may help."""
        # Semantic search in blocker namespace
        results = self.index.search(
            query=description,
            namespace="blockers",
            limit=5
        )
        
        # Filter to resolved blockers with useful resolutions
        return [
            self._memory_to_blocker(m)
            for m, score in results
            if score > 0.7 and self._has_resolution(m)
        ]
```

### 7.2 Blocker Detection Hook Integration

```python
# plugins/cs/hooks/blocker_detection.py
"""PostToolUse hook for blocker detection."""

def main():
    hook_data = json.loads(sys.stdin.read())
    tool_name = hook_data.get("toolName", "")
    tool_output = hook_data.get("toolOutput", "")
    
    # Skip successful operations
    if is_success(tool_name, tool_output):
        sys.exit(0)
    
    tracker = BlockerTracker(GitNotesStorage(), MemoryIndex())
    
    # Check if this looks like a blocker
    blocker = tracker.detect_blocker(tool_output, {
        "tool": tool_name,
        "cwd": hook_data.get("cwd"),
    })
    
    if not blocker:
        sys.exit(0)
    
    # Check for similar past blockers
    similar = tracker.find_similar_blockers(blocker.summary)
    
    context_parts = [f"🚧 Potential blocker detected: {blocker.summary}"]
    
    if similar:
        context_parts.append("\n**Similar past blockers with resolutions:**")
        for past in similar[:3]:
            resolution = past.resolution or past.workaround
            context_parts.append(f"- {past.summary}: {resolution}")
    
    print(json.dumps({
        "additionalContext": "\n".join(context_parts)
    }))
```

---

## Phase 8: Pattern Extraction Pipeline

### 8.1 Pattern Types

```python
# plugins/cs/memory/patterns.py

class PatternType(Enum):
    """Types of extractable patterns."""
    ARCHITECTURAL = "architectural"     # Design patterns used
    CONFIGURATION = "configuration"     # Config patterns that work
    ERROR_HANDLING = "error_handling"   # How errors are handled
    TESTING = "testing"                 # Testing patterns
    DEPLOYMENT = "deployment"           # Deployment patterns
    SECURITY = "security"               # Security patterns
    PERFORMANCE = "performance"         # Performance patterns
    INTEGRATION = "integration"         # Integration patterns

@dataclass
class Pattern:
    """A reusable pattern extracted from project experience."""
    id: str
    type: PatternType
    name: str
    description: str
    context: str              # When to use this pattern
    solution: str             # The pattern implementation
    consequences: str         # Trade-offs and implications
    
    # Provenance
    source_specs: list[str]   # Specs this was extracted from
    source_learnings: list[str]  # Learning IDs that informed this
    confidence: float         # How well-established is this pattern
    
    # Usage
    usage_count: int          # Times this pattern was applied
    success_rate: float       # Success rate when applied
    
    # Metadata
    technologies: list[str]   # Relevant technologies
    tags: list[str]
    created_at: datetime
    updated_at: datetime
```

### 8.2 Pattern Extraction Engine

```python
# plugins/cs/memory/patterns/extraction.py

class PatternExtractor:
    """Extract generalizable patterns from project learnings."""
    
    def __init__(self, storage: GitNotesStorage, index: MemoryIndex):
        self.storage = storage
        self.index = index
    
    def extract_patterns_from_spec(self, spec: str) -> list[Pattern]:
        """Extract patterns from a completed specification."""
        # Gather all learnings and decisions for the spec
        memories = self.storage.list_memories(spec=spec)
        
        # Group by category
        decisions = [m for m in memories if m.type == "decision"]
        learnings = [m for m in memories if m.type == "learning"]
        blockers = [m for m in memories if m.type == "blocker"]
        
        patterns = []
        
        # Extract architectural patterns from decisions
        patterns.extend(self._extract_architectural_patterns(decisions))
        
        # Extract error handling patterns from resolved blockers
        patterns.extend(self._extract_error_patterns(blockers))
        
        # Extract configuration patterns from learnings
        patterns.extend(self._extract_config_patterns(learnings))
        
        # Merge with existing patterns
        patterns = self._merge_with_existing(patterns)
        
        return patterns
    
    def _extract_architectural_patterns(
        self,
        decisions: list[Memory]
    ) -> list[Pattern]:
        """Extract architectural patterns from decisions."""
        patterns = []
        
        for decision in decisions:
            # Check if this decision represents a reusable pattern
            if self._is_generalizable(decision):
                pattern = Pattern(
                    id=f"pattern-{decision.commit[:8]}",
                    type=PatternType.ARCHITECTURAL,
                    name=self._generalize_name(decision.summary),
                    description=self._generalize_description(decision.content),
                    context=self._extract_context(decision),
                    solution=self._extract_solution(decision),
                    consequences=self._extract_consequences(decision),
                    source_specs=[decision.spec],
                    source_learnings=[],
                    confidence=0.7,
                    usage_count=1,
                    success_rate=1.0,
                    technologies=decision.tags,
                    tags=decision.tags,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                patterns.append(pattern)
        
        return patterns
    
    def _is_generalizable(self, memory: Memory) -> bool:
        """Determine if a memory represents a generalizable pattern."""
        # Look for signals of generalizability
        generalizable_signals = [
            r"best practice",
            r"recommended",
            r"standard approach",
            r"pattern",
            r"always",
            r"never",
            r"prefer",
        ]
        
        content = f"{memory.summary} {memory.content}".lower()
        
        signal_count = sum(
            1 for signal in generalizable_signals
            if signal in content
        )
        
        return signal_count >= 2
    
    def _generalize_name(self, summary: str) -> str:
        """Convert specific summary to general pattern name."""
        # Remove project-specific references
        generalized = re.sub(r'\b(our|my|the|this)\s+', '', summary, flags=re.I)
        generalized = re.sub(r'for\s+\w+(-\w+)*\s+', '', generalized)
        return generalized.strip()
    
    def _merge_with_existing(self, new_patterns: list[Pattern]) -> list[Pattern]:
        """Merge new patterns with existing ones, increasing confidence."""
        existing = self._load_existing_patterns()
        
        merged = []
        for new in new_patterns:
            match = self._find_similar_pattern(new, existing)
            if match:
                # Increase confidence and update
                match.confidence = min(1.0, match.confidence + 0.1)
                match.usage_count += 1
                match.source_specs.extend(new.source_specs)
                match.updated_at = datetime.utcnow()
                merged.append(match)
            else:
                merged.append(new)
        
        return merged
```

### 8.3 Pattern Application

```python
# plugins/cs/memory/patterns/application.py

class PatternApplicator:
    """Apply patterns to new specifications."""
    
    def suggest_patterns(
        self,
        spec_description: str,
        technologies: list[str]
    ) -> list[tuple[Pattern, float]]:
        """Suggest applicable patterns for a new spec."""
        # Semantic search in patterns namespace
        results = self.index.search(
            query=spec_description,
            namespace="patterns",
            limit=10
        )
        
        # Filter by technology match
        filtered = []
        for memory, score in results:
            pattern = self._memory_to_pattern(memory)
            
            # Boost score for technology match
            tech_overlap = set(pattern.technologies) & set(technologies)
            if tech_overlap:
                score *= 1.0 + (0.1 * len(tech_overlap))
            
            # Filter by confidence
            if pattern.confidence >= 0.5:
                filtered.append((pattern, score))
        
        return sorted(filtered, key=lambda x: x[1], reverse=True)[:5]
```

---

## Phase 9: git-adr Deep Integration

### 9.1 Unified Decision Storage

```python
# plugins/cs/memory/adr_bridge.py
"""Bridge between claude-spec decisions and git-adr."""

import subprocess
from memory.models import Memory

class ADRBridge:
    """Synchronize decisions with git-adr."""
    
    def __init__(self):
        self._check_git_adr_available()
    
    def _check_git_adr_available(self):
        """Verify git-adr is installed."""
        try:
            subprocess.run(["git", "adr", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("git-adr not installed. Run: pip install git-adr")
    
    def sync_decision_to_adr(self, decision: Memory) -> str:
        """Create or update ADR from decision memory."""
        # Convert decision format to ADR format
        adr_content = self._format_as_adr(decision)
        
        # Check if ADR already exists for this decision
        existing_adr = self._find_existing_adr(decision)
        
        if existing_adr:
            # Update existing ADR
            result = subprocess.run(
                ["git", "adr", "edit", existing_adr, "--content", adr_content],
                capture_output=True,
                text=True
            )
        else:
            # Create new ADR
            result = subprocess.run(
                ["git", "adr", "new", decision.summary, "--content", adr_content],
                capture_output=True,
                text=True
            )
        
        # Link ADR to decision commit
        adr_id = self._extract_adr_id(result.stdout)
        subprocess.run(
            ["git", "adr", "link", adr_id, decision.commit],
            capture_output=True
        )
        
        return adr_id
    
    def import_adr_as_decision(self, adr_id: str, spec: str) -> Memory:
        """Import an ADR as a decision memory."""
        # Get ADR content
        result = subprocess.run(
            ["git", "adr", "show", adr_id, "--format", "yaml"],
            capture_output=True,
            text=True
        )
        
        adr_data = yaml.safe_load(result.stdout)
        
        # Convert to decision memory
        return Memory(
            type="decision",
            spec=spec,
            phase="planning",
            timestamp=adr_data.get("date", datetime.utcnow().isoformat()),
            tags=adr_data.get("tags", []),
            summary=adr_data.get("title", ""),
            commit=adr_data.get("linked_commits", [None])[0] or "HEAD",
            content=self._format_adr_as_decision(adr_data)
        )
    
    def query_decisions_via_adr(self, query: str) -> list[Memory]:
        """Use git-adr's AI Q&A to find relevant decisions."""
        result = subprocess.run(
            ["git", "adr", "ai", "ask", query, "--format", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return []
        
        response = json.loads(result.stdout)
        
        # Convert ADR references to decision memories
        decisions = []
        for adr_ref in response.get("referenced_adrs", []):
            decision = self.import_adr_as_decision(adr_ref["id"], spec="")
            decisions.append(decision)
        
        return decisions
    
    def _format_as_adr(self, decision: Memory) -> str:
        """Format decision memory as MADR content."""
        # Parse decision content
        sections = self._parse_decision_sections(decision.content)
        
        return f"""## Context and Problem Statement

{sections.get('context', 'No context provided.')}

## Decision Drivers

{sections.get('drivers', '* Not specified')}

## Considered Options

{sections.get('options', '* Not specified')}

## Decision Outcome

Chosen option: "{decision.summary}"

{sections.get('rationale', '')}

### Consequences

{sections.get('consequences', '* Not specified')}
"""
```

### 9.2 Unified Search

```python
# plugins/cs/memory/unified_search.py
"""Unified search across memories and ADRs."""

class UnifiedSearch:
    """Search across both memory index and git-adr."""
    
    def __init__(self, index: MemoryIndex, adr_bridge: ADRBridge):
        self.index = index
        self.adr_bridge = adr_bridge
    
    def search(
        self,
        query: str,
        include_adrs: bool = True,
        include_memories: bool = True,
        **filters
    ) -> list[tuple[Memory | dict, float, str]]:
        """
        Unified search returning (item, score, source) tuples.
        Source is 'memory' or 'adr'.
        """
        results = []
        
        if include_memories:
            memory_results = self.index.search(query, **filters)
            results.extend([
                (m, score, "memory")
                for m, score in memory_results
            ])
        
        if include_adrs:
            adr_results = self._search_adrs(query)
            results.extend([
                (adr, score, "adr")
                for adr, score in adr_results
            ])
        
        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def _search_adrs(self, query: str) -> list[tuple[dict, float]]:
        """Search ADRs using git-adr."""
        result = subprocess.run(
            ["git", "adr", "search", query, "--format", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return []
        
        adrs = json.loads(result.stdout)
        return [(adr, adr.get("score", 0.5)) for adr in adrs]
```

---

## Phase 10: Memory Lifecycle Management

### 10.1 Archival Policy

```python
# plugins/cs/memory/lifecycle.py

@dataclass
class ArchivalPolicy:
    """Policy for archiving memories."""
    
    # Age thresholds (days) by memory type
    age_thresholds: dict[str, int] = field(default_factory=lambda: {
        "progress": 90,      # Progress memories archive after 90 days
        "blocker": 180,      # Resolved blockers after 6 months
        "learning": 365,     # Learnings after 1 year
        "decision": 730,     # Decisions after 2 years
        "pattern": None,     # Patterns never auto-archive
    })
    
    # Quality thresholds
    min_utility_score: float = 0.2  # Archive if utility falls below
    min_access_count: int = 0       # Archive if never accessed
    
    # Retention
    keep_resolved_blockers: bool = True  # Keep blockers with resolutions
    keep_high_confidence: bool = True    # Keep high-confidence learnings

class LifecycleManager:
    """Manage memory lifecycle: archival, pruning, export."""
    
    def __init__(
        self,
        storage: GitNotesStorage,
        index: MemoryIndex,
        utility: UtilityTracker,
        policy: ArchivalPolicy
    ):
        self.storage = storage
        self.index = index
        self.utility = utility
        self.policy = policy
    
    def identify_archivable(self) -> list[Memory]:
        """Identify memories eligible for archival."""
        candidates = []
        
        for memory in self.storage.list_memories():
            if self._should_archive(memory):
                candidates.append(memory)
        
        return candidates
    
    def _should_archive(self, memory: Memory) -> bool:
        """Determine if memory should be archived."""
        # Check age threshold
        threshold = self.policy.age_thresholds.get(memory.type)
        if threshold is None:
            return False  # Never archive
        
        age_days = (datetime.utcnow() - memory.timestamp).days
        if age_days < threshold:
            return False
        
        # Check utility
        utility = self.utility.get_utility_score(memory.id)
        if utility < self.policy.min_utility_score:
            return True
        
        # Check special retention rules
        if memory.type == "blocker" and self.policy.keep_resolved_blockers:
            if hasattr(memory, 'resolution') and memory.resolution:
                return False
        
        return True
    
    def archive_memories(
        self,
        memories: list[Memory],
        export_path: str | None = None
    ) -> int:
        """Archive memories, optionally exporting first."""
        if export_path:
            self._export_memories(memories, export_path)
        
        archived = 0
        for memory in memories:
            # Move to archive namespace
            self.storage.move_to_archive(memory)
            # Remove from active index
            self.index.remove(memory.id)
            archived += 1
        
        return archived
    
    def prune_index(self) -> int:
        """Remove orphaned index entries."""
        # Get all memory IDs from notes
        note_ids = set(m.id for m in self.storage.list_memories())
        
        # Get all indexed IDs
        indexed_ids = set(self.index.list_ids())
        
        # Remove orphaned
        orphaned = indexed_ids - note_ids
        for memory_id in orphaned:
            self.index.remove(memory_id)
        
        return len(orphaned)
    
    def gc(self, dry_run: bool = True) -> dict:
        """Garbage collection: archive old, prune orphaned."""
        archivable = self.identify_archivable()
        orphaned_count = len(set(self.index.list_ids()) - set(m.id for m in self.storage.list_memories()))
        
        result = {
            "archivable_count": len(archivable),
            "orphaned_index_entries": orphaned_count,
            "dry_run": dry_run,
        }
        
        if not dry_run:
            result["archived"] = self.archive_memories(archivable)
            result["pruned"] = self.prune_index()
        
        return result
```

### 10.2 Export & Import

```python
# plugins/cs/memory/export.py

class MemoryExporter:
    """Export memories to various formats."""
    
    def export_spec_memories(
        self,
        spec: str,
        format: str = "markdown",
        include_content: bool = True
    ) -> str:
        """Export all memories for a specification."""
        memories = self.storage.list_memories(spec=spec)
        
        if format == "markdown":
            return self._to_markdown(memories, include_content)
        elif format == "json":
            return self._to_json(memories)
        elif format == "yaml":
            return self._to_yaml(memories)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _to_markdown(self, memories: list[Memory], include_content: bool) -> str:
        """Export as markdown document."""
        lines = ["# Project Memory Export\n"]
        
        # Group by type
        by_type = defaultdict(list)
        for m in memories:
            by_type[m.type].append(m)
        
        for mem_type, mems in by_type.items():
            lines.append(f"\n## {mem_type.title()}s\n")
            
            for m in sorted(mems, key=lambda x: x.timestamp):
                lines.append(f"### {m.summary}\n")
                lines.append(f"**Date:** {m.timestamp}")
                lines.append(f"**Tags:** {', '.join(m.tags)}")
                lines.append(f"**Commit:** `{m.commit[:8]}`\n")
                
                if include_content:
                    lines.append(m.content)
                    lines.append("")
        
        return "\n".join(lines)


class MemoryImporter:
    """Import memories from external sources."""
    
    def import_from_markdown(self, content: str, spec: str) -> list[Memory]:
        """Import memories from markdown export."""
        memories = []
        
        # Parse markdown structure
        sections = self._parse_markdown_sections(content)
        
        for section in sections:
            memory = Memory(
                type=self._infer_type(section["heading"]),
                spec=spec,
                phase="imported",
                timestamp=section.get("date", datetime.utcnow().isoformat()),
                tags=section.get("tags", []),
                summary=section["title"],
                commit="HEAD",  # Will be attached to current HEAD
                content=section["content"]
            )
            memories.append(memory)
        
        return memories
    
    def import_from_adr_files(self, adr_dir: str, spec: str) -> list[Memory]:
        """Import from traditional file-based ADR directory."""
        memories = []
        
        for adr_file in Path(adr_dir).glob("*.md"):
            content = adr_file.read_text()
            
            # Parse ADR format
            adr_data = self._parse_adr_file(content)
            
            memory = Memory(
                type="decision",
                spec=spec,
                phase="imported",
                timestamp=adr_data.get("date", datetime.utcnow().isoformat()),
                tags=adr_data.get("tags", []),
                summary=adr_data.get("title", adr_file.stem),
                commit="HEAD",
                content=content
            )
            memories.append(memory)
        
        return memories
```

---

## Phase 11: Cross-Repository Knowledge Transfer

### 11.1 Pattern Federation

```python
# plugins/cs/memory/federation.py
"""Cross-repository pattern sharing."""

@dataclass
class FederatedPattern:
    """A pattern shared across repositories."""
    pattern: Pattern
    source_repo: str
    source_url: str
    imported_at: datetime
    local_adaptations: list[str]

class PatternFederation:
    """Share and import patterns across repositories."""
    
    PATTERN_REMOTE = "pattern-hub"  # Convention for pattern sharing
    
    def __init__(self, storage: GitNotesStorage):
        self.storage = storage
    
    def export_patterns(self, min_confidence: float = 0.8) -> list[Pattern]:
        """Export high-confidence patterns for sharing."""
        all_patterns = self._load_patterns()
        return [p for p in all_patterns if p.confidence >= min_confidence]
    
    def publish_to_hub(self, patterns: list[Pattern], hub_url: str):
        """Publish patterns to a central hub repository."""
        # Create a patterns branch
        branch = "patterns/export"
        
        # Serialize patterns
        patterns_yaml = yaml.dump([asdict(p) for p in patterns])
        
        # Push to hub
        subprocess.run([
            "git", "push", hub_url,
            f"refs/notes/cs/patterns:{branch}"
        ])
    
    def import_from_hub(self, hub_url: str, filter_tags: list[str] = None):
        """Import patterns from a hub repository."""
        # Fetch pattern notes
        subprocess.run([
            "git", "fetch", hub_url,
            "refs/notes/cs/patterns:refs/notes/cs/patterns-import"
        ])
        
        # Parse and filter
        imported = self._parse_imported_patterns()
        
        if filter_tags:
            imported = [
                p for p in imported
                if set(p.tags) & set(filter_tags)
            ]
        
        # Merge with local patterns
        for pattern in imported:
            self._merge_pattern(pattern)
        
        return len(imported)
    
    def discover_patterns(self, query: str) -> list[FederatedPattern]:
        """Search for patterns across federated repositories."""
        # This would integrate with a pattern registry service
        # For now, search local imports
        results = []
        
        for pattern in self._load_patterns():
            if self._matches_query(pattern, query):
                results.append(FederatedPattern(
                    pattern=pattern,
                    source_repo=pattern.source_specs[0] if pattern.source_specs else "local",
                    source_url="",
                    imported_at=pattern.created_at,
                    local_adaptations=[]
                ))
        
        return results
```

---

## Phase 12: Testing & Benchmarking

### 12.1 Heuristics Test Suite

```python
# tests/memory/test_heuristics.py

class TestLearningHeuristics:
    """Test learning detection heuristics."""
    
    @pytest.fixture
    def engine(self):
        return HeuristicsEngine()
    
    # Error Resolution Tests
    
    def test_detects_fixed_by_pattern(self, engine):
        output = "The import error was fixed by adding __init__.py to the package."
        
        results = engine.analyze("Bash", {}, output, {})
        
        assert len(results) == 1
        assert results[0].category == LearningCategory.ERROR_RESOLUTION
        assert "adding __init__.py" in results[0].resolution
    
    def test_detects_the_issue_was_pattern(self, engine):
        output = "After debugging, the issue was a missing CORS header in the response."
        
        results = engine.analyze("Bash", {}, output, {})
        
        assert len(results) == 1
        assert "CORS header" in results[0].summary
    
    def test_detects_turns_out_pattern(self, engine):
        output = "Turns out the API requires pagination even for small datasets."
        
        results = engine.analyze("Bash", {}, output, {})
        
        assert len(results) == 1
        assert results[0].category == LearningCategory.API_BEHAVIOR
    
    # Configuration Tests
    
    def test_detects_env_var_requirement(self, engine):
        output = "You need to set DATABASE_URL=postgres://... before running migrations."
        
        results = engine.analyze("Bash", {}, output, {})
        
        assert len(results) >= 1
        assert any(r.category == LearningCategory.CONFIGURATION for r in results)
    
    # Compatibility Tests
    
    def test_detects_version_requirement(self, engine):
        output = "This feature requires Node.js version 18.0 or higher."
        
        results = engine.analyze("Bash", {}, output, {})
        
        assert len(results) == 1
        assert results[0].category == LearningCategory.COMPATIBILITY
        assert "18.0" in results[0].summary
    
    def test_detects_deprecation_warning(self, engine):
        output = "Warning: Buffer() is deprecated. Use Buffer.from() instead."
        
        results = engine.analyze("Bash", {}, output, {})
        
        assert len(results) == 1
        assert results[0].category == LearningCategory.COMPATIBILITY
    
    # Confidence Scoring Tests
    
    def test_high_confidence_for_specific_resolution(self, engine):
        output = "Fixed by running: pip install cryptography --break-system-packages"
        
        results = engine.analyze("Bash", {"command": "pip install"}, output, {})
        
        assert len(results) >= 1
        assert results[0].confidence >= 0.7
    
    def test_low_confidence_for_vague_resolution(self, engine):
        output = "Fixed it by changing something."
        
        results = engine.analyze("Bash", {}, output, {})
        
        # Should either not detect or have low confidence
        if results:
            assert results[0].confidence < 0.6
    
    # False Positive Tests
    
    def test_ignores_generic_output(self, engine):
        output = "Build successful. All tests passed."
        
        results = engine.analyze("Bash", {}, output, {})
        
        assert len(results) == 0
    
    def test_ignores_help_text(self, engine):
        output = "Usage: git commit [options]\n  --fix  Fix the previous commit"
        
        results = engine.analyze("Bash", {}, output, {})
        
        # Should not trigger on help text containing "fix"
        assert len(results) == 0


class TestBlockerDetection:
    """Test blocker detection and tracking."""
    
    @pytest.fixture
    def tracker(self, storage, index):
        return BlockerTracker(storage, index)
    
    def test_detects_permission_denied(self, tracker):
        output = "Error: Permission denied when accessing /etc/hosts"
        
        blocker = tracker.detect_blocker(output, {"tool": "Bash"})
        
        assert blocker is not None
        assert blocker.status == BlockerStatus.ACTIVE
    
    def test_detects_dependency_missing(self, tracker):
        output = "ModuleNotFoundError: No module named 'cryptography'"
        
        blocker = tracker.detect_blocker(output, {"tool": "Bash"})
        
        assert blocker is not None
        assert "dependency" in blocker.summary.lower() or "missing" in blocker.summary.lower()
    
    def test_finds_similar_resolved_blockers(self, tracker, populated_blockers):
        description = "Cannot connect to PostgreSQL database"
        
        similar = tracker.find_similar_blockers(description)
        
        assert len(similar) > 0
        assert any(b.resolution for b in similar)


class TestPatternExtraction:
    """Test pattern extraction from project learnings."""
    
    @pytest.fixture
    def extractor(self, storage, index):
        return PatternExtractor(storage, index)
    
    def test_extracts_architectural_pattern(self, extractor, spec_with_decisions):
        patterns = extractor.extract_patterns_from_spec("test-spec")
        
        architectural = [p for p in patterns if p.type == PatternType.ARCHITECTURAL]
        assert len(architectural) > 0
    
    def test_generalizes_pattern_name(self, extractor):
        summary = "Use JWT for our user-auth service authentication"
        
        generalized = extractor._generalize_name(summary)
        
        assert "our" not in generalized.lower()
        assert "user-auth" not in generalized.lower()
    
    def test_merges_similar_patterns(self, extractor, existing_patterns):
        new_pattern = Pattern(
            id="new-pattern",
            type=PatternType.ARCHITECTURAL,
            name="Use JWT for authentication",
            # ... (similar to existing)
        )
        
        merged = extractor._merge_with_existing([new_pattern])
        
        # Should merge with existing, not create duplicate
        jwt_patterns = [p for p in merged if "JWT" in p.name]
        assert len(jwt_patterns) == 1
        assert jwt_patterns[0].confidence > 0.7  # Boosted
```

### 12.2 Benchmark Scenarios

```python
# benchmarks/v1_scenarios.py
"""Benchmark scenarios for V1 expansion features."""

V1_BENCHMARK_SCENARIOS = [
    # Heuristics Accuracy
    {
        "id": "heuristics-precision-001",
        "name": "Learning Detection Precision",
        "description": "Measure precision of learning detection",
        "setup": {
            "tool_outputs": [
                {"output": "Fixed by adding --legacy-peer-deps", "expected": True},
                {"output": "Build successful", "expected": False},
                {"output": "The issue was a missing semicolon", "expected": True},
                {"output": "Running tests...", "expected": False},
                {"output": "Turns out you need Python 3.11+", "expected": True},
            ]
        },
        "metrics": {
            "precision": {"min": 0.85},
            "recall": {"min": 0.80},
            "f1_score": {"min": 0.82},
        }
    },
    
    # Confidence Calibration
    {
        "id": "confidence-calibration-001",
        "name": "Confidence Score Calibration",
        "description": "Verify confidence scores correlate with actual utility",
        "setup": {
            "memories_with_feedback": "fixtures/memories_with_feedback.json"
        },
        "metrics": {
            "correlation": {"min": 0.7},  # Confidence vs actual usefulness
        }
    },
    
    # Blocker Resolution
    {
        "id": "blocker-resolution-001",
        "name": "Similar Blocker Retrieval",
        "description": "Test retrieval of similar resolved blockers",
        "setup": {
            "seed_blockers": "fixtures/resolved_blockers.json",
            "test_blockers": [
                {"description": "Cannot connect to database", "should_find": "postgres_connection_fix"},
                {"description": "API rate limit exceeded", "should_find": "rate_limit_workaround"},
            ]
        },
        "metrics": {
            "retrieval_accuracy": {"min": 0.80},
            "resolution_relevance": {"min": 0.75},
        }
    },
    
    # Pattern Quality
    {
        "id": "pattern-quality-001",
        "name": "Extracted Pattern Quality",
        "description": "Evaluate quality of automatically extracted patterns",
        "setup": {
            "completed_specs": "fixtures/completed_specs/",
        },
        "metrics": {
            "generalizability_score": {"min": 0.70},
            "actionability_score": {"min": 0.75},
        }
    },
    
    # Cross-Repo Transfer
    {
        "id": "federation-001",
        "name": "Pattern Federation Roundtrip",
        "description": "Export patterns, import to new repo, verify applicability",
        "setup": {
            "source_repo": "fixtures/repo_with_patterns/",
            "target_repo": "fixtures/empty_repo/",
        },
        "expected": {
            "patterns_exported": {"min": 5},
            "patterns_imported": {"min": 5},
            "applicable_patterns": {"min": 3},
        }
    },
    
    # Performance
    {
        "id": "performance-heuristics-001",
        "name": "Heuristics Engine Performance",
        "description": "Ensure heuristics run within latency budget",
        "setup": {
            "output_size_kb": 100,
            "iterations": 100,
        },
        "metrics": {
            "p50_latency_ms": {"max": 50},
            "p99_latency_ms": {"max": 200},
        }
    },
]
```

---

## Implementation Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1-2 | Learning Heuristics | `heuristics/` module, 15+ rules, tool-specific analyzers |
| 3 | Memory Quality | Quality scoring, relevance decay, utility tracking |
| 4 | Blocker Tracking | Blocker lifecycle, detection hook, resolution tracking |
| 5-6 | Pattern Extraction | Pattern types, extraction engine, application API |
| 7 | git-adr Integration | ADR bridge, unified search, sync workflows |
| 8 | Lifecycle Management | Archival policy, export/import, garbage collection |
| 9 | Federation | Pattern sharing, cross-repo import, discovery |
| 10 | Testing & Benchmarks | Full test suite, benchmark scenarios, documentation |

---

## Success Criteria

### Quantitative

| Metric | Target |
|--------|--------|
| Learning detection precision | ≥ 85% |
| Learning detection recall | ≥ 80% |
| Blocker resolution retrieval accuracy | ≥ 80% |
| Pattern generalizability score | ≥ 70% |
| Heuristics p99 latency | ≤ 200ms |
| Test coverage | ≥ 85% |

### Qualitative

- Developers report finding relevant past blockers before getting stuck
- Pattern suggestions are actionable and applicable
- Decision memory seamlessly syncs with git-adr
- Cross-repository pattern sharing enables knowledge reuse
- Memory lifecycle prevents unbounded growth

---

## Dependencies

### Required

```toml
[project.dependencies]
sqlite-vec = ">=0.1.0"
sentence-transformers = ">=2.2.0"
pyyaml = ">=6.0"

[project.optional-dependencies]
v1 = [
    "git-adr>=0.2.0",  # ADR integration
    "scikit-learn>=1.0",  # Pattern clustering
]
```

### External

- `git-adr` CLI must be installed for ADR integration
- Embedding model (`all-MiniLM-L6-v2`) downloaded on first run

---

## Execution Instructions

1. Complete initial implementation (Phases 1-4) first
2. Create `feature/v1-expansion` branch
3. Implement phases sequentially with tests
4. Run benchmark suite after each phase
5. Document performance characteristics
6. Create PR for review before merging

Use the benchmark suite (`claude-spec-benchmark`) to validate each phase meets success criteria before proceeding.
