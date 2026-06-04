# 侦探 — 基于调查方法论的通用问题解决框架

一个 Claude Code 插件，实现了基于侦探办案方法论的通用 AI 问题解决框架。每个问题都是一个**案件**；每个结论都有可追溯的**证据链**支撑。

## 核心概念

AI 维护一块**案件白板（CaseBoard）**——由**案情片段（Fragment）**和**红线（Thread）**构成的有向标签图。已交付的 v2 以本地 MCP 图核心为主接口，用于项目本地案件状态、图概览/查询、最短路径查询以及 Markdown/Mermaid 导出。

```text
当前已交付的 v2 MCP 核心：本地案件存储 + 图状态 + 图概览/查询 + 最短路径 + 导出
旧版 v1 工作流标签：审板(Scan) → 演化(Evolve) → 聚焦(Focus) → 行动(Act) → 归档(File)
规划中的 v2.1 编排：构建在 MCP 图核心之上的自主循环
```

## Fragment + Thread 模型

白板上只有两种基本单元：

**Fragment（案情片段）**——由两个维度描述的信息单元：

| 维度 | 取值 | 含义 |
|------|------|------|
| 成熟度 | 原始(Raw) → 线索(Clue) → 证据(Evidence) → 锚点(Anchor) | 信息的确定程度 |
| 角色 | 观察(Observation)、假设(Hypothesis)、约束(Constraint)、结论(Conclusion) | 在推理中的功能 |

**Thread（红线）**——Fragment 之间的有向标签连接：

| 类型 | 含义 |
|------|------|
| `supports` | 来源为目标提供证据支撑 |
| `contradicts` | 来源与目标矛盾 |
| `derives` | 目标由来源推导而出 |
| `eliminates` | 来源彻底证伪目标 |
| `requires` | 目标依赖来源 |

## 核心特性

- **MCP 图核心**：项目本地案件存储、图概览/搜索、最短路径和 Markdown/Mermaid 导出
- **旧版策略辅助逻辑**：v1 评分、约束传播、方向删减和收敛辅助逻辑仍作为 CLI 兼容 wrappers 存在，并委托共享 `detective_mcp` utilities
- **案情研讨**：在僵局、分歧或关键时刻与用户进行结构化讨论
- **全程可追溯**：每个结论都能沿证据链回溯到初始观察

## 使用方式

```
/detective:brainstorm
/detective:open-case "调查这次性能下降的根因"
/detective:investigate
/detective:review-board
/detective:discuss-case
/detective:close-case
```

| Skill | 用途 |
|-------|------|
| `brainstorm` | 脑暴：在正式立案前协作探索问题空间 |
| `open-case` | 立案：初始化调查，定义案发现场和目标 |
| `investigate` | 主循环：执行 审板→演化→聚焦→行动→归档 |
| `review-board` | 审板：展示白板状态、片段、红线、假设 |
| `discuss-case` | 研讨：在关键决策点进行结构化讨论 |
| `close-case` | 结案：输出结论 + 完整证据链回溯 |

## v2 MCP 图核心

Detective v2 提供一个通过 `.mcp.json` 注册、由 `uv` 启动的本地 stdio MCP 服务。v2 MCP 图核心是当前权威架构，新的工作流应优先通过 MCP 工具读写调查图状态。

核心工具：

- `detective_open_case`
- `detective_load_case`
- `detective_save_case`
- `detective_graph_overview`
- `detective_add_node`
- `detective_update_node`
- `detective_get_node`
- `detective_list_nodes`
- `detective_search_nodes`
- `detective_add_edge`
- `detective_list_edges`
- `detective_neighbors`
- `detective_shortest_path`
- `detective_export_markdown`
- `detective_export_mermaid`

权威状态存储在当前项目：

```text
.detective/cases/<case-id>/case.json
```

生成的人类可读产物保存在同一目录：

```text
.detective/cases/<case-id>/notes.md
.detective/cases/<case-id>/graph.mmd
.detective/cases/<case-id>/events.jsonl
```

JSON 是唯一权威状态源。Markdown 和 Mermaid 都是从 JSON 生成的视图。
旧版 scripts 仍可使用，但现在只是共享 detective_mcp utility 模块之上的薄 CLI wrapper。

## 架构

```
┌─────────────────────────────────────────────┐
│           Claude Code 会话                   │
│                                             │
│  ┌─────────┐   ┌──────────┐   ┌────────┐  │
│  │ Skills  │←→│ v2 MCP   │←→│案件白板 │  │
│  │         │   │ 图核心    │   │ (JSON) │  │
│  └─────────┘   └──────────┘   └────────┘  │
│       │              ↑                      │
│       └──── 旧版 CLI wrappers ─────────────┘
└─────────────────────────────────────────────┘
```

