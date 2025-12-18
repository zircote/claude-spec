---
document_type: architecture
project_id: SPEC-2025-12-17-001
version: 1.0.0
last_updated: 2025-12-17T14:00:00Z
status: draft
---

# Hooks Based Git-Native Memory Architecture - Technical Design

## System Overview

This architecture extends the existing cs-memory system with hook-based integration, enabling bidirectional memory flow: automatic capture during tool execution and intelligent injection at session start and on trigger phrases.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Claude Code Session                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐       │
│  │   SessionStart   │    │ UserPromptSubmit │    │   PostToolUse    │       │
│  │      Hook        │    │      Hooks       │    │      Hook        │       │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘       │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐       │
│  │ Memory Injection │    │ Trigger Detector │    │ Learning Capture │       │
│  │   (5-10 items)   │    │ (regex patterns) │    │   (score >0.6)   │       │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘       │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     CaptureAccumulator (In-Memory Queue)             │   │
│  │                     - Mutable, session-scoped                        │   │
│  │                     - add(result), count, by_namespace, summary()    │   │
│  └──────────────────────────────────┬──────────────────────────────────┘    │
│                                     │                                       │
│  ┌──────────────────┐               │                                       │
│  │    Stop Hook     │◄──────────────┘                                       │
│  │  (Queue Flush)   │                                                       │
│  └────────┬─────────┘                                                       │
│           │                                                                 │
└───────────┼─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           cs-memory System                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐       │
│  │  CaptureService  │    │  RecallService   │    │  IndexService    │       │
│  │                  │    │                  │    │                  │       │
│  │  - capture()     │    │  - search()      │    │  - search_vector │       │
│  │  - capture_*()   │    │  - hydrate()     │    │  - get_batch()   │       │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘       │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         GitOps + git notes                           │   │
│  │                    refs/notes/cs/<namespace>                         │   │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Queue strategy | In-memory CaptureAccumulator | Simpler than file-based, reliable with Stop flush |
| Capture threshold | Score ≥0.6 | Balances signal vs noise based on research |
| Memory injection limit | 5-10 memories | Prevents context bloat while providing value |
| Hook timeout | 5s for PostToolUse, 10s for SessionStart | Never block user interaction |

## Component Design

### Component 1: PostToolUse Hook (`post_tool_capture.py`)

**Purpose**: Capture learnable moments from tool execution without blocking.

**Responsibilities**:
- Detect learnable signals (errors, workarounds, discoveries)
- Calculate capture score using heuristics
- Deduplicate against session captures
- Queue captures via CaptureAccumulator

**Interfaces**:
- Input: PostToolUse hook JSON from stdin
- Output: Exit code 0 (never blocks), optional additionalContext

**Technology**: Python 3.11+, uses existing memory module

```python
# post_tool_capture.py structure
class LearningDetector:
    """Detect learnable moments from tool output."""

    def calculate_score(self, tool_name: str, response: dict) -> float:
        """Return 0.0-1.0 capture score."""

    def extract_learning(self, tool_name: str, response: dict) -> ToolLearning | None:
        """Extract structured learning if score >= threshold."""

class LearningCapture:
    """Hook main class - orchestrates detection and queuing."""

    def __init__(self, detector: LearningDetector, queue: CaptureAccumulator):
        ...

    def process(self, hook_input: dict) -> None:
        """Process PostToolUse event, queue learnings."""
```

### Component 2: SessionStart Memory Injection (`session_start.py` extension)

**Purpose**: Inject relevant memories at session start for proactive context.

**Responsibilities**:
- Query RecallService for relevant memories
- Apply memory aging/decay for freshness
- Format memories for context injection
- Limit to 5-10 items

**Interfaces**:
- Extends existing session_start.py
- Adds memory section to context_parts output

```python
# Memory injection extension
class MemoryInjector:
    """Inject relevant memories at session start."""

    def __init__(self, recall_service: RecallService):
        ...

    def get_session_memories(
        self,
        spec: str | None,
        limit: int = 10,
    ) -> list[Memory]:
        """Query and filter relevant memories."""

    def format_for_context(self, memories: list[Memory]) -> str:
        """Format memories as markdown for injection."""
```

### Component 3: Trigger Phrase Detector (`trigger_detector.py`)

**Purpose**: Detect memory-related phrases in user prompts and inject context.

**Responsibilities**:
- Match trigger patterns (why did we, remind me, etc.)
- Query RecallService with prompt as semantic query
- Return additionalContext with matching memories

