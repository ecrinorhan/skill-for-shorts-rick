#!/usr/bin/env node
// render.mjs — renders a project's storyboard to frames with headless Chromium (WebGL via SwiftShader or a GPU).
//
//   node render.mjs <project_dir> --timeline              write timeline.json (takes, camera moves, SFX cues) and stop
//   node render.mjs <project_dir> --still 0,45,300        write preview frames to <project>/stills/
//   node render.mjs <project_dir> [--workers 4]           render every frame to <project>/frames/ and encode video.mp4
//   node render.mjs <project_dir> --frames 0:150          render only these frames and encode preview.mp4
//   node render.mjs <project_dir> --range 0:300           (used by the workers)
//
// The project folder needs storyboard.mjs, sentences.json, words.json, captions.json, voice_meta.json (from voice.py).
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const proj = path.resolve(args[0]);
const opt = (name, dflt) => { const i = args.indexOf(`--${name}`); return i < 0 ? dflt : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true); };
const threeDir = path.join(here, 'node_modules', 'three', 'build');
const FONT = path.join(here, '..', '..', 'assets', 'fonts', 'Archivo-VariableFont.ttf');
const TYPES = { '.js': 'application/javascript', '.mjs': 'application/javascript', '.json': 'application/json', '.ttf': 'font/ttf', '.html': 'text/html' };

const HTML = `<!doctype html><html><head><script type="importmap">{"imports":{"three":"/three.module.js"}}</script><style>
@font-face { font-family: Caption; src: url(/font.ttf); font-weight: 100 900; }
body { margin: 0; background: #000; }</style></head><body><canvas id="out"></canvas>
<script type="module">
import { Stage } from '/stage.js';
import storyboard from '/project/storyboard.mjs';
const j = (n) => fetch('/project/' + n).then((r) => r.json());
const [sentences, words, captions, meta] = await Promise.all([j('sentences.json'), j('words.json'), j('captions.json'), j('voice_meta.json')]);
await document.fonts.load('800 74px Caption'); await document.fonts.ready;
try {
  const stage = new Stage({ storyboard, sentences, words, captions, duration: meta.duration_s });
  window.stage = stage;
  window.renderFrame = (f, q) => { stage.render(f); return stage.out.toDataURL('image/jpeg', q); };
  window.ready = true;
} catch (e) { window.failed = String(e.stack || e); }
</script></body></html>`;

async function open() {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--use-gl=angle', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('console', (m) => { if (m.type() === 'error' || process.env.STAGE_DEBUG) console.log('[page]', m.text()); });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.route('**/*', (route) => {
    const u = new URL(route.request().url());
    let file;
    if (u.pathname === '/' || u.pathname === '/index.html') return route.fulfill({ contentType: 'text/html', body: HTML });
    if (u.pathname === '/font.ttf') file = FONT;
    else if (u.pathname.startsWith('/project/')) file = path.join(proj, u.pathname.slice(9));
    else if (u.pathname.startsWith('/three.')) file = path.join(threeDir, u.pathname.slice(1));
    else if (u.pathname.startsWith('/jsm/')) file = path.join(here, 'node_modules', 'three', 'examples', u.pathname.slice(1));
    else file = path.join(here, u.pathname.slice(1));
    if (!fs.existsSync(file)) return route.fulfill({ status: 404, body: 'not found: ' + u.pathname });
    return route.fulfill({ contentType: TYPES[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
  });
  await page.goto('http://stage.local/index.html');
  await page.waitForFunction('window.ready === true || window.failed', null, { timeout: 180000 });
  const failed = await page.evaluate(() => window.failed);
  if (failed) { await browser.close(); throw new Error('storyboard failed to build:\n' + failed); }
  return { browser, page };
}

async function frames(list, dir, quality = 0.93) {
  fs.mkdirSync(dir, { recursive: true });
  const { browser, page } = await open();
  for (const f of list) {
    const url = await page.evaluate(([n, q]) => window.renderFrame(n, q), [f, quality]);
    fs.writeFileSync(path.join(dir, String(f).padStart(5, '0') + '.jpg'), Buffer.from(url.slice(url.indexOf(',') + 1), 'base64'));
  }
  await browser.close();
}

const run = (cmd, a) => new Promise((res, rej) => { const p = spawn(cmd, a, { stdio: 'inherit' }); p.on('exit', (c) => (c === 0 ? res() : rej(new Error(`${cmd} exited ${c}`)))); });

if (opt('timeline')) {
  const { browser, page } = await open();
  const tl = await page.evaluate(() => window.stage.timeline());
  fs.writeFileSync(path.join(proj, 'timeline.json'), JSON.stringify(tl, null, 1));
  console.log(`timeline: ${tl.frames} frames, ${tl.takes.length} takes, ${tl.moves.length} camera moves, ${tl.sfx.length} sfx cues, ${(tl.lowPoly || []).length} low-poly shapes`);
  for (const s of tl.lowPoly || []) console.log(`  low-poly: ${s.shape} with ${s.sides ?? 'sharp'} sides in take "${s.take}". Build it with tk.box, tk.cyl, tk.sphere, tk.cone, tk.capsule or tk.torus, or pass { sides: n } if it is meant to have flat faces.`);
  await browser.close();
} else if (opt('still')) {
  const list = String(opt('still')).split(',').map(Number);
  await frames(list, path.join(proj, 'stills'), 0.92);
  console.log('stills:', list.join(','));
} else if (opt('range')) {
  const [a, b] = String(opt('range')).split(':').map(Number);
  await frames([...Array(b - a).keys()].map((i) => i + a), path.join(proj, 'frames'));
} else {
  const meta = JSON.parse(fs.readFileSync(path.join(proj, 'voice_meta.json'), 'utf8'));
  const part = opt('frames') ? String(opt('frames')).split(':').map(Number) : null;
  const f0 = part ? part[0] : 0, f1 = part ? Math.min(part[1], meta.frames) : meta.frames;
  const total = f1 - f0, n = Math.max(1, Math.min(Number(opt('workers', 4)), total)), per = Math.ceil(total / n);
  const out = path.join(proj, part ? 'preview.mp4' : 'video.mp4');
  fs.rmSync(path.join(proj, 'frames'), { recursive: true, force: true });
  const t0 = Date.now();
  await Promise.all([...Array(n).keys()].map((k) => run(process.execPath, [fileURLToPath(import.meta.url), proj, '--range', `${f0 + k * per}:${Math.min(f1, f0 + (k + 1) * per)}`])));
  console.log(`rendered ${total} frames in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  await run('ffmpeg', ['-v', 'error', '-y', '-framerate', '30', '-start_number', String(f0), '-i', path.join(proj, 'frames', '%05d.jpg'), '-c:v', 'libx264', '-preset', 'slow', '-crf', '15',
    '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart', out]);
  console.log('wrote', out);
}
