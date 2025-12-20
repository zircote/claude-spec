# Claude Code Execution Prompt: V1 Memory Architecture Expansion

## Prerequisites

This prompt assumes completion of the foundational memory architecture:
- Git notes storage layer (`plugins/cs/memory/storage.py`)
- SQLite-vec index layer (`plugins/cs/memory/index.py`)
- Basic hooks (SessionStart, UserPromptSubmit, PostToolUse, Stop)
- CLI commands (`/remember`, `/recall`, `/memory`)

## Expansion Goals

Transform the basic memory capture into an intelligent system with:
1. **High-precision learning detection** via heuristics engine
2. **Memory quality scoring** with relevance decay
3. **Blocker lifecycle tracking** with resolution suggestions
4. **Pattern extraction** for cross-project knowledge reuse
5. **Deep git-adr integration** for unified decision management

---

## Module 1: Learning Heuristics Engine

Create `plugins/cs/memory/heuristics/` with intelligent learning detection.

### File Structure

```
plugins/cs/memory/heuristics/
├── __init__.py
├── engine.py         # Main HeuristicsEngine class
├── rules.py          # HeuristicRule definitions
├── extractors.py     # Context extraction functions
├── scoring.py        # Confidence scoring logic
└── tools/
    ├── __init__.py
    ├── bash.py       # Bash-specific heuristics
    ├── write.py      # Write-specific heuristics
    └── task.py       # Task (subagent) heuristics
```

### Learning Taxonomy

```python
class LearningCategory(Enum):
    ERROR_RESOLUTION = "error_resolution"
    CONFIGURATION = "configuration"
    PERFORMANCE = "performance"
    COMPATIBILITY = "compatibility"
    SECURITY = "security"
    API_BEHAVIOR = "api_behavior"
    TOOLING = "tooling"
    ARCHITECTURE = "architecture"

class LearningSeverity(Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    HELPFUL = "helpful"
    TRIVIAL = "trivial"
```

### Core Heuristic Rules

Implement these pattern-based rules with weighted scoring:

| Pattern | Category | Weight | Example Match |
|---------|----------|--------|---------------|
| `fixed by \|resolved with` | ERROR_RESOLUTION | 0.9 | "Fixed by adding --force flag" |
| `the issue was` | ERROR_RESOLUTION | 0.85 | "The issue was a missing import" |
| `turns out` | API_BEHAVIOR | 0.7 | "Turns out the API requires auth" |
| `need to set\|configure` | CONFIGURATION | 0.75 | "Need to set DATABASE_URL" |
| `requires version` | COMPATIBILITY | 0.8 | "Requires Python 3.11+" |
| `deprecated\|use instead` | COMPATIBILITY | 0.85 | "Deprecated, use Buffer.from()" |
| `workaround\|hack` | ERROR_RESOLUTION | 0.65 | "Workaround: disable SSL verify" |
| `undocumented\|not in docs` | API_BEHAVIOR | 0.7 | "Undocumented: returns null on empty" |

### Confidence Scoring

Multi-factor confidence calculation:

```python
def calculate_confidence(rule, context, existing_learnings) -> float:
    factors = {
        "rule_weight": rule.weight,                    # 30%
        "context_richness": score_context(context),    # 20%
        "specificity": score_specificity(context),     # 20%
        "actionability": score_actionability(context), # 15%
        "novelty": score_novelty(context, existing),   # 15%
    }
    return weighted_sum(factors)
```

**Specificity Scoring:**
- Penalize vague terms: "it", "this", "something" → 0.3
- Reward: version numbers, env vars, CLI flags, code refs → +0.15 each

**Actionability Scoring:**
- Look for actionable verbs: "add", "set", "use", "run" → 0.9
- Prescriptive language: "should", "must", "need to" → 0.8

### Tool-Specific Analyzers

**Bash Analyzer:**
```python
EXIT_CODE_MAPPINGS = {
    1: ERROR_RESOLUTION,
    126: COMPATIBILITY,    # Permission denied
    127: CONFIGURATION,    # Command not found
    137: PERFORMANCE,      # OOM killed
}
```

