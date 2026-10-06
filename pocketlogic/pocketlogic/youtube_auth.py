"""Einmaliger Google-Login (OAuth 2.0, Desktop-Client mit PKCE) und automatische Token-Erneuerung.

Ablauf ohne Bildschirm auf dem Server:
  1. python -m pocketlogic.youtube_auth client client_secret_XXX.json   # Client-ID/Secret in .env
  2. python -m pocketlogic.youtube_auth url        # Link ausgeben, im eigenen Browser oeffnen
  3. Nach "Zulassen" landet der Browser auf http://localhost:8765/?code=... (Seite laedt nicht - ok).
     python -m pocketlogic.youtube_auth code "<komplette Adresse>"
  4. python -m pocketlogic.youtube_auth test       # zeigt den verbundenen Kanal
"""
import base64
import hashlib
import json
import os
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from .config import ROOT, load_config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]
REDIRECT = "http://localhost:8765"  # Loopback-Adresse: fuer Desktop-Clients ohne Registrierung erlaubt
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class AuthError(RuntimeError):
    pass


def _paths(cfg: dict) -> tuple[Path, Path]:
    d = Path(cfg["paths"]["data_dir"])
    d.mkdir(parents=True, exist_ok=True)
    return d / "youtube_token.json", d / "oauth_pending.json"


def _write_private(path: Path, data: dict) -> None:
    """Datei nur fuer den eigenen Benutzer lesbar (enthaelt Geheimnisse)."""
    path.write_text(json.dumps(data, indent=1))
    os.chmod(path, 0o600)


def _client() -> tuple[str, str]:
    cid, secret = os.environ.get("GOOGLE_CLIENT_ID"), os.environ.get("GOOGLE_CLIENT_SECRET")
    if not cid or not secret:
        raise AuthError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET fehlen in der .env")
    return cid, secret


def import_client(json_path: str) -> None:
    """Uebernimmt Client-ID und Secret aus der heruntergeladenen JSON in die .env."""
    data = json.loads(Path(json_path).read_text())
    inst = data.get("installed") or data.get("web")
    if not inst:
        raise AuthError("unbekanntes JSON-Format (erwartet 'installed' = Desktop-App)")
    env = ROOT / ".env"
    lines = [ln for ln in (env.read_text().splitlines() if env.exists() else [])
             if not ln.startswith(("GOOGLE_CLIENT_ID=", "GOOGLE_CLIENT_SECRET="))]
    lines += [f"GOOGLE_CLIENT_ID={inst['client_id']}", f"GOOGLE_CLIENT_SECRET={inst['client_secret']}"]
    env.write_text("\n".join(lines) + "\n")
    os.chmod(env, 0o600)


def login_url(cfg: dict) -> str:
    cid, _ = _client()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    _write_private(_paths(cfg)[1], {"verifier": verifier, "state": state, "created": time.time()})
    return AUTH_URL + "?" + urlencode({
        "client_id": cid, "redirect_uri": REDIRECT, "response_type": "code", "scope": " ".join(SCOPES),
        "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})


def finish_login(cfg: dict, redirect_url: str) -> None:
    """Tauscht den Code aus der Weiterleitungs-Adresse gegen ein dauerhaftes Refresh-Token."""
    token_file, pending_file = _paths(cfg)
    if not pending_file.exists():
        raise AuthError("zuerst 'url' ausfuehren")
    pending = json.loads(pending_file.read_text())
    q = parse_qs(urlparse(redirect_url.strip()).query)
    if "error" in q:
        raise AuthError(f"Google meldet: {q['error'][0]}")
    if q.get("state", [""])[0] != pending["state"]:
        raise AuthError("state passt nicht - bitte mit einem neuen Link wiederholen")
    cid, secret = _client()
    r = requests.post(TOKEN_URL, timeout=30, data={
        "code": q["code"][0], "client_id": cid, "client_secret": secret, "redirect_uri": REDIRECT,
        "grant_type": "authorization_code", "code_verifier": pending["verifier"]})
    if not r.ok:
        raise AuthError(f"Token-Tausch fehlgeschlagen: HTTP {r.status_code} {r.json().get('error', '')}")
    tok = r.json()
    if "refresh_token" not in tok:
        raise AuthError("kein Refresh-Token erhalten - Zugriff unter myaccount.google.com/permissions "
                        "entfernen und Login wiederholen")
    _write_private(token_file, {"refresh_token": tok["refresh_token"], "access_token": tok["access_token"],
                                "expires_at": time.time() + tok.get("expires_in", 3600) - 60,
                                "scope": tok.get("scope", "")})
    pending_file.unlink()


def access_token(cfg: dict, force_refresh: bool = False) -> str:
    """Gueltiges Access-Token; erneuert es automatisch mit dem Refresh-Token."""
    token_file, _ = _paths(cfg)
    if not token_file.exists():
        raise AuthError("kein YouTube-Login vorhanden - 'python -m pocketlogic.youtube_auth url' ausfuehren")
    tok = json.loads(token_file.read_text())
    if not force_refresh and tok.get("access_token") and tok.get("expires_at", 0) > time.time():
        return tok["access_token"]
    cid, secret = _client()
    r = requests.post(TOKEN_URL, timeout=30, data={
        "client_id": cid, "client_secret": secret, "refresh_token": tok["refresh_token"],
        "grant_type": "refresh_token"})
    if r.status_code == 400 and r.json().get("error") == "invalid_grant":
        raise AuthError("YouTube-Login abgelaufen oder widerrufen (App im Status 'Testen'?) - Login neu ausfuehren")
    if not r.ok:
        raise AuthError(f"Token-Erneuerung fehlgeschlagen: HTTP {r.status_code}")
    new = r.json()
    tok.update(access_token=new["access_token"], expires_at=time.time() + new.get("expires_in", 3600) - 60)
    _write_private(token_file, tok)
    return tok["access_token"]


def channel_info(cfg: dict) -> dict:
    r = requests.get("https://www.googleapis.com/youtube/v3/channels", timeout=30,
                     params={"part": "snippet", "mine": "true"},
                     headers={"Authorization": f"Bearer {access_token(cfg)}"})
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise AuthError("dieses Google-Konto hat keinen YouTube-Kanal")
    return {"id": items[0]["id"], "title": items[0]["snippet"]["title"]}


def main(argv: list[str]) -> int:
    cfg = load_config()
    cmd = argv[0] if argv else ""
    try:
        if cmd == "client" and len(argv) == 2:
            import_client(argv[1])
            print("Client-ID und Secret in .env gespeichert.")
        elif cmd == "url":
            print("Diesen Link im Browser oeffnen, Kanal waehlen, zulassen:\n")
            print(login_url(cfg))
            print("\nDanach die komplette Adresse aus der Adresszeile kopieren (http://localhost:8765/?...).")
        elif cmd == "code" and len(argv) == 2:
            finish_login(cfg, argv[1])
            print("Login gespeichert. Verbunden mit Kanal:", channel_info(cfg)["title"])
        elif cmd == "test":
            print("Verbunden mit Kanal:", channel_info(cfg)["title"])
        else:
            print(__doc__)
            return 2
    except (AuthError, requests.RequestException) as e:
        print("Fehler:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
