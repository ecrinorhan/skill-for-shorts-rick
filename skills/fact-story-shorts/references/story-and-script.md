# Story and script

How to find a story for this format and write it to the measured shape. Numbers are from the 20 reference videos
(`style-bible.md`); "by eye" numbers are from one reviewer per video. All example lines here are new, written for this
skill. None is taken from the reference channel.

## 1. What the format is

A one-minute story told by a single narrator, in which somebody does something that looks stupid, a doubter says so,
things escalate, and one true fact explains why the "stupid" thing was right (or why the clever thing was wrong). The fact is real.
The people and the plot around it are usually invented.

| What the reference stories are about (by eye) | Share |
|---|---|
| Engineering and physics, history and war, crime and scams, psychology and behaviour | about a fifth each |
| Law, money and work | about an eighth |
| Pure parable with no real-world fact | about an eighth |

Settings are spread evenly over modern day, the 1900s, the 1800s, the Middle Ages and the future. The reviewers judged about
four in ten of the plots to be invented parables, a quarter history, a fifth psychology experiments and the rest legend or news.

## 2. Pick a fact that fits

A fact fits when you can answer yes to all five:

1. **Backwards at first sight.** The right action looks wrong (a bridge keeper orders an army to walk out of step) or the obvious action fails.
2. **One mechanism.** You can explain why in two or three short sentences a ten-year-old follows.
3. **Visible.** The cause and the result can be shown as objects doing things. No abstract "the economy shifted".
4. **A physical ending.** Something snaps, sinks, opens, vanishes or pays out in the last five seconds.
5. **Checkable.** You have read a source for it, and you know which parts of your story you made up.

Write a fact card before any script: the claim in one sentence, the mechanism in two, the source, and a list of what you
will invent. That card becomes the `fact` and `sources` fields of `script.json`.

## 3. Choose one of four structures

| Structure (by eye, 16 videos) | Share | Shape |
|---|---|---|
| **A. Act first, explain at the end** | 56 % | Odd action → doubter → the action seems to fail or cost him → question → "You see / Well," mechanism → consequence |
| **B. Pure story, the twist explains itself** | 19 % | Odd action → escalation → reveal of who was really behind it or what it was really for. No separate explanation |
| **C. Premise first, then story** | 12 % | Odd action → "You see," the rule of this world in one or two sentences → story plays out under that rule → consequence |
| **D. Second-person scenario** | 12 % | A claim → "Imagine you …" → what happens to you, step by step → question → explanation |

The examples in `examples/` cover three of them: `bridge-keeper` (C with a late explainer as well), `rat-tails` (A),
`smoky-room` (D).

## 4. Beat sheet and word budget

Positions are where each beat starts as a share of the runtime (median of 16 videos, by eye). The word budget turns that
into a 231-word script.

| Beat | Label in `script.json` | Starts at | Words | Job |
|---|---|---|---|---|
| Hook | `hook` | 0 % | 14 | One sentence: the odd action, with its catch. Ends by 3.8 s |
| Setup | `setup` | 6 % | 38 | Who he is, what is at stake, the one rule or deadline. The doubter may speak here |
| Conflict and escalation | `conflict`, `escalation` | 24 % | 62 | The doubter or the boss pushes back. He does it anyway. It gets worse in two or three steps, each a new picture |
| Turn | `escalation` or `payoff` | 51 % | 36 | The moment it seems lost, or the first sign that he was right |
| Question | `question` | 60 – 70 % | 6 | A short question the viewer is already asking. 15 of 20 videos have one |
| Explanation | `explainer` | 68 % | 36 | The mechanism, starting with "You see," or "Well,". Two to four sentences, one everyday comparison |
| Payoff | `payoff` | 80 % | 24 | The mechanism plays out on screen |
| Ending | `ending` | 93 % | 15 | One sentence. The consequence lands, and the video stops |

Twelve of the 16 reviewed videos have a separate explanation beat; it takes about 16 % of the runtime (10 seconds).
Structure B has none, and structure C puts a two-sentence premise right after the hook ("You see" is the second sentence in
7 of 20 videos) and may or may not explain again later.

## 5. The first sentence

