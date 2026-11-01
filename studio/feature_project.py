"""One-file project: a shoot or a board packed into one .psproject file (a plain zip) with its graphs, seeds, model hashes and download sources, and media if asked for. Open it on another machine and it says what is missing there, then re-renders only on a click.
What can never be in the file: model weights, folder paths, or anything read from the home folder. Files come only from ComfyUI's input and output folders and only with media extensions; every string is checked for paths before the file is written, and media loses its metadata. Reopening treats the file as a stranger's: no path in it is trusted, and its graphs get the same check a pasted graph does."""
import hashlib, io, json, os, re, shutil, subprocess, tempfile, threading, time, urllib.error, urllib.parse, urllib.request, uuid, zipfile
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from psn import paths
from studio import sfw
from studio.model_sources import source
from studio.names import MODEL_FILE

router = APIRouter(prefix="/api/project")
PAGE = {"tab": "project", "label": "Project File", "title": ["Project File", "A whole shoot. One file.", "Graphs, seeds, model hashes and where to get each model, ready to reopen on another machine. Never weights, never your folders."], "module": "project.js", "export": "ProjectFile", "css": "project.css"}
FORMAT = "parametric-studio-project"; VERSION = 1; EXT = ".psproject"
MEDIA_EXT = (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov", ".mkv", ".wav", ".mp3", ".flac")
MAX_FILE_BYTES = 8 * 2**30; MAX_MEDIA_BYTES = 2 * 2**30; MAX_JSON_BYTES = 64 * 2**20; MAX_MEMBERS = 2000; NAME_OK = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,160}")
PATHISH = re.compile(r"(?<![\w.])(?:/(?:home|Users|mnt|root|media|var|tmp|opt|srv|data|run|etc)/|~/|[A-Za-z]:[\\/])")
_jobs: dict = {}; _lock = threading.Lock()


def state_dir() -> Path:
    return Path(os.environ.get("STUDIO_STATE_DIR") or Path.home() / ".local" / "state" / "parametric-studio") / "projects"


def _comfy_url() -> str: return os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/")


def _comfy(path, payload=None, timeout=30):
    req = urllib.request.Request(_comfy_url() + path, data=json.dumps(payload).encode() if payload is not None else None, headers={"Content-Type": "application/json"} if payload is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read() or b"{}")


# ---------- keeping private things out ----------
def leaks(value, home=None) -> list:
    """Every string in here that holds a folder path, or this machine's home folder or user name. The file is not written while this list has anything in it."""
    home = home or str(Path.home()); user = os.path.basename(home.rstrip("/\\")); out = []
    def walk(v, where):
        if isinstance(v, dict):
            for k, x in v.items(): walk(k, where + "/key"); walk(x, f"{where}/{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v): walk(x, f"{where}/{i}")
        elif isinstance(v, str) and (PATHISH.search(v) or home in v or (len(user) >= 4 and re.search(rf"\b{re.escape(user)}\b", v))): out.append(where)
    walk(value, ""); return out


def scrub(value, home=None):
    """A path in a value becomes its last part, and a model's subfolder stays only if it holds nothing private. -> (clean value, how many changed)."""
    home = home or str(Path.home()); n = [0]
    def go(v):
        if isinstance(v, dict): return {k: go(x) for k, x in v.items()}
        if isinstance(v, list): return [go(x) for x in v]
        if isinstance(v, str) and leaks(v, home):
            n[0] += 1
            return re.split(r"[\\/]", v.strip())[-1] if re.fullmatch(r"\S+", v) else PATHISH.sub("", v.replace(home, "")).strip()
        return v
    return go(value), n[0]


def models_in(graph: dict) -> list:
    names = set()
    for n in graph.values():
        for v in ((n or {}).get("inputs") or {}).values():
            if isinstance(v, str) and MODEL_FILE.search(v): names.add(v.replace("\\", "/").split("/")[-1])
    return sorted(names)


def inputs_in(graph: dict) -> list:
    """Files a graph reads from ComfyUI's input folder."""
    names = set()
    for n in graph.values():
        if (n or {}).get("class_type") in ("LoadImage", "LoadVideo", "LoadAudio", "VHS_LoadVideo", "LoadImageMask"):
            for k in ("image", "video", "file", "audio"):
                v = ((n or {}).get("inputs") or {}).get(k)
                if isinstance(v, str) and "${" not in v: names.add(v)
    return sorted(names)


# ---------- hashes ----------
def _hash_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(2**22), b""): h.update(c)
    return h.hexdigest()


