"""Testuniversum: alles, was es bei Fusion Markets auch gibt und wofür freie M1-Daten existieren.

Kosten (Fusion Markets Zero-Konto, Annahme): FX und Metalle 4,50 USD Kommission pro Lot
hin+zurück, Indizes und Öl nur Spread. Die Spreads werden aus Dukascopy-Bid/Ask-Daten
gemessen; FALLBACK_SPREAD greift nur, wenn das nicht klappt.
"""
from dataclasses import dataclass

# Grobe Wechselkurse: Einheiten Quote-Währung pro 1 USD (nur zur Kommissions-Umrechnung)
QUOTE_PER_USD = {"USD": 1.0, "JPY": 150.0, "GBP": 0.75, "CHF": 0.80, "CAD": 1.38,
                 "AUD": 1.52, "NZD": 1.70, "EUR": 0.86}


@dataclass(frozen=True)
class Instrument:
    name: str  # Name wie bei MT5/Fusion (Annahme, mit `python -m bot.check --list` prüfen)
    histdata: str
    dukascopy: str
    asset: str  # fx, metal, index, energy
    quote: str
    contract_size: float
    commission_usd: float  # pro Lot hin+zurück
    sessions: tuple  # (Zeitzone, "HH:MM") Markteröffnungen, an denen sich Strategien orientieren
    fallback_spread: float
    commission_price_override: float | None = None  # exakt aus MT5 (tick_value), falls bekannt
    minlot_value_override: float | None = None  # Kontowährung pro 1.0 Preisbewegung beim Mindestlot

    @property
    def commission_price(self) -> float:
        """Kommission ausgedrückt in Preis-Einheiten pro gehandelter Einheit."""
        if self.commission_price_override is not None:
            return self.commission_price_override
        return self.commission_usd / self.contract_size * QUOTE_PER_USD.get(self.quote, 1.0)

    def minlot_value(self, usd_to_account: float = 0.86) -> float | None:
        """Wert einer Preisbewegung von 1.0 beim Mindestlot (0,01) in Kontowährung (None = unbekannt)."""
        if self.minlot_value_override is not None:
            return self.minlot_value_override
        if self.asset == "index":
            return None  # Kontraktgröße der Index-CFDs bei Fusion hier unbekannt
        return 0.01 * self.contract_size / QUOTE_PER_USD.get(self.quote, 1.0) * usd_to_account


LDN = ("Europe/London", "08:00")
NY_FX = ("America/New_York", "08:00")
TKY = ("Asia/Tokyo", "09:00")
NY_CASH = ("America/New_York", "09:30")


def _fx(name, spread, sessions=(LDN, NY_FX)):
    return Instrument(name, name, name, "fx", name[3:], 100_000, 4.5, sessions, spread)


UNIVERSE = [
    _fx("EURUSD", 0.00002), _fx("GBPUSD", 0.00004), _fx("USDJPY", 0.003, (TKY, LDN, NY_FX)),
    _fx("USDCHF", 0.00004), _fx("USDCAD", 0.00004), _fx("AUDUSD", 0.00003, (TKY, LDN, NY_FX)),
    _fx("NZDUSD", 0.00005, (TKY, LDN, NY_FX)), _fx("EURGBP", 0.00004, (LDN,)),
    _fx("EURJPY", 0.006, (TKY, LDN)), _fx("GBPJPY", 0.010, (TKY, LDN)),
    _fx("EURCHF", 0.00006, (LDN,)), _fx("AUDJPY", 0.006, (TKY, LDN)),
    _fx("EURAUD", 0.00008, (TKY, LDN)), _fx("GBPCHF", 0.00010, (LDN,)),
    _fx("AUDNZD", 0.00008, (TKY,)), _fx("CADJPY", 0.008, (TKY, NY_FX)),
    _fx("EURCAD", 0.00008, (LDN, NY_FX)), _fx("GBPAUD", 0.00010, (TKY, LDN)),
    _fx("AUDCAD", 0.00006, (TKY, NY_FX)), _fx("NZDJPY", 0.008, (TKY,)),
    _fx("CHFJPY", 0.010, (TKY, LDN)),
    Instrument("XAUUSD", "XAUUSD", "XAUUSD", "metal", "USD", 100, 4.5,
               (LDN, ("America/New_York", "08:30")), 0.12),
    Instrument("XAGUSD", "XAGUSD", "XAGUSD", "metal", "USD", 5000, 4.5,
               (LDN, ("America/New_York", "08:30")), 0.015),
    Instrument("US500", "SPXUSD", "USA500IDXUSD", "index", "USD", 1, 0.0, (NY_CASH,), 0.5),
    Instrument("US100", "NSXUSD", "USATECHIDXUSD", "index", "USD", 1, 0.0, (NY_CASH,), 1.5),
    Instrument("GER40", "GRXEUR", "DEUIDXEUR", "index", "EUR", 1, 0.0, (("Europe/Berlin", "09:00"),), 1.5),
    Instrument("UK100", "UKXGBP", "GBRIDXGBP", "index", "GBP", 1, 0.0, (LDN,), 1.0),
    Instrument("JPN225", "JPXJPY", "JPNIDXJPY", "index", "JPY", 1, 0.0, (TKY,), 8.0),
    Instrument("WTI", "WTIUSD", "LIGHTCMDUSD", "energy", "USD", 1000, 0.0, (("America/New_York", "09:00"),), 0.03),
    Instrument("BRENT", "BCOUSD", "BRENTCMDUSD", "energy", "USD", 1000, 0.0, (LDN, ("America/New_York", "09:00")), 0.03),
]
BY_NAME = {i.name: i for i in UNIVERSE}
