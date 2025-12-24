# Code Review Report

**Date:** 2025-12-24
**Project:** claude-spec
**Scope:** Full codebase review (MAXALL mode)
**Reviewers:** 10 specialist agents (Security, Penetration Testing, Compliance, Chaos Engineering, Python Expert, Performance, Architecture, Code Quality, Testing, Documentation)

---

## Health Scores

| Dimension | Score | Status |
|-----------|-------|--------|
| Security | 5/10 | 🔴 Critical Issues |
| Performance | 8/10 | ✅ Good |
| Architecture | 7.5/10 | ⚠️ Minor Issues |
| Code Quality | 7/10 | ⚠️ Minor Issues |
| Test Coverage | 7/10 | ⚠️ Minor Issues |
| Documentation | 6/10 | ⚠️ Needs Attention |
| Resilience | 5.6/10 | ⚠️ Needs Attention |
| **Overall** | **6.5/10** | 🔴 Action Required |

---

## Critical Findings

### SEC-CRIT-001: Command Injection via GitHub Issue Titles (CRITICAL)

**File:** `scripts/github-issues/build-issue-prompt.sh:47-54`
**OWASP Category:** A03:2021 - Injection
**CVSS:** 9.8 (Critical)

**Description:** Issue titles from GitHub are interpolated directly into a heredoc without escaping. An attacker who can create an issue in the target repository can inject shell commands.

**Proof of Concept:**
```bash
# Attacker creates issue with title:
# Test $(whoami > /tmp/pwned)
#
# When build-issue-prompt.sh runs:
cat << EOF
/claude-spec:plan Issue #42: Test $(whoami > /tmp/pwned)
...
EOF
# The $() gets executed by the shell
```

**Impact:** Remote code execution with user privileges.

**Remediation:**
```bash
# Use printf with proper quoting
title_escaped=$(printf '%s' "$title" | sed "s/'/'\\\\''/g")
# Or use environment variables with envsubst
```

---

### SEC-CRIT-002: Dangerous Mode Enabled by Default (CRITICAL)

**File:** `skills/worktree-manager/scripts/lib/config.sh:66` and `claude-spec.config.json:4`
**Compliance:** SOC 2 CC6.1 (Least Privilege), NIST 800-53 AC-6

**Description:** The default `claudeCommand` includes `--dangerously-skip-permissions` which bypasses all permission prompts, granting autonomous access without user confirmation.

**Impact:** Amplifies all injection vulnerabilities by removing the human confirmation barrier. Combined with SEC-CRIT-001, achieves full system compromise.

**Remediation:**
```json
// claude-spec.config.json - change default
"claudeCommand": "claude"  // Remove --dangerously-skip-permissions
```

---

## High Severity Findings

### SEC-HIGH-001: Command Injection via AppleScript

**File:** `skills/worktree-manager/scripts/launch-agent.sh:192-214`
**CVSS:** 7.8 (High)

**Description:** `WORKTREE_PATH` is interpolated directly into AppleScript executed via `osascript`. Malicious characters in paths can inject commands.

**Remediation:**
```bash
escape_for_applescript() {
    local input="$1"
    printf '%s' "$input" | sed "s/'/'\\\\''/g"
}
SAFE_PATH=$(escape_for_applescript "$WORKTREE_PATH")
```

---

### SEC-HIGH-002: JSON Injection in Issue Context File

**File:** `scripts/github-issues/create-issue-worktree.sh:143-152`
**CVSS:** 7.5 (High)

**Description:** The `.issue-context.json` file uses heredoc with partial jq escaping. The `url` field is directly interpolated without escaping.

**Remediation:**
```bash
# Use jq to construct the entire JSON
jq -n \
  --argjson number "$number" \
  --arg title "$title" \
  --arg url "$url" \
  --arg body "$body" \
  '{number: $number, title: $title, url: $url, body: $body}'
```

---

### SEC-HIGH-003: Registry JSON Injection

**File:** `skills/worktree-manager/scripts/register.sh:90-94`
**CVSS:** 5.0 (Medium-High)

**Description:** The `TASK` variable is interpolated into a JSON string without proper escaping.

**Remediation:**
```bash
TASK_JSON=$(echo "$TASK" | jq -Rs .)
```

---

### SEC-HIGH-004: GitHub Token Scope Validation Missing

**File:** `scripts/github-issues/check-gh-prerequisites.sh`
**Compliance:** SOC 2 CC6.1, NIST 800-53 AC-6(1)

**Description:** Script verifies `gh auth status` but does not validate token scopes. Excessive scopes increase attack surface.

**Remediation:** Add scope validation and warn if token has admin scopes.

---

### ARCH-HIGH-001: Duplicate `safe_mtime` Implementation

