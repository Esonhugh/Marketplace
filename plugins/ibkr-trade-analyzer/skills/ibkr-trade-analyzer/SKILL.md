---
name: ibkr-trade-analyzer
description: >
  Analyze Interactive Brokers (IBKR) trading history with read-only access.
  Generates comprehensive reports on trading patterns, P&L performance, portfolio structure,
  and fee analysis. Supports Flex Web Service API and local CSV/XML file import.
  Use this skill whenever the user mentions IBKR trading analysis, Interactive Brokers
  trade history, portfolio review, trading pattern analysis, P&L breakdown, or wants to
  understand their brokerage trading behavior. Also trigger when the user mentions
  Flex Query, activity statement, trade log analysis, or asks about their win rate,
  Sharpe ratio, max drawdown, or commission costs from IBKR.
---

# IBKR Trade Analyzer

Analyze Interactive Brokers trading history using **read-only** data access. This skill
generates reports covering four dimensions: trading behavior patterns, P&L performance,
portfolio structure, and fee/cash flow analysis.

Safety is the core principle here — the user explicitly wants read-only analysis with
zero risk of accidental order execution. The Flex Web Service is inherently read-only
(no order endpoints exist), and the local file mode has zero network access.

## Interaction Flow

### Step 1: Ask the user how they want to provide data

Use AskUserQuestion to determine the data source:

- **Flex Web Service** — online, pulls data from IBKR's read-only reporting API
- **Local file** — offline, reads a CSV or XML file exported from IBKR

### Step 2: Collect credentials or file path

**If Flex Web Service mode:**

Credentials are stored in `~/.claude/settings.json` under `pluginConfigs`. Because
Python subprocesses launched via `uv run` do **not** inherit `CLAUDE_PLUGIN_OPTION_*`
environment variables from Claude Code's own process, you must read the credentials
explicitly before running the script.

Use the `Read` tool to read `~/.claude/settings.json`, then locate the plugin config:

```json
{
  "pluginConfigs": {
    "ibkr-trade-analyzer@<marketplace-id>": {
      "options": {
        "ibkr_flex_token": "...",
        "ibkr_query_id": "...",
        "proxy": ""
      }
    }
  }
}
```

Find the key that starts with `ibkr-trade-analyzer@` (prefer non-`@inline` entries if
multiple exist). Extract `ibkr_flex_token`, `ibkr_query_id`, and `proxy` from `options`.

If no `ibkr-trade-analyzer@*` entry exists in `pluginConfigs`, guide the user to
reinstall the plugin so credentials are saved:

```
/plugin install ibkr-trade-analyzer
```

To set up a Flex Query for the first time:

