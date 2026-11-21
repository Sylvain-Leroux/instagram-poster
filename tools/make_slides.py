#!/usr/bin/env python3
"""Rendert Karussell-Folien (1080x1350 JPEG) aus einer JSON-Datei.

Aufruf: python3 make_slides.py slides.json ausgabe-ordner/

slides.json:
{
  "handle": "@deinaccount",
  "slides": [
    {"title": "Hook-Satz", "text": "Untertitel", "sketch": "palate_top"},
    {"title": "Kernaussage", "text": "Erklaerung", "sketch": "palate_section:mittel"},
    {"title": "Vergleich", "sketch": "palate_sections"},
    {"title": "Quellen", "text": "Autor (Jahr) ...", "small": true}
  ]
}

Skizzen (eigene, schematische Zeichnungen, nicht massstabsgetreu):
  palate_top               Gaumen von unten mit A. palatina major
  palate_section:hoch      Querschnitt, hoher Gaumen (auch: mittel, flach)
  palate_sections          drei Querschnitte nebeneinander mit mm-Angaben
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
S = 2  # Supersampling fuer glatte Kanten
BG = (255, 214, 0)        # Gelb
INK = (12, 12, 12)        # Schwarz
ACCENT = (12, 12, 12)     # Balken, Zahlen
MUTED = (70, 60, 20)
HIL = (255, 214, 0)       # Hervorhebung in Skizzen (gelb auf dunkel)
BONE = (28, 28, 28)
BONE_EDGE = (12, 12, 12)
MUCOSA = (95, 95, 95)
TOOTH = (250, 250, 250)
PAD = 96

FONT_DIR = Path("/usr/share/fonts/opentype/inter")


def font(name, size):
    p = FONT_DIR / name
    if p.exists():
        return ImageFont.truetype(str(p), size * S)
    return ImageFont.truetype("DejaVuSans.ttf", size * S)


def wrap(draw, text, fnt, max_w):
    lines = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w in words:
            test = f"{line} {w}".strip()
            if draw.textlength(test, font=fnt) <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = w
        lines.append(line)
    return lines


# ---------- Skizzen ----------

VAULT_DEPTH = {"hoch": 0.60, "mittel": 0.42, "flach": 0.24}
VAULT_MM = {"hoch": "17 mm", "mittel": "12 mm", "flach": "7 mm"}


def vault_y(u, base, depth, p=2.6):
    u = min(1.0, abs(u))
    return base - depth * (1 - u ** p) ** (1 / p)


def draw_section(d, x, y, w, h, kind, label=True, big=False):
    """Querschnitt (frontal) durch Oberkiefer mit Gaumengewoelbe."""
    lw = 3 * S
    gum = y + h * 0.62          # Hoehe Gingivarand
    xl, xr = x + w * 0.27, x + w * 0.73
    xc, half = (xl + xr) / 2, (xr - xl) / 2
    depth = h * VAULT_DEPTH[kind] * 0.85

    # Knochen
    outer = [(x + w * 0.05, y + h * 0.05), (x + w * 0.95, y + h * 0.05),
             (x + w * 0.95, gum - h * 0.05), (x + w * 0.80, gum + h * 0.02)]
    inner = []
    steps = 60
    for i in range(steps + 1):
        u = 1 - 2 * i / steps
        inner.append((xc + u * half, vault_y(u, gum, depth)))
    outer += inner + [(x + w * 0.20, gum + h * 0.02), (x + w * 0.05, gum - h * 0.05)]
    d.polygon(outer, fill=BONE, outline=BONE_EDGE)

    # Schleimhaut entlang des Gewoelbes
    d.line(inner, fill=MUCOSA, width=10 * S if big else 7 * S, joint="curve")

    # Zaehne (Molaren) unter den Alveolarfortsaetzen
    for cx in (x + w * 0.135, x + w * 0.865):
        tw = w * 0.15
        d.rounded_rectangle([cx - tw / 2, gum - h * 0.02, cx + tw / 2, y + h * 0.95],
                            radius=int(tw * 0.25), fill=TOOTH, outline=BONE_EDGE, width=lw // 2)

    # Gefaess-Nerven-Buendel am Uebergang senkrechte/waagerechte Wand
    for u in (-0.62, 0.62):
        bx = xc + u * half
        by = vault_y(u, gum, depth) + 6 * S
        r = (14 if big else 11) * S
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=HIL, outline=BONE, width=3 * S)

    # Masslinie links: Gingivarand -> Buendel
    bx = xc - 0.62 * half
    by = vault_y(-0.62, gum, depth) + 6 * S
    mx = xl - w * (0.20 if label else 0.06)
    d.line([(mx, gum), (mx, by)], fill=HIL, width=lw)
    for yy in (gum, by):
        d.line([(mx - 10 * S, yy), (mx + 10 * S, yy)], fill=HIL, width=lw)
    if label:
        f = font("Inter-Bold.otf", 30 if big else 26)
        txt = VAULT_MM[kind]
        d.text((mx + 18 * S, (gum + by) / 2 - 16 * S), txt, font=f, fill=HIL)


def arch_points(cx, top, a, b, leg, n=120):
    """U-foermiger Bogen: vorne Halbellipse, hinten gerade Schenkel. Rueckgabe von links hinten nach rechts hinten."""
    pts = []
    for i in range(n // 4, 0, -1):
        pts.append((cx - a - (i / (n // 4)) * a * 0.10, top + b + leg * i / (n // 4)))
    for i in range(n + 1):
        th = -math.pi / 2 + math.pi * i / n
        pts.append((cx + a * math.sin(th), top + b * (1 - math.cos(th))))
    for i in range(1, n // 4 + 1):
        pts.append((cx + a + (i / (n // 4)) * a * 0.10, top + b + leg * i / (n // 4)))
    return pts


def along(pts, frac):
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    target, acc = sum(seg) * frac, 0.0
    for i, L in enumerate(seg):
        if acc + L >= target:
            t = (target - acc) / L if L else 0
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
                    pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
        acc += L
    return pts[-1]


def draw_palate_top(d, x, y, w, h):
    """Gaumen von unten: Zahnbogen, Raphe, A. palatina major (schematisch)."""
    cx, top = x + w / 2, y + h * 0.05
    teeth_arch = arch_points(cx, top, w * 0.36, h * 0.40, h * 0.50)
    palate = arch_points(cx, top + h * 0.03, w * 0.33, h * 0.40, h * 0.50)
    d.polygon(palate, fill=MUCOSA)
    # Raphe
    yy = top + h * 0.14
    while yy < y + h * 0.95:
        d.line([(cx, yy), (cx, yy + 10 * S)], fill=(150, 150, 150), width=3 * S)
        yy += 24 * S
    # Zaehne: Schneidezaehne klein, Molaren gross
    n = 16
    for i in range(n):
        fpos = (i + 0.5) / n
        tx, ty = along(teeth_arch, fpos)
        k = abs(i - (n - 1) / 2) / ((n - 1) / 2)
        r = (20 + 18 * k ** 1.5) * S
        d.ellipse([tx - r, ty - r, tx + r, ty + r], fill=TOOTH, outline=BONE_EDGE, width=2 * S)
    # Arterie: vom Foramen palatinum majus (Hoehe 2./3. Molar) nach vorne zum Foramen incisivum
    inc = (cx, top + h * 0.12)
    for side in (-1, 1):
        art = arch_points(cx, top + h * 0.10, w * 0.27, h * 0.34, h * 0.40)
        half_pts = art[: len(art) // 2] if side < 0 else art[len(art) // 2:][::-1]
        half_pts = [p for p in half_pts if p[1] > inc[1] + h * 0.04] + [inc]
        d.line(half_pts, fill=HIL, width=7 * S, joint="curve")
        fx, fy = half_pts[0]
        r = 15 * S
        d.ellipse([fx - r, fy - r, fx + r, fy + r], fill=BONE, outline=HIL, width=5 * S)
    r = 11 * S
    d.ellipse([inc[0] - r, inc[1] - r, inc[0] + r, inc[1] + r], fill=BONE, outline=HIL, width=4 * S)


def draw_sketch(d, name, box):
    x, y, w, h = box
    if name == "palate_top":
        side = min(w, h)
        draw_palate_top(d, x + (w - side) / 2, y, side, side)
    elif name.startswith("palate_section:"):
        kind = name.split(":", 1)[1]
        sw = min(w, h * 1.25)
        draw_section(d, x + (w - sw) / 2, y, sw, sw / 1.25, kind, big=True)
    elif name == "palate_sections":
        f = font("Inter-SemiBold.otf", 30)
        rows = ["hoch", "mittel", "flach"]
        rh = h / 3
        for i, kind in enumerate(rows):
            ry = y + i * rh
            sw = min(w * 0.62, (rh - 10 * S) * 1.25)
            draw_section(d, x + w - sw, ry, sw, sw / 1.25, kind, label=False)
            d.text((x, ry + rh * 0.22), {"hoch": "Hoher Gaumen", "mittel": "Mittlerer Gaumen",
                                         "flach": "Flacher Gaumen"}[kind], font=f, fill=INK)
            fb = font("Inter-Bold.otf", 64)
            d.text((x, ry + rh * 0.22 + 46 * S), "ca. " + VAULT_MM[kind], font=fb, fill=ACCENT)


# ---------- Folien ----------

def render(slide, idx, total, handle, is_hook):
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)
    pad = PAD * S
    max_w = W * S - 2 * pad
    small = slide.get("small", False)
    sketch = slide.get("sketch")

    title_size = 88 if is_hook else (54 if small else 68)
    text_size = 32 if small else 40
    f_title = font("Inter-ExtraBold.otf" if (FONT_DIR / "Inter-ExtraBold.otf").exists()
                   else "Inter-Bold.otf", title_size)
    f_text = font("Inter-Regular.otf", text_size)
    f_meta = font("Inter-Medium.otf", 30)

    # Akzent-Balken oben
    d.rectangle([pad, pad, pad + 140 * S, pad + 14 * S], fill=ACCENT)

    title_lines = wrap(d, slide.get("title", ""), f_title, max_w)
    text_lines = wrap(d, slide.get("text", ""), f_text, max_w) if slide.get("text") else []
    t_lh, x_lh = int(title_size * 1.15 * S), int(text_size * 1.45 * S)
    block_h = len(title_lines) * t_lh + (40 * S + len(text_lines) * x_lh if text_lines else 0)

    if sketch or small:
        y = pad + 90 * S
    else:
        y = max(pad + 90 * S, (H * S - block_h) // 2 - 40 * S)

    for line in title_lines:
        d.text((pad, y), line, font=f_title, fill=INK)
        y += t_lh
    if text_lines:
        y += 40 * S
        for line in text_lines:
            d.text((pad, y), line, font=f_text, fill=MUTED if small else INK)
            y += x_lh

    if sketch:
        top = y + 50 * S
        bottom = H * S - pad - 80 * S
        draw_sketch(d, sketch, (pad, top, max_w, bottom - top))
        cap = slide.get("sketch_caption", "Schematische Skizze, nicht maßstabsgetreu")
        f_cap = font("Inter-Regular.otf", 22)
        d.text((pad, bottom + 14 * S), cap, font=f_cap, fill=MUTED)

    d.text((pad, H * S - pad - 30 * S), handle, font=f_meta, fill=MUTED)
    counter = f"{idx}/{total}"
    d.text((W * S - pad - d.textlength(counter, font=f_meta), H * S - pad - 30 * S),
           counter, font=f_meta, fill=MUTED)
    if is_hook and total > 1:
        hint = "Wischen →"
        d.text((W * S - pad - d.textlength(hint, font=f_meta), pad - 8 * S), hint,
               font=f_meta, fill=ACCENT)
    return img.resize((W, H), Image.LANCZOS)


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    slides = spec["slides"]
    for i, s in enumerate(slides, 1):
        img = render(s, i, len(slides), spec.get("handle", ""), i == 1)
        img.save(out / f"{i:02d}.jpg", "JPEG", quality=92)
    print(f"{len(slides)} Folien in {out}")


if __name__ == "__main__":
    main()
