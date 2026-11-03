"""The Commercials page: a library of TV-spot genres as structured templates, a brief-to-script writer, and the generator that renders a full spot on the recipe queue.
The page only shows what a real run left behind: commercial_proof.json and the media in web/commercials/, recorded by scripts/record_commercial.py after a person looked at every shot. Flaws stay on the page, labelled.
Every brand, product and person is invented; studio/commercial_safety.py holds the rules and runs on every brief, script and rewrite."""
import json, re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from studio import commercials as C, recipes as R

router = APIRouter(prefix="/api/commercials")
PAGE = {"tab": "commercials", "label": "Commercials", "title": ["Commercials", "Twenty-four kinds of TV spot. Every brand invented.", "From the pharma parody to the big-game comedy: pick a genre, write a brief, get a script, a shot list and a finished, captioned spot. Every word on screen is set by ffmpeg, never painted by a model."], "module": "commercials.js", "export": "Commercials", "css": "commercials.css"}
HERE = Path(__file__).resolve().parent; PROOF = HERE / "commercial_proof.json"; WEB = HERE / "web" / "commercials"
RULES = ["Only invented brands, products and people.", "No real brand names, logos, trademarks, celebrities, politicians or parties: a list and a near-miss check refuse them.", "Pharma-style spots sell an invented drug for an invented condition, make no medical claims, and carry a parody card.",
         "Every spot carries an “AI-generated” label for its whole length.", "Adults only, fully clothed. Nothing sexual. No alcohol or tobacco: the beer-style genre sells a soda.", "Words on screen come from ffmpeg and a font, never from an image model."]


def _proof():
    try: return json.loads(PROOF.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {"spots": []}


def problems():
    """What the proof file gets wrong, as sentences. A test keeps this empty."""
    bad = []; ids = {g["id"] for g in C.genres()}
    for sp in _proof().get("spots", []):
        sid = sp.get("id", "?")
        if sp.get("genre") not in ids: bad.append(f"{sid}: unknown genre {sp.get('genre')}")
        if sp.get("status") not in ("passed", "flawed", "failed"): bad.append(f"{sid}: status {sp.get('status')}")
        for k in ("video", "poster", "sheet"):
            if sp.get(k) and not (WEB / sp[k]).is_file(): bad.append(f"{sid}: {sp[k]} is not in web/commercials")
        for sh in sp.get("shots", []):
            if sh.get("frame") and not (WEB / sh["frame"]).is_file(): bad.append(f"{sid}: {sh['frame']} is not in web/commercials")
        if sp.get("status") != "failed" and not (sp.get("audio") or {}).get("lufs"): bad.append(f"{sid}: no audio measurement")
        if (sp.get("audio") or {}).get("listened_by_a_person") is not False: bad.append(f"{sid}: must say whether a person listened")
    return bad


def _summary(g):
    return {**{k: g[k] for k in ("id", "title", "group", "pitch", "lengths", "tone", "look", "vo", "music", "type", "legal")}, "parody": bool(g.get("parody")), "fields": g["fields"], "placeholders": C.placeholders(g),
            "beats": g["beats"], "end_card": g["end_card"], "labels": {k: C.FIELD_LABELS.get(k, k.replace("_", " ").capitalize()) for k in g["fields"]}}


@router.get("/genres")
def genres_get():
    return {"genres": [_summary(g) for g in C.genres()], "tones": C.tones(), "lengths": list(C.LENGTHS), "end_card": C.END_CARD, "parody_card": C.PARODY_CARD, "models": C.MODELS, "vo_engines": C.VO_ENGINES, "rules": RULES, "llm": bool(C.llm_ready())}


def _brief(b):
    brief = {k: v for k, v in (b.get("brief") or {}).items() if isinstance(k, str) and isinstance(v, (str, int, float))}
    for k in ("length", "tone"):
        if b.get(k) not in (None, ""): brief[k] = b[k]
    return brief


def _with_lines(s, b):
    """The script with the voice-over lines the page sent (edited, or rewritten earlier), kept only if they keep its shape and every rule."""
    vo, end = b.get("vo"), b.get("end_vo")
    if vo is None and end is None: return s
    if not isinstance(vo, list) or len(vo) != len(s["beats"]): raise HTTPException(400, "the voice-over lines don't match the script's beats")
    s2 = json.loads(json.dumps(s))
    for beat, line in zip(s2["beats"], vo): beat["vo"] = re.sub(r"\s+", " ", str(line or "")).strip()[:400]
    if isinstance(end, str): s2["end_card"]["vo"] = re.sub(r"\s+", " ", end).strip()[:200]
    bad = C.script_problems(s2)
    if bad: raise HTTPException(400, " ".join(bad[:6]))
    s2["writer"] = str(b.get("writer") or "edited on the page")[:80]; return s2


@router.post("/script")
def script_post(b: dict):
    """A brief -> the script, the shot list and the timing. With rewrite: true, the local model punches up the voice-over, if it is already up."""
    s = C.build_script(str(b.get("genre") or ""), _brief(b))
    if b.get("rewrite"): s = C.rewrite(s)
    return {"script": s, "steps": [{k: x.get(k) for k in ("id", "label", "model", "type")} for x in C.specs(s, engine=str(b.get("engine") or "kokoro"))]}


@router.post("/run")
def run_post(b: dict):
    """Render the spot. The script is rebuilt here from the genre and the brief, so nothing the page sends can skip the rules."""
    s = _with_lines(C.build_script(str(b.get("genre") or ""), _brief(b)), b)
    try: seed_add = int(b.get("seed_add") or 0)
    except (TypeError, ValueError): seed_add = 0
    return C.start(s, str(b.get("engine") or "kokoro"), seed_add)


@router.get("/runs/{rid}")
def run_get(rid: str):
    r = R.get_run(rid)
    if not r or r.get("recipe") != "commercial": raise HTTPException(404, "no such run")
    return R._public(r) if rid in R.RUNS else {**r, "position": 0}


@router.post("/runs/{rid}/cancel")
def run_cancel(rid: str):
    r = R.RUNS.get(rid)
    if not r or r.get("recipe") != "commercial": raise HTTPException(404, "no such run")
    r["_cancel"] = True
    if r["status"] == "queued": r["status"] = "cancelled"; R._save(r)
    return {"ok": True, "status": r["status"]}


@router.get("/proof")
def proof_get(): return _proof()
