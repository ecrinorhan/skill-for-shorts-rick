---
name: fact-story-shorts
description: Write, storyboard, voice, caption, render, mix and quality-check an original 60-second vertical Short that tells one true fact as a fast narrated cartoon story (an odd action in the first frame, the explanation near the end). Use it for "Why X did Y" style fact stories, and whenever a script, shot list, caption track or finished video has to match the numeric style measured on 20 reference Shorts. The style is a set of numbers; the stories, characters and wording must be original.
---

# Fact-story Shorts

A fact-story Short is about 62 seconds of non-stop narration over a cartoon story. Someone does something odd in the first
frame, it is doubted or goes wrong, and near the end one true fact explains it. This folder holds the numbers measured on
the 20 newest Shorts of one channel that works this way, and tools to write, voice, caption, render, mix and check a
video against those numbers.

## 1. Formula, never material

Measurements and common craft are free to reuse: lengths, pace, caption geometry, camera rhythm, loudness, story shape.
The reference channel's stories, titles, sentences, characters, drawings, voice, music and frames are not.

- Write your own story about a fact you researched yourself. `scripts/check_script.py` fails a script that shares any
  6-word sequence with the reference narration and warns at 5 words. It compares hashes
  (`references/reference_shingles.json`); the reference text is not in this folder and must not be added to it.
- Design your own cast. It must differ from the reference cast on at least four of the six traits in
  `references/originality.md`.
- Never put a reference frame, audio clip or transcript into an image generator, a voice cloner or a style-transfer tool.
- State what is real and what is invented in the script's `fact` field, with at least one source you actually read.

Read `references/originality.md` before you start and again before you publish.

## 2. The format in numbers

Means over the 20 reference videos. Spread, ranges and the confidence of every number are in `references/style-bible.md`.

| | |
|---|---|
| Frame | 1080 × 1920 (9:16), 30 fps; stereo audio at 44.1 kHz |
| Length | 62 s (58 – 66), 231 words, 222 words per minute, no pause of 250 ms anywhere |
| Script | 20 sentences of 12 words; the first is 14 words and ends at 3.8 s; 1 question; no call to action |
| Captions | always on; 1.26 words each, 2.9 per second; white with a black outline and a hard shadow; centred at 70 % of the height; each one appears a few frames before its word |
| Picture | 13 takes joined mostly by 10-frame dissolves; 17 fast camera moves; something changes every 1.6 s; the camera pushes in slowly the rest of the time; almost no static holds |
| Colour | brightness 109 of 255, contrast 53, saturation 114 of 255; warm and cool hues in balance |
| Sound | −14.1 LUFS, true peak −2.1 dBTP; voice on 98 % of the time; music 19 LU under the voice, never ducked; 6 short effects per 10 s |
| Technique (by eye) | flat, thick-outlined characters standing in lit 3D sets; faces change by swapping drawn expressions; the camera does most of the moving |

Confidence labels used throughout: **measured** = read directly from the video files; **estimate** = from separated audio
stems, a heuristic classifier, or a property that YouTube's compression changes; **by eye** = one AI reviewer per video
looking at extracted frames. Tool routes are marked **tested here** or **not tested here**.

## 3. What is in this folder

| Path | Use |
|---|---|
| `references/style-bible.md` | every measured number with mean, spread and confidence; what is fixed and what varies |
| `references/story-and-script.md` | choosing a fact, the four structures, beat sheet and word budget, first sentence, wording, ending, title, `script.json` |
| `references/visuals.md` | the look, characters, sets and light, camera grammar, effects, planning numbers, shot list |
| `references/captions.md` | caption spec, how words are grouped, timing |
| `references/sound.md` | voice, music, effects, mix targets |
| `references/renderer.md` | the storyboard API of the bundled renderer |
| `references/originality.md` | what may and may not be reused; cast and fact rules |
| `references/assets-and-tools.md` | what is and is not known about how the reference is made, tool and asset options with confidence labels, licences |
| `references/style_targets.json`, `references/reference_shingles.json` | targets and hashes the scripts read |
| `templates/` | `script.json`, `shot-list.md` and `storyboard.mjs` to copy into a project |
| `examples/bridge-keeper/` | a worked project: script, timed sheet, storyboard, narration timings, timeline |
| `examples/rat-tails/`, `examples/smoky-room/` | two more original scripts with timed sheets (no storyboard) |
| `scripts/` | `install.py`, `check_script.py`, `voice.py`, `render/render.mjs`, `mix.py`, `measure/measure.py` |
| `assets/fonts/` | Archivo (SIL Open Font License), the stand-in caption font |

