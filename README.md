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

This is Esonhugh's private [Claude Code Plugin Marketplace](https://code.claude.com/docs/en/plugin-marketplaces) — a curated collection of Claude Code plugins and skills for personal use and sharing.

### Installation

Register this marketplace in Claude Code:

```bash
/plugin marketplace add Esonhugh/Marketplace
```

Then install any plugin from the catalog:

```bash
/plugin install <plugin-name>@Esonhugh/Marketplace
```

---

## Plugin Catalog

### ibkr-trade-analyzer

Analyze Interactive Brokers (IBKR) trading history with **read-only** access. Supports both the Flex Web Service API (online) and local CSV/XML file import (offline). Generates comprehensive reports covering four dimensions of your trading activity.

**Install:**

```bash
/plugin install ibkr-trade-analyzer@Esonhugh/Marketplace
```

**Analysis Dimensions:**

| Dimension | Metrics |
|:---|:---|
| Trading Behavior | Trade frequency, holding periods, time-of-day patterns, win rate, profit factor |
| P&L Performance | Realized/unrealized P&L, equity curve, max drawdown, Sharpe ratio, monthly returns, top winners/losers |
| Portfolio Structure | Asset allocation, sector concentration, long/short ratio, position concentration, currency exposure |
| Fees & Cash Flow | Commissions, dividends, interest, financing costs, fee-to-PnL ratio |

**Output Formats:**

| Format | Description |
|:---|:---|
| Terminal | Quick summary printed to console |
| Markdown | Full report with tables (`reports/ibkr-analysis-YYYY-MM-DD.md`) |
| HTML | Interactive report with Plotly charts (`reports/ibkr-analysis-YYYY-MM-DD.html`) |

**Features:**
- FIFO lot matching for accurate realized P&L (handles IBKR's `fifoPnlRealized=0` edge case)
- Unrealized P&L computation from FIFO remaining lots
- Stock price history overlay with buy/sell markers via yfinance
- Proxy support (SOCKS5/HTTP) with auto-detection from environment variables
- Interactive guided setup via AskUserQuestion (token, query ID, file path)
- PEP 723 inline metadata — runs with `uv run`, no venv/pyproject.toml needed

**Requirements:** Python >= 3.10, [uv](https://docs.astral.sh/uv/)

**Safety:** Read-only by design. The Flex Web Service has zero write/order endpoints. The script imports no trading execution libraries. Local file mode has zero network access.

---

### finance-market-analysis

Market analysis toolkit for stock investors. Contains 6 skills covering earnings analysis, portfolio risk assessment, and trend-following entry methodology. Forked from [himself65/finance-skills](https://github.com/himself65/finance-skills).

**Install:**

```bash
/plugin install finance-market-analysis@Esonhugh/Marketplace
```

**Included Skills:**

| Skill | Description |
|:---|:---|
| `earnings-preview` | Pre-earnings briefing: consensus estimates, beat/miss history, analyst sentiment, key metrics to watch |
| `earnings-recap` | Post-earnings analysis: actual vs estimated, price reaction, margin trends, earnings-day move comparison |
| `estimate-analysis` | EPS/revenue revision trends (7d/30d/60d/90d), revision breadth ratio, growth estimates vs peers/sector/S&P 500 |
| `stock-correlation` | Co-movement discovery, rolling correlation, sector clustering, regime-conditional correlation (crisis detection) |
| `etf-premium` | ETF premium/discount vs NAV, automatic peer comparison by category, screener across 80+ ETFs |
| `sepa-strategy` | Mark Minervini's SEPA methodology: Weinstein stage analysis, 8-condition trend template, VCP pattern, position sizing, stop-loss evolution |

**Use Cases:**
- Earnings season prep for individual stock holdings (NET, AMZN, BRK B, etc.)
- Portfolio concentration risk assessment via correlation analysis
- ETF selection and monitoring (SGOV, QQQI, TQQQ premium/discount tracking)
- Stock entry timing using trend template and VCP breakout patterns

**Requirements:** Python >= 3.10, yfinance

---

### pydoll-antibot-bypasser

A Claude Code skill that teaches Claude how to write stealth browser automation scripts using [Pydoll](https://github.com/autoscrape-labs/pydoll) — an async-native, zero-WebDriver Chromium automation library specialized in bypassing WAF protections and bot detection systems.

**Install:**

```bash
/plugin install pydoll-antibot-bypasser@Esonhugh/Marketplace
```

**Capabilities:**

| Feature | Description |
|:---|:---|
| Cloudflare Turnstile | Auto-detect and solve Turnstile CAPTCHA, works in headless mode |
| Cloudflare Managed Challenge | Bypass with `headless=False` + xvfb on servers |
| Cloudflare JS Challenge | Auto-execute JavaScript challenges |
| Human-like Interaction | Bezier curve mouse movement, typo simulation, random delays |
| Shadow DOM Access | Penetrate closed shadow roots for hidden elements |
| Browser Fingerprint Spoofing | Fake engagement time, WebRTC leak protection, language spoofing |
| Concurrent Scraping | Async-native, multi-tab parallel execution |
| Request Interception | Block images/CSS/fonts to accelerate page loading |

**WAF Support:**

| WAF Provider | Status | Notes |
|:---|:---:|:---|
| Cloudflare Turnstile | ✅ Full | Works in headless mode |
| Cloudflare JS Challenge | ✅ Full | Auto JS execution |
| Cloudflare Managed Challenge | ✅ Verified | Requires `headless=False` + xvfb |
| DataDome | ⚠️ Partial | Needs high-quality proxy |
| PerimeterX | ⚠️ Partial | Needs randomized behavior |
| Akamai Bot Manager | ⚠️ Partial | TLS fingerprint sensitive |

**Included Templates:** `basic_browser`, `bypass_cloudflare`, `web_scraping`, `form_filling`, `hybrid_automation`, `screenshot`, `concurrent_scraping`, `stealth_browser`

**Requirements:** Python >= 3.10, Chrome/Chromium, [uv](https://docs.astral.sh/uv/) (recommended)

---

## Repository Structure

```
Marketplace/
├── .claude-plugin/
│   └── marketplace.json                  # Marketplace catalog
├── plugins/
│   ├── finance-market-analysis/          # Plugin: Finance Market Analysis
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       ├── earnings-preview/
│   │       ├── earnings-recap/
│   │       ├── estimate-analysis/
│   │       ├── etf-premium/
│   │       ├── sepa-strategy/
│   │       └── stock-correlation/
│   ├── ibkr-trade-analyzer/              # Plugin: IBKR Trade Analyzer
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── ibkr-trade-analyzer/
│   │           ├── SKILL.md
│   │           └── scripts/
│   │               └── ibkr_analyzer.py
│   └── pydoll-antibot-bypasser/          # Plugin: Pydoll Antibot Bypasser
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/
│           └── pydoll-antibot-bypasser/
│               ├── SKILL.md
│               ├── examples/
│               ├── knowledge/
│               └── scripts/
└── README.md
```

---

## Disclaimer

All plugins are provided for **authorized security testing, educational purposes, and legitimate automation** only. Users are responsible for complying with applicable laws and target websites' Terms of Service.

---

<p align="center">
  <sub>Maintained by <a href="https://github.com/Esonhugh">Esonhugh</a></sub>
</p>
