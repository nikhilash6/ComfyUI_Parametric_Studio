"""Camera Paths: draw the camera's move in 3D (or drag a point on a globe around the subject), move an object along a line you draw, and check whether a take really did the move.
- A drawn camera path renders with Wan 2.2 Fun Camera 14B through PSN_CameraPathEmbedding (psn_nodes/camera_path.py), which turns the keyframes into the same camera conditioning as ComfyUI's presets.
- A drawn object path renders with LTX-2.5 and Lightricks' LTX-2.3 Motion-Track-Control IC-LoRA (a 2.3 LoRA on 2.5; camera_proof.json says whether that held up here).
- The checker (studio/camera_verify.py) runs on the CPU and says MATCH, MISMATCH or INCONCLUSIVE. INCONCLUSIVE is never counted as a pass, and only a MATCH can be picked as the best take.
Every rendered result carries the AI-generated mark. Renders go to this server's ComfyUI (COMFYUI_URL), one at a time from this page."""
import json, math, os, re, shutil, subprocess, threading, time, urllib.parse, urllib.request, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from psn import paths
from studio import camera_verify as V, sfw

ROOT = Path(__file__).resolve().parent; REPO = ROOT.parent; PROOF = ROOT / "camera_proof.json"
router = APIRouter(prefix="/api/campath"); JOBS: dict = {}; _LOCK = threading.Lock()
PAGE = {"tab": "campath", "label": "Camera Paths", "title": ["Camera Paths", "Draw the move. Check the take.", "Draw a camera path around your subject, or a line for something to follow, and render it. Then check any clip against the move you asked for: match, mismatch, or not enough to tell."], "module": "camerapath.js", "export": "CameraPaths", "css": "camerapath.css"}
NEG_WAN = "blurry, low quality, static, still image, distorted, warped, watermark, text, letters, logo"
NEG_LTX = "worst quality, inconsistent motion, blurry, jittery, distorted, watermark, text, letters, logo"
WAN = {"graph": "campath_wan_api.json", "model": "Wan 2.2 Fun Camera 14B (fp8)", "licence": "Apache-2.0", "size": (832, 480), "frames": 81, "fps": 16, "peak_gb": 46.0}
LTX = {"graph": "campath_ltx_track_api.json", "model": "LTX-2.5 22B distilled int8 + LTX-2.3 Motion-Track-Control IC-LoRA", "licence": "LTX-2 Community License (free under $10M yearly revenue; label generated content)", "size": (960, 576), "frames": 121, "fps": 24, "peak_gb": 44.0}   # the Motion-Track LoRA works on a half-size grid (latent_downscale_factor 2), so both sides are multiples of 64
SUBJECT_DEPTH = 4.0           # the look-at point of a globe path, in the node's units
MOVE_WORDS = {k: v.replace("_", " ") for k, v in {m: m for m in V.MOVES}.items()}
IMAGE_EXT, VIDEO_EXT = (".png", ".jpg", ".jpeg", ".webp"), (".mp4", ".mov", ".webm", ".mkv")
#: Ready-made paths, in the node's units (x right, y down, z forward; the subject sits at z = 4). Each is a few keys; the page can drag any of them.
def _arc(deg_from, deg_to, elev=0.0, n=5, r=SUBJECT_DEPTH):
    """Keys on a circle around the subject: 0 degrees is the starting view, positive goes round to the camera's right."""
    out = []
    for i in range(n):
        a = math.radians(deg_from + (deg_to - deg_from) * i / (n - 1)); e = math.radians(elev * i / (n - 1))
        out.append({"t": i / (n - 1), "pos": [round(r * math.sin(a) * math.cos(e), 4), round(-r * math.sin(e), 4), round(SUBJECT_DEPTH - r * math.cos(a) * math.cos(e), 4)]})
    return out