def find_model(name: str, root=None):
    root = root or paths.models_root(True)
    for dp, _, fn in os.walk(root, followlinks=True):
        if name in fn: return os.path.join(dp, name)
    return None


def local_hash(name: str, root=None):
    """The sha256 of this machine's copy, cached by size and time. -> (hash or None, bytes or None)."""
    p = find_model(name, root)
    if not p: return None, None
    st = os.stat(p); key = f"{name}:{st.st_size}:{int(st.st_mtime)}"; cache = state_dir() / "model_hashes.json"
    try: known = json.loads(cache.read_text()).get(key)
    except (OSError, ValueError): known = None
    if known: return known, st.st_size
    h = _hash_file(p)
    with _lock:
        try: c = json.loads(cache.read_text())
        except (OSError, ValueError): c = {}
        c[key] = h; cache.parent.mkdir(parents=True, exist_ok=True); cache.write_text(json.dumps(c))
    return h, st.st_size


def model_rows(names, root=None, hash_them=True, progress=None) -> list:
    rows = []
    for i, n in enumerate(names):
        src = source(n) or {}
        if progress: progress(f"Hashing {n} ({i + 1} of {len(names)})")
        h, size = local_hash(n, root) if hash_them else (None, None)
        rows.append({"file": n, "sha256": h or src.get("sha256"), "hash_of": "the file on the machine that made this" if h else "the published file" if src.get("sha256") else None, "bytes": size, "url": src.get("url"), "folder": src.get("dir"), "gated": bool(src.get("gated"))})
    return rows


# ---------- reading the board and the runs ----------
def graph_as_ran(job_id):
    """ComfyUI's own record of what ran, while it still has it."""
    if not job_id or not re.fullmatch(r"[0-9a-fA-F-]{8,64}", str(job_id)): return None
    try: h = _comfy(f"/history/{urllib.parse.quote(str(job_id))}", timeout=10).get(str(job_id)) or {}
    except Exception: return None
    p = h.get("prompt")
    return p[2] if isinstance(p, (list, tuple)) and len(p) > 2 and isinstance(p[2], dict) else None


def rebuild(body: dict):
    """The graph a Shot Board job's body makes, by the same code a render uses."""
    from studio import server as S
    goal = body.get("goal")
    if goal not in S.GOALS: return None
    try: return S._graph(goal, body, body.get("image"))[0]
    except Exception: return None


def board_shots(board: dict) -> list:
    shots = []
    for j in (board.get("jobs") or [])[:64]:
        if not isinstance(j, dict) or not isinstance(j.get("body"), dict): continue
        body = {**j["body"]}
        if j.get("seed") is not None: body["seed"] = j["seed"]
        g = graph_as_ran(j.get("job")); how = "as it ran" if g else None
        if g is None and j.get("seed") is not None: g = rebuild(body); how = "rebuilt from the board" if g else None
        files = [{k: f.get(k) for k in ("filename", "subfolder", "type", "kind") if f.get(k) is not None} for f in (j.get("files") or []) if isinstance(f, dict)]
        shots.append({"id": re.sub(r"[^\w-]", "_", str(j.get("id") or len(shots)))[:40], "label": str(j.get("label") or j.get("id") or "Shot")[:120], "goal": body.get("goal"), "seed": j.get("seed"), "status": j.get("status"), "graph_source": how, "graph": g, "outputs": files})
    return shots


