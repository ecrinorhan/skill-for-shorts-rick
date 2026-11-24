// storyboard.mjs — "Why Soldiers Break Step on Bridges" (original story, original cast, original sets).
// Every time comes from the narration: tk.s(i) / tk.e(i) = start / end of sentence i, tk.word(/regex/, nth) = a spoken word.
import * as THREE from '/three.module.js';
import { POSES } from '/cast.js';
import { rng } from '/stage.js';

const BEAT = 60 / 116, SPAN = 14;
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const ramp = (t, t0, t1, a = 0, b = 1) => a + (b - a) * clamp((t - t0) / (t1 - t0), 0, 1);
const IRON = { c: '#3d4250', rough: 0.5, metal: 0.25 };

const soldier = (skin, extra = {}) => ({ skin, top: '#2f8f86', bottom: '#ebe4d2', boots: '#1d1b22', detail: 'uniform', sash: '#f4f0e6', detailColor: '#f0c75e',
  hat: { type: 'shako', color: '#23222f', band: '#f0c75e', plume: '#d94f3d' }, hair: { style: 'short', color: '#5a3a22' }, ...extra });
const cast = {
  keeper: { skin: '#e9b98c', top: '#c9742e', bottom: '#4a3f38', boots: '#2a2420', detail: 'scarf', detailColor: '#2f8f86', hat: { type: 'brim', color: '#6a4a2e' }, moustache: '#dcd7cf', hair: { style: 'grey', color: '#dcd7cf' }, build: 1.08 },
  colonel: { skin: '#f0c4a0', top: '#27407a', bottom: '#ebe4d2', boots: '#1d1b22', detail: 'uniform', sash: '#d94f3d', detailColor: '#f0c75e', epaulettes: true, hat: { type: 'bicorne', color: '#1f2a4a', band: '#f0c75e' }, moustache: '#3a2a20', hair: { style: 'short', color: '#3a2a20' } },
  soldierA: soldier('#e8b98a'), soldierB: soldier('#c98f62', { moustache: '#3a2a20' }), soldierC: soldier('#f3d0b0', { hair: { style: 'short', color: '#c98a3a' } }),
  drummer: soldier('#d9a878', { top: '#b33f3a' }),
  kid: { skin: '#e8b98a', top: '#f0c040', bottom: '#3f6fb0', boots: '#b33f3a', hat: { type: 'beanie', color: '#d94f3d', band: '#f4f0e6' }, hair: { style: 'bald' }, build: 0.94 },
  parent: { skin: '#b9825a', top: '#7a5aa8', bottom: '#3a3f52', boots: '#2a2420', detail: 'coat', detailColor: '#e9d2a6', hair: { style: 'side', color: '#2a2420' } },
};

const MOODS = {
  day: { sky: ['#2f7fd8', '#bfe2ff'], sun: ['#fff0d2', 3.3, [-6, 9, 7]], hemi: ['#d6e9ff', '#8f7a55', 1.05], exposure: 1.0, tint: '#ffffff', grass: ['#73b04a', '#4f8a34'], water: ['#2f86b8', '#bfe6f5'], fog: [70, 330], glow: 0.3 },
  storm: { sky: ['#3a4668', '#a3aec8'], sun: ['#e3e9ff', 2.5, [-4, 8, 6]], hemi: ['#b9c6e6', '#55586a', 1.3], exposure: 1.08, tint: '#d6dbee', grass: ['#5f8f5c', '#3f6a48'], water: ['#2f6490', '#a8c6dc'], fog: [45, 230], glow: 0.75 },
  morning: { sky: ['#4aa6ee', '#ffe7c4'], sun: ['#fff4dc', 3.5, [7, 8, 6]], hemi: ['#dcecff', '#a08a5a', 1.1], exposure: 1.05, tint: '#ffffff', grass: ['#7cba4e', '#58963a'], water: ['#3a94c4', '#cfeefa'], fog: [80, 350], glow: 0.25 },
};

function tree(tk, x, z, s, c) {
  tk.cyl(0.14 * s, 0.2 * s, 1.2 * s, { p: [x, 0.6 * s, z], c: '#6b4a2e' }, 8);
  tk.cone(1.0 * s, 2.0 * s, { p: [x, 2.0 * s, z], c }, 9);
  tk.cone(0.75 * s, 1.6 * s, { p: [x, 3.0 * s, z], c }, 9);
}

