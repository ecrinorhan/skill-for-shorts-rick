#!/usr/bin/env python3
"""Per-video cards: metadata, measurements and the by-eye review of each video in one Markdown file.

Usage: 23_cards.py <analysis_dir>
Reads  <analysis>/data/videos.json, summary.json, script_stats.json, reviews/<video>.json
Writes <analysis>/output/02_video_cards.md

The only narration quoted is the first sentence of each video (the hook), as a short quotation for analysis.
Everything else about the wording is a paraphrase written by the reviewer.
"""
import json
import sys
from pathlib import Path

STAND = [("duration_s", "runtime", "s"), ("words", "words", ""), ("wpm", "words per minute", ""), ("sentences", "sentences", ""), ("avg_sentence_words", "words per sentence", ""),
         ("hook_sentence_words", "first-sentence length", "words"), ("questions", "questions", ""), ("you_per_100w", "'you' per 100 words", ""), ("joins", "joins between takes", ""),
         ("cuts", "hard cuts", ""), ("dissolve_share", "share of joins that are dissolves", ""), ("take_mean_s", "mean take length", "s"), ("moves", "fast camera moves", ""),
         ("move_time_pct", "runtime in fast moves", "%"), ("changes_per_min", "picture changes per minute", ""), ("still_frame_pct", "fully still frames", "%"),
         ("hold_zoom_abs_median_pct_s", "slow zoom during holds", "%/s"), ("luma_mean", "brightness", ""), ("contrast_rms", "contrast", ""), ("saturation_mean", "saturation", ""),
         ("colorfulness", "colourfulness", ""), ("warm_share", "warm-hue share", ""), ("voice_f0_median_hz", "voice pitch", "Hz"), ("voice_minus_music_lu", "voice above music", "LU"),
         ("music_bpm_est", "music tempo (est.)", "BPM"), ("sfx_per_10s", "sound effects per 10 s", ""), ("like_rate_pct", "likes per 100 views", ""), ("comments_per_1k_views", "comments per 1,000 views", "")]


def g(d, *keys, default="–"):
    for k in keys:
        if not isinstance(d, dict) or d.get(k) in (None, ""):
            return default
        d = d[k]
    return d


def cell(s):
    return str(s).replace("|", "/").replace("\n", " ").strip()


