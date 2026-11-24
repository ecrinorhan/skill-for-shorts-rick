#!/usr/bin/env python3
"""Second-by-second breakdown of the three most-viewed videos.

Usage: 24_top3.py <work_dir> <review_dir> <analysis_dir> [n=3]
Reads  <work>/<video>/{words,shots,audio}.json, frame_metrics.csv; <review>/<video>/{review,seconds}.json
Writes <analysis>/output/04_top3_second_by_second.md, <analysis>/data/seconds/<video>.json, <analysis>/data/top3_tallies.json

Columns per second
  measured   words spoken, sentence starts, captions shown, camera state, joins, brightness, saturation
  estimate   sound-effect events (from the separated effects stem; the class is a heuristic label)
  by eye     what is on screen, shot size, what the picture is doing (one reviewer, analysis/review/SECONDS_PROMPT.md)
No narration is reproduced: the "narration" column is the beat the second belongs to.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path


def norm(s):
    return " ".join(str(s).strip().lower().split())


def main():
    work, rdir, adir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    V = json.loads((adir / "data" / "videos.json").read_text())
    top = sorted(V, key=lambda x: -x["views"])[:n]
    (adir / "data" / "seconds").mkdir(parents=True, exist_ok=True)
    out = ["# The three most-viewed videos, second by second", "",
           "Videos #10, #19 and #11 had the most views of the 20 at the snapshot. Each table has one row per second.", "",
           "- **Measured** columns come from the files: words and sentence starts from the forced-aligned transcript, captions from the burned-in caption track, camera and joins from "
           "optical flow and frame differences, brightness and saturation from every frame.",
           "- **SFX** is an estimate: events found in a separated effects stem, with a heuristic class for the loudest one.",
           "- **By eye** columns were written by one reviewer per video from one frame per second (`analysis/review/SECONDS_PROMPT.md`).",
           "- The narration itself is not reproduced. The *Beat* column says which part of the story the second belongs to; the beat table above each video paraphrases what is said.", "",
           "Camera notation: `hold` = the framing is steady apart from a slow drift, with the measured zoom rate in % per second (positive = pushing in); `MOVE` = a fast camera move, with its "
           "peak speed in % of frame height per second. A join is where two separately made takes meet: `cut`, or `dissolve` with its length in frames."]
    tall = {"shot_size": Counter(), "subject": Counter(), "picture_job": Counter(), "seconds": 0, "new_setups": 0, "per_video": {}}
    job_by_beat, size_by_beat = {}, {}
    for v in top:
        d = work / v["video"]
        wj, sj, aj = (json.loads((d / f"{k}.json").read_text()) for k in ("words", "shots", "audio"))
        rv = json.loads((rdir / v["video"] / "review.json").read_text()) if (rdir / v["video"] / "review.json").exists() else {}
        sp = rdir / v["video"] / "seconds.json"
        sec = {int(x["s"]): x for x in json.loads(sp.read_text())["seconds"]} if sp.exists() else {}
        if sec:
            (adir / "data" / "seconds" / f"{v['video']}.json").write_text(json.dumps({"video": v["video"], "seconds": [sec[k] for k in sorted(sec)]}, indent=1, ensure_ascii=False))
        dur = v["duration_s"]
        N = int(dur) + (1 if dur - int(dur) > 0.05 else 0)
        luma, sat = [[] for _ in range(N)], [[] for _ in range(N)]
        with open(d / "frame_metrics.csv") as fh:
            for row in csv.DictReader(fh):
                s = min(N - 1, int(float(row["t"])))
                luma[s].append(float(row["luma_mean"]))
                sat[s].append(float(row["sat_mean"]))
        W = wj["words"]
        starts = [W[0]["start"]] + [W[i]["start"] for i in range(1, len(W)) if W[i - 1]["text"].rstrip("\"'”’")[-1:] in ".?!"]
        caps = [c for c in wj["captions"] if c.get("n_words", 0) > 0]
        beats = rv.get("beats", [])
        out += ["", f"## #{v['n']} · {v['title']}", "",
                f"{v['views']:,} views · {v['duration_s']:.1f} s · {v['words']} words at {v['wpm']} per minute · {v['joins']} joins ({v['cuts']} cuts, {v['dissolves']} dissolves) · {v['moves']} fast camera moves · "
                f"{v['captions']} captions · *est.* {v['sfx_events']} sound effects · <{v['url']}>", ""]
        if beats:
            out += ["| Beat | Time | Share of runtime | What the narration does (paraphrase) |", "|---|---|---|---|"]
            for b in beats:
                out.append(f"| {b.get('name')} | {float(b['start']):.1f} – {float(b['end']):.1f} s | {(float(b['end']) - float(b['start'])) / dur:.0%} | {str(b.get('said')).replace('|', '/')} |")
            out.append("")
        out += ["| s | Beat | Words | New sentence | Captions | Camera (measured) | Join | SFX (est.) | Luma | Sat. | On screen (by eye) | Shot | Picture is |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        prev_beat, pv = None, {"seconds": N, "new_setups": 0, "shot_size": Counter(), "picture_job": Counter(), "subject": Counter()}
        for s in range(N):
            a, b = s, s + 1
            beat = next((norm(x.get("name")) for x in beats if float(x["start"]) <= s + 0.5 < float(x["end"])), "")
            nw = sum(1 for w in W if a <= w["start"] < b)
            ns = sum(1 for t in starts if a <= t < b)
            nc = sum(1 for c in caps if a <= c["on"] < b)
            segs = [(min(b, g["end"]) - max(a, g["start"]), g) for g in sj["segments"] if g["end"] > a and g["start"] < b]
            mv = [g for ov, g in segs if g["type"] == "move" and ov >= 0.2]
            if mv:
                g = max(mv, key=lambda g: g.get("flow_peak_pct_h_per_s", 0))
                cam = f"MOVE {g['camera']} ({g.get('flow_peak_pct_h_per_s', 0) * 1:.0f})"
            elif segs:
                g = max(segs, key=lambda x: x[0])[1]
                cam = f"hold {g['camera']} ({g.get('zoom_pct_per_s', 0):+.1f})"
            else:
                cam = "–"
            jn = [("cut" if j["type"] == "cut" else f"dissolve {j['length_frames']} f") for j in sj["joins"] if a <= j["t"] < b]
            jn += ["in-place change" for j in sj.get("inplace_blends", []) if a <= j["t"] < b]
            ev = [e for e in aj["sfx"]["events"] if a <= e["start"] < b]
            fx = f"{len(ev)}: {max(ev, key=lambda e: e['peak_dbfs'])['class_est']}" if ev else ""
            x = sec.get(s, {})
            if x:
                for k in ("shot_size", "subject", "picture_job"):
                    val = norm(x.get(k, ""))
                    tall[k][val] += 1
                    pv[k][val] += 1
                if x.get("new_setup"):
                    tall["new_setups"] += 1
                    pv["new_setups"] += 1
                tall["seconds"] += 1
                if beat:
                    job_by_beat.setdefault(beat, Counter())[norm(x.get("picture_job", ""))] += 1
                    size_by_beat.setdefault(beat, Counter())[norm(x.get("shot_size", ""))] += 1
            lm = f"{sum(luma[s]) / len(luma[s]):.0f}" if luma[s] else ""
            sm = f"{sum(sat[s]) / len(sat[s]):.0f}" if sat[s] else ""
            mark = "▸ " if x.get("new_setup") else ""
            out.append(f"| {s} | {beat if beat != prev_beat else ''} | {nw} | {'●' * ns} | {nc} | {cam} | {', '.join(jn)} | {fx} | {lm} | {sm} | {mark}{str(x.get('shown', '')).replace('|', '/')} | "
                       f"{x.get('shot_size', '')} | {x.get('picture_job', '')} |")
            prev_beat = beat
        tall["per_video"][v["video"]] = {"seconds": pv["seconds"], "new_setups_by_eye": pv["new_setups"], "seconds_per_setup": round(pv["seconds"] / max(pv["new_setups"], 1), 2) if sec else None,
                                         "shot_size": dict(pv["shot_size"].most_common()), "picture_job": dict(pv["picture_job"].most_common()), "subject": dict(pv["subject"].most_common())}
    T = {"seconds_logged": tall["seconds"], "new_setups_by_eye": tall["new_setups"], "seconds_per_setup": round(tall["seconds"] / max(tall["new_setups"], 1), 2),
         "shot_size_share": {k: round(c / max(tall["seconds"], 1), 3) for k, c in tall["shot_size"].most_common()},
         "subject_share": {k: round(c / max(tall["seconds"], 1), 3) for k, c in tall["subject"].most_common()},
         "picture_job_share": {k: round(c / max(tall["seconds"], 1), 3) for k, c in tall["picture_job"].most_common()},
         "picture_job_by_beat": {b: dict(c.most_common()) for b, c in job_by_beat.items()}, "shot_size_by_beat": {b: dict(c.most_common()) for b, c in size_by_beat.items()},
         "per_video": tall["per_video"]}
    (adir / "data" / "top3_tallies.json").write_text(json.dumps(T, indent=1))
    if tall["seconds"]:
        out += ["", "## Tallies over the three videos (by eye, one row per second)", "",
                f"{T['seconds_logged']} seconds logged; a new place or framing in {T['new_setups_by_eye']} of them, one every {T['seconds_per_setup']} s.", "",
                "| Shot size | Share of seconds |", "|---|---|"] + [f"| {k} | {x:.0%} |" for k, x in T["shot_size_share"].items()] + [
                "", "| Main subject | Share of seconds |", "|---|---|"] + [f"| {k} | {x:.0%} |" for k, x in T["subject_share"].items()] + [
                "", "| What the picture is doing | Share of seconds |", "|---|---|"] + [f"| {k} | {x:.0%} |" for k, x in T["picture_job_share"].items()]
    takeaways = adir / "output" / "_top3_takeaways.md"
    if takeaways.exists():
        out += ["", takeaways.read_text().rstrip()]
    (adir / "output" / "04_top3_second_by_second.md").write_text("\n".join(out) + "\n")
    print("top:", [(v["n"], v["title"]) for v in top], "| seconds logged by eye:", tall["seconds"])
    print(json.dumps({k: v for k, v in T.items() if k != "per_video"})[:3000])
    for k, x in T["per_video"].items():
        print(k, x)


if __name__ == "__main__":
    main()