/** The chain bridge over the gorge. o: mood, amp(t) deck heave in metres, lantern(t) swing angle, links, broken, collapse (time). */
function bridge(tk, o = {}) {
  const m = MOODS[o.mood || 'day'];
  tk.exposure = m.exposure; tk.tint.set(m.tint);
  tk.sky(m.sky[0], m.sky[1], { near: m.fog[0], far: m.fog[1] });
  tk.sun({ c: m.sun[0], i: m.sun[1], dir: m.sun[2], area: 32 });
  tk.hemi(...m.hemi);
  const amp = o.amp || (() => 0);
  const chainY = (x) => (Math.abs(x) <= SPAN ? 1.05 + 6.5 * (x / SPAN) ** 2 : Math.max(0.3, 7.55 - (Math.abs(x) - SPAN) * 2.1));
  const fallT = (x) => (o.collapse == null ? Infinity : o.collapse + 0.035 * Math.abs(x - 1));
  const yAt = (x, t) => {
    if (Math.abs(x) >= SPAN) return 0;
    let y = amp(t) * Math.sin(Math.PI * (x + SPAN) / (2 * SPAN)) * Math.sin(Math.PI * t / BEAT);
    const tt = t - fallT(x);
    if (tt > 0) y -= 4.9 * tt * tt;
    return y;
  };
  for (const sx of [-1, 1]) {
    tk.box(140, 30, 200, { p: [sx * (SPAN + 70), -15, 0], c: m.grass[0], c2: m.grass[1], tex: 'mottle', rep: [24, 34], cast: false });
    tk.box(0.8, 30, 200, { p: [sx * (SPAN + 0.35), -15.02, 0], c: '#8d8478', c2: '#5d564f', tex: 'stone', rep: [50, 8], cast: false });
    tk.box(60, 0.08, 5.0, { p: [sx * (SPAN + 30), 0.02, 0], c: '#cdb083', c2: '#a98c60', tex: 'gravel', rep: [20, 2], cast: false });
    for (const sz of [-1, 1]) {
      tk.box(1.2, 8.2, 1.2, { p: [sx * SPAN, 4.1, sz * 2.9], c: '#b9b0a2', c2: '#6f675e', tex: 'stone', rep: [1, 4] });
      tk.cone(1.0, 1.1, { p: [sx * SPAN, 8.75, sz * 2.9], r: [0, 45, 0], c: '#b0503c' }, 4);
    }
    tk.box(1.0, 0.8, 6.6, { p: [sx * SPAN, 7.4, 0], c: '#a39a8c', c2: '#6f675e', tex: 'stone', rep: [3, 1] });
  }
  tk.water({ y: -10, c: m.water[0], c2: m.water[1], size: 420 });
  for (const [x, z, s] of [[-70, -130, 1.3], [40, -150, 1.7], [110, -120, 1.2], [-140, -100, 1.5], [0, -180, 2.2]]) tk.sphere(30 * s, { p: [x, -6, z], s: [1.7, 0.5, 1], c: m.grass[1], cast: false }, 18);
  if (o.mood !== 'storm') for (const [x, y, z, s] of [[-30, 34, -120, 2.2], [45, 42, -150, 2.8], [10, 30, -100, 1.6], [-80, 46, -160, 3]]) tk.cloud([x, y, z], s);
  const r = rng(11);
  for (let i = 0; i < 18; i++) {
    const sx = i % 2 ? 1 : -1, x = sx * (SPAN + 5 + r() * 40), z = (r() < 0.5 ? -1 : 1) * (5.5 + r() * 26);
    if (x < -17 && x > -24 && z < 0 && z > -10) continue;
    tree(tk, x, z, 0.9 + r() * 0.9, r() < 0.5 ? m.grass[1] : '#3f7a3a');
  }
  tk.scatter('pebble', 260, { x: [-44, 44], z: [-2.4, 2.4] }, { skip: (x) => Math.abs(x) < SPAN + 0.3, s: [0.05, 0.13], c: ['#a89a84', '#8d8478', '#c2b59c'] });
  tk.scatter('blade', 700, { x: [-40, 40], z: [-12, 12] }, { skip: (x, z) => Math.abs(x) < SPAN + 0.6 || Math.abs(z) < 2.9, c: [m.grass[0], m.grass[1], '#8fca5a'], s: [0.06, 0.12] });
  // chains
  for (const sz of [-1, 1]) {
    const pts = [];
    for (let x = -18; x <= 18; x += 1) pts.push([x, chainY(x), sz * 2.9]);
    if (o.broken && sz === 1) {
      tk.tube(pts.filter((p) => p[0] <= -4).concat([[-3.6, 1.0, 2.9], [-3.4, 0.1, 2.95]]), 0.1, IRON, 40);
      tk.tube([[5.3, 0.3, 2.95], [5.6, 1.4, 2.9]].concat(pts.filter((p) => p[0] >= 6)), 0.1, IRON, 40);
    } else tk.tube(pts, 0.1, IRON, 96);
  }
  const links = [];
  if (o.links) for (let k = -5; k <= 5; k++) {
    const x = k * 0.36, l = tk.add(new THREE.TorusGeometry(0.18, 0.055, 8, 18), { p: [x, chainY(x), 2.9], r: [k % 2 ? 90 : 0, 0, 0], c: '#565c6c', rough: 0.45, metal: 0.3 });
    l.userData.y = chainY(x); links.push(l);
  }
  // deck
  const planks = [], hangers = [];
  for (let i = 0; i < 28; i++) {
    const x = i - 13.5, g = tk.group({ p: [x, 0, 0] });
    tk.box(0.96, 0.2, 4.8, { in: g, p: [0, -0.1, 0], c: i % 2 ? '#a9754a' : '#b8845a', c2: '#6b4a2e', tex: 'planks' });
    for (const sz of [-1, 1]) {
      tk.box(1.0, 0.09, 0.09, { in: g, p: [0, 0.95, sz * 2.3], c: '#7a5636' });
      if (i % 2 === 0) tk.box(0.09, 0.95, 0.09, { in: g, p: [0, 0.47, sz * 2.3], c: '#7a5636' });
    }
    planks.push({ x, g, spin: (i % 2 ? 1 : -1) * (0.6 + 0.08 * ((i * 7) % 5)) });
  }
  for (let x = -13; x <= 13; x += 2) for (const sz of [-1, 1]) {
    if (o.broken && sz === 1 && x > -4 && x < 6) continue;
    hangers.push({ x, m: tk.box(0.05, 1, 0.05, { p: [x, 0, sz * 2.9], c: '#3d4250', cast: false }) });
  }
  // keeper's hut and the lantern on its hook
  const hut = tk.group({ p: [-20.5, 0, -6.5] });
  tk.box(3.2, 2.5, 3.0, { in: hut, p: [0, 1.25, 0], c: '#ead9b5' });
  tk.cone(2.9, 1.7, { in: hut, p: [0, 3.35, 0], r: [0, 45, 0], c: '#b0503c' }, 4);
  tk.box(0.9, 1.7, 0.08, { in: hut, p: [0.3, 0.85, 1.52], c: '#6b4a2e' });
  tk.box(0.8, 0.7, 0.08, { in: hut, p: [-0.9, 1.5, 1.52], c: '#ffd98a', emissive: '#ffb347', glowI: 0.9 });
  const post = tk.group({ p: [-15.6, 0, 3.6] });
  tk.cyl(0.07, 0.09, 2.7, { in: post, p: [0, 1.35, 0], c: '#4a3a2c' }, 8);
  tk.box(0.7, 0.07, 0.07, { in: post, p: [0.32, 2.66, 0], c: '#4a3a2c' });
  const lantern = tk.group({ in: post, p: [0.62, 2.62, 0] });
  tk.cyl(0.014, 0.014, 0.22, { in: lantern, p: [0, -0.11, 0], c: '#2a2420' }, 6);
  tk.box(0.26, 0.34, 0.26, { in: lantern, p: [0, -0.4, 0], c: '#ffd35a', emissive: '#ffb428', glowI: 1.5 });
  tk.cone(0.24, 0.16, { in: lantern, p: [0, -0.16, 0], r: [0, 45, 0], c: '#3a332c' }, 4);
  tk.glow([0, -0.4, 0], 0.8, '#ffcf70', m.glow, { in: lantern });
  if (o.mood === 'storm') tk.lamp([-15, 2.2, 3.6], '#ffc56a', 14, 9);
  tk.every((t) => {
    for (const pl of planks) {
      const y = yAt(pl.x, t), tt = t - fallT(pl.x);
      pl.g.position.y = y; pl.g.visible = y > -10.4;
      pl.g.rotation.z = tt > 0 ? pl.spin * tt * 1.7 : Math.atan(yAt(pl.x + 0.5, t) - yAt(pl.x - 0.5, t));
      pl.g.rotation.x = tt > 0 ? pl.spin * tt : 0;
    }
    for (const h of hangers) {
      const yd = yAt(h.x, t) + 0.05, yc = chainY(h.x), len = Math.max(0.05, yc - yd);
      h.m.position.y = yd + len / 2; h.m.scale.y = len; h.m.visible = t < fallT(h.x);
    }
    lantern.rotation.z = o.lantern ? o.lantern(t) : 0.05 * Math.sin(1.3 * t);
  });
  return { yAt, chainY, links, lantern, m };
}

