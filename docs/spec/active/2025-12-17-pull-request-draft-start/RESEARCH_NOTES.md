---
document_type: research_notes
project_id: SPEC-2025-12-17-001
version: 1.0.0
last_updated: 2025-12-17T17:30:00Z
status: draft
---

# Research Notes

This document captures research findings that informed the architecture and implementation plan.

---

## 1. Existing Step Module Analysis

### Source Files Analyzed

- `plugins/cs/steps/base.py` - BaseStep and StepResult classes
- `plugins/cs/steps/security_reviewer.py` - Reference implementation
- `plugins/cs/hooks/lib/step_runner.py` - Whitelist and execution
- `plugins/cs/hooks/lib/config_loader.py` - Configuration system

### Key Findings

#### BaseStep Pattern

```python
class BaseStep(ABC):
    name: str = "base"

    def __init__(self, cwd: str, config: dict | None = None):
        self.cwd = cwd
        self.config = config or {}

    @abstractmethod
    def execute(self) -> StepResult: ...

    def validate(self) -> bool:
        return True

    def run(self) -> StepResult:
        # Handles validation, execution, error catching
```

#### StepResult Contract

```python
@dataclass
class StepResult:
    success: bool
    message: str
    data: dict[str, Any]
    warnings: list[str]
    error_code: ErrorCode
    retriable: bool

    @classmethod
    def ok(cls, message: str = "Success", **data) -> "StepResult"

    @classmethod
    def fail(cls, message: str, error_code: ErrorCode = ...) -> "StepResult"
```

#### Whitelist Security

The `STEP_MODULES` dict in `step_runner.py` maps step names to module names:

```python
STEP_MODULES = {
    "security-review": "security_reviewer",
    "context-loader": "context_loader",
    "generate-retrospective": "retrospective_gen",
    "archive-logs": "log_archiver",
    "cleanup-markers": "marker_cleaner",
}
```

**Implication**: New step must be added to this whitelist.

#### Fail-Open Philosophy

From `base.py` docstring:
> "The step system follows a 'fail-open' philosophy:
> - Steps should not block the main command workflow on failure
> - Errors are captured and converted to StepResult.fail() with warnings
> - Only StepError exceptions propagate up (for critical failures)"

---

## 2. Configuration System Analysis

### Source Files Analyzed

- `plugins/cs/hooks/lib/config_loader.py`
- `plugins/cs/skills/worktree-manager/config.template.json`

### Key Findings

#### Configuration Hierarchy

1. User config: `~/.claude/worktree-manager.config.json`
2. Template config: `skills/worktree-manager/config.template.json`
3. Default: empty dict

User config is deep-merged over template.

#### Lifecycle Configuration Schema

```json
{
  "lifecycle": {
    "sessionStart": {
      "enabled": true,
      "loadContext": { ... }
    },
    "commands": {
      "cs:c": {
        "preSteps": [ { "name": "...", "enabled": true } ],
        "postSteps": [ { "name": "...", "enabled": true } ]
      }
    }
  }
}
```

#### Step Configuration Access

```python
# In step module
def execute(self) -> StepResult:
    timeout = self.config.get("timeout", 60)
    custom = self.config.get("custom_option", "default")
```

---

## 3. gh CLI Research

### Commands Required

| Operation | Command | Notes |
|-----------|---------|-------|
| Check auth | `gh auth status` | Exit 0 if logged in |
| Create draft | `gh pr create --draft --title "..." --body "..."` | Returns PR URL |
| View PR | `gh pr view --json url` | JSON output |
| Update body | `gh pr edit --body "..."` | Accepts multiline |
| Mark ready | `gh pr ready` | Converts draft |
| Add label | `gh pr edit --add-label "name"` | Idempotent |
| Remove label | `gh pr edit --remove-label "name"` | Idempotent |

### Error Handling Patterns

```bash
# Installation check
gh --version 2>/dev/null || echo "not installed"

# Auth check
gh auth status 2>&1  # Outputs to stderr

# PR exists check
gh pr view --json url 2>/dev/null && echo "exists"
```

### PR Creation Output

```bash
$ gh pr create --draft --title "Test" --body "Body"
https://github.com/owner/repo/pull/123
```

