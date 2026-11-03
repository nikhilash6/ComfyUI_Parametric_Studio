"""Prove It: re-run one of our renders on your machine, with its exact graph and seed, and show the difference from ours.
Every figure is measured from the two files. It never says a re-run "proves" anything it cannot: the same graph and seed only promise the same output on the same model files, the same software and the same kind of GPU, so the report lists what differs and leaves the reading to you.
A render with no seed on record, or that started from a file we do not ship, is refused with the reason. Nothing starts without a click."""
import gzip, hashlib, io, json, os, re, subprocess, tempfile, threading, time, urllib.parse, urllib.request, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from PIL import Image, ImageChops, ImageStat
from psn import paths

router = APIRouter(prefix="/api/prove")
PAGE = {"tab": "prove", "label": "Prove It", "title": ["Prove It", "Our render. Your machine.", "Re-run the exact graph and seed here, then wipe between the two. What differs is listed, not hidden."], "module": "prove.js", "export": "ProveIt", "css": "prove.css"}
HERE = Path(__file__).resolve().parent; DATA = HERE / "prove_it.json.gz"; SHOWCASE = HERE / "web" / "showcase" / "showcase.json"
FRAME_AT = (0.1, 0.5, 0.9); OFF_BY = 8; CLOSE_MEAN = 3.0; COARSE_FLOOR = 6.0
NOT_A_PROMISE = "The same graph and seed only promise the same output on the same model files, the same software and the same kind of GPU. A different GPU, driver, PyTorch build or attention backend can change the result with nothing wrong on either side, and we have not tested your machine."
_cache: dict = {}; _lock = threading.Lock()


def data() -> dict:
    if "d" not in _cache:
        try:
            with gzip.open(DATA, "rt", encoding="utf-8") as f: _cache["d"] = json.load(f)
        except OSError: _cache["d"] = {"renders": {}, "models": {}, "hardware": {}}
    return _cache["d"]


def same_machine() -> str:
    """What we really measured when repeating our own renders on the machine that made them. Empty if there is no record."""
    try: rows = json.loads((HERE / "prove_it_repeats.json").read_text(encoding="utf-8"))["repeats"]
    except (OSError, ValueError, KeyError): return ""
    same = sum(1 for r in rows if r.get("result") == "identical")
    return f"We repeated {len(rows)} of our renders on the machine that made them, and {same} came back identical by hash. That is what it is: too few to promise anything, and it says nothing about another machine." if rows else ""


def state_dir() -> Path:
    return Path(os.environ.get("STUDIO_STATE_DIR") or Path.home() / ".local" / "state" / "parametric-studio") / "prove"


def _comfy_url() -> str: return os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/")


# ---------- what is on this machine ----------
def your_hardware() -> dict:
    """What this machine says about itself. Nothing is guessed: what does not answer stays null."""
    out = {"gpu": None, "vram_gib": None, "driver": None, "comfyui": None, "torch": None, "comfy_up": False}
    try:
        with urllib.request.urlopen(_comfy_url() + "/system_stats", timeout=4) as r: s = json.load(r)
        d = (s.get("devices") or [{}])[0]; sy = s.get("system") or {}
        name = str(d.get("name") or ""); name = re.sub(r"^cuda:\d+\s*", "", name).split(" : ")[0].strip()
        out.update(comfy_up=True, gpu=name or None, vram_gib=round(d["vram_total"] / 2**30) if d.get("vram_total") else None, comfyui=sy.get("comfyui_version"), torch=sy.get("pytorch_version"))
    except Exception: pass
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip(): out["driver"] = r.stdout.split("\n")[0].strip()
    except (OSError, subprocess.SubprocessError): pass
    return out


def hardware_rows(ours: dict, yours: dict) -> list:
    rows = []
    for k, label in (("gpu", "GPU"), ("vram_gib", "Video memory, GiB"), ("driver", "GPU driver"), ("torch", "PyTorch"), ("comfyui", "ComfyUI")):
        a, b = ours.get(k), yours.get(k)
        rows.append({"what": label, "ours": a, "yours": b, "same": None if a is None or b is None else str(a) == str(b)})
    return rows


def _hash_cache_path() -> Path: return state_dir() / "model_hashes.json"
_hashing: dict = {}


def find_model(name: str, root=None):
    root = root or paths.models_root(True)
    for dp, _, fn in os.walk(root, followlinks=True):
        if name in fn: return os.path.join(dp, name)
    return None


