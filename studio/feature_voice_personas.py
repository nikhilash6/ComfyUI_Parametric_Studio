"""Voice personas for the Voices page's design models: 21 trait groups and 56 ready personas from voice_personas.json, joined into one description a design model can read.
Every phrase describes a voice, never a person, a character or a brand, and every head says "adult". A description over the limit loses its least important traits first (drop_order), and the
reply says which. Traits that pull against each other (slow and fast, soft and loud, low and high) come back as warnings. No page of its own: the Voices page uses these routes."""
import json, re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from studio import sfw

router = APIRouter(prefix="/api/voices/personas")
DATA = Path(__file__).resolve().parent / "voice_personas.json"
LIMIT = 300              # feature_voices.command() keeps the first 300 characters of a voice description
BRANDS = re.compile(r"\b(siri|alexa|google|disney|pixar|marvel|netflix|youtube|tiktok|instagram|spotify|bbc|cnn|npr|hbo|nike|apple|amazon)\b", re.I)
_cache: dict = {}


def load():
    mt = DATA.stat().st_mtime
    if _cache.get("mt") != mt:
        d = json.loads(DATA.read_text(encoding="utf-8"))
        d["_cats"] = {c["id"]: {**c, "_by": {o["key"]: o for o in c["options"]}} for c in d["categories"]}
        d["_personas"] = {p["id"]: p for p in d["personas"]}
        _cache.update(mt=mt, d=d)
    return _cache["d"]


def problems(d=None):
    """Everything wrong with the catalogue, as sentences. Empty when it is sound."""
    d = d or load(); out = []
    for c in d["categories"]:
        if not c["options"] or c["options"][0]["key"] != "auto": out.append(f"{c['id']}: the first option must be auto")
        for o in c["options"]:
            text = o["label"] + " " + o["phrase"]
            if sfw.flagged(text) or BRANDS.search(text): out.append(f"{c['id']}/{o['key']}: wording not allowed")
            if o["key"] != "auto" and not o["phrase"].strip(): out.append(f"{c['id']}/{o['key']}: no phrase")
    for cid in d.get("drop_order") or []:
        if cid not in d["_cats"]: out.append(f"drop_order names an unknown group {cid}")
    for p in d["personas"]:
        for cid, key in p["picks"].items():
            if cid not in d["_cats"] or key not in d["_cats"][cid]["_by"]: out.append(f"persona {p['id']}: unknown pick {cid}={key}")
        if "presentation" not in p["picks"] or "age" not in p["picks"]: out.append(f"persona {p['id']}: needs a presentation and an age")
        if sfw.flagged(p["label"], p["blurb"]) or BRANDS.search(p["label"] + " " + p["blurb"]): out.append(f"persona {p['id']}: wording not allowed")
    return out


def clean_picks(picks):
    """Only real groups and real keys, and nothing set to auto. Raises on anything unknown rather than guessing."""
    d = load(); out = {}
    for cid, key in (picks or {}).items():
        c = d["_cats"].get(str(cid))
        if c is None: raise HTTPException(400, f"no voice trait group called {cid}")
        if str(key) not in c["_by"]: raise HTTPException(400, f"{c['label']} has no option {key}")
        if key != "auto" and ("design" in c.get("use", []) or cid == "language"): out[cid] = str(key)
    return out


def _conflicts(d, picks):
    tags = {}
    for cid, key in picks.items():
        for t in d["_cats"][cid]["_by"][key].get("tags") or []: tags.setdefault(t, []).append(d["_cats"][cid]["_by"][key]["label"])
    return [f"'{a1}' and '{b1}' pull against each other" for a, b in d.get("conflicts") or [] for a1 in tags.get(a, []) for b1 in tags.get(b, [])]


def compose(picks, limit=LIMIT):
    """-> {"text", "dropped", "warnings", "language", "length"}. The head always says adult: "An adult woman in her mid twenties, ..." """
    d = load(); live = clean_picks(picks); dropped = []
    def build(cur):
        pres = d["_cats"]["presentation"]["_by"].get(cur.get("presentation", ""))
        age = d["_cats"]["age"]["_by"].get(cur.get("age", ""))
        noun = pres["phrase"] if pres else "voice"
        if "adult" not in noun.lower(): noun = "adult " + noun
        head = ("An " if noun[0].lower() in "aeiou" else "A ") + noun
        if age: head += " " + age["phrase"].replace("{poss}", (pres or {}).get("poss", "their"))
        rest = [d["_cats"][cid]["_by"][k]["phrase"] for cid, k in cur.items() if cid not in ("presentation", "age")]
        return head + (", " + ", ".join(rest) if rest else "") + "."
    text = build(live)
    order = [c for c in d.get("drop_order") or [] if c in live] + [c["id"] for c in reversed(d["categories"]) if c["id"] in live and c["id"] not in d.get("drop_order", []) and c["id"] not in ("presentation", "age")]
    while len(text) > limit and order:
        cid = order.pop(0); live.pop(cid, None); dropped.append(cid); text = build(live)
    lang = d["_cats"]["language"]["_by"].get(live.get("language", ""), {}).get("language") or "English"
    return {"text": text, "dropped": dropped, "warnings": _conflicts(d, live), "language": lang, "length": len(text)}


def personas():
    d = load()
    return [{"id": p["id"], "label": p["label"], "blurb": p["blurb"], "picks": p["picks"], **{k: v for k, v in compose(p["picks"]).items() if k in ("text", "dropped", "warnings")}} for p in d["personas"]]


@router.get("")
def personas_get():
    d = load()
    groups = [{"id": c["id"], "label": c["label"], "help": c.get("help", ""), "options": [{"key": o["key"], "label": o["label"]} for o in c["options"]]} for c in d["categories"] if "design" in c.get("use", [])]
    return {"about": d["note"], "personas": personas(), "groups": groups, "limit": LIMIT, "counts": {"personas": len(d["personas"]), "groups": len(d["categories"]), "options": sum(len(c["options"]) for c in d["categories"])}}


@router.post("/compose")
def compose_post(b: dict = None):
    b = b or {}
    picks = dict(load()["_personas"][b["persona"]]["picks"]) if b.get("persona") in load()["_personas"] else {}
    if b.get("persona") and not picks: raise HTTPException(404, "no such persona")
    picks.update(b.get("picks") or {})
    return compose(picks)
