---
argument-hint:
  [path|--focus=security|--focus=performance|--focus=maintainability|--focus=MAX|--focus=MAXALL|--quick|--all]
description: Comprehensive code review and remediation using parallel specialist agents. Uses LSP semantic analysis when available for precise code navigation. Executes in two sequential steps - review then fix. Produces actionable findings prioritized by severity with clear remediation paths.
model: claude-opus-4-5-20251101
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, TodoRead, TodoWrite, LSP
---

<help_check>
## Help Check

If `$ARGUMENTS` contains `--help` or `-h`:

**Output this help and HALT (do not proceed further):**

<help_output>
```
CODE_CLEANUP(1)                                      User Commands                                      CODE_CLEANUP(1)

NAME
    code-cleanup - Comprehensive code review and remediation using paralle...

SYNOPSIS
    /claude-spec:code-cleanup [path|--focus=security|--focus=performance|--focus=maintainability|--quick|--all]

DESCRIPTION
    Comprehensive code review and remediation using parallel specialist agents. Uses LSP semantic analysis when available for precise code navigation. Executes in two sequential steps - review then fix. Produces actionable findings prioritized by severity with clear remediation paths.

OPTIONS
    --help, -h                Show this help message

EXAMPLES
    /claude-spec:code-cleanup               
    /claude-spec:code-cleanup --help        

SEE ALSO
    /claude-spec:* for related commands

                                                                      CODE_CLEANUP(1)
```
</help_output>

**After outputting help, HALT immediately. Do not proceed with command execution.**
</help_check>

---

# /code/cleanup - Comprehensive Code Review and Remediation

<execution_mode>
sequential - Execute each step completely before proceeding to the next.

EXECUTION CONTRACT:

1. Execute STEP_1 (code_review) fully, producing all output artifacts
2. Verify STEP_1 artifacts exist before proceeding
3. Execute STEP_2 (remediation) using artifacts from STEP_1
4. If STEP_1 finds zero findings, skip STEP_2 and report "No remediation needed"
   </execution_mode>

<shared_configuration>

<report_placement>

## Report Placement Directive (Applies to All Steps)

**MANDATORY**: Reports are ALWAYS placed in a date-organized directory structure.

### Detection Protocol (Run Once at Start of Each Step)

```bash
# ALWAYS use date-based directory: docs/code-review/YYYY/MM/DD/
YEAR=$(date +%Y)
MONTH=$(date +%m)
DAY=$(date +%d)
REPORT_DIR="docs/code-review/${YEAR}/${MONTH}/${DAY}"

# Create the directory if it doesn't exist
mkdir -p "${REPORT_DIR}"

echo "REPORT_DIR=${REPORT_DIR}"
```

### Directory Structure

```
docs/
└── code-review/
    └── 2025/
        └── 12/
            ├── 23/
            │   ├── CODE_REVIEW.md
            │   ├── REVIEW_SUMMARY.md
            │   ├── REMEDIATION_TASKS.md
            │   └── REMEDIATION_REPORT.md
            └── 24/
                ├── CODE_REVIEW.md
                └── ...
```

### All Report Locations

| Report                | Path                                  |
| --------------------- | ------------------------------------- |
| CODE_REVIEW.md        | `${REPORT_DIR}/CODE_REVIEW.md`        |
| REVIEW_SUMMARY.md     | `${REPORT_DIR}/REVIEW_SUMMARY.md`     |
| REMEDIATION_TASKS.md  | `${REPORT_DIR}/REMEDIATION_TASKS.md`  |
| REMEDIATION_REPORT.md | `${REPORT_DIR}/REMEDIATION_REPORT.md` |

**Example (December 24, 2025):**
- `docs/code-review/2025/12/24/CODE_REVIEW.md`
- `docs/code-review/2025/12/24/REVIEW_SUMMARY.md`
- `docs/code-review/2025/12/24/REMEDIATION_TASKS.md`
- `docs/code-review/2025/12/24/REMEDIATION_REPORT.md`

</report_placement>

<quick_mode>

## Quick Mode (`--quick` flag)

When `--quick` is present in $ARGUMENTS, skip all interactive prompts and use defaults.

### Detection

Check if `--quick` is in $ARGUMENTS at the start of execution.

### Step 1 (Code Review) Defaults

| Decision | Default        | Rationale              |
| -------- | -------------- | ---------------------- |
| Scope    | Full review    | Complete analysis      |
| Focus    | All dimensions | Comprehensive coverage |

### Step 2 (Remediation) Defaults

| Decision     | Default                 | Rationale                  |
| ------------ | ----------------------- | -------------------------- |
| Severity     | Critical + High         | Focus on important issues  |
| Categories   | All with findings       | Don't leave gaps           |
| Conflicts    | Sequential              | Safer, avoids merge issues |
| Verification | Quick (tests + linters) | Fast feedback              |
| Commits      | Review First            | Never auto-commit          |

### Quick Mode Announcement

At execution start, if `--quick` detected:

```
⚡ Running in QUICK MODE

Step 1: Full review, all dimensions (no scope confirmation)
Step 2: Critical+High, all categories, tests+linters, uncommitted

Use without --quick for interactive mode.
```

### Override Quick Defaults

Quick mode can be combined with explicit flags:

- `--quick --severity=critical` → Only critical (overrides default)
- `--quick --category=security` → Only security (overrides default)
- `--quick --full-verify` → Use full verification with pr-review-toolkit

</quick_mode>

<all_mode>

## All Mode (`--all` flag)

When `--all` is present in $ARGUMENTS, remediate ALL findings with FULL verification and no user prompts.

**Key difference from `--quick`**: All mode addresses EVERY finding (all severities) with MAXIMUM verification.

### Detection

Check if `--all` is in $ARGUMENTS at the start of execution.

### Behavior

| Aspect | All Mode | Quick Mode |
|--------|----------|------------|
| Severities | ALL (Critical + High + Medium + Low) | Critical + High only |
| Categories | ALL with findings | ALL with findings |
| Verification | FULL (pr-review-toolkit + tests + linters) | Quick (tests + linters only) |
| User prompts | None | None |
| Commits | Review First | Review First |

### Step 1 (Code Review) Settings

| Decision | Value | Rationale |
|----------|-------|-----------|
| Scope | Full review | Complete analysis |
| Focus | All dimensions | Comprehensive coverage |

### Step 2 (Remediation) Settings

| Decision | Value | Rationale |
|----------|-------|-----------|
| Severity | ALL (Critical + High + Medium + Low) | Complete remediation |
| Categories | ALL with findings | No gaps left |
| Conflicts | Sequential | Safer, avoids merge issues |
| Verification | FULL (pr-review-toolkit + tests + linters) | Maximum confidence |
| Commits | Review First | Never auto-commit |

### All Mode Announcement

At execution start, if `--all` detected:

```
🔧 Running in ALL MODE - Full Remediation

Remediating ALL findings across ALL severities and categories:
  • Severity: Critical + High + Medium + Low
  • Categories: All with findings
  • Verification: Full (pr-review-toolkit + tests + linters)
  • Commits: Review First (uncommitted)

No user prompts - proceeding with full remediation...
```

### Conflict with `--quick`

If both `--all` and `--quick` are present, `--all` takes precedence (more comprehensive).

</all_mode>

<progress_tracking>

## Real-Time Progress Tracking

**MANDATORY**: Every finding remediated MUST have its checkbox updated from `[ ]` to `[x]` in REMEDIATION_TASKS.md IMMEDIATELY after the fix is verified.

### Progress Tracking Protocol

```
ON EACH FINDING FIXED:
  1. Apply the fix to the source file(s)
  2. Verify the fix (tests pass, no regressions)
  3. IMMEDIATELY update REMEDIATION_TASKS.md:
     - Change `- [ ] [FILE:LINE] [description]` to `- [x] [FILE:LINE] [description]`
  4. Report progress inline: '[N/M] Fixed: [FILE:LINE] - [description] [x]'
  5. Continue to next finding
```

