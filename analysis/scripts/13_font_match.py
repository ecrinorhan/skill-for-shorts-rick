#!/usr/bin/env python3
"""Closest free font to the burned-in captions, by shape overlap.

Usage: 13_font_match.py <work_dir> <fonts_dir> <out.json> [n_samples=48]
For ~48 clean multi-letter captions (taken from several videos) the white glyph mask is cut out of the frame, the
same text is rendered with every candidate font/weight, scaled to the same ink height, and compared by IoU (best over a
small horizontal shift). Also reported: ink width ratio (rendered / observed), which separates wide from narrow designs.

Only free fonts (Google Fonts repo) can be tested here. A commercial face cannot be confirmed by this script;
the output says "closest free match", not "the font".
"""
import importlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
cap = importlib.import_module("08_captions")

GF = "https://raw.githubusercontent.com/google/fonts/main/"
CANDIDATES = [  # (family, repo path, [weights] or None for static)
    ("Poppins Bold", "ofl/poppins/Poppins-Bold.ttf", None),
    ("Poppins ExtraBold", "ofl/poppins/Poppins-ExtraBold.ttf", None),
    ("Poppins Black", "ofl/poppins/Poppins-Black.ttf", None),
    ("Montserrat", "ofl/montserrat/Montserrat[wght].ttf", [700, 800, 900]),
    ("Nunito", "ofl/nunito/Nunito[wght].ttf", [800, 900, 1000]),
    ("Nunito Sans", "ofl/nunitosans/NunitoSans[YTLC,opsz,wdth,wght].ttf", [800, 900, 1000]),
    ("Inter", "ofl/inter/Inter[opsz,wght].ttf", [700, 800, 900]),
    ("Rubik", "ofl/rubik/Rubik[wght].ttf", [700, 800, 900]),
    ("Lexend", "ofl/lexend/Lexend[wght].ttf", [700, 800, 900]),
    ("Outfit", "ofl/outfit/Outfit[wght].ttf", [700, 800, 900]),
    ("DM Sans", "ofl/dmsans/DMSans[opsz,wght].ttf", [700, 800, 900, 1000]),
    ("Figtree", "ofl/figtree/Figtree[wght].ttf", [700, 800, 900]),
    ("Urbanist", "ofl/urbanist/Urbanist[wght].ttf", [700, 800, 900]),
    ("Work Sans", "ofl/worksans/WorkSans[wght].ttf", [700, 800, 900]),
    ("Albert Sans", "ofl/albertsans/AlbertSans[wght].ttf", [700, 800, 900]),
    ("Plus Jakarta Sans", "ofl/plusjakartasans/PlusJakartaSans[wght].ttf", [700, 800]),
    ("Red Hat Display", "ofl/redhatdisplay/RedHatDisplay[wght].ttf", [700, 800, 900]),
    ("Manrope", "ofl/manrope/Manrope[wght].ttf", [700, 800]),
    ("Raleway", "ofl/raleway/Raleway[wght].ttf", [700, 800, 900]),
    ("Mulish", "ofl/mulish/Mulish[wght].ttf", [800, 900, 1000]),
    ("Hanken Grotesk", "ofl/hankengrotesk/HankenGrotesk[wght].ttf", [700, 800, 900]),
    ("Source Sans 3", "ofl/sourcesans3/SourceSans3[wght].ttf", [700, 800, 900]),
    ("Open Sans", "ofl/opensans/OpenSans[wdth,wght].ttf", [700, 800]),
    ("Roboto", "ofl/roboto/Roboto[wdth,wght].ttf", [700, 800, 900]),
    ("Archivo", "ofl/archivo/Archivo[wdth,wght].ttf", [700, 800, 900]),
    ("Sora", "ofl/sora/Sora[wght].ttf", [700, 800]),
    ("Onest", "ofl/onest/Onest[wght].ttf", [700, 800, 900]),
    ("Geologica", "ofl/geologica/Geologica[CRSV,SHRP,slnt,wght].ttf", [700, 800, 900]),
    ("Kumbh Sans", "ofl/kumbhsans/KumbhSans[YOPQ,wght].ttf", [700, 800, 900]),
    ("Be Vietnam Pro ExtraBold", "ofl/bevietnampro/BeVietnamPro-ExtraBold.ttf", None),
    ("Be Vietnam Pro Black", "ofl/bevietnampro/BeVietnamPro-Black.ttf", None),
    ("Kanit ExtraBold", "ofl/kanit/Kanit-ExtraBold.ttf", None),
    ("Prompt ExtraBold", "ofl/prompt/Prompt-ExtraBold.ttf", None),
    ("Lato Black", "ofl/lato/Lato-Black.ttf", None),
    ("Archivo Black", "ofl/archivoblack/ArchivoBlack-Regular.ttf", None),
    ("Barlow ExtraBold", "ofl/barlow/Barlow-ExtraBold.ttf", None),
    ("Heebo", "ofl/heebo/Heebo[wght].ttf", [700, 800, 900]),
    ("Gabarito", "ofl/gabarito/Gabarito[wght].ttf", [700, 800, 900]),
    ("Wix Madefor Display", "ofl/wixmadefordisplay/WixMadeforDisplay[wght].ttf", [700, 800]),
    ("Instrument Sans", "ofl/instrumentsans/InstrumentSans[wdth,wght].ttf", [700]),
    ("Golos Text", "ofl/golostext/GolosText[wght].ttf", [700, 800, 900]),
    ("Readex Pro", "ofl/readexpro/ReadexPro[HEXP,wght].ttf", [700]),
    ("Sen", "ofl/sen/Sen[wght].ttf", [700, 800]),
    ("Schibsted Grotesk", "ofl/schibstedgrotesk/SchibstedGrotesk[wght].ttf", [700, 800, 900]),
    ("Chivo", "ofl/chivo/Chivo[wght].ttf", [700, 800, 900]),
    ("Public Sans", "ofl/publicsans/PublicSans[wght].ttf", [700, 800, 900]),
    ("Epilogue", "ofl/epilogue/Epilogue[wght].ttf", [700, 800, 900]),
    ("Work Sans", "ofl/worksans/WorkSans[wght].ttf", [700, 800, 900]),
    ("Noto Sans", "ofl/notosans/NotoSans[wdth,wght].ttf", [800, 900]),
    ("Arimo", "apache/arimo/Arimo[wght].ttf", [700]),
    ("Familjen Grotesk", "ofl/familjengrotesk/FamiljenGrotesk[wght].ttf", [700]),
    ("Libre Franklin", "ofl/librefranklin/LibreFranklin[wght].ttf", [800, 900]),
    ("Jost", "ofl/jost/Jost[wght].ttf", [800, 900]),
    ("Anton", "ofl/anton/Anton-Regular.ttf", None),
    ("Sofia Sans", "ofl/sofiasans/SofiaSans[wght].ttf", [800, 900, 1000]),
    ("Bricolage Grotesque", "ofl/bricolagegrotesque/BricolageGrotesque[opsz,wdth,wght].ttf", [800]),
    ("Mona Sans", "ofl/monasans/MonaSans[wdth,wght].ttf", [800, 900]),
    ("Radio Canada Big", "ofl/radiocanadabig/RadioCanadaBig[wght].ttf", [700]),
    ("Atkinson Hyperlegible Next", "ofl/atkinsonhyperlegiblenext/AtkinsonHyperlegibleNext[wght].ttf", [800]),
    ("Funnel Display", "ofl/funneldisplay/FunnelDisplay[wght].ttf", [800]),
    ("Geist", "ofl/geist/Geist[wght].ttf", [800, 900]),
    ("Parkinsans", "ofl/parkinsans/Parkinsans[wght].ttf", [800]),
    ("Host Grotesk", "ofl/hostgrotesk/HostGrotesk[wght].ttf", [800]),
]


