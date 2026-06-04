---
name: close-case
description: This skill should be used when the user asks to "close the case", "conclude the investigation", "wrap up", "present findings", or when the convergence check indicates the case has been solved. Produces the final resolution with complete evidence chain.
---

# Close Case — Conclude Investigation with Resolution

Produce the final investigation resolution: a confirmed conclusion supported by a complete, traceable evidence chain from initial clues to final answer.

## MCP-first closing

For Detective v2/v2.1 cases:

1. Call `detective_convergence_status`.
2. If converged, call `detective_export_markdown` and `detective_export_mermaid`.
3. If not converged, present unmet conditions and ask whether to continue, discuss, or force a partial close.
4. Use Detective MCP tools for any conclusion, close marker, state change, or export artifact.
5. Do not edit `case.json` directly.

Do not create resolution files under `.detective/` by hand for v2/v2.1 cases. MCP export tools produce the Markdown and Mermaid outputs.

## Closing Process

### 1. Check Convergence

Call `detective_convergence_status` before closing.

- If converged → proceed with MCP-backed closing.
- If not converged → present the unmet conditions and ask: "Continue investigating, discuss the case, or force a partial close?"
- If the MCP server is unavailable for a v2/v2.1 case → stop and ask the user to check `/mcp`.

### 2. Identify the Conclusion

Use MCP-provided graph state, not manual file inspection:

1. Call `detective_graph_overview`.
2. Call `detective_list_nodes` for active hypotheses, conclusions, constraints, open questions, and evidence.
3. Call `detective_list_edges` to trace support, contradiction, derivation, and elimination relationships.
4. Select the converged conclusion or the highest-confidence partial conclusion if the user explicitly chose partial close.

### 3. Trace the Evidence Chain

Build the explanation from MCP-returned nodes and edges:

1. Start from the confirmed or partial conclusion.
2. Follow supporting and deriving edges back to the evidence and initial observations.
3. Include eliminated alternatives and the evidence or constraints that ruled them out.
4. Call MCP tools for any conclusion state that must be recorded.

Present the chain in conversation:

```
1. [Crime Scene] <initial observation>
2. [Clue → Evidence] <first finding> (verified by: <action>)
3. [Evidence] <second finding> (supports hypothesis via: <reasoning>)
4. [Constraint] <elimination rule> (eliminated alternatives: <list>)
5. [Conclusion] <final answer> (confidence: <X>)
```

### 4. Export Reports

For v2/v2.1 cases, use MCP exports only:

1. Call `detective_export_markdown`.
2. Call `detective_export_mermaid`.
3. Report the paths or artifact identifiers returned by those tools.

### 5. Present to User

Display the resolution in conversation:

```
## Case Closed: <title>

**Conclusion**: <answer>
**Confidence**: <X>%
**Evidence Chain**: <count> links, fully traced

<brief narrative of how we got here>

Markdown export: <path returned by detective_export_markdown>
Mermaid export: <path returned by detective_export_mermaid>
```

## Forced Close (Partial Resolution)

When closing without full convergence:

- State that this is a partial resolution.
- Explicitly list unmet convergence conditions.
- List remaining open questions and caveats.
- Use MCP tools for any partial-close state or export.
- Ask the user whether to continue, discuss, or accept the partial close.

## Legacy v1 fallback

The historical script workflow is a deprecated fallback for legacy v1 flat JSON case files only when MCP is unavailable. It is not valid for v2/v2.1 cases.

For legacy v1 inspection only:

```bash
python $PLUGIN_ROOT/scripts/convergence.py .detective/cases/<case-id>.json
```

If a legacy v1 close requires manual reporting or state changes, ask the user for explicit confirmation first and label the result as a legacy fallback. For v2/v2.1, use Detective MCP tools instead.

## Additional Resources

### Scripts
- **`scripts/convergence.py`** — Legacy v1 convergence inspection
- **`scripts/board.py`** — Legacy v1 board inspection and deprecated mutation helpers
