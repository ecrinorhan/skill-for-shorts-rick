#!/usr/bin/env python3
"""Wording statistics of the reference narration (no text is written out) + hashed word shingles for an originality check.

Usage: 22_script_stats.py <work_dir> <analysis_dir> <skill_dir>
Reads  <work>/<video>/words.json (corrected transcript with word times)
Writes <analysis>/data/script_stats.json                per-video and pooled numbers: sentence openers, hook form, reading
                                                         level, contractions, numbers, questions, direct-speech markers,
                                                         where the turns sit in the runtime
       <skill>/references/reference_shingles.json        salted, truncated SHA-1 hashes of every 6-word sequence in the 20
                                                         transcripts. check_script.py uses it to flag copied phrases. The
                                                         hashes are an unordered set; the narration cannot be read back.
"""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

SALT = "fact-story-shorts/v1"
NGRAM = 6
CONJ = {"so", "and", "but", "then", "yet", "because", "until", "while", "or", "except", "still", "instead", "which", "meanwhile", "although", "since"}
PRON = {"he", "she", "they", "it", "you", "we", "i", "he's", "she's", "they're", "it's", "you're", "we're", "i'm", "he'd", "they'll", "you'll", "i've"}
DET = {"the", "a", "an", "his", "her", "their", "this", "that", "every", "one", "each", "these", "those", "some", "all", "your", "my", "our", "no", "two", "three", "another", "any", "anyone", "everyone", "nobody", "somebody"}
TIME = {"at", "by", "soon", "eventually", "after", "next", "when", "now", "today", "tonight", "later", "once", "before", "finally", "suddenly", "within", "halfway", "deeper", "in", "on", "up", "around", "under"}
DISC = {"well", "wait", "see", "okay", "sir", "yeah", "pal", "congrats", "hey", "no", "yes", "oh", "sorry", "wow", "imagine", "look", "just", "not", "even", "maybe", "trust", "steer", "get"}
SPEECH_VERBS = re.compile(r"\b(says?|said|goes|asks?|yells?|laughs?|shouts?|replies|whispers?|tells?)\b", re.I)
FIRST_PERSON = re.compile(r"\b(i|i'm|i've|i'll|i'd|we|we're|we'll|we've|my|our|me|us)\b", re.I)
JUMP = re.compile(r"\b(the next (morning|night|day|week)|that night|one (morning|night|day|monday)|by (midnight|the end of|july|the time)|a (week|year|month) later|(next|every) (morning|night|week)|"
                  r"eventually|soon|at (night|three|two)|then summer|within a (year|week|month)|at this point|at first|until one)\b", re.I)


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


def sentences(W):
    out, cur = [], []
    for w in W:
        cur.append(w)
        if w["text"].rstrip("\"'”’")[-1:] in ".?!":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def opener_class(first, second):
    if first == "you" and second == "see":
        return "you see"
    if first in ("well",):
        return "well"
    if first in CONJ:
        return "conjunction (so / and / but / then ...)"
    if first in PRON:
        return "pronoun (he / they / it / you ...)"
    if first in DET:
        return "article or determiner (the / his / a / every ...)"
    if first in TIME:
        return "time or place (at / by / soon / in ...)"
    if first in DISC:
        return "interjection or imperative"
    return "other"


def hook_form(text):
    t = text.lower()
    if re.match(r"(he|she|they|a man|a woman|a guy) \w+ed\b|(he|she|they|a man) (dug|sold|bent|bet|snuck|sawed|drilled|rolled|loaded|slammed|poured|scanned|buried|painted|stopped|cut|built|hid|put|took|threw|ran|made|broke|drove)\b", t):
        return "he/they + past-tense action"
    if t.startswith("if you"):
        return "if you + consequence"
    if t.startswith(("there's", "there is", "there are")):
        return "there is + premise"
    if t.startswith(("look at", "imagine")):
        return "imperative (look at / imagine)"
    return "claim or paradox about the world"


def stat(a):
    a = np.array([x for x in a if x is not None], float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)), "mean": round(float(a.mean()), 3), "sd": round(float(a.std(ddof=1)), 3) if len(a) > 1 else 0.0, "median": round(float(np.median(a)), 3),
            "min": round(float(a.min()), 3), "max": round(float(a.max()), 3)}


