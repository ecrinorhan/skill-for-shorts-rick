#!/usr/bin/env python3
"""Burned-in caption track: detect, segment into caption events, OCR, measure geometry/colour/animation.

Usage: 08_captions.py <work_dir> [jobs=6] [only=<video-stem>]
Writes <work>/<video>/captions_frames.csv   one row per frame (bbox, fill colour, glyph count)
       <work>/<video>/captions.json         caption events: text, on/off frame, size, position, colours, pop-in curve

Detection: a caption glyph is a bright connected component (max(R,G,B) >= 215) whose boundary is almost entirely
ringed by dark stroke pixels (max(R,G,B) <= 70). Components are kept only inside the caption band and when they
sit on a common line. Sizes are reported in px at 1080x1920 and in % of frame height.
"""
import csv
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

FPS = 30.0
BAND = (0.60, 0.82)          # search band, fraction of frame height
K9 = np.ones((9, 9), np.uint8)
K3 = np.ones((3, 3), np.uint8)


def detect(frame_bgr, line=None):
    """line=(top_px, bottom_px) restricts glyphs to the calibrated caption line (full-frame pixel rows)."""
    H, W = frame_bgr.shape[:2]
    y0, y1 = int(BAND[0] * H), int(BAND[1] * H)
    band = frame_bgr[y0:y1]
    mx = band.max(axis=2)
    bright = (mx >= 215).astype(np.uint8)
    dark = (mx <= 70).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(bright, connectivity=8)
    if n <= 1:
        return None
    edge = (bright & (1 - cv2.erode(bright, K3))).astype(bool)
    near_dark = cv2.dilate(dark, K9).astype(bool)
    lab_e = lab[edge]
    tot = np.bincount(lab_e, minlength=n).astype(np.float32)
    hit = np.bincount(lab_e[near_dark[edge]], minlength=n).astype(np.float32)
    frac = hit / np.maximum(tot, 1)
    # second test: the ring 2-4 px outside a glyph must be stroke-dark (rejects pebbles, sparkles, highlights).
    # The first pixel outside is anti-aliased grey, so it is skipped. Measured: glyphs 0.88-1.00, non-glyphs <0.4.
    lab16 = lab.astype(np.uint16) if n < 65535 else np.minimum(lab, 65534).astype(np.uint16)
    dil = cv2.dilate(lab16, np.ones((9, 9), np.uint8))
    inner = cv2.dilate(bright, K3)
    ring_px = (dil > 0) & (inner == 0)
    ring_lab = dil[ring_px]
    rtot = np.bincount(ring_lab, minlength=n).astype(np.float32)[:n]
    rdark = np.bincount(ring_lab[dark[ring_px].astype(bool)], minlength=n).astype(np.float32)[:n]
    ring_frac = rdark / np.maximum(rtot, 1)
    hs, ws, areas = stats[:, cv2.CC_STAT_HEIGHT], stats[:, cv2.CC_STAT_WIDTH], stats[:, cv2.CC_STAT_AREA]
    glyph = (frac >= 0.85) & (ring_frac >= 0.72)
    ok = glyph & (hs >= 12) & (hs <= 150) & (ws <= 200) & (areas >= 30)
    if line is not None:
        tops = stats[:, cv2.CC_STAT_TOP] + y0
        inside = (tops >= line[0]) & (tops + hs <= line[1])
        ok &= inside
        ok |= glyph & (areas >= 12) & (hs < 40) & inside  # dots, commas, apostrophes
    ok[0] = False
    idx = np.where(ok)[0]
    if len(idx) == 0:
        return None
    # letters vs. small marks: marks (punctuation) only count when they hug a letter
    min_letter_h = 0.55 * (line[2] if line is not None and len(line) > 2 else np.percentile(hs[idx], 90))
    letters = idx[hs[idx] >= min_letter_h]
    if len(letters) == 0:
        return None
    marks = idx[hs[idx] < min_letter_h]
    if len(marks):
        lx0 = stats[letters, cv2.CC_STAT_LEFT]
        lx1 = lx0 + stats[letters, cv2.CC_STAT_WIDTH]
        keep_m = []
        for mk in marks:
            mx0 = stats[mk, cv2.CC_STAT_LEFT]
            mx1 = mx0 + stats[mk, cv2.CC_STAT_WIDTH]
            gap = np.minimum(np.abs(mx0 - lx1), np.abs(lx0 - mx1)).min()
            overl = ((mx0 < lx1) & (mx1 > lx0)).any()
            if overl or gap <= 0.35 * min_letter_h / 0.55:
                keep_m.append(mk)
        idx = np.concatenate([letters, np.array(keep_m, dtype=letters.dtype)])
    else:
        idx = letters
    # keep the components that share a text line: tallest cluster around the median centre-y of big glyphs
    cy = cent[idx, 1]
    big = idx[hs[idx] >= 0.6 * np.percentile(hs[idx], 90)]
    line_y = np.median(cent[big, 1])
    line_h = np.percentile(hs[big], 90)
    keep = idx[np.abs(cy - line_y) <= 0.75 * line_h]
    if len(keep) == 0:
        return None
    # drop far-away stragglers: sort by x and cut where the gap exceeds 2.2 glyph heights
    order = keep[np.argsort(stats[keep, cv2.CC_STAT_LEFT])]
    groups, cur = [], [order[0]]
    for a, b in zip(order[:-1], order[1:]):
        gap = stats[b, cv2.CC_STAT_LEFT] - (stats[a, cv2.CC_STAT_LEFT] + stats[a, cv2.CC_STAT_WIDTH])
        if gap > 2.2 * line_h:
            groups.append(cur)
            cur = [b]
        else:
            cur.append(b)
    groups.append(cur)
    # choose the group closest to the horizontal centre
    def gcx(g):
        return 0.5 * (stats[g[0], cv2.CC_STAT_LEFT] + stats[g[-1], cv2.CC_STAT_LEFT] + stats[g[-1], cv2.CC_STAT_WIDTH])
    g = min(groups, key=lambda g: abs(gcx(g) - W / 2))
    g = np.array(g)
    x0 = int(stats[g, cv2.CC_STAT_LEFT].min())
    x1 = int((stats[g, cv2.CC_STAT_LEFT] + stats[g, cv2.CC_STAT_WIDTH]).max())
    ty0 = int(stats[g, cv2.CC_STAT_TOP].min())
    ty1 = int((stats[g, cv2.CC_STAT_TOP] + stats[g, cv2.CC_STAT_HEIGHT]).max())
    mask = np.isin(lab, g)
    if abs((x0 + x1) / 2 - W / 2) > 0.22 * W or mask.sum() < 150:
        return None
    fill = band[mask].astype(np.float32).mean(axis=0)  # BGR
    ring = cv2.dilate(mask.astype(np.uint8), K9).astype(bool) & ~mask
    stroke = band[ring].astype(np.float32).mean(axis=0)
    return {
        "x0": x0, "x1": x1, "y0": ty0 + y0, "y1": ty1 + y0, "n": int(len(g)), "area": int(mask.sum()),
        "fill": fill[::-1], "stroke": stroke[::-1], "mask": mask[ty0:ty1, x0:x1], "line_h": float(line_h),
    }


