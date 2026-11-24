# The bundled renderer: storyboard reference

`scripts/render/render.mjs` turns a project's `storyboard.mjs` into frames with three.js in headless Chromium. A storyboard
is plain JavaScript: a cast, and a list of takes. Every moment is computed from the time alone, so frames can be rendered
in any order and in parallel. A complete, working storyboard is `examples/bridge-keeper/storyboard.mjs`; a minimal one is
`templates/storyboard.mjs`.

Units: metres, seconds, degrees. `y` is up. A standing character is 1.7 m tall. The frame is 1080 × 1920 with a 35°
vertical field of view by default.

## Commands

```
node scripts/render/render.mjs <project> --timeline        # write timeline.json (takes, camera moves, sound cues); no frames
node scripts/render/render.mjs <project> --still 0,45,300  # preview frames into <project>/stills/
node scripts/render/render.mjs <project> --frames 0:150    # render frames 0-149 and encode <project>/preview.mp4
node scripts/render/render.mjs <project> --workers 4       # render everything and encode <project>/video.mp4
```

The project folder must already hold `sentences.json`, `words.json`, `captions.json` and `voice_meta.json` (written by
`voice.py`). On software WebGL with 3 workers a 90-frame preview took 37 s here, which works out at about 13 minutes for
a 62-second video; a GPU is faster.

## File layout

```js
import * as THREE from '/three.module.js';      // only if you need raw three.js
import { POSES } from '/cast.js';               // only if you tweak poses
const cast = { hero: { skin: '#e9b98c', top: '#c9742e', bottom: '#4a3f38', hat: { type: 'brim', color: '#6a4a2e' } } };
const takes = [];
const T = (id, start, join, build) => takes.push({ id, start, join, build });

T('hook', 0, 'start', (tk) => { /* build the scene, the camera and the cues */ });
T('setup', (tk) => tk.s(1), 'cut', (tk) => { /* ... */ });
T('chains', (tk) => tk.s(2, 0.17), 'dissolve', (tk) => { /* ... */ });

export default { cast, takes, style: { push: 0.035 } };   // style is optional
```

A take runs from its `start` to the next take's `start`. Give `start` as a number of seconds or as a function of `tk`.
For a dissolve, start the take about 0.17 s after its sentence begins (`tk.s(i, 0.17)`): the dissolve is centred on the
start, so it then begins on the first word, which is what the reference does.

| Take field | Meaning | Default |
|---|---|---|
| `id` | name, used for random seeds and in `timeline.json` | required |
| `start` | seconds, or `(tk) => seconds` | required |
| `join` | `'dissolve'`, `'cut'`; the first take is `'start'` | `'dissolve'` |
| `joinFrames` | dissolve length in frames | 10 |
| `tint` | colour multiplied onto the characters, to match the scene's light | `'#ffffff'` |
| `exposure` | scene exposure | 1 |

## Timing helpers

| Call | Returns |
|---|---|
| `tk.s(i, offset = 0)` | start of sentence `i` (0-based, as in `script.json`) plus `offset` seconds |
| `tk.e(i, offset = 0)` | end of sentence `i` |
| `tk.word(/^regex/i, nth = 1, offset = 0)` | start of the `nth` spoken word matching the regex. Throws if the word is not in the narration |

Always time things to sentences and words, never to hard-coded seconds. If you change the script and rebuild the voice,
the storyboard follows.

## Camera

`tk.cam([...])` takes a list of shots. A shot holds from its `t` until the next shot's `t`.

| Shot field | Meaning | Default |
|---|---|---|
| `t` | when the shot begins | required |
| `pos`, `look` | camera position and the point it looks at, `[x, y, z]` | required |
| `fov` | vertical field of view in degrees | 35 |
| `push` | slow zoom toward `look`, as a rate per second (0.04 = 4 % per second). Negative pulls out | `style.push` (0.035) |
| `orbit` | slow rotation around `look`, degrees per second | 0 |
| `drift` | `[x, y, z]` metres per second added to `look` (a slow truck or follow) | none |
| `move` | seconds taken to travel here from the previous shot: a fast camera move inside the take | 0 (the first shot of a take needs none) |
| `ease` | `'inOut'`, `'inOut3'`, `'out'`, `'in'`, `'linear'`, `'back'` | `'inOut'` |
| `roll` | degrees of roll | 0 |
| `shake` | `{ from, to, amp, freq }` | none |

