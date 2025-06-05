import requests

DEX_API = 'https://api.dexscreener.io/latest/dex/tokens/'


def get_new_listings() -> list:
    """Return a list of recently listed token addresses."""
    url = f"{DEX_API}new"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return [item.get('address') for item in data.get('tokens', [])]

def check_token(token_address: str):
    """Fetch token data from Dexscreener."""
    url = f"{DEX_API}{token_address}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
