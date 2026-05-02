"""FxAnalyzer — weighted average FX rate analysis for foreign currency ↔ USD conversions."""

from __future__ import annotations

from typing import Any

from models import Trade


class FxAnalyzer:
    """Weighted average FX rate analysis for all foreign currency ↔ USD conversions.

    IBKR FX trade conventions (asset_category == "CASH"):
      - symbol  : "USD.CNH"  → base=USD, quote=CNH
      - quantity : USD side  (positive = bought USD)
      - proceeds : CNH side  (negative = paid CNH, positive = received CNH)
      - trade_price: rate in quote-per-base at execution time

    Weighted average rate (foreign → base) is computed as:
        rate = Σ|base_amount_i| / Σ|foreign_amount_i|
    This is the volume-weighted true average, not a simple arithmetic mean.
    """

    def __init__(
        self,
        trades: list[Trade],
        base_currency: str = "USD",
        conversion_rates: dict[str, float] | None = None,
    ):
        self.fx_trades = [t for t in trades if t.asset_category == "CASH"]
        self.base_currency = base_currency
        self.conversion_rates = conversion_rates or {}

    def summary(self) -> dict[str, Any]:
        """Returns per-foreign-currency FX stats keyed by currency code."""
        by_ccy: dict[str, list[dict]] = {}

        for t in self.fx_trades:
            parts = t.symbol.split(".")
            if len(parts) != 2:
                continue
            sym_base, sym_quote = parts[0], parts[1]

            if sym_base == self.base_currency:
                # e.g. USD.CNH: quantity=USD, proceeds=CNH (negative when paying)
                foreign_ccy = sym_quote
                base_amount = abs(t.quantity)
                foreign_amount = abs(t.proceeds)
            elif sym_quote == self.base_currency:
                # e.g. EUR.USD: quantity=EUR, proceeds=USD
                foreign_ccy = sym_base
                base_amount = abs(t.proceeds)
                foreign_amount = abs(t.quantity)
            else:
                continue  # cross pair not involving base currency

            if foreign_amount < 1e-9:
                continue

            by_ccy.setdefault(foreign_ccy, []).append({
                "date": t.date_time,
                "base_amount": base_amount,
                "foreign_amount": foreign_amount,
                # rate: 1 unit of foreign currency = N units of base currency (USD/FCY)
                "rate": base_amount / foreign_amount,
                "commission": abs(t.commission),
                "buy_sell": t.buy_sell,
                "symbol": t.symbol,
            })

        result: dict[str, Any] = {}
        for ccy, entries in sorted(by_ccy.items()):
            total_base = sum(e["base_amount"] for e in entries)
            total_foreign = sum(e["foreign_amount"] for e in entries)
            total_commission = sum(e["commission"] for e in entries)

            # Volume-weighted average: true cost basis (USD per 1 FCY)
            weighted_avg = total_base / total_foreign if total_foreign > 0 else 0.0
            # Effective rate after deducting commission from base received
            effective_rate = (total_base - total_commission) / total_foreign if total_foreign > 0 else 0.0

            rates = [e["rate"] for e in entries]
            dates = [e["date"] for e in entries if e["date"]]

            # Current market rate from ConversionRate XML section
            # conversion_rates stores {foreign_ccy: rate_to_base}, e.g. {"CNH": 0.137}
            current_rate = self.conversion_rates.get(ccy)

            entry: dict[str, Any] = {
                "currency": ccy,
                "n_trades": len(entries),
                "total_base_exchanged": total_base,
                "total_foreign_exchanged": total_foreign,
                "weighted_avg_rate": weighted_avg,       # USD per 1 FCY (internal math)
                "effective_rate": effective_rate,         # USD per 1 FCY after commission
                "best_rate": max(rates),                  # best USD per 1 FCY
                "worst_rate": min(rates),                 # worst USD per 1 FCY
                "rate_spread_pct": (max(rates) - min(rates)) / weighted_avg * 100 if weighted_avg > 0 else 0.0,
                "total_commission": total_commission,
                "commission_pct": total_commission / total_base * 100 if total_base > 0 else 0.0,
                "first_date": min(dates).strftime("%Y-%m-%d") if dates else "",
                "last_date": max(dates).strftime("%Y-%m-%d") if dates else "",
                "current_rate": current_rate,            # USD per 1 FCY (market)
            }

            # Mark-to-market: if converted at today's rate instead of weighted avg,
            # how much more/less base currency would you have received?
            if current_rate and weighted_avg > 0:
                mtm_base = total_foreign * current_rate
                entry["mtm_base"] = mtm_base
                entry["mtm_pnl"] = mtm_base - total_base
                entry["mtm_pnl_pct"] = (mtm_base - total_base) / total_base * 100 if total_base > 0 else 0.0

            result[ccy] = entry

        return result