> 1. Log into [IBKR Account Management](https://www.interactivebrokers.com/sso/Login)
> 2. Navigate to **Performance & Reports > Flex Queries**
> 3. Click **Create New Flex Query** (Activity Flex Query type)
>    - Enable sections: **Trades, Cash Transactions, Open Positions, Account Information**
>    - Output format: **XML** → Save → note the **Query ID**
> 4. Go to **Performance & Reports > Flex Queries > Manage Flex Web Service**
>    - Generate or view your **Flex Web Service Token**

**If local file mode:**

Use AskUserQuestion to ask for the file path. Accept CSV or XML files. Mention that
the user can export from IBKR via:
- Client Portal: Performance & Reports > Statements > Activity
- TWS: Account > Account Window > Export

### Step 3: Run the analysis

Before running, verify `uv` is available:

```bash
uv --version 2>/dev/null || echo "UV_NOT_FOUND"
```

If the output contains `UV_NOT_FOUND`, tell the user:

> `uv` is required to run the analyzer in an isolated environment (no system Python pollution).
> Install it with:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```
> Then restart your terminal and try again.

If `uv` is available, run the analyzer.

**Flex Web Service mode** — use the credentials extracted from `~/.claude/settings.json`
in Step 2 and pass them explicitly as environment variable prefixes, since `uv run`
subprocesses do not inherit `CLAUDE_PLUGIN_OPTION_*` from Claude Code's process:

```bash
# Replace <TOKEN>, <QUERY_ID>, <PROXY> with values read from ~/.claude/settings.json
CLAUDE_PLUGIN_OPTION_IBKR_FLEX_TOKEN="<TOKEN>" \
CLAUDE_PLUGIN_OPTION_IBKR_QUERY_ID="<QUERY_ID>" \
CLAUDE_PLUGIN_OPTION_PROXY="<PROXY>" \
uv run ${CLAUDE_PLUGIN_ROOT}/skills/ibkr-trade-analyzer/scripts/ibkr_analyzer.py \
  --mode flex --output reports/
```

**Local file mode** — no credentials needed:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/ibkr-trade-analyzer/scripts/ibkr_analyzer.py \
  --mode file --source "$FILE_PATH" --output reports/
```

The script uses PEP 723 inline metadata — `uv run` creates a temporary isolated venv
automatically, installing all dependencies without touching your system Python or any
project virtualenv.

### Step 4: Present results

After the script completes:

1. Read and display the terminal summary output to the user
2. Tell the user where the detailed reports are saved:
   - `reports/ibkr-analysis-YYYY-MM-DD.md` — full Markdown report with tables
   - `reports/ibkr-analysis-YYYY-MM-DD.html` — interactive HTML report with plotly charts

If the user wants to dive deeper into specific findings, read the Markdown report
and discuss the details.

## What the Analysis Covers

**Trading Behavior Patterns:**
Trade frequency distribution, holding periods by asset type (STK/OPT/FUT/CASH),
time-of-day patterns, win rate, profit factor, trade size distribution

**P&L Performance:**
Total realized P&L, equity curve, monthly/quarterly returns, max drawdown,
Sharpe ratio, P&L by asset type and symbol, top 10 best/worst trades

**Portfolio Structure:**
Asset type allocation, sector concentration, long/short ratio,
position concentration (top N holdings with per-position cost basis and unrealized P&L),
currency exposure

**Fees & Cash Flow:**
Total commissions and trends, per-trade costs, interest income/expense,
dividend income, financing costs, fee-to-PnL ratio

**Cash & Currency Analysis:**
Multi-currency cash balances with USD equivalent, account composition breakdown
(cash / quasi-cash treasury ETFs / equity), total liquidity ratio.
FX conversion history with avg rate, rate range, current rate comparison,
rate change since conversion, and FX commission tracking per currency pair.

**Trading Style Profile:**
Auto-generated qualitative summary: trading frequency classification (day/swing/position),
directional bias, risk profile, asset preference (ETF vs stock), income vs growth orientation,
concentration level, cash management style, average position sizing

**Portfolio Risk Assessment:**
Scored 0-100 across 6 dimensions: concentration risk (single-stock exposure), leverage
(leveraged ETF decay risk), drawdown history, directional risk (hedging), liquidity buffer
(treasury/cash allocation), and fee drag. Includes specific warnings and strengths.

**Price History & Trade Overlay:**
For the top traded stock symbols, fetches historical price data via yfinance and
overlays buy/sell markers on the price chart. Use `--no-prices` to skip this,
or `--price-top-n N` to control how many symbols to fetch (default: 5).

## Read-Only Safety Guarantees

This is important context for why the skill is designed the way it is:

1. **API level:** Flex Web Service has zero write/order endpoints — it is a pure reporting service
2. **Code level:** The Python script imports no trading execution libraries (no `ibapi`, no `ib_insync`)
3. **Network level:** Only outbound HTTPS to `gdcdyn.interactivebrokers.com` (Flex endpoints); local file mode has zero network access
4. **File level:** Script only writes to the `reports/` output directory

## Script Reference

The analyzer is split into focused modules under `scripts/analyzers/`. For the full CLI flag reference,
module API, and common recipes, read:

```
${CLAUDE_PLUGIN_ROOT}/skills/ibkr-trade-analyzer/scripts/USAGE.md
```

Key commands at a glance:

| Scenario | Command |
|----------|---------|
| All sections (default — no flag needed) | *(omit `--analyzers`)* |
| Only FX analysis | `--analyzers fx --no-prices` |
| P&L + trading patterns only | `--analyzers pnl,trade` |
| Portfolio snapshot | `--analyzers portfolio --no-prices` |
| Skip price charts (faster, no network) | `--analyzers trade,pnl,portfolio,cost,fx` |
| Debug — dump raw XML | add `--dump-xml debug.xml` |
| Skip price fetch (no network) | add `--no-prices` |
| Filter by date range | `--period 2025-01-01:2025-12-31` |
| Filter by asset type | `--asset-types STK,OPT` |
| Use proxy | `--proxy socks5://127.0.0.1:7980` |
| Custom output dir | `--output /path/to/dir/` |

## Troubleshooting

- **`uv` not found:** Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Missing credentials:** Read `~/.claude/settings.json` and check for a `pluginConfigs["ibkr-trade-analyzer@*"]` entry. If absent, reinstall the plugin (`/plugin install ibkr-trade-analyzer`) — credentials are saved on install. Remember to pass them explicitly to `uv run` (they are not auto-injected into subprocesses).
- **"Token expired" error:** Flex tokens rotate — reinstall the plugin to re-enter a new token (`/plugin install ibkr-trade-analyzer`), then re-read the updated token from `~/.claude/settings.json`
- **Rate limit (10-min cooldown):** Flex queries can run at most once per 10 minutes — tell the user to wait and retry
- **Empty data:** The Flex Query may not include the right sections — guide the user to edit the query to include Trades + Cash Transactions
- **XML parse error on local file:** The file may be CSV, not XML — the script auto-detects, but the user can force format with `--format csv`
