# Analysis of the 20 reference Shorts

Measurements of the 20 newest Shorts of `youtube.com/@RicksClips3000`, taken from the video files and the public
listing. The channel listed 155 Shorts and had no Videos tab, so there are no long videos to compare with. The skill
built from these numbers is in `../skills/fact-story-shorts/`.

## Where each result is

| Result | File |
|---|---|
| Metadata and headline numbers per video | `output/01_video_table.md`, `output/01_video_table.csv`, `data/videos.json` |
| Analysis per video: measurements and the by-eye review | `output/02_video_cards.md`, `data/videos/<video>/`, `data/reviews/` |
| Comparison across the videos and the numeric style bible | `../skills/fact-story-shorts/references/style-bible.md`, `data/summary.json` |
| The three most-viewed videos, second by second | `output/04_top3_second_by_second.md`, `data/seconds/` |
| What could not be established | `output/05_limitations.md` |
| Three original scripts | `../skills/fact-story-shorts/examples/` |
| Tool and asset findings with confidence labels | `../skills/fact-story-shorts/references/assets-and-tools.md` |
| Finished-video checklist | `../skills/fact-story-shorts/SKILL.md`, section 6 |

The reference narration is not reproduced anywhere. Reports paraphrase it, and the originality check compares hashed
word sequences (`../skills/fact-story-shorts/references/reference_shingles.json`).

## The scripts, in the order they run

They read and write a work folder that is not in the repository (the videos, every frame, the separated audio).

| Script | What it does |
|---|---|
| `00_list_channel.py`, `01_fetch_metadata.py` | list the channel's tabs; collect metadata, counts and top comments |
| `02_extract.py`, `03_contact_sheets.py` | technical specs, frames at 30 fps, audio; contact sheets |
| `04_transcribe.py` | word-level transcription |
| `05_separate.py`, `05b_separate_dnr.py` | separate the voice; separate dialogue, music and effects |
| `06_frame_metrics.py`, `07_shots.py`, `07b_boundary_sheets.py` | per-frame measurements; joins, takes, holds and camera moves; sheets for checking joins by eye |
| `08_captions.py` | find the burned-in captions, read them, measure position and colour |
| `09_audio.py` | loudness, voice, music bed, sound-effect events |
| `10_align.py` | reconcile the transcript with the captions and time every word |
| `11_palette.py` | colour and grade |
| `12_music_match.py`, `12b_music_id.py` | is a music track reused; can it be identified |
| `13_font_match.py` | closest free font to the captions |
| `14_pack.py` | one data pack per video for the by-eye review |
| `15_sync.py` | what the picture changes are timed to |
| `16_aggregate.py` | one record per video, summary statistics, rankings, trends |
| `17_caption_style.py`, `18_caption_grouping.py` | caption outline, shadow and size; the rule that groups words into captions |
| `19_voice_forensics.py` | numbers that bear on how the voice track was made |
| `20_style_targets.py` | the targets file the skill's tools read, and their copy of the measuring scripts |
| `21_reviews.py` | collect the by-eye reviews (`review/REVIEW_PROMPT.md`) and tally them |
| `22_script_stats.py` | wording statistics and the hashed sequences for the originality check |
| `23_cards.py`, `24_top3.py`, `25_style_bible.py` | write the per-video cards, the second-by-second report and the style bible |
| `26_aligner_check.py` | compare the two word-timing models on all 20 videos |

`20`, `23` and `25` need only `data/`, so the targets, the cards and the style bible can be regenerated from this
repository. The others need the work folder.

## Word timing: two models

The word times in `data/` were made with torchaudio's MMS_FA model, whose weights are licensed for non-commercial use
only. The skill's tools use the MIT-licensed wav2vec2 base model instead, and `10_align.py` now defaults to it
(`ALIGN_MODEL=mms` selects the old one). On the 20 reference videos the new model puts word starts a median 20 ms later;
91.3 % of 4,612 words agree within one frame and 99.8 % within two. Measured with the new model, the reference captions
lead their words by 4.06 frames (3.89 to 4.29 between videos) instead of 3.73, and that is the value the tools work to
(`data/aligner_check.json`).
