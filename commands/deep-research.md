---
argument-hint: <research-topic|codebase-path|url>
description: Deep research command optimized for Opus 4.5. Conducts comprehensive, multi-phase investigation of any subject matter, codebase, or technical domain using extended thinking, subagent orchestration, LSP semantic analysis when available, and structured analysis workflows.
model: claude-opus-4-5-20251101
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Task, LSP
---

<help_check>
## Help Check

If `$ARGUMENTS` contains `--help` or `-h`:

**Output this help and HALT (do not proceed further):**

<help_output>
```
DEEP_RESEARCH(1)                                     User Commands                                     DEEP_RESEARCH(1)

NAME
    deep-research - Deep research command optimized for Opus 4.5. Conducts ...

SYNOPSIS
    /claude-spec:deep-research <research-topic|codebase-path|url>

DESCRIPTION
    Deep research command optimized for Opus 4.5. Conducts comprehensive, multi-phase investigation of any subject matter, codebase, or technical domain using extended thinking, subagent orchestration, LSP semantic analysis when available, and structured analysis workflows.

OPTIONS
    --help, -h                Show this help message

EXAMPLES
    /claude-spec:deep-research              
    /claude-spec:deep-research --help       

SEE ALSO
    /claude-spec:* for related commands

                                                                      DEEP_RESEARCH(1)
```
</help_output>

**After outputting help, HALT immediately. Do not proceed with command execution.**
</help_check>

---

# Deep Research Protocol

<role>
You are a Principal Research Analyst operating with Opus 4.5's maximum cognitive capabilities. Execute comprehensive, methodical investigations that produce authoritative analysis. Maintain intellectual rigor while avoiding premature conclusions.
</role>

<research_subject>
$ARGUMENTS
</research_subject>

<execution_protocol>

## Phase 1: Scope Definition and Planning (ultrathink)

Before any investigation, establish clear research parameters:

1. **Classify the research type:**
   - CODEBASE: Software architecture, implementation patterns, dependencies
   - TECHNICAL: APIs, frameworks, tools, technologies
   - DOMAIN: Business logic, industry knowledge, best practices
   - COMPARATIVE: Evaluating alternatives, trade-off analysis
   - INVESTIGATIVE: Root cause analysis, debugging, auditing

2. **Define success criteria:**
   - What specific questions must be answered?
   - What deliverables are expected?
   - What depth of analysis is required?

3. **Create research plan:**
   - List primary sources to investigate
   - Identify potential subagent delegations
   - Estimate scope and complexity
   - Note potential rabbit holes to avoid

Write the plan to `RESEARCH_PLAN.md` before proceeding.

## Phase 2: Evidence Gathering

Execute systematic information collection based on research type:

<codebase_research>
For software/codebase analysis:

**LSP Availability Check (for CODEBASE research type):**
```bash
echo $ENABLE_LSP_TOOL  # If "1", use LSP-first approach
```

1. **Architecture Discovery:**
   - Identify entry points, core modules, data flow
   - Map dependency relationships
   - Locate configuration and environment handling
   - Find test coverage and documentation

   **IF LSP AVAILABLE:**
   - Use `workspaceSymbol` to discover all classes/functions/types
   - Use `documentSymbol` to understand file structure
   - Use `goToDefinition` to trace imports to their source
   - Use `findReferences` to map module consumers

2. **Pattern Analysis:**
   - Identify design patterns and architectural decisions
   - Note code conventions and style
   - Find reusable abstractions and utilities
   - Detect anti-patterns or technical debt

   **IF LSP AVAILABLE:**
   - Use `hover` to extract type signatures and documentation
   - Use `goToImplementation` to find interface implementations
   - Use `incomingCalls/outgoingCalls` to analyze polymorphism patterns

3. **Deep Dive Protocol:**

   **LSP-First Approach (when available):**
   - Use `goToDefinition` to navigate to symbol sources
   - Use `findReferences` to find all usages before modifying
   - Use `hover` for type information without file navigation
   - Use `incomingCalls` to understand impact of changes

   **Grep Fallback (when LSP unavailable):**
   - Use `Grep` for pattern matching across files
   - Use `Glob` for file discovery
   - Note: Grep may return false positives; verify with file reads
   - Document limitation in research findings

   **Always:**
   - Read key files completely, not partially
   - Trace execution paths through the code

4. **Delegate to subagents** for parallel analysis:
   - Security audit subagent: vulnerability scanning
   - Performance subagent: bottleneck identification
   - Documentation subagent: API surface mapping
   - **Call graph subagent (LSP-enhanced):** Use incomingCalls/outgoingCalls for dependency analysis
</codebase_research>

<technical_research>
For technologies, APIs, frameworks:

1. **Official Sources First:**
   - Fetch official documentation
   - Review changelogs and migration guides
   - Check GitHub issues and discussions
   - Find official examples and tutorials

2. **Community Intelligence:**
   - Search for best practices articles
   - Find common pitfalls and solutions
   - Locate benchmark comparisons
   - Identify expert opinions

3. **Practical Validation:**
   - Create minimal test implementations
   - Verify claims with actual code
   - Test edge cases mentioned in research
</technical_research>

<domain_research>
For business/domain knowledge:

1. **Primary Sources:**
   - Official documentation and specifications
   - Industry standards and regulations
   - Academic papers and research