PRESETS = {
    "orbit_right": {"label": "Orbit right", "path": {"keys": _arc(0, 40), "look_at": [0, 0, SUBJECT_DEPTH]}},
    "orbit_left": {"label": "Orbit left", "path": {"keys": _arc(0, -40), "look_at": [0, 0, SUBJECT_DEPTH]}},
    "crane_up": {"label": "Crane up", "path": {"keys": [{"t": 0, "pos": [0, 0, 0]}, {"t": 1, "pos": [0, -1.4, 0.3]}], "look_at": [0, 0, SUBJECT_DEPTH]}},
    "dolly_in": {"label": "Dolly in", "path": {"keys": [{"t": 0, "pos": [0, 0, 0]}, {"t": 1, "pos": [0, 0, 1.6]}], "look_at": None}},
    "dolly_out": {"label": "Dolly out", "path": {"keys": [{"t": 0, "pos": [0, 0, 0]}, {"t": 1, "pos": [0, 0, -1.6]}], "look_at": None}},
    "pan_left": {"label": "Pan left", "path": {"keys": [{"t": 0, "pos": [0, 0, 0], "yaw": 0}, {"t": 1, "pos": [0, 0, 0], "yaw": -25}], "look_at": None}},
    "rise_and_circle": {"label": "Rise and circle", "path": {"keys": _arc(0, 60, elev=20), "look_at": [0, 0, SUBJECT_DEPTH]}},
}


