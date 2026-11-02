"""The Game Builder page: a few prompts in, a game you can play in the page and download. The work is in studio/gamebuilder; this is its routes. Route logic is in plain functions, so tests run them with no server, ComfyUI, Godot or GPU."""
import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from studio.gamebuilder import assemble as AS
from studio.gamebuilder import models as M
from studio.gamebuilder import pipeline as P
from studio.gamebuilder import spec as SP

router = APIRouter(prefix="/api/gamebuilder")
PAGE = {"tab": "gamebuilder", "label": "Game Builder", "title": ["Game Builder", "A few prompts in. A game you can play.", "Prompts pick a genre kit written by hand and fill a checked spec. Models make what you see and hear. Godot checks it, a bot plays it to the end, and you get a build."], "module": "gamebuilder.js", "export": "GameBuilder", "css": "gamebuilder.css"}
HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "web" / "games" / "samples.json"
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".wasm": "application/wasm", ".pck": "application/octet-stream", ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon", ".json": "application/json"}
SAFE_WEB = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
#: What runs at the same moment, and the most the card must hold for it: one at a time, measured on our card where we measured it.
NEEDS = (("Pictures and textures", "krea2", "Krea 2 Turbo, or FLUX.2 Klein 4B"), ("Meshes", "trellis2_main", "TRELLIS.2, then TripoSR, Hunyuan3D or Shap-E"), ("Rig", "skintokens", "SkinTokens"), ("Motion", "kimodo", "Kimodo"), ("Retarget", "retarget", "Blender"), ("Picture check", "picturecheck", "InsightFace and NudeNet"), ("Words to mesh", "shap_e", "Shap-E"))


def readiness(need=None, comfy=None) -> dict:
    """Each stage against this machine, from a file check on every call."""
    from studio.worldkit import capabilities as C
    need = need or C.need
    rows = []
    for label, key, model in NEEDS:
        n = need(key)
        rows.append({"label": label, "model": model, "ready": n["state"] == "ready", "why": "" if n["state"] == "ready" else n["message"], "peak_gib": M.PEAK.get(key)})
    t = AS.templates_state()
    godot = AS.godot_path()
    return {"godot": bool(godot), "godot_version": AS.VERSION, "templates": t["ready"], "templates_web": t["web"], "templates_linux": t["linux"], "comfy": (comfy or C.comfy_up)(), "models": rows,
            "peak_gib": max(M.PEAK.values()), "note": "Every model that's missing or fails is replaced by a stand-in drawn by code, and marked. A game with no GPU at all still runs: it just looks like a sketch."}


def kits() -> list:
    return [{"id": k, "label": v["label"], "pitch": v["pitch"]} for k, v in SP.KITS.items()]


