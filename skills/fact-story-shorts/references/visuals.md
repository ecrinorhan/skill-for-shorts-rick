# Visuals: characters, sets, camera, effects

Two kinds of evidence are used here and kept apart:

- **measured**: computed from every frame of the 20 reference videos (`analysis/scripts/06_frame_metrics.py`, `07_shots.py`, `11_palette.py`)
- **by eye**: one reviewer per video looked at contact sheets and frame montages (`analysis/review/REVIEW_PROMPT.md`); for the
  three most-viewed videos a reviewer also logged every second (`SECONDS_PROMPT.md`)

By-eye findings are observations. Nobody has seen the creator's project files.

## 1. The look

By eye, all 20 videos are built the same way:

- **Sets are 3D.** Rooms, streets and landscapes with real perspective, textured surfaces, soft light and shadows. Geometry
  stays rigid through camera moves, the same set is seen again from other angles, and small in-world text stays sharp. Of
  113 observations the reviewers made about how the picture looks made, 84 point to a 3D render, 23 to hand-drawn
  animation of the characters, 5 are undecided and 1 points to generated imagery.
- **Characters are flat.** Thick dark outline, flat fills, placed in the 3D scene and scaled by distance. 15 of 20 reviewers
  called the mix "3D sets with flat outlined characters"; the other 5 saw toon-shaded or outline-free 3D.
- **The camera does the moving.** Characters hold a pose and swap to the next one. The camera pushes in, orbits and flies.
- **Captions sit on top** (see `captions.md`).

Layers, back to front: sky → distant scenery with haze → the 3D set → 3D props → flat characters → foreground props and
particles → glow, vignette and colour grade → caption.

## 2. Characters

What the reference characters look like (by eye). This describes their design so that yours can be different. Read
`originality.md` before designing a cast.

| Trait | Reference (by eye) |
|---|---|
| Head | a large circle or egg, white or off-white, tinted by the scene's light. Sampled head fills: `#FDFAF5`, `#FCF9F0`, `#FBFAF6`; in shade `#CDCCCA`; under coloured light pink, lilac or blue |
| Head height | about a third of the body height (estimates 0.25 – 0.45; most often 0.33) |
| Outline | thick, near-black, even width, on characters and hand-held props. The sets have no outline |
| Body | a small capsule or coat in one or two flat colours, with one job marker: a tie, a vest, an apron, a badge |
| Limbs | thin dark strokes, usually without hands or feet |
| Hair or hat | one flat shape. The hat tells you the job: bowler, cap, helmet, crown |
| Eyes | dots; rings with a dot when surprised; half-lids when smug; closed arcs when smiling. Swapped, not animated |
| Mouth | a small line, a toothy grid, an open oval. Swapped with the pose |
| Shadow on the ground | a soft blob in 9 videos, a cast silhouette in 5, none in 4 |
| Recurring characters | 3 – 4 per video, plus crowds of the same build |

How they move (by eye):

- **Pose to pose.** A character snaps or eases between a few drawn poses. There is little in-between drawing.
- **Mouths.** The reviewers' labels were: changes with the pose only 9, flaps while speaking 6, static 3, follows speech 2.
  They sampled frames 2 – 8 frames apart, so nobody has checked syllable by syllable. Safe reading: mouths open and close
  during a spoken line in some shots, and that is all the lip movement there is.
- **Eyes.** Expression swaps. No reviewer saw a regular blink.
- **Idle.** A small sway or head tilt. In a hold, the slow camera push supplies the life.
- **Squash and stretch.** Rare: a hop, an impact, a head that swells on a shout.

Roles (from the story coding): a calm protagonist who acts, an authority or rival who objects (boss, captain, sheriff,
guard), a doubter or sidekick who says the funny line, and a crowd that reacts as one.

**For your own cast** fill in one sheet per character:

| | |
|---|---|
| Role and one-word temperament | |
| Silhouette (what makes it readable at 80 px tall) | |
| Three colours (hex): main, second, accent | |
| Job marker (hat, tool or badge) | |
| Six expressions | neutral, smug, angry, shocked, worried, happy |
| Eight poses | stand, hands on hips, point, hold an object, arms up, shrug, sit, walk cycle |

The bundled renderer has such a cast system (`scripts/render/cast.js`): 18 poses, 12 expressions, 4 gaits, 5 hats and 6
hand-held items, drawn from a palette you give it. See `renderer.md`.

