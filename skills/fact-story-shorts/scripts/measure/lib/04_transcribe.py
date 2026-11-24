#!/usr/bin/env python3
"""Word-level transcription with faster-whisper (CPU).

Usage: 04_transcribe.py <work_dir> [model=large-v3] [threads=4] [audio=audio16k.wav] [tag=]
Writes <work>/<video>/whisper{tag}.json  {text, segments:[{start,end,text,words:[{w,start,end,p}]}]}
"""
import json
import sys
import time
from pathlib import Path

import librosa
import soundfile as sf
from faster_whisper import WhisperModel


def main():
    root = Path(sys.argv[1])
    model_name = sys.argv[2] if len(sys.argv) > 2 else "large-v3"
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    audio_name = sys.argv[4] if len(sys.argv) > 4 else "audio16k.wav"
    tag = sys.argv[5] if len(sys.argv) > 5 else ""
    model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=threads)
    for d in sorted(p for p in root.iterdir() if (p / audio_name).exists()):
        out = d / f"whisper{tag}.json"
        if out.exists():
            continue
        t0 = time.time()
        # decode here: passing an array keeps faster-whisper off its PyAV code path
        wav, sr = sf.read(d / audio_name, dtype="float32", always_2d=True)
        mono = wav.mean(axis=1)
        if sr != 16000:
            mono = librosa.resample(mono, orig_sr=sr, target_sr=16000)
        segments, info = model.transcribe(
            mono,
            language="en",
            beam_size=5,
            word_timestamps=True,
            condition_on_previous_text=False,
            vad_filter=False,
            temperature=0.0,
        )
        segs = []
        for s in segments:
            segs.append(
                {
                    "start": round(s.start, 3),
                    "end": round(s.end, 3),
                    "text": s.text.strip(),
                    "avg_logprob": round(s.avg_logprob, 3),
                    "no_speech_prob": round(s.no_speech_prob, 3),
                    "words": [
                        {"w": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3), "p": round(w.probability, 3)}
                        for w in (s.words or [])
                    ],
                }
            )
        res = {
            "model": model_name,
            "audio": audio_name,
            "duration": round(info.duration, 3),
            "text": " ".join(s["text"] for s in segs),
            "segments": segs,
        }
        out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
        n = sum(len(s["words"]) for s in segs)
        print(f"{d.name}: {n} words, {len(segs)} segments, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
