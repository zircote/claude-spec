# learnings Module Developer Guide

Technical documentation for extending and integrating with the tool learning detection system.

## Overview

The `learnings` module provides automatic capture of learnable moments from tool execution. It detects errors, warnings, workarounds, and discoveries from Claude Code tool output (Bash, Read, Write, etc.) and converts them into structured memories.

```
+-------------------------------------------------------------+
|                   PostToolUse Hook                          |
|  Receives tool_name, response, context                      |
+--------------------------+----------------------------------+
                           |
+--------------------------v----------------------------------+
|                    LearningDetector                         |
|  Pattern matching + scoring -> DetectionResult              |
+--------------------------+----------------------------------+
                           |
                      score >= 0.6?
                           |
+--------------------------v----------------------------------+
|                  SessionDeduplicator                        |
|  LRU cache + content hashing -> DeduplicationResult         |
+--------------------------+----------------------------------+
                           |
                      is_duplicate?
                           |
+--------------------------v----------------------------------+
|                    extract_learning()                       |
|  Secret filter + path sanitize + truncate -> ToolLearning   |
+--------------------------+----------------------------------+
                           |
+--------------------------v----------------------------------+
|                    CaptureService                           |
|  ToolLearning.to_memory_args() -> Memory (git notes)        |
+-------------------------------------------------------------+
```

## Module Reference

### models.py

Frozen dataclasses for domain objects:

```python
from learnings.models import (
    LearningCategory,   # Enum: ERROR, WORKAROUND, DISCOVERY, WARNING
    LearningSeverity,   # Enum: SEV_0 (silent), SEV_1 (hard), SEV_2 (recoverable), SEV_3 (info)
    ToolLearning,       # Structured learning ready for memory capture
    DetectionSignal,    # Single matched pattern with weight
)
```

### Learning Categories

| Category | Description | Example |
|----------|-------------|---------|
| `ERROR` | Command/operation failed | `npm install` with exit code 1 |
| `WORKAROUND` | Recovery or fallback triggered | "falling back to default" in output |
| `DISCOVERY` | New information learned | Version info, config loaded |
| `WARNING` | Non-fatal warning | Deprecation notice |

### Severity Levels

| Severity | Description | Scoring Weight |
|----------|-------------|----------------|
| `SEV_0` | Silent failure - no obvious indication | Highest (dangerous) |
| `SEV_1` | Hard failure - operation completely failed | High |
| `SEV_2` | Recoverable - partial success or recovered | Medium |
| `SEV_3` | Informational - minor or noteworthy | Low |

### detector.py

Pattern-based detection engine:

```python
from learnings.detector import (
    LearningDetector,    # Main detection class
    DetectionResult,     # Score + signals + category/severity
    SignalPattern,       # Pattern definition
    DEFAULT_THRESHOLD,   # 0.6

    # Pre-defined pattern lists
    ERROR_PATTERNS,
    WARNING_PATTERNS,
    DISCOVERY_PATTERNS,
    WORKAROUND_PATTERNS,
    NOISE_PATTERNS,
)
```

### extractor.py

High-level extraction with filtering:

```python
from learnings.extractor import (
    extract_learning,    # Main entry point
    sanitize_paths,      # Redact /Users/xxx paths
    truncate_output,     # Smart truncation (1KB limit)
    generate_summary,    # Auto-generate 100-char summary
)
```

### deduplicator.py

Session-scoped deduplication:

```python
from learnings.deduplicator import (
    SessionDeduplicator,          # LRU cache for hashes
    DeduplicationResult,          # is_duplicate, hash, hit_count
    get_content_hash,             # SHA256[:16] of content
    get_learning_hash,            # Hash combining tool+exit+output
    get_session_deduplicator,     # Global singleton
    reset_session_deduplicator,   # Reset on session start
)
```

## Detection System

### How Scoring Works

The detector calculates a score (0.0-1.0) based on pattern matches:

1. **Signal Detection**: Each matched pattern contributes its weight to the score
2. **Weight Summation**: Weights are summed and capped at 1.0
3. **Noise Reduction**: Common non-learnable output reduces the score (up to 0.3)
4. **Threshold Check**: Score >= 0.6 triggers capture

```python
detector = LearningDetector()
result = detector.detect("Bash", {"stderr": "error: file not found", "exit_code": 1})

print(result.score)            # 0.9 (exit_nonzero:0.5 + file_not_found:0.4)
print(result.should_capture)   # True (0.9 >= 0.6)
print(result.primary_category) # "error"
print(result.primary_severity) # "sev-1"
```

### Built-in Signal Patterns

Patterns are organized by category in `detector.py`:

