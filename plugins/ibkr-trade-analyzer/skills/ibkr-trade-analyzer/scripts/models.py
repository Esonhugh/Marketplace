"""Data models for IBKR trading data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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
class CashBalance:
    currency: str = ""
    ending_cash: float = 0.0
    ending_settled_cash: float = 0.0


@dataclass
class AccountData:
    trades: list[Trade] = field(default_factory=list)
    cash_transactions: list[CashTransaction] = field(default_factory=list)
    open_positions: list[OpenPosition] = field(default_factory=list)
    cash_balances: list[CashBalance] = field(default_factory=list)
    conversion_rates: dict[str, float] = field(default_factory=dict)
    account_id: str = ""
    base_currency: str = "USD"
