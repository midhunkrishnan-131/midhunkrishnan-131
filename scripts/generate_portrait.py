#!/usr/bin/env python3
"""Build a green-on-dark line-art portrait SVG from the LinkedIn headshot.

Pipeline: grayscale, Sobel edges, hair texture, half-block characters
(▀ ▄ █) so facial detail survives a README-sized grid.
"""

from __future__ import annotations

import html
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "assets" / "linkedin_avatar.jpg"
DEFAULT_OUT = ROOT / "assets" / "portrait.svg"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

BG = "#070b10"
GREEN_DIM = "#1f9a4a"
GREEN_MID = "#3ddc84"
GREEN_HOT = "#d8ffe8"
GOLD = "#e3b341"
FRAME = "#1f6f43"


def build_art(src: Path):
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    luma_raw = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    warm = red - blue
    base = ImageOps.autocontrast(
        Image.fromarray(np.clip(luma_raw, 0, 255).astype(np.uint8)), cutoff=1
    )
    luma = np.asarray(base).astype(np.float32)
    soft = np.asarray(base.filter(ImageFilter.GaussianBlur(radius=1.5))).astype(np.float32)
    mag = np.hypot(*np.gradient(soft))
    fine = np.asarray(base.filter(ImageFilter.GaussianBlur(radius=0.45))).astype(np.float32)
    fmag = np.hypot(*np.gradient(fine))

    height, width = luma.shape
    yy, xx = np.mgrid[0:height, 0:width]
    cy, cx = (height - 1) / 2, (width - 1) / 2
    rad = min(cx, cy) * 0.97
    circle = (xx - cx) ** 2 + (yy - cy) ** 2 <= rad ** 2
    ring = (xx - cx) ** 2 + (yy - cy) ** 2 > (rad * 0.945) ** 2
    background = (warm < 0) & (luma < 75) & (fmag < 6)

    edges = mag.copy()
    edges[background | ~circle | ring] = 0
    scale = np.percentile(edges[edges > 0.3], 97.5)
    edge = np.clip(edges / scale, 0, 1) ** 0.85
    hair = (luma < 55) & (warm > -6) & circle & ~background
    texture = np.clip(fmag / 22, 0, 1) * hair * 0.62
    art = np.maximum(edge, texture)
    art[art < 0.06] = 0

    shirt = (luma > 175) & (np.abs(warm) < 28) & circle

    ys, xs = np.where(art > 0.28)
    y0 = max(0, int(ys.min() - 12))
    x0 = max(0, int(np.percentile(xs, 1) - 18))
    x1 = min(width, int(np.percentile(xs, 99) + 18))
    span = ys.max() - ys.min()
    y1 = min(height, int(ys.min() + span * 0.78))
    return art[y0:y1, x0:x1], shirt[y0:y1, x0:x1]


def cell_metrics(font_size: int = 14):
    """Advance and ink height of the block glyphs, so rows tile without gaps."""
    font = ImageFont.truetype(FONT_PATH, font_size)
    char_w = font.getlength("█")
    left, top, right, bottom = font.getbbox("█")
    line_h = max(1, bottom - top)
    return font, char_w, line_h, top


def sample_grid(art, shirt, cols: int, char_w: float, line_h: float, threshold: float = 0.17):
    aspect = art.shape[0] / art.shape[1]
    rows = int(round(cols * (char_w / line_h) * aspect))
    field = (
        np.asarray(
            Image.fromarray((np.clip(art, 0, 1) * 255).astype(np.uint8)).resize(
                (cols, rows * 2), Image.Resampling.BOX
            )
        ).astype(np.float32)
        / 255.0
    )
    shirt_s = (
        np.asarray(
            Image.fromarray(shirt.astype(np.uint8) * 255).resize(
                (cols, rows * 2), Image.Resampling.BOX
            )
        ).astype(np.float32)
        / 255.0
    )
    grid = []
    for i in range(rows):
        row = []
        for j in range(cols):
            top = float(field[i * 2, j])
            bot = float(field[i * 2 + 1, j])
            top_on, bot_on = top >= threshold, bot >= threshold
            if not top_on and not bot_on:
                row.append(None)
                continue
            if top_on and bot_on:
                char = "█"
            elif top_on:
                char = "▀"
            else:
                char = "▄"
            strength = max(top, bot)
            if max(float(shirt_s[i * 2, j]), float(shirt_s[i * 2 + 1, j])) > 0.5:
                color = GOLD
            elif strength > 0.62:
                color = GREEN_HOT
            elif strength > 0.36:
                color = GREEN_MID
            else:
                color = GREEN_DIM
            row.append((char, color))
        grid.append(row)
    return grid


