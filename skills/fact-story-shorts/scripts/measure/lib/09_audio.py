#!/usr/bin/env python3
"""Audio measurements per video: mix loudness, stems, voice, music bed, SFX events.

Usage: 09_audio.py <work_dir> [jobs=6] [only=<video-stem>]
Reads  <video>/audio.wav, <video>/stems/{vocals,no_vocals,drums,bass,other}.wav, <video>/whisper.json
Writes <video>/audio.json

Everything here is measured from the published AAC audio and from Demucs stems. Stem leakage means stem levels
carry roughly +-1.5 dB of uncertainty; labels on SFX events are heuristic classes (estimates), the timestamps are measured.
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln
import scipy.signal as sps
import soundfile as sf

HOP_S = 0.010           # 10 ms envelope hop
WIN_S = 0.050           # 50 ms RMS window
BANDS = [(20, 80), (80, 160), (160, 315), (315, 630), (630, 1250), (1250, 2500), (2500, 5000), (5000, 10000), (10000, 16000), (16000, 20000)]
KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-9))


def rms_env(y, sr):
    """50 ms RMS every 10 ms, dBFS."""
    hop, win = int(HOP_S * sr), int(WIN_S * sr)
    sq = np.concatenate([[0.0], np.cumsum(y.astype(np.float64) ** 2)])
    idx = np.arange(0, len(y) - win, hop)
    return db(np.sqrt((sq[idx + win] - sq[idx]) / win)), (idx + win / 2) / sr


def runs(mask, min_len):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    if start is not None and len(mask) - start >= min_len:
        out.append((start, len(mask)))
    return out


def ebur128(path):
    p = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    tail = p.stderr[p.stderr.rfind("Summary:"):]
    def grab(pat):
        m = re.search(pat, tail)
        return float(m.group(1)) if m else None
    return {"integrated_lufs": grab(r"I:\s+(-?[\d.]+) LUFS"), "lra_lu": grab(r"LRA:\s+(-?[\d.]+) LU"),
            "true_peak_dbtp": grab(r"Peak:\s+(-?[\d.]+) dBFS")}


def lufs(y, sr):
    try:
        return round(float(pyln.Meter(sr).integrated_loudness(y)), 2)
    except Exception:  # noqa: BLE001
        return None


def band_levels(y, sr, mask_t=None):
    f, t, Z = sps.stft(y, sr, nperseg=4096, noverlap=2048)
    P = np.abs(Z) ** 2
    if mask_t is not None:
        keep = np.interp(t, mask_t[1], mask_t[0].astype(float)) > 0.5
        if keep.sum() > 10:
            P = P[:, keep]
    psd = P.mean(axis=1)
    tot = psd[(f >= 20) & (f <= 20000)].sum() + 1e-18
    out = {f"{lo}-{hi}Hz": round(float(10 * np.log10(psd[(f >= lo) & (f < hi)].sum() / tot + 1e-12)), 1) for lo, hi in BANDS}
    spec_db = 10 * np.log10(psd + 1e-18)
    peak = spec_db[(f > 100) & (f < 5000)].max()
    above = np.where((spec_db > peak - 60) & (f > 1000))[0]
    cutoff = float(f[above.max()]) if len(above) else None
    centroid = float((f * psd).sum() / (psd.sum() + 1e-18))
    return out, cutoff, centroid


def voice_analysis(voc, sr, words):
    env, t = rms_env(voc, sr)
    speech_level = np.percentile(env, 90)
    active = env > speech_level - 32            # voice-active frames
    active = sps.medfilt(active.astype(float), 5) > 0.5
    first = t[np.argmax(active)] if active.any() else 0.0
    last = t[len(active) - 1 - np.argmax(active[::-1])] if active.any() else 0.0
    inside = (t >= first) & (t <= last)
    gaps = [(t[a], t[b - 1] + HOP_S) for a, b in runs(~active & inside, int(0.12 / HOP_S))]
    gap_d = np.array([b - a for a, b in gaps]) if gaps else np.array([])
    sp = env[active]
    # pitch
    y22 = librosa.resample(voc, orig_sr=sr, target_sr=22050)
    f0, vflag, vprob = librosa.pyin(y22, fmin=60, fmax=450, sr=22050, frame_length=2048, hop_length=256)
    f0v = f0[vflag & ~np.isnan(f0)]
    st = 12 * np.log2(f0v / np.median(f0v)) if len(f0v) else np.array([0.0])
    ft = librosa.frames_to_time(np.arange(len(f0)), sr=22050, hop_length=256)
    # words
    nw = len(words)
    dur_speech = float(active.sum() * HOP_S)
    span = (words[-1]["end"] - words[0]["start"]) if nw else 0.0
    syl = sum(max(1, len(re.findall(r"[aeiouy]+", re.sub(r"e\b", "", w["w"].lower())))) for w in words)
    bands, cutoff, centroid = band_levels(voc, sr, (active, t))
    # decay after phrase ends -> crude reverb/tail estimate
    slopes = []
    for a, b in gaps:
        if b - a < 0.2:
            continue
        i0 = int(np.searchsorted(t, a))
        seg = env[i0:i0 + int(0.15 / HOP_S)]
        if len(seg) >= 8 and seg[0] - seg[-1] > 6:
            slopes.append(np.polyfit(np.arange(len(seg)) * HOP_S, seg, 1)[0])
    # breaths: quiet noisy bursts inside gaps (80-450 ms, 18-40 dB below speech level)
    breaths = 0
    for a, b in gaps:
        i0, i1 = int(np.searchsorted(t, a)), int(np.searchsorted(t, b))
        seg = env[i0:i1]
        mid = (seg > speech_level - 42) & (seg < speech_level - 18)
        if any(0.08 <= (e - s) * HOP_S <= 0.45 for s, e in runs(mid, int(0.08 / HOP_S))):
            breaths += 1
    peak = float(np.max(np.abs(voc)) + 1e-9)
    rep = np.repeat(active, int(HOP_S * sr))
    smask = np.zeros(len(voc), bool)
    smask[:min(len(rep), len(voc))] = rep[:len(voc)]
    return {
        "first_voice_s": round(float(first), 3), "last_voice_s": round(float(last), 3),
        "voice_active_s": round(dur_speech, 2), "voice_active_frac_of_video": round(dur_speech / (len(voc) / sr), 3),
        "level_p10_p50_p90_dbfs": [round(float(np.percentile(sp, p)), 1) for p in (10, 50, 90)],
        "level_spread_p90_p10_db": round(float(np.percentile(sp, 90) - np.percentile(sp, 10)), 1),
        "crest_factor_db": round(float(db(peak) - db(np.sqrt(np.mean(voc[smask] ** 2)))), 1) if smask.any() else None,
        "f0_median_hz": round(float(np.median(f0v)), 1) if len(f0v) else None,
        "f0_p05_p95_hz": [round(float(np.percentile(f0v, p)), 1) for p in (5, 95)] if len(f0v) else None,
        "f0_range_p05_p95_semitones": round(float(np.percentile(st, 95) - np.percentile(st, 5)), 1),
        "f0_sd_semitones": round(float(st.std()), 2),
        "voiced_frac_of_speech": round(float(vflag.sum() * 256 / 22050 / max(dur_speech, 1e-3)), 3),
        "words": nw, "syllables_est": syl,
        "wpm_overall": round(nw / (len(voc) / sr) * 60, 1),
        "wpm_first_to_last_word": round(nw / max(span, 1e-3) * 60, 1),
        "wpm_articulation": round(nw / max(dur_speech, 1e-3) * 60, 1),
        "syll_per_s_articulation": round(syl / max(dur_speech, 1e-3), 2),
        "pauses_ge_120ms": int(len(gap_d)), "pauses_ge_250ms": int((gap_d >= 0.25).sum()), "pauses_ge_400ms": int((gap_d >= 0.4).sum()),
        "pause_median_s": round(float(np.median(gap_d)), 3) if len(gap_d) else 0.0,
        "pause_max_s": round(float(gap_d.max()), 3) if len(gap_d) else 0.0,
        "pause_total_s": round(float(gap_d.sum()), 2),
        "pauses": [{"start": round(float(a), 3), "dur": round(float(b - a), 3)} for a, b in gaps if b - a >= 0.2],
        "ltas_band_db_rel_total": bands, "hf_cutoff_hz_at_-60db": cutoff, "spectral_centroid_hz": round(centroid, 0),
        "tail_decay_db_per_s_median": round(float(np.median(slopes)), 0) if slopes else None,
        "tail_rt60_est_s": round(float(60 / abs(np.median(slopes))), 3) if slopes else None,
        "breath_like_events": breaths,
        "_active": active, "_t": t, "_env": env, "_f0": (ft, f0),
    }


def key_estimate(y, sr):
    yh = librosa.effects.harmonic(y, margin=3.0)
    chroma = librosa.feature.chroma_cqt(y=yh, sr=sr, hop_length=2048).mean(axis=1)
    scores = []
    for i in range(12):
        scores.append((float(np.corrcoef(np.roll(KS_MAJOR, i), chroma)[0, 1]), f"{NOTES[i]} major"))
        scores.append((float(np.corrcoef(np.roll(KS_MINOR, i), chroma)[0, 1]), f"{NOTES[i]} minor"))
    scores.sort(reverse=True)
    return {"key": scores[0][1], "score": round(scores[0][0], 3), "second": scores[1][1], "second_score": round(scores[1][0], 3),
            "chroma": [round(float(c), 3) for c in chroma / (chroma.max() + 1e-9)]}


def tempo_estimate(y, sr):
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=512)
    tempo = float(np.atleast_1d(tempo)[0])
    ac = librosa.autocorrelate(oenv, max_size=int(4 * sr / 512))
    ac = ac / (ac[0] + 1e-9)
    lags = np.arange(len(ac))
    bpm = 60.0 * sr / 512 / np.maximum(lags, 1)
    sel = (bpm >= 55) & (bpm <= 200)
    order = np.argsort(ac[sel])[::-1][:3]
    cands = [(round(float(bpm[sel][i]), 1), round(float(ac[sel][i]), 3)) for i in order]
    return {"bpm": round(tempo, 1), "beat_count": int(len(beats)), "autocorr_candidates_bpm_strength": cands,
            "pulse_strength": cands[0][1] if cands else 0.0}, librosa.frames_to_time(beats, sr=sr, hop_length=512)


def sfx_class(dur, attack, cent, slope, flat, lf, hf):
    """Coarse, heuristic label (estimate) from duration / attack / spectrum of one event."""
    if dur < 0.10:
        return "click/pop/tick" if cent > 1500 else "thud/tap"
    if lf > 0.45 and attack < 0.08:
        return "impact/boom/thump"
    if dur >= 0.35 and attack > 0.6 * dur:
        return "riser/swell"
    if flat > 0.06 and dur <= 1.5:
        if slope > 1500:
            return "whoosh (rising)"
        if slope < -1500:
            return "whoosh (falling)"
        return "whoosh/noise burst"
    if flat < 0.02 and cent > 1500:
        return "ding/chime/bell (tonal)"
    if dur > 1.5:
        return "sustained ambience/rumble" if cent < 1200 else "sustained hiss/noise"
    if lf > 0.35:
        return "low hit/rumble"
    return "foley/other"


def sfx_events(sfx, sr):
    """Events on the effects stem: 50 ms RMS above -50 dBFS (released below -56 dBFS), >= 40 ms, gaps < 80 ms merged."""
    env, t = rms_env(sfx, sr)
    on = env > -50
    keep = env > -56
    spans = []
    for a, b in runs(on, 2):
        while a > 0 and keep[a - 1]:
            a -= 1
        while b < len(env) and keep[b]:
            b += 1
        if spans and a - spans[-1][1] <= int(0.08 / HOP_S):
            spans[-1] = (spans[-1][0], max(b, spans[-1][1]))
        else:
            spans.append((a, b))
    S = np.abs(librosa.stft(sfx, n_fft=2048, hop_length=441)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    events = []
    for a, b in spans:
        dur = float((b - a) * HOP_S)
        if dur < 0.04:
            continue
        seg = S[:, a:b + 5]
        pw = seg.sum(axis=1) + 1e-18
        cent_t = (freqs[:, None] * seg).sum(axis=0) / (seg.sum(axis=0) + 1e-18)
        cent = float((freqs * pw).sum() / pw.sum())
        flat = float(np.exp(np.mean(np.log(pw[5:700] + 1e-18))) / (np.mean(pw[5:700]) + 1e-18))
        lf = float(pw[freqs < 150].sum() / pw.sum())
        hf = float(pw[freqs > 4000].sum() / pw.sum())
        pk = int(np.argmax(env[a:b]))
        attack = float(pk * HOP_S)
        slope = float(np.polyfit(np.arange(len(cent_t)) * 441 / sr, cent_t, 1)[0]) if len(cent_t) > 4 else 0.0
        events.append({
            "start": round(float(t[a]), 3), "end": round(float(t[min(b, len(t) - 1)]), 3), "dur": round(dur, 3),
            "peak_t": round(float(t[a + pk]), 3), "peak_dbfs": round(float(env[a + pk]), 1), "attack_s": round(attack, 3),
            "centroid_hz": round(cent), "centroid_slope_hz_per_s": round(slope), "flatness": round(flat, 3),
            "lf_share": round(lf, 2), "hf_share": round(hf, 2),
            "class_est": sfx_class(dur, attack, cent, slope, flat, lf, hf),
        })
    return events, env, t


def analyse(d: Path):
    mix, sr = sf.read(d / "audio.wav", dtype="float32", always_2d=True)
    stems = {k: sf.read(d / "stems" / f"{k}.wav", dtype="float32", always_2d=True)[0] for k in ("vocals", "no_vocals", "drums", "bass", "other")}
    wj = json.loads((d / "whisper.json").read_text())
    words = [w for s in wj["segments"] for w in s["words"]]
    mono = mix.mean(axis=1)
    voc, bed = stems["vocals"].mean(axis=1), stems["no_vocals"].mean(axis=1)
    dur = len(mono) / sr
    out = {"video": d.name, "duration_s": round(dur, 3), "sample_rate": sr, "channels": mix.shape[1]}

    # --- mix
    eb = ebur128(d / "audio.wav")
    env_mix, t = rms_env(mono, sr)
    st = [lufs(mix[int(a * sr):int((a + 3) * sr)], sr) for a in np.arange(0, max(dur - 3, 0.1), 1.0)]
    st = [v for v in st if v is not None and np.isfinite(v)]
    side = (mix[:, 0] - mix[:, 1]) / 2 if mix.shape[1] == 2 else np.zeros_like(mono)
    bands_mix, cutoff_mix, cent_mix = band_levels(mono, sr)
    quiet = [(t[a], t[b - 1]) for a, b in runs(env_mix < -45, int(0.10 / HOP_S))]
    out["mix"] = {
        **eb, "integrated_lufs_pyloudnorm": lufs(mix, sr),
        "sample_peak_dbfs": round(float(db(np.abs(mix).max())), 2), "rms_dbfs": round(float(db(np.sqrt((mono ** 2).mean()))), 2),
        "short_term_lufs_min_max": [round(min(st), 1), round(max(st), 1)] if st else None,
        "stereo_side_to_mid_db": round(float(db(np.sqrt((side ** 2).mean())) - db(np.sqrt((mono ** 2).mean()))), 1),
        "band_db_rel_total": bands_mix, "hf_cutoff_hz_at_-60db": cutoff_mix, "spectral_centroid_hz": round(cent_mix),
        "below_-45dbfs_ge_100ms": [{"start": round(float(a), 3), "dur": round(float(b - a), 3)} for a, b in quiet],
        "below_-45dbfs_total_s": round(float(sum(b - a for a, b in quiet)), 2),
    }

    # --- voice
    v = voice_analysis(voc, sr, words)
    active, vt, venv, (ft, f0) = v.pop("_active"), v.pop("_t"), v.pop("_env"), v.pop("_f0")
    v["lufs"] = lufs(stems["vocals"], sr)
    side_v = (stems["vocals"][:, 0] - stems["vocals"][:, 1]) / 2
    v["stereo_side_to_mid_db"] = round(float(db(np.sqrt((side_v ** 2).mean())) - db(np.sqrt((voc ** 2).mean()))), 1)
    out["voice"] = v

    # --- beds: Demucs no_vocals (music+SFX together) and the DnR music / sfx stems
    dnr = {k: sf.read(d / "stems_dnr" / f"{k}.wav", dtype="float32", always_2d=True)[0] for k in ("music", "sfx", "speech")}
    music, sfx = dnr["music"].mean(axis=1), dnr["sfx"].mean(axis=1)
    env_bed, _ = rms_env(bed, sr)
    env_mus, _ = rms_env(music, sr)
    n = min(len(env_bed), len(active), len(env_mus))
    env_bed_n, env_mus_n, act = env_bed[:n], env_mus[:n], active[:n]
    tt = vt[:n]
    pre = tt < v["first_voice_s"] - 0.03
    post = tt > v["last_voice_s"] + 0.10
    mus_on = [(tt[a], tt[b - 1]) for a, b in runs(env_mus_n > -55, int(0.5 / HOP_S))]
    drop = [(tt[a], tt[b - 1]) for a, b in runs(env_mus_n < -58, int(0.25 / HOP_S)) if tt[a] > 0.3 and tt[b - 1] < dur - 0.3]
    tempo, beat_times = tempo_estimate(music, sr)
    steps = []
    for k in range(3, int(dur) - 3):
        a = np.median(env_mus_n[(tt >= k - 3) & (tt < k)])
        b = np.median(env_mus_n[(tt >= k) & (tt < k + 3)])
        if abs(b - a) >= 4:
            steps.append({"t": k, "delta_db": round(float(b - a), 1)})
    # 5 s windows: does the music level follow the voice level (ducking) or stay flat?
    lv, lm = [], []
    for k in np.arange(0, dur - 2, 2.0):
        sel = (tt >= k) & (tt < k + 2)
        if sel.sum() > 20:
            lv.append(np.median(venv[:n][sel]))
            lm.append(np.median(env_mus_n[sel]))
    side_m = (dnr["music"][:, 0] - dnr["music"][:, 1]) / 2
    out["music"] = {
        "lufs": lufs(dnr["music"], sr),
        "level_p10_p50_p90_dbfs": [round(float(np.percentile(env_mus_n, p)), 1) for p in (10, 50, 90)],
        "level_during_speech_median_dbfs": round(float(np.median(env_mus_n[act])), 1),
        "level_before_first_word_dbfs": round(float(np.median(env_mus_n[pre])), 1) if pre.sum() >= 3 else None,
        "level_after_last_word_dbfs": round(float(np.median(env_mus_n[post])), 1) if post.sum() >= 5 else None,
        "level_2s_window_sd_db": round(float(np.std(lm)), 2),
        "level_2s_corr_with_voice": round(float(np.corrcoef(lv, lm)[0, 1]), 2) if len(lv) > 4 else None,
        "active_spans_above_-55dbfs": [[round(float(a), 2), round(float(b), 2)] for a, b in mus_on],
        "starts_s": round(float(mus_on[0][0]), 2) if mus_on else None, "ends_s": round(float(mus_on[-1][1]), 2) if mus_on else None,
        "dropouts_below_-58dbfs_ge_250ms": [{"start": round(float(a), 2), "dur": round(float(b - a), 2)} for a, b in drop],
        "level_steps_ge_4db": steps,
        "stereo_side_to_mid_db": round(float(db(np.sqrt((side_m ** 2).mean())) - db(np.sqrt((music ** 2).mean()))), 1),
        "tempo": tempo, "key": key_estimate(music, sr),
        "band_db_rel_total": band_levels(music, sr)[0], "spectral_centroid_hz": round(band_levels(music, sr)[2]),
    }
    out["bed_demucs_no_vocals"] = {
        "lufs": lufs(stems["no_vocals"], sr),
        "level_p10_p50_p90_dbfs": [round(float(np.percentile(env_bed_n, p)), 1) for p in (10, 50, 90)],
        "sub_stem_lufs": {k: lufs(stems[k], sr) for k in ("drums", "bass", "other")},
    }

    # --- SFX (effects stem)
    ev, env_sfx, _ = sfx_events(sfx, sr)
    out["sfx"] = {
        "lufs": lufs(dnr["sfx"], sr),
        "events": ev, "count": len(ev), "per_10s": round(len(ev) / dur * 10, 2),
        "time_active_frac": round(float(sum(e["dur"] for e in ev) / dur), 3),
        "peak_dbfs_median": round(float(np.median([e["peak_dbfs"] for e in ev])), 1) if ev else None,
        "by_class": {k: sum(1 for e in ev if e["class_est"] == k) for k in sorted({e["class_est"] for e in ev})},
        "density_per_10s_bins": [sum(1 for e in ev if a <= e["start"] < a + 10) for a in range(0, int(np.ceil(dur)), 10)],
    }

    # --- relations
    out["balance"] = {
        "voice_lufs": v["lufs"], "music_lufs": out["music"]["lufs"], "sfx_lufs": out["sfx"]["lufs"],
        "voice_minus_music_lufs": round(v["lufs"] - out["music"]["lufs"], 1),
        "voice_minus_bed_lufs": round(v["lufs"] - out["bed_demucs_no_vocals"]["lufs"], 1),
        "voice_p50_minus_music_during_speech_db": round(v["level_p10_p50_p90_dbfs"][1] - out["music"]["level_during_speech_median_dbfs"], 1),
        "sfx_peak_median_minus_voice_p50_db": round(out["sfx"]["peak_dbfs_median"] - v["level_p10_p50_p90_dbfs"][1], 1) if ev else None,
        "speech_stem_dnr_lufs": lufs(dnr["speech"], sr),
    }
    out["beats"] = [round(float(b), 3) for b in beat_times]
    m_ = min(n, len(env_sfx))
    np.savez_compressed(d / "audio_curves.npz", t=tt[:m_], voice_db=venv[:m_], bed_db=env_bed_n[:m_], music_db=env_mus_n[:m_],
                        sfx_db=env_sfx[:m_], mix_db=env_mix[:m_], f0_t=ft, f0=f0)
    (d / "audio.json").write_text(json.dumps(out, indent=1))
    m, b = out["mix"], out["music"]
    return (f"{d.name}: I={m['integrated_lufs']} LUFS TP={m['true_peak_dbtp']} LRA={m['lra_lu']} | voice {v['lufs']} LUFS f0={v['f0_median_hz']}Hz "
            f"range={v['f0_range_p05_p95_semitones']}st wpm={v['wpm_overall']} pauses>=250ms={v['pauses_ge_250ms']} | music {b['lufs']} LUFS "
            f"v-m={out['balance']['voice_minus_music_lufs']} bpm={b['tempo']['bpm']} key={b['key']['key']} | sfx={len(ev)} ({out['sfx']['per_10s']}/10s)")


def main():
    root = Path(sys.argv[1])
    jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    only = sys.argv[3] if len(sys.argv) > 3 else None
    dirs = sorted(p for p in root.iterdir() if (p / "stems_dnr" / "sfx.wav").exists() and (p / "stems" / "no_vocals.wav").exists()
                  and (p / "whisper.json").exists() and (only is None or p.name == only))
    with ProcessPoolExecutor(jobs) as ex:
        for line in ex.map(analyse, dirs):
            print(line, flush=True)


if __name__ == "__main__":
    main()
