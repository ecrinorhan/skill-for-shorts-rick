# Reference averages vs “Why Soldiers Break Step on Bridges”

Verdict: **ok** = within 15 % of the reference mean (or equal / inside the reference range where the mean is zero or fixed); **in range** = more than 15 % from the mean but inside what the 20 reference videos span; **OFF** = outside both.


## Format

| Metric | Reference mean (min – max) | Test | Δ vs mean | Verdict |
|---|---|---|---|---|
| Frame rate | 30 fps (30 – 30) | 30 fps | – | ok |
| Audio sample rate | 44,100 Hz (44,100 – 44,100) | 44,100 Hz | – | ok |
| Audio channels | 2 (2 – 2) | 2 | – | ok |
| Duration | 62.4 s (55.4 – 77.9) | 63.0 s | +1.0 % | ok |

## Script

| Metric | Reference mean (min – max) | Test | Δ vs mean | Verdict |
|---|---|---|---|---|
| Words | 230.6 (202 – 295) | 233 | +1.0 % | ok |
| Words per minute | 222 (199.8 – 245.5) | 222 | +0.0 % | ok |
| Sentences | 19.6 (14 – 26) | 21 | +7.1 % | ok |
| Words per sentence (mean) | 12.0 (8.9 – 17.1) | 11.1 | -7.8 % | ok |
| First sentence, words | 13.8 (6 – 21) | 16 | +15.5 % | in range |
| First sentence ends | 3.78 s (1.56 – 5.6) | 3.86 s | +2.3 % | ok |
| Words in the first 3 s | 11.5 (9 – 13) | 11 | -4.3 % | ok |
| First word starts | 0.107 s (0.08 – 0.2) | 0.1 s | – | ok |
| Silence after the last word | 0.181 s (0.04 – 0.34) | 0.3 s | – | ok |
| Questions | 1.15 (0 – 3) | 1 | – | ok |
| Exclamations | 0.4 (0 – 2) | 0 | – | ok |
| you / your per 100 words | 1.8 (0 – 9.6) | 0.9 | – | ok |

## Captions

| Metric | Reference mean (min – max) | Test | Δ vs mean | Verdict |
|---|---|---|---|---|
| Caption events | 182.9 (163 – 231) | 184 | +0.6 % | ok |
| Captions per second | 2.94 (2.73 – 3.15) | 2.92 | -0.5 % | ok |
| Words per caption | 1.26 (1.19 – 1.33) | 1.27 | +0.8 % | ok |
| One-word captions, share | 0.761 (0.71 – 0.83) | 0.81 | +6.4 % | ok |
| Two-word captions, share | 0.215 (0.15 – 0.27) | 0.11 | -48.8 % | **OFF** |
| Caption duration, median | 0.325 s (0.3 – 0.367) | 0.333 s | +2.5 % | ok |
| Caption appears before its word | 4.06 frames (3.89 – 4.29) | 4.08 frames | +0.5 % | ok |
| Caption centre, % of height | 70.3 % (70.3 – 70.3) | 70.4 % | +0.2 % | ok |
| Caption line top | 1,324 px (1,322 – 1,324) | 1,324 px | +0.0 % | ok |
| Letter height | 54.7 px (54 – 68) | 54 px | -1.3 % | ok |
| Frames with a caption | 100.0 % (99.9 – 100) | 100 % | +0.0 % | ok |
| Characters per caption, median | 5.15 (5 – 6) | 5 | -2.9 % | ok |
| Caption width, % of frame width, median | 19.3 % (18.2 – 20.6) | 18.9 % | -1.9 % | ok |
| Coloured captions, share | 0.001 (0 – 0.005) | 0 | – | ok |

## Picture

| Metric | Reference mean (min – max) | Test | Δ vs mean | Verdict |
|---|---|---|---|---|
| Joins between takes | 13.2 (9 – 19) | 12 | -9.4 % | ok |
| Joins per minute | 12.8 (8.3 – 20.6) | 11.4 | -10.8 % | ok |
| Hard cuts | 2.75 (0 – 14) | 3 | – | ok |
| Dissolves | 10.5 (4 – 19) | 9 | -14.3 % | ok |
| Dissolves, share of joins | 0.807 (0.25 – 1) | 0.75 | -7.1 % | ok |
| Dissolve length, median | 10.4 frames (6.5 – 14) | 11 frames | +5.8 % | ok |
| Take length, mean | 4.62 s (2.76 – 6.52) | 4.83 s | +4.5 % | ok |
| Hold length, median | 1.18 s (0.7 – 1.8) | 0.87 s | -26.5 % | in range |
| Fast camera moves | 16.7 (9 – 28) | 24 | +43.7 % | in range |
| Fast camera moves per minute | 16.2 (8.7 – 28.9) | 22.9 | +41.8 % | in range |
| Camera move length, median | 0.696 s (0.35 – 1.02) | 0.75 s | +7.8 % | ok |
| Runtime spent in fast moves | 22.2 % (7.7 – 40.9) | 37.7 % | +69.8 % | in range |
| Camera move peak speed, median | 64.6 % H/s (45.5 – 84.1) | 118.2 % H/s | +83.0 % | **OFF** |
| Composition changes per minute | 28.9 (21.1 – 38.5) | 34.4 | +18.8 % | in range |
| Time between changes, median | 1.62 s (1.08 – 2.54) | 1.55 s | -4.6 % | ok |
| Fully still frames | 9.95 % (2 – 19.4) | 4.6 % | -53.8 % | in range |
| Image motion, median | 9.06 % H/s (4.4 – 16.2) | 7.8 % H/s | -14.0 % | ok |
| Image motion, 90th percentile | 41.5 % H/s (23.2 – 65.9) | 81.5 % H/s | +96.2 % | **OFF** |
| Slow zoom during holds | 4.1 %/s (1.36 – 11.8) | 3.51 %/s | -14.4 % | ok |
| Hold time spent pushing in | 0.634 (0.42 – 0.83) | 0.7 | +10.4 % | ok |
| Hold time fully static | 0.014 (0 – 0.12) | 0 | – | ok |

