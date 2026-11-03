"""The Music page: one place per music model, each with real renders of one original brief, its real graph, its licence and how far it has been proved.
Facts live in music_models.json, measurements in music_proof.json (scripts/build_music_page.py). The page only ever calls its own routes; the audio is in web/music/.
A graph that needs RyanOnTheInside's pack says so and tells you how to install it. Nothing here installs a pack."""
import json, os, re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths
from studio.graph_template import fill, placeholders

router = APIRouter(prefix="/api/music")
PAGE = {"tab": "music", "label": "Music", "title": ["Music", "One song. Every model on this machine.", "Every render here came from the same original brief. Measured by machine and by Whisper. No person has listened yet."], "module": "music.js", "export": "Music", "css": "music.css"}
ROOT = Path(__file__).resolve().parent; WF = ROOT.parent / "workflows"
#: The graphs this page can queue. Each one says what it needs beyond ComfyUI's own nodes.
PACK = "ComfyUI_RyanOnTheInside"
RUNNABLE = {
    "music3_api.json": {"needs": None}, "music_music3_kit_api.json": {"needs": None}, "music_ace15_turbo_api.json": {"needs": None}, "music_ace15_xl_turbo_api.json": {"needs": None}, "music_ace15_xl_base_api.json": {"needs": None},
    "music_yue2_int8_api.json": {"needs": None}, "music_yue2_bf16_api.json": {"needs": None}, "music_stable_open_api.json": {"needs": None}, "music_yue2_cover_api.json": {"needs": None},
    "music_roti_ace_cover_api.json": {"needs": PACK}, "music_roti_ace_edit_api.json": {"needs": PACK}, "music_roti_ace_extract_api.json": {"needs": PACK}, "music_roti_features_api.json": {"needs": PACK}, "music_roti_visualizer_api.json": {"needs": PACK},
}
LIMITS = {"style": 3000, "caption": 6000, "lyrics": 8000}
_cache: dict = {}


def _read(name):
    p = ROOT / name; mt = p.stat().st_mtime if p.exists() else 0
    if _cache.get(name, (None,))[0] != mt:
        try: _cache[name] = (mt, json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError): _cache[name] = (mt, {})
    return _cache[name][1]


def catalogue(): return _read("music_models.json")
def kit(): return _read("music3_kit.json")
def proof(): return _read("music_proof.json")


def _roots():
    root = paths.models_root()
    return [root] if root and os.path.isdir(root) else []


def _have_file(name, roots):
    """Is a model file really here? A name with a folder is checked as written under _by_repo; a bare name is looked for across the library's model folders. A checksum marker or a card beside it doesn't count."""
    for r in roots:
        if "/" in name:
            if os.path.isfile(os.path.join(r, "_by_repo", name)): return True
            continue
        for sub in ("checkpoints", "diffusion_models", "text_encoders", "vae", "clip", "_by_repo"):
            base = os.path.join(r, sub)
            if any(os.path.isfile(os.path.join(d, name)) for d in (base, *_children(base))): return True
        for fam in _children(os.path.join(r, "_complete_pipelines")):
            if any(os.path.isfile(os.path.join(fam, sub, name)) for sub in ("diffusion_models", "text_encoders", "vae", "checkpoints")): return True
    return False


def _children(d):
    try: return [e.path for e in os.scandir(d) if e.is_dir()]
    except OSError: return []


def state(m, roots=None):
    """What this machine has of a model, read now: its weights, and whether the page has a recorded render."""
    roots = _roots() if roots is None else roots
    need = m.get("need") or []; miss = [n for n in need if not _have_file(n, roots)]
    done = (proof().get("renders") or {}).get(m["id"]) or {}
    if done.get("status") == "success": st = "proven"
    elif miss and roots: st = "missing"
    elif miss: st = "unknown"
    else: st = "unproven"
    return {"state": st, "missing": miss}


def listing():
    c = catalogue(); roots = _roots(); out = []
    for m in c.get("models") or []:
        out.append({**m, **state(m, roots), "render": (proof().get("renders") or {}).get(m["id"])})
    return {"models": out, "not_music": c.get("not_music") or [], "roti": c.get("roti") or {}, "film": c.get("film"), "brief": proof().get("brief") or {}, "extras": proof().get("extras") or {}, "note": proof().get("note") or "", "measured_with": proof().get("measured_with") or {}}


@router.get("/models")
def models(): return listing()


@router.get("/kit")
def kit_get():
    """The Music 3 style kit: sliders, turbo, their sources and what they can and can't do, and what has been rendered with them."""
    k = kit()
    if not k: raise HTTPException(503, "the style kit is not installed")
    return k


def graph_file(name):
    if name not in RUNNABLE or not (WF / name).is_file(): raise HTTPException(404, "no such music graph")
    return json.loads((WF / name).read_text(encoding="utf-8"))


def _clean(v, limit):
    return str(v or "").strip()[:limit]