## 3. Sets and light

| | Reference | Source |
|---|---|---|
| Distinct places per video | 10.9 (6 – 18): a new place about every 6 s | by eye |
| Places with readable in-world text | 59 % of 218 places | by eye |
| Day and night | day or morning 100 places, night, dusk or sunset 87, interior or undecided 31 | by eye |
| Changes of light or mood | 5.5 per video (2 – 9) | by eye |
| Brightness | 109 of 255 on average; between videos 63 – 139 | measured |
| How much brightness swings inside a video | standard deviation of 30 between one second and another | measured |
| Contrast | 53 (luma standard deviation); blacks at 21, whites at 241 | measured |
| Saturation | 114 of 255 (69 – 161) | measured |
| Warm and cool | 47 % warm hues, 45 % cool hues | measured |
| Corners | 69 % as bright as the centre | measured |

What the reviewers' notes on 218 places mention: soft light 45 %, haze or fog 30 %, practical lights such as lamps and
lanterns 26 %, window light 21 %, a blurred background 20 %, hard shadows 17 %, rim light 6 %, light shafts 6 %.

Working rules:

1. **One place per idea.** Eleven places in a minute means most sentences get their own. A place can be tiny: a desk top,
   a keyhole, a calendar on a wall.
2. **Write on the set.** Dates, names, rules and prices appear as signs, labels, screens, newspapers and calendars, so the
   narration does not have to say them. Use invented names.
3. **Let the light tell the story.** Day for the plan, night or storm for the doubt, a warm or bright scene for the
   payoff. Change the light two to nine times.
4. **Complementary colours.** A cool set with a warm key light or the other way round: orange lamp on blue night, teal
   shadow on a tan desert.
5. **Depth.** Haze toward the horizon, something soft in the foreground, a vignette at the corners. Nothing may look low-poly: round things are round, boxes have soft edges, and animals and props are built from capsules and spheres, not from blocks.
6. **Keep heads in the upper 60 % of the frame.** The caption crosses the picture at 70 %.

The five largest colour clusters of each video are listed in `analysis/output/02_video_cards.md`. Dark navy or plum
shadows with one saturated accent are the most common combination. Colourfulness fell over the five weeks studied (76 in
the five oldest, 46 in the five newest), so the recent videos are more muted.

## 4. Camera

All numbers measured, per video, mean and range over 20 videos.

**Takes and joins**

| | |
|---|---|
| Takes (continuous pieces of picture) | about 16. The detector found 13.3 joins; the by-eye check raises that to about 15 |
| Mean take length | 4.6 s as detected, nearer 4 s after the correction; the longest take is 13 s (8 – 23) |
| Join type | dissolve 81 % of joins, hard cut 19 % |
| Dissolve length | 10 frames (6.5 – 14) |
| Hard cuts | 2.75 per video (0 – 14). Almost none in the five oldest videos (0.2), 8.2 in the five newest |
| Where a join falls | 43 % of dissolves start within 3 frames of the first word of a sentence (6 % by chance); the middle of the dissolve comes about 5 frames after that word |

**Holds** (the framing is steady; 78 % of the runtime)

| | |
|---|---|
| Holds | 31 per video, 1.2 s median, longest 6.5 s (3.5 – 12.7) |
| Never static | 63 % of hold time the camera pushes in, 11 % it pulls out, the rest drifts sideways or rolls slightly; 1.4 % is fully static |
| Push-in speed | 4.1 % per second on average, median 3.4 (1.4 – 11.8). Over a 3 s hold the subject grows by a tenth |

**Fast moves** (22 % of the runtime)

| | |
|---|---|
| Moves | 16.7 per video (9 – 28), 0.7 s median (0.35 – 1.0) |
| Peak speed | 65 % of the frame height per second (46 – 84) |
| What they are | half of them (51 %) end on a different place or subject: the camera flies, whips or orbits to the next thing inside the same take. The other half re-frame the same subject |
| Motion blur | none on average (sharpness during a move is 1.02 times the sharpness before it) |
| Timing | not tied to sentence starts, effects or the music's beat. A move happens when the story moves |

By eye, the 119 moves the reviewers singled out were push-ins 30 %, orbits and fly-throughs 26 %, pull-outs 19 %, whips and
pans 9 %, cranes and tilts 3 %.

**Rhythm**