Give the first shot of a take a `t` about one second before the take starts (`a - 1`), so a dissolve into the take
already shows it drifting. Every shot with a `move` is written to `timeline.json` as a camera move.

## Characters

A cast entry is a look: `{ skin, top, bottom, boots, build, hair: { style, color }, hat: { type, color, band, plume },
detail, detailColor, belt, sash, epaulettes, moustache }`.

| Field | Values |
|---|---|
| `hair.style` | `short`, `side`, `grey`, `bald` |
| `hat.type` | `cap`, `shako`, `bicorne`, `brim`, `beanie`, `none` |
| `detail` | `coat`, `uniform`, `apron`, `scarf` |
| `build` | 1 is regular; below 1 slimmer, above 1 stockier |
| `moustache` | a colour, or leave out |

`const a = tk.actor(id, lookName, { p: [x, y, z], pose, expr, face, item, height, gaze })` places a character.

| Method | Use |
|---|---|
| `a.key(t, { pose, expr, face, item, gaze, blend })` | change pose, expression, facing (`'left'`, `'right'`, `'front'`), held item or eye direction at time `t`. `blend` is the pose change time in seconds (0.2) |
| `a.walk(t0, t1, [x, z], { gait, step })` | walk in a straight line. `gait`: `walk`, `march`, `shuffle`, `run` |
| `a.offset((t) => [dx, dy, dz, rotDeg])` | add any motion: a jump, a ride, a shake |

Poses: `stand`, `hips`, `point`, `pointUp`, `pointDown`, `armsUp`, `shrug`, `hold`, `carry`, `push`, `windup`, `throwEnd`,
`cower`, `salute`, `sit`, `laugh`, `stop`, `lean`. A pose can also be an object, for example
`{ ...POSES.sit, aF: [150, 10] }` (arm and leg angles in degrees: `aF`, `aB`, `lF`, `lB`, plus `lean` and `head`).

Expressions: `neutral`, `smug`, `happy`, `grin`, `angry`, `shout`, `shock`, `worried`, `bored`, `determined`, `laugh`, `dizzy`.

Held items: `lantern`, `cup`, `sword`, `staff`, `sticks`, `drum`.

Characters always face the camera plane, blink every 3 – 4 s, and sway slightly. Mouths change with the expression only;
there is no lip-sync, in line with the reference.

`tk.crowd([lookNames], n, (i, t) => [x, y, z], { variants, state })` draws `n` characters cheaply. `state` is an object or
`(t, v) => ({ pose, expr, face, item })`, or `{ phase, gait, spread }` for a walking crowd.

## Building a set

Every builder takes an options object: `p` position, `r` rotation in degrees, `s` scale, `c` colour, `c2` second colour,
`tex` texture (`mottle`, `grass`, `gravel`, `planks`, `stone`, `checker`, `water`), `rep` texture repeats, `rough`, `metal`,
`emissive`, `glowI`, `opacity`, `cast`, `receive`, `in` (a parent group).

| Shapes | |
|---|---|
| `tk.box(w, h, d, o)`, `tk.cyl(rTop, rBottom, h, o, segments)`, `tk.sphere(r, o)`, `tk.cone(r, h, o, segments)`, `tk.plane(w, h, o)`, `tk.tube(points, radius, o)` | basic solids |
| `tk.group({ p, r, in })` | an empty parent, to move or rotate several parts together |
| `tk.add(geometry, o)` | any three.js geometry |

