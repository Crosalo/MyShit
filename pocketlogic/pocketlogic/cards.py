"""Eigene Grafiken im Pocket-Logic-Stil (Pillow): Hook-Karte, Fakten-Karten, Overlays, Thumbnail.

Sichere Zone fuer Shorts: oben ~10 % und unten ~25 % verdeckt die YouTube-Oberflaeche,
rechts liegen die Buttons. Texte bleiben daher zwischen y=200 und y=1150, x=70..930.
"""
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .brand import logo_tile

NUMERIC = re.compile(r"[\d$%€£]")


def rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@lru_cache(maxsize=64)
def _font(font_dir: str, name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Path(font_dir) / name), size)


def font_any(size: int) -> ImageFont.FreeTypeFont:
    """Schrift ohne Config (fuer interne Hilfsbilder); faellt auf die Pillow-Standardschrift zurueck."""
    for path in ("/usr/share/fonts/opentype/inter/Inter-Bold.otf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(path).exists():
            return _font(str(Path(path).parent), Path(path).name, size)
    return ImageFont.load_default(size)


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
    # dunkle Kontur, damit die Wortmarke auch auf hellen Clips lesbar bleibt
    kw = {"stroke_width": 3, "stroke_fill": rgb(b["bg"])}
    d.text((70 + s + 18, 136), "Pocket", font=f, fill=rgb(b["ink"]), **kw)
    d.text((70 + s + 18 + d.textlength("Pocket ", font=f), 136), "Logic", font=f, fill=rgb(b["accent"]), **kw)
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


# --- Clickbait-Stil: riesiger Punch-Text, ein Wort als gekippter Sticker ---------------------

def _sticker(cfg, word: str, fnt) -> Image.Image:
    """Hervorgehobenes Wort: Akzentflaeche, dunkle Schrift, leicht gekippt."""
    b = cfg["brand"]
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t, r, btm = tmp.textbbox((0, 0), word, font=fnt)
    pad_x, pad_y = int(fnt.size * 0.18), int(fnt.size * 0.10)
    w, h = r - l + 2 * pad_x, btm - t + 2 * pad_y
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(fnt.size * 0.18), fill=rgb(b["accent"]) + (255,))
    d.text((pad_x - l, pad_y - t), word, font=fnt, fill=rgb(b["bg"]))
    return img.rotate(4, resample=Image.BICUBIC, expand=True)


def punch_layer(cfg, text: str, highlight: str, center_y: int, W=1080, H=1920,
                max_w: int = 860, label: str | None = None) -> Image.Image:
    """Transparente Ebene mit riesigem Text in Grossbuchstaben; highlight-Wort als Sticker."""
    b = cfg["brand"]
    text = text.upper()
    hl = highlight.upper().strip(".,!?")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for size in range(210, 96, -6):
        fnt = font(cfg, "bold", size)
        lines = wrap(d, text, fnt, max_w)
        if len(lines) <= 3 and all(d.textlength(ln, font=fnt) <= max_w for ln in lines):
            break
    lh = int(fnt.size * 1.12)
    cx = 495  # leicht links der Mitte: rechts liegen die Shorts-Buttons
    top = int(center_y - lh * len(lines) / 2)
    if label:
        label = label.rstrip(" .…")  # "The math behind ..." -> "The math behind"
        lf = font(cfg, "bold", 34)
        lw = d.textlength(label.upper(), font=lf)
        d.rounded_rectangle([cx - lw / 2 - 22, top - 92, cx + lw / 2 + 22, top - 36], radius=28,
                            fill=rgb(b["label"]) + (255,))
        d.text((cx - lw / 2, top - 86), label.upper(), font=lf, fill=rgb(b["bg"]))
    stroke = max(4, fnt.size // 22)
    for i, line in enumerate(lines):
        words = line.split()
        space = d.textlength(" ", font=fnt)
        widths = [d.textlength(w, font=fnt) for w in words]
        x = cx - (sum(widths) + space * (len(words) - 1)) / 2
        y = top + i * lh
        for w, wd in zip(words, widths):
            if w.strip(".,!?") == hl:
                st = _sticker(cfg, w, fnt)
                layer.alpha_composite(st, (int(x + wd / 2 - st.width / 2), int(y + fnt.size * 0.55 - st.height / 2)))
            else:
                d.text((x + 6, y + 8), w, font=fnt, fill=(0, 0, 0, 150))          # Schlagschatten
                d.text((x, y), w, font=fnt, fill=rgb(b["ink"]), stroke_width=stroke, stroke_fill=rgb(b["bg"]))
            x += wd + space
    return layer


def _darken(img: Image.Image, cfg, W, H) -> Image.Image:
    """Clip-Frame fuellend zuschneiden, abdunkeln, violett toenen, Vignette."""
    src = img.convert("RGB")
    scale = max(W / src.width, H / src.height)
    src = src.resize((int(src.width * scale + 1), int(src.height * scale + 1)), Image.LANCZOS)
    left, top = (src.width - W) // 2, (src.height - H) // 2
    src = src.crop((left, top, left + W, top + H))
    src = ImageEnhance.Brightness(src).enhance(0.55)
    src = Image.blend(src, Image.new("RGB", (W, H), rgb(cfg["brand"]["bg"])), 0.3)
    vignette = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vignette).ellipse([-W * 0.25, -H * 0.1, W * 1.25, H * 1.1], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(160))
    return Image.composite(src, Image.new("RGB", (W, H), (0, 0, 0)), vignette)


