"""Stufe 2: Skript per Claude (HPC: Hook - Progression - Climax), validiert."""
import re

from pydantic import BaseModel, Field, ValidationError

from .claude_client import ask_json


class Scene(BaseModel):
    text: str                                   # Satz/Abschnitt aus dem Skript
    search_terms: list[str] = Field(min_length=1, max_length=3)  # englische Stock-Suchbegriffe
    card_text: str | None = None                # optionaler Text fuer eigene Grafik


class Script(BaseModel):
    title: str
    hook: str
    thumb_text: str                             # 2-5 Woerter, riesig auf Thumbnail + erstem Bild
    thumb_highlight: str                        # ein Wort daraus, wird als Sticker hervorgehoben
    cta: str = ""                               # gesprochener Call-to-Action in der Mitte
    script: str
    scenes: list[Scene] = Field(min_length=5)
    description: str
    tags: list[str]
    category: str
    format: str


def word_count(s: str) -> int:
    return len(s.split())


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9$%]+", text.lower())


def check_cta(s: Script, cfg: dict) -> None:
    """CTA muss woertlich im Skript stehen, kurz sein und etwa in der Mitte kommen."""
    c = cfg["cta"]
    cta, body = _tokens(s.cta), _tokens(s.script)
    if not 3 <= len(cta) <= c["max_words"]:
        raise ValueError(f"CTA muss 3-{c['max_words']} Woerter haben: {s.cta!r}")
    pos = next((i for i in range(len(body) - len(cta) + 1) if body[i:i + len(cta)] == cta), None)
    if pos is None:
        raise ValueError("CTA-Satz muss woertlich im Skript vorkommen")
    rel = pos / len(body)
    if not c["position_min"] <= rel <= c["position_max"]:
        raise ValueError(f"CTA steht bei {rel:.0%} des Skripts, erlaubt {c['position_min']:.0%}-{c['position_max']:.0%}")


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
    if not 2 <= word_count(s.thumb_text) <= 5 or len(s.thumb_text) > 32:
        raise ValueError(f"thumb_text muss 2-5 Woerter / max. 32 Zeichen haben: {s.thumb_text!r}")
    tw = [w.strip(".,!?").lower() for w in s.thumb_text.split()]
    if s.thumb_highlight.strip(".,!?").lower() not in tw:
        s.thumb_highlight = s.thumb_text.split()[-1]  # Fallback: letztes Wort
    if cfg["cta"]["enabled"]:
        check_cta(s, cfg)
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

Viewers swipe away within 1-2 seconds. Every word must earn its place.
Structure (HPC):
1. HOOK - the very first words, max {c['hook_max_words']} words. The script MUST start with the hook text.
   No intro, no "Here's why", no "Let's talk about", no "Did you know". Start mid-action.
   Speak to "you", use a concrete number or stake, a pattern interrupt or a contrarian claim.
   Energy examples (do not copy): "Your bank makes money every time you do this."
   / "That $5 coffee actually costs you $50." / "Stop paying the minimum."
2. OPEN LOOP - within the first two sentences, tease the payoff so people stay
   (e.g. "and the last number is the one that hurts").
3. PROGRESSION - fast, one idea per short sentence, simple math, keep tension. No filler.
3b. CALL TO ACTION - one short spoken sentence (max {cfg['cta']['max_words']} words) at roughly the middle,
   right before the payoff, so viewers stay for the answer. Ask to follow and to like, comment or share,
   tied to the topic, never generic begging. Examples (do not copy): "Follow, and share this with the friend
   who stacks coupons." / "Like this if you also thought it was 70." Then continue straight into the payoff.
4. CLIMAX - the "aha" payoff that delivers on the hook, then a final short line that leads INTO
   the hook so the Short loops seamlessly on replay. Do NOT repeat the hook at the end; end with a
   half-sentence the hook completes (e.g. ending "...and that's exactly why" -> hook "Your bank ...").
   No second call to action at the end, no "in conclusion".

Length of "script": {length} (spoken, no stage directions, no emojis).

Packaging (title + thumbnail) - maximum curiosity, but 100% honest:
- "title": max 60 characters. Curiosity gap + specific number or stake, e.g.
  "The $20 Trap Hidden in Every Credit Card Bill", "Why Paying the Minimum Keeps You Broke".
  Title case. At most one emoji, optional. Never ALL CAPS for the whole title.
- "thumb_text": 2-5 words, ALL CAPS, huge on the thumbnail and the first frame. Shocking or
  intriguing, e.g. "$30 PAID, $10 GONE?", "THE MINIMUM TRAP", "YOU'RE PAYING TWICE".
- "thumb_highlight": exactly one word from thumb_text to highlight (usually the number or the twist).
- The video MUST pay off whatever title and thumb_text promise. No false claims, no fake urgency,
  no "banks hate this" unless literally true. Misleading packaging gets the channel penalized.

Hard rules:
- Everything must be factually correct and verifiable. Do NOT invent numbers, statistics or sources. Prefer worked examples with round numbers you calculate yourself and label as examples ("say you ...").
- No investment, tax or legal advice. Explain how things work.
- If you are unsure about a fact, keep it general instead of guessing.
- search_terms: concrete, filmable stock-footage queries (objects, hands, people, places),
  e.g. "hand swiping credit card", "pile of coins close up". Avoid abstract words like "interest" or "debt".

Answer ONLY with JSON:
{{"title": "...",
  "hook": "...",
  "thumb_text": "...",
  "thumb_highlight": "...",
  "cta": "the exact call-to-action sentence as it appears in the script",
  "script": "full voice-over text",
  "scenes": [{{"text": "sentence(s) from the script", "search_terms": ["1-3 English stock-footage search terms"], "card_text": "optional short on-screen text (max 6 words) or null"}}],
  "description": "first line is a hook question, then 1-2 sentences + #Shorts + 3-5 hashtags",
  "tags": ["..."],
  "category": "{t['category']}",
  "format": "{t['format']}"}}
Scenes must together cover the whole script in order: 8-14 scenes, each one short sentence or phrase."""


def generate_script(cfg: dict, topic: dict, shorten_to: int | None = None) -> dict:
    def validate(data):
        try:
            return check_limits(Script(**data), cfg)
        except ValidationError as e:
            raise ValueError(f"Schema: {e.errors()[0]['loc']} {e.errors()[0]['msg']}") from e

    return ask_json(build_prompt(cfg, topic, shorten_to), cfg, validate=validate).model_dump()