def ocr(mask):
    pad = 24
    img = np.full((mask.shape[0] + 2 * pad, mask.shape[1] + 2 * pad), 255, np.uint8)
    img[pad:-pad, pad:-pad][mask] = 0
    img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    with tempfile.NamedTemporaryFile(suffix=".png") as tf:
        cv2.imwrite(tf.name, img)
        for psm in ("7", "8", "13"):   # line, then single word, then raw line for very short captions
            p = subprocess.run(["tesseract", tf.name, "stdout", "--psm", psm, "-l", "eng"], capture_output=True, text=True)
            txt = p.stdout.strip()
            if any(ch.isalnum() for ch in txt):
                return txt
    return ""


def profile(mask, bins=48):
    col = mask.mean(axis=0).astype(np.float32)
    xs = np.linspace(0, len(col) - 1, bins)
    return np.interp(xs, np.arange(len(col)), col)


def calibrate_line(frames):
    """Find the caption line from every 6th frame: most common glyph-row top and height."""
    tops, hts = [], []
    for fp in frames[::6]:
        det = detect(cv2.imread(str(fp)))
        if det is not None and det["n"] >= 2 and (det["y1"] - det["y0"]) < 110:
            tops.append(det["y0"])
            hts.append(det["y1"] - det["y0"])
    if len(tops) < 10:
        return None
    tv, tc = np.unique(np.round(np.array(tops) / 2) * 2, return_counts=True)
    top = float(tv[tc.argmax()])
    sel = np.array(hts)[np.abs(np.array(tops) - top) <= 3]
    hv, hc = np.unique(sel, return_counts=True)
    h = float(hv[hc.argmax()])
    return top, h, round(float(tc.max() / len(tops)), 3)


