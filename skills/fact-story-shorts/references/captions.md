# Captions

Measured on 3,732 caption events in the 20 reference videos (burned-in text, read back by detection and OCR;
`analysis/scripts/08_captions.py`, `17_caption_style.py`, `18_caption_grouping.py`). Sizes are for a 1080 × 1920 frame.
`voice.py` builds the caption track and `stage.js` draws it to this spec.

## The spec

| Property | Value | Spread across the 20 videos | Confidence |
|---|---|---|---|
| Frames with a caption on screen | 99.98 % | 99.9 – 100 % | measured |
| Lines | 1, never wraps | – | measured |
| Horizontal position | centred (centre at 49.9 % of width) | 49.8 – 50.1 % | measured |
| Vertical centre | 70.3 % of frame height | 70.31 – 70.34 % | measured |
| Baseline | y = 1377 px | ± 1 px | measured |
| Top of capitals and tall letters | y = 1323 – 1324 px | 1322 – 1324 px | measured |
| Height of capitals / height of small letters (x-height) | 54 px / 41 px | – | measured |
| Fill | white, RGB 251 251 252 | luma 254 | measured |
| Outline | near-black, RGB 29 28 30, about 5.5 px wide (the dark edge is 5 px at the top of a letter and 6 px on its left) | – | measured |
| Hard shadow | the dark edge grows to 10 px at the bottom and on the right (8 – 9.6 px at the 90th – 97th percentile overall), which is a copy of the outlined text shifted about 4 px right and 5 px down | – | measured |
| Soft glow or blur behind the text | none (luma just outside the stroke equals luma further out, −2.8 of 255) | – | measured |
| Coloured or highlighted words | none (0.1 % of captions are not white) | 0 – 0.5 % | measured |
| Emoji, icons, boxes behind the text | none | – | observed |
| Animation | none: the caption is at full size on its first frame (99.8 % of events) and is replaced by a hard switch | – | measured |
| Capitalisation and punctuation | as written: sentence case, with commas, full stops and question marks shown | – | observed |

**Typeface.** A heavy, slightly wide grotesque sans. The actual font was not identified. Closest free fonts by
letter-shape overlap (48 samples; 1.0 would be an exact match):

| Free font | Overlap (IoU) | Size that gives the measured letter height |
|---|---|---|
| Mona Sans, weight 900 | 0.730 | 72.6 px |
| Archivo, weight 800 (bundled, SIL OFL) | 0.726 | 74.0 px |
| Chivo, weight 900 | 0.716 | 75.0 px |
| Rubik, weight 800 | 0.702 | 74.1 px |

An overlap of 0.73 is "similar", not "the same font". Use one of these as a stand-in; do not claim it is the reference font.

## How many words per caption

| | Value | Spread |
|---|---|---|
| Words per caption (mean) | 1.26 | 1.19 – 1.34 |
| One-word captions | 76 % | 71 – 83 % |
| Two-word captions | 21.7 % | 15 – 27 % |
| Three-word captions | 2.4 % | 1 – 4 % |
| Characters per caption (median / longest) | 5 / 15 | longest 13 – 21 |
| Caption width (median / widest) | 19 % / 54 % of frame width | widest 44 – 66 % |

Grouping rule, fitted to the real caption boundaries (it reproduces 77.7 % of them and gives 1.25 words per caption):

1. A caption never continues past `.` `?` `!` or `,`. (After a comma the next word joined the caption in 10 of 295 cases, after a full stop in 3 of 341.)
2. Join two neighbouring words when the shorter one has 1 or 2 letters and the pair, with its space, is at most 8 characters ("of the", "in a", "he is", "to ever").
3. Add a third word only when all three are short (first two at most 4 letters, third at most 5) and the caption stays within 12 characters.
4. Everything else is one word per caption.

How often a pair was joined, by the length of its shorter word: 1 letter 45 %, 2 letters 32 %, 3 letters 20 %, 4 letters 6.5 %, 6 or more under 1 %.

## Timing

| | Value | Spread |
|---|---|---|
| Captions per second | 2.94 | 2.73 – 3.15 |
| Captions per video | 183 | 163 – 231 |
| Time on screen (median / mean) | 0.325 s / 0.339 s (10 frames) | median 0.30 – 0.37 s; one event in ten is 4 frames or shorter, one in ten 16 frames or longer |
| Caption appears before its first word is heard | 3.7 frames (0.12 s) | 3.5 – 4.0 frames between videos; 2.6 – 5.6 frames inside a video |
| First caption | on screen in frame 0 | all 20 |
| Gap between captions | none: each stays until the next replaces it | – |

The early appearance matters: text that arrives a tenth of a second ahead of the voice reads as "in sync", text that
arrives with or after the word reads as late.

Where a word "starts" depends on the model that times the words. The 3.7 frames come from the model used for the
analysis. The bundled tools time words with a different model, which puts each start a median 20 ms later (91 % of 4,612
reference words agree within one frame). By that model's clock the same reference captions lead by 4.1 frames (3.9 – 4.3
between videos), so `voice.py` and `measure.py` work to 4.1. The captions land on the same frames either way.

## The captions are machine-made

The reference captions contain speech-recognition mistakes that were left in (a wrong homophone, a doubled word across a
caption boundary). So they were generated from the audio and not proofread. For your own videos, generate captions from
the script text (as `voice.py` does), not from speech recognition: you get the same look with no errors.

## What to keep clear of the caption

The caption line occupies y = 1310 – 1395 px. Keep the main subject's face out of that band; in the reference the
characters' heads sit in the upper 60 % of the frame and the caption crosses bodies, props or ground. YouTube's own
interface covers roughly the bottom 20 % and the right-hand 12 % of a Short, so nothing important goes there either.
