#!/usr/bin/env python3
"""Grid of frames taken from different videos (for cross-video visual comparison).

Usage: grid.py <work_dir> <out.jpg> <tile_w> <cols> NN:frame [NN:frame ...]      NN = two-digit video prefix
       grid.py --crop x0,y0,x1,y1 <work_dir> <out.jpg> <tile_w> <cols> NN:frame ...
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    args = sys.argv[1:]
    crop = None
    if args[0] == "--crop":
        crop = [float(v) for v in args[1].split(",")]
        args = args[2:]
    root, out, tile_w, cols = Path(args[0]), args[1], int(args[2]), int(args[3])
    fp = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(fp, max(13, tile_w // 14)) if Path(fp).exists() else ImageFont.load_default()
    tiles = []
    for spec in args[4:]:
        nn, fr = spec.split(":")
        d = next(p for p in sorted(root.iterdir()) if p.name.startswith(nn + "_"))
        im = Image.open(d / "frames" / f"{int(fr):05d}.jpg").convert("RGB")
        if crop:
            w, h = im.size
            im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
        th = round(im.size[1] * tile_w / im.size[0])
        tiles.append((f"{nn} f{fr}", im.resize((tile_w, th), Image.LANCZOS)))
    th = tiles[0][1].size[1]
    rows = (len(tiles) + cols - 1) // cols
    pad = 4
    sheet = Image.new("RGB", (cols * (tile_w + pad) + pad, rows * (th + pad) + pad), (25, 25, 25))
    dr = ImageDraw.Draw(sheet)
    for n, (label, im) in enumerate(tiles):
        x = pad + (n % cols) * (tile_w + pad)
        y = pad + (n // cols) * (th + pad)
        sheet.paste(im, (x, y))
        tw = dr.textlength(label, font=font)
        dr.rectangle([x, y, x + tw + 8, y + font.size + 6], fill=(0, 0, 0))
        dr.text((x + 4, y + 2), label, fill=(255, 235, 60), font=font)
    sheet.save(out, quality=88)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