- **v2 MCP 图核心**：当前权威架构，用于读写项目本地的案件图状态。
- **案件白板**：权威 JSON 状态位于 `.detective/cases/<case-id>/case.json`；生成的 `notes.md`、`graph.mmd` 和 `events.jsonl` 与它保存在同一目录。
- **旧版 CLI wrappers**：旧版 v1 风格 scripts 继续作为兼容入口，并委托共享 `detective_mcp` utility 模块处理评分、约束和收敛辅助逻辑。
- **行动执行器**：Claude Code 本身——bash、文件操作、搜索、MCP 工具。

## 旧版评分兼容

旧版 Focus 阶段辅助逻辑用于回答："所有可能的下一步中，哪一步最值得做？"

```
Score(action) = (区分力 × 可行性) / 归一化成本
```

在已交付的 v2 中，这个评分仅作为构建在共享 MCP 图工具之上的旧版兼容辅助逻辑保留。当前交付的 MCP 图核心提供本地案件存储、图状态、图概览/查询、最短路径查询和导出；自主剪枝启发式并不是当前核心能力描述的一部分。

## 安装

```bash
# 本地测试
claude --plugin-dir /path/to/detective-plugin

# 或软链接到插件目录
ln -s /path/to/detective-plugin ~/.claude/plugins/detective
```

## 状态存储

当前 v2 案件状态存储在项目本地：

```text
.detective/cases/<case-id>/case.json
```

生成的审阅产物与权威 JSON 文件保存在同一目录：

```text
.detective/cases/<case-id>/notes.md
.detective/cases/<case-id>/graph.mmd
.detective/cases/<case-id>/events.jsonl
```

旧版 v1 案件文件使用扁平路径 `.detective/cases/<case-id>.json`；该路径仅为兼容旧数据和旧脚本保留。

## 适用领域

| 领域 | 假设是什么 | 证据是什么 |
|------|-----------|-----------|
| 安全研究 / 渗透测试 | 攻击向量 | 已确认的漏洞 |
| 情报分析 / OSINT | 候选解释 | 经交叉验证的情报 |
| 根因分析 / Debug | 故障模式 | 诊断结果 |
| 代码考古 | 设计意图 | 代码模式与历史 |

## 与破军（PoJun）的关系

| | 破军 | Detective 框架 |
|---|---|---|
| 架构 | 三进程分布式 | 本地 MCP 图核心 + 兼容 CLI wrappers |
| 状态 | SQLite + HTTP | 项目本地 JSON 案件图 |
| 实体 | origin/goal/fact/intent | Fragment + Thread（统一） |
| 循环 | OODA | Scan-Evolve-Focus-Act-File |
| 策略 | 人工 priority + reviewer | 形式化评分 + 约束传播辅助逻辑 |
| 收敛 | LLM 判断 "complete: true" | MCP 图状态 + 旧版评分/收敛辅助逻辑；自主编排计划在 v2.1 提供 |
| 并发 | 多 Worker 并行 | 顺序案件工作流 |
| 领域 | CTF/安全锁定 | 领域无关 + 配置适配 |

Detective 框架是破军 OODA 方法论的**理论泛化和轻量降维**。

## 设计规格

当前与规划中的设计规格：

- 当前 v2.0 MCP 图核心：`docs/superpowers/specs/2026-06-03-detective-mcp-graph-core-design.md`
- 未来/规划中的 v2.1 自主调查编排：`docs/superpowers/specs/2026-06-03-detective-v2-1-autonomous-investigation-design.md`

## 文件结构

```
detective-plugin/
├── .claude-plugin/
│   └── plugin.json              # 插件清单
├── .mcp.json                    # 本地 MCP 服务注册
├── .gitignore
├── pyproject.toml               # Python package 与 uv 配置
├── README.md                    # 英文文档
├── README-zh.md                 # 中文文档
├── agents/
│   └── strategy-evaluator.md    # 策略评分 Agent
├── detective_mcp/               # 共享 v2 MCP 图核心与 utility 模块
│   ├── exports.py               # Markdown 与 Mermaid 导出
│   ├── graph.py                 # 图操作与遍历
│   ├── legacy_board.py          # 旧版白板兼容辅助逻辑
│   ├── legacy_convergence.py    # 旧版收敛兼容辅助逻辑
│   ├── legacy_scoring.py        # 旧版评分兼容辅助逻辑
│   ├── models.py                # 案件图数据模型
│   ├── server.py                # stdio MCP 服务工具
│   └── store.py                 # 项目本地案件存储
├── scripts/                     # detective_mcp utilities 之上的旧版 CLI wrappers
│   ├── board.py
│   ├── scoring.py
│   └── convergence.py
├── skills/
│   ├── brainstorm/SKILL.md      # 脑暴（立案前问题探索）
│   ├── open-case/SKILL.md       # 立案
│   ├── investigate/SKILL.md     # 主循环
│   ├── review-board/SKILL.md    # 审板
│   ├── discuss-case/SKILL.md    # 案情研讨
│   └── close-case/SKILL.md      # 结案
└── tests/                       # MCP 核心、导出、存储与旧版 wrapper 测试
```