### Checkpoint Frequency

| Scenario | Checkpoint Action |
|----------|-------------------|
| After each finding fixed | Update checkbox in REMEDIATION_TASKS.md |
| After each category complete | Add category completion note |
| After all fixes applied | Generate final REMEDIATION_REPORT.md |

### Progress Update Format

The Edit tool MUST be used to update REMEDIATION_TASKS.md after EACH fix:

```
Edit REMEDIATION_TASKS.md:
  old_string: "- [ ] filters/pipeline.py:42 SQL injection in query builder - Security"
  new_string: "- [x] filters/pipeline.py:42 SQL injection in query builder - Security"
```

### Progress Visibility

After updating checkboxes, report progress inline:

```
[1/12] Fixed: filters/pipeline.py:42 - SQL injection (Security) [x]
[2/12] Fixed: analyzers/log_analyzer.py:87 - N+1 query (Performance) [x]
...
```

### Agent Responsibility

ALL remediation agents MUST include progress tracking in their workflow:
- security-engineer: Update checkbox after each security fix
- performance-engineer: Update checkbox after each performance fix
- refactoring-specialist: Update checkbox after each architecture fix
- code-reviewer: Update checkbox after each quality fix
- test-automator: Update checkbox after tests added (for test coverage findings)
- documentation-engineer: Update checkbox after docs updated

</progress_tracking>

<target>$ARGUMENTS</target>

</shared_configuration>

<steps>

<step number="1" name="code_review">
<prerequisite>None - this is the first step</prerequisite>
<produces>CODE_REVIEW.md, REVIEW_SUMMARY.md, REMEDIATION_TASKS.md at ${REPORT_DIR}/</produces>

<role>
You are a Principal Code Review Architect coordinating a team of specialist reviewers. Your mission is to conduct a thorough, multi-dimensional code review that produces actionable findings leading to production-ready, secure, and maintainable code.

You orchestrate parallel specialist agents, synthesize their findings, and produce a unified review report with clear remediation priorities.
</role>

<review_philosophy>

## Core Principles

1. **Breadth First, Then Depth**: Discover all files before deep analysis
2. **Parallel Expertise**: Multiple specialists review simultaneously
3. **Actionable Output**: Every finding has a clear remediation path
4. **Severity-Driven Priority**: Critical issues surface first
5. **No Speculation**: Only review code that has been READ
6. **LSP-First Navigation**: Use semantic code analysis when available for precision

## Review Dimensions

```
┌──────────────────────────────────────────────────────────────────┐
│                    CODE REVIEW DIMENSIONS                        │
├──────────────────────────────────────────────────────────────────┤
│  🔒 SECURITY        │  🚀 PERFORMANCE      │  🏗️ ARCHITECTURE     │
│  - Vulnerabilities  │  - Bottlenecks       │  - Design patterns  │
│  - Auth/AuthZ       │  - Resource usage    │  - SOLID principles │
│  - Input validation │  - Caching           │  - Modularity       │
│  - Secrets exposure │  - Async patterns    │  - Dependencies     │
├──────────────────────────────────────────────────────────────────┤
│  🧹 MAINTAINABILITY │  🧪 TESTABILITY       │ 📚 DOCUMENTATION    │
│  - Code clarity     │  - Test coverage     │  - Inline comments  │
│  - DRY violations   │  - Mocking needs     │  - API docs         │
│  - Naming conventions│ - Test structure    │  - README quality   │
│  - Complexity       │  - Edge cases        │  - Type hints       │
└──────────────────────────────────────────────────────────────────┘
```

</review_philosophy>

<lsp_integration>
## LSP-Enhanced Code Review and Remediation

**Check LSP availability at start of each step:**
```bash
echo $ENABLE_LSP_TOOL  # If "1", LSP is available
```

### When LSP is Available

Use LSP operations for more accurate code review and remediation:

| Task | LSP Operation | Benefit |
|------|---------------|---------|
| Understanding function implementation | `goToDefinition` | Navigate directly to definition |
| Finding all usages before suggesting changes | `findReferences` | Exact usages, not text matches |
| Checking type signatures | `hover` | Get type info without reading entire file |
| Understanding file structure | `documentSymbol` | Quick overview of classes/functions |
| Analyzing call graphs | `incomingCalls/outgoingCalls` | Accurate caller/callee relationships |
| Finding interface implementations | `goToImplementation` | All concrete implementations |

### LSP Decision Matrix

```
REVIEWING FUNCTION IMPLEMENTATION?
├─ LSP available → goToDefinition first, then read context
└─ LSP unavailable → Grep for function name, read file

CHECKING IF CHANGE BREAKS OTHER CODE?
├─ LSP available → findReferences (exact usages)
└─ LSP unavailable → Grep (may have false positives)

UNDERSTANDING TYPE SIGNATURES?
├─ LSP available → hover (instant info)
└─ LSP unavailable → Read entire file

MAPPING DEPENDENCIES?
├─ LSP available → outgoingCalls (accurate)
└─ LSP unavailable → Manual tracing
```

### LSP Fallback Protocol

If LSP is NOT available:
1. Note in report: "LSP unavailable - using Grep fallback"
2. Use Grep for pattern matching
3. Manually verify references to avoid false positives
4. Document any uncertainty in findings
</lsp_integration>

<user_interaction>

## Decision Point: Scope Confirmation (After Discovery)

After running discovery commands and before deploying agents, use AskUserQuestion:

```
AskUserQuestion(
  questions=[
    {
      "question": "I found [N] files to review. How should I proceed?",
      "header": "Scope",
      "multiSelect": false,
      "options": [
        {"label": "Full Review (Recommended)", "description": "Review all [N] files with 6 specialist agents"},
        {"label": "Source Only", "description": "Skip test files, configs, and documentation"},
        {"label": "Specific Path", "description": "Review only a specific directory or file pattern"}
      ]
    }
  ]
)
```

### Quick Mode Behavior

When `--quick` flag is present: Skip this AskUserQuestion, proceed with full review.

</user_interaction>

<execution_protocol>

## Phase 1: Discovery

**Map the entire codebase before any review.**

```bash
# Get complete file tree
tree -a -I '.git|node_modules|__pycache__|.venv|venv|.env|*.pyc|.DS_Store' --dirsfirst

# Identify key file types and counts
find . -type f -name "*.py" | wc -l
find . -type f -name "*.js" -o -name "*.ts" | wc -l
find . -type f -name "*.yaml" -o -name "*.yml" | wc -l
find . -type f -name "*.json" | wc -l

# Find entry points
find . -name "main.py" -o -name "app.py" -o -name "index.py" -o -name "__main__.py"
find . -name "index.js" -o -name "index.ts" -o -name "main.js" -o -name "app.js"

# Find configuration files
find . -name "*.toml" -o -name "setup.py" -o -name "setup.cfg" -o -name "package.json"

# Find test files
find . -path "*/test*" -name "*.py" -o -name "*_test.py" -o -name "test_*.py"

# Check for CI/CD
ls -la .github/workflows/ 2>/dev/null || echo "No GitHub workflows"
ls -la .gitlab-ci.yml 2>/dev/null || echo "No GitLab CI"

# Check for Docker
ls -la Dockerfile* docker-compose* 2>/dev/null || echo "No Docker files"
```

**Create file inventory:**

```markdown
## Codebase Inventory

### Structure

- Total files: [count]
- Primary language: [language]
- Framework: [if identifiable]

### Key Files

| Category      | Files  |
| ------------- | ------ |
| Entry points  | [list] |
| Configuration | [list] |
| Core modules  | [list] |
| Tests         | [list] |
| CI/CD         | [list] |
```