def build(name, b):
    """Fill a graph from a request. Every value is checked here, and a name the graph needs that the request doesn't give is refused rather than guessed."""
    g = graph_file(name); want = placeholders(g); vals = {}
    for k in want:
        if k in ("seed",): vals[k] = max(0, min(2**31, int(b.get("seed") or 7701)))
        elif k in ("seconds", "duration"): vals[k] = max(8, min(300, int(b.get("seconds") or 60)))
        elif k == "bpm": vals[k] = max(30, min(300, int(b.get("bpm") or 90)))
        elif k == "fps": vals[k] = float(max(1, min(60, int(b.get("fps") or 15))))
        elif k in ("start", "end", "extend", "repaint_start", "repaint_end"): vals[k] = max(-1.0, min(600.0, float(b.get(k) if b.get(k) is not None else (-1.0 if k.startswith("repaint") else 0.0))))
        elif k == "key":
            kv = str(b.get("key") or "C major"); vals[k] = kv if re.fullmatch(r"[A-G][#b]? (major|minor)", kv) else "C major"
        elif k == "track":
            tv = str(b.get("track") or "vocals"); vals[k] = tv if tv in ("vocals", "drums", "bass", "guitar", "keyboard", "strings", "percussion", "synth", "fx", "brass", "woodwinds", "backing_vocals") else "vocals"
        elif k == "method": vals[k] = "line" if b.get("method") == "line" else "bar"
        elif k == "source":
            sv = os.path.basename(str(b.get("source") or ""))
            if not sv: raise HTTPException(400, "this graph needs a source audio file: upload one first")
            vals[k] = sv
        elif k == "slider":      # the kit: one ntc-ai slider by id, or none (strength 0 on a real file leaves the text encoder untouched)
            sl = {x["id"]: x for x in kit().get("sliders") or []}; sv = str(b.get("slider") or "none")
            if sv != "none" and sv not in sl: raise HTTPException(400, "no such style slider")
            vals[k] = sl[sv]["file"] if sv != "none" else next(iter(sl.values()), {}).get("file", "")
            if not vals[k]: raise HTTPException(503, "the style kit is not installed")
        elif k == "slider_strength":
            lim = kit().get("strength") or {"min": 0.0, "max": 1.5, "default": 1.0}
            try: sv = float(b.get("slider_strength") if b.get("slider_strength") is not None else lim["default"])
            except (TypeError, ValueError): raise HTTPException(400, "slider strength must be a number") from None
            vals[k] = 0.0 if str(b.get("slider") or "none") == "none" else max(lim["min"], min(lim["max"], sv))
        elif k == "turbo": vals[k] = b.get("turbo") is True
        elif k in LIMITS: vals[k] = _clean(b.get(k) if b.get(k) else (b.get("style") if k == "caption" else ""), LIMITS[k])
        else: raise HTTPException(400, f"this graph asks for {k}, which this page doesn't know")
    if "style" in want and not vals["style"] or "caption" in want and not vals["caption"]: raise HTTPException(400, "write a style first")
    from studio import sfw
    sfw.check(*(vals[k] for k in LIMITS if k in vals))
    return fill(g, vals)


INSTALL = "This graph needs RyanOnTheInside's node pack, and this ComfyUI doesn't have it. The Music page shows how to install it. Try it in Pack Lab or a separate ComfyUI first: on load it rewrites a folder inside ComfyUI."


def _has_pack_nodes():
    """Ask ComfyUI itself. Any trouble reaching it reads as not having the nodes, so nothing is queued blind."""
    from studio import apps as A
    try: return "ACEStep15NativeCoverGuider" in A.object_info() and "AudioFeatureExtractor" in A.object_info()
    except Exception: return False


@router.post("/run")
def run(b: dict = None):
    """Queue one music graph on the main ComfyUI. The answer has the same job id /api/jobs/{id} reads."""
    b = b or {}; name = str(b.get("graph") or ""); g = build(name, b)
    if RUNNABLE[name]["needs"] == PACK and not _has_pack_nodes(): raise HTTPException(409, INSTALL)
    from studio import apps as A, backends as B, server as S
    try: g, _ = A.resolve(g, A.object_info())       # a model kept in a subfolder here is found under the name this ComfyUI uses for it
    except Exception: pass
    meta = {"goal": "music-page", "prompt": str(b.get("style") or b.get("caption") or "")[:200], "seed": b.get("seed"), "graph": name}
    if B.use_sdk():
        try: jid = B.submit(g, meta=meta)
        except Exception as e: raise HTTPException(400, f"Comfy SDK: {type(e).__name__}") from None
        return {"job": jid}
    if not S.comfy_up(): raise HTTPException(503, "ComfyUI is not reachable, so nothing was queued")
    import time, urllib.error
    try: res = S.comfy("/prompt", {"prompt": g, "client_id": S.CLIENT_ID})
    except urllib.error.HTTPError as e: raise S._rejected(e) from None
    except (OSError, ValueError): raise HTTPException(503, "ComfyUI didn't take the job") from None
    if not isinstance(res, dict) or not res.get("prompt_id"): raise HTTPException(502, "ComfyUI did not return a job")
    jid = res["prompt_id"]; S.JOBS[jid] = {**meta, "started": time.time()}
    return {"job": jid}
