<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Marketplace-blueviolet?style=for-the-badge" alt="Claude Code Marketplace"/>
  <img src="https://img.shields.io/badge/Private-Esonhugh-red?style=for-the-badge" alt="Private"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"/>
</p>

<h1 align="center">Esonhugh's Marketplace</h1>

<p align="center">
  <b><a href="https://github.com/Esonhugh">Esonhugh</a> 的私有 Claude Code 插件市场</b>
</p>

<p align="center">
  <a href="README.md">English</a> | <b>中文</b>
</p>

---

## 简介

这是 Esonhugh 的私有 [Claude Code 插件市场](https://code.claude.com/docs/en/plugin-marketplaces) — 涵盖安全研究、金融分析、浏览器自动化、推理框架和生产力工具的精选插件集合。

### 添加市场

```bash
/plugin marketplace add Esonhugh/Marketplace
```

### 安装插件

```bash
/plugin install <plugin-name>@Esonhugh-Marketplace
```

---

## 插件目录

| 插件 | 类别 | 作者 | 来源 | 描述 |
|:---|:---:|:---:|:---:|:---|
| [fofa-intel](#fofa-intel) | 安全 | Esonhugh | 本地 | FOFA 网络空间搜索引擎 — 资产测绘与威胁情报 |
| [threatbook-intel](#threatbook-intel) | 安全 | Esonhugh | [skills](skills/threatbook-intel/) | 微步在线 — IP/域名/哈希威胁情报 + 浏览器自动化 |
| [macos-control-bypasser](#macos-control-bypasser) | 安全 | Esonhugh | [skills](skills/macos-control-bypasses/) | macOS 攻击安全 — TCC 绕过、沙箱逃逸、dylib 注入 |
| [interactive-cli-systemic-debugging](#interactive-cli-systemic-debugging) | 开发 | Esonhugh | [skills](skills/interactive-cli-systemic-debugging/) | 用 tmux 调试交互式 CLI、REPL、TUI 和 watch-mode 进程 |
| [pydoll-antibot-bypasser](#pydoll-antibot-bypasser) | 自动化 | Esonhugh | [仓库](https://github.com/Esonhugh/pydoll-cf-waf-bypasser-skills) | 隐匿浏览器自动化 — 绕过 Cloudflare WAF 与 CAPTCHA |
| [ibkr-trade-analyzer](#ibkr-trade-analyzer) | 金融 | Esonhugh | [仓库](https://github.com/Esonhugh/ibkr-trade-analyzer) | IBKR 交易历史分析 — 盈亏、持仓、费用，支持 Flex API + 本地导入 |
| [detective](#detective) | 推理 | Esonhugh | 本地 | 基于证据链的调查推理框架 |
| [video-extractor](#video-extractor) | 生产力 | Esonhugh | [仓库](https://github.com/Esonhugh/video_extractor) | 视频教程转 Markdown — mlx-whisper + Vision OCR |
| [tradingview](#tradingview) | 金融 | Esonhugh | [仓库](https://github.com/Esonhugh/tradingview) | TradingView 数据访问 — 行情、期权、筛选器、新闻、警报 |
| [finance-market-analysis](#finance-market-analysis) | 金融 | himself65 | [上游](https://github.com/himself65/finance-skills) | 财报分析、相关性、ETF 溢价、SEPA 策略 |
| [document-skills](#document-skills) | 生产力 | Anthropic | [上游](https://github.com/anthropics/skills) | 文档处理 — xlsx、docx、pptx、pdf |
| [skill-creator](#skill-creator) | 开发 | Anthropic | [上游](https://github.com/anthropics/skills) | Skill 编写与优化工具 |
| [chrome-devtools-mcp](#chrome-devtools-mcp) | 开发 | Chrome DevTools Team | [上游](https://github.com/ChromeDevTools/chrome-devtools-mcp) | Chrome 自动化、调试、网络、控制台与性能追踪 |
| [frontend-design](#frontend-design) | 开发 | Anthropic | [上游](https://github.com/anthropics/claude-plugins-official) | 生产级前端 UI/UX 设计技能 |
| [superpowers](#superpowers) | 开发 | Jesse Vincent | [上游](https://github.com/obra/superpowers) | 头脑风暴、TDD、调试、代码审查与技能编写工作流 |
| [mattpocock-skills](#mattpocock-skills) | 开发 | Matt Pocock | [仓库](https://github.com/mattpocock/skills) | 包含 grill-me 的工程与生产力技能 |

---

## Esonhugh 的插件

### fofa-intel

FOFA 网络空间搜索引擎插件。内置预编译的 GoFOFA 二进制文件（macOS/Linux/Windows），安装后 `fofa` 命令即刻可用，无需手动配置 PATH。

```bash
/plugin install fofa-intel@Esonhugh-Marketplace
```

**功能：**

| 能力 | 命令 |
|:---|:---|
| 按域名 / IP / 端口 / 证书搜索资产 | `fofa search` |
| 批量数据导出（百万级记录） | `fofa dump` |
| 完整主机画像 | `fofa host` |
| 字段分布统计 | `fofa stats` |
| 子域名枚举 | `fofa domains` |
| 结果计数 | `fofa count` |

**依赖：** FOFA 账号 + API Key（`FOFA_KEY` 环境变量或 `~/.config/gofofa/.env`）

**注意：** 查询消耗 F 点。`cert`/`banner` 字段每页上限 2,000 条；`body` 上限 500 条。

---

### threatbook-intel

微步在线威胁情报插件。支持 IP/域名/哈希查询、X 语法资产测绘、pydoll 浏览器自动化（含微信扫码登录）。

```bash
/plugin install threatbook-intel@Esonhugh-Marketplace
```

**功能：**

| 能力 | 详情 |
|:---|:---|
| IP / 域名 / 哈希威胁情报 | 信誉评分、标签、关联恶意软件、地理位置 |
| 漏洞情报 | CVE 详情及受影响资产 |
| X 语法资产测绘 | 布尔运算符：`ip=`、`port=`、`asn=`、`country=`、`os=` 等 |
| 内容搜索 | `intitle=`、`intext=`、`blog=`、`x=`、`smedia=` |
| 微信登录自动化 | 通过 pydoll 完成扫码流程 — 登录态保存在 Chrome Profile |
| XGPT 对话 | AI 驱动的威胁分析聊天 |

**依赖：** Chrome、[uv](https://docs.astral.sh/uv/)、微步账号、微信账号

**Skill 路径：** [`skills/threatbook-intel/`](skills/threatbook-intel/)

---

### macos-control-bypasser

面向授权渗透测试和安全研究的 macOS 攻击安全技能，覆盖从用户态到内核的完整攻击面。

```bash
/plugin install macos-control-bypasser@Esonhugh-Marketplace
```

**覆盖范围：**

| 领域 | 主题 |
|:---|:---|
| 二进制分析 | Mach-O 内部结构、dyld、代码签名、Entitlements |
| 代码注入 | Dylib 注入、`DYLD_INSERT_LIBRARIES`、task_for_pid、应用运行时注入（Electron/Chromium/NIB） |
| 提权 | Shellcode（x64/ARM64）、Mach IPC、XPC 攻击 |
| 安全绕过 | Gatekeeper、AMFI、MACF、沙箱逃逸、TCC 绕过 |
| 持久化 | LaunchAgents/Daemons、登录项、cron、plist 操控 |
| 系统组件 | IOKit/DriverKit、MDM 利用、钥匙串攻击 |

**适用场景：** 授权渗透测试、CTF、macOS 安全研究。

**Skill 路径：** [`skills/macos-control-bypasses/`](skills/macos-control-bypasses/)

---

### interactive-cli-systemic-debugging

基于 tmux 的系统化调试 workflow，适用于交互式 CLI、REPL、TUI、prompt loop、watch mode 和长时间运行的终端程序。

```bash
/plugin install interactive-cli-systemic-debugging@Esonhugh-Marketplace
```

**包含的 Skill：** [`interactive-cli-systemic-debugging`](skills/interactive-cli-systemic-debugging/)

**适用场景：** 命令在 prompt 后 hang、TUI 在不同终端尺寸下显示异常、watch mode 在输入后失败，或任何需要用 `tmux capture-pane` / `send-keys` 保留屏幕状态的 CLI 调试。

---

### pydoll-antibot-bypasser

教导 Claude 使用 [Pydoll](https://github.com/autoscrape-labs/pydoll) 编写隐匿浏览器自动化 — 异步原生、零 WebDriver 的 Chromium 自动化，专攻 WAF 绕过。

```bash
/plugin install pydoll-antibot-bypasser@Esonhugh-Marketplace
```

**WAF 支持：**

| WAF | 状态 |
|:---|:---:|
| Cloudflare Turnstile | 完全支持（headless） |
| Cloudflare JS Challenge | 完全支持 |
| Cloudflare Managed Challenge | 完全支持（headless=False + xvfb） |
| DataDome | 部分支持 |
| PerimeterX | 部分支持 |
| Akamai Bot Manager | 部分支持 |

**内置模板：** `basic_browser`、`bypass_cloudflare`、`web_scraping`、`form_filling`、`hybrid_automation`、`screenshot`、`concurrent_scraping`、`stealth_browser`

**依赖：** Python >= 3.10、Chrome/Chromium、[uv](https://docs.astral.sh/uv/)

**独立仓库：** [Esonhugh/pydoll-cf-waf-bypasser-skills](https://github.com/Esonhugh/pydoll-cf-waf-bypasser-skills)（同时也是一个市场）

---

### ibkr-trade-analyzer

以**只读**方式分析 Interactive Brokers 交易历史。生成交易行为、盈亏表现、持仓结构和费用的综合报告。支持 Flex Web Service API（在线）和本地 CSV/XML 文件导入（离线）。

```bash
/plugin install ibkr-trade-analyzer@Esonhugh-Marketplace
```

**分析维度：**

| 维度 | 指标 |
|:---|:---|
| 交易行为 | 交易频率、持仓时长、日内时段分布、胜率、盈亏比 |
| 盈亏表现 | 已实现/未实现盈亏、权益曲线、最大回撤、夏普比率、月度收益 |
| 持仓结构 | 资产配置、行业集中度、多空比、货币敞口 |
| 费用与现金流 | 佣金、分红、利息、融资成本、费用占盈亏比 |

**输出格式：** 终端摘要、Markdown 报告、HTML（含交互式 Plotly 图表）

**配置：** 需在插件设置中填写 `ibkr_flex_token` 和 `ibkr_query_id`。可选 `proxy` 用于网络访问。

**依赖：** Python >= 3.10、[uv](https://docs.astral.sh/uv/)

**安全性：** 设计上只读。零写入/下单端点。本地文件模式零网络访问。

**独立仓库：** [Esonhugh/ibkr-trade-analyzer](https://github.com/Esonhugh/ibkr-trade-analyzer)（同时也是一个市场）

---

### detective

基于调查驱动的问题解决框架，提供用于项目本地案件存储、图查询、最短路径和 Markdown/Mermaid 导出的本地 MCP 图核心。旧版评分与收敛 scripts 仍作为兼容 CLI wrappers 可用。

```bash
/plugin install detective@Esonhugh-Marketplace
```

**技能：**

| 技能 | 用途 |
|:---|:---|
| `brainstorm` | 预调查：协作式问题探索，产出案件简报 |
| `open-case` | 初始化 CaseBoard，定义案发现场和目标 |
| `investigate` | 围绕 v2 MCP 图核心查看图状态、补充证据并推进案件；循环表述仅作为旧版 v1 工作流标签与 v2.1 编排规划保留 |
| `review-board` | 展示面板状态、碎片、线索、假设 |
| `discuss-case` | 在僵局、歧义或关键节点进行结构化对话 |
| `close-case` | 产出含完整证据链溯源的结案报告 |

**核心概念：**

- **Fragment**：信息单元，成熟度（Raw → Clue → Evidence → Anchor），角色（Observation、Hypothesis、Constraint、Conclusion）
- **Thread**：碎片间的有向边（supports、contradicts、derives、eliminates、requires）
- **MCP 图核心**：在本地存储案件，维护项目本地的图状态，支持图概览/查询、最短路径，以及 Markdown/Mermaid 导出
- **旧版评分兼容**：旧版评分/收敛辅助逻辑仍以 CLI 兼容 wrapper 形式复用共享 MCP 图工具，但它们并不是已交付的 v2 自主编排核心

**适用领域：** 安全研究、情报分析、根因分析、代码考古

**MCP 图核心存储：** 当前 v2 案件状态存储在项目本地，并采用目录结构：

```text
.detective/cases/<case-id>/case.json
.detective/cases/<case-id>/notes.md
.detective/cases/<case-id>/graph.mmd
.detective/cases/<case-id>/events.jsonl
```

扁平路径 `.detective/cases/<case-id>.json` 仅用于旧版 v1 兼容。

---

### video-extractor

视频教程转结构化 Markdown 工具。针对 Apple Silicon Mac 优化 — 使用 mlx-whisper 进行 GPU 加速转录，macOS 原生 Vision 框架进行 OCR。

```bash
/plugin install video-extractor@Esonhugh-Marketplace
```

**处理流程：**

1. 智能关键帧提取（检测场景变化，避免冗余帧）
2. mlx-whisper GPU 转录（Apple Silicon MLX 后端）
3. macOS Vision OCR（提取屏幕文字、代码、UI 元素）
4. 结构化 Markdown 组装（时间戳、说话人分段、屏幕内容）

**用例：**
- 将编程教程转为分步文本指南
- 从会议演讲中提取幻灯片和语音内容
- 从视频演示中创建可搜索的文档

**依赖：** macOS（Apple Silicon）、ffmpeg、uv、Python >= 3.11

**平台：** 仅 macOS（依赖 MLX + Vision 框架）

**独立仓库：** [Esonhugh/video_extractor](https://github.com/Esonhugh/video_extractor)（同时也是一个市场）

---

### tradingview

只读 TradingView 数据访问插件，基于持久化 headless Chrome。提供实时行情、完整期权链、筛选器、新闻、自选列表、警报、图表状态检查和截图 — 无需 TradingView API Key。

```bash
/plugin install tradingview@Esonhugh-Marketplace
```

**技能：**

| 技能 | 用途 |
|:---|:---|
| `launch` | 启动 headless Chrome 并连接 TradingView 会话 |
| `stop` | 优雅关闭浏览器 |
| `status` | 检查运行中的浏览器实例健康状态 |
| `preflight` | 验证插件前置条件 |
| `quote` | 获取标的实时行情 |
| `search` | 搜索 TradingView 标的 |
| `options-chain` | 获取完整期权链 |
| `options-expiries` | 列出可用期权到期日 |
| `screener` | 运行股票/加密货币筛选器 |
| `news` | 获取新闻头条 |
| `news-research` | 通过新闻聚合进行深度研究 |
| `watchlists` | 列出 TradingView 自选列表 |
| `alerts` | 获取价格警报 |
| `chart-state` | 读取当前图表标的、周期、指标 |
| `screenshot` | 对图表截取 PNG 截图 |
| `login-email` | 非交互式邮箱/密码登录 |
| `login-interactive` | 打开可见浏览器进行手动登录 |
| `options-analysis` | 分析期权策略与收益图 |

**架构：** 插件管理的 headless Chrome 实例通过 CDP（Chrome DevTools Protocol）连接 TradingView。Monitor hook 自动启动、健康检查并在崩溃时重启浏览器。

**依赖：** Chrome/Chromium、Node.js、持久化 Chrome Profile 用于保存会话

**独立仓库：** [Esonhugh/tradingview](https://github.com/Esonhugh/tradingview)（同时也是一个市场）

---

## 第三方引用

以下插件来源于外部仓库，为便于使用收录在本市场中，由各自作者维护。

### finance-market-analysis

> **引用：** [`himself65/finance-skills`](https://github.com/himself65/finance-skills) 的 `plugins/market-analysis/`

面向股票投资者的市场分析工具包。提供财报分析（预览/回顾/预估修正）、投资组合风险评估（股票相关性、ETF 溢折价）和 SEPA 趋势跟踪入场方法论。

```bash
/plugin install finance-market-analysis@Esonhugh-Marketplace
```

**包含技能：** `earnings-preview`、`earnings-recap`、`estimate-analysis`、`stock-correlation`、`etf-premium`、`sepa-strategy`、`options-payoff`、`yfinance-data`、`company-valuation`、`saas-valuation-compression`、`stock-liquidity`

**依赖：** Python >= 3.10、yfinance

---

### document-skills

> **引用：** [`anthropics/skills`](https://github.com/anthropics/skills) 的 `skills/xlsx`、`skills/docx`、`skills/pptx`、`skills/pdf`

Anthropic 出品的文档处理套件。在 Claude Code 中直接生成和操作 Excel 表格、Word 文档、PowerPoint 演示文稿和 PDF 文件。

```bash
/plugin install document-skills@Esonhugh-Marketplace
```

**包含技能：** `xlsx`（Excel）、`docx`（Word）、`pptx`（PowerPoint）、`pdf`（PDF）

---

### skill-creator

> **引用：** [`anthropics/skills`](https://github.com/anthropics/skills) 的 `skills/skill-creator`

Anthropic 出品的元技能，用于创建、修改和衡量 Claude Code Skills 的效果。适合构建自有技能库的插件开发者。

```bash
/plugin install skill-creator@Esonhugh-Marketplace
```

---

### chrome-devtools-mcp

> **引用：** [`ChromeDevTools/chrome-devtools-mcp`](https://github.com/ChromeDevTools/chrome-devtools-mcp) 的独立插件仓库，与官方 marketplace 索引一致。

Chrome DevTools MCP 集成，用于在 Claude Code 中控制和检查实时 Chrome 浏览器：浏览器自动化、控制台和网络检查、截图以及性能追踪。

```bash
/plugin install chrome-devtools-mcp@Esonhugh-Marketplace
```

---

### frontend-design

> **引用：** [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official) 的 `plugins/frontend-design/`

Anthropic 前端设计技能，用于创建有辨识度的生产级 UI/UX 实现，避免通用 AI 风格界面。

```bash
/plugin install frontend-design@Esonhugh-Marketplace
```

---

### superpowers

> **引用：** [`obra/superpowers`](https://github.com/obra/superpowers) 的独立插件仓库，与官方 marketplace 索引一致。

工作流技能集合，覆盖头脑风暴、红绿 TDD、系统化调试、子代理驱动开发、代码审查和技能编写。

```bash
/plugin install superpowers@Esonhugh-Marketplace
```

---

### mattpocock-skills

> **引用：** [`mattpocock/skills`](https://github.com/mattpocock/skills) 作为根 Claude Code 插件。

Matt Pocock 的工程与生产力技能集合。包含 `grill-me`、`grill-with-docs`、`tdd`、`diagnose`、`triage`、`handoff` 等真实工程工作流技能。

```bash
/plugin install mattpocock-skills@Esonhugh-Marketplace
```

---

## 来源类型

本市场使用多种来源策略：

| 类型 | 示例 | 适用场景 |
|:---|:---|:---|
| 本地插件 | `"./plugins/fofa-intel"` | 完整插件位于本仓库 |
| 本地纯 skills | `"source": "./"` + `"skills": ["./skills/name"]` | 纯 skills entry 存放在顶层 `skills/` |
| URL | `{"source": "url", "url": "https://...git"}` | 插件有独立仓库 |
| Git 子目录 | `{"source": "git-subdir", "url": "...", "path": "..."}` | 插件是其他仓库的子目录 |

拥有独立仓库的插件同时是**插件**和**市场** — 可独立使用或在此聚合。

---

## 仓库结构

```
Marketplace/
├── .claude-plugin/
│   └── marketplace.json              # 市场目录（16 个插件）
├── skills/
│   ├── interactive-cli-systemic-debugging/  # tmux CLI 调试 skill
│   ├── macos-control-bypasses/              # macOS 安全研究 skill
│   └── threatbook-intel/                    # 微步情报 skill
├── plugins/
│   ├── fofa-intel/                   # FOFA 网络空间搜索（本地插件）
│   └── detective-plugin/             # 调查推理框架（本地插件）
└── README.md
```

纯 skills entry 存放在顶层 `skills/`，并在 `marketplace.json` 中通过 `source: "./"` 和显式 `skills` 相对路径引用。未列出的插件通过 URL/git-subdir 引用，安装时拉取。

---

## 免责声明

所有插件仅用于**授权安全测试、教育目的和合法自动化**。用户有责任遵守适用法律及任何目标系统或网站的服务条款。

---

<p align="center">
  <sub>由 <a href="https://github.com/Esonhugh">Esonhugh</a> 维护</sub>
</p>
