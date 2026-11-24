#!/usr/bin/env python3
"""Joins (hard cuts, cross-dissolves), continuous takes, and hold / move segmentation with camera statistics.

These videos are not cut-driven: most scene changes happen inside a continuous take as a fast camera move
(fly-through / orbit / morph), and takes are joined mostly with short cross-dissolves. So three levels are measured:

  joins     hard cut   = one isolated frame-to-frame jump (difference image uncorrelated with its neighbours)
            dissolve   = >=3 consecutive difference images that correlate (same A->B pattern) and whose middle
                         frames fit a linear blend of the end frames
  takes     spans between joins
  segments  inside the timeline every frame is 'move' (smoothed optical flow >= 0.9 % of frame height per frame,
            released below 0.55) or 'hold'. A 'beat' is the stretch between two composition changes
            (joins or moves); beat length is the closest equivalent of shot length for this style.

Usage: 07_shots.py <work_dir> [only=<video-stem>]
Writes <work>/<video>/shots.json
"""
import csv
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

FPS = 30.0
MOVE_ON, MOVE_STAY, MOVE_MIN = 0.9, 0.55, 4      # % frame height per frame, frames
STILL_FLOW = 0.05                                # % frame height per frame -> "camera and scene effectively still"


def load_metrics(d: Path):
    with open(d / "frame_metrics.csv") as fh:
        rows = list(csv.DictReader(fh))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0].keys()}


def load_gray(d: Path, n: int):
    g = np.empty((n, 240, 135), np.float32)
    for i in range(n):
        g[i] = cv2.imread(str(d / "frames" / f"{i:05d}.jpg"), cv2.IMREAD_REDUCED_GRAYSCALE_8)[:240, :135]
    return g


def corr(a, b):
    a = a - a.mean()
    b = b - b.mean()
    den = float(np.sqrt((a * a).sum() * (b * b).sum())) + 1e-6
    return float((a * b).sum() / den)


def blend_fit(g, a, b):
    """Model frames a+1..b-1 as (1-al)*A + al*B. Returns mean relative residual, alphas."""
    A, B = g[a], g[b]
    diff = B - A
    den = float((diff * diff).sum()) + 1e-6
    base = float(np.abs(diff).mean()) + 1e-6
    al, res = [], []
    for k in range(a + 1, b):
        x = float(((g[k] - A) * diff).sum() / den)
        al.append(x)
        res.append(float(np.abs(g[k] - (A + x * diff)).mean()) / base)
    return (float(np.mean(res)) if res else 0.0), al


