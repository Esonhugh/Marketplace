# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pandas>=2.0",
#     "plotly>=5.0",
#     "jinja2>=3.0",
#     "requests[socks]>=2.28",
#     "yfinance>=0.2",
# ]
# ///
"""IBKR Trading History Analyzer — read-only analysis of Interactive Brokers data.

Supports two data sources:
  - Flex Web Service (online, inherently read-only)
  - Local CSV/XML file import (offline, zero network)

No trading execution libraries are imported. This script only reads and reports.

Usage:
  uv run ibkr_analyzer.py --mode flex --output reports/
  uv run ibkr_analyzer.py --mode file --source activity.xml --output reports/
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from analyzers import CostAnalyzer, FxAnalyzer, PnLAnalyzer, PortfolioAnalyzer, PriceAnalyzer, TradeAnalyzer
from loader import DataLoader
from report import ReportGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description="IBKR Trading History Analyzer (read-only)")
    parser.add_argument("--mode", choices=["flex", "file"], required=True, help="Data source mode")
    parser.add_argument("--token", help="Flex Web Service token")
    parser.add_argument("--query-id", help="Flex Query ID")
    parser.add_argument("--source", help="Local file path (for file mode)")
    parser.add_argument("--output", default="reports/", help="Output directory for reports")
    parser.add_argument("--format", choices=["csv", "xml"], help="Force input format (auto-detected if omitted)")
    parser.add_argument("--period", help="Date range filter, e.g. 2025-01-01:2026-04-19")
    parser.add_argument("--asset-types", help="Filter by asset types, e.g. STK,OPT,FUT,CASH")
    parser.add_argument("--no-prices", action="store_true", help="Skip fetching stock price history from yfinance")
    parser.add_argument("--price-top-n", type=int, default=5, help="Number of top traded symbols to fetch prices for (default: 5)")
    parser.add_argument("--proxy", help="HTTP/SOCKS5 proxy URL, e.g. socks5://127.0.0.1:7980")
    parser.add_argument("--dump-xml", help="Dump raw Flex XML response to this file path for debugging")
    _ALL_SECTIONS = {"trade", "pnl", "portfolio", "cost", "price", "fx"}
    parser.add_argument(
        "--analyzers",
        help=(
            "Comma-separated list of sections to run and include in the report. "
            f"Available: {', '.join(sorted(_ALL_SECTIONS))}. "
            "Default: all sections. Example: --analyzers trade,pnl,fx"
        ),
    )
    args = parser.parse_args()

    enabled_sections: set[str] = _ALL_SECTIONS
    if args.analyzers:
        requested = {s.strip().lower() for s in args.analyzers.split(",")}
        unknown = requested - _ALL_SECTIONS
        if unknown:
            print(f"Error: unknown analyzer(s): {', '.join(sorted(unknown))}. "
                  f"Valid options: {', '.join(sorted(_ALL_SECTIONS))}", file=sys.stderr)
            sys.exit(1)
        enabled_sections = requested
        print(f"Running analyzers: {', '.join(sorted(enabled_sections))}")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Data directory for auto-saving / auto-loading Flex XML files.
    # Resolved from CLAUDE_PLUGIN_ROOT env var (injected by Claude Code plugin system).
    # Falls back to a 'data/' sibling of this script so local dev still works.
    _plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    data_dir = Path(_plugin_root) / "data" if _plugin_root else Path(__file__).parent.parent.parent / "data"

    # Credential resolution: CLI args → plugin userConfig env vars (injected by Claude Code)
    token = args.token or os.environ.get("CLAUDE_PLUGIN_OPTION_IBKR_FLEX_TOKEN")
    query_id = args.query_id or os.environ.get("CLAUDE_PLUGIN_OPTION_IBKR_QUERY_ID")
    proxy = (
        args.proxy
        or os.environ.get("CLAUDE_PLUGIN_OPTION_PROXY")
        or os.environ.get("ALL_PROXY")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
    )

    # Load data
    if args.mode == "flex":
        if not token or not query_id:
            print("Error: Flex token and query ID are required for flex mode.", file=sys.stderr)
            print("Set them via: claude plugin configure ibkr-trade-analyzer", file=sys.stderr)
            print("Or pass --token and --query-id as CLI arguments.", file=sys.stderr)
            sys.exit(1)

        # Check data dir for a today's cached XML before hitting the API.
        today_str = datetime.now().strftime("%Y-%m-%d")
        cached_xml: Path | None = None
        if data_dir.exists():
            matches = sorted(data_dir.glob(f"*-flex-ibkr-{today_str}.xml"), key=lambda p: p.stat().st_mtime, reverse=True)
            if matches:
                cached_xml = matches[0]

        if cached_xml:
            print(f"Found today's cached Flex XML: {cached_xml}")
            print("Loading from cache (skipping API call)...")
            data = DataLoader.from_file(str(cached_xml), "xml")
        else:
            if proxy:
                print(f"Using proxy: {proxy}")
            print("Fetching data from Flex Web Service (read-only)...")
            data = DataLoader.from_flex(token, query_id, proxy=proxy, dump_xml=args.dump_xml, save_dir=data_dir)
    else:
        if not args.source:
            print("Error: --source is required for file mode", file=sys.stderr)
            sys.exit(1)
        print(f"Loading data from {args.source}...")
        data = DataLoader.from_file(args.source, args.format)

    print(f"Loaded: {len(data.trades)} trades, {len(data.cash_transactions)} cash transactions, "
          f"{len(data.open_positions)} open positions")

    # Optional filters
    if args.period:
        parts = args.period.split(":")
        if len(parts) == 2:
            start = datetime.strptime(parts[0], "%Y-%m-%d")
            end = datetime.strptime(parts[1], "%Y-%m-%d")
            data.trades = [t for t in data.trades if t.date_time and start <= t.date_time <= end]
            data.cash_transactions = [ct for ct in data.cash_transactions if ct.date_time and start <= ct.date_time <= end]

    if args.asset_types:
        types = set(args.asset_types.split(","))
        data.trades = [t for t in data.trades if t.asset_category in types]
        data.open_positions = [p for p in data.open_positions if p.asset_category in types]

    # Analyze
    print("Analyzing...")
    ta = TradeAnalyzer(data.trades) if "trade" in enabled_sections else None
    pa = PnLAnalyzer(data.trades) if "pnl" in enabled_sections else None
    porta = PortfolioAnalyzer(
        data.open_positions, data.trades,
        cash_balances=data.cash_balances,
        conversion_rates=data.conversion_rates,
        base_currency=data.base_currency,
    ) if "portfolio" in enabled_sections else None
    ca = CostAnalyzer(data.trades, data.cash_transactions) if "cost" in enabled_sections else None
    fxa = FxAnalyzer(data.trades, base_currency=data.base_currency,
                     conversion_rates=data.conversion_rates) if "fx" in enabled_sections else None

    # Fetch price history
    price_charts: list[dict] = []
    if "price" in enabled_sections and not args.no_prices:
        print("Fetching price history for top traded symbols...")
        price_analyzer = PriceAnalyzer(data.trades, top_n=args.price_top_n)
        top_syms = price_analyzer.get_top_symbols()
        if top_syms:
            prices = price_analyzer.fetch_prices(top_syms)
            for sym, pdf in prices.items():
                price_charts.append(price_analyzer.price_vs_trades_data(sym, pdf))
            print(f"  Fetched price data for: {', '.join(prices.keys())}")

    # Generate reports
    rg = ReportGenerator(
        trade_summary=ta.summary() if ta else {},
        pnl_summary=pa.summary() if pa else {},
        portfolio_summary=porta.summary() if porta else {},
        cost_summary=ca.summary() if ca else {},
        equity_curve=pa.equity_curve_data() if pa else [],
        trade_df=ta.df if ta else __import__("pandas").DataFrame(),
        output_dir=output_dir,
        price_charts=price_charts,
        fx_summary=fxa.summary() if fxa else {},
        enabled_sections=enabled_sections,
    )

    rg.print_terminal_summary()
    md_path = rg.write_markdown()
    html_path = rg.write_html()

    print(f"\nReports saved:")
    print(f"  Markdown: {md_path}")
    print(f"  HTML:     {html_path}")


if __name__ == "__main__":
    main()
