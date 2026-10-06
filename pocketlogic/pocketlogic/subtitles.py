"""Stufe 5: .ass-Untertitel aus den Wortzeitmarken; aktives Wort in der Akzentfarbe."""
import re
from pathlib import Path

from .cards import rgb


def ass_color(hex_color: str) -> str:
    r, g, b = rgb(hex_color)
    return f"&H00{b:02X}{g:02X}{r:02X}"  # ASS: &HAABBGGRR


def ass_time(t: float) -> str:
    cs = int(round(max(t, 0) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def clean(word: str) -> str:
    return word.replace("{", "").replace("}", "").replace("\\", "").strip()


def chunk_words(words: list[dict], max_words: int, pause: float) -> list[list[dict]]:
    """1-3 Woerter pro Einblendung; nach einer Sprechpause beginnt eine neue."""
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > pause):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(cfg: dict, words: list[dict], out: Path) -> Path:
    s, b, r = cfg["subtitles"], cfg["brand"], cfg["render"]
    ink, accent, outline = ass_color(b["ink"]), ass_color(b["accent"]), ass_color(b["bg"])
    family = Path(b["font_bold"]).stem.replace("-", " ")  # "Inter-ExtraBold.otf" -> "Inter ExtraBold"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {r['width']}
PlayResY: {r['height']}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,{family},{s['font_size']},{ink},{ink},{outline},&H80000000,0,0,0,0,100,100,0,0,1,{s['outline']},3,2,80,160,{s['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    chunks = chunk_words(words, s["max_words"], s["pause_break_s"])
    for ci, chunk in enumerate(chunks):
        next_start = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else chunk[-1]["end"] + 0.4
        chunk_end = min(next_start, chunk[-1]["end"] + 0.35)
        for wi, w in enumerate(chunk):
            start = w["start"]
            end = chunk[wi + 1]["start"] if wi + 1 < len(chunk) else chunk_end
            parts = []
            for wj, other in enumerate(chunk):
                text = clean(other["word"]).upper()
                parts.append(f"{{\\c{accent}}}{text}{{\\c{ink}}}" if wj == wi else text)
            pop = "{\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)}" if wi == 0 else ""
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Word,,0,0,0,,{pop}{' '.join(parts)}")
    out.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return out


def find_phrase(words: list[dict], phrase: str) -> tuple[float, float] | None:
    """Zeitbereich (Start erstes Wort, Ende letztes Wort) einer Phrase in den Wortzeitmarken."""
    toks, owner = [], []
    for i, w in enumerate(words):
        for t in re.findall(r"[a-z0-9$%]+", w["word"].lower()):
            toks.append(t)
            owner.append(i)
    target = re.findall(r"[a-z0-9$%]+", phrase.lower())
    n = len(target)
    for i in range(len(toks) - n + 1):
        if toks[i:i + n] == target:
            return words[owner[i]]["start"], words[owner[i + n - 1]]["end"]
    return None
