"""The Sampling Lab: what samplers, schedulers, guidance, noise and latent maths really do, read from the source of ComfyUI and the node packs, with what can run here and proof for each.
Data is built by scripts/build_sampling_lab.py from the Sampling Atlas and kept in studio/sampling_lab/: atlas.json (facts in our own words, no pack code), measures.json (numbers from core's own code on the CPU), renders.json with the JPEGs in web/sampling_lab (fixed-seed proof renders).
live.json (every sampler and scheduler name this machine's ComfyUI offered, with pack, licence, entry and render; built by scripts/add_pool51_atlas.py).
GET /api/sampling/summary, /atlas, /entry/{id}, /measures, /renders, /live, /walk, /graph. POST /api/sampling/run queues one core-only graph, the same builder as the proof sweep."""
import json, os, sys, time, hashlib
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from studio import sfw, sampling_graph as G

router = APIRouter()
DATA = Path(__file__).resolve().parent / "sampling_lab"
_cache: dict = {}

def _load(name, empty):
    p = DATA / name
    try: sig = p.stat().st_mtime
    except OSError: return empty
    hit = _cache.get(name)
    if hit and hit[0] == sig: return hit[1]
    d = json.loads(p.read_text(encoding="utf8")); _cache[name] = (sig, d); return d
def atlas(): return _load("atlas.json", {"entries": [], "counts": {}, "credits": [], "coverage": {}})
def measures(): return _load("measures.json", {})
def renders(): return _load("renders.json", {"renders": [], "models": {}})
def walk(): return _load("walk.json", {})
def live(): return _load("live.json", {"samplers": [], "schedulers": [], "guidance": []})

LIST_FIELDS = ("id", "name", "family", "subfamily", "in_core", "live", "needs_pack", "label", "plain", "rendered", "providers_n", "licences", "verdicts", "core_ref", "rendered_ids")
@router.get("/api/sampling/summary")
def summary():
    a = atlas(); r = renders()
    return {"counts": a.get("counts", {}), "coverage": a.get("coverage", {}), "entries": len(a["entries"]), "core": sum(1 for e in a["entries"] if e.get("in_core")), "live": sum(1 for e in a["entries"] if e.get("live")), "renders": sum(1 for x in r["renders"] if x.get("status") == "rendered")}
@router.get("/api/sampling/atlas")
def atlas_list():
    a = atlas()
    return {"entries": [{**{k: e.get(k) for k in LIST_FIELDS}, "by": [(p.get("author") or "") for p in e.get("providers", [])[:1]]} for e in a["entries"]], "counts": a.get("counts", {}), "coverage": a.get("coverage", {}), "credits": a.get("credits", []), "surprises": a.get("surprises", [])}
@router.get("/api/sampling/entry/{eid}")
def entry(eid: str):
    for e in atlas()["entries"]:
        if e["id"] == eid: return e
    raise HTTPException(404, "No such method in the atlas.")
@router.get("/api/sampling/measures")
def measures_route(): return measures()
@router.get("/api/sampling/renders")
def renders_route(): return renders()
@router.get("/api/sampling/live")
def live_route():
    """Every sampler and scheduler name this machine's ComfyUI offered when the page was built, and the guidance that runs here, each with its pack, licence, atlas entry and render."""
    return live()
@router.get("/api/sampling/walk")
def walk_route():
    """The latent walk: two seeds slerped, two prompts lerped, every sampler step, rendered on a lane of its own by scripts/latent_walk_renders.py."""
    w = walk()
    if not w: raise HTTPException(404, "No latent walk has been rendered on this machine yet.")
    return w

