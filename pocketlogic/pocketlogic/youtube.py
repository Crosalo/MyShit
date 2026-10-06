"""Stufe 7: Upload zu YouTube (Data API v3, resumable) mit geplanter Veroeffentlichung."""
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from .youtube_auth import access_token

log = logging.getLogger(__name__)
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
API = "https://www.googleapis.com/youtube/v3"
RETRY_STATUS = {500, 502, 503, 504}


class UploadError(RuntimeError):
    pass


def next_publish_time(cfg: dict, now: datetime | None = None, lead_minutes: int = 30) -> datetime:
    """Naechster Termin um publish_time in publish_tz (z. B. 15:00 New York), mindestens lead_minutes
    in der Zukunft. zoneinfo beruecksichtigt Sommer-/Winterzeit automatisch."""
    sch = cfg["schedule"]
    tz = ZoneInfo(sch["publish_tz"])
    now = (now or datetime.now(timezone.utc)).astimezone(tz)
    hh, mm = map(int, sch["publish_time"].split(":"))
    slot = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if slot < now + timedelta(minutes=lead_minutes):
        slot = (slot + timedelta(days=1)).replace(hour=hh, minute=mm)  # replace: DST-sicher
    return slot.astimezone(timezone.utc)


def _clean(text: str) -> str:
    return text.replace("<", "").replace(">", "")  # YouTube lehnt spitze Klammern ab


def build_metadata(cfg: dict, script: dict, publish_at: datetime, sources: list[str]) -> dict:
    up, ch = cfg["upload"], cfg["channel"]
    desc = _clean(script["description"])
    if up.get("credits") and sources:
        names = " & ".join(s.capitalize() for s in sources)
        desc += f"\n\nFootage: {names}"
    tags, total = [], 0
    for t in script.get("tags", []):  # Tags zusammen hoechstens ~500 Zeichen
        t = _clean(t).strip()
        if t and total + len(t) + 2 <= 480:
            tags.append(t)
            total += len(t) + 2
    status = {"privacyStatus": up["privacy"], "selfDeclaredMadeForKids": ch["made_for_kids"],
              "embeddable": True}
    if up["privacy"] == "private" and publish_at:
        status["publishAt"] = publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    if up.get("ai_disclosure"):
        status["containsSyntheticMedia"] = True
    return {"snippet": {"title": _clean(script["title"])[:100], "description": desc[:4900], "tags": tags,
                        "categoryId": str(ch["youtube_category"]), "defaultLanguage": ch["language"],
                        "defaultAudioLanguage": ch["language"]},
            "status": status}


def _headers(cfg: dict, refresh: bool = False, **extra) -> dict:
    return {"Authorization": f"Bearer {access_token(cfg, force_refresh=refresh)}", **extra}


def _api_error(r: requests.Response) -> str:
    try:
        err = r.json()["error"]
        reason = (err.get("errors") or [{}])[0].get("reason", "")
        return f"HTTP {r.status_code} {reason}: {err.get('message', '')}"[:300]
    except (ValueError, KeyError):
        return f"HTTP {r.status_code}"


def _start_session(cfg: dict, meta: dict, size: int) -> tuple[str, dict]:
    """Startet die resumable Session. Kennt die API ein Statusfeld nicht, wird es weggelassen."""
    refresh = False
    for attempt in range(5):
        r = requests.post(UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
                          json=meta, timeout=60,
                          headers=_headers(cfg, refresh=refresh, **{"X-Upload-Content-Length": str(size),
                                                                    "X-Upload-Content-Type": "video/mp4"}))
        refresh = False
        if r.ok and r.headers.get("Location"):
            return r.headers["Location"], meta
        msg = _api_error(r)
        if r.status_code == 400 and "containsSyntheticMedia" in r.text:
            log.warning("API kennt containsSyntheticMedia nicht - KI-Kennzeichnung bitte in YouTube Studio setzen")
            meta = {**meta, "status": {k: v for k, v in meta["status"].items() if k != "containsSyntheticMedia"}}
        elif r.status_code == 401:
            refresh = True  # naechster Versuch mit frisch erneuertem Token
        elif "quotaExceeded" in msg or "uploadLimitExceeded" in msg:
            raise UploadError(f"YouTube-Kontingent erschoepft: {msg}")
        elif r.status_code in RETRY_STATUS:
            time.sleep(2 ** attempt * 3)
        else:
            raise UploadError(f"Upload-Start abgelehnt: {msg}")
    raise UploadError("Upload-Session konnte nicht gestartet werden")


