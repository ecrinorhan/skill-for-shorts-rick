# Visual review brief (one reviewer per video)

This is the brief each by-eye reviewer received. `{V}` is the work-folder name (for example `10_7xS87iActkU`), `{ID}` the
YouTube id. The reviewer's JSON is copied to `analysis/data/reviews/{V}.json`.

---

You are reviewing ONE YouTube Short frame by frame for a style study. The goal is to learn the production formula, not to
copy the video. All inputs are on disk. Do not use the network. Create files only under `/opt/rc/review/{V}/`.

**Budget: at most 14 tool calls in total. Send several Read calls in ONE step whenever you view images. Do not re-read files.**

## Steps

1. Read `/opt/rc/work/{V}/pack.md` in full (transcript by sentence with timestamps, joins, hold/move timeline, SFX, colour).
2. In ONE step, Read these images: `/opt/rc/work/{V}/hook.jpg` (first 3 s, a tile every 0.2 s), `/opt/rc/work/{V}/contact_01.jpg`
   and `contact_02.jpg` if it exists (one tile per second), `/opt/rc/work/{V}/ending.jpg` (last 3 s),
   `/opt/rc/raw/meta/videos/{ID}/thumb_oar2.jpg` (thumbnail).
3. In ONE step, Read every `/opt/rc/work/{V}/boundaries_*.jpg`. Each item shows four frames around a detected join
   (cuts: f-2, f-1 | f, f+1; dissolves: start, 1/3, 2/3, end). Label colours: green = CUT, blue = DISSOLVE,
   pink = in-place blend, orange = "suspect" (a strong change the detector did NOT call a join).
4. With ONE Bash call build 4 or 5 montages (never more than 5), then Read them in ONE step:

       cd /opt/rc/review/{V} && M="/opt/rc/venv/bin/python /tmp/hoplite/workspace/analysis/scripts/lib/montage.py" && W=/opt/rc/work/{V}
       $M a_move.jpg 300 6 $W 300-322:2        # 12 frames through one fast camera move (pick a MOVE from pack.md; frame = seconds x 30)
       $M --crop 0.1,0.05,0.9,0.6 b_face.jpg 360 4 $W 550-564:2   # a character's face during a line of direct speech: does the mouth move?
       $M c_idle.jpg 300 6 $W 900-925:5        # 6 frames of one hold: blinking, breathing, drifting detail?
       $M --crop 0.1,0.2,0.9,0.7 d_text.jpg 500 2 $W 1000 1040   # any in-world text or fine detail, at two moments of one take
       $M e_other.jpg 360 4 $W ...             # anything odd you want to check

   (Frame files are `/opt/rc/work/{V}/frames/NNNNN.jpg`, 30 fps, 1080x1920. The crop option must come before the output name.)
5. Write `/opt/rc/review/{V}/review.json` with the Write tool, then validate it with ONE Bash call:
   `/opt/rc/venv/bin/python -m json.tool /opt/rc/review/{V}/review.json > /dev/null && echo OK`.

## review.json (exactly these keys; strings under 240 characters; choose enumerated values verbatim)