/** A marching column, 4 abreast. head(t) = x of the first row; B = bridge (for the deck height) or null on the road. */
function column(tk, B, o) {
  const cols = 4;
  return tk.crowd(['soldierA', 'soldierB', 'soldierC'], o.rows * cols, (i, t) => {
    const row = Math.floor(i / cols), c = i % cols, x = o.head(t) - row * 1.15 - (c % 2) * 0.1, z = (c - 1.5) * 0.92;
    let y = B ? B.yAt(x, t) : 0;
    if (o.floor != null && y < o.floor) y = o.floor + 0.07 * Math.sin(3.1 * t + x * 2.3 + c);
    return [x, y, z];
  }, { variants: 3, state: o.state });
}

function horse(tk, p, o = {}) {
  const c = o.c || '#8a5a34', dark = '#3f2a1a';
  const outer = tk.group({ p: [p[0] - 0.6, p[1], p[2]] }), g = tk.group({ in: outer, p: [0.6, 0, 0] });
  tk.box(1.7, 0.72, 0.6, { in: g, p: [0, 1.25, 0], c });
  tk.sphere(0.4, { in: g, p: [0.82, 1.27, 0], s: [1, 0.92, 0.76], c }, 14);
  tk.sphere(0.42, { in: g, p: [-0.82, 1.27, 0], s: [1, 0.92, 0.76], c }, 14);
  const neck = tk.group({ in: g, p: [0.8, 1.5, 0] });
  tk.box(0.44, 0.8, 0.42, { in: neck, p: [0.2, 0.3, 0], r: [0, 0, -40], c });
  tk.box(0.12, 0.72, 0.16, { in: neck, p: [0.0, 0.42, 0], r: [0, 0, -40], c: dark });
  const head = tk.group({ in: neck, p: [0.5, 0.62, 0] });
  tk.box(0.74, 0.36, 0.34, { in: head, p: [0.22, 0, 0], r: [0, 0, -20], c });
  tk.box(0.2, 0.2, 0.36, { in: head, p: [0.52, -0.12, 0], r: [0, 0, -20], c: '#c9a57e' });
  for (const sz of [-1, 1]) { tk.cone(0.07, 0.2, { in: head, p: [-0.06, 0.26, sz * 0.11], c: dark }, 6); tk.sphere(0.045, { in: head, p: [0.18, 0.08, sz * 0.175], c: '#1d1b33' }, 8); }
  tk.box(0.14, 0.85, 0.14, { in: g, p: [-0.98, 1.05, 0], r: [0, 0, -16], c: dark });
  tk.box(0.72, 0.12, 0.66, { in: g, p: [-0.05, 1.66, 0], c: '#b33f3a' });
  const legs = [];
  for (const [x, z, ph] of [[0.62, 0.2, 0], [0.62, -0.2, 0.5], [-0.62, 0.2, 0.5], [-0.62, -0.2, 0]]) {
    const leg = tk.group({ in: g, p: [x, 1.0, z] });
    tk.cyl(0.1, 0.075, 0.9, { in: leg, p: [0, -0.45, 0], c }, 8);
    tk.box(0.2, 0.12, 0.2, { in: leg, p: [0, -0.94, 0], c: dark });
    legs.push({ leg, ph, front: x > 0 });
  }
  return {
    outer, g, head, neck,
    walk: (ph) => legs.forEach((l) => { l.leg.rotation.z = 0.45 * Math.sin(2 * Math.PI * (ph + l.ph)); }),
    kick: (ph) => legs.forEach((l) => { l.leg.rotation.z = l.front ? 0.5 * Math.sin(2 * Math.PI * (ph + l.ph)) - 0.4 * Math.min(1, ph) : 0; }),
  };
}

/** Put a puppet in the saddle; it follows the horse wherever the horse goes (and rears with it). */
function rider(tk, H, lookName, o = {}) {
  const a = tk.actor('rider-' + lookName, lookName, { p: [0, 0, 0], pose: 'sit', face: 'right', ...o });
  a.offset(() => {
    const th = H.outer.rotation.z, c = Math.cos(th), s = Math.sin(th), vx = 0.55, vy = 0.98;
    return [H.outer.position.x + vx * c - vy * s, H.outer.position.y + vx * s + vy * c, H.outer.position.z + 0.34, THREE.MathUtils.radToDeg(th)];
  });
  return a;
}

