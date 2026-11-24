# Second-by-second visual log (one reviewer per video)

This is the brief the by-eye reviewers of the three most-viewed videos received. `{V}` is the work-folder name
(for example `10_7xS87iActkU`). The reviewer's JSON is copied to `analysis/data/seconds/{V}.json`.

---

You are logging what is ON SCREEN in every second of ONE YouTube Short for a style study. The goal is to learn the
production formula (shot sizes, staging, which kind of picture goes with which kind of line), not to copy the video.
All inputs are on disk. Do not use the network. Create files only under `/opt/rc/review/{V}/`.

**Budget: at most 10 tool calls in total. Read all montage images in ONE step. Do not re-read files.**

## Steps

1. Read `/opt/rc/work/{V}/pack.md` in full (sentences with timestamps, joins between takes, hold/move timeline).
2. The per-second montages are already built in `/opt/rc/review/{V}/` as `sec_0.jpg`, `sec_1.jpg` ... (one frame from the
   middle of every second, 12 per sheet). Check with ONE Bash call: `ls /opt/rc/review/{V}/`. Only if no `sec_*.jpg`
   exists, build them, writing the full command on each line (shell variables that hold a command are blocked here):

       mkdir -p /opt/rc/review/{V} && cd /opt/rc/review/{V} && for k in 0 1 2 3 4 5 6; do a=$((k*360+15)); b=$((a+330)); /opt/rc/venv/bin/python /tmp/hoplite/workspace/analysis/scripts/lib/montage.py sec_$k.jpg 300 6 /opt/rc/work/{V} $a-$b:30 || true; done; ls

   Sheet `sec_k.jpg` holds seconds 12k to 12k+11; a tile labelled `f375 12.50s` is second 12. A sheet past the end of
   the video is missing or shorter, which is fine; describe a last second without a tile from the nearest tile.
3. Read every `sec_*.jpg` in ONE step.
4. Write `/opt/rc/review/{V}/seconds.json` with the Write tool, then validate it with ONE Bash call:
   `/opt/rc/venv/bin/python -m json.tool /opt/rc/review/{V}/seconds.json > /dev/null && echo OK`.

## seconds.json (exactly these keys; choose enumerated values verbatim)

```
{
 "video": "{V}",
 "seconds": [
  {"s": 0,
   "shown": "who or what is in the frame, doing what, where; at most 16 words",
   "shot_size": "close-up | medium close-up | medium | medium-long | long (full body) | wide | extreme wide | insert (object or detail)",
   "subject": "protagonist | antagonist or authority | secondary character | crowd or group | object or prop | environment | diagram or insert",
   "picture_job": "shows the narrated action | shows a reaction | establishes the place | shows the object named | visual gag | diagram or explanation | consequence or result | travel or transition",
   "new_setup": true}
 ]
}
```

## Rules

1. One entry for EVERY whole second from 0 to the last second of the video, in order, without gaps.
2. `shown` describes the picture only. Do not transcribe or paraphrase the narration, and ignore the burned-in caption word.
3. `new_setup` is true when the place or framing is clearly different from the previous second (a new take, or a camera
   move that reframes), otherwise false. Second 0 is true.
4. Write "estimate" inside `shown` when you are unsure what something is.

Final reply (short): the JSON path and the number of entries.
