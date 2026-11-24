#!/usr/bin/env python3
"""check_script.py — check a script.json against the numbers measured on the 20 reference videos.

  check_script.py <script.json> [--wpm 222] [--json out.json]

What it checks
  length      words, estimated runtime at the target pace, sentences, words per sentence, share of short sentences
  hook        length of the first sentence, when it ends, its form, whether it repeats the title
  wording     reading level, long words, sentences that open with So / And / But / Then, questions, exclamations,
              "you", numbers
  structure   beat order, where the explanation starts, how the script ends, no call to action
  title       4-8 words, a pattern the reference uses
  originality no 6-word sequence in common with the reference narration (hashed, see references/reference_shingles.json)

Verdicts
  ok        within 15 % of the reference mean, or equal to a count the reference shows
  in range  further than 15 % from the mean but inside what the 20 videos span
  WARN      outside the span on a soft property (rewrite unless you mean it)
  FAIL      outside the span on a core property, a copied phrase, or a call to action  -> exit code 1
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEATS = ["hook", "setup", "conflict", "escalation", "question", "explainer", "payoff", "ending"]
CONJ = {"so", "and", "but", "then", "yet", "because", "until", "while", "or", "except", "still", "instead", "which", "meanwhile", "although", "since"}
NUMS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "fifteen", "twenty", "thirty", "fifty", "hundred", "hundreds", "thousand", "million", "half", "first", "second", "third", "fifth"}
STOP = set("a an the and or but so to of in on at for with by from is are was were be been it its it's this that these those he she they we you i his her their your my our as if then than not no do does did "
           "have has had will would can could just up out into over about what when who why how one every all".split())
CTA = re.compile(r"\b(subscribe|follow (me|us|for)|like (and|this video)|comment (below|down)|link in (bio|the description)|part (two|2)|smash that|hit the bell)\b", re.I)
TITLE_PATTERNS = ((r"^why\b", "Why ..."), (r"^how\b", "How ..."), (r"^what\b", "What ..."), (r"^this\b", "This X ..."), (r"^the\b", "The X ..."), (r"^(he|she)\b", "He/She ..."), (r"^every\b", "Every ..."))


def toks(s):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", s.lower())


def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    if not w:
        return 1
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    if w.endswith("ed") and len(w) > 3 and w[-3] not in "td" and n > 1:
        n -= 1
    return max(1, n)


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[:-len(suf)]
    return w


def content(s):
    return {stem(w) for w in toks(s) if w not in STOP and len(w) > 2}


def split_sentences(text):
    parts = re.findall(r"[^.!?]+[.!?]+[\"'”’]*|[^.!?]+$", text)
    return [p.strip() for p in parts if re.search(r"[A-Za-z0-9]", p)]


def hook_form(text):
    t = text.lower()
    if re.match(r"(he|she|they|a man|a woman|a guy|an? \w+) \w+", t) and re.match(r"(he|she|they|a man|a woman|a guy|an? \w+) (\w+ed|dug|sold|bent|bet|snuck|sawed|cut|built|hid|put|took|threw|ran|made|broke|drove|paid|caught|sat|let|left|gave|wrote|hung|stood|kept|told|taught)\b", t):
        return "he/they + past-tense action"
    if t.startswith("if you"):
        return "if you + consequence"
    if t.startswith(("there's", "there is", "there are")):
        return "there is + premise"
    if t.startswith(("look at", "imagine")):
        return "imperative (look at / imagine)"
    return "claim or paradox about the world"


class Report:
    def __init__(self):
        self.rows = []

    def add(self, group, name, value, ref=None, verdict="info", note=""):
        self.rows.append({"group": group, "check": name, "value": value, "reference": ref, "verdict": verdict, "note": note})

    def num(self, group, name, value, s, core=False, mode="pct", note=""):
        """s = {mean, min, max} from style_targets.json"""
        if not s:
            return self.add(group, name, value, None, "info", note)
        ref = f"{s['mean']:g} ({s['min']:g} - {s['max']:g})"
        inside = s["min"] - 1e-9 <= value <= s["max"] + 1e-9
        close = abs(value - s["mean"]) <= 0.15 * abs(s["mean"]) if abs(s["mean"]) > 1e-9 else inside
        if mode == "range":
            v = "ok" if inside else ("FAIL" if core else "WARN")
        else:
            v = "ok" if close and inside else "in range" if inside else ("FAIL" if core else "WARN")
        self.add(group, name, round(value, 3) if isinstance(value, float) else value, ref, v, note)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--wpm", type=float, default=None)
    ap.add_argument("--json")
    a = ap.parse_args()
    T = json.loads((ROOT / "references" / "style_targets.json").read_text())
    M, SS, ST = T["metrics"], T.get("script_stats", {}), T.get("structure", {})
    wpm = a.wpm or T.get("wpm", 222)
    sc = json.loads(Path(a.script).read_text())
    entries = sc["sentences"]
    full = " ".join(e["text"].strip() for e in entries)
    S = split_sentences(full)
    W = [toks(s) for s in S]
    flat = [w for s in W for w in s]
    nw = len(flat)
    R = Report()

    # ---- length and pacing
    R.num("length", "words", nw, M.get("words"), core=True)
    R.num("length", f"estimated runtime at {wpm:g} wpm (s)", round(nw / wpm * 60 + 0.3, 1), M.get("duration_s"), core=True)
    R.num("length", "sentences", len(S), M.get("sentences"), core=True)
    R.num("length", "words per sentence (mean)", nw / len(S), M.get("avg_sentence_words"), core=True)
    R.num("length", "longest sentence (words)", max(len(s) for s in W), M.get("max_sentence_words"), mode="range")
    R.num("length", "share of sentences with 5 words or fewer", sum(len(s) <= 5 for s in W) / len(S), M.get("short_sentence_share_le5w"), mode="range")

    # ---- hook
    hook = S[0]
    R.num("hook", "first sentence (words)", len(W[0]), M.get("hook_sentence_words"), core=True, mode="range")
    R.num("hook", "first sentence ends at (s, estimate)", round(len(W[0]) / wpm * 60 + 0.1, 2), M.get("hook_sentence_end_s"), mode="range")
    form = hook_form(hook)
    forms = SS.get("hook_forms", {})
    R.add("hook", "form of the first sentence", form, ", ".join(f"{k}: {v}" for k, v in forms.items()) or None, "ok" if not forms or form in forms else "WARN")
    R.add("hook", "first sentence has a turn (comma / and / but / yet / because)", bool(re.search(r",| but | yet | and | because | with | so ", hook)), f"{SS.get('hooks_with_turn', '?')} of {T.get('n_videos', 20)} videos",
          "ok" if re.search(r",| but | yet | and | because | with | so ", hook) else "WARN", "a bare statement gives the viewer nothing to wonder about")
    title = sc.get("title", "")
    tc = content(title)
    R.num("hook", "title content words repeated in the first sentence", len(tc & content(hook)), M.get("title_words_in_first_sentence"), mode="range",
          note="the title names the topic; the first sentence shows the scene")

    # ---- wording
    syl = [syllables(w) for w in flat]
    fk = 0.39 * nw / len(S) + 11.8 * sum(syl) / nw - 15.59
    P = SS.get("pooled", {})
    R.num("wording", "Flesch-Kincaid grade", round(fk, 1), P.get("flesch_kincaid_grade"), mode="range", note="keep it at primary-school reading level")
    R.num("wording", "syllables per word", sum(syl) / nw, P.get("syllables_per_word"), mode="range")
    R.num("wording", "share of words with 3+ syllables", sum(s >= 3 for s in syl) / nw, P.get("words_ge_3_syllables_share"), mode="range")
    rest = [s for s in W[1:] if s]
    R.num("wording", "sentences opening with So / And / But / Then ...", sum(s[0] in CONJ for s in rest) / max(len(rest), 1), P.get("conjunction_opener_share"), mode="range")
    R.num("wording", "questions", sum(s.rstrip("\"'”’").endswith("?") for s in S), M.get("questions"), mode="range")
    R.num("wording", "exclamations", sum(s.rstrip("\"'”’").endswith("!") for s in S), M.get("exclamations"), mode="range")
    R.num("wording", "you / your per 100 words", sum(w.startswith("you") for w in flat) / nw * 100, M.get("you_per_100w"), mode="range")
    R.num("wording", "numbers in the script", sum(bool(re.fullmatch(r"\d[\d,]*(st|nd|rd|th|s)?", w)) or w in NUMS for w in flat), P.get("numbers_per_script"), mode="range", note="concrete numbers make a story sound true")
    R.num("wording", "contractions per 100 words", sum(("'" in w and not w.endswith("'s")) or w in ("it's", "he's", "that's", "there's", "what's", "let's", "she's") for w in flat) / nw * 100,
          P.get("contractions_per_100w"), mode="range")

    # ---- structure
    beats = [e.get("beat") for e in entries]
    unknown = sorted({b for b in beats if b not in BEATS})
    R.add("structure", "beat labels", ", ".join(dict.fromkeys(b for b in beats if b)), " > ".join(BEATS), "FAIL" if unknown or None in beats else "ok", f"unknown: {unknown}" if unknown else "")
    R.add("structure", "first beat is the hook", beats[0], "hook", "ok" if beats[0] == "hook" else "FAIL")
    order = [BEATS.index(b) for b in beats if b in BEATS]
    back = sum(1 for x, y in zip(order, order[1:]) if y < x and not (BEATS[x] in ("explainer", "payoff", "question") and BEATS[y] in ("escalation", "payoff", "explainer", "conflict")))
    R.add("structure", "beats run forward", "yes" if back == 0 else f"{back} step(s) back", None, "ok" if back == 0 else "WARN", "explainer and payoff may swap; anything else should not go backwards")
    cum, pos = 0, {}
    for e in entries:
        pos.setdefault(e.get("beat"), cum / nw)
        cum += len(toks(e["text"]))
    you_see = next((i for i, e in enumerate(entries) if re.match(r"(well, )?you see\b", e["text"].lower())), None)
    if "explainer" in pos:
        late = pos["explainer"]
        early_ok = you_see is not None and you_see <= 2
        R.num("structure", "explanation starts at (share of the script)", round(late, 2), ST.get("explainer_turn_rel") or P.get("explainer_turn_rel"), mode="range",
              note="or state the premise in sentence 2 with 'You see,' and resume the story" if not early_ok else "")
    else:
        R.add("structure", "explanation", "none", "13 of 20 videos turn to an explanation late; the others put the premise in sentence 2", "ok" if you_see is not None and you_see <= 2 else "WARN",
              "a pure story needs a twist that explains itself")
    R.add("structure", "turn marker (You see / Well / it's called)", "yes" if re.search(r"\byou see\b|(^|[.!?] )well,|\bcalled\b", full.lower()) else "no", f"'You see' in {SS.get('videos_with_you_see', 16)} of 20 videos",
          "ok" if re.search(r"\byou see\b|(^|[.!?] )well,|\bcalled\b", full.lower()) else "WARN")
    R.num("structure", "last sentence (words)", len(W[-1]), M.get("last_sentence_words"), mode="range")
    R.add("structure", "call to action", "found" if CTA.search(full) else "none", "none in 20 videos", "FAIL" if CTA.search(full) else "ok")
    R.add("structure", "last sentence is not a moral or sign-off", S[-1], "ends on the consequence or the last piece of the explanation",
          "WARN" if re.search(r"\b(moral|lesson|remember|so next time|thanks for watching|that's why you should)\b", S[-1].lower()) else "ok")
    R.add("structure", "beat map (share of words where each beat starts)", ", ".join(f"{b} {pos[b]:.0%}" for b in BEATS if b in pos), ST.get("beat_start_rel_note"), "info")

    # ---- title
    tw = len(title.split())
    R.num("title", "title words", tw, M.get("title_words"), core=True, mode="range")
    pat = next((n for p, n in TITLE_PATTERNS if re.match(p, title.lower())), "other")
    R.add("title", "title pattern", pat, ", ".join(f"{k}: {v}" for k, v in T.get("title_patterns", {}).items()) or None, "ok" if pat != "other" else "WARN")
    R.num("title", "title content words found in the script", len(tc & content(full)), M.get("title_words_in_script"), mode="range")
    R.add("title", "no hashtags, emoji or clickbait punctuation in the title", title, "plain sentence case or title case; no '#', no emoji, no '!!'",
          "WARN" if re.search(r"#|!!|\?\?|[\U0001F300-\U0001FAFF]", title) else "ok")

    # ---- fact
    R.add("fact", "fact core stated", "yes" if len(sc.get("fact", "")) > 40 else "missing", "one paragraph: what is real, what is invented", "ok" if len(sc.get("fact", "")) > 40 else "FAIL")
    R.add("fact", "sources listed", len(sc.get("sources", [])), "at least one checkable source for the fact core", "ok" if sc.get("sources") else "WARN")

    # ---- originality
    sp = ROOT / "references" / "reference_shingles.json"
    if sp.exists():
        sh = json.loads(sp.read_text())
        H, n, salt = set(sh["hashes"]), sh["n"], sh["salt"]
        hits = []
        for i in range(len(flat) - n + 1):
            g = " ".join(flat[i:i + n])
            if hashlib.sha1((salt + g).encode()).hexdigest()[:12] in H:
                hits.append(g)
        R.add("originality", f"{n}-word sequences shared with the reference narration", len(hits), "0", "FAIL" if hits else "ok", "; ".join(hits[:6]))
    else:
        R.add("originality", "reference shingles", "file missing", None, "WARN")

    # ---- print
    width = max(len(r["check"]) for r in R.rows) + 2
    cur = None
    for r in R.rows:
        if r["group"] != cur:
            cur = r["group"]
            print(f"\n{cur.upper()}")
        val = r["value"] if not isinstance(r["value"], str) or len(r["value"]) < 70 else r["value"][:67] + "..."
        ref = f"   ref {r['reference']}" if r["reference"] else ""
        note = f"   ({r['note']})" if r["note"] and r["verdict"] not in ("ok", "info") else ""
        print(f"  {r['verdict']:<8} {r['check']:<{width}} {val}{ref}{note}")
    n = {k: sum(r["verdict"] == k for r in R.rows) for k in ("ok", "in range", "WARN", "FAIL")}
    print(f"\n{n['ok']} ok, {n['in range']} in range, {n['WARN']} warnings, {n['FAIL']} failures")
    if a.json:
        Path(a.json).write_text(json.dumps(R.rows, indent=1))
    sys.exit(1 if n["FAIL"] else 0)


if __name__ == "__main__":
    main()