def _resume_offset(session: str, size: int, cfg: dict) -> int | dict:
    """Fragt ab, wie viele Bytes schon angekommen sind (oder ob der Upload fertig ist)."""
    r = requests.put(session, timeout=60, headers=_headers(cfg, **{"Content-Range": f"bytes */{size}",
                                                                   "Content-Length": "0"}))
    if r.status_code in (200, 201):
        return r.json()
    if r.status_code == 308:
        rng = r.headers.get("Range")
        return int(rng.split("-")[1]) + 1 if rng else 0
    raise UploadError(f"Upload-Status unklar: {_api_error(r)}")


def upload_video(cfg: dict, video: Path, meta: dict) -> tuple[dict, dict]:
    """Resumable Upload in Bloecken; bei Netzfehlern wird an der letzten Position fortgesetzt."""
    size = video.stat().st_size
    chunk = cfg["upload"]["chunk_mb"] * 1024 * 1024  # Vielfaches von 256 KiB
    session, meta = _start_session(cfg, meta, size)
    offset, failures = 0, 0
    with open(video, "rb") as f:
        while True:
            f.seek(offset)
            data = f.read(chunk)
            end = offset + len(data) - 1
            try:
                r = requests.put(session, data=data, timeout=300, headers=_headers(
                    cfg, **{"Content-Length": str(len(data)), "Content-Range": f"bytes {offset}-{end}/{size}"}))
            except requests.RequestException as e:
                r = None
                log.warning("Netzwerkfehler beim Upload (%s)", type(e).__name__)
            if r is not None and r.status_code in (200, 201):
                return r.json(), meta
            if r is not None and r.status_code == 308:
                rng = r.headers.get("Range")
                offset = int(rng.split("-")[1]) + 1 if rng else 0
                failures = 0
                log.info("Upload %d%%", offset * 100 // size)
                continue
            if r is not None and r.status_code not in RETRY_STATUS | {401}:
                raise UploadError(f"Upload abgebrochen: {_api_error(r)}")
            failures += 1
            if failures > 8:
                raise UploadError("Upload nach 8 Fehlversuchen abgebrochen")
            time.sleep(min(60, 2 ** failures))
            pos = _resume_offset(session, size, cfg)
            if isinstance(pos, dict):
                return pos, meta
            offset = pos


def video_status(cfg: dict, video_id: str) -> dict:
    r = requests.get(f"{API}/videos", timeout=30, params={"part": "status", "id": video_id},
                     headers=_headers(cfg))
    r.raise_for_status()
    items = r.json().get("items", [])
    return items[0]["status"] if items else {}


def set_thumbnail(cfg: dict, video_id: str, image: Path) -> bool:
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set", timeout=60,
                      params={"videoId": video_id}, data=image.read_bytes(),
                      headers=_headers(cfg, **{"Content-Type": "image/png"}))
    if not r.ok:
        log.warning("Thumbnail nicht gesetzt (%s) - meist fehlt die Telefon-Bestaetigung", _api_error(r))
    return r.ok


def upload_run(cfg: dict, run: Path) -> dict:
    """Laedt das fertige Video eines Runs hoch und prueft, ob es geplant oder privat gesperrt ist."""
    script = json.loads((run / "script.json").read_text())
    visuals = json.loads((run / "visuals.json").read_text())
    sources = sorted({cid.split(":")[0] for cid in visuals.get("clip_ids", []) if ":" in str(cid)})
    publish_at = next_publish_time(cfg)
    meta = build_metadata(cfg, script, publish_at, sources)
    t0 = time.monotonic()
    result, sent = upload_video(cfg, run / "final.mp4", meta)
    vid = result["id"]
    log.info("Hochgeladen: %s (%.0fs)", vid, time.monotonic() - t0)

    if cfg["upload"].get("set_thumbnail"):
        set_thumbnail(cfg, vid, run / "thumbnail.png")
    try:
        st = video_status(cfg, vid)
    except requests.RequestException:
        st = result.get("status", {})
    scheduled = bool(st.get("publishAt")) and cfg["upload"].get("audited")
    return {"video_id": vid, "url": f"https://youtube.com/shorts/{vid}",
            "studio_url": f"https://studio.youtube.com/video/{vid}/edit",
            "publish_at": publish_at.isoformat(), "privacy": st.get("privacyStatus"),
            "scheduled": scheduled, "ai_disclosure_sent": "containsSyntheticMedia" in sent["status"]}