The URL is printed to stdout on success.

### Rate Limiting

GitHub API has rate limits. The gh CLI handles this gracefully but may fail silently. For MVP, we accept this risk.

---

## 4. /cs:p Command Flow Analysis

### Source File

- `plugins/cs/commands/p.md`

### Phase Transitions

The `/cs:p` command has clear phases:

1. **Inception**: Branch creation, project scaffold
2. **Elicitation**: AskUserQuestion rounds for requirements
3. **Research**: Codebase analysis, external research
4. **Design**: Architecture, decisions
5. **Planning**: Implementation plan creation
6. **Post-Approval**: Artifact finalization

### Recommended Integration Point

The PR should be created after the **first artifact** is generated (REQUIREMENTS.md), which occurs at the end of the Elicitation phase.

This was confirmed via user elicitation:
> Q: When should the draft PR be created?
> A: "After first artifact" - Early in the process, after initial planning documents exist

### Post-Approval Section (Reference)

The `/cs:p` command has a "Post-Approval" section where:
- All artifacts are finalized
- Ready for implementation

This is where the final PR update could occur (if implementing phase-based updates as P1).

---

## 5. README.md Frontmatter Format

### Current Format

```yaml
---
project_id: SPEC-2025-12-17-001
project_name: "Draft PR Creation for /cs:p Workflow"
slug: pull-request-draft-start
status: draft
created: 2025-12-17T16:31:00Z
approved: null
started: null
completed: null
expires: 2026-03-17T16:31:00Z
superseded_by: null
tags: [github, workflow, visibility, pr, planning]
stakeholders: []
github_issue: zircote/claude-spec#13
worktree:
  branch: plan/feat-pull-request-draft-start
  base_branch: main
  created_from_commit: 835add9
---
```

### Proposed Addition

```yaml
draft_pr_url: https://github.com/zircote/claude-spec/pull/XX
```

### YAML Parsing Considerations

- Use `ruamel.yaml` for round-trip parsing (preserves formatting)
- Or use regex-based insertion (simpler, less robust)
- Must handle case where field already exists (update vs. insert)

---

## 6. Similar Implementations (Reference)

### security_reviewer.py Pattern

```python
class SecurityReviewerStep(BaseStep):
    name = "security-review"
    DEFAULT_TIMEOUT = 120

    def execute(self) -> StepResult:
        timeout = self.config.get("timeout", self.DEFAULT_TIMEOUT)
        findings, scan_complete = self._run_bandit(timeout)

        if not findings and not scan_complete:
            # Tool not available - graceful degradation
            result = StepResult.ok(
                "Security review skipped (bandit not installed)",
                findings=[],
                scan_complete=False,
            )
            result.add_warning("Install bandit for security scanning")
            return result

        # ... rest of implementation
```

This pattern directly applies to our gh CLI availability check.

---

## 7. Open Questions (Resolved)

| Question | Resolution | Source |
|----------|------------|--------|
| When to create PR? | After first artifact | User elicitation |
| How to handle auth failure? | Graceful degradation | User elicitation |
| How often to push? | Batch at phase transitions | User elicitation |
| What does /cs:c do? | Convert draft to ready | User elicitation |
| Where to store PR URL? | README.md frontmatter | ADR-003 |

---

## 8. Risk Analysis

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| gh CLI version incompatibility | Low | Medium | Test with 2.x; document minimum |
| Network flakiness | Medium | Low | Timeouts; fail-open |
| README parsing errors | Low | Medium | Safe YAML; backup before write |
| PR URL format changes | Very Low | Low | Validate URL format |

### User Experience Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Users don't know PR wasn't created | Medium | Low | Clear warning message |
| Duplicate PRs | Medium | Medium | Check `gh pr view` first |
| Wrong base branch | Low | Low | Configurable base_branch |

---

## Appendix: Test Repository Results

### Manual Testing (Not Performed Yet)

The following should be verified during Phase 4:

1. `gh pr create --draft` succeeds in fresh repo
2. `gh pr view` detects existing PR
3. `gh pr ready` converts draft
4. Labels can be added/removed
5. Rate limiting behavior under load