def samples() -> list:
    """Games made here, shown as a video in the repo. One is playable in the page too when its web build is on this machine."""
    try:
        rows = json.loads(SAMPLES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    for r in rows:
        d = P.game_dir(str(r.get("game_id") or ""))
        r["playable"] = bool(d and (d / "build" / "web" / "index.html").is_file())
        r["src"] = f"/api/gamebuilder/games/{r['game_id']}/web/index.html" if r["playable"] else ""
    return rows


def check_body(b) -> tuple[list, dict]:
    if not isinstance(b, dict):
        raise HTTPException(400, "send a JSON object")
    prompts = SP.clean(b.get("prompts"))
    if not prompts:
        raise HTTPException(400, "Say what the game is: one prompt is enough, a few is better.")
    bad = SP.text_problems(prompts)
    if bad:
        raise HTTPException(400, bad)
    o = {}
    if b.get("kit") not in (None, "", "auto"):
        if b["kit"] not in SP.KITS:
            raise HTTPException(400, f"kit is one of {', '.join(SP.KITS)}")
        o["kit"] = b["kit"]
    for key, allowed in (("size", SP.SIZES), ("difficulty", SP.DIFFICULTIES)):
        v = b.get(key) or ("small" if key == "size" else "normal")
        if v not in allowed:
            raise HTTPException(400, f"{key} is one of {', '.join(allowed)}")
        o[key] = v
    seed = b.get("seed")
    if seed not in (None, ""):
        try:
            o["seed"] = int(seed)
        except (TypeError, ValueError):
            raise HTTPException(400, "seed is a whole number") from None
    return prompts, o


def plan(b, *, ask=None) -> dict:
    """The spec these prompts would give, without building anything. Asks Qwen only if it's already running."""
    prompts, o = check_body(b)
    spec, note = SP.from_model(prompts, ask or M.RealModels().ask_qwen, seed=o.get("seed"), kit=o.get("kit"), size=o.get("size", "small"), difficulty=o.get("difficulty", "normal"))
    checked, bad = SP.validate(spec)
    if bad:
        raise HTTPException(400, "; ".join(bad))
    return {"spec": checked, "note": note, "source": checked.get("source")}


def start(b, *, starter=None) -> dict:
    prompts, o = check_body(b)
    if any(g.get("running") for g in P.list_games()):
        raise HTTPException(409, "A game is being built. The card is shared, so they go one at a time.")
    return {"id": (starter or P.start)(prompts, o)}


@router.get("/status")
def status():
    return {"kits": kits(), "readiness": readiness(), "samples": samples(), "games": P.list_games()}


@router.post("/plan")
def plan_post(b: dict = None):
    return plan(b)


@router.post("/games")
def games_post(b: dict = None):
    return start(b)


@router.get("/games")
def games_get():
    return {"games": P.list_games()}


def _state(gid: str) -> dict:
    s = P.read_state(gid)
    if s is None:
        raise HTTPException(404, "no such game")
    return s


@router.get("/games/{gid}")
def game_get(gid: str):
    s = _state(gid)
    s["running"] = P.is_running(gid)
    if s.get("state") == "building" and not s["running"]:
        s["interrupted"] = True
    s["has_video"] = (P.game_dir(gid) / "playtest" / "play.mp4").is_file()
    return s


@router.post("/games/{gid}/cancel")
def game_cancel(gid: str):
    _state(gid)
    return {"cancelled": P.cancel(gid)}


@router.get("/games/{gid}/web/{name}")
def game_web(gid: str, name: str):
    """One file of a game's web build. The name is matched against a strict pattern, never joined raw."""
    _state(gid)
    if not SAFE_WEB.match(name) or name.startswith("."):
        raise HTTPException(404, "no such file")
    p = P.game_dir(gid) / "build" / "web" / name
    if not p.is_file():
        raise HTTPException(404, "no such file")
    return FileResponse(p, media_type=MIME.get(p.suffix.lower(), "application/octet-stream"))


@router.get("/games/{gid}/download/{kind}")
def game_download(gid: str, kind: str):
    s = _state(gid)
    if kind not in ("project", "linux", "web"):
        raise HTTPException(404, "no such download")
    p = P.game_dir(gid) / "zips" / f"{kind}.zip"
    if not p.is_file():
        raise HTTPException(404, "that download wasn't made for this game")
    return FileResponse(p, media_type="application/zip", filename=f"{P._slug(s.get('title') or gid)}-{kind}.zip")


@router.get("/games/{gid}/video")
def game_video(gid: str):
    _state(gid)
    p = P.game_dir(gid) / "playtest" / "play.mp4"
    if not p.is_file():
        raise HTTPException(404, "no play-test video was recorded for this game")
    return FileResponse(p, media_type="video/mp4")


@router.post("/templates")
def templates_post(b: dict = None):
    """Fetch Godot's export templates from its official release, checked against the published SHA-512. Over a gigabyte, so only when asked."""
    if not isinstance(b, dict) or b.get("confirm") is not True:
        raise HTTPException(400, "send {\"confirm\": true}: this downloads over a gigabyte from Godot's official release")
    try:
        return AS.install_templates()
    except (AS.GodotError, OSError) as exc:
        raise HTTPException(502, str(exc)[:500]) from None
