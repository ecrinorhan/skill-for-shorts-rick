# Assets and tools: what is known, and what to use

Two different questions are answered here, each with a confidence label.

Labels for findings about the reference videos:

- **Confirmed**: read directly from the video files or the public listing.
- **Likely**: several independent observations point the same way. Not proof.
- **Unknown**: the evidence does not decide it.

Labels for tools and assets you might use:

- **Tested here**: it ran in this project. What was run is stated.
- **Not tested here**: a reasonable option that was not run.

Nobody listened to any audio in this project, neither the reference's nor the tools' output. Every statement about sound
rests on numbers.

## 1. How the reference videos appear to be made

| Element | Finding | Label |
|---|---|---|
| Picture technique | Flat, thick-outlined characters placed in lit 3D sets. Faces change by swapping mouth and eye drawings. The camera travels through rigid geometry. | Likely (by eye, frames from all 20 videos: set geometry stays stable through long camera moves, the same assets recur, in-world lettering stays crisp) |
| Software | Not identified. No interface, watermark or credit is visible in the frames. A 3D package with the characters as flat planes would give this look. | Unknown |
| Generated pictures | Of 113 frame observations noted by the reviewers, 84 point to a 3D engine render, 23 to hand-made animation, 5 are unclear and 1 points to a generated image with added motion. The usual marks of generated video, such as lettering or shapes that warp inside a take, were otherwise not seen. That does not rule out generated source art (textures, character drawings). | Unknown |
| Narration voice | One voice plays every part in all 20 videos, at nearly the same pitch and pace each time. Whether it is a person or a synthetic voice was not decided: no pause of 250 ms or more and no breath sounds were found, which fits a synthetic voice and a tightly edited recording equally. | Unknown |
| Captions | Produced by speech recognition from the audio and not proofread: recognition mistakes are left in. | Likely |
| Caption font | Not identified. The closest free fonts by letter-shape overlap (1.0 would be identical): Mona Sans 900 (0.730), Archivo 800 (0.726), Chivo 900 (0.716), Rubik 800 (0.702). | Unknown; the stand-ins are similar, not the same |
| Music | A different quiet instrumental bed in each of the 20 videos; no track is reused. The source was not identified: a fingerprint lookup on 60 excerpts gave 58 misses and 2 isolated single hits that the other excerpts from the same videos did not repeat. | No reuse: estimate (separated stems). Source: Unknown |
| Sound effects | About 37 short effects per video, mostly belonging to things that happen on screen. The source library was not identified. | Unknown |
| Audio label on YouTube | "Original Sound" on all 20. It means the audio was uploaded with the video. It says nothing about where the music and effects came from or how they are licensed. | Confirmed (the label); Unknown (the source) |
| Synthetic-content disclosure | Not recorded in the metadata that could be collected. | Unknown |
| Edit | Takes joined by dissolves of about 10 frames and a few hard cuts; captions burned into the picture. | Confirmed (measured on every frame) |

Do not present any of the "Likely" or "Unknown" rows as fact about the channel.

## 2. What to use for your own videos