def fetch(fonts_dir: Path):
    fonts_dir.mkdir(parents=True, exist_ok=True)
    got = []
    for fam, rel, weights in CANDIDATES:
        fp = fonts_dir / Path(rel).name
        if not fp.exists():
            try:
                urllib.request.urlretrieve(GF + urllib.parse.quote(rel), fp)
            except Exception as e:  # noqa: BLE001
                print("skip", fam, str(e)[:60])
                continue
        got.append((fam, fp, weights))
    return got


def render(text, fp, weight, px=160):
    font = ImageFont.truetype(str(fp), px)
    if weight is not None:
        try:
            axes = font.get_variation_axes()
            vals = []
            for ax in axes:
                name = ax.get("name", b"")
                name = name.decode() if isinstance(name, bytes) else str(name)
                vals.append(weight if "eight" in name else ax["default"])
            font.set_variation_by_axes(vals)
        except Exception:  # noqa: BLE001
            return None
    w = int(font.getlength(text)) + 80
    img = Image.new("L", (w, px * 2), 0)
    ImageDraw.Draw(img).text((40, px // 3), text, fill=255, font=font)
    m = np.array(img) > 127
    ys, xs = np.where(m)
    if len(ys) == 0:
        return None
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def iou_best(obs, ren, erode=0):
    """Scale the render to the observed ink height (+2*erode, then erode: models a centred stroke eating into the
    fill), then slide horizontally."""
    h = obs.shape[0]
    hs = h + 2 * erode
    w = max(4, int(round(ren.shape[1] * hs / ren.shape[0])))
    r = cv2.resize(ren.astype(np.uint8), (w, hs), interpolation=cv2.INTER_AREA)
    if erode:
        r = cv2.erode(np.pad(r, erode), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * erode + 1, 2 * erode + 1)))[erode:-erode, erode:-erode]
        ys, xs = np.where(r > 0)
        if len(ys) == 0:
            return 0.0, 0.0
        r = r[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        r = cv2.resize(r, (max(4, int(round(r.shape[1] * h / r.shape[0]))), h), interpolation=cv2.INTER_AREA)
        w = r.shape[1]
    r = r > 0
    W = max(obs.shape[1], w) + 24
    best = 0.0
    oc = np.zeros((h, W), bool)
    o0 = (W - obs.shape[1]) // 2
    oc[:, o0:o0 + obs.shape[1]] = obs
    for dx in range(-10, 11, 2):
        rc = np.zeros((h, W), bool)
        r0 = (W - w) // 2 + dx
        if r0 < 0 or r0 + w > W:
            continue
        rc[:, r0:r0 + w] = r
        best = max(best, float((oc & rc).sum() / max((oc | rc).sum(), 1)))
    return best, w / obs.shape[1]


def samples(root: Path, n):
    out = []
    dirs = sorted(p for p in root.iterdir() if (p / "words.json").exists())
    per = max(2, n // len(dirs) + 1)
    for d in dirs:
        wj = json.loads((d / "words.json").read_text())
        cj = json.loads((d / "captions.json").read_text())
        cal = cj["calibration"]
        line = (cal["line_top_px"] - 14, cal["line_top_px"] + 1.32 * cal["line_glyph_h_px"] + 10, cal["line_glyph_h_px"])
        good = [c for c in wj["captions"] if c["frames"] >= 6 and c["text"] == c["spoken"] and c["text"].isalpha() and 6 <= len(c["text"]) <= 12]
        good.sort(key=lambda c: -len(set(c["text"].lower())))
        for c in good[:per]:
            f = (c["on_f"] + c["off_f"]) // 2
            det = cap.detect(cv2.imread(str(d / "frames" / f"{f:05d}.jpg")), line)
            if det is None:
                continue
            out.append({"video": d.name, "frame": f, "text": c["text"], "mask": det["mask"]})
    return out[:n]


def main():
    root, fonts_dir, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 48
    fonts = fetch(fonts_dir)
    smp = samples(root, n)
    print(len(fonts), "font files,", len(smp), "caption samples:", " ".join(s["text"] for s in smp[:20]), "...")
    results = []
    for fam, fp, weights in fonts:
        for wt in (weights or [None]):
            rens = [render(s["text"], fp, wt) for s in smp]
            if any(r is None for r in rens):
                continue
            for er in (0, 1, 2, 3, 4):
                pairs = [iou_best(s["mask"], ren, er) for s, ren in zip(smp, rens)]
                ious, wr = [p[0] for p in pairs], [p[1] for p in pairs]
                results.append({"font": fam + (f" {wt}" if wt else ""), "file": fp.name, "weight": wt, "erode_px": er,
                                "iou_mean": round(float(np.mean(ious)), 4), "iou_p10": round(float(np.percentile(ious, 10)), 4),
                                "width_ratio_mean": round(float(np.mean(wr)), 4), "n": len(ious)})
    results.sort(key=lambda r: -r["iou_mean"])
    best_per_font, seen = [], set()
    for r in results:
        if r["font"] not in seen:
            seen.add(r["font"])
            best_per_font.append(r)
    for r in best_per_font[:18]:
        print(f"{r['font']:<28} IoU {r['iou_mean']:.3f} (p10 {r['iou_p10']:.3f})  width ratio {r['width_ratio_mean']:.3f}  fill eroded by {r['erode_px']} px")
    outp.write_text(json.dumps({"samples": [{k: s[k] for k in ("video", "frame", "text")} for s in smp], "ranking": best_per_font, "all": results}, indent=1))
    # visual proof sheet: observed mask vs top 4 fonts for 8 samples
    top = best_per_font[:4]
    rows = []
    for s in smp[:8]:
        h = 70
        tiles = [cv2.resize(s["mask"].astype(np.uint8) * 255, (int(s["mask"].shape[1] * h / s["mask"].shape[0]), h))]
        for r in top:
            fam = next(f for f in fonts if f[1].name == r["file"])
            ren = render(s["text"], fam[1], r["weight"])
            tiles.append(cv2.resize(ren.astype(np.uint8) * 255, (int(ren.shape[1] * h / ren.shape[0]), h)))
        wmax = max(t.shape[1] for t in tiles) + 20
        row = np.concatenate([np.pad(t, ((6, 6), (10, wmax - t.shape[1] - 10)), constant_values=0) for t in tiles], axis=0)
        rows.append(row)
    wmax = max(r.shape[1] for r in rows)
    half = len(rows) // 2
    def stack(rs):
        return np.concatenate([np.pad(r, ((0, 14), (0, wmax - r.shape[1])), constant_values=60) for r in rs], axis=0)
    left, right = stack(rows[:half]), stack(rows[half:])
    hh = max(left.shape[0], right.shape[0])
    sheet = np.concatenate([np.pad(left, ((0, hh - left.shape[0]), (0, 20)), constant_values=60), np.pad(right, ((0, hh - right.shape[0]), (0, 0)), constant_values=60)], axis=1)
    cv2.imwrite(str(outp.with_suffix(".png")), sheet)
    print("rows per sample: observed, then", " | ".join(r["font"] for r in top))


if __name__ == "__main__":
    main()
