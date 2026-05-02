# IBKR Trade Analyzer

[![Version](https://img.shields.io/badge/version-1.1.0-blue)](https://github.com/Esonhugh/Marketplace/tree/Skyworship/plugins/ibkr-trade-analyzer)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**A Claude Code plugin for analyzing Interactive Brokers trading history — read-only, zero risk.**

## What It Does

This plugin connects to your IBKR account (via the read-only Flex Web Service API) or reads local CSV/XML exports, then generates comprehensive trading analysis reports covering:

| Dimension | Details |
|-----------|---------|
| **Trading Patterns** | Frequency, holding periods, time-of-day patterns, win rate, profit factor |
| **P&L Performance** | Realized P&L, equity curve, Sharpe ratio, max drawdown, monthly returns |
| **Portfolio Structure** | Asset allocation, sector concentration, long/short ratio, position sizing |
| **Fees & Cash Flow** | Commissions, interest, dividends, financing costs, fee-to-PnL ratio |
| **Cash & Currency** | Multi-currency balances, FX conversion rates (1 USD = X FCY), liquidity ratio |
| **Trading Style Profile** | Auto-generated qualitative summary (day/swing/position trader, bias, risk) |
| **Risk Assessment** | Scored 0-100 across 6 dimensions with specific warnings |
| **Price Charts** | Historical price data with buy/sell trade markers overlaid |

### What's New in v1.1.0

- **`--analyzers` flag** — run only the sections you care about (e.g. `--analyzers pnl,fx`), default is all six
- **XML auto-cache** — Flex XML saved to plugin data dir as `{accountId}-flex-ibkr-YYYY-MM-DD.xml`; same-day reruns skip the API call automatically
- **FX rate display** — now shown as `1 USD = X FCY` (more natural for USD-base accounts)
- **Modular analyzers** — split into `analyzers/` subpackage (`trade.py`, `pnl.py`, `portfolio.py`, `cost.py`, `price.py`, `fx.py`)

## Installation

### Method 1: Via Marketplace (Recommended)

First, add this repository as a marketplace source:

```claude
/plugin marketplace add Esonhugh/Marketplace
```

Then install the plugin:

```claude
/plugin install ibkr-trade-analyzer
```

Or with the `claude` CLI:

```bash
claude plugin marketplace add Esonhugh/Marketplace
claude plugin install ibkr-trade-analyzer
```

### Method 2: Clone from GitHub

Clone the entire marketplace repo and point Claude Code to the plugin directory:

```bash
git clone https://github.com/Esonhugh/Marketplace.git
claude --plugin-dir ./Marketplace/plugins/ibkr-trade-analyzer
```

Or clone just the plugin into your plugins directory:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/Esonhugh/Marketplace.git /tmp/marketplace
cd /tmp/marketplace && git sparse-checkout set plugins/ibkr-trade-analyzer
cp -r plugins/ibkr-trade-analyzer ~/.claude/plugins/ibkr-trade-analyzer
```

## Usage

Once installed, simply tell Claude:

```
Analyze my IBKR trading history
```

Claude will guide you through:

1. **Choose data source** — Flex Web Service (online) or local file (offline)
2. **Provide credentials** — Flex Token + Query ID, or a file path
3. **Run analysis** — automated, produces Markdown + interactive HTML reports
4. **Review results** — discuss findings interactively

### Selective Analysis

Run only specific sections with `--analyzers`:

```bash
# P&L deep-dive only
uv run ibkr_analyzer.py --mode flex --analyzers pnl,trade

# FX costs only (no network for prices)
uv run ibkr_analyzer.py --mode file --source activity.xml --analyzers fx --no-prices

# Portfolio snapshot
uv run ibkr_analyzer.py --mode flex --analyzers portfolio --no-prices
```

Available sections: `trade`, `pnl`, `portfolio`, `cost`, `price`, `fx` (default: all).

## Data Source Options

### Option A: Flex Web Service (Recommended)

Pulls data directly from IBKR's read-only reporting API.

**Setup:**
1. Log into [IBKR Account Management](https://www.interactivebrokers.com/sso/Login)
2. Go to **Performance & Reports > Flex Queries**
3. Create a new Activity Flex Query with sections: **Trades, Cash Transactions, Open Positions, Account Information**
4. Set output format to **XML**, save and note the **Query ID**
5. Under **Manage Flex Web Service**, get your **Flex Token**

**Plugin Configuration:** Credentials are prompted automatically when you install the plugin:

```claude
/plugin install ibkr-trade-analyzer
```

Claude Code will prompt you for your Flex Token (stored securely in system keychain)
and Query ID. Credentials are injected automatically on every future run — no files to
manage, no `.gitignore` entries needed.

**For CI/CD or scripting only** — for automation without the interactive prompt, use environment variables:

```bash
export CLAUDE_PLUGIN_OPTION_IBKR_FLEX_TOKEN="your-token-here"
export CLAUDE_PLUGIN_OPTION_IBKR_QUERY_ID="123456"
```

## Configuration

Credentials are configured at install time via Claude Code's built-in settings system — no manual file editing required. To update credentials, reinstall or set environment variables directly.

| Field | Sensitive | Description |
|-------|-----------|-------------|
| `flex_token` | Yes — stored in system keychain | Flex Web Service token |
| `query_id` | No — stored in settings.json | Flex Query numeric ID |
| `proxy` | No | Proxy URL, e.g. `socks5://127.0.0.1:7980`. Falls back to `ALL_PROXY` / `HTTPS_PROXY` env vars |

### Option B: Local File

Export from IBKR Client Portal or TWS, then provide the file path. Supports CSV and XML formats.

- **Client Portal**: Performance & Reports → Statements → Activity → Download (XML recommended)
- **TWS**: Account → Account Window → Export

Example command (if running the script directly):
```bash
uv run ibkr_analyzer.py --mode file --source ~/Downloads/activity.xml --output reports/
```

## Output

Reports are saved to `reports/`:
- `ibkr-analysis-YYYY-MM-DD.md` — full Markdown report with tables
- `ibkr-analysis-YYYY-MM-DD.html` — interactive HTML report with Plotly charts

The Flex XML response is also auto-cached to the plugin data dir (`$CLAUDE_PLUGIN_ROOT/data/`) as `{accountId}-flex-ibkr-YYYY-MM-DD.xml`. Subsequent runs on the same day skip the API call and load from cache automatically.

## Safety Guarantees

This plugin is designed with **read-only safety** as a core principle:

1. **API level** — Flex Web Service has zero write/order endpoints
2. **Code level** — No trading execution libraries imported (no `ibapi`, no `ib_insync`)
3. **Network level** — Only outbound HTTPS to IBKR's Flex reporting endpoints
4. **File level** — Only writes to the `reports/` output directory

## Requirements

- Python >= 3.10
- Dependencies are auto-installed via [PEP 723](https://peps.python.org/pep-0723/) inline metadata with `uv run`

## License

MIT

## Author

[Esonhugh](https://github.com/Esonhugh) — [Plugin Homepage](https://github.com/Esonhugh/Marketplace/tree/Skyworship/plugins/ibkr-trade-analyzer)