def _hash_now(name: str, path: str, key: str) -> None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for c in iter(lambda: f.read(2**22), b""): h.update(c)
        with _lock:
            p = _hash_cache_path(); c = json.loads(p.read_text()) if p.is_file() else {}; c[key] = h.hexdigest(); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(c))
    except OSError: pass
    finally:
        with _lock: _hashing.pop(key, None)


def model_row(name: str, ours, root=None, start=True) -> dict:
    """One model: our hash against yours. Yours is worked out in the background once per file version, since these files are large."""
    row = {"file": name, "ours": (ours or {}).get("sha256"), "ours_bytes": (ours or {}).get("bytes"), "yours": None, "yours_bytes": None, "state": "missing"}
    path = find_model(name, root)
    if not path: return row
    st = os.stat(path); key = f"{name}:{st.st_size}:{int(st.st_mtime)}"; row["yours_bytes"] = st.st_size
    try: known = json.loads(_hash_cache_path().read_text()).get(key)
    except (OSError, ValueError): known = None
    if known: row.update(yours=known, state="same" if known == row["ours"] else "different" if row["ours"] else "no hash of ours")
    else:
        row["state"] = "hashing"
        if start:
            with _lock:
                if key not in _hashing: _hashing[key] = True; threading.Thread(target=_hash_now, args=(name, path, key), daemon=True).start()
    return row


def models_of(entry: dict) -> list:
    names = set()
    for st in entry.get("steps") or []:
        for n in (st.get("graph") or {}).values():
            for v in (n.get("inputs") or {}).values():
                if isinstance(v, str) and v.split("/")[-1] in data().get("models", {}): names.add(v.split("/")[-1])
    return sorted(names)


# ---------- comparing two files ----------
def compare_images(ours: Image.Image, yours: Image.Image) -> tuple:
    """-> ({mean_diff 0-255, pct_off, resized}, heat map). Yours is scaled to ours when the sizes differ, and the result says so."""
    a = ours.convert("RGB"); resized = a.size != yours.size; b = yours.convert("RGB").resize(a.size, Image.LANCZOS) if resized else yours.convert("RGB")
    d = ImageChops.difference(a, b); mean = sum(ImageStat.Stat(d).mean) / 3; grey = d.convert("L"); hist = grey.histogram(); off = sum(hist[OFF_BY + 1:]) / max(1, sum(hist))
    heat = Image.merge("RGB", (grey.point(lambda v: min(255, v * 6)), grey.point(lambda v: min(255, v * 4)), grey.point(lambda v: 0)))
    return {"mean_diff": round(mean, 3), "pct_off": round(off * 100, 2), "off_by": OFF_BY, "resized": resized}, heat


def pixels_sha(im: Image.Image) -> str:
    return hashlib.sha256(f"{im.size[0]}x{im.size[1]}:".encode() + im.convert("RGB").tobytes()).hexdigest()


def verdict(identical, mean, floor) -> dict:
    """Plain words for the numbers. Only a hash match says the same; the rest say how far apart, and what that does not tell you."""
    if identical: return {"word": "Identical", "tone": "ok", "text": "Every pixel of your render matches our original, by hash."}
    if mean is None: return {"word": "Not compared", "tone": "warn", "text": "The two files could not be compared."}
    tol = floor * 1.25 + 0.05 if floor is not None else 0
    if floor is not None and floor > COARSE_FLOOR and mean <= floor * 2: return {"word": "Too coarse to tell", "tone": "warn", "text": f"Our web copy of this render is itself {floor} away from our original, so a difference of {mean} here says little. The hash of your full picture does not match ours."}
    if floor is not None and mean <= tol: return {"word": "Indistinguishable here", "tone": "ok", "text": f"The difference ({mean}) is no bigger than the compression of our web copy ({floor}), so this page cannot tell them apart. That is not proof they are identical: the hash of your full picture does not match ours."}
    if mean <= max(CLOSE_MEAN, tol * 1.6): return {"word": "Close, not the same", "tone": "warn", "text": f"A mean difference of {mean} out of 255, more than our web copy's own compression{f' ({floor})' if floor is not None else ''}. Small differences like this are common across GPUs and software versions."}
    return {"word": "Different", "tone": "bad", "text": f"A mean difference of {mean} out of 255. Check the list below: a different model file changes everything, and so can a different GPU or PyTorch build."}


def _frame(path, seconds) -> Image.Image:
    with tempfile.TemporaryDirectory() as td:
        o = os.path.join(td, "f.png"); subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{seconds:.3f}", "-i", str(path), "-frames:v", "1", o], check=True, timeout=120)
        return Image.open(o).convert("RGB").copy()


