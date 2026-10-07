"""Minimaler Ersatz für das MetaTrader5-Paket (nur für Tests)."""
import time
from types import SimpleNamespace as NS

import numpy as np


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO, ACCOUNT_TRADE_MODE_CONTEST, ACCOUNT_TRADE_MODE_REAL = 0, 1, 2
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY, ORDER_TYPE_SELL = 0, 1
    POSITION_TYPE_BUY, POSITION_TYPE_SELL = 0, 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK, ORDER_FILLING_IOC, ORDER_FILLING_RETURN = 0, 1, 2
    TRADE_RETCODE_DONE = 10009
    TIMEFRAME_M15 = 15

    def __init__(self, trade_mode=0, filling_mode=2, server_offset_h=3, stops_level=0):
        self.trade_mode = trade_mode
        self.filling_mode = filling_mode
        self.server_offset_h = server_offset_h
        self.stops_level = stops_level
        self.sent = []
        self.positions = []
        self.init_args = None

    def initialize(self, *args, **kwargs):
        self.init_args = (args, kwargs)
        return True

    def shutdown(self):
        pass

    def last_error(self):
        return (0, "ok")

    def account_info(self):
        return NS(login=123, trade_mode=self.trade_mode, equity=1000.0, balance=1000.0,
                  currency="EUR", company="Fusion Markets", server="FusionMarkets-Demo", leverage=500)

    def terminal_info(self):
        return NS(trade_allowed=True, connected=True)

    def symbol_select(self, symbol, enable):
        return symbol != "NOPE"

    def symbol_info(self, symbol):
        return NS(point=0.00001, digits=5, trade_tick_size=0.00001, trade_tick_value=1.0,
                  trade_tick_value_loss=1.0, volume_min=0.01, volume_max=100.0, volume_step=0.01,
                  trade_stops_level=self.stops_level, filling_mode=self.filling_mode)

    def symbol_info_tick(self, symbol):
        return NS(time=int(time.time()) + self.server_offset_h * 3600, bid=1.10000, ask=1.10002)

    def copy_rates_from_pos(self, symbol, tf, start, count):
        dtype = [("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"),
                 ("close", "f8"), ("tick_volume", "i8"), ("spread", "i4"), ("real_volume", "i8")]
        t0 = 1_791_000_000
        return np.array([(t0 + k * 900, 1.1, 1.1001, 1.0999, 1.1, 10, 2, 0) for k in range(count)], dtype=dtype)

    def positions_get(self, symbol=None):
        return [p for p in self.positions if symbol in (None, p.symbol)]

    def order_check(self, request):
        return NS(retcode=0, comment="Done")

    def order_send(self, request):
        self.sent.append(request)
        return NS(retcode=self.TRADE_RETCODE_DONE, comment="Request executed", order=777, price=request["price"])