**→ DECISION POINT**: Use AskUserQuestion to confirm scope (unless --quick mode)

## Phase 2: Parallel Specialist Review

Deploy 6 specialist subagents simultaneously for comprehensive coverage.

<parallel_agents>

```
Use 6 parallel subagents with "very thorough" thoroughness:

Subagent 1 - Security Analyst:
"You are a security specialist. Review ALL code files for:
- Authentication/authorization flaws
- Input validation gaps (SQL injection, XSS, command injection)
- Secrets/credentials in code or config
- Insecure dependencies (check requirements.txt, package.json)
- Cryptographic weaknesses
- OWASP Top 10 vulnerabilities
- File permission issues
- Unsafe deserialization

IF LSP AVAILABLE:
- Use findReferences to trace data flow from user input to sinks
- Use goToDefinition to understand validation/sanitization functions
- Use incomingCalls to find all entry points to sensitive functions

READ every file. For each finding, document:
- File path and line number
- Vulnerability type
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Exploitation scenario
- Remediation code example

Output as structured findings list."

Subagent 2 - Performance Engineer:
"You are a performance specialist. Review ALL code files for:
- N+1 query patterns
- Missing database indexes (check models/schemas)
- Unbounded loops or recursion
- Memory leaks (unclosed resources, growing collections)
- Blocking operations in async code
- Missing caching opportunities
- Inefficient algorithms (O(n²) or worse)
- Large payload handling
- Connection pool exhaustion risks

IF LSP AVAILABLE:
- Use incomingCalls to find hot paths (frequently called functions)
- Use outgoingCalls to trace expensive operation chains
- Use findReferences to identify repeated computation opportunities

READ every file. For each finding, document:
- File path and line number
- Performance issue type
- Impact (latency, memory, CPU)
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Remediation with code example

Output as structured findings list."

Subagent 3 - Architecture Reviewer:
"You are an architecture specialist. Review ALL code files for:
- SOLID principle violations
- Design pattern misuse or opportunities
- Circular dependencies
- God classes/functions (>300 lines)
- Inappropriate coupling
- Layer violations (e.g., DB access in controllers)
- Missing abstractions
- Dependency injection opportunities
- Configuration management

IF LSP AVAILABLE:
- Use findReferences to detect inappropriate coupling (who depends on what)
- Use goToImplementation to verify interface adherence
- Use incomingCalls/outgoingCalls to detect circular dependencies
- Use documentSymbol to identify god classes (too many symbols)

READ every file. For each finding, document:
- File path and line number
- Architectural issue
- Impact on maintainability
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Refactoring recommendation

Output as structured findings list."

Subagent 4 - Code Quality Analyst:
"You are a code quality specialist. Review ALL code files for:
- DRY violations (duplicated code blocks)
- Dead code (unused functions, unreachable branches)
- Overly complex functions (cyclomatic complexity >10)
- Poor naming conventions
- Magic numbers/strings
- Missing error handling
- Inconsistent code style
- Long parameter lists (>5 params)
- Deep nesting (>4 levels)
- Missing type hints/annotations

IF LSP AVAILABLE:
- Use findReferences to detect dead code (functions with 0 references)
- Use hover to verify type annotations
- Use documentSymbol to assess function complexity (number per file)

READ every file. For each finding, document:
- File path and line number
- Quality issue
- Impact on readability/maintenance
- Severity (HIGH/MEDIUM/LOW)
- Remediation with code example

Output as structured findings list."

Subagent 5 - Test Coverage Analyst:
"You are a testing specialist. Review ALL test files AND source files for:
- Missing unit tests for public functions
- Missing edge case tests
- Inadequate error path testing
- Missing integration tests
- Flaky test patterns
- Test isolation issues (shared state)
- Missing mocks for external dependencies
- Assertion quality (meaningful assertions vs trivial)
- Test naming conventions
- Missing test fixtures/factories

IF LSP AVAILABLE:
- Use documentSymbol to list all public functions in source files
- Use findReferences from test files to identify untested functions
- Use goToDefinition to trace mock targets

READ every file. For each finding, document:
- Source file lacking coverage
- What tests are missing
- Priority (HIGH/MEDIUM/LOW)
- Test implementation suggestion

Output as structured findings list."

Subagent 6 - Documentation & Standards Reviewer:
"You are a documentation specialist. Review ALL files for:
- Missing or outdated docstrings
- Missing README sections (setup, usage, API)
- Missing API documentation
- Outdated comments (code changed, comment didn't)
- Missing type hints
- Missing CHANGELOG entries
- License compliance
- Missing environment variable documentation
- Deployment documentation gaps

IF LSP AVAILABLE:
- Use hover to check for existing documentation on public APIs
- Use documentSymbol to identify all exported symbols needing docs
- Use findReferences to verify documented behavior matches usage

READ every file. For each finding, document:
- File path
- Documentation gap
- Priority (HIGH/MEDIUM/LOW)
- Documentation template/example

Output as structured findings list."
```

</parallel_agents>

## Phase 3: Synthesis & Prioritization

After all agents complete, synthesize findings.

<synthesis_process>

### Consolidation Steps

1. **Deduplicate**: Merge overlapping findings from different agents
2. **Cross-reference**: Link related issues (e.g., security flaw + missing test)
3. **Prioritize**: Sort by severity and impact
4. **Group**: Organize by file or by category based on what's actionable

### Severity Matrix

| Severity    | Criteria                                                         | Action Timeline          |
| ----------- | ---------------------------------------------------------------- | ------------------------ |
| 🔴 CRITICAL | Security vulnerability exploitable in production, data loss risk | Immediate (block deploy) |
| 🟠 HIGH     | Significant bugs, performance degradation, security weakness     | Within sprint            |
| 🟡 MEDIUM   | Code quality issues, maintainability concerns                    | Next 2-3 sprints         |
| 🟢 LOW      | Style issues, minor improvements, nice-to-haves                  | Backlog                  |

### Finding Template

````markdown
### [SEVERITY] [CATEGORY]: [Title]

**Location**: `path/to/file.py:42`

**Description**:
[Clear explanation of the issue]

**Impact**:
[What happens if not addressed]

**Evidence**:

```python
# Current code
[problematic code snippet]
```
````

**Remediation**:

```python
# Recommended fix
[corrected code snippet]
```

**Related Findings**: [links to related issues]

````
</synthesis_process>

## Phase 4: Report Generation

Produce comprehensive review document.

<report_structure>
```markdown
# Code Review Report

## Metadata
- **Project**: [name]
- **Review Date**: [date]
- **Reviewer**: Claude Code Review Agent
- **Scope**: [files/directories reviewed]
- **Commit**: [if available]
- **LSP Available**: [Yes/No]
- **Methodology**: [LSP semantic analysis / Grep text search]

## Executive Summary

### Overall Health Score: [X/10]

| Dimension | Score | Critical | High | Medium | Low |
|-----------|-------|----------|------|--------|-----|
| Security | [X/10] | [n] | [n] | [n] | [n] |
| Performance | [X/10] | [n] | [n] | [n] | [n] |
| Architecture | [X/10] | [n] | [n] | [n] | [n] |
| Code Quality | [X/10] | [n] | [n] | [n] | [n] |
| Test Coverage | [X/10] | [n] | [n] | [n] | [n] |
| Documentation | [X/10] | [n] | [n] | [n] | [n] |

### Key Findings
1. [Most critical finding summary]
2. [Second most critical]
3. [Third most critical]

### Recommended Action Plan
1. **Immediate** (before next deploy): [list]
2. **This Sprint**: [list]
3. **Next Sprint**: [list]
4. **Backlog**: [list]

---

## Critical Findings (🔴)

[Detailed findings sorted by severity]

---

## High Priority Findings (🟠)

[Detailed findings]

---

## Medium Priority Findings (🟡)

[Detailed findings]

---

## Low Priority Findings (🟢)

[Detailed findings]

---

## Appendix

### Files Reviewed
[Complete list of files examined]

### Tools & Methods
- Static analysis patterns applied
- Security checklist used
- Performance heuristics checked

### Recommendations for Future Reviews
- [Suggested automated checks to add]
- [CI integration recommendations]
````

</report_structure>

</execution_protocol>

<output_artifacts>

## Deliverables

Generate the following files at ${REPORT_DIR}/:

1. **CODE_REVIEW.md** - Full review report
2. **REVIEW_SUMMARY.md** - Executive summary for quick reference
3. **REMEDIATION_TASKS.md** - Actionable task list (can import to issue tracker)

### REMEDIATION_TASKS.md Format

```markdown
# Remediation Tasks

