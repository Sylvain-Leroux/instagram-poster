#!/usr/bin/env python3
"""Rendert Karussell-Folien (1080x1350 JPEG) aus einer JSON-Datei.

Aufruf: python3 make_slides.py slides.json ausgabe-ordner/

slides.json:
{
  "handle": "@deinaccount",
  "slides": [
    {"title": "Hook-Satz", "text": "optionaler Untertitel"},
    {"title": "Kernaussage", "text": "Erklaerung in 1-3 Saetzen"},
    {"title": "Quellen", "text": "Autor (Jahr). Journal. DOI ...", "small": true}
  ]
}
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
BG = (247, 243, 236)
INK = (28, 33, 40)
ACCENT = (32, 110, 100)
MUTED = (110, 116, 124)
PAD = 96

FONT_DIR = Path("/usr/share/fonts/opentype/inter")


def font(name, size):
    for p in (FONT_DIR / name, Path(name)):
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.truetype("DejaVuSans.ttf", size)


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


def render(slide, idx, total, handle, is_hook):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    max_w = W - 2 * PAD
    small = slide.get("small", False)

    title_size = 92 if is_hook else (54 if small else 72)
    text_size = 34 if small else 42
    f_title = font("Inter-Bold.otf", title_size)
    f_text = font("Inter-Regular.otf", text_size)
    f_meta = font("Inter-Medium.otf", 30)

    d.rectangle([PAD, PAD, PAD + 120, PAD + 12], fill=ACCENT)

    title_lines = wrap(d, slide.get("title", ""), f_title, max_w)
    text_lines = wrap(d, slide.get("text", ""), f_text, max_w) if slide.get("text") else []
    t_lh, x_lh = int(title_size * 1.18), int(text_size * 1.45)
    block_h = len(title_lines) * t_lh + (48 + len(text_lines) * x_lh if text_lines else 0)
    y = max(PAD + 80, (H - block_h) // 2 - 40) if not small else PAD + 110

    for line in title_lines:
        d.text((PAD, y), line, font=f_title, fill=INK)
        y += t_lh
    if text_lines:
        y += 48
        for line in text_lines:
            d.text((PAD, y), line, font=f_text, fill=INK if not small else MUTED)
            y += x_lh

    d.text((PAD, H - PAD - 30), handle, font=f_meta, fill=MUTED)
    counter = f"{idx}/{total}"
    d.text((W - PAD - d.textlength(counter, font=f_meta), H - PAD - 30),
           counter, font=f_meta, fill=MUTED)
    if is_hook and total > 1:
        hint = "Wischen →"
        d.text((W - PAD - d.textlength(hint, font=f_meta), PAD - 6), hint,
               font=f_meta, fill=ACCENT)
    return img


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    slides = spec["slides"]
    for i, s in enumerate(slides, 1):
        img = render(s, i, len(slides), spec.get("handle", ""), i == 1)
        img.save(out / f"{i:02d}.jpg", "JPEG", quality=90)
    print(f"{len(slides)} Folien in {out}")


if __name__ == "__main__":
    main()