def render_svg(grid, char_w: float, line_h: float, baseline_offset: float, out: Path) -> None:
    cols = len(grid[0])
    rows = len(grid)
    pad_x, pad_top, pad_bot = 22, 46, 36
    width = int(round(cols * char_w + pad_x * 2))
    height = int(round(rows * line_h + pad_top + pad_bot))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">Line-art portrait of Midhun Krishnan</title>",
        "<desc id=\"desc\">Green phosphor half-block portrait generated from his LinkedIn photo.</desc>",
        f'<rect width="{width}" height="{height}" rx="16" fill="{BG}"/>',
        f'<rect x="1.5" y="1.5" width="{width - 3}" height="{height - 3}" rx="14" fill="none" stroke="{FRAME}" stroke-width="2"/>',
        f'<circle cx="22" cy="22" r="5" fill="{GOLD}"/>',
        f'<circle cx="38" cy="22" r="5" fill="{GREEN_MID}"/>',
        f'<circle cx="54" cy="22" r="5" fill="#16324f"/>',
        f'<text x="72" y="27" fill="{GREEN_MID}" font-family="DejaVu Sans Mono, Cascadia Mono, Consolas, Liberation Mono, monospace" font-size="13">midhun@profile:~</text>',
    ]
    family = "DejaVu Sans Mono, Cascadia Mono, Consolas, Liberation Mono, monospace"
    for i, row in enumerate(grid):
        # baseline_offset is negative (glyph top relative to the baseline).
        y = pad_top + i * line_h - baseline_offset
        begin = f"{0.15 + i * 0.018:.2f}s"
        chunks = []
        color = None
        chars: list[str] = []
        xs: list[str] = []
        end = -1

        def flush():
            if not chars:
                return
            x_attr = " ".join(xs)
            chunks.append(
                f'<tspan fill="{color}" x="{x_attr}">{html.escape("".join(chars))}</tspan>'
            )

        for j, cell in enumerate(row):
            if cell is None:
                flush()
                chars, xs, color, end = [], [], None, -1
                continue
            ch, col = cell
            x = f"{pad_x + j * char_w:.2f}"
            if color == col and end == j:
                chars.append(ch)
                xs.append(x)
                end = j + 1
            else:
                flush()
                color, chars, xs, end = col, [ch], [x], j + 1
        flush()
        if not chunks:
            continue
        # opacity stays 1 if a renderer strips <animate> (GitHub's sanitizer sometimes does).
        parts.append(
            f'<text y="{y:.2f}" font-family="{family}" font-size="14" opacity="1">'
            + "".join(chunks)
            + f'<animate attributeName="opacity" values="0;1" begin="{begin}" dur="0.22s" fill="freeze"/>'
            + "</text>"
        )
    caption = "MIDHUN KRISHNAN  ·  PYTHON  ·  GENERATIVE AI"
    parts.append(
        f'<text x="{width / 2:.1f}" y="{height - 14}" text-anchor="middle" fill="{GOLD}" '
        f'font-family="{family}" font-size="12" opacity="1">{html.escape(caption)}'
        f'<animate attributeName="opacity" values="0;1" begin="{0.2 + rows * 0.018:.2f}s" dur="0.35s" fill="freeze"/>'
        "</text>"
    )
    parts.append("</svg>")
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes, {cols}x{rows})")


def main():
    _font, char_w, line_h, baseline_offset = cell_metrics(14)
    art, shirt = build_art(DEFAULT_SRC)
    grid = sample_grid(art, shirt, cols=92, char_w=char_w, line_h=line_h)
    render_svg(grid, char_w, line_h, baseline_offset, DEFAULT_OUT)


if __name__ == "__main__":
    main()
