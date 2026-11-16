#!/usr/bin/env python3
"""Self-hosted terminal cards for the profile README side columns.

Text is converted to paths from JetBrains Mono so the cards stay crisp and
identical wherever GitHub renders the SVG. Regenerate with:

    python3 scripts/generate_cards.py
"""

from __future__ import annotations

from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
FONT_DIR = Path("/usr/share/fonts/truetype/jetbrains-mono")

WIDTH = 320

BG = "#050a0c"
FRAME = "#1f8f4e"
GREEN = "#3ddc84"
GREEN_MID = "#1f9a4a"
GREEN_DEEP = "#145c32"
AMBER = "#e3b341"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
DIM = "#6e7681"
CHIP_BG = "#0c1812"
CHIP_STROKE = "#1b5434"
RULE = "#143d28"


class Face:
    def __init__(self, path: Path) -> None:
        font = TTFont(path)
        self.glyphset = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.hmtx = font["hmtx"]
        self.upem = font["head"].unitsPerEm
        self._cache: dict[str, tuple[str, int]] = {}

    def _glyph(self, ch: str) -> tuple[str, int]:
        cached = self._cache.get(ch)
        if cached is not None:
            return cached
        name = self.cmap.get(ord(ch))
        if name is None:
            raise ValueError(f"font has no glyph for {ch!r} (U+{ord(ch):04X})")
        pen = SVGPathPen(self.glyphset)
        self.glyphset[name].draw(pen)
        cached = (pen.getCommands(), self.hmtx[name][0])
        self._cache[ch] = cached
        return cached

    def width(self, text: str, size: float) -> float:
        scale = size / self.upem
        return sum(self._glyph(ch)[1] for ch in text) * scale

    def cap(self, size: float) -> float:
        return 730 / self.upem * size

    def svg(self, text: str, x: float, baseline: float, size: float, color: str) -> str:
        if not text:
            return ""
        scale = size / self.upem
        parts: list[str] = []
        cursor = 0
        for ch in text:
            d, adv = self._glyph(ch)
            if d:
                parts.append(f'<path d="{d}" transform="translate({cursor},0)"/>')
            cursor += adv
        return (
            f'<g fill="{color}" transform="translate({x:.2f},{baseline:.2f}) '
            f'scale({scale:.6f},{-scale:.6f})">' + "".join(parts) + "</g>"
        )


REGULAR = Face(FONT_DIR / "JetBrainsMono-Regular.ttf")
MEDIUM = Face(FONT_DIR / "JetBrainsMono-Medium.ttf")
FACES = {"regular": REGULAR, "medium": MEDIUM}


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class Card:
    def __init__(self, title: str, desc: str) -> None:
        self.title = title
        self.desc = desc
        self.parts: list[str] = []
        self.y = 40.0

    def add(self, fragment: str) -> None:
        if fragment:
            self.parts.append(fragment)

    def text(
        self,
        text: str,
        x: float,
        baseline: float,
        size: float,
        color: str,
        weight: str = "regular",
    ) -> float:
        face = FACES[weight]
        self.add(face.svg(text, x, baseline, size, color))
        return face.width(text, size)

    def baseline(self, size: float) -> float:
        return self.y + FACES["regular"].cap(size)

    def finish(self, height: float | None = None) -> str:
        height = int(round(height if height is not None else self.y + 14))
        width = WIDTH
        dots = [
            (18, GREEN_MID),
            (30, GREEN),
            (42, GREEN_DEEP),
        ]
        body = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f"<title>{esc(self.title)}</title>",
            f"<desc>{esc(self.desc)}</desc>",
            f'<rect width="{width}" height="{height}" rx="14" fill="{BG}"/>',
            f'<rect x="1.5" y="1.5" width="{width - 3}" height="{height - 3}" rx="12" '
            f'fill="none" stroke="{FRAME}" stroke-width="1.5"/>',
        ]
        for cx, fill in dots:
            body.append(f'<circle cx="{cx}" cy="16" r="3.5" fill="{fill}"/>')
        body.append(
            MEDIUM.svg(self.title, 54, 16 + MEDIUM.cap(12) / 2 + 1, 12, GREEN)
        )
        body.append(
            f'<path d="M14 31 H{width - 14}" stroke="{RULE}" stroke-width="1"/>'
        )
        body.extend(self.parts)
        body.append("</svg>")
        return "\n".join(body) + "\n", height


