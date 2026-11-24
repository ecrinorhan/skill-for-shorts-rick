#!/usr/bin/env python3
"""Collect per-video metadata without a working player response.

YouTube answers this sandbox's IP with LOGIN_REQUIRED ("confirm you're not a bot") for
every player client, so formats/tags/subtitle tracks are not reachable through yt-dlp.
Everything else is collected from routes that still answer:

  * yt-dlp --ignore-no-formats-error  -> title, upload date (UTC), views, likes, top comments
  * watch page ytInitialData          -> exact views/likes, description, disclosure panel, transcript params
  * youtubei/v1/next (comments token) -> exact comment count as shown in the header
  * youtubei/v1/get_transcript        -> YouTube caption text (if the panel exists)
  * channel RSS feed                  -> exact publish timestamps for the newest 15 uploads
  * i.ytimg.com                       -> thumbnails (oar2 = 1080x1920 Shorts frame)
  * returnyoutubedislike API          -> independent likes/views cross-check (third party)

Usage: 01_fetch_metadata.py <ids.txt> <out_dir> [channel_id]
"""
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from yt_initial_data import extract  # noqa: E402

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+cb; SOCS=CAI; PREF=tz=UTC&hl=en"}
THUMBS = ("oar2", "maxresdefault", "hq720", "sddefault", "hqdefault")


def walk(obj):
    """Yield every dict/list node in a JSON tree."""
    stack = [obj]
    while stack:
        cur = stack.pop()
        yield cur
        if isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)


def find_first(obj, key):
    for node in walk(obj):
        if isinstance(node, dict) and key in node:
            return node[key]
    return None


def text_of(node):
    if node is None:
        return None
    if isinstance(node, str):
        return node
    if "simpleText" in node:
        return node["simpleText"]
    if "content" in node:
        return node["content"]
    if "runs" in node:
        return "".join(r.get("text", "") for r in node["runs"])
    return None


def to_int(s):
    if s is None:
        return None
    m = re.search(r"[\d,]+", str(s))
    return int(m.group(0).replace(",", "")) if m else None


def ytcfg(html, key):
    m = re.search(r'"%s":"([^"]+)"' % re.escape(key), html)
    return m.group(1) if m else None


def innertube(endpoint, html, payload):
    ctx = {
        "client": {
            "clientName": "WEB",
            "clientVersion": ytcfg(html, "INNERTUBE_CLIENT_VERSION") or "2.20241101.00.00",
            "hl": "en",
            "gl": "US",
            "timeZone": "UTC",
            "visitorData": ytcfg(html, "VISITOR_DATA"),
        }
    }
    r = requests.post(
        f"https://www.youtube.com/youtubei/v1/{endpoint}?prettyPrint=false",
        headers={**HEADERS, "Content-Type": "application/json", "Origin": "https://www.youtube.com"},
        json={"context": ctx, **payload},
        timeout=40,
    )
    r.raise_for_status()
    return r.json()


