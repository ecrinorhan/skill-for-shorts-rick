// cast.js — an original flat 2D puppet cast, drawn with Canvas 2D (no external art).
// Shape language (deliberately its own): loaf-shaped heads in skin tones, two-tone oval eyes, thick brow bars,
// coat-shaped bodies, coloured sleeves and trousers, mitten hands, dark-indigo outlines.
export const CW = 512, CH = 896, FOOT = 862, INK = '#1d1b33', OUT = 5;
const rad = (d) => (d * Math.PI) / 180;
const lerp = (a, b, u) => a + (b - a) * u;
const TAU = Math.PI * 2;

// Limb angles in degrees from "hanging straight down"; +90 points forward (the way the character faces).
// a = [shoulder, elbow bend], l = [hip, knee bend]. F = the limb nearer the camera, B = the far one.
export const POSES = {
  stand: { aF: [12, 8], aB: [-12, 8], lF: [5, 0], lB: [-5, 0], lean: 0, head: 0 },
  hips: { aF: [38, -105], aB: [-38, 105], lF: [8, 0], lB: [-8, 0], lean: 0, head: 0 },
  point: { aF: [86, 0], aB: [-14, 8], lF: [8, 0], lB: [-8, 0], lean: 3, head: 0 },
  pointUp: { aF: [140, 0], aB: [-14, 8], lF: [6, 0], lB: [-6, 0], lean: 0, head: -4 },
  pointDown: { aF: [48, 0], aB: [-14, 8], lF: [8, 0], lB: [-8, 0], lean: 6, head: 6 },
  armsUp: { aF: [158, 10], aB: [-158, -10], lF: [8, 0], lB: [-8, 0], lean: 0, head: -5 },
  shrug: { aF: [62, -75], aB: [-62, 75], lF: [6, 0], lB: [-6, 0], lean: 0, head: 6 },
  hold: { aF: [48, -68], aB: [34, -58], lF: [6, 0], lB: [-6, 0], lean: 2, head: 0 },
  carry: { aF: [62, -22], aB: [-10, 8], lF: [6, 0], lB: [-6, 0], lean: 0, head: 0 },
  push: { aF: [84, -8], aB: [74, -8], lF: [22, 0], lB: [-24, 0], lean: 12, head: 0 },
  windup: { aF: [-150, -30], aB: [40, 20], lF: [18, 0], lB: [-20, 0], lean: -10, head: -4 },
  throwEnd: { aF: [70, 0], aB: [-40, 20], lF: [24, 0], lB: [-22, 0], lean: 14, head: 4 },
  cower: { aF: [150, -95], aB: [-150, 95], lF: [10, 20], lB: [-10, 20], lean: -6, head: 8 },
  salute: { aF: [138, -118], aB: [-8, 4], lF: [3, 0], lB: [-3, 0], lean: 0, head: 0 },
  sit: { aF: [130, -30], aB: [120, -30], lF: [84, 84], lB: [76, 84], lean: -4, head: 0 },
  laugh: { aF: [40, -100], aB: [-40, 100], lF: [8, 0], lB: [-8, 0], lean: -8, head: -12 },
  stop: { aF: [96, 62], aB: [-12, 8], lF: [10, 0], lB: [-10, 0], lean: -2, head: 0 },
  lean: { aF: [20, 30], aB: [-30, 20], lF: [14, 0], lB: [-2, 0], lean: 10, head: 4 },
};

export const EXPR = {
  neutral: { eyes: 'open', brow: 0, mouth: 'flat' },
  smug: { eyes: 'half', brow: -6, mouth: 'smirk' },
  happy: { eyes: 'open', brow: 6, mouth: 'smile' },
  grin: { eyes: 'arc', brow: 8, mouth: 'grin' },
  angry: { eyes: 'open', brow: -22, mouth: 'frown' },
  shout: { eyes: 'open', brow: -22, mouth: 'open' },
  shock: { eyes: 'wide', brow: 16, mouth: 'o' },
  worried: { eyes: 'open', brow: 18, mouth: 'frown' },
  bored: { eyes: 'half', brow: 0, mouth: 'flat' },
  determined: { eyes: 'open', brow: -14, mouth: 'flat' },
  laugh: { eyes: 'arc', brow: 10, mouth: 'grin' },
  dizzy: { eyes: 'wide', brow: 10, mouth: 'wavy' },
};