# ---------- reading a drawn path
def path_plan(path, frames=WAN["frames"]):
    """A drawn path -> what it will do: sampled positions for the page, predicted screen motion of the subject and of the far background, and the move the checker will hold the take to."""
    from psn_nodes import camera_path as C
    try: mats = C.poses(json.dumps(path) if not isinstance(path, str) else path, frames)
    except ValueError as e: raise HTTPException(400, str(e)) from None
    near, far = C.screen_motion(mats, SUBJECT_DEPTH), C.screen_motion(mats, SUBJECT_DEPTH * 4); travel = [float(v) for v in mats[-1][:3, 3]]
    return {"positions": [[round(float(v), 3) for v in m[:3, 3]] for m in mats[:: max(1, frames // 40)]], "subject": near, "background": far, "travel": [round(v, 3) for v in travel], "expect": expected_move(near, far, travel)}


def expected_move(near, far, travel=(0.0, 0.0, 0.0)):
    """The move name a drawn path should produce on screen, from where the subject and the far background end up and which way the camera travelled."""
    if near.get("behind") or far.get("behind"): return "dolly_zoom"          # never checkable: the camera passed the subject
    held = max(abs(near["dx"]), abs(near["dy"])) < 0.08
    if held and abs(travel[1]) > abs(travel[0]) and abs(travel[1]) >= 0.3: return "crane_up" if travel[1] < 0 else "crane_down"     # y is down
    if held and abs(far["dx"]) >= 0.1 and abs(far["dx"]) >= abs(far["dy"]): return "orbit_right" if far["dx"] > 0 else "orbit_left"
    return V.expected_from_path(near)


# ---------- ComfyUI
class Comfy:
    """The few calls this page needs from a ComfyUI server."""
    def __init__(self, url=None): self.url = (url or os.environ.get("CAMPATH_COMFYUI_URL") or os.environ.get("COMFYUI_URL") or "http://127.0.0.1:8200").rstrip("/")

    def _req(self, path, body=None, timeout=60):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.url + path, data=data, headers={"Content-Type": "application/json"} if data else {})
        with urllib.request.urlopen(r, timeout=timeout) as f: return json.loads(f.read() or b"{}")

    def upload(self, path):
        """Put a local file in ComfyUI's input folder. -> the name to use in LoadImage."""
        p = Path(path); bnd = uuid.uuid4().hex; name = f"campath_{uuid.uuid4().hex[:8]}{p.suffix.lower()}"
        body = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + p.read_bytes() + f"\r\n--{bnd}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{bnd}--\r\n".encode()
        r = urllib.request.Request(self.url + "/upload/image", data=body, headers={"Content-Type": f"multipart/form-data; boundary={bnd}"})
        with urllib.request.urlopen(r, timeout=120) as f: d = json.loads(f.read())
        return (d.get("subfolder") + "/" if d.get("subfolder") else "") + d["name"]

    def run(self, graph, timeout=3600):
        """Queue, wait, and return the history entry. Raises with ComfyUI's own words on a failure."""
        try: pid = self._req("/prompt", {"prompt": graph, "client_id": "campath"})["prompt_id"]
        except urllib.error.HTTPError as e: raise RuntimeError("ComfyUI refused the graph: " + e.read().decode("utf8", "replace")[:600]) from None
        t0 = time.time()
        while time.time() - t0 < timeout:
            h = self._req(f"/history/{pid}").get(pid)
            if h and h.get("status", {}).get("completed"): return h
            if h and h.get("status", {}).get("status_str") == "error":
                msg = [m for m in h["status"].get("messages", []) if m[0] == "execution_error"]
                raise RuntimeError("ComfyUI stopped: " + (msg[0][1].get("exception_message", "")[:500] if msg else "error"))
            time.sleep(2)
        raise RuntimeError("timed out waiting for ComfyUI")

    def fetch(self, item, dest):
        q = urllib.parse.urlencode({"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": item.get("type", "output")})
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"{self.url}/view?{q}", timeout=300) as f, open(dest, "wb") as o: shutil.copyfileobj(f, o)
        return Path(dest)

    def free(self):
        try: self._req("/free", {"unload_models": True, "free_memory": True})
        except Exception: pass

    def cancel(self):
        try: self._req("/interrupt", {})
        except Exception: pass


def outputs(hist, node):
    """The files one node saved, from a history entry."""
    o = hist.get("outputs", {}).get(node, {})
    return [x for k in ("images", "videos", "gifs", "audio") for x in o.get(k, [])]


def graph(name, values, prefix=None):
    from studio.graph_template import fill
    g = fill(json.loads((REPO / "workflows" / name).read_text()), values)
    if prefix:
        for nid, n in g.items():
            if n["class_type"] == "SaveVideo": n["inputs"]["filename_prefix"] = prefix + ("_guide" if nid == "trks" else "")
    return g


def wan_values(image, path, prompt, seed):
    w, h = WAN["size"]
    return {"image": image, "path": json.dumps(path), "prompt": prompt, "negative": NEG_WAN, "width": w, "height": h, "frames": WAN["frames"], "seed": int(seed)}


def tracks_json(tracks, frames=LTX["frames"], size=LTX["size"]):
    """Drawn lines (each a list of [x, y] in 0..1 of the frame) -> LTXVDrawTracks' text: one point per frame per line, in pixels, evenly spaced along the line."""
    w, h = size; out = []
    if not isinstance(tracks, list) or not tracks: raise HTTPException(400, "draw at least one line")
    for t in tracks[:8]:
        if not isinstance(t, list) or len(t) < 2: raise HTTPException(400, "each line needs at least two points")
        pts = []
        for p in t[:400]:
            if not (isinstance(p, (list, tuple)) and len(p) == 2 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in p)): raise HTTPException(400, "a point is [x, y] between 0 and 1")
            pts.append((min(1.0, max(0.0, float(p[0]))) * (w - 1), min(1.0, max(0.0, float(p[1]))) * (h - 1)))
        seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; total = sum(seg)
        if total < 4: raise HTTPException(400, "a line is too short to follow")
        res, acc, j = [], 0.0, 0
        for f in range(frames):
            want = total * f / (frames - 1)
            while j < len(seg) - 1 and acc + seg[j] < want: acc += seg[j]; j += 1
            u = 0.0 if seg[j] == 0 else min(1.0, (want - acc) / seg[j])
            res.append({"x": round(pts[j][0] + (pts[j + 1][0] - pts[j][0]) * u, 2), "y": round(pts[j][1] + (pts[j + 1][1] - pts[j][1]) * u, 2)})
        out.append(res)
    return json.dumps(out)


def ltx_values(image, tracks, prompt, seed, strength=1.0):
    w, h = LTX["size"]
    return {"image": image, "tracks": tracks if isinstance(tracks, str) else tracks_json(tracks), "prompt": prompt, "negative": NEG_LTX, "width": w, "height": h, "frames": LTX["frames"], "seed": int(seed), "strength": float(strength)}


# ---------- following a drawn object path
def centroid_track(clip, start_xy, max_frames=400, box=None, search=None):
    """Follow what sits at start_xy (0..1) on frame 0 through the clip: a template cut around it is matched (normalised cross-correlation) near where it was last seen,
    and re-cut from each confident match so a turning object stays followed. -> [(x, y) in 0..1, or None once it is lost] per frame."""
    import cv2, numpy as np
    cap = cv2.VideoCapture(str(clip)); ok, f = cap.read(); out = []
    if not ok: return out
    h, w = f.shape[:2]; half = box or max(12, int(0.045 * min(w, h))); reach = search or half * 3
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); cx, cy = int(start_xy[0] * w), int(start_xy[1] * h)
    cut = lambda img, x, y: img[max(0, y - half):y + half, max(0, x - half):x + half]
    tpl = cut(g, cx, cy); out.append((cx / w, cy / h))
    while len(out) < max_frames:
        ok, f = cap.read()
        if not ok: break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); x0, y0 = max(0, cx - reach), max(0, cy - reach); win = g[y0:cy + reach, x0:cx + reach]
        if win.shape[0] <= tpl.shape[0] or win.shape[1] <= tpl.shape[1]: out.append(None); break
        r = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED); _, score, _, loc = cv2.minMaxLoc(r)
        if score < 0.3: out.append(None); break
        cx, cy = x0 + loc[0] + tpl.shape[1] // 2, y0 + loc[1] + tpl.shape[0] // 2; out.append((cx / w, cy / h))
        if score > 0.6: tpl = cut(g, cx, cy)
    cap.release(); return out


