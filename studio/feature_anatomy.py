"""Model Anatomy page: what each model file on this machine is made of, read from its header with no GPU and no weights loaded.
The answers come from a cache that scripts/build_model_anatomy.py writes to studio/anatomy/ (index.json, and models.json.gz with one record per file), so the read-only demo shows the same numbers. Nothing here opens a model file while serving.
GET /api/anatomy (every file, one row each) and /api/anatomy/model/{id} (one file: dtype mix, layer kinds, groups, the block tree, LoRA rank and targets, and what the header can't tell)."""
import gzip, json, threading
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter(prefix="/api/anatomy")
PAGE = {"tab": "anatomy", "label": "Anatomy", "title": ["Model Anatomy", "Every network, opened up.", "What each model file is made of, read from its header: parameters, blocks, number formats, attention and MLP, LoRA rank. No GPU, no weights loaded."], "module": "anatomy.js", "export": "Anatomy", "css": "anatomy.css"}
DATA = Path(__file__).resolve().parent / "anatomy"
_lock = threading.Lock(); _cache: dict = {}


def _load(name, read):
    p = DATA / name
    try: sig = p.stat().st_mtime
    except OSError: return None
    with _lock:
        hit = _cache.get(name)
        if hit and hit[0] == sig: return hit[1]
    v = read(p)
    with _lock: _cache[name] = (sig, v)
    return v


def index():
    return _load("index.json", lambda p: json.loads(p.read_text(encoding="utf8")))


def models():
    return _load("models.json.gz", lambda p: json.loads(gzip.decompress(p.read_bytes()).decode("utf8")))


def _gz(request: Request, obj):
    """The index is a few hundred kilobytes of JSON, so it goes compressed when the browser takes that."""
    body = json.dumps(obj, separators=(",", ":")).encode()
    if "gzip" in request.headers.get("accept-encoding", "") and len(body) > 2048:
        return Response(gzip.compress(body, 6), media_type="application/json", headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
    return Response(body, media_type="application/json")


@router.get("")
def anatomy_index(request: Request):
    i = index()
    if i is None: raise HTTPException(404, "No anatomy has been built on this machine yet. Run scripts/build_model_anatomy.py --models <your models folder>.")
    return _gz(request, i)


@router.get("/model/{mid}")
def anatomy_model(mid: str, request: Request):
    m = models() or {}
    if mid not in m: raise HTTPException(404, "No file with that id in the anatomy.")
    return _gz(request, m[mid])
