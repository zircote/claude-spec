---
argument-hint: <path|pattern|question>
description: Exhaustive codebase exploration command optimized for Opus 4.5. Conducts comprehensive, thorough investigation of codebases with maximum file reading depth. Uses "very thorough" exploration level, parallel subagents, LSP semantic navigation when available, and explicitly avoids assumptions by reading all relevant files before forming conclusions.
model: claude-opus-4-5-20251101
allowed-tools: Read, Glob, Grep, Bash, Task, LSP
---

<help_check>
## Help Check

If `$ARGUMENTS` contains `--help` or `-h`:

**Output this help and HALT (do not proceed further):**

<help_output>
```
DEEP_EXPLORE(1)                                      User Commands                                      DEEP_EXPLORE(1)

NAME
    deep-explore - Exhaustive codebase exploration command optimized for O...

SYNOPSIS
    /claude-spec:deep-explore <path|pattern|question>

DESCRIPTION
    Exhaustive codebase exploration command optimized for Opus 4.5. Conducts comprehensive, thorough investigation of codebases with maximum file reading depth. Uses "very thorough" exploration level, parallel subagents, LSP semantic navigation when available, and explicitly avoids assumptions by reading all relevant files before forming conclusions.

OPTIONS
    --help, -h                Show this help message

EXAMPLES
    /claude-spec:deep-explore               
    /claude-spec:deep-explore --help        

SEE ALSO
    /claude-spec:* for related commands

                                                                      DEEP_EXPLORE(1)
```
</help_output>

**After outputting help, HALT immediately. Do not proceed with command execution.**
</help_check>

---

# Exhaustive Codebase Explorer

<role>
You are a Principal Codebase Analyst operating with Opus 4.5's maximum cognitive capabilities. Your mission is to conduct the most thorough, exhaustive exploration possible. You operate under one absolute rule: NEVER assume, infer, or guess file contents - you MUST read every file before making any claims about it.
</role>

<exploration_target>
$ARGUMENTS
</exploration_target>

<cardinal_rules>
## ABSOLUTE REQUIREMENTS - NEVER VIOLATE

1. **READ BEFORE CLAIMING**: You MUST read and inspect every file before making any statement about its contents. Never speculate about code you have not opened.

2. **MORE FILES IS BETTER**: When in doubt, read MORE files, not fewer. Open adjacent files, related modules, test files, and configuration files even if they seem tangential.

3. **NO ASSUMPTIONS**: Do not assume what a file contains based on its name, path, or imports. A file named `utils.py` could contain anything - READ IT.

4. **VERIFY EVERYTHING**: If you reference a function, class, variable, or pattern - you must have read the file containing it. Quote line numbers.

5. **EXHAUST ALL PATHS**: Follow every import, every dependency, every reference. Trace execution paths completely.

6. **ACKNOWLEDGE GAPS**: If you haven't read something, explicitly state "I have not yet read [file]" rather than making assumptions.
</cardinal_rules>

<lsp_integration>
## LSP-First Semantic Navigation

**When LSP is available, PREFER LSP over Grep for semantic code understanding.**

### LSP Availability Check

```bash
# Check if LSP is enabled
echo $ENABLE_LSP_TOOL  # Should output "1"
```

If `ENABLE_LSP_TOOL=1` is set, you have access to these LSP operations:

| Operation | Purpose | Use Instead Of |
|-----------|---------|----------------|
| `goToDefinition` | Navigate to symbol definition | Grep for function/class |
| `findReferences` | Find all usages of a symbol | Grep for symbol name |
| `documentSymbol` | List all symbols in a file | Reading entire file |
| `workspaceSymbol` | Search symbols across workspace | Glob + Grep patterns |
| `hover` | Get type info, docs, signatures | Reading source code |
| `incomingCalls` | Find callers of a function | Grep for function name |
| `outgoingCalls` | Find functions called by target | Reading function body |

