from dataclasses import dataclass
import os

@dataclass
class Config:
    WEB3_PROVIDER: str = os.getenv('WEB3_PROVIDER', 'http://127.0.0.1:8545')
    PRIVATE_KEY: str = os.getenv('PRIVATE_KEY', 'YOUR_PRIVATE_KEY')
    DEX_API_URL: str = os.getenv('DEX_API_URL',
                                 'https://api.dexscreener.com/latest/dex/')
    # Default to Uniswap V2 router address
    ROUTER_ADDRESS: str = os.getenv('ROUTER_ADDRESS', '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')
    # WETH token address for swapping to/from ETH
    WETH_ADDRESS: str = os.getenv('WETH_ADDRESS', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    TRADE_AMOUNT_ETH: float = float(os.getenv('TRADE_AMOUNT_ETH', '0.01'))
    HOLD_SECONDS: int = int(os.getenv('HOLD_SECONDS', '60'))
    GAS_PRICE_GWEI: int = int(os.getenv('GAS_PRICE_GWEI', '10'))

config = Config()
