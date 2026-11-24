#!/usr/bin/env python3
"""Write the numeric style bible from the measured data, so every number in it is traceable.

Usage: 25_style_bible.py <analysis_dir> <skill_dir>
Reads  <analysis>/data/{summary,videos,script_stats,reviews_summary,top3_tallies,caption_grouping,caption_style}.json
Writes <skill>/references/style-bible.md
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

M_, E_, B_ = "measured", "estimate", "by eye"
# (key, label, unit, decimals, confidence)
GROUPS = [
    ("Length and pace", "", [
        ("duration_s", "Runtime", "s", 1, M_), ("words", "Words", "", 0, M_), ("wpm", "Words per minute", "", 0, M_), ("voice_syll_per_s", "Syllables per second", "", 2, M_),
        ("sentences", "Sentences", "", 1, M_), ("avg_sentence_words", "Words per sentence, mean", "", 1, M_), ("median_sentence_words", "Words per sentence, median", "", 1, M_),
        ("max_sentence_words", "Longest sentence", "words", 0, M_), ("short_sentence_share_le5w", "Sentences of 5 words or fewer, share", "", 2, M_),
        ("first_word_start_s", "First word starts", "s", 2, M_), ("tail_after_last_word_s", "File ends after the last word", "s", 2, M_)]),
    ("Hook and title", "", [
        ("hook_sentence_words", "First sentence", "words", 1, M_), ("hook_sentence_end_s", "First sentence ends", "s", 2, M_), ("words_in_first_3s", "Words spoken in the first 3 s", "", 1, M_),
        ("title_words", "Title", "words", 1, M_), ("title_content_words", "Title content words", "", 1, M_), ("title_words_in_first_sentence", "Title content words repeated in the first sentence", "", 2, M_),
        ("title_words_in_script", "Title content words found anywhere in the script", "", 1, M_)]),
    ("Wording", "", [
        ("questions", "Questions", "", 2, M_), ("exclamations", "Exclamations", "", 2, M_), ("you_per_100w", "you / your per 100 words", "", 1, M_), ("you_see_count", "Sentences starting “You see”", "", 2, M_),
        ("last_sentence_words", "Last sentence", "words", 1, M_), ("last_sentence_start_rel", "Last sentence starts at (share of runtime)", "", 2, M_),
        ("loop_overlap_words", "Content words shared by the last and first sentence", "", 2, M_)]),
    ("Captions", "Details and drawing spec: `captions.md`.", [
        ("captions", "Captions per video", "", 0, M_), ("captions_per_s", "Captions per second", "", 2, M_), ("words_per_caption", "Words per caption", "", 2, M_), ("cap1_share", "One-word captions, share", "", 2, M_),
        ("cap2_share", "Two-word captions, share", "", 2, M_), ("cap3plus_share", "Three-word captions, share", "", 3, M_), ("caption_dur_median_s", "Time on screen, median", "s", 3, M_),
        ("caption_lead_frames_median", "Appears before its word", "frames", 2, M_), ("caption_centre_y_pct", "Vertical centre, % of height", "%", 2, M_), ("caption_coverage_pct", "Frames with a caption", "%", 2, M_),
        ("caption_chars_median", "Characters per caption, median", "", 1, M_), ("caption_chars_max", "Characters, longest caption", "", 1, M_), ("caption_width_pct_median", "Width, median, % of frame width", "%", 1, M_),
        ("caption_width_pct_max", "Width, widest caption", "%", 1, M_), ("caption_nonwhite_share", "Captions that are not white, share", "", 3, M_)]),
    ("Picture: takes and joins", "A *take* is one continuously rendered piece of picture. A *join* is where two takes meet.", [
        ("joins", "Joins per video", "", 1, M_), ("joins_per_min", "Joins per minute", "", 1, M_), ("cuts", "Hard cuts", "", 1, M_), ("dissolves", "Dissolves", "", 1, M_), ("dissolve_share", "Dissolves, share of joins", "", 2, M_),
        ("dissolve_len_frames_median", "Dissolve length, median", "frames", 1, M_), ("inplace_blends", "In-place changes (same framing, content or light changes)", "", 1, E_),
        ("take_mean_s", "Take length, mean", "s", 2, M_), ("take_median_s", "Take length, median", "s", 2, M_), ("take_max_s", "Longest take", "s", 1, M_),
        ("joins_at_sentence_start_share", "Dissolves that start within 3 frames of a sentence start, share", "", 2, M_)]),
    ("Picture: camera", "A *move* is a stretch where the whole image travels fast (smoothed optical flow of 27 % of the frame height per second or more). A *hold* is everything between moves; "
     "in a hold the camera still drifts or pushes in slowly. Speeds are in % of frame height per second.", [
        ("moves", "Fast camera moves per video", "", 1, M_), ("moves_per_min", "Fast moves per minute", "", 1, M_), ("move_median_s", "Move length, median", "s", 2, M_), ("move_time_pct", "Runtime spent in fast moves", "%", 1, M_),
        ("move_peak_speed_median_pctH_s", "Peak speed of a move, median", "% H/s", 1, M_), ("moves_changing_content_share", "Moves that end on different content (a new place or subject), share", "", 2, M_),
        ("move_blur_sharp_ratio_median", "Sharpness during a move relative to before it (1 = no motion blur)", "", 2, M_),
        ("holds", "Holds per video", "", 1, M_), ("hold_median_s", "Hold length, median", "s", 2, M_), ("hold_max_s", "Longest hold", "s", 1, M_),
        ("hold_zoom_abs_median_pct_s", "Zoom rate during holds, median", "%/s", 2, M_), ("hold_push_in_time_share", "Hold time spent pushing in", "", 2, M_),
        ("hold_pull_out_time_share", "Hold time spent pulling out", "", 2, M_), ("hold_static_time_share", "Hold time fully static", "", 3, M_),
        ("changes_per_min", "Picture changes (joins + moves) per minute", "", 1, M_), ("beat_median_s", "Time between two picture changes, median", "s", 2, M_),
        ("beat_mean_s", "Time between two picture changes, mean", "s", 2, M_), ("beat_max_s", "Longest stretch without a picture change", "s", 1, M_),
        ("still_frame_pct", "Frames with no motion at all", "%", 1, M_), ("flow_median_pctH_s", "Image motion, median", "% H/s", 1, M_), ("flow_p90_pctH_s", "Image motion, 90th percentile", "% H/s", 1, M_)]),
    ("Colour and image", "Measured on the files as YouTube serves them (about 3.7 Mbit/s), with the caption line masked out. Sharpness, grain and bloom depend on that compression, so treat them as estimates.", [
        ("luma_mean", "Brightness (luma mean, 0–255)", "", 1, M_), ("contrast_rms", "Contrast (luma standard deviation)", "", 1, M_), ("black_p01", "Black level (1st percentile)", "", 1, M_),
        ("white_p99", "White level (99th percentile)", "", 1, M_), ("saturation_mean", "Saturation (HSV S mean, 0–255)", "", 1, M_), ("colorfulness", "Colourfulness (Hasler–Süsstrunk)", "", 1, M_),
        ("warm_share", "Warm hues, share of saturated pixels", "", 2, M_), ("cool_share", "Cool hues, share of saturated pixels", "", 2, M_), ("warm_dominant_time_share", "Runtime where warm hues dominate", "", 2, M_),
        ("luma_1s_sd", "Brightness change through the video (SD of 1 s means)", "", 1, M_), ("sat_1s_sd", "Saturation change through the video (SD of 1 s means)", "", 1, M_),
        ("vignette_ratio", "Corner brightness / centre brightness", "", 2, M_), ("sharpness", "Sharpness (variance of the Laplacian at 540 × 960)", "", 0, E_), ("grain_sigma", "Grain (noise SD, 8-bit)", "", 2, E_),
        ("bloom_lift", "Glow around highlights (luma lift)", "", 1, E_)]),
    ("Sound", "Details and mix targets: `sound.md`. Stem values come from software separation of voice, music and effects.", [
        ("lufs_i", "Integrated loudness", "LUFS", 1, M_), ("true_peak_dbtp", "True peak", "dBTP", 1, M_), ("lra_lu", "Loudness range", "LU", 1, M_), ("stereo_side_mid_db", "Stereo width (side vs mid)", "dB", 1, M_),
        ("voice_active_pct", "Voice sounding, share of runtime", "%", 1, M_), ("pauses_ge_250ms", "Pauses of 250 ms or more", "", 1, M_), ("pauses_ge_120ms", "Pauses of 120 ms or more", "", 1, M_),
        ("voice_f0_median_hz", "Voice pitch, median", "Hz", 0, E_), ("voice_f0_range_st", "Voice pitch range, 5th–95th percentile", "semitones", 1, E_), ("voice_lufs", "Voice loudness", "LUFS", 1, E_),
        ("voice_level_spread_db", "Voice level spread, 10th–90th percentile", "dB", 1, E_), ("music_lufs", "Music loudness", "LUFS", 1, E_), ("voice_minus_music_lu", "Voice above music", "LU", 1, E_),
        ("music_starts_s", "Music starts", "s", 2, E_), ("music_ends_before_end_s", "Music stops before the end of the file", "s", 2, E_), ("music_level_2s_sd_db", "Music level variation (SD of 2 s windows)", "dB", 1, E_),
        ("music_voice_level_corr", "Music level follows voice level (correlation; ducking would be strongly negative)", "", 2, E_), ("music_bpm_est", "Music tempo", "BPM", 0, E_),
        ("music_centroid_hz", "Music brightness (spectral centroid)", "Hz", 0, E_), ("sfx_events", "Sound-effect events per video", "", 0, E_), ("sfx_per_10s", "Sound effects per 10 s", "", 1, E_),
        ("sfx_active_pct", "Runtime with an effect sounding", "%", 0, E_), ("sfx_peak_median_dbfs", "Effect peak, median", "dBFS", 1, E_), ("sfx_peak_vs_voice_p50_db", "Effect peak relative to the voice", "dB", 1, E_)]),
    ("Publishing", "Counts are a snapshot (see `analysis/output/01_video_table.md` for the time).", [
        ("views", "Views", "", 0, M_), ("views_per_day", "Views per day since upload", "", 0, M_), ("like_rate_pct", "Likes per 100 views", "", 2, M_), ("comments_per_1k_views", "Comments per 1,000 views", "", 3, M_),
        ("video_kbps", "Video bitrate as served", "kbit/s", 0, M_), ("size_mb", "File size as served", "MB", 1, M_)]),
]


def f(x, nd):
    if x is None:
        return "–"
    if nd == 0:
        return f"{x:,.0f}"
    return f"{x:,.{nd}f}"


def table(S, rows):
    out = ["| | Mean | Median | Middle 80 % | Min – Max | Confidence |", "|---|---|---|---|---|---|"]
    for key, label, unit, nd, conf in rows:
        s = S.get(key)
        if not s:
            continue
        u = f" {unit}" if unit else ""
        out.append(f"| {label} | {f(s['mean'], nd)}{u} | {f(s['median'], nd)} | {f(s['p10'], nd)} – {f(s['p90'], nd)} | {f(s['min'], nd)} – {f(s['max'], nd)} | {conf} |")
    return out


def share_table(title, d, n, unit="videos"):
    out = [f"| {title} | {unit.capitalize()} | Share |", "|---|---|---|"]
    for k, c in d.items():
        out.append(f"| {k} | {c} | {c / n:.0%} |")
    return out


def main():
    adir, skill = Path(sys.argv[1]), Path(sys.argv[2])
    D = adir / "data"
    J = lambda n: json.loads((D / n).read_text()) if (D / n).exists() else {}
    S, V, SS, RV, T3, CG = J("summary.json"), J("videos.json"), J("script_stats.json"), J("reviews_summary.json"), J("top3_tallies.json"), J("caption_grouping.json")
    M = S["metrics"]
    n = S["n_videos"]
    o = ["# Style bible: the numbers", "",
         f"Everything here was measured on the {n} newest uploads of the reference channel (all Shorts; the channel has no long videos). This file is generated by "
         "`analysis/scripts/25_style_bible.py` from `analysis/data/`, so the numbers match the data exactly.", "",
         "**How to read the tables.** *Mean* and *Median* are across the 20 videos. *Middle 80 %* runs from the 10th to the 90th percentile: aim inside it. *Min – Max* is the full spread: "
         "staying inside it keeps you within what the channel itself does. Confidence: **measured** = read directly from the file; **estimate** = from separated audio stems, a heuristic "
         "classifier, or a property that YouTube's compression changes; **by eye** = one reviewer per video looked at frames (16 – 20 of the videos, stated per table).", "",
         "## The format on one screen", "",
         "| | |", "|---|---|",
         "| Frame | 1080 × 1920 (9:16), 30 fps, H.264, about 3.7 Mbit/s as served; AAC stereo 44.1 kHz |",
         f"| Length | {M['duration_s']['mean']:.0f} s ({M['duration_s']['p10']:.0f} – {M['duration_s']['p90']:.0f}), {M['words']['mean']:.0f} words, {M['wpm']['mean']:.0f} words per minute, no pause of 250 ms anywhere |",
         f"| Script | {M['sentences']['mean']:.0f} sentences of {M['avg_sentence_words']['mean']:.0f} words; the first one is {M['hook_sentence_words']['mean']:.0f} words and ends at {M['hook_sentence_end_s']['mean']:.1f} s; "
         f"{M['questions']['mean']:.0f} question; no call to action |",
         f"| Captions | always on; {M['words_per_caption']['mean']:.2f} words each, {M['captions_per_s']['mean']:.1f} per second; white with a black outline; centred at {M['caption_centre_y_pct']['mean']:.0f} % of the height; "
         f"{M['caption_lead_frames_median']['mean']:.1f} frames ahead of the voice |",
         f"| Picture | {M['joins']['mean']:.0f} takes joined mostly by {M['dissolve_len_frames_median']['mean']:.0f}-frame dissolves; {M['moves']['mean']:.0f} fast camera moves; something changes every "
         f"{M['beat_median_s']['mean']:.1f} s; the camera pushes in for {M['hold_push_in_time_share']['mean']:.0%} of the rest; {M['hold_static_time_share']['mean']:.0%} of hold time is static |",
         f"| Colour | brightness {M['luma_mean']['mean']:.0f} of 255, contrast {M['contrast_rms']['mean']:.0f}, saturation {M['saturation_mean']['mean']:.0f} of 255; warm and cool hues in balance "
         f"({M['warm_share']['mean']:.0%} / {M['cool_share']['mean']:.0%}) |",
         f"| Sound | {M['lufs_i']['mean']:.1f} LUFS, true peak {M['true_peak_dbtp']['mean']:.1f} dBTP; voice on {M['voice_active_pct']['mean']:.0f} % of the time; music {M['voice_minus_music_lu']['mean']:.0f} LU under the voice, "
         f"never ducked; {M['sfx_per_10s']['mean']:.0f} effects per 10 s |",
         "| Technique (by eye) | flat, thick-outlined 2D characters standing in lit 3D sets; faces change by swapping drawn expressions; the camera does most of the moving |"]
    for title, note, rows in GROUPS:
        o += ["", f"## {title}", ""]
        if note:
            o += [note, ""]
        o += table(M, rows)
        if title == "Length and pace":
            h = S["sentence_words_hist"]
            tot = sum(h.values())
            p = S["sentence_words_pooled"]
            o += ["", f"Sentence length over all {p['n']:.0f} sentences: " + ", ".join(f"{k} words {v / tot:.0%}" for k, v in h.items()) + f". Median {p['median']:.0f}, 10th – 90th percentile {p['p10']:.0f} – {p['p90']:.0f}.",
                  "", "Pace through the video, words per minute in 10 s windows (mean of 20): " + ", ".join(
                      f"{sum(v['wpm_by_10s'][i] for v in V if len(v['wpm_by_10s']) > i) / sum(1 for v in V if len(v['wpm_by_10s']) > i):.0f}" for i in range(6)) + "."]
        if title == "Wording" and SS:
            P = SS["pooled"]
            o += ["", "| | Mean | Min – Max | Confidence |", "|---|---|---|---|"]
            for k, label, nd in (("flesch_kincaid_grade", "Reading grade (Flesch–Kincaid)", 1), ("flesch_reading_ease", "Flesch reading ease", 0), ("syllables_per_word", "Syllables per word", 2),
                                 ("letters_per_word", "Letters per word", 2), ("words_ge_3_syllables_share", "Words of 3 or more syllables, share", 3), ("conjunction_opener_share", "Sentences opening with So / And / But / Then …, share", 2),
                                 ("contractions_per_100w", "Contractions per 100 words", 1), ("numbers_per_script", "Number words and figures per script", 1), ("time_jump_phrases", "Time-jump phrases (“the next morning”, “by midnight” …)", 1),
                                 ("speech_verb_sentences", "Sentences with a speech verb (says, goes, asks …)", 1), ("explainer_turn_rel", "Late “You see” / “Well” turn, share of runtime (13 videos)", 2)):
                s = P.get(k)
                if s:
                    o.append(f"| {label} | {f(s['mean'], nd)} | {f(s['min'], nd)} – {f(s['max'], nd)} | measured (syllables estimated) |")
            o += ["", "How sentences open (all sentences after the first, pooled):", "", "| Opening | Share |", "|---|---|"] + [f"| {k} | {v:.0%} |" for k, v in SS["sentence_opener_share_pooled"].items()]
            o += ["", "Most frequent first words: " + ", ".join(f"*{x['word']}* {x['count']}" for x in S["sentence_openers"][:10]) + ". Two-word openings found in 4 or more videos: " +
                  ", ".join(f"*{x['words']}* ({x['videos']} videos)" for x in S["sentence_openers_2w"][:8]) + ".",
                  "", f"“You see” appears in {SS['videos_with_you_see']} of {n} videos: as the second sentence in {SS['videos_with_you_see_as_second_sentence']}, and as a late turn into the explanation "
                  f"(after 30 % of the runtime, with “You see” or “Well”) in {SS['videos_with_late_explainer_turn_after_30pct']}. {SS['videos_with_question']} videos contain a question; "
                  f"{SS['videos_with_it_is_called']} name the phenomenon with “it's called …”.",
                  "", "First-sentence forms: " + ", ".join(f"{k} {v}" for k, v in SS["hook_forms"].items()) + f". {SS.get('hooks_with_turn', '?')} of {n} first sentences contain a turn (a comma, *and*, *but*, *yet*, *because*).",
                  "", "Title openings: " + ", ".join(f"{k} {v}" for k, v in S["title_patterns"].items()) + "."]
        if title == "Captions" and CG:
            r = CG["best_rule_matching_words_per_caption"]
            o += ["", f"Grouping rule fitted to the real caption boundaries (agreement {r['boundary_agreement']:.1%}, gives {r['words_per_caption']:.2f} words per caption): join two words when the shorter has "
                  f"at most {r['SHORT']} letters and the pair is at most {r['MAXCHARS']} characters; allow a third short word up to {r['MAX3']} characters; never continue past `{r['stop_punct']}`."]
        if title == "Picture: takes and joins" and RV:
            jc = RV["join_check"]
            o += ["", f"Detector check by eye on {RV['n_reviewed']} videos: of the automatically found joins, {jc['precision'].get('dissolve', 0):.0%} of the dissolves and {jc['precision'].get('cut', 0):.0%} of the "
                  f"cuts were confirmed; the reviewers found {jc['missed_joins_found_by_eye']} joins the detector missed, so it finds about {jc['recall_cut_or_dissolve']:.0%} of them. "
                  f"Of the items flagged as in-place changes, {jc['precision'].get('inplace_blend', 0):.0%} were confirmed as such; most of the rest were dissolves. "
                  "So the join counts above are slightly low (by roughly one per video)."]
        if title == "Picture: camera":
            cam = S["camera_time_share_by_label"]
            o += ["", "Share of the total runtime by measured camera state: " + "; ".join(f"{k} {v:.0%}" for k, v in list(cam.items())[:8]) + ". The labels come from fitting zoom, pan, tilt and roll to the "
                  "optical flow; “orbit / fly-through” means the motion did not fit a flat pan or zoom, as when the camera travels through the set.",
                  "", "Picture changes per 5 s through the video (mean of 20): " + ", ".join(
                      f"{sum(v['change_curve_per_5s'][i] for v in V if len(v['change_curve_per_5s']) > i) / sum(1 for v in V if len(v['change_curve_per_5s']) > i):.1f}" for i in range(12)) +
                  ". The rate is steady from the first second to the last; it does not start fast and settle."]
        if title == "Sound":
            keys, cls = S["music_keys"], S["sfx_class_totals_est"]
            tot = sum(cls.values())
            o += ["", "Music key (estimate): " + ", ".join(f"{k} {v}" for k, v in keys.items()) + ". No two of the 20 videos use the same track (pairwise similarity at most "
                  f"{S['music_match']['offdiag_similarity_max']:.2f}, where the same recording would score 0.9 or more).",
                  "", "Sound-effect classes (estimate, share of " + f"{tot} events): " + ", ".join(f"{k} {v / tot:.0%}" for k, v in cls.items()) + "."]
            sp = S["sync_pooled"]
            o += ["", "What picture changes are timed to (share within 3 frames, against chance):", "", "| | Within 3 frames | By chance |", "|---|---|---|"]
            for k, label in (("dissolve_start__vs__sentence_start", "A dissolve starts at a sentence start"), ("cut__vs__sentence_start", "A hard cut falls at a sentence start"),
                             ("move_start__vs__sentence_start", "A fast camera move starts at a sentence start"), ("join_mid__vs__sfx_onset", "A join has a sound effect starting on it"),
                             ("move_start__vs__sfx_onset", "A fast camera move has a sound effect starting on it"), ("join_mid__vs__music_beat", "A join falls on a music beat"),
                             ("sfx_onset__vs__sentence_start", "A sound effect starts at a sentence start")):
                if k in sp:
                    o.append(f"| {label} | {sp[k]['within_3f']:.0%} | {sp[k]['chance_within_3f']:.0%} |")
    # ---- by eye
    if RV:
        nr, T, st = RV["n_reviewed"], RV["tallies"], RV["structure_targets"]
        o += ["", f"## Story structure (by eye, {nr} videos)", "",
              "One reviewer per video split the runtime into beats and coded the story. Positions are shares of the runtime.", "",
              "| Beat | Starts at, median | Range | Share of runtime, median | Present in |", "|---|---|---|---|---|"]
        for b in ("hook", "setup", "escalation", "twist", "explainer", "payoff", "ending"):
            a, sh = st["beat_start_rel"].get(b), st["beat_share_of_runtime"].get(b)
            if a:
                o.append(f"| {b} | {a['median']:.0%} | {a['min']:.0%} – {a['max']:.0%} | {sh['median']:.0%} | {a['n']} of {nr} |")
        o += ["", f"The hook beat ends at {st['hook_end_s']['median']:.1f} s (median; {st['hook_end_s']['min']:.1f} – {st['hook_end_s']['max']:.1f}). The ending beat starts at "
              f"{st['ending_start_rel']['median']:.0%} of the runtime. Lines of direct speech per video: median {st['direct_speech_lines']['median']:.0f} "
              f"({st['direct_speech_lines']['min']:.0f} – {st['direct_speech_lines']['max']:.0f}). A separate explainer beat exists in {st['explainer_turn_rel']['n']} of {nr} videos and starts at "
              f"{st['explainer_turn_rel']['median']:.0%} of the runtime (median); in the others the explanation is folded into the story or the twist explains itself."]
        for key, title in (("story.structure", "Structure"), ("hook.line_type", "Kind of first line"), ("story.topic_type", "Topic"), ("story.setting_era", "Setting"),
                           ("story.likely_source_type", "Likely source of the story"), ("story.ending_type", "Ending"), ("story.tense", "Tense"), ("story.second_person", "Told in the second person"),
                           ("story.call_to_action", "Call to action")):
            if key in T:
                o += [""] + share_table(title, T[key], nr)
        o += ["", f"## First frame (by eye, {nr} videos)", ""] + share_table("Subject of frame 0", T.get("hook.first_frame_subject", {}), nr) + [""] + share_table("Shot size of frame 0", T.get("hook.first_frame_shot_size", {}), nr) + [
            ""] + share_table("Protagonist looks at the camera in frame 0", T.get("hook.protagonist_looks_at_camera", {}), nr)
        nenv = sum(T.get("env.has_in_world_text", {}).values()) or 1
        ne = Counter({int(k): v for k, v in T.get("n_environments", {}).items()})
        nc = Counter({int(k): v for k, v in T.get("n_characters", {}).items()})
        nfx = Counter({int(k): v for k, v in T.get("n_effects", {}).items()})
        mean = lambda c: sum(k * v for k, v in c.items()) / max(sum(c.values()), 1)
        o += ["", f"## Characters, sets and effects (by eye, {nr} videos)", "",
              f"- Recurring characters per video: {mean(nc):.1f} on average (the review form allowed at most 4).",
              f"- Distinct places per video: {mean(ne):.1f} on average ({min(ne)} – {max(ne)}); {T.get('env.has_in_world_text', {}).get('True', T.get('env.has_in_world_text', {}).get('true', 0)) / nenv:.0%} of the "
              f"{nenv} places show readable in-world text (signs, labels, screens, calendars).",
              f"- Visual effects noted per video: {mean(nfx):.1f} on average ({min(nfx)} – {max(nfx)}). By type: " + ", ".join(f"{k} {v}" for k, v in list(T.get("effects.type", {}).items())[:10]) + ".",
              "- Head height as a share of body height (estimate): " + ", ".join(f"{k} in {v}" for k, v in T.get("_head_share", {}).items()) + ".",
              "- Set style: " + ", ".join(f"{k} in {v}" for k, v in T.get("set_style", {}).items()) + " (“mixed” = 3D sets with flat outlined characters).",
              "- Mouths: " + ", ".join(f"{k} in {v}" for k, v in T.get("animation.lip_sync", {}).items()) + ". The reviewers sampled frames 2 – 8 frames apart, so this is not a syllable-level check.",
              "- Shadow under the characters: " + ", ".join(f"{k} in {v}" for k, v in T.get("character.shadow", {}).items()) + ".",
              "- Light and depth, share of the " + f"{nenv} places whose notes mention it: " + ", ".join(f"{k} {v / nenv:.0%}" for k, v in RV.get("depth_and_light_keywords_by_environment", {}).items()) + ".",
              "- What the frames suggest about how the picture is made (count of reviewer observations): " + ", ".join(f"{k} {v}" for k, v in T.get("evidence.points_to", {}).items()) + "."]
    if T3 and T3.get("seconds_logged"):
        o += ["", f"## Shot sizes and what the picture does (by eye, the 3 most-viewed videos, {T3['seconds_logged']} seconds)", "",
              f"A new place or framing every {T3['seconds_per_setup']} s.", "", "| Shot size | Share of seconds |", "|---|---|"] + [f"| {k} | {v:.0%} |" for k, v in T3["shot_size_share"].items()] + [
              "", "| Main subject | Share of seconds |", "|---|---|"] + [f"| {k} | {v:.0%} |" for k, v in T3["subject_share"].items()] + [
              "", "| The picture | Share of seconds |", "|---|---|"] + [f"| {k} | {v:.0%} |" for k, v in T3["picture_job_share"].items()]
    # ---- fixed vs free
    cv = []
    skip = {"views", "likes", "comments", "views_per_day", "age_days_at_snapshot", "fps", "audio_hz", "audio_ch", "audio_kbps", "uploader_comments_in_top100", "last_word_end_s", "caption_line_top_px", "music_key_score",
            # near zero in every video: a spread relative to the mean says nothing, they are listed under "never" instead
            "pauses_ge_120ms", "pauses_ge_250ms", "hold_static_time_share", "caption_nonwhite_share", "loop_overlap_words", "music_starts_s", "music_ends_before_end_s", "music_voice_level_corr",
            "cap3plus_share", "views", "comments_per_1k_views", "like_rate_pct", "video_kbps", "size_mb"}
    label = {k: lab for _, _, rows in GROUPS for k, lab, *_ in rows}
    for k, s in M.items():
        if s and k not in skip and k in label and abs(s["mean"]) > 1e-9 and s["min"] >= 0:
            cv.append((s["sd"] / abs(s["mean"]), k))
    cv.sort()
    o += ["", "## What is fixed and what is free", "",
          "Spread across the 20 videos as a share of the mean (coefficient of variation). A small spread means the channel does it the same way every time; treat those as rules. A large spread means "
          "it changes with the story.", "",
          "**Fixed (spread under 6 %):** " + "; ".join(f"{label[k]} ({c:.1%})" for c, k in cv if c < 0.06) + ".", "",
          "**Free (spread over 40 %):** " + "; ".join(f"{label[k]} ({c:.0%})" for c, k in cv[::-1] if c > 0.40) + ".", "",
          f"**Never, or almost never (of {n} videos):** a pause of 250 ms or more ({sum(v['pauses_ge_250ms'] > 0 for v in V)} videos); a caption that is not white "
          f"({sum(v['caption_nonwhite_share'] > 0.01 for v in V)} videos above 1 % of captions); a frame without a caption ({sum(v['caption_coverage_pct'] < 99.9 for v in V)} videos below 99.9 % coverage); "
          f"a fully static hold (more than 5 % of hold time in {sum(v['hold_static_time_share'] > 0.05 for v in V)} videos); music that starts later than half a second in "
          f"({sum(v['music_starts_s'] > 0.5 for v in V)} videos); a last sentence that repeats the first one (2 or more shared content words in {sum(v['loop_overlap_words'] >= 2 for v in V)} videos); "
          f"a creator comment among the top comments fetched ({sum(v['uploader_comments_in_top100'] > 0 for v in V)} videos); a hashtag in the title or description (0 videos).", "",
          "## Change over the five weeks covered", "",
          "Rank correlation with upload order (oldest to newest), strongest first. With 20 videos these are tendencies, not laws.", "",
          "| | Oldest 5, mean | Newest 5, mean | Rank correlation |", "|---|---|---|---|"]
    for t in S["trend_oldest_to_newest"]:
        if t["metric"] in label and abs(t["rho"]) >= 0.5 and t["metric"] not in ("likes", "views", "like_rate_pct"):
            o.append(f"| {label[t['metric']]} | {t['oldest5_mean']:g} | {t['newest5_mean']:g} | {t['rho']:+.2f} |")
    (skill / "references").mkdir(parents=True, exist_ok=True)
    text = re.sub(r"(\d)%", r"\1 %", "\n".join(o) + "\n")
    (skill / "references" / "style-bible.md").write_text(text)
    print("style bible:", len(o), "lines;", sum(len(r) for _, _, r in GROUPS), "metric rows")


if __name__ == "__main__":
    main()