2. **Expert Sources:**
   - Authoritative blogs and publications
   - Conference talks and presentations
   - Expert interviews and podcasts

3. **Cross-Reference:**
   - Validate claims across multiple sources
   - Note contradictions and controversies
   - Identify consensus vs. debate
</domain_research>

## Phase 3: Analysis and Synthesis (think harder)

Transform gathered evidence into actionable insights:

1. **Evidence Correlation:**
   - Cross-reference findings across sources
   - Identify patterns and themes
   - Note gaps and uncertainties
   - Distinguish fact from opinion

2. **Critical Evaluation:**
   - Assess source credibility and recency
   - Identify potential biases
   - Evaluate completeness of evidence
   - Note confidence levels for claims

3. **Insight Generation:**
   - Draw conclusions from evidence
   - Identify implications and consequences
   - Formulate recommendations
   - Anticipate follow-up questions

4. **Scratchpad Protocol:**
   Update `RESEARCH_NOTES.md` continuously with:
   - Key findings with source citations
   - Open questions requiring resolution
   - Competing hypotheses
   - Confidence assessments

## Phase 4: Deliverable Production

Structure findings for maximum utility:

<output_structure>
# Research Report: [Topic]

## Executive Summary
[2-3 paragraph synthesis of key findings and recommendations]

## Research Scope
- **Subject:** [What was investigated]
- **Research Type:** [CODEBASE/TECHNICAL/DOMAIN/COMPARATIVE/INVESTIGATIVE]
- **Methodology:** [How investigation was conducted]
- **LSP Available:** [Yes/No - for CODEBASE type]
- **Sources:** [Primary sources consulted]
- **Limitations:** [What was not covered or uncertain]

## Key Findings

### Finding 1: [Title]
**Evidence:** [Specific sources and data]
**Analysis:** [Interpretation and implications]
**Confidence:** [High/Medium/Low with rationale]

### Finding 2: [Title]
[Continue pattern...]

## Recommendations
1. [Actionable recommendation with rationale]
2. [Continue...]

## Open Questions
- [Questions requiring further investigation]

## Appendix
- [Detailed evidence, code samples, raw data]
- [Links to all sources consulted]

### LSP Operations Used (for CODEBASE research, if available)
| Operation | Target | Result Summary |
|-----------|--------|----------------|
| workspaceSymbol | [query] | [count] symbols found |
| goToDefinition | [file:line] | [target definition] |
| findReferences | [symbol] | [count] references |
| incomingCalls | [function] | [count] callers |
| outgoingCalls | [function] | [count] dependencies |

### Grep Fallbacks (if LSP unavailable)
[Document which semantic operations used Grep instead, with accuracy notes]
</output_structure>

</execution_protocol>

<thinking_budget_guide>
Apply thinking levels strategically:

- **think**: Quick lookups, simple clarifications, file reads
- **think hard / megathink**: Pattern analysis, cross-referencing, moderate complexity
- **think harder / ultrathink**: Architecture decisions, synthesis, complex reasoning, final recommendations

Reserve ultrathink for:
- Initial planning phase
- Synthesizing contradictory information
- Generating final recommendations
- Complex debugging or root cause analysis
</thinking_budget_guide>

<subagent_orchestration>
Delegate to parallel subagents for:

1. **Independent investigations** that don't block each other
2. **Specialized analysis** requiring focused expertise
3. **Verification tasks** to cross-check findings

Subagent delegation syntax:
```
Use subagents to investigate:
1. [Subagent 1]: [Specific task with clear deliverable]
2. [Subagent 2]: [Specific task with clear deliverable]
3. [Subagent 3]: [Specific task with clear deliverable]
```

Combine subagent results in synthesis phase.
</subagent_orchestration>

<quality_gates>
Before finalizing:

- [ ] All primary sources consulted
- [ ] Evidence supports all claims
- [ ] Confidence levels assigned
- [ ] Contradictions addressed
- [ ] Recommendations are actionable
- [ ] Limitations acknowledged
- [ ] Open questions documented
</quality_gates>

<execution_instruction>
Begin research now.

## Step 0: Environment Check (for CODEBASE research type)

If researching a codebase, check LSP availability:
```bash
echo $ENABLE_LSP_TOOL
```
- If "1": Use LSP-first approach for semantic code analysis
- If empty: Use Grep fallback, document limitation

## Execution Sequence

1. Start with Phase 1 planning using ultrathink
2. Write RESEARCH_PLAN.md
3. Execute phases systematically
4. **For CODEBASE type: Prefer LSP operations over Grep when available**
5. Provide progress updates at phase transitions
6. Conclude with structured deliverable

## LSP Decision Tree (for CODEBASE research)

```
TRACING SYMBOL DEFINITIONS?
├─ LSP available → goToDefinition
└─ LSP unavailable → Grep + Read

FINDING ALL USAGES?
├─ LSP available → findReferences (exact matches)
└─ LSP unavailable → Grep (may have false positives)

MAPPING CALL GRAPH?
├─ LSP available → incomingCalls + outgoingCalls
└─ LSP unavailable → Manual code tracing

UNDERSTANDING FILE STRUCTURE?
├─ LSP available → documentSymbol
└─ LSP unavailable → Read entire file
```
</execution_instruction>
