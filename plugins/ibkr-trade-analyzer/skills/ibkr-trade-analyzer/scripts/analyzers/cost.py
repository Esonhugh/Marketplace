"""CostAnalyzer — fee and cash flow analysis."""

from __future__ import annotations

from typing import Any

from models import CashTransaction, Trade


class CostAnalyzer:
    """Fee and cash flow analysis."""

    def __init__(self, trades: list[Trade], cash_txns: list[CashTransaction]):
        self.trades = trades
        self.cash_txns = cash_txns

    def summary(self) -> dict[str, Any]:
        total_comm = sum(abs(t.commission) for t in self.trades)
        num_trades = len(self.trades) or 1
        gross_profit = sum(t.realized_pnl for t in self.trades if t.realized_pnl > 0) or 1

        dividends = sum(ct.amount for ct in self.cash_txns if "dividend" in ct.type.lower())
        interest = sum(ct.amount for ct in self.cash_txns if "interest" in ct.type.lower())
        fees = sum(abs(ct.amount) for ct in self.cash_txns if "fee" in ct.type.lower())
        withholding = sum(abs(ct.amount) for ct in self.cash_txns if "withholding" in ct.type.lower())

        comm_by_month: dict[str, float] = {}
        for t in self.trades:
            if t.date_time:
                key = t.date_time.strftime("%Y-%m")
                comm_by_month[key] = comm_by_month.get(key, 0) + abs(t.commission)

        return {
            "total_commissions": total_comm,
            "avg_commission_per_trade": total_comm / num_trades,
            "fee_to_pnl_ratio_pct": total_comm / gross_profit * 100 if gross_profit > 0 else 0,
            "dividend_income": dividends,
            "withholding_tax": withholding,
            "net_dividend": dividends - withholding,
            "interest_net": interest,
            "other_fees": fees,
            "commission_by_month": dict(sorted(comm_by_month.items())),
        }