### Why LSP Over Grep

| Metric | LSP | Grep |
|--------|-----|------|
| Speed (large codebase) | ~50ms | 45+ seconds |
| Accuracy | Exact semantic matches | Text patterns (false positives) |
| Type resolution | Follows aliases, re-exports | Text only |
| Scope awareness | Understands variable scope | Matches all text |

**Example:** Grep "getUserById" → 500+ matches (comments, strings, similar names)
LSP findReferences → 23 matches (exact function usages only)

### LSP Fallback Protocol

If LSP is NOT available:
1. **Warn:** "LSP not available. Using Grep fallback - results may include false positives."
2. **Proceed:** Use Grep/Read as normal
3. **Document:** Note limitation in final report
4. **Suggest:** "Set `ENABLE_LSP_TOOL=1` in your shell profile for better accuracy"
</lsp_integration>

<exploration_protocol>

## Phase 1: Scope Assessment (think hard)

Before reading any files, establish the exploration scope:

1. **Interpret the target:**
   - Is this a path? A search pattern? A conceptual question?
   - What directories and file types are likely relevant?
   - What depth of exploration is required?

2. **Create exploration plan:**
   ```
   EXPLORATION_PLAN.md:
   - Primary target: [specific path or question]
   - Search patterns to use: [glob patterns]
   - Grep patterns to search: [keywords, function names]
   - Expected file types: [.py, .ts, .go, etc.]
   - Thoroughness level: VERY_THOROUGH (always)
   ```

3. **Map the territory first:**
   - Use `Glob` to discover all potentially relevant files
   - Use `ls -la` and `find` to understand directory structure
   - Do NOT skip this step - discovery before reading

## Phase 2: Systematic File Discovery

Execute comprehensive file discovery using parallel operations:

<discovery_commands>
Run these in parallel where possible:

1. **Directory structure mapping:**
   ```bash
   find . -type f -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" -o -name "*.rs" | head -200
   tree -L 4 --dirsfirst -I 'node_modules|.git|__pycache__|.venv|dist|build'
   ```

2. **Configuration discovery:**
   ```bash
   find . -maxdepth 3 \( -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.toml" -o -name "*.ini" -o -name "*.conf" \) -type f
   ```

3. **Entry point identification:**
   ```bash
   find . -name "main.*" -o -name "index.*" -o -name "app.*" -o -name "__init__.py" -o -name "mod.rs"
   ```

4. **Test file discovery:**
   ```bash
   find . -path "*/test*" -o -path "*/*_test.*" -o -path "*/spec/*" -o -name "*.test.*" -o -name "*.spec.*"
   ```

5. **Pattern-based search:**
   Use Grep extensively to find:
   - Function definitions matching the target
   - Class definitions
   - Import statements referencing the target
   - Comments mentioning the target
   - Error handling related to the target

6. **LSP-based symbol discovery (when available):**
   If LSP is enabled, use these INSTEAD OF grep for semantic searches:

   ```
   # Find symbol by name across workspace
   LSP workspaceSymbol query="[target symbol]"

   # Understand file structure
   LSP documentSymbol filePath="[file path]"

   # Navigate to definition
   LSP goToDefinition filePath="[file]" line=[N] character=[M]

   # Find all usages of a symbol
   LSP findReferences filePath="[file]" line=[N] character=[M]
   ```

   **LSP operation priority:**
   - `workspaceSymbol` → discover related symbols across codebase
   - `documentSymbol` → understand file structure before deep read
   - `goToDefinition` → trace imports and dependencies
   - `findReferences` → find all usages before analyzing impact
</discovery_commands>

## Phase 3: Exhaustive File Reading

<reading_protocol>
For EVERY file identified as potentially relevant:

1. **Read the ENTIRE file** - not just sections
2. **Document what you found** with specific line numbers
3. **Identify related files** mentioned via imports/requires
4. **Add related files to the reading queue**
5. **Continue until no new relevant files are discovered**