def _duration(path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True, timeout=30).stdout.strip())


def _pcm(path) -> bytes:
    return subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "22050", "-f", "s16le", "-"], capture_output=True, check=True, timeout=300).stdout


def compare_audio(ours_pcm: bytes, yours_pcm: bytes) -> dict:
    import numpy as np
    a, b = np.frombuffer(ours_pcm, dtype=np.int16).astype(np.float32) / 32768, np.frombuffer(yours_pcm, dtype=np.int16).astype(np.float32) / 32768; n = min(len(a), len(b))
    return {"mean_diff": round(float(np.abs(a[:n] - b[:n]).mean()) * 100, 3) if n else None, "unit": "percent of full scale, sample by sample", "seconds_ours": round(len(a) / 22050, 2), "seconds_yours": round(len(b) / 22050, 2)}


def compare_files(kind: str, ours_path, yours_path, entry: dict, out_dir: Path) -> dict:
    """Writes ours_N.png, yours_N.png and diff_N.png into out_dir and returns the figures."""
    out_dir.mkdir(parents=True, exist_ok=True); floor = entry.get("noise_floor")
    if kind == "audio":
        y = _pcm(yours_path); same = hashlib.sha256(y).hexdigest() == entry.get("pcm_sha256"); c = compare_audio(_pcm(ours_path), y); c["identical"] = same; c["hash_on_record"] = bool(entry.get("pcm_sha256"))
        v = {"word": "Identical", "tone": "ok", "text": "Your audio matches our original sample for sample, by hash."} if same else {"word": "Not the same", "tone": "warn", "text": f"Mean difference {c['mean_diff']} percent of full scale. Compare them by ear."}
        return {"kind": kind, "figures": c, "verdict": v, "frames": []}
    frames = []
    if kind == "video":
        dur = _duration(yours_path); ours_dur = _duration(ours_path)
        pairs = [(at, _frame(ours_path, min(ours_dur * at, ours_dur - 0.05)), _frame(yours_path, min(dur * at, dur - 0.05))) for at in FRAME_AT]; same = False
    else:
        y = Image.open(yours_path).convert("RGB"); same = bool(entry.get("pixels_sha256")) and pixels_sha(y) == entry["pixels_sha256"]; pairs = [(None, Image.open(ours_path).convert("RGB"), y)]
    worst = None
    for i, (at, a, b) in enumerate(pairs):
        c, heat = compare_images(a, b); a.save(out_dir / f"ours_{i}.png"); (b if not c["resized"] else b.resize(a.size, Image.LANCZOS)).save(out_dir / f"yours_{i}.png"); heat.save(out_dir / f"diff_{i}.png")
        frames.append({"i": i, "at": at, **c}); worst = max(worst or 0, c["mean_diff"])
    return {"kind": kind, "figures": {"mean_diff": worst, "noise_floor": floor, "hash_on_record": bool(entry.get("pixels_sha256")), "identical": same, "compared_against": "our web copy, which is smaller and compressed; the hash is of our original"}, "verdict": verdict(same, worst, floor), "frames": frames}


def diff_graphs(ours, yours) -> list:
    """What changed between two API graphs, input by input."""
    rows = []
    for nid in sorted(set(ours) | set(yours), key=str):
        a, b = ours.get(nid), yours.get(nid)
        if a is None or b is None: rows.append({"node": nid, "input": "(whole node)", "ours": (a or {}).get("class_type"), "yours": (b or {}).get("class_type")}); continue
        ia, ib = a.get("inputs") or {}, b.get("inputs") or {}
        for k in sorted(set(ia) | set(ib)):
            if ia.get(k) != ib.get(k):
                carried = isinstance(ib.get(k), str) and re.fullmatch(r"studio_[0-9a-f]{10}\.\w+", ib[k]) is not None
                rows.append({"node": nid, "class": a.get("class_type"), "input": k, "ours": ia.get(k), "yours": ib.get(k), "note": "The file handed on from an earlier step. Its name is its hash, so it changes whenever that step's output does." if carried else ""})
    return rows


# ---------- what a render's page says ----------
def provable(rid: str, entry) -> tuple:
    if not entry: return False, "We have no record of this render."
    if not entry.get("seeds") and not any(s.get("seed") is not None for s in entry.get("steps") or []): return False, "No seed was recorded for this render, so a re-run could not show anything."
    if entry.get("uploads"): return False, "This render started from a sample file we do not ship, so its exact graph cannot run on your machine. Run the recipe with your own file instead."
    return True, ""


