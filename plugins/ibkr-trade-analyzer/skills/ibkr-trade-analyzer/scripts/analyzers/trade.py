"""TradeAnalyzer — trading behavior pattern analysis."""

from __future__ import annotations

from typing import Any

import pandas as pd

from models import Trade


class TradeAnalyzer:
    """Trading behavior pattern analysis."""

    def __init__(self, trades: list[Trade]):
        self.trades = trades
        self.df = self._to_dataframe()

    def _to_dataframe(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame()
        records = [{
            "symbol": t.symbol,
            "asset_category": t.asset_category,
            "date_time": t.date_time,
            "quantity": t.quantity,
            "price": t.trade_price,
            "proceeds": t.proceeds,
            "commission": t.commission,
            "realized_pnl": t.realized_pnl,
            "buy_sell": t.buy_sell,
            "open_close": t.open_close,
            "multiplier": t.multiplier,
            "notional": abs(t.quantity * t.trade_price * t.multiplier),
        } for t in self.trades]
        df = pd.DataFrame(records)
        if not df.empty and "date_time" in df.columns:
            df["date_time"] = pd.to_datetime(df["date_time"])
            df = df.sort_values("date_time").reset_index(drop=True)
            df["date"] = df["date_time"].dt.date
            df["hour"] = df["date_time"].dt.hour
            df["weekday"] = df["date_time"].dt.day_name()
            df["month"] = df["date_time"].dt.to_period("M")
        return df

    def summary(self) -> dict[str, Any]:
        if self.df.empty:
            return {"total_trades": 0}
        closing = self.df[self.df["realized_pnl"] != 0]
        winners = closing[closing["realized_pnl"] > 0]
        losers = closing[closing["realized_pnl"] < 0]
        gross_profit = winners["realized_pnl"].sum() if not winners.empty else 0
        gross_loss = abs(losers["realized_pnl"].sum()) if not losers.empty else 0
        n_days = (self.df["date_time"].max() - self.df["date_time"].min()).days or 1

        by_asset: dict = {}
        for cat, grp in self.df.groupby("asset_category"):
            cl = grp[grp["realized_pnl"] != 0]
            by_asset[cat] = {
                "count": len(grp),
                "win_rate": len(cl[cl["realized_pnl"] > 0]) / len(cl) * 100 if len(cl) > 0 else 0,
                "total_pnl": grp["realized_pnl"].sum(),
            }

        return {
            "total_trades": len(self.df),
            "total_closing_trades": len(closing),
            "win_rate": len(winners) / len(closing) * 100 if len(closing) > 0 else 0,
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
            "avg_trade_size": self.df["notional"].mean(),
            "median_trade_size": self.df["notional"].median(),
            "trades_per_day": len(self.df) / n_days,
            "by_asset": by_asset,
            "by_weekday": self.df.groupby("weekday").size().to_dict() if "weekday" in self.df.columns else {},
            "by_hour": self.df.groupby("hour").size().to_dict() if "hour" in self.df.columns else {},
        }
