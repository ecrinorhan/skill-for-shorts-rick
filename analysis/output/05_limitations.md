# Limitations

What the analysis could not establish, and how far each kind of number can be trusted.

## Coverage

- 20 videos: the 20 newest of the 155 Shorts the channel listed. They span about five weeks. The channel had no Videos
  tab, so "Shorts and long videos" reduces to Shorts.
- View, like and comment counts are one snapshot (time in `01_video_table.md`). Newer videos had less time to collect
  views.

## Metadata

- YouTube's player data asked for a sign-in in this environment. Tags, subtitle tracks and YouTube's own transcripts
  could not be read.
- Upload time is exact for the 15 newest uploads and date-only for #16 to #20.
- Ten top comments per video were fetched. No pinned comment and no creator comment was among them, which does not
  prove there is none.
- The audio label is "Original Sound" on all 20. It does not say where the music or the effects came from.
- Whether the videos carry a synthetic-content disclosure was not recorded.

## Transcripts

- The narration was transcribed by software and corrected against the burned-in captions, with a few manual fixes made
  by looking at frames (`../data/transcript_overrides.json`). Nobody listened to the audio.
- The narration is not reproduced in any report.

## Picture

- Joins between takes are detected automatically. A by-eye check confirmed 207 of 210 detected dissolves and 53 of 55
  detected cuts, and found 26 joins the detector had missed. Join counts are therefore a little low.
- Camera labels (push-in, orbit and so on) come from optical flow and are heuristic.
- The caption font was not identified. The rule that groups words into captions reproduces 77.7 % of the caption
  boundaries.

## Sound

- Everything split into voice, music and effects comes from software-separated stems: levels are good to about
  ±1.5 dB and counts to about ±10 %. Effect classes, musical key and tempo are estimates.
- The music was not identified, and whether the voice is a person or synthetic was not decided.

## By-eye reviews

- One AI reviewer per video looked at extracted frames, following `../review/REVIEW_PROMPT.md`. No person reviewed the
  videos.
- The second-by-second logs of the three most-viewed videos (191 seconds) were written from one frame per second
  (`../review/SECONDS_PROMPT.md`).
- What the reviewers could not determine from frames, such as the software used, is listed per video in
  `02_video_cards.md`.

## Views

- Links between a metric and views were computed for every metric on 17 to 20 videos. With that many comparisons a few
  low p-values are expected by chance. Treat them as leads, not findings.

## Word timing

- The stored word times come from a model licensed for non-commercial use. The skill's tools use a different,
  MIT-licensed model that puts word starts a median 20 ms later (see `../README.md`).

## Not done

- One video was made with the skill's tools and measured against the targets: 8 of 86 metrics fall outside the
  reference's range (listed in the skill's `SKILL.md`, section 7). No second story was produced.
- Nobody listened to the tools' audio output.