export function gait(name, ph, seed = 0) {
  const s = Math.sin(TAU * ph), c = Math.cos(TAU * ph);
  if (name === 'march') {
    return { aF: [-38 * s, 4], aB: [38 * s, 4], lF: [s > 0 ? 46 * s : 14 * s, s > 0 ? 52 * s : 0], lB: [s < 0 ? -46 * s : -14 * s, s < 0 ? -52 * s : 0], lean: 0, head: 0, bob: 9 * Math.abs(c) };
  }
  if (name === 'shuffle') {
    const w = Math.sin(TAU * (ph * 0.61 + seed)), w2 = Math.sin(TAU * (ph * 1.37 + seed * 3.1));
    return { aF: [24 + 22 * w, 26 + 20 * w2], aB: [-20 + 22 * w2, 30], lF: [12 * s, 14 * Math.max(0, c)], lB: [-12 * s, 14 * Math.max(0, -c)], lean: 7 * w, head: 6 * w2, bob: 4 * Math.abs(c) };
  }
  if (name === 'run') {
    return { aF: [-55 * s, 70], aB: [55 * s, 70], lF: [48 * s, 60 * Math.max(0, -c)], lB: [-48 * s, 60 * Math.max(0, c)], lean: 14, head: 0, bob: 12 * Math.abs(c) };
  }
  return { aF: [-26 * s, 14], aB: [26 * s, 14], lF: [26 * s, 30 * Math.max(0, -c)], lB: [-26 * s, 30 * Math.max(0, c)], lean: 2, head: 0, bob: 6 * Math.abs(c) };
}

export function blendPose(a, b, u) {
  const o = {};
  for (const k of ['aF', 'aB', 'lF', 'lB']) o[k] = [lerp(a[k][0], b[k][0], u), lerp(a[k][1], b[k][1], u)];
  o.lean = lerp(a.lean || 0, b.lean || 0, u);
  o.head = lerp(a.head || 0, b.head || 0, u);
  o.bob = lerp(a.bob || 0, b.bob || 0, u);
  return o;
}

function seg(ctx, x, y, a1, l1, a2, l2, w, col) {
  const x1 = x + Math.sin(rad(a1)) * l1, y1 = y + Math.cos(rad(a1)) * l1;
  const x2 = x1 + Math.sin(rad(a2)) * l2, y2 = y1 + Math.cos(rad(a2)) * l2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.strokeStyle = INK;
  ctx.lineWidth = w + 2 * OUT;
  ctx.stroke();
  ctx.strokeStyle = col;
  ctx.lineWidth = w;
  ctx.stroke();
  return [x2, y2, a2];
}

function blob(ctx, fill, lw = 2 * OUT) {
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = INK;
  ctx.lineWidth = lw;
  ctx.lineJoin = 'round';
  ctx.stroke();
}

