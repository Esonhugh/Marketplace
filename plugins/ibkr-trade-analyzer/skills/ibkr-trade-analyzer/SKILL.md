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

Credentials are managed by Claude Code's plugin configuration system and injected
automatically as environment variables when the plugin is enabled:

- `CLAUDE_PLUGIN_OPTION_FLEX_TOKEN` — Flex Web Service token
- `CLAUDE_PLUGIN_OPTION_QUERY_ID` — Flex Query numeric ID
- `CLAUDE_PLUGIN_OPTION_PROXY` — proxy URL (may be empty)

The analyzer script reads these automatically — no manual credential handling needed.

If the user reports that credentials are missing or invalid, guide them to reconfigure:

```
claude plugin configure ibkr-trade-analyzer
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

If `uv` is available, run the analyzer. The script reads credentials from environment
variables automatically — no need to pass `--token` or `--query-id`:

```bash
# Flex Web Service mode — credentials come from CLAUDE_PLUGIN_OPTION_* env vars
uv run ${CLAUDE_PLUGIN_ROOT}/skills/ibkr-trade-analyzer/scripts/ibkr_analyzer.py \
  --mode flex --output reports/
```

```bash
# Local file mode
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

## Troubleshooting

- **`uv` not found:** Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Missing credentials:** Run `claude plugin configure ibkr-trade-analyzer` to set token and query ID
- **"Token expired" error:** Flex tokens rotate — run `claude plugin configure ibkr-trade-analyzer` to update the token
- **Rate limit (10-min cooldown):** Flex queries can run at most once per 10 minutes — tell the user to wait and retry
- **Empty data:** The Flex Query may not include the right sections — guide the user to edit the query to include Trades + Cash Transactions
- **XML parse error on local file:** The file may be CSV, not XML — the script auto-detects, but the user can force format with `--format csv`