def one_video(d: Path):
    frames = sorted((d / "frames").glob("*.jpg"))
    cal = calibrate_line(frames)
    line = (cal[0] - 14, cal[0] + 1.32 * cal[1] + 10, cal[1]) if cal else None
    per = []
    for i, fp in enumerate(frames):
        im = cv2.imread(str(fp))
        det = detect(im, line)
        per.append(det)
    H, W = 1920, 1080
    # frame table
    with open(d / "captions_frames.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["f", "t", "has", "x0", "y0", "x1", "y1", "n_glyphs", "area", "fill_r", "fill_g", "fill_b", "stroke_r", "stroke_g", "stroke_b"])
        for i, det in enumerate(per):
            if det is None:
                w.writerow([i, round(i / FPS, 4), 0] + [""] * 12)
            else:
                w.writerow([i, round(i / FPS, 4), 1, det["x0"], det["y0"], det["x1"], det["y1"], det["n"], det["area"],
                            *[round(float(v), 1) for v in det["fill"]], *[round(float(v), 1) for v in det["stroke"]]])
    # segment into events: same caption while width and column profile stay similar
    events, cur = [], None
    for i, det in enumerate(per):
        if det is None:
            if cur:
                events.append(cur)
                cur = None
            continue
        pr = profile(det["mask"])
        wd = det["x1"] - det["x0"]
        if cur is not None:
            same = abs(wd - cur["w_ref"]) <= 0.12 * max(cur["w_ref"], 1) + 6 and float(np.corrcoef(pr, cur["p_ref"])[0, 1]) > 0.80
            if same:
                cur["frames"].append(i)
                if len(cur["frames"]) == 4:   # refresh the reference after any pop-in animation has settled
                    cur["w_ref"], cur["p_ref"] = wd, pr
                continue
            events.append(cur)
        cur = {"frames": [i], "w_ref": wd, "p_ref": pr}
    if cur:
        events.append(cur)
    out = []
    for ev in events:
        fr = ev["frames"]
        mid = fr[min(len(fr) - 1, max(len(fr) // 2, min(4, len(fr) - 1)))]
        det = per[mid]
        text = ocr(det["mask"])
        hs = np.array([per[f]["y1"] - per[f]["y0"] for f in fr], np.float32)
        ws = np.array([per[f]["x1"] - per[f]["x0"] for f in fr], np.float32)
        stable_w = float(np.median(ws[min(4, len(ws) - 1):])) if len(ws) > 1 else float(ws[0])
        stable_h = float(np.median(hs[min(4, len(hs) - 1):])) if len(hs) > 1 else float(hs[0])
        fills = np.array([per[f]["fill"] for f in fr])
        strokes = np.array([per[f]["stroke"] for f in fr])
        out.append({
            "text": text, "on_f": int(fr[0]), "off_f": int(fr[-1] + 1), "frames": len(fr),
            "on": round(fr[0] / FPS, 4), "off": round((fr[-1] + 1) / FPS, 4), "dur": round(len(fr) / FPS, 4),
            "x0": det["x0"], "x1": det["x1"], "y0": det["y0"], "y1": det["y1"],
            "width_px": round(stable_w, 1), "height_px": round(stable_h, 1), "line_h_px": round(det["line_h"], 1),
            "cx_pct": round((det["x0"] + det["x1"]) / 2 / W * 100, 2), "cy_pct": round((det["y0"] + det["y1"]) / 2 / H * 100, 2),
            "width_pct_w": round(stable_w / W * 100, 2), "height_pct_h": round(stable_h / H * 100, 2),
            "fill_rgb": [round(float(v)) for v in np.median(fills, axis=0)],
            "stroke_rgb": [round(float(v)) for v in np.median(strokes, axis=0)],
            "popin_width_ratio": [round(float(v / stable_w), 3) for v in ws[:6]],
            "popin_height_ratio": [round(float(v / stable_h), 3) for v in hs[:6]],
        })
    # merge neighbours with identical text (animation can split an event)
    def norm(s):
        return "".join(ch for ch in s.lower() if ch.isalnum())

    def absorb(m, ev):
        m["off_f"], m["off"] = ev["off_f"], ev["off"]
        m["frames"] = m["off_f"] - m["on_f"]
        m["dur"] = round(m["frames"] / FPS, 4)

    merged = []
    k = 0
    while k < len(out):
        ev = out[k]
        if merged and ev["text"] and norm(ev["text"]) == norm(merged[-1]["text"]) and ev["on_f"] - merged[-1]["off_f"] <= 1:
            absorb(merged[-1], ev)
        elif (merged and k + 1 < len(out) and ev["frames"] <= 2 and norm(out[k + 1]["text"]) == norm(merged[-1]["text"])
              and norm(merged[-1]["text"]) and out[k + 1]["on_f"] - merged[-1]["off_f"] <= 3):
            absorb(merged[-1], out[k + 1])   # 1-2 frame glitch between two halves of the same caption
            k += 1
        else:
            merged.append(ev)
        k += 1
    meta = {"line_top_px": cal[0] if cal else None, "line_glyph_h_px": cal[1] if cal else None, "line_top_share": cal[2] if cal else None}
    (d / "captions.json").write_text(json.dumps({"calibration": meta, "events": merged}, indent=1, ensure_ascii=False))
    cov = sum(1 for p in per if p is not None) / max(len(per), 1)
    return d.name, len(merged), round(cov, 3), meta


def main():
    root = Path(sys.argv[1])
    jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    only = sys.argv[3] if len(sys.argv) > 3 else None
    dirs = sorted(p for p in root.iterdir() if (p / "frames").is_dir() and (only is None or p.name == only))
    cv2.setNumThreads(1)
    with ProcessPoolExecutor(jobs) as ex:
        for name, n, cov, meta in ex.map(one_video, dirs):
            print(f"{name}: {n} caption events, caption on screen {cov * 100:.1f}% of frames, line={meta}", flush=True)


if __name__ == "__main__":
    main()
