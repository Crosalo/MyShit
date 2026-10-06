"""Push-Nachrichten ueber ntfy.sh (Topic aus NTFY_TOPIC). Fehler beim Senden brechen nie den Run ab."""
import logging
import os

import requests

log = logging.getLogger(__name__)


def notify(cfg: dict, title: str, message: str, priority: int = 3, tags: list[str] | None = None,
           click: str | None = None) -> bool:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        log.info("NTFY_TOPIC nicht gesetzt - keine Push-Nachricht")
        return False
    body = {"topic": topic, "title": title, "message": message, "priority": priority, "tags": tags or []}
    if click:
        body["click"] = click
    try:  # JSON-Variante: Umlaute/Emojis im Titel sind hier problemlos
        r = requests.post(cfg["ntfy"]["server"], json=body, timeout=15)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning("ntfy fehlgeschlagen: %s", type(e).__name__)
        return False