def cursor(x: float, baseline: float, size: float) -> str:
    cap = REGULAR.cap(size)
    w = round(size * 0.52, 2)
    h = round(cap, 2)
    y = round(baseline - cap, 2)
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w}" height="{h}" rx="1" fill="{GREEN}">'
        '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.55;0.55;1" '
        'dur="1.15s" repeatCount="indefinite" calcMode="discrete"/>'
        "</rect>"
    )


def build_whoami() -> tuple[str, int]:
    card = Card(
        "whoami",
        "Midhun Krishnan, Python Developer and Generative AI. "
        "BCA at Yenepoya University, graduating 2028. "
        "Thiruvananthapuram, Kerala. Open to Python and GenAI internships.",
    )
    x = 16
    card.y = 40
    prompt = 13
    base = card.baseline(prompt)
    card.text("$ ", x, base, prompt, GREEN)
    card.text("whoami", x + REGULAR.width("$ ", prompt), base, prompt, DIM)
    card.y += 18
    name_size = 18
    card.text("Midhun Krishnan", x, card.baseline(name_size), name_size, GREEN, "medium")
    card.y += 22

    # Full-width output lines. 13px keeps every fact on one row inside the column.
    body = 13
    lines = [
        ("Python Developer · Generative AI", TEXT, False),
        ("BCA @ Yenepoya University (2028)", TEXT, False),
        ("Thiruvananthapuram, Kerala", MUTED, False),
        ("open to Python & GenAI internships", AMBER, True),
    ]
    for i, (value, color, blink) in enumerate(lines):
        base = card.baseline(body)
        width = card.text(value, x, base, body, color)
        if blink:
            card.add(cursor(x + width + 5, base, body))
        card.y += 18 if i < len(lines) - 1 else 14
    card.y += 2
    return card.finish()


def build_building() -> tuple[str, int]:
    card = Card(
        "currently building",
        "CodeDoctor AI, DevAssist, and MYX AI.",
    )
    projects = [
        ("01", "CodeDoctor AI", "Groq · Gemini"),
        ("02", "DevAssist", "tool calling"),
        ("03", "MYX AI", "CVSS · copilot"),
    ]
    card.y = 38
    for index, name, tag in projects:
        base = card.baseline(14)
        card.text(index, 16, base, 12, AMBER, "medium")
        card.text(name, 42, base, 14, GREEN, "medium")
        tag_w = REGULAR.width(tag, 12)
        card.text(tag, WIDTH - 16 - tag_w, base + 0.5, 12, MUTED)
        card.y += 24
    card.y += 12
    return card.finish()


def build_stack() -> tuple[str, int]:
    card = Card(
        "stack",
        "Python, FastAPI, Pydantic, Groq, OpenAI, Gemini, React, TypeScript, PostgreSQL, Docker, and Git.",
    )
    items = [
        ("Py", "Python", GREEN),
        ("Fa", "FastAPI", GREEN),
        ("Pd", "Pydantic", AMBER),
        ("Gq", "Groq", AMBER),
        ("OA", "OpenAI", GREEN),
        ("Ge", "Gemini", AMBER),
        ("Re", "React", GREEN),
        ("Ts", "TypeScript", GREEN),
        ("Pg", "PostgreSQL", GREEN),
        ("Dk", "Docker", AMBER),
        ("Gt", "Git", GREEN),
    ]
    pad = 14
    gap = 6
    cols = 2
    chip_w = (WIDTH - pad * 2 - gap) / cols
    chip_h = 34
    card.y = 42
    for i, (mono, name, accent) in enumerate(items):
        row, col = divmod(i, cols)
        last_row = row == (len(items) - 1) // cols
        lone = last_row and len(items) % cols == 1
        x = pad + (WIDTH - pad * 2 - chip_w) / 2 if lone else pad + col * (chip_w + gap)
        y = card.y + row * (chip_h + gap)
        card.add(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{chip_w:.2f}" height="{chip_h}" rx="8" '
            f'fill="{CHIP_BG}" stroke="{CHIP_STROKE}" stroke-width="1"/>'
        )
        box = 24
        bx = x + 8
        by = y + (chip_h - box) / 2
        card.add(
            f'<rect x="{bx:.2f}" y="{by:.2f}" width="{box}" height="{box}" rx="6" '
            f'fill="#10261a" stroke="{accent}" stroke-width="1"/>'
        )
        mono_w = MEDIUM.width(mono, 11)
        mono_base = by + box / 2 + MEDIUM.cap(11) / 2
        card.text(mono, bx + (box - mono_w) / 2, mono_base, 11, accent, "medium")
        name_base = y + chip_h / 2 + REGULAR.cap(13) / 2
        card.text(name, bx + box + 8, name_base, 13, TEXT)
    rows = (len(items) + cols - 1) // cols
    card.y += rows * (chip_h + gap) - gap + 14
    return card.finish()


