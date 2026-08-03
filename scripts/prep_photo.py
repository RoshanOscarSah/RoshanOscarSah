#!/usr/bin/env python3
"""
prep_photo.py — prepares a photo for ASCII conversion.

A flatly-lit face converts to a dark, unreadable blob. Three fixes:
  1. Remove the background (rembg) so only the subject remains.
     -> OPTIONAL. If rembg isn't installed we fall back to a centre-weighted
        vignette, which works fine for a plain-background headshot.
  2. Boost local contrast with CLAHE so a flat face gains real
     highlights and shadows.
  3. Composite onto pure WHITE, so background maps to the blank end of the
     ASCII ramp (white -> space) and only the subject prints.

Usage:  python scripts/prep_photo.py source-photo.jpg
Output: source-prepped.png  (grayscale)
"""
import sys
import numpy as np
import cv2
from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else "source-photo.jpg"
OUT = "source-prepped.png"

# how hard to push local contrast; raise for very flat lighting
CLAHE_CLIP = 3.4
CLAHE_GRID = (8, 8)
# final gamma: <1 brightens midtones (less dense ASCII), >1 darkens
GAMMA = 1.02


def load_rgba(path):
    """Load image, removing the background if rembg is available."""
    try:
        from rembg import remove          # optional, heavy dependency
        with open(path, "rb") as f:
            cut = remove(f.read())
        import io
        img = Image.open(io.BytesIO(cut)).convert("RGBA")
        print("background removed with rembg")
        return img, True
    except ImportError:
        print("rembg not installed — using OpenCV GrabCut instead "
              "(`pip install rembg` gives a cleaner cut-out)")
        return Image.open(path).convert("RGBA"), False
    except Exception as e:                # rembg present but failed
        print(f"rembg failed ({e}) — falling back to GrabCut")
        return Image.open(path).convert("RGBA"), False


def grabcut_alpha(rgb, iters=6):
    """
    Segment the subject with GrabCut, seeded by a centred rectangle.
    Returns a soft 0..1 alpha mask. Local — no model download required.
    """
    h, w = rgb.shape[:2]
    # generous rect: subject assumed centred and filling most of the frame
    rect = (int(w * 0.06), int(h * 0.02), int(w * 0.88), int(h * 0.97))
    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(rgb, mask, rect, bgd, fgd, iters, cv2.GC_INIT_WITH_RECT)

    a = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1.0, 0.0)

    # keep only the largest connected component (drops stray background blobs)
    m8 = (a * 255).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m8, 8)
    if n > 1:
        biggest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        a = (lab == biggest).astype(np.float32)

    # close small holes, then feather the edge so ASCII doesn't get a hard cut
    a8 = (a * 255).astype(np.uint8)
    a8 = cv2.morphologyEx(a8, cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    a8 = cv2.GaussianBlur(a8, (0, 0), 3.5)
    a = np.clip(a8.astype(np.float32) / 255.0, 0, 1)

    # Fade alpha to 0 at the frame edges. Where the subject is clipped by the
    # crop (usually the shoulders at the bottom) a hard alpha edge prints as a
    # solid dark band in ASCII; this dissolves it into the white background.
    fade = max(6, int(min(h, w) * 0.035))
    ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
    edge = np.ones((h, w), np.float32)
    edge[:fade, :] *= ramp[:, None]
    edge[-fade:, :] *= ramp[::-1][:, None]
    edge[:, :fade] *= ramp[None, :]
    edge[:, -fade:] *= ramp[::-1][None, :]
    return a * edge


def main():
    img, had_alpha = load_rgba(SRC)

    # square-ish crop around the centre so the face fills the frame
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = int((h - side) * 0.35)          # bias upward: heads sit high
    img = img.crop((left, top, left + side, top + side))

    rgb = np.array(img.convert("RGB"))
    alpha = np.array(img.split()[-1]).astype(np.float32) / 255.0

    if not had_alpha:
        print("segmenting subject with GrabCut…")
        alpha = grabcut_alpha(rgb)
        had_alpha = True

    # --- local contrast (CLAHE on the L channel of LAB)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_GRID)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)

    # --- normalise to full range so the ramp is fully used
    lo, hi = np.percentile(gray, 2), np.percentile(gray, 98)
    if hi > lo:
        gray = np.clip((gray - lo) / (hi - lo), 0, 1) * 255.0

    # --- gamma
    gray = np.power(gray / 255.0, GAMMA) * 255.0

    if not had_alpha:
        # vignette: fade corners to white so only the centre subject prints
        yy, xx = np.mgrid[0:gray.shape[0], 0:gray.shape[1]]
        cy, cx = gray.shape[0] / 2, gray.shape[1] / 2
        r = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
        alpha = np.clip(1.35 - r * 1.15, 0, 1)

    # --- composite onto WHITE using alpha
    out = gray * alpha + 255.0 * (1.0 - alpha)
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out, mode="L").save(OUT)
    print(f"wrote {OUT}  ({out.shape[1]}x{out.shape[0]})")
    print("Inspect it: the face should show clear light/dark separation "
          "and the background should be near-white.")


if __name__ == "__main__":
    main()
