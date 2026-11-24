#!/usr/bin/env python3
"""Technical specs + 30 fps frame extraction + audio extraction for every video.

Usage: 02_extract.py <videos_dir> <work_dir> [jobs]
Per video writes  <work>/<NN_ID>/{probe.json,specs.json,frames/%05d.jpg,audio.wav,audio16k.wav}
and a combined    <work>/specs_all.json
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from math import gcd
from pathlib import Path


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path: Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    return json.loads(p.stdout)


def specs_from(pr: dict) -> dict:
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    w, h = int(v["width"]), int(v["height"])
    g = gcd(w, h)
    fps = Fraction(v["avg_frame_rate"])
    out = {
        "container": pr["format"]["format_name"],
        "duration_s": round(float(pr["format"]["duration"]), 3),
        "size_bytes": int(pr["format"]["size"]),
        "total_bitrate_kbps": round(int(pr["format"]["bit_rate"]) / 1000, 1),
        "width": w,
        "height": h,
        "aspect_ratio": f"{w // g}:{h // g}",
        "fps": round(float(fps), 3),
        "r_frame_rate": v["r_frame_rate"],
        "video_codec": v["codec_name"],
        "video_profile": v.get("profile"),
        "video_level": v.get("level"),
        "pix_fmt": v.get("pix_fmt"),
        "color_space": v.get("color_space"),
        "color_transfer": v.get("color_transfer"),
        "color_primaries": v.get("color_primaries"),
        "color_range": v.get("color_range"),
        "video_bitrate_kbps": round(int(v.get("bit_rate", 0)) / 1000, 1),
        "video_frames": int(v.get("nb_frames", 0)),
        "has_b_frames": v.get("has_b_frames"),
        "encoder_tag": (v.get("tags") or {}).get("encoder") or (pr["format"].get("tags") or {}).get("encoder"),
        "format_tags": pr["format"].get("tags"),
    }
    if a:
        out.update(
            {
                "audio_codec": a["codec_name"],
                "audio_profile": a.get("profile"),
                "audio_sample_rate": int(a["sample_rate"]),
                "audio_channels": int(a["channels"]),
                "audio_channel_layout": a.get("channel_layout"),
                "audio_bitrate_kbps": round(int(a.get("bit_rate", 0)) / 1000, 1),
            }
        )
    return out


def work(video: Path, root: Path) -> dict:
    d = root / video.stem
    (d / "frames").mkdir(parents=True, exist_ok=True)
    pr = probe(video)
    (d / "probe.json").write_text(json.dumps(pr, indent=1))
    sp = specs_from(pr)
    sp["name"] = video.stem
    # 30 fps frames, full resolution, high-quality JPEG
    if not (d / "frames" / "00001.jpg").exists():
        run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", "fps=30", "-q:v", "2", "-start_number", "0", str(d / "frames" / "%05d.jpg")])
    sp["frames_extracted"] = len(list((d / "frames").glob("*.jpg")))
    if not (d / "audio.wav").exists():
        run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(d / "audio.wav")])
        run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(d / "audio16k.wav")])
    (d / "specs.json").write_text(json.dumps(sp, indent=1))
    print(f"{video.stem}: {sp['width']}x{sp['height']} {sp['fps']}fps {sp['video_codec']} {sp['video_bitrate_kbps']}kbps "
          f"{sp['duration_s']}s frames={sp['frames_extracted']} audio={sp.get('audio_codec')} {sp.get('audio_sample_rate')}Hz x{sp.get('audio_channels')}", flush=True)
    return sp


def main():
    vids = sorted(Path(sys.argv[1]).glob("*.mp4"))
    root = Path(sys.argv[2])
    jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    root.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(jobs) as ex:
        allspecs = list(ex.map(lambda v: work(v, root), vids))
    (root / "specs_all.json").write_text(json.dumps(allspecs, indent=1))


if __name__ == "__main__":
    main()