## 4. Setup

```
python3 scripts/install.py              # script checker, narration, captions, renderer, mixer
python3 scripts/install.py --measure    # also what scripts/measure/measure.py needs
```

Needs Python 3.10+, Node 20+ with npm, `ffmpeg` and `rubberband` on the PATH (`tesseract` too for `--measure`). The top
of `scripts/install.py` gives the package names for Debian / Ubuntu and macOS. The installer creates `.venv/`, downloads
the speech model (about 350 MB) into `models/kokoro/` and the word-timing model (about 360 MB) into the torch cache, and
installs three.js, Playwright and a headless Chromium under `scripts/render/`. Those folders are not part of the
repository. Run every Python tool with `.venv/bin/python`. Developed and run on Linux without a GPU.

## 5. Workflow

A project is any folder that holds `script.json` and, later, `storyboard.mjs`. Below, `P` is that folder. Run the
commands from this skill folder.

1. **Fact.** Pick one fact with a visible, physical consequence and fill in the fact card
   (`references/story-and-script.md` sections 2 and 3). Read the source yourself.
2. **Script.** Copy `templates/script.json` to `P/script.json` and write to the beat sheet (sections 4 to 10 of the same
   file). Then:
   ```
   .venv/bin/python scripts/check_script.py P/script.json --md P/script.md
   ```
   Fix every FAIL (exit code 1) and every WARN you did not intend. `--md` writes the timed beat sheet.
3. **Narration and captions.**
   ```
   .venv/bin/python scripts/voice.py build P                    # bundled text-to-speech voice
   .venv/bin/python scripts/voice.py build P --clips P/voice_in  # your own recording: 01.wav, 02.wav ... one per sentence
   .venv/bin/python scripts/voice.py probe out_dir               # compare the stock voices: pace, pitch, pitch range
   ```
   `build` removes pauses, sets the pace, times every word and writes `voice_dry.wav`, `words.json`, `sentences.json`,
   `captions.json` and `voice_meta.json`. Check the line it prints: about 222 words per minute, `pauses_ge_250ms` 0,
   about 1.26 words per caption. Everything after this step takes its timing from these files.
4. **Shot list.** Fill in `templates/shot-list.md`: cast, places, one row per take, with the planning numbers from
   `references/visuals.md` section 6.
5. **Pictures.** Copy `templates/storyboard.mjs` to `P/storyboard.mjs` and write one `T(...)` block per row
   (`references/renderer.md`; full example in `examples/bridge-keeper/storyboard.mjs`).
   ```
   node scripts/render/render.mjs P --timeline          # timeline.json and the counts: takes, camera moves, sound cues
   node scripts/render/render.mjs P --still 0,45,300    # single frames into P/stills/ to check framing and light
   node scripts/render/render.mjs P --frames 0:150      # a 5-second motion preview, P/preview.mp4
   node scripts/render/render.mjs P --workers 4         # every frame, P/video.mp4
   ```
   Software rendering is slow: a 90-frame preview took 37 s here with 3 workers, which works out at about 13 minutes
   for a full video. Other ways to make the pictures are in `references/visuals.md` section 8.
6. **Sound.**
   ```
   .venv/bin/python scripts/mix.py P                        # voice chain, music bed, effects, loudness -> P/final.mp4
   .venv/bin/python scripts/mix.py P --video preview.mp4    # sound for the preview -> P/preview_sound.mp4
   ```
   The music and the effects are synthesised by the script from the script's beats and the storyboard's cues, so there
   is nothing to license. `--seed` and `--bpm` give a different bed. Read `P/mix_report.json` against
   `references/sound.md`.
7. **Measure (optional).**
   ```
   .venv/bin/python scripts/measure/measure.py P/final.mp4 work_dir --title "Your title" --as-youtube
   ```
   Runs the same measurements that were run on the reference videos and writes `work_dir/comparison.md`: **ok** (within
   15 % of the reference mean), **in range** (inside what the 20 videos span) or **OFF** for each metric. It downloads
   several large models on first use and is slow without a GPU.
8. **Check and publish.** Go through section 6, then title and description as in `references/story-and-script.md`
   section 11.

## 6. Finished-video checklist

Originality and facts
- [ ] The story, title, names, characters and wording are yours. `check_script.py` reports 0 failures and every 5-word
      warning was reworded.