| | |
|---|---|
| Picture changes (joins + fast moves) | 29 per minute (21 – 38) |
| Time between two changes | 1.6 s median, 2.1 s mean; the longest stretch without one is 6.9 s (3.9 – 13.7) |
| Through the video | steady: 2.0 – 2.9 changes in every 5 s from the first second to the last |
| Fully still frames | 10 % (2 – 19 %) |

The by-eye log of the three most-viewed videos agrees: a new place or framing every 1.61 s.

**Framing** (by eye, the three most-viewed videos, 191 seconds)

| Shot size | Share | | The picture | Share |
|---|---|---|---|---|
| Wide | 26 % | | shows the action being narrated | 35 % |
| Medium | 22 % | | shows the object just named | 17 % |
| Medium-long | 17 % | | shows a reaction | 13 % |
| Insert of an object or detail | 14 % | | establishes the place | 12 % |
| Medium close-up | 9 % | | shows the consequence | 7 % |
| Full body | 7 % | | travels to the next place | 6 % |
| Extreme wide | 5 % | | is a visual joke | 6 % |
| Close-up | 2 % | | is a diagram or explanation view | 4 % |

Who or what is in the frame: the protagonist 22 % of seconds, an object or prop 22 %, the authority or rival 20 %, the
place itself 18 %, a secondary character 11 %, a crowd 5 %.

So this is a wide-and-medium style. Faces are small. Objects get as much screen time as the hero. Angles (by eye, mentions):
eye level 21, low 19, top-down or aerial 15, high 12, tilted 5.

**The first frame** (by eye, 20 videos): the protagonist doing the hook action 14, posing with the key object 4, two
characters 2. Shot size medium-long 9, full body 6, medium 5. The protagonist looks at the camera in 13. The first
caption is already on screen.

## 5. Effects

By eye, 9.7 visual effects per video (4 – 19). Share of the 194 noted: particles (sparks, dust, coins, snow) 19 %; glow
13 %; screens and interface inserts (a phone, a monitor, a gauge) 9 %; smoke and steam 8 %; in-world signs that appear
on cue 8 %; a colour shift of the whole scene 8 %; a flash 7 %; diagram or cutaway views 3 %; defocus 3 %; speed lines 3 %.

Each one lands on a narrated action or on the word that names the thing. Explanations are mostly shown with the story's
own objects (a cutaway of the wall, the mechanism in close-up); a separate diagram view takes 4 % of the seconds.

## 6. Planning numbers for a 62-second video

| Plan | Count |
|---|---|
| Takes | 15 – 17, one per sentence or pair of sentences, each starting on the first word of its sentence |
| Joins | 10-frame dissolves; 0 – 3 hard cuts for a shock or a punchline |
| Camera setups | about 38 (one new framing every 1.6 s): 2 – 3 per take, linked by fast moves |
| Fast moves | 15 – 20, each 0.5 – 0.9 s |
| Slow push-in | on every hold, 3 – 5 % per second |
| Places | 9 – 12 |
| In-world text | on 5 – 7 of the places |
| Changes of light | 3 – 6 |
| Visual effects | 8 – 12 |
| Sound cues | 35 – 40 (see `sound.md`) |

## 7. Shot list

Fill in one row per take before building anything (`templates/shot-list.md`):

| Take | Sentences | Starts | Join in | Place and light | Who, pose, expression | Opening framing | Fast move: when, to what | Effect and in-world text | Sound cues |
|---|---|---|---|---|---|---|---|---|---|

For the bundled renderer, each row becomes one `T(...)` block in `storyboard.mjs` (`renderer.md`).

## 8. Three ways to make the pictures

| Route | Fits the measured style | Status |
|---|---|---|
| The bundled renderer: three.js sets from simple shapes, flat canvas-drawn puppets, the camera grammar above built in | timing, camera, captions and layering match; sets are plainer than the reference | runs here from script to MP4 (see `SKILL.md`) |
| A 3D package (Blender, Unreal Engine, Unity) with your characters as flat planes or sprites | closest to what the frames suggest | not tested here |
| Generated stills or clips | the reviewers saw rigid geometry and crisp, stable in-world text, which generators often fail at. Check every shot for warped text and shapes that change inside a take | not tested here |

Whatever the route: 1080 × 1920, 30 frames per second, captions burned in to `captions.md`, and the timing taken from the
narration (`words.json`, `sentences.json`), never the other way round.