| Environment | |
|---|---|
| `tk.sky(top, bottom, { near, far, mid })` | gradient sky dome and matching fog, plus the living backdrop below unless `alive: false` |
| `tk.backdrop(top, bottom, { hills, clouds, birds, stars, wind })` | what `tk.sky` adds so the background is never empty: two ridges of hills with trees on the horizon, clouds that drift, a flock of birds that flaps across the view, and twinkling stars instead of birds when the sky is dark. `hills` is a colour or `false`, `clouds` and `birds` are counts, `wind` is degrees of drift per second. Pass the same options to `tk.sky` |
| `tk.sun({ c, i, dir, area, soft })` | key light with shadows |
| `tk.hemi(skyColor, groundColor, intensity)` | fill light |
| `tk.lamp([x, y, z], c, intensity, distance, { glow })` | a practical light |
| `tk.glow([x, y, z], radius, c, opacity)` | a soft additive halo |
| `tk.beam(p, r, length, radius, c, opacity)` | a light shaft |
| `tk.ground({ c, c2, tex, tile })`, `tk.water({ y, c, c2, flow })` | large planes |
| `tk.life({ x: [a, b], z: [a, b], y }, { n, flowers, butterflies, shadows, c, wind })` | life on a stretch of ground: grass tufts and flowers that sway in gusts, butterflies, and cloud shadows drifting across. Call it for every area of open ground a take shows, and keep roads, floors and water out of the area |
| `tk.cloud([x, y, z], scale)` | a cloud |
| `tk.scatter('pebble' | 'blade' | 'block', count, { x: [a, b], z: [a, b] }, { c: [colours], s: [min, max], skip })` | hundreds of small pieces |
| `tk.sign('TEXT\nLINE 2', { p, r, w, h, bg, c })` | in-world text on a board |

| Effects | |
|---|---|
| `tk.puff({ t, p, n, size, c, up, speed, life, g })` | a burst of dust, sparks or spray at time `t` |
| `tk.motes({ x, y, z }, n, { c, opacity })` | floating dust in light |
| `tk.ring({ t, p, r0, r1, life, c, upright })` | an expanding ring, for a pulse or an impact |

| Animation | |
|---|---|
| `tk.tween(object, 'position' | 'rotation' | 'scale', [[t, value, ease], ...])` | keyframes on any object |
| `tk.every((t) => { ... })` | run code every frame. Must depend on `t` only |

## Sound cues

Cues are written into `timeline.json`, and `mix.py` synthesizes them.

`tk.sfx(type, t, { gain, pan, f, dur, down, every })`, with `gain` in dB (default −26; typical quiet cue −28, a key hit −12 to −18).

| Kind | Types |
|---|---|
| One-shots | `thud`, `stomp`, `step`, `pop`, `blip`, `ding`, `chime`, `chain`, `squeak`, `whoosh` (`down: true` for a falling one), `swish`, `riser` (`dur`), `boom`, `rumble` (`dur`), `creak`, `drum`, `snap`, `splash`, `crash`, `neigh`, `sip` |
| Repeating | `march`, `steps`, `drums` with `dur` and `every` (seconds between hits) |
| Background | `tk.ambience('river' | 'wind', { gain })` for the length of the take |

Aim for 35 – 40 cues in a minute: one on each fast camera move (`whoosh`, `swish`), one on each action, a `riser` into the
turn, one loud hit at the climax.

## Style defaults

`export default { cast, takes, style: { ... } }` can override: `push` 0.035, `pushGain` 1.45, `moveGain` 1.3, `aliveSky` true, `dissolveFrames` 10, `vignette` 0.5,
`captionFont` 74, `captionY` 1378, `captionStroke` 5.5, `captionShadow` [4, 5]. The caption values are the measured ones;
change them only if you change the font (`assets/fonts/`).

## Working method

1. Write `timeline.json` (`--timeline`) and read the counts it prints: takes, camera moves, sound cues. Compare with
   `visuals.md` section 6.
2. Render one still from the middle of every take (`--still`). Check framing, that heads clear the caption line, and that
   every character is lit.
3. Render a short stretch (`--frames 0:150`) to judge motion.
4. Render everything.
