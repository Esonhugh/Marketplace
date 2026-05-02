"""PriceAnalyzer — historical price data via yfinance (read-only)."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from models import Trade


class PriceAnalyzer:
    """Fetch historical price data for traded symbols via yfinance (read-only)."""

    def __init__(self, trades: list[Trade], top_n: int = 10):
        self.trades = trades
        self.top_n = top_n

    def get_top_symbols(self) -> list[str]:
        counts: dict[str, int] = {}
        for t in self.trades:
            if t.asset_category == "STK" and t.symbol:
                counts[t.symbol] = counts.get(t.symbol, 0) + 1
        return [s for s, _ in sorted(counts.items(), key=lambda x: x[1], reverse=True)[: self.top_n]]

    def fetch_prices(self, symbols: list[str] | None = None, period: str = "1y") -> dict[str, pd.DataFrame]:
        if symbols is None:
            symbols = self.get_top_symbols()
        result = {}
        for sym in symbols:
            try:
                hist = yf.Ticker(sym).history(period=period)
                if not hist.empty:
                    result[sym] = hist[["Close", "Volume"]].reset_index()
            except Exception:
                continue
        return result

    def price_vs_trades_data(self, symbol: str, price_df: pd.DataFrame) -> dict:
        sym_trades = [t for t in self.trades if t.symbol == symbol and t.date_time]
        return {
            "symbol": symbol,
            "dates": [str(d.date()) if hasattr(d, "date") else str(d) for d in price_df["Date"]],
            "prices": price_df["Close"].tolist(),
            "buys": [{"date": str(t.date_time.date()), "price": t.trade_price, "qty": t.quantity}
                     for t in sym_trades if t.buy_sell in ("BUY", "BOT")],
            "sells": [{"date": str(t.date_time.date()), "price": t.trade_price, "qty": abs(t.quantity)}
                      for t in sym_trades if t.buy_sell in ("SELL", "SLD")],
        }