| Job | Option | Label | Notes |
|---|---|---|---|
| Script check | `scripts/check_script.py` | Tested here | all three example scripts pass its 36 checks |
| Voice | the bundled Kokoro text-to-speech voice through `scripts/voice.py` | Tested here | the bridge-keeper script came out at 233 words in 62.9 s (222 words per minute), no pause of 120 ms or more, pitch range 16 semitones by its own measure and 15.2 measured on the finished video (target 16). The pitch is widened by resynthesis in up to three passes: judge it by ear before publishing |
| Voice | your own recording, one file per sentence (`--clips`) | Not tested here with a human recording | the surest way to reach the reference's wide pitch range |
| Voice | another text-to-speech service or a voice actor | Not tested here | check that the licence covers monetised video, then feed the audio in through `--clips` |
| Word timing and captions | `scripts/voice.py`: forced alignment, then the grouping rule fitted to the reference | Tested here | the rule reproduces 77.7 % of the reference's caption boundaries. Word starts agree with the analysis's timing model to within one frame for 91 % of 4,612 reference words; the constant 20 ms difference between the two models is built into the targets (`captions.md`, "Timing") |
| Caption font | Archivo 800 (bundled) or Mona Sans 900 | Tested here (Archivo, drawn by the renderer) | a stand-in, not the reference's font |
| Pictures | the bundled three.js renderer, `scripts/render/render.mjs` | Tested here on a full 63-second video | rendering took 10 to 20 minutes on 8 CPU cores without a GPU. Sets are plainer than the reference, and fast moves came out about twice as fast as the reference's |
| Pictures | Blender, Unreal Engine or Unity with the characters as flat planes | Not tested here | closest to what the frames suggest |
| Pictures | generated stills or clips | Not tested here | check every take for warped lettering and shapes, and follow the platform's disclosure rules |
| Music | the synthesised bed from `scripts/mix.py` | Tested here, by numbers only | the example mix measured −14.1 LUFS and −2.25 dBTP true peak, with the music 19.4 LU under the voice |
| Music | a licensed library track or a commission | Not tested here | minor key, about 115 BPM, dark and soft, constant level; the licence must cover monetised Shorts |
| Sound effects | synthesised by `scripts/mix.py` from the storyboard's cues | Tested here, by numbers only | the example storyboard's 108 cues measured as 45 separate effects (reference mean 37), sounding for 17 % of the runtime against the reference's 29 %: add longer sounds such as ambience and risers |
| Sound effects | a licensed effects library | Not tested here | keep most effects about 21 dB under the voice |
| Final check | `scripts/measure/measure.py` | Tested here | run on a reference video and on the finished example video (`examples/bridge-keeper/measured.md`) |

## 3. Licences of what the tools install

As stated by each publisher. Rows marked † were not re-checked against the publisher's page during this project. Check
them yourself before commercial use; this is information, not legal advice.

| Component | Used for | Licence |
|---|---|---|
| Kokoro-82M model files † | text-to-speech | Apache-2.0 |
| kokoro-onnx | running that model | MIT |
| phonemizer, eSpeak NG † | pronunciation for the speech model | GPL-3.0 |
| wav2vec2 base 960h, through torchaudio | word timing | MIT |
| PyTorch, torchaudio | running the timing model | BSD |
| NumPy, SciPy, soundfile, librosa, pyloudnorm, ONNX Runtime | audio processing | BSD, ISC or MIT |
| praat-parselmouth (Praat) | measuring and reshaping pitch | GPL-3.0-or-later |
| num2words | reading numbers aloud for timing | LGPL |
| Rubber Band command-line tool † | changing tempo and pitch | GPL-2.0-or-later; a commercial licence is sold separately |
| ffmpeg † | encoding | LGPL or GPL, depending on the build |
| three.js | the renderer | MIT |
| Playwright, Chromium † | headless rendering | Apache-2.0; BSD-style |
| Archivo | caption font | SIL Open Font License 1.1 (`assets/fonts/OFL.txt`) |
| faster-whisper with Whisper large-v3 † (measuring tool only) | transcription | MIT |
| Demucs `htdemucs` (measuring tool only) | separating the voice | code MIT; its README states no separate licence for the pretrained weights, which were trained on MUSDB-HQ plus 800 other songs |
| CDX23 cinematic demixing checkpoints (measuring tool only) | separating dialogue, music and effects | repository MIT; no separate statement for the weights, which were trained on the DnR dataset |
| OpenCV, Tesseract † (measuring tool only) | frames, reading captions | Apache-2.0 |
| MMS_FA, through torchaudio (off by default) | reproducing the analysis's own word timing with `ALIGN_MODEL=mms` | CC-BY-NC 4.0: non-commercial only |

The GPL components are installed from their publishers, not copied into this folder. The GPL governs passing that
software on; it does not by itself restrict the audio or video you make with it.

## 4. If you replace a bundled part

- Keep the order: narration first, then everything else timed to `words.json` and `sentences.json`.
- Burn the captions in to the spec in `captions.md`, generated from the script text, not from speech recognition.
- Mix to the targets in `sound.md`, and run `scripts/measure/measure.py` on the result.
- Record where every asset came from and under which licence.
