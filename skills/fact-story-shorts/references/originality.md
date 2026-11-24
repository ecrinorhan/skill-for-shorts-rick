# Originality: use the formula, never the material

The reference channel is somebody else's work. This skill copies **how** those videos are built (lengths, pacing, order of
beats, where the caption sits, how loud the music is) and nothing of **what** they contain.

## Free to reuse (these are measurements and common craft)

- Format: 1080 × 1920, 30 fps, about 62 s, about 231 words at about 222 words per minute.
- Structure: a strange action in the first sentence, a doubter, a story told in the present tense, a question, a short
  explanation, an ending that stops on the consequence.
- Caption layout: one or two words at a time, white with a black outline, 70 % down the frame, a tenth of a second early.
- Picture grammar: one continuous take per sentence or two, joined by short dissolves, a slow push-in during every hold,
  a fast camera move when the story moves.
- Technique: flat outlined 2D characters standing in lit 3D sets.
- Sound: a voice with no pauses, a quiet minor-key bed that never ducks, a short effect every second or two, −14 LUFS.

## Not to be reused

| Do not reuse | Do instead |
|---|---|
| Their stories: the plot, the twist, the gags, the invented people | Start from a fact you found yourself and invent your own people and events around it |
| Their sentences | Write every line fresh. `check_script.py` fails a script that shares any 6-word sequence with the reference narration and warns on 5 |
| Their titles | Write your own in the same length (4 – 8 words). Search the channel first; if they already told a story on your fact, pick another fact |
| Their characters: white ball-shaped head, thin black stick limbs, capsule body | Design your own cast (see below) |
| Their sets, props and in-world signs | Build or generate your own; never trace or paste a reference frame |
| Their narrator's voice | Record your own voice or use a licensed voice. Do not clone or imitate theirs |
| Their music and effects | Use the bundled generator or licensed libraries. Never lift audio from their videos |
| Their channel name, thumbnails or any frame | Not in your video, description, thumbnail or prompts |

Do not give any generator (image, video, voice or music) a reference frame, reference audio or a reference transcript as its
input. Describe what you want in your own words, using the numbers in `style-bible.md`.

## An original cast

Characters in this style are simple, so two casts can end up looking alike by accident. Make yours differ from the
reference on at least four of these six points and keep it the same in every video:

| Trait | Reference (observed) | Bundled cast (`scripts/render/cast.js`) | Yours |
|---|---|---|---|
| Head shape | circle or egg | wide loaf with rounded corners | pick a shape that is not a circle |
| Head colour | white or off-white | skin tones | |
| Outline | black, thick, even | dark indigo `#1d1b33` | |
| Limbs | thin black single strokes, no hands | thick coloured sleeves and trousers, mitten hands, boots | |
| Body | small capsule in one or two flat colours | coat that widens at the hem, with buttons, sash or scarf | |
| Face | dot or half-lidded eyes, eyebrow strokes, tiny mouth | two-tone oval eyes, thick brow bars, nose bump | |

Keep what makes the style readable on a phone: head about a third of the body height, thick outlines, two or three flat
colours per character, one clear prop.

## Facts

A story in this format makes a factual claim, and viewers check it. In the 200 top comments fetched from the 20 reference
videos (10 per video), a keyword count finds 13 (6.5 %) with fact-checking words such as "actually", "not true" or "wrong"
and 6 (3 %) that mention AI or ChatGPT. The counts are by keyword, not by reading each comment.

1. Every script has a `fact` field that says what is real and what is invented, and a `sources` list with at least one
   source you actually read.
2. Whatever the narration presents as explanation ("You see, …") must be true as stated. Numbers in the explanation come from the source.
3. The people, the dialogue and the staging may be invented. Never attach invented words or deeds to a real, named person.
4. If the whole story is a made-up parable, the title must not promise history or science.
5. Follow the platform's current rules on disclosing synthetic voices and generated or altered pictures.

## Before publishing

- [ ] `check_script.py` reports 0 shared 6-word sequences and you have reworded any 5-word hit.
- [ ] The title is not on the reference channel and the story is not one they told.
- [ ] The cast differs from the reference on four of the six traits above.
- [ ] No reference frame, audio or text went into any tool.
- [ ] The `fact` field is filled in and every claim in the explanation is in a source you read.
