import requests

DEX_API = 'https://api.dexscreener.com/latest/dex/'


def get_new_listings() -> list:
    """Return a list of recently listed token addresses."""
    url = f"{DEX_API}tokens/new"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        data = response.json()
    except Exception as err:
        print('Failed to fetch new listings:', err)
        return []

    tokens = []
    if isinstance(data.get('tokens'), list):
        tokens = [item.get('address') for item in data.get('tokens', [])]
    elif isinstance(data.get('pairs'), list):
        for pair in data['pairs']:
            base = pair.get('baseToken') or {}
            addr = base.get('address')
            if addr:
                tokens.append(addr)
    return tokens

def check_token(token_address: str):
    """Fetch token data from Dexscreener."""
    url = f"{DEX_API}tokens/{token_address}"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.json()