**Write Analyzer:**
- Detect config files (`.env`, `config.*`, `*.yaml`)
- Extract workaround comments (`# HACK:`, `# FIXME:`)

---

## Module 2: Memory Quality Scoring

Create `plugins/cs/memory/quality.py` with multi-dimensional scoring.

### Quality Dimensions

```python
@dataclass
class MemoryQuality:
    relevance: float      # Context match (0-1)
    freshness: float      # Time decay (0-1)
    confidence: float     # Extraction confidence (0-1)
    utility: float        # Usage-based (0-1)
    specificity: float    # Detail level (0-1)
    
    @property
    def composite_score(self) -> float:
        weights = [0.35, 0.20, 0.20, 0.15, 0.10]
        return sum(v * w for v, w in zip(self.values(), weights))
```

### Relevance Decay

```python
HALF_LIFE_DAYS = {
    "blocker": 30,
    "progress": 14,
    "learning": 180,
    "decision": 365,
    "pattern": 730,
}

def calculate_freshness(memory_type: str, age_days: int) -> float:
    half_life = HALF_LIFE_DAYS[memory_type]
    return 0.5 ** (age_days / half_life)
```

### Utility Tracking

Create `plugins/cs/memory/utility.py`:

```sql
CREATE TABLE memory_access (
    memory_id TEXT,
    accessed_at DATETIME,
    query TEXT,
    was_useful INTEGER,  -- User feedback
    PRIMARY KEY (memory_id, accessed_at)
);

CREATE TABLE memory_utility (
    memory_id TEXT PRIMARY KEY,
    access_count INTEGER DEFAULT 0,
    useful_count INTEGER DEFAULT 0,
    utility_score REAL DEFAULT 0.5
);
```

---

## Module 3: Blocker Lifecycle Tracking

Create `plugins/cs/memory/blockers.py` with full lifecycle management.

### Blocker States

```python
class BlockerStatus(Enum):
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    WORKAROUND_FOUND = "workaround_found"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"
```

### Blocker Detection Patterns

```python
BLOCKER_INDICATORS = [
    r"blocked|stuck|can't proceed",
    r"fatal|critical error",
    r"dependency.*missing|not found",
    r"permission|access denied",
    r"timeout|timed out",
    r"out of memory|insufficient",
]
```

### Resolution Suggestions

When a blocker is detected:
1. Search index for similar past blockers
2. Filter to those with `status == RESOLVED`
3. Rank by semantic similarity
4. Present top 3 with resolution summaries

### Hook Integration

Update `post_tool_use.py`:
```python
# After learning detection
blocker = tracker.detect_blocker(tool_output, context)
if blocker:
    similar = tracker.find_similar_blockers(blocker.summary)
    # Inject resolution suggestions via additionalContext
```

---

## Module 4: Pattern Extraction Pipeline

Create `plugins/cs/memory/patterns/` for cross-project knowledge.

### Pattern Types

```python
class PatternType(Enum):
    ARCHITECTURAL = "architectural"
    CONFIGURATION = "configuration"
    ERROR_HANDLING = "error_handling"
    TESTING = "testing"
    SECURITY = "security"
    PERFORMANCE = "performance"
```

### Extraction Triggers

Patterns are extracted during `/c` (close-out):

1. Gather all decisions, learnings, blockers for spec
2. Identify generalizable insights (2+ "best practice" signals)
3. Remove project-specific references
4. Merge with existing patterns (boost confidence)
5. Store in `refs/notes/cs/patterns`

### Generalization Rules

```python
def generalize_name(summary: str) -> str:
    # Remove: "our", "my", "the", project-specific slugs
    # Keep: technical terms, action verbs
    ...

def is_generalizable(memory: Memory) -> bool:
    signals = ["best practice", "recommended", "always", "never", "pattern"]
    return sum(1 for s in signals if s in memory.content.lower()) >= 2
```

### Pattern Application

