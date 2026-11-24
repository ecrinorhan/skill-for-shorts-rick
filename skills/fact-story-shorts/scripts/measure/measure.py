#!/usr/bin/env python3
"""measure.py — run the reference measurements on a finished video and compare it with the style targets.

  measure.py <video.mp4> <work_dir> [--title "Why ..."] [--as-youtube] [--name 99_test]

The steps are the same code that measured the 20 reference videos (scripts/measure/lib):
  frames at 30 fps -> per-frame metrics -> joins, holds and camera moves; caption detection + OCR; Whisper large-v3;
  Demucs and dialogue / music / effects separation; loudness, voice, music and SFX statistics; forced alignment; colour.
Writes <work_dir>/record.json, comparison.json, comparison.md and prints the table.

--as-youtube first re-encodes to about 3.9 Mbit/s H.264 + 128 kbit/s AAC, roughly what YouTube serves for a 1080x1920 Short.
The reference files came from YouTube, so sharpness, grain and bitrate are only comparable after this step.
"""
import argparse
import importlib
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE / "lib"
TARGETS = HERE.parents[1] / "references" / "style_targets.json"

# key, label, unit, mode: pct = within 15 % of the reference mean; range = inside the reference min-max (means near zero); exact
METRICS = [
    ("Format", [("width", "Width", "px", "exact"), ("height", "Height", "px", "exact"), ("fps", "Frame rate", "fps", "exact"), ("audio_hz", "Audio sample rate", "Hz", "exact"),
                ("audio_ch", "Audio channels", "", "exact"), ("duration_s", "Duration", "s", "pct")]),
    ("Script", [("words", "Words", "", "pct"), ("wpm", "Words per minute", "", "pct"), ("sentences", "Sentences", "", "pct"), ("avg_sentence_words", "Words per sentence (mean)", "", "pct"),
                ("hook_sentence_words", "First sentence, words", "", "pct"), ("hook_sentence_end_s", "First sentence ends", "s", "pct"), ("words_in_first_3s", "Words in the first 3 s", "", "pct"),
                ("first_word_start_s", "First word starts", "s", "range"), ("tail_after_last_word_s", "Silence after the last word", "s", "range"), ("questions", "Questions", "", "range"),
                ("exclamations", "Exclamations", "", "range"), ("you_per_100w", "you / your per 100 words", "", "range")]),
    ("Captions", [("captions", "Caption events", "", "pct"), ("captions_per_s", "Captions per second", "", "pct"), ("words_per_caption", "Words per caption", "", "pct"),
                  ("cap1_share", "One-word captions, share", "", "pct"), ("cap2_share", "Two-word captions, share", "", "pct"), ("caption_dur_median_s", "Caption duration, median", "s", "pct"),
                  ("caption_lead_frames_median", "Caption appears before its word", "frames", "pct"), ("caption_centre_y_pct", "Caption centre, % of height", "%", "pct"),
                  ("caption_line_top_px", "Caption line top", "px", "pct"), ("caption_glyph_h_px", "Letter height", "px", "pct"), ("caption_coverage_pct", "Frames with a caption", "%", "pct"),
                  ("caption_chars_median", "Characters per caption, median", "", "pct"), ("caption_width_pct_median", "Caption width, % of frame width, median", "%", "pct"),
                  ("caption_nonwhite_share", "Coloured captions, share", "", "range")]),
    ("Picture", [("joins", "Joins between takes", "", "pct"), ("joins_per_min", "Joins per minute", "", "pct"), ("cuts", "Hard cuts", "", "range"), ("dissolves", "Dissolves", "", "pct"),
                 ("dissolve_share", "Dissolves, share of joins", "", "pct"), ("dissolve_len_frames_median", "Dissolve length, median", "frames", "pct"), ("take_mean_s", "Take length, mean", "s", "pct"),
                 ("hold_median_s", "Hold length, median", "s", "pct"), ("moves", "Fast camera moves", "", "pct"), ("moves_per_min", "Fast camera moves per minute", "", "pct"),
                 ("move_median_s", "Camera move length, median", "s", "pct"), ("move_time_pct", "Runtime spent in fast moves", "%", "pct"),
                 ("move_peak_speed_median_pctH_s", "Camera move peak speed, median", "% H/s", "pct"), ("changes_per_min", "Composition changes per minute", "", "pct"),
                 ("beat_median_s", "Time between changes, median", "s", "pct"), ("still_frame_pct", "Fully still frames", "%", "pct"), ("flow_median_pctH_s", "Image motion, median", "% H/s", "pct"),
                 ("flow_p90_pctH_s", "Image motion, 90th percentile", "% H/s", "pct"), ("hold_zoom_abs_median_pct_s", "Slow zoom during holds", "%/s", "pct"),
                 ("hold_push_in_time_share", "Hold time spent pushing in", "", "pct"), ("hold_static_time_share", "Hold time fully static", "", "range")]),
    ("Colour", [("luma_mean", "Brightness (luma mean, 0-255)", "", "pct"), ("contrast_rms", "Contrast (luma SD)", "", "pct"), ("black_p01", "Black level (1st percentile)", "", "pct"),
                ("white_p99", "White level (99th percentile)", "", "pct"), ("saturation_mean", "Saturation (HSV S mean, 0-255)", "", "pct"), ("colorfulness", "Colourfulness", "", "pct"),
                ("warm_share", "Warm hues, share of saturated pixels", "", "pct"), ("cool_share", "Cool hues, share of saturated pixels", "", "pct"),
                ("vignette_ratio", "Corner / centre brightness", "", "pct"), ("sharpness", "Sharpness (Laplacian variance)", "", "pct"), ("luma_1s_sd", "Brightness change across the video (SD of 1 s means)", "", "pct")]),
    ("Sound", [("lufs_i", "Integrated loudness", "LUFS", "pct"), ("true_peak_dbtp", "True peak", "dBTP", "pct"), ("lra_lu", "Loudness range", "LU", "pct"), ("voice_lufs", "Voice stem loudness", "LUFS", "pct"),
               ("voice_f0_median_hz", "Voice pitch, median", "Hz", "pct"), ("voice_f0_range_st", "Voice pitch range (p5-p95)", "semitones", "pct"), ("voice_active_pct", "Voice on, share of runtime", "%", "pct"),
               ("voice_syll_per_s", "Syllables per second", "", "pct"), ("pauses_ge_250ms", "Pauses of 250 ms or more", "", "range"), ("pause_max_s", "Longest pause", "s", "range"),
               ("voice_level_spread_db", "Voice level spread (p90-p10)", "dB", "pct"), ("voice_crest_db", "Voice crest factor", "dB", "pct"), ("voice_centroid_hz", "Voice spectral centroid", "Hz", "pct"),
               ("music_lufs", "Music stem loudness", "LUFS", "pct"), ("voice_minus_music_lu", "Voice above music", "LU", "pct"), ("music_starts_s", "Music starts", "s", "range"),
               ("music_dropouts", "Music drop-outs", "", "range"), ("music_level_2s_sd_db", "Music level variation (SD of 2 s windows)", "dB", "pct"), ("music_bpm_est", "Music tempo (estimate)", "BPM", "pct"),
               ("sfx_events", "Sound-effect events", "", "pct"), ("sfx_per_10s", "Sound effects per 10 s", "", "pct"), ("sfx_active_pct", "Runtime with an effect sounding", "%", "pct"),
               ("sfx_peak_median_dbfs", "Effect level, median peak", "dBFS", "pct"), ("sfx_peak_vs_voice_p50_db", "Effect peak relative to voice", "dB", "pct")]),
]