def follow_error(track, drawn, size):
    """Mean and worst distance (pixels, and as a share of the frame diagonal) between the followed object and where the drawn line said it should be on each frame."""
    w, h = size; diag = math.hypot(w, h); d = []
    for i, p in enumerate(track):
        if p is None or i >= len(drawn): continue
        d.append(math.hypot(p[0] * w - drawn[i]["x"], p[1] * h - drawn[i]["y"]))
    if not d: return None
    return {"frames": len(d), "mean_px": round(sum(d) / len(d), 1), "max_px": round(max(d), 1), "mean_of_diagonal": round(sum(d) / len(d) / diag, 4), "lost_at": next((i for i, p in enumerate(track) if p is None), None)}


# ---------- the page's runs
def _input_file(name, exts):
    """A file the person added through the studio (ComfyUI's input folder) or made here (the output folder). A name from the browser is never joined raw."""
    if not isinstance(name, str) or not name.strip(): raise HTTPException(400, "pick a file")
    clean = os.path.normpath(name.strip()).lstrip("/")
    if clean.startswith("..") or Path(clean).suffix.lower() not in exts: raise HTTPException(400, f"{Path(name).name} is not a usable file")
    for base in (Path(paths.comfy_input(True)), Path(paths.output_dir(True))):
        p = (base / clean).resolve()
        if str(p).startswith(str(base.resolve()) + os.sep) and p.is_file(): return p
    raise HTTPException(404, f"{Path(clean).name} is not in the studio's input or output folder")


def _out_dir():
    d = Path(paths.output_dir(True)) / "campath"; d.mkdir(parents=True, exist_ok=True); return d


def _mark(src, dest):
    """The visible AI-generated mark, burned in with ffmpeg (the same words as the rest of the studio)."""
    from studio import likeness
    try: likeness.mark(src, dest); return dest
    except Exception:
        shutil.copy2(src, dest); return dest


def execute(kind, b, comfy=None):
    """One render from the page. -> result record (file, verdict for a camera path, follow error for an object path)."""
    c = comfy or Comfy(); seed = int(b.get("seed") or 7); prompt = " ".join(str(b.get("prompt") or "").split())[:800]
    if not prompt: raise HTTPException(400, "describe the scene")
    sfw.check(prompt); img = _input_file(b.get("image"), IMAGE_EXT); name = c.upload(img); t0 = time.time(); stamp = time.strftime("%Y%m%d_%H%M%S")
    if kind == "wan_path":
        plan = path_plan(b.get("path")); h = c.run(graph(WAN["graph"], wan_values(name, b["path"], prompt, seed), f"campath/wan_{stamp}"))
        raw = c.fetch(outputs(h, "save")[0], _out_dir() / f"wan_{stamp}_raw.mp4"); chk = V.verify(raw, plan["expect"])      # checked before the mark: a still corner tag would read as part of the scene
        out = _mark(raw, _out_dir() / f"wan_{stamp}.mp4"); raw.unlink(missing_ok=True)
        return {"kind": kind, "file": str(out.relative_to(Path(paths.output_dir(True)))), "seconds": round(time.time() - t0, 1), "expect": plan["expect"], "verdict": chk["verdict"], "why": chk["why"], "said": chk["said"], "model": WAN["model"], "licence": WAN["licence"], "seed": seed}
    if kind == "ltx_track":
        tj = tracks_json(b.get("tracks")); h = c.run(graph(LTX["graph"], ltx_values(name, tj, prompt, seed, b.get("strength") or 1.0), f"campath/ltx_{stamp}"))
        raw = c.fetch(outputs(h, "save")[0], _out_dir() / f"ltx_{stamp}_raw.mp4")
        drawn = json.loads(tj)[0]; w, hh = LTX["size"]; err = follow_error(centroid_track(raw, (drawn[0]["x"] / w, drawn[0]["y"] / hh)), drawn, LTX["size"])
        out = _mark(raw, _out_dir() / f"ltx_{stamp}.mp4"); raw.unlink(missing_ok=True)
        return {"kind": kind, "file": str(out.relative_to(Path(paths.output_dir(True)))), "seconds": round(time.time() - t0, 1), "follow": err, "model": LTX["model"], "licence": LTX["licence"], "seed": seed}
    raise HTTPException(400, "unknown render kind")


