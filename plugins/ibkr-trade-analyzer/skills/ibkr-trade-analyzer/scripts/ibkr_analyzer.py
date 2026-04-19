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
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import jinja2
import requests
import yfinance as yf


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    trade_id: str = ""
    account_id: str = ""
    symbol: str = ""
    asset_category: str = ""  # STK, OPT, FUT, CASH
    currency: str = "USD"
    description: str = ""
    date_time: datetime | None = None
    quantity: float = 0.0
    trade_price: float = 0.0
    proceeds: float = 0.0
    commission: float = 0.0
    realized_pnl: float = 0.0
    cost_basis: float = 0.0
    buy_sell: str = ""  # BUY / SELL
    open_close: str = ""  # O / C
    exchange: str = ""
    order_type: str = ""
    multiplier: float = 1.0


@dataclass
class CashTransaction:
    date_time: datetime | None = None
    type: str = ""  # Dividends, Interest, Fees, etc.
    symbol: str = ""
    currency: str = "USD"
    amount: float = 0.0
    description: str = ""


@dataclass
class OpenPosition:
    symbol: str = ""
    asset_category: str = ""
    currency: str = "USD"
    quantity: float = 0.0
    cost_basis_price: float = 0.0
    mark_price: float = 0.0
    unrealized_pnl: float = 0.0
    position_value: float = 0.0


@dataclass
class AccountData:
    trades: list[Trade] = field(default_factory=list)
    cash_transactions: list[CashTransaction] = field(default_factory=list)
    open_positions: list[OpenPosition] = field(default_factory=list)
    account_id: str = ""
    base_currency: str = "USD"


# ---------------------------------------------------------------------------
# DataLoader
# ---------------------------------------------------------------------------

