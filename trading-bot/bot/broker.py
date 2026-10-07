"""MT5-Anbindung mit Demo-Sperre.

Windows-PC: offizielles MetaTrader5-Paket (bridge: native).
Linux-VPS:  MT5 läuft unter Wine, Python spricht per mt5linux/RPyC (bridge: rpyc).
"""
import logging
import os
import time

import pandas as pd

from .risk import SymbolSpec

log = logging.getLogger(__name__)

# Bitflags in symbol_info().filling_mode
SYMBOL_FILLING_FOK = 1
SYMBOL_FILLING_IOC = 2
LIVE_CONFIRM_ENV = "BOT_LIVE_CONFIRM"
LIVE_CONFIRM_VALUE = "ICH-AKZEPTIERE-TOTALVERLUST"


class LiveTradingBlocked(RuntimeError):
    pass


class BrokerError(RuntimeError):
    pass


def load_mt5_module(cfg: dict):
    if cfg["bridge"] == "native":
        import MetaTrader5 as mt5  # nur unter Windows installierbar

        return mt5
    if cfg["bridge"] == "rpyc":
        from mt5linux import MetaTrader5

        return MetaTrader5(host=cfg["rpyc_host"], port=cfg["rpyc_port"])
    raise ValueError(f"Unbekannte bridge: {cfg['bridge']}")