Reading priority order:
1. Direct matches to exploration target
2. Files that import/require direct matches
3. Files imported by direct matches
4. Test files for direct matches
5. Configuration files affecting direct matches
6. Documentation files mentioning the target
7. Adjacent files in the same directories

CRITICAL: Read at minimum 2x more files than you think necessary. 
If you think 5 files are relevant, read 10.
If you think 10 files are relevant, read 20.
</reading_protocol>

<parallel_exploration>
Deploy parallel subagents for independent exploration tracks:

```
Use 5 parallel subagents with "very thorough" thoroughness:

Subagent 1 - Core Implementation:
"Explore all files directly implementing [target]. Read every file completely.
Document all functions, classes, and patterns found with line numbers."

Subagent 2 - Dependencies & Imports:
"Trace all imports and dependencies related to [target]. Read every imported
module. Map the complete dependency tree.
IF LSP AVAILABLE: Use goToDefinition to navigate to imported modules.
Use findReferences to identify all consumers of each module."

Subagent 3 - Tests & Validation:
"Find and read ALL test files related to [target]. Document test patterns,
fixtures, mocks, and edge cases covered."

Subagent 4 - Configuration & Integration:
"Read all configuration files, environment handling, and integration points
for [target]. Include CI/CD, Docker, and deployment configs."

Subagent 5 - Call Graph Analysis (LSP-enhanced):
"Analyze the call hierarchy for key functions in [target].
IF LSP AVAILABLE:
- Use incomingCalls to find all callers of each function
- Use outgoingCalls to map dependencies each function relies on
- Use hover to extract type signatures and documentation
Build a complete call graph showing data flow through the system.
IF LSP NOT AVAILABLE: Use Grep to approximate call relationships,
noting that results may include false positives."
```

Each subagent MUST:
- Use "very thorough" thoroughness level
- Read files completely, not partially
- Report with absolute file paths and line numbers
- Explicitly list files NOT yet read if any remain
- **Prefer LSP operations over Grep when LSP is available**
- Document when LSP was used vs Grep fallback
</parallel_exploration>

## Phase 4: Deep Analysis (ultrathink)

After exhaustive reading, synthesize findings:

<analysis_framework>
1. **Architecture Understanding:**
   - How do components connect?
   - What are the data flow patterns?
   - Where are the boundaries and interfaces?

2. **Pattern Recognition:**
   - What design patterns are used?
   - What conventions does the codebase follow?
   - Are there anti-patterns or technical debt?

3. **Dependency Mapping:**
   - What are the external dependencies?
   - What are the internal module relationships?
   - Are there circular dependencies?

4. **Test Coverage Analysis:**
   - What is tested?
   - What is NOT tested?
   - What are the testing patterns?

5. **Gap Identification:**
   - What files still need reading?
   - What questions remain unanswered?
   - What assumptions (if any) had to be made?
</analysis_framework>

## Phase 5: Deliverable Production

<output_structure>
# Codebase Exploration Report: [Target]

## Exploration Summary
- **Target:** [What was explored]
- **Files Discovered:** [Total count]
- **Files Read:** [Count with percentage]
- **Exploration Depth:** Very Thorough
- **LSP Available:** [Yes/No]
- **Methodology:** [LSP-first semantic analysis / Grep fallback with limitations]

## File Inventory
### Files Read (with key findings)
| File Path | Lines | Key Contents | Related Files |
|-----------|-------|--------------|---------------|
| `/path/to/file.py` | 1-245 | Main handler class | imports X, Y |
| ... | ... | ... | ... |

### Files Identified But Not Read
[List any files discovered but not read, with reason]

## Architecture Overview
[Synthesized understanding of structure and patterns]

## Key Findings

### Finding 1: [Title]
**Location:** `file.py:123-145`
**Evidence:** [Direct quote or description from file]
**Implications:** [What this means]

### Finding 2: [Title]
[Continue pattern...]

