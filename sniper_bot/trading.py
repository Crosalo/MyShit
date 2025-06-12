"""Uniswap trading functions."""
from typing import Any

from web3 import Web3
from uniswap import Uniswap

from .config import CONFIG


class Trader:
    def __init__(self) -> None:
        if CONFIG is None:
            raise RuntimeError("CONFIG not loaded")
        self.web3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR-PROJECT-ID"))
        self.uniswap = Uniswap(
            address=CONFIG.wallet_address,
            private_key=CONFIG.wallet_private_key,
            provider=self.web3,
            version=2,
        )

    def buy_token(self, token_address: str, amount_eth: float) -> Any:
        return self.uniswap.make_trade("ETH", token_address, Web3.toWei(amount_eth, 'ether'))

    def sell_token(self, token_address: str, amount_token: int) -> Any:
        return self.uniswap.make_trade(token_address, "ETH", amount_token)
