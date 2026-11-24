#!/usr/bin/env python3
"""Write the machine-readable style targets the skill's scripts read.

Usage: 20_style_targets.py <analysis_dir> <skill_dir>
Reads  <analysis>/data/summary.json, caption_grouping.json, caption_style.json, font_match.json, script_stats.json and, when they
       exist, reviews_summary.json and aligner_check.json
Writes <skill>/references/style_targets.json and copies the measurement scripts into <skill>/scripts/measure/lib
"""
import json
import shutil
import sys
from pathlib import Path

LIB = ["02_extract.py", "04_transcribe.py", "05_separate.py", "05b_separate_dnr.py", "06_frame_metrics.py", "07_shots.py", "08_captions.py", "09_audio.py",
       "10_align.py", "11_palette.py", "15_sync.py", "16_aggregate.py"]


def main():
    adir, skill = Path(sys.argv[1]), Path(sys.argv[2])
    s = json.loads((adir / "data" / "summary.json").read_text())
    grp = json.loads((adir / "data" / "caption_grouping.json").read_text())
    cst = json.loads((adir / "data" / "caption_style.json").read_text())
    fm = json.loads((adir / "data" / "font_match.json").read_text())
    m = s["metrics"]
    ss = json.loads((adir / "data" / "script_stats.json").read_text()) if (adir / "data" / "script_stats.json").exists() else {}
    rv = json.loads((adir / "data" / "reviews_summary.json").read_text()) if (adir / "data" / "reviews_summary.json").exists() else {}
    rule = grp["best_rule_matching_words_per_caption"] or grp["best_rule"]
    out = {
        "source": "20 Shorts measured in analysis/ (explained in references/style-bible.md)", "n_videos": s["n_videos"],
        "wpm": m["wpm"]["mean"], "words": m["words"]["mean"], "duration_s": m["duration_s"]["mean"], "voice_f0_range_st": m["voice_f0_range_st"]["mean"],
        "voice_f0_median_hz": m["voice_f0_median_hz"]["mean"],
        "caption_rule": {"SHORT": rule["SHORT"], "MAXCHARS": rule["MAXCHARS"], "MAX3": rule["MAX3"], "stop_punct": rule["stop_punct"],
                         "lead_frames": m["caption_lead_frames_median"]["mean"], "boundary_agreement": rule["boundary_agreement"]},
        "caption_style": {"font_closest_free": [r["font"] for r in fm["ranking"][:4]], "font_px_at_1080x1920": cst["font_px_at_1080x1920"], "stroke_px": 5.5, "shadow_offset_px": [4, 5],
                          "ring_margin_px_measured": cst["ring_margin_px"], "fill_luma": cst["fill_luma"], "stroke_luma": cst["stroke_luma"],
                          "line_top_px": m["caption_line_top_px"]["mean"], "letter_height_px": m["caption_glyph_h_px"]["median"], "centre_y_pct": m["caption_centre_y_pct"]["mean"]},
        "title_patterns": s.get("title_patterns", {}),
        "script_stats": {k: v for k, v in ss.items() if k not in ("videos", "note")},
        "structure": rv.get("structure_targets", {}),
        "metrics": {k: v for k, v in m.items() if v},
    }
    ac = adir / "data" / "aligner_check.json"
    if ac.exists():      # the tools time words with another model than the analysis did: give them the lead measured with theirs
        lead = json.loads(ac.read_text())["caption_lead_frames"]
        out["caption_rule"]["lead_frames_analysis_model"] = out["caption_rule"]["lead_frames"]
        out["caption_rule"]["lead_frames"] = lead["wav2vec2"]["mean"]
        out["metrics"]["caption_lead_frames_median"] = {**lead["wav2vec2"], "note": "re-measured with the tools' word-timing model (analysis/data/aligner_check.json)"}
    (skill / "references").mkdir(parents=True, exist_ok=True)
    (skill / "references" / "style_targets.json").write_text(json.dumps(out, indent=1))
    lib = skill / "scripts" / "measure" / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    for name in LIB:
        shutil.copy(adir / "scripts" / name, lib / name)
    (lib / "README.md").write_text("Copies of `analysis/scripts/*` (the code that measured the reference videos), kept here so the skill folder works on its own.\n"
                                   "Edit the originals and re-run `analysis/scripts/20_style_targets.py analysis skills/fact-story-shorts`.\n")
    print("targets:", len(out["metrics"]), "metrics; caption rule", out["caption_rule"], "; lib files", len(LIB))


if __name__ == "__main__":
    main()
