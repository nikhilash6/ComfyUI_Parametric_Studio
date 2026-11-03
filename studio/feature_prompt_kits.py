"""Per-model prompt-writer kits and the prompt enhancer that uses them. prompt_kits.json holds, for each model, the notes the local writer gets, the words to avoid, the
model's own negative and its settings, with sources. POST /api/prompt-kits/enhance turns a short idea into a prompt for the goal's model: the verified prompt_enhancer subagent
writes it with that model's notes, and if the language model is off or its answer fails the checks, a fixed formula writes one instead, and the reply says which. Nothing here
starts a render. No page of its own: the Create page's "Improve" button uses these routes."""
import json, re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from studio import sfw

router = APIRouter(prefix="/api/prompt-kits")
DATA = Path(__file__).resolve().parent / "prompt_kits.json"
MAX_IDEA = 1200
H3_FIELDS = ("integrated_multimodal_description:", "overall_soundscape:", "non_diegetic_music:")
_cache: dict = {}


def load():
    mt = DATA.stat().st_mtime
    if _cache.get("mt") != mt: _cache.update(mt=mt, d=json.loads(DATA.read_text(encoding="utf-8")))
    return _cache["d"]


def kit_for(goal=None, kit=None):
    """The kit for a Create goal, or a kit by id. None when there is none."""
    for k in load()["kits"]:
        if (kit and k["id"] == kit) or (goal and goal in k["goals"]): return k
    return None


def brief(k, edit=False):
    """What the writer is told: the target model, its notes, and the word range."""
    notes = k["edit_notes"] if edit and k.get("edit_notes") else k["notes"]
    lo, hi = k["words"]
    return f"Target model family: {k['label']}. Style notes for this model: {notes} Write {lo} to {hi} words. Safe for work only, no real people, no brands."


def wrap(k, text):
    """H3 wants its three fields. A plain description goes in the first one, with a neutral sound line and no score."""
    if k.get("wrap") != "h3_fields" or all(f in text for f in H3_FIELDS): return text
    return f"{H3_FIELDS[0]} {text.strip()}\n\n{H3_FIELDS[1]} Natural sound of the place and the action.\n\n{H3_FIELDS[2]} N/A"


def lint(k, text):
    """The kit's own checks on a finished prompt, as sentences: the word range, the words to avoid, and one camera move for video."""
    from psn.camera import one_move_problems
    body = text.split(H3_FIELDS[1])[0] if k.get("wrap") == "h3_fields" else text
    n = len(body.replace(H3_FIELDS[0], "").split()); lo, hi = k["words"]; out = []
    if not lo <= n <= hi: out.append(f"{n} words; {k['label']} prompts work best at {lo} to {hi}")
    low = text.lower(); out += [f"avoid \"{w}\" for {k['label']}" for w in k.get("avoid") or [] if w.lower() in low]
    if k["kind"] == "video": out += one_move_problems(body)
    if sfw.flagged(text): out.append("non-SFW wording")
    return out


def _fallback(k, idea, seed, video):
    from psn.fallback_prompt import build_prompt
    lead = {"flux3_klein": "Full-color photograph, ", "flux2_klein": "A photograph, ", "h3": "Live-action, cinematic, "}.get(k["id"], "")
    text = build_prompt({"subject": idea}, seed, video)
    return lead + text if lead and not text.lower().startswith(lead.strip(", ").lower()) else text


def enhance(idea, goal=None, kit=None, seed=0, edit=False, runner=None):
    """-> {"prompt", "negative", "source": "model" | "fallback", "problems", "kit"}. The model's answer is used only when the subagent's verifier accepts it."""
    idea = re.sub(r"\s+", " ", str(idea or "")).strip()[:MAX_IDEA]
    if not idea: raise HTTPException(400, "Write a few words first, then improve them.")
    sfw.check(idea)
    k = kit_for(goal, kit)
    if not k: raise HTTPException(404, "No prompt kit for that model yet.")
    video = k["kind"] == "video"; lo, hi = k["words"]
    first = next((w for w in (x.strip(",.;:!?\"'") for x in idea.split()) if w.lower() not in ("a", "an", "the", "my", "some", "one")), "")
    neg = k.get("negative") or {}; neg_text = neg.get("text", "") if neg.get("default") == "on" else ""   # the goals already send their own negatives; a kit only adds one it marks on
    try:
        if runner is None:
            from psn.subagents import run_subagent as runner
        r = runner("prompt_enhancer", f"{brief(k, edit)}\n\nIdea: {idea}", {"must_keep": [first] if len(first) > 2 else [], "video": video, "min_words": lo, "max_words": hi + 40}, max_attempts=2, max_seconds=120)
        if r.ok:
            text = wrap(k, r.output["prompt"])
            return {"prompt": text, "negative": neg_text, "source": "model", "problems": lint(k, text), "kit": k["id"]}
        why = list(r.problems)
    except HTTPException: raise
    except Exception as e: why = [f"the local writer did not answer ({type(e).__name__})"]
    text = wrap(k, _fallback(k, idea, seed, video))
    return {"prompt": text, "negative": neg_text, "source": "fallback", "problems": why[:4] + lint(k, text), "kit": k["id"]}


@router.get("")
def kits_get():
    d = load()
    return {"about": d["about"], "kits": [{x: k[x] for x in ("id", "label", "goals", "families", "kind", "words", "notes", "edit_notes", "avoid", "negative", "settings", "sources", "proof") if x in k} for k in d["kits"]], "sdxl_checkpoints": d["sdxl_checkpoints"]}


@router.get("/for/{goal}")
def kit_get(goal: str):
    k = kit_for(goal)
    if not k: raise HTTPException(404, "No prompt kit for that goal yet.")
    return k


@router.post("/enhance")
def enhance_post(b: dict = None):
    b = b or {}
    return enhance(b.get("prompt") or b.get("idea"), goal=b.get("goal"), kit=b.get("kit"), seed=int(b.get("seed") or 0), edit=bool(b.get("edit")))


@router.post("/lint")
def lint_post(b: dict = None):
    b = b or {}; k = kit_for(b.get("goal"), b.get("kit"))
    if not k: raise HTTPException(404, "No prompt kit for that model yet.")
    return {"problems": lint(k, str(b.get("prompt") or ""))}