**Interfaces**:
- New UserPromptSubmit hook (runs after command_detector)
- Input: prompt from hook JSON
- Output: additionalContext with memories or empty

```python
# Trigger detection patterns
TRIGGER_PATTERNS = [
    re.compile(r"why did we", re.I),
    re.compile(r"what was the decision", re.I),
    re.compile(r"remind me", re.I),
    re.compile(r"continue (from|where)", re.I),
    re.compile(r"last time", re.I),
    re.compile(r"previous(ly)?", re.I),
    re.compile(r"the blocker", re.I),
    re.compile(r"what happened with", re.I),
]

class TriggerDetector:
    """Detect memory trigger phrases in prompts."""

    def should_inject(self, prompt: str) -> bool:
        """Check if prompt contains trigger phrase."""

    def get_context_memories(
        self,
        prompt: str,
        recall_service: RecallService,
        limit: int = 5,
    ) -> list[MemoryResult]:
        """Get memories matching prompt semantically."""
```

### Component 4: Memory Queue Flusher (`memory_queue_flusher.py`)

**Purpose**: Flush queued memories to git notes on session Stop.

**Responsibilities**:
- Read queued memories from CaptureAccumulator
- Persist via CaptureService to git notes
- Index for semantic search
- Generate capture summary

**Interfaces**:
- New post-step in STEP_MODULES whitelist
- Triggered by Stop hook via post_command.py

```python
# Memory queue flusher step
class MemoryQueueFlusherStep:
    """Post-step to flush memory queue."""

    def run(self, cwd: str, config: dict) -> StepResult:
        """Flush queued memories and return summary."""
```

## Data Design

### Session State Extension

Extend `.cs-session-state.json` to include memory queue reference:

```json
{
    "command": "cs:i",
    "session_id": "abc123",
    "prompt": "...",
    "memory_queue": {
        "count": 5,
        "namespaces": ["learnings", "blockers"]
    }
}
```

### ToolLearning Model

New model for PostToolUse captures:

```python
@dataclass(frozen=True)
class ToolLearning:
    """Structured learning from tool execution."""
    tool_name: str           # Bash, Read, Write, Edit, WebFetch
    category: str            # error, workaround, discovery, warning
    severity: str            # sev-0 (silent fail), sev-1 (hard fail), sev-2 (recoverable)
    summary: str             # One-line auto-generated summary
    context: str             # What was being attempted
    observation: str         # What actually happened
    exit_code: int | None    # For Bash tools
    output_excerpt: str      # Truncated relevant output (1KB max)
```

### Data Flow

```
PostToolUse Event
       │
       ▼
┌──────────────────────┐
│  LearningDetector    │
│  - Signal detection  │
│  - Score calculation │
└──────────┬───────────┘
           │ score >= 0.6
           ▼
┌──────────────────────┐
│  Deduplication       │
│  - Content hash      │
│  - Session cache     │
└──────────┬───────────┘
           │ not duplicate
           ▼
┌──────────────────────┐
│  Extract Learning    │
│  - Structured data   │
│  - Truncate output   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  CaptureAccumulator  │◄──── In-memory queue
│  - add(result)       │
└──────────┬───────────┘
           │
           ▼ (on Stop)
┌──────────────────────┐
│  CaptureService      │
│  - capture_learning  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  GitOps + Index      │
│  - append_note       │
│  - insert embedding  │
└──────────────────────┘
```

## Hook Registration

### Updated hooks.json

```json
{
  "description": "Lifecycle hooks for claude-spec projects",
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/plugins/cs/hooks/session_start.py",
        "timeout": 10
      }]
    }],
    "UserPromptSubmit": [
      {
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/plugins/cs/hooks/command_detector.py",
          "timeout": 30
        }]
      },
      {
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/plugins/cs/hooks/trigger_detector.py",
          "timeout": 5
        }]
      },
      {
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/plugins/cs/hooks/prompt_capture.py",
          "timeout": 30
        }]
      }
    ],
    "PostToolUse": [{
      "matcher": {"toolName": "^(Bash|Read|Write|Edit|WebFetch)$"},
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/plugins/cs/hooks/post_tool_capture.py",
        "timeout": 5
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/plugins/cs/hooks/post_command.py",
        "timeout": 60
      }]
    }]
  }
}
```

## Security Design

### Secret Filtering

All captured content passes through existing filter_pipeline:

