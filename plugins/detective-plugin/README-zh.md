# 侦探 — 基于调查方法论的通用问题解决框架

一个 Claude Code 插件，实现了基于侦探办案方法论的通用 AI 问题解决框架。每个问题都是一个**案件**；每个结论都有可追溯的**证据链**支撑。

## 核心概念

AI 维护一块**案件白板（CaseBoard）**——由**案情片段（Fragment）**和**红线（Thread）**构成的有向标签图——通过侦探的调查循环解决问题：

```
审板(Scan) → 演化(Evolve) → 聚焦(Focus) → 行动(Act) → 归档(File) → (循环直到收敛)
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

- **策略引擎**：信息增益评分（`区分力 × 可行性 / 成本`）、约束传播、方向删减、自动相态识别
- **自主收敛**：系统自己知道"够了"——当图的拓扑满足形式化收敛条件时
- **案情研讨**：在僵局、分歧或关键时刻与用户进行结构化讨论
- **全程可追溯**：每个结论都能沿证据链回溯到初始观察
- **相态自动检测**：白板拓扑自动决定调查阶段（立案 → 勘查 → 追踪 → 收敛 → 收网 → 结案）

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

## 架构

```
┌─────────────────────────────────────────────┐
│           Claude Code 会话                   │
│                                             │
│  ┌─────────┐   ┌──────────┐   ┌────────┐  │
│  │案件白板  │   │ 策略引擎  │   │ 行动   │  │
│  │  (JSON) │←→│(Python)  │──→│ 执行器 │  │
│  └─────────┘   └──────────┘   └────────┘  │
│       ↑              ↑                      │
│       └──── Skills ──┘                      │
└─────────────────────────────────────────────┘
```

- **案件白板**：一个 JSON 文件（`.detective/cases/<id>.json`）——就是侦探的那块墙
- **策略引擎**：Python 脚本负责评分、约束传播、收敛检测
- **行动执行器**：Claude Code 本身——bash、文件操作、搜索、MCP 工具

## 策略引擎

Focus 阶段回答："所有可能的下一步中，哪一步最值得做？"

```
Score(action) = (区分力 × 可行性) / 归一化成本
```

删减规则自动排除：
- 针对已排除假设的行动（死靶子）
- 结果会重复已有证据的行动（冗余）
- 同方向尝试 3 次以上无进展（冷线索）
- 循环论证链

## 安装

```bash
# 本地测试
claude --plugin-dir /path/to/detective-plugin

# 或软链接到插件目录
ln -s /path/to/detective-plugin ~/.claude/plugins/detective
```

## 状态存储

案件文件存储在项目本地：`.detective/cases/<case-id>.json`

每个案件文件包含完整白板状态，自包含，可移植。

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
| 架构 | 三进程分布式 | 单进程，文件状态 |
| 状态 | SQLite + HTTP | JSON 文件 |
| 实体 | origin/goal/fact/intent | Fragment + Thread（统一） |
| 循环 | OODA | Scan-Evolve-Focus-Act-File |
| 策略 | 人工 priority + reviewer | 形式化评分 + 约束传播 |
| 收敛 | LLM 判断 "complete: true" | 图拓扑 + 形式化条件 |
| 并发 | 多 Worker 并行 | 顺序执行 |
| 领域 | CTF/安全锁定 | 领域无关 + 配置适配 |

Detective 框架是破军 OODA 方法论的**理论泛化和轻量降维**。

## 设计规格

完整理论模型：`docs/superpowers/specs/2026-05-06-detective-framework-design.md`

## 文件结构

```
detective-plugin/
├── .claude-plugin/
│   └── plugin.json              # 插件清单
├── .gitignore
├── README.md                    # 英文文档
├── README-zh.md                 # 中文文档
├── agents/
│   └── strategy-evaluator.md    # 策略评分 Agent
├── scripts/
│   ├── board.py                 # 白板增删改查
│   ├── scoring.py               # 评分与约束传播
│   └── convergence.py           # 收敛检测
└── skills/
    ├── brainstorm/SKILL.md      # 脑暴（立案前问题探索）
    ├── open-case/SKILL.md       # 立案
    ├── investigate/SKILL.md     # 主循环
    ├── review-board/SKILL.md    # 审板
    ├── discuss-case/SKILL.md    # 案情研讨
    └── close-case/SKILL.md      # 结案
```
