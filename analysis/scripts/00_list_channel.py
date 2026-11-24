#!/usr/bin/env python3
"""List a channel's Shorts / Videos / Streams tabs with yt-dlp (flat, no downloads).

Usage: 00_list_channel.py <channel_url> <out_dir> [max_per_tab]
Writes tab_<name>.json per tab and channel_listing.json (merged, newest first per tab).
"""
import json
import subprocess
import sys
from pathlib import Path


def main():
    channel = sys.argv[1].rstrip("/")
    out = Path(sys.argv[2])
    limit = sys.argv[3] if len(sys.argv) > 3 else "60"
    out.mkdir(parents=True, exist_ok=True)
    merged = {"channel_url": channel, "tabs": {}}
    for tab in ("shorts", "videos", "streams"):
        cmd = ["yt-dlp", "--flat-playlist", "--playlist-end", limit, "-J", f"{channel}/{tab}"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0 or not p.stdout.strip():
            err = (p.stderr or "").strip().splitlines()[-1:] or ["no output"]
            print(f"[{tab}] unavailable: {err[0]}")
            merged["tabs"][tab] = {"available": False, "error": err[0], "entries": []}
            continue
        d = json.loads(p.stdout)
        (out / f"tab_{tab}.json").write_text(json.dumps(d, indent=1))
        entries = [
            {
                "id": e.get("id"),
                "title": e.get("title"),
                "duration": e.get("duration"),
                "view_count": e.get("view_count"),
                "url": e.get("url"),
            }
            for e in (d.get("entries") or [])
        ]
        merged["channel"] = d.get("channel") or merged.get("channel")
        merged["channel_id"] = d.get("channel_id") or merged.get("channel_id")
        merged["followers"] = d.get("channel_follower_count") or merged.get("followers")
        merged["description"] = d.get("description") or merged.get("description")
        merged["tabs"][tab] = {"available": True, "count_listed": len(entries), "entries": entries}
        print(f"[{tab}] {len(entries)} entries (limit {limit})")
        for i, e in enumerate(entries, 1):
            print(f"  {i:>2} {e['id']} | {e['title']} | dur={e['duration']} | views={e['view_count']}")
    print("channel:", merged.get("channel"), "| id:", merged.get("channel_id"), "| followers:", merged.get("followers"))
    print("description:", (merged.get("description") or "")[:800])
    (out / "channel_listing.json").write_text(json.dumps(merged, indent=1))


if __name__ == "__main__":
    main()
