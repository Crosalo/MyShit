"""Stufe 4: Szenen-Timing, Pixabay-Clips (mit Cache) und Fallback-Karten."""
import hashlib
import json
import logging
import math
import os
import re
import time
from pathlib import Path

import requests
from PIL import Image

from . import cards
from .render import ffmpeg
from .runlog import published, read_log, recent
from .subtitles import find_phrase

log = logging.getLogger(__name__)
API = "https://pixabay.com/api/videos/"

# Woerter, die in Suchanfragen nichts ueber den Inhalt sagen (Pixabay matcht sie trotzdem)
GENERIC = {"close", "up", "closeup", "slow", "motion", "time", "lapse", "timelapse", "hand", "hands",
           "person", "people", "man", "woman", "on", "of", "and", "the", "a", "an", "in", "with", "at",
           "to", "from", "shot", "video", "footage", "background", "4k", "hd", "top", "view", "detail"}


# Clips mit diesen Tags wirken billig oder lenken ab (3D-Figuren, Text-Animationen, KI-Bilder)
BLOCKED_TAGS = {"cartoon", "3d", "animation", "animated", "character", "mascot", "ai generated", "ai",
                "logo", "intro", "text", "letter", "letters", "alphabet", "font", "typography", "title",
                "illustration", "render", "cgi", "abstract", "particles", "skull", "horror", "halloween",
                "zombie", "monster", "demon", "fantasy", "anime", "game", "green screen", "greenscreen",
                "chroma key", "chromakey"}


def blocked(tags: str) -> bool:
    phrases = {t.strip().lower() for t in tags.split(",")}
    words = {w for p in phrases for w in p.split()}
    return bool(BLOCKED_TAGS & (phrases | words))


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


class StockSource:
    """Gemeinsame Basis: Such-Cache (24 h), Rate-Limit-Behandlung, Vorschaubilder, Downloads."""
    name = "stock"

    def __init__(self, cfg: dict, key_env: str):
        self.cfg = cfg
        self.key = os.environ.get(key_env)
        if not self.key:
            raise RuntimeError(f"{key_env} fehlt in der .env")
        self.cache = Path(cfg["paths"]["cache_dir"]) / self.name
        for sub in ("api", "clips", "thumbs"):
            (self.cache / sub).mkdir(parents=True, exist_ok=True)

    def _request(self, query: str) -> requests.Response:
        raise NotImplementedError

    def _parse(self, data: dict) -> list[dict]:
        raise NotImplementedError

    def search(self, query: str) -> list[dict]:
        v = self.cfg["visuals"]
        f = self.cache / "api" / (hashlib.sha1(query.lower().encode()).hexdigest() + ".json")
        if f.exists() and time.time() - f.stat().st_mtime < v["api_cache_hours"] * 3600:
            return json.loads(f.read_text())
        for attempt in range(4):
            time.sleep(v["request_pause_s"])
            try:
                r = self._request(query)
            except requests.RequestException as e:
                log.warning("%s-Netzwerkfehler (%s), neuer Versuch", self.name, type(e).__name__)
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429:
                wait = min(120, int(r.headers.get("X-RateLimit-Reset", r.headers.get("Retry-After", 30))))
                log.warning("%s-Rate-Limit, warte %ss", self.name, wait)
                time.sleep(wait)
                continue
            if not r.ok:  # Key nie loggen: nur Statuscode ausgeben
                raise RuntimeError(f"{self.name} HTTP {r.status_code}")
            hits = self._parse(r.json())
            f.write_text(json.dumps(hits))
            return hits
        raise RuntimeError(f"{self.name} nicht erreichbar")

    def candidates(self, query: str, hits: list[dict], need: float, exclude: set) -> list[dict]:
        """Passende Clips, beste zuerst: Hochformat bevorzugt, lang und scharf genug, neu."""
        v = self.cfg["visuals"]
        scored = []
        for rank, h in enumerate(hits):
            cid = f"{self.name}:{h['id']}"
            if cid in exclude or h.get("skip") or blocked(h["tags"]):
                continue
            if h.get("check_tags", True) and not relevant(query, h["tags"]):
                continue
            variants = [x for x in h["variants"] if x["height"] >= v["min_height"]
                        and x.get("size", 0) <= v["max_download_mb"] * 1024 * 1024]
            if not variants:
                continue
            vertical = h["height"] > h["width"]
            # kleinste Variante, die nach dem Zuschnitt noch ~1920 px hoch ist; sonst die groesste
            enough = [x for x in variants if x["height"] >= 1920]
            var = min(enough, key=lambda x: x["height"]) if enough else max(variants, key=lambda x: x["height"])
            score = (100 if vertical else 0) + (20 if var["height"] >= 1920 else 0) \
                + (10 if h["duration"] >= need else 0) - rank
            scored.append((score, {"id": cid, "source": self.name, "url": var["url"], "duration": h["duration"],
                                   "width": var["width"], "height": var["height"], "thumb": h["thumb"],
                                   "tags": h["tags"]}))
        return [c for _, c in sorted(scored, key=lambda x: -x[0])]

    def thumbnail(self, clip: dict) -> Path | None:
        """Vorschaubild fuer den Bildredakteur (gecacht)."""
        if not clip.get("thumb"):
            return None
        out = self.cache / "thumbs" / f"{clip['id'].split(':')[1]}.jpg"
        if out.exists():
            return out
        try:
            r = requests.get(clip["thumb"], timeout=20)
            r.raise_for_status()
            out.write_bytes(r.content)
            return out
        except requests.RequestException:
            return None

    def download(self, clip: dict) -> Path:
        out = self.cache / "clips" / f"{clip['id'].split(':')[1]}_{clip['height']}.mp4"
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


