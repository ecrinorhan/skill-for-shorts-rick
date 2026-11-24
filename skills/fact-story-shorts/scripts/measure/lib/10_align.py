#!/usr/bin/env python3
"""Reconcile the ASR transcript with the burned-in captions, then force-align every word.

Usage: 10_align.py <work_dir> [only=<video-stem>]
Reads  whisper.json (ASR words), captions.json (OCR caption events), stems/vocals.wav
Writes words.json:
  words[]      final word list: text, start/end (MMS forced alignment, 20 ms grid), whisper_start/end, caption index, source
  captions[]   caption events with their words, word count, and sync offsets in frames
  review[]     ASR/OCR disagreements that could not be auto-resolved (resolved by eye from the frames; see overrides)
  stats        word count, sentences, WPM, caption stats

"Corrected by listening" is not possible for a script; the correction source here is the creator's own on-screen
captions (OCR) plus manual overrides stored in analysis/data/transcript_overrides.json.
"""
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio
from num2words import num2words

FPS = 30.0
OVERRIDES = Path(__file__).resolve().parents[1] / "data" / "transcript_overrides.json"


def norm(tok):
    return re.sub(r"[^a-z0-9]", "", tok.lower())


def spoken(tok):
    """Letters-only spoken form of a token for the aligner (digits -> words)."""
    t = tok.lower().replace("%", " percent").replace("$", " dollars ").replace("&", " and ")
    def rep(m):
        s = m.group(0).replace(",", "")
        try:
            if re.fullmatch(r"\d+(st|nd|rd|th)", s):
                return num2words(int(s[:-2]), to="ordinal")
            if re.fullmatch(r"(1[0-9]|20)\d\ds?", s):   # years / decades: 1800s -> eighteen hundreds
                y = int(s.rstrip("s"))
                w = num2words(y, to="year")
                return w + ("s" if s.endswith("s") else "")
            return num2words(float(s) if "." in s else int(s))
        except Exception:  # noqa: BLE001
            return s
    t = re.sub(r"\d[\d,]*(\.\d+)?(st|nd|rd|th|s)?", rep, t)
    t = re.sub(r"[^a-z' ]", " ", t)
    return [w.strip("'") for w in t.split() if w.strip("'")]


def edit_distance(a, b):
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, dp[0] = dp[0], i
        for j, cb in enumerate(b, 1):
            prev, dp[j] = dp[j], min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
    return dp[-1]


