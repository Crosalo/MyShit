"""Stufe 1: Kategorie + Format per Rotation, Thema von Claude, keine Wiederholung."""
import re

from .claude_client import ask_json
from .runlog import read_log, recent


def _norm(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower())) - {"the", "a", "of", "to", "your", "is", "why", "how", "does", "do"}


def too_similar(topic: str, used: list[str], threshold: float = 0.6) -> bool:
    a = _norm(topic)
    for u in used:
        b = _norm(u)
        if a and b and len(a & b) / min(len(a), len(b)) >= threshold:
            return True
    return False


def pick_rotation(cfg: dict, entries: list[dict]) -> tuple[str, str]:
    """Waehlt die am laengsten nicht genutzte Kategorie/Format; nie dieselbe Kombination zweimal in Folge."""
    cats, fmts = cfg["content"]["categories"], cfg["content"]["formats"]

    def least_recent(options, key):
        last_seen = {o: -1 for o in options}
        for i, e in enumerate(entries):
            if e.get(key) in last_seen:
                last_seen[e[key]] = i
        return sorted(options, key=lambda o: last_seen[o])

    last = entries[-1] if entries else {}
    cat = next((c for c in least_recent(cats, "category") if c != last.get("category")), cats[0])
    fmt = next((f for f in least_recent(fmts, "format") if f != last.get("format")), fmts[0])
    return cat, fmt


def build_prompt(cfg: dict, category: str, fmt: str, used: list[str]) -> str:
    avoid = "\n".join(f"- {u}" for u in used[-60:]) or "- (none yet)"
    return f"""You plan topics for a YouTube Shorts channel "{cfg['channel']['name']}" ({cfg['channel']['tagline']}).
Audience: US/international English speakers interested in everyday money.
Category: {category}
Format: {fmt}

Give 5 topic ideas, best first. Rules:
- Real informational value, 100% factually verifiable. Do NOT rely on invented statistics.
- Prefer topics explainable by simple mechanics or math the viewer can follow in 40 seconds.
- No investment, tax or legal advice; explain how things work only.
- If you are not sure a claim is true, pick a different topic.
- Must not be similar to these recent topics:
{avoid}

Answer ONLY with JSON: {{"topics": [{{"topic": "...", "angle": "one sentence on the surprising point"}}, ...]}}"""


def choose_topic(cfg: dict, manual: str | None = None) -> dict:
    entries = read_log(cfg["paths"]["run_log"])
    category, fmt = pick_rotation(cfg, entries)
    if manual:
        return {"topic": manual, "angle": "", "category": category, "format": fmt}
    used = [e["topic"] for e in recent(entries, cfg["content"]["no_repeat_days"]) if e.get("topic")]

    def validate(data):
        topics = data["topics"]
        if not isinstance(topics, list) or not topics:
            raise ValueError("keine Themen geliefert")
        return topics

    topics = ask_json(build_prompt(cfg, category, fmt, used), cfg, validate=validate)
    for t in topics:
        if not too_similar(t["topic"], used):
            return {"topic": t["topic"], "angle": t.get("angle", ""), "category": category, "format": fmt}
    raise RuntimeError("alle Vorschlaege zu aehnlich zu kuerzlich genutzten Themen")
