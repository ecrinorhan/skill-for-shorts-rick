#!/usr/bin/env python3
"""install.py — install everything the skill's tools need, inside the skill folder.

  python3 scripts/install.py              narration, captions, renderer, mixer, script checker
  python3 scripts/install.py --measure    also the packages for scripts/measure/measure.py

Creates  .venv/                         Python packages (requirements.txt)
         models/kokoro/                 text-to-speech model files (about 350 MB, Apache-2.0)
         ~/.cache/torch/                word-timing model for the captions (wav2vec2 base, about 360 MB, MIT)
         scripts/render/node_modules/   three.js and Playwright, plus a headless Chromium

Needs on the PATH already: Python 3.10+, Node 20+ with npm, ffmpeg, rubberband (and tesseract for --measure).
  Debian / Ubuntu:  sudo apt-get install -y python3-venv nodejs npm ffmpeg rubberband-cli tesseract-ocr
  macOS:            brew install python node ffmpeg rubberband tesseract
Safe to run again: finished steps are skipped or refreshed.
"""
import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KOKORO = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"


def run(*cmd, cwd=None):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", action="store_true", help="also install what measure.py needs")
    a = ap.parse_args()
    need = ["node", "npm", "ffmpeg", "rubberband"] + (["tesseract"] if a.measure else [])
    missing = [t for t in need if not shutil.which(t)]
    if missing:
        sys.exit("missing on the PATH: " + ", ".join(missing) + "  (see the top of scripts/install.py)")
    py = ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    if not py.exists():
        print("creating", ROOT / ".venv", flush=True)
        venv.create(ROOT / ".venv", with_pip=True)
    run(py, "-m", "pip", "install", "--quiet", "--upgrade", "pip")
    run(py, "-m", "pip", "install", "--quiet", "-r", ROOT / "requirements.txt")
    if a.measure:
        run(py, "-m", "pip", "install", "--quiet", "-r", ROOT / "requirements-measure.txt")
    kd = ROOT / "models" / "kokoro"
    kd.mkdir(parents=True, exist_ok=True)
    for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        if not (kd / name).exists() or (kd / name).stat().st_size == 0:
            print("downloading", name, flush=True)
            tmp = kd / (name + ".part")
            urllib.request.urlretrieve(KOKORO + name, tmp)
            tmp.replace(kd / name)
    run(py, "-c", "import torchaudio; torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H.get_model()")   # word-timing model
    rd = ROOT / "scripts" / "render"
    run("npm", "ci", "--silent", cwd=rd)
    run("npx", "playwright", "install", "chromium", cwd=rd)
    print(f"\nready. Try:\n  {py} {ROOT / 'scripts' / 'check_script.py'} {ROOT / 'examples' / 'bridge-keeper' / 'script.json'}")


if __name__ == "__main__":
    main()
