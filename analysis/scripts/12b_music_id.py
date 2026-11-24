#!/usr/bin/env python3
"""Try to identify the background music with Shazam (unofficial shazamio client).

Usage: 12b_music_id.py <work_dir> <out.json>
For each video three 15 s excerpts are tested: the music stem at its loudest stretch, the music stem from the
middle of the video, and the unseparated mix. A miss proves nothing (library / AI-generated / heavily masked music is
often not in Shazam's catalogue); a hit is evidence that the same recording exists commercially.
"""
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from shazamio import Shazam


def excerpt(src, start, dur, gain_db=0.0):
    tf = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", str(src), "-af", f"volume={gain_db}dB",
                    "-ar", "44100", "-ac", "2", "-b:a", "192k", tf.name], check=True)
    return tf.name


async def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    shazam = Shazam()
    res = {}
    for d in sorted(p for p in root.iterdir() if (p / "stems_dnr" / "music.wav").exists()):
        mus = d / "stems_dnr" / "music.wav"
        y, sr = sf.read(mus, dtype="float32", always_2d=True)
        mono = y.mean(axis=1)
        win = 15 * sr
        if len(mono) <= win:
            continue
        energy = np.convolve(mono ** 2, np.ones(win) / win, mode="valid")[::sr]
        loud = float(np.argmax(energy))
        rms = float(np.sqrt((mono ** 2).mean()))
        gain = float(np.clip(-20 - 20 * np.log10(rms + 1e-9), 0, 30))     # bring the quiet stem up to about -20 dBFS
        tries = [("music stem, loudest 15 s", mus, loud, gain), ("music stem, middle", mus, max(0.0, len(mono) / sr / 2 - 7.5), gain),
                 ("full mix, middle", d / "audio.wav", max(0.0, len(mono) / sr / 2 - 7.5), 0.0)]
        hits = []
        for label, src, start, g in tries:
            fp = excerpt(src, start, 15, g)
            try:
                r = await shazam.recognize(fp)
                tr = r.get("track")
                hits.append({"excerpt": label, "start_s": round(start, 1), "match": bool(tr),
                             "title": tr.get("title") if tr else None, "artist": tr.get("subtitle") if tr else None,
                             "url": tr.get("url") if tr else None, "matches": len(r.get("matches", []))})
            except Exception as e:  # noqa: BLE001
                hits.append({"excerpt": label, "start_s": round(start, 1), "error": str(e)[:160]})
            Path(fp).unlink(missing_ok=True)
            await asyncio.sleep(1.0)
        res[d.name] = hits
        print(d.name, " | ".join((h.get("title") or ("ERR " + h["error"][:40] if "error" in h else "no match")) for h in hits), flush=True)
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
