"""Inside a mixture of experts: real per-token routing from Qwen3-Omni-30B-A3B, recorded once and served as static JSON.
scripts/pack_moe_routing.py writes studio/moe/ (index.json, prompts.json.gz with every token's experts per layer, load.json.gz with expert
load per text category). Nothing here loads a model, so the read-only demo shows the same page.
GET /api/moe (model facts, the prompt list, the categories), /api/moe/prompt/{id} (one prompt's routing), /api/moe/load (expert load and top tokens)."""
import gzip, json, threading
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter(prefix="/api/moe")
PAGE = {"tab": "moe", "label": "Experts", "title": ["Inside a mixture of experts", "128 experts. 8 at a time.", "Real routing from a 30-billion-parameter model: for every word piece, each of its 48 layers picks 8 of 128 experts. Recorded once on one GPU; this page only reads the record."], "module": "moe.js", "export": "Moe", "css": "moe.css"}
DATA = Path(__file__).resolve().parent / "moe"
_lock = threading.Lock(); _cache: dict = {}


def _load(name):
    p = DATA / name
    try: sig = p.stat().st_mtime
    except OSError: return None
    with _lock:
        hit = _cache.get(name)
        if hit and hit[0] == sig: return hit[1]
    raw = p.read_bytes(); v = json.loads((gzip.decompress(raw) if name.endswith(".gz") else raw).decode("utf8"))
    with _lock: _cache[name] = (sig, v)
    return v


def _send(request: Request, obj):
    body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
    if "gzip" in request.headers.get("accept-encoding", "") and len(body) > 2048:
        return Response(gzip.compress(body, 6), media_type="application/json", headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
    return Response(body, media_type="application/json")


MISSING = "No routing has been recorded here yet. See scripts/pack_moe_routing.py."


@router.get("")
def moe_index(request: Request):
    i = _load("index.json")
    if i is None: raise HTTPException(404, MISSING)
    return _send(request, i)


@router.get("/prompt/{pid}")
def moe_prompt(pid: str, request: Request):
    p = (_load("prompts.json.gz") or {}).get(pid)
    if p is None: raise HTTPException(404, "No prompt with that id.")
    return _send(request, p)


@router.get("/load")
def moe_load(request: Request):
    l = _load("load.json.gz")
    if l is None: raise HTTPException(404, MISSING)
    return _send(request, l)