**Files:** `steps/log_archiver.py:58-63` and `steps/retrospective_gen.py:53-58`

**Description:** Identical `safe_mtime` helper function defined in two step modules.

**Remediation:** Extract to `steps/utils.py` or `steps/base.py`.

---

### ARCH-HIGH-002: Duplicate Project Directory Logic

**Files:** `steps/log_archiver.py:41-66` and `steps/retrospective_gen.py:36-61`

**Description:** Nearly identical code for finding the most recently modified project directory.

**Remediation:** Create shared `find_most_recent_completed_project()` utility.

---

### RES-HIGH-001: File Lock Acquisition Has No Timeout

**File:** `filters/log_writer.py:264`

**Description:** `fcntl.flock(f.fileno(), fcntl.LOCK_EX)` blocks forever if another process holds the lock.

**Impact:** Tool becomes unresponsive indefinitely.

**Remediation:**
```python
import signal
def timeout_handler(signum, frame):
    raise TimeoutError("Lock acquisition timed out")
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)
try:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
finally:
    signal.alarm(0)
```

---

### RES-HIGH-002: Shell Commands Lack Timeout Protection

**File:** `scripts/github-issues/check-gh-prerequisites.sh:59-67`

**Description:** `gh auth status` and `gh repo view` can hang indefinitely on network issues.

**Remediation:**
```bash
timeout 10 gh auth status &>/dev/null
```

---

### DOC-HIGH-001: CHANGELOG.md Missing GitHub Issues Workflow

**File:** `CHANGELOG.md`

**Description:** The `[Unreleased]` section does not document the new GitHub Issues Worktree Workflow feature.

---

### DOC-HIGH-002: README.md Missing GitHub Issues Workflow

**File:** `README.md`

**Description:** Users should know they can run `/claude-spec:plan` without arguments to select from GitHub issues.

---

### QUAL-HIGH-001: Unnecessary `pass` in Exception Class

**File:** `filters/log_writer.py:122-129`

**Description:** `PathTraversalError` class has docstring + `pass`, but `pass` is unnecessary when docstring is present.

---

## Medium Severity Findings

### SEC-MED-001: Path Traversal via Template Variables

**File:** `skills/worktree-manager/scripts/launch-agent.sh:120-130`

**Description:** Template substitution doesn't sanitize branch/project names that could contain path traversal sequences.

---

### SEC-MED-002: TOCTOU Race in Symlink Check

**File:** `filters/log_writer.py:155-176`

**Description:** Race window between symlink check and file open. Mitigated by `O_NOFOLLOW` but could be simplified.

---

### SEC-MED-003: sys.path Manipulation at Runtime

**File:** `analyzers/analyze_cli.py:8-9`

**Description:** Modifies `sys.path` at runtime which can introduce security risks.

---

### SEC-MED-004: Subprocess Secrets in Output

**File:** `scripts/github-issues/post-issue-comment.sh:78`

**Description:** Subprocess output may contain secrets if commands fail with verbose errors.

---

### SEC-MED-005: Issue Context May Contain Sensitive Data

**File:** `scripts/github-issues/create-issue-worktree.sh:143-152`

**Description:** `.issue-context.json` is created from GitHub issue data without secret filtering.

---

### PERF-MED-001: Multiple Regex Pattern Iterations

**File:** `filters/pipeline.py:340-354`

**Description:** `detect_secrets()` iterates through 20+ patterns, scanning text 20+ times.

---

### PERF-MED-002: Repeated jq Invocations

**File:** `scripts/github-issues/create-issue-worktree.sh:70-74`

**Description:** JSON is piped through jq 5 separate times to extract different fields.

---

### ARCH-MED-001: ContextLoaderStep Dependency Inversion

**File:** `steps/context_loader.py:24-34`

**Description:** Step directly imports from `utils.context_utils` with module-level try/except.

---

### ARCH-MED-002: LogAnalysis Class Has 17 Fields

**File:** `analyzers/log_analyzer.py:39-76`

**Description:** SRP tension - large dataclass with computation method.

---

### ARCH-MED-003: `generate_interaction_analysis` 137 Lines

**File:** `analyzers/log_analyzer.py:190-327`

**Description:** Function length and multiple responsibilities.

---

### RES-MED-001: Worktree Creation Not Idempotent

**File:** `scripts/github-issues/create-issue-worktree.sh:101-117`

**Description:** Running twice causes hard error "Branch already exists".

---

### RES-MED-002: Port Allocation Without Cleanup on Failure

**File:** `skills/worktree-manager/scripts/allocate-ports.sh:90-92`

**Description:** Ports marked as allocated but never used if script fails.

---

### RES-MED-003: lsof Port Check Can Block

**File:** `skills/worktree-manager/scripts/allocate-ports.sh:64`