**ERROR_PATTERNS** (high weight):
- `exit_nonzero` (0.4): Non-zero exit code
- `error_keyword` (0.3): "error", "failed", "fatal", etc.
- `command_not_found` (0.5): Command not in PATH
- `permission_error` (0.5): Access denied, EACCES
- `file_not_found` (0.4): ENOENT, "no such file"
- `syntax_error` (0.5): Parse/syntax errors
- `type_error` (0.5): TypeError, AttributeError, etc.
- `import_error` (0.5): ModuleNotFoundError
- `connection_error` (0.5): Connection refused/timeout
- `timeout` (0.4): Operation timeout

**WARNING_PATTERNS** (medium weight):
- `warning_keyword` (0.25): "warning", "deprecated"
- `experimental_feature` (0.2): "experimental", "unstable"

**DISCOVERY_PATTERNS** (low weight):
- `version_info` (0.15): Version numbers
- `config_loaded` (0.15): Configuration detected

**WORKAROUND_PATTERNS** (medium weight):
- `retry_success` (0.3): Retry behavior detected
- `fallback` (0.35): Fallback triggered

**NOISE_PATTERNS** (reduce score):
- Simple success messages ("ok", "done")
- Empty lines
- Markdown headers
- Test passed messages
- Build succeeded messages
- INFO log levels

### Silent Failure Detection (SEV-0)

The detector identifies silent failures - the most dangerous type:

```python
# Exit code non-zero but no output = silent failure
response = {"exit_code": 1, "stdout": "", "stderr": ""}
result = detector.detect("Bash", response)

# Signal indicates SEV-0 (silent)
print(result.primary_severity)  # "sev-0"
```

## Adding New Signal Patterns

### Step 1: Define the Pattern

Add a new `SignalPattern` to the appropriate list in `detector.py`:

```python
# In ERROR_PATTERNS list
SignalPattern(
    name="disk_full",                    # Unique identifier
    pattern=re.compile(
        r"no space left on device|ENOSPC|disk full",
        re.IGNORECASE,
    ),
    weight=0.5,                          # Contribution to score (0.0-1.0)
    category=LearningCategory.ERROR,     # Category assignment
    severity=LearningSeverity.SEV_1,     # Severity assignment
    description="Disk space exhausted",  # Human-readable description
),
```

### Step 2: Pattern Design Guidelines

1. **Use anchors sparingly**: Most patterns should match anywhere in output
2. **Case insensitivity**: Use `re.IGNORECASE` for most patterns
3. **Word boundaries**: Use `\b` to avoid partial matches
4. **Weight calibration**:
   - 0.5: Strong signal (alone should trigger capture with some other signal)
   - 0.3-0.4: Medium signal (needs 2+ signals to trigger)
   - 0.1-0.2: Weak signal (informational, needs multiple)
5. **Test with real output**: Verify against actual tool output

### Step 3: Add Tests

```python
# tests/learnings/test_detector.py

def test_disk_full_pattern():
    """Test disk full error detection."""
    detector = LearningDetector()

    # Test with typical error message
    result = detector.detect("Bash", {
        "stderr": "cp: error writing '/tmp/file': No space left on device",
        "exit_code": 1,
    })

    assert result.score >= 0.6
    assert result.primary_category == "error"
    assert any(s.pattern_name == "disk_full" for s in result.signals)


def test_disk_full_enospc():
    """Test ENOSPC variant."""
    detector = LearningDetector()

    result = detector.detect("Bash", {
        "stderr": "write: ENOSPC",
        "exit_code": 1,
    })

    assert result.score >= 0.6
```

### Step 4: Consider Noise Patterns

If your pattern might trigger on routine output, add a corresponding noise pattern:

```python
# In NOISE_PATTERNS list (reduces score)
re.compile(r"^disk usage: \d+%", re.MULTILINE),  # Ignore disk usage reports
```

## Deduplication System

### How It Works

The deduplicator prevents capturing the same learning multiple times within a session:

1. **Hash Generation**: Content is normalized (lowercase, stripped, truncated) and hashed with SHA256
2. **LRU Cache**: Hashes are stored in an OrderedDict with max 100 entries
3. **Hit Tracking**: Duplicate hits are counted for statistics

```python
dedup = SessionDeduplicator()

# First occurrence - not duplicate
result1 = dedup.check_learning("Bash", 1, "error: file not found")
print(result1.is_duplicate)  # False
print(result1.content_hash)  # "a1b2c3d4e5f6g7h8"

# Same error again - duplicate
result2 = dedup.check_learning("Bash", 1, "error: file not found")
print(result2.is_duplicate)  # True
print(result2.hit_count)     # 2
```

### Hash Components

The learning hash combines:
- Tool name (lowercase)
- Exit code (or "none")
- First 500 chars of output (normalized)