class Pixabay(StockSource):
    name = "pixabay"

    def __init__(self, cfg: dict):
        super().__init__(cfg, "PIXABAY_API_KEY")

    def _request(self, query):
        return requests.get(API, timeout=20, params={
            "key": self.key, "q": query[:100], "per_page": self.cfg["visuals"]["per_page"], "safesearch": "true"})

    def _parse(self, data):
        out = []
        for h in data.get("hits", []):
            vids = h.get("videos", {})
            variants = [{"url": x["url"], "width": x["width"], "height": x["height"], "size": x.get("size", 0)}
                        for x in vids.values() if x.get("url") and x.get("height")]
            if not variants:
                continue
            first = max(variants, key=lambda x: x["height"])
            out.append({"id": h["id"], "tags": h.get("tags", ""), "duration": h.get("duration", 0),
                        "width": first["width"], "height": first["height"], "variants": variants,
                        "thumb": (vids.get("small") or vids.get("tiny") or {}).get("thumbnail"),
                        "skip": bool(h.get("isAiGenerated") or h.get("isLowQuality"))})
        return out


class Pexels(StockSource):
    """Pexels: bessere Suche, viel echtes Hochformat-Material. Keine Tags -> Beschreibung aus der URL."""
    name = "pexels"
    API = "https://api.pexels.com/videos/search"

    def __init__(self, cfg: dict):
        super().__init__(cfg, "PEXELS_API_KEY")

    def _request(self, query):
        return requests.get(self.API, headers={"Authorization": self.key}, timeout=20, params={
            "query": query[:100], "orientation": "portrait", "per_page": self.cfg["visuals"]["per_page"]})

    def _parse(self, data):
        out = []
        for v in data.get("videos", []):
            variants = [{"url": f["link"], "width": f["width"], "height": f["height"]}
                        for f in v.get("video_files", [])
                        if f.get("file_type") == "video/mp4" and f.get("height") and f.get("link")]
            if not variants:
                continue
            slug = v.get("url", "").rstrip("/").rsplit("/", 1)[-1]
            desc = ", ".join(w for w in slug.split("-") if not w.isdigit())
            out.append({"id": v["id"], "tags": desc, "duration": v.get("duration", 0),
                        "width": v["width"], "height": v["height"], "variants": variants,
                        "thumb": v.get("image"), "check_tags": False})  # Pexels-Suche ist selbst treffsicher
        return out