def fetch_rss(channel_id):
    out = {}
    if not channel_id:
        return out
    r = requests.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}", headers=HEADERS, timeout=40)
    ns = {
        "a": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(r.text)
    out["_channel_published"] = root.findtext("a:published", namespaces=ns)
    for e in root.findall("a:entry", ns):
        vid = e.findtext("yt:videoId", namespaces=ns)
        grp = e.find("media:group", ns)
        comm = grp.find("media:community", ns) if grp is not None else None
        out[vid] = {
            "published_utc": e.findtext("a:published", namespaces=ns),
            "updated_utc": e.findtext("a:updated", namespaces=ns),
            "description": grp.findtext("media:description", namespaces=ns) if grp is not None else None,
            "views": to_int(comm.find("media:statistics", ns).get("views")) if comm is not None else None,
            "likes": to_int(comm.find("media:starRating", ns).get("count")) if comm is not None else None,
        }
    return out


def main():
    ids = [l.split()[0] for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    out = Path(sys.argv[2])
    channel_id = sys.argv[3] if len(sys.argv) > 3 else None
    out.mkdir(parents=True, exist_ok=True)
    rss = fetch_rss(channel_id)
    (out / "rss.json").write_text(json.dumps(rss, indent=1))
    summary = []
    for n, vid in enumerate(ids, 1):
        d = out / vid
        d.mkdir(exist_ok=True)
        rec = {"n": n, "id": vid, "url": f"https://www.youtube.com/shorts/{vid}", "sources": {}}

        # 1) yt-dlp: info + top comments
        cmd = [
            "yt-dlp", "--skip-download", "--ignore-no-formats-error", "--write-info-json", "--write-comments",
            "--extractor-args", "youtube:max_comments=100,all,0,0;comment_sort=top",
            "-o", str(d / "%(id)s.%(ext)s"), f"https://www.youtube.com/watch?v={vid}",
        ]
        p = subprocess.run(cmd, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (d / "ytdlp.log").write_text(log)
        m = re.search(r"Downloading ~?([\d,]+) comments", log)
        rec["comment_count_ytdlp_header"] = to_int(m.group(1)) if m else None
        rec["player_blocked"] = "Sign in to confirm" in log
        info_p = d / f"{vid}.info.json"
        info = json.loads(info_p.read_text()) if info_p.exists() else {}
        for k in ("title", "upload_date", "view_count", "like_count", "duration", "tags", "categories", "channel", "channel_follower_count"):
            rec[k] = info.get(k)
        comments = info.get("comments") or []
        pinned = [c for c in comments if c.get("is_pinned")]
        rec["pinned_comment"] = (
            {"author": pinned[0].get("author"), "text": pinned[0].get("text"), "likes": pinned[0].get("like_count")} if pinned else None
        )
        rec["uploader_comments_in_top100"] = [
            {"text": c.get("text"), "likes": c.get("like_count"), "is_reply": c.get("parent") != "root"}
            for c in comments if c.get("author_is_uploader")
        ]
        rec["top_comments"] = [
            {"author": c.get("author"), "text": c.get("text"), "likes": c.get("like_count"), "hearted": c.get("is_favorited")}
            for c in sorted([c for c in comments if c.get("parent") == "root"], key=lambda c: -(c.get("like_count") or 0))[:10]
        ]
        rec["comments_fetched"] = len(comments)

        # 2) watch page
        html = requests.get(f"https://www.youtube.com/watch?v={vid}", headers=HEADERS, timeout=40).text
        (d / "watch.html").write_text(html)
        init = extract(html, "ytInitialData") or {}
        (d / "watch.initial.json").write_text(json.dumps(init))
        vpi = find_first(init, "videoPrimaryInfoRenderer") or {}
        rec["views_exact"] = to_int(find_first(vpi, "originalViewCount") or text_of(find_first(vpi, "viewCount")))
        rec["date_text_utc"] = text_of(vpi.get("dateText"))
        like_label = None
        for node in walk(init):
            if isinstance(node, dict) and isinstance(node.get("accessibilityText"), str) and "like this video along with" in node["accessibilityText"]:
                like_label = node["accessibilityText"]
                break
        rec["likes_exact"] = to_int(like_label)
        vsi = find_first(init, "videoSecondaryInfoRenderer") or {}
        rec["description"] = text_of(vsi.get("attributedDescription"))
        rec["subscribers_text"] = text_of(find_first(vsi, "subscriberCountText"))
        st = vpi.get("superTitleLink")
        rec["hashtags_super_title"] = text_of(st) if st else None
        how = find_first(init, "howThisWasMadeSectionViewModel")
        rec["how_this_was_made"] = (
            {"header": text_of(how.get("bodyHeader")), "body": text_of(how.get("bodyText"))} if how else None
        )
        rec["has_transcript_panel"] = find_first(init, "getTranscriptEndpoint") is not None

        # 3) exact comment count from the comments header
        try:
            # Several watch-next tokens exist; only the comments-section one returns the header count.
            tokens = []
            for node in walk(init):
                if isinstance(node, dict) and node.get("sectionIdentifier") == "comment-item-section":
                    t = find_first(node, "token")
                    if t and t not in tokens:
                        tokens.insert(0, t) if node.get("targetId") == "comments-section" else tokens.append(t)
            for token in tokens:
                nxt = innertube("next", html, {"continuation": token})
                hdr = find_first(nxt, "commentsHeaderRenderer") or {}
                if hdr.get("countText"):
                    rec["comment_count_header"] = to_int(text_of(hdr.get("countText")))
                    rec["comment_count_header_text"] = text_of(hdr.get("countText"))
                    break
        except Exception as e:  # noqa: BLE001
            rec["sources"]["comments_header_error"] = str(e)[:200]

        # 4) YouTube's own transcript
        try:
            params = (find_first(init, "getTranscriptEndpoint") or {}).get("params")
            if params:
                tr = innertube("get_transcript", html, {"params": params})
                (d / "yt_transcript_raw.json").write_text(json.dumps(tr))
                segs = []
                for node in walk(tr):
                    if isinstance(node, dict) and "transcriptSegmentRenderer" in node:
                        s = node["transcriptSegmentRenderer"]
                        segs.append({
                            "start_ms": int(s.get("startMs", 0)), "end_ms": int(s.get("endMs", 0)),
                            "text": text_of(s.get("snippet")),
                        })
                rec["yt_transcript_segments"] = len(segs)
                if segs:
                    (d / "yt_transcript.json").write_text(json.dumps(segs, indent=1))
                lang = find_first(tr, "languageCode") or text_of(find_first(tr, "title"))
                rec["yt_transcript_note"] = str(lang)[:120] if lang else None
        except Exception as e:  # noqa: BLE001
            rec["sources"]["transcript_error"] = str(e)[:200]

        # 5) Shorts overlay: sound attribution ("Original Sound" = audio baked into the upload) and UI counts
        try:
            reel = innertube("reel/reel_item_watch", html, {"playerRequest": {"videoId": vid}, "params": "CAUwAg%3D%3D", "disablePlayerResponse": True})
            (d / "reel_item_watch.json").write_text(json.dumps(reel))
            rec["shorts_sound_attribution"] = text_of(find_first(reel, "soundAttributionTitle"))
            labels = [
                v for node in walk(reel.get("overlay", {})) if isinstance(node, dict)
                for k, v in node.items() if isinstance(v, str) and k in ("accessibilityText", "label", "title", "content")
            ]
            rec["shorts_ui_comment_label"] = next((s for s in labels if re.match(r"View [\d,.KM]+ comments", s)), None)
            rec["shorts_ui_like_label"] = next((s for s in labels if re.match(r"[\d,.KM]+ likes$", s)), None)
            rec["shorts_ui_has_audio_track_picker"] = "Audio Track" in labels
            rec["shorts_ui_has_captions_toggle"] = "Captions" in labels
        except Exception as e:  # noqa: BLE001
            rec["sources"]["shorts_error"] = str(e)[:200]

        # 6) RSS + RYD
        rec["rss"] = rss.get(vid)
        try:
            ryd = requests.get(f"https://returnyoutubedislikeapi.com/votes?videoId={vid}", timeout=30).json()
            rec["ryd"] = {k: ryd.get(k) for k in ("likes", "viewCount", "dateCreated")}
        except Exception as e:  # noqa: BLE001
            rec["sources"]["ryd_error"] = str(e)[:200]

        # 7) thumbnails
        got = []
        for name in THUMBS:
            r = requests.get(f"https://i.ytimg.com/vi/{vid}/{name}.jpg", timeout=30)
            if r.status_code == 200 and len(r.content) > 2000:
                (d / f"thumb_{name}.jpg").write_bytes(r.content)
                got.append(name)
        rec["thumbnails"] = got

        (d / "meta.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        summary.append(rec)
        print(
            f"{n:>2} {vid} | {rec.get('title')} | date={rec.get('upload_date')} | views={rec.get('views_exact')} "
            f"| likes={rec.get('likes_exact')} | comments={rec.get('comment_count_header')}/{rec.get('comment_count_ytdlp_header')} "
            f"| pinned={'yes' if rec['pinned_comment'] else 'no'} | transcript_segs={rec.get('yt_transcript_segments')} "
            f"| how={rec['how_this_was_made']['header'] if rec['how_this_was_made'] else None} | thumbs={','.join(got)}",
            flush=True,
        )
        time.sleep(1.0)
    (out / "metadata_all.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