| | Reference |
|---|---|
| Length | 13.8 words on average; 9 – 19 covers most; shortest 6, longest 21 |
| Ends at | 3.8 s (2.9 – 5.3) |
| Words spoken in the first 3 s | 11.5 |
| Has a turn in it (a comma, *and*, *but*, *yet*, *because*) | 15 of 20 |
| Title content words it repeats | 1 of about 4. The title names the topic, the first sentence shows the scene |

Five forms, with how often each is used:

| Form | Used in | Pattern | New example |
|---|---|---|---|
| Somebody did an odd physical thing | 14 of 20 | *He / They* + past-tense action verb + object + place, then the catch | "She glued a coin to the sidewalk, and it paid her rent for a year." |
| If you … | 2 | *If you* + ordinary action + special place, + what goes wrong | "If you whistle on a submarine, the whole crew stops breathing." |
| A claim that sounds wrong | 2 | A plain statement of the paradox, + *but* / *and* the worse part | "The safest seat on this train was the one nobody would sit in." |
| A place with a rule | 1 | *There is* + a thing + where, + the rule about it | "There's a door in this school that has never been opened, and every student has the key." |
| Look at this | 1 | An order to look at two things that seem alike | "Look at these two bridges. One is about to fall down." |

Rules that hold for all five:

- In the action form the verb comes in the first three words, and it is something a hand does: cut, pour, bury, bend, glue, sell.
- The action form is in the past tense. The story then switches to the present tense and stays there (by eye, 10 of 16
  videos mix tenses this way; the other 6 are in the present throughout).
- It contains one concrete object the viewer can see in the first frame.
- It does not explain anything, greet anyone, or mention the channel.
- The picture in frame 0 already shows it: the protagonist doing the action (12 of 16) or holding the key object (3 of 16).

## 6. Sentences

| | Reference |
|---|---|
| Sentences | 19.6 per video (15 – 22) |
| Words per sentence | 12 on average, median 11; one sentence in five has 5 words or fewer; the longest has 21 – 30 |
| Reading level | US grade 4.4 (2.3 – 6.7); 1.29 syllables per word; under 5 % of the words have three syllables or more |
| How sentences open | 37 % with *So / And / But / Then / Yet / Until*; 18 % with *The / His / A / Every*; 14 % with *He / They / It / You* |
| Questions | 1.15 per video (0 – 3) |
| Exclamations | 0.4 per video (0 – 2) |
| *you / your* | 1.8 per 100 words; up to 9.6 in a second-person story |
| Number words and figures | 5.7 per video (1 – 14) |
| Contractions | 2.6 per 100 words |
| Time jumps ("the next morning", "by midnight", "a month later") | about 2 per video |

How to write like that:

- **Chain with conjunctions.** Start every third sentence with *So*, *But*, *And* or *Then*. Each one is a cause or a
  reversal, which is what keeps a one-minute story moving.
- **Mix lengths.** A run of two long sentences, then one of three to five words. The short one carries the turn.
- **Use plain words.** If a word has three syllables, look for a shorter one. Keep the one technical term for the
  explanation (four reference videos name the effect with "it's called …").
- **Be specific with numbers.** "Six hundred boots", "fifteen minutes", "one cent". A number sounds true and gives the
  picture something to show.
