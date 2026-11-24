#!/usr/bin/env python3
"""Boundary inspection sheets: frames on both sides of every detected join plus the strongest undetected suspects.

Usage: 07b_boundary_sheets.py <work_dir> [only=<video-stem>] [max_suspects=16]
Writes <work>/<video>/boundaries_NN.jpg  -- one row per item: [f-2, f-1, f, f+1] (cuts) or [start, 1/3, 2/3, end] (dissolves)
Row label: time, type (CUT / DISSOLVE / FLASH / suspect), hist_d, mad.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FPS = 30
TW = 150
TH = TW * 16 // 9


def font(size):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(p, size) if Path(p).exists() else ImageFont.load_default()


def tile(d, i):
    fp = d / "frames" / f"{max(i, 0):05d}.jpg"
    if not fp.exists():
        return Image.new("RGB", (TW, TH), (0, 0, 0))
    return Image.open(fp).convert("RGB").resize((TW, TH), Image.BILINEAR)


def main():
    root = Path(sys.argv[1])
    only = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "all" else None
    max_sus = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    f = font(13)
    for d in sorted(p for p in root.iterdir() if (p / "shots.json").exists() and (only is None or p.name == only)):
        sj = json.loads((d / "shots.json").read_text())
        with open(d / "frame_metrics.csv") as fh:
            rows = list(csv.DictReader(fh))
        hd = np.array([float(r["hist_d"]) for r in rows])
        mad = np.array([float(r["mad"]) for r in rows])
        inl = np.array([float(r["g_inl"]) for r in rows])
        items = []
        taken = np.zeros(len(rows), bool)
        for b in sj["joins"] + sj.get("inplace_blends", []):
            if b["type"] in ("dissolve", "inplace_blend"):
                a, e = b["from_frame"], b["to_frame"]
                idx = [a, a + (e - a) // 3, a + 2 * (e - a) // 3, e] if e - a >= 3 else [a - 1, a, a + 1, e]
                taken[max(0, a - 3):e + 4] = True
                name = "DISSOLVE" if b["type"] == "dissolve" else "in-place blend"
                col = (90, 200, 255) if b["type"] == "dissolve" else (230, 130, 255)
                items.append((b["frame"], f"{b['t']:.2f}s {name} {b['length_frames']}f res={b.get('blend_residual')} sc={b.get('struct_corr')}", idx, col))
            else:
                c = b["frame"]
                taken[max(0, c - 4):c + 5] = True
                items.append((c, f"{b['t']:.2f}s {b['type'].upper()} hd={b.get('hist_d')} chg={b.get('change')}", [c - 2, c - 1, c, c + 1], (120, 255, 120)))
        score = hd * mad * (1.2 - inl)
        score[taken] = 0
        sus = []
        for _ in range(max_sus):
            k = int(np.argmax(score))
            if score[k] <= 0.6:
                break
            sus.append(k)
            score[max(0, k - 8):k + 9] = 0
        for k in sorted(sus):
            items.append((k, f"{k / FPS:.2f}s suspect hd={hd[k]:.2f} mad={mad[k]:.1f} inl={inl[k]:.2f}", [k - 2, k - 1, k, k + 1], (255, 170, 60)))
        items.sort(key=lambda x: x[0])
        per_row, pad, lab_h = 3, 6, 18
        cell_w = 4 * TW + pad * 2
        rows_per_page = 5
        for page, s in enumerate(range(0, len(items), per_row * rows_per_page), 1):
            chunk = items[s:s + per_row * rows_per_page]
            nrows = (len(chunk) + per_row - 1) // per_row
            sheet = Image.new("RGB", (per_row * cell_w, nrows * (TH + lab_h + pad)), (18, 18, 18))
            dr = ImageDraw.Draw(sheet)
            for n, (_, label, idx, col) in enumerate(chunk):
                x0 = (n % per_row) * cell_w + pad
                y0 = (n // per_row) * (TH + lab_h + pad)
                dr.text((x0, y0 + 2), label, fill=col, font=f)
                for j, i in enumerate(idx):
                    sheet.paste(tile(d, i), (x0 + j * TW, y0 + lab_h))
                    dr.text((x0 + j * TW + 3, y0 + lab_h + 2), f"f{i}", fill=(255, 235, 60), font=f)
                dr.line([(x0 + 2 * TW, y0 + lab_h), (x0 + 2 * TW, y0 + lab_h + TH)], fill=col, width=2)
            sheet.save(d / f"boundaries_{page:02d}.jpg", quality=85)
        print(d.name, len(items), "items", f"({len(sus)} suspects)")


if __name__ == "__main__":
    main()
