"""PnLAnalyzer — P&L performance metrics."""

from __future__ import annotations

from typing import Any

import pandas as pd

from models import Trade


class PnLAnalyzer:
    """P&L performance metrics."""

    def __init__(self, trades: list[Trade]):
        self.trades = trades
        self.df = self._to_dataframe()

    def _to_dataframe(self) -> pd.DataFrame:
        records = [
            {
                "date_time": t.date_time,
                "symbol": t.symbol,
                "asset_category": t.asset_category,
                "realized_pnl": t.realized_pnl,
                "commission": t.commission,
            }
            for t in self.trades if t.date_time and t.realized_pnl != 0
        ]
        df = pd.DataFrame(records)
        if not df.empty:
            df["date_time"] = pd.to_datetime(df["date_time"])
            df = df.sort_values("date_time").reset_index(drop=True)
            df["cumulative_pnl"] = df["realized_pnl"].cumsum()
            df["date"] = df["date_time"].dt.date
            df["month"] = df["date_time"].dt.to_period("M")
        return df

    def summary(self) -> dict[str, Any]:
        if self.df.empty:
            return {"total_realized_pnl": 0}
        total_pnl = self.df["realized_pnl"].sum()
        monthly = self.df.groupby("month")["realized_pnl"].sum()

        by_symbol = self.df.groupby("symbol")["realized_pnl"].sum()
        top_winners = [{"symbol": s, "pnl": v} for s, v in
                       by_symbol[by_symbol > 0].sort_values(ascending=False).head(10).items()]
        top_losers = [{"symbol": s, "pnl": v} for s, v in
                      by_symbol[by_symbol < 0].sort_values(ascending=True).head(10).items()]

        # Max drawdown
        cum = self.df["cumulative_pnl"]
        peak = cum.cummax()
        drawdown = cum - peak
        max_dd = (drawdown.min() / peak.max()) * 100 if peak.max() != 0 else 0

        # Sharpe (annualised from monthly returns)
        sharpe = 0.0
        if not monthly.empty and monthly.std() != 0:
            sharpe = (monthly.mean() / monthly.std()) * (12 ** 0.5)

        return {
            "total_realized_pnl": total_pnl,
            "max_drawdown_pct": max_dd,
            "sharpe_ratio": sharpe,
            "best_month": {"period": str(monthly.idxmax()), "pnl": monthly.max()} if not monthly.empty else None,
            "worst_month": {"period": str(monthly.idxmin()), "pnl": monthly.min()} if not monthly.empty else None,
            "monthly_pnl": {str(k): v for k, v in monthly.items()},
            "by_asset": self.df.groupby("asset_category")["realized_pnl"].sum().to_dict(),
            "top_winners": top_winners,
            "top_losers": top_losers,
        }

    def equity_curve_data(self) -> list[dict]:
        if self.df.empty:
            return []
        daily = self.df.groupby("date")["realized_pnl"].sum().cumsum().reset_index()
        daily.columns = ["date", "cumulative_pnl"]
        return daily.to_dict("records")