```python
# These produce the same hash:
get_learning_hash("Bash", 1, "error: file not found")
get_learning_hash("bash", 1, "  ERROR: FILE NOT FOUND  ")  # Normalized
```

### Session Lifecycle

```python
from learnings.deduplicator import (
    get_session_deduplicator,
    reset_session_deduplicator,
)

# SessionStart hook should reset
reset_session_deduplicator()

# Get singleton for use
dedup = get_session_deduplicator()

# Check stats
stats = dedup.get_stats()
print(stats)
# {
#     "cache_size": 42,
#     "max_size": 100,
#     "unique_hashes": 42,
#     "duplicate_hits": 15,
#     "duplicate_patterns": 8,
# }
```

### LRU Eviction

When cache exceeds max_size (default 100), oldest entries are evicted:

```python
dedup = SessionDeduplicator(max_size=3)

dedup.check("hash1")
dedup.check("hash2")
dedup.check("hash3")
dedup.check("hash4")  # Evicts "hash1"

print(dedup.is_duplicate("hash1"))  # False (evicted)
print(dedup.is_duplicate("hash2"))  # True (still cached)
```

## Integration with Memory System

### ToolLearning to Memory Conversion

The `ToolLearning.to_memory_args()` method converts to `CaptureService.capture_learning()` arguments:

```python
from learnings import extract_learning
from memory.capture import CaptureService

# Extract learning from tool response
learning = extract_learning(
    tool_name="Bash",
    response={"stderr": "npm WARN deprecated", "exit_code": 0},
    context="Installing dependencies",
    spec="auth-feature",
)

if learning:
    # Convert to memory args
    args = learning.to_memory_args()
    # args = {
    #     "spec": "auth-feature",
    #     "summary": "Bash warning: npm WARN deprecated",
    #     "insight": "**Tool**: Bash\n**Category**: warning\n...",
    #     "applicability": "When using Bash tool",
    #     "tags": ["bash", "warning", "sev-3"],
    # }

    # Capture to memory
    capture = CaptureService()
    result = capture.capture_learning(**args)
```

### Memory Content Structure

The generated `insight` field follows a structured format:

```markdown
**Tool**: Bash
**Category**: warning
**Severity**: sev-3

## Context
Installing dependencies

## Observation
Detected signals: npm WARN deprecated

## Output Excerpt
```
npm WARN deprecated inflight@1.0.6: This module is not supported...
```
```

### PostToolUse Hook Integration

The learnings module is designed for use in a PostToolUse hook:

```python
# hooks/post_tool_use.py

import json
import sys
from learnings import extract_learning
from memory.capture import CaptureService, is_auto_capture_enabled

def main():
    # Read hook input
    input_data = json.loads(sys.stdin.read())

    tool_name = input_data["tool_name"]
    response = input_data["response"]

    # Only capture if enabled
    if not is_auto_capture_enabled():
        return

    # Extract learning
    learning = extract_learning(
        tool_name=tool_name,
        response=response,
        context=input_data.get("context", ""),
        spec=input_data.get("spec"),
    )

    if learning:
        # Capture to memory (fail-open)
        try:
            capture = CaptureService()
            result = capture.capture_learning(**learning.to_memory_args())
        except Exception:
            pass  # Log but don't block
```

## Security: Secret Filtering

All output passes through the secret filter pipeline before capture:

```python
from filters.pipeline import filter_pipeline

# Filter secrets from output
filtered = filter_pipeline(raw_output)

# filtered.filtered_text: Content with secrets replaced
# filtered.secret_count: Number of secrets found
# filtered.stats: {"aws_key": 1, "github_token": 2, ...}
```

### Filtered Secret Types

- AWS keys (AKIA*, ASIA*)
- GitHub tokens (ghp_*, gho_*, ghu_*, ghs_*)
- OpenAI/Anthropic keys
- Database connection strings
- Private keys
- JWT tokens
- Generic passwords

Secrets are replaced with `[SECRET:type]` placeholders.

### Path Sanitization

Home directories and credential paths are redacted:

```python
from learnings.extractor import sanitize_paths

text = "/Users/john/.ssh/id_rsa"
sanitized = sanitize_paths(text)
# Result: "/Users/[USER]/[.ssh-REDACTED]/id_rsa"
```

## Output Truncation

Captured output is truncated to 1KB with smart prioritization:

```python
from learnings.extractor import truncate_output

long_output = "..." # 10KB of output
truncated = truncate_output(long_output)

# Truncation prioritizes:
# 1. Lines containing "error", "Error", "ERROR"
# 2. Lines containing "warning", "Warning", "WARNING"
# 3. Lines containing "failed", "exception", "traceback"
# 4. Other lines (fill remaining space)
# 5. Adds "...[TRUNCATED: N chars]" notice
```

