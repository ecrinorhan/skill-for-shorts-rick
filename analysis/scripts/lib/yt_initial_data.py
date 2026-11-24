#!/usr/bin/env python3
"""Extract ytInitialData / ytInitialPlayerResponse JSON blobs from a saved YouTube HTML page.

Usage: yt_initial_data.py <page.html> <out_prefix>
Writes <out_prefix>.initial.json and <out_prefix>.player.json when present.
"""
import json
import re
import sys
from pathlib import Path


def extract(html: str, var: str):
    m = re.search(r"(?:var\s+|window\[\"|window\.)?%s(?:\"\])?\s*=\s*" % re.escape(var), html)
    if not m:
        return None
    start = html.find("{", m.end() - 1)
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(html[start:])
        return obj
    except json.JSONDecodeError:
        return None


def main():
    html = Path(sys.argv[1]).read_text(errors="replace")
    prefix = sys.argv[2]
    for var, suffix in (("ytInitialData", "initial"), ("ytInitialPlayerResponse", "player")):
        obj = extract(html, var)
        if obj is None:
            print(f"{var}: not found")
            continue
        Path(f"{prefix}.{suffix}.json").write_text(json.dumps(obj))
        print(f"{var}: ok, top-level keys = {list(obj.keys())[:20]}")


if __name__ == "__main__":
    main()
