"""Positionsgröße und Tages-Verlustgrenze."""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SymbolSpec:
    name: str
    point: float
    digits: int
    tick_size: float
    tick_value: float  # Kontowährung pro Tick pro 1 Lot (Verlustseite)
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level: int = 0  # in Points


@dataclass
class SizeResult:
    lots: float
    risk_money: float
    risk_pct: float
    reason: str = ""


def _step_decimals(step: float) -> int:
    return max(0, -int(math.floor(math.log10(step)))) if step < 1 else 0


def position_size(
    equity: float,
    risk_pct: float,
    sl_distance: float,
    spec: SymbolSpec,
    commission_per_lot: float = 0.0,
) -> SizeResult:
    """Lots so, dass Stop + Kommission höchstens risk_pct % der Equity kosten.

    Rundet IMMER ab. Liegt das Ergebnis unter dem Mindestlot, wird NICHT
    aufgerundet, sondern der Trade abgelehnt.
    """
    if equity <= 0 or sl_distance <= 0:
        return SizeResult(0.0, 0.0, 0.0, "ungültige Equity oder Stop-Abstand")
    loss_per_lot = sl_distance / spec.tick_size * spec.tick_value + commission_per_lot
    budget = equity * risk_pct / 100
    raw = budget / loss_per_lot
    steps = math.floor(raw / spec.volume_step + 1e-9)
    lots = round(steps * spec.volume_step, _step_decimals(spec.volume_step))
    lots = min(lots, spec.volume_max)
    if lots < spec.volume_min:
        min_risk = spec.volume_min * loss_per_lot
        return SizeResult(
            0.0,
            0.0,
            0.0,
            f"Mindestlot {spec.volume_min} würde {min_risk:.2f} riskieren "
            f"= {min_risk / equity * 100:.1f}% des Kontos (Limit {risk_pct}%)",
        )
    risk_money = lots * loss_per_lot
    return SizeResult(lots, risk_money, risk_money / equity * 100)


@dataclass
class DailyGuard:
    """Tagesbuchhaltung (UTC-Tag), überlebt Neustarts über eine JSON-Datei."""

    max_daily_loss_pct: float
    max_trades_per_day: int
    state_file: Path | None = None
    day: str = ""
    start_equity: float = 0.0
    trades: int = 0
    halted: bool = False
    halt_reason: str = ""
    manual_stop: bool = False
    _loaded: bool = field(default=False, repr=False)

    def load(self):
        if self.state_file and Path(self.state_file).exists():
            data = json.loads(Path(self.state_file).read_text(encoding="utf-8"))
            for key in ("day", "start_equity", "trades", "halted", "halt_reason", "manual_stop"):
                if key in data:
                    setattr(self, key, data[key])
        self._loaded = True

    def save(self):
        if not self.state_file:
            return
        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "day": self.day,
            "start_equity": self.start_equity,
            "trades": self.trades,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "manual_stop": self.manual_stop,
        }
        Path(self.state_file).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def roll_day(self, day: str, equity: float) -> bool:
        """Neuer Tag -> Zähler zurücksetzen. Manueller Stopp bleibt bestehen."""
        if not self._loaded:
            self.load()
        if day == self.day:
            return False
        self.day = day
        self.start_equity = equity
        self.trades = 0
        self.halted = False
        self.halt_reason = ""
        self.save()
        return True

    def loss_breached(self, equity: float) -> bool:
        if self.start_equity <= 0:
            return False
        loss_pct = (self.start_equity - equity) / self.start_equity * 100
        return loss_pct >= self.max_daily_loss_pct

    def halt(self, reason: str):
        self.halted = True
        self.halt_reason = reason
        self.save()

    def can_open(self) -> tuple[bool, str]:
        if self.manual_stop:
            return False, "manuell gestoppt"
        if self.halted:
            return False, self.halt_reason or "für heute gestoppt"
        if self.trades >= self.max_trades_per_day:
            return False, f"max. {self.max_trades_per_day} Trades/Tag erreicht"
        return True, ""

    def record_trade(self):
        self.trades += 1
        self.save()
