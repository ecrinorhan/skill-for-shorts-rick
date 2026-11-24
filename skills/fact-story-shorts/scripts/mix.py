#!/usr/bin/env python3
"""mix.py — voice chain + an original synthesized music bed + synthesized sound effects -> mix.wav -> final.mp4

  mix.py <project_dir> [--bpm 116] [--music-lu 19.4] [--lufs -14.1] [--peak -2.1] [--seed 7] [--video preview.mp4]

Reads  voice_dry.wav, sentences.json, timeline.json (SFX cues written by the storyboard), video.mp4
Writes voice.wav, music.wav, sfx.wav, mix.wav, mix_report.json and, when the picture exists, final.mp4
       (with --video preview.mp4: preview_sound.mp4, cut to the length of the preview)

Everything audible besides the voice is generated here with numpy, so there is nothing to license.
Targets (measured on the 20 reference videos): mix -14.1 LUFS integrated, true peak about -2.1 dBTP, loudness range 2.2 LU,
music 19.4 LU under the voice and never ducked, about 6 effects per 10 s with a median 50 ms level near -38 dBFS.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import butter, istft, resample_poly, sawtooth, sosfilt, stft

SR = 44100
TAU = 2 * np.pi


# ------------------------------------------------------------------ small DSP kit
def db(x):
    return 10 ** (x / 20)


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, btype=kind, fs=SR, output="sos"), x).astype(np.float32)


def biquad(x, kind, f0, gain_db, q=0.8):
    """RBJ cookbook peaking / shelving filters."""
    a = 10 ** (gain_db / 40)
    w = TAU * f0 / SR
    cw, sw = np.cos(w), np.sin(w)
    al = sw / (2 * q)
    if kind == "peak":
        b = [1 + al * a, -2 * cw, 1 - al * a]
        aa = [1 + al / a, -2 * cw, 1 - al / a]
    else:
        s2 = 2 * np.sqrt(a) * al
        sg = 1 if kind == "high" else -1
        b = [a * ((a + 1) + sg * (a - 1) * cw + s2), -sg * 2 * a * ((a - 1) + sg * (a + 1) * cw), a * ((a + 1) + sg * (a - 1) * cw - s2)]
        aa = [(a + 1) - sg * (a - 1) * cw + s2, sg * 2 * ((a - 1) - sg * (a + 1) * cw), (a + 1) - sg * (a - 1) * cw - s2]
    sos = np.array([[b[0] / aa[0], b[1] / aa[0], b[2] / aa[0], 1.0, aa[1] / aa[0], aa[2] / aa[0]]])
    return sosfilt(sos, x).astype(np.float32)


def compress(x, thr=-24.0, ratio=3.5, att=0.004, rel=0.09):
    hop = SR // 1000
    n = len(x) // hop
    lvl = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12))
    gr = -np.maximum(lvl - thr, 0) * (1 - 1 / ratio)
    out, g = np.zeros(n), 0.0
    aa, ar = np.exp(-1 / (att * 1000)), np.exp(-1 / (rel * 1000))
    for i in range(n):
        a = aa if gr[i] < g else ar
        g = a * g + (1 - a) * gr[i]
        out[i] = g
    gain = np.interp(np.arange(len(x)), (np.arange(n) + 0.5) * hop, out)
    return (x * db(gain)).astype(np.float32)


def limit(x, ceiling_db, look=0.004, rel=0.06):
    """Look-ahead limiter on the 4x oversampled peak, so inter-sample (true) peaks are held too."""
    c = db(ceiling_db)
    up = np.abs(resample_poly(x, 4, 1, axis=0))
    up = up.max(axis=1) if up.ndim == 2 else up
    peak = up[:len(x) * 4].reshape(len(x), 4).max(axis=1)
    g = np.minimum(1.0, c / np.maximum(peak, 1e-9))
    n = max(3, int(look * SR))
    g = minimum_filter1d(g, size=2 * n + 1)
    g = np.minimum(g, uniform_filter1d(minimum_filter1d(g, size=int(rel * SR)), size=int(rel * SR)))
    g = uniform_filter1d(g, size=n)
    return (x * (g[:, None] if x.ndim == 2 else g)).astype(np.float32)


def true_peak_db(x):
    return float(20 * np.log10(np.abs(resample_poly(x, 4, 1, axis=0)).max() + 1e-12))


def lufs(x):
    return float(pyln.Meter(SR).integrated_loudness(x))


def ar(n, a=0.005, r=0.05):
    e = np.ones(n, np.float32)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[n - nr:] *= np.linspace(1, 0, nr)
    return e


def tvec(dur):
    return np.arange(int(dur * SR), dtype=np.float32) / SR


def swept_noise(dur, f0, f1, rs, width=0.5):
    """White noise through a band that glides from f0 to f1 (log), done in the STFT domain."""
    x = rs.standard_normal(int(dur * SR)).astype(np.float32)
    f, t, z = stft(x, SR, nperseg=1024, noverlap=768)
    fc = f0 * (f1 / f0) ** np.clip(t / dur, 0, 1)
    mask = np.exp(-0.5 * ((np.log(np.maximum(f[:, None], 20)) - np.log(fc[None, :])) / width) ** 2)
    _, y = istft(z * mask, SR, nperseg=1024, noverlap=768)
    y = np.pad(y, (0, max(0, len(x) - len(y))))[:len(x)]
    return y.astype(np.float32)


def norm(x):
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)


# ------------------------------------------------------------------ sound effects (all synthesized)
def fx_thud(o, rs, f=85.0, dur=0.24):
    t = tvec(dur)
    ph = TAU * np.cumsum(o.get("f", f) * (0.5 + 0.5 * np.exp(-t / 0.03))) / SR
    return np.sin(ph) * np.exp(-t / 0.07) + 0.3 * filt(rs.standard_normal(len(t)), "low", 400) * np.exp(-t / 0.012)


def fx_stomp(o, rs):
    t = tvec(0.2)
    return fx_thud({"f": 72}, rs, dur=0.2) + 0.55 * filt(rs.standard_normal(len(t)), "band", [700, 2600]) * np.exp(-t / 0.022)


def fx_step(o, rs):
    t = tvec(0.1)
    return 0.7 * filt(rs.standard_normal(len(t)), "low", 900) * np.exp(-t / 0.018) + 0.5 * fx_thud({"f": 120}, rs, dur=0.1)


def fx_pop(o, rs):
    t = tvec(0.1)
    f = o.get("f", 520) * (1 + 0.6 * np.clip(t / 0.05, 0, 1))
    return np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.03)


def fx_blip(o, rs):
    t = tvec(0.14)
    f = o.get("f", 660)
    return (np.sin(TAU * f * t) + 0.4 * np.sin(TAU * 2 * f * t)) * np.exp(-t / 0.045) * ar(len(t), 0.002, 0.02)


def fx_ding(o, rs):
    t = tvec(o.get("dur", 0.9))
    f = o.get("f", 1320)
    return sum(a * np.sin(TAU * f * k * t) * np.exp(-t / d) for k, a, d in ((1, 1, 0.35), (2.76, 0.5, 0.2), (5.4, 0.25, 0.11), (8.93, 0.12, 0.06)))


def fx_chime(o, rs):
    out = np.zeros(int(0.9 * SR), np.float32)
    for k, f in enumerate((1047, 1319, 1568)):
        d = fx_ding({"f": f, "dur": 0.6}, rs)
        i = int(k * 0.09 * SR)
        out[i:i + len(d)] += d[:len(out) - i]
    return out


def fx_chain(o, rs):
    out = np.zeros(int(0.4 * SR), np.float32)
    for k in range(4):
        d = fx_ding({"f": 2300 + 500 * rs.random(), "dur": 0.12}, rs) * (0.5 + 0.5 * rs.random())
        i = int((k * 0.05 + 0.02 * rs.random()) * SR)
        out[i:i + len(d)] += d[:len(out) - i]
    return out


def fx_squeak(o, rs):
    t = tvec(0.2)
    f = o.get("f", 2100) * (1 + 0.14 * np.sin(TAU * 4.5 * t))
    return np.sin(TAU * np.cumsum(f) / SR) * np.hanning(len(t))


def fx_whoosh(o, rs):
    dur = o.get("dur", 0.5)
    f0, f1 = (5200, 500) if o.get("down") else (500, 5200)
    y = swept_noise(dur, f0, f1, rs)
    return y * np.sin(np.pi * np.arange(len(y)) / len(y)) ** 1.5


def fx_swish(o, rs):
    y = swept_noise(0.22, 1400, 5600, rs, 0.4)
    return y * np.sin(np.pi * np.arange(len(y)) / len(y)) ** 2


def fx_riser(o, rs):
    dur = max(0.3, o.get("dur", 1.0))
    t = tvec(dur)
    y = swept_noise(dur, 300, 6500, rs, 0.45)[:len(t)]
    tone = np.sin(TAU * np.cumsum(180 * (5 ** (t / dur))) / SR)
    return (y + 0.35 * tone) * (t / dur) ** 2 * ar(len(t), 0.01, 0.02)


def fx_boom(o, rs):
    t = tvec(1.2)
    f = 32 + 40 * np.exp(-t / 0.12)
    return np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.4) + 0.5 * filt(rs.standard_normal(len(t)), "low", 220) * np.exp(-t / 0.15)


def fx_rumble(o, rs):
    dur = o.get("dur", 2.0)
    t = tvec(dur)
    y = filt(rs.standard_normal(len(t)), "low", 75, 4)
    return norm(y) * (0.5 + 0.5 * np.sin(np.pi * t / dur)) * ar(len(t), 0.3, 0.3)


def fx_creak(o, rs):
    t = tvec(o.get("dur", 0.55))
    f = o.get("f", 95) * (1 + 0.25 * np.sin(TAU * 2.3 * t) + 0.1 * rs.standard_normal(1)[0])
    y = sawtooth(TAU * np.cumsum(f) / SR)
    y = filt(y, "band", [450, 1900]) * (0.6 + 0.4 * np.sin(TAU * 13 * t) ** 2)
    return y * ar(len(t), 0.06, 0.12)


def fx_drum(o, rs):
    t = tvec(0.17)
    f = 150 + 80 * np.exp(-t / 0.02)
    return 0.8 * np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.06) + 0.7 * filt(rs.standard_normal(len(t)), "band", [1500, 6500]) * np.exp(-t / 0.045)


def fx_snap(o, rs):
    t = tvec(0.45)
    y = filt(rs.standard_normal(len(t)), "high", 2000) * np.exp(-t / 0.006)
    y = y + 0.5 * sum(np.sin(TAU * f * t) * np.exp(-t / 0.09) for f in (1900, 2750, 3900, 5300)) / 4
    return y + 0.6 * np.pad(fx_thud({"f": 130}, rs, dur=0.2), (0, len(t) - int(0.2 * SR)))


def fx_splash(o, rs):
    dur = 1.0
    t = tvec(dur)
    y = swept_noise(dur, 6000, 700, rs, 0.7)[:len(t)] * (1 - np.exp(-t / 0.004)) * np.exp(-t / 0.32)
    for k in range(5):
        p = fx_pop({"f": 280 + 500 * rs.random()}, rs) * 0.25
        i = int((0.15 + 0.6 * rs.random()) * SR)
        y[i:i + len(p)] += p[:len(y) - i]
    return y


def fx_crash(o, rs):
    out = np.zeros(int(0.9 * SR), np.float32)
    for k in range(14):
        n = int((0.03 + 0.08 * rs.random()) * SR)
        lo = 250 + 1500 * rs.random()
        g = filt(rs.standard_normal(n), "band", [lo, lo * 2.4]) * np.exp(-np.arange(n) / (0.02 * SR))
        i = int(0.55 * rs.random() ** 1.6 * SR)
        out[i:i + n] += g[:len(out) - i] * (0.4 + 0.6 * rs.random())
    d = fx_thud({"f": 90}, rs, dur=0.3)
    out[:len(d)] += d
    return out


def fx_neigh(o, rs):
    t = tvec(0.75)
    f = 1100 * (620 / 1100) ** (t / 0.75) * (1 + (0.04 + 0.1 * t) * np.sin(TAU * 14 * t))
    ph = TAU * np.cumsum(f) / SR
    y = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph)
    return filt(y * (0.6 + 0.4 * np.sin(TAU * 23 * t)), "band", [500, 3600]) * ar(len(t), 0.04, 0.2)


def fx_sip(o, rs):
    t = tvec(0.32)
    y = filt(rs.standard_normal(len(t)), "band", [1400, 4200]) * (t / 0.32) ** 1.5 * ar(len(t), 0.01, 0.01)
    p = fx_pop({"f": 700}, rs) * 0.6
    return np.concatenate([y, p])


def fx_loop(kind, dur, rs):
    t = tvec(dur)
    x = rs.standard_normal(len(t)).astype(np.float32)
    if kind == "river":
        y = filt(x, "band", [220, 2600]) * (0.75 + 0.25 * np.sin(TAU * 0.37 * t + 1) * np.sin(TAU * 0.11 * t))
    else:
        y = filt(x, "band", [180, 800]) * (0.6 + 0.4 * np.sin(TAU * 0.19 * t) ** 2)
    return norm(y) * ar(len(t), 0.25, 0.25)


def fx_train(one, o, rs, accent=None):
    """Repeat a one-shot every o['every'] seconds for o['dur'] seconds."""
    dur, every = o["dur"], o["every"]
    out = np.zeros(int((dur + 0.6) * SR), np.float32)
    k = 0
    while k * every < dur:
        d = one(o, rs) * (accent(k) if accent else 1.0)
        i = int(k * every * SR)
        out[i:i + len(d)] += d[:len(out) - i]
        k += 1
    return out


FX = {"thud": fx_thud, "stomp": fx_stomp, "step": fx_step, "pop": fx_pop, "blip": fx_blip, "ding": fx_ding, "chime": fx_chime, "chain": fx_chain, "squeak": fx_squeak,
      "whoosh": fx_whoosh, "swish": fx_swish, "riser": fx_riser, "boom": fx_boom, "rumble": fx_rumble, "creak": fx_creak, "drum": fx_drum, "snap": fx_snap,
      "splash": fx_splash, "crash": fx_crash, "neigh": fx_neigh, "sip": fx_sip}
TRAINS = {"march": (fx_stomp, lambda k: 1.0 if k % 2 == 0 else 0.8), "steps": (fx_step, lambda k: 0.7 + 0.3 * ((k * 7) % 3) / 2), "drums": (fx_drum, lambda k: 1.0 if k % 4 == 0 else 0.6)}


def render_sfx(cues, dur, seed):
    out = np.zeros((int(dur * SR) + SR, 2), np.float32)
    unknown = set()
    for n, c in enumerate(cues):
        rs = np.random.default_rng(seed * 1000 + n)
        kind = c["type"]
        if c.get("loop"):
            y = fx_loop(kind, c["dur"], rs)
        elif kind in TRAINS:
            y = fx_train(TRAINS[kind][0], c, rs, TRAINS[kind][1])
            y = y / (np.abs(y).max() + 1e-9)
        elif kind in FX:
            y = norm(np.asarray(FX[kind](c, rs), np.float32))
        else:
            unknown.add(kind)
            continue
        y = y * db(c.get("gain", -26))
        pan = c.get("pan", (rs.random() - 0.5) * 0.5)             # a little width; the voice stays dead centre
        i = max(0, int(c["t"] * SR))
        y = y[:len(out) - i]
        out[i:i + len(y), 0] += y * np.sqrt(0.5 * (1 - pan)) * 1.414
        out[i:i + len(y), 1] += y * np.sqrt(0.5 * (1 + pan)) * 1.414
    if unknown:
        print("unknown sfx types (skipped):", sorted(unknown))
    return out[:int(dur * SR)]


# ------------------------------------------------------------------ music (original, generated)
NOTE = {"C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
CHORDS = {"Dm": ["D", "F", "A"], "Bb": ["Bb", "D", "F"], "F": ["F", "A", "C"], "C": ["C", "E", "G"], "Gm": ["G", "Bb", "D"], "A": ["A", "C#", "E"], "Am": ["A", "C", "E"]}
PROG = {"A": ["Dm", "Bb", "F", "C"], "B": ["Dm", "Dm", "Gm", "A"], "C": ["F", "C", "Dm", "Bb"], "D": ["Dm", "Am", "Bb", "A"]}


def hz(name, octave):
    return 440.0 * 2 ** ((NOTE[name] - 9) / 12 + (octave - 4))


def add(buf, y, t, g=1.0):
    i = int(t * SR)
    if i < len(buf):
        y = y[:len(buf) - i]
        buf[i:i + len(y)] += y * g


def pluck(f, dur=0.5):
    t = tvec(dur)
    return (np.sin(TAU * f * t) + 0.35 * np.sin(TAU * 2 * f * t) + 0.12 * np.sin(TAU * 3 * f * t)) * np.exp(-t / 0.16) * ar(len(t), 0.003, 0.03)


def mallet(f, dur=0.7):
    t = tvec(dur)
    return (np.sin(TAU * f * t) * np.exp(-t / 0.24) + 0.3 * np.sin(TAU * 4 * f * t) * np.exp(-t / 0.04)) * ar(len(t), 0.002, 0.05)


def pad(freqs, dur):
    t = tvec(dur)
    y = sum(np.sin(TAU * f * t) + np.sin(TAU * f * 1.004 * t + 1) + 0.3 * np.sin(TAU * 2 * f * t) for f in freqs)
    return filt(y, "low", 1300) * ar(len(t), 0.35, 0.45) / len(freqs)


def bass(f, dur):
    t = tvec(dur)
    return (np.sin(TAU * f * t) + 0.3 * np.sin(TAU * 2 * f * t)) * (0.6 + 0.4 * np.exp(-t / 0.25)) * ar(len(t), 0.015, 0.12)


def render_music(dur, sections, bpm, seed):
    """sections: [(start_s, name, layers, gain_db)], layers out of: pluck pad bass shaker kick mallet tremolo."""
    rs = np.random.default_rng(seed)
    beat, bar = 60 / bpm, 240 / bpm
    buf = np.zeros(int(dur * SR) + SR, np.float32)
    nbars = int(np.ceil(dur / bar))
    for b in range(nbars):
        t0 = b * bar
        sec = [s for s in sections if s[0] <= t0 + 1e-6][-1]
        _, name, layers, gdb = sec
        g = db(gdb)
        chord = CHORDS[PROG[name][b % 4]]
        tones = [hz(n, 4 if NOTE[n] < 7 else 3) for n in chord]
        if "pad" in layers:
            add(buf, pad([f / 2 for f in tones], bar + 0.4), t0, 0.5 * g)
        if "tremolo" in layers:
            y = pad(tones, bar + 0.2)
            add(buf, y * (0.55 + 0.45 * np.sin(TAU * 8 * tvec(bar + 0.2)[:len(y)])), t0, 0.6 * g)
        if "bass" in layers:
            for k in ((0, 2) if name in ("B", "D") else (0,)):
                add(buf, bass(hz(chord[0], 2), beat * 1.8), t0 + k * beat, 0.8 * g)
        for k in range(8):
            te = t0 + k * beat / 2
            if "pluck" in layers:
                add(buf, pluck(tones[(0, 2, 1, 2, 0, 2, 1, 2)[k]] * (2 if k in (3, 7) else 1)), te, (0.5 if k % 2 else 0.75) * g)
            if "shaker" in layers:
                n = int(0.05 * SR)
                add(buf, filt(rs.standard_normal(n), "high", 6000) * np.exp(-np.arange(n) / (0.012 * SR)), te, (0.1 if k % 2 == 0 else 0.2) * g)
        if "kick" in layers:
            for k in range(4):
                add(buf, fx_thud({"f": 58}, rs, dur=0.2), t0 + k * beat, 0.5 * g)
        if "mallet" in layers:
            motif = ((0, 2), (1, 1), (2, 2), (3, 0)) if b % 2 == 0 else ((0, 1), (1.5, 2), (2, 1), (3, 0))
            for k, i in motif:
                add(buf, mallet(tones[i] * 2), t0 + k * beat, 0.55 * g)
    y = filt(buf[:int(dur * SR)], "high", 45)
    st = np.stack([y, y], 1)
    st[:, 0] += 0.12 * np.roll(y, 441)                       # a touch of width
    st[:, 1] += 0.12 * np.roll(y, 613)
    return st.astype(np.float32)


def sections_from(sent, dur):
    """Map story beats (script.json 'beat' of each sentence) to music sections."""
    def first(beat, dflt):
        return next((s["start"] for s in sent if s.get("beat") == beat), dflt)
    t_conf, t_esc, t_q = first("conflict", dur * 0.28), first("escalation", dur * 0.42), first("question", dur * 0.62)
    t_exp, t_pay, t_end = first("explainer", dur * 0.66), first("payoff", dur * 0.82), first("ending", dur * 0.95)
    sec = [(0.0, "A", {"pluck"}, 0.0), (min(4.2, t_conf * 0.25), "A", {"pluck", "pad"}, 0.0), (t_conf, "A", {"pluck", "pad", "bass", "shaker"}, 1.0),
           (t_esc, "B", {"pluck", "bass", "kick", "shaker", "pad"}, 3.0), (t_q, "D", {"pad"}, -3.0), (t_exp, "C", {"mallet", "pad", "shaker"}, 0.0),
           (t_pay, "B", {"tremolo", "bass", "kick", "pluck"}, 4.0), (t_end, "C", {"mallet", "pluck", "pad", "bass"}, 1.0)]
    return sorted(sec, key=lambda s: s[0])


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--bpm", type=float, default=116)
    ap.add_argument("--music-lu", dest="music_lu", type=float, default=19.4, help="music this many LU under the voice")
    ap.add_argument("--lufs", type=float, default=-14.1)
    ap.add_argument("--peak", type=float, default=-2.1, help="true-peak ceiling, dBTP")
    ap.add_argument("--sfx-db", dest="sfx_db", type=float, default=0.0, help="trim for all effects, dB")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--video", default="video.mp4", help="picture to add the sound to (a preview must start at frame 0)")
    a = ap.parse_args()
    proj = Path(a.project)
    sent = json.loads((proj / "sentences.json").read_text())
    tl = json.loads((proj / "timeline.json").read_text())
    v, sr = sf.read(proj / "voice_dry.wav", dtype="float32")
    assert sr == SR
    dur = len(v) / SR
    # voice: high-pass, warmth, air, 3.5:1 compression, then level
    v = filt(v, "high", 70)
    v = biquad(v, "peak", 210, 2.0, 0.9)
    v = biquad(v, "peak", 900, -1.5, 1.0)
    v = biquad(v, "high", 6500, 3.5, 0.7)
    v = compress(v, thr=-26, ratio=3.5)
    voice = np.stack([v, v], 1)
    voice *= db(a.lufs - 0.2 - lufs(voice))
    music = render_music(dur, sections_from(sent, dur), a.bpm, a.seed)
    music *= db(lufs(voice) - a.music_lu - lufs(music))
    sfx = render_sfx(tl["sfx"], dur, a.seed) * db(a.sfx_db)
    mix = voice + music + sfx
    mix *= db(a.lufs - lufs(mix))
    for _ in range(4):                                         # limiter, then re-level; converges in 2-3 passes
        mix = limit(mix, a.peak - 0.15)
        mix *= db(np.clip(a.lufs - lufs(mix), -2, 2))
    mix = limit(mix, a.peak - 0.05)
    over = true_peak_db(mix) - a.peak
    if over > 0:                                               # gain smoothing can let a few hundredths of a dB through
        mix *= db(-over)
    n = int(0.01 * SR)
    mix[-n:] *= np.linspace(1, 0, n)[:, None]
    for name, x in (("voice", voice), ("music", music), ("sfx", sfx), ("mix", mix)):
        sf.write(proj / f"{name}.wav", x, SR, subtype="PCM_24")
    rep = {"duration_s": round(dur, 3), "mix_lufs": round(lufs(mix), 2), "true_peak_dbtp": round(true_peak_db(mix), 2), "voice_lufs": round(lufs(voice), 2),
           "music_lufs": round(lufs(music), 2), "sfx_cues": len(tl["sfx"]), "bpm": a.bpm}
    (proj / "mix_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep))
    if not a.no_video and (proj / a.video).exists():
        out = proj / ("final.mp4" if a.video == "video.mp4" else Path(a.video).stem + "_sound.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(proj / a.video), "-i", str(proj / "mix.wav"), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                        "-shortest", "-movflags", "+faststart", str(out)], check=True)
        print("wrote", out)


if __name__ == "__main__":
    main()