def reconcile(asr_words, cap_events):
    """Returns final tokens [{text, cap, src, w_start, w_end, cap_punct}] and a review list.

    The transcript text is always the ASR token (plus manual overrides). The captions are the creator's own machine
    captions, read back by OCR: they give each word its caption index, flag disagreements, and lend sentence-final
    punctuation where the ASR left a long unpunctuated run.
    """
    asr = [{"text": w["w"], "n": norm(w["w"]), "start": w["start"], "end": w["end"]} for w in asr_words if norm(w["w"])]
    ocr = []
    for ci, ev in enumerate(cap_events):
        for tok in ev["text"].split():
            if norm(tok):
                ocr.append({"text": tok, "n": norm(tok), "cap": ci, "punct": tok.rstrip("\"'”’)]}| _")[-1:] if tok.rstrip("\"'”’)]}| _")[-1:] in ".?!" else ""})
    sm = difflib.SequenceMatcher(a=[w["n"] for w in asr], b=[w["n"] for w in ocr], autojunk=False)
    final, review = [], []

    def add(a, cap, src, punct=""):
        final.append({"text": a["text"], "cap": cap, "src": src, "w_start": a["start"], "w_end": a["end"], "cap_punct": punct})

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        A, B = asr[i1:i2], ocr[j1:j2]
        if tag == "equal":
            for a, b in zip(A, B):
                add(a, b["cap"], "asr=ocr", b["punct"])
            continue
        ja, jb = "".join(a["n"] for a in A), "".join(b["n"] for b in B)
        if A and B and ja == jb:
            # same letters, different word breaks (OCR glued 'as a' into 'aSa', or 'end-to-end' vs 'end to end'):
            # map every ASR word to the OCR token that covers its letters
            ends, pos = [], 0
            for b in B:
                pos += len(b["n"])
                ends.append(pos)
            pos = 0
            for a in A:
                mid = pos + len(a["n"]) / 2
                k = next(i for i, e in enumerate(ends) if mid <= e)
                pos += len(a["n"])
                add(a, B[k]["cap"], "asr=ocr(spacing)", B[k]["punct"] if pos == ends[k] else "")
        elif A and B and len(A) == len(B) and all(edit_distance(a["n"], b["n"]) <= max(1, len(a["n"]) // 3) for a, b in zip(A, B)):
            for a, b in zip(A, B):
                add(a, b["cap"], "asr(ocr differs slightly)", b["punct"])
                review.append({"t": a["start"], "asr": a["text"], "ocr": b["text"], "resolved": "asr", "auto": True})
        elif A and not B:
            for a in A:
                add(a, None, "asr-only")
            review.append({"t": A[0]["start"], "asr": " ".join(a["text"] for a in A), "ocr": "", "resolved": "asr", "auto": False})
        elif B and not A:
            review.append({"t": final[-1]["w_end"] if final else 0.0, "asr": "", "ocr": " ".join(b["text"] for b in B), "resolved": "dropped-ocr", "auto": False})
        else:
            t0 = A[0]["start"]
            for k, a in enumerate(A):
                add(a, B[min(k * len(B) // len(A), len(B) - 1)]["cap"], "asr(conflict)")
            review.append({"t": t0, "asr": " ".join(a["text"] for a in A), "ocr": " ".join(b["text"] for b in B), "resolved": "asr", "auto": False})
    # caption index for asr-only words from timing
    for w in final:
        if w["cap"] is None:
            mid = (w["w_start"] + w["w_end"]) / 2
            w["cap"] = min(range(len(cap_events)), key=lambda c: 0 if cap_events[c]["on"] <= mid < cap_events[c]["off"] else min(abs(cap_events[c]["on"] - mid), abs(cap_events[c]["off"] - mid)))
    # borrow sentence-final punctuation from the captions where the ASR has none nearby
    def has_end(k):
        return 0 <= k < len(final) and final[k]["text"].rstrip("\"'”’")[-1:] in ".?!"
    for k, w in enumerate(final[:-1]):
        if w["cap_punct"] and not has_end(k) and not any(has_end(k + o) for o in (-2, -1, 1, 2)):
            w["text"] = w["text"].rstrip(",;:") + w["cap_punct"]
            w["src"] += "+cap-punct"
            nxt = final[k + 1]["text"]
            final[k + 1]["text"] = nxt[:1].upper() + nxt[1:]
    if final and not has_end(len(final) - 1):
        final[-1]["text"] = final[-1]["text"].rstrip(",;:") + "."
    return final, review


class Aligner:
    def __init__(self):
        b = torchaudio.pipelines.MMS_FA
        self.model = b.get_model(with_star=False)
        self.model.eval()
        self.tok = b.get_tokenizer()
        self.al = b.get_aligner()

    def __call__(self, wav16k, token_lists):
        flat = [w for toks in token_lists for w in toks]
        with torch.inference_mode():
            em, _ = self.model(torch.from_numpy(wav16k)[None])
            spans = self.al(em[0], self.tok(flat))
        ratio = len(wav16k) / em.size(1) / 16000
        out, k = [], 0
        for toks in token_lists:
            if not toks:
                out.append(None)
                continue
            sp = spans[k:k + len(toks)]
            k += len(toks)
            out.append((ratio * sp[0][0].start, ratio * sp[-1][-1].end, float(np.mean([s.score for w in sp for s in w]))))
        return out


def main():
    root = Path(sys.argv[1])
    only = sys.argv[2] if len(sys.argv) > 2 else None
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    torch.set_num_threads(8)
    aligner = Aligner()
    for d in sorted(p for p in root.iterdir() if (p / "captions.json").exists() and (p / "whisper.json").exists() and (only is None or p.name == only)):
        wj = json.loads((d / "whisper.json").read_text())
        asr_words = [w for s in wj["segments"] for w in s["words"]]
        caps = json.loads((d / "captions.json").read_text())["events"]
        ov = overrides.get(d.name, {})
        for fix in ov.get("asr", []):          # {"at": seconds, "from": "x", "to": "y"}
            for w in asr_words:
                if abs(w["start"] - fix["at"]) < 0.6 and norm(w["w"]) == norm(fix["from"]):
                    w["w"] = fix["to"]
                    break
        for fix in ov.get("ocr", []):          # {"on": seconds, "to": "text"}
            for ev in caps:
                if abs(ev["on"] - fix["on"]) < 0.02:
                    ev["text"] = fix["to"]
        final, review = reconcile(asr_words, caps)
        wav, sr = sf.read(d / "stems" / "vocals.wav", dtype="float32", always_2d=True)
        mono = torchaudio.functional.resample(torch.from_numpy(wav.mean(axis=1)), sr, 16000).numpy()
        al = aligner(mono, [spoken(w["text"]) for w in final])
        for w, a in zip(final, al):
            if a is None:
                w["start"], w["end"], w["score"] = round(w["w_start"], 3), round(w["w_end"], 3), None
            else:
                w["start"], w["end"], w["score"] = round(a[0], 3), round(a[1], 3), round(a[2], 3)
            w["w_start"], w["w_end"] = round(w["w_start"], 3), round(w["w_end"], 3)
        # captions with words + sync
        cap_out = []
        for ci, ev in enumerate(caps):
            ws = [w for w in final if w["cap"] == ci]
            rec = {k: ev[k] for k in ("text", "on", "off", "on_f", "off_f", "frames", "dur", "cy_pct", "cx_pct", "height_px", "width_px", "height_pct_h", "width_pct_w", "fill_rgb", "stroke_rgb")}
            rec["n_words"] = len(ws)
            rec["spoken"] = " ".join(w["text"] for w in ws)
            if ws:
                rec["first_word_start"] = ws[0]["start"]
                rec["last_word_end"] = ws[-1]["end"]
                rec["on_minus_word_start_frames"] = round((ev["on"] - ws[0]["start"]) * FPS, 2)
                rec["off_minus_word_end_frames"] = round((ev["off"] - ws[-1]["end"]) * FPS, 2)
            cap_out.append(rec)
        text = " ".join(w["text"] for w in final)
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        slens = [len(s.split()) for s in sents]
        dur = wj["duration"]
        valid = [c for c in cap_out if c["n_words"] > 0]
        on_off = np.array([c["on_minus_word_start_frames"] for c in valid]) if valid else np.array([0.0])
        stats = {
            "duration_s": dur, "words": len(final), "wpm": round(len(final) / dur * 60, 1),
            "sentences": len(sents), "avg_sentence_words": round(float(np.mean(slens)), 1) if slens else 0,
            "median_sentence_words": float(np.median(slens)) if slens else 0, "max_sentence_words": max(slens) if slens else 0,
            "questions": sum(s.endswith("?") for s in sents), "exclamations": sum(s.endswith("!") for s in sents),
            "you_count": sum(norm(w["text"]) in ("you", "your", "youre", "youll", "youd", "youve", "yours") for w in final),
            "captions": len(cap_out), "captions_with_words": len(valid),
            "words_per_caption_mean": round(float(np.mean([c["n_words"] for c in valid])), 2) if valid else 0,
            "words_per_caption_hist": {str(k): int(sum(c["n_words"] == k for c in valid)) for k in range(1, 6)},
            "caption_dur_mean_s": round(float(np.mean([c["dur"] for c in valid])), 3) if valid else 0,
            "caption_dur_median_s": round(float(np.median([c["dur"] for c in valid])), 3) if valid else 0,
            "caption_on_minus_word_frames_median": round(float(np.median(on_off)), 2),
            "caption_on_minus_word_frames_p10_p90": [round(float(np.percentile(on_off, 10)), 2), round(float(np.percentile(on_off, 90)), 2)],
            "caption_on_abs_offset_frames_mean": round(float(np.mean(np.abs(on_off))), 2),
            "align_score_mean": round(float(np.mean([w["score"] for w in final if w["score"] is not None])), 3),
            "asr_vs_fa_start_abs_diff_ms_median": round(float(np.median([abs(w["start"] - w["w_start"]) for w in final]) * 1000), 1),
            "review_items": len(review), "review_unresolved_auto": sum(not r["auto"] for r in review),
        }
        (d / "words.json").write_text(json.dumps({"text": text, "sentences": sents, "words": final, "captions": cap_out, "review": review, "stats": stats}, indent=1, ensure_ascii=False))
        print(f"{d.name}: words={stats['words']} wpm={stats['wpm']} sent={stats['sentences']} avg_sent={stats['avg_sentence_words']} caps={stats['captions']} "
              f"w/cap={stats['words_per_caption_mean']} cap_on-word={stats['caption_on_minus_word_frames_median']}f "
              f"[{stats['caption_on_minus_word_frames_p10_p90'][0]},{stats['caption_on_minus_word_frames_p10_p90'][1]}] review={stats['review_unresolved_auto']}/{len(review)}", flush=True)


if __name__ == "__main__":
    main()
