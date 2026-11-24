#!/usr/bin/env python3
"""Cross-video aggregation: one record per video, summary statistics, rankings, trends, recurring wording.

Usage: 16_aggregate.py <work_dir> <meta_dir> <analysis_dir> [out_dir=/opt/rc/out] [--quiet]
Writes <analysis_dir>/data/videos.json               one flat record per video (all key numbers)
       <analysis_dir>/data/summary.json              mean / sd / median / min / max / p10 / p90 per metric + pooled stats
       <analysis_dir>/data/videos/<video>/           compact copies of the measurements (no frames, no third-party comments)
       <analysis_dir>/output/01_video_table.md, .csv
"""
import csv
import gzip
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

STOP = set("a an the and or but so to of in on at for with by from is are was were be been it its it's this that these those he she they we you i "
           "his her their your my our as if then than not no do does did have has had will would can could just up out into over about what when "
           "who why how one every all".split())


def tidy(t):
    return re.sub(r"\s+-\s*(\w)", r"-\1", t)


def toks(s):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", s.lower())


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[:-len(suf)]
    return w


def cwords(s):
    return {stem(w) for w in toks(s) if w not in STOP and len(w) > 2}


def sentences(W):
    out, cur = [], []
    for w in W:
        cur.append(w)
        if w["text"].rstrip("\"'”’")[-1:] in ".?!":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [{"start": s[0]["start"], "end": s[-1]["end"], "text": tidy(" ".join(x["text"] for x in s)), "n": len(s)} for s in out]


def title_pattern(t):
    for pat, name in ((r"^why\b", "Why …"), (r"^how\b", "How …"), (r"^what\b", "What …"), (r"^this\b", "This X …"), (r"^the\b", "The X …"), (r"^(he|she)\b", "He/She …")):
        if re.match(pat, t.lower()):
            return name
    return "other"


def r(x, nd=2):
    return None if x is None else round(float(x), nd)


