"""PortfolioAnalyzer — position structure and cash analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models import CashTransaction, OpenPosition, Trade


class PortfolioAnalyzer:
    """Position structure and cash analysis."""

    def __init__(self, positions: list[OpenPosition], trades: list[Trade],
                 cash_balances: list | None = None,
                 conversion_rates: dict[str, float] | None = None,
                 base_currency: str = "USD"):
        self.positions = positions
        self.trades = trades
        self.cash_balances = cash_balances or []
        self.conversion_rates = conversion_rates or {}
        self.base_currency = base_currency

    def summary(self) -> dict[str, Any]:
        if not self.positions:
            return self._from_trades()

        total_value = sum(abs(p.position_value) for p in self.positions) or 1
        by_asset: dict[str, float] = {}
        by_symbol: dict[str, float] = {}
        long_value = short_value = 0.0

        for p in self.positions:
            cat = p.asset_category or "Other"
            by_asset[cat] = by_asset.get(cat, 0) + abs(p.position_value)
            by_symbol[p.symbol] = by_symbol.get(p.symbol, 0) + abs(p.position_value)
            if p.quantity > 0:
                long_value += abs(p.position_value)
            else:
                short_value += abs(p.position_value)

        sorted_symbols = sorted(by_symbol.items(), key=lambda x: x[1], reverse=True)
        top5_pct = sum(v for _, v in sorted_symbols[:5]) / total_value * 100
        top10_pct = sum(v for _, v in sorted_symbols[:10]) / total_value * 100

        result: dict[str, Any] = {
            "total_positions": len(self.positions),
            "total_value": total_value,
            "unrealized_pnl": sum(p.unrealized_pnl for p in self.positions),
            "by_asset": {k: {"value": v, "pct": v / total_value * 100} for k, v in by_asset.items()},
            "long_short_ratio": long_value / short_value if short_value > 0 else float("inf"),
            "long_pct": long_value / total_value * 100,
            "short_pct": short_value / total_value * 100,
            "top5_concentration_pct": top5_pct,
            "top10_concentration_pct": top10_pct,
            "top_holdings": [
                {
                    "symbol": s,
                    "value": v,
                    "pct": v / total_value * 100,
                    "quantity": next((p.quantity for p in self.positions if p.symbol == s), 0),
                    "cost_basis": next((p.cost_basis_price for p in self.positions if p.symbol == s), 0),
                    "unrealized_pnl": next((p.unrealized_pnl for p in self.positions if p.symbol == s), 0),
                }
                for s, v in sorted_symbols[:10]
            ],
            "currencies": {k: v / total_value * 100 for k, v in
                          {p.currency: {p.currency: 0 for _ in self.positions}
                           .get(p.currency, 0) for p in self.positions}.items()},
        }

        # Build currency breakdown properly
        ccy: dict[str, float] = {}
        for p in self.positions:
            ccy[p.currency] = ccy.get(p.currency, 0) + abs(p.position_value)
        result["currencies"] = {k: v / total_value * 100 for k, v in ccy.items()}

        cash_analysis = self._cash_analysis(total_value)
        if cash_analysis:
            result["cash"] = cash_analysis
        return result

    def _from_trades(self) -> dict[str, Any]:
        if not self.trades:
            return {"total_positions": 0}
        by_asset: dict[str, int] = {}
        for t in self.trades:
            cat = t.asset_category or "Other"
            by_asset[cat] = by_asset.get(cat, 0) + 1
        total = sum(by_asset.values())
        return {
            "total_positions": 0,
            "note": "No open position data; showing trade distribution by asset type",
            "by_asset": {k: {"count": v, "pct": v / total * 100} for k, v in by_asset.items()},
        }

    def _cash_analysis(self, position_value: float) -> dict[str, Any]:
        if not self.cash_balances:
            return {}
        balances = []
        total_cash_base = 0.0

        for cb in self.cash_balances:
            if abs(cb.ending_cash) < 0.01:
                continue
            if cb.currency == self.base_currency:
                base_value = cb.ending_cash
            elif cb.currency in self.conversion_rates:
                base_value = cb.ending_cash * self.conversion_rates[cb.currency]
            else:
                base_value = self._estimate_fx_value(cb.currency, cb.ending_cash)
            total_cash_base += base_value
            balances.append({
                "currency": cb.currency,
                "amount": cb.ending_cash,
                "base_value": base_value,
                "rate": base_value / cb.ending_cash if cb.ending_cash != 0 else 0,
            })

        total_account = position_value + total_cash_base
        safe_etfs = {"SGOV", "SHV", "BIL", "SCHO", "VGSH"}
        quasi_cash = sum(abs(p.position_value) for p in self.positions if p.symbol in safe_etfs)

        return {
            "balances": sorted(balances, key=lambda x: x["base_value"], reverse=True),
            "total_cash_base": total_cash_base,
            "total_account_value": total_account,
            "cash_pct": total_cash_base / total_account * 100 if total_account > 0 else 0,
            "quasi_cash": quasi_cash,
            "quasi_cash_pct": quasi_cash / total_account * 100 if total_account > 0 else 0,
            "total_liquid": total_cash_base + quasi_cash,
            "total_liquid_pct": (total_cash_base + quasi_cash) / total_account * 100 if total_account > 0 else 0,
            "equity_value": position_value - quasi_cash,
            "equity_pct": (position_value - quasi_cash) / total_account * 100 if total_account > 0 else 0,
            "fx_analysis": self._fx_analysis(),
        }

    def _fx_analysis(self) -> list[dict]:
        fx_trades = [t for t in self.trades if t.asset_category == "CASH"]
        if not fx_trades:
            return []
        by_pair: dict[str, list] = {}
        for t in fx_trades:
            by_pair.setdefault(t.symbol, []).append(t)

        result = []
        for pair, trades in sorted(by_pair.items()):
            total_qty = sum(abs(t.quantity) for t in trades)
            total_proceeds = sum(abs(t.proceeds) for t in trades)
            total_commission = sum(abs(t.commission) for t in trades)
            avg_rate = total_proceeds / total_qty if total_qty > 0 else 0
            rates = [abs(t.proceeds / t.quantity) for t in trades if t.quantity != 0 and t.proceeds / t.quantity > 0]
            dates = [t.date_time for t in trades if t.date_time]

            parts = pair.split(".")
            current_rate = None
            if len(parts) == 2:
                quote_ccy = parts[1]
                if quote_ccy in self.conversion_rates and self.conversion_rates[quote_ccy] > 0:
                    current_rate = 1.0 / self.conversion_rates[quote_ccy]

            entry: dict[str, Any] = {
                "pair": pair,
                "n_trades": len(trades),
                "total_base_amount": total_qty,
                "total_quote_amount": total_proceeds,
                "total_commission": total_commission,
                "avg_rate": avg_rate,
                "min_rate": min(rates) if rates else 0,
                "max_rate": max(rates) if rates else 0,
                "current_rate": current_rate,
                "first_date": min(dates).strftime("%Y-%m-%d") if dates else "",
                "last_date": max(dates).strftime("%Y-%m-%d") if dates else "",
            }
            if current_rate and avg_rate > 0:
                rate_change_pct = (current_rate - avg_rate) / avg_rate * 100
                entry["rate_change_pct"] = rate_change_pct
                entry["fx_impact_note"] = f"Rate moved {rate_change_pct:+.2f}% since your avg conversion"
            result.append(entry)
        return result

    def _estimate_fx_value(self, currency: str, amount: float) -> float:
        fx_trades = [t for t in self.trades if t.asset_category == "CASH" and currency in t.symbol]
        if fx_trades:
            last = sorted(fx_trades, key=lambda t: t.date_time or datetime.min)[-1]
            if last.quantity != 0:
                rate = abs(last.proceeds / last.quantity)
                return amount / rate if rate > 0 else 0
        return 0
