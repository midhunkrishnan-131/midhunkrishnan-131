#!/usr/bin/env python3
"""Fine monochrome-green ASCII line portrait from the LinkedIn headshot.

Grayscale, Sobel edges with the background knocked out, a light hair/beard
stipple, then a dense ASCII ramp. Every glyph stays on a green hue.
"""

from __future__ import annotations

import html
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "assets" / "linkedin_avatar.jpg"
DEFAULT_OUT = ROOT / "assets" / "portrait.svg"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

BG = "#050a0c"
FRAME = "#1f8f4e"
GREEN = ("#145c32", "#1f9a4a", "#3ddc84", "#b6ffd0")
RAMP = " .,:;+*#@"
COLS = 146
FONT_SIZE = 8
LINE_H = 9
FLOOR = 0.16


def build_art(src: Path) -> np.ndarray:
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    luma_raw = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    warm = red - blue
    base = ImageOps.autocontrast(
        Image.fromarray(np.clip(luma_raw, 0, 255).astype(np.uint8)), cutoff=1
    )
    luma = np.asarray(base).astype(np.float32)
    height, width = luma.shape
    yy, xx = np.mgrid[0:height, 0:width]
    cy, cx = (height - 1) / 2, (width - 1) / 2
    rad = min(cx, cy) * 0.97
    circle = (xx - cx) ** 2 + (yy - cy) ** 2 <= rad ** 2
    ring = (xx - cx) ** 2 + (yy - cy) ** 2 > (rad * 0.95) ** 2

    fine = np.asarray(base.filter(ImageFilter.GaussianBlur(0.4))).astype(np.float32)
    fine_mag = np.hypot(*np.gradient(fine))
    background = (warm < 2) & (luma < 80) & (fine_mag < 5.5)

    soft = np.asarray(base.filter(ImageFilter.GaussianBlur(1.05))).astype(np.float32)
    mag = np.hypot(*np.gradient(soft))
    mag = mag.copy()
    mag[background | ~circle | ring] = 0
    scale = np.percentile(mag[mag > 0.5], 94)
    edge = np.clip((np.clip(mag / scale, 0, 1) - 0.06) / 0.5, 0, 1) ** 0.75

    hair = (luma < 62) & (warm > -4) & circle & ~background & ~ring
    curl = np.clip(fine_mag / 16, 0, 1)
    art = np.maximum(edge, hair * (0.38 + 0.42 * curl))
    art[art < 0.07] = 0

    ys, xs = np.where(art > 0.2)
    y0 = max(0, int(ys.min() - 8))
    x0 = max(0, int(np.percentile(xs, 3) - 8))
    x1 = min(width, int(np.percentile(xs, 97) + 8))
    span = int(ys.max() - ys.min())
    y1 = min(height, int(ys.min() + span * 0.70))
    return art[y0:y1, x0:x1]


def sample(art: np.ndarray) -> np.ndarray:
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    char_w = font.getlength("M")
    aspect = art.shape[0] / art.shape[1]
    rows = int(round(COLS * (char_w / LINE_H) * aspect))
    small = Image.fromarray((np.clip(art, 0, 1) * 255).astype(np.uint8)).resize(
        (COLS, rows), Image.Resampling.BOX
    )
    return np.asarray(small).astype(np.float32) / 255.0


def glyph(strength: float) -> tuple[str, str] | None:
    if strength < FLOOR:
        return None
    unit = min(1.0, (strength - FLOOR) / 0.85)
    char = RAMP[min(len(RAMP) - 1, int(unit * (len(RAMP) - 1)))]
    if char == " ":
        return None
    color = GREEN[min(len(GREEN) - 1, int(unit * (len(GREEN) - 1) + 0.15))]
    return char, color


def render_svg(field: np.ndarray, out: Path) -> None:
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    char_w = font.getlength("M")
    _left, top, _right, _bottom = font.getbbox("M")
    rows, cols = field.shape
    pad_x, pad_top, pad_bot = 18, 28, 28
    width = int(round(cols * char_w + pad_x * 2))
    height = int(round(rows * LINE_H + pad_top + pad_bot))
    family = "DejaVu Sans Mono, Cascadia Mono, Consolas, Liberation Mono, monospace"
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">ASCII line portrait of Midhun Krishnan</title>',
        '<desc id="desc">Monochrome green ASCII portrait generated from his LinkedIn photo.</desc>',
        f'<rect width="{width}" height="{height}" rx="14" fill="{BG}"/>',
        f'<rect x="1.5" y="1.5" width="{width - 3}" height="{height - 3}" rx="12" fill="none" stroke="{FRAME}" stroke-width="1.5"/>',
        f'<circle cx="18" cy="16" r="3.5" fill="{GREEN[1]}"/>',
        f'<circle cx="30" cy="16" r="3.5" fill="{GREEN[2]}"/>',
        f'<circle cx="42" cy="16" r="3.5" fill="{GREEN[0]}"/>',
        f'<text x="54" y="20" fill="{GREEN[2]}" font-family="{family}" font-size="11">midhun@profile:~</text>',
    ]
    for i in range(rows):
        y = pad_top + i * LINE_H - top
        chunks: list[str] = []
        color = None
        chars: list[str] = []
        xs: list[str] = []
        end = -1

        def flush() -> None:
            if not chars:
                return
            chunks.append(
                f'<tspan fill="{color}" x="{" ".join(xs)}">{html.escape("".join(chars))}</tspan>'
            )

        for j in range(cols):
            cell = glyph(float(field[i, j]))
            if cell is None:
                flush()
                color, chars, xs, end = None, [], [], -1
                continue
            ch, col = cell
            if color == col and end == j:
                chars.append(ch)
                xs.append(f"{pad_x + j * char_w:.2f}")
                end = j + 1
            else:
                flush()
                color, chars, xs = col, [ch], [f"{pad_x + j * char_w:.2f}"]
                end = j + 1
        flush()
        if not chunks:
            continue
        begin = f"{0.12 + i * 0.012:.2f}s"
        parts.append(
            f'<text y="{y:.2f}" font-family="{family}" font-size="{FONT_SIZE}" opacity="1">'
            + "".join(chunks)
            + f'<animate attributeName="opacity" values="0;1" begin="{begin}" dur="0.18s" fill="freeze"/>'
            + "</text>"
        )
    caption = "MIDHUN KRISHNAN  ·  PYTHON  ·  GENERATIVE AI"
    parts.append(
        f'<text x="{width / 2:.1f}" y="{height - 12}" text-anchor="middle" fill="{GREEN[2]}" '
        f'font-family="{family}" font-size="11" opacity="1">{html.escape(caption)}'
        f'<animate attributeName="opacity" values="0;1" begin="{0.15 + rows * 0.012:.2f}s" dur="0.3s" fill="freeze"/>'
        "</text></svg>"
    )
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes, {cols}x{rows})")


def main() -> None:
    render_svg(sample(build_art(DEFAULT_SRC)), DEFAULT_OUT)


if __name__ == "__main__":
    main()