def run(script, *args, log=None):
    t0 = time.time()
    p = subprocess.run([sys.executable, str(LIB / script), *map(str, args)], capture_output=True, text=True)
    if log:
        log.write(f"\n== {script} ({time.time() - t0:.0f}s, exit {p.returncode})\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}\n")
        log.flush()
    if p.returncode != 0:
        raise SystemExit(f"{script} failed:\n{p.stderr[-2500:]}")
    print(f"  {script} {time.time() - t0:.0f}s", flush=True)


def verdict(v, s, mode):
    mean, lo, hi = s["mean"], s["min"], s["max"]
    if v is None:
        return None, "n/a"
    dev = (v - mean) / abs(mean) * 100 if abs(mean) > 1e-9 else None
    if mode == "exact":
        return dev, "ok" if abs(v - mean) < 1e-6 else "OFF"
    if mode == "range":
        return dev, "ok" if lo - 1e-9 <= v <= hi + 1e-9 else "OFF"
    if dev is not None and abs(dev) <= 15:
        return dev, "ok"
    return dev, "in range" if lo <= v <= hi else "OFF"


def compare(rec, targets):
    rows = []
    for group, items in METRICS:
        for key, label, unit, mode in items:
            s = targets["metrics"].get(key)
            if not s or key not in rec:
                continue
            dev, ver = verdict(rec[key], s, mode)
            rows.append({"group": group, "key": key, "metric": label, "unit": unit, "mode": mode, "ref_mean": s["mean"], "ref_min": s["min"], "ref_max": s["max"], "ref_sd": s["sd"],
                         "test": rec[key], "dev_pct": None if dev is None else round(dev, 1), "verdict": ver})
    return rows


