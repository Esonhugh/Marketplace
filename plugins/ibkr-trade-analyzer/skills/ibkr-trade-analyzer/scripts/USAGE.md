# IBKR Analyzer Scripts — Usage Guide

Plugin version: **1.1.0**  
Scripts are split across focused modules under `scripts/`.  
Entry point: **`ibkr_analyzer.py`** (PEP 723 — run with `uv run`, no venv setup needed).

## Quick Start

```bash
# Flex Web Service — fetches live data, auto-saves XML to plugin data dir
uv run ibkr_analyzer.py --mode flex --output reports/

# Second run same day — loads from today's cached XML automatically, no API call
uv run ibkr_analyzer.py --mode flex --output reports/

# Local XML/CSV file
uv run ibkr_analyzer.py --mode file --source activity.xml --output reports/

# Only FX and P&L analysis
uv run ibkr_analyzer.py --mode file --source activity.xml --analyzers fx,pnl
```

## All Options

| Flag | Default | Description |
|------|---------|-------------|
| `--mode flex\|file` | *(required)* | Data source |
| `--token TOKEN` | env `CLAUDE_PLUGIN_OPTION_IBKR_FLEX_TOKEN` | Flex Web Service token |
| `--query-id ID` | env `CLAUDE_PLUGIN_OPTION_IBKR_QUERY_ID` | Flex Query numeric ID |
| `--source PATH` | — | Local CSV or XML file (file mode only) |
| `--format csv\|xml` | auto-detect | Force input format |
| `--output DIR` | `reports/` | Output directory |
| `--period START:END` | all dates | Date filter, e.g. `2025-01-01:2025-12-31` |
| `--asset-types LIST` | all types | Comma-separated, e.g. `STK,OPT` |
| `--analyzers LIST` | all sections | Comma-separated sections to run (see below) |
| `--proxy URL` | env `ALL_PROXY` | HTTP or SOCKS5 proxy, e.g. `socks5://127.0.0.1:7980` |
| `--no-prices` | off | Skip yfinance price history fetch |
| `--price-top-n N` | `5` | Number of top symbols to fetch prices for |
| `--dump-xml PATH` | — | Save raw Flex XML response for debugging |

### `--analyzers` sections

Use `--analyzers` to run only the sections you care about.  
**Default (when flag is omitted): all six sections are enabled.** Specify a subset to focus the report and skip unneeded work.

| Section | What it covers |
|---------|----------------|
| `trade` | Trade counts, win rate, profit factor, by-asset breakdown, day/hour heatmap |
| `pnl` | Total P&L, equity curve, monthly returns, Sharpe ratio, max drawdown, top winners/losers |
| `portfolio` | Open positions, concentration, long/short ratio, cash balances, risk assessment |
| `cost` | Commissions, dividends, interest income, withholding tax, commission trend |
| `price` | Historical price chart with buy/sell markers for top traded symbols (needs network) |
| `fx` | Weighted average exchange rates (1 USD = X FCY), effective rate after commission, MTM P&L |

Examples:

```bash
# Only FX analysis — review currency conversion costs
uv run ibkr_analyzer.py --mode file --source activity.xml --analyzers fx --no-prices

# P&L deep-dive — equity curve, monthly breakdown, winners/losers
uv run ibkr_analyzer.py --mode flex --analyzers pnl,trade

# Portfolio snapshot — current holdings, cash, risk score
uv run ibkr_analyzer.py --mode flex --analyzers portfolio --no-prices

# All sections except price charts (no external network calls beyond Flex)
uv run ibkr_analyzer.py --mode flex --analyzers trade,pnl,portfolio,cost,fx
```

## XML Data Cache

When running in `--mode flex`, the script automatically manages a local XML cache in the plugin's data directory (`$CLAUDE_PLUGIN_ROOT/data/`).

**Auto-save:** After a successful Flex API fetch, the raw XML is saved as:
```
{account_id}-flex-ibkr-YYYY-MM-DD.xml
```

**Auto-load:** On subsequent runs the same day, if a matching file already exists in the data dir, the script loads it instead of hitting the API — no wait, no rate-limit risk.

The cache is per-day. A new fetch happens automatically on the first run of each day.

```
data/
└── U1234567-flex-ibkr-2026-05-02.xml   ← created on first run of the day
```

To force a fresh API fetch (e.g. after new trades), delete the today's file:
```bash
rm "$CLAUDE_PLUGIN_ROOT/data/*-flex-ibkr-$(date +%Y-%m-%d).xml"
```

## Module Overview

```
scripts/
├── ibkr_analyzer.py     ← entry point: argparse + main(), PEP 723 deps header
├── models.py            ← dataclasses: Trade, CashTransaction, OpenPosition, CashBalance, AccountData
├── loader.py            ← DataLoader: Flex API polling, CSV/XML parsing, auto-save/cache, FIFO PnL
├── analyzers/           ← analysis subpackage (one file per analyzer)
│   ├── __init__.py      ← re-exports all six analyzer classes
│   ├── trade.py         ← TradeAnalyzer
│   ├── pnl.py           ← PnLAnalyzer
│   ├── portfolio.py     ← PortfolioAnalyzer
│   ├── cost.py          ← CostAnalyzer
│   ├── price.py         ← PriceAnalyzer
│   └── fx.py            ← FxAnalyzer
└── report.py            ← ReportGenerator: terminal summary, Markdown tables, interactive HTML
```

### `models.py` — Data structures

Pure dataclasses, no external dependencies.

| Class | Purpose |
|-------|---------|
| `Trade` | Single executed trade |
| `CashTransaction` | Dividend / interest / fee entry |
| `OpenPosition` | Current open position |
| `CashBalance` | Per-currency cash balance |
| `AccountData` | Container for all of the above |

### `loader.py` — Data loading

