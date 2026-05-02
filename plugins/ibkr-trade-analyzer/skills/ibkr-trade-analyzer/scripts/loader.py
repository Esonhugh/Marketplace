"""IBKR data loader — Flex Web Service and local CSV/XML file import."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

import requests

from models import AccountData, CashBalance, CashTransaction, OpenPosition, Trade


class DataLoader:
    """Load IBKR data from Flex Web Service or local files."""

    FLEX_SEND_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest"
    FLEX_GET_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement"

    @staticmethod
    def _get_session(proxy: str | None = None) -> requests.Session:
        session = requests.Session()
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        return session

    @staticmethod
    def from_flex(
        token: str,
        query_id: str,
        proxy: str | None = None,
        dump_xml: str | None = None,
        save_dir: Path | None = None,
    ) -> AccountData:
        """Fetch data via Flex Web Service (read-only API).

        Args:
            token:    Flex Web Service token.
            query_id: Flex Query numeric ID.
            proxy:    Optional HTTP/SOCKS5 proxy URL.
            dump_xml: Optional path to write raw XML for debugging.
            save_dir: Optional directory to auto-save the XML as
                      ``{account_id}-flex-ibkr-YYYY-MM-DD.xml``.
        """
        session = DataLoader._get_session(proxy)

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

        # IBKR "not ready yet" codes: 1018 = queued, 1019 = in progress
        PENDING_CODES = {"1018", "1019"}

        for attempt in range(10):
            time.sleep(5 if attempt > 0 else 2)
            resp2 = session.get(
                DataLoader.FLEX_GET_URL,
                params={"t": token, "q": ref_code, "v": "3"},
                timeout=60,
            )
            resp2.raise_for_status()

            body = resp2.text.strip()
            if not body.startswith("<"):
                print(f"  Attempt {attempt + 1}: unexpected non-XML response, retrying…")
                continue

            try:
                check = ET.fromstring(body)
            except ET.ParseError as exc:
                raise RuntimeError(f"Flex GetStatement returned unparseable XML: {exc}\n{body[:200]}") from exc

            err_code = check.findtext("ErrorCode") or ""
            if err_code in PENDING_CODES:
                msg = check.findtext("ErrorMessage", "report not ready")
                print(f"  Attempt {attempt + 1}: {msg} (code {err_code}), waiting…")
                continue

            if err_code:
                err_msg = check.findtext("ErrorMessage", "unknown error")
                raise RuntimeError(f"Flex GetStatement failed (code {err_code}): {err_msg}")

            # Auto-save to data dir before parsing
            if save_dir is not None:
                DataLoader._autosave_xml(body, save_dir)

            return DataLoader._parse_flex_xml(body, dump_path=dump_xml)

        raise RuntimeError("Flex report not ready after multiple attempts. Try again in a few minutes.")

    @staticmethod
    def _autosave_xml(xml_text: str, save_dir: Path) -> Path | None:
        """Save raw XML to *save_dir* as ``{account_id}-flex-ibkr-YYYY-MM-DD.xml``.

        Returns the saved path, or None on failure (non-fatal).
        """
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
            # Extract account ID before full parse
            acct_id = "unknown"
            try:
                r = ET.fromstring(xml_text)
                acct_node = r.find(".//AccountInformation")
                if acct_node is not None:
                    acct_id = acct_node.get("accountId", "unknown") or "unknown"
                elif r.get("accountId"):
                    acct_id = r.get("accountId", "unknown")
            except ET.ParseError:
                pass
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{acct_id}-flex-ibkr-{date_str}.xml"
            dest = save_dir / filename
            dest.write_text(xml_text, encoding="utf-8")
            print(f"  Saved Flex XML → {dest}")
            return dest
        except Exception as exc:
            print(f"  Warning: could not save XML to data dir: {exc}")
            return None

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
        return DataLoader._parse_csv(p.read_text(encoding="utf-8"))

    # ---- XML parsing ----

    @staticmethod
    def _parse_flex_xml(xml_text: str, dump_path: str | None = None) -> AccountData:
        if dump_path:
            Path(dump_path).write_text(xml_text, encoding="utf-8")
            print(f"  Raw XML dumped to: {dump_path}")
        root = ET.fromstring(xml_text)
        data = AccountData()

        acct_info = root.find(".//AccountInformation")
        if acct_info is not None:
            data.account_id = acct_info.get("accountId", "")
            data.base_currency = acct_info.get("currency", "USD")

        for node in root.iter("Trade"):
            fifo_pnl = DataLoader._float(node.get("fifoPnlRealized", node.get("realizedPnl", "0")))
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
                buy_sell=node.get("buySell", ""),
                open_close=node.get("openCloseIndicator", ""),
                exchange=node.get("exchange", ""),
                order_type=node.get("orderType", ""),
                multiplier=DataLoader._float(node.get("multiplier", "1")),
            )
            data.trades.append(t)

        if not any(t.realized_pnl != 0 for t in data.trades) and data.trades:
            DataLoader._compute_fifo_pnl(data.trades)

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

        if not any(p.unrealized_pnl != 0 or p.cost_basis_price != 0 for p in data.open_positions) \
                and data.open_positions and data.trades:
            DataLoader._compute_unrealized_pnl(data.trades, data.open_positions)

        for node in root.iter("CashReportCurrency"):
            ccy = node.get("currency", "")
            if ccy and ccy != "BASE_SUMMARY":
                data.cash_balances.append(CashBalance(
                    currency=ccy,
                    ending_cash=DataLoader._float(node.get("endingCash", "0")),
                    ending_settled_cash=DataLoader._float(node.get("endingSettledCash", "0")),
                ))

        for node in root.iter("ConversionRate"):
            from_ccy = node.get("fromCurrency", "")
            to_ccy = node.get("toCurrency", "")
            rate = DataLoader._float(node.get("rate", "0"))
            if from_ccy and to_ccy == data.base_currency and rate > 0:
                data.conversion_rates[from_ccy] = rate

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

            if row_type == "Header":
                current_section = section_marker
                headers = [p.strip('"') for p in parts[2:]]
                continue
            if row_type != "Data":
                continue

            values = [p.strip('"') for p in parts[2:]]
            row = dict(zip(headers, values)) if len(values) == len(headers) else {}

            if current_section == "Trades":
                data.trades.append(Trade(
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
                ))

            elif current_section in ("Dividends", "Interest", "Fees"):
                data.cash_transactions.append(CashTransaction(
                    date_time=DataLoader._parse_dt(row.get("Date/Time", row.get("Date", ""))),
                    type=current_section,
                    symbol=row.get("Symbol", row.get("Description", "")),
                    currency=row.get("Currency", "USD"),
                    amount=DataLoader._float(row.get("Amount", "0")),
                    description=row.get("Description", ""),
                ))

            elif current_section == "Open Positions":
                data.open_positions.append(OpenPosition(
                    symbol=row.get("Symbol", ""),
                    asset_category=row.get("Asset Category", ""),
                    currency=row.get("Currency", "USD"),
                    quantity=DataLoader._float(row.get("Quantity", "0")),
                    cost_basis_price=DataLoader._float(row.get("Cost Basis", "0")),
                    mark_price=DataLoader._float(row.get("Mark Price", row.get("Close Price", "0"))),
                    unrealized_pnl=DataLoader._float(row.get("Unrealized P/L", "0")),
                    position_value=DataLoader._float(row.get("Value", "0")),
                ))

            elif current_section == "Account Information":
                if row.get("Field Name") == "Account":
                    data.account_id = row.get("Value", "")
                if row.get("Field Name") == "Base Currency":
                    data.base_currency = row.get("Value", "USD")

        return data

    # ---- Helpers ----

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
        """Compute realized PnL via FIFO lot matching (mutates trade.realized_pnl)."""
        by_symbol: dict[str, list[Trade]] = defaultdict(list)
        for t in trades:
            by_symbol[t.symbol].append(t)

        for sym_trades in by_symbol.values():
            sym_trades.sort(key=lambda t: t.date_time or datetime.min)
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
                    t.realized_pnl = realized + t.commission

    @staticmethod
    def _compute_unrealized_pnl(trades: list[Trade], positions: list[OpenPosition]) -> None:
        """Compute unrealized PnL and cost basis from FIFO remaining lots."""
        by_symbol: dict[str, list[Trade]] = defaultdict(list)
        for t in trades:
            by_symbol[t.symbol].append(t)

        for pos in positions:
            sym_trades = sorted(by_symbol.get(pos.symbol, []), key=lambda t: t.date_time or datetime.min)
            lots: deque[list] = deque()
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
            if lots:
                total_qty = sum(l[0] for l in lots)
                total_cost = sum(l[0] * l[1] for l in lots)
                if total_qty > 0:
                    pos.cost_basis_price = total_cost / total_qty
                    pos.unrealized_pnl = (pos.mark_price - pos.cost_basis_price) * pos.quantity
