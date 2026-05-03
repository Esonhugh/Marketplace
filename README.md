<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Marketplace-blueviolet?style=for-the-badge" alt="Claude Code Marketplace"/>
  <img src="https://img.shields.io/badge/Private-Esonhugh-red?style=for-the-badge" alt="Private"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"/>
</p>

<h1 align="center">Esonhugh's Marketplace</h1>

<p align="center">
  <b>Private Claude Code Plugin Marketplace by <a href="https://github.com/Esonhugh">Esonhugh</a></b>
</p>

---

## About

This is Esonhugh's private [Claude Code Plugin Marketplace](https://code.claude.com/docs/en/plugin-marketplaces) — a curated collection of Claude Code plugins for security research, finance analysis, and browser automation.

### Add This Marketplace

```bash
/plugin marketplace add Esonhugh/Marketplace
```

### Install a Plugin

```bash
/plugin install <plugin-name>@Esonhugh/Marketplace
```

---

## Plugin Catalog

| Plugin | Category | Description |
|:---|:---:|:---|
| [fofa-intel](#fofa-intel) | Security | FOFA cyberspace search engine — asset mapping & threat intel |
| [threatbook-intel](#threatbook-intel) | Security | ThreatBook (微步) — IP/domain/hash threat intel with browser automation |
| [macos-control-bypasser](#macos-control-bypasser) | Security | macOS offensive security — TCC bypass, sandbox escape, dylib injection |
| [pydoll-antibot-bypasser](#pydoll-antibot-bypasser) | Automation | Stealth browser automation bypassing Cloudflare WAF & CAPTCHA |
| [ibkr-trade-analyzer](#ibkr-trade-analyzer) | Finance | IBKR trading history analysis — P&L, portfolio, fees |
| [finance-market-analysis](#finance-market-analysis) | Finance | Earnings analysis, stock correlation, ETF premium, SEPA strategy |

---

### fofa-intel

FOFA cyberspace search engine plugin. Bundles pre-compiled GoFOFA binaries for macOS/Linux/Windows — the `fofa` command is available immediately after installation with no manual PATH setup.

```bash
/plugin install fofa-intel@Esonhugh/Marketplace
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

→ [README](plugins/fofa-intel/README.md) · [中文说明](plugins/fofa-intel/README-zh.md)

---

### threatbook-intel

ThreatBook (微步在线) threat intelligence plugin. Query IPs, domains, and file hashes; perform asset mapping with X language; automate the browser via pydoll including full WeChat QR login.

```bash
/plugin install threatbook-intel@Esonhugh/Marketplace
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

→ [README](plugins/threatbook-intel/README.md) · [中文说明](plugins/threatbook-intel/README-zh.md)

---

### macos-control-bypasser

Comprehensive macOS offensive security skill for authorized penetration testing and security research. Covers the full attack surface from userland to kernel.

```bash
/plugin install macos-control-bypasser@Esonhugh/Marketplace
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
/plugin install pydoll-antibot-bypasser@Esonhugh/Marketplace
```

**WAF Support:**

| WAF | Status |
|:---|:---:|
| Cloudflare Turnstile | ✅ Full (headless) |
| Cloudflare JS Challenge | ✅ Full |
| Cloudflare Managed Challenge | ✅ (headless=False + xvfb) |
| DataDome | ⚠️ Partial |
| PerimeterX | ⚠️ Partial |
| Akamai Bot Manager | ⚠️ Partial |

**Included Templates:** `basic_browser`, `bypass_cloudflare`, `web_scraping`, `form_filling`, `hybrid_automation`, `screenshot`, `concurrent_scraping`, `stealth_browser`

**Requirements:** Python >= 3.10, Chrome/Chromium, [uv](https://docs.astral.sh/uv/)

---

### ibkr-trade-analyzer

Analyze Interactive Brokers trading history with **read-only** access. Supports both the Flex Web Service API (online) and local CSV/XML file import (offline).

```bash
/plugin install ibkr-trade-analyzer@Esonhugh/Marketplace
```

**Analysis Dimensions:**

| Dimension | Metrics |
|:---|:---|
| Trading Behavior | Trade frequency, holding periods, time-of-day patterns, win rate, profit factor |
| P&L Performance | Realized/unrealized P&L, equity curve, max drawdown, Sharpe ratio, monthly returns |
| Portfolio Structure | Asset allocation, sector concentration, long/short ratio, currency exposure |
| Fees & Cash Flow | Commissions, dividends, interest, financing costs, fee-to-PnL ratio |

**Output Formats:** Terminal summary · Markdown report · HTML with interactive Plotly charts

**Requirements:** Python >= 3.10, [uv](https://docs.astral.sh/uv/)

**Safety:** Read-only by design. Zero write/order endpoints. Local file mode has zero network access.

---

### finance-market-analysis

Market analysis toolkit for stock investors. Forked from [himself65/finance-skills](https://github.com/himself65/finance-skills).

```bash
/plugin install finance-market-analysis@Esonhugh/Marketplace
```

**Included Skills:**

| Skill | Description |
|:---|:---|
| `earnings-preview` | Pre-earnings briefing: estimates, beat/miss history, analyst sentiment |
| `earnings-recap` | Post-earnings analysis: actual vs estimated, price reaction, margin trends |
| `estimate-analysis` | EPS/revenue revision trends (7d/30d/60d/90d), revision breadth ratio |
| `stock-correlation` | Co-movement discovery, rolling correlation, regime-conditional analysis |
| `etf-premium` | ETF premium/discount vs NAV, peer comparison, 80+ ETF screener |
| `sepa-strategy` | Minervini SEPA: Weinstein stage, 8-condition trend template, VCP, position sizing |

**Requirements:** Python >= 3.10, yfinance

---

## Repository Structure

```
Marketplace/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace catalog
├── plugins/
│   ├── fofa-intel/               # FOFA cyberspace search engine
│   │   ├── .claude-plugin/
│   │   ├── bin/                  # Pre-compiled binaries (auto-added to PATH)
│   │   └── skills/fofa-intel/
│   ├── threatbook-intel/         # ThreatBook threat intelligence
│   │   ├── .claude-plugin/
│   │   └── skills/threatbook-intel/
│   │       └── scripts/          # pydoll browser automation script
│   ├── macos-control-bypasser/   # macOS offensive security
│   │   ├── .claude-plugin/
│   │   └── skills/
│   ├── pydoll-antibot-bypasser/  # Cloudflare WAF bypass
│   │   ├── .claude-plugin/
│   │   └── skills/
│   ├── ibkr-trade-analyzer/      # IBKR trading analysis
│   │   ├── .claude-plugin/
│   │   └── skills/ibkr-trade-analyzer/
│   │       └── scripts/
│   └── finance-market-analysis/  # Stock market analysis
│       ├── .claude-plugin/
│       └── skills/
└── README.md
```

---

## Disclaimer

All plugins are provided for **authorized security testing, educational purposes, and legitimate automation** only. Users are responsible for complying with applicable laws and the Terms of Service of any target systems or websites.

---

<p align="center">
  <sub>Maintained by <a href="https://github.com/Esonhugh">Esonhugh</a></sub>
</p>
