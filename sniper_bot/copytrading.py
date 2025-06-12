"""Simple copy trading management."""
from typing import Dict, Callable


class CopyTradingManager:
    def __init__(self) -> None:
        # mapping of user_id -> trader address
        self.copies: Dict[int, str] = {}
        # hook for executing trades when the target performs them
        self.on_trade: Callable[[str, str, float], None] | None = None

    def start_copy(self, user_id: int, trader: str) -> None:
        self.copies[user_id] = trader

    def stop_copy(self, user_id: int) -> None:
        self.copies.pop(user_id, None)

    def handle_external_trade(self, trader: str, token: str, amount: float) -> None:
        """Trigger trade for all users copying the given trader."""
        if self.on_trade is None:
            return
        for user, target in self.copies.items():
            if target == trader:
                self.on_trade(token, trader, amount)
