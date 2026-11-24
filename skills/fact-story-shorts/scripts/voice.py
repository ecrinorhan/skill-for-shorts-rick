#!/usr/bin/env python3
"""Narration for a fact-story Short: script.json -> voice.wav, words.json, sentences.json, captions.json

  voice.py probe <out_dir> [voice ...]        compare TTS voices on a test paragraph (natural WPM, F0 median, F0 range)
  voice.py build <project_dir> [--voice af_heart] [--wpm 222] [--clips voice_in/]

build
  1. speaks every sentence (Kokoro TTS, Apache-2.0), or takes your own recording cut into one file per sentence
     (--clips folder with 01.wav, 02.wav ... in script order)
  2. removes pauses: none longer than 80 ms inside a sentence, 60 ms between sentences (the reference style has no pause
     of 250 ms or more anywhere and the voice is on for 98 % of the runtime); the pauses left are measured and reported
  3. sets the pace to the target words per minute
  4. force-aligns every word (wav2vec2 base through torchaudio; MIT-licensed weights, about 360 MB, fetched on first use)
     and groups words into 1-2 word captions

Kokoro model files (kokoro-v1.0.onnx, voices-v1.0.bin) are looked up in $KOKORO_DIR, then in <skill>/models/kokoro
(scripts/install.py downloads them there).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

FPS = 30
SR = 44100
TARGETS = json.loads((Path(__file__).resolve().parents[1] / "references" / "style_targets.json").read_text()) if (Path(__file__).resolve().parents[1] / "references" / "style_targets.json").exists() else {}
CAP = TARGETS.get("caption_rule", {"SHORT": 2, "MAXCHARS": 8, "MAX3": 12, "stop_punct": ".?!,", "lead_frames": 3.7})
PROBE_TEXT = ("He stopped an army at his bridge and ordered every soldier to march out of step. The colonel just laughs. "
              "My men walk in step or they don't walk! But the keeper won't move. So how do boots break iron? "
              "Well, ever pushed a kid on a swing? Push at the same moment every time, and she flies.")


# ---------------------------------------------------------------- audio helpers
def clean(x, sr):
    """Remove DC and sub-audio rumble. Some TTS model builds and most microphones add an offset; with an offset the
    'silence' between words is never quiet, so trimming and pause removal would silently stop working."""
    return sosfiltfilt(butter(2, 60, btype="high", fs=sr, output="sos"), np.asarray(x, np.float64)).astype(np.float32)


def pause_stats(x, sr, floor_db=-35.0):
    """Silent stretches in the finished track (quieter than floor_db below the loud parts), in the reference's terms."""
    hop, win = int(0.005 * sr), int(0.02 * sr)
    n = max(1, (len(x) - win) // hop)
    rms = np.array([np.sqrt(np.mean(x[i * hop:i * hop + win] ** 2)) for i in range(n)])
    quiet = rms < np.percentile(rms, 90) * 10 ** (floor_db / 20)
    runs, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if i > 0 and j < n:                       # the head and the tail of the file are not pauses
                runs.append((j - i) * hop / sr)
            i = j
        else:
            i += 1
    return {"longest_pause_ms": int(round(1000 * max(runs, default=0))), "pauses_ge_120ms": int(sum(r >= 0.12 for r in runs)),
            "pauses_ge_250ms": int(sum(r >= 0.25 for r in runs))}


def trim(x, sr, db=-42.0, pad=0.012):
    thr = np.abs(x).max() * 10 ** (db / 20)
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    a, b = max(0, idx[0] - int(pad * sr)), min(len(x), idx[-1] + int(pad * sr))
    y = x[a:b].copy()
    f = int(0.004 * sr)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def tighten(x, sr, max_gap=0.08, floor_db=-40.0):
    """Shorten every internal silence longer than max_gap to max_gap (10 ms crossfades)."""
    hop = int(0.005 * sr)
    win = int(0.02 * sr)
    n = max(1, (len(x) - win) // hop)
    rms = np.array([np.sqrt(np.mean(x[i * hop:i * hop + win] ** 2)) for i in range(n)])
    quiet = rms < np.percentile(rms, 90) * 10 ** (floor_db / 20)
    out, i, pos = [], 0, 0
    xf = int(0.01 * sr)
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            dur = (j - i) * hop / sr
            if dur > max_gap and i > 0 and j < n:
                a = i * hop + int(max_gap / 2 * sr)
                b = j * hop + win - int(max_gap / 2 * sr)
                if b - a > 2 * xf:
                    seg = x[pos:a].copy()
                    seg[-xf:] *= np.linspace(1, 0, xf)
                    out.append(seg)
                    nxt = x[b:b + xf] * np.linspace(0, 1, xf) if b + xf <= len(x) else x[b:]
                    out.append(nxt)
                    pos = b + len(nxt)
            i = j
        else:
            i += 1
    out.append(x[pos:])
    return np.concatenate(out)


def f0_stats(x, sr):
    import parselmouth
    f0 = parselmouth.Sound(x.astype(np.float64), sampling_frequency=sr).to_pitch(0.01, 75, 500).selected_array["frequency"]
    v = f0[f0 > 0]
    if len(v) == 0:
        return None, None
    st = 12 * np.log2(v / np.median(v))
    return float(np.median(v)), float(np.percentile(st, 95) - np.percentile(st, 5))


def reshape_pitch(x, sr, shift_st=0.0, expand=1.0):
    """Shift the pitch and widen the melody around its median with Praat overlap-add; timing is untouched."""
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(x.astype(np.float64), sampling_frequency=sr)
    manip = call(snd, "To Manipulation", 0.01, 75, 600)
    tier = call(manip, "Extract pitch tier")
    n = call(tier, "Get number of points")
    med = float(np.median([call(tier, "Get value at index", i) for i in range(1, n + 1)]))
    call(tier, "Formula", f"min(520, max(70, {med * 2 ** (shift_st / 12):.3f} * (self / {med:.3f}) ^ {expand:.4f}))")
    call([tier, manip], "Replace pitch tier")
    return call(manip, "Get resynthesis (overlap-add)").values[0].astype(np.float32)


def rubberband(x, sr, tempo=1.0, pitch=0.0):
    if abs(tempo - 1) < 0.004 and abs(pitch) < 0.05:
        return x
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "a.wav", Path(td) / "b.wav"
        sf.write(a, x, sr)
        cmd = ["rubberband", "-q", "--tempo", f"{tempo:.4f}", "-p", f"{pitch:.3f}", "-F", str(a), str(b)]
        subprocess.run(cmd, check=True, capture_output=True)
        y, _ = sf.read(b, dtype="float32")
    return y


def words_of(text):
    return [w for w in text.split() if re.search(r"[A-Za-z0-9]", w)]


# ---------------------------------------------------------------- TTS
class Tts:
    def __init__(self):
        from kokoro_onnx import Kokoro
        d = Path(os.environ.get("KOKORO_DIR") or Path(__file__).resolve().parents[1] / "models" / "kokoro")
        if not (d / "kokoro-v1.0.onnx").exists():
            raise SystemExit(f"Kokoro model files not found in {d}. Run scripts/install.py or set KOKORO_DIR.")
        self.k = Kokoro(str(d / "kokoro-v1.0.onnx"), str(d / "voices-v1.0.bin"))
        self.sr = 24000

    def say(self, text, voice, speed=1.0):
        x, sr = self.k.create(text, voice=voice, speed=float(speed), lang="en-us")
        self.sr = sr
        return np.asarray(x, np.float32)


# ---------------------------------------------------------------- alignment
def spoken(tok):
    from num2words import num2words
    t = tok.lower().replace("%", " percent").replace("$", " dollars ").replace("&", " and ")

    def rep(m):
        s = m.group(0).replace(",", "")
        try:
            if re.fullmatch(r"\d+(st|nd|rd|th)", s):
                return num2words(int(s[:-2]), to="ordinal")
            if re.fullmatch(r"(1[0-9]|20)\d\ds?", s):      # years and decades are spoken as "nineteen oh two", "eighteen hundreds"
                return num2words(int(s.rstrip("s")), to="year") + ("s" if s.endswith("s") else "")
            return num2words(float(s) if "." in s else int(re.sub(r"\D", "", s)))
        except Exception:  # noqa: BLE001
            return s
    t = re.sub(r"\d[\d,]*(\.\d+)?(st|nd|rd|th|s)?", rep, t)
    t = re.sub(r"[^a-z' ]", " ", t)
    return [w.strip("'") for w in t.split() if w.strip("'")]


def align(x, sr, tokens):
    """(start, end) in seconds for every token, by CTC forced alignment against the letters of its spoken form."""
    import torch
    import torchaudio
    b = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H          # English; weights under the MIT licence
    model = b.get_model().eval()
    idx = {c: i for i, c in enumerate(b.get_labels())}      # '-' blank, '|' word break, A-Z, apostrophe
    wav = torchaudio.functional.resample(torch.from_numpy(x.astype(np.float32)), sr, 16000)
    lists = [[w.upper() for w in spoken(t)] for t in tokens]
    target = [idx[c] for c in "|".join(w for l in lists for w in l)]
    with torch.inference_mode():
        em, _ = model(wav[None])
        ali, score = torchaudio.functional.forced_align(torch.log_softmax(em, dim=-1), torch.tensor([target], dtype=torch.int32), blank=0)
    spans = torchaudio.functional.merge_tokens(ali[0], score[0].exp())
    if len(spans) != len(target):
        raise SystemExit("word alignment failed: the narration audio does not match the script text")
    ratio = len(wav) / em.size(1) / 16000
    out, k = [], 0
    for l in lists:
        if not l:
            out.append(None)
            continue
        n = sum(len(w) for w in l) + len(l) - 1               # letters, plus the breaks between the words of one token
        out.append((round(ratio * spans[k].start, 3), round(ratio * spans[k + n - 1].end, 3)))
        k += n + 1                                            # the break after the token
    return out


# ---------------------------------------------------------------- captions
def letters(t):
    return re.sub(r"[^A-Za-z0-9']", "", t)


def group_captions(words):
    caps, i = [], 0
    while i < len(words):
        cur = [i]
        while len(cur) < 3 and cur[-1] + 1 < len(words):
            a, b = words[cur[-1]]["text"], words[cur[-1] + 1]["text"]
            if a.rstrip("\"'”’")[-1:] in CAP["stop_punct"]:
                break
            text = " ".join(words[k]["text"] for k in cur) + " " + b
            la, lb = len(letters(a)), len(letters(b))
            if len(cur) == 1:
                ok = min(la, lb) <= CAP["SHORT"] and len(text) <= CAP["MAXCHARS"]
            else:
                ok = CAP["MAX3"] > 0 and max(len(letters(words[k]["text"])) for k in cur) <= 4 and lb <= 5 and len(text) <= CAP["MAX3"]
            if not ok:
                break
            cur.append(cur[-1] + 1)
        caps.append(cur)
        i = cur[-1] + 1
    return caps


def build_captions(words, duration):
    lead = CAP.get("lead_frames", 3.7) / FPS
    out = []
    for idx in group_captions(words):
        on_f = max(0, round((words[idx[0]]["start"] - lead) * FPS))
        if out:
            on_f = max(on_f, out[-1]["on_f"] + 2)
        out.append({"text": " ".join(words[k]["text"] for k in idx), "on_f": int(on_f), "words": idx})
    out[0]["on_f"] = 0                                  # the first word is on screen in frame 0
    last = int(round(duration * FPS))
    for a, b in zip(out[:-1], out[1:]):
        a["off_f"] = b["on_f"]
    out[-1]["off_f"] = last
    for c in out:
        c["on"], c["off"] = round(c["on_f"] / FPS, 4), round(c["off_f"] / FPS, 4)
    return out


# ---------------------------------------------------------------- commands
def probe(out_dir, voices):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tts = Tts()
    voices = voices or ["af_heart", "af_bella", "af_nova", "af_sarah", "af_nicole", "am_michael", "am_puck", "am_fenrir", "am_adam", "bm_george", "bf_emma"]
    nw = len(words_of(PROBE_TEXT))
    print(f"{'voice':<12}{'natural WPM':>12}{'F0 median Hz':>14}{'F0 range st':>13}")
    rows = []
    for v in voices:
        try:
            parts = [tighten(trim(clean(tts.say(s.strip(), v), tts.sr), tts.sr), tts.sr) for s in re.split(r"(?<=[.!?])\s+", PROBE_TEXT) if s.strip()]
        except Exception as e:  # noqa: BLE001
            print(v, "failed:", str(e)[:80])
            continue
        gap = np.zeros(int(0.09 * tts.sr), np.float32)
        x = np.concatenate([p for part in parts for p in (part, gap)])
        f0, rng = f0_stats(x, tts.sr)
        wpm = nw / (len(x) / tts.sr) * 60
        sf.write(out_dir / f"probe_{v}.wav", x, tts.sr)
        rows.append({"voice": v, "natural_wpm": round(wpm, 1), "f0_median_hz": round(f0, 1), "f0_range_st": round(rng, 1)})
        print(f"{v:<12}{wpm:>12.1f}{f0:>14.1f}{rng:>13.1f}")
    (out_dir / "probe.json").write_text(json.dumps(rows, indent=1))


def build(args):
    proj = Path(args.project)
    script = json.loads((proj / "script.json").read_text())
    sents = script["sentences"]
    voice = args.voice or script.get("voice", "af_heart")
    gap_s = args.gap
    nwords = sum(len(words_of(s["text"])) for s in sents)
    target_dur = nwords / args.wpm * 60
    tts = None if args.clips else Tts()

    def render(speed):
        parts = []
        for i, s in enumerate(sents):
            if args.clips:
                x, sr = sf.read(Path(args.clips) / f"{i + 1:02d}.wav", dtype="float32", always_2d=True)
                x, sr = x.mean(axis=1), sr
            else:
                x, sr = tts.say(s["text"], s.get("voice", voice), speed * s.get("speed", 1.0)), tts.sr
            x = tighten(trim(clean(x, sr), sr), sr, max_gap=args.max_gap)
            if s.get("pitch"):
                x = rubberband(x, sr, 1.0, s["pitch"])
            parts.append(librosa.resample(x, orig_sr=sr, target_sr=SR) if sr != SR else x)
        return parts

    parts = render(1.0)
    speech = sum(len(p) for p in parts) / SR
    gaps = gap_s * (len(parts) - 1)
    speed = speech / max(target_dur - gaps - args.head - args.tail, 1.0)
    if not args.clips and abs(speed - 1) > 0.01:
        parts = render(speed)
        speech = sum(len(p) for p in parts) / SR
    resid = speech / max(target_dur - gaps - args.head - args.tail, 1.0)      # finish with a small time-stretch
    if args.clips and not 0.92 <= resid <= 1.15:
        print(f"note: your recording runs at {nwords / ((speech + gaps) / 60):.0f} words per minute after pauses are removed; "
              f"stretching is limited to keep it natural, so the result will not reach {args.wpm:.0f}. Re-record faster or slower.")
        resid = min(max(resid, 0.92), 1.15)
    if abs(resid - 1) > 0.006:
        parts = [rubberband(p, SR, tempo=resid) for p in parts]
    track, sent_times = [np.zeros(int(args.head * SR), np.float32)], []
    pos = args.head
    for i, p in enumerate(parts):
        sent_times.append({"i": i, "start": round(pos, 3), "end": round(pos + len(p) / SR, 3), "text": sents[i]["text"], "beat": sents[i].get("beat")})
        track.append(p)
        pos += len(p) / SR
        if i < len(parts) - 1:
            track.append(np.zeros(int(gap_s * SR), np.float32))
            pos += gap_s
    track.append(np.zeros(int(args.tail * SR), np.float32))
    x = np.concatenate(track)
    f0, rng_st = f0_stats(x, SR)
    shift = 12 * np.log2(args.f0 / f0) if args.f0 and f0 else 0.0
    expand = float(np.clip(args.f0_range / rng_st, 1.0, 1.7)) if args.f0_range and rng_st and not args.clips else 1.0
    if abs(shift) > 0.3 or expand > 1.05:      # the reference narration moves over 16 semitones; flat TTS reads as flat
        x = reshape_pitch(x, SR, shift if abs(shift) > 0.3 else 0.0, expand)
    x = x / (np.abs(x).max() + 1e-9) * 0.7
    duration = len(x) / SR
    sf.write(proj / "voice_dry.wav", x, SR)
    tokens = [(w, i) for i, s in enumerate(sents) for w in words_of(s["text"])]
    al = align(x, SR, [t for t, _ in tokens])
    words = []
    for (t, si), a in zip(tokens, al):
        st, en = a if a else (sent_times[si]["start"], sent_times[si]["end"])
        words.append({"text": t, "start": st, "end": en, "sentence": si})
    for s in sent_times:                                   # sentence anchors from the aligned words (what the storyboard uses)
        ws = [w for w in words if w["sentence"] == s["i"]]
        s["start"], s["end"] = ws[0]["start"], ws[-1]["end"]
    caps = build_captions(words, duration)
    f0, rng = f0_stats(x, SR)
    meta = {"voice": voice, "speed": round(float(speed), 3), "stretch": round(float(resid), 3), "words": len(words), "duration_s": round(duration, 3),
            "frames": int(round(duration * FPS)), "wpm": round(len(words) / duration * 60, 1), "f0_median_hz": round(f0, 1) if f0 else None,
            "f0_range_st": round(rng, 1) if rng else None, "captions": len(caps), "words_per_caption": round(len(words) / len(caps), 3), **pause_stats(x, SR)}
    if meta["pauses_ge_250ms"]:
        print(f"warning: {meta['pauses_ge_250ms']} pause(s) of 250 ms or more are left (longest {meta['longest_pause_ms']} ms). The reference has none: "
              "check for commas or dashes that make the voice stop, or lower --max-gap.")
    (proj / "words.json").write_text(json.dumps(words, indent=1))
    (proj / "sentences.json").write_text(json.dumps(sent_times, indent=1))
    (proj / "captions.json").write_text(json.dumps(caps, indent=1))
    (proj / "voice_meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "probe":
        return probe(sys.argv[2], sys.argv[3:])
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("project")
    ap.add_argument("--voice")
    ap.add_argument("--wpm", type=float, default=TARGETS.get("wpm", 222))
    ap.add_argument("--gap", type=float, default=0.06, help="silence between sentences, seconds")
    ap.add_argument("--max-gap", dest="max_gap", type=float, default=0.08, help="longest silence allowed inside a sentence")
    ap.add_argument("--head", type=float, default=0.08, help="silence before the first word")
    ap.add_argument("--tail", type=float, default=0.18, help="silence after the last word")
    ap.add_argument("--f0", type=float, default=None, help="move the median pitch to this many Hz (off by default)")
    ap.add_argument("--f0-range", dest="f0_range", type=float, default=TARGETS.get("voice_f0_range_st", 16.1), help="widen a TTS voice to this p5-p95 pitch range in semitones (0 = leave as is)")
    ap.add_argument("--clips", help="folder with your own recording cut into 01.wav, 02.wav ... (one file per sentence)")
    build(ap.parse_args())


if __name__ == "__main__":
    main()