def _worker(rec, kind, b):
    try:
        with _LOCK: rec.update(execute(kind, b), status="done")
    except HTTPException as e: rec.update(status="error", error=str(e.detail))
    except Exception as e: rec.update(status="error", error=f"{e}"[:900])


def proof():
    try: return json.loads(PROOF.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}


@router.get("")
def overview():
    return {"moves": [{"id": k, "label": k.replace("_", " "), "readable": r["kind"] != "unreadable", "why": r.get("why", "")} for k, r in V.MOVES.items()],
            "presets": {k: {"label": v["label"], "path": v["path"], "plan": path_plan(v["path"])} for k, v in PRESETS.items()},
            "renders": {"wan_path": {k: WAN[k] for k in ("model", "licence", "size", "frames", "fps", "peak_gb")}, "ltx_track": {k: LTX[k] for k in ("model", "licence", "size", "frames", "fps", "peak_gb")}},
            "verdicts": {"MATCH": "The clip did the move.", "MISMATCH": "The clip did something else, or nothing.", "INCONCLUSIVE": "Not enough evidence either way. This is never counted as a pass."},
            "proof": proof()}


@router.post("/plan")
def plan_post(b: dict = None):
    b = b or {}
    return path_plan(b.get("path"))


@router.post("/verify")
async def verify_post(b: dict = None):
    b = b or {}; move = str(b.get("move") or "")
    if move not in V.MOVES: raise HTTPException(400, "pick a move")
    clip = _input_file(b.get("clip"), VIDEO_EXT)
    return await run_in_threadpool(lambda: {"clip": clip.name, **V.verify(clip, move)})


@router.post("/pick")
async def pick_post(b: dict = None):
    b = b or {}; move = str(b.get("move") or "")
    if move not in V.MOVES: raise HTTPException(400, "pick a move")
    clips = b.get("clips")
    if not isinstance(clips, list) or not 2 <= len(clips) <= 12: raise HTTPException(400, "pick two to twelve takes")
    files = [(Path(str(c)).name, _input_file(c, VIDEO_EXT)) for c in clips]
    return await run_in_threadpool(V.pick, files, move)


def take_set_files(sid, takes_mod=None):
    """The finished clips of a Story & Takes set (studio/takes.py, package P4), as (name, path). Raises 409 when that package is not in this build."""
    if takes_mod is None:
        try: from studio import takes as takes_mod
        except ImportError: raise HTTPException(409, "Takes are not part of this build yet, so pick the clips by hand.") from None
    try: s = takes_mod.get(str(sid))
    except Exception: s = None
    if not s: raise HTTPException(404, "no such take set")
    d = takes_mod._dir(s["id"])
    files = [(f"take {t['i'] + 1}", d / t["file"]) for t in s.get("takes", []) if t.get("status") == "done" and t.get("kind") == "video" and t.get("file") and (d / t["file"]).is_file()]
    if len(files) < 2: raise HTTPException(400, "the set needs at least two finished clips")
    return files


@router.post("/pick_set")
async def pick_set_post(b: dict = None):
    """Pick the take in a Story & Takes set that followed the move best. Only a MATCH is picked; keeping it is still the person's click on the Takes page."""
    b = b or {}; move = str(b.get("move") or "")
    if move not in V.MOVES: raise HTTPException(400, "pick a move")
    files = take_set_files(b.get("set"))
    return await run_in_threadpool(V.pick, files, move)


@router.post("/render")
def render_post(b: dict = None):
    b = b or {}; kind = str(b.get("kind") or "")
    if kind not in ("wan_path", "ltx_track"): raise HTTPException(400, "kind is wan_path or ltx_track")
    if kind == "wan_path": path_plan(b.get("path"))
    else: tracks_json(b.get("tracks"))
    _input_file(b.get("image"), IMAGE_EXT); sfw.check(str(b.get("prompt") or ""))
    jid = "cam-" + uuid.uuid4().hex[:10]; rec = {"job": jid, "kind": kind, "status": "running", "started": time.time()}; JOBS[jid] = rec
    threading.Thread(target=_worker, args=(rec, kind, b), daemon=True, name=f"campath-{jid}").start(); return rec


@router.get("/jobs/{jid}")
def job_get(jid: str):
    r = JOBS.get(jid)
    if not r: raise HTTPException(404, "no such job")
    return r
