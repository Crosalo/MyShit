"""Dexscreener integration for token search."""
import requests
from typing import List, Dict, Any

from .config import CONFIG


def search_token(query: str) -> List[Dict[str, Any]]:
    """Search tokens on Dexscreener by query string."""
    if CONFIG is None:
        raise RuntimeError("CONFIG not loaded")
    url = f"{CONFIG.dex_api_base}/search?q={query}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("pairs", [])