def params(q):
    """Check one request against core's lists. Anything else is refused, so a 'core' graph can never name a pack."""
    model = q.get("model") or "sdxl"
    if model not in G.MODELS: raise HTTPException(400, f"Unknown model. Use one of: {', '.join(G.MODELS)}.")
    sampler = q.get("sampler") or "euler"; scheduler = q.get("scheduler") or "normal"
    if sampler not in G.CORE_SAMPLERS: raise HTTPException(400, "That sampler is not in ComfyUI core, so this page can't run it. It needs a pack.")
    if scheduler not in G.CORE_SCHEDULERS: raise HTTPException(400, "That scheduler is not in ComfyUI core, so this page can't run it. It needs a pack.")
    try:
        cfg = float(q.get("cfg", 4.5 if G.MODELS[model]["kind"] == "flow" else 7.0)); steps = int(q.get("steps", G.STEPS)); seed = int(q.get("seed", G.SEED))
    except (TypeError, ValueError): raise HTTPException(400, "cfg, steps and seed must be numbers.") from None
    if not 0 <= cfg <= 30: raise HTTPException(400, "cfg must be between 0 and 30.")
    if not 1 <= steps <= 60: raise HTTPException(400, "steps must be between 1 and 60.")
    patch = q.get("patch") or ""; patches = []
    if patch:
        if patch not in G.CORE_PATCHES: raise HTTPException(400, "That model patch is not one of the core patches this page can run.")
        if patch == "SkipLayerGuidanceSD3" and G.MODELS[model]["kind"] != "flow": raise HTTPException(400, "Skip Layer Guidance here is written for SD3's blocks. Pick SD 3.5.")
        patches = [[patch, G.CORE_PATCHES[patch]]]
    prompt = q.get("prompt") or G.PROMPT
    if not isinstance(prompt, str) or len(prompt) > 1000: raise HTTPException(400, "The prompt must be text of at most 1000 characters.")
    sfw.check(prompt)
    guider = "PerpNegGuider" if q.get("guider") == "PerpNegGuider" else None
    return {"id": "lab_" + hashlib.sha1(f"{model}{sampler}{scheduler}{cfg}{patch}{guider}{seed}{steps}".encode()).hexdigest()[:8], "model": model, "sampler": sampler, "scheduler": scheduler, "cfg": cfg, "steps": steps, "seed": seed, "patches": patches, "guider": guider, "prompt": prompt}
@router.get("/api/sampling/graph")
def graph(request: Request):
    p = params(dict(request.query_params))
    return {"graph": G.build(p), "params": p, "model": G.MODELS[p["model"]], "core_only": True}

def _srv():
    m = sys.modules.get("__main__")
    if m is not None and hasattr(m, "JOBS") and hasattr(m, "comfy"): return m
    import studio.server as m
    return m
def _missing_model(info, m):
    """Names the file a graph needs when this machine doesn't have it. No fallback to another model."""
    names = (((info.get("CheckpointLoaderSimple") or {}).get("input") or {}).get("required") or {}).get("ckpt_name") or [[]]
    opts = names[0] if isinstance(names[0], list) else (names[1] or {}).get("options", [])
    return None if m["ckpt"] in opts else m["ckpt"]
def _run(q):
    p = params(q); srv = _srv(); m = G.MODELS[p["model"]]
    if not srv.comfy_up(): raise HTTPException(503, "ComfyUI is not reachable, so nothing can run right now.")
    try: info = srv.comfy("/object_info/CheckpointLoaderSimple", timeout=20)
    except Exception: info = {}
    miss = _missing_model(info, m)
    if miss: raise HTTPException(400, f"This needs {miss}, which is not installed on this machine. The studio will not swap in a different model.")
    g = G.build(p)
    try: res = srv.comfy("/prompt", {"prompt": g, "client_id": srv.CLIENT_ID})
    except Exception as e: raise HTTPException(502, f"ComfyUI refused the graph: {type(e).__name__}") from None
    if not isinstance(res, dict) or not res.get("prompt_id"): raise HTTPException(502, "ComfyUI did not return a job.")
    jid = res["prompt_id"]; srv.JOBS[jid] = {"goal": "sampling_lab", "prompt": p["prompt"], "seed": p["seed"], "options": {k: p[k] for k in ("model", "sampler", "scheduler", "cfg", "steps")}, "started": time.time(), "graph_hash": hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest()[:12]}
    return {"job": jid, "params": p}
@router.post("/api/sampling/run")
async def run(request: Request):
    try: q = await request.json()
    except Exception: raise HTTPException(400, "Send JSON.") from None
    if not isinstance(q, dict): raise HTTPException(400, "Send a JSON object.")
    return await run_in_threadpool(_run, q)