function swingSet(tk) {
  tk.exposure = 1.0; tk.tint.set('#ffe9d2');
  tk.sky('#4f4596', '#ffb070', { near: 50, far: 260, mid: 0.62 });
  tk.sun({ c: '#ffc98f', i: 3.1, dir: [-9, 4.5, 5], area: 16 });
  tk.hemi('#ffd6b0', '#6a4a3a', 0.95);
  tk.ground({ c: '#86ad4c', c2: '#5d8a3a' });
  tk.glow([-70, 16, -150], 34, '#fff0c0', 0.95);
  for (const [x, z, s] of [[-50, -110, 1.2], [60, -130, 1.6], [0, -160, 2]]) tk.sphere(30 * s, { p: [x, -7, z], s: [1.7, 0.5, 1], c: '#5d8a3a', cast: false }, 18);
  tree(tk, -6.5, -6, 1.6, '#4f8a3a'); tree(tk, 7.5, -9, 2.0, '#5d8a3a'); tree(tk, -11, -14, 1.3, '#3f7a3a'); tree(tk, 4.2, -4.5, 0.8, '#6f9a44');
  tk.scatter('blade', 900, { x: [-9, 9], z: [-8, 6] }, { c: ['#86ad4c', '#6f9a44', '#a3c860'], s: [0.06, 0.13] });
  tk.scatter('pebble', 40, { x: [-1.6, 1.6], z: [-0.8, 0.8] }, { c: ['#b59a6f', '#a08a5f'], s: [0.04, 0.09] });
  const wood = { c: '#b0503c' };
  for (const sz of [-1, 1]) for (const sx of [-1, 1]) tk.cyl(0.07, 0.08, 3.35, { p: [sx * 0.75, 1.55, sz * 1.05], r: [0, 0, sx * -13], ...wood }, 8);
  tk.cyl(0.07, 0.07, 2.3, { p: [0, 3.1, 0], r: [90, 0, 0], ...wood }, 8);
  const pivot = tk.group({ p: [0, 3.1, 0] });
  for (const sz of [-1, 1]) tk.cyl(0.02, 0.02, 2.1, { in: pivot, p: [0, -1.05, sz * 0.26], c: '#e9d2a6' }, 6);
  tk.box(0.5, 0.06, 0.62, { in: pivot, p: [0, -2.1, 0], c: '#e9d2a6' });
  tk.motes({ x: [-4, 4], y: [0.4, 3.6], z: [-2, 3] }, 50, { c: '#ffe9b0', opacity: 0.6 });
  return { pivot, L: 2.1 };
}

const takes = [];
const T = (id, start, join, build) => takes.push({ id, start, join, build });

// 1 ─ hook: the action, in frame 0
T('hook', 0, 'start', (tk) => {
  bridge(tk, { mood: 'day' });
  const tArmy = tk.word(/^army/i, 1, -0.1), tOut = tk.word(/^walk/i, 1, -0.1);
  tk.actor('keeper', 'keeper', { p: [-18.0, 0, 0], pose: 'stop', expr: 'determined', face: 'left' });
  column(tk, null, { rows: 12, head: () => -20.05, state: (t, v) => (t < tOut ? { pose: 'stand', expr: v > 0.5 ? 'worried' : 'neutral' } : { phase: (t - tOut) * 1.7, gait: 'shuffle', spread: true, expr: 'worried' }) });
  const H = horse(tk, [-23.4, 0, 2.3]);
  rider(tk, H, 'colonel', { expr: 'angry' });
  tk.cam([
    { t: 0, pos: [-19.2, 1.55, 9.2], look: [-19.3, 1.15, 0], push: 0.05 },
    { t: tArmy, move: 0.6, pos: [-32, 8.5, 12], look: [-23, 0.6, 0], fov: 40, push: 0.03, orbit: 3 },
    { t: tOut, move: 0.5, pos: [-20.3, 0.95, 3.7], look: [-21.3, 0.85, 0], push: 0.04, orbit: 2 },
  ]);
  tk.sfx('stomp', 0.05, { gain: -14 }); tk.sfx('drum', 0.3, { gain: -22 }); tk.sfx('neigh', 0.9, { gain: -30 });
  tk.sfx('whoosh', tArmy, { gain: -27 });
  tk.sfx('steps', tOut + 0.3, { dur: tk.e(0) - tOut - 0.3, every: 0.23, gain: -27 });
  tk.ambience('river', { gain: -46 });
});

// 2 ─ who he is, why the bridge matters
T('keeper', (tk) => tk.s(1), 'cut', (tk) => {
  bridge(tk, { mood: 'day' });
  const a = tk.s(1), tKeeper = tk.word(/^bridge/i, 2, -0.2), tOnly = tk.word(/^only/i, 1, -0.15);
  tk.actor('keeper', 'keeper', { p: [-17.4, 0, -3.2], pose: 'carry', expr: 'happy', face: 'right', item: 'lantern' }).key(tKeeper + 1.0, { pose: 'hips', item: null, blend: 0.25 });
  tk.cam([
    { t: a, pos: [-9, 15, 34], look: [0, 0.5, 0], fov: 42, orbit: 5, push: 0.02 },
    { t: tKeeper, move: 0.8, pos: [-15.9, 1.45, 1.9], look: [-17.45, 1.15, -3.2], push: 0.05 },
    { t: tOnly, move: 0.9, pos: [-46, 44, 70], look: [0, -6, 0], fov: 42, push: -0.03, orbit: -3 },
  ]);
  tk.sfx('whoosh', tKeeper, { gain: -26, down: true }); tk.sfx('squeak', tKeeper + 0.9, { gain: -30 }); tk.sfx('riser', tOnly - 0.1, { dur: 0.9, gain: -30 });
  tk.sfx('ding', tk.word(/^fifty/i, 1), { gain: -30, f: 1175 });
  tk.ambience('river', { gain: -42 }); tk.ambience('wind', { gain: -46 });
});