class DataLoader:
    """Load IBKR data from Flex Web Service or local files."""

    FLEX_SEND_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest"
    FLEX_GET_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement"

    @staticmethod
    def _get_session(proxy: str | None = None) -> requests.Session:
        """Create a requests session with optional proxy."""
        session = requests.Session()
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        return session

    @staticmethod
    def from_flex(token: str, query_id: str, proxy: str | None = None, dump_xml: str | None = None) -> AccountData:
        """Fetch data via Flex Web Service (read-only API)."""
        session = DataLoader._get_session(proxy)

        # Step 1: request report generation
        resp = session.get(
            DataLoader.FLEX_SEND_URL,
            params={"t": token, "q": query_id, "v": "3"},
            timeout=30,
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        status = root.findtext("Status")
        if status != "Success":
            err_msg = root.findtext("ErrorMessage", "Unknown error")
            raise RuntimeError(f"Flex SendRequest failed: {err_msg}")

        ref_code = root.findtext("ReferenceCode")
        if not ref_code:
            raise RuntimeError("No ReferenceCode in Flex response")

        # Step 2: poll for report (may take a few seconds)
        for attempt in range(6):
            time.sleep(5 if attempt > 0 else 1)
            resp2 = session.get(
                DataLoader.FLEX_GET_URL,
                params={"t": token, "q": ref_code, "v": "3"},
                timeout=60,
            )
            resp2.raise_for_status()
            if resp2.text.strip().startswith("<"):
                # Check if it's a "still generating" response
                try:
                    check = ET.fromstring(resp2.text)
                    if check.findtext("ErrorCode") == "1019":
                        continue  # not ready yet
                except ET.ParseError:
                    pass
                return DataLoader._parse_flex_xml(resp2.text, dump_path=dump_xml)

        raise RuntimeError("Flex report not ready after multiple attempts. Try again in a few minutes.")

    @staticmethod
    def from_file(path: str, fmt: str | None = None) -> AccountData:
        """Load from local CSV or XML file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if fmt is None:
            fmt = "xml" if p.suffix.lower() in (".xml",) else "csv"

        if fmt == "xml":
            return DataLoader._parse_flex_xml(p.read_text(encoding="utf-8"))
        else:
            return DataLoader._parse_csv(p.read_text(encoding="utf-8"))

    # ---- XML parsing ----

    @staticmethod
    def _parse_flex_xml(xml_text: str, dump_path: str | None = None) -> AccountData:
        if dump_path:
            Path(dump_path).write_text(xml_text, encoding="utf-8")
            print(f"  Raw XML dumped to: {dump_path}")
        root = ET.fromstring(xml_text)
        data = AccountData()

        # Account info
        acct_info = root.find(".//AccountInformation")
        if acct_info is not None:
            data.account_id = acct_info.get("accountId", "")
            data.base_currency = acct_info.get("currency", "USD")

        # Trades
        for node in root.iter("Trade"):
            fifo_pnl = DataLoader._float(node.get("fifoPnlRealized", node.get("realizedPnl", "0")))
            buy_sell = node.get("buySell", "")

            t = Trade(
                trade_id=node.get("tradeID", ""),
                account_id=node.get("accountId", ""),
                symbol=node.get("symbol", ""),
                asset_category=node.get("assetCategory", ""),
                currency=node.get("currency", "USD"),
                description=node.get("description", ""),
                date_time=DataLoader._parse_dt(node.get("dateTime", "")),
                quantity=DataLoader._float(node.get("quantity", "0")),
                trade_price=DataLoader._float(node.get("tradePrice", "0")),
                proceeds=DataLoader._float(node.get("proceeds", "0")),
                commission=DataLoader._float(node.get("ibCommission", node.get("commission", "0"))),
                realized_pnl=fifo_pnl,
                cost_basis=DataLoader._float(node.get("cost", "0")),
                buy_sell=buy_sell,
                open_close=node.get("openCloseIndicator", ""),
                exchange=node.get("exchange", ""),
                order_type=node.get("orderType", ""),
                multiplier=DataLoader._float(node.get("multiplier", "1")),
            )
            data.trades.append(t)

        # If fifoPnlRealized is all zeros, compute realized PnL via FIFO matching
        has_fifo = any(t.realized_pnl != 0 for t in data.trades)
        if not has_fifo and data.trades:
            DataLoader._compute_fifo_pnl(data.trades)

        # Cash transactions
        for node in root.iter("CashTransaction"):
            ct = CashTransaction(
                date_time=DataLoader._parse_dt(node.get("dateTime", node.get("reportDate", ""))),
                type=node.get("type", ""),
                symbol=node.get("symbol", ""),
                currency=node.get("currency", "USD"),
                amount=DataLoader._float(node.get("amount", "0")),
                description=node.get("description", ""),
            )
            data.cash_transactions.append(ct)

        # Open positions
        for node in root.iter("OpenPosition"):
            op = OpenPosition(
                symbol=node.get("symbol", ""),
                asset_category=node.get("assetCategory", ""),
                currency=node.get("currency", "USD"),
                quantity=DataLoader._float(node.get("position", node.get("quantity", "0"))),
                cost_basis_price=DataLoader._float(node.get("costBasisPrice", "0")),
                mark_price=DataLoader._float(node.get("markPrice", "0")),
                unrealized_pnl=DataLoader._float(node.get("fifoPnlUnrealized", node.get("unrealizedPnl", "0"))),
                position_value=DataLoader._float(node.get("positionValue", "0")),
            )
            data.open_positions.append(op)

        # If unrealized PnL and cost basis are all zeros, compute from FIFO remaining lots
        has_unrealized = any(p.unrealized_pnl != 0 or p.cost_basis_price != 0 for p in data.open_positions)
        if not has_unrealized and data.open_positions and data.trades:
            DataLoader._compute_unrealized_pnl(data.trades, data.open_positions)

        return data

    # ---- CSV parsing ----

    @staticmethod
    def _parse_csv(csv_text: str) -> AccountData:
        """Parse IBKR Activity Statement CSV (section-based format)."""
        data = AccountData()
        current_section = ""
        headers: list[str] = []

        for line in csv_text.splitlines():
            parts = line.split(",")
            if len(parts) < 2:
                continue

            section_marker = parts[0].strip('"')
            row_type = parts[1].strip('"') if len(parts) > 1 else ""

            # Section detection
            if row_type == "Header":
                current_section = section_marker
                headers = [p.strip('"') for p in parts[2:]]
                continue

            if row_type != "Data":
                continue

            values = [p.strip('"') for p in parts[2:]]
            row = dict(zip(headers, values)) if len(values) == len(headers) else {}

            if current_section == "Trades":
                t = Trade(
                    symbol=row.get("Symbol", ""),
                    asset_category=row.get("Asset Category", ""),
                    currency=row.get("Currency", "USD"),
                    description=row.get("Description", ""),
                    date_time=DataLoader._parse_dt(row.get("Date/Time", row.get("TradeDate", ""))),
                    quantity=DataLoader._float(row.get("Quantity", "0")),
                    trade_price=DataLoader._float(row.get("T. Price", row.get("TradePrice", "0"))),
                    proceeds=DataLoader._float(row.get("Proceeds", "0")),
                    commission=DataLoader._float(row.get("Comm/Fee", row.get("IBCommission", "0"))),
                    realized_pnl=DataLoader._float(row.get("Realized P/L", row.get("FifoPnlRealized", "0"))),
                    cost_basis=DataLoader._float(row.get("Basis", row.get("Cost", "0"))),
                    buy_sell=row.get("Buy/Sell", ""),
                )
                data.trades.append(t)

            elif current_section in ("Dividends", "Interest", "Fees"):
                ct = CashTransaction(
                    date_time=DataLoader._parse_dt(row.get("Date/Time", row.get("Date", ""))),
                    type=current_section,
                    symbol=row.get("Symbol", row.get("Description", "")),
                    currency=row.get("Currency", "USD"),
                    amount=DataLoader._float(row.get("Amount", "0")),
                    description=row.get("Description", ""),
                )
                data.cash_transactions.append(ct)

            elif current_section == "Open Positions":
                op = OpenPosition(
                    symbol=row.get("Symbol", ""),
                    asset_category=row.get("Asset Category", ""),
                    currency=row.get("Currency", "USD"),
                    quantity=DataLoader._float(row.get("Quantity", "0")),
                    cost_basis_price=DataLoader._float(row.get("Cost Basis", "0")),
                    mark_price=DataLoader._float(row.get("Mark Price", row.get("Close Price", "0"))),
                    unrealized_pnl=DataLoader._float(row.get("Unrealized P/L", "0")),
                    position_value=DataLoader._float(row.get("Value", "0")),
                )
                data.open_positions.append(op)

            elif current_section == "Account Information":
                data.account_id = row.get("Value", "") if row.get("Field Name", "") == "Account" else data.account_id
                if row.get("Field Name", "") == "Base Currency":
                    data.base_currency = row.get("Value", "USD")

        return data

    # ---- helpers ----

    @staticmethod
    def _parse_dt(s: str) -> datetime | None:
        if not s:
            return None
        for fmt in ("%Y%m%d;%H%M%S", "%Y%m%d", "%Y-%m-%d, %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s.strip(), fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _float(s: str) -> float:
        try:
            return float(s.replace(",", ""))
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _compute_fifo_pnl(trades: list[Trade]) -> None:
        """Compute realized PnL using FIFO lot matching when fifoPnlRealized is unavailable.

        Groups trades by symbol, sorts by time, and matches sells against earliest buys.
        Mutates trade.realized_pnl in place for closing (sell) trades.
        """
        from collections import defaultdict, deque

        # Group by symbol, sorted by time
        by_symbol: dict[str, list[Trade]] = defaultdict(list)
        for t in trades:
            by_symbol[t.symbol].append(t)

        for sym, sym_trades in by_symbol.items():
            sym_trades.sort(key=lambda t: t.date_time or datetime.min)
            # FIFO queue of open lots: (qty_remaining, cost_per_unit)
            lots: deque[list] = deque()

            for t in sym_trades:
                qty = abs(t.quantity)
                if t.buy_sell in ("BUY", "BOT"):
                    lots.append([qty, t.trade_price])
                elif t.buy_sell in ("SELL", "SLD") and lots:
                    realized = 0.0
                    remaining = qty
                    while remaining > 0 and lots:
                        lot = lots[0]
                        matched = min(remaining, lot[0])
                        realized += matched * (t.trade_price - lot[1]) * t.multiplier
                        lot[0] -= matched
                        remaining -= matched
                        if lot[0] <= 1e-9:
                            lots.popleft()
                    # Subtract commissions from both buy and sell side
                    t.realized_pnl = realized + t.commission  # commission is negative

    @staticmethod
    def _compute_unrealized_pnl(trades: list[Trade], positions: list[OpenPosition]) -> None:
        """Compute unrealized PnL and cost basis from FIFO remaining lots."""
        from collections import defaultdict, deque

        by_symbol: dict[str, list[Trade]] = defaultdict(list)
        for t in trades:
            by_symbol[t.symbol].append(t)

        for pos in positions:
            sym_trades = sorted(by_symbol.get(pos.symbol, []), key=lambda t: t.date_time or datetime.min)
            lots: deque[list] = deque()  # [qty_remaining, cost_per_unit]

            for t in sym_trades:
                qty = abs(t.quantity)
                if t.buy_sell in ("BUY", "BOT"):
                    lots.append([qty, t.trade_price])
                elif t.buy_sell in ("SELL", "SLD"):
                    remaining = qty
                    while remaining > 0 and lots:
                        lot = lots[0]
                        matched = min(remaining, lot[0])
                        lot[0] -= matched
                        remaining -= matched
                        if lot[0] <= 1e-9:
                            lots.popleft()

            # Remaining lots = open position cost basis
            if lots:
                total_qty = sum(l[0] for l in lots)
                total_cost = sum(l[0] * l[1] for l in lots)
                if total_qty > 0:
                    pos.cost_basis_price = total_cost / total_qty
                    pos.unrealized_pnl = (pos.mark_price - pos.cost_basis_price) * pos.quantity


# ---------------------------------------------------------------------------
# TradeAnalyzer
# ---------------------------------------------------------------------------

class TradeAnalyzer:
    """Trading behavior pattern analysis."""

    def __init__(self, trades: list[Trade]):
        self.trades = trades
        self.df = self._to_dataframe()

    def _to_dataframe(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame()
        records = []
        for t in self.trades:
            records.append({
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
            })
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

        return {
            "total_trades": len(self.df),
            "total_closing_trades": len(closing),
            "win_rate": len(winners) / len(closing) * 100 if len(closing) > 0 else 0,
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
            "avg_trade_size": self.df["notional"].mean(),
            "median_trade_size": self.df["notional"].median(),
            "trades_per_day": self._trades_per_day(),
            "by_asset": self._by_asset(),
            "by_weekday": self._by_weekday(),
            "by_hour": self._by_hour(),
        }

    def _trades_per_day(self) -> float:
        if self.df.empty:
            return 0
        n_days = (self.df["date_time"].max() - self.df["date_time"].min()).days or 1
        return len(self.df) / n_days

    def _by_asset(self) -> dict:
        if self.df.empty:
            return {}
        result = {}
        for cat, grp in self.df.groupby("asset_category"):
            closing = grp[grp["realized_pnl"] != 0]
            winners = closing[closing["realized_pnl"] > 0]
            result[cat] = {
                "count": len(grp),
                "win_rate": len(winners) / len(closing) * 100 if len(closing) > 0 else 0,
                "total_pnl": grp["realized_pnl"].sum(),
            }
        return result

    def _by_weekday(self) -> dict:
        if self.df.empty or "weekday" not in self.df.columns:
            return {}
        return self.df.groupby("weekday").size().to_dict()

    def _by_hour(self) -> dict:
        if self.df.empty or "hour" not in self.df.columns:
            return {}
        return self.df.groupby("hour").size().to_dict()


# ---------------------------------------------------------------------------
# PnLAnalyzer
# ---------------------------------------------------------------------------

class PnLAnalyzer:
    """P&L performance metrics."""

    def __init__(self, trades: list[Trade]):
        self.trades = trades
        self.df = self._to_dataframe()

    def _to_dataframe(self) -> pd.DataFrame:
        records = []
        for t in self.trades:
            if t.date_time and t.realized_pnl != 0:
                records.append({
                    "date_time": t.date_time,
                    "symbol": t.symbol,
                    "asset_category": t.asset_category,
                    "realized_pnl": t.realized_pnl,
                    "commission": t.commission,
                })
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

        return {
            "total_realized_pnl": total_pnl,
            "max_drawdown_pct": self._max_drawdown(),
            "sharpe_ratio": self._sharpe_ratio(monthly),
            "best_month": {"period": str(monthly.idxmax()), "pnl": monthly.max()} if not monthly.empty else None,
            "worst_month": {"period": str(monthly.idxmin()), "pnl": monthly.min()} if not monthly.empty else None,
            "monthly_pnl": {str(k): v for k, v in monthly.items()},
            "by_asset": self.df.groupby("asset_category")["realized_pnl"].sum().to_dict(),
            "top_winners": self._top_n(10, ascending=False),
            "top_losers": self._top_n(10, ascending=True),
        }

    def _max_drawdown(self) -> float:
        if self.df.empty:
            return 0
        cum = self.df["cumulative_pnl"]
        peak = cum.cummax()
        drawdown = cum - peak
        if peak.max() == 0:
            return 0
        return (drawdown.min() / peak.max()) * 100 if peak.max() != 0 else 0

    def _sharpe_ratio(self, monthly_returns: pd.Series) -> float:
        if monthly_returns.empty or monthly_returns.std() == 0:
            return 0
        # Annualize: mean monthly return / std, * sqrt(12)
        return (monthly_returns.mean() / monthly_returns.std()) * (12 ** 0.5)

    def _top_n(self, n: int, ascending: bool) -> list[dict]:
        by_symbol = self.df.groupby("symbol")["realized_pnl"].sum()
        if ascending:
            # Losers only: filter to negative PnL
            by_symbol = by_symbol[by_symbol < 0].sort_values(ascending=True).head(n)
        else:
            # Winners only: filter to positive PnL
            by_symbol = by_symbol[by_symbol > 0].sort_values(ascending=False).head(n)
        return [{"symbol": s, "pnl": v} for s, v in by_symbol.items()]

    def equity_curve_data(self) -> list[dict]:
        if self.df.empty:
            return []
        daily = self.df.groupby("date")["realized_pnl"].sum().cumsum().reset_index()
        daily.columns = ["date", "cumulative_pnl"]
        return daily.to_dict("records")


# ---------------------------------------------------------------------------
# PortfolioAnalyzer
# ---------------------------------------------------------------------------

class PortfolioAnalyzer:
    """Position structure analysis."""

    def __init__(self, positions: list[OpenPosition], trades: list[Trade]):
        self.positions = positions
        self.trades = trades

    def summary(self) -> dict[str, Any]:
        if not self.positions:
            return self._from_trades()

        total_value = sum(abs(p.position_value) for p in self.positions) or 1

        by_asset: dict[str, float] = {}
        by_symbol: dict[str, float] = {}
        long_value = 0.0
        short_value = 0.0

        for p in self.positions:
            cat = p.asset_category or "Other"
            by_asset[cat] = by_asset.get(cat, 0) + abs(p.position_value)
            by_symbol[p.symbol] = by_symbol.get(p.symbol, 0) + abs(p.position_value)
            if p.quantity > 0:
                long_value += abs(p.position_value)
            else:
                short_value += abs(p.position_value)

        # Top N concentration
        sorted_symbols = sorted(by_symbol.items(), key=lambda x: x[1], reverse=True)
        top5_pct = sum(v for _, v in sorted_symbols[:5]) / total_value * 100
        top10_pct = sum(v for _, v in sorted_symbols[:10]) / total_value * 100

        return {
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
            "currencies": self._currency_breakdown(),
        }

    def _from_trades(self) -> dict[str, Any]:
        """Fallback: derive asset distribution from trade history."""
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

    def _currency_breakdown(self) -> dict[str, float]:
        ccy: dict[str, float] = {}
        total = 0.0
        for p in self.positions:
            ccy[p.currency] = ccy.get(p.currency, 0) + abs(p.position_value)
            total += abs(p.position_value)
        if total == 0:
            return {}
        return {k: v / total * 100 for k, v in ccy.items()}


# ---------------------------------------------------------------------------
# CostAnalyzer
# ---------------------------------------------------------------------------

class CostAnalyzer:
    """Fee and cash flow analysis."""

    def __init__(self, trades: list[Trade], cash_txns: list[CashTransaction]):
        self.trades = trades
        self.cash_txns = cash_txns

    def summary(self) -> dict[str, Any]:
        # Commissions from trades
        total_comm = sum(abs(t.commission) for t in self.trades)
        num_trades = len(self.trades) or 1
        gross_profit = sum(t.realized_pnl for t in self.trades if t.realized_pnl > 0) or 1

        # Cash transactions
        dividends = sum(ct.amount for ct in self.cash_txns if "dividend" in ct.type.lower())
        interest = sum(ct.amount for ct in self.cash_txns if "interest" in ct.type.lower())
        fees = sum(abs(ct.amount) for ct in self.cash_txns if "fee" in ct.type.lower() or "other fee" in ct.type.lower())
        withholding = sum(abs(ct.amount) for ct in self.cash_txns if "withholding" in ct.type.lower())

        # Commission trend by month
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


# ---------------------------------------------------------------------------
# PriceAnalyzer
# ---------------------------------------------------------------------------

class PriceAnalyzer:
    """Fetch historical price data for traded symbols via yfinance (read-only)."""

    def __init__(self, trades: list[Trade], top_n: int = 10):
        self.trades = trades
        self.top_n = top_n

    def get_top_symbols(self) -> list[str]:
        """Return the top-N most traded stock symbols."""
        counts: dict[str, int] = {}
        for t in self.trades:
            if t.asset_category == "STK" and t.symbol:
                counts[t.symbol] = counts.get(t.symbol, 0) + 1
        sorted_syms = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [s for s, _ in sorted_syms[: self.top_n]]

    def fetch_prices(self, symbols: list[str] | None = None, period: str = "1y") -> dict[str, pd.DataFrame]:
        """Fetch daily price history for given symbols. Returns {symbol: DataFrame}."""
        if symbols is None:
            symbols = self.get_top_symbols()
        result = {}
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period=period)
                if not hist.empty:
                    result[sym] = hist[["Close", "Volume"]].reset_index()
            except Exception:
                continue  # skip symbols that yfinance can't resolve
        return result

    def price_vs_trades_data(self, symbol: str, price_df: pd.DataFrame) -> dict:
        """Build combined price + trade markers data for a single symbol."""
        sym_trades = [t for t in self.trades if t.symbol == symbol and t.date_time]
        buys = [{"date": str(t.date_time.date()), "price": t.trade_price, "qty": t.quantity}
                for t in sym_trades if t.buy_sell in ("BUY", "BOT")]
        sells = [{"date": str(t.date_time.date()), "price": t.trade_price, "qty": abs(t.quantity)}
                 for t in sym_trades if t.buy_sell in ("SELL", "SLD")]
        return {
            "symbol": symbol,
            "dates": [str(d.date()) if hasattr(d, "date") else str(d) for d in price_df["Date"]],
            "prices": price_df["Close"].tolist(),
            "buys": buys,
            "sells": sells,
        }


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------

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
    ):
        self.trade_s = trade_summary
        self.pnl_s = pnl_summary
        self.port_s = portfolio_summary
        self.cost_s = cost_summary
        self.equity_curve = equity_curve
        self.trade_df = trade_df
        self.output_dir = output_dir
        self.price_charts = price_charts or []
        self.date_str = datetime.now().strftime("%Y-%m-%d")

    # ---- Terminal summary ----

    def print_terminal_summary(self) -> str:
        lines = []
        lines.append("=" * 55)
        lines.append("  IBKR Trading Analysis Summary")
        lines.append("=" * 55)

        if self.trade_df.empty:
            lines.append("No trade data available.")
            summary = "\n".join(lines)
            print(summary)
            return summary

        period_start = self.trade_df["date_time"].min().strftime("%Y-%m-%d")
        period_end = self.trade_df["date_time"].max().strftime("%Y-%m-%d")
        lines.append(f"Period: {period_start} to {period_end}")
        lines.append("")

        # Key metrics
        total = self.trade_s.get("total_trades", 0)
        wr = self.trade_s.get("win_rate", 0)
        pf = self.trade_s.get("profit_factor", 0)
        pnl = self.pnl_s.get("total_realized_pnl", 0)
        dd = self.pnl_s.get("max_drawdown_pct", 0)
        sr = self.pnl_s.get("sharpe_ratio", 0)
        comm = self.cost_s.get("total_commissions", 0)
        fee_ratio = self.cost_s.get("fee_to_pnl_ratio_pct", 0)

        lines.append(f"Total Trades: {total:,}  |  Win Rate: {wr:.1f}%  |  Profit Factor: {pf:.2f}")
        lines.append(f"Total P&L: ${pnl:,.2f}  |  Max Drawdown: {dd:.1f}%  |  Sharpe: {sr:.2f}")
        lines.append(f"Total Fees: ${comm:,.2f} ({fee_ratio:.1f}% of gross profit)")

        # Top / worst
        winners = self.pnl_s.get("top_winners", [])
        losers = self.pnl_s.get("top_losers", [])
        if winners:
            w = winners[0]
            lines.append(f"Top Performer: {w['symbol']} (+${w['pnl']:,.2f})")
        if losers:
            l = losers[0]
            lines.append(f"Worst Performer: {l['symbol']} (${l['pnl']:,.2f})")

        # Key findings
        lines.append("")
        lines.append("Key Findings:")
        by_asset = self.trade_s.get("by_asset", {})
        if by_asset:
            best_wr_cat = max(by_asset, key=lambda c: by_asset[c].get("win_rate", 0))
            lines.append(f"  - Best win rate by asset: {best_wr_cat} ({by_asset[best_wr_cat]['win_rate']:.1f}%)")

        by_weekday = self.trade_s.get("by_weekday", {})
        if by_weekday:
            busiest = max(by_weekday, key=by_weekday.get)
            lines.append(f"  - Most active trading day: {busiest} ({by_weekday[busiest]} trades)")

        top5 = self.port_s.get("top5_concentration_pct", 0)
        if top5 > 0:
            lines.append(f"  - Top 5 positions: {top5:.1f}% of portfolio")

        div = self.cost_s.get("net_dividend", 0)
        if div != 0:
            lines.append(f"  - Net dividend income: ${div:,.2f}")

        lines.append("=" * 55)
        summary = "\n".join(lines)
        print(summary)
        return summary

    # ---- Markdown report ----

    def write_markdown(self) -> Path:
        out = self.output_dir / f"ibkr-analysis-{self.date_str}.md"
        sections = []

        sections.append("# IBKR Trading Analysis Report\n")
        sections.append(f"Generated: {self.date_str}\n")

        # Trade behavior
        sections.append("## Trading Behavior Patterns\n")
        sections.append(f"| Metric | Value |")
        sections.append(f"|--------|-------|")
        sections.append(f"| Total Trades | {self.trade_s.get('total_trades', 0):,} |")
        sections.append(f"| Win Rate | {self.trade_s.get('win_rate', 0):.1f}% |")
        sections.append(f"| Profit Factor | {self.trade_s.get('profit_factor', 0):.2f} |")
        sections.append(f"| Avg Trade Size | ${self.trade_s.get('avg_trade_size', 0):,.0f} |")
        sections.append(f"| Trades Per Day | {self.trade_s.get('trades_per_day', 0):.1f} |")
        sections.append("")

        by_asset = self.trade_s.get("by_asset", {})
        if by_asset:
            sections.append("### By Asset Type\n")
            sections.append("| Asset | Trades | Win Rate | Total P&L |")
            sections.append("|-------|--------|----------|-----------|")
            for cat, info in sorted(by_asset.items()):
                sections.append(f"| {cat} | {info['count']:,} | {info['win_rate']:.1f}% | ${info['total_pnl']:,.2f} |")
            sections.append("")

        # P&L
        sections.append("## P&L Performance\n")
        sections.append(f"| Metric | Value |")
        sections.append(f"|--------|-------|")
        sections.append(f"| Total Realized P&L | ${self.pnl_s.get('total_realized_pnl', 0):,.2f} |")
        sections.append(f"| Max Drawdown | {self.pnl_s.get('max_drawdown_pct', 0):.1f}% |")
        sections.append(f"| Sharpe Ratio | {self.pnl_s.get('sharpe_ratio', 0):.2f} |")
        best = self.pnl_s.get("best_month")
        worst = self.pnl_s.get("worst_month")
        if best:
            sections.append(f"| Best Month | {best['period']} (${best['pnl']:,.2f}) |")
        if worst:
            sections.append(f"| Worst Month | {worst['period']} (${worst['pnl']:,.2f}) |")
        sections.append("")

        # Top winners / losers
        for label, key in [("Top 10 Winners", "top_winners"), ("Top 10 Losers", "top_losers")]:
            items = self.pnl_s.get(key, [])
            if items:
                sections.append(f"### {label}\n")
                sections.append("| Symbol | P&L |")
                sections.append("|--------|-----|")
                for it in items:
                    sections.append(f"| {it['symbol']} | ${it['pnl']:,.2f} |")
                sections.append("")

        # Portfolio
        sections.append("## Portfolio Structure\n")
        pa = self.port_s
        if pa.get("total_positions", 0) > 0:
            sections.append(f"| Metric | Value |")
            sections.append(f"|--------|-------|")
            sections.append(f"| Open Positions | {pa['total_positions']} |")
            sections.append(f"| Total Value | ${pa.get('total_value', 0):,.2f} |")
            sections.append(f"| Unrealized P&L | ${pa.get('unrealized_pnl', 0):,.2f} |")
            sections.append(f"| Long % | {pa.get('long_pct', 0):.1f}% |")
            sections.append(f"| Short % | {pa.get('short_pct', 0):.1f}% |")
            sections.append(f"| Top 5 Concentration | {pa.get('top5_concentration_pct', 0):.1f}% |")
            sections.append("")

            holdings = pa.get("top_holdings", [])
            if holdings:
                sections.append("### Top Holdings\n")
                sections.append("| Symbol | Qty | Cost Basis | Market Value | Unrealized P&L | % |")
                sections.append("|--------|-----|-----------|-------------|----------------|---|")
                for h in holdings:
                    qty = h.get("quantity", 0)
                    cb = h.get("cost_basis", 0)
                    upnl = h.get("unrealized_pnl", 0)
                    qty_str = f"{qty:g}" if qty == int(qty) else f"{qty:.4f}"
                    cb_str = f"${cb:,.2f}" if cb > 0 else "N/A"
                    upnl_str = f"${upnl:+,.2f}" if cb > 0 else "N/A"
                    sections.append(f"| {h['symbol']} | {qty_str} | {cb_str} | ${h['value']:,.2f} | {upnl_str} | {h['pct']:.1f}% |")
                sections.append("")
        else:
            note = pa.get("note", "No open position data available.")
            sections.append(f"_{note}_\n")

        # Costs
        sections.append("## Fees & Cash Flow\n")
        sections.append(f"| Metric | Value |")
        sections.append(f"|--------|-------|")
        sections.append(f"| Total Commissions | ${self.cost_s.get('total_commissions', 0):,.2f} |")
        sections.append(f"| Avg Per Trade | ${self.cost_s.get('avg_commission_per_trade', 0):,.2f} |")
        sections.append(f"| Fee/Profit Ratio | {self.cost_s.get('fee_to_pnl_ratio_pct', 0):.1f}% |")
        sections.append(f"| Dividend Income | ${self.cost_s.get('dividend_income', 0):,.2f} |")
        sections.append(f"| Withholding Tax | ${self.cost_s.get('withholding_tax', 0):,.2f} |")
        sections.append(f"| Net Interest | ${self.cost_s.get('interest_net', 0):,.2f} |")
        sections.append("")

        out.write_text("\n".join(sections), encoding="utf-8")
        return out

    # ---- HTML report ----

    def write_html(self) -> Path:
        out = self.output_dir / f"ibkr-analysis-{self.date_str}.html"
        charts_json = self._generate_charts_json()

        template_path = Path(__file__).parent / "templates" / "report.html.j2"
        if template_path.exists():
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(template_path.parent)))
            tmpl = env.get_template(template_path.name)
            html = tmpl.render(
                date=self.date_str,
                trade_summary=self.trade_s,
                pnl_summary=self.pnl_s,
                portfolio_summary=self.port_s,
                cost_summary=self.cost_s,
                charts=charts_json,
            )
        else:
            html = self._generate_standalone_html(charts_json)

        out.write_text(html, encoding="utf-8")
        return out

    def _generate_charts_json(self) -> dict[str, str]:
        charts = {}

        # 1. Equity curve
        if self.equity_curve:
            dates = [str(r["date"]) for r in self.equity_curve]
            values = [r["cumulative_pnl"] for r in self.equity_curve]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=values, mode="lines", name="Cumulative P&L",
                                     fill="tozeroy", line=dict(color="#2196F3")))
            fig.update_layout(title="Equity Curve", xaxis_title="Date", yaxis_title="Cumulative P&L ($)",
                              template="plotly_white", height=400)
            charts["equity_curve"] = fig.to_json()

        # 2. Monthly P&L bar chart
        monthly = self.pnl_s.get("monthly_pnl", {})
        if monthly:
            months = list(monthly.keys())
            vals = list(monthly.values())
            colors = ["#4CAF50" if v >= 0 else "#F44336" for v in vals]
            fig = go.Figure(go.Bar(x=months, y=vals, marker_color=colors))
            fig.update_layout(title="Monthly P&L", xaxis_title="Month", yaxis_title="P&L ($)",
                              template="plotly_white", height=400)
            charts["monthly_pnl"] = fig.to_json()

        # 3. Asset distribution
        by_asset = self.port_s.get("by_asset", {})
        if by_asset:
            labels = list(by_asset.keys())
            values = [v.get("value", v.get("count", 0)) for v in by_asset.values()]
            fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.4))
            fig.update_layout(title="Asset Distribution", template="plotly_white", height=400)
            charts["asset_distribution"] = fig.to_json()

        # 4. Trade frequency heatmap (weekday x hour)
        if not self.trade_df.empty and "weekday" in self.trade_df.columns and "hour" in self.trade_df.columns:
            pivot = self.trade_df.groupby(["weekday", "hour"]).size().unstack(fill_value=0)
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            pivot = pivot.reindex([d for d in day_order if d in pivot.index])
            fig = go.Figure(go.Heatmap(
                z=pivot.values, x=[str(h) for h in pivot.columns], y=pivot.index,
                colorscale="YlOrRd", hoverongaps=False,
            ))
            fig.update_layout(title="Trade Frequency (Day x Hour)", xaxis_title="Hour",
                              yaxis_title="Day", template="plotly_white", height=400)
            charts["frequency_heatmap"] = fig.to_json()

        # 5. Position concentration with unrealized P&L
        holdings = self.port_s.get("top_holdings", [])
        if holdings:
            symbols = [h["symbol"] for h in holdings]
            upnl = [h.get("unrealized_pnl", 0) for h in holdings]
            colors = ["#4CAF50" if v >= 0 else "#F44336" for v in upnl]
            fig = make_subplots(rows=1, cols=2, subplot_titles=("Portfolio Weight (%)", "Unrealized P&L ($)"))
            fig.add_trace(go.Bar(x=symbols, y=[h["pct"] for h in holdings], marker_color="#FF9800", name="Weight"), row=1, col=1)
            fig.add_trace(go.Bar(x=symbols, y=upnl, marker_color=colors, name="Unrealized P&L"), row=1, col=2)
            fig.update_layout(title="Top Holdings: Concentration & Unrealized P&L", template="plotly_white", height=400, showlegend=False)
            charts["concentration"] = fig.to_json()

        # 6. Commission trend
        comm_monthly = self.cost_s.get("commission_by_month", {})
        if comm_monthly:
            fig = go.Figure(go.Scatter(
                x=list(comm_monthly.keys()), y=list(comm_monthly.values()),
                mode="lines+markers", line=dict(color="#9C27B0"),
            ))
            fig.update_layout(title="Commission Trend", xaxis_title="Month",
                              yaxis_title="Commission ($)", template="plotly_white", height=400)
            charts["commission_trend"] = fig.to_json()

        # 7. Price charts with trade markers
        for pc in self.price_charts:
            sym = pc["symbol"]
            fig = go.Figure()
            # Price line
            fig.add_trace(go.Scatter(
                x=pc["dates"], y=pc["prices"], mode="lines",
                name=f"{sym} Price", line=dict(color="#607D8B"),
            ))
            # Buy markers
            if pc["buys"]:
                fig.add_trace(go.Scatter(
                    x=[b["date"] for b in pc["buys"]],
                    y=[b["price"] for b in pc["buys"]],
                    mode="markers", name="Buy",
                    marker=dict(symbol="triangle-up", size=10, color="#4CAF50"),
                    text=[f"Qty: {b['qty']}" for b in pc["buys"]],
                ))
            # Sell markers
            if pc["sells"]:
                fig.add_trace(go.Scatter(
                    x=[s["date"] for s in pc["sells"]],
                    y=[s["price"] for s in pc["sells"]],
                    mode="markers", name="Sell",
                    marker=dict(symbol="triangle-down", size=10, color="#F44336"),
                    text=[f"Qty: {s['qty']}" for s in pc["sells"]],
                ))
            fig.update_layout(
                title=f"{sym} Price & Trades", xaxis_title="Date", yaxis_title="Price ($)",
                template="plotly_white", height=400, showlegend=True,
            )
            charts[f"price_{sym}"] = fig.to_json()

        return charts

    def _generate_standalone_html(self, charts: dict[str, str]) -> str:
        """Generate a self-contained HTML report without the Jinja2 template."""
        chart_divs = []
        for i, (name, fig_json) in enumerate(charts.items()):
            chart_divs.append(f'<div id="chart-{i}" style="width:100%;margin-bottom:30px;"></div>')
            chart_divs.append(f'<script>Plotly.newPlot("chart-{i}", JSON.parse({json.dumps(fig_json)}).data, JSON.parse({json.dumps(fig_json)}).layout, {{responsive:true}});</script>')

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
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
              gap: 16px; margin: 20px 0; }}
  .metric-card {{ background: white; border-radius: 8px; padding: 16px;
                  box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .metric-value {{ font-size: 24px; font-weight: bold; color: #1a237e; }}
  .metric-label {{ font-size: 13px; color: #666; margin-top: 4px; }}
</style>
</head>
<body>
<h1>IBKR Trading Analysis</h1>
<p>Generated: {self.date_str}</p>

<div class="metrics">
  <div class="metric-card">
    <div class="metric-value">{self.trade_s.get('total_trades', 0):,}</div>
    <div class="metric-label">Total Trades</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{self.trade_s.get('win_rate', 0):.1f}%</div>
    <div class="metric-label">Win Rate</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">${self.pnl_s.get('total_realized_pnl', 0):,.2f}</div>
    <div class="metric-label">Total P&L</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{self.pnl_s.get('sharpe_ratio', 0):.2f}</div>
    <div class="metric-label">Sharpe Ratio</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{self.pnl_s.get('max_drawdown_pct', 0):.1f}%</div>
    <div class="metric-label">Max Drawdown</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">${self.cost_s.get('total_commissions', 0):,.2f}</div>
    <div class="metric-label">Total Commissions</div>
  </div>
</div>

<h2>Charts</h2>
{''.join(chart_divs)}

</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
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
    parser.add_argument("--proxy", help="HTTP/SOCKS5 proxy URL, e.g. socks5://127.0.0.1:7980 or http://127.0.0.1:7980")
    parser.add_argument("--dump-xml", help="Dump raw Flex XML response to this file path for debugging")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    # Auto-detect proxy from env if not specified
    proxy = args.proxy or os.environ.get("ALL_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    if args.mode == "flex":
        if not args.token or not args.query_id:
            print("Error: --token and --query-id are required for flex mode", file=sys.stderr)
            sys.exit(1)
        if proxy:
            print(f"Using proxy: {proxy}")
        print("Fetching data from Flex Web Service (read-only)...")
        data = DataLoader.from_flex(args.token, args.query_id, proxy=proxy, dump_xml=args.dump_xml)
    else:
        if not args.source:
            print("Error: --source is required for file mode", file=sys.stderr)
            sys.exit(1)
        print(f"Loading data from {args.source}...")
        data = DataLoader.from_file(args.source, args.format)

    print(f"Loaded: {len(data.trades)} trades, {len(data.cash_transactions)} cash transactions, {len(data.open_positions)} open positions")

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

    # Run analysis
    print("Analyzing...")
    ta = TradeAnalyzer(data.trades)
    pa = PnLAnalyzer(data.trades)
    porta = PortfolioAnalyzer(data.open_positions, data.trades)
    ca = CostAnalyzer(data.trades, data.cash_transactions)

    trade_summary = ta.summary()
    pnl_summary = pa.summary()
    port_summary = porta.summary()
    cost_summary = ca.summary()
    equity_curve = pa.equity_curve_data()

    # Fetch price history for top traded symbols
    price_charts: list[dict] = []
    if not args.no_prices:
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
        trade_summary=trade_summary,
        pnl_summary=pnl_summary,
        portfolio_summary=port_summary,
        cost_summary=cost_summary,
        equity_curve=equity_curve,
        trade_df=ta.df,
        output_dir=output_dir,
        price_charts=price_charts,
    )

    rg.print_terminal_summary()
    md_path = rg.write_markdown()
    html_path = rg.write_html()

    print(f"\nReports saved:")
    print(f"  Markdown: {md_path}")
    print(f"  HTML:     {html_path}")


if __name__ == "__main__":
    main()