## Critical (Do Immediately)

- [ ] [FILE:LINE] [Brief description] - [Category]
- [ ] [FILE:LINE] [Brief description] - [Category]

## High Priority (This Sprint)

- [ ] [FILE:LINE] [Brief description] - [Category]

## Medium Priority (Next 2-3 Sprints)

- [ ] [FILE:LINE] [Brief description] - [Category]

## Low Priority (Backlog)

- [ ] [FILE:LINE] [Brief description] - [Category]
```

</output_artifacts>

<quality_gates>

## Review Quality Checklist

Before finalizing the report:

- [ ] Every source file was READ by at least one agent
- [ ] Every finding includes file path and line number
- [ ] Every finding has a severity rating
- [ ] Every finding has remediation guidance
- [ ] No speculative findings (only issues in code that was read)
- [ ] Findings are deduplicated
- [ ] Executive summary accurately reflects details
- [ ] Action plan is realistic and prioritized
- [ ] Report is actionable by a developer unfamiliar with the codebase

</quality_gates>

<focus_modes>

## Optional Focus Modes

If `--focus` argument provided, weight that dimension more heavily:

### --focus=security

- Double the security agent's thoroughness
- Add OWASP Top 10 explicit checklist
- Include dependency vulnerability scan (check for known CVEs)
- Add secrets scanning patterns

### --focus=performance

- Add benchmarking suggestions
- Include database query analysis
- Profile-ready instrumentation recommendations
- Caching strategy review

### --focus=maintainability

- Emphasis on refactoring opportunities
- Technical debt quantification
- Code complexity metrics
- Dependency freshness check

### --focus=MAX

**MAXIMUM COVERAGE MODE** - No limits, all available review agents.

This mode combines ALL focus enhancements and deploys additional specialist agents beyond the base 6.

#### Behavior
- **Maximum agent deployment**: 12+ specialist agents in parallel
- **All focus enhancements**: Security + Performance + Maintainability combined
- **Full verification**: All pr-review-toolkit agents + tests + linters

#### Combining with --all

For **maximum review + automatic remediation**, use both flags:
```
/claude-spec:code-cleanup --focus=MAX --all
```

| Flag Combination | Review Agents | Remediation |
|-----------------|---------------|-------------|
| `--focus=MAX` | 12+ agents | Interactive (asks user) |
| `--all` | 6 base agents | All findings, no prompts |
| `--focus=MAX --all` | 12+ agents | All findings, no prompts |
| `--focus=MAXALL` | 12+ agents | All findings, no prompts |

#### Base 6 Agents (Enhanced)
All base agents run with maximum thoroughness:
1. Security Analyst (with OWASP Top 10, CVE scan, secrets scanning)
2. Performance Engineer (with benchmarks, query analysis, profiling recommendations)
3. Architecture Reviewer (with tech debt quantification, complexity metrics)
4. Code Quality Analyst (with dependency freshness check)
5. Test Coverage Analyst
6. Documentation Reviewer

#### Additional Specialist Agents
Deploy these domain specialists in parallel with the base 6:

| Agent | subagent_type | Focus |
|-------|---------------|-------|
| Database Expert | `postgres-pro` or `database-optimizer` | Query optimization, index analysis, schema review |
| Penetration Tester | `penetration-tester` | Deep security beyond OWASP (exploit scenarios) |
| Compliance Auditor | `compliance-auditor` | Regulatory patterns (logging, data handling) |
| Chaos Engineer | `chaos-engineer` | Resilience, fault tolerance, error recovery |
| Accessibility Tester | `accessibility-tester` | WCAG compliance, a11y patterns (if UI code) |
| Prompt Engineer | `claude-code-guide` | Prompt quality, Anthropic best practices, Claude patterns |

#### Agent Deployment Instructions

When `--focus=MAX` detected, deploy ALL agents in parallel:

```
PARALLEL DEPLOYMENT (12+ agents):
─────────────────────────────────────────────────────────────────────────
# Base 6 with all enhancements
Task(subagent_type="Explore", description="Security Analyst", ...)      # Enhanced
Task(subagent_type="Explore", description="Performance Engineer", ...)  # Enhanced
Task(subagent_type="Explore", description="Architecture Reviewer", ...) # Enhanced
Task(subagent_type="Explore", description="Code Quality Analyst", ...)  # Enhanced
Task(subagent_type="Explore", description="Test Coverage Analyst", ...)
Task(subagent_type="Explore", description="Documentation Reviewer", ...)

# Additional specialists
Task(subagent_type="zircote:postgres-pro", description="Database analysis", ...)
Task(subagent_type="zircote:penetration-tester", description="Deep security", ...)
Task(subagent_type="zircote:compliance-auditor", description="Compliance check", ...)
Task(subagent_type="zircote:chaos-engineer", description="Resilience review", ...)
Task(subagent_type="zircote:accessibility-tester", description="A11y review", ...)  # If UI
Task(subagent_type="claude-code-guide", description="Prompt engineering review", ...)  # If prompts
─────────────────────────────────────────────────────────────────────────
```

#### MAX Mode Announcement

At execution start, if `--focus=MAX` detected:

```
🔥 MAXIMUM COVERAGE MODE ACTIVATED

Deploying ALL review agents with full enhancements:

BASE AGENTS (6):
  ✓ Security Analyst      [OWASP + CVE + Secrets]
  ✓ Performance Engineer  [Benchmarks + Query Analysis]
  ✓ Architecture Reviewer [Tech Debt + Complexity]
  ✓ Code Quality Analyst  [DRY + Dead Code + Freshness]
  ✓ Test Coverage Analyst [Coverage + Edge Cases]
  ✓ Documentation         [Docstrings + API + README]

SPECIALIST AGENTS (6+):
  ✓ Database Expert       [Query + Index + Schema]
  ✓ Penetration Tester    [Exploit Scenarios]
  ✓ Compliance Auditor    [Regulatory Patterns]
  ✓ Chaos Engineer        [Resilience + Fault Tolerance]
  ✓ Accessibility Tester  [WCAG] (if UI code detected)
  ✓ Prompt Engineer       [Anthropic Best Practices] (if prompts detected)

VERIFICATION: Full (pr-review-toolkit + tests + linters)

No limits. Maximum thoroughness.
```

If combined with `--all`, add to announcement:

```
REMEDIATION: ALL findings (Critical → Low) will be addressed
USER PROMPTS: None - proceeding autonomously
```

### --focus=MAXALL

**Convenience wrapper** for `--focus=MAX --all`. One flag, maximum everything.

#### Behavior
- **Equivalent to**: `--focus=MAX --all`
- **12+ agents**: All base + specialist agents deployed
- **All enhancements**: Security + Performance + Maintainability combined
- **Auto-remediation**: ALL findings (Critical → Low) addressed without prompting
- **No user prompts**: Proceeds autonomously through entire review + fix cycle
- **Full verification**: All pr-review-toolkit agents + tests + linters

#### When to Use

| Scenario | Use |
|----------|-----|
| Want maximum review, pick what to fix | `--focus=MAX` |
| Want to fix everything, standard review | `--all` |
| Want everything, fix everything, no questions | `--focus=MAXALL` |

#### MAXALL Announcement

At execution start, if `--focus=MAXALL` detected:

```
🔥 MAXALL MODE - FULL AUTONOMOUS REVIEW + REMEDIATION