## Colour

| Metric | Reference mean (min – max) | Test | Δ vs mean | Verdict |
|---|---|---|---|---|
| Brightness (luma mean, 0-255) | 109.4 (62.8 – 139.4) | 102.8 | -6.1 % | ok |
| Contrast (luma SD) | 53.0 (41.8 – 63.1) | 47.5 | -10.3 % | ok |
| Black level (1st percentile) | 21.0 (1.2 – 32.6) | 9.2 | -56.2 % | in range |
| White level (99th percentile) | 241.0 (221.2 – 253.6) | 208.3 | -13.6 % | ok |
| Saturation (HSV S mean, 0-255) | 113.8 (69.2 – 160.8) | 114.1 | +0.2 % | ok |
| Colourfulness | 65.9 (39.5 – 87.1) | 57.3 | -13.1 % | ok |
| Warm hues, share of saturated pixels | 0.466 (0.171 – 0.964) | 0.541 | +16.1 % | in range |
| Cool hues, share of saturated pixels | 0.454 (0.034 – 0.807) | 0.276 | -39.2 % | in range |
| Corner / centre brightness | 0.689 (0.379 – 0.861) | 0.726 | +5.4 % | ok |
| Sharpness (Laplacian variance) | 1,301 (619 – 2,329) | 544 | -58.2 % | **OFF** |
| Brightness change across the video (SD of 1 s means) | 30.0 (18.5 – 38.4) | 15 | -50.0 % | **OFF** |

## Sound

| Metric | Reference mean (min – max) | Test | Δ vs mean | Verdict |
|---|---|---|---|---|
| Integrated loudness | -14.1 LUFS (-15.1 – -14) | -14.1 LUFS | +0.1 % | ok |
| True peak | -2.1 dBTP (-3.5 – -1.7) | -2.1 dBTP | +0.0 % | ok |
| Loudness range | 2.18 LU (1.6 – 3.2) | 1.3 LU | -40.4 % | **OFF** |
| Voice stem loudness | -14.3 LUFS (-15.2 – -14.1) | -14.3 LUFS | +0.3 % | ok |
| Voice pitch, median | 196.4 Hz (174.7 – 208.9) | 204.2 Hz | +4.0 % | ok |
| Voice pitch range (p5-p95) | 16.1 semitones (15 – 17.2) | 15.2 semitones | -5.4 % | ok |
| Voice on, share of runtime | 98.3 % (97 – 99.3) | 96.9 % | -1.4 % | ok |
| Syllables per second | 4.86 (4.48 – 5.24) | 4.82 | -0.8 % | ok |
| Pauses of 250 ms or more | 0 (0 – 0) | 0 | – | ok |
| Longest pause | 0.03 s (0 – 0.21) | 0.14 s | – | ok |
| Voice level spread (p90-p10) | 16.1 dB (14.4 – 18.6) | 15.7 dB | -2.5 % | ok |
| Voice crest factor | 14.6 dB (13.6 – 15) | 14.8 dB | +1.7 % | ok |
| Voice spectral centroid | 1,008 Hz (771 – 1,244) | 1,079 Hz | +7.1 % | ok |
| Music stem loudness | -33.7 LUFS (-36.1 – -28.9) | -33.8 LUFS | -0.4 % | ok |
| Voice above music | 19.4 LU (14.6 – 21.9) | 19.5 LU | +0.7 % | ok |
| Music starts | 0.115 s (0.04 – 0.46) | 0.03 s | – | **OFF** |
| Music drop-outs | 0.05 (0 – 1) | 0 | – | ok |
| Music level variation (SD of 2 s windows) | 2.25 dB (1.07 – 3.85) | 2.74 dB | +21.8 % | in range |
| Music tempo (estimate) | 115.2 BPM (92.3 – 152) | 114.8 BPM | -0.3 % | ok |
| Sound-effect events | 37.1 (23 – 56) | 45 | +21.3 % | in range |
| Sound effects per 10 s | 5.92 (4.1 – 8.54) | 7.15 | +20.7 % | in range |
| Runtime with an effect sounding | 28.9 % (18.8 – 46.7) | 16.5 % | -42.9 % | **OFF** |
| Effect level, median peak | -38.4 dBFS (-43.2 – -32.2) | -42.1 dBFS | -9.6 % | ok |
| Effect peak relative to voice | -20.5 dB (-25.5 – -14.8) | -24.5 dB | -19.5 % | in range |

**64 ok, 14 in range, 8 off, of 86 metrics.**