**Description:** lsof can hang on network filesystem issues.

---

### QUAL-MED-001: DRY Violation - `LOG_FILE` Constant

**Files:** `steps/log_archiver.py:25`, `steps/retrospective_gen.py:25`

**Description:** Same constant defined in two files; should import from `log_writer.py`.

---

### QUAL-MED-002: Magic Numbers in `log_analyzer.py`

**File:** `analyzers/log_analyzer.py:179, 248, 264`

**Description:** Thresholds like `10`, `0.5`, `0.3`, `500` are inline.

---

### QUAL-MED-003: `os.path` Instead of `pathlib`

**Files:** `analyzers/log_analyzer.py`, `analyzers/analyze_cli.py`

**Description:** Uses `os.path` while rest of codebase uses `pathlib`.

---

### QUAL-MED-004: Missing `from __future__ import annotations`

**Files:** `filters/pipeline.py`, `filters/log_entry.py`, `filters/log_writer.py`

**Description:** `steps/` uses this import but `filters/` does not.

---

### TEST-MED-001: ErrorCode Enum Values Not Tested

**File:** `steps/base.py`

**Description:** `ErrorCode` enum values and usage in StepResult not tested.

---

### TEST-MED-002: `StepResult.is_retriable()` Not Tested

**File:** `steps/base.py`

**Description:** Method exists but has no direct tests.

---

### TEST-MED-003: SEC-005 Path Traversal Validation Not Tested

**File:** `scripts/github-issues/create-issue-worktree.sh`

**Description:** The path traversal validation added for SEC-005 lacks test coverage.

---

### TEST-MED-004: Exception Handling Paths in BaseStep.run()

**File:** `steps/base.py`

**Description:** TimeoutError, PermissionError, OSError paths not tested.

---

### DOC-MED-001: Package `__init__.py` Files Missing Docstrings

**Files:** `steps/__init__.py`, `analyzers/__init__.py`, `filters/__init__.py`

**Description:** Package files are empty, should document exports.

---

### DOC-MED-002: docs/ARCHITECTURE.md Outdated

**File:** `docs/ARCHITECTURE.md`

**Description:** May reference removed memory/hooks systems.

---

### DOC-MED-003: scripts/github-issues/ Missing README

**File:** `scripts/github-issues/`

**Description:** Directory has 6 scripts but no README explaining the system.

---

### DOC-MED-004: SessionStats/LogAnalysis Missing Docstrings

**File:** `analyzers/log_analyzer.py`

**Description:** Dataclasses lack field documentation.

---

### COMP-MED-001: Session ID as PII Not Redacted

**File:** `filters/log_entry.py:153`

**Description:** Session IDs may correlate to users, potentially GDPR-relevant.

---

### COMP-MED-002: No Data Retention Policy Enforcement

**File:** `filters/log_writer.py`, `steps/log_archiver.py`

**Description:** Logs accumulate indefinitely with no cleanup mechanism.

---

### COMP-MED-003: Missing Operation Attribution

**File:** `filters/log_writer.py`, `steps/*.py`

**Description:** Operations not attributed to user identity for non-repudiation.

---

### COMP-MED-004: File Modification Events Not Logged

**Files:** `steps/marker_cleaner.py`, `steps/log_archiver.py`

**Description:** Cleanup/archival operations logged to stderr but not persisted.

---

### COMP-MED-005: Error Messages Expose Internal Paths

**File:** Multiple files

**Description:** Full file paths in errors may reveal structure.

---

### COMP-MED-006: Worktree Created Without Explicit Permissions

**File:** `scripts/github-issues/create-issue-worktree.sh`

**Description:** `.issue-context.json` created inheriting umask, could be world-readable.

---

## Low Severity Findings

(41 additional low-severity findings across all categories - see REMEDIATION_TASKS.md for full list)

---

## Summary by Category

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Security | 2 | 4 | 5 | 4 | 15 |
| Performance | 0 | 0 | 2 | 9 | 11 |
| Architecture | 0 | 2 | 3 | 4 | 9 |
| Code Quality | 0 | 1 | 4 | 11 | 16 |
| Resilience | 0 | 2 | 3 | 6 | 11 |
| Test Coverage | 0 | 0 | 4 | 8 | 12 |
| Documentation | 0 | 2 | 4 | 6 | 12 |
| Compliance | 0 | 0 | 6 | 3 | 9 |
| **Total** | **2** | **11** | **31** | **51** | **95** |

---

## Recommended Priority

1. **Immediate (Critical):** SEC-CRIT-001 (command injection), SEC-CRIT-002 (dangerous mode default)
2. **This Sprint (High):** All HIGH severity findings
3. **Next Sprint (Medium):** All MEDIUM severity findings
4. **Backlog (Low):** LOW severity findings during regular maintenance
