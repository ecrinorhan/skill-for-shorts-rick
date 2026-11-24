#!/usr/bin/env python3
"""Contact sheets from the 30 fps frame dumps.

Usage: 03_contact_sheets.py <work_dir> [step_s=1.0] [cols=10] [tile_w=216] [suffix=]
Writes <work>/<video>/contact{suffix}_NN.jpg (pages of up to 60 tiles) with a timestamp on every tile.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FPS = 30


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def sheet(frames, times, cols, tile_w, out):
    tile_h = tile_w * 16 // 9
    rows = (len(frames) + cols - 1) // cols
    pad = 4
    img = Image.new("RGB", (cols * (tile_w + pad) + pad, rows * (tile_h + pad) + pad), (20, 20, 20))
    dr = ImageDraw.Draw(img)
    f = font(max(12, tile_w // 12))
    for i, (fp, t) in enumerate(zip(frames, times)):
        im = Image.open(fp).convert("RGB").resize((tile_w, tile_h), Image.LANCZOS)
        x = pad + (i % cols) * (tile_w + pad)
        y = pad + (i // cols) * (tile_h + pad)
        img.paste(im, (x, y))
        label = f"{t:05.2f}"
        tw = dr.textlength(label, font=f)
        dr.rectangle([x, y, x + tw + 8, y + f.size + 6], fill=(0, 0, 0))
        dr.text((x + 4, y + 2), label, fill=(255, 235, 60), font=f)
    img.save(out, quality=88)


def main():
    root = Path(sys.argv[1])
    step = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    tile_w = int(sys.argv[4]) if len(sys.argv) > 4 else 216
    suffix = sys.argv[5] if len(sys.argv) > 5 else ""
    per_page = cols * 6
    for d in sorted(p for p in root.iterdir() if (p / "frames").is_dir()):
        allf = sorted((d / "frames").glob("*.jpg"))
        idx = [int(round(i * step * FPS)) for i in range(int(len(allf) / FPS / step) + 1)]
        idx = [i for i in idx if i < len(allf)]
        frames = [allf[i] for i in idx]
        times = [i / FPS for i in idx]
        for page, s in enumerate(range(0, len(frames), per_page), 1):
            out = d / f"contact{suffix}_{page:02d}.jpg"
            sheet(frames[s:s + per_page], times[s:s + per_page], cols, tile_w, out)
        print(d.name, len(frames), "tiles")


if __name__ == "__main__":
    main()