// 3 ─ the chains
T('chains', (tk) => tk.s(2, 0.17), 'dissolve', (tk) => {
  bridge(tk, { mood: 'day', links: true });
  const a = tk.s(2), tOil = tk.word(/^oils/i, 1, -0.15);
  tk.actor('keeper', 'keeper', { p: [-0.95, 0, 2.05], pose: 'hold', expr: 'happy', face: 'right', item: 'cup' })
    .key(tOil + 0.1, { pose: 'pointDown', blend: 0.18 }).key(tOil + 0.6, { pose: 'hold', blend: 0.18 }).key(tOil + 1.05, { pose: 'pointDown', blend: 0.18 });
  tk.cam([
    { t: a - 1, pos: [9, 9.6, 12.5], look: [13.5, 7.3, 2.9], push: 0.03, orbit: -4 },
    { t: tOil - 0.3, move: 0.75, pos: [1.7, 1.8, 6.7], look: [-0.45, 1.2, 2.5], push: 0.06 },
  ]);
  tk.sfx('chain', a + 0.55, { gain: -30 }); tk.sfx('whoosh', tOil - 0.3, { gain: -29, down: true });
  tk.sfx('squeak', tOil + 0.2, { gain: -28 }); tk.sfx('chain', tOil + 0.75, { gain: -32 }); tk.sfx('squeak', tOil + 1.15, { gain: -28, f: 2500 });
  tk.ambience('river', { gain: -46 });
});

// 4 ─ the army arrives, he plants himself in the road
T('army', (tk) => tk.s(3, 0.17), 'dissolve', (tk) => {
  bridge(tk, { mood: 'day' });
  const a = tk.s(3), e = tk.e(3), v = 1.24, tPlant = tk.word(/^plants/i, 1, -0.45), head = (t) => -43 + v * (t - a);
  column(tk, null, { rows: 12, head, state: (t) => ({ phase: (t - a) / (2 * BEAT), gait: 'march' }) });
  const H = horse(tk, [0, 0, 2.3]);
  tk.every((t) => { H.outer.position.x = head(t) + 1.2; H.walk((t - a) / (2 * BEAT)); });
  rider(tk, H, 'colonel', { expr: 'smug' });
  tk.actor('keeper', 'keeper', { p: [-18.7, 0, -3.4], pose: 'stand', expr: 'determined', face: 'left' })
    .walk(tPlant, tPlant + 0.9, [-18.0, 0]).key(tPlant + 0.9, { pose: 'stop', face: 'left', blend: 0.16 });
  tk.cam([
    { t: a - 1, pos: [-33.6, 0.75, 3.1], look: [-38.6, 1.15, 0], push: 0.02 },
    { t: tPlant - 0.15, move: 0.6, pos: [-15.3, 1.45, 4.7], look: [-18.2, 1.1, 0], push: 0.04 },
  ]);
  tk.sfx('march', a, { dur: tPlant - a, every: BEAT, gain: -31 }); tk.sfx('drums', a, { dur: tPlant - a, every: BEAT, gain: -33 });
  tk.sfx('whoosh', tPlant - 0.15, { gain: -28 }); tk.sfx('step', tPlant + 0.3, { gain: -26 }); tk.sfx('step', tPlant + 0.6, { gain: -26 });
  tk.sfx('thud', tPlant + 0.92, { gain: -17 });
  tk.puff({ t: tPlant + 0.92, p: [-18.0, 0.05, 0.3], n: 12, size: 0.3, c: '#d9c3a0', up: 0.7, speed: 1.1, life: 0.5 });
});

// 5 ─ the colonel
T('colonel', (tk) => tk.s(4, 0.17), 'dissolve', (tk) => {
  bridge(tk, { mood: 'day' });
  const a = tk.s(4), tShout = tk.s(5), eShout = tk.e(5);
  const H = horse(tk, [-21.6, 0, 1.2]);
  rider(tk, H, 'colonel', { expr: 'angry' }).key(tShout - 0.05, { expr: 'shout', pose: { ...POSES.sit, aF: [150, 10], lean: 8 }, blend: 0.14 });
  tk.every((t) => { H.head.rotation.z = 0.12 * Math.sin(5 * t); });
  column(tk, null, { rows: 8, head: () => -24.3, state: () => ({ pose: 'stand' }) });
  tk.cam([
    { t: a - 1, pos: [-19.2, 0.75, 4.5], look: [-21.2, 1.95, 1.45], push: 0.04 },
    { t: tShout - 0.2, move: 0.4, pos: [-20.25, 2.5, 3.75], look: [-21.1, 2.45, 1.54], push: 0.07, shake: { from: tShout, to: eShout, amp: 0.03, freq: 31 } },
  ]);
  for (let k = 0; k < 4; k++) tk.puff({ t: tShout + 0.1 + k * 0.42, p: [-21.05, 3.15, 1.56], n: 7, size: 0.26, c: '#ffffff', up: 1.5, speed: 0.5, life: 0.55, g: 0.6, seed: k });
  tk.sfx('neigh', a + 0.15, { gain: -27 }); tk.sfx('thud', a + 0.9, { gain: -27 }); tk.sfx('swish', tShout - 0.2, { gain: -27 });
  tk.sfx('boom', tShout + 0.05, { gain: -19 }); tk.sfx('pop', tShout + 0.55, { gain: -28 }); tk.sfx('pop', tShout + 0.97, { gain: -28, f: 620 });
});

// 6 ─ he won't move
T('wontmove', (tk) => tk.s(6), 'cut', (tk) => {
  bridge(tk, { mood: 'day' });
  const a = tk.s(6), tLine = tk.s(7), tSwim = tk.word(/^swim/i, 1, -0.3);
  tk.actor('keeper', 'keeper', { p: [-18.0, 0, 0], pose: 'hips', expr: 'determined', face: 'left' })
    .key(tLine, { pose: 'shrug', expr: 'smug', blend: 0.2 }).key(tSwim, { pose: 'pointDown', face: 'right', blend: 0.15 });
  tk.cam([
    { t: a - 1, pos: [-19.35, 1.5, 3.3], look: [-18.05, 1.3, 0], push: 0.05 },
    { t: tSwim + 0.05, move: 0.6, pos: [-13.2, 3.0, 5.5], look: [-7, -10, 0], fov: 40, push: 0.05 },
  ]);
  tk.sfx('thud', a + 0.1, { gain: -24 }); tk.sfx('pop', tLine + 0.05, { gain: -29 }); tk.sfx('whoosh', tSwim + 0.05, { gain: -25, down: true });
  tk.sfx('splash', tSwim + 0.75, { gain: -29 });
  tk.ambience('river', { gain: -40 });
});

