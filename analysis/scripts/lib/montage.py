#!/usr/bin/env python3
"""Montage helper for visual inspection.

Usage:
  montage.py <out.jpg> <tile_w> <cols> <video_dir> <frame_idx|a-b|a-b:step> [...]   frames by index
  montage.py --crop x0,y0,x1,y1 <out.jpg> <tile_w> <cols> <video_dir> <spec> [...]  crop (fractions 0-1) first
Each tile is labelled "<frame> <seconds>".
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FPS = 30


def font(size):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(p, size) if Path(p).exists() else ImageFont.load_default()


def parse(spec):
    step = 1
    if ":" in spec:
        spec, s = spec.split(":")
        step = int(s)
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1, step))
    return [int(spec)]


def main():
    args = sys.argv[1:]
    crop = None
    if args[0] == "--crop":
        crop = [float(v) for v in args[1].split(",")]
        args = args[2:]
    out, tile_w, cols, vdir = args[0], int(args[1]), int(args[2]), Path(args[3])
    idx = [i for s in args[4:] for i in parse(s)]
    tiles = []
    for i in idx:
        fp = vdir / "frames" / f"{i:05d}.jpg"
        if not fp.exists():
            continue
        im = Image.open(fp).convert("RGB")
        if crop:
            w, h = im.size
            im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
        th = round(im.size[1] * tile_w / im.size[0])
        tiles.append((i, im.resize((tile_w, th), Image.LANCZOS)))
    if not tiles:
        sys.exit("no frames")
    th = tiles[0][1].size[1]
    rows = (len(tiles) + cols - 1) // cols
    pad = 4
    sheet = Image.new("RGB", (cols * (tile_w + pad) + pad, rows * (th + pad) + pad), (25, 25, 25))
    dr = ImageDraw.Draw(sheet)
    f = font(max(13, tile_w // 16))
    for n, (i, im) in enumerate(tiles):
        x = pad + (n % cols) * (tile_w + pad)
        y = pad + (n // cols) * (th + pad)
        sheet.paste(im, (x, y))
        label = f"f{i} {i / FPS:.2f}s"
        tw = dr.textlength(label, font=f)
        dr.rectangle([x, y, x + tw + 8, y + f.size + 6], fill=(0, 0, 0))
        dr.text((x + 4, y + 2), label, fill=(255, 235, 60), font=f)
    sheet.save(out, quality=90)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
