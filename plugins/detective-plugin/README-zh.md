# Detective v0.4 — OODA 原生调查 MCP

Detective 是一个用于结构化调查的 Claude Code 插件。v0.4 是破坏性版本：公开接口只保留一套 MCP API、一套项目本地 JSON 案件模型，以及一套 OODA 原生生命周期。旧版 v1 scripts、迁移 API、scheduler next_actions API，以及独立的 convergence/deadlock API 都不再保留。

## 模型

案件存储在 `.detective/cases/<case-id>/case.json`，只能通过 MCP 工具修改。案件包含：

- `nodes`：观察、线索、证据、假设、约束、结论、问题、任务。
- `edges`：有向推理关系：`supports`、`contradicts`、`derives`、`requires`、`eliminates`、`related_to`。
- `ooda`：当前阶段与调查意图。
- `blackboard`：可提升为图节点的临时记录。
- `actions`：待办、执行中、已完成的调查工作。
- `coverage`：调查范围与覆盖状态。
- `proofs`、`checkpoints`、`events`、`closure`：审计轨迹与完成门状态。

生命周期是 OODA：观察 → 定向 → 决策 → 行动 → 复盘。使用 `detective_transition_phase` 记录阶段，使用 intents 记录目标，使用 actions 执行工作，只有在 `detective_completion_gate` 允许后才结案；若未通过，则需要用户明确选择强制结案。调查技能应自主推进 OODA 循环，直到完成门通过或出现明确停止条件。

当运行环境提供 SetGoal 或等价目标工具时，Detective 技能可以把它用于会话编排：案件创建后，目标应包含 case id、调查意图、完成标准，以及自主推进 OODA 的要求。这不替代 `detective_open_case` 或 MCP 案件状态；`.detective/cases/<case-id>/case.json` 仍是权威状态，并且只能通过 MCP 工具修改。

## StopHook 兜底

SetGoal 或等价的目标驱动续跑机制是推进活跃调查的首选方式。插件同时提供一个基于提示词的 Stop hook 作为安全兜底，但静态注册默认是惰性的：除非 transcript 中出现显式激活标记，否则 hook 会立即允许停止。

动态激活依赖 transcript，而不是文件系统。Skills 不得通过编辑 `.detective/` 文件或 hook 文件来控制兜底。只有当没有 SetGoal 等价工具可用时，`/detective:open-case` 或 `/detective:investigate` 才可以在持久 MCP 案件创建后输出简短可见标记：

```xml
<DETECTIVE-STOP-FALLBACK status="active" case-id="<case_id>">
```

在用户暂停/停止、案件阻塞、预算/时间盒/步数耗尽、完成或结案时，输出匹配的停用标记：

```xml
<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="<pause|blocked|budget-exhausted|complete|closed>">
```

对每个 case id，最新标记生效。只有该 case id 的最新标记是 `status="active"` 时，兜底才处于激活状态；同一 case id 后续的 `status="inactive"` 会解除激活。Hook 不得仅凭打开/活跃的 Detective 案件推断激活。Brainstorm 在用户批准并创建持久 MCP 案件之前绝不发出激活标记。Review 和 discussion 保持当前状态，除非它们发现需要停止/停用的条件。

当标记处于 active 时，Stop hook 仍必须在以下情况允许停止：案件已关闭或完成门已通过；用户要求停止或暂停；正在等待只能由用户决定的事项；案件受阻或没有合法行动；预算或 `max_actions` 耗尽；目标机制已激活/可用；非 Detective 任务或测试已完成；或上下文显示 StopHook 反复阻止/行动循环。只有在标记对应案件尚未完成、没有目标机制可用、且仍有具体合法有用的下一步 OODA 行动时，才会阻止停止。

Claude Code 在会话启动时加载插件 hooks。该标记协议不会真正热添加或热移除 hook；它只让已经注册的 Stop hook 根据 transcript 上下文 fail-open 或参与判断。真正的 hook 加载变更需要重启 Claude Code，Detective 不会尝试热加载。

## 精确公开 MCP 工具

- `detective_open_case`
- `detective_load_case`
- `detective_graph_overview`
- `detective_case_status`
- `detective_transition_phase`
- `detective_add_intent`
- `detective_list_intents`
- `detective_add_node`
- `detective_update_node`
- `detective_delete_node`
- `detective_get_node`
- `detective_list_nodes`
- `detective_search_nodes`
- `detective_add_edge`
- `detective_get_edge`
- `detective_update_edge`
- `detective_delete_edge`
- `detective_list_edges`
- `detective_neighbors`
- `detective_shortest_path`
- `detective_export_markdown`
- `detective_export_mermaid`
- `detective_add_action`
- `detective_update_action`
- `detective_list_actions`
- `detective_add_checkpoint`
- `detective_blackboard_add`
- `detective_blackboard_list`
- `detective_blackboard_update`
- `detective_blackboard_promote`
- `detective_coverage_add`
- `detective_coverage_update`
- `detective_coverage_status`
- `detective_evaluate_proof`
- `detective_completion_gate`
- `detective_close_case`
- `detective_list_events`

## v0.4 已移除

- 旧公开 API 不再恢复。

完成门要求且仅允许一个 `status="confirmed"` 的 `hypothesis` 节点，并且它必须被 `status="confirmed"` 的 `evidence` 节点通过 `supports` 边直接支持；同时不能有开放的替代假设、问题或行动，覆盖范围必须完整。
- 旧版 v1 scripts 与兼容 helper 模块。
- 加载时 schema 迁移。v0.4 只创建并接受 schema `4.0` 案件。

## 使用方式

```bash
/detective:brainstorm
/detective:open-case "调查这次回归的根因"
/detective:investigate
/detective:review-board
/detective:discuss-case
/detective:close-case
```

Skills 和 agents 必须通过 MCP 工具读写状态，不能直接编辑 `.detective/` 文件。

## 存储与导出

权威状态：

```text
.detective/cases/<case-id>/case.json
.detective/cases/<case-id>/events.jsonl
```

生成视图：

```text
.detective/cases/<case-id>/notes.md
.detective/cases/<case-id>/graph.mmd
```

JSON 是唯一权威状态；Markdown 与 Mermaid 是可重新生成的视图。