function heldItem(ctx, item, hx, hy, look) {
  if (!item) return;
  ctx.save();
  ctx.translate(hx, hy);
  if (item === 'lantern') {
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, 26); ctx.strokeStyle = INK; ctx.lineWidth = 7; ctx.stroke();
    ctx.beginPath(); ctx.roundRect(-30, 26, 60, 78, 12); blob(ctx, '#ffd35a');
    ctx.beginPath(); ctx.roundRect(-36, 20, 72, 14, 5); blob(ctx, '#4a4038', 7);
    ctx.beginPath(); ctx.roundRect(-36, 98, 72, 14, 5); blob(ctx, '#4a4038', 7);
    ctx.beginPath(); ctx.ellipse(0, 66, 11, 20, 0, 0, TAU); ctx.fillStyle = '#fff6c9'; ctx.fill();
  } else if (item === 'cup') {
    ctx.beginPath(); ctx.roundRect(-18, -6, 36, 44, 6); blob(ctx, '#b9c2cc', 7);
  } else if (item === 'sword') {
    ctx.rotate(rad(-25));
    ctx.beginPath(); ctx.roundRect(-6, -150, 12, 150, 5); blob(ctx, '#d7dde6', 7);
    ctx.beginPath(); ctx.roundRect(-26, -8, 52, 12, 5); blob(ctx, '#d9a441', 7);
  } else if (item === 'staff') {
    ctx.beginPath(); ctx.roundRect(-7, -210, 14, 330, 6); blob(ctx, '#8a5a34', 7);
  } else if (item === 'sticks') {
    ctx.rotate(rad(35));
    ctx.beginPath(); ctx.roundRect(-5, -70, 10, 86, 5); blob(ctx, '#e9d2a6', 6);
  } else if (item === 'drum') {
    ctx.beginPath(); ctx.roundRect(-52, -10, 104, 84, 14); blob(ctx, '#b33f3a');
    ctx.beginPath(); ctx.ellipse(0, -8, 52, 15, 0, 0, TAU); blob(ctx, '#f1e6cf', 7);
    for (const dx of [-30, 0, 30]) { ctx.beginPath(); ctx.moveTo(dx - 12, 8); ctx.lineTo(dx + 12, 66); ctx.strokeStyle = '#f0c75e'; ctx.lineWidth = 5; ctx.stroke(); }
  }
  ctx.restore();
}

function hat(ctx, h, cx, top, w) {
  if (!h || h.type === 'none') return;
  const c = h.color || '#3b5b7a';
  ctx.save();
  if (h.type === 'cap') {
    ctx.beginPath(); ctx.roundRect(cx - w * 0.5, top - 34, w, 74, [60, 60, 14, 14]); blob(ctx, c);
    ctx.beginPath(); ctx.roundRect(cx + w * 0.12, top + 20, w * 0.56, 22, 11); blob(ctx, c, 8);
  } else if (h.type === 'shako') {
    ctx.beginPath(); ctx.roundRect(cx - w * 0.36, top - 118, w * 0.72, 150, [16, 16, 6, 6]); blob(ctx, c);
    ctx.beginPath(); ctx.roundRect(cx - w * 0.4, top + 14, w * 0.98, 20, 10); blob(ctx, '#22212e', 8);
    ctx.beginPath(); ctx.roundRect(cx - w * 0.36, top - 14, w * 0.72, 16, 4); ctx.fillStyle = h.band || '#f0c75e'; ctx.fill();
    ctx.beginPath(); ctx.ellipse(cx, top - 138, 15, 30, 0, 0, TAU); blob(ctx, h.plume || '#d94f3d', 7);
  } else if (h.type === 'bicorne') {
    ctx.beginPath(); ctx.moveTo(cx - w * 0.72, top + 28); ctx.quadraticCurveTo(cx, top - 150, cx + w * 0.72, top + 28);
    ctx.quadraticCurveTo(cx, top - 12, cx - w * 0.72, top + 28); ctx.closePath(); blob(ctx, c);
    ctx.beginPath(); ctx.arc(cx, top - 26, 15, 0, TAU); blob(ctx, h.band || '#f0c75e', 7);
  } else if (h.type === 'brim') {
    ctx.beginPath(); ctx.roundRect(cx - w * 0.36, top - 62, w * 0.72, 92, [44, 44, 8, 8]); blob(ctx, c);
    ctx.beginPath(); ctx.ellipse(cx, top + 26, w * 0.74, 18, 0, 0, TAU); blob(ctx, c, 8);
  } else if (h.type === 'beanie') {
    ctx.beginPath(); ctx.roundRect(cx - w * 0.5, top - 36, w, 86, [70, 70, 10, 10]); blob(ctx, c);
    ctx.beginPath(); ctx.arc(cx, top - 44, 17, 0, TAU); blob(ctx, h.band || '#f4f0e6', 7);
  }
  ctx.restore();
}