// 7 ─ the colonel laughs; drums
T('drums', (tk) => tk.s(8, 0.17), 'dissolve', (tk) => {
  bridge(tk, { mood: 'day' });
  const a = tk.s(8), e = tk.e(8), tDrum = tk.word(/^orders/i, 1, -0.05);
  const H = horse(tk, [-21.6, 0, 1.2]);
  rider(tk, H, 'colonel', { expr: 'laugh', pose: { ...POSES.sit, aF: [40, -100], head: -12, lean: -6 } }).key(tDrum, { expr: 'smug', pose: { ...POSES.sit, aF: [96, 0] }, blend: 0.15 });
  tk.every((t) => { H.outer.position.y = t < tDrum ? 0.05 * Math.abs(Math.sin(9 * (t - a))) : 0; });
  tk.crowd(['drummer'], 3, (i) => [-24.4 - (i % 2) * 0.25, 0, (i - 1) * 1.15], { variants: 1, state: (t) => { const s = Math.sin(Math.PI * 4 * (t - a) / BEAT); return { pose: { ...POSES.stand, aF: [62 + 26 * s, -70], aB: [50 - 26 * s, -60] }, item: 'drum', expr: 'determined' }; } });
  column(tk, null, { rows: 8, head: () => -26.0, state: () => ({ pose: 'stand' }) });
  tk.cam([
    { t: a - 1, pos: [-19.5, 2.3, 4.8], look: [-21.15, 2.2, 1.5], push: 0.04 },
    { t: tDrum + 0.2, move: 0.5, pos: [-22.3, 1.25, 4.1], look: [-24.4, 1.0, 0.2], push: 0.06 },
  ]);
  for (let k = 0; k < 3; k++) tk.sfx('pop', a + 0.15 + k * 0.33, { gain: -27, f: 440 + 60 * k });
  tk.sfx('swish', tDrum + 0.2, { gain: -27 }); tk.sfx('drums', tDrum + 0.45, { dur: e - tDrum - 0.3, every: BEAT / 2, gain: -22 });
});

// 8 ─ six hundred boots, one instant
T('boots', (tk) => tk.s(9, 0.17), 'dissolve', (tk) => {
  const a = tk.s(9), e = tk.e(9), v = 1.24, head = (t) => -6.5 + v * (t - a);
  const B = bridge(tk, { mood: 'day', amp: () => 0.03 });
  column(tk, B, { rows: 12, head, state: (t) => ({ phase: (t - a) / (2 * BEAT), gait: 'march' }) });
  tk.cam([
    { t: a - 1, pos: [-6.6, 0.45, 5.8], look: [-8.6, 0.5, 0], fov: 30, push: 0.03, drift: [v * 0.6, 0, 0] },
    { t: tk.word(/^exact/i, 1, -0.25), move: 0.6, pos: [5.5, 6.5, 9.5], look: [-3.5, 0.6, 0], push: 0.05 },
  ]);
  for (let k = 0; a + k * BEAT < e + 0.2; k++) {
    const t = a + k * BEAT;
    tk.sfx('stomp', t, { gain: -19 });
    tk.puff({ t, p: [head(t) - 2.2, 0.05, 1.7], n: 8, size: 0.3, c: '#d9c3a0', up: 0.6, speed: 0.8, life: 0.42, seed: k });
  }
  tk.sfx('whoosh', tk.word(/^exact/i, 1, -0.25), { gain: -28 });
});

// 9 ─ first sign, second sign
T('lantern', (tk) => tk.s(10, 0.17), 'dissolve', (tk) => {
  const a = tk.s(10), tPl = tk.s(11), e = tk.e(11), v = 1.24, head = (t) => -2.5 + v * (t - a);
  const sw = (t) => ramp(t, a, tPl, 0.05, 0.55) * Math.sin(Math.PI * (t - a) / BEAT);
  const B = bridge(tk, { mood: 'day', amp: (t) => ramp(t, a, e, 0.05, 0.42), lantern: sw });
  column(tk, B, { rows: 12, head, state: (t) => ({ phase: (t - a) / (2 * BEAT), gait: 'march' }) });
  tk.actor('keeper', 'keeper', { p: [-16.25, 0, 3.9], pose: 'hips', expr: 'bored', face: 'right' }).key(a + 1.3, { expr: 'smug' });
  tk.cam([
    { t: a - 1, pos: [-13.6, 2.2, 9.9], look: [-15.5, 1.75, 3.6], push: 0.05 },
    { t: tPl - 0.15, move: 0.5, pos: [2.5, 1.3, 6.2], look: [-1.5, 0.5, 0], push: 0.04, shake: { from: tPl, to: e + 0.3, amp: 0.02, freq: 12 } },
  ]);
  for (let k = 0; a + 0.5 + k * 2 * BEAT < tPl; k++) tk.sfx('squeak', a + 0.5 + k * 2 * BEAT, { gain: -30 + 2 * k, f: 1900 + 80 * k });
  tk.sfx('march', a, { dur: e - a, every: BEAT, gain: -33 });
  tk.sfx('swish', tPl - 0.15, { gain: -27 }); tk.sfx('creak', tPl + 0.15, { gain: -22 }); tk.sfx('creak', tPl + 0.8, { gain: -21, f: 110 });
});

