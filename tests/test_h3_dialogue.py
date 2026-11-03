"""H3 speaks only the words it is given. The vendor prompt guide (4.4) puts speech after a speaker phrase and an (S1) ID, as
<d>[English] exact words</d>. A step that only says "they speak to the camera" gets made-up, speech-like babble (measured by Whisper
on our renders, 2026-11-02). These checks keep every speaking video template on written words. Fixtures only: no live port, no GPU."""
import json, re
from studio import recipes as R

TEMPLATES = [r for r in R.library() if r["id"].startswith("vid_")]
D = re.compile(r"\(S1\) [^<]*?: <d>\[English\] \{([a-z_][a-z0-9_]*)\}</d>")
TALKS = re.compile(r"\b(speak\w*|says?|saying|talks?|explains?|asks?|answers?|announces?|tells?|thanks?|confess\w*|brags?|insists?|declaims?)\b", re.I)


def speaking(r):
    return [s for s in r["steps"] if "<d>" in str(s.get("prompt", "")) or TALKS.search(str(s.get("prompt", "")).split("overall_soundscape")[0])]


def shot_seconds(s):
    return s["frames"] / 24 if s.get("frames") else float((s.get("options") or {}).get("seconds") or 0)


def test_no_step_asks_for_speech_without_the_words():
    for r in TEMPLATES:
        for s in r["steps"]:
            p = str(s.get("prompt", ""))
            assert "speak directly to the camera" not in p, (r["id"], s["id"])
            if TALKS.search(p.split("overall_soundscape")[0]): assert D.search(p), (r["id"], s["id"], p[:200])


def test_every_line_is_a_declared_field_with_real_words():
    n = 0
    for r in TEMPLATES:
        vals = R.field_defaults(r)
        for s in speaking(r):
            for key in D.findall(s["prompt"]):
                line = vals.get(key); n += 1
                assert line and line.strip(), (r["id"], s["id"], key)
                assert "{" not in line and "<" not in line and "[" not in line, (r["id"], key, line)       # recipes fill in one pass; the tag is added by the template
                assert line.rstrip()[-1] in ".!?", (r["id"], key, line)                                  # the guide keeps terminal punctuation inside <d>
    assert n >= 80


def test_lines_fit_their_shot():
    """Pacing from the H3 prompt rules: about 3 words a second for a reference shot, 4.2 for text-to-video."""
    for r in TEMPLATES:
        vals = R.field_defaults(r)
        for s in speaking(r):
            secs = shot_seconds(s); rate = 3.0 if s["type"] == "h3_reference" else 4.2
            for key in D.findall(s["prompt"]):
                words = len(vals[key].split()); assert 0 < words <= rate * secs, (r["id"], s["id"], words, secs)


def test_the_filled_prompt_reaches_h3_with_the_words_inside_the_tag():
    r = R.find("vid_short_greeting"); s = r["steps"][0]; p = R._fill(s["prompt"], R.field_defaults(r))
    assert "(S1) looks into the camera and warmly says: <d>[English] Happy birthday, Sam!</d>" in p and "{" not in p


def test_the_tip_says_why_the_words_are_written():
    for r in TEMPLATES:
        if speaking(r): assert any("word for word inside <d>[English]" in t for t in r.get("tips", [])), r["id"]
