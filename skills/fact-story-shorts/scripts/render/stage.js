// stage.js — scene kit for fact-story Shorts: flat 2D puppets inside lit 3D sets, rendered with three.js.
// Everything is a pure function of time, so frames can be rendered in any order and in parallel workers.
import * as THREE from './three.module.js';
import { CW, CH, FOOT, POSES, EXPR, gait, blendPose, drawActor } from './cast.js';

export const W = 1080, H = 1920, FPS = 30;
const FIG_PX = 703;                                   // feet to top of head in the puppet canvas
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const lerp = (a, b, u) => a + (b - a) * u;
const V = (a) => new THREE.Vector3(a[0], a[1], a[2]);
export const EASE = {
  linear: (u) => u,
  inOut: (u) => u * u * (3 - 2 * u),
  inOut3: (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2),
  out: (u) => 1 - Math.pow(1 - u, 3),
  in: (u) => u * u * u,
  back: (u) => { const c = 1.70158; return 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); },
};
export function rng(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export function hash(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
/** keys: [[t, value, ease?], ...] with number or array values */
export function track(keys, t, dflt = 'inOut') {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    if (t <= keys[i][0]) {
      const [t0, v0] = keys[i - 1], [t1, v1, e] = keys[i];
      const u = EASE[e || dflt]((t - t0) / Math.max(t1 - t0, 1e-6));
      return Array.isArray(v0) ? v0.map((a, k) => lerp(a, v1[k], u)) : lerp(v0, v1, u);
    }
  }
  return keys[keys.length - 1][1];
}

// ------------------------------------------------------------------ procedural textures
const texCache = new Map();
function surface(kind, c1, c2 = '#000000') {
  const key = `${kind}|${c1}|${c2}`;
  if (texCache.has(key)) return texCache.get(key);
  const cv = document.createElement('canvas');
  cv.width = cv.height = 256;
  const g = cv.getContext('2d'), r = rng(hash(key));
  g.fillStyle = c1; g.fillRect(0, 0, 256, 256);
  if (kind === 'mottle' || kind === 'grass' || kind === 'gravel') {
    const n = kind === 'gravel' ? 900 : 260;
    for (let i = 0; i < n; i++) {
      g.globalAlpha = kind === 'gravel' ? 0.35 + 0.4 * r() : 0.08 + 0.12 * r();
      g.fillStyle = r() < 0.6 ? c2 : (r() < 0.5 ? '#ffffff' : '#000000');
      const x = r() * 256, y = r() * 256, s = kind === 'gravel' ? 2 + r() * 5 : 8 + r() * 26;
      for (const [ox, oy] of [[0, 0], [256, 0], [-256, 0], [0, 256], [0, -256]]) { g.beginPath(); g.ellipse(x + ox, y + oy, s, s * (0.6 + 0.4 * r()), r() * 3, 0, 7); g.fill(); }
    }
  } else if (kind === 'checker') {
    g.fillStyle = c2; g.fillRect(0, 0, 128, 128); g.fillRect(128, 128, 128, 128);
  } else if (kind === 'planks') {
    for (let i = 0; i < 8; i++) { g.globalAlpha = 0.10 * r(); g.fillStyle = r() < 0.5 ? '#000' : '#fff'; g.fillRect(0, i * 32, 256, 32); g.globalAlpha = 0.55; g.fillStyle = c2; g.fillRect(0, i * 32, 256, 3); g.fillRect((i % 2) * 128 + 40, i * 32, 3, 32); }
  } else if (kind === 'stone') {
    for (let j = 0; j < 4; j++) for (let i = 0; i < 2; i++) { g.globalAlpha = 0.14 * r(); g.fillStyle = r() < 0.5 ? '#000' : '#fff'; const ox = (j % 2) * 64; g.fillRect(i * 128 + ox - 128, j * 64, 128, 64); g.fillRect(i * 128 + ox + 128, j * 64, 128, 64); g.fillRect(i * 128 + ox, j * 64, 128, 64); }
    g.globalAlpha = 0.6; g.fillStyle = c2;
    for (let j = 0; j < 4; j++) { g.fillRect(0, j * 64, 256, 4); const ox = (j % 2) * 64; g.fillRect(ox, j * 64, 4, 64); g.fillRect(ox + 128, j * 64, 4, 64); }
  } else if (kind === 'water') {
    for (let i = 0; i < 60; i++) { g.globalAlpha = 0.10 + 0.25 * r(); g.fillStyle = r() < 0.7 ? c2 : '#ffffff'; const y = r() * 256, x = r() * 256, w = 30 + r() * 90; for (const ox of [0, 256, -256]) g.fillRect(x + ox, y, w, 2 + r() * 3); }
  }
  const tex = new THREE.CanvasTexture(cv);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  texCache.set(key, tex);
  return tex;
}
function dotTex() {
  if (texCache.has('dot')) return texCache.get('dot');
  const cv = document.createElement('canvas'); cv.width = cv.height = 128;
  const g = cv.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,0.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; texCache.set('dot', tex);
  return tex;
}

// ------------------------------------------------------------------ actors
class Puppet {
  constructor(look) {
    this.look = look;
    this.canvas = document.createElement('canvas'); this.canvas.width = CW; this.canvas.height = CH;
    this.ctx = this.canvas.getContext('2d');
    this.tex = new THREE.CanvasTexture(this.canvas); this.tex.colorSpace = THREE.SRGBColorSpace; this.tex.anisotropy = 4;
    this.sig = '';
  }
  draw(st) {
    const p = st.pose;
    const sig = [st.exprName, st.facing, st.blink ? 1 : 0, st.item || '', (st.talk || 0).toFixed(1), ...['aF', 'aB', 'lF', 'lB'].flatMap((k) => p[k].map((v) => v.toFixed(0))), (p.lean || 0).toFixed(0), (p.head || 0).toFixed(0), (p.bob || 0).toFixed(0), (st.gaze || []).join(',')].join('|');
    if (sig === this.sig) return;
    this.sig = sig;
    drawActor(this.ctx, this.look, st);
    this.tex.needsUpdate = true;
  }
}
function puppetGeometry(height) {
  const s = height / FIG_PX, g = new THREE.PlaneGeometry(CW * s, CH * s);
  g.translate(0, (FOOT - CH / 2) * s, 0);
  return g;
}
function puppetMaterials(tex, tint) {
  const m = new THREE.MeshBasicMaterial({ map: tex, alphaTest: 0.5, side: THREE.DoubleSide, color: tint });
  m.alphaToCoverage = true;
  const d = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: tex, alphaTest: 0.5 });
  return [m, d];
}