def main():
    work, adir, skill = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    per, shingles, openers, hooks = [], set(), Counter(), Counter()
    for d in sorted(p for p in work.iterdir() if (p / "words.json").exists()):
        wj = json.loads((d / "words.json").read_text())
        W = wj["words"]
        dur = json.loads((d / "specs.json").read_text())["duration_s"]
        S = sentences(W)
        texts = [" ".join(w["text"] for w in s) for s in S]
        T = [toks(t) for t in texts]
        flat = [w for t in T for w in t]
        for i in range(len(flat) - NGRAM + 1):
            shingles.add(hashlib.sha1((SALT + " ".join(flat[i:i + NGRAM])).encode()).hexdigest()[:12])
        cls = Counter(opener_class(t[0], t[1] if len(t) > 1 else "") for t in T[1:] if t)
        openers.update(cls)
        nsent = max(len(T) - 1, 1)
        syl = [syllables(w) for w in flat]
        nw = len(flat)
        fre = 206.835 - 1.015 * nw / len(S) - 84.6 * sum(syl) / nw
        fk = 0.39 * nw / len(S) + 11.8 * sum(syl) / nw - 15.59
        q = [s[0]["start"] / dur for s, t in zip(S, texts) if t.rstrip("\"'”’").endswith("?")]
        ys = [s[0]["start"] / dur for s, t in zip(S, T) if t[:2] == ["you", "see"] or t[:3] == ["well", "you", "see"]]
        well = [s[0]["start"] / dur for s, t in zip(S, T) if t[:1] == ["well"]]
        called = [s[0]["start"] / dur for s, t in zip(S, texts) if re.search(r"\b(it's|they) called\b|\bis called\b", t.lower())]
        ever = [s[0]["start"] / dur for s, t in zip(S, texts) if re.match(r"(ever|think about|imagine)\b", t.lower()) and s[0]["start"] / dur > 0.3]
        first_person = [i for i, t in enumerate(texts) if FIRST_PERSON.search(t)]
        hooks[hook_form(texts[0])] += 1
        nums = [w for w in flat if re.fullmatch(r"\d[\d,]*(st|nd|rd|th|s)?", w) or w in ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "fifteen", "twenty", "thirty", "fifty", "hundred", "hundreds", "thousand", "million", "half", "first", "second", "third", "fifth")]
        names = Counter(w["text"].strip(".,!?\"'") for s in S for w in s[1:] if re.match(r"[A-Z][a-z]{2,}", w["text"]) and w["text"].strip(".,!?\"'").lower() not in CONJ | PRON | DET | TIME | DISC)
        per.append({
            "video": d.name, "sentences": len(S), "words": nw,
            "opener_share": {k: round(v / nsent, 3) for k, v in cls.items()},
            "conjunction_opener_share": round(cls.get("conjunction (so / and / but / then ...)", 0) / nsent, 3),
            "hook_form": hook_form(texts[0]), "hook_first_two_words": " ".join(T[0][:2]), "hook_has_comma_or_and_but_turn": bool(re.search(r",| but | yet | and | because | with ", texts[0])),
            "syllables_per_word": round(sum(syl) / nw, 3), "words_ge_3_syllables_share": round(float(np.mean([s >= 3 for s in syl])), 3), "letters_per_word": round(float(np.mean([len(re.sub(r"[^a-z0-9]", "", w)) for w in flat])), 2),
            "flesch_reading_ease": round(fre, 1), "flesch_kincaid_grade": round(fk, 1),
            "contractions_per_100w": round(sum("'" in w and not w.endswith("'s") or w in ("it's", "he's", "that's", "there's", "what's", "let's", "she's") for w in flat) / nw * 100, 2),
            "numbers_per_script": len(nums), "like_similes": sum(1 for w in flat if w == "like"),
            "just_per_100w": round(flat.count("just") / nw * 100, 2),
            "speech_verb_sentences": sum(1 for t in texts if SPEECH_VERBS.search(t)), "first_person_sentences_proxy_for_direct_speech": len(first_person),
            "first_person_sentence_positions": [round(S[i][0]["start"] / dur, 2) for i in first_person],
            "time_jump_phrases": sum(len(JUMP.findall(t)) for t in texts),
            "question_positions": [round(x, 2) for x in q], "you_see_positions": [round(x, 2) for x in ys], "well_positions": [round(x, 2) for x in well],
            "it_is_called_positions": [round(x, 2) for x in called], "analogy_turn_positions": [round(x, 2) for x in ever],
            "capitalised_mid_sentence_words_n": len(names), "sentence_len_first_half_mean": round(float(np.mean([len(t) for t in T[:len(T) // 2]])), 1),
            "sentence_len_second_half_mean": round(float(np.mean([len(t) for t in T[len(T) // 2:]])), 1),
            "last_sentence_start_rel": round(S[-1][0]["start"] / dur, 3), "second_sentence_starts_you_see": T[1][:2] == ["you", "see"] if len(T) > 1 else False,
            "explainer_turn_rel": round(max([x for x in ys + well if x > 0.3], default=float("nan")), 2) if [x for x in ys + well if x > 0.3] else None,
        })
    keys = ["conjunction_opener_share", "syllables_per_word", "words_ge_3_syllables_share", "letters_per_word", "flesch_reading_ease", "flesch_kincaid_grade", "contractions_per_100w", "numbers_per_script",
            "like_similes", "just_per_100w", "speech_verb_sentences", "first_person_sentences_proxy_for_direct_speech", "time_jump_phrases", "sentence_len_first_half_mean", "sentence_len_second_half_mean",
            "explainer_turn_rel"]
    tot = sum(openers.values())
    out = {
        "note": "Numbers only; the narration text is not stored. Reading-level formulas use a vowel-group syllable estimate.",
        "pooled": {k: stat([p[k] for p in per]) for k in keys},
        "sentence_opener_share_pooled": {k: round(v / tot, 3) for k, v in openers.most_common()},
        "hook_forms": dict(hooks.most_common()),
        "videos_with_you_see": sum(bool(p["you_see_positions"]) for p in per),
        "videos_with_you_see_as_second_sentence": sum(p["second_sentence_starts_you_see"] for p in per),
        "videos_with_late_explainer_turn_after_30pct": sum(p["explainer_turn_rel"] is not None for p in per),
        "videos_with_question": sum(bool(p["question_positions"]) for p in per),
        "videos_with_it_is_called": sum(bool(p["it_is_called_positions"]) for p in per),
        "videos_with_analogy_turn": sum(bool(p["analogy_turn_positions"]) for p in per),
        "question_positions_all": sorted(x for p in per for x in p["question_positions"]),
        "you_see_positions_all": sorted(x for p in per for x in p["you_see_positions"]),
        "videos": per,
    }
    (adir / "data" / "script_stats.json").write_text(json.dumps(out, indent=1))
    (skill / "references").mkdir(parents=True, exist_ok=True)
    (skill / "references" / "reference_shingles.json").write_text(json.dumps({"note": "salted SHA-1 (first 12 hex) of every 6-word sequence in the 20 reference transcripts; unordered; used only to flag copied phrases",
                                                                            "salt": SALT, "n": NGRAM, "hashes": sorted(shingles)}, separators=(",", ":")))
    print("videos", len(per), "| shingles", len(shingles))
    for k, v in out["pooled"].items():
        print(f"{k:<48}{v}")
    for k in ("sentence_opener_share_pooled", "hook_forms", "videos_with_you_see", "videos_with_you_see_as_second_sentence", "videos_with_late_explainer_turn_after_30pct", "videos_with_question",
              "videos_with_it_is_called", "videos_with_analogy_turn", "question_positions_all", "you_see_positions_all"):
        print(k, out[k])
    for p in per:
        print(p["video"][:2], p["hook_form"], "|", p["hook_first_two_words"], "| you see", p["you_see_positions"], "| well", p["well_positions"], "| q", p["question_positions"], "| 1st-person", p["first_person_sentence_positions"],
              "| called", p["it_is_called_positions"], "| analogy", p["analogy_turn_positions"], "| FK", p["flesch_kincaid_grade"])


if __name__ == "__main__":
    main()
