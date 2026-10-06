"""Eigene Grafiken im Pocket-Logic-Stil (Pillow): Hook-Karte, Fakten-Karten, Overlays, Thumbnail.

Sichere Zone fuer Shorts: oben ~10 % und unten ~25 % verdeckt die YouTube-Oberflaeche,
rechts liegen die Buttons. Texte bleiben daher zwischen y=200 und y=1150, x=70..930.
"""
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .brand import logo_tile

NUMERIC = re.compile(r"[\d$%€£]")


def rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@lru_cache(maxsize=64)
def _font(font_dir: str, name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Path(font_dir) / name), size)


def font(cfg: dict, weight: str, size: int) -> ImageFont.FreeTypeFont:
    name = cfg["brand"]["font_bold"] if weight == "bold" else cfg["brand"]["font_medium"]
    return _font(cfg["paths"]["font_dir"], name, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=fnt) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(cfg, draw, text, max_w, max_lines, sizes) -> tuple:
    """Groesste Schriftgroesse, bei der der Text in max_lines Zeilen passt."""
    for size in sizes:
        fnt = font(cfg, "bold", size)
        lines = wrap(draw, text, fnt, max_w)
        if len(lines) <= max_lines:
            return fnt, lines
    return fnt, lines[:max_lines]


def draw_rich(draw, x, y, line, fnt, ink, accent, highlight: set[str]):
    """Zeichnet eine Zeile; Zahlen/Betraege und Highlight-Woerter in der Akzentfarbe."""
    for w in line.split():
        color = accent if NUMERIC.search(w) or w.lower().strip(".,!?") in highlight else ink
        draw.text((x, y), w, font=fnt, fill=color)
        x += draw.textlength(w + " ", font=fnt)


def _highlight_words(text: str) -> set[str]:
    """Ohne Zahl im Text: die letzten zwei Woerter hervorheben (meist die Pointe)."""
    if NUMERIC.search(text):
        return set()
    return {w.lower().strip(".,!?") for w in text.split()[-2:]}


def _background(cfg, W, H) -> Image.Image:
    """Dunkelvioletter Hintergrund mit weichem Lichtschein."""
    b = cfg["brand"]
    img = Image.new("RGB", (W, H), rgb(b["bg"]))
    glow = Image.new("RGB", (W, H), rgb(b["bg"]))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-W * 0.3, H * 0.05, W * 1.0, H * 0.6], fill=rgb(b["panel"]))
    gd.ellipse([W * 0.5, H * 0.55, W * 1.4, H * 1.1], fill=tuple(int(c * 0.6) for c in rgb(b["accent"])))
    return Image.blend(img, glow.filter(ImageFilter.GaussianBlur(220)), 0.9)


def watermark(cfg, W=1080, H=1920) -> Image.Image:
    """Transparente Ebene: dezente Abdunklung oben + kleines Logo mit Wortmarke oben links."""
    b = cfg["brand"]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    scrim = Image.linear_gradient("L").resize((W, 420)).transpose(Image.FLIP_TOP_BOTTOM)
    shade = Image.new("RGBA", (W, 420), rgb(b["bg"]) + (0,))
    shade.putalpha(scrim.point(lambda v: int(v * 0.55)))
    layer.alpha_composite(shade, (0, 0))
    s = 64
    layer.alpha_composite(logo_tile(s), (70, 130))
    d = ImageDraw.Draw(layer)
    f = font(cfg, "bold", 44)
    d.text((70 + s + 18, 136), "Pocket", font=f, fill=rgb(b["ink"]))
    d.text((70 + s + 18 + d.textlength("Pocket ", font=f), 136), "Logic", font=f, fill=rgb(b["accent"]))
    return layer


def _panel(layer: Image.Image, box, cfg, alpha=235):
    pd = ImageDraw.Draw(layer)
    pd.rounded_rectangle(box, radius=40, fill=rgb(cfg["brand"]["panel"]) + (alpha,))


def hook_overlay(cfg, hook: str, label: str, W=1080, H=1920) -> Image.Image:
    """Hook als grosse Titelzeile ueber einem Clip (Szene 1)."""
    b = cfg["brand"]
    layer = watermark(cfg, W, H)
    d = ImageDraw.Draw(layer)
    fnt, lines = fit(cfg, d, hook, 820, 4, range(104, 60, -4))
    lh = int(fnt.size * 1.18)
    top = 300
    _panel(layer, [50, top - 40, W - 130, top + 80 + lh * len(lines) + 30], cfg)
    d = ImageDraw.Draw(layer)
    d.text((90, top), label.upper(), font=font(cfg, "bold", 34), fill=rgb(b["label"]))
    hl = _highlight_words(hook)
    for i, line in enumerate(lines):
        draw_rich(d, 90, top + 70 + i * lh, line, fnt, rgb(b["ink"]), rgb(b["accent"]), hl)
    return layer


def fact_overlay(cfg, text: str, W=1080, H=1920) -> Image.Image:
    """Kurzer Einblendtext (card_text) in einem Panel ueber einem Clip."""
    b = cfg["brand"]
    layer = watermark(cfg, W, H)
    d = ImageDraw.Draw(layer)
    fnt, lines = fit(cfg, d, text, 800, 3, range(92, 52, -4))
    lh = int(fnt.size * 1.2)
    top = 320
    _panel(layer, [50, top - 45, W - 130, top + lh * len(lines) + 35], cfg)
    d = ImageDraw.Draw(layer)
    hl = _highlight_words(text)
    for i, line in enumerate(lines):
        draw_rich(d, 90, top + i * lh, line, fnt, rgb(b["ink"]), rgb(b["accent"]), hl)
    return layer


def full_card(cfg, text: str, label: str | None = None, W=1080, H=1920) -> Image.Image:
    """Vollbild-Karte als Fallback, wenn kein passender Clip gefunden wurde (auch Thumbnail)."""
    b = cfg["brand"]
    img = _background(cfg, W, H).convert("RGBA")
    img.alpha_composite(watermark(cfg, W, H))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 12], fill=rgb(b["accent"]))
    fnt, lines = fit(cfg, d, text, 860, 6, range(120, 60, -4))
    lh = int(fnt.size * 1.18)
    top = max(420, int(H * 0.36 - lh * len(lines) / 2))
    if label:
        d.text((80, top - 80), label.upper(), font=font(cfg, "bold", 38), fill=rgb(b["label"]))
    hl = _highlight_words(text)
    for i, line in enumerate(lines):
        draw_rich(d, 80, top + i * lh, line, fnt, rgb(b["ink"]), rgb(b["accent"]), hl)
    return img.convert("RGB")