class Actor {
  constructor(take, id, look, o = {}) {
    this.take = take; this.id = id; this.seed = (hash(take.id + id) % 1000) / 1000;
    this.puppet = new Puppet(look);
    this.height = o.height || 1.7;
    const [m, d] = puppetMaterials(this.puppet.tex, take.tint);
    this.mesh = new THREE.Mesh(puppetGeometry(this.height), m);
    this.mesh.customDepthMaterial = d; this.mesh.castShadow = o.cast !== false; this.mesh.renderOrder = 2;
    (o.in || take.scene).add(this.mesh);
    this.p0 = o.p || [0, 0, 0];
    this.keys = [{ t: -1e9, pose: o.pose || 'stand', expr: o.expr || 'neutral', face: o.face || 'right', item: o.item || null, gaze: o.gaze || null }];
    this.walks = []; this.offsets = []; this.says = [];
  }
  /** change pose / expression / facing / held item at time t (seconds) */
  key(t, k) { this.keys.push({ t, ...k }); this.keys.sort((a, b) => a.t - b.t); return this; }
  /** walk in a straight line; gait: walk | march | shuffle | run */
  walk(t0, t1, to, o = {}) { this.walks.push({ t0, t1, to, gait: o.gait || 'walk', step: o.step || 0.62, sfx: o.sfx }); this.walks.sort((a, b) => a.t0 - b.t0); return this; }
  /** extra offset: fn(t) -> [dx, dy, dz, rotZdeg?] (jump, shake, ride a swing ...) */
  offset(fn) { this.offsets.push(fn); return this; }
  say(t0, t1) { this.says.push([t0, t1]); return this; }
  at(t) {
    let p = this.p0.slice(), walking = null, from = this.p0;
    for (const w of this.walks) {
      if (t >= w.t1) { p = [w.to[0], p[1], w.to[1]]; from = p; continue; }
      if (t >= w.t0) { const u = (t - w.t0) / (w.t1 - w.t0); const a = [from[0], from[2]]; p = [lerp(a[0], w.to[0], u), p[1], lerp(a[1], w.to[1], u)]; walking = { w, dist: Math.hypot(w.to[0] - a[0], w.to[1] - a[1]) * u, dir: [w.to[0] - a[0], w.to[1] - a[1]] }; }
      break;
    }
    return { p, walking };
  }
  update(t, cam) {
    const { p, walking } = this.at(t);
    let cur = this.keys[0], prev = this.keys[0], st = { exprName: 'neutral', facing: 'right', item: null, gaze: null }, poseKey = null, prevPose = null;
    for (const k of this.keys) {
      if (k.t > t) break;
      if (k.pose) { prevPose = poseKey; poseKey = k; }
      if (k.expr) st.exprName = k.expr;
      if (k.face) st.facing = k.face;
      if (k.item !== undefined) st.item = k.item;
      if (k.gaze !== undefined) st.gaze = k.gaze;
    }
    let pose, stretch = 1;
    const get = (k) => (typeof k.pose === 'string' ? POSES[k.pose] : k.pose);
    if (walking) {
      pose = gait(walking.w.gait, walking.dist / (2 * walking.w.step), this.seed);
      const right = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 0);
      const d = walking.dir[0] * right.x + walking.dir[1] * right.z;
      st.facing = d >= 0 ? 'right' : 'left';
    } else {
      pose = get(poseKey);
      const u = clamp((t - poseKey.t) / (poseKey.blend || 0.2), 0, 1);
      if (prevPose && u < 1) { pose = blendPose(get(prevPose), pose, EASE.back(u)); stretch = 1 + 0.05 * Math.sin(u * Math.PI); }
    }
    st.pose = pose; st.expr = EXPR[st.exprName] || EXPR.neutral;
    const period = 2.8 + 1.6 * this.seed;
    st.blink = ((t + this.seed * 7) % period) < 0.1;
    st.talk = 0;
    this.puppet.draw(st);
    let off = [0, 0, 0, 0];
    for (const fn of this.offsets) { const o = fn(t); if (o) off = [off[0] + o[0], off[1] + o[1], off[2] + o[2], off[3] + (o[3] || 0)]; }
    this.mesh.position.set(p[0] + off[0], p[1] + off[1], p[2] + off[2]);
    this.mesh.rotation.set(0, Math.atan2(cam.position.x - this.mesh.position.x, cam.position.z - this.mesh.position.z), THREE.MathUtils.degToRad(off[3] + 0.5 * Math.sin(6.283 * (0.31 * t + this.seed))));
    this.mesh.scale.set(1, stretch * (1 + 0.012 * Math.sin(6.283 * (0.4 * t + this.seed))), 1);
    this.world = this.mesh.position;
  }
}