def detect_joins(g, m):
    """hd[k+1] = HSV-histogram distance between frame k and k+1 (06_frame_metrics); d[k] = mean |frame k+1 - frame k|.

    Calibrated by eye on the boundary sheets:
      hard cut  -> one isolated spike: hd >= 0.42, at least 1.3x both neighbours, pixel jump >= 1.5x both neighbours
      dissolve  -> >= 2 consecutive frames with hd >= 0.12 while optical flow stays low (a fast camera move also
                   shifts the histogram, but with flow >= 1.2 % H/frame), end frames clearly different, and the
                   frames in between fit a monotonic linear blend of the end frames
    """
    n = len(g)
    D = g[1:] - g[:-1]                          # D[k] = frame k+1 - frame k
    d = np.abs(D).mean(axis=(1, 2))
    c = np.array([corr(D[k], D[k + 1]) for k in range(n - 2)] + [0.0])
    hd, fl = m["hist_d"], m["flow_mag"]
    joins, used = [], np.zeros(n, bool)

    # --- hard cuts
    for k in range(1, n - 2):
        if (hd[k + 1] >= 0.42 and d[k] >= 12 and d[k] >= 1.5 * max(d[k - 1], d[k + 1])
                and hd[k + 1] >= 1.3 * max(hd[k], hd[k + 2])):
            joins.append({"type": "cut", "frame": int(k + 1), "t": round((k + 1) / FPS, 3), "length_frames": 0,
                          "hist_d": round(float(hd[k + 1]), 3), "change": round(float(d[k]), 1)})
            used[k:k + 2] = True

    # --- dissolves: runs of elevated histogram change with little optical flow
    hot = hd >= 0.12
    i = 1
    while i < n:
        if hot[i] and not used[i]:
            j = i
            while j + 1 < n and not used[j + 1] and (hot[j + 1] or (j + 2 < n and hot[j + 2] and not used[j + 2])):
                j += 1
            # frames i..j changed relative to their predecessor -> blend spans frame i-1 .. j
            fa, fb = i - 1, j
            if fb - fa >= 2 and fb - fa <= 45:
                flow_med = float(np.median(fl[i:j + 1]))
                total = float(np.abs(g[fb] - g[fa]).mean())
                hdist = float(cv2.compareHist(hist(g[fa]), hist(g[fb]), cv2.HISTCMP_BHATTACHARYYA))
                res, al = blend_fit(g, fa, fb)
                mono = all(al[x] <= al[x + 1] + 0.06 for x in range(len(al) - 1))
                peak = float(hd[i:j + 1].max())
                ok = flow_med < 1.2 and total > 9 and (hdist > 0.2 or total > 20) and mono and res < 0.45
                if ok:
                    # same structure at both ends = the framing did not change (state change / lighting / texture
                    # shimmer inside one shot). Calibrated by eye: scene-change dissolves 0.03-0.17, in-place >= 0.34.
                    sc = corr(gradmag(g[fa]), gradmag(g[fb]))
                    joins.append({"type": "dissolve" if sc < 0.3 else "inplace_blend", "from_frame": int(fa), "to_frame": int(fb),
                                  "frame": int((fa + fb + 1) // 2), "t": round((fa + fb) / 2 / FPS, 3), "length_frames": int(fb - fa),
                                  "blend_residual": round(res, 3), "struct_corr": round(sc, 2),
                                  "change": round(total, 1), "hist_d_peak": round(peak, 3), "flow_med": round(flow_med, 2)})
                    used[fa:fb + 1] = True
            i = j + 1
        else:
            i += 1
    joins.sort(key=lambda j: j["frame"])
    return joins, d, c


def gradmag(img):
    b = cv2.GaussianBlur(img, (0, 0), 1.5)
    return np.hypot(cv2.Sobel(b, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(b, cv2.CV_32F, 0, 1, ksize=3))


def apply_overrides(name, joins):
    """Manual corrections from the by-eye pass over the boundary sheets (analysis/data/join_overrides.json).

    {"<video>": {"remove": [t, ...], "retype": {"<t>": "cut|dissolve|inplace_blend|flash"}, "add": [{"t":..,"type":..,"length_frames":..}]}}
    """
    p = Path(__file__).resolve().parents[1] / "data" / "join_overrides.json"
    if not p.exists():
        return joins
    ov = json.loads(p.read_text()).get(name, {})
    out = []
    for j in joins:
        if any(abs(j["t"] - t) < 0.12 for t in ov.get("remove", [])):
            continue
        for t, ty in ov.get("retype", {}).items():
            if abs(j["t"] - float(t)) < 0.12:
                j = {**j, "type": ty, "verified": "by eye"}
        out.append(j)
    for a in ov.get("add", []):
        f = int(round(a["t"] * FPS))
        L = int(a.get("length_frames", 0))
        out.append({"type": a["type"], "frame": f, "t": a["t"], "length_frames": L, "from_frame": f - L // 2, "to_frame": f + (L + 1) // 2,
                    "verified": "by eye (added)"})
    out.sort(key=lambda j: j["frame"])
    return out


def hist(gray):
    h = cv2.calcHist([gray.astype(np.uint8)], [0], None, [32], [0, 256])
    return cv2.normalize(h, h, 1.0, 0.0, cv2.NORM_L1)


def segment_motion(m, joins):
    n = len(m["f"])
    fl = m["flow_mag"].copy()
    for j in joins:                                # flow across a join is meaningless
        a = j.get("from_frame", j["frame"] - 1)
        b = j.get("to_frame", j["frame"]) + 1
        fl[max(0, a):min(n, b + 1)] = 0.0
    sm = np.array([np.median(fl[max(0, i - 2):i + 3]) for i in range(n)])
    state = np.zeros(n, bool)
    on = False
    for i in range(n):
        on = sm[i] >= (MOVE_STAY if on else MOVE_ON)
        state[i] = on
    # drop short blips, close short gaps
    i = 0
    while i < n:
        j = i
        while j < n and state[j] == state[i]:
            j += 1
        if state[i] and j - i < MOVE_MIN:
            state[i:j] = False
        elif not state[i] and j - i < 3 and i > 0 and j < n:
            state[i:j] = True
        i = j
    return state, sm


def camera_stats(m, a, b):
    s = slice(a, b)
    zoom = (m["g_scale"][s] - 1.0) * 100.0
    tx, ty, rot, inl = m["g_tx"][s], m["g_ty"][s], m["g_rot"][s], m["g_inl"][s]
    return {
        "zoom_pct_per_s": round(float(np.median(zoom)) * FPS, 2),
        "pan_pct_w_per_s": round(float(np.median(tx)) * FPS, 2),
        "tilt_pct_h_per_s": round(float(np.median(ty)) * FPS, 2),
        "roll_deg_per_s": round(float(np.median(rot)) * FPS, 2),
        "rigid_frac": round(float((inl > 0.5).mean()), 2),
        "flow_mean_pct_h_per_s": round(float(m["flow_mag"][s].mean()) * FPS, 1),
        "flow_peak_pct_h_per_s": round(float(m["flow_mag"][s].max()) * FPS, 1),
        "subject_motion_pct_h_per_s": round(float(np.median(m["resid_med"][s])) * FPS, 2),
    }


def label_hold(cs, still_frac):
    if still_frac > 0.8:
        return "static"
    lab = []
    z, px, ty = cs["zoom_pct_per_s"], cs["pan_pct_w_per_s"], cs["tilt_pct_h_per_s"]
    if z > 1.5:
        lab.append("push-in")
    elif z < -1.5:
        lab.append("pull-out")
    if abs(px) > 2.5:
        lab.append("pan/truck-right" if px < 0 else "pan/truck-left")
    if abs(ty) > 2.5:
        lab.append("tilt/crane-down" if ty < 0 else "tilt/crane-up")
    if abs(cs["roll_deg_per_s"]) > 1.5:
        lab.append("roll")
    return "+".join(lab) if lab else "slow drift"


def label_move(cs):
    if cs["rigid_frac"] < 0.35:
        return "orbit/fly-through (non-rigid)"
    z, px, ty = cs["zoom_pct_per_s"], cs["pan_pct_w_per_s"], cs["tilt_pct_h_per_s"]
    cand = {"push-in": z, "pull-out": -z, "whip/truck-right": -px * 0.5, "whip/truck-left": px * 0.5, "crane-down": -ty * 0.5, "crane-up": ty * 0.5}
    k = max(cand, key=cand.get)
    return k if cand[k] > 4 else "orbit/fly-through (non-rigid)"


def one(d: Path):
    m = load_metrics(d)
    n = len(m["f"])
    g = load_gray(d, n)
    all_joins, dser, cser = detect_joins(g, m)
    all_joins = apply_overrides(d.name, all_joins)
    inplace = [j for j in all_joins if j["type"] == "inplace_blend"]
    joins = [j for j in all_joins if j["type"] != "inplace_blend"]     # scene-change joins only
    state, sm = segment_motion(m, joins)
    # hard boundaries for segments: join frames
    cutpts = sorted({0, n} | {j["frame"] for j in joins})
    segs = []
    for a0, b0 in zip(cutpts[:-1], cutpts[1:]):
        i = a0
        while i < b0:
            j = i
            while j < b0 and state[j] == state[i]:
                j += 1
            kind = "move" if state[i] else "hold"
            cs = camera_stats(m, min(i + 1, j - 1), j)
            seg = {"type": kind, "start_f": int(i), "end_f": int(j - 1), "start": round(i / FPS, 3), "end": round(j / FPS, 3),
                   "dur": round((j - i) / FPS, 3), **cs}
            if kind == "hold":
                still = float((m["flow_mag"][i:j] < STILL_FLOW).mean())
                seg["still_frac"] = round(still, 2)
                seg["camera"] = label_hold(cs, still)
                for k in ("luma_mean", "luma_std", "sat_mean", "warm_frac", "cool_frac", "sharp"):
                    seg[k] = round(float(np.median(m[k][i:j])), 2)
            else:
                seg["camera"] = label_move(cs)
                pk = int(np.argmax(m["flow_mag"][i:j]))
                seg["peak_pos"] = round(pk / max(j - i - 1, 1), 2)
                pre, post = max(a0, i - 3), min(b0 - 1, j + 2)
                seg["content_change"] = round(float(cv2.compareHist(hist(g[pre]), hist(g[post]), cv2.HISTCMP_BHATTACHARYYA)), 3)
                seg["blur_sharp_ratio"] = round(float(np.median(m["sharp"][i:j]) / (np.median(m["sharp"][max(a0, i - 8):i + 1]) + 1e-6)), 2)
            segs.append(seg)
            i = j
    holds = [s for s in segs if s["type"] == "hold"]
    moves = [s for s in segs if s["type"] == "move"]
    dur = n / FPS
    takes = [round((b - a) / FPS, 3) for a, b in zip(cutpts[:-1], cutpts[1:])]
    # composition changes: joins + moves; beats = stretches between them
    change_t = sorted([j["t"] for j in joins] + [(s["start"] + s["end"]) / 2 for s in moves])
    edges = [0.0] + change_t + [dur]
    beats = np.diff(edges)
    hd = np.array([s["dur"] for s in holds]) if holds else np.array([0.0])
    md = np.array([s["dur"] for s in moves]) if moves else np.array([0.0])
    dis = [j["length_frames"] for j in joins if j["type"] == "dissolve"]
    cam_counts = {}
    for s in segs:
        cam_counts[f"{s['type']}: {s['camera']}"] = round(cam_counts.get(f"{s['type']}: {s['camera']}", 0) + s["dur"], 2)
    zoom_all = (m["g_scale"] - 1.0) * 100.0 * FPS
    out = {
        "video": d.name, "frames": n, "duration": round(dur, 3),
        "joins": joins, "inplace_blends": inplace, "n_inplace_blends": len(inplace),
        "n_joins": len(joins), "n_cuts": sum(j["type"] in ("cut", "flash") for j in joins), "n_dissolves": len(dis),
        "dissolve_len_frames_median": float(np.median(dis)) if dis else None, "dissolve_len_frames_min_max": [int(min(dis)), int(max(dis))] if dis else None,
        "takes_s": takes, "take_mean_s": round(float(np.mean(takes)), 2), "take_median_s": round(float(np.median(takes)), 2), "take_max_s": max(takes),
        "n_holds": len(holds), "hold_mean_s": round(float(hd.mean()), 2), "hold_median_s": round(float(np.median(hd)), 2), "hold_max_s": round(float(hd.max()), 2),
        "n_moves": len(moves), "move_mean_s": round(float(md.mean()), 2), "move_median_s": round(float(np.median(md)), 2),
        "move_time_frac": round(float(md.sum() / dur), 3),
        "move_peak_speed_median_pct_h_per_s": round(float(np.median([s["flow_peak_pct_h_per_s"] for s in moves])), 1) if moves else None,
        "moves_with_content_change": sum(s["content_change"] > 0.25 for s in moves),
        "n_changes": len(change_t), "changes_per_min": round(len(change_t) / dur * 60, 1),
        "beat_mean_s": round(float(beats.mean()), 2), "beat_median_s": round(float(np.median(beats)), 2),
        "beat_min_s": round(float(beats.min()), 2), "beat_max_s": round(float(beats.max()), 2),
        "change_curve_per_5s": [int(sum(1 for t in change_t if a <= t < a + 5)) for a in range(0, int(np.ceil(dur)), 5)],
        "still_frame_frac": round(float((m["flow_mag"][1:] < STILL_FLOW).mean()), 3),
        "flow_median_pct_h_per_s": round(float(np.median(m["flow_mag"][1:])) * FPS, 1),
        "flow_p90_pct_h_per_s": round(float(np.percentile(m["flow_mag"][1:], 90)) * FPS, 1),
        "hold_zoom_abs_median_pct_per_s": round(float(np.median([abs(s["zoom_pct_per_s"]) for s in holds])), 2) if holds else None,
        "hold_push_in_frac_time": round(float(sum(s["dur"] for s in holds if "push-in" in s["camera"]) / max(hd.sum(), 1e-6)), 2),
        "hold_pull_out_frac_time": round(float(sum(s["dur"] for s in holds if "pull-out" in s["camera"]) / max(hd.sum(), 1e-6)), 2),
        "hold_static_frac_time": round(float(sum(s["dur"] for s in holds if s["camera"] == "static") / max(hd.sum(), 1e-6)), 2),
        "camera_time_by_label_s": dict(sorted(cam_counts.items(), key=lambda kv: -kv[1])),
        "segments": segs,
    }
    (d / "shots.json").write_text(json.dumps(out, indent=1))
    np.savez_compressed(d / "join_series.npz", d=dser, c=cser, flow_smooth=sm, move=state)
    return (f"{d.name}: joins={len(joins)} (cuts {out['n_cuts']}, dissolves {out['n_dissolves']} med {out['dissolve_len_frames_median']}f) "
            f"takes mean {out['take_mean_s']}s | holds {len(holds)} med {out['hold_median_s']}s | moves {len(moves)} med {out['move_median_s']}s "
            f"({out['move_time_frac'] * 100:.0f}% of time) | changes/min {out['changes_per_min']} beat med {out['beat_median_s']}s | still {out['still_frame_frac'] * 100:.0f}%")


def main():
    root = Path(sys.argv[1])
    only = sys.argv[2] if len(sys.argv) > 2 else None
    dirs = sorted(p for p in root.iterdir() if (p / "frame_metrics.csv").exists() and (only is None or p.name == only))
    cv2.setNumThreads(1)
    with ProcessPoolExecutor(3) as ex:
        for line in ex.map(one, dirs):
            print(line, flush=True)


if __name__ == "__main__":
    main()
