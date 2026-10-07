import copy
from datetime import datetime, timezone
from types import SimpleNamespace as NS


from bot.config import DEFAULTS
from bot.main import TradingBot
from bot.news import Event
from bot.notifier import Notifier
from bot.risk import SymbolSpec
from tests.helpers import append_bars, uptrend_with_pullback

EURUSD = SymbolSpec("EURUSD", 0.00001, 5, 0.00001, 1.0, 0.01, 100.0, 0.01, 0)
WED_NOON = datetime(2026, 1, 7, 12, 0, tzinfo=timezone.utc)


class FakeBroker:
    def __init__(self, equity=1000.0):
        self._equity = equity
        df = uptrend_with_pullback()
        self.df = append_bars(df, [(df["close"].iloc[-1],) * 4])  # laufende (offene) Kerze
        self.sent, self.pos = [], []

    def connect(self):
        return NS(company="Fusion Markets", login=1, equity=self._equity, currency="EUR")

    def is_demo(self):
        return True

    def spec(self, symbol):
        return EURUSD

    def equity(self):
        return self._equity

    def positions(self, symbol=None):
        return [p for p in self.pos if symbol in (None, p.symbol)]

    def close_all(self):
        n = len(self.pos)
        self.pos = []
        return n

    def server_offset_hours(self, symbols):
        return 0

    def rates(self, symbol, tf, count, offset):
        return self.df

    def tick(self, symbol):
        c = self.df["close"].iloc[-1]
        return NS(bid=c, ask=c + 0.000001)

    def build_market_request(self, symbol, side, lots, sl_d, tp_d, spec, comment=""):
        price = self.tick(symbol).ask
        return {"symbol": symbol, "volume": lots, "price": price, "sl": price - sl_d, "tp": price + tp_d}

    def send(self, request):
        self.sent.append(request)
        self.pos.append(NS(symbol=request["symbol"], type=0, volume=request["volume"], profit=0.0))
        return NS(price=request["price"], order=1)


class FakeNews:
    def __init__(self, block=None):
        self.block = block

    def refresh(self):
        pass

    def blocking_event(self, symbol, now):
        return self.block

    def upcoming(self, now, hours):
        return []


def make_bot(tmp_path, broker=None, news=None, now=WED_NOON):
    cfg = copy.deepcopy(DEFAULTS)
    cfg["symbols"] = ["EURUSD"]
    cfg["state_dir"] = str(tmp_path / "state")
    cfg["log_dir"] = str(tmp_path / "logs")
    (tmp_path / "logs").mkdir()
    clock = NS(now=now)
    bot = TradingBot(cfg, broker or FakeBroker(), Notifier(False), news or FakeNews(), clock=lambda: clock.now)
    bot.startup()
    return bot, clock


def test_opens_one_trade_per_signal_bar(tmp_path):
    bot, _ = make_bot(tmp_path)
    bot.step()
    bot.step()  # gleiche Kerze -> kein zweiter Trade
    assert len(bot.broker.sent) == 1
    assert bot.guard.trades == 1
    assert (tmp_path / "logs" / "trades.csv").exists()


def test_news_block_prevents_trade(tmp_path):
    ev = Event(WED_NOON, "USD", "High", "CPI m/m")
    bot, _ = make_bot(tmp_path, news=FakeNews(block=ev))
    bot.step()
    assert bot.broker.sent == []


def test_tiny_account_sends_no_order(tmp_path):
    bot, _ = make_bot(tmp_path, broker=FakeBroker(equity=19.0))
    bot.step()
    assert bot.broker.sent == []


def test_kill_file_closes_and_blocks(tmp_path):
    bot, _ = make_bot(tmp_path)
    bot.broker.pos.append(NS(symbol="GBPUSD", type=0, volume=0.01, profit=0.0))
    bot.kill_file.parent.mkdir(parents=True, exist_ok=True)
    bot.kill_file.touch()
    bot.step()
    assert bot.broker.pos == [] and bot.broker.sent == []


def test_daily_loss_limit_closes_and_halts(tmp_path):
    broker = FakeBroker()
    bot, _ = make_bot(tmp_path, broker=broker)
    bot.guard.roll_day(WED_NOON.date().isoformat(), 1000.0)
    broker.pos.append(NS(symbol="GBPUSD", type=0, volume=0.01, profit=-40.0))
    broker._equity = 960.0  # -4 % > 3 % Limit
    bot.step()
    assert broker.pos == [] and broker.sent == []
    assert bot.guard.halted


def test_positions_closed_at_session_end(tmp_path):
    bot, clock = make_bot(tmp_path, now=datetime(2026, 1, 7, 20, 50, tzinfo=timezone.utc))
    bot.broker.pos.append(NS(symbol="EURUSD", type=0, volume=0.01, profit=1.0))
    bot.step()
    assert bot.broker.pos == [] and bot.broker.sent == []
