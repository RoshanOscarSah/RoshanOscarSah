#!/usr/bin/env python3
"""
make_ascii_svg.py — converts source-prepped.png into a self-typing
monochrome ASCII portrait as a self-contained animated SVG.

Each row is revealed by a left-to-right wipe (an animated clipPath), with a
small block cursor riding the wipe edge. Rows are staggered top to bottom.
The portrait prints ONCE and freezes — no looping.

Animation is SMIL (<animate>), which GitHub renders inside <img>-embedded SVGs.

Usage:  python scripts/make_ascii_svg.py
Output: roshan-ascii.svg
"""
import os
import numpy as np
from PIL import Image

STATIC = os.environ.get("STATIC") == "1"

SRC = "source-prepped.png"
OUT = "roshan-ascii.svg"

# bright (sparse) -> dark (dense). Leading space clears background to nothing.
RAMP = " .`:-=+*cs#%@"

COLS = 100          # character columns
FS = 6.2            # font size (px)
ADV = FS * 0.600    # monospace advance width
LH = FS * 1.200     # line height  -> cell aspect 2:1, matches sampling
CELL_ASPECT = LH / ADV

FG = "#c9d1d9"      # single light-grey fill. Monochrome on purpose:
                    # per-character colouring is what makes ASCII look like static.
BG = "#0d1117"
CURSOR = "#f0f6fc"

ROW_DUR = 0.20      # seconds for one row to wipe across
ROW_STEP = 0.030    # stagger between consecutive rows
START = 0.15


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    if not os.path.exists(SRC):
        raise SystemExit(f"missing {SRC} — run prep_photo.py first")

    img = Image.open(SRC).convert("L")
    w, h = img.size

    # sample at 2:1 because character cells are ~2x taller than wide
    rows = max(1, int(round(COLS * (h / w) / CELL_ASPECT)))
    small = img.resize((COLS, rows), Image.LANCZOS)
    a = np.array(small).astype(np.float32) / 255.0   # 0=black .. 1=white

    # brightness -> ramp index (bright maps to index 0 = space)
    idx = np.clip((1.0 - a) * (len(RAMP) - 1e-6), 0, len(RAMP) - 1).astype(int)

    lines = ["".join(RAMP[i] for i in row) for row in idx]
    # trim fully-blank leading/trailing rows
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    rows = len(lines)

    W = COLS * ADV
    H = rows * LH + LH * 0.6
    total = START + rows * ROW_STEP + ROW_DUR

    p = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
        f'viewBox="0 0 {W:.2f} {H:.2f}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">'
    )
    p.append(f'<rect width="{W:.2f}" height="{H:.2f}" fill="{BG}"/>')

    # --- clip paths: one animated wipe rect per row
    p.append("<defs>")
    for i in range(rows):
        y = i * LH
        d = START + i * ROW_STEP
        if STATIC:
            p.append(
                f'<clipPath id="w{i}">'
                f'<rect x="0" y="{y:.2f}" width="{W:.2f}" height="{LH:.2f}"/>'
                f'</clipPath>'
            )
        else:
            p.append(
                f'<clipPath id="w{i}">'
                f'<rect x="0" y="{y:.2f}" width="0" height="{LH:.2f}">'
                f'<animate attributeName="width" from="0" to="{W:.2f}" '
                f'begin="{d:.3f}s" dur="{ROW_DUR}s" fill="freeze" '
                f'calcMode="spline" keySplines="0.3 0 0.2 1" keyTimes="0;1"/>'
                f'</rect></clipPath>'
            )
    p.append("</defs>")

    # --- the portrait
    p.append(f'<g fill="{FG}" font-size="{FS}" xml:space="preserve">')
    for i, line in enumerate(lines):
        baseline = (i + 1) * LH - LH * 0.22
        # Every glyph gets an explicit x coordinate via SVG's x-list syntax.
        # This makes the character grid independent of whatever monospace font
        # the viewer resolves — GitHub, Safari and Chrome all substitute
        # differently, and relying on font metrics shears the portrait.
        # (textLength/lengthAdjust is worse still: rows have differing numbers
        # of trailing spaces, so each row stretches by a different amount.)
        stripped = line.rstrip()
        if not stripped:
            continue
        lead = len(stripped) - len(stripped.lstrip())
        glyphs = stripped[lead:]
        xs = " ".join(f"{(lead + j) * ADV:.2f}" for j in range(len(glyphs)))
        p.append(
            f'<text x="{xs}" y="{baseline:.2f}" '
            f'clip-path="url(#w{i})">{esc(glyphs)}</text>'
        )
    p.append("</g>")

    # --- block cursor riding the wipe edge of each row
    p.append(f'<g fill="{CURSOR}">' if not STATIC else '<g style="display:none">')
    for i in range(rows):
        y = i * LH
        d = START + i * ROW_STEP
        p.append(
            f'<rect x="0" y="{y:.2f}" width="{ADV*1.1:.2f}" height="{LH*0.88:.2f}" opacity="0">'
            f'<animate attributeName="x" from="0" to="{W:.2f}" begin="{d:.3f}s" '
            f'dur="{ROW_DUR}s" fill="remove" calcMode="spline" '
            f'keySplines="0.3 0 0.2 1" keyTimes="0;1"/>'
            f'<animate attributeName="opacity" values="0;0.85;0.85;0" '
            f'keyTimes="0;0.05;0.9;1" begin="{d:.3f}s" dur="{ROW_DUR}s" fill="remove"/>'
            f'</rect>'
        )
    p.append("</g>")

    # --- trailing prompt + blinking cursor once the portrait finishes
    p.append(
        f'<g opacity="{1 if STATIC else 0}">'
        f'<animate attributeName="opacity" from="0" to="1" '
        f'begin="{total:.2f}s" dur="0.3s" fill="freeze"/>'
        f'<text x="0" y="{H - LH*0.15:.2f}" font-size="{FS}" fill="#6e7681">'
        f'roshan@github ~ $ </text>'
        f'<rect x="{ADV*17:.2f}" y="{H - LH*1.05:.2f}" width="{ADV*1.1:.2f}" '
        f'height="{LH*0.85:.2f}" fill="{CURSOR}">'
        f'<animate attributeName="opacity" values="1;1;0;0" dur="1s" '
        f'begin="{total:.2f}s" repeatCount="indefinite" calcMode="discrete"/>'
        f'</rect></g>'
    )

    p.append("</svg>")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("".join(p))
    print(f"wrote {OUT}  ({W:.0f}x{H:.0f}, {COLS}x{rows} chars, "
          f"animation {total:.1f}s)")


if __name__ == "__main__":
    main()