```python
# In post_tool_capture.py
from filters.pipeline import filter_pipeline

def capture_learning(learning: ToolLearning) -> CaptureResult:
    # Filter secrets from output excerpt
    filtered = filter_pipeline(learning.output_excerpt)
    if filtered.secret_count > 0:
        learning = dataclasses.replace(
            learning,
            output_excerpt=filtered.filtered_text
        )
    # Proceed with capture
```

### Path Sanitization

Prevent path traversal in captured content:

```python
def sanitize_paths(content: str) -> str:
    """Remove or redact sensitive paths."""
    # Redact home directory
    content = re.sub(r'/Users/[^/]+', '/Users/[USER]', content)
    # Redact credentials paths
    content = re.sub(r'\.env|credentials|secrets', '[REDACTED]', content)
    return content
```

## Performance Considerations

### Expected Load

- PostToolUse fires: ~50-200 times per session
- Learnable moments: ~5-20% of tool executions
- Actual captures: ~10-50 per session

### Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| Signal detection | <10ms | Fast pattern matching |
| Score calculation | <50ms | Simple heuristics |
| Queue operation | <1ms | In-memory append |
| Total hook time | <100ms | Never noticeable |

### Optimization Strategies

1. **Lazy service initialization**: Don't load embedding model in PostToolUse hook
2. **Deferred indexing**: Queue captures, batch index on Stop
3. **Content truncation**: Limit captured output to 1KB
4. **Pattern caching**: Pre-compile regex patterns

## Reliability & Operations

### Failure Modes

| Failure | Impact | Recovery |
|---------|--------|----------|
| PostToolUse timeout | Learning lost | Silent fail, log to stderr |
| Queue full | Recent learnings lost | LRU eviction, warn user |
| Stop hook fails | Queue not flushed | Persist queue to file as backup |
| RecallService unavailable | No memory injection | Skip injection, proceed without |

### Monitoring

Log to stderr (visible in Claude Code logs):
- Hook execution times
- Capture scores and decisions
- Queue flush statistics

## Testing Strategy

### Unit Testing

```python
# test_learning_detector.py
class TestLearningDetector:
    def test_error_detection(self):
        detector = LearningDetector()
        response = {"exit_code": 1, "stderr": "Error: file not found"}
        score = detector.calculate_score("Bash", response)
        assert score >= 0.6

    def test_noise_filtering(self):
        detector = LearningDetector()
        response = {"exit_code": 0, "stdout": "Build complete"}
        score = detector.calculate_score("Bash", response)
        assert score < 0.6
```

### Integration Testing

```python
# test_hook_integration.py
def test_post_tool_capture_flow(mock_capture_service):
    """Test full PostToolUse capture flow."""
    input_data = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_response": {"exit_code": 1, "stderr": "Error"},
        "cwd": "/project"
    }
    # Run hook
    result = run_hook("post_tool_capture", input_data)
    # Verify queued
    assert mock_capture_service.queue.count == 1
```

## Deployment Considerations

### Environment Requirements

- Python 3.11+ (existing requirement)
- No new dependencies (uses existing cs-memory)

### Configuration

Add to `~/.claude/worktree-manager.config.json`:

```json
{
  "lifecycle": {
    "commands": {
      "*": {
        "postSteps": [
          { "name": "flush-memory-queue", "enabled": true }
        ]
      }
    },
    "postToolCapture": {
      "enabled": true,
      "captureThreshold": 0.6,
      "tools": ["Bash", "Read", "Write", "Edit", "WebFetch"]
    },
    "sessionMemory": {
      "enabled": true,
      "limit": 10,
      "hydrationLevel": "SUMMARY"
    }
  }
}
```

### Rollout Strategy

1. **Phase 1**: PostToolUse hook (error capture only)
2. **Phase 2**: SessionStart memory injection
3. **Phase 3**: Trigger phrase detection
4. **Phase 4**: Full noise filtering and tuning

### Rollback Plan

- Set `CS_TOOL_CAPTURE_ENABLED=false` to disable PostToolUse
- Remove PostToolUse entry from hooks.json
- Disable via config: `postToolCapture.enabled: false`

## Future Considerations

1. **ML-based learning extraction**: Replace heuristics with trained model
2. **Cross-session deduplication**: Check git notes for duplicates
3. **User feedback loop**: Allow rating captured learnings
4. **Configurable trigger phrases**: User-defined patterns
5. **Selective tool capture**: Per-tool enable/disable
