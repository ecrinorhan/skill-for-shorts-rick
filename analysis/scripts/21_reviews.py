#!/usr/bin/env python3
"""Collect the by-eye reviews, read exact colours at the reviewers' sample points, and tally what they saw.

Usage: 21_reviews.py <review_dir> <work_dir> <analysis_dir>
Reads  <review_dir>/<video>/review.json (written by one reviewer per video following analysis/review/REVIEW_PROMPT.md)
Writes <analysis>/data/reviews/<video>.json (with a hex colour per sample point) and <analysis>/data/reviews_summary.json
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np


def hex_at(work, video, frame, x, y):
    fp = work / video / "frames" / f"{int(frame):05d}.jpg"
    if not fp.exists():
        return None
    im = cv2.imread(str(fp))
    h, w = im.shape[:2]
    cx, cy = int(np.clip(x, 0, 1) * (w - 1)), int(np.clip(y, 0, 1) * (h - 1))
    patch = im[max(0, cy - 6):cy + 7, max(0, cx - 6):cx + 7].reshape(-1, 3)
    b, g, r = np.median(patch, axis=0)
    spread = float(patch.std(axis=0).mean())
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}", round(spread, 1)


def norm(s):
    return re.sub(r"\s+", " ", str(s).strip().lower())


def main():
    rdir, work, adir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out_dir = adir / "data" / "reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    C = defaultdict(Counter)
    joins = Counter()
    missed, colours, evid, undetermined, moods, depth, per_video = 0, defaultdict(list), [], [], [], Counter(), {}
    done = []
    beat_start, beat_share, hook_end, expl_start, end_start, speech = defaultdict(list), defaultdict(list), [], [], [], []
    for d in sorted(p for p in rdir.iterdir() if (p / "review.json").exists()):
        try:
            R = json.loads((d / "review.json").read_text())
        except Exception as e:  # noqa: BLE001
            print("BAD JSON", d.name, e)
            continue
        v = d.name
        done.append(v)
        dur = json.loads((work / v / "specs.json").read_text())["duration_s"]
        seen, share = {}, Counter()
        for b in R.get("beats", []):
            name = norm(b.get("name"))
            seen.setdefault(name, float(b["start"]) / dur)
            share[name] += (float(b["end"]) - float(b["start"])) / dur
        for name, x in seen.items():
            beat_start[name].append(round(x, 3))
            beat_share[name].append(round(share[name], 3))
        hk = [b for b in R.get("beats", []) if norm(b.get("name")) == "hook"]
        if hk:
            hook_end.append(float(hk[0]["end"]))
        if "explainer" in seen:
            expl_start.append(round(seen["explainer"], 3))
        if "ending" in seen:
            end_start.append(round(seen["ending"], 3))
        ds = (R.get("story") or {}).get("direct_speech_lines")
        if isinstance(ds, (int, float)):
            speech.append(ds)
        for sp in R.get("sample_points", []):
            try:
                res = hex_at(work, v, sp["frame"], float(sp["x"]), float(sp["y"]))
            except Exception:  # noqa: BLE001
                res = None
            if res:
                sp["hex"], sp["patch_spread"] = res
                what = norm(sp.get("what", ""))
                key = ("head" if "head" in what or "face" in what else "outline" if "outline" in what else "body/clothes" if re.search(r"body|cloth|shirt|coat|jacket|uniform|torso|suit|dress|apron|vest", what)
                       else "hair/hat" if re.search(r"hair|hat|cap|helmet", what) else "sky" if "sky" in what else "set")
                if res[1] < 14:
                    colours[key].append({"video": v, "hex": res[0], "what": sp.get("what")})
        (out_dir / f"{v}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
        for j in R.get("joins_verified", []):
            joins[(j.get("auto_type"), j.get("verdict"))] += 1
        missed += len(R.get("missed_joins", []))
        h, s, a = R.get("hook", {}), R.get("story", {}), R.get("animation", {})
        for k in ("line_type", "first_frame_shot_size", "first_frame_subject", "protagonist_looks_at_camera"):
            C["hook." + k][norm(h.get(k))] += 1
        for k in ("topic_type", "setting_era", "structure", "likely_source_type", "tense", "ending_type", "call_to_action", "second_person"):
            C["story." + k][norm(s.get(k))] += 1
        C["story.explainer_turn"][norm(re.sub(r"[\d.:]+\s*s?", "", str(s.get("explainer_turn"))).strip(" @(),-at"))] += 1
        C["story.direct_speech_lines"][str(s.get("direct_speech_lines"))] += 1
        C["animation.lip_sync"][norm(a.get("lip_sync"))] += 1
        C["set_style"][norm(R.get("set_style"))] += 1
        cs = R.get("character_style", {})
        C["character.shadow"][norm(cs.get("shadow_under_character"))] += 1
        hs = cs.get("head_height_share_of_body_estimate")
        if isinstance(hs, (int, float)):
            C["_head_share"][round(float(hs), 2)] += 1
        C["n_characters"][len(R.get("characters", []))] += 1
        C["n_environments"][len(R.get("environments", []))] += 1
        C["n_beats"][len(R.get("beats", []))] += 1
        for e in R.get("effects", []):
            C["effects.type"][norm(e.get("type"))] += 1
        C["n_effects"][len(R.get("effects", []))] += 1
        for g in R.get("generation_evidence", []):
            C["evidence.points_to"][norm(g.get("points_to"))] += 1
            evid.append({"video": v, **g})
        for env in R.get("environments", []):
            C["env.time_of_day"][norm(env.get("time_of_day"))] += 1
            txt = norm(env.get("depth_cues", "")) + " " + norm(env.get("lighting", ""))
            for kw, name in (("depth of field", "depth of field"), ("bokeh", "depth of field"), ("blur", "background blur"), ("haze", "haze/fog"), ("fog", "haze/fog"), ("shaft", "light shafts"),
                             ("god ray", "light shafts"), ("rim", "rim light"), ("practical", "practical lights"), ("lamp", "practical lights"), ("lantern", "practical lights"), ("window", "window light"),
                             ("hard", "hard shadows"), ("soft", "soft light")):
                if kw in txt:
                    depth[name] += 1
            C["env.has_in_world_text"][bool(env.get("in_world_text"))] += 1
        for sz in R.get("camera", {}).get("shot_sizes", []):
            C["camera.shot_sizes"][norm(sz)] += 1
        for ang in R.get("camera", {}).get("angles", []):
            C["camera.angles"][norm(ang)] += 1
        for mv in R.get("camera", {}).get("notable_moves", []):
            C["camera.move_types"][norm(mv.get("type"))] += 1
        for ms in R.get("lighting_mood_shifts", []):
            moods.append({"video": v, **ms})
        undetermined += [{"video": v, "item": x} for x in R.get("could_not_determine", [])]
        per_video[v] = {"hook": h, "story": s, "tone": R.get("tone"), "beats": R.get("beats"), "thumbnail": R.get("thumbnail"), "set_style": R.get("set_style"),
                        "lip_sync": a.get("lip_sync"), "n_joins_checked": len(R.get("joins_verified", [])), "n_missed": len(R.get("missed_joins", []))}
    auto = Counter()
    agree = Counter()
    for (at, ver), n in joins.items():
        auto[at] += n
        if (at == "cut" and ver == "cut") or (at == "dissolve" and ver == "dissolve") or (at == "inplace_blend" and ver in ("in_place_change", "camera_move")):
            agree[at] += n
    def st(a):
        a = np.array(a, float)
        return None if len(a) == 0 else {"n": int(len(a)), "mean": round(float(a.mean()), 3), "median": round(float(np.median(a)), 3), "min": round(float(a.min()), 3), "max": round(float(a.max()), 3),
                                         "sd": round(float(a.std(ddof=1)), 3) if len(a) > 1 else 0.0}

    real = sum(n for (at, ver), n in joins.items() if at in ("cut", "dissolve") and ver in ("cut", "dissolve"))
    names = ["hook", "setup", "escalation", "twist", "payoff", "explainer", "ending"]
    structure = {
        "hook_end_s": st(hook_end), "explainer_turn_rel": st(expl_start), "ending_start_rel": st(end_start), "direct_speech_lines": st(speech),
        "beat_start_rel": {k: st(beat_start[k]) for k in names if beat_start[k]},
        "beat_share_of_runtime": {k: st(beat_share[k]) for k in names if beat_share[k]},
        "beat_start_rel_note": "reference medians: " + ", ".join(f"{k} {np.median(beat_start[k]):.0%}" for k in names if beat_start[k]),
    }
    summary = {
        "videos_reviewed": done, "n_reviewed": len(done),
        "structure_targets": structure,
        "join_check": {"auto_counts": dict(auto), "confirmed": dict(agree), "precision": {k: round(agree[k] / auto[k], 3) for k in auto if auto[k]},
                       "matrix": {f"{a}->{v}": n for (a, v), n in sorted(joins.items(), key=lambda kv: -kv[1])}, "missed_joins_found_by_eye": missed,
                       "recall_cut_or_dissolve": round(real / max(real + missed, 1), 3)},
        "tallies": {k: dict(v.most_common()) for k, v in C.items()},
        "depth_and_light_keywords_by_environment": dict(depth.most_common()),
        "sampled_colours": colours, "generation_evidence": evid, "lighting_mood_shifts": moods, "could_not_determine": undetermined, "per_video": per_video,
    }
    (adir / "data" / "reviews_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str))
    print("reviewed:", len(done), "of 20;", "missing:", sorted(set(p.name for p in work.iterdir() if (p / "frames").is_dir()) - set(done)))
    print("joins:", json.dumps(summary["join_check"]))
    print("structure:", json.dumps(structure))
    for k, v in summary["tallies"].items():
        print(k, json.dumps(v, default=str)[:420])
    print("depth/light:", json.dumps(summary["depth_and_light_keywords_by_environment"]))
    for k, lst in colours.items():
        print("colours", k, len(lst), Counter(c["hex"] for c in lst).most_common(8))
    print("evidence samples:")
    for g in evid[:14]:
        print("  ", g["video"][:2], g.get("points_to"), "|", str(g.get("observation"))[:150])
    print("undetermined:", Counter(norm(u["item"])[:60] for u in undetermined).most_common(12))


if __name__ == "__main__":
    main()