```
{
 "video": "{V}",
 "joins_verified": [ {"t": 3.73, "auto_type": "cut|dissolve|inplace_blend", "verdict": "cut|dissolve|camera_move|in_place_change|unclear", "note": "what the frames show"} ],
 "missed_joins": [ {"t": 0.0, "type": "cut|dissolve", "note": ""} ],
 "beats": [ {"name": "hook|setup|escalation|twist|payoff|explainer|ending", "start": 0.0, "end": 3.2, "said": "PARAPHRASE, at most 18 words", "shown": "what is on screen"} ],
 "hook": {
   "first_frame": "what frame 0 shows",
   "first_3s": "what changes on screen in the first 3 s",
   "line_type": "strange action by he/they | second-person hypothetical (if you) | second-person scenario (imagine) | world premise (there is a) | paradox or claim | direct demo (look at)",
   "first_frame_shot_size": "close-up | medium close-up | medium | medium-long | long (full body) | wide",
   "first_frame_subject": "protagonist doing the hook action | protagonist posing with the key prop | two characters | object only | environment only",
   "protagonist_looks_at_camera": true,
   "title_vs_first_line": "how the title relates to the first sentence"
 },
 "story": {
   "topic_type": "engineering/physics | history/war | crime/scam | psychology/behaviour | law/economics/work | science/biology/space | parable/fiction",
   "setting_era": "ancient/medieval | 1700s-1800s | 1900s | modern | future/space | timeless/fable",
   "structure": "act first, explain at the end | premise explained early, then story | pure story with twist reveal | second-person scenario, then explainer",
   "real_fact_core": "the mechanism or fact the story turns on, one sentence",
   "likely_source_type": "history | science | psychology | law/economics | urban legend | news | reddit-style anecdote | invented parable",
   "protagonist": "", "authority_or_antagonist": "", "direct_speech_lines": 0, "second_person": false, "tense": "present | past | mixed",
   "explainer_turn": "the 2-3 words that switch from story to explanation and their timestamp, or null",
   "ending_type": "consequence shown, stops on impact | explanation is the last line | twist reveal is the last line | one-line moral | loops back to the hook",
   "call_to_action": "none or what"
 },
 "tone": {"humour": "", "deadpan_or_irony": "", "dialogue_style": ""},
 "characters": [ {"role": "", "head": "", "hair_or_hat": "", "eyes": "", "mouth": "", "body_and_clothes": "", "limbs": "", "accessories": "", "expressions_seen": []} ],
 "character_style": {"head_height_share_of_body_estimate": 0.33, "outline": "", "shading": "", "consistency_between_shots": "", "shadow_under_character": "none | soft blob | cast silhouette | unclear"},
 "animation": {"body_motion": "", "lip_sync": "none (mouth static) | mouth changes with pose only | flaps while speaking | true lip-sync | unclear", "lip_sync_evidence_frames": [], "eyes_and_blinks": "", "idle_motion": "", "squash_and_stretch": ""},
 "environments": [ {"start": 0.0, "end": 0.0, "place": "", "key_props": [], "in_world_text": [], "time_of_day": "", "lighting": "key direction, hard or soft, colour temperature, practical lights", "depth_cues": "depth of field, haze, light shafts"} ],
 "set_style": "realistic PBR 3D | stylised 3D without outlines | toon 3D with ink outlines | mixed",
 "layer_stack": ["back to front"],
 "camera": {"shot_sizes": [], "angles": [], "lens_feel": "", "camera_height": "", "notable_moves": [ {"t": 0.0, "type": "", "note": ""} ]},
 "effects": [ {"t": 0.0, "dur_s": 0.0, "type": "particles | smoke | glow | flash | speed lines | motion blur | defocus | screen or UI insert | diagram | map | in-world sign | colour shift | shake | other", "trigger": "the word or action it lands on"} ],
 "lighting_mood_shifts": [ {"t": 0.0, "change": "", "story_reason": ""} ],
 "generation_evidence": [ {"frames": [0], "observation": "", "points_to": "AI video | AI image plus motion | 3D engine render | hand animation | unclear"} ],
 "sample_points": [ {"frame": 0, "x": 0.5, "y": 0.5, "what": "main character head fill"} ],
 "thumbnail": "what it shows and which moment of the video it is",
 "could_not_determine": []
}
```

## Rules

1. `joins_verified` lists EVERY green, blue and pink item on the boundary sheets. A dissolve shows a double exposure in the
   middle tiles; a camera move shows the same scene shifted or streaked; an in-place change keeps the framing and changes
   content or light. Put an orange suspect under `missed_joins` only if it really is a cut or dissolve.
2. `beats`: 5 to 8 beats covering the whole runtime without gaps, timestamps from pack.md. Paraphrase; never quote more
   than 4 consecutive words of the narration.
3. `characters`: one entry per recurring character, at most 4. Plain words for shapes and colours.
4. `environments`: one entry per distinct place, in order, times to the second from the contact sheets.
5. `sample_points`: 8 to 10 points in the middle of large flat areas, as frame index plus x,y fractions of the full frame
   (x from the left, y from the top): main character head fill, body or clothes, hair or hat, and 4 to 6 dominant set
   colours from different scenes. A script reads the exact hex values.
6. `generation_evidence`: 3 to 6 concrete observations with frame numbers. Look for detail that changes inside one
   continuous take, in-world text that warps or stays crisp, objects appearing or vanishing, texture that swims, limbs
   that change length; or the opposite: rock-solid geometry, identical assets repeating, clean perspective.
7. Write "estimate" where you judge by eye. Put anything you could not decide under `could_not_determine`.

Final reply (short): the JSON path, counts of join verdicts, and the 3 most important things you noticed about how this
video is made.
