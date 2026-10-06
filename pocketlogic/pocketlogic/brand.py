"""Pocket-Logic-Branding: Logo (Variante B, steigende Balken)."""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

GRAD_FROM = (150, 80, 255)
GRAD_TO = (255, 92, 200)
DOT = (18, 10, 36)


def logo_tile(size: int, supersample: int = 4) -> Image.Image:
    """Abgerundetes Quadrat mit Violett-Pink-Verlauf und drei steigenden Balken."""
    s = size * supersample
    vert = Image.linear_gradient("L").resize((s, s))
    grad = ImageChops.add(vert, vert.rotate(90), scale=2.0)  # Diagonale: oben links -> unten rechts
    tile = Image.composite(Image.new("RGB", (s, s), GRAD_TO), Image.new("RGB", (s, s), GRAD_FROM), grad)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=s // 4, fill=255)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    im.paste(tile, (0, 0), mask)
    d = ImageDraw.Draw(im)
    bw, base = s * 0.14, s * 0.76
    for i, h in enumerate((0.20, 0.34, 0.52)):
        x = s * 0.22 + i * (bw + s * 0.07)
        d.rounded_rectangle([x, base - s * h, x + bw, base], radius=bw / 3, fill=(255, 255, 255))
    d.ellipse([s * 0.62, s * 0.18, s * 0.79, s * 0.35], fill=DOT)
    return im.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(exist_ok=True)
    logo_tile(800).save(out / "logo.png")
    print(out / "logo.png")
