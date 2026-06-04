# Detective v2 MCP Graph Core Design

## Summary

Detective v2 adds a local Python MCP server to `plugins/detective-plugin` and makes it the canonical graph-state interface for open-ended investigations. The server exposes typed tools for case creation, clue/evidence/hypothesis nodes, relationship edges, graph search, shortest paths, overview queries, and Markdown/Mermaid exports. It stores canonical state as JSON under the current project's `.detective/` directory.

The goal is to turn detective from a skill-driven workflow that shells out to Python scripts into a reusable investigation graph service that Claude and subagents can call directly.

## Goals

- Provide a generic, domain-neutral investigation graph core.
- Register the core as a plugin-provided stdio MCP server using `uv` in `.mcp.json`.
- Persist case state locally in `.detective/cases/<case-id>/case.json`.
- Keep JSON as the only canonical state source.
- Generate human-readable Markdown and Mermaid files from JSON.
- Support graph operations needed by open/semi-open research tasks: overview, list nodes, search nodes, neighbors, shortest path.
- Preserve compatibility with existing detective skills and scripts during the v2 transition.

## Non-goals

- Do not implement autonomous multi-agent dispatch in v2.
- Do not make the MCP server call Claude or other LLM APIs.
- Do not replace all existing skills/scripts immediately.
- Do not add a browser UI.
- Do not add cross-case learning or long-term strategy memory in v2.
- Do not implement advanced convergence scoring in v2.

## Architecture

```text
Claude / subagents
   │
   │ MCP tools
   ▼
detective MCP server
   │
   ├─ models: Case, Node, Edge, Action/Event
   ├─ store: load/save JSON from .detective/
   ├─ graph: search, neighbors, shortest path, overview
   └─ exports: Markdown and Mermaid projections
   │
   ▼
.detective/cases/<case-id>/
   ├─ case.json
   ├─ notes.md
   ├─ graph.mmd
   └─ events.jsonl
```

The MCP server owns state mutation. Claude and future agents should not edit `case.json` directly.

## Plugin file layout

Add these files under `plugins/detective-plugin`:

```text
plugins/detective-plugin/
├── .mcp.json
├── pyproject.toml
├── uv.lock
├── detective_mcp/
│   ├── __init__.py
│   ├── server.py
│   ├── models.py
│   ├── store.py
│   ├── graph.py
│   ├── exports.py
│   └── ids.py
├── skills/
├── agents/
└── scripts/
```

Existing `scripts/board.py`, `scripts/scoring.py`, and `scripts/convergence.py` remain in place for v1 compatibility.

## MCP registration

Create `plugins/detective-plugin/.mcp.json`:

```json
{
  "detective": {
    "command": "uv",
    "args": [
      "--directory",
      "${CLAUDE_PLUGIN_ROOT}",
      "run",
      "python",
      "-m",
      "detective_mcp.server"
    ]
  }
}
```

This uses the plugin root as the uv project directory and avoids hardcoded Python paths.

## Storage model

Cases are stored in the user's current working project, not inside the plugin cache:

```text
.detective/
└── cases/
    └── <case-id>/
        ├── case.json
        ├── notes.md
        ├── graph.mmd
        └── events.jsonl
```

`case.json` is canonical. `notes.md` and `graph.mmd` are regenerated projections. `events.jsonl` is append-only and records mutations for debugging and future replay.

## Data model

### Case

```json
{
  "schema_version": "2.0",
  "id": "case_...",
  "title": "...",
  "description": "...",
  "created_at": "...",
  "updated_at": "...",
  "config": {
    "autonomy": "manual | checkpoint | full_auto",
    "checkpoint_interval": 5,
    "max_actions": 50
  },
  "nodes": [],
  "edges": [],
  "actions": []
}
```

Default autonomy is `full_auto`, but user intervention overrides automated decisions.

### Node

```json
{
  "id": "n_...",
  "type": "observation | clue | evidence | hypothesis | constraint | conclusion | question | task",
  "status": "open | verified | rejected | stale | resolved",
  "content": "...",
  "confidence": 0.5,
  "source": "user | agent | tool | file | web | mcp | system",
  "tags": [],
  "created_by": "...",
  "created_at": "...",
  "updated_at": "...",
  "metadata": {}
}
```

### Edge

```json
{
  "id": "e_...",
  "from_id": "n_...",
  "to_id": "n_...",
  "type": "supports | contradicts | derives | requires | eliminates | related_to",
  "confidence": 0.5,
  "rationale": "...",
  "created_by": "...",
  "created_at": "...",
  "metadata": {}
}
```

## MCP tool set

### Case lifecycle

#### `detective_open_case`

Creates a new case directory and `case.json`.

Inputs:

```json
{
  "title": "string",
  "description": "string",
  "case_id": "optional string",
  "config": "optional object"
}
```

Returns:

```json
{
  "case_id": "case-id",
  "case_path": ".detective/cases/<case-id>/case.json"
}
```

#### `detective_load_case`

Loads a case into server memory.

Inputs:

```json
{ "case_id": "string" }
```

Returns a compact case summary.

#### `detective_save_case`

Flushes in-memory state to disk.

Inputs:

```json
{ "case_id": "string" }
```

Returns save status and path.

