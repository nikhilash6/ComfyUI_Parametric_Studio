"""Which word painted what: a heatmap per prompt word, from SD 1.5 and SDXL cross-attention, recorded by our own PSN nodes while the picture is made.
Proof renders live in sampling_lab/attention.json with their pictures and maps in web/sampling_lab/attn (made by scripts/attention_maps_renders.py).
GET /api/words lists them. GET /api/words/graph gives the exact graph. POST /api/words/run queues one on this studio's ComfyUI, which needs this
pack's PSN_AttentionRecord node; GET /api/words/result/{job} reads the maps back from ComfyUI's history."""
import json, hashlib, sys, time, urllib.parse
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from studio import sfw, words_graph as G

router = APIRouter(prefix="/api/words")
PAGE = {"tab": "words", "label": "Which Word", "title": ["Which word painted what", "Every prompt word. Where it looked.", "Heatmaps read out of the model's cross-attention while it drew: one per word, from real SD 1.5 and SDXL renders on this machine."], "module": "words.js", "export": "WhichWord", "css": "words.css"}
DATA = Path(__file__).resolve().parent / "sampling_lab" / "attention.json"
MAX_PROMPT = 300; _cache: dict = {}


def data():
    try: sig = DATA.stat().st_mtime
    except OSError: return {"renders": []}
    hit = _cache.get("d")
    if hit and hit[0] == sig: return hit[1]
    d = json.loads(DATA.read_text(encoding="utf-8")); _cache["d"] = (sig, d); return d


@router.get("")
def renders(): return data()


def params(q):
    """One request checked: an SD 1.5 or SDXL model, a short prompt that passes the SFW check, and numbers in range."""
    model = q.get("model") or "sd15"
    if model not in G.MODELS: raise HTTPException(400, f"Attention maps need a UNet with cross-attention. Use one of: {', '.join(G.MODELS)}.")
    prompt = q.get("prompt") or "a red hat on a wooden table"
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT: raise HTTPException(400, f"The prompt must be text of 1 to {MAX_PROMPT} characters.")
    sfw.check(prompt)
    try: seed = int(q.get("seed", G.SEED)); steps = int(q.get("steps", G.STEPS)); cfg = float(q.get("cfg", G.CFG))
    except (TypeError, ValueError): raise HTTPException(400, "seed, steps and cfg must be numbers.") from None
    if not 1 <= steps <= 50: raise HTTPException(400, "steps must be between 1 and 50.")
    if not 1 <= cfg <= 20: raise HTTPException(400, "cfg must be between 1 and 20.")
    if not 0 <= seed < 2**53: raise HTTPException(400, "seed must be a whole number from 0.")
    return {"id": "words_" + hashlib.sha1(f"{model}{prompt}{seed}{steps}{cfg}".encode()).hexdigest()[:8], "model": model, "prompt": prompt.strip(), "seed": seed, "steps": steps, "cfg": cfg}


@router.get("/graph")
def graph(request: Request):
    p = params(dict(request.query_params))
    return {"graph": G.build(p), "params": p, "model": G.MODELS[p["model"]], "nodes": ["PSN_AttentionRecord", "PSN_AttentionMaps"]}


def _srv():
    m = sys.modules.get("__main__")
    if m is not None and hasattr(m, "JOBS") and hasattr(m, "comfy"): return m
    import studio.server as m
    return m


def _run(q):
    p = params(q); srv = _srv(); m = G.MODELS[p["model"]]
    if not srv.comfy_up(): raise HTTPException(503, "ComfyUI is not reachable, so nothing can run right now.")
    try: info = srv.comfy("/object_info/PSN_AttentionRecord", timeout=20)
    except Exception: info = {}
    if "PSN_AttentionRecord" not in (info or {}): raise HTTPException(400, "This ComfyUI does not have the PSN attention nodes. Update the Parametric Studio pack in its custom_nodes and restart it.")
    try: ck = srv.comfy("/object_info/CheckpointLoaderSimple", timeout=20)
    except Exception: ck = {}
    names = ((((ck.get("CheckpointLoaderSimple") or {}).get("input") or {}).get("required") or {}).get("ckpt_name") or [[]])[0]
    if isinstance(names, list) and m["ckpt"] not in names: raise HTTPException(400, f"This needs {m['ckpt']}, which is not installed on this machine. The studio will not swap in a different model.")
    g = G.build(p)
    try: res = srv.comfy("/prompt", {"prompt": g, "client_id": srv.CLIENT_ID})
    except Exception as e: raise HTTPException(502, f"ComfyUI refused the graph: {type(e).__name__}") from None
    if not isinstance(res, dict) or not res.get("prompt_id"): raise HTTPException(502, "ComfyUI did not return a job.")
    jid = res["prompt_id"]; srv.JOBS[jid] = {"goal": "words", "prompt": p["prompt"], "seed": p["seed"], "options": {k: p[k] for k in ("model", "steps", "cfg")}, "started": time.time()}
    return {"job": jid, "params": p}


@router.post("/run")
async def run(request: Request):
    try: q = await request.json()
    except Exception: raise HTTPException(400, "Send JSON.") from None
    if not isinstance(q, dict): raise HTTPException(400, "Send a JSON object.")
    return await run_in_threadpool(_run, q)


def read_result(h):
    """The maps and the picture of a finished job, from its ComfyUI history entry. None while it has not finished."""
    st = (h or {}).get("status") or {}
    if not h or not (st.get("completed") or st.get("status_str") == "success"): return None
    out = h.get("outputs") or {}; maps = ((out.get(G.MAPS) or {}).get("psn_attention") or [None])[0]
    imgs = (out.get(G.PICTURE) or {}).get("images") or []
    if not maps or not imgs: raise HTTPException(502, "The job finished without attention maps. Was it queued from this page?")
    f = imgs[0]; url = "/api/view?" + urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
    return {"status": "done", "image": url, "maps": maps}


@router.get("/result/{jid}")
def result(jid: str):
    if not jid.replace("-", "").isalnum() or len(jid) > 64: raise HTTPException(400, "Not a job id.")
    try: h = _srv().comfy(f"/history/{urllib.parse.quote(jid)}").get(jid)
    except Exception: raise HTTPException(503, "ComfyUI is not reachable.") from None
    st = (h or {}).get("status") or {}
    if st.get("status_str") == "error":
        msg = next((i.get("exception_message", "") for k, i in st.get("messages", []) if k == "execution_error"), "")
        return {"status": "error", "error": msg.strip()[:400]}
    return read_result(h) or {"status": "running"}