def run_shots(run_id: str) -> list:
    """A recipe run: each step's kept graph and seed."""
    from studio import recipes as R
    run = R.get_run(run_id)
    if not run: raise HTTPException(404, "no such recipe run")
    shots = []
    for st in run.get("steps") or []:
        try: g = json.loads((R._root() / run["run"] / f"{st['id']}.graph.json").read_text())
        except (OSError, ValueError): g = None
        if g is None and st.get("type") == "cpu": continue
        files = []
        for f in st.get("files") or []:
            q = dict(urllib.parse.parse_qsl(str(f.get("url") or "").split("?", 1)[-1]))
            files.append({"filename": f.get("filename"), "kind": f.get("kind"), "subfolder": q.get("subfolder", ""), "type": q.get("type", "output")})
        shots.append({"id": re.sub(r"[^\w-]", "_", f"{run['run']}_{st['id']}")[:40], "label": f"{run.get('title')}: {st.get('label') or st['id']}"[:120], "goal": (st.get("body") or {}).get("goal"), "seed": st.get("seed"), "status": st.get("status"), "graph_source": "as it ran" if g else None, "graph": g, "outputs": files})
    return shots


# ---------- media ----------
def _roots():
    return {"input": Path(paths.comfy_input(True)).resolve(), "output": Path(paths.output_dir(True)).resolve()}


def media_path(name, subfolder="", kind="output"):
    """A media file inside ComfyUI's folders, or None. A model file, a link out of the folder or any other extension is refused."""
    root = _roots().get(kind)
    if not root or not isinstance(name, str) or not name.lower().endswith(MEDIA_EXT) or MODEL_FILE.search(name): return None
    p = (root / str(subfolder or "") / name).resolve()
    return p if root in p.parents and p.is_file() else None


def strip_metadata(src, dst) -> bool:
    """Copies media without metadata, which can hold prompts, graphs or folder paths. False when it cannot be done, and then the file stays out."""
    ext = Path(src).suffix.lower()
    if ext == ".png":
        from PIL import Image
        with Image.open(src) as im: im.save(dst, "PNG")
        return True
    if not shutil.which("ffmpeg"): return False
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src), "-map", "0", "-map_metadata", "-1", "-c", "copy", str(dst)], capture_output=True, timeout=600)
    return r.returncode == 0 and Path(dst).is_file()


def member_name(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(str(name)))[:120]
    return base if NAME_OK.fullmatch(base) else "file" + Path(base).suffix


# ---------- writing the file ----------
def build_project(name: str, shots: list, include_media=False, root=None, progress=None) -> tuple:
    """-> (bytes-free manifest, [(member name, source path)], notes). Raises when something private would go in."""
    notes = []; shots, changed = scrub(shots)
    if changed: notes.append(f"{changed} folder {'path was' if changed == 1 else 'paths were'} cut down to file names.")
    names = sorted({m for s in shots if s.get("graph") for m in models_in(s["graph"])}); models = model_rows(names, root, progress=progress); media = []; used = 0; done = set()
    def add(fname, sub, kind, role):
        nonlocal used
        p = media_path(fname, sub, kind)
        if not p: return {"file": member_name(fname), "role": role, "included": False, "why": "not found in ComfyUI's folders" if include_media else "media was left out"}
        size = p.stat().st_size; m = member_name(fname)
        if not include_media: return {"file": m, "role": role, "bytes": size, "sha256": None, "included": False, "why": "media was left out"}
        if used + size > MAX_MEDIA_BYTES: return {"file": m, "role": role, "bytes": size, "included": False, "why": "over the 2 GB media limit"}
        if m not in done: media.append((m, p)); done.add(m); used += size
        return {"file": m, "role": role, "bytes": size, "included": True}
    for s in shots:
        s["inputs"] = [add(n, "", "input", "input") for n in inputs_in(s.get("graph") or {})]
        s["output_files"] = [add(o["filename"], o.get("subfolder", ""), "output", "output") for o in s.get("outputs") or [] if o.get("filename") and o.get("type") != "input"]
        s.pop("outputs", None)
        s["graph_hash"] = hashlib.sha256(json.dumps(s["graph"], sort_keys=True).encode()).hexdigest()[:12] if s.get("graph") else None
    manifest = {"format": FORMAT, "version": VERSION, "name": str(name or "Untitled")[:120], "made": time.strftime("%Y-%m-%d"), "shots": shots, "models": models, "contains": {"weights": False, "media": bool(media)}, "notes": notes}
    bad = leaks(manifest)
    if bad: raise HTTPException(500, f"Stopped: {len(bad)} values would still have carried a folder path or your user name, so no file was written.")
    return manifest, media, notes


