"""Telegram: Meldungen senden und Befehle (/status /stop /resume /flat) empfangen.

Token und Chat-ID kommen aus den Umgebungsvariablen TELEGRAM_TOKEN und
TELEGRAM_CHAT_ID. Befehle werden nur aus genau diesem Chat angenommen.
"""
import logging
import os

import requests

log = logging.getLogger(__name__)
COMMANDS = {"/status", "/stop", "/resume", "/flat"}


class Notifier:
    def __init__(self, enabled: bool, token: str | None = None, chat_id: str | None = None, http=requests):
        self.token = token or os.environ.get("TELEGRAM_TOKEN")
        self.chat_id = str(chat_id or os.environ.get("TELEGRAM_CHAT_ID") or "")
        self.enabled = enabled and bool(self.token) and bool(self.chat_id)
        if enabled and not self.enabled:
            log.warning("Telegram aktiviert, aber TELEGRAM_TOKEN/TELEGRAM_CHAT_ID fehlen")
        self.http = http
        self.offset = None

    def _url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.token}/{method}"

    def send(self, text: str):
        log.info("[Meldung] %s", text)
        if not self.enabled:
            return
        try:
            self.http.post(self._url("sendMessage"), data={"chat_id": self.chat_id, "text": text}, timeout=10)
        except requests.RequestException as exc:
            log.warning("Telegram-Senden fehlgeschlagen: %s", exc)

    def poll_commands(self) -> list[str]:
        if not self.enabled:
            return []
        params = {"timeout": 0}
        if self.offset is not None:
            params["offset"] = self.offset
        try:
            resp = self.http.get(self._url("getUpdates"), params=params, timeout=10)
            updates = resp.json().get("result", [])
        except (requests.RequestException, ValueError) as exc:
            log.warning("Telegram-Abfrage fehlgeschlagen: %s", exc)
            return []
        commands = []
        for upd in updates:
            self.offset = upd["update_id"] + 1
            msg = upd.get("message") or {}
            if str(msg.get("chat", {}).get("id")) != self.chat_id:
                continue
            text = (msg.get("text") or "").strip().split("@")[0].lower()
            if text in COMMANDS:
                commands.append(text)
        return commands
