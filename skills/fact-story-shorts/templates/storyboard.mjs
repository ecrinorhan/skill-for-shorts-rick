// storyboard.mjs — a minimal starting point. Copy it into your project folder and replace the sets, the cast and the takes.
// It needs a narration with at least three sentences (sentences.json, words.json, captions.json from voice.py).
// Reference: references/renderer.md. A full example: examples/bridge-keeper/storyboard.mjs.

// Your own cast: change the shapes in scripts/render/cast.js if you want a different drawing style.
const cast = {
  hero: { skin: '#e9b98c', top: '#2f8f86', bottom: '#3a3f52', boots: '#2a2420', detail: 'scarf', detailColor: '#f0c040', hat: { type: 'cap', color: '#b33f3a' }, hair: { style: 'short', color: '#5a3a22' } },
  doubter: { skin: '#b9825a', top: '#7a5aa8', bottom: '#ebe4d2', boots: '#1d1b22', detail: 'coat', detailColor: '#f0c75e', hair: { style: 'side', color: '#2a2420' }, build: 1.08 },
};

// One small set, reused by every take with a different mood. Build your own places the same way.
function yard(tk, mood = 'day') {
  const night = mood === 'night';
  tk.exposure = night ? 1.1 : 1.0;
  tk.tint.set(night ? '#c9d2f0' : '#ffffff');                 // set the tint before adding characters
  tk.sky(night ? '#1b2250' : '#2f7fd8', night ? '#6a6fa8' : '#bfe2ff', { near: 40, far: 220 });
  tk.sun({ c: night ? '#cfd8ff' : '#fff0d2', i: night ? 1.6 : 3.2, dir: [-5, 8, 6], area: 18 });
  tk.hemi(night ? '#8f9ad6' : '#d6e9ff', '#8f7a55', night ? 0.9 : 1.05);
  tk.ground({ c: '#7cba4e', c2: '#58963a' });
  tk.box(5.2, 3.0, 0.3, { p: [0, 1.5, -2.6], c: '#ead9b5', c2: '#b9a37a', tex: 'planks', rep: [3, 2] });          // back wall
  tk.box(1.6, 0.9, 0.9, { p: [1.3, 0.45, -1.2], c: '#a9754a', c2: '#6b4a2e', tex: 'planks' });                    // crate
  tk.sign('NO\nENTRY', { p: [-0.75, 2.0, -2.42], w: 1.2, h: 0.85 });                                              // in-world text
  tk.scatter('blade', 400, { x: [-7, 7], z: [-2, 5] }, { c: ['#7cba4e', '#58963a', '#8fca5a'], s: [0.06, 0.12] });
  tk.life({ x: [-7, 7], z: [0.6, 5] }, { n: 70 });                                                            // swaying grass, flowers, butterflies, cloud shadows
  if (night) tk.lamp([1.3, 1.6, -1.1], '#ffc56a', 16, 9, { glow: 0.5 });
}

const takes = [];
const T = (id, start, join, build) => takes.push({ id, start, join, build });

// 1. Hook: the action is on screen in frame 0.
T('hook', 0, 'start', (tk) => {
  yard(tk, 'day');
  const a = tk.s(0), e = tk.e(0);
  tk.actor('hero', 'hero', { p: [0.2, 0, 0], pose: 'hold', expr: 'determined', face: 'right', item: 'cup' })
    .key(a + (e - a) * 0.5, { pose: 'pointDown', expr: 'smug', blend: 0.18 });
  tk.cam([
    { t: 0, pos: [0.4, 1.5, 6.2], look: [0.3, 1.15, 0], push: 0.05 },                             // slow push-in from frame 0
    { t: a + (e - a) * 0.55, move: 0.6, pos: [3.6, 2.6, 5.0], look: [1.2, 0.7, -1.0], push: 0.04, orbit: 3 },   // fast move to the crate
  ]);
  tk.sfx('pop', 0.05, { gain: -20 });
  tk.sfx('whoosh', a + (e - a) * 0.55, { gain: -27 });
  tk.ambience('wind', { gain: -46 });
});

// 2. The doubter. A hard cut on the first word of sentence 2.
T('doubter', (tk) => tk.s(1), 'cut', (tk) => {
  yard(tk, 'day');
  const a = tk.s(1);
  tk.actor('doubter', 'doubter', { p: [-0.9, 0, 0.3], pose: 'hips', expr: 'bored', face: 'right' }).key(a + 0.8, { pose: 'shrug', expr: 'worried' });
  tk.actor('hero', 'hero', { p: [1.0, 0, 0], pose: 'stand', expr: 'smug', face: 'left' });
  tk.cam([{ t: a - 1, pos: [-2.6, 1.5, 4.6], look: [0, 1.2, 0], push: 0.04 }]);
  tk.sfx('thud', a + 0.05, { gain: -24 });
});

// 3. Later. A 10-frame dissolve that starts on the first word of sentence 3, and a change of light.
T('night', (tk) => tk.s(2, 0.17), 'dissolve', (tk) => {
  yard(tk, 'night');
  const a = tk.s(2);
  tk.actor('hero', 'hero', { p: [0.4, 0, 0.2], pose: 'carry', expr: 'happy', face: 'right', item: 'lantern' }).walk(a + 0.4, a + 2.4, [2.4, 0.4]);
  tk.motes({ x: [-2, 3], y: [0.4, 2.6], z: [-1, 2] }, 40, { c: '#ffe9b0', opacity: 0.6 });
  tk.cam([
    { t: a - 1, pos: [-1.0, 1.9, 7.5], look: [1.0, 1.1, 0], push: 0.03 },
    { t: a + 2.6, move: 0.7, pos: [3.4, 1.4, 3.6], look: [2.4, 1.2, 0.4], push: 0.05 },
  ]);
  tk.sfx('steps', a + 0.4, { dur: 2.0, every: 0.25, gain: -28 });
  tk.sfx('swish', a + 2.6, { gain: -27 });
  tk.sfx('chime', a + 3.2, { gain: -24 });
});

export default { cast, takes };