def main():
    adir = Path(sys.argv[1])
    V = json.loads((adir / "data" / "videos.json").read_text())
    S = json.loads((adir / "data" / "summary.json").read_text())
    SS = {p["video"]: p for p in json.loads((adir / "data" / "script_stats.json").read_text())["videos"]}
    M = S["metrics"]
    rank = {x["n"]: x["rank"] for x in S["rank_by_views"]}
    R = {}
    for v in V:
        p = adir / "data" / "reviews" / f"{v['video']}.json"
        R[v["n"]] = json.loads(p.read_text()) if p.exists() else {}
    out = ["# Per-video cards", "",
           "One card per video, newest first (#1 is the newest upload). Numbers are measured by the scripts in `analysis/scripts/`; values marked *est.* come from separated audio stems or "
           "heuristic classifiers. Everything under **By eye** was written by one reviewer per video who looked at contact sheets, join sheets and frame montages "
           "(`analysis/review/REVIEW_PROMPT.md`); it is an observation, not a measurement, and was not cross-checked by a second reviewer. View, like and comment counts are the "
           f"snapshot of {V[0]['snapshot_utc']} UTC.", "",
           "The first sentence of each video is quoted because the hook is the thing being studied. No other narration is reproduced; beat descriptions are paraphrases.", "",
           "## Overview: story coding (by eye)", "",
           "| # | Title | Topic | Era | Structure | Hook type | Ending | Speech lines | Characters | Places | Effects |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in V:
        r = R[v["n"]]
        out.append(f"| {v['n']} | {cell(v['title'])} | {cell(g(r, 'story', 'topic_type'))} | {cell(g(r, 'story', 'setting_era'))} | {cell(g(r, 'story', 'structure'))} | {cell(g(r, 'hook', 'line_type'))} | "
                   f"{cell(g(r, 'story', 'ending_type'))} | {g(r, 'story', 'direct_speech_lines')} | {len(r.get('characters', [])) or '–'} | {len(r.get('environments', [])) or '–'} | {len(r.get('effects', [])) or '–'} |")
    out += ["", "## Overview: hooks", "", "| # | First sentence | Words | Ends at | Form | First frame shows | Looks at camera |", "|---|---|---|---|---|---|---|"]
    for v in V:
        r = R[v["n"]]
        out.append(f"| {v['n']} | “{cell(v['hook_sentence'])}” | {v['hook_sentence_words']} | {v['hook_sentence_end_s']:.1f} s | {SS[v['video']]['hook_form']} | {cell(g(r, 'hook', 'first_frame_subject'))}, "
                   f"{cell(g(r, 'hook', 'first_frame_shot_size'))} | {('yes' if g(r, 'hook', 'protagonist_looks_at_camera') is True else 'no' if g(r, 'hook', 'protagonist_looks_at_camera') is False else '–')} |")
    for v in V:
        r, n = R[v["n"]], v["n"]
        st = SS[v["video"]]
        up = v["published_utc"][:16].replace("T", " ") + " UTC" if v["published_precision"] == "second" else v["published_utc"][:10] + " (date only)"
        out += ["", f"## {n} · {v['title']}", "", f"<{v['url']}> · uploaded {up} · {v['duration_s']:.1f} s · {v['width']}×{v['height']}, {v['fps']:g} fps", "",
                f"**Reach.** {v['views']:,} views (rank {rank[n]} of 20) · {v['likes']:,} likes ({v['like_rate_pct']} per 100 views) · {v['comments']:,} comments "
                f"({v['comments_per_1k_views']} per 1,000 views) · {v['views_per_day']:,} views per day over {v['age_days_at_snapshot']} days.", "",
                f"**Listing.** Description: “{cell(v['description'])}”{' (same as the title)' if v['description'] == v['title'] else ''} · hashtags: none · tags: not readable (see `05_limitations.md`) · "
                f"pinned comment: none among the fetched comments · creator comments among them: {v['uploader_comments_in_top100']} · YouTube label: "
                f"{('“' + v['how_this_was_made'] + '”') if v['how_this_was_made'] else 'none returned'} · sound credit: “{v['sound_attribution']}”.", "",
                f"**Hook.** “{v['hook_sentence']}” · {v['hook_sentence_words']} words, ends at {v['hook_sentence_end_s']:.2f} s · {v['words_in_first_3s']} words spoken in the first 3 s · form: {st['hook_form']}."]
        if r:
            h, s, t = r.get("hook", {}), r.get("story", {}), r.get("tone", {})
            out += ["", "**By eye: hook.** " + f"Frame 0: {cell(g(h, 'first_frame'))} First 3 s: {cell(g(h, 'first_3s'))} Title and first line: {cell(g(h, 'title_vs_first_line'))}",
                    "", f"**By eye: story.** Topic: {cell(g(s, 'topic_type'))} · era: {cell(g(s, 'setting_era'))} · structure: {cell(g(s, 'structure'))} · likely source: {cell(g(s, 'likely_source_type'))} · "
                    f"tense: {cell(g(s, 'tense'))} · second person: {'yes' if s.get('second_person') else 'no'} · direct-speech lines: {g(s, 'direct_speech_lines')} · explainer turn: {cell(g(s, 'explainer_turn'))} · "
                    f"ending: {cell(g(s, 'ending_type'))} · call to action: {cell(g(s, 'call_to_action'))}.",
                    "", f"Fact core as the reviewer understood it (not fact-checked): {cell(g(s, 'real_fact_core'))}",
                    "", f"Protagonist: {cell(g(s, 'protagonist'))}. Opposing figure: {cell(g(s, 'authority_or_antagonist'))}.",
                    "", f"Tone: {cell(g(t, 'humour'))} {cell(g(t, 'deadpan_or_irony'))} Dialogue: {cell(g(t, 'dialogue_style'))}",
                    "", "| Beat | Time | What the narration does (paraphrase) | What is on screen |", "|---|---|---|---|"]
            for b in r.get("beats", []):
                out.append(f"| {cell(b.get('name'))} | {float(b['start']):.1f} – {float(b['end']):.1f} s | {cell(b.get('said'))} | {cell(b.get('shown'))} |")
        yq = ", ".join(f"{x * v['duration_s']:.0f} s" for x in st["question_positions"]) or "none"
        ys = ", ".join(f"{x * v['duration_s']:.0f} s" for x in st["you_see_positions"]) or "not used"
        out += ["", f"**Script numbers.** {v['words']} words at {v['wpm']} words per minute · {v['sentences']} sentences, {v['avg_sentence_words']} words on average, longest {v['max_sentence_words']} · "
                f"{v['questions']} question(s) at {yq} · “You see” at {ys} · {v['you_per_100w']} ‘you’ per 100 words · reading grade {st['flesch_kincaid_grade']} (Flesch-Kincaid) · "
                f"{round(st['conjunction_opener_share'] * 100)} % of sentences open with So / And / But / Then · last sentence {v['last_sentence_words']} words, starting at "
                f"{round(v['last_sentence_start_rel'] * 100)} % of the runtime · silence after the last word {v['tail_after_last_word_s']} s.", "",
                f"**Captions.** {v['captions']} captions, {v['captions_per_s']} per second, {v['words_per_caption']} words each ({round(v['cap1_share'] * 100)} % one word, {round(v['cap2_share'] * 100)} % two) · "
                f"median {v['caption_dur_median_s']} s on screen · appear {v['caption_lead_frames_median']} frames before the word · centre at {v['caption_centre_y_pct']} % of the height.", "",
                f"**Picture.** {v['joins']} joins between takes: {v['cuts']} hard cuts, {v['dissolves']} dissolves (median {v['dissolve_len_frames_median']:g} frames) · takes average {v['take_mean_s']} s, longest "
                f"{v['take_max_s']:.1f} s · {v['moves']} fast camera moves (median {v['move_median_s']} s, {v['move_time_pct']} % of the runtime) · {v['changes_per_min']} picture changes per minute, "
                f"one every {v['beat_median_s']} s (median) · between moves the camera pushes in for {round(v['hold_push_in_time_share'] * 100)} % of the time at {v['hold_zoom_abs_median_pct_s']} % per second (median) · "
                f"fully still frames {v['still_frame_pct']} %.", "",
                f"**Colour.** Brightness {v['luma_mean']} of 255 · contrast {v['contrast_rms']} · saturation {v['saturation_mean']} of 255 · colourfulness {v['colorfulness']} · warm hues {round(v['warm_share'] * 100)} % and "
                f"cool hues {round(v['cool_share'] * 100)} % of the saturated pixels · corner brightness {round(v['vignette_ratio'] * 100)} % of the centre · five largest colour clusters: "
                + " ".join(f"`{c}`" for c in v["palette_top5"]) + ".", "",
                f"**Sound.** Mix {v['lufs_i']} LUFS, true peak {v['true_peak_dbtp']} dBTP, loudness range {v['lra_lu']} LU · voice pitch {v['voice_f0_median_hz']} Hz (median) over {v['voice_f0_range_st']} semitones, "
                f"{v['voice_syll_per_s']} syllables per second, voice on for {v['voice_active_pct']} % of the runtime, {v['pauses_ge_250ms']} pauses of 250 ms or more · music *est.* {v['music_lufs']} LUFS, "
                f"{v['voice_minus_music_lu']} LU under the voice, about {v['music_bpm_est']:g} BPM in {v['music_key_est']} · *est.* {v['sfx_events']} sound-effect events, {v['sfx_per_10s']} per 10 s, median peak "
                f"{v['sfx_peak_median_dbfs']} dBFS."]
        if r:
            out += ["", "**By eye: characters.**"]
            for c in r.get("characters", []):
                out.append(f"- *{cell(c.get('role'))}*: head {cell(c.get('head'))}; hair or hat {cell(c.get('hair_or_hat'))}; eyes {cell(c.get('eyes'))}; mouth {cell(c.get('mouth'))}; body {cell(c.get('body_and_clothes'))}; "
                           f"limbs {cell(c.get('limbs'))}; carries {cell(c.get('accessories'))}; expressions seen: {', '.join(map(str, c.get('expressions_seen', []))) or '–'}.")
            cs, an = r.get("character_style", {}), r.get("animation", {})
            out += ["", f"Style: outline {cell(g(cs, 'outline'))}; shading {cell(g(cs, 'shading'))}; head about {g(cs, 'head_height_share_of_body_estimate')} of the body height (estimate); shadow under the character: "
                    f"{cell(g(cs, 'shadow_under_character'))}. Motion: {cell(g(an, 'body_motion'))} Mouth: {cell(g(an, 'lip_sync'))}. Eyes: {cell(g(an, 'eyes_and_blinks'))} Idle: {cell(g(an, 'idle_motion'))}",
                    "", f"**By eye: places ({len(r.get('environments', []))}).** Set style: {cell(g(r, 'set_style'))}. Layers, back to front: {cell(' → '.join(map(str, r.get('layer_stack', []))))}.", "",
                    "| Time | Place | Key props | In-world text | Time of day | Light | Depth cues |", "|---|---|---|---|---|---|---|"]
            for e in r.get("environments", []):
                out.append(f"| {e.get('start')} – {e.get('end')} s | {cell(e.get('place'))} | {cell(', '.join(map(str, e.get('key_props', []))))} | {cell(', '.join(map(str, e.get('in_world_text', []))) or '–')} | "
                           f"{cell(e.get('time_of_day'))} | {cell(e.get('lighting'))} | {cell(e.get('depth_cues'))} |")
            cam = r.get("camera", {})
            out += ["", f"**By eye: camera.** Shot sizes: {cell(', '.join(map(str, cam.get('shot_sizes', []))))}. Angles: {cell(', '.join(map(str, cam.get('angles', []))))}. Lens feel: {cell(g(cam, 'lens_feel'))}. "
                    + "Notable moves: " + "; ".join(f"{m.get('t')} s {cell(m.get('type'))} ({cell(m.get('note'))})" for m in cam.get("notable_moves", [])) + "."]
            if r.get("effects"):
                out += ["", "**By eye: effects.** " + "; ".join(f"{e.get('t')} s {cell(e.get('type'))} on {cell(e.get('trigger'))}" for e in r["effects"]) + "."]
            if r.get("lighting_mood_shifts"):
                out += ["", "**By eye: light and mood shifts.** " + "; ".join(f"{m.get('t')} s: {cell(m.get('change'))} ({cell(m.get('story_reason'))})" for m in r["lighting_mood_shifts"]) + "."]
            if r.get("sample_points"):
                out += ["", "**Sampled colours** (exact pixel values at points the reviewer chose): " + "; ".join(f"{cell(p.get('what'))} `{p.get('hex')}`" for p in r["sample_points"] if p.get("hex")) + "."]
            jv = r.get("joins_verified", [])
            ok = sum(1 for j in jv if (j.get("auto_type"), j.get("verdict")) in (("cut", "cut"), ("dissolve", "dissolve"), ("inplace_blend", "in_place_change"), ("inplace_blend", "camera_move")))
            out += ["", f"**By eye: thumbnail.** {cell(g(r, 'thumbnail'))}", "",
                    f"**Join check.** The reviewer looked at {len(jv)} automatically detected joins and in-place changes and agreed with {ok}; joins the detector missed: {len(r.get('missed_joins', []))}"
                    + (" (" + "; ".join(f"{m.get('t')} s {m.get('type')}" for m in r["missed_joins"]) + ")" if r.get("missed_joins") else "") + "."]
            if r.get("generation_evidence"):
                out += ["", "**By eye: how it looks made.** " + " ".join(f"[{cell(e.get('points_to'))}] {cell(e.get('observation'))}" for e in r["generation_evidence"])]
            if r.get("could_not_determine"):
                out += ["", "**Could not be decided from the frames.** " + "; ".join(cell(x) for x in r["could_not_determine"]) + "."]
        big = []
        for k, label, unit in STAND:
            m = M.get(k)
            if m and m["sd"] and v.get(k) is not None:
                z = (v[k] - m["mean"]) / m["sd"]
                if abs(z) >= 1.5:
                    big.append((abs(z), f"{label} {v[k]:g}{(' ' + unit) if unit else ''} against a mean of {m['mean']:g} ({z:+.1f} SD)"))
        out += ["", "**Stands out from the other 19.** " + ("; ".join(t for _, t in sorted(big, reverse=True)) + "." if big else "Nothing is more than 1.5 standard deviations from the mean.")]
    (adir / "output" / "02_video_cards.md").write_text("\n".join(out) + "\n")
    print("cards:", len(V), "videos,", sum(1 for x in R.values() if x), "with a by-eye review,", len(out), "lines")


if __name__ == "__main__":
    main()