def write_zip(manifest: dict, media: list, out: Path, progress=None) -> None:
    out.parent.mkdir(parents=True, exist_ok=True); tmp = out.with_suffix(".part")
    readme = f"{manifest['name']}\nA Parametric Studio project. Open it on the Project File page.\nproject.json holds the graphs, seeds, model hashes and download sources. It holds no model weights and no folder paths.\n"
    with tempfile.TemporaryDirectory() as td, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme); kept = []
        for i, (m, p) in enumerate(media):
            if progress: progress(f"Packing {m} ({i + 1} of {len(media)})")
            clean = os.path.join(td, "c" + Path(m).suffix)
            ok = False
            try: ok = strip_metadata(p, clean)
            except Exception: pass
            if ok: z.write(clean, "media/" + m, compress_type=zipfile.ZIP_STORED); kept.append(m); os.remove(clean)
            else: manifest["notes"].append(f"{m} was left out: its metadata could not be removed.")
        for s in manifest["shots"]:
            for f in s["inputs"] + s["output_files"]:
                if f.get("included") and f["file"] not in kept: f.update(included=False, why="its metadata could not be removed")
        manifest["contains"]["media"] = bool(kept)
        z.writestr("project.json", json.dumps(manifest, indent=1))
    os.replace(tmp, out)


def _export_job(jid, b):
    def say(t): _jobs[jid]["note"] = t
    try:
        shots = []
        if isinstance(b.get("board"), dict): shots += board_shots(b["board"])
        for rid in (b.get("runs") or [])[:32]:
            if isinstance(rid, str): shots += run_shots(rid)
        if not shots: raise HTTPException(400, "There is nothing to pack yet: no board jobs and no recipe runs were chosen.")
        manifest, media, _ = build_project(b.get("name") or "Untitled", shots, bool(b.get("include_media")), progress=say)
        out = state_dir() / "exports" / jid / (re.sub(r"[^\w-]+", "_", manifest["name"]).strip("_")[:60] + EXT or "project" + EXT); write_zip(manifest, media, out, say)
        _jobs[jid].update(state="done", note="", file=out.name, bytes=out.stat().st_size, shots=len(manifest["shots"]), models=len(manifest["models"]), with_graph=sum(1 for s in manifest["shots"] if s.get("graph")), media=sum(1 for s in manifest["shots"] for f in s["inputs"] + s["output_files"] if f.get("included")), notes=manifest["notes"], path=str(out))
    except HTTPException as e: _jobs[jid].update(state="error", error=str(e.detail))
    except Exception as e: _jobs[jid].update(state="error", error=f"{type(e).__name__}: {str(e)[:200]}")


@router.post("/export")
def export(b: dict):
    jid = uuid.uuid4().hex[:12]; _jobs[jid] = {"id": jid, "state": "working", "note": "Reading the board"}
    threading.Thread(target=_export_job, args=(jid, b), daemon=True).start(); return {"id": jid}


@router.get("/export/{jid}")
def export_status(jid: str):
    j = _jobs.get(jid)
    if not j: raise HTTPException(404, "no such export")
    return {k: v for k, v in j.items() if k != "path"}


@router.get("/export/{jid}/file")
def export_file(jid: str):
    j = _jobs.get(jid)
    if not j or j.get("state") != "done": raise HTTPException(404, "no such file")
    return FileResponse(j["path"], filename=j["file"], media_type="application/zip")


@router.get("/runs")
def recent_runs():
    """Recipe runs that can be packed."""
    from studio import recipes as R
    return {"runs": [{"run": r["run"], "title": r.get("title"), "status": r.get("status"), "created": r.get("created")} for r in R.list_runs(None, 30) if r.get("status") == "done"]}


