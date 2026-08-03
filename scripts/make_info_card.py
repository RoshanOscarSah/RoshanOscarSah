#!/usr/bin/env python3
"""
make_info_card.py — renders a neofetch-style info card as a self-contained
animated SVG. Monochrome: white keys, grey values, on a dark terminal panel.

Each row fades + slides in on a stagger, then freezes (no looping).
Set STATIC=1 to emit a frozen frame (useful for local previews).

Usage:  python scripts/make_info_card.py
Output: info-card.svg
"""
import os

STATIC = os.environ.get("STATIC") == "1"

# ---------------------------------------------------------------- content
USER = "roshan"
HOST = "github"

ROWS = [
    ("Now",       "Senior Flutter Developer @ Cubit Inc."),
    ("Prev",      "Sr. Flutter Developer @ ITNovus"),
    ("Education", "MSc IT & Applied Security — Merit"),
    ("Uptime",    "4+ years shipping cross-platform apps"),
    None,  # spacer
    ("Mobile",    "Flutter · Dart · BLoC · Clean Arch"),
    ("Native",    "Swift · CoreBluetooth · WidgetKit"),
    ("Backend",   "Firebase · Cloud Functions · Node · TS"),
    ("On-device", "ML Kit · MediaPipe"),
    ("Payments",  "eSewa · Stripe · StoreKit"),
    None,
    ("Shipped",   "8+ apps live on App Store & Play Store"),
    ("OSS",       "flutter_virtual_tryon — pub.dev"),
    ("Notable",   "Reverse-engineered KTM BCCU BLE protocol"),
    None,
    ("Location",  "Kathmandu, Nepal — UTC+5:45"),
    ("Web",       "roshansah.com.np"),
]

# ---------------------------------------------------------------- styling
W, H = 490, 366
PAD_X = 20
TOP = 30

FS = 10.5           # body font size
LH = 15.2           # line height
KEY_W = 74          # px reserved for the key column

BG      = "#0d1117"
BORDER  = "#30363d"
KEY_C   = "#f0f6fc"   # bright white
VAL_C   = "#9aa4b2"   # muted grey
DIM     = "#6e7681"
BAR     = "#161b22"

STEP = 0.09         # stagger between rows (seconds)
DUR  = 0.42         # per-row animation duration


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">'
)

# ---- styles / keyframes (CSS inside SVG survives GitHub sanitisation)
if STATIC:
    parts.append("<style>.r{opacity:1}</style>")
else:
    parts.append(
        "<style>"
        "@keyframes fin{from{opacity:0;transform:translateX(-8px)}"
        "to{opacity:1;transform:translateX(0)}}"
        ".r{opacity:0;animation:fin .42s ease-out forwards}"
        "@keyframes cur{0%,49%{opacity:1}50%,100%{opacity:0}}"
        ".cursor{animation:cur 1s step-end infinite}"
        "</style>"
    )

# ---- panel
parts.append(f'<rect width="{W}" height="{H}" rx="8" fill="{BG}" stroke="{BORDER}"/>')
parts.append(f'<rect width="{W}" height="24" rx="8" fill="{BAR}"/>')
parts.append(f'<rect y="16" width="{W}" height="8" fill="{BAR}"/>')
parts.append(f'<line x1="0" y1="24" x2="{W}" y2="24" stroke="{BORDER}"/>')

# traffic-light dots, monochrome
for i, cx in enumerate((16, 30, 44)):
    shade = ["#484f58", "#3d444d", "#32383f"][i]
    parts.append(f'<circle cx="{cx}" cy="12" r="4" fill="{shade}"/>')
parts.append(
    f'<text x="{W/2}" y="16" fill="{DIM}" font-size="9.5" text-anchor="middle">'
    f'{USER}@{HOST} — neofetch</text>'
)

delay = 0.0
y = TOP + 14


def anim(d):
    return "" if STATIC else f' style="animation-delay:{d:.2f}s"'


# ---- header line: user@host
parts.append(
    f'<text class="r" x="{PAD_X}" y="{y}" font-size="{FS+1.5}"{anim(delay)}>'
    f'<tspan fill="{KEY_C}" font-weight="bold">{USER}</tspan>'
    f'<tspan fill="{DIM}">@</tspan>'
    f'<tspan fill="{KEY_C}" font-weight="bold">{HOST}</tspan></text>'
)
delay += STEP
y += LH - 2
parts.append(
    f'<text class="r" x="{PAD_X}" y="{y}" font-size="{FS}" fill="{DIM}"{anim(delay)}>'
    f'{"─" * 44}</text>'
)
delay += STEP
y += LH + 2

# ---- rows
for row in ROWS:
    if row is None:
        y += LH * 0.45
        continue
    k, v = row
    parts.append(
        f'<text class="r" x="{PAD_X}" y="{y:.1f}" font-size="{FS}"{anim(delay)}>'
        f'<tspan fill="{KEY_C}" font-weight="bold">{esc(k)}</tspan>'
        f'<tspan fill="{DIM}">:</tspan>'
        f'<tspan x="{PAD_X + KEY_W}" fill="{VAL_C}">{esc(v)}</tspan></text>'
    )
    delay += STEP
    y += LH

# ---- greyscale palette blocks (classic neofetch footer)
y += 6
sw, sh, gap = 22, 9, 4
shades = ["#161b22", "#21262d", "#30363d", "#484f58",
          "#6e7681", "#8b949e", "#b1bac4", "#f0f6fc"]
for i, c in enumerate(shades):
    parts.append(
        f'<rect class="r" x="{PAD_X + i*(sw+gap)}" y="{y:.1f}" width="{sw}" '
        f'height="{sh}" rx="2" fill="{c}"{anim(delay + i*0.03)}/>'
    )
delay += 0.3
y += sh + LH + 1

# ---- trailing prompt with blinking cursor
parts.append(
    f'<text class="r" x="{PAD_X}" y="{y:.1f}" font-size="{FS}"{anim(delay)}>'
    f'<tspan fill="{DIM}">{USER}@{HOST} ~ $ </tspan>'
    f'<tspan class="cursor" fill="{KEY_C}">█</tspan></text>'
)

parts.append("</svg>")

out = "info-card.svg"
with open(out, "w", encoding="utf-8") as f:
    f.write("".join(parts))
print(f"wrote {out}  ({W}x{H})")
