"""Stufe 2: Skript per Claude (HPC: Hook - Progression - Climax), validiert."""
from pydantic import BaseModel, Field, ValidationError

from .claude_client import ask_json


class Scene(BaseModel):
    text: str                                   # Satz/Abschnitt aus dem Skript
    search_terms: list[str] = Field(min_length=1, max_length=3)  # englische Stock-Suchbegriffe
    card_text: str | None = None                # optionaler Text fuer eigene Grafik


class Script(BaseModel):
    title: str
    hook: str
    script: str
    scenes: list[Scene] = Field(min_length=3)
    description: str
    tags: list[str]
    category: str
    format: str


def word_count(s: str) -> int:
    return len(s.split())


def check_limits(s: Script, cfg: dict) -> Script:
    c = cfg["script"]
    n = word_count(s.script)
    if not c["words_min"] <= n <= c["words_max"]:
        raise ValueError(f"Skript hat {n} Woerter, erlaubt {c['words_min']}-{c['words_max']}")
    if len(s.title) > c["title_max_chars"]:
        raise ValueError(f"Titel zu lang ({len(s.title)} Zeichen)")
    if word_count(s.hook) > c["hook_max_words"]:
        raise ValueError(f"Hook zu lang ({word_count(s.hook)} Woerter)")
    if not s.script.strip().startswith(s.hook.strip().rstrip(".!?")[:20]):
        raise ValueError("Skript muss mit dem Hook beginnen")
    if "#Shorts" not in s.description:
        s.description += " #Shorts"
    if "financial advice" not in s.description.lower():
        s.description += f"\n\n{cfg['content']['disclaimer']}"
    return s


def build_prompt(cfg: dict, t: dict, shorten_to: int | None = None) -> str:
    c = cfg["script"]
    length = (f"at most {shorten_to} words" if shorten_to
              else f"{c['words_min']}-{c['words_max']} words")
    return f"""You write voice-over scripts for the YouTube Shorts channel "{cfg['channel']['name']}" ({cfg['channel']['tagline']}). English, US audience.
Topic: {t['topic']}
Angle: {t.get('angle', '')}
Category: {t['category']}
Format: {t['format']}

Structure (HPC):
1. HOOK - first 2 seconds, max {c['hook_max_words']} words, curiosity or surprise. The script MUST start with the hook text.
2. PROGRESSION - build the explanation step by step, simple mechanics or math.
3. CLIMAX - the "aha" payoff, short closing line. No "like and subscribe".

Length of "script": {length} (spoken, no stage directions, no emojis).

Hard rules:
- Everything must be factually correct and verifiable. Do NOT invent numbers, statistics or sources. Prefer worked examples with round numbers you calculate yourself and label as examples ("say you ...").
- No investment, tax or legal advice. Explain how things work.
- If you are unsure about a fact, keep it general instead of guessing.

Answer ONLY with JSON:
{{"title": "<=70 chars, clickworthy, not misleading",
  "hook": "...",
  "script": "full voice-over text",
  "scenes": [{{"text": "sentence(s) from the script", "search_terms": ["1-3 English stock-footage search terms"], "card_text": "optional short on-screen text or null"}}],
  "description": "2-3 sentences + #Shorts + 3-5 hashtags",
  "tags": ["..."],
  "category": "{t['category']}",
  "format": "{t['format']}"}}
Scenes must together cover the whole script in order (about 6-10 scenes)."""


def generate_script(cfg: dict, topic: dict, shorten_to: int | None = None) -> dict:
    def validate(data):
        try:
            return check_limits(Script(**data), cfg)
        except ValidationError as e:
            raise ValueError(f"Schema: {e.errors()[0]['loc']} {e.errors()[0]['msg']}") from e

    return ask_json(build_prompt(cfg, topic, shorten_to), cfg, validate=validate).model_dump()