function face(ctx, look, e, cx, cy, fx, skin, talk) {
  const eyes = [[cx + fx - 46, cy - 6, 1], [cx + fx + 50, cy - 6, fx > 0 ? 0.9 : 1]];
  for (const [ex, ey, k] of eyes) {
    const rx = 23 * k, ry = (e.eyes === 'wide' ? 35 : 29) * k;
    if (e.eyes === 'arc' || e.eyes === 'closed') {
      ctx.beginPath();
      if (e.eyes === 'arc') ctx.arc(ex, ey + 8, 20 * k, Math.PI * 1.12, Math.PI * 1.88);
      else { ctx.moveTo(ex - 20 * k, ey); ctx.lineTo(ex + 20 * k, ey); }
      ctx.strokeStyle = INK; ctx.lineWidth = 8; ctx.lineCap = 'round'; ctx.stroke();
    } else {
      ctx.beginPath(); ctx.ellipse(ex, ey, rx, ry, 0, 0, TAU); ctx.fillStyle = '#fffdf7'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = 6; ctx.stroke();
      const pr = (e.eyes === 'wide' ? 8 : 11) * k;
      ctx.beginPath(); ctx.arc(ex + look[0] * 9, ey + look[1] * 9 + (e.eyes === 'half' ? 6 : 0), pr, 0, TAU); ctx.fillStyle = INK; ctx.fill();
      if (e.eyes === 'half') {
        ctx.save(); ctx.beginPath(); ctx.ellipse(ex, ey, rx + 3, ry + 3, 0, 0, TAU); ctx.clip();
        ctx.fillStyle = skin; ctx.fillRect(ex - rx - 6, ey - ry - 6, 2 * rx + 12, ry + 2); ctx.restore();
        ctx.beginPath(); ctx.moveTo(ex - rx, ey - 4); ctx.lineTo(ex + rx, ey - 4); ctx.strokeStyle = INK; ctx.lineWidth = 6; ctx.stroke();
      }
    }
    const side = ex < cx + fx ? -1 : 1;                     // brows: negative angle = inner ends down (angry)
    ctx.save(); ctx.translate(ex, ey - (e.eyes === 'wide' ? 52 : 46) * k); ctx.rotate(rad(-e.brow * side));
    ctx.beginPath(); ctx.moveTo(-23 * k, 0); ctx.lineTo(23 * k, 0); ctx.strokeStyle = INK; ctx.lineWidth = 11; ctx.lineCap = 'round'; ctx.stroke(); ctx.restore();
  }
  const mx = cx + fx + 4, my = cy + 62;
  let m = e.mouth, open = 1;
  if (talk > 0) { m = 'open'; open = talk; }
  ctx.strokeStyle = INK; ctx.lineWidth = 8; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath();
  if (m === 'flat') { ctx.moveTo(mx - 20, my); ctx.lineTo(mx + 20, my); ctx.stroke(); }
  else if (m === 'smile') { ctx.arc(mx, my - 14, 28, Math.PI * 0.2, Math.PI * 0.8); ctx.stroke(); }
  else if (m === 'frown') { ctx.arc(mx, my + 26, 28, Math.PI * 1.22, Math.PI * 1.78); ctx.stroke(); }
  else if (m === 'smirk') { ctx.moveTo(mx - 20, my + 2); ctx.quadraticCurveTo(mx + 6, my + 8, mx + 26, my - 12); ctx.stroke(); }
  else if (m === 'o') { ctx.arc(mx, my + 2, 13, 0, TAU); ctx.fillStyle = '#5a1f2a'; ctx.fill(); ctx.stroke(); }
  else if (m === 'wavy') { ctx.moveTo(mx - 26, my); ctx.bezierCurveTo(mx - 12, my - 14, mx - 4, my + 14, mx + 8, my); ctx.bezierCurveTo(mx + 14, my - 8, mx + 20, my + 8, mx + 28, my); ctx.stroke(); }
  else if (m === 'grin') { ctx.roundRect(mx - 32, my - 12, 64, 30, [6, 6, 16, 16]); ctx.fillStyle = '#fffdf7'; ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.moveTo(mx - 30, my + 3); ctx.lineTo(mx + 30, my + 3); ctx.lineWidth = 4; ctx.stroke(); }
  else { ctx.ellipse(mx, my + 4, 22, 5 + 17 * open, 0, 0, TAU); ctx.fillStyle = '#5a1f2a'; ctx.fill(); ctx.stroke(); if (open > 0.5) { ctx.beginPath(); ctx.ellipse(mx, my + 14, 12, 6, 0, 0, TAU); ctx.fillStyle = '#e07a7a'; ctx.fill(); } }
}

