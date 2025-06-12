"""Configuration for the Sniper Bot."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class BotConfig:
    telegram_token: str
    wallet_private_key: str
    wallet_address: str
    dex_api_base: str = "https://api.dexscreener.io/latest/dex"
    uniswap_router_address: str = "0xE592427A0AEce92De3Edee1F18E0157C05861564"  # Example router


CONFIG: Optional[BotConfig] = None


def load_config(token: str, private_key: str, address: str) -> BotConfig:
    global CONFIG
    CONFIG = BotConfig(
        telegram_token=token,
        wallet_private_key=private_key,
        wallet_address=address,
    )
    return CONFIG
