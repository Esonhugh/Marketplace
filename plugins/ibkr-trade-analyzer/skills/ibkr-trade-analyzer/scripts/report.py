"""IBKR report generator — terminal summary, Markdown, and interactive HTML."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class ReportGenerator:
    """Generate terminal summary, Markdown report, and HTML report."""

    def __init__(
        self,
        trade_summary: dict,
        pnl_summary: dict,
        portfolio_summary: dict,
        cost_summary: dict,
        equity_curve: list[dict],
        trade_df: pd.DataFrame,
        output_dir: Path,
        price_charts: list[dict] | None = None,
        fx_summary: dict | None = None,
        enabled_sections: set[str] | None = None,
    ):
        self.trade_s = trade_summary
        self.pnl_s = pnl_summary
        self.port_s = portfolio_summary
        self.cost_s = cost_summary
        self.equity_curve = equity_curve
        self.trade_df = trade_df
        self.output_dir = output_dir
        self.price_charts = price_charts or []
        self.fx_s = fx_summary or {}
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        # Default: all sections enabled
        _all = {"trade", "pnl", "portfolio", "cost", "price", "fx"}
        self.enabled = enabled_sections if enabled_sections is not None else _all

    def _on(self, *sections: str) -> bool:
        """Return True if any of the given section names are enabled."""
        return any(s in self.enabled for s in sections)

    # ---- Terminal summary ----

    def print_terminal_summary(self) -> str:
        lines = ["=" * 55, "  IBKR Trading Analysis Summary", "=" * 55]

        if self.trade_df.empty:
            lines.append("No trade data available.")
            summary = "\n".join(lines)
            print(summary)
            return summary

        period_start = self.trade_df["date_time"].min().strftime("%Y-%m-%d")
        period_end = self.trade_df["date_time"].max().strftime("%Y-%m-%d")
        lines += [f"Period: {period_start} to {period_end}", ""]

        if self._on("trade"):
            pnl = self.pnl_s.get("total_realized_pnl", 0) if self._on("pnl") else None
            lines.append(
                f"Total Trades: {self.trade_s.get('total_trades', 0):,}  |  "
                f"Win Rate: {self.trade_s.get('win_rate', 0):.1f}%  |  "
                f"Profit Factor: {self.trade_s.get('profit_factor', 0):.2f}"
            )
        if self._on("pnl"):
            pnl = self.pnl_s.get("total_realized_pnl", 0)
            lines.append(
                f"Total P&L: ${pnl:,.2f}  |  "
                f"Max Drawdown: {self.pnl_s.get('max_drawdown_pct', 0):.1f}%  |  "
                f"Sharpe: {self.pnl_s.get('sharpe_ratio', 0):.2f}"
            )
        if self._on("cost"):
            comm = self.cost_s.get("total_commissions", 0)
            lines.append(f"Total Fees: ${comm:,.2f} ({self.cost_s.get('fee_to_pnl_ratio_pct', 0):.1f}% of gross profit)")

        if self._on("pnl"):
            winners = self.pnl_s.get("top_winners", [])
            losers = self.pnl_s.get("top_losers", [])
            if winners:
                lines.append(f"Top Performer: {winners[0]['symbol']} (+${winners[0]['pnl']:,.2f})")
            if losers:
                lines.append(f"Worst Performer: {losers[0]['symbol']} (${losers[0]['pnl']:,.2f})")

        if self._on("trade", "pnl", "portfolio"):
            lines += ["", "Key Findings:"]
        if self._on("trade"):
            by_asset = self.trade_s.get("by_asset", {})
            if by_asset:
                best = max(by_asset, key=lambda c: by_asset[c].get("win_rate", 0))
                lines.append(f"  - Best win rate by asset: {best} ({by_asset[best]['win_rate']:.1f}%)")
            by_weekday = self.trade_s.get("by_weekday", {})
            if by_weekday:
                busiest = max(by_weekday, key=by_weekday.get)
                lines.append(f"  - Most active trading day: {busiest} ({by_weekday[busiest]} trades)")
        if self._on("portfolio"):
            top5 = self.port_s.get("top5_concentration_pct", 0)
            if top5 > 0:
                lines.append(f"  - Top 5 positions: {top5:.1f}% of portfolio")
        if self._on("cost"):
            div = self.cost_s.get("net_dividend", 0)
            if div != 0:
                lines.append(f"  - Net dividend income: ${div:,.2f}")

        if self._on("portfolio"):
            cash = self.port_s.get("cash", {})
            if cash:
                lines += ["", "Account Breakdown:"]
                lines.append(f"  - Cash: ${cash.get('total_cash_base', 0):,.2f} ({cash.get('cash_pct', 0):.1f}%)")
                lines.append(f"  - Quasi-cash (treasury): ${cash.get('quasi_cash', 0):,.2f} ({cash.get('quasi_cash_pct', 0):.1f}%)")
                lines.append(f"  - Equity: ${cash.get('equity_value', 0):,.2f} ({cash.get('equity_pct', 0):.1f}%)")
                lines.append(f"  - Total account: ${cash.get('total_account_value', 0):,.2f}")
                for b in cash.get("balances", []):
                    if b["currency"] != self.port_s.get("base_currency", "USD"):
                        lines.append(f"    {b['currency']}: {b['amount']:,.2f} (≈${b['base_value']:,.2f})")

        if self._on("fx") and self.fx_s:
            lines += ["", "FX Weighted Avg Rates (USD → foreign):"]
            for ccy, fx in self.fx_s.items():
                rate = fx["weighted_avg_rate"]
                fcy_per_usd = 1 / rate if rate else 0.0
                total_f = fx["total_foreign_exchanged"]
                total_b = fx["total_base_exchanged"]
                line = f"  - {ccy}: {total_f:,.2f} {ccy} → ${total_b:,.2f}  |  avg rate 1 USD = {fcy_per_usd:.4f} {ccy}"
                if fx.get("current_rate"):
                    curr_fcy_per_usd = 1 / fx["current_rate"] if fx["current_rate"] else 0.0
                    diff_pct = (fx["current_rate"] - rate) / rate * 100
                    line += f"  (market 1 USD = {curr_fcy_per_usd:.4f} {ccy}, {diff_pct:+.2f}%)"
                if fx.get("mtm_pnl"):
                    mtm = fx["mtm_pnl"]
                    line += f"  MTM {'+' if mtm >= 0 else ''}${mtm:,.2f}"
                lines.append(line)

        profile = self._build_style_profile()
        if profile:
            lines += ["", "Trading Style:"]
            for label, value in profile:
                lines.append(f"  - {label}: {value}")

        risk = self._build_risk_assessment()
        if risk:
            lines += ["", f"Risk Score: {risk['overall_score']}/100 ({risk['overall_level']})"]
            for w in risk.get("warnings", []):
                lines.append(f"  ⚠ {w}")
            for s in risk.get("strengths", []):
                lines.append(f"  ✓ {s}")

        lines.append("=" * 55)
        summary = "\n".join(lines)
        print(summary)
        return summary

    # ---- Markdown report ----

    def write_markdown(self) -> Path:
        out = self.output_dir / f"ibkr-analysis-{self.date_str}.md"
        enabled_label = ", ".join(sorted(self.enabled)) if self.enabled != {"trade", "pnl", "portfolio", "cost", "price", "fx"} else "all"
        s = ["# IBKR Trading Analysis Report\n", f"Generated: {self.date_str}  |  Sections: {enabled_label}\n"]

        # Trading behavior
        if self._on("trade"):
            s += [
                "## Trading Behavior Patterns\n",
                "| Metric | Value |", "|--------|-------|",
                f"| Total Trades | {self.trade_s.get('total_trades', 0):,} |",
                f"| Win Rate | {self.trade_s.get('win_rate', 0):.1f}% |",
                f"| Profit Factor | {self.trade_s.get('profit_factor', 0):.2f} |",
                f"| Avg Trade Size | ${self.trade_s.get('avg_trade_size', 0):,.0f} |",
                f"| Trades Per Day | {self.trade_s.get('trades_per_day', 0):.1f} |", "",
            ]
            by_asset = self.trade_s.get("by_asset", {})
            if by_asset:
                s += ["### By Asset Type\n", "| Asset | Trades | Win Rate | Total P&L |", "|-------|--------|----------|-----------|"]
                for cat, info in sorted(by_asset.items()):
                    s.append(f"| {cat} | {info['count']:,} | {info['win_rate']:.1f}% | ${info['total_pnl']:,.2f} |")
                s.append("")

        # P&L
        if self._on("pnl"):
            best = self.pnl_s.get("best_month")
            worst = self.pnl_s.get("worst_month")
            s += [
                "## P&L Performance\n",
                "| Metric | Value |", "|--------|-------|",
                f"| Total Realized P&L | ${self.pnl_s.get('total_realized_pnl', 0):,.2f} |",
                f"| Max Drawdown | {self.pnl_s.get('max_drawdown_pct', 0):.1f}% |",
                f"| Sharpe Ratio | {self.pnl_s.get('sharpe_ratio', 0):.2f} |",
            ]
            if best:
                s.append(f"| Best Month | {best['period']} (${best['pnl']:,.2f}) |")
            if worst:
                s.append(f"| Worst Month | {worst['period']} (${worst['pnl']:,.2f}) |")
            s.append("")

            for label, key in [("Top 10 Winners", "top_winners"), ("Top 10 Losers", "top_losers")]:
                items = self.pnl_s.get(key, [])
                if items:
                    s += [f"### {label}\n", "| Symbol | P&L |", "|--------|-----|"]
                    for it in items:
                        s.append(f"| {it['symbol']} | ${it['pnl']:,.2f} |")
                    s.append("")

        # Portfolio
        if self._on("portfolio"):
            pa = self.port_s
            s.append("## Portfolio Structure\n")
            if pa.get("total_positions", 0) > 0:
                s += [
                    "| Metric | Value |", "|--------|-------|",
                    f"| Open Positions | {pa['total_positions']} |",
                    f"| Total Value | ${pa.get('total_value', 0):,.2f} |",
                    f"| Unrealized P&L | ${pa.get('unrealized_pnl', 0):,.2f} |",
                    f"| Long % | {pa.get('long_pct', 0):.1f}% |",
                    f"| Short % | {pa.get('short_pct', 0):.1f}% |",
                    f"| Top 5 Concentration | {pa.get('top5_concentration_pct', 0):.1f}% |", "",
                ]
                holdings = pa.get("top_holdings", [])
                if holdings:
                    s += ["### Top Holdings\n",
                          "| Symbol | Qty | Cost Basis | Market Value | Unrealized P&L | % |",
                          "|--------|-----|-----------|-------------|----------------|---|"]
                    for h in holdings:
                        qty = h.get("quantity", 0)
                        cb = h.get("cost_basis", 0)
                        upnl = h.get("unrealized_pnl", 0)
                        qty_str = f"{qty:g}" if qty == int(qty) else f"{qty:.4f}"
                        s.append(f"| {h['symbol']} | {qty_str} | "
                                 f"{'${:,.2f}'.format(cb) if cb > 0 else 'N/A'} | "
                                 f"${h['value']:,.2f} | "
                                 f"{'${:+,.2f}'.format(upnl) if cb > 0 else 'N/A'} | "
                                 f"{h['pct']:.1f}% |")
                    s.append("")
            else:
                s.append(f"_{pa.get('note', 'No open position data available.')}_\n")

            # Cash & FX (sub-section of portfolio)
            cash = pa.get("cash", {})
            if cash:
                s += [
                    "## Cash & Currency Analysis\n",
                    "### Cash Balances\n",
                    "| Currency | Amount | USD Equivalent | Rate |",
                    "|----------|--------|---------------|------|",
                ]
                for b in cash.get("balances", []):
                    rate_str = f"{b['rate']:.4f}" if b["rate"] > 0 else "—"
                    s.append(f"| {b['currency']} | {b['amount']:,.2f} | ${b['base_value']:,.2f} | {rate_str} |")
                s += [
                    "", "### Account Composition\n",
                    "| Category | Value | % of Account |", "|----------|-------|-------------|",
                    f"| Cash (all currencies) | ${cash.get('total_cash_base', 0):,.2f} | {cash.get('cash_pct', 0):.1f}% |",
                    f"| Quasi-cash (treasury ETFs) | ${cash.get('quasi_cash', 0):,.2f} | {cash.get('quasi_cash_pct', 0):.1f}% |",
                    f"| **Total Liquid** | **${cash.get('total_liquid', 0):,.2f}** | **{cash.get('total_liquid_pct', 0):.1f}%** |",
                    f"| Equity positions | ${cash.get('equity_value', 0):,.2f} | {cash.get('equity_pct', 0):.1f}% |",
                    f"| **Total Account** | **${cash.get('total_account_value', 0):,.2f}** | **100%** |", "",
                ]
                for f in cash.get("fx_analysis", []):
                    s += [
                        f"**{f['pair']}** ({f['n_trades']} trades, {f['first_date']} ~ {f['last_date']})\n",
                        "| Metric | Value |", "|--------|-------|",
                        f"| Total Converted | {f['total_base_amount']:,.2f} base / {f['total_quote_amount']:,.2f} quote |",
                        f"| Avg Rate | {f['avg_rate']:.4f} |",
                        f"| Rate Range | {f['min_rate']:.4f} ~ {f['max_rate']:.4f} |",
                    ]
                    if f.get("current_rate"):
                        s.append(f"| Current Rate | {f['current_rate']:.4f} |")
                    s.append(f"| FX Commission | ${f['total_commission']:,.2f} |")
                    if f.get("rate_change_pct") is not None:
                        s.append(f"| Rate Change | {f['rate_change_pct']:+.2f}% since avg conversion |")
                    s.append("")

        # Costs
        if self._on("cost"):
            s += [
                "## Fees & Cash Flow\n",
                "| Metric | Value |", "|--------|-------|",
                f"| Total Commissions | ${self.cost_s.get('total_commissions', 0):,.2f} |",
                f"| Avg Per Trade | ${self.cost_s.get('avg_commission_per_trade', 0):,.2f} |",
                f"| Fee/Profit Ratio | {self.cost_s.get('fee_to_pnl_ratio_pct', 0):.1f}% |",
                f"| Dividend Income | ${self.cost_s.get('dividend_income', 0):,.2f} |",
                f"| Withholding Tax | ${self.cost_s.get('withholding_tax', 0):,.2f} |",
                f"| Net Interest | ${self.cost_s.get('interest_net', 0):,.2f} |", "",
            ]

        # FX weighted average rates
        if self._on("fx") and self.fx_s:
            s += [
                "## FX Conversion Analysis\n",
                "_Weighted average rate = total USD exchanged ÷ total foreign currency exchanged "
                "(volume-weighted, not arithmetic mean)._\n",
                "| Currency | Trades | Total Foreign | Total USD | Avg Rate (1 USD=) | Effective Rate¹ | Spread % | Commission |",
                "|----------|--------|--------------|-----------|-------------------|----------------|----------|------------|",
            ]
            for ccy, fx in self.fx_s.items():
                rate = fx["weighted_avg_rate"]
                eff = fx["effective_rate"]
                fcy_per_usd = 1 / rate if rate else 0.0
                eff_fcy_per_usd = 1 / eff if eff else 0.0
                s.append(
                    f"| {ccy} | {fx['n_trades']} "
                    f"| {fx['total_foreign_exchanged']:,.2f} {ccy} "
                    f"| ${fx['total_base_exchanged']:,.2f} "
                    f"| 1 USD = {fcy_per_usd:.4f} {ccy} "
                    f"| 1 USD = {eff_fcy_per_usd:.4f} {ccy} "
                    f"| {fx['rate_spread_pct']:.2f}% "
                    f"| ${fx['total_commission']:,.2f} ({fx['commission_pct']:.2f}%) |"
                )
            s.append("\n¹ Effective rate = (total USD paid − commission) ÷ total foreign received\n")

            for ccy, fx in self.fx_s.items():
                rate = fx["weighted_avg_rate"]
                eff = fx["effective_rate"]
                best = fx["best_rate"]
                worst = fx["worst_rate"]
                fcy_per_usd_avg = 1 / rate if rate else 0.0
                fcy_per_usd_eff = 1 / eff if eff else 0.0
                fcy_per_usd_best = 1 / best if best else 0.0
                fcy_per_usd_worst = 1 / worst if worst else 0.0
                s += [f"### {ccy} → USD\n",
                      "| Metric | Value |", "|--------|-------|",
                      f"| Period | {fx['first_date']} ~ {fx['last_date']} |",
                      f"| Trades | {fx['n_trades']} |",
                      f"| Total {ccy} exchanged | {fx['total_foreign_exchanged']:,.4f} |",
                      f"| Total USD received | ${fx['total_base_exchanged']:,.4f} |",
                      f"| Weighted avg rate | 1 USD = {fcy_per_usd_avg:.4f} {ccy} |",
                      f"| Effective rate (after commission) | 1 USD = {fcy_per_usd_eff:.4f} {ccy} |",
                      f"| Best single-trade rate | 1 USD = {fcy_per_usd_best:.4f} {ccy} |",
                      f"| Worst single-trade rate | 1 USD = {fcy_per_usd_worst:.4f} {ccy} |",
                      f"| Rate spread | {fx['rate_spread_pct']:.2f}% |",
                      f"| Total FX commission | ${fx['total_commission']:,.4f} ({fx['commission_pct']:.3f}% of USD) |",
                ]
                if fx.get("current_rate"):
                    curr_fcy_per_usd = 1 / fx["current_rate"] if fx["current_rate"] else 0.0
                    diff_pct = (fx["current_rate"] - fx["weighted_avg_rate"]) / fx["weighted_avg_rate"] * 100
                    s.append(f"| Current market rate | 1 USD = {curr_fcy_per_usd:.4f} {ccy} ({diff_pct:+.2f}% vs your avg) |")
                if fx.get("mtm_pnl") is not None:
                    mtm = fx["mtm_pnl"]
                    s.append(f"| MTM P&L vs current rate | {'+'if mtm>=0 else ''}${mtm:,.2f} ({fx.get('mtm_pnl_pct',0):+.2f}%) |")
                s.append("")

        # Style profile (derived from trade + portfolio data)
        if self._on("trade", "portfolio"):
            profile = self._build_style_profile()
            if profile:
                s.append("## Trading Style Profile\n")
                for label, value in profile:
                    s.append(f"- **{label}:** {value}")
                s.append("")

        # Risk assessment (derived from portfolio data)
        if self._on("portfolio"):
            risk_report = self._build_risk_assessment()
            if risk_report:
                score = risk_report.get("overall_score", 0)
                level = risk_report.get("overall_level", "")
                s += [
                    "## Portfolio Risk Assessment\n",
                    f"**Overall Risk Score: {score}/100 ({level})**\n",
                ]
                details = risk_report.get("details", [])
                if details:
                    s += ["| Risk Factor | Score | Rating | Detail |", "|-------------|-------|--------|--------|"]
                    for d in details:
                        s.append(f"| {d['factor']} | {d['score']}/100 | {d['rating']} | {d['detail']} |")
                    s.append("")
                if risk_report.get("warnings"):
                    s.append("### Risk Warnings\n")
                    for w in risk_report["warnings"]:
                        s.append(f"- {w}")
                    s.append("")
                if risk_report.get("strengths"):
                    s.append("### Strengths\n")
                    for st in risk_report["strengths"]:
                        s.append(f"- {st}")
                    s.append("")

        out.write_text("\n".join(s), encoding="utf-8")
        return out

    # ---- Style profile ----

    def _build_style_profile(self) -> list[tuple[str, str]]:
        profile: list[tuple[str, str]] = []
        tpd = self.trade_s.get("trades_per_day", 0)
        if tpd >= 5:
            freq = "Day Trader (high frequency)"
        elif tpd >= 1:
            freq = "Active Trader"
        elif tpd >= 0.2:
            freq = "Swing Trader (low frequency)"
        else:
            freq = "Position Trader / Long-term Investor"
        profile.append(("Trading Frequency", f"{freq} ({tpd:.1f} trades/day)"))

        long_pct = self.port_s.get("long_pct", 0)
        short_pct = self.port_s.get("short_pct", 0)
        if short_pct == 0:
            bias = "Pure Long — no short exposure"
        elif long_pct > 80:
            bias = f"Long-biased ({long_pct:.0f}% long / {short_pct:.0f}% short)"
        elif short_pct > 80:
            bias = f"Short-biased ({short_pct:.0f}% short)"
        else:
            bias = f"Balanced ({long_pct:.0f}% long / {short_pct:.0f}% short)"
        profile.append(("Directional Bias", bias))

        dd = self.pnl_s.get("max_drawdown_pct", 0)
        wr = self.trade_s.get("win_rate", 0)
        sharpe = self.pnl_s.get("sharpe_ratio", 0)
        if dd < 5 and wr > 70:
            risk = "Conservative — low drawdown, high win rate"
        elif dd < 15:
            risk = "Moderate"
        else:
            risk = "Aggressive — high drawdown tolerance"
        if sharpe > 2:
            risk += f", excellent risk-adjusted returns (Sharpe {sharpe:.2f})"
        elif sharpe > 1:
            risk += f", good risk-adjusted returns (Sharpe {sharpe:.2f})"
        profile.append(("Risk Profile", risk))

        holdings = self.port_s.get("top_holdings", [])
        if holdings:
            etf_keywords = {"ETF", "SGOV", "TQQQ", "QQQI", "QQQ", "SPY", "IVV", "VOO", "VTI", "AGG", "BND"}
            etf_pct = sum(h["pct"] for h in holdings if h["symbol"] in etf_keywords or h["symbol"].endswith("Q"))
            stock_pct = 100 - etf_pct
            if etf_pct > 70:
                pref = f"ETF-centric ({etf_pct:.0f}% ETFs)"
            elif stock_pct > 70:
                pref = f"Individual stock picker ({stock_pct:.0f}% stocks)"
            else:
                pref = f"Mixed ({stock_pct:.0f}% stocks, {etf_pct:.0f}% ETFs)"
            profile.append(("Asset Preference", pref))

        div = self.cost_s.get("dividend_income", 0)
        total_pnl = self.pnl_s.get("total_realized_pnl", 0)
        unrealized = self.port_s.get("unrealized_pnl", 0)
        total_return = total_pnl + unrealized + div
        if total_return > 0 and div >= 0:
            div_share = div / total_return * 100 if div > 0 else 0
            if div_share > 40:
                orient = f"Income-oriented — dividends contribute {div_share:.0f}% of total return"
            elif div_share > 15:
                orient = f"Balanced growth + income (dividends = {div_share:.0f}% of return)"
            else:
                orient = f"Growth-oriented — capital gains dominate ({100 - div_share:.0f}% of return)"
            profile.append(("Investment Style", orient))

        top5 = self.port_s.get("top5_concentration_pct", 0)
        n_pos = self.port_s.get("total_positions", 0)
        if top5 > 90:
            conc = f"Highly concentrated — top 5 = {top5:.0f}% across {n_pos} positions"
        elif top5 > 60:
            conc = f"Moderately concentrated — top 5 = {top5:.0f}%"
        else:
            conc = f"Well diversified — top 5 = {top5:.0f}%"
        profile.append(("Concentration", conc))

        if holdings:
            cash_etfs = {"SGOV", "SHV", "BIL", "SCHO", "VGSH"}
            cash_pct = sum(h["pct"] for h in holdings if h["symbol"] in cash_etfs)
            if cash_pct > 30:
                profile.append(("Cash Management", f"Active — {cash_pct:.0f}% in short-term treasury ETFs as cash substitute"))
            elif cash_pct > 10:
                profile.append(("Cash Management", f"Moderate cash reserve ({cash_pct:.0f}% in treasury ETFs)"))

        avg_size = self.trade_s.get("avg_trade_size", 0)
        total_value = self.port_s.get("total_value", 0)
        if avg_size > 0 and total_value > 0:
            size_pct = avg_size / total_value * 100
            profile.append(("Avg Position Size", f"${avg_size:,.0f} ({size_pct:.1f}% of portfolio per trade)"))

        return profile

    # ---- Risk assessment ----

    def _build_risk_assessment(self) -> dict:
        details: list[dict] = []
        warnings: list[str] = []
        strengths: list[str] = []
        holdings = self.port_s.get("top_holdings", [])
        top5 = self.port_s.get("top5_concentration_pct", 0)

        if holdings:
            max_single = max(h["pct"] for h in holdings)
            max_sym = max(holdings, key=lambda h: h["pct"])["symbol"]
            if max_single > 50:
                conc_score = min(90, 50 + int(max_single - 50))
                conc_rating = "HIGH"
                warnings.append(f"{max_sym} alone is {max_single:.0f}% of portfolio — single-asset risk is elevated")
            elif max_single > 30:
                conc_score = 30 + int(max_single - 30)
                conc_rating = "MEDIUM"
            else:
                conc_score = int(max_single)
                conc_rating = "LOW"
                strengths.append("No single position exceeds 30% — good diversification")
            details.append({"factor": "Concentration", "score": conc_score, "rating": conc_rating,
                            "detail": f"Largest position: {max_sym} at {max_single:.0f}%, top 5 = {top5:.0f}%"})

            leveraged_etfs = {"TQQQ", "SQQQ", "UPRO", "SPXU", "TNA", "TZA", "SOXL", "SOXS", "FNGU", "FNGD", "LABU", "LABD"}
            lev_pct = sum(h["pct"] for h in holdings if h["symbol"] in leveraged_etfs)
            if lev_pct > 10:
                lev_score, lev_rating = min(90, int(lev_pct * 3)), "HIGH"
                warnings.append(f"{lev_pct:.1f}% in leveraged ETFs — daily rebalancing causes decay in sideways markets")
            elif lev_pct > 0:
                lev_score, lev_rating = max(10, int(lev_pct * 3)), "LOW"
                strengths.append(f"Minimal leveraged ETF exposure ({lev_pct:.1f}%)")
            else:
                lev_score, lev_rating = 0, "NONE"
                strengths.append("No leveraged ETF exposure")
            details.append({"factor": "Leverage", "score": lev_score, "rating": lev_rating,
                            "detail": f"{lev_pct:.1f}% in leveraged ETFs"})

        dd = self.pnl_s.get("max_drawdown_pct", 0)
        if dd < 5:
            dd_score, dd_rating = int(dd * 4), "LOW"
            strengths.append(f"Max drawdown only {dd:.1f}% — excellent capital preservation")
        elif dd < 20:
            dd_score, dd_rating = 20 + int((dd - 5) * 2), "MEDIUM"
        else:
            dd_score, dd_rating = min(95, 50 + int(dd - 20)), "HIGH"
            warnings.append(f"Max drawdown {dd:.1f}% — significant capital at risk")
        details.append({"factor": "Drawdown", "score": dd_score, "rating": dd_rating, "detail": f"Max drawdown: {dd:.1f}%"})

        long_pct = self.port_s.get("long_pct", 100)
        if long_pct in (100, 0):
            dir_score, dir_rating = 60, "MEDIUM"
            warnings.append("100% directional — no hedging against market downturns")
        elif long_pct > 80 or long_pct < 20:
            dir_score, dir_rating = 40, "MEDIUM"
        else:
            dir_score, dir_rating = 15, "LOW"
            strengths.append("Balanced long/short exposure provides natural hedge")
        details.append({"factor": "Directional", "score": dir_score, "rating": dir_rating,
                        "detail": f"{long_pct:.0f}% long / {100 - long_pct:.0f}% short"})

        if holdings:
            safe_assets = {"SGOV", "SHV", "BIL", "SCHO", "VGSH"}
            safe_pct = sum(h["pct"] for h in holdings if h["symbol"] in safe_assets)
            if safe_pct > 30:
                liq_score, liq_rating = 10, "LOW"
                strengths.append(f"{safe_pct:.0f}% in treasury/cash — strong liquidity buffer")
            elif safe_pct > 10:
                liq_score, liq_rating = 30, "LOW"
            else:
                liq_score, liq_rating = 55, "MEDIUM"
                warnings.append(f"Only {safe_pct:.0f}% in safe/liquid assets — limited buffer for drawdowns")
            details.append({"factor": "Liquidity", "score": liq_score, "rating": liq_rating,
                            "detail": f"{safe_pct:.0f}% in treasury/cash equivalents"})

        fee_ratio = self.cost_s.get("fee_to_pnl_ratio_pct", 0)
        if fee_ratio > 30:
            fee_score, fee_rating = 70, "HIGH"
            warnings.append(f"Fees consume {fee_ratio:.0f}% of gross profit — consider reducing trade frequency")
        elif fee_ratio > 15:
            fee_score, fee_rating = 40, "MEDIUM"
        else:
            fee_score, fee_rating = max(0, int(fee_ratio * 2)), "LOW"
        details.append({"factor": "Fee Drag", "score": fee_score, "rating": fee_rating,
                        "detail": f"Fees = {fee_ratio:.1f}% of gross profit"})

        if not details:
            return {}

        overall = sum(d["score"] for d in details) / len(details)
        level = "Low Risk" if overall < 25 else "Moderate Risk" if overall < 50 else "Elevated Risk" if overall < 75 else "High Risk"
        return {"overall_score": int(overall), "overall_level": level,
                "details": details, "warnings": warnings, "strengths": strengths}

    # ---- HTML report ----

    def write_html(self) -> Path:
        out = self.output_dir / f"ibkr-analysis-{self.date_str}.html"
        charts_json = self._generate_charts_json()
        out.write_text(self._generate_standalone_html(charts_json), encoding="utf-8")
        return out

    def _generate_charts_json(self) -> dict[str, str]:
        charts: dict[str, str] = {}

        if self._on("pnl") and self.equity_curve:
            dates = [str(r["date"]) for r in self.equity_curve]
            values = [r["cumulative_pnl"] for r in self.equity_curve]
            fig = go.Figure(go.Scatter(x=dates, y=values, mode="lines", name="Cumulative P&L",
                                       fill="tozeroy", line=dict(color="#2196F3")))
            fig.update_layout(title="Equity Curve", xaxis_title="Date", yaxis_title="Cumulative P&L ($)",
                              template="plotly_white", height=400)
            charts["equity_curve"] = fig.to_json()

        if self._on("pnl"):
            monthly = self.pnl_s.get("monthly_pnl", {})
            if monthly:
                vals = list(monthly.values())
                fig = go.Figure(go.Bar(x=list(monthly.keys()), y=vals,
                                       marker_color=["#4CAF50" if v >= 0 else "#F44336" for v in vals]))
                fig.update_layout(title="Monthly P&L", xaxis_title="Month", yaxis_title="P&L ($)",
                                  template="plotly_white", height=400)
                charts["monthly_pnl"] = fig.to_json()

        if self._on("portfolio"):
            by_asset = self.port_s.get("by_asset", {})
            if by_asset:
                labels = list(by_asset.keys())
                values = [v.get("value", v.get("count", 0)) for v in by_asset.values()]
                fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.4))
                fig.update_layout(title="Asset Distribution", template="plotly_white", height=400)
                charts["asset_distribution"] = fig.to_json()

        if self._on("trade") and not self.trade_df.empty and "weekday" in self.trade_df.columns and "hour" in self.trade_df.columns:
            pivot = self.trade_df.groupby(["weekday", "hour"]).size().unstack(fill_value=0)
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            pivot = pivot.reindex([d for d in day_order if d in pivot.index])
            fig = go.Figure(go.Heatmap(z=pivot.values, x=[str(h) for h in pivot.columns],
                                        y=pivot.index, colorscale="YlOrRd", hoverongaps=False))
            fig.update_layout(title="Trade Frequency (Day x Hour)", xaxis_title="Hour",
                              yaxis_title="Day", template="plotly_white", height=400)
            charts["frequency_heatmap"] = fig.to_json()

        if self._on("portfolio"):
            holdings = self.port_s.get("top_holdings", [])
            if holdings:
                symbols = [h["symbol"] for h in holdings]
                upnl = [h.get("unrealized_pnl", 0) for h in holdings]
                fig = make_subplots(rows=1, cols=2, subplot_titles=("Portfolio Weight (%)", "Unrealized P&L ($)"))
                fig.add_trace(go.Bar(x=symbols, y=[h["pct"] for h in holdings], marker_color="#FF9800", name="Weight"), row=1, col=1)
                fig.add_trace(go.Bar(x=symbols, y=upnl, marker_color=["#4CAF50" if v >= 0 else "#F44336" for v in upnl], name="Unrealized P&L"), row=1, col=2)
                fig.update_layout(title="Top Holdings: Concentration & Unrealized P&L", template="plotly_white", height=400, showlegend=False)
                charts["concentration"] = fig.to_json()

        if self._on("cost"):
            comm_monthly = self.cost_s.get("commission_by_month", {})
            if comm_monthly:
                fig = go.Figure(go.Scatter(x=list(comm_monthly.keys()), y=list(comm_monthly.values()),
                                            mode="lines+markers", line=dict(color="#9C27B0")))
                fig.update_layout(title="Commission Trend", xaxis_title="Month",
                                  yaxis_title="Commission ($)", template="plotly_white", height=400)
                charts["commission_trend"] = fig.to_json()

        if self._on("price"):
            for pc in self.price_charts:
                sym = pc["symbol"]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=pc["dates"], y=pc["prices"], mode="lines",
                                         name=f"{sym} Price", line=dict(color="#607D8B")))
                if pc["buys"]:
                    fig.add_trace(go.Scatter(x=[b["date"] for b in pc["buys"]], y=[b["price"] for b in pc["buys"]],
                                             mode="markers", name="Buy",
                                             marker=dict(symbol="triangle-up", size=10, color="#4CAF50"),
                                             text=[f"Qty: {b['qty']}" for b in pc["buys"]]))
                if pc["sells"]:
                    fig.add_trace(go.Scatter(x=[s["date"] for s in pc["sells"]], y=[s["price"] for s in pc["sells"]],
                                             mode="markers", name="Sell",
                                             marker=dict(symbol="triangle-down", size=10, color="#F44336"),
                                             text=[f"Qty: {s['qty']}" for s in pc["sells"]]))
                fig.update_layout(title=f"{sym} Price & Trades", xaxis_title="Date", yaxis_title="Price ($)",
                                  template="plotly_white", height=400, showlegend=True)
                charts[f"price_{sym}"] = fig.to_json()

        # FX weighted avg rate vs current rate comparison
        if self._on("fx") and self.fx_s:
            ccys = list(self.fx_s.keys())
            avg_rates = [self.fx_s[c]["weighted_avg_rate"] for c in ccys]
            eff_rates = [self.fx_s[c]["effective_rate"] for c in ccys]
            curr_rates = [self.fx_s[c].get("current_rate") or self.fx_s[c]["weighted_avg_rate"] for c in ccys]
            # Display as FCY-per-USD (reciprocal)
            avg_fcy = [1 / r if r else 0.0 for r in avg_rates]
            eff_fcy = [1 / r if r else 0.0 for r in eff_rates]
            curr_fcy = [1 / r if r else 0.0 for r in curr_rates]
            labels = [f"1 USD = ? {c}" for c in ccys]

            fig = go.Figure()
            fig.add_trace(go.Bar(name="Weighted Avg Rate", x=labels, y=avg_fcy, marker_color="#2196F3"))
            fig.add_trace(go.Bar(name="Effective Rate (after commission)", x=labels, y=eff_fcy, marker_color="#FF9800"))
            fig.add_trace(go.Scatter(name="Current Market Rate", x=labels, y=curr_fcy,
                                     mode="markers", marker=dict(symbol="diamond", size=12, color="#F44336")))
            fig.update_layout(
                title="FX Conversion: Weighted Avg vs Effective vs Current Rate",
                yaxis_title="Foreign currency per 1 USD",
                barmode="group", template="plotly_white", height=400,
            )
            charts["fx_rates"] = fig.to_json()

            # MTM P&L bar chart (if any currency has current_rate)
            mtm_data = [(c, self.fx_s[c]["mtm_pnl"]) for c in ccys if self.fx_s[c].get("mtm_pnl") is not None]
            if mtm_data:
                mtm_ccys, mtm_vals = zip(*mtm_data)
                fig2 = go.Figure(go.Bar(
                    x=list(mtm_ccys), y=list(mtm_vals),
                    marker_color=["#4CAF50" if v >= 0 else "#F44336" for v in mtm_vals],
                    text=[f"${v:+,.2f}" for v in mtm_vals], textposition="outside",
                ))
                fig2.update_layout(
                    title="FX Mark-to-Market P&L (vs current rate)",
                    yaxis_title="USD", template="plotly_white", height=350,
                )
                charts["fx_mtm"] = fig2.to_json()

        return charts

    def _generate_standalone_html(self, charts: dict[str, str]) -> str:
        chart_divs = []
        for i, (name, fig_json) in enumerate(charts.items()):
            chart_divs.append(f'<div id="chart-{i}" style="width:100%;margin-bottom:30px;"></div>')
            chart_divs.append(
                f'<script>Plotly.newPlot("chart-{i}", '
                f'JSON.parse({json.dumps(fig_json)}).data, '
                f'JSON.parse({json.dumps(fig_json)}).layout, '
                f'{{responsive:true}});</script>'
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IBKR Trading Analysis - {self.date_str}</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 1200px; margin: 0 auto; padding: 20px; background: #fafafa; color: #333; }}
  h1 {{ color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }}
  h2 {{ color: #283593; margin-top: 40px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0; }}
  .metric-card {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .metric-value {{ font-size: 24px; font-weight: bold; color: #1a237e; }}
  .metric-label {{ font-size: 13px; color: #666; margin-top: 4px; }}
</style>
</head>
<body>
<h1>IBKR Trading Analysis</h1>
<p>Generated: {self.date_str}</p>
<div class="metrics">
  <div class="metric-card"><div class="metric-value">{self.trade_s.get('total_trades', 0):,}</div><div class="metric-label">Total Trades</div></div>
  <div class="metric-card"><div class="metric-value">{self.trade_s.get('win_rate', 0):.1f}%</div><div class="metric-label">Win Rate</div></div>
  <div class="metric-card"><div class="metric-value">${self.pnl_s.get('total_realized_pnl', 0):,.2f}</div><div class="metric-label">Total P&L</div></div>
  <div class="metric-card"><div class="metric-value">{self.pnl_s.get('sharpe_ratio', 0):.2f}</div><div class="metric-label">Sharpe Ratio</div></div>
  <div class="metric-card"><div class="metric-value">{self.pnl_s.get('max_drawdown_pct', 0):.1f}%</div><div class="metric-label">Max Drawdown</div></div>
  <div class="metric-card"><div class="metric-value">${self.cost_s.get('total_commissions', 0):,.2f}</div><div class="metric-label">Total Commissions</div></div>
</div>
<h2>Charts</h2>
{''.join(chart_divs)}
</body>
</html>"""
