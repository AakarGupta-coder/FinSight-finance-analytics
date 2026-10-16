"""Render the FinSight mark (public/favicon.svg geometry) to PNG/ICO fallbacks.

Uses only Pillow (already a backend dependency), so no extra tooling is needed:
    python frontend/scripts/generate_icons.py
Outputs to frontend/public/. Keep the geometry in sync with favicon.svg.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

PUBLIC = Path(__file__).resolve().parent.parent / "public"
NAVY, TEAL, MINT, WHITE = (16, 185, 129), (6, 95, 70), (167, 243, 208), (255, 255, 255)

# Geometry in the 32-unit SVG coordinate system.
ARM_RISING = [(10.5, 24.5), (10.5, 11.0), (16.25, 11.0), (22.5, 6.5)]
ARM_MIDDLE = [(10.5, 17.75), (17.5, 17.75)]
DOT = (22.5, 6.5, 2.4)
STROKE = 3.2
RADIUS = 7.5


def _gradient(size: int) -> Image.Image:
    """Diagonal emerald -> deep emerald gradient (same stops as favicon.svg)."""
    grad = Image.new("RGB", (size, size))
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(NAVY, TEAL))
    return grad


def _polyline(draw: ImageDraw.ImageDraw, points, scale: float, width: float, fill) -> None:
    pts = [(x * scale, y * scale) for x, y in points]
    w = width * scale
    draw.line(pts, fill=fill, width=round(w), joint="curve")
    r = w / 2
    for x, y in (pts[0], pts[-1]):  # round caps
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def render(size: int, *, rounded: bool = True, inset: float = 0.0) -> Image.Image:
    """Render at 16x supersampling and downscale for clean anti-aliasing."""
    ss = size * 16
    scale = ss / 32
    img = _gradient(ss).convert("RGBA")
    glyph = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(glyph)
    # Optional inset (e.g. apple-touch icons, which the OS rounds itself).
    g_scale = scale * (1 - 2 * inset)
    offset = ss * inset

    def shift(points):
        return [(x + offset / g_scale, y + offset / g_scale) for x, y in points]

    _polyline(d, shift(ARM_RISING), g_scale, STROKE, WHITE)
    _polyline(d, shift(ARM_MIDDLE), g_scale, STROKE, WHITE)
    cx, cy, r = DOT
    cx, cy = cx * g_scale + offset, cy * g_scale + offset
    rr = r * g_scale
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=MINT)
    img.alpha_composite(glyph)
    if rounded:
        mask = Image.new("L", (ss, ss), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, ss - 1, ss - 1), radius=RADIUS * scale, fill=255)
        img.putalpha(mask)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    outputs = {
        "favicon-16x16.png": render(16),
        "favicon-32x32.png": render(32),
        "icon-192.png": render(192),
        "icon-512.png": render(512),
        "apple-touch-icon.png": render(180, rounded=False, inset=0.06),
    }
    for name, img in outputs.items():
        img.save(PUBLIC / name, optimize=True)
    render(48).save(PUBLIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("wrote", ", ".join([*outputs, "favicon.ico"]))


if __name__ == "__main__":
    main()
