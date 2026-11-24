# Sound: voice, music, effects, mix

Measured on the audio of the 20 reference files (AAC 128 kbit/s, 44.1 kHz stereo, as served by YouTube).
Voice, music and effects were separated by software before measuring (`analysis/scripts/05_separate.py`,
`05b_separate_dnr.py`, `09_audio.py`, `19_voice_forensics.py`), so:

- **measured** = taken from the full mix or from word timings; trust it
- **estimate** = taken from a separated stem; levels are good to about ±1.5 dB, counts to about ±10 %, class names are heuristic

Nobody listened to the files. Everything about how the voice *sounds* comes from numbers.

## Mix

| | Mean | Range over 20 videos | Confidence |
|---|---|---|---|
| Integrated loudness | −14.1 LUFS | −15.1 to −14.0 (18 of 20 at −14.0 or −14.1) | measured |
| True peak | −2.1 dBTP | −3.5 to −1.7 | measured |
| Loudness range | 2.2 LU | 1.6 – 3.2 | measured |
| Stereo width (side level relative to mid) | −26.5 dB | −32 to −20.5 | measured |
| Silence before the first word | 0.11 s | 0.08 – 0.20 | measured |
| Sound after the last word | 0.18 s | 0.04 – 0.34 | measured |

A loudness range of 2 LU means the level is flat from start to finish: no quiet intro, no swell at the end.
The mix is close to mono; what width there is comes from the effects.

## Voice

| | Mean | Range | Confidence |
|---|---|---|---|
| Speaking pace | 222 words per minute | 200 – 246 | measured |
| Syllables per second | 4.86 | 4.48 – 5.24 | measured |
| Pace by position | 220 wpm in the first 10 s, 225 in the middle, 210 in the last window | – | measured |
| Voice sounding | 98.3 % of the runtime | 97.0 – 99.3 | measured |
| Pauses of 250 ms or more | 0 | 0 in every video | measured |
| Pauses of 120 ms or more | 0.3 per video | 0 – 2 | measured |
| Gap between sentences | 154 ms (median) | 120 – 200 | measured (word timings) |
| Breath sounds | none found | 0 in every video | estimate |
| Pitch, median | 196 Hz | 175 – 209 | estimate |
| Pitch range (5th to 95th percentile) | 16.1 semitones | 15.0 – 17.2 | estimate |
| Sentences pitched 3 semitones or more away from the video's median | 25 % | – | estimate |
| Questions and exclamations | 4.5 semitones above the median on average | – | estimate |
| Loudness of the voice stem | −14.3 LUFS | −15.2 to −14.1 | estimate |
| Level spread (10th to 90th percentile) | 16.1 dB | 14.4 – 18.6 | estimate |
| Position in the stereo field | centre (side −37.7 dB below mid) | −40.6 to −35.1 | estimate |

What this means for a narrator or a text-to-speech voice:

1. **No gaps.** Cut every silence longer than about 0.1 s inside a sentence and leave about 0.15 s between sentences. The
   first word starts a tenth of a second into the file and the file ends two tenths after the last word.
2. **Fast but even.** 220 – 225 words per minute throughout. It does not start slow and speed up.
3. **Wide melody.** The pitch moves over 16 semitones, which is animated storytelling, not a flat read. Eleven stock
   text-to-speech voices reading a test paragraph measured 6 – 15 semitones (the bundled default, `af_heart`, 10). `voice.py`
   widens the pitch contour toward the target; the bundled example ends at 14 to 14.5 (it varies a little between runs).
4. **Act the quoted lines.** One sentence in four sits 3 semitones or more above or below the narrator's normal pitch. Those are the
   lines spoken by characters, the questions and the exclamations. One voice plays every part; there are no second voices.
5. **Dry and close.** No audible room. A gentle high-pass, a little compression, nothing else.

Whether the reference voice is a person or a synthetic voice could not be decided (see `assets-and-tools.md`). Do not
imitate or clone it. Use your own voice or a licensed voice.

## Music