// 10 ─ third sign; the question
T('horse', (tk) => tk.s(12, 0.17), 'dissolve', (tk) => {
  const a = tk.s(12), tRef = tk.word(/^refuses/i, 1, -0.12), tQ = tk.s(13), e = tk.e(13);
  const B = bridge(tk, { mood: 'storm', amp: (t) => ramp(t, a, e, 0.42, 0.6) });
  column(tk, B, { rows: 12, head: () => 0.2, state: (t) => ({ phase: (t - a) / (2 * BEAT), gait: 'march', expr: 'worried' }) });
  const H = horse(tk, [2.2, 0, 0.9]);
  const rear = (t) => (t < tRef ? 0 : 0.42 * Math.sin(Math.min(1, (t - tRef) / 0.35) * Math.PI / 2) * (0.85 + 0.15 * Math.sin(14 * (t - tRef))));
  tk.every((t) => { H.outer.position.y = B.yAt(1.6, t); H.outer.rotation.z = rear(t); H.kick(t < tRef ? 0 : (t - tRef) * 3); });
  rider(tk, H, 'colonel', { expr: 'worried' }).key(tRef, { expr: 'shock', pose: { ...POSES.sit, aF: [160, 20], aB: [150, 20] }, blend: 0.12 });
  tk.cam([
    { t: a - 1, pos: [5.4, 1.9, 7.6], look: [2.4, 1.9, 0.9], push: 0.04, shake: { from: tRef, to: tQ, amp: 0.03, freq: 19 } },
    { t: tQ - 0.1, move: 0.8, pos: [8, 5, 52], look: [0, 1.5, 0], fov: 38, push: 0.02 },
  ]);
  tk.sfx('creak', a + 0.2, { gain: -24 }); tk.sfx('neigh', tRef, { gain: -15 }); tk.sfx('thud', tRef + 0.35, { gain: -20 }); tk.sfx('thud', tRef + 0.6, { gain: -22 });
  tk.sfx('rumble', a, { dur: e - a, gain: -34 }); tk.sfx('whoosh', tQ - 0.1, { gain: -24, dur: 0.8 }); tk.sfx('ding', tQ + 0.75, { gain: -27, f: 880 });
});

// 11 ─ the explainer: a swing
T('swing', (tk) => tk.s(14, 0.17), 'dissolve', (tk) => {
  const a = tk.s(14), tSame = tk.word(/^same/i, 2, -0.25), tFly = tk.word(/^flies/i, 1, -0.4), e = tk.e(15), f = 0.95;
  const S = swingSet(tk);
  const th = (t) => (ramp(t, a, tSame, 0.11, 0.16) + ramp(t, tSame, e, 0, 1.0)) * Math.sin(2 * Math.PI * f * (t - a));
  tk.every((t) => { S.pivot.rotation.z = th(t); });
  tk.actor('kid', 'kid', { p: [0, 3.1 - S.L - 0.4, 0.05], height: 1.12, pose: 'sit', expr: 'happy', face: 'right' })
    .offset((t) => [S.L * Math.sin(th(t)), S.L * (1 - Math.cos(th(t))), 0, THREE.MathUtils.radToDeg(th(t))])
    .key(tSame, { expr: 'grin' }).key(tFly, { expr: 'laugh', pose: { ...POSES.sit, aF: [150, 0], aB: [140, 0] }, blend: 0.15 });
  const parent = tk.actor('parent', 'parent', { p: [-1.85, 0, 0.35], pose: 'stand', expr: 'happy', face: 'right' });
  for (let k = 0; ; k++) {
    const t = a + (0.75 + k) / f;
    if (t > e) break;
    parent.key(t - 0.14, { pose: 'push', blend: 0.1 }).key(t + 0.22, { pose: 'stand', blend: 0.2 });
    tk.sfx('swish', t + 0.12, { gain: -29 });
    if (t >= tSame - 0.3) { tk.ring({ t, p: [-0.95, 1.15, 0.4], upright: true, r0: 0.15, r1: 0.9 + 0.15 * k, life: 0.4, c: '#fff0a8' }); tk.sfx('pop', t, { gain: -25, f: 392 * 2 ** (k / 6) }); }
  }
  tk.cam([
    { t: a - 1, pos: [0.9, 1.7, 9.4], look: [0.1, 1.55, 0], push: 0.04 },
    { t: tFly, move: 0.5, pos: [3.6, 0.6, 5.9], look: [1.2, 2.7, 0], push: 0.03 },
  ]);
  tk.sfx('ding', tFly + 0.42, { gain: -22, f: 1568 }); tk.sfx('whoosh', tFly, { gain: -27 });
  tk.ambience('wind', { gain: -47 });
});

// 12 ─ the explainer, on the bridge: pushes on the beat
T('pulse', (tk) => tk.s(16, 0.17), 'dissolve', (tk) => {
  const a = tk.s(16), e = tk.e(16), tGiant = tk.word(/^giant/i, 1, -0.3);
  const B = bridge(tk, { mood: 'storm', amp: (t) => ramp(t, a, e, 0.3, 0.75) });
  column(tk, B, { rows: 12, head: () => 3.0, state: (t) => ({ phase: (t - a) / (2 * BEAT), gait: 'march' }) });
  for (let k = 0; a + k * BEAT < e + 0.3; k++) {
    const t = a + k * BEAT;
    for (const x of [-8.5, -4.5, -0.5, 3.5]) tk.ring({ t, p: [x, 0.5, 2.6], upright: true, r0: 0.3, r1: 2.3 + 0.15 * k, life: 0.42, c: '#ffd76a' });
    tk.sfx('blip', t, { gain: -29 + 0.8 * k, f: 392 * 2 ** (k / 12) });
  }
  tk.cam([
    { t: a - 1, pos: [-5, 3.4, 25], look: [-2, 0.9, 0], fov: 38, push: 0.03 },
    { t: tGiant, move: 0.7, pos: [3.5, 1.5, 10.5], look: [-1.5, 0.7, 0], push: 0.05 },
  ]);
  tk.sfx('whoosh', tGiant, { gain: -27 }); tk.sfx('rumble', a, { dur: e - a, gain: -36 }); tk.sfx('creak', e - 0.6, { gain: -24 });
});

