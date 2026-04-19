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

First, check if environment variables are already set:
- `$IBKR_FLEX_TOKEN`
- `$IBKR_QUERY_ID`

If either is missing, use AskUserQuestion to collect them. When asking, include these
setup instructions so the user knows where to find them:

> **How to get your Flex Token and Query ID:**
>
> 1. Log into [IBKR Account Management](https://www.interactivebrokers.com/sso/Login)
> 2. Navigate to **Performance & Reports > Flex Queries**
> 3. Click **Create New Flex Query** (Activity Flex Query type)
>    - In the "Sections" (Models) selection, check these 4 modules:
>      **Trades, Cash Transactions, Open Positions, Account Information**
>    - Other modules (NAV, Cash Report, Corporate Actions, etc.) are optional
>    - Set the output format to **XML**
>    - Save the query — note the **Query ID** shown
> 4. Go to **Performance & Reports > Flex Queries > Manage Flex Web Service**
>    - Generate or view your **Flex Web Service Token**
>
> The token is a long alphanumeric string. The Query ID is a numeric ID.

Ask for the token first, then the query ID, as separate AskUserQuestion calls.

**If local file mode:**

Use AskUserQuestion to ask for the file path. Accept CSV or XML files. Mention that
the user can export from IBKR via:
- Client Portal: Performance & Reports > Statements > Activity
- TWS: Account > Account Window > Export

### Step 3: Run the analysis

The analyzer script is bundled at `scripts/ibkr_analyzer.py` within this skill directory.
Locate it relative to this SKILL.md file and run it with `uv run`.

```bash
# Flex Web Service mode
uv run .claude/skills/ibkr-trade-analyzer/scripts/ibkr_analyzer.py \
  --mode flex --token "$TOKEN" --query-id "$QUERY_ID" --output reports/
```

Or for local file mode:

```bash
# Local file mode
uv run .claude/skills/ibkr-trade-analyzer/scripts/ibkr_analyzer.py \
  --mode file --source "$FILE_PATH" --output reports/
```

The script uses PEP 723 inline metadata for dependencies — `uv run` handles
installation automatically, no `pyproject.toml` or venv setup needed.

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

- **"Token expired" error:** Flex tokens rotate — guide the user back to Account Management to regenerate
- **Rate limit (10-min cooldown):** Flex queries can run at most once per 10 minutes — tell the user to wait and retry
- **Empty data:** The Flex Query may not include the right sections — guide the user to edit the query to include Trades + Cash Transactions
- **XML parse error on local file:** The file may be CSV, not XML — the script auto-detects, but the user can force format with `--format csv`