# ---------- reopening ----------
def read_project(path) -> tuple:
    """Opens a file someone else may have made. -> (manifest, media names). Refuses anything that is not plainly a project."""
    try: z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError): raise HTTPException(400, "This is not a project file: it is not a zip.") from None
    with z:
        infos = z.infolist()
        if len(infos) > MAX_MEMBERS: raise HTTPException(400, "This file has too many parts to be a project.")
        media = []
        for i in infos:
            n = i.filename
            if (i.external_attr >> 16) & 0o170000 == 0o120000: raise HTTPException(400, f"This file holds a link ({n}). Projects never do, so it was refused.")
            if n in ("project.json", "README.txt") or (n.endswith(".txt") and "project.json" not in z.namelist()): continue
            base = n[6:] if n.startswith("media/") else None
            if not base or "/" in base or "\\" in base or ".." in base or not NAME_OK.fullmatch(base) or not base.lower().endswith(MEDIA_EXT): raise HTTPException(400, f"This file holds something a project never does: {n[:80]}. It was refused and nothing was unpacked.")
            if i.file_size > MAX_MEDIA_BYTES: raise HTTPException(400, f"{base} is larger than a project's media limit.")
            media.append(base)
        if sum(i.file_size for i in infos) > MAX_MEDIA_BYTES + MAX_JSON_BYTES: raise HTTPException(400, "This file unpacks to more than a project may hold.")
        try: info = z.getinfo("project.json")
        except KeyError: raise HTTPException(400, "This zip is not a project: it has no project.json.") from None
        if info.file_size > MAX_JSON_BYTES: raise HTTPException(400, "project.json is too large.")
        try: m = json.loads(z.read(info))
        except ValueError: raise HTTPException(400, "project.json cannot be read.") from None
    if not isinstance(m, dict) or m.get("format") != FORMAT: raise HTTPException(400, "This zip is not a Parametric Studio project.")
    if int(m.get("version") or 0) > VERSION: raise HTTPException(400, f"This project was made by a newer studio (format {m.get('version')}). Update this one to open it.")
    if not isinstance(m.get("shots"), list): raise HTTPException(400, "This project has no shots list.")
    return m, media