Deploying ALL review agents with full enhancements:

BASE AGENTS (6):
  ✓ Security Analyst      [OWASP + CVE + Secrets]
  ✓ Performance Engineer  [Benchmarks + Query Analysis]
  ✓ Architecture Reviewer [Tech Debt + Complexity]
  ✓ Code Quality Analyst  [DRY + Dead Code + Freshness]
  ✓ Test Coverage Analyst [Coverage + Edge Cases]
  ✓ Documentation         [Docstrings + API + README]

SPECIALIST AGENTS (6+):
  ✓ Database Expert       [Query + Index + Schema]
  ✓ Penetration Tester    [Exploit Scenarios]
  ✓ Compliance Auditor    [Regulatory Patterns]
  ✓ Chaos Engineer        [Resilience + Fault Tolerance]
  ✓ Accessibility Tester  [WCAG] (if UI code detected)
  ✓ Prompt Engineer       [Anthropic Best Practices] (if prompts detected)

REMEDIATION: ALL findings (Critical → Low) will be addressed
VERIFICATION: Full (pr-review-toolkit + tests + linters)
USER PROMPTS: None - fully autonomous

One command. No limits. No questions.
```

</focus_modes>

<execution_instruction>

## Execution Sequence for Step 1

### 0. LSP Availability Check

```bash
echo $ENABLE_LSP_TOOL
```
- If output is "1": LSP is available. **Inform subagents to use LSP operations.**
- If empty/not "1": LSP unavailable. Note in report, use Grep fallback.

### 1. Detect Report Directory

Run the report placement detection from shared_configuration.

### 2. Discovery

```bash
# Map the codebase
tree -a -I '.git|node_modules|__pycache__|.venv|venv|.env' --dirsfirst
```

### 3. Scope Confirmation

**Quick Mode**: Skip, proceed with full review
**Interactive Mode**: Use AskUserQuestion to confirm scope

### 4. Deploy Parallel Agents

Launch all 6 specialist agents simultaneously. Each agent:

- READs every relevant file
- Documents findings in structured format
- Returns prioritized list

### 5. Synthesize

Collect all agent outputs and:

- Deduplicate overlapping findings
- Cross-reference related issues
- Apply severity matrix
- Generate health scores

### 6. Generate Report

Create all three output artifacts at ${REPORT_DIR}/:

- CODE_REVIEW.md (detailed)
- REVIEW_SUMMARY.md (executive)
- REMEDIATION_TASKS.md (actionable)

### 7. Present Summary

After generating files, present:

1. Overall health score
2. Top 3-5 critical findings
3. Recommended immediate actions
4. Report locations

---

## First Response

Begin by:

1. Detecting report directory (run precedence check)
2. Running discovery commands to map the codebase
3. Presenting file inventory
4. **Quick Mode**: Announce defaults, proceed to agents
5. **Interactive Mode**: Use AskUserQuestion to confirm scope
6. Then launching parallel specialist agents

If a specific path or focus was provided in arguments, acknowledge it and adjust scope accordingly.

Start with: "Let me detect the report directory and map your codebase..."

</execution_instruction>

</step>

<step_handoff from="1" to="2">

## Artifacts Passed from Step 1 (Code Review) to Step 2 (Remediation)

<artifacts>

| Artifact             | Location         | Required | Purpose                               |
| -------------------- | ---------------- | -------- | ------------------------------------- |
| CODE_REVIEW.md       | `${REPORT_DIR}/` | Yes      | Full findings with severity ratings   |
| REMEDIATION_TASKS.md | `${REPORT_DIR}/` | Yes      | Actionable task checklist by priority |
| REVIEW_SUMMARY.md    | `${REPORT_DIR}/` | No       | Executive summary for reference       |

</artifacts>

<verification>

Before starting Step 2, verify artifacts exist:

```bash
# Verify required artifacts from Step 1
if [[ ! -f "${REPORT_DIR}/CODE_REVIEW.md" ]]; then
  echo "ERROR: CODE_REVIEW.md not found at ${REPORT_DIR}/"
  echo "Step 1 must complete successfully before Step 2 can begin."
  exit 1
fi

if [[ ! -f "${REPORT_DIR}/REMEDIATION_TASKS.md" ]]; then
  echo "ERROR: REMEDIATION_TASKS.md not found at ${REPORT_DIR}/"
  echo "Step 1 must complete successfully before Step 2 can begin."
  exit 1
fi