class Sources:
    """Alle verfuegbaren Quellen in der Reihenfolge aus der Config (z. B. erst Pexels, dann Pixabay)."""
    TYPES = {"pexels": Pexels, "pixabay": Pixabay}

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.items: list[StockSource] = []
        for name in cfg["visuals"].get("sources", ["pexels", "pixabay"]):
            try:
                self.items.append(self.TYPES[name](cfg))
            except (RuntimeError, KeyError) as e:
                log.warning("Quelle %s nicht verfuegbar: %s", name, e)
        if not self.items:
            raise RuntimeError("keine Stock-Quelle verfuegbar")
        self.by_name = {s.name: s for s in self.items}

    def find(self, query: str, need: float, exclude: set, cap: int) -> list[dict]:
        """Kandidaten aller Quellen zu einem Suchbegriff, je Quelle hoechstens `cap`."""
        found = []
        for src in self.items:
            try:
                found += src.candidates(query, src.search(query), need, exclude)[:cap]
            except RuntimeError as e:
                log.warning("Suche '%s' bei %s: %s", query, src.name, e)
        return found

    def thumbnail(self, clip: dict) -> Path | None:
        return self.by_name[clip["source"]].thumbnail(clip)

    def download(self, clip: dict) -> Path:
        return self.by_name[clip["source"]].download(clip)


def used_clip_ids(cfg: dict) -> set:
    entries = published(recent(read_log(cfg["paths"]["run_log"]), cfg["content"]["no_repeat_days"]))
    return {cid for e in entries for cid in (e.get("clip_ids") or [])}


def split_shots(start: float, end: float, max_shot: float) -> list[tuple[float, float]]:
    """Teilt eine Szene in gleich lange Einstellungen von hoechstens max_shot Sekunden."""
    n = max(1, math.ceil((end - start) / max_shot - 1e-9))
    step = (end - start) / n
    return [(round(start + k * step, 3), round(start + (k + 1) * step, 3)) for k in range(n)]


def gather_candidates(px: Sources, scene: dict, limit: int, need: float, exclude: set,
                      fallback: list[str] | None = None) -> list[dict]:
    """Bis zu `limit` verschiedene Kandidaten: erst Claudes Begriffe, dann Kernwort-Suchen,
    zuletzt allgemeine Geld-Motive (fallback). Pro Begriff und Quelle hoechstens die Haelfte."""
    terms = list(scene["search_terms"])
    terms += [" ".join(key_words(t)[:2]) for t in scene["search_terms"] if len(key_words(t)) > 2]
    terms += fallback or []
    found: list[dict] = []
    cap = max(2, math.ceil(limit / 2))
    for term in terms:
        for c in px.find(term, need, exclude | {f["id"] for f in found}, cap):
            if len(found) < limit and c["id"] not in {f["id"] for f in found}:
                found.append(c)
        if len(found) >= limit:
            break
    return found