def _unsafe_prefix(graph: dict) -> list:
    """A save path that climbs out of the output folder, in a stranger's graph."""
    bad = []
    for nid, n in graph.items():
        for k, v in ((n or {}).get("inputs") or {}).items():
            if k in ("filename_prefix", "output_path", "save_path", "folder_path") and isinstance(v, str) and (".." in v or v.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", v)): bad.append(f"{(n or {}).get('class_type')} would write outside the output folder ({k})")
    return bad


def report(m: dict, media: list) -> dict:
    """What this machine has and does not have for each shot. Nothing here starts a render."""
    from studio import recipe_check as C
    try: oi = _comfy("/object_info", timeout=30)
    except Exception: oi = None
    files = C.model_files() if oi is not None else {}
    models = []
    for r in m.get("models") or []:
        if not isinstance(r, dict) or not isinstance(r.get("file"), str): continue
        name = os.path.basename(r["file"]); here = name in files; mine, _ = (None, None)
        if here:
            cache = state_dir() / "model_hashes.json"
            p = find_model(name); st = os.stat(p); key = f"{name}:{st.st_size}:{int(st.st_mtime)}"
            try: mine = json.loads(cache.read_text()).get(key)
            except (OSError, ValueError): mine = None
        url = r.get("url") if isinstance(r.get("url"), str) and r["url"].startswith("https://") else None
        models.append({"file": name, "here": here, "hash_in_file": r.get("sha256"), "hash_here": mine, "hash_state": "missing" if not here else "not hashed yet" if not mine else "not in the file" if not r.get("sha256") else "same" if mine == r["sha256"] else "different", "url": url, "folder": r.get("folder"), "gated": bool(r.get("gated"))})
    shots = []
    input_dir = Path(paths.comfy_input(True))
    for s in m["shots"]:
        if not isinstance(s, dict): continue
        g = s.get("graph") if isinstance(s.get("graph"), dict) else None; probs = []
        if g is None: probs.append("No graph was recorded for this shot.")
        elif oi is None: probs.append("ComfyUI could not be asked, so this was not checked.")
        else:
            try: probs += C.check_graph(g, oi, files)
            except Exception as e: probs.append(f"This graph could not be read: {type(e).__name__}")
            probs += _unsafe_prefix(g)
            if sfw.flagged(*[str((n or {}).get("inputs", {}).get("text", "")) for n in g.values()]): probs.append(sfw.MESSAGE)
        need = []
        for name in inputs_in(g or {}):
            base = member_name(name); inc = base in media; there = (input_dir / os.path.basename(name)).is_file()
            need.append({"file": name, "in_file": inc, "on_machine": there})
            if not inc and not there: probs.append(f"The input file {os.path.basename(name)} is not in this project and not on this machine.")
        shots.append({"id": str(s.get("id"))[:40], "label": str(s.get("label"))[:120], "goal": s.get("goal"), "seed": s.get("seed"), "graph_source": s.get("graph_source"), "has_graph": g is not None, "needs": need, "problems": sorted(set(probs)), "ready": oi is not None and g is not None and not probs, "outputs": [f.get("file") for f in s.get("output_files") or [] if isinstance(f, dict) and f.get("included")]})
    return {"comfy_up": oi is not None, "models": models, "shots": shots, "missing_models": [x["file"] for x in models if not x["here"]], "ready": sum(1 for s in shots if s["ready"]), "media": media}


def _pid_dir(pid: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{12}", pid or ""): raise HTTPException(404, "no such project")
    d = state_dir() / "open" / pid
    if not (d / "project.psproject").is_file(): raise HTTPException(404, "no such project")
    return d


@router.post("/open")
async def open_project(file: UploadFile = File(...)):
    pid = uuid.uuid4().hex[:12]; d = state_dir() / "open" / pid; d.mkdir(parents=True, exist_ok=True); dst = d / "project.psproject"; n = 0
    with open(dst, "wb") as f:
        while True:
            c = await file.read(2**20)
            if not c: break
            n += len(c)
            if n > MAX_FILE_BYTES: shutil.rmtree(d, ignore_errors=True); raise HTTPException(413, "That file is over 8 GB, far bigger than a project.")
            f.write(c)
    try: m, media = await run_in_threadpool(read_project, dst)
    except HTTPException: shutil.rmtree(d, ignore_errors=True); raise
    return await run_in_threadpool(_view, pid, m, media)


def _view(pid, m, media) -> dict:
    return {"id": pid, "name": str(m.get("name") or "Untitled")[:120], "made": m.get("made"), "contains": m.get("contains"), "notes": [str(x)[:300] for x in (m.get("notes") or [])][:10], "report": report(m, media)}


@router.get("/open/{pid}")
def reopen(pid: str):
    m, media = read_project(_pid_dir(pid) / "project.psproject")
    return _view(pid, m, media)


def _upload_media(path, member) -> str:
    """Puts a project's input file into this ComfyUI, through its own upload. -> the name it answered with."""
    from studio import server as S
    with zipfile.ZipFile(path) as z: data = z.read("media/" + member)
    return S._upload(data, member, None)["name"]


def _render(pid: str, b: dict) -> dict:
    if b.get("confirm") is not True: raise HTTPException(400, "A project only renders when you press the button.")
    d = _pid_dir(pid); m, media = read_project(d / "project.psproject"); rep = report(m, media); shot_id = b.get("shot")
    row = next((s for s in rep["shots"] if s["id"] == shot_id), None); src = next((s for s in m["shots"] if str(s.get("id"))[:40] == shot_id), None)
    if not row or not src: raise HTTPException(404, "no such shot")
    if not row["ready"]: raise HTTPException(409, "; ".join(row["problems"][:4]) or "This shot is not ready.")
    g = json.loads(json.dumps(src["graph"]))
    for need in row["needs"]:
        if need["in_file"]:
            new = _upload_media(d / "project.psproject", member_name(need["file"]))
            for n in g.values():
                for k, v in (n.get("inputs") or {}).items():
                    if v == need["file"]: n["inputs"][k] = new
    try: res = _comfy("/prompt", {"prompt": g, "client_id": "project-" + pid})
    except urllib.error.HTTPError as e:
        from studio import server as S
        raise S._rejected(e) from None
    except OSError: raise HTTPException(503, "ComfyUI is not reachable.") from None
    if not res.get("prompt_id"): raise HTTPException(502, "ComfyUI did not return a job.")
    return {"job": res["prompt_id"], "shot": shot_id, "seed": src.get("seed")}


@router.post("/open/{pid}/render")
def render(pid: str, b: dict): return _render(pid, b)