def fmt(x):
    if x is None:
        return "–"
    return f"{x:,.0f}" if abs(x) >= 1000 else (f"{x:.0f}" if float(x).is_integer() else f"{x:.3g}" if abs(x) < 10 else f"{x:.1f}")


def markdown(rows, title):
    out = [f"# {title}", "", "Verdict: **ok** = within 15 % of the reference mean (or equal / inside the reference range where the mean is zero or fixed); "
           "**in range** = more than 15 % from the mean but inside what the 20 reference videos span; **OFF** = outside both.", ""]
    cur = None
    for r in rows:
        if r["group"] != cur:
            cur = r["group"]
            out += ["", f"## {cur}", "", "| Metric | Reference mean (min – max) | Test | Δ vs mean | Verdict |", "|---|---|---|---|---|"]
        unit = f" {r['unit']}" if r["unit"] else ""
        dev = "–" if r["dev_pct"] is None or r["mode"] != "pct" else f"{r['dev_pct']:+.1f} %"
        v = {"ok": "ok", "in range": "in range", "OFF": "**OFF**", "n/a": "n/a"}[r["verdict"]]
        out.append(f"| {r['metric']} | {fmt(r['ref_mean'])}{unit} ({fmt(r['ref_min'])} – {fmt(r['ref_max'])}) | {fmt(r['test'])}{unit} | {dev} | {v} |")
    n = {k: sum(r["verdict"] == k for r in rows) for k in ("ok", "in range", "OFF")}
    out += ["", f"**{n['ok']} ok, {n['in range']} in range, {n['OFF']} off, of {len(rows)} metrics.**", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("work")
    ap.add_argument("--title", default="Test video")
    ap.add_argument("--name", default="99_test")
    ap.add_argument("--as-youtube", action="store_true")
    ap.add_argument("--compare-only", action="store_true")
    a = ap.parse_args()
    work = Path(a.work)
    vids, wd = work / "videos", work / "work"
    vids.mkdir(parents=True, exist_ok=True)
    wd.mkdir(exist_ok=True)
    d = wd / a.name
    log = open(work / "measure.log", "a")
    if not a.compare_only:
        dst = vids / f"{a.name}.mp4"
        if a.as_youtube:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-b:v", "3900k", "-maxrate", "5200k", "-bufsize", "9000k",
                            "-pix_fmt", "yuv420p", "-r", "30", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                            "-movflags", "+faststart", str(dst)], check=True)
        else:
            shutil.copy(a.video, dst)
        if d.exists():
            shutil.rmtree(d)
        run("02_extract.py", vids, wd, 1, log=log)
        with ThreadPoolExecutor(3) as ex:
            jobs = [ex.submit(lambda: (run("06_frame_metrics.py", wd, 1, a.name, log=log), run("07_shots.py", wd, a.name, log=log), run("11_palette.py", wd, 1, a.name, log=log))),
                    ex.submit(lambda: run("08_captions.py", wd, 1, a.name, log=log)),
                    ex.submit(lambda: (run("05_separate.py", wd, "htdemucs", 3, log=log), run("05b_separate_dnr.py", wd, work / "models", 3, a.name, log=log), run("04_transcribe.py", wd, "large-v3", 4, log=log)))]
            for j in jobs:
                j.result()
        run("10_align.py", wd, a.name, log=log)
        run("09_audio.py", wd, 1, a.name, log=log)
        run("15_sync.py", wd, a.name, log=log)
    sys.path.insert(0, str(LIB))
    agg = importlib.import_module("16_aggregate")
    vid = a.name.split("_", 1)[1]
    meta_dir = work / "meta"
    (meta_dir / vid).mkdir(parents=True, exist_ok=True)
    (meta_dir / vid / "meta.json").write_text(json.dumps({"title": a.title, "url": "", "upload_date": datetime.now(timezone.utc).strftime("%Y%m%d"), "views_exact": 1, "likes_exact": 0,
                                                         "comment_count_header": 0, "description": a.title, "tags": []}))
    rec, _ = agg.build(d, meta_dir, work / "compact")
    (work / "record.json").write_text(json.dumps(rec, indent=1))
    targets = json.loads(TARGETS.read_text())
    rows = compare(rec, targets)
    (work / "comparison.json").write_text(json.dumps(rows, indent=1))
    md = markdown(rows, f"Reference averages vs “{a.title}”")
    (work / "comparison.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