// 13 ─ higher and higher, until the chain goes
T('heave', (tk) => tk.s(17, 0.17), 'dissolve', (tk) => {
  const a = tk.s(17), tChain = tk.word(/^chain/i, 2, -0.3), tSnap = tk.word(/^snaps/i, 1, 0.1);
  const B = bridge(tk, { mood: 'storm', links: true, amp: (t) => ramp(t, a, tSnap, 0.75, 1.15) });
  column(tk, B, { rows: 12, head: () => 4.0, state: (t) => ({ phase: (t - a) / (2 * BEAT), gait: 'march', expr: 'worried' }) });
  B.links[5].material.emissive.set('#ff5a1f');
  const flash = tk.glow([0, 1.1, 2.9], 3.2, '#fff2c0', 0);
  tk.every((t) => {
    const u = ramp(t, tChain, tSnap, 0, 1);
    B.links.forEach((l, i) => { l.scale.x = 1 + (i === 5 ? 0.55 : 0.12) * u; l.position.y = l.userData.y + 0.02 * Math.sin(60 * t) * u; });
    B.links[5].material.emissiveIntensity = 1.6 * u * u;
    flash.material.opacity = t >= tSnap ? Math.max(0, 1 - (t - tSnap) / 0.16) : 0;
  });
  tk.cam([
    { t: a - 1, pos: [-9, 2.4, 9.6], look: [-2, 0.8, 0], push: 0.03, shake: { from: a, to: tSnap, amp: 0.025, freq: 9 } },
    { t: tChain, move: 0.6, pos: [1.9, 1.75, 6.3], look: [0, 1.12, 2.9], push: 0.09, shake: { from: tChain, to: tSnap + 0.3, amp: 0.02, freq: 23 } },
  ]);
  tk.puff({ t: tSnap, p: [0, 1.1, 2.9], n: 30, size: 0.16, c: '#ffd98a', speed: 4, up: 2, life: 0.4 });
  for (let k = 0; k < 3; k++) tk.sfx('creak', a + 0.4 + k * 1.0, { gain: -23 + 2 * k, f: 95 + 15 * k });
  tk.sfx('march', a, { dur: tChain - a, every: BEAT, gain: -31 });
  tk.sfx('swish', tChain, { gain: -27 }); tk.sfx('riser', tChain + 0.2, { dur: tSnap - tChain - 0.2, gain: -22 }); tk.sfx('snap', tSnap, { gain: -9 });
});

// 14 ─ the consequence
T('swim', (tk) => tk.word(/^snaps/i, 1, 0.26), 'cut', (tk) => {
  const t0 = tk.word(/^snaps/i, 1, 0.26), tDrums = tk.word(/^drums/i, 2, -0.2), tSplash = t0 + 1.5;
  const B = bridge(tk, { mood: 'storm', broken: true, collapse: t0 + 0.05, amp: () => 1.0 });
  column(tk, B, { rows: 12, head: () => 4.0, floor: -11.2, state: () => ({ pose: 'armsUp', expr: 'shock' }) });
  for (let k = 0; k < 7; k++) {
    const x = -9 + k * 2.6, t = tSplash + 0.035 * Math.abs(x - 1);
    tk.puff({ t, p: [x, -9.95, (k % 3 - 1) * 1.2], n: 22, size: 1.0, c: '#eaf6ff', up: 6, speed: 2.2, life: 0.95, g: -9, floor: -10, seed: k });
    if (k % 2 === 0) tk.sfx('splash', t, { gain: -15 - k });
  }
  const drum = tk.group({ p: [2, -9.9, 3.4] });
  tk.cyl(0.42, 0.42, 0.55, { in: drum, c: '#b33f3a', r: [70, 0, 20] }, 16);
  tk.every((t) => { drum.visible = t > tSplash + 0.2; drum.position.y = -9.86 + 0.07 * Math.sin(3 * t); drum.rotation.y = 0.4 * t; });
  tk.actor('keeper', 'keeper', { p: [-18.1, 0, 2.6], pose: 'hold', expr: 'bored', face: 'right', item: 'cup' });
  tk.cam([
    { t: t0 - 1, pos: [-10, 8, 34], look: [1, -1, 0], fov: 40, push: 0.03, shake: { from: t0, to: t0 + 0.5, amp: 0.05, freq: 21 } },
    { t: t0 + 0.95, move: 0.6, pos: [-9, -3.5, 26], look: [1.5, -9.6, 0], fov: 40, push: 0.04 },
    { t: tDrums, move: 0.5, pos: [-16.3, 1.5, 5.6], look: [-18.05, 1.3, 2.6], push: 0.05 },
  ]);
  tk.sfx('crash', t0 + 0.05, { gain: -12 }); tk.sfx('boom', t0 + 0.1, { gain: -16 }); tk.sfx('whoosh', t0 + 0.95, { gain: -26, down: true });
  tk.sfx('pop', tSplash + 0.7, { gain: -27, f: 300 }); tk.sfx('pop', tSplash + 0.95, { gain: -29, f: 360 });
  tk.sfx('swish', tDrums, { gain: -28 }); tk.sfx('sip', tDrums + 0.55, { gain: -24 });
  tk.ambience('river', { gain: -40 });
});

// 15 ─ which is why
T('epilogue', (tk) => tk.s(19, 0.17), 'dissolve', (tk) => {
  const a = tk.s(19), e = tk.e(19), tBreak = tk.word(/^break/i, 2, -0.25);
  const B = bridge(tk, { mood: 'morning' });
  tk.cyl(0.06, 0.07, 2.3, { p: [-15.2, 1.15, -3.35], c: '#6b4a2e' }, 8);
  tk.sign('BREAK\nSTEP', { p: [-15.2, 2.2, -3.3], w: 1.9, h: 1.25 });
  column(tk, B, { rows: 12, head: (t) => -13 + 0.9 * (t - a), state: (t) => ({ phase: (t - a) * 0.8, gait: 'shuffle', spread: true, expr: 'happy' }) });
  tk.actor('keeper', 'keeper', { p: [-16.8, 0, -2.4], pose: 'hold', item: 'cup', expr: 'happy', face: 'right' });
  tk.cam([
    { t: a - 1, pos: [-17.8, 1.7, 5.4], look: [-16.0, 1.5, -2.8], push: 0.04 },
    { t: tBreak, move: 0.8, pos: [-30, 8, 22], look: [-8, 1, 0], fov: 40, push: -0.03 },
  ]);
  tk.sfx('ding', a + 0.25, { gain: -23, f: 1568 }); tk.sfx('steps', a + 0.2, { dur: e - a - 0.2, every: 0.19, gain: -29 }); tk.sfx('whoosh', tBreak, { gain: -28 });
  tk.sfx('chime', e - 0.5, { gain: -24 });
  tk.ambience('river', { gain: -46 });
});

export default { cast, takes };
