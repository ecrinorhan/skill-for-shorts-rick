#!/usr/bin/env bash
# setup.sh — install everything the skill's tools need, inside the skill folder.
#
#   scripts/setup.sh              narration, captions, renderer, mixer, script checker
#   scripts/setup.sh --measure    also the packages for scripts/measure/measure.py
#
# Creates  .venv/            Python packages (requirements.txt)
#          models/kokoro/    text-to-speech model files (about 350 MB, Apache-2.0)
#          scripts/render/node_modules/   three.js and Playwright, plus a headless Chromium
# Needs on the PATH already: python3 (3.10+), node (20+), npm, ffmpeg, rubberband, curl.
#   Debian/Ubuntu: sudo apt-get install -y python3-venv nodejs npm ffmpeg rubberband-cli curl
#   macOS:         brew install python node ffmpeg rubberband
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

missing=0
for tool in python3 node npm ffmpeg rubberband curl; do
  if ! command -v "$tool" >/dev/null 2>&1; then echo "missing: $tool"; missing=1; fi
done
if [ "$missing" = 1 ]; then echo "Install the missing tools (see the top of this file) and run again."; exit 1; fi

python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
if [ "${1:-}" = "--measure" ]; then
  .venv/bin/python -m pip install --quiet -r requirements-measure.txt
  command -v tesseract >/dev/null 2>&1 || echo "note: measure.py also needs the tesseract command (tesseract-ocr)"
fi

mkdir -p models/kokoro
BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  if [ ! -s "models/kokoro/$f" ]; then
    echo "downloading $f"
    curl -L --fail --silent --show-error -o "models/kokoro/$f.part" "$BASE/$f"
    mv "models/kokoro/$f.part" "models/kokoro/$f"
  fi
done

(cd scripts/render && npm ci --silent && npx playwright install chromium)

echo "ready. Try:  .venv/bin/python scripts/check_script.py examples/bridge-keeper/script.json"
