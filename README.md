<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Marketplace-blueviolet?style=for-the-badge" alt="Claude Code Marketplace"/>
  <img src="https://img.shields.io/badge/Private-Esonhugh-red?style=for-the-badge" alt="Private"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"/>
</p>

<h1 align="center">Esonhugh's Marketplace</h1>

<p align="center">
  <b>Private Claude Code Plugin Marketplace by <a href="https://github.com/Esonhugh">Esonhugh</a></b>
</p>

<p align="center">
  <b>English</b> | <a href="README-zh.md">中文</a>
</p>

---

## About

This is Esonhugh's private [Claude Code Plugin Marketplace](https://code.claude.com/docs/en/plugin-marketplaces) — a curated collection of Claude Code plugins for security research, finance analysis, browser automation, reasoning frameworks, and productivity tools.

### Add This Marketplace

```bash
/plugin marketplace add Esonhugh/Marketplace
```

### Install a Plugin

```bash
/plugin install <plugin-name>@Esonhugh-Marketplace
```

---

## Plugin Catalog

| Plugin | Category | Author | Source | Description |
|:---|:---:|:---:|:---:|:---|
| [fofa-intel](#fofa-intel) | Security | Esonhugh | local | FOFA cyberspace search engine — asset mapping & threat intel |
| [threatbook-intel](#threatbook-intel) | Security | Esonhugh | local | ThreatBook (微步) — IP/domain/hash threat intel with browser automation |
| [macos-control-bypasser](#macos-control-bypasser) | Security | Esonhugh | local | macOS offensive security — TCC bypass, sandbox escape, dylib injection |
| [pydoll-antibot-bypasser](#pydoll-antibot-bypasser) | Automation | Esonhugh | [repo](https://github.com/Esonhugh/pydoll-cf-waf-bypasser-skills) | Stealth browser automation bypassing Cloudflare WAF & CAPTCHA |
| [ibkr-trade-analyzer](#ibkr-trade-analyzer) | Finance | Esonhugh | [repo](https://github.com/Esonhugh/ibkr-trade-analyzer) | IBKR trading history analysis — P&L, portfolio, fees, Flex API + local import |
| [detective](#detective) | Reasoning | Esonhugh | local | Investigation-driven problem solving with evidence chains |
| [video-extractor](#video-extractor) | Productivity | Esonhugh | [repo](https://github.com/Esonhugh/video_extractor) | Video tutorial to Markdown — mlx-whisper + Vision OCR |
| [tradingview](#tradingview) | Finance | Esonhugh | [repo](https://github.com/Esonhugh/tradingview) | TradingView data access — quotes, options, screener, news, alerts |
| [finance-market-analysis](#finance-market-analysis) | Finance | himself65 | [upstream](https://github.com/himself65/finance-skills) | Earnings, correlation, ETF premium, SEPA strategy |
| [document-skills](#document-skills) | Productivity | Anthropic | [upstream](https://github.com/anthropics/skills) | Document processing — xlsx, docx, pptx, pdf |
| [skill-creator](#skill-creator) | Development | Anthropic | [upstream](https://github.com/anthropics/skills) | Skill authoring and improvement tool |

---

## Esonhugh's Plugins

### fofa-intel

FOFA cyberspace search engine plugin. Bundles pre-compiled GoFOFA binaries for macOS/Linux/Windows — the `fofa` command is available immediately after installation with no manual PATH setup.

```bash
/plugin install fofa-intel@Esonhugh-Marketplace
```

**Features:**

| Capability | Command |
|:---|:---|
| Asset search by domain / IP / port / cert | `fofa search` |
| Bulk data export (millions of records) | `fofa dump` |
| Full host profile | `fofa host` |
| Field distribution statistics | `fofa stats` |
| Subdomain enumeration | `fofa domains` |
| Result count | `fofa count` |

**Requirements:** FOFA account + API Key (`FOFA_KEY` env var or `~/.config/gofofa/.env`)

**Notes:** Queries consume F-Points. `cert`/`banner` fields cap at 2,000 per page; `body` caps at 500.

---

### threatbook-intel

ThreatBook (微步在线) threat intelligence plugin. Query IPs, domains, and file hashes; perform asset mapping with X language; automate the browser via pydoll including full WeChat QR login.

```bash
/plugin install threatbook-intel@Esonhugh-Marketplace
```

**Features:**

| Capability | Detail |
|:---|:---|
| IP / domain / hash threat intel | Reputation, tags, associated malware, geolocation |
| Vulnerability intelligence | CVE detail and affected assets |
| X language asset mapping | Boolean operators: `ip=`, `port=`, `asn=`, `country=`, `os=`, etc. |
| Content search | `intitle=`, `intext=`, `blog=`, `x=`, `smedia=` |
| WeChat login automation | Full QR flow via pydoll — login state persisted in Chrome profile |
| XGPT conversation | AI-powered threat analysis chat |

**Requirements:** Chrome, [uv](https://docs.astral.sh/uv/), ThreatBook account, WeChat account

---

### macos-control-bypasser

Comprehensive macOS offensive security skill for authorized penetration testing and security research. Covers the full attack surface from userland to kernel.

```bash
/plugin install macos-control-bypasser@Esonhugh-Marketplace
```

**Coverage:**

| Area | Topics |
|:---|:---|
| Binary Analysis | Mach-O internals, dyld, code signing, entitlements |
| Code Injection | Dylib injection, `DYLD_INSERT_LIBRARIES`, task_for_pid, app-runtime injection (Electron/Chromium/NIB) |
| Privilege Escalation | Shellcode (x64/ARM64), Mach IPC, XPC attacks |
| Security Bypass | Gatekeeper, AMFI, MACF, sandbox escapes, TCC bypasses |
| Persistence | LaunchAgents/Daemons, login items, cron, plist manipulation |
| System Components | IOKit/DriverKit, MDM exploitation, keychain attacks |

**Intended use:** Authorized pentesting engagements, CTF, macOS security research.

---

### pydoll-antibot-bypasser

Teaches Claude how to write stealth browser automation using [Pydoll](https://github.com/autoscrape-labs/pydoll) — async-native, zero-WebDriver Chromium automation specialized in WAF bypass.

```bash
/plugin install pydoll-antibot-bypasser@Esonhugh-Marketplace
```

**WAF Support:**

| WAF | Status |
|:---|:---:|
| Cloudflare Turnstile | Full (headless) |
| Cloudflare JS Challenge | Full |
| Cloudflare Managed Challenge | Full (headless=False + xvfb) |
| DataDome | Partial |
| PerimeterX | Partial |
| Akamai Bot Manager | Partial |

**Included Templates:** `basic_browser`, `bypass_cloudflare`, `web_scraping`, `form_filling`, `hybrid_automation`, `screenshot`, `concurrent_scraping`, `stealth_browser`

**Requirements:** Python >= 3.10, Chrome/Chromium, [uv](https://docs.astral.sh/uv/)

**Standalone repo:** [Esonhugh/pydoll-cf-waf-bypasser-skills](https://github.com/Esonhugh/pydoll-cf-waf-bypasser-skills) (also a marketplace)

---

### ibkr-trade-analyzer

Analyze Interactive Brokers trading history with **read-only** access. Generates comprehensive reports on trading patterns, P&L performance, portfolio structure, and fee analysis. Supports Flex Web Service API (online) and local CSV/XML file import (offline).

```bash
/plugin install ibkr-trade-analyzer@Esonhugh-Marketplace
```

**Analysis Dimensions:**

| Dimension | Metrics |
|:---|:---|
| Trading Behavior | Trade frequency, holding periods, time-of-day patterns, win rate, profit factor |
| P&L Performance | Realized/unrealized P&L, equity curve, max drawdown, Sharpe ratio, monthly returns |
| Portfolio Structure | Asset allocation, sector concentration, long/short ratio, currency exposure |
| Fees & Cash Flow | Commissions, dividends, interest, financing costs, fee-to-PnL ratio |

**Output Formats:** Terminal summary, Markdown report, HTML with interactive Plotly charts

**Configuration:** Requires `ibkr_flex_token` and `ibkr_query_id` in plugin settings. Optional `proxy` for network access.

**Requirements:** Python >= 3.10, [uv](https://docs.astral.sh/uv/)

**Safety:** Read-only by design. Zero write/order endpoints. Local file mode has zero network access.

**Standalone repo:** [Esonhugh/ibkr-trade-analyzer](https://github.com/Esonhugh/ibkr-trade-analyzer) (also a marketplace)

---

### detective

Investigation-driven problem solving framework. Maintains a **CaseBoard** — a directed labeled graph of **Fragments** (information units) and **Threads** (logical connections) — to solve unknown-target problems through evidence chains, hypothesis testing, constraint propagation, and autonomous convergence detection.

```bash
/plugin install detective@Esonhugh-Marketplace
```

**Skills:**

| Skill | Purpose |
|:---|:---|
| `brainstorm` | Pre-investigation: collaborative problem exploration, produce case brief |
| `open-case` | Initialize a CaseBoard, define crime scene and goal |
| `investigate` | Main loop: Scan → Evolve → Focus → Act → File (until convergence) |
| `review-board` | Display board state, fragments, threads, hypotheses |
| `discuss-case` | Structured dialogue at deadlocks, ambiguity, or critical junctures |
| `close-case` | Produce resolution with complete evidence chain traceback |

**Core Concepts:**

- **Fragment**: Information unit with maturity (Raw → Clue → Evidence → Anchor) and role (Observation, Hypothesis, Constraint, Conclusion)
- **Thread**: Directed edge between fragments (supports, contradicts, derives, eliminates, requires)
- **Strategy Engine**: `Score(action) = (Discrimination x Feasibility) / Cost` with automatic pruning of dead targets, redundancy, cold leads, and circular reasoning
- **Autonomous Convergence**: Graph topology determines when the investigation is complete — no LLM self-assessment

**Applicable Domains:** Security research, intelligence analysis, root cause analysis, code archaeology

**State Storage:** `.detective/cases/<case-id>.json` (project-local, self-contained)

---

### video-extractor

Video tutorial to structured Markdown converter. Optimized for Apple Silicon Mac — uses mlx-whisper for GPU-accelerated transcription and macOS native Vision framework for OCR.

```bash
/plugin install video-extractor@Esonhugh-Marketplace
```

**Pipeline:**

1. Intelligent keyframe extraction (detects scene changes, avoids redundant frames)
2. mlx-whisper GPU transcription (Apple Silicon MLX backend)
3. macOS Vision OCR (extracts on-screen text, code, UI elements)
4. Structured Markdown assembly (timestamps, speaker segments, screen content)

**Use Cases:**
- Convert coding tutorials into step-by-step text guides
- Extract slides and spoken content from conference talks
- Create searchable documentation from video walkthroughs

**Requirements:** macOS (Apple Silicon), ffmpeg, uv, Python >= 3.11

**Platforms:** macOS only (depends on MLX + Vision framework)

**Standalone repo:** [Esonhugh/video_extractor](https://github.com/Esonhugh/video_extractor) (also a marketplace)

---

### tradingview

Read-only TradingView data access with persistent headless Chrome. Provides spot quotes, full options chains, screener, news, watchlists, alerts, chart state inspection, and screenshots — all without requiring a TradingView API key.

```bash
/plugin install tradingview@Esonhugh-Marketplace
```

**Skills:**

| Skill | Purpose |
|:---|:---|
| `launch` | Start headless Chrome with TradingView session |
| `stop` | Gracefully shut down the browser |
| `status` | Health-check the running browser instance |
| `preflight` | Verify plugin prerequisites |
| `quote` | Get real-time spot quote for a symbol |
| `search` | Search TradingView symbols |
| `options-chain` | Fetch full options chain for a symbol |
| `options-expiries` | List available option expiration dates |
| `screener` | Run stock/crypto screener with filters |
| `news` | Fetch news headlines |
| `news-research` | Deep research via news aggregation |
| `watchlists` | List TradingView watchlists |
| `alerts` | Fetch price alerts |
| `chart-state` | Read current chart symbol, interval, indicators |
| `screenshot` | Take a PNG screenshot of a chart |
| `login-email` | Non-interactive email/password login |
| `login-interactive` | Open visible browser for manual login |
| `options-analysis` | Analyze options strategy and payoff |

**Architecture:** A plugin-managed headless Chrome instance connects to TradingView via CDP (Chrome DevTools Protocol). The monitor hook auto-launches, health-checks, and restarts the browser on crash.

**Requirements:** Chrome/Chromium, Node.js, persistent Chrome profile for session

**Standalone repo:** [Esonhugh/tradingview](https://github.com/Esonhugh/tradingview) (also a marketplace)

---

## Third-Party References

Plugins below are sourced from external repositories. They are included in this marketplace for convenience but maintained by their respective authors.

### finance-market-analysis

> **Reference:** [`himself65/finance-skills`](https://github.com/himself65/finance-skills) at `plugins/market-analysis/`

Market analysis toolkit for stock investors. Provides earnings analysis (preview/recap/estimate revisions), portfolio risk assessment (stock correlation, ETF premium/discount), and SEPA trend-following entry methodology.

```bash
/plugin install finance-market-analysis@Esonhugh-Marketplace
```

**Included Skills:** `earnings-preview`, `earnings-recap`, `estimate-analysis`, `stock-correlation`, `etf-premium`, `sepa-strategy`, `options-payoff`, `yfinance-data`, `company-valuation`, `saas-valuation-compression`, `stock-liquidity`

**Requirements:** Python >= 3.10, yfinance

---

### document-skills

> **Reference:** [`anthropics/skills`](https://github.com/anthropics/skills) at `skills/xlsx`, `skills/docx`, `skills/pptx`, `skills/pdf`

Document processing suite from Anthropic. Generate and manipulate Excel spreadsheets, Word documents, PowerPoint presentations, and PDF files directly from Claude Code.

```bash
/plugin install document-skills@Esonhugh-Marketplace
```

**Included Skills:** `xlsx` (Excel), `docx` (Word), `pptx` (PowerPoint), `pdf` (PDF)

---

### skill-creator

> **Reference:** [`anthropics/skills`](https://github.com/anthropics/skills) at `skills/skill-creator`

Meta-skill from Anthropic for creating, modifying, and measuring the effectiveness of Claude Code skills. Useful for plugin developers building their own skill libraries.

```bash
/plugin install skill-creator@Esonhugh-Marketplace
```

---

## Source Types

This marketplace uses multiple source strategies:

| Type | Example | When |
|:---|:---|:---|
| Local | `"./plugins/fofa-intel"` | Plugin lives in this repo |
| URL | `{"source": "url", "url": "https://...git"}` | Plugin has its own standalone repo |
| Git Subdir | `{"source": "git-subdir", "url": "...", "path": "..."}` | Plugin is a subdirectory in another repo |

Plugins with standalone repos are both a **plugin** and a **marketplace** — they can be used independently or aggregated here.

---

## Repository Structure

```
Marketplace/
├── .claude-plugin/
│   └── marketplace.json              # Marketplace catalog (11 plugins)
├── plugins/
│   ├── fofa-intel/                   # FOFA cyberspace search (local)
│   ├── threatbook-intel/             # ThreatBook threat intel (local)
│   ├── macos-control-bypasser/       # macOS offensive security (local)
│   └── detective-plugin/             # Investigation framework (local)
└── README.md
```

Plugins not listed above are referenced via URL/git-subdir and fetched at install time.

---

## Disclaimer

All plugins are provided for **authorized security testing, educational purposes, and legitimate automation** only. Users are responsible for complying with applicable laws and the Terms of Service of any target systems or websites.

---

<p align="center">
  <sub>Maintained by <a href="https://github.com/Esonhugh">Esonhugh</a></sub>
</p>