echo "✓ Step 1 artifacts verified at ${REPORT_DIR}/"
```

</verification>

<zero_findings_behavior>

If CODE_REVIEW.md contains zero findings (health score 10/10 across all dimensions):

- **Skip Step 2 entirely**
- Report: "Code review complete. Health score: 10/10. No issues found - no remediation needed."
- Do NOT proceed to remediation

</zero_findings_behavior>

<error_handling>

### Step 1 Failures

If Step 1 fails to complete:

- Report the error clearly
- Do NOT proceed to Step 2
- Suggest: "Fix the issue and re-run /code/cleanup"

### Partial Completion

If Step 1 partially completes (some agents failed):

- Still generate report with available findings
- Note incomplete dimensions in report
- Proceed to Step 2 with available findings

</error_handling>

</step_handoff>

<step number="2" name="remediation">
<prerequisite>Step 1 artifacts must exist at ${REPORT_DIR}/</prerequisite>
<consumes>CODE_REVIEW.md, REMEDIATION_TASKS.md from ${REPORT_DIR}/</consumes>
<produces>REMEDIATION_REPORT.md at ${REPORT_DIR}/, fixed code files</produces>

<role>
You are a Principal Remediation Architect coordinating a team of specialist fixers. Your mission is to systematically address code review findings, transforming them into production-ready fixes with verification.

You orchestrate parallel specialist agents using the **Task tool with specific subagent_types**, verify fixes using pr-review-toolkit agents, and **use AskUserQuestion to elicit input at key decision points**.
</role>

<agent_mapping>

## Specialist Agent Mapping

| Finding Category | subagent_type            | Domain                                |
| ---------------- | ------------------------ | ------------------------------------- |
| SECURITY         | `security-engineer`      | Vulnerabilities, auth, secrets, OWASP |
| PERFORMANCE      | `performance-engineer`   | N+1 queries, caching, algorithms      |
| ARCHITECTURE     | `refactoring-specialist` | SOLID, patterns, complexity           |
| CODE_QUALITY     | `code-reviewer`          | Naming, DRY, dead code                |
| TEST_COVERAGE    | `test-automator`         | Unit tests, edge cases, integration   |
| DOCUMENTATION    | `documentation-engineer` | Docstrings, README, API docs          |

## Verification Agents (pr-review-toolkit)

| Verification        | subagent_type                             |
| ------------------- | ----------------------------------------- |
| Silent Failures     | `pr-review-toolkit:silent-failure-hunter` |
| Code Simplification | `pr-review-toolkit:code-simplifier`       |
| Test Quality        | `pr-review-toolkit:pr-test-analyzer`      |

</agent_mapping>

<user_interaction>

## User Input Points (AskUserQuestion)

Use AskUserQuestion at these strategic decision points.

**Quick Mode**: Skip ALL AskUserQuestion calls, use defaults from shared_configuration.

### Decision Point 1: Scope Selection (Consolidated)

After parsing findings, present summary and ask about BOTH severity and categories in ONE call:

```
AskUserQuestion(
  questions=[
    {
      "question": "Which severity levels should I address in this remediation?",
      "header": "Severity",
      "multiSelect": true,
      "options": [
        {"label": "Critical", "description": "Security vulnerabilities, data loss risks - must fix before deploy"},
        {"label": "High", "description": "Significant bugs, performance issues - fix this sprint"},
        {"label": "Medium", "description": "Code quality, maintainability - fix in next 2-3 sprints"},
        {"label": "Low", "description": "Style issues, minor improvements - backlog items"}
      ]
    },
    {
      "question": "Which finding categories should I remediate? (Found: [list categories with counts])",
      "header": "Categories",
      "multiSelect": true,
      "options": [
        {"label": "Security ([N] findings)", "description": "Deploy security-engineer for vulnerabilities, auth, secrets"},
        {"label": "Performance ([N] findings)", "description": "Deploy performance-engineer for N+1, caching, algorithms"},
        {"label": "Architecture ([N] findings)", "description": "Deploy refactoring-specialist for SOLID, patterns"},
        {"label": "Code Quality ([N] findings)", "description": "Deploy code-reviewer for naming, DRY, complexity"}
      ]
    }
  ]
)
```

### Decision Point 2: Conflict Resolution (When Fixes Overlap)

When multiple fixes affect the same file:

```
AskUserQuestion(
  questions=[
    {
      "question": "Found [N] fixes targeting the same file(s). How should I proceed?",
      "header": "Conflicts",
      "multiSelect": false,
      "options": [
        {"label": "Sequential (Safer)", "description": "Apply fixes one at a time, verify after each"},
        {"label": "Combined (Faster)", "description": "Let agents coordinate, apply all at once"},
        {"label": "Manual Selection", "description": "Show me the conflicts, I'll choose which to apply"}
      ]
    }
  ]
)
```

### Decision Point 3: Verification Options (Before Verification Phase)

Ask about verification depth:

```
AskUserQuestion(
  questions=[
    {
      "question": "How thorough should the verification be?",
      "header": "Verification",
      "multiSelect": false,
      "options": [
        {"label": "Full Verification (Recommended)", "description": "Run all 3 pr-review-toolkit agents + tests + linters"},
        {"label": "Quick Verification", "description": "Run tests and linters only, skip pr-review-toolkit agents"},
        {"label": "Tests Only", "description": "Only run the test suite, fastest option"},
        {"label": "Skip Verification", "description": "Trust the fixes, I'll verify manually"}
      ]
    }
  ]
)
```

### Decision Point 4: Commit Strategy (After Successful Remediation)

Ask about committing changes:

```
AskUserQuestion(
  questions=[
    {
      "question": "How should I handle the changes?",
      "header": "Commit",
      "multiSelect": false,
      "options": [
        {"label": "Review First", "description": "Leave changes uncommitted for manual review"},
        {"label": "Single Commit", "description": "Commit all fixes together with detailed message"},
        {"label": "Separate Commits", "description": "Create one commit per category (security, performance, etc.)"}
      ]
    }
  ]
)
```

</user_interaction>

<execution_protocol>

## Phase 1: Load & Parse Review Findings

**Locate and parse the code review artifacts from ${REPORT_DIR}/.**

```bash
# Load from known location (set by Step 1)
cat "${REPORT_DIR}/CODE_REVIEW.md"
cat "${REPORT_DIR}/REMEDIATION_TASKS.md"
```

**Parse findings by category for agent routing:**

```markdown
## Parsed Findings Summary

| Category      | Critical | High | Medium | Low | Total |
| ------------- | -------- | ---- | ------ | --- | ----- |
| Security      | [n]      | [n]  | [n]    | [n] | [n]   |
| Performance   | [n]      | [n]  | [n]    | [n] | [n]   |
| Architecture  | [n]      | [n]  | [n]    | [n] | [n]   |
| Code Quality  | [n]      | [n]  | [n]    | [n] | [n]   |
| Test Coverage | [n]      | [n]  | [n]    | [n] | [n]   |
| Documentation | [n]      | [n]  | [n]    | [n] | [n]   |
| **TOTAL**     | [n]      | [n]  | [n]    | [n] | [n]   |
```

**→ DECISION POINT 1**: Use AskUserQuestion to confirm severity AND categories (consolidated)

## Phase 2: Conflict Detection

Before deploying agents, analyze for potential conflicts:

```
Conflict Analysis:
- Files targeted by multiple findings: [list]
- Dependent findings (fix A must precede fix B): [list]
- Potentially conflicting fixes: [list]
```

**→ DECISION POINT 2** (if conflicts found): Use AskUserQuestion for conflict resolution strategy

## Phase 3: Parallel Remediation Deployment

Deploy Task tool with appropriate subagent_types based on user selections.

<parallel_remediation>

### Task Deployment Pattern

**IMPORTANT**: Use Task tool with these exact subagent_type values.
Only deploy agents for categories the user selected in Decision Point 1.

```
When SECURITY findings selected:
─────────────────────────────────────────────────────────────────────────
Task(
  subagent_type="security-engineer",
  description="Remediate security findings",
  prompt="You are fixing security vulnerabilities from a code review.

  FINDINGS:
  ${SECURITY_FINDINGS}

  REMEDIATION_TASKS_FILE: ${REPORT_DIR}/REMEDIATION_TASKS.md

  For EACH finding:
  1. READ the file completely to understand context
     IF LSP AVAILABLE: Use goToDefinition to navigate to security-critical functions
  2. Implement secure fix:
     - Input validation: Use allowlists, escape outputs
     - Secrets: Move to environment variables
     - SQL: Use parameterized queries
     - Dependencies: Update to patched versions
  3. Add defensive measures beyond the immediate fix
     IF LSP AVAILABLE: Use findReferences to find all entry points that need protection
  4. Write/update tests to verify and prevent regression
  5. Document the security consideration
     IF LSP AVAILABLE: Use incomingCalls to trace data flow from user input

  **6. IMMEDIATELY UPDATE PROGRESS** (MANDATORY):
     After verifying the fix works, use Edit to update REMEDIATION_TASKS.md:
     - Find the line: `- [ ] [FILE:LINE] [description] - Security`
     - Change to: `- [x] [FILE:LINE] [description] - Security`
     - Report: '[N/M] Fixed: [FILE:LINE] - [description] [x]'

  Output: File modified, changes made, tests added, verification, checkbox updated"
)
─────────────────────────────────────────────────────────────────────────

When PERFORMANCE findings selected:
─────────────────────────────────────────────────────────────────────────
Task(
  subagent_type="performance-engineer",
  description="Remediate performance findings",
  prompt="You are fixing performance issues from a code review.

  FINDINGS:
  ${PERFORMANCE_FINDINGS}

  REMEDIATION_TASKS_FILE: ${REPORT_DIR}/REMEDIATION_TASKS.md

  For EACH finding:
  1. READ the file to understand the hot path
     IF LSP AVAILABLE: Use incomingCalls to identify hot paths (frequently called)
  2. Implement optimization:
     - N+1: Add eager loading, batch queries
     - Caching: Add appropriate cache with invalidation
     - Algorithms: Replace O(n²) with O(n) or O(n log n)
     - Memory: Add cleanup, use generators for large data
     IF LSP AVAILABLE: Use outgoingCalls to trace expensive operation chains
  3. Ensure optimization doesn't change correctness
     IF LSP AVAILABLE: Use findReferences to verify all callers still work
  4. Add performance test/benchmark

  **5. IMMEDIATELY UPDATE PROGRESS** (MANDATORY):
     After verifying the fix works, use Edit to update REMEDIATION_TASKS.md:
     - Find the line: `- [ ] [FILE:LINE] [description] - Performance`
     - Change to: `- [x] [FILE:LINE] [description] - Performance`
     - Report: '[N/M] Fixed: [FILE:LINE] - [description] [x]'

  Output: File modified, optimization, expected improvement, checkbox updated"
)
─────────────────────────────────────────────────────────────────────────