def contact_sheet(px: Sources, cands: list[dict], out: Path) -> list[dict]:
    """Nummerierte Vorschaubilder (3x2) fuer den Bildredakteur; liefert die gezeigten Kandidaten."""
    from PIL import ImageDraw  # lokal, wird nur hier gebraucht
    shown = [(c, px.thumbnail(c)) for c in cands]
    shown = [(c, t) for c, t in shown if t]
    cell, cols = 360, 3
    rows = max(1, math.ceil(len(shown) / cols))
    sheet = Image.new("RGB", (cell * cols, cell * rows), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    f = cards.font_any(64)
    for k, (c, t) in enumerate(shown):
        im = Image.open(t).convert("RGB")
        im.thumbnail((cell - 12, cell - 12))
        x, y = (k % cols) * cell, (k // cols) * cell
        sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        d.rectangle([x + 6, y + 6, x + 76, y + 82], fill=(0, 0, 0))
        d.text((x + 20, y + 8), str(k), font=f, fill=(255, 255, 0))
    sheet.save(out, quality=85)
    return [c for c, _ in shown]


def judge_clips(cfg: dict, items: list[dict], judge_dir: Path) -> dict[int, list[int]] | None:
    """Claude (headless, darf nur Dateien lesen) waehlt pro Szene passende Kandidaten aus."""
    from .claude_client import ClaudeError, ask_json
    lines = []
    for it in items:
        if not it["shown"]:
            continue
        lines.append(f'Scene {it["scene"] + 1}: narration "{it["text"]}"'
                     + (f' / on-screen text "{it["card_text"]}"' if it.get("card_text") else "")
                     + f' -> sheet {it["sheet"]} (candidates 0-{len(it["shown"]) - 1}), pick up to {it["need"]}')
    if not lines:
        return {}
    prompt = f"""You are the photo editor of the YouTube Shorts channel "{cfg['channel']['name']}" (everyday money explained).
For each scene, open the contact sheet image file (numbered candidate video stills) with the Read tool and choose
clips for that scene, best first. These are b-roll shots behind a voice-over: a clip does not have to show the
exact sentence. Good: footage that fits the line literally, an obvious visual metaphor, or simply the topic and
mood (money, prices, shopping, cards, people deciding or paying). A solid generic money/shopping shot is better
than nothing. Never pick: cartoons, 3D renders, sci-fi, fantasy, AI-looking art, text or number animations,
green screens, smoking, creepy or clearly unrelated images (nature, sports, beach ...).
Only return an empty list if every candidate is unusable.

{chr(10).join(lines)}

Answer ONLY with JSON: {{"scenes": [{{"scene": 1, "picks": [2, 0]}}, ...]}}"""

    def validate(data):
        out = {}
        for e in data["scenes"]:
            it = next((i for i in items if i["scene"] == int(e["scene"]) - 1), None)
            if it:
                out[it["scene"]] = [p for p in e.get("picks", []) if isinstance(p, int) and 0 <= p < len(it["shown"])]
        return out

    try:
        return ask_json(prompt, cfg, validate=validate, attempts=2,
                        extra_args=["--allowedTools", "Read"], cwd=judge_dir)
    except (ClaudeError, KeyError, TypeError, ValueError) as e:
        log.warning("Bildredakteur fehlgeschlagen (%s) - nutze Tag-Reihenfolge", e)
        return None


def build_visuals(cfg: dict, topic: dict, script: dict, tts: dict, words: list[dict], run: Path) -> dict:
    """Plant die Einstellungen (Shots): Schnitt spaetestens alle max_shot_s, Punch-Bild am Anfang."""
    r = cfg["render"]
    out = run / "visuals"
    out.mkdir(parents=True, exist_ok=True)
    times = scene_timings(script["scenes"], words, tts["duration"], r["tail_s"])
    try:
        px = Sources(cfg)
    except RuntimeError as e:
        log.warning("%s - nutze nur eigene Karten", e)
        px = None
    exclude = used_clip_ids(cfg)

    punch_ov = out / "overlay_punch.png"
    cards.punch_overlay(cfg, script["thumb_text"], script["thumb_highlight"], topic["format"]).save(punch_ov)
    plain_ov = out / "overlay_plain.png"
    cards.watermark(cfg).save(plain_ov)

    # Phase A: Shots planen und Clip-Kandidaten sammeln
    v = cfg["visuals"]
    judge_dir = out / "judge"
    judge_dir.mkdir(exist_ok=True)
    plan, claimed = [], set()  # claimed: Kandidaten frueherer Szenen (jede Szene bekommt eigene)
    for i, (scene, (start, end)) in enumerate(zip(script["scenes"], times)):
        # Szene 1: zuerst das Punch-Bild (kurz), dann normale Shots
        segments = []
        if i == 0 and end - start > r["punch_seconds"] + 0.6:
            segments.append(("punch", start, start + r["punch_seconds"]))
            start += r["punch_seconds"]
        elif i == 0:
            segments.append(("punch", start, end))
            start = end
        if end - start > 0.05:
            segments += [("normal", a, b) for a, b in split_shots(start, end, r["max_shot_s"])]
        fb = v.get("fallback_terms") or []
        fb = fb[i % len(fb):] + fb[:i % len(fb)] if fb else []  # pro Szene andere Reihenfolge
        cands = (gather_candidates(px, scene, v["judge_candidates"], r["max_shot_s"], exclude | claimed, fb)
                 if px else [])
        claimed.update(c["id"] for c in cands)
        item = {"scene": i, "text": scene["text"], "card_text": scene.get("card_text"),
                "segments": segments, "need": len(segments), "cands": cands, "shown": cands}
        if px and v.get("ai_judge") and cands:
            item["sheet"] = f"scene_{i + 1:02d}.jpg"
            item["shown"] = contact_sheet(px, cands, judge_dir / item["sheet"])
        plan.append(item)

    # Phase B: Bildredakteur (Claude schaut die Vorschaubilder an)
    picks = judge_clips(cfg, plan, judge_dir) if px and v.get("ai_judge") else None
    if picks is not None:
        (judge_dir / "picks.json").write_text(json.dumps(picks))

    # Phase C: ausgewaehlte Clips laden
    for item in plan:
        order = picks.get(item["scene"], []) if picks is not None else list(range(len(item["shown"])))
        item["clips"] = []
        for k in order:
            c = item["shown"][k]
            if len(item["clips"]) >= item["need"] or c["id"] in exclude:
                continue
            try:
                item["clips"].append({**c, "path": str(px.download(c))})
                exclude.add(c["id"])
            except RuntimeError as e:
                log.warning("%s", e)
    pool = [c for item in plan for c in item["clips"]]  # Ersatz fuer Szenen ohne passenden Clip

    # Phase D: Shots bauen
    shots, used = [], []
    for item in plan:
        i, scene, segments = item["scene"], script["scenes"][item["scene"]], item["segments"]
        clips, reused = item["clips"], False
        if not clips and pool:
            # akzeptierten Clip einer anderen Szene wiederverwenden, aber an anderer Stelle
            clips, reused = [pool[(i * 2) % len(pool)], pool[(i * 2 + 1) % len(pool)]], True
        used += [c["id"] for c in clips]

        if scene.get("card_text") and i > 0:
            ov = out / f"overlay_{i:02d}.png"
            cards.fact_overlay(cfg, scene["card_text"]).save(ov)
        else:
            ov = plain_ov

        for k, (kind, a, b) in enumerate(segments):
            shot = {"scene": i, "start": a, "end": b, "duration": round(b - a, 3),
                    "slam": kind == "punch", "zoom": "in" if len(shots) % 2 == 0 else "out"}
            if clips:
                c = clips[k % len(clips)]
                # Clip mehrfach noetig (oder aus dem Pool): spaeteren Abschnitt desselben Clips nehmen
                ss = (k // len(clips) + (2 if reused else 0)) * r["max_shot_s"]
                ss = ss % max(1.0, c.get("duration", 0) - (b - a)) if c.get("duration") else 0.0
                shot.update(type="clip", path=c["path"], clip_id=c["id"], ss=round(ss, 2),
                            overlay=str(punch_ov if kind == "punch" else ov))
            else:
                img = out / f"card_{len(shots):02d}.png"
                if kind == "punch":
                    cards.thumbnail(cfg, script["thumb_text"], script["thumb_highlight"]).save(img)
                else:
                    cards.full_card(cfg, scene.get("card_text") or scene["text"]).save(img)
                shot.update(type="card", path=str(img))
            shots.append(shot)
        log.info("Szene %d: %d Shot(s), %d Clip(s) %s%s", i + 1, len(segments), len(clips),
                 [c["id"] for c in clips], " (aus Pool)" if reused else "")

    # Thumbnail: Frame aus dem ersten Clip als Hintergrund + Punch-Text
    frame = None
    first_clip = next((sh for sh in shots if sh["type"] == "clip"), None)
    if first_clip:
        jpg = out / "thumb_frame.jpg"
        try:
            ffmpeg(["-ss", str(first_clip["ss"] + 0.5), "-i", first_clip["path"], "-frames:v", "1", str(jpg)])
            frame = Image.open(jpg)
        except (RuntimeError, OSError) as e:
            log.warning("Thumbnail-Frame nicht extrahierbar: %s", e)
    thumb = run / "thumbnail.png"
    cards.thumbnail(cfg, script["thumb_text"], script["thumb_highlight"], frame).save(thumb)

    # Call-to-Action: Einblendung genau waehrend der CTA-Satz gesprochen wird
    cta = None
    if cfg["cta"]["enabled"] and script.get("cta"):
        total = times[-1][1]
        rng = find_phrase(words, script["cta"])
        if rng is None:
            log.warning("CTA-Satz nicht in den Wortzeitmarken gefunden - nutze die Videomitte")
            rng = (total * 0.45, total * 0.45 + cfg["cta"]["min_seconds"])
        a, b = rng[0], max(rng[1] + 0.25, rng[0] + cfg["cta"]["min_seconds"])
        ov = out / "overlay_cta.png"
        cards.cta_overlay(cfg).save(ov)
        cta = {"start": round(a, 3), "end": round(min(b, total), 3), "overlay": str(ov)}

    scene_starts = [t[0] for t in times]
    return {"shots": shots, "scene_starts": scene_starts, "thumbnail": str(thumb), "cta": cta,
            "clip_ids": list(dict.fromkeys(used))}