class Crowd {
  /** n puppets sharing `variants` textures. posFn(i, t) -> [x, y, z]; phaseFn(t, v) -> gait phase in cycles (or null = standing). */
  constructor(take, looks, n, posFn, o = {}) {
    this.take = take; this.n = n; this.posFn = posFn; this.o = o;
    const nv = o.variants || 1;
    this.variants = [];
    for (let v = 0; v < nv; v++) {
      const puppet = new Puppet(looks[v % looks.length]);
      const [m, d] = puppetMaterials(puppet.tex, take.tint);
      const idx = [...Array(n).keys()].filter((i) => i % nv === v);
      const mesh = new THREE.InstancedMesh(puppetGeometry(o.height || 1.7), m, idx.length);
      mesh.customDepthMaterial = d; mesh.castShadow = o.cast !== false; mesh.frustumCulled = false; mesh.renderOrder = 2;
      take.scene.add(mesh);
      this.variants.push({ puppet, mesh, idx, seed: v / nv });
    }
    this.m4 = new THREE.Matrix4(); this.q = new THREE.Quaternion(); this.s = new THREE.Vector3(1, 1, 1); this.pv = new THREE.Vector3();
  }
  update(t, cam) {
    const o = this.o;
    for (const va of this.variants) {
      const st = typeof o.state === 'function' ? o.state(t, va.seed) : (o.state || {});
      const ph = st.phase;
      const pose = ph == null ? (typeof st.pose === 'object' ? st.pose : POSES[st.pose || 'stand']) : gait(st.gait || 'march', ph + (st.spread ? va.seed : 0), va.seed);
      va.puppet.draw({ pose, exprName: st.expr || 'neutral', expr: EXPR[st.expr || 'neutral'], facing: st.face || 'right', item: st.item || null, blink: false, talk: 0 });
      va.idx.forEach((i, k) => {
        const p = this.posFn(i, t);
        this.pv.set(p[0], p[1], p[2]);
        this.q.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, Math.atan2(cam.position.x - p[0], cam.position.z - p[2]));
        this.m4.compose(this.pv, this.q, this.s);
        va.mesh.setMatrixAt(k, this.m4);
      });
      va.mesh.instanceMatrix.needsUpdate = true;
    }
  }
}