def punch_overlay(cfg, text: str, highlight: str, label: str, W=1080, H=1920) -> Image.Image:
    """Erstes Bild im Video: abgedunkelter Clip + riesiger Punch-Text (wirkt wie das Thumbnail)."""
    layer = Image.new("RGBA", (W, H), rgb(cfg["brand"]["bg"]) + (110,))
    layer.alpha_composite(watermark(cfg, W, H))
    layer.alpha_composite(punch_layer(cfg, text, highlight, center_y=760, label=label))
    return layer


def thumbnail(cfg, text: str, highlight: str, frame: Image.Image | None = None, W=1080, H=1920) -> Image.Image:
    """Thumbnail: echter Clip-Frame (falls vorhanden) + riesiger Punch-Text + Logo."""
    base = _darken(frame, cfg, W, H) if frame is not None else _background(cfg, W, H)
    img = base.convert("RGBA")
    img.alpha_composite(watermark(cfg, W, H))
    img.alpha_composite(punch_layer(cfg, text, highlight, center_y=820))
    return img.convert("RGB")


# --- Call-to-Action: "+ FOLLOW" und Like / Comment / Share --------------------------------

def _icon(kind: str, s: int, color, hole) -> Image.Image:
    """Einfache Vektor-Icons (doppelt gross gezeichnet, dann verkleinert fuer glatte Kanten)."""
    S = s * 2
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "like":      # Herz
        r = S * 0.27
        d.ellipse([S * 0.28 - r, S * 0.36 - r, S * 0.28 + r, S * 0.36 + r], fill=color)
        d.ellipse([S * 0.72 - r, S * 0.36 - r, S * 0.72 + r, S * 0.36 + r], fill=color)
        d.polygon([(S * 0.03, S * 0.45), (S * 0.97, S * 0.45), (S * 0.5, S * 0.95)], fill=color)
    elif kind == "comment":  # Sprechblase mit drei Punkten
        d.rounded_rectangle([S * 0.02, S * 0.08, S * 0.98, S * 0.74], radius=S * 0.2, fill=color)
        d.polygon([(S * 0.22, S * 0.66), (S * 0.16, S * 0.96), (S * 0.48, S * 0.72)], fill=color)
        for cx in (0.3, 0.5, 0.7):
            d.ellipse([S * cx - S * 0.06, S * 0.35, S * cx + S * 0.06, S * 0.47], fill=hole)
    else:                    # Teilen-Pfeil
        d.polygon([(S * 0.04, S * 0.88), (S * 0.06, S * 0.62), (S * 0.2, S * 0.44), (S * 0.52, S * 0.4),
                   (S * 0.52, S * 0.12), (S * 0.98, S * 0.5), (S * 0.52, S * 0.88), (S * 0.52, S * 0.6),
                   (S * 0.3, S * 0.61), (S * 0.14, S * 0.7)], fill=color)
    return im.resize((s, s), Image.LANCZOS)


def cta_overlay(cfg, W=1080, H=1920, center_y=930) -> Image.Image:
    """Transparente Ebene: Panel mit '+ FOLLOW'-Button und Like/Comment/Share darunter."""
    b = cfg["brand"]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pw, ph, cx = 720, 330, 495
    x0, y0 = cx - pw // 2, center_y - ph // 2
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=44, fill=rgb(b["panel"]) + (238,),
                        outline=rgb(b["accent"]) + (255,), width=4)
    # Follow-Button
    f = font(cfg, "bold", 64)
    label = "+ FOLLOW"
    tw = d.textlength(label, font=f)
    bx0, by0 = cx - tw / 2 - 40, y0 + 34
    d.rounded_rectangle([bx0, by0, cx + tw / 2 + 40, by0 + 96], radius=48, fill=rgb(b["accent"]))
    d.text((cx - tw / 2, by0 + 10), label, font=f, fill=rgb(b["bg"]))
    # Like / Comment / Share
    lf = font(cfg, "bold", 30)
    icon, gap = 78, 220
    for k, (kind, text, color) in enumerate((("like", "LIKE", rgb(b["label"])),
                                              ("comment", "COMMENT", rgb(b["ink"])),
                                              ("share", "SHARE", rgb(b["ink"])))):
        ix = int(cx + (k - 1) * gap)
        layer.alpha_composite(_icon(kind, icon, color + (255,), rgb(b["panel"]) + (255,)),
                              (ix - icon // 2, y0 + 158))
        lw = d.textlength(text, font=lf)
        d.text((ix - lw / 2, y0 + 248), text, font=lf, fill=rgb(b["ink"]))
    return layer