- **Compare to the kitchen.** When something big happens, compare it to something small and domestic ("as fat as a fence
  post", "like landing a plane"). The reference averages about one such simile per video.
- **Skip time in three words.** "That night,", "A month later,", "By minute six,". Each skip is also a new picture.
- **Present tense, third person, no name.** The hero is *he* or *she* in 17 of 20 videos. Where a name is used it is a plain
  first name. Other people are their job: the captain, the guard, the boss.

## 7. Spoken lines

18 of the 20 reference transcripts contain direct speech, usually one to three short exchanges (the per-video reviewers
counted a median of 2 spoken lines).

- Most lines belong to the doubter or the authority. The hero mostly answers by acting; when he speaks it is a short order.
- Each is one short sentence, usually a sarcastic question or a flat order.
- Most have no "he said". The narrator simply changes voice (see `sound.md`: quoted lines sit 3 semitones or more off the
  narrator's normal pitch). A speech verb appears in 1.6 sentences per video.
- Mark them in `script.json` with `"speech": "<who>"` and a `"pitch"` offset in semitones (+2 to +4 for a shout, −2 for a
  low, dry line), so the narration and the storyboard can act on them.

## 8. Humour

By eye, every reviewed video is told deadpan. The recurring devices:

1. The doubter describes the hero's action as something silly and ordinary.
2. A character is thrilled or smug at exactly the wrong moment.
3. An understatement after a disaster ("goes for a swim").
4. A list of three with the odd one last.
5. The narrator admits the hero has no idea what he is doing.

One joke every 10 – 15 seconds, never explained, never laughed at by the narrator.

## 9. The explanation

- Open with "You see," or "Well,". 13 of 20 videos turn this way, at 74 % of the runtime on average (58 – 91 %).
- Often a question comes just before it ("So how …?", "But why …?"). The 23 questions in the 20 videos fall in two
  groups: 14 at 9 – 37 % of the runtime (the doubter's) and 9 at 46 – 76 % (the viewer's).
- Two to four sentences. The first states the fact. The second gives the mechanism with an everyday comparison the viewer
  has felt (pushing a swing, squeezing through a crowded doorway, gripping a wet bar of soap). The third connects it to
  the story.
- Everything said in this part must be true as stated. This is the part people check.
- Then go back to the story for the consequence. The explanation is the last line in 7 of 16 videos; in the others the
  story's result is.

## 10. The ending

| | Reference |
|---|---|
| Last sentence | 13 words on average (2 – 27), starting at 94 % of the runtime |
| What it is (by eye, 16 videos) | the last piece of the explanation 44 %; the consequence, stopping on the impact 38 %; a twist reveal 12 %; a return to the opening 6 % |
| Call to action, sign-off, moral | none in any video |
| After the last word | 0.18 s of sound, then the file ends. No outro, no logo, no fade |
| Loop | the last sentence shares at most one content word with the first; the videos do not loop by wording |

Stop one beat early. If the last sentence explains what the viewer has just seen, delete it.

## 11. Title and description

| | Reference |
|---|---|
| Title length | 5.9 words (4 – 8) |
| Opening word | *Why* 7, *The* 6, *How* 3, *This*, *What*, *He* 1 each, other 1 |
| Style | a plain statement of the topic or the puzzle; title case; no emoji, no hashtag, no question mark needed |
| Description | the title again, nothing else |
| Hashtags and tags | none visible; tags could not be read (see `analysis/output/05_limitations.md`) |

Title patterns to fill in: *Why [group] [did odd thing]* · *The [person] Who [did odd thing]* · *How [small thing] [beat big thing]* ·
*The [adjective] [thing] Experiment* · *What the [object] Really Meant*.

The title gives away the topic but not the mechanism, and it must be true of the video.

## 12. `script.json`

```json
{
  "title": "Why Soldiers Break Step on Bridges",
  "structure": "one line: which of the four structures and any twist on it",
  "fact": "What is real, with the key numbers. Then: INVENTED for this story: ...",
  "sources": ["a URL or citation you actually read"],
  "voice": "af_heart",
  "sentences": [
    {"beat": "hook", "text": "One sentence per entry."},
    {"beat": "conflict", "text": "A spoken line.", "speech": "colonel", "pitch": 3.0}
  ]
}
```

- `beat` is one of `hook`, `setup`, `conflict`, `escalation`, `question`, `explainer`, `payoff`, `ending`. The mixer uses the
  beats to change the music's layers; the storyboard uses the sentence index for timing.
- One sentence per entry. A two-word reaction ("It has no tail.") is its own entry.
- Write numbers as words when they should be read as words ("fifty miles"); figures are read as figures.

## 13. Writing procedure

1. Fill in the fact card (section 2).
2. Pick the structure (section 3) and write the first sentence in three different forms (section 5). Keep the one whose
   picture you can see most clearly.
3. Write the ending sentence next. Know where you are going.
4. Lay out the beats with their word budgets (section 4) and draft.
5. Cut to 215 – 245 words. Cut explanation first, then adjectives, never the short reaction sentences.
6. Run `scripts/check_script.py script.json`. Fix every FAIL and every WARN you did not intend. Write the timed sheet
   with `--md script.md`.
7. Read it aloud once at full speed with a timer. It should take 60 – 66 seconds without a breath pause. If you run
   out of air, a sentence is too long.
8. Check `originality.md` before going further.