All numbers in this section are estimates from a separated music stem that sits about 20 dB under the voice.

| | Mean | Range |
|---|---|---|
| Loudness | −33.7 LUFS | −36.1 to −28.9 |
| Below the voice | 19.4 LU | 14.6 – 21.9 |
| Starts | 0.04 s (median), with the first frame | 0.04 – 0.46 |
| Stops | at the end of the file (0.15 s before it) | 0.02 – 0.59 |
| Drop-outs | none in 19 videos, one in 1 | – |
| Level follows the voice (ducking) | no (correlation 0.05) | −0.22 to 0.31 |
| Level variation over 2 s windows | 2.3 dB | 1.1 – 3.9 |
| Tempo | about 115 BPM | 92 – 152 |
| Key | minor in 18 of 20 (D minor 9, E minor 6, A minor 3), major in 2 | – |
| Brightness (spectral centroid) | 560 Hz, a dark, soft bed | 294 – 829 |
| Stereo | effectively mono | – |
| Same track reused | no: 20 different tracks (no two videos share one) | – |

So: one continuous, quiet, dark, minor-key instrumental bed per video, a different one each time, running from the first
frame to the last at a constant level. It is felt more than heard. It is never ducked, never stops for effect and never
has a "drop".

## Sound effects

Estimates from a separated effects stem.

| | Mean | Range |
|---|---|---|
| Events per video | 37 | 23 – 56 |
| Events per 10 s | 5.9 | 4.1 – 8.5 |
| Density by position (per 10 s) | 5.4, 6.4, 6.5, 5.8, 5.7, 5.7 (first to sixth 10 s) | – |
| Runtime with an effect sounding | 29 % | 19 – 47 |
| Peak level of a typical effect | −38 dBFS, about 21 dB under the voice's median level | −43 to −32 |
| Loudest tenth of the effects | about 8 dB under the voice | −16 to −1 |
| Loudest single effect in a video | about level with the voice (1 dB under) | 8 dB under to 6 dB over |
| Effects within 10 dB of the voice | 6 per video | 1 – 12 |
| Length of an effect | 0.26 s (median); 56 % are shorter than 0.3 s, 11 % longer than 1 s | – |

Kinds of effect, by heuristic class, share of 742 events: whooshes 27 % (rising 11 %, falling 11 %, bursts 4 %), foley and
other short sounds 18 %, risers and swells 13 %, low hits and rumbles 12 %, clicks, pops and ticks 9 %, impacts and booms
7 %, thuds and taps 5 %, dings, chimes and bells 5 %, sustained ambience 5 %.

What the effects are timed to (measured against a chance baseline of 12 %):

- 19 % of joins between takes and 15 % of fast camera moves have an effect starting within 0.1 s. That is a little above chance.
- Effects are not timed to sentence starts (6.5 % against 6.1 % by chance).

So most effects belong to things that happen in the picture (a hammer hit, a door, a splash, a bell), not to the edit.
One short effect about every 1.7 s, most of them quiet enough never to compete with a word, and about six per video
nearly as loud as the voice (which moments those are was not checked by ear).

## Picture and sound together

- A new take arrives with a new sentence: 43 % of dissolves begin within 0.1 s of the first word of a sentence (6 % by chance),
  and the middle of a join falls 5 frames after the sentence starts.
- Fast camera moves are not timed to sentences, words, effects or the music's beat. They happen when the story moves.
- Joins are not on the musical beat.

## Targets for your own mix

`mix.py` applies these and reports the result.

| | Target |
|---|---|
| Integrated loudness | −14.1 LUFS |
| True peak | at or under −2.1 dBTP |
| Voice | centre, −14.3 LUFS before the final limiter |
| Music | 19 – 20 LU under the voice, start at 0.0 s, run to the end, no ducking |
| Effects | 5 – 7 per 10 s; typical peak about 21 dB under the voice; up to about six key hits per video (a crash, a snap, a bell) within 10 dB of it |
| Head and tail | first word at 0.08 – 0.12 s, end 0.15 – 0.25 s after the last word, no fade-out |
