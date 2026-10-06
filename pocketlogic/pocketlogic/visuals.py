"""Stufe 4: Szenen-Timing, Pixabay-Clips (mit Cache) und Fallback-Karten."""
import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from PIL import Image

from . import cards
from .render import ffmpeg
from .runlog import published, read_log, recent

log = logging.getLogger(__name__)
API = "https://pixabay.com/api/videos/"

# Woerter, die in Suchanfragen nichts ueber den Inhalt sagen (Pixabay matcht sie trotzdem)
GENERIC = {"close", "up", "closeup", "slow", "motion", "time", "lapse", "timelapse", "hand", "hands",
           "person", "people", "man", "woman", "on", "of", "and", "the", "a", "an", "in", "with", "at",
           "to", "from", "shot", "video", "footage", "background", "4k", "hd", "top", "view", "detail"}


def _stem(w: str) -> str:
    w = w.lower()
    for suf in ("ing", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def key_words(query: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-zA-Z]+", query) if w.lower() not in GENERIC]


def relevant(query: str, tags: str, min_ratio: float = 0.5) -> bool:
    """Mindestens die Haelfte der Kernwoerter der Suche muss in den Clip-Tags vorkommen."""
    keys = set(key_words(query))
    if not keys:
        return True
    tag_words = {_stem(w) for w in re.findall(r"[a-zA-Z]+", tags)}
    return len(keys & tag_words) / len(keys) >= min_ratio


def scene_timings(scenes: list[dict], words: list[dict], audio_dur: float, tail: float) -> list[tuple[float, float]]:
    """Verteilt die Szenen auf die Wortzeitmarken (anteilig nach Wortzahl, an Wortgrenzen ausgerichtet)."""
    counts = [max(1, len(s["text"].split())) for s in scenes]
    total = sum(counts)
    starts, acc = [], 0
    for c in counts:
        idx = min(len(words) - 1, round(acc / total * len(words)))
        starts.append(0.0 if acc == 0 else words[idx]["start"])
        acc += c
    ends = starts[1:] + [audio_dur + tail]
    return [(round(s, 3), round(e, 3)) for s, e in zip(starts, ends)]


class Pixabay:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.key = os.environ.get("PIXABAY_API_KEY")
        if not self.key:
            raise RuntimeError("PIXABAY_API_KEY fehlt in der .env")
        self.cache = Path(cfg["paths"]["cache_dir"]) / "pixabay"
        (self.cache / "api").mkdir(parents=True, exist_ok=True)
        (self.cache / "clips").mkdir(parents=True, exist_ok=True)

    def search(self, query: str) -> list[dict]:
        """Suche mit 24-h-Cache (Pixabay-Vorgabe) und Rate-Limit-Pause."""
        v = self.cfg["visuals"]
        f = self.cache / "api" / (hashlib.sha1(query.lower().encode()).hexdigest() + ".json")
        if f.exists() and time.time() - f.stat().st_mtime < v["api_cache_hours"] * 3600:
            return json.loads(f.read_text())
        params = {"key": self.key, "q": query[:100], "per_page": v["per_page"], "safesearch": "true"}
        for attempt in range(4):
            time.sleep(v["request_pause_s"])
            try:
                r = requests.get(API, params=params, timeout=20)
            except requests.RequestException as e:
                log.warning("Pixabay-Netzwerkfehler (%s), neuer Versuch", type(e).__name__)
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429:
                wait = int(r.headers.get("X-RateLimit-Reset", 30))
                log.warning("Pixabay-Rate-Limit, warte %ss", wait)
                time.sleep(wait)
                continue
            if not r.ok:  # Key nie loggen: nur Statuscode ausgeben
                raise RuntimeError(f"Pixabay HTTP {r.status_code}")
            hits = r.json().get("hits", [])
            f.write_text(json.dumps(hits))
            return hits
        raise RuntimeError("Pixabay nicht erreichbar")

    def pick(self, query: str, hits: list[dict], need: float, exclude: set[int]) -> dict | None:
        """Bester Clip: thematisch passend (Tags), Hochformat bevorzugt, lang und scharf genug, neu."""
        v = self.cfg["visuals"]
        best, best_score = None, -1e9
        for rank, h in enumerate(hits):
            if h["id"] in exclude or not relevant(query, h.get("tags", "")):
                continue
            variants = [x for x in h.get("videos", {}).values()
                        if x.get("url") and x.get("height", 0) >= v["min_height"]
                        and x.get("size", 0) <= v["max_download_mb"] * 1024 * 1024]
            if not variants:
                continue
            vertical = variants[0]["height"] > variants[0]["width"]
            # kleinste Variante, die nach dem Zuschnitt noch ~1920 px hoch ist; sonst die groesste
            enough = [x for x in variants if x["height"] >= 1920]
            var = min(enough, key=lambda x: x["size"]) if enough else max(variants, key=lambda x: x["height"])
            score = (100 if vertical else 0) + (20 if var["height"] >= 1920 else 0) \
                + (10 if h.get("duration", 0) >= need else 0) - rank
            if score > best_score:
                best, best_score = {"id": h["id"], "url": var["url"], "duration": h.get("duration", 0),
                                    "width": var["width"], "height": var["height"]}, score
        return best

    def download(self, clip: dict) -> Path:
        out = self.cache / "clips" / f"{clip['id']}_{clip['height']}.mp4"
        if out.exists() and out.stat().st_size > 0:
            return out
        tmp = out.with_suffix(".part")
        for attempt in range(3):
            try:
                with requests.get(clip["url"], stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(tmp, "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
                tmp.rename(out)
                return out
            except requests.RequestException as e:
                log.warning("Download %s fehlgeschlagen (%s), Versuch %d", clip["id"], type(e).__name__, attempt + 1)
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Clip {clip['id']} nicht ladbar")


def used_clip_ids(cfg: dict) -> set[int]:
    entries = published(recent(read_log(cfg["paths"]["run_log"]), cfg["content"]["no_repeat_days"]))
    return {cid for e in entries for cid in (e.get("clip_ids") or [])}


def build_visuals(cfg: dict, topic: dict, script: dict, tts: dict, words: list[dict], run: Path) -> dict:
    out = run / "visuals"
    out.mkdir(parents=True, exist_ok=True)
    times = scene_timings(script["scenes"], words, tts["duration"], cfg["render"]["tail_s"])
    try:
        px = Pixabay(cfg)
    except RuntimeError as e:
        log.warning("%s - nutze nur eigene Karten", e)
        px = None
    exclude = used_clip_ids(cfg)
    scenes = []
    for i, (scene, (start, end)) in enumerate(zip(script["scenes"], times)):
        need = end - start
        clip = None
        if px:
            # erst die Begriffe von Claude, dann verkuerzte Kernwort-Suchen
            terms = list(scene["search_terms"])
            terms += [" ".join(key_words(t)[:2]) for t in scene["search_terms"] if len(key_words(t)) > 2]
            for term in terms:
                try:
                    clip = px.pick(term, px.search(term), need, exclude)
                except RuntimeError as e:
                    log.warning("Szene %d, Suche '%s': %s", i + 1, term, e)
                if clip:
                    break
        item = {"index": i, "start": start, "end": end, "duration": round(need, 3)}
        if clip:
            try:
                item.update(type="clip", path=str(px.download(clip)), clip_id=clip["id"])
                exclude.add(clip["id"])
            except RuntimeError as e:
                log.warning("%s - Fallback auf Karte", e)
                clip = None
        if clip:
            # Overlay: Szene 1 zeigt den Punch-Text (wie das Thumbnail), sonst optional card_text
            if i == 0:
                ov = cards.punch_overlay(cfg, script["thumb_text"], script["thumb_highlight"], topic["format"])
            elif scene.get("card_text"):
                ov = cards.fact_overlay(cfg, scene["card_text"])
            else:
                ov = cards.watermark(cfg)
            item["overlay"] = str(out / f"overlay_{i:02d}.png")
            ov.save(item["overlay"])
        else:
            if i == 0:
                card = cards.thumbnail(cfg, script["thumb_text"], script["thumb_highlight"])
            else:
                card = cards.full_card(cfg, scene.get("card_text") or scene["text"])
            item.update(type="card", path=str(out / f"card_{i:02d}.png"))
            card.save(item["path"])
        log.info("Szene %d: %s %.1fs%s", i + 1, item["type"], need,
                 f" (Pixabay {item.get('clip_id')})" if item["type"] == "clip" else "")
        scenes.append(item)

    # Thumbnail: Frame aus dem ersten Clip als Hintergrund + Punch-Text
    frame = None
    first_clip = next((sc for sc in scenes if sc["type"] == "clip"), None)
    if first_clip:
        jpg = out / "thumb_frame.jpg"
        try:
            ffmpeg(["-ss", "1", "-i", first_clip["path"], "-frames:v", "1", str(jpg)])
            frame = Image.open(jpg)
        except (RuntimeError, OSError) as e:
            log.warning("Thumbnail-Frame nicht extrahierbar: %s", e)
    thumb = run / "thumbnail.png"
    cards.thumbnail(cfg, script["thumb_text"], script["thumb_highlight"], frame).save(thumb)
    return {"scenes": scenes, "thumbnail": str(thumb),
            "clip_ids": [s["clip_id"] for s in scenes if s["type"] == "clip"]}