## Configuration

### Capture Threshold

Adjust the minimum score for capture:

```python
from learnings.detector import LearningDetector

# Default threshold is 0.6
detector = LearningDetector(threshold=0.7)  # Stricter
detector = LearningDetector(threshold=0.5)  # More permissive
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CS_TOOL_CAPTURE_ENABLED` | `true` | Enable/disable tool learning capture |
| `CS_AUTO_CAPTURE_ENABLED` | `true` | Master switch for all auto-capture |

### Deduplication Cache Size

```python
from learnings.deduplicator import SessionDeduplicator

# Default is 100 entries
dedup = SessionDeduplicator(max_size=200)  # Larger cache
```

## Testing

### Unit Tests

```python
# tests/learnings/test_detector.py

import pytest
from learnings.detector import LearningDetector, DetectionResult

@pytest.fixture
def detector():
    return LearningDetector()


def test_nonzero_exit_triggers_capture(detector):
    """Non-zero exit code should trigger capture."""
    result = detector.detect("Bash", {"exit_code": 1, "stderr": "error"})

    assert result.score >= 0.6
    assert result.should_capture


def test_success_does_not_trigger(detector):
    """Successful command should not trigger."""
    result = detector.detect("Bash", {"exit_code": 0, "stdout": "ok"})

    assert result.score < 0.6
    assert not result.should_capture
```

### Run Tests

```bash
# All learnings tests
uv run pytest tests/learnings/ -v

# Specific test file
uv run pytest tests/learnings/test_detector.py -v

# With coverage
uv run pytest tests/learnings/ --cov=learnings --cov-report=html
```

### Integration Tests

```python
# tests/learnings/test_integration.py

def test_full_extraction_pipeline(tmp_path, monkeypatch):
    """Test complete extraction from response to ToolLearning."""
    from learnings import extract_learning
    from learnings.deduplicator import reset_session_deduplicator

    # Reset deduplicator
    reset_session_deduplicator()

    # Simulate tool response
    response = {
        "exit_code": 1,
        "stderr": "npm ERR! code ENOENT\nnpm ERR! syscall open",
        "stdout": "",
    }

    learning = extract_learning(
        tool_name="Bash",
        response=response,
        context="Installing package",
        spec="my-feature",
    )

    assert learning is not None
    assert learning.category == "error"
    assert learning.severity == "sev-1"
    assert "ENOENT" in learning.output_excerpt
    assert learning.spec == "my-feature"
```

## Performance Considerations

### Pattern Compilation

All regex patterns are pre-compiled at module load:

```python
# Patterns are compiled once
ERROR_PATTERNS = [
    SignalPattern(
        pattern=re.compile(r"..."),  # Pre-compiled
        ...
    ),
]
```

### Detection Latency

Typical detection times:
- Small output (<1KB): <1ms
- Medium output (1-10KB): 1-5ms
- Large output (>10KB): 5-20ms

### Memory Usage

- Deduplicator cache: ~100 hashes * 16 bytes = ~1.6KB
- Pattern list: ~50 patterns * 200 bytes = ~10KB
- Total module overhead: ~15KB

## Troubleshooting

### Learning Not Captured

**Symptoms**: Tool error occurred but no learning was captured

**Diagnosis**:
```python
from learnings.detector import LearningDetector

detector = LearningDetector()
result = detector.detect("Bash", your_response)

print(f"Score: {result.score}")
print(f"Threshold: {detector.threshold}")
print(f"Signals: {[s.pattern_name for s in result.signals]}")
print(f"Noise factor: {result.noise_factor}")
```

**Common causes**:
- Score below threshold (add patterns or lower threshold)
- High noise factor (output contains success patterns)
- Deduplication filtered it (same error seen before)

### Duplicate Learnings

**Symptoms**: Same learning captured multiple times

**Diagnosis**:
```python
from learnings.deduplicator import get_session_deduplicator

dedup = get_session_deduplicator()
stats = dedup.get_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Duplicates: {stats['duplicate_patterns']}")
```

**Common causes**:
- Session deduplicator not reset between sessions
- Output differs slightly (different line numbers, timestamps)
- Cache eviction (max_size reached)

### Secrets in Captured Output

**Symptoms**: Sensitive data appears in learning output

**Diagnosis**:
```python
from filters.pipeline import filter_pipeline

filtered = filter_pipeline(your_output)
print(f"Secrets found: {filtered.secret_count}")
print(f"Types: {filtered.stats}")
```

**Fix**: Add new pattern to `filters/pipeline.py::SECRET_PATTERNS`