def build_learning() -> tuple[str, int]:
    card = Card(
        "now learning",
        "Currently learning LLM agents, RAG, and MLOps.",
    )
    topics = [
        ("01", "LLM agents", "tool use · planning · handoffs"),
        ("02", "RAG", "chunking · retrieval · citations"),
        ("03", "MLOps", "evals · deploy · observability"),
    ]
    card.y = 44
    for index, title, detail in topics:
        base = card.baseline(14)
        card.text(index, 16, base, 12, AMBER, "medium")
        card.text(title, 44, base, 14, TEXT, "medium")
        card.y += 18
        card.text(detail, 44, card.baseline(12), 12, MUTED)
        card.y += 24
    card.y += 2
    return card.finish()


def build_badge(label: str, mark: str, mark_color: str, desc: str) -> str:
    """Small pill. The README wraps the file in an <a>, since an SVG <img> cannot be clicked."""
    width, height = 118, 28
    size = 12
    box = 16
    bx = 8
    by = (height - box) / 2
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        f"<title>{esc(label)}</title>",
        f"<desc>{esc(desc)}</desc>",
        f'<rect width="{width}" height="{height}" rx="8" fill="{BG}"/>',
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="7" '
        f'fill="none" stroke="{FRAME}" stroke-width="1.25"/>',
        f'<rect x="{bx}" y="{by:.2f}" width="{box}" height="{box}" rx="4" '
        f'fill="#10261a" stroke="{mark_color}" stroke-width="1"/>',
    ]
    mark_w = MEDIUM.width(mark, 9)
    parts.append(
        MEDIUM.svg(mark, bx + (box - mark_w) / 2, by + box / 2 + MEDIUM.cap(9) / 2, 9, mark_color)
    )
    parts.append(
        MEDIUM.svg(label, bx + box + 6, height / 2 + MEDIUM.cap(size) / 2, size, TEXT)
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    cards = {
        "whoami.svg": build_whoami(),
        "building.svg": build_building(),
        "stack.svg": build_stack(),
        "learning.svg": build_learning(),
    }
    badges = {
        "badge-linkedin.svg": build_badge(
            "LinkedIn", "in", AMBER, "LinkedIn profile for Midhun Krishnan."
        ),
        "badge-email.svg": build_badge(
            "Email", "@", GREEN, "Email Midhun Krishnan."
        ),
    }
    OUT.mkdir(exist_ok=True)
    for name, svg in badges.items():
        path = OUT / name
        path.write_text(svg, encoding="utf-8")
        print(f"{name:16} {path.stat().st_size:6} bytes")
    for name, (svg, height) in cards.items():
        path = OUT / name
        path.write_text(svg, encoding="utf-8")
        print(f"{name:16} {WIDTH}x{height:4}  aspect {height / WIDTH:.3f}  {path.stat().st_size:6} bytes")

    # Measured on a GitHub-dark page with a 960px markdown column.
    side = 256.0
    gap = 30.0
    portrait = 594.0
    stats = side * 195 / 379.0333309173584
    streak = side * 195 / 495
    langs = side * 165 / 300

    def rendered(name: str) -> float:
        return cards[name][1] * side / WIDTH

    left = rendered("whoami.svg") + stats + streak + rendered("building.svg") + 3 * gap
    right = langs + rendered("stack.svg") + rendered("learning.svg") + 2 * gap
    print(f"predicted left  {left:.0f}px   portrait {portrait:.0f}px   delta {left - portrait:+.0f}")
    print(f"predicted right {right:.0f}px   portrait {portrait:.0f}px   delta {right - portrait:+.0f}")


if __name__ == "__main__":
    main()