Add to `/p` (planning):
```python
def suggest_patterns(description: str, technologies: list[str]):
    results = index.search(description, namespace="patterns", limit=10)
    # Boost for technology overlap
    # Filter by confidence >= 0.5
    return ranked_patterns[:5]
```

---

## Module 5: git-adr Integration

Create `plugins/cs/memory/adr_bridge.py` for bidirectional sync.

### Decision ↔ ADR Mapping

| claude-spec Decision | git-adr ADR |
|---------------------|-------------|
| `summary` | `title` |
| `content.context` | `Context and Problem Statement` |
| `content.options` | `Considered Options` |
| `content.rationale` | `Decision Outcome` |
| `tags` | `tags` |
| `commit` | `linked_commits` |

### Sync Operations

```python
class ADRBridge:
    def sync_decision_to_adr(self, decision: Memory) -> str:
        """Create/update ADR from decision memory."""
        # Format as MADR
        # Run: git adr new/edit
        # Link: git adr link <id> <commit>
    
    def import_adr_as_decision(self, adr_id: str, spec: str) -> Memory:
        """Import ADR as decision memory."""
        # Run: git adr show <id> --format yaml
        # Convert to Memory
    
    def query_via_adr(self, query: str) -> list[Memory]:
        """Use git-adr AI for natural language queries."""
        # Run: git adr ai ask <query>
        # Convert results to Memories
```

### Unified Search

```python
def unified_search(query: str, include_adrs=True, include_memories=True):
    results = []
    if include_memories:
        results.extend(index.search(query))
    if include_adrs:
        results.extend(adr_bridge.search(query))
    return sorted(results, key=lambda x: x.score, reverse=True)
```

---

## Module 6: Lifecycle Management

Create `plugins/cs/memory/lifecycle.py` for long-term sustainability.

### Archival Policy

```python
@dataclass
class ArchivalPolicy:
    age_thresholds = {
        "progress": 90,
        "blocker": 180,
        "learning": 365,
        "decision": 730,
        "pattern": None,  # Never auto-archive
    }
    min_utility_score = 0.2
    keep_resolved_blockers = True
```

### Commands

Add to `/memory`:
- `gc --dry-run` - Preview archival candidates
- `gc --force` - Execute archival
- `export --spec <slug>` - Export to markdown
- `import --file <path>` - Import from markdown/ADR files

---

## Testing Requirements

### Heuristics Tests

```python
# Test precision/recall targets
def test_learning_detection_precision():
    # Precision >= 85%
    
def test_learning_detection_recall():
    # Recall >= 80%

def test_confidence_calibration():
    # Correlation with actual utility >= 0.7
```

### Integration Tests

```python
def test_blocker_resolution_retrieval():
    # Given seeded resolved blockers
    # When similar blocker detected
    # Then relevant resolution suggested

def test_pattern_extraction_roundtrip():
    # Given completed spec with decisions
    # When close-out runs
    # Then generalizable patterns extracted
```

### Performance Tests

```python
def test_heuristics_latency():
    # p50 <= 50ms
    # p99 <= 200ms
```

---

## Implementation Order

| Week | Module | Key Deliverables |
|------|--------|------------------|
| 1-2 | Heuristics | Engine, 15+ rules, tool analyzers |
| 3 | Quality | Scoring, decay, utility tracking |
| 4 | Blockers | Lifecycle, detection, resolution suggestions |
| 5-6 | Patterns | Types, extraction, application |
| 7 | git-adr | Bridge, sync, unified search |
| 8 | Lifecycle | Archival, export/import, GC |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Learning precision | ≥ 85% |
| Learning recall | ≥ 80% |
| Blocker retrieval accuracy | ≥ 80% |
| Heuristics p99 latency | ≤ 200ms |
| Test coverage | ≥ 85% |

---

## Begin Implementation

Start with Module 1 (Heuristics Engine). Create `plugins/cs/memory/heuristics/engine.py` first, implementing the core `HeuristicsEngine` class with the rule matching system. Write tests alongside.

Reference the V1 Expansion Plan for detailed code examples and the full taxonomy/rules list.