- [ ] The title is not one the reference channel used and the story is not one it told.
- [ ] The cast differs from the reference cast on at least four of the six traits in `references/originality.md`.
- [ ] No reference frame, audio or text went into any tool. The voice is yours or licensed, not a clone or an imitation.
- [ ] The `fact` field says what is real and what is invented. Every claim in the explanation is in a source you read.
      No invented words or deeds are attached to a real, named person.

Script
- [ ] 215 – 245 words and 58 – 66 seconds.
- [ ] About 20 sentences averaging 12 words. The first sentence is about 14 words, describes an action that is on screen
      in the first frame, and ends by about 3.8 s.
- [ ] One question at the turn, the explanation late, the last line a consequence. No call to action, and the last line
      does not repeat the first.
- [ ] The title is 4 – 8 words in a pattern such as "Why …", "The X …" or "How …". No hashtags in the title or
      description.

Voice
- [ ] 200 – 246 words per minute (aim for 222), the same pace from start to finish.
- [ ] No pause of 250 ms or more. The voice sounds for about 98 % of the runtime.
- [ ] The first word starts about 0.1 s in. The file ends about 0.2 s after the last word, with no fade-out.
- [ ] The pitch moves over about 16 semitones. Spoken lines and questions sit 3 semitones or more away from the
      narrator's normal pitch. The bundled text-to-speech voice reaches about 14.

Captions
- [ ] A caption is on screen in every frame: one line, one or two words, about 2.9 per second.
- [ ] White with a near-black outline and a hard shadow, centred, at 70 % of the frame height, sentence case with
      punctuation.
- [ ] No coloured words, emoji, boxes or animation. Each caption is replaced by a hard switch.
- [ ] Heads and important props stay clear of the caption band.

Picture
- [ ] 1080 × 1920 at 30 frames per second.
- [ ] 13 – 17 takes, each starting on the first word of a sentence, joined mostly by 10-frame dissolves. Hard cuts are
      the exception (the reference's newest uploads use more of them: see "Change over the five weeks covered" in the
      style bible).
- [ ] 15 – 20 fast camera moves of 0.5 – 0.9 s, and a new framing about every 1.6 s.
- [ ] A slow push-in of 3 – 5 % per second on every hold. No stretch longer than about 7 s without a new picture.
- [ ] 9 – 12 places, in-world text with invented names on 5 – 7 of them, 3 – 6 changes of light, 8 – 12 visual effects.
- [ ] Every character is lit and readable. With generated pictures, no warped text and no shapes that change inside a take.

Sound
- [ ] −14.1 LUFS integrated, true peak at or under −2.1 dBTP, loudness range about 2 LU.
- [ ] One continuous music bed from the first frame to the last, 19 – 20 LU under the voice, never ducked. Original or
      licensed.
- [ ] 5 – 7 short effects per 10 s, tied to things that happen in the picture. Most peak about 21 dB under the voice;
      at most about six are within 10 dB of it.

Publishing
- [ ] `mix_report.json` is on target and, if you ran `measure.py`, every OFF is understood.
- [ ] Synthetic voice and generated or altered pictures are disclosed as the platform currently requires.

## 7. Limits of what is known

- The numbers describe 20 Shorts from one channel over about five weeks. They say what that channel does, not why a
  video gets views: view counts are a single snapshot, and the few links between a metric and views rest on 17 – 20
  videos, which is too little to act on.
- The narration was machine-transcribed and corrected against the on-screen captions. Nobody listened to the audio.
  Anything split into voice, music and effects comes from software-separated stems.
- "By eye" means an AI reviewer working from extracted frames. No person reviewed the videos.
- How the reference videos are produced (software, voice, music, font) is not known. What the evidence does and does
  not support is in `references/assets-and-tools.md`.
- The tools were run from a fresh copy of this folder: install, script check, the full narration, captions and timeline
  of one example, three stills, and a 2-second rendered and mixed preview (1080 × 1920, 30 fps, −14.1 LUFS). A
  full-length video has not been rendered or put through `scripts/measure/measure.py`, and nobody has listened to the
  result. Do both before you rely on the sound.

## 8. Licences

None of the default downloads is marked non-commercial by its publisher. Some of the tools are under the GPL (Praat
through `praat-parselmouth`, eSpeak NG, Rubber Band), which concerns redistributing that software rather than the videos
made with it. The table, with the one optional non-commercial model that is off by default, is in
`references/assets-and-tools.md`. This is information, not legal advice: check the licences yourself before commercial
use.