def build(d: Path, meta_dir: Path, out_videos: Path):
    vid = d.name.split("_", 1)[1]
    mp = meta_dir / vid / "meta.json"
    meta = json.loads(mp.read_text())
    J = {k: json.loads((d / f"{k}.json").read_text()) for k in ("specs", "words", "shots", "audio", "color", "sync", "captions")}
    specs, wj, sj, aj, cj = J["specs"], J["words"], J["shots"], J["audio"], J["color"]
    W, st, caps = wj["words"], wj["stats"], [c for c in wj["captions"] if c["n_words"] > 0]
    dur = specs["duration_s"]
    snap = datetime.fromtimestamp(mp.stat().st_mtime, timezone.utc)
    pub = (meta.get("rss") or {}).get("published_utc")
    if pub:
        published, prec = datetime.fromisoformat(pub), "second"
    else:   # only the UTC date is known for uploads that have dropped out of the 15-entry RSS feed -> assume noon
        published, prec = datetime.strptime(meta["upload_date"], "%Y%m%d").replace(hour=12, tzinfo=timezone.utc), "day"
    age = (snap - published).total_seconds() / 86400
    S = sentences(W)
    first, last = S[0], S[-1]
    tcw, fcw, acw = cwords(meta["title"]), cwords(first["text"]), cwords(wj["text"])
    yousee = [s["start"] for s in S if re.match(r"(well, )?you see\b", s["text"].lower())]
    with open(d / "captions_frames.csv") as fh:
        has = [int(row["has"]) for row in csv.DictReader(fh)]
    chars = [len(c["spoken"]) for c in caps]
    hist = st["words_per_caption_hist"]
    nc = max(sum(hist.values()), 1)
    v, mu, fx, bal, mix, g = aj["voice"], aj["music"], aj["sfx"], aj["balance"], aj["mix"], cj["grade"]
    moves = [s for s in sj["segments"] if s["type"] == "move"]
    holds = [s for s in sj["segments"] if s["type"] == "hold" and s["dur"] >= 0.5]
    views, likes, comments = meta["views_exact"], meta["likes_exact"], meta["comment_count_header"]
    rec = {
        "n": int(d.name[:2]), "video": d.name, "id": vid, "title": meta["title"], "url": meta["url"],
        "published_utc": published.isoformat(), "published_precision": prec, "age_days_at_snapshot": r(age, 1), "snapshot_utc": snap.isoformat(timespec="minutes"),
        "views": views, "likes": likes, "comments": comments, "like_rate_pct": r(likes / views * 100), "comments_per_1k_views": r(comments / views * 1000, 3),
        "views_per_day": round(views / age), "description": meta.get("description"), "tags": meta.get("tags") or [],
        "pinned_comment": meta.get("pinned_comment"), "uploader_comments_in_top100": len(meta.get("uploader_comments_in_top100") or []),
        "how_this_was_made": (meta.get("how_this_was_made") or {}).get("header"), "sound_attribution": meta.get("shorts_sound_attribution"),
        "title_pattern": title_pattern(meta["title"]), "title_words": len(meta["title"].split()),
        # file
        "duration_s": dur, "width": specs["width"], "height": specs["height"], "aspect": specs["aspect_ratio"], "fps": specs["fps"],
        "vcodec": f"{specs['video_codec']} {specs['video_profile']}", "pix_fmt": specs["pix_fmt"], "video_kbps": specs["video_bitrate_kbps"],
        "acodec": f"{specs['audio_codec']} {specs.get('audio_profile')}", "audio_hz": specs["audio_sample_rate"], "audio_ch": specs["audio_channels"],
        "audio_kbps": specs["audio_bitrate_kbps"], "size_mb": r(specs["size_bytes"] / 1e6, 1),
        # script
        "words": st["words"], "wpm": st["wpm"], "sentences": len(S), "avg_sentence_words": r(np.mean([s["n"] for s in S]), 1),
        "median_sentence_words": float(np.median([s["n"] for s in S])), "max_sentence_words": max(s["n"] for s in S),
        "short_sentence_share_le5w": r(np.mean([s["n"] <= 5 for s in S])), "questions": sum(s["text"].endswith("?") for s in S),
        "exclamations": sum(s["text"].endswith("!") for s in S), "you_count": st["you_count"], "you_per_100w": r(st["you_count"] / st["words"] * 100, 1),
        "first_word_start_s": W[0]["start"], "last_word_end_s": W[-1]["end"], "tail_after_last_word_s": r(dur - W[-1]["end"]),
        "hook_sentence": first["text"], "hook_sentence_words": first["n"], "hook_sentence_end_s": first["end"],
        "words_in_first_3s": sum(1 for w in W if w["start"] < 3.0), "title_content_words": len(tcw),
        "title_words_in_first_sentence": len(tcw & fcw), "title_words_in_script": len(tcw & acw),
        "you_see_count": len(yousee), "you_see_first_s": yousee[0] if yousee else None, "you_see_first_rel": r(yousee[0] / dur) if yousee else None,
        "last_sentence": last["text"], "last_sentence_words": last["n"], "last_sentence_start_rel": r(last["start"] / dur),
        "loop_overlap_words": len(cwords(last["text"]) & fcw),
        "wpm_by_10s": [round(sum(1 for w in W if a <= w["start"] < a + 10) * 60 / min(10, dur - a)) for a in range(0, int(dur), 10) if dur - a >= 4],
        # captions
        "captions": len(caps), "captions_per_s": r(len(caps) / dur), "words_per_caption": st["words_per_caption_mean"],
        "cap1_share": r(hist.get("1", 0) / nc), "cap2_share": r(hist.get("2", 0) / nc), "cap3plus_share": r(sum(hist.get(k, 0) for k in ("3", "4", "5")) / nc),
        "caption_dur_median_s": st["caption_dur_median_s"], "caption_dur_mean_s": st["caption_dur_mean_s"],
        "caption_lead_frames_median": r(-st["caption_on_minus_word_frames_median"]), "caption_lead_frames_p10_p90": [r(-x) for x in st["caption_on_minus_word_frames_p10_p90"]][::-1],
        "caption_centre_y_pct": r(np.median([c["cy_pct"] for c in caps])), "caption_line_top_px": J["captions"]["calibration"]["line_top_px"],
        "caption_glyph_h_px": J["captions"]["calibration"]["line_glyph_h_px"], "caption_coverage_pct": r(np.mean(has) * 100, 1),
        "caption_chars_median": float(np.median(chars)), "caption_chars_max": int(max(chars)),
        "caption_width_pct_median": r(np.median([c["width_pct_w"] for c in caps]), 1), "caption_width_pct_max": r(max(c["width_pct_w"] for c in caps), 1),
        "caption_nonwhite_share": r(np.mean([max(c["fill_rgb"]) - min(c["fill_rgb"]) > 40 for c in caps]), 3),
        "caption_fill_rgb_median": [int(np.median([c["fill_rgb"][i] for c in caps])) for i in range(3)],
        "caption_stroke_rgb_median": [int(np.median([c["stroke_rgb"][i] for c in caps])) for i in range(3)],
        # picture
        "joins": sj["n_joins"], "cuts": sj["n_cuts"], "dissolves": sj["n_dissolves"], "dissolve_share": r(sj["n_dissolves"] / max(sj["n_joins"], 1)),
        "dissolve_len_frames_median": sj["dissolve_len_frames_median"], "inplace_blends": sj["n_inplace_blends"],
        "take_mean_s": sj["take_mean_s"], "take_median_s": sj["take_median_s"], "take_max_s": sj["take_max_s"],
        "holds": sj["n_holds"], "hold_median_s": sj["hold_median_s"], "hold_max_s": sj["hold_max_s"],
        "moves": sj["n_moves"], "move_median_s": sj["move_median_s"], "move_time_pct": r(sj["move_time_frac"] * 100, 1),
        "move_peak_speed_median_pctH_s": sj["move_peak_speed_median_pct_h_per_s"], "moves_per_min": r(sj["n_moves"] / dur * 60, 1),
        "joins_per_min": r(sj["n_joins"] / dur * 60, 1), "changes_per_min": sj["changes_per_min"], "beat_median_s": sj["beat_median_s"],
        "beat_mean_s": sj["beat_mean_s"], "beat_max_s": sj["beat_max_s"], "still_frame_pct": r(sj["still_frame_frac"] * 100, 1),
        "flow_median_pctH_s": sj["flow_median_pct_h_per_s"], "flow_p90_pctH_s": sj["flow_p90_pct_h_per_s"],
        "hold_zoom_abs_median_pct_s": sj["hold_zoom_abs_median_pct_per_s"], "hold_push_in_time_share": sj["hold_push_in_frac_time"],
        "hold_pull_out_time_share": sj["hold_pull_out_frac_time"], "hold_static_time_share": sj["hold_static_frac_time"],
        "move_blur_sharp_ratio_median": r(np.median([m["blur_sharp_ratio"] for m in moves])) if moves else None,
        "moves_changing_content_share": r(np.mean([m["content_change"] > 0.25 for m in moves])) if moves else None,
        "change_curve_per_5s": sj["change_curve_per_5s"],
        # colour
        "luma_mean": g["luma_mean"], "contrast_rms": g["contrast_rms_mean"], "black_p01": g["black_level_p01_median"], "white_p99": g["white_level_p99_median"],
        "saturation_mean": g["saturation_mean"], "colorfulness": g["colorfulness_mean"], "warm_share": g["warm_frac_mean"], "cool_share": g["cool_frac_mean"],
        "warm_dominant_time_share": g["warm_dominant_time_frac"], "vignette_ratio": g["vignette_corner_over_centre_median"],
        "grain_sigma": g["grain_sigma_8bit_median"], "bloom_lift": g["bloom_ring_lift_8bit_median"], "sharpness": g["sharpness_laplacian_var_median"],
        "luma_1s_sd": g["luma_1s_sd"], "sat_1s_sd": g["sat_1s_sd"], "hold_luma_sd": r(np.std([h["luma_mean"] for h in holds]), 1) if holds else None,
        "palette_top5": [p["hex"] for p in cj["video_palette"][:5]],
        # sound
        "lufs_i": mix["integrated_lufs"], "true_peak_dbtp": mix["true_peak_dbtp"], "lra_lu": mix["lra_lu"], "stereo_side_mid_db": mix["stereo_side_to_mid_db"],
        "voice_lufs": v["lufs"], "voice_f0_median_hz": v["f0_median_hz"], "voice_f0_range_st": v["f0_range_p05_p95_semitones"], "voice_f0_sd_st": v["f0_sd_semitones"],
        "voice_active_pct": r(v["voice_active_frac_of_video"] * 100, 1), "voice_syll_per_s": v["syll_per_s_articulation"],
        "pauses_ge_120ms": v["pauses_ge_120ms"], "pauses_ge_250ms": v["pauses_ge_250ms"], "pause_max_s": v["pause_max_s"], "breath_like_events": v["breath_like_events"],
        "voice_level_spread_db": v["level_spread_p90_p10_db"], "voice_crest_db": v["crest_factor_db"], "voice_centroid_hz": v["spectral_centroid_hz"],
        "voice_stereo_side_mid_db": v["stereo_side_to_mid_db"], "voice_tail_rt60_est_s": v["tail_rt60_est_s"],
        "music_lufs": mu["lufs"], "voice_minus_music_lu": bal["voice_minus_music_lufs"], "music_starts_s": mu["starts_s"], "music_ends_before_end_s": r(dur - mu["ends_s"]) if mu["ends_s"] else None,
        "music_dropouts": len(mu["dropouts_below_-58dbfs_ge_250ms"]), "music_level_steps": len(mu["level_steps_ge_4db"]),
        "music_level_2s_sd_db": mu["level_2s_window_sd_db"], "music_voice_level_corr": mu["level_2s_corr_with_voice"],
        "music_bpm_est": mu["tempo"]["bpm"], "music_pulse_strength": mu["tempo"]["pulse_strength"], "music_key_est": mu["key"]["key"], "music_key_score": mu["key"]["score"],
        "music_centroid_hz": mu["spectral_centroid_hz"], "music_stereo_side_mid_db": mu["stereo_side_to_mid_db"],
        "sfx_events": fx["count"], "sfx_per_10s": fx["per_10s"], "sfx_active_pct": r(fx["time_active_frac"] * 100, 1), "sfx_peak_median_dbfs": fx["peak_dbfs_median"],
        "sfx_lufs": fx["lufs"], "sfx_peak_vs_voice_p50_db": bal["sfx_peak_median_minus_voice_p50_db"], "sfx_by_class": fx["by_class"],
        "sfx_density_per_10s": fx["density_per_10s_bins"],
        "joins_at_sentence_start_share": (J["sync"].get("dissolve_start__vs__sentence_start") or {}).get("within_3f"),
    }
    # compact copies for the repository. The narration text is the creator's work, so the public copies keep
    # every timing and geometry number but no words (word text -> character count and punctuation only).
    od = out_videos / d.name
    od.mkdir(parents=True, exist_ok=True)
    for k in ("specs", "shots", "audio", "color", "sync"):
        (od / f"{k}.json").write_text(json.dumps(J[k], ensure_ascii=False, separators=(",", ":")))
    timing = {
        "note": "text removed on purpose; see analysis/README.md",
        "stats": st, "caption_calibration": J["captions"]["calibration"],
        "sentences": [{"start": s["start"], "end": s["end"], "words": s["n"]} for s in S],
        "words": [{"start": w["start"], "end": w["end"], "cap": w["cap"], "chars": len(re.sub(r"[^A-Za-z0-9]", "", w["text"])),
                   "punct": (w["text"].rstrip("\"'”’")[-1:] if w["text"].rstrip("\"'”’")[-1:] in ".?!,;:" else ""), "align_score": w.get("score")} for w in W],
        "captions": [{k2: c[k2] for k2 in c if k2 not in ("text", "spoken")} | {"chars": len(c["spoken"])} for c in wj["captions"]],
        "review_items": len(wj.get("review", [])),
    }
    (od / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, separators=(",", ":")))
    for stale in ("words.json", "captions.json"):
        (od / stale).unlink(missing_ok=True)
    keep = {k: v_ for k, v_ in meta.items() if k not in ("top_comments", "uploader_comments_in_top100", "sources")}
    (od / "meta.json").write_text(json.dumps(keep, indent=1, ensure_ascii=False))
    with open(d / "frame_metrics.csv", "rb") as fi, gzip.open(od / "frame_metrics.csv.gz", "wb") as fo:
        shutil.copyfileobj(fi, fo)
    return rec, S