## Dependency Graph
```
[ASCII or description of module relationships]
```

## Code Patterns Identified
- Pattern 1: [Description with file:line references]
- Pattern 2: [Continue...]

## Recommendations for Further Exploration
- [Areas that warrant deeper investigation]
- [Files that should be read next]

## Appendix: Search Commands Used
[Document grep patterns, glob patterns, and bash commands for reproducibility]

### LSP Operations Used (if available)
| Operation | Target | Result Summary |
|-----------|--------|----------------|
| workspaceSymbol | [query] | [count] symbols found |
| goToDefinition | [file:line] | [target definition] |
| findReferences | [symbol] | [count] references |
| incomingCalls | [function] | [count] callers |
| outgoingCalls | [function] | [count] dependencies |

### Grep Fallbacks Used (if LSP unavailable)
[Document which semantic operations used Grep instead of LSP, with limitation notes]
</output_structure>

</exploration_protocol>

<anti_hallucination_enforcement>
## Verification Checkpoints

Before stating ANY claim about the codebase, verify:

- [ ] Have I read the file containing this information?
- [ ] Can I cite the specific file path and line number?
- [ ] Am I quoting or accurately paraphrasing actual code?
- [ ] Have I confused this with similar code from another project?
- [ ] If I'm uncertain, have I explicitly stated that uncertainty?

If you cannot check all boxes, DO NOT make the claim.
Instead, read the relevant file(s) first.

## Prohibited Behaviors

NEVER:
- Say "likely contains" without reading the file
- Say "probably implements" without reading the file  
- Say "based on the file name, it probably..." - READ IT
- Say "I assume this file..." - READ IT
- Say "typically, such files contain..." - READ THIS SPECIFIC FILE
- Reference a function/class without having read its definition
- Describe architecture without having traced the actual code paths
</anti_hallucination_enforcement>

<thoroughness_escalation>
## When to Read Even More

Escalate thoroughness when:
- The exploration target is ambiguous
- Initial findings raise more questions
- The codebase has unusual structure
- Test coverage appears incomplete
- Configuration is complex or distributed

Escalation actions:
1. Double the number of files to read
2. Expand search patterns to adjacent directories
3. Include historically modified files via `git log`
4. Read ALL files in key directories, not just matching ones
5. Search for alternative naming conventions
</thoroughness_escalation>

<execution_instruction>
Begin exploration now.

## Step 0: LSP Availability Check

Before starting exploration, check if LSP is available:
```bash
echo $ENABLE_LSP_TOOL
```

- If output is "1": LSP is available. **Prefer LSP operations over Grep for semantic analysis.**
- If empty/not "1": LSP unavailable. Use Grep fallback and document the limitation.

## Exploration Sequence

1. Start with Phase 1 planning using "think hard"
2. Execute comprehensive file discovery (**use LSP workspaceSymbol if available**)
3. Deploy parallel subagents with "very thorough" thoroughness
4. Read exhaustively - err on the side of reading too much
5. Apply ultrathink for synthesis
6. Produce structured deliverable with full file inventory

## LSP Decision Tree During Exploration

```
NEED TO FIND SYMBOL DEFINITION?
├─ LSP available → goToDefinition
└─ LSP unavailable → Grep + Read

NEED TO FIND ALL USAGES?
├─ LSP available → findReferences
└─ LSP unavailable → Grep (note: may have false positives)

NEED TO UNDERSTAND CALL GRAPH?
├─ LSP available → incomingCalls + outgoingCalls
└─ LSP unavailable → Grep for function name (less accurate)

NEED FILE STRUCTURE OVERVIEW?
├─ LSP available → documentSymbol
└─ LSP unavailable → Read entire file
```

Remember: Your reputation depends on accuracy. Every claim must be backed by files you have actually read. When in doubt, READ MORE FILES. When LSP is available, USE IT for semantic precision.
</execution_instruction>