```python
from loader import DataLoader
from pathlib import Path

# Flex Web Service — auto-saves XML to data_dir
data = DataLoader.from_flex(token, query_id, proxy="socks5://...", save_dir=Path("data/"))

# Local file (auto-detects CSV vs XML)
data = DataLoader.from_file("activity.xml")
data = DataLoader.from_file("activity.csv", fmt="csv")
```

Key internals:
- `from_flex()` — two-step flow: SendRequest → poll GetStatement with 1018/1019 retry; `save_dir` triggers auto-save
- `_autosave_xml()` — extracts `accountId` from XML, writes `{id}-flex-ibkr-{date}.xml`
- `_compute_fifo_pnl()` — FIFO lot matching when `fifoPnlRealized` is absent in export
- `_compute_unrealized_pnl()` — derives cost basis from remaining FIFO lots

### `analyzers/` — Analysis subpackage

All analyzers accept `list[Trade]` (and other model lists) and expose a `.summary() -> dict` method.
Import from the package directly — `__init__.py` re-exports everything:

```python
from analyzers import TradeAnalyzer, PnLAnalyzer, PortfolioAnalyzer, CostAnalyzer, PriceAnalyzer, FxAnalyzer

ta   = TradeAnalyzer(data.trades)
pa   = PnLAnalyzer(data.trades)
port = PortfolioAnalyzer(data.open_positions, data.trades,
                         cash_balances=data.cash_balances,
                         conversion_rates=data.conversion_rates,
                         base_currency=data.base_currency)
ca   = CostAnalyzer(data.trades, data.cash_transactions)
fxa  = FxAnalyzer(data.trades, base_currency="USD", conversion_rates=data.conversion_rates)

trade_s = ta.summary()    # win rate, profit factor, by-asset breakdown, ...
pnl_s   = pa.summary()    # total PnL, Sharpe, drawdown, monthly returns, ...
port_s  = port.summary()  # holdings, concentration, FX analysis, cash breakdown, ...
cost_s  = ca.summary()    # commissions, dividends, interest, fee/PnL ratio, ...
fx_s    = fxa.summary()   # per-currency: weighted avg rate (1 USD = X FCY), MTM PnL, ...

# Equity curve for charting
curve = pa.equity_curve_data()   # list[{date, cumulative_pnl}]

# Price data with trade markers (requires network; skippable with --no-prices)
price_a = PriceAnalyzer(data.trades, top_n=5)
symbols = price_a.get_top_symbols()
prices  = price_a.fetch_prices(symbols)              # {sym: DataFrame}
charts  = [price_a.price_vs_trades_data(s, df) for s, df in prices.items()]
```

### `report.py` — Report generation

```python
from report import ReportGenerator
from pathlib import Path

rg = ReportGenerator(
    trade_summary=trade_s,
    pnl_summary=pnl_s,
    portfolio_summary=port_s,
    cost_summary=cost_s,
    equity_curve=curve,
    trade_df=ta.df,                  # pandas DataFrame from TradeAnalyzer
    output_dir=Path("reports/"),
    price_charts=charts,             # optional
    fx_summary=fx_s,                 # optional
    enabled_sections={"pnl", "fx"},  # optional — defaults to all six
)

rg.print_terminal_summary()   # prints to stdout, returns str
md_path   = rg.write_markdown()   # → reports/ibkr-analysis-YYYY-MM-DD.md
html_path = rg.write_html()       # → reports/ibkr-analysis-YYYY-MM-DD.html
```

## Credential Resolution Order

For `--mode flex`, credentials are resolved in this order:

1. CLI flags: `--token`, `--query-id`, `--proxy`
2. Plugin userConfig env vars: `CLAUDE_PLUGIN_OPTION_IBKR_FLEX_TOKEN`, `CLAUDE_PLUGIN_OPTION_IBKR_QUERY_ID`, `CLAUDE_PLUGIN_OPTION_PROXY`

Configure credentials (prompted automatically at install time):
```bash
/plugin install ibkr-trade-analyzer
```

## Common Recipes

```bash
# Debug: dump raw XML to inspect what IBKR returned
uv run ibkr_analyzer.py --mode flex --dump-xml debug.xml --output reports/

# Force fresh fetch today (delete cached XML first)
rm "$CLAUDE_PLUGIN_ROOT/data/"*-flex-ibkr-$(date +%Y-%m-%d).xml
uv run ibkr_analyzer.py --mode flex --output reports/

# Analyse only stocks, skip expensive price fetch
uv run ibkr_analyzer.py --mode file --source activity.xml \
  --asset-types STK --no-prices --output reports/

# Narrow to a specific quarter
uv run ibkr_analyzer.py --mode flex \
  --period 2025-01-01:2025-03-31 --output reports/q1-2025/

# Behind a SOCKS5 proxy (e.g. local VPN tunnel)
uv run ibkr_analyzer.py --mode flex \
  --proxy socks5://127.0.0.1:7980 --output reports/
```

## Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `Flex SendRequest failed` | Invalid token or query ID | Reinstall plugin (`/plugin install ibkr-trade-analyzer`) or set `CLAUDE_PLUGIN_OPTION_IBKR_FLEX_TOKEN` / `CLAUDE_PLUGIN_OPTION_IBKR_QUERY_ID` |
| `code 1018 / 1019, waiting…` | Report still generating (normal) | Wait; script retries automatically up to 10× |
| `code 1003` | Token expired | Re-run plugin configure to update token |
| `Rate limit` | Flex queries limited to once per 10 min | Wait 10 minutes, or reuse today's cached XML |
| `File not found` | Wrong `--source` path | Check path; use absolute path if unsure |
| `XML parse error` | File is CSV, not XML | Add `--format csv` to force format |
| `uv: command not found` | uv not installed | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