// ------------------------------------------------------------------ one continuous take
export class Take {
  constructor(stage, spec, start, end) {
    this.stage = stage; this.id = spec.id; this.start = start; this.end = end;
    this.join = spec.join || 'dissolve'; this.joinFrames = spec.joinFrames ?? stage.style.dissolveFrames;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(35, W / H, 0.1, 900);
    this.tint = new THREE.Color(spec.tint || '#ffffff');
    this.updaters = []; this.actors = []; this.crowds = []; this.shots = []; this.exposure = spec.exposure || 1;
    this.r = rng(hash(spec.id));
  }
  // ---- time helpers
  s(i, off = 0) { return this.stage.sentences[i].start + off; }
  e(i, off = 0) { return this.stage.sentences[i].end + off; }
  word(re, nth = 1, off = 0) { let k = 0; for (const w of this.stage.words) if (re.test(w.text) && ++k === nth) return w.start + off; throw new Error(`word ${re} #${nth} not found`); }
  // ---- generic helpers
  mat(o = {}) {
    const m = new THREE.MeshStandardMaterial({ color: o.c || '#888888', roughness: o.rough ?? 0.9, metalness: o.metal ?? 0, flatShading: !!o.flat });
    if (o.emissive) { m.emissive = new THREE.Color(o.emissive); m.emissiveIntensity = o.glowI ?? 1; }
    if (o.opacity != null && o.opacity < 1) { m.transparent = true; m.opacity = o.opacity; m.depthWrite = false; }
    if (o.tex) { m.map = surface(o.tex, o.c, o.c2).clone(); m.map.needsUpdate = true; m.map.repeat.set(...(o.rep || [1, 1])); m.color.set('#ffffff'); }
    if (o.double) m.side = THREE.DoubleSide;
    return m;
  }
  add(geom, o = {}) {
    const mesh = new THREE.Mesh(geom, o.material || this.mat(o));
    if (o.p) mesh.position.set(...o.p);
    if (o.r) mesh.rotation.set(...o.r.map(THREE.MathUtils.degToRad));
    if (o.s) mesh.scale.set(...(Array.isArray(o.s) ? o.s : [o.s, o.s, o.s]));
    mesh.castShadow = o.cast !== false; mesh.receiveShadow = o.receive !== false;
    (o.in || this.scene).add(mesh);
    return mesh;
  }
  group(o = {}) { const g = new THREE.Group(); if (o.p) g.position.set(...o.p); if (o.r) g.rotation.set(...o.r.map(THREE.MathUtils.degToRad)); (o.in || this.scene).add(g); return g; }
  box(w, h, d, o) { return this.add(new THREE.BoxGeometry(w, h, d), o); }
  cyl(r1, r2, h, o, seg = 20) { return this.add(new THREE.CylinderGeometry(r1, r2, h, seg), o); }
  sphere(r, o, seg = 20) { return this.add(new THREE.SphereGeometry(r, seg, Math.max(8, seg * 0.7 | 0)), o); }
  cone(r, h, o, seg = 16) { return this.add(new THREE.ConeGeometry(r, h, seg), o); }
  plane(w, h, o) { return this.add(new THREE.PlaneGeometry(w, h), { double: true, ...o }); }
  tube(points, radius, o, seg = 40) { return this.add(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map(V)), seg, radius, 8, false), o); }
  // ---- environment
  sky(top, bottom, o = {}) {
    const cv = document.createElement('canvas'); cv.width = 4; cv.height = 256;
    const g = cv.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, 256);
    gr.addColorStop(0, top); gr.addColorStop(o.mid ?? 0.52, bottom); gr.addColorStop(1, bottom);
    g.fillStyle = gr; g.fillRect(0, 0, 4, 256);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    const dome = new THREE.Mesh(new THREE.SphereGeometry(700, 24, 16), new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, fog: false, depthWrite: false }));
    dome.renderOrder = -10; this.scene.add(dome);
    this.updaters.push(() => dome.position.copy(this.camera.position));
    if (o.fog !== false) this.fog(o.fogColor || bottom, o.near ?? 40, o.far ?? 260);
    return dome;
  }
  fog(c, near, far) { this.scene.fog = new THREE.Fog(c, near, far); }
  sun(o = {}) {
    const l = new THREE.DirectionalLight(o.c || '#fff1d6', o.i ?? 3);
    const dir = V(o.dir || [4, 8, 3]).normalize(), area = o.area || 30;
    l.castShadow = true; l.shadow.mapSize.set(o.map || 2048, o.map || 2048);
    Object.assign(l.shadow.camera, { left: -area, right: area, top: area, bottom: -area, near: 1, far: 260 });
    l.shadow.bias = -0.0005; l.shadow.normalBias = 0.04; l.shadow.radius = o.soft ?? 3;
    this.scene.add(l, l.target);
    const focus = o.focus ? V(o.focus) : null;
    this.updaters.push(() => { const f = focus || this.look; l.target.position.copy(f); l.position.copy(f).addScaledVector(dir, 110); });
    return l;
  }
  hemi(sky = '#cfe3ff', ground = '#8a6a4a', i = 1) { const l = new THREE.HemisphereLight(sky, ground, i); this.scene.add(l); return l; }
  lamp(p, c = '#ffd27a', i = 40, dist = 14, o = {}) {
    const l = new THREE.PointLight(c, i, dist, 2); l.position.set(...p); (o.in || this.scene).add(l);
    if (o.glow) l.add(this.glow([0, 0, 0], o.glow, c, o.glowOpacity ?? 0.7, { in: l }));
    return l;
  }
  glow(p, radius, c = '#ffe9a8', opacity = 0.7, o = {}) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTex(), color: c, blending: THREE.AdditiveBlending, depthWrite: false, fog: false, opacity, transparent: true }));
    s.scale.set(radius * 2, radius * 2, 1); s.position.set(...p); s.renderOrder = 5; (o.in || this.scene).add(s); return s;
  }
  beam(p, r, length, radius, c = '#fff2c4', opacity = 0.16) {
    const g = new THREE.ConeGeometry(radius, length, 24, 1, true); g.translate(0, -length / 2, 0);
    const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, fog: false }));
    m.position.set(...p); m.rotation.set(...r.map(THREE.MathUtils.degToRad)); m.renderOrder = 4; this.scene.add(m); return m;
  }
  ground(o = {}) {
    const size = o.size || 500;
    return this.add(new THREE.PlaneGeometry(size, size), { c: o.c || '#6f9a4a', c2: o.c2 || '#4f7a34', tex: o.tex || 'mottle', rep: [size / (o.tile || 6), size / (o.tile || 6)], r: [-90, 0, 0], p: [o.x || 0, o.y || 0, o.z || 0], cast: false, rough: o.rough ?? 1 });
  }
  water(o = {}) {
    const size = o.size || 500, m = this.add(new THREE.PlaneGeometry(size, o.depth || size), { c: o.c || '#2f6f9a', c2: o.c2 || '#9fd4ee', tex: 'water', rep: [size / 10, (o.depth || size) / 10], r: [-90, 0, o.rot || 0], p: [o.x || 0, o.y ?? -0.4, o.z || 0], cast: false, rough: 0.25, metal: 0.1 });
    const sp = o.flow || [0.05, 0.02];
    this.updaters.push((t) => m.material.map.offset.set(t * sp[0], t * sp[1]));
    return m;
  }
  cloud(p, s = 1) { const g = this.group({ p }); for (const [x, y, z, r] of [[0, 0, 0, 5], [5, 1, 0, 4], [-5, 0.5, 0, 3.6], [1.5, 2.2, 0, 3.4]]) { const m = this.sphere(r * s, { c: '#ffffff', emissive: '#c9d6e6', glowI: 0.55, rough: 1, in: g, p: [x * s, y * s, z * s], cast: false, receive: false, s: [1.25, 0.72, 1] }, 14); m.material.fog = false; } return g; }
  /** scatter small instanced pieces: kind = pebble | blade | block */
  scatter(kind, count, area, o = {}) {
    const geom = kind === 'blade' ? new THREE.ConeGeometry(0.035, 0.42, 4) : kind === 'block' ? new THREE.BoxGeometry(1, 1, 1) : new THREE.IcosahedronGeometry(0.5, 0);
    if (kind === 'blade') geom.translate(0, 0.21, 0);
    const mesh = new THREE.InstancedMesh(geom, this.mat({ c: '#ffffff', flat: kind !== 'blade', rough: 1 }), count);
    const r = rng(hash(this.id + kind + count + JSON.stringify(area))), m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), col = new THREE.Color();
    const pal = o.c || ['#8a8f96', '#a39a8c', '#6f6a66'], [s0, s1] = o.s || [0.08, 0.2];
    let k = 0, guard = 0;
    while (k < count && guard++ < count * 20) {
      const x = lerp(area.x[0], area.x[1], r()), z = lerp(area.z[0], area.z[1], r());
      if (o.skip && o.skip(x, z)) continue;
      const s = lerp(s0, s1, r());
      e.set(kind === 'blade' ? (r() - 0.5) * 0.5 : r() * 3, r() * 6.28, kind === 'blade' ? (r() - 0.5) * 0.5 : r() * 3);
      q.setFromEuler(e);
      m4.compose(new THREE.Vector3(x, (area.y || 0) + (kind === 'blade' ? 0 : s * 0.25), z), q, new THREE.Vector3(s * (kind === 'blade' ? 4 : 1.3), s * (kind === 'blade' ? 4 * (0.6 + r()) : 0.75), s * (kind === 'blade' ? 4 : 1)));
      mesh.setMatrixAt(k, m4);
      mesh.setColorAt(k, col.set(pal[(r() * pal.length) | 0]).offsetHSL(0, 0, (r() - 0.5) * 0.08));
      k++;
    }
    mesh.count = k; mesh.castShadow = !!o.cast; mesh.receiveShadow = true; mesh.frustumCulled = false;
    this.scene.add(mesh); return mesh;
  }
  /** an in-world sign: text painted on a board */
  sign(str, o = {}) {
    const w = o.w || 2, h = o.h || 0.8, cv = document.createElement('canvas'); cv.width = 512; cv.height = Math.round(512 * h / w);
    const g = cv.getContext('2d'); g.fillStyle = o.bg || '#f1e6cf'; g.fillRect(0, 0, cv.width, cv.height);
    g.strokeStyle = o.c || '#2a2420'; g.lineWidth = 14; g.strokeRect(7, 7, cv.width - 14, cv.height - 14);
    g.fillStyle = o.c || '#2a2420'; g.textAlign = 'center'; g.textBaseline = 'middle';
    const lines = str.split('\n'); let size = o.size || Math.min(cv.height * 0.7 / lines.length, 150);
    g.font = `800 ${size}px Caption, sans-serif`;
    while (Math.max(...lines.map((l) => g.measureText(l).width)) > cv.width * 0.86) { size *= 0.92; g.font = `800 ${size}px Caption, sans-serif`; }
    lines.forEach((l, i) => g.fillText(l, cv.width / 2, cv.height / 2 + (i - (lines.length - 1) / 2) * size * 1.08));
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
    return this.add(new THREE.PlaneGeometry(w, h), { material: new THREE.MeshStandardMaterial({ map: tex, roughness: 0.9, side: THREE.DoubleSide }), p: o.p, r: o.r, in: o.in });
  }
  // ---- particles and overlays (all closed-form in t)
  puff(o) {
    const n = o.n || 14, r = rng(hash(this.id + 'puff' + o.t + (o.seed || 0))), geo = new THREE.BufferGeometry(), pos = new Float32Array(n * 3);
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: o.size || 0.35, color: o.c || '#e9dcc3', map: dotTex(), transparent: true, depthWrite: false, sizeAttenuation: true }));
    pts.frustumCulled = false; pts.renderOrder = 3; this.scene.add(pts);
    const vel = [...Array(n)].map(() => { const a = r() * 6.283, sp = (o.speed || 1.4) * (0.4 + r()); return [Math.cos(a) * sp * (o.flat ?? 1), (o.up ?? 1.2) * (0.4 + r()), Math.sin(a) * sp * (o.flat ?? 1)]; });
    const life = o.life || 0.7, g = o.g ?? -2.5;
    this.updaters.push((t) => {
      const tt = t - o.t; pts.visible = tt >= 0 && tt < life; if (!pts.visible) return;
      for (let i = 0; i < n; i++) { pos[i * 3] = o.p[0] + vel[i][0] * tt; pos[i * 3 + 1] = Math.max(o.floor ?? -99, o.p[1] + vel[i][1] * tt + 0.5 * g * tt * tt); pos[i * 3 + 2] = o.p[2] + vel[i][2] * tt; }
      geo.attributes.position.needsUpdate = true; pts.material.opacity = (o.opacity ?? 0.9) * (1 - tt / life);
    });
    return pts;
  }
  motes(area, n = 60, o = {}) {
    const r = rng(hash(this.id + 'motes')), geo = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), base = [...Array(n)].map(() => [lerp(area.x[0], area.x[1], r()), lerp(area.y[0], area.y[1], r()), lerp(area.z[0], area.z[1], r()), r() * 6.28]);
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: o.size || 0.07, color: o.c || '#fff3cf', map: dotTex(), transparent: true, opacity: o.opacity ?? 0.7, depthWrite: false, blending: THREE.AdditiveBlending }));
    pts.frustumCulled = false; this.scene.add(pts);
    this.updaters.push((t) => { base.forEach((b, i) => { pos[i * 3] = b[0] + 0.3 * Math.sin(0.4 * t + b[3]); pos[i * 3 + 1] = b[1] + 0.25 * Math.sin(0.31 * t + 2 * b[3]); pos[i * 3 + 2] = b[2] + 0.3 * Math.cos(0.27 * t + b[3]); }); geo.attributes.position.needsUpdate = true; });
    return pts;
  }
  /** expanding flat ring on the ground (explainer "pulse") */
  ring(o) {
    const m = new THREE.Mesh(new THREE.RingGeometry(0.86, 1, 40), new THREE.MeshBasicMaterial({ color: o.c || '#ffe07a', transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, fog: false }));
    if (!o.upright) m.rotation.x = -Math.PI / 2;
    m.position.set(...o.p); m.renderOrder = 4; this.scene.add(m);
    const life = o.life || 0.6;
    this.updaters.push((t) => { const tt = t - o.t; m.visible = tt >= 0 && tt < life; if (m.visible) { const u = tt / life, s = lerp(o.r0 ?? 0.2, o.r1 ?? 2, EASE.out(u)); m.scale.set(s, s, s); m.material.opacity = (o.opacity ?? 0.9) * (1 - u); } });
    return m;
  }
  // ---- cast
  actor(id, lookName, o = {}) { const a = new Actor(this, id, this.stage.cast[lookName], o); this.actors.push(a); return a; }
  crowd(lookNames, n, posFn, o = {}) { const c = new Crowd(this, lookNames.map((k) => this.stage.cast[k]), n, posFn, o); this.crowds.push(c); return c; }
  // ---- animation
  every(fn) { this.updaters.push(fn); }
  tween(obj, prop, keys, dflt) { this.updaters.push((t) => { const v = track(keys, t, dflt); if (Array.isArray(v)) obj[prop].set(...(prop === 'rotation' ? v.map(THREE.MathUtils.degToRad) : v)); else obj[prop] = v; }); }
  sfx(type, t, o = {}) { this.stage.sfx.push({ type, t: +t.toFixed(3), ...o }); }
  ambience(type, o = {}) { this.stage.sfx.push({ type, t: +this.start.toFixed(3), dur: +(this.end - this.start).toFixed(3), loop: true, ...o }); }
  /** camera shots. {t, pos, look, fov, push (zoom-in rate /s, negative = pull out), orbit (deg/s around look), drift [x,y,z]/s, move (s to arrive from the previous shot), ease} */
  cam(shots) {
    const st = this.stage.style;
    this.shots = shots.map((s) => ({ fov: 35, push: st.push, orbit: 0, move: 0, ease: 'inOut', ...s })).sort((a, b) => a.t - b.t);
    this.shots.forEach((s, i) => {
      s.push *= st.pushGain;
      if (!s.move) return;
      const next = this.shots[i + 1];                       // a longer move must still finish before the next shot
      s.move = Math.min(s.move * st.moveGain, next ? (next.t - s.t) * 0.9 : Infinity);
      this.stage.moves.push({ t: +s.t.toFixed(3), dur: +s.move.toFixed(3) });
    });
  }
  shotAt(i, t) {
    const s = this.shots[i], dt = t - s.t, look = V(s.look), rel = V(s.pos).sub(look);
    if (s.orbit) rel.applyAxisAngle(THREE.Object3D.DEFAULT_UP, THREE.MathUtils.degToRad(s.orbit * dt));
    rel.multiplyScalar(Math.exp(-s.push * dt));
    if (s.drift) look.add(V(s.drift).multiplyScalar(dt));
    return { pos: look.clone().add(rel), look, fov: s.fov, roll: s.roll || 0 };
  }
  update(t) {
    let i = 0;
    while (i + 1 < this.shots.length && this.shots[i + 1].t <= t) i++;
    let c = this.shotAt(i, t);
    const s = this.shots[i];
    if (i > 0 && s.move > 0 && t < s.t + s.move) {
      const a = this.shotAt(i - 1, t), u = EASE[s.ease]((t - s.t) / s.move);
      c = { pos: a.pos.lerp(c.pos, u), look: a.look.lerp(c.look, u), fov: lerp(a.fov, c.fov, u), roll: lerp(a.roll, c.roll, u) };
    }
    if (s.shake && t >= s.shake.from && t <= s.shake.to) { const a = s.shake.amp || 0.05, f = s.shake.freq || 17; c.pos.x += a * Math.sin(f * t * 1.3); c.pos.y += a * Math.sin(f * t * 1.7 + 1); c.look.y += a * Math.sin(f * t * 2.1 + 2); }
    this.look = c.look;
    this.camera.fov = c.fov; this.camera.position.copy(c.pos); this.camera.up.set(Math.sin(THREE.MathUtils.degToRad(c.roll)), Math.cos(THREE.MathUtils.degToRad(c.roll)), 0);
    this.camera.lookAt(c.look); this.camera.updateProjectionMatrix(); this.camera.updateMatrixWorld();
    for (const fn of this.updaters) fn(t);
    for (const a of this.actors) a.update(t, this.camera);
    for (const cr of this.crowds) cr.update(t, this.camera);
  }
}