def card(rid: str, start_hash=False) -> dict:
    from studio import recipes as R
    rec = R.find(rid); x = R.renders().get(rid); entry = data()["renders"].get(rid)
    if not rec or not x: raise HTTPException(404, "no render of ours for this recipe")
    ok, why = provable(rid, entry); e = entry or {}
    return {"source": "recipe", "id": rid, "title": rec.get("title"), "kind": x["kind"], "file": x.get("file"), "poster": x.get("poster"), "seeds": e.get("seeds") or x.get("seeds"), "seconds": x.get("seconds"), "peak_vram_gib": x.get("peak_vram_gib"), "peak_scope": x.get("peak_scope"), "rendered": x.get("rendered"), "graphs_kept": bool(e.get("graphs_kept")),
            "provable": ok, "why": why, "promise": NOT_A_PROMISE, "steps": [{"id": s["id"], "label": s.get("label"), "type": s.get("type"), "seed": s.get("seed"), "has_graph": bool(s.get("graph")), "graph_hash": s.get("graph_hash")} for s in e.get("steps") or []],
            "models": [model_row(n, data()["models"].get(n), start=start_hash) for n in models_of(e)], "hardware": hardware_rows(data().get("hardware") or {}, your_hardware()), "hardware_captured": (data().get("hardware") or {}).get("captured"), "noise_floor": e.get("noise_floor"), "same_machine": same_machine(), "last_proof": last_proof(rid)}


def last_proof(rid: str):
    """The newest proof of this render, so a reload does not lose it."""
    best, when = None, 0
    try:
        for p in state_dir().glob("*/proof.json"):
            try: d = json.loads(p.read_text())
            except ValueError: continue
            if d.get("recipe") == rid and d.get("created", 0) > when: best, when = d["id"], d["created"]
    except OSError: pass
    return best


@router.get("/recipe/{rid}")
def get_recipe(rid: str): return card(rid)


@router.get("/showcase/{sid}")
def get_showcase(sid: str):
    try: rows = json.loads(SHOWCASE.read_text(encoding="utf-8"))
    except OSError: rows = []
    x = next((r for r in rows if r.get("id") == sid), None)
    if not x: raise HTTPException(404, "no such showcase render")
    return {"source": "showcase", "id": sid, "title": "A showcase render", "prompt": x.get("prompt"), "kind": x.get("kind"), "file": x.get("src"), "poster": x.get("poster"), "seconds": x.get("seconds"), "peak_vram_gib": x.get("peak_vram_gib"), "seeds": None, "provable": False, "promise": NOT_A_PROMISE, "steps": [], "models": [], "hardware": hardware_rows(data().get("hardware") or {}, your_hardware()),
            "why": "We did not keep the seed of this render when it was made, so a re-run could only show a different picture. We would rather say so than show you a comparison that means nothing. Every recipe render below has its seed on record."}


@router.get("/renders")
def renders_list(q: str = "", limit: int = 24):
    """Renders that can be proved, for the page's picker."""
    from studio import recipes as R
    q = q.strip().lower(); out = []
    for rid, x in R.renders().items():
        e = data()["renders"].get(rid); ok, _ = provable(rid, e)
        if not ok: continue
        r = R.find(rid) or {}
        if q and q not in (str(r.get("title")) + " " + rid + " " + x["kind"]).lower(): continue
        out.append({"id": rid, "title": r.get("title") or rid, "kind": x["kind"], "poster": x.get("poster") or (x.get("file") if x["kind"] in ("image", "picture") else None), "seconds": x.get("seconds")})
    return {"renders": out[:max(1, min(limit, 60))], "total": len(out)}