#### `detective_graph_overview`

Returns counts, active hypotheses, evidence counts, unresolved questions, and graph density.

Inputs:

```json
{ "case_id": "string" }
```

### Nodes

#### `detective_add_node`

Adds a node and persists the case.

Inputs:

```json
{
  "case_id": "string",
  "type": "string",
  "content": "string",
  "status": "optional string",
  "confidence": "optional number",
  "source": "optional string",
  "tags": "optional string array",
  "created_by": "optional string",
  "metadata": "optional object"
}
```

#### `detective_update_node`

Updates allowed node fields: status, content, confidence, tags, metadata.

#### `detective_get_node`

Fetches one node by ID.

#### `detective_list_nodes`

Lists nodes with optional filters:

```json
{
  "case_id": "string",
  "type": "optional string",
  "status": "optional string",
  "tag": "optional string",
  "limit": "optional integer"
}
```

#### `detective_search_nodes`

Searches node content and tags with simple local matching.

Inputs:

```json
{
  "case_id": "string",
  "query": "string",
  "types": "optional string array",
  "limit": "optional integer"
}
```

### Edges

#### `detective_add_edge`

Adds a relationship between two existing nodes.

Inputs:

```json
{
  "case_id": "string",
  "from_id": "string",
  "to_id": "string",
  "type": "string",
  "confidence": "optional number",
  "rationale": "optional string",
  "created_by": "optional string",
  "metadata": "optional object"
}
```

The server validates that both endpoint nodes exist.

#### `detective_list_edges`

Lists edges with optional filters by type, source node, or target node.

#### `detective_neighbors`

Returns incoming and outgoing neighbors for a node.

### Graph algorithms

#### `detective_shortest_path`

Finds the shortest path between two nodes. MVP uses unweighted BFS over directed edges, with an option to treat edges as undirected.

Inputs:

```json
{
  "case_id": "string",
  "from_id": "string",
  "to_id": "string",
  "undirected": "optional boolean"
}
```

Returns ordered nodes and edges, or an empty result if no path exists.

### Exports

#### `detective_export_markdown`

Regenerates `notes.md` from `case.json`.

Output sections:

- Title and description
- Overview statistics
- Active hypotheses
- Evidence
- Constraints
- Open questions
- Key relationships
- Recent actions

#### `detective_export_mermaid`

Regenerates `graph.mmd` from `case.json`.

MVP uses Mermaid `graph LR` with node labels and edge labels.

## Markdown and Mermaid projection rules

Markdown and Mermaid are read surfaces, not state sources.

Allowed flow:

```text
case.json → notes.md
case.json → graph.mmd
```

Disallowed flow in v2:

```text
notes.md → case.json
```

This avoids lossy or ambiguous parsing.

## Concurrency and consistency

The MVP server runs as a local stdio MCP process. It should keep a small in-memory case cache and write through on every mutation.

Minimum consistency rules:

- Validate node IDs before adding edges.
- Persist after every mutation.
- Append mutation events to `events.jsonl`.
- Update `updated_at` on case/node changes.
- Return clear errors for missing cases, missing nodes, invalid edge types, and malformed inputs.

File locking can be deferred unless real multi-process write conflicts appear.

## Error handling

The server should return structured errors for:

- Case not found.
- Node not found.
- Edge endpoint missing.
- Invalid node type.
- Invalid edge type.
- JSON persistence failure.
- Export failure.

Errors should mention the case ID and the invalid field when relevant.

## Migration and compatibility

v2 does not need automatic migration from v1 case files in the first implementation.

Compatibility strategy:

1. Keep v1 scripts and skills unchanged.
2. Add MCP tools in parallel.
3. Update README to document v2 MCP usage.
4. Later, update skills to prefer MCP tools when available.
5. Add migration from v1 `fragments/threads` to v2 `nodes/edges` in a later release if needed.

## Testing strategy

Add tests for:

- Case creation persists expected directory/files.
- Add/list/get/update node.
- Add/list edge and reject missing endpoints.
- Search nodes by content and tag.
- Neighbors query.
- Shortest path over directed and undirected graphs.
- Markdown export includes hypotheses/evidence/constraints.
- Mermaid export includes node and edge labels.
- Reloading a case preserves state.

Use temporary directories in tests so `.detective/` writes do not affect the real repo.

## Acceptance criteria

- `plugins/detective-plugin/.mcp.json` registers a uv-launched stdio MCP server.
- MCP tools are discoverable in Claude Code after enabling the plugin.
- A user can open a case, add nodes and edges, list/search nodes, get graph overview, compute a shortest path, and export Markdown/Mermaid.
- All canonical state is stored under `.detective/cases/<case-id>/case.json` in the current project.
- Existing detective-plugin v1 scripts remain present and usable.

## Example workflow

```text
1. detective_open_case(title="Investigate unknown regression", description="...")
2. detective_add_node(type="observation", content="Regression started after config change")
3. detective_add_node(type="hypothesis", content="Config drift caused the regression")
4. detective_add_edge(type="supports", from_id=<observation>, to_id=<hypothesis>)
5. detective_graph_overview(case_id=...)
6. detective_export_markdown(case_id=...)
7. detective_export_mermaid(case_id=...)
```