def stat(vals):
    a = np.array([x for x in vals if x is not None], float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)), "mean": r(a.mean(), 3), "sd": r(a.std(ddof=1), 3) if len(a) > 1 else 0.0, "median": r(np.median(a), 3),
            "min": r(a.min(), 3), "max": r(a.max(), 3), "p10": r(np.percentile(a, 10), 3), "p90": r(np.percentile(a, 90), 3)}


def md_table(rows, cols):
    head = "| " + " | ".join(c[0] for c in cols) + " |\n|" + "|".join("---" for _ in cols) + "|\n"
    body = ""
    for rec in rows:
        body += "| " + " | ".join(str(c[1](rec)) for c in cols) + " |\n"
    return head + body


def main():
    work, meta_dir, adir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    outdir = Path(sys.argv[4]) if len(sys.argv) > 4 and not sys.argv[4].startswith("--") else Path("/opt/rc/out")
    quiet = "--quiet" in sys.argv
    (adir / "data" / "videos").mkdir(parents=True, exist_ok=True)
    (adir / "output").mkdir(parents=True, exist_ok=True)
    recs, sents = [], {}
    for d in sorted(p for p in work.iterdir() if (p / "words.json").exists() and (p / "audio.json").exists()):
        rec, S = build(d, meta_dir, adir / "data" / "videos")
        recs.append(rec)
        sents[rec["video"]] = S
    num = [k for k in recs[0] if isinstance(recs[0][k], (int, float)) and not isinstance(recs[0][k], bool) and k not in ("n", "width", "height")]
    summary = {"n_videos": len(recs), "metrics": {k: stat([x[k] for x in recs]) for k in num}}

    # ---- pooled wording statistics
    openers1, openers2, vids1, vids2, pos1 = Counter(), Counter(), defaultdict(set), defaultdict(set), defaultdict(list)
    ngram_vids = defaultdict(set)
    allsent = []
    for rec in recs:
        S = sents[rec["video"]]
        for i, s in enumerate(S):
            t = toks(s["text"])
            allsent.append(s["n"])
            if i > 0 and t:
                openers1[t[0]] += 1
                vids1[t[0]].add(rec["n"])
                pos1[t[0]].append(s["start"] / rec["duration_s"])
                if len(t) > 1:
                    k = " ".join(t[:2])
                    openers2[k] += 1
                    vids2[k].add(rec["n"])
        T = toks(" ".join(s["text"] for s in S))
        for n in (2, 3, 4, 5):
            for i in range(len(T) - n + 1):
                ngram_vids[" ".join(T[i:i + n])].add(rec["n"])
    summary["sentence_openers"] = [{"word": w, "count": c, "videos": len(vids1[w]), "median_position": r(np.median(pos1[w]))} for w, c in openers1.most_common(22)]
    summary["sentence_openers_2w"] = [{"words": w, "count": c, "videos": len(vids2[w])} for w, c in openers2.most_common(40) if len(vids2[w]) >= 4][:18]
    ng = [(k, len(v_)) for k, v_ in ngram_vids.items() if len(v_) >= (10 if len(k.split()) == 2 else 5) and not all(w in STOP for w in k.split())]
    summary["phrases_in_many_videos"] = [{"phrase": k, "videos": c} for k, c in sorted(ng, key=lambda x: (-len(x[0].split()), -x[1]))[:40]]
    summary["sentence_words_pooled"] = stat(allsent)
    summary["sentence_words_hist"] = {f"{a}-{b}": int(sum(a <= x <= b for x in allsent)) for a, b in ((1, 3), (4, 6), (7, 10), (11, 15), (16, 20), (21, 30), (31, 99))}
    summary["title_patterns"] = dict(Counter(x["title_pattern"] for x in recs))
    summary["music_keys"] = dict(Counter(x["music_key_est"] for x in recs))
    cls = Counter()
    for x in recs:
        cls.update(x["sfx_by_class"])
    summary["sfx_class_totals_est"] = dict(cls.most_common())
    cam = Counter()
    for d in sorted(p for p in work.iterdir() if (p / "shots.json").exists()):
        for k, v_ in json.loads((d / "shots.json").read_text())["camera_time_by_label_s"].items():
            cam[k] += v_
    tot = sum(cam.values())
    summary["camera_time_share_by_label"] = {k: r(v_ / tot, 3) for k, v_ in cam.most_common(16)}
    for name in ("sync_pooled",):
        p = work / f"{name}.json"
        if p.exists():
            summary[name] = json.loads(p.read_text())
    for name in ("music_match", "music_id", "font_match"):
        p = outdir / f"{name}.json"
        if p.exists():
            j = json.loads(p.read_text())
            if name == "music_match":
                summary[name] = {k: j[k] for k in ("same_track_groups", "offdiag_similarity_median", "offdiag_similarity_max")}
            elif name == "music_id":
                summary[name] = {"videos_tested": len(j), "excerpts_tested": sum(len(v_) for v_ in j.values()),
                                 "matches": [h for v_ in j.values() for h in v_ if h.get("match")], "errors": sum(1 for v_ in j.values() for h in v_ if "error" in h)}
            else:
                summary[name] = {"ranking_top10": j["ranking"][:10], "n_samples": len(j["samples"])}

    # ---- rankings and comparisons
    by_views = sorted(recs, key=lambda x: -x["views"])
    mature = [x for x in recs if x["age_days_at_snapshot"] >= 8]
    mature_by_views = sorted(mature, key=lambda x: -x["views"])

    def compare(top, bot):
        out = []
        for k in num:
            if k in ("views", "likes", "comments", "views_per_day"):
                continue
            a, b = [x[k] for x in top if x[k] is not None], [x[k] for x in bot if x[k] is not None]
            sd = summary["metrics"][k]["sd"] if summary["metrics"][k] else 0
            if a and b and sd:
                out.append({"metric": k, "top_mean": r(np.mean(a), 2), "bottom_mean": r(np.mean(b), 2), "diff_in_sd": r((np.mean(a) - np.mean(b)) / sd, 2)})
        return sorted(out, key=lambda x: -abs(x["diff_in_sd"]))

    summary["rank_by_views"] = [{"rank": i + 1, "n": x["n"], "title": x["title"], "views": x["views"], "age_days": x["age_days_at_snapshot"], "views_per_day": x["views_per_day"]} for i, x in enumerate(by_views)]
    summary["top5_vs_bottom5_all"] = compare(by_views[:5], by_views[-5:])
    summary["top5_vs_bottom5_age_ge_8d"] = compare(mature_by_views[:5], mature_by_views[-5:])
    cor = []
    for k in num:
        if k in ("views", "likes", "comments", "views_per_day", "age_days_at_snapshot"):
            continue
        xs = [(x[k], x["views"]) for x in mature if x[k] is not None]
        if len(xs) >= 10 and len({a for a, _ in xs}) > 2:
            rho, p = spearmanr([a for a, _ in xs], [b for _, b in xs])
            cor.append({"metric": k, "rho": r(rho, 2), "p": r(p, 3), "n": len(xs)})
    summary["views_spearman_age_ge_8d"] = sorted(cor, key=lambda x: -abs(x["rho"]))
    chrono = sorted(recs, key=lambda x: x["published_utc"])
    tr = []
    for k in num:
        if k in ("age_days_at_snapshot",):
            continue
        xs = [(i, x[k]) for i, x in enumerate(chrono) if x[k] is not None]
        if len(xs) >= 10 and len({b for _, b in xs}) > 2:
            rho, p = spearmanr([a for a, _ in xs], [b for _, b in xs])
            tr.append({"metric": k, "rho": r(rho, 2), "p": r(p, 3), "oldest5_mean": r(np.mean([b for _, b in xs[:5]]), 2), "newest5_mean": r(np.mean([b for _, b in xs[-5:]]), 2)})
    summary["trend_oldest_to_newest"] = sorted(tr, key=lambda x: -abs(x["rho"]))
    (adir / "data" / "videos.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False))
    (adir / "data" / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))

    # ---- tables
    A = [("#", lambda x: x["n"]), ("Title", lambda x: f"[{x['title']}]({x['url']})"), ("Uploaded (UTC)", lambda x: x["published_utc"][:16].replace("T", " ") if x["published_precision"] == "second" else x["published_utc"][:10]),
         ("Age d", lambda x: x["age_days_at_snapshot"]), ("Dur s", lambda x: f"{x['duration_s']:.1f}"), ("Views", lambda x: f"{x['views']:,}"), ("Likes", lambda x: f"{x['likes']:,}"),
         ("Comments", lambda x: f"{x['comments']:,}"), ("Like %", lambda x: x["like_rate_pct"]), ("Views/day", lambda x: f"{x['views_per_day']:,}")]
    B = [("#", lambda x: x["n"]), ("Words", lambda x: x["words"]), ("WPM", lambda x: x["wpm"]), ("Sent.", lambda x: x["sentences"]), ("Avg sent. w", lambda x: x["avg_sentence_words"]),
         ("Hook w", lambda x: x["hook_sentence_words"]), ("Hook ends s", lambda x: x["hook_sentence_end_s"]), ("you/100w", lambda x: x["you_per_100w"]), ("“You see” at s", lambda x: x["you_see_first_s"] if x["you_see_first_s"] is not None else "–"),
         ("Captions", lambda x: x["captions"]), ("Words/cap", lambda x: x["words_per_caption"]), ("Cap. dur med s", lambda x: x["caption_dur_median_s"]), ("Cap. lead f", lambda x: x["caption_lead_frames_median"]),
         ("Cap. centre y %", lambda x: x["caption_centre_y_pct"])]
    C = [("#", lambda x: x["n"]), ("Joins", lambda x: x["joins"]), ("Cuts", lambda x: x["cuts"]), ("Dissolves", lambda x: x["dissolves"]), ("Diss. len f", lambda x: x["dissolve_len_frames_median"]),
         ("Take mean s", lambda x: x["take_mean_s"]), ("Moves", lambda x: x["moves"]), ("Move med s", lambda x: x["move_median_s"]), ("Move time %", lambda x: x["move_time_pct"]),
         ("Changes/min", lambda x: x["changes_per_min"]), ("Beat med s", lambda x: x["beat_median_s"]), ("Still %", lambda x: x["still_frame_pct"]), ("Luma", lambda x: x["luma_mean"]),
         ("Contrast", lambda x: x["contrast_rms"]), ("Sat.", lambda x: x["saturation_mean"]), ("Warm share", lambda x: x["warm_share"]), ("Video kbps", lambda x: round(x["video_kbps"]))]
    D = [("#", lambda x: x["n"]), ("LUFS-I", lambda x: x["lufs_i"]), ("TP dBTP", lambda x: x["true_peak_dbtp"]), ("LRA LU", lambda x: x["lra_lu"]), ("Voice LUFS", lambda x: x["voice_lufs"]),
         ("Music LUFS", lambda x: x["music_lufs"]), ("Voice−music LU", lambda x: x["voice_minus_music_lu"]), ("F0 med Hz", lambda x: x["voice_f0_median_hz"]), ("F0 range st", lambda x: x["voice_f0_range_st"]),
         ("Pauses ≥250 ms", lambda x: x["pauses_ge_250ms"]), ("Voice on %", lambda x: x["voice_active_pct"]), ("SFX n", lambda x: x["sfx_events"]), ("SFX/10 s", lambda x: x["sfx_per_10s"]),
         ("Music BPM est", lambda x: x["music_bpm_est"]), ("Key est", lambda x: x["music_key_est"])]
    md = ("# Table: one row per video\n\nAll values are measured by the scripts in `analysis/scripts/` unless marked *est* (tempo and key are estimates from a separated, "
          "very quiet music stem; SFX counts come from a separated effects stem). View, like and comment counts are a snapshot taken "
          f"{recs[0]['snapshot_utc']} UTC. Upload time is exact for the 15 newest uploads (RSS feed) and date-only for #16–20. Full data: `analysis/data/videos.json`, `01_video_table.csv`.\n\n"
          "## A. Publishing and engagement\n\n" + md_table(recs, A) + "\n## B. Script and captions\n\n" + md_table(recs, B) +
          "\n## C. Picture\n\nJoins = places where two separately rendered takes meet. Moves = fast camera moves inside a take. Changes/min = joins + moves per minute. "
          "Beat = time between two consecutive changes. Still % = frames with optical flow under 0.05 % of frame height.\n\n" + md_table(recs, C) +
          "\n## D. Sound\n\n" + md_table(recs, D))
    (adir / "output" / "01_video_table.md").write_text(md)
    flat = [k for k in recs[0] if not isinstance(recs[0][k], (list, dict))]
    with open(adir / "output" / "01_video_table.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=flat, extrasaction="ignore")
        w.writeheader()
        w.writerows(recs)
    if quiet:
        return

    # ---- console digest
    show = ["duration_s", "words", "wpm", "sentences", "avg_sentence_words", "short_sentence_share_le5w", "hook_sentence_words", "hook_sentence_end_s", "words_in_first_3s", "first_word_start_s",
            "tail_after_last_word_s", "you_per_100w", "questions", "exclamations", "title_words", "title_words_in_first_sentence", "title_words_in_script", "last_sentence_words", "loop_overlap_words",
            "captions", "captions_per_s", "words_per_caption", "cap1_share", "cap2_share", "cap3plus_share", "caption_dur_median_s", "caption_lead_frames_median", "caption_centre_y_pct",
            "caption_line_top_px", "caption_glyph_h_px", "caption_coverage_pct", "caption_chars_median", "caption_chars_max", "caption_width_pct_median", "caption_width_pct_max", "caption_nonwhite_share",
            "joins", "cuts", "dissolves", "dissolve_share", "dissolve_len_frames_median", "inplace_blends", "take_mean_s", "take_max_s", "holds", "hold_median_s", "moves", "move_median_s", "move_time_pct",
            "move_peak_speed_median_pctH_s", "moves_per_min", "joins_per_min", "changes_per_min", "beat_median_s", "beat_mean_s", "beat_max_s", "still_frame_pct", "flow_median_pctH_s", "flow_p90_pctH_s",
            "hold_zoom_abs_median_pct_s", "hold_push_in_time_share", "hold_pull_out_time_share", "hold_static_time_share", "move_blur_sharp_ratio_median", "moves_changing_content_share",
            "luma_mean", "contrast_rms", "black_p01", "white_p99", "saturation_mean", "colorfulness", "warm_share", "cool_share", "vignette_ratio", "grain_sigma", "bloom_lift", "sharpness", "luma_1s_sd", "hold_luma_sd",
            "lufs_i", "true_peak_dbtp", "lra_lu", "stereo_side_mid_db", "voice_lufs", "voice_f0_median_hz", "voice_f0_range_st", "voice_active_pct", "voice_syll_per_s", "pauses_ge_120ms", "pauses_ge_250ms",
            "pause_max_s", "breath_like_events", "voice_level_spread_db", "voice_crest_db", "voice_centroid_hz", "voice_stereo_side_mid_db", "voice_tail_rt60_est_s", "music_lufs", "voice_minus_music_lu",
            "music_starts_s", "music_ends_before_end_s", "music_dropouts", "music_level_steps", "music_level_2s_sd_db", "music_voice_level_corr", "music_bpm_est", "music_pulse_strength", "music_centroid_hz",
            "music_stereo_side_mid_db", "sfx_events", "sfx_per_10s", "sfx_active_pct", "sfx_peak_median_dbfs", "sfx_peak_vs_voice_p50_db", "joins_at_sentence_start_share", "video_kbps", "like_rate_pct", "comments_per_1k_views"]
    print(f"{'metric':<34}{'mean':>9}{'sd':>8}{'median':>9}{'min':>9}{'max':>9}")
    for k in show:
        s = summary["metrics"].get(k)
        if s:
            print(f"{k:<34}{s['mean']:>9}{s['sd']:>8}{s['median']:>9}{s['min']:>9}{s['max']:>9}")
    for key in ("title_patterns", "music_keys", "sfx_class_totals_est", "camera_time_share_by_label", "sentence_words_hist", "music_match", "music_id"):
        print(key, json.dumps(summary.get(key))[:700])
    print("font:", [(x["font"], x["iou_mean"]) for x in summary.get("font_match", {}).get("ranking_top10", [])[:6]])
    print("openers:", [(o["word"], o["count"], o["videos"], o["median_position"]) for o in summary["sentence_openers"]])
    print("openers2:", [(o["words"], o["count"], o["videos"]) for o in summary["sentence_openers_2w"]])
    print("phrases:", [(o["phrase"], o["videos"]) for o in summary["phrases_in_many_videos"]])
    print("\nRANK BY VIEWS")
    for x in summary["rank_by_views"]:
        print(f"  {x['rank']:>2}. #{x['n']:<2} {x['views']:>11,} age {x['age_days']:>5} d  {x['views_per_day']:>10,}/d  {x['title']}")
    for key in ("top5_vs_bottom5_all", "top5_vs_bottom5_age_ge_8d"):
        print(key, [(c["metric"], c["top_mean"], c["bottom_mean"], c["diff_in_sd"]) for c in summary[key][:16]])
    print("views spearman (age>=8d):", [(c["metric"], c["rho"], c["p"]) for c in summary["views_spearman_age_ge_8d"][:14]])
    print("trend:", [(c["metric"], c["rho"], c["p"], c["oldest5_mean"], c["newest5_mean"]) for c in summary["trend_oldest_to_newest"][:16]])
    print("\nTRANSCRIPTS (sentence start s | text)")
    for rec in recs:
        print(f"\n## {rec['n']:02d} {rec['title']}  [{rec['duration_s']:.1f}s, {rec['words']}w]")
        print(" ".join(f"[{s['start']:.1f}] {s['text']}" for s in sents[rec["video"]]))


if __name__ == "__main__":
    main()