// ------------------------------------------------------------------ the whole film
export class Stage {
  constructor({ storyboard, sentences, words, captions, duration, style }) {
    // pushGain, moveGain and vignette were set after measuring a finished video: at 1 / 1 / 0.22 the holds zoomed at 2.7 %/s
    // (reference 4.1), fast moves peaked at twice the reference speed, and the corners were not darker than the centre
    this.style = { push: 0.035, pushGain: 1.45, moveGain: 1.3, dissolveFrames: 10, vignette: 0.5, captionFont: 74, captionY: 1378, captionStroke: 5.5, captionShadow: [4, 5], ...(storyboard.style || {}), ...(style || {}) };
    this.sentences = sentences; this.words = words; this.captions = captions; this.cast = storyboard.cast; this.sfx = []; this.moves = [];
    this.duration = duration; this.frames = Math.round(duration * FPS);
    this.gl = document.createElement('canvas'); this.gl.width = W; this.gl.height = H;
    this.renderer = new THREE.WebGLRenderer({ canvas: this.gl, antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(1); this.renderer.setSize(W, H, false);
    this.renderer.shadowMap.enabled = true; this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping; this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.out = document.getElementById('out'); this.out.width = W; this.out.height = H; this.ctx = this.out.getContext('2d');
    const probe = new Take(this, { id: 'probe' }, 0, 0);
    const starts = storyboard.takes.map((sp) => (typeof sp.start === 'function' ? sp.start(probe) : sp.start));
    this.takes = storyboard.takes.map((sp, i) => {
      const tk = new Take(this, sp, i === 0 ? 0 : starts[i], i + 1 < starts.length ? starts[i + 1] : duration);
      if (i === 0) tk.join = 'start';
      sp.build(tk);
      if (!tk.shots.length) throw new Error(`take ${sp.id} has no camera`);
      return tk;
    });
    this.vig = this.makeVignette(this.style.vignette);
  }
  makeVignette(a) {
    const cv = document.createElement('canvas'); cv.width = W / 4; cv.height = H / 4;
    const g = cv.getContext('2d'), gr = g.createRadialGradient(W / 8, H / 8, H / 8 * 0.42, W / 8, H / 8, H / 8 * 1.15);
    gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, `rgba(0,0,0,${a})`); g.fillStyle = gr; g.fillRect(0, 0, cv.width, cv.height);
    return cv;
  }
  drawTake(tk, t, alpha) {
    tk.update(t);
    this.renderer.toneMappingExposure = tk.exposure;
    this.renderer.render(tk.scene, tk.camera);
    this.ctx.globalAlpha = alpha; this.ctx.drawImage(this.gl, 0, 0);
  }
  render(f) {
    const t = f / FPS, ctx = this.ctx;
    let i = 0;
    while (i + 1 < this.takes.length && this.takes[i + 1].start <= t) i++;
    let done = false;
    for (const j of [i, i + 1]) {                      // inside a dissolve window around the start of take j?
      const b = this.takes[j];
      if (!b || j === 0 || b.join !== 'dissolve') continue;
      const half = b.joinFrames / 2 / FPS, u = (t - (b.start - half)) / (2 * half);
      if (u > 0 && u < 1) { this.drawTake(this.takes[j - 1], t, 1); this.drawTake(b, t, u); done = true; break; }
    }
    if (!done) this.drawTake(this.takes[i], t, 1);
    ctx.globalAlpha = 1;
    if (this.style.vignette > 0) ctx.drawImage(this.vig, 0, 0, W, H);
    const cap = this.captions.find((c) => f >= c.on_f && f < c.off_f);
    if (cap) this.drawCaption(cap.text);
  }
  drawCaption(text) {
    const ctx = this.ctx, st = this.style, x = W / 2, y = st.captionY;
    ctx.font = `800 ${st.captionFont}px Caption, sans-serif`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic'; ctx.lineJoin = 'round'; ctx.miterLimit = 2;
    ctx.strokeStyle = '#0d0d0d'; ctx.fillStyle = '#0d0d0d'; ctx.lineWidth = st.captionStroke * 2;
    ctx.strokeText(text, x + st.captionShadow[0], y + st.captionShadow[1]);      // hard drop shadow of the outlined text
    ctx.fillText(text, x + st.captionShadow[0], y + st.captionShadow[1]);
    ctx.strokeText(text, x, y);
    ctx.fillStyle = '#fdfdfd'; ctx.fillText(text, x, y);
  }
  timeline() {
    return { duration: this.duration, frames: this.frames, fps: FPS,
      takes: this.takes.map((t) => ({ id: t.id, start: +t.start.toFixed(3), end: +t.end.toFixed(3), join: t.join, joinFrames: t.joinFrames, shots: t.shots.map((s) => ({ t: +s.t.toFixed(3), move: s.move, push: s.push, orbit: s.orbit })) })),
      moves: this.moves.sort((a, b) => a.t - b.t), sfx: this.sfx.sort((a, b) => a.t - b.t) };
  }
}