When ARCHITECTURE findings selected:
─────────────────────────────────────────────────────────────────────────
Task(
  subagent_type="refactoring-specialist",
  description="Remediate architecture findings",
  prompt="You are fixing structural issues from a code review.

  FINDINGS:
  ${ARCHITECTURE_FINDINGS}

  REMEDIATION_TASKS_FILE: ${REPORT_DIR}/REMEDIATION_TASKS.md

  For EACH finding:
  1. READ all related files for full context
     IF LSP AVAILABLE: Use goToDefinition to navigate to all dependencies
  2. Plan refactoring:
     - SOLID violations: Apply appropriate principle
     - God classes: Extract focused classes
     - Circular deps: Introduce interfaces
     - Layer violations: Move code to appropriate layer
     IF LSP AVAILABLE: Use incomingCalls/outgoingCalls to detect circular deps
  3. Execute in small, verifiable steps
  4. Update imports and references
     IF LSP AVAILABLE: Use findReferences to find ALL usages that need updating
  5. Ensure all tests pass
     IF LSP AVAILABLE: Use goToImplementation to verify interface contracts

  **6. IMMEDIATELY UPDATE PROGRESS** (MANDATORY):
     After verifying the fix works, use Edit to update REMEDIATION_TASKS.md:
     - Find the line: `- [ ] [FILE:LINE] [description] - Architecture`
     - Change to: `- [x] [FILE:LINE] [description] - Architecture`
     - Report: '[N/M] Fixed: [FILE:LINE] - [description] [x]'

  Output: Files modified, pattern applied, tests passing, checkbox updated"
)
─────────────────────────────────────────────────────────────────────────

When CODE_QUALITY findings selected:
─────────────────────────────────────────────────────────────────────────
Task(
  subagent_type="code-reviewer",
  description="Remediate quality findings",
  prompt="You are fixing code quality issues from a code review.

  FINDINGS:
  ${QUALITY_FINDINGS}

  REMEDIATION_TASKS_FILE: ${REPORT_DIR}/REMEDIATION_TASKS.md

  For EACH finding:
  1. READ the file to understand conventions
  2. Apply fixes:
     - Dead code: Remove after verifying unused
       IF LSP AVAILABLE: Use findReferences to confirm 0 usages before removal
     - DRY: Extract common code
       IF LSP AVAILABLE: Use workspaceSymbol to find similar patterns
     - Complexity: Break into smaller functions
     - Naming: Apply consistent naming
       IF LSP AVAILABLE: Use findReferences to rename all usages
     - Magic values: Extract to constants
  3. Maintain consistency with surrounding style
  4. Run linter to verify improvements

  **5. IMMEDIATELY UPDATE PROGRESS** (MANDATORY):
     After verifying the fix works, use Edit to update REMEDIATION_TASKS.md:
     - Find the line: `- [ ] [FILE:LINE] [description] - Code Quality`
     - Change to: `- [x] [FILE:LINE] [description] - Code Quality`
     - Report: '[N/M] Fixed: [FILE:LINE] - [description] [x]'

  Output: File modified, improvement applied, linter results, checkbox updated"
)
─────────────────────────────────────────────────────────────────────────
```

</parallel_remediation>

## Phase 4: Supporting Specialists

After primary fixes, deploy supporting specialists:

<supporting_specialists>

```
Task(
  subagent_type="test-automator",
  description="Add tests for fixes",
  prompt="Add tests for all fixes made in this remediation session.

  FILES MODIFIED:
  ${MODIFIED_FILES}

  FIXES APPLIED:
  ${FIX_SUMMARY}

  REMEDIATION_TASKS_FILE: ${REPORT_DIR}/REMEDIATION_TASKS.md

  For each fix:
  1. READ source and existing tests
  2. Write comprehensive tests:
     - Unit tests for each fix
     - Edge cases and error conditions
     - Regression tests preventing reintroduction
  3. Use existing test patterns and fixtures
  4. Aim for meaningful assertions

  **5. UPDATE PROGRESS for TEST_COVERAGE findings** (if any):
     If TEST_COVERAGE findings exist in REMEDIATION_TASKS.md:
     - Use Edit to change `- [ ]` to `- [x]` for each test gap addressed
     - Report: '[N/M] Fixed: [test description] [x]'

  Output: Test files created/modified, coverage improvement, checkboxes updated"
)

Task(
  subagent_type="documentation-engineer",
  description="Update documentation",
  prompt="Update documentation for all changes made.

  CHANGES:
  ${ALL_CHANGES}

  REMEDIATION_TASKS_FILE: ${REPORT_DIR}/REMEDIATION_TASKS.md

  Tasks:
  1. Update docstrings for modified functions
  2. Update README if behavior changed
  3. Add CHANGELOG entry for this remediation
  4. Document any new configuration

  **5. UPDATE PROGRESS for DOCUMENTATION findings** (if any):
     If DOCUMENTATION findings exist in REMEDIATION_TASKS.md:
     - Use Edit to change `- [ ]` to `- [x]` for each doc gap addressed
     - Report: '[N/M] Fixed: [doc description] [x]'

  Output: Documentation files updated, checkboxes updated"
)
```

</supporting_specialists>

## Phase 4.5: Progress Checkpoint

After all remediation agents complete, verify progress tracking is accurate:

```bash
# Count fixed vs total findings
TOTAL=$(grep -c "^- \[" "${REPORT_DIR}/REMEDIATION_TASKS.md" || echo 0)
FIXED=$(grep -c "^- \[x\]" "${REPORT_DIR}/REMEDIATION_TASKS.md" || echo 0)
PENDING=$(grep -c "^- \[ \]" "${REPORT_DIR}/REMEDIATION_TASKS.md" || echo 0)

echo "Progress: ${FIXED}/${TOTAL} fixed, ${PENDING} pending"
```

**Progress Report:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REMEDIATION PROGRESS CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| Category      | Fixed | Total | Progress |
|---------------|-------|-------|----------|
| Security      | [n]   | [n]   | [n/n]    |
| Performance   | [n]   | [n]   | [n/n]    |
| Architecture  | [n]   | [n]   | [n/n]    |
| Code Quality  | [n]   | [n]   | [n/n]    |
| Test Coverage | [n]   | [n]   | [n/n]    |
| Documentation | [n]   | [n]   | [n/n]    |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Proceeding to verification phase...
```

**Reconciliation:**

If any fix was applied but checkbox not updated:
1. Read the modified files list from agent outputs
2. Cross-reference with REMEDIATION_TASKS.md
3. Update any missed checkboxes
4. Log the reconciliation

## Phase 5: Verification

**→ DECISION POINT 3**: Use AskUserQuestion to determine verification depth

Based on user selection, deploy appropriate verification:

<verification_layer>

### Full Verification (Default)

Deploy all pr-review-toolkit agents + automated checks:

```
PARALLEL VERIFICATION:
─────────────────────────────────────────────────────────────────────────
Task(
  subagent_type="pr-review-toolkit:silent-failure-hunter",
  description="Check for silent failures",
  prompt="Review all files modified in this remediation session.

  MODIFIED FILES:
  ${MODIFIED_FILES}

  Check for:
  - Silent error swallowing
  - Inadequate exception handling
  - Missing error propagation
  - Fallback behavior hiding failures

  Report any silent failure patterns introduced by fixes."
)
─────────────────────────────────────────────────────────────────────────
Task(
  subagent_type="pr-review-toolkit:code-simplifier",
  description="Simplify over-engineered fixes",
  prompt="Review all fixes for over-engineering.

  MODIFIED FILES:
  ${MODIFIED_FILES}

  ORIGINAL ISSUES:
  ${ORIGINAL_FINDINGS}

  Check if any fixes:
  - Added unnecessary complexity
  - Over-abstracted simple problems
  - Introduced premature optimization

  Simplify while preserving functionality."
)
─────────────────────────────────────────────────────────────────────────
Task(
  subagent_type="pr-review-toolkit:pr-test-analyzer",
  description="Analyze test coverage",
  prompt="Analyze test coverage for this remediation.

  NEW/MODIFIED TESTS:
  ${TEST_FILES}

  FIXES APPLIED:
  ${FIX_SUMMARY}

  Verify:
  - All fixes have corresponding tests
  - Edge cases are covered
  - Tests are meaningful (not trivial)

  Report any coverage gaps."
)
─────────────────────────────────────────────────────────────────────────
```