# ---------- running it ----------
def _proof_path(pid: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{12}", pid or ""): raise HTTPException(404, "no such proof")
    return state_dir() / pid / "proof.json"


def _load(pid: str) -> dict:
    p = _proof_path(pid)
    if not p.is_file(): raise HTTPException(404, "no such proof")
    return json.loads(p.read_text())


def _save(d: dict) -> None:
    p = _proof_path(d["id"]); p.parent.mkdir(parents=True, exist_ok=True); tmp = p.with_suffix(".part"); tmp.write_text(json.dumps(d)); os.replace(tmp, p)


@router.post("/recipe/{rid}/start")
def start(rid: str, b: dict):
    """Starts the render. Only ever from a click: the page sends confirm, and nothing here runs on its own."""
    if b.get("confirm") is not True: raise HTTPException(400, "Prove It only runs when you press the button.")
    from studio import recipes as R, backends
    if backends.use_sdk(): raise HTTPException(400, "This studio is sending graphs to a cloud service. Prove It compares your own machine, so switch to local first.")
    rec, entry = R.find(rid), data()["renders"].get(rid); ok, why = provable(rid, entry)
    if not rec: raise HTTPException(404, "no such recipe")
    if not ok: raise HTTPException(409, why)
    r = R.recipe_run(rid, R.RunReq(values=entry.get("values") or {}, uploads={}, seed_add=int(entry.get("seed_add") or 0)))     # a recipe that cannot run here says why, with a 409
    d = {"id": uuid.uuid4().hex[:12], "recipe": rid, "run": r["run"], "created": time.time(), "state": "running", "report": None}; _save(d); return d


def _output_path(run: dict):
    """The local file of a finished run's final output, wherever the runner left it."""
    from studio import recipes as R
    o = run.get("output") or {}; url = str(o.get("url") or ""); name = o.get("filename") or ""
    if url.startswith("/api/recipes/files/"): return R._root() / run["run"] / name
    q = dict(urllib.parse.parse_qsl(url.split("?", 1)[1])) if "?" in url else {"filename": name}
    p = Path(paths.output_dir(True)) / q.get("subfolder", "") / q.get("filename", name)
    if p.is_file(): return p
    keep = R._root() / run["run"] / q.get("filename", name)
    if not keep.is_file():
        with urllib.request.urlopen(_comfy_url() + "/view?" + urllib.parse.urlencode({"filename": q.get("filename", name), "subfolder": q.get("subfolder", ""), "type": q.get("type", "output")}), timeout=300) as r: keep.write_bytes(r.read())
    return keep


def build_report(d: dict, run: dict) -> dict:
    from studio import recipes as R
    entry = data()["renders"][d["recipe"]]; x = R.renders()[d["recipe"]]; steps = []
    for st in entry.get("steps") or []:
        mine = next((s for s in run.get("steps") or [] if s["id"] == st["id"]), {}); g = None
        try: g = json.loads((R._root() / run["run"] / f"{st['id']}.graph.json").read_text())
        except (OSError, ValueError): pass
        ch = diff_graphs(st["graph"], g) if st.get("graph") and g else None
        steps.append({"id": st["id"], "label": st.get("label"), "seed_ours": st.get("seed"), "seed_yours": mine.get("seed"), "graph": "not on record" if not st.get("graph") else "not kept on your side" if g is None else "same" if not ch else "different", "changes": (ch or [])[:40], "graph_hash_ours": st.get("graph_hash"), "graph_hash_yours": mine.get("graph_hash")})
    cmp = compare_files(x["kind"], HERE / "web" / x["file"], _output_path(run), entry, state_dir() / d["id"])
    return {**cmp, "steps": steps, "seconds_yours": run.get("seconds"), "seconds_ours": x.get("seconds"), "peak_yours": run.get("peak_vram_gib"), "peak_ours": x.get("peak_vram_gib"), "peak_ours_scope": x.get("peak_scope"), "output_url": (run.get("output") or {}).get("url")}


@router.get("/runs/{pid}")
def status(pid: str):
    from studio import recipes as R
    d = _load(pid); run = R.get_run(d["run"]) or {}; card_now = card(d["recipe"], start_hash=True)
    if d["state"] == "running":
        st = run.get("status")
        if st == "done":
            try: d.update(state="done", report=build_report(d, run))
            except Exception as e: d.update(state="error", error=f"The render finished, but the two could not be compared: {type(e).__name__}: {str(e)[:200]}")
            _save(d)
        elif st in ("error", "cancelled", "interrupted"): d.update(state="error", error=run.get("error") or f"The run ended: {st}."); _save(d)
    return {**d, "run_status": run.get("status"), "position": run.get("position") or 0, "steps_now": [{k: s.get(k) for k in ("id", "label", "status")} for s in run.get("steps") or []], "card": card_now}


@router.post("/runs/{pid}/cancel")
def cancel(pid: str):
    from studio import recipes as R
    d = _load(pid); return R.recipe_run_cancel(d["recipe"], d["run"])


@router.get("/runs/{pid}/image/{name}")
def image(pid: str, name: str):
    _load(pid)
    if not re.fullmatch(r"(ours|yours|diff)_\d\.png", name): raise HTTPException(404, "no such image")
    p = state_dir() / pid / name
    if not p.is_file(): raise HTTPException(404, "no such image")
    return Response(p.read_bytes(), media_type="image/png")