/** Draw one character. look = palette/outfit (see CAST examples in the storyboard), st = {pose, expr, facing, talk, blink, item, gaze}. */
export function drawActor(ctx, look, st) {
  const p = st.pose, e = st.blink ? { ...st.expr, eyes: st.expr.eyes === 'arc' ? 'arc' : 'closed' } : st.expr;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, CW, CH);
  if (st.facing === 'left') ctx.setTransform(-1, 0, 0, 1, CW, 0);
  const front = st.facing === 'front';
  const fx = front ? 0 : 26;
  const cx = CW / 2, bob = -(p.bob || 0);
  const k = look.build || 1;                         // 1 = regular, <1 slimmer, >1 stockier
  const hipY = FOOT - 262 + bob, shY = hipY - 236, headCy = shY - 96;
  const top = look.top || '#c9742e', bot = look.bottom || '#3a3f52', skin = look.skin || '#e8b98a';
  ctx.save();
  ctx.translate(cx, FOOT); ctx.rotate(rad(p.lean || 0)); ctx.translate(-cx, -FOOT);
  // far arm, far leg
  const armL = 96, legL = 128;
  const bA = seg(ctx, cx - (front ? 84 * k : 34), shY + 26, p.aB[0], armL, p.aB[0] + p.aB[1], armL * 0.92, 30, top);
  ctx.beginPath(); ctx.arc(bA[0], bA[1], 21, 0, TAU); blob(ctx, skin, 8);
  const bL = seg(ctx, cx - (front ? 44 * k : 18), hipY, p.lB[0], legL, p.lB[0] - p.lB[1], legL, 40, bot);
  ctx.save(); ctx.translate(bL[0], bL[1]); ctx.rotate(-rad(bL[2]) * 0.35); ctx.beginPath(); ctx.roundRect(-26, -10, front ? 54 : 78, 34, 15); blob(ctx, look.boots || '#2a2420', 8); ctx.restore();
  // near leg: under the coat, so the hem covers its top, unless the thigh is raised (sitting, kicking) and crosses the coat
  const nearLeg = () => {
    const fL = seg(ctx, cx + (front ? 44 * k : 22), hipY, p.lF[0], legL, p.lF[0] - p.lF[1], legL, 40, bot);
    ctx.save(); ctx.translate(fL[0], fL[1]); ctx.rotate(-rad(fL[2]) * 0.35); ctx.beginPath(); ctx.roundRect(-26, -10, front ? 54 : 78, 34, 15); blob(ctx, look.boots || '#2a2420', 8); ctx.restore();
  };
  const legOver = Math.abs(p.lF[0]) > 40;
  if (!legOver) nearLeg();
  // body: coat that widens toward the hem
  ctx.beginPath();
  const tw = 78 * k, bw = 112 * k;
  ctx.moveTo(cx - tw, shY + 26); ctx.quadraticCurveTo(cx - tw, shY - 8, cx - tw + 34, shY - 8); ctx.lineTo(cx + tw - 34, shY - 8);
  ctx.quadraticCurveTo(cx + tw, shY - 8, cx + tw, shY + 26); ctx.lineTo(cx + bw, hipY + 18); ctx.quadraticCurveTo(cx + bw, hipY + 46, cx + bw - 30, hipY + 46);
  ctx.lineTo(cx - bw + 30, hipY + 46); ctx.quadraticCurveTo(cx - bw, hipY + 46, cx - bw, hipY + 18); ctx.closePath(); blob(ctx, top);
  if (look.detail === 'coat' || look.detail === 'uniform') {
    for (let i = 0; i < 4; i++) { ctx.beginPath(); ctx.arc(cx + fx * 0.6, shY + 42 + i * 46, 9, 0, TAU); ctx.fillStyle = look.detailColor || '#f0c75e'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = 4; ctx.stroke(); }
    ctx.beginPath(); ctx.roundRect(cx - bw * 0.93, hipY - 26, bw * 1.86, 24, 6); blob(ctx, look.belt || '#2a2420', 7);
  }
  if (look.detail === 'uniform') {
    ctx.beginPath(); ctx.moveTo(cx - tw + 6, shY + 4); ctx.lineTo(cx + tw * 0.9, hipY - 30); ctx.lineWidth = 20; ctx.strokeStyle = look.sash || '#f4f0e6'; ctx.stroke();
  }
  if (look.detail === 'apron') { ctx.beginPath(); ctx.roundRect(cx - tw * 0.8, shY + 60, tw * 1.6, hipY - shY - 20, 14); blob(ctx, look.detailColor || '#f4f0e6', 7); }
  if (look.detail === 'scarf') {
    ctx.beginPath(); ctx.roundRect(cx - tw * 0.86, shY - 16, tw * 1.72, 34, 16); blob(ctx, look.detailColor || '#d94f3d', 8);
    ctx.beginPath(); ctx.roundRect(cx - tw * 0.5, shY + 8, 30, 74, 10); blob(ctx, look.detailColor || '#d94f3d', 8);
  }
  if (look.epaulettes) for (const sx of [-1, 1]) { ctx.beginPath(); ctx.roundRect(cx + sx * tw - 30, shY - 14, 60, 22, 9); blob(ctx, '#f0c75e', 7); }
  if (legOver) nearLeg();
  if (st.item === 'drum') heldItem(ctx, 'drum', cx + 70, hipY - 60, look);
  // head
  ctx.save();
  ctx.translate(cx + fx * 0.3, shY); ctx.rotate(rad(p.head || 0)); ctx.translate(-(cx + fx * 0.3), -shY);
  const hw = 250, hh = 226, hx = cx - hw / 2 + fx * 0.3, hy = headCy - hh / 2 + 4;
  if (!front) { ctx.beginPath(); ctx.ellipse(hx + 14, headCy + 22, 22, 30, 0, 0, TAU); blob(ctx, skin, 8); }
  else for (const sx of [-1, 1]) { ctx.beginPath(); ctx.ellipse(cx + sx * (hw / 2 - 2), headCy + 22, 20, 28, 0, 0, TAU); blob(ctx, skin, 8); }
  ctx.beginPath(); ctx.roundRect(hx, hy, hw, hh, 92);
  ctx.fillStyle = skin; ctx.fill();
  const hair = look.hair || { style: 'short', color: '#5a3a22' };
  if (hair.style !== 'bald') {
    ctx.save(); ctx.clip(); ctx.fillStyle = hair.color;
    if (hair.style === 'side') { ctx.beginPath(); ctx.ellipse(hx + hw * 0.36, hy + 8, hw * 0.66, 78, -0.16, 0, TAU); ctx.fill(); }
    else if (hair.style === 'grey' || hair.style === 'short') { ctx.fillRect(hx, hy, hw, 58); ctx.fillRect(hx, hy, front ? 0 : 54, 150); }
    ctx.restore();
  }
  ctx.beginPath(); ctx.roundRect(hx, hy, hw, hh, 92); ctx.strokeStyle = INK; ctx.lineWidth = 2 * OUT; ctx.stroke();
  if (!front) { ctx.beginPath(); ctx.arc(hx + hw - 2, headCy + 26, 15, -1.2, 1.5); ctx.strokeStyle = INK; ctx.lineWidth = 8; ctx.stroke(); }   // nose bump
  face(ctx, st.gaze || [front ? 0 : 0.4, 0], e, cx + fx * 0.3, headCy, fx, skin, st.talk || 0);
  if (look.moustache) { ctx.beginPath(); ctx.roundRect(cx + fx - 44, headCy + 34, 100, 22, 11); blob(ctx, look.moustache, 7); }
  hat(ctx, look.hat, cx + fx * 0.3, hy + 8, hw);
  ctx.restore();
  // near arm + whatever it holds
  const fA = seg(ctx, cx + (front ? 84 * k : 40), shY + 26, p.aF[0], armL, p.aF[0] + p.aF[1], armL * 0.92, 30, top);
  if (st.item && st.item !== 'drum') heldItem(ctx, st.item, fA[0], fA[1], look);
  ctx.beginPath(); ctx.arc(fA[0], fA[1], 22, 0, TAU); blob(ctx, skin, 8);
  ctx.restore();
}
