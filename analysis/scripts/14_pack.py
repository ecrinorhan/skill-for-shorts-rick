#!/usr/bin/env python3
"""Per-video data pack: one Markdown file with every measurement, plus hook / ending sheets for visual review.

Usage: 14_pack.py <work_dir> <meta_dir> [only=<video-stem>]
Writes <work>/<video>/pack.md, hook.jpg (first 3 s at 6 fps), ending.jpg (last 3 s at 6 fps)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

FPS = 30
HERE = Path(__file__).parent


def sentences(words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if w["text"].rstrip("\"'”’")[-1:] in ".?!":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [{"start": s[0]["start"], "end": s[-1]["end"], "text": tidy(" ".join(w["text"] for w in s)), "n": len(s)} for s in out]


def tidy(t):
    return re.sub(r"\s+-\s*(\w)", r"-\1", t)


def words_between(words, a, b):
    return tidy(" ".join(w["text"] for w in words if w["start"] < b and w["end"] > a))


def main():
    root, meta_dir = Path(sys.argv[1]), Path(sys.argv[2])
    only = sys.argv[3] if len(sys.argv) > 3 else None
    for d in sorted(p for p in root.iterdir() if (p / "words.json").exists() and (only is None or p.name == only)):
        vid = d.name.split("_", 1)[1]
        meta = json.loads((meta_dir / vid / "meta.json").read_text())
        specs = json.loads((d / "specs.json").read_text())
        wj = json.loads((d / "words.json").read_text())
        sj = json.loads((d / "shots.json").read_text())
        aj = json.loads((d / "audio.json").read_text())
        cj = json.loads((d / "color.json").read_text())
        W = wj["words"]
        st = wj["stats"]
        L = []
        L.append(f"# {d.name} — {meta['title']}\n")
        L.append(f"- URL: {meta['url']} | uploaded (UTC): {(meta.get('rss') or {}).get('published_utc') or meta.get('upload_date')}")
        L.append(f"- views {meta.get('views_exact')} | likes {meta.get('likes_exact')} | comments {meta.get('comment_count_header')} | pinned comment: {meta.get('pinned_comment') or 'none'}")
        L.append(f"- file: {specs['width']}x{specs['height']} {specs['fps']} fps {specs['video_codec']} {specs['video_bitrate_kbps']} kbps, {specs['duration_s']} s, audio {specs['audio_codec']} {specs['audio_sample_rate']} Hz x{specs['audio_channels']} {specs['audio_bitrate_kbps']} kbps\n")
        L.append("## Transcript by sentence (start-end s, words)\n")
        sents = sentences(W)
        for i, s in enumerate(sents, 1):
            L.append(f"{i:>2}. [{s['start']:6.2f}-{s['end']:6.2f}] ({s['n']:>2}w) {s['text']}")
        L.append(f"\nwords {st['words']} | WPM {st['wpm']} | sentences {len(sents)} | avg sentence {st['avg_sentence_words']} words | questions {st['questions']} | 'you/your' {st['you_count']}\n")
        L.append("## Captions\n")
        L.append(f"events {st['captions']} | words/caption mean {st['words_per_caption_mean']} hist {st['words_per_caption_hist']} | caption duration median {st['caption_dur_median_s']} s | "
                 f"caption appears {abs(st['caption_on_minus_word_frames_median'])} frames {'before' if st['caption_on_minus_word_frames_median'] < 0 else 'after'} the word starts (median; p10-p90 {st['caption_on_minus_word_frames_p10_p90']})")
        L.append("\n## Joins between takes (auto-detected; verify on boundaries_*.jpg)\n")
        for j in sj["joins"]:
            L.append(f"- {j['t']:6.2f}s {j['type']:<9} len {j['length_frames']:>2}f | words: \"{words_between(W, j['t'] - 0.6, j['t'] + 0.6)}\"")
        if sj.get("inplace_blends"):
            L.append("\nIn-place blends (same framing before/after; may be clip joins, state changes or false alarms):")
            for j in sj["inplace_blends"]:
                L.append(f"- {j['t']:6.2f}s len {j['length_frames']}f struct_corr {j.get('struct_corr')}")
        L.append(f"\njoins {sj['n_joins']} (cuts {sj['n_cuts']}, dissolves {sj['n_dissolves']}, dissolve length median {sj['dissolve_len_frames_median']} frames) | take mean {sj['take_mean_s']} s max {sj['take_max_s']} s")
        L.append(f"holds {sj['n_holds']} median {sj['hold_median_s']} s | camera moves {sj['n_moves']} median {sj['move_median_s']} s, {round(sj['move_time_frac'] * 100)}% of runtime | composition changes/min {sj['changes_per_min']} | beat median {sj['beat_median_s']} s | still frames {round(sj['still_frame_frac'] * 100)}%\n")
        L.append("## Timeline segments (hold / move, camera label, speed)\n")
        for s in sj["segments"]:
            if s["type"] == "move":
                L.append(f"- {s['start']:6.2f}-{s['end']:6.2f} MOVE {s['dur']:.2f}s {s['camera']} peak {s['flow_peak_pct_h_per_s']}%H/s content_change {s['content_change']} | \"{words_between(W, s['start'], s['end'])}\"")
            elif s["dur"] >= 0.5:
                L.append(f"- {s['start']:6.2f}-{s['end']:6.2f} hold {s['dur']:.2f}s {s['camera']} zoom {s['zoom_pct_per_s']}%/s luma {s['luma_mean']} sat {s['sat_mean']} warm {s['warm_frac']} | \"{words_between(W, s['start'], s['end'])}\"")
        L.append("\n## Sound\n")
        m, v, mu, fx, bal = aj["mix"], aj["voice"], aj["music"], aj["sfx"], aj["balance"]
        L.append(f"- mix: {m['integrated_lufs']} LUFS integrated, true peak {m['true_peak_dbtp']} dBTP, LRA {m['lra_lu']} LU, stereo side/mid {m['stereo_side_to_mid_db']} dB")
        L.append(f"- voice stem: {v['lufs']} LUFS, F0 median {v['f0_median_hz']} Hz (p5-p95 {v['f0_p05_p95_hz']}, range {v['f0_range_p05_p95_semitones']} st), {v['wpm_overall']} WPM, {v['syll_per_s_articulation']} syll/s, "
                 f"pauses >=120 ms: {v['pauses_ge_120ms']}, >=250 ms: {v['pauses_ge_250ms']}, voice active {round(v['voice_active_frac_of_video'] * 100)}% of runtime")
        L.append(f"- music stem: {mu['lufs']} LUFS ({bal['voice_minus_music_lufs']} LU under the voice), starts {mu['starts_s']} s ends {mu['ends_s']} s, tempo est {mu['tempo']['bpm']} BPM "
                 f"(pulse strength {mu['tempo']['pulse_strength']}), key est {mu['key']['key']} (score {mu['key']['score']}), dropouts {mu['dropouts_below_-58dbfs_ge_250ms']}, level steps {mu['level_steps_ge_4db']}")
        L.append(f"- SFX stem: {fx['count']} events ({fx['per_10s']} per 10 s), active {round(fx['time_active_frac'] * 100)}% of runtime, median peak {fx['peak_dbfs_median']} dBFS; per 10 s: {fx['density_per_10s_bins']}")
        L.append("\nSFX events (start, duration, peak dBFS, heuristic class, words spoken):")
        for e in fx["events"]:
            L.append(f"- {e['start']:6.2f}s {e['dur']:.2f}s {e['peak_dbfs']:6.1f} {e['class_est']:<26} | \"{words_between(W, e['start'] - 0.2, e['end'] + 0.2)[:70]}\"")
        L.append("\n## Colour\n")
        g = cj["grade"]
        L.append(f"- luma mean {g['luma_mean']} (p5-p95 {g['luma_mean_p05_p95']}), RMS contrast {g['contrast_rms_mean']}, black level p1 {g['black_level_p01_median']}, white level p99 {g['white_level_p99_median']}")
        L.append(f"- saturation mean {g['saturation_mean']}/255, colourfulness {g['colorfulness_mean']}, warm share {g['warm_frac_mean']} cool share {g['cool_frac_mean']}, vignette corner/centre {g['vignette_corner_over_centre_median']}, grain sigma {g['grain_sigma_8bit_median']}")
        L.append("- video palette: " + ", ".join(f"{p['hex']} {round(p['share'] * 100)}%" for p in cj["video_palette"]))
        L.append("- hold palettes (first 3 colours):")
        for s in cj["segment_palettes"]:
            L.append(f"  - {s['start']:6.2f}-{s['end']:6.2f}: " + ", ".join(f"{p['hex']} {round(p['share'] * 100)}%" for p in s["palette"][:3]) + f" | luma {s['luma']} sat {s['sat']}")
        (d / "pack.md").write_text("\n".join(L) + "\n")
        n = sj["frames"]
        subprocess.run([sys.executable, str(HERE / "lib" / "montage.py"), str(d / "hook.jpg"), "270", "8", str(d), "0-90:6"], capture_output=True)
        subprocess.run([sys.executable, str(HERE / "lib" / "montage.py"), str(d / "ending.jpg"), "270", "8", str(d), f"{n - 91}-{n - 1}:6"], capture_output=True)
        print(d.name, "pack lines:", len(L))


if __name__ == "__main__":
    main()