class Broker:
    def __init__(self, mt5, cfg: dict):
        self.mt5 = mt5
        self.cfg = cfg
        self.magic = int(cfg["magic"])
        self._offset_cache: float | None = None
        self.account = None

    # ---------- Verbindung ----------
    def connect(self):
        args = [self.cfg["path"]] if self.cfg.get("path") else []
        kwargs = {}
        if self.cfg.get("login"):
            kwargs = {
                "login": int(self.cfg["login"]),
                "password": os.environ.get("MT5_PASSWORD", ""),
                "server": self.cfg["server"],
            }
        if not self.mt5.initialize(*args, **kwargs):
            raise BrokerError(f"MT5 initialize fehlgeschlagen: {self.mt5.last_error()}")
        self.account = self.mt5.account_info()
        if self.account is None:
            raise BrokerError(f"Kein Konto eingeloggt: {self.mt5.last_error()}")
        self.check_account_mode(self.account)
        term = self.mt5.terminal_info()
        if term is not None and not term.trade_allowed:
            log.warning("Algo-Trading ist im MT5-Terminal AUS - Orders werden abgelehnt.")
        return self.account

    def is_demo(self, account=None) -> bool:
        account = account or self.account
        return account.trade_mode == self.mt5.ACCOUNT_TRADE_MODE_DEMO

    def check_account_mode(self, account):
        if self.is_demo(account):
            return
        if not self.cfg.get("allow_live"):
            raise LiveTradingBlocked(
                "Echtgeld-Konto erkannt, aber mt5.allow_live ist false. Bot stoppt."
            )
        if os.environ.get(LIVE_CONFIRM_ENV) != LIVE_CONFIRM_VALUE:
            raise LiveTradingBlocked(
                f"Echtgeld-Konto: setze zusätzlich {LIVE_CONFIRM_ENV}={LIVE_CONFIRM_VALUE}"
            )
        log.warning("ECHTGELD-MODUS aktiv auf Konto %s", account.login)

    def shutdown(self):
        self.mt5.shutdown()

    # ---------- Kontodaten ----------
    def equity(self) -> float:
        info = self.mt5.account_info()
        if info is None:
            raise BrokerError(f"account_info fehlgeschlagen: {self.mt5.last_error()}")
        return float(info.equity)

    def spec(self, symbol: str) -> SymbolSpec | None:
        if not self.mt5.symbol_select(symbol, True):
            return None
        info = self.mt5.symbol_info(symbol)
        if info is None:
            return None
        tick_value = getattr(info, "trade_tick_value_loss", 0) or info.trade_tick_value
        return SymbolSpec(
            name=symbol,
            point=info.point,
            digits=info.digits,
            tick_size=info.trade_tick_size or info.point,
            tick_value=tick_value,
            volume_min=info.volume_min,
            volume_max=info.volume_max,
            volume_step=info.volume_step,
            stops_level=info.trade_stops_level,
        )

    def tick(self, symbol: str):
        return self.mt5.symbol_info_tick(symbol)

    # ---------- Zeit ----------
    def server_offset_hours(self, symbols: list[str]) -> float:
        """MT5-Kerzenzeiten sind Serverzeit. Versatz zu UTC aus frischem Tick ableiten."""
        configured = self.cfg.get("server_utc_offset_hours", "auto")
        if configured != "auto":
            return float(configured)
        for sym in symbols:
            tick = self.tick(sym)
            if tick is None:
                continue
            diff = tick.time - time.time()
            hours = round(diff / 1800) / 2
            if -12 <= hours <= 14 and abs(diff - hours * 3600) < 120:
                self._offset_cache = hours
                return hours
        if self._offset_cache is None:
            log.warning("Server-Zeitversatz nicht ermittelbar (Markt zu?), nehme +2h an")
            return 2.0
        return self._offset_cache

    # ---------- Kursdaten ----------
    def rates(self, symbol: str, timeframe: str, count: int, offset_hours: float) -> pd.DataFrame | None:
        tf = getattr(self.mt5, f"TIMEFRAME_{timeframe}")
        raw = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if raw is None or len(raw) == 0:
            return None
        df = pd.DataFrame(raw)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True) - pd.Timedelta(hours=offset_hours)
        return df[["time", "open", "high", "low", "close", "spread"]].reset_index(drop=True)

    # ---------- Positionen ----------
    def positions(self, symbol: str | None = None) -> list:
        res = self.mt5.positions_get(symbol=symbol) if symbol else self.mt5.positions_get()
        return [p for p in (res or []) if p.magic == self.magic]

    def _filling(self, symbol: str) -> int:
        mode = self.mt5.symbol_info(symbol).filling_mode
        if mode & SYMBOL_FILLING_FOK:
            return self.mt5.ORDER_FILLING_FOK
        if mode & SYMBOL_FILLING_IOC:
            return self.mt5.ORDER_FILLING_IOC
        return self.mt5.ORDER_FILLING_RETURN

    def build_market_request(self, symbol, side, lots, sl_distance, tp_distance, spec, comment=""):
        tick = self.tick(symbol)
        if tick is None:
            raise BrokerError(f"Kein Tick für {symbol}")
        if side == "buy":
            price, order_type = tick.ask, self.mt5.ORDER_TYPE_BUY
            sl, tp = price - sl_distance, price + tp_distance
        else:
            price, order_type = tick.bid, self.mt5.ORDER_TYPE_SELL
            sl, tp = price + sl_distance, price - tp_distance
        min_dist = spec.stops_level * spec.point
        if sl_distance < min_dist or tp_distance < min_dist:
            raise BrokerError(f"{symbol}: Stop-Abstand kleiner als Broker-Minimum ({min_dist})")
        return {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lots),
            "type": order_type,
            "price": price,
            "sl": round(sl, spec.digits),
            "tp": round(tp, spec.digits),
            "deviation": int(self.cfg["deviation_points"]),
            "magic": self.magic,
            "comment": comment[:31],
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(symbol),
        }

    def send(self, request: dict):
        check = self.mt5.order_check(request)
        if check is None or check.retcode != 0:
            raise BrokerError(f"order_check abgelehnt: {getattr(check, 'comment', self.mt5.last_error())}")
        result = self.mt5.order_send(request)
        if result is None:
            raise BrokerError(f"order_send ohne Antwort: {self.mt5.last_error()}")
        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            raise BrokerError(f"Order abgelehnt ({result.retcode}): {result.comment}")
        return result

    def close_position(self, pos):
        tick = self.tick(pos.symbol)
        is_buy = pos.type == self.mt5.POSITION_TYPE_BUY
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": self.mt5.ORDER_TYPE_SELL if is_buy else self.mt5.ORDER_TYPE_BUY,
            "position": pos.ticket,
            "price": tick.bid if is_buy else tick.ask,
            "deviation": int(self.cfg["deviation_points"]),
            "magic": self.magic,
            "comment": "bot close",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(pos.symbol),
        }
        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            raise BrokerError(f"Schließen von {pos.ticket} fehlgeschlagen: {getattr(result, 'comment', self.mt5.last_error())}")
        return result

    def close_all(self) -> int:
        closed = 0
        for pos in self.positions():
            try:
                self.close_position(pos)
                closed += 1
            except BrokerError as exc:
                log.error("%s", exc)
        return closed