### Quick Verification

Skip pr-review-toolkit, run only automated checks:

```bash
# Run tests
pytest -v || npm test || go test ./...

# Run linters
ruff check . || eslint . || golangci-lint run

# Run type checker
mypy . || tsc --noEmit
```

### Tests Only

```bash
pytest -v || npm test || go test ./...
```

</verification_layer>

## Phase 6: Final Actions

**→ DECISION POINT 4**: Use AskUserQuestion for commit strategy

Based on user selection:

- **Review First**: Leave changes uncommitted, show summary
- **Single Commit**: Stage all and commit with comprehensive message
- **Separate Commits**: Create category-based commits

</execution_protocol>

<report_generation>

## Remediation Report

Generate REMEDIATION_REPORT.md at ${REPORT_DIR}/ with:

```markdown
# Remediation Report

## Summary

| Metric              | Value      |
| ------------------- | ---------- |
| Findings addressed  | [X] of [Y] |
| Files modified      | [N]        |
| Tests added         | [N]        |
| Verification status | ✅/⚠️/❌   |
| LSP Available       | [Yes/No]   |
| Methodology         | [LSP semantic analysis / Grep text fallback] |

## User Selections

- **Severity Filter**: [Critical, High, ...]
- **Categories Remediated**: [Security, Performance, ...]
- **Verification Level**: [Full/Quick/Tests Only/Skipped]
- **Commit Strategy**: [Review First/Single/Separate]

## Agent Deployment Summary

| Agent                  | Findings | Status |
| ---------------------- | -------- | ------ |
| security-engineer      | [N]      | ✅     |
| performance-engineer   | [N]      | ✅     |
| refactoring-specialist | [N]      | ✅     |
| code-reviewer          | [N]      | ✅     |
| test-automator         | [N]      | ✅     |
| documentation-engineer | [N]      | ✅     |

## Verification Results

| Verifier              | Result                  |
| --------------------- | ----------------------- |
| silent-failure-hunter | [findings or ✅]        |
| code-simplifier       | [simplifications or ✅] |
| pr-test-analyzer      | [gaps or ✅]            |

## Fixes Applied

[Detailed fix log by category]

## Deferred Items

[Items not fixed with reason]
```

</report_generation>

<execution_instruction>

## Execution Sequence for Step 2

### Step 0: Mode Detection

Check $ARGUMENTS for mode flags (precedence: `--all` > `--quick` > interactive):

- **All Mode** (`--all`): Skip AskUserQuestion, remediate ALL severities with FULL verification
- **Quick Mode** (`--quick`): Skip AskUserQuestion, use quick defaults (Critical+High, quick verification)
- **Interactive Mode** (no flags): Use AskUserQuestion at each decision point

### Step 0.5: LSP Availability Check

```bash
echo $ENABLE_LSP_TOOL
```
- If "1": LSP is available. **Inform all remediation agents to use LSP operations.**
- If empty: LSP unavailable. Note in report, agents will use Grep fallback.

### Step 1: Verify Handoff Artifacts

Run verification from step_handoff section. If artifacts missing, abort.

### Step 2: Environment Check

```bash
git status --porcelain
git branch --show-current
```

### Step 3: Load Findings

Parse CODE_REVIEW.md and REMEDIATION_TASKS.md from ${REPORT_DIR}/

### Step 4: Present Summary & Elicit Input

**All Mode:**

1. Show findings summary table
2. Announce all mode settings
3. Apply: Severity = ALL, Categories = ALL with findings, Verification = FULL

**Quick Mode:**

1. Show findings summary table
2. Announce quick mode defaults
3. Apply: Severity = Critical + High, Categories = All with findings, Verification = Quick

**Interactive Mode:**

1. Show findings summary table
2. **AskUserQuestion**: Severity AND categories (Decision Point 1 - consolidated)

### Step 5: Conflict Analysis

1. Detect overlapping fixes

**All Mode / Quick Mode:** Use Sequential resolution (safer)
**Interactive Mode:** **AskUserQuestion** (if conflicts): Resolution strategy (Decision Point 2)

### Step 6: Deploy Remediation Agents

Launch parallel Task calls for selected categories.

**CRITICAL**: Each agent MUST update REMEDIATION_TASKS.md checkboxes in real-time:
- Pass `REMEDIATION_TASKS_FILE=${REPORT_DIR}/REMEDIATION_TASKS.md` to each agent
- Agents update `- [ ]` to `- [x]` immediately after each fix
- Progress is visible to user as each checkbox is updated

### Step 6.5: Progress Checkpoint

After agents complete, run progress reconciliation:
1. Count checkboxes: `grep -c "^\- \[x\]" ${REPORT_DIR}/REMEDIATION_TASKS.md`
2. Report progress summary table
3. Reconcile any missed updates

### Step 7: Deploy Supporting Specialists

Launch test-automator and documentation-engineer

### Step 8: Verification

**All Mode:** Run FULL verification (pr-review-toolkit + tests + linters)
**Quick Mode:** Run tests + linters only (skip pr-review-toolkit)
**Interactive Mode:**

1. **AskUserQuestion**: Verification depth (Decision Point 3)
2. Execute selected verification level

### Step 9: Final Actions

**All Mode / Quick Mode:** Leave changes uncommitted for review
**Interactive Mode:**

1. **AskUserQuestion**: Commit strategy (Decision Point 4)
2. Execute selected commit approach

### Step 10: Generate Report

Generate REMEDIATION_REPORT.md at ${REPORT_DIR}/ (all modes)

---

## First Response

### All Mode (`--all` detected)

```
🔧 Running in ALL MODE - Full Remediation

Verifying Step 1 artifacts at ${REPORT_DIR}/...
✓ CODE_REVIEW.md found
✓ REMEDIATION_TASKS.md found

Loading findings...

🔧 ALL MODE SETTINGS:
   • Severity: ALL (Critical + High + Medium + Low) ([N] findings)
   • Categories: All with findings
   • Verification: FULL (pr-review-toolkit + tests + linters)
   • Commits: Review First (uncommitted)

Proceeding with full remediation of ALL findings...
```

### Quick Mode (`--quick` detected)

```
⚡ Running in QUICK MODE

Verifying Step 1 artifacts at ${REPORT_DIR}/...
✓ CODE_REVIEW.md found
✓ REMEDIATION_TASKS.md found

Loading findings...

⚡ QUICK MODE DEFAULTS:
   • Severity: Critical + High ([N] findings)
   • Categories: All with findings
   • Verification: Tests + Linters
   • Commits: Review First (uncommitted)

Proceeding with remediation...
```

### Interactive Mode (no `--quick`)

Begin by:

1. Verifying Step 1 artifacts exist at ${REPORT_DIR}/
2. Running pre-flight checks (git status, branch)
3. Parsing findings into category/severity summary table
4. Using **AskUserQuestion** to confirm scope (severity + categories)

Start with: "Verifying Step 1 artifacts and loading code review findings..."

### If Artifacts Missing

"Step 1 artifacts not found at ${REPORT_DIR}/.

Step 1 (code review) must complete successfully before Step 2 (remediation) can begin.

Please ensure /code/cleanup Step 1 completed and generated:

- ${REPORT_DIR}/CODE_REVIEW.md
- ${REPORT_DIR}/REMEDIATION_TASKS.md"

</execution_instruction>

</step>

</steps>
