"""The Train page: pictures in, a trained LoRA out, and every number on the page read from the run itself.

The path is ComfyUI's own training nodes: LoadImageTextDataSetFromFolder -> MakeTrainingDataset -> TrainLoraNode -> SaveLoRA, with
PreviewAny turning the loss_map into text in /history, so the finished curve is the node's per-step list. While it runs, the curve comes
from the "Training LoRA" progress line in ComfyUI's /internal/logs/raw (sampled by tqdm, so not every step). Nothing here estimates,
smooths or fills a gap: a number that was not measured is sent as null and the page says so.

What TrainLoraNode really supports: nodes_train.py has no list of architectures. It adds adapters to every module with a weight_function
and needs model_sampling, so anything ComfyUI loads as a MODEL may run. A base is offered here only when its file is on disk, its
safetensors header shows float tensors (no quantized weights) and a real run is on record in train_measured.json or this box's own runs.
Mid-run checkpoints do not exist in the node: Cancel or a crash loses the steps of that run. Continue starts from a finished LoRA,
through the node's existing_lora input; the optimizer state is not saved, so it is a new run on top of old weights, not a resume.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from PIL import Image, ImageChops, ImageOps, ImageStat, UnidentifiedImageError

from psn import paths
from studio import sfw

router = APIRouter(prefix="/api/train")

BASES = {
    "sdxl-base-1.0": {"label": "Stable Diffusion XL base 1.0", "file": "sd_xl_base_1.0.safetensors", "arch": "SDXL", "sizes": [768, 1024], "needs": ("conditioner.embedders.1.", "model.diffusion_model.")},
    "sd-1.5": {"label": "Stable Diffusion 1.5", "file": "v1-5-pruned-emaonly.safetensors", "arch": "SD 1.5", "sizes": [512], "needs": ("cond_stage_model.", "model.diffusion_model.")},
}
RANKS = (4, 8, 16, 32)
BATCHES = (1, 2, 4)
LIMITS = {"steps": (1, 5000), "learning_rate": (1e-6, 1e-2), "seed": (0, 2**53)}
DEFAULTS = {"steps": 300, "rank": 8, "batch": 1, "learning_rate": 0.0005, "seed": 0}
MIN_PICTURES, FEW_PICTURES, MAX_PICTURES = 2, 10, 500
MAX_PICTURE_BYTES = 50 * 2**20
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
FLOAT_DTYPES = {"F16", "BF16", "F32", "F64"}
ACTIVE = ("preparing", "queued", "running", "cancelling")
INPUT_SUB = "parametric_train"     # under ComfyUI's input folder: LoadImageTextDataSetFromFolder cannot read anywhere else
OUTPUT_SUB = "parametric_train"    # under ComfyUI's output folder: where SaveLoRA has to write
LORA_SUB = "parametric_trained"    # under the loras folder
POLL_S = 1.5
VANISHED_S = 30.0
MAX_CURVE_POINTS = 600
AUTO_MONITOR = True                # tests drive _tick themselves
PROGRESS = re.compile(r"Training LoRA:\s*\d+%\|[^|]*\|\s*(\d+)/(\d+)\s*\[[^\]]*?loss=([-+0-9.eE]+|nan|inf)")
REFUSED = re.compile(r"\b(loli|lolita|lolicon|shota|shotacon|underage|preteen|jailbait)\b", re.I)    # on top of sfw.BAD, for every setting: there is no switch that turns this off
_lock = threading.RLock()
_monitors: dict = {}


def data_root() -> Path:
    return Path(os.environ.get("STUDIO_TRAIN_DIR") or Path.home() / ".local" / "share" / "parametric-studio" / "train")


def _ds_dir(ds_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{12}", ds_id or ""): raise HTTPException(404, "no such dataset")
    d = data_root() / "datasets" / ds_id
    if not d.is_dir(): raise HTTPException(404, "no such dataset")
    return d


def _job_path(job_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{12}", job_id or ""): raise HTTPException(404, "no such job")
    return data_root() / "jobs" / f"{job_id}.json"


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{uuid.uuid4().hex[:6]}")
    tmp.write_text(json.dumps(value, indent=1))
    os.replace(tmp, path)


def _load_job(job_id: str) -> dict:
    p = _job_path(job_id)
    if not p.exists(): raise HTTPException(404, "no such job")
    return json.loads(p.read_text())


def _save_job(job: dict) -> None:
    with _lock: _write_json(_job_path(job["id"]), job)


def _commit(job: dict) -> None:
    """Saves what a look at ComfyUI found, without undoing a Cancel pressed while it was looking."""
    with _lock:
        if job["state"] in ("queued", "running") and json.loads(_job_path(job["id"]).read_text()).get("state") == "cancelling": job["state"] = "cancelling"
        _save_job(job)


def _all_jobs() -> list[dict]:
    d = data_root() / "jobs"
    out = []
    if d.is_dir():
        for f in d.glob("*.json"):
            try: out.append(json.loads(f.read_text()))
            except ValueError: pass
    return sorted(out, key=lambda j: -j.get("created", 0))


# ---------- talking to ComfyUI ----------

def _comfy_url() -> str:
    return os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/")


def _comfy(path: str, payload=None, timeout: float = 30, raw: bool = False):
    req = urllib.request.Request(_comfy_url() + path, data=json.dumps(payload).encode() if payload is not None else None, headers={"Content-Type": "application/json"} if payload is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r: body = r.read()
    return body if raw else json.loads(body or b"{}")


def _gpu_used_gib():
    """What the whole card holds now: nvidia-smi if it is there, ComfyUI's own report if not. None when neither answers, and then no peak is reported."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip(): return round(float(out.stdout.split()[0]) / 1024, 2)
    except (OSError, ValueError, subprocess.SubprocessError): pass
    try:
        d = (_comfy("/system_stats", timeout=3).get("devices") or [{}])[0]
        if d.get("vram_total"): return round((d["vram_total"] - d.get("vram_free", 0)) / 2**30, 2)
    except Exception: pass
    return None


def _comfy_folder(name: str) -> list[str]:
    try: return [p for p in (_comfy("/internal/folder_paths", timeout=5).get(name) or []) if isinstance(p, str)]
    except Exception: return []


def _loras_dir() -> Path:
    """Inside a folder ComfyUI really lists for loras, or LoraLoader would not find the result. Prefers the models root, because /api/loras scans there."""
    root = os.path.realpath(paths.models_root(True))
    listed = _comfy_folder("loras")
    for p in listed:
        if os.path.realpath(p) == os.path.realpath(os.path.join(root, "loras")): return Path(p)
    if listed: return Path(listed[0])
    return Path(root) / "loras"


# ---------- word checks ----------

def flagged(*texts) -> bool:
    """sfw.check's word list, plus file-name forms: \\b does not fire between 'nude' and '_01', so names are read with separators turned into spaces."""
    for t in texts:
        if not t: continue
        plain = re.sub(r"[_\-.\d]+", " ", str(t))
        if sfw.flagged(t, plain) or REFUSED.search(str(t)) or REFUSED.search(plain): return True
    return False


# ---------- datasets ----------

def _images_dir(ds: Path) -> Path:
    return ds / "images"


def _meta(ds: Path) -> dict:
    return json.loads((ds / "dataset.json").read_text())


def _new_dataset(name: str) -> dict:
    name = (name or "").strip()[:80] or "Untitled pictures"
    if flagged(name): raise HTTPException(400, sfw.MESSAGE)
    ds_id = uuid.uuid4().hex[:12]
    ds = data_root() / "datasets" / ds_id
    _images_dir(ds).mkdir(parents=True)
    (ds / "thumbs").mkdir()
    meta = {"id": ds_id, "name": name, "created": time.time(), "items": {}}
    _write_json(ds / "dataset.json", meta)
    return meta


def _safe_name(name: str) -> str:
    base = os.path.basename((name or "").replace("\\", "/"))
    stem, ext = os.path.splitext(base)
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", stem).strip(" .") or "picture"
    return stem[:80] + ext.lower()


def _add_picture(ds: Path, meta: dict, name: str, data: bytes) -> str | None:
    """Keeps a picture only if PIL can really decode it. Returns the problem, or None."""
    if len(meta["items"]) >= MAX_PICTURES: return f"{name}: this set already holds {MAX_PICTURES} pictures"
    if len(data) > MAX_PICTURE_BYTES: return f"{name}: over 50 MB"
    fn = _safe_name(name)
    stem, ext = os.path.splitext(fn)
    if ext not in IMAGE_EXT: return f"{name}: png, jpg or webp only"
    tmp = _images_dir(ds) / f".in_{uuid.uuid4().hex[:8]}{ext}"
    tmp.write_bytes(data)
    try:
        with Image.open(tmp) as im:
            im.load()
            rgb = ImageOps.exif_transpose(im).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as e:
        tmp.unlink(missing_ok=True)
        return f"{name}: not a picture this can read ({type(e).__name__})"
    n, target = 1, fn
    while target in meta["items"] or (_images_dir(ds) / (os.path.splitext(target)[0] + ".txt")).exists():
        target = f"{stem}_{n}{ext}"; n += 1
    os.replace(tmp, _images_dir(ds) / target)
    thumb = rgb.copy(); thumb.thumbnail((320, 320)); thumb.save(ds / "thumbs" / (target + ".jpg"), quality=80)
    meta["items"][target] = {"width": rgb.width, "height": rgb.height, "sha256": hashlib.sha256(data).hexdigest(), "flat": ImageStat.Stat(rgb.convert("L").resize((64, 64))).stddev[0] < 4.0}
    return None


def _caption_path(ds: Path, file: str) -> Path:
    return _images_dir(ds) / (os.path.splitext(file)[0] + ".txt")


def _caption(ds: Path, file: str) -> str:
    p = _caption_path(ds, file)
    return p.read_text(encoding="utf-8", errors="replace").strip() if p.exists() else ""


def report(ds: Path, trigger: str = "", size: int | None = None) -> dict:
    """The caption check. 'block' stops Train, 'warn' does not. Says nothing about what a picture shows: nothing here can read a picture."""
    meta = _meta(ds)
    seen: dict = {}
    rows, blocks, warns = [], 0, 0
    for file, it in sorted(meta["items"].items()):
        cap = _caption(ds, file)
        problems = []
        add = lambda level, code, text: problems.append({"level": level, "code": code, "text": text})
        if not cap: add("block", "no_caption", "No caption. Write one, or use Fill empty captions.")
        if flagged(cap): add("block", "word_list", "The caption has a word outside this studio's safe-for-work list.")
        if flagged(file): add("block", "word_list", "The file name has a word outside this studio's safe-for-work list. Remove this picture or rename the file.")
        if cap and trigger and not re.search(rf"(?<!\w){re.escape(trigger)}(?!\w)", cap, re.I): add("warn", "no_trigger", "The trigger word is not in this caption.")
        if len(cap.split()) > 65: add("warn", "long_caption", f"{len(cap.split())} words. The text encoder cuts off near 75 tokens, so the end may be ignored.")
        if size and min(it["width"], it["height"]) < size: add("warn", "small", f"{it['width']} x {it['height']} is smaller than {size}, so it will be scaled up and soft.")
        if it.get("flat"): add("warn", "flat", "Almost one flat colour. It may be a failed render.")
        if it["sha256"] in seen: add("warn", "duplicate", f"The same file as {seen[it['sha256']]}.")
        else: seen[it["sha256"]] = file
        blocks += sum(p["level"] == "block" for p in problems); warns += sum(p["level"] == "warn" for p in problems)
        rows.append({"file": file, "caption": cap, "width": it["width"], "height": it["height"], "problems": problems, "thumb": f"/api/train/datasets/{meta['id']}/thumb/{urllib.parse.quote(file)}"})
    set_problems = []
    if len(rows) < MIN_PICTURES: set_problems.append({"level": "block", "code": "too_few", "text": f"Add at least {MIN_PICTURES} pictures."})
    elif len(rows) < FEW_PICTURES: set_problems.append({"level": "warn", "code": "few", "text": f"{len(rows)} pictures will train, but a LoRA from so few tends to copy them."})
    blocks += sum(p["level"] == "block" for p in set_problems); warns += sum(p["level"] == "warn" for p in set_problems)
    return {"id": meta["id"], "name": meta["name"], "created": meta["created"], "items": rows, "problems": set_problems, "blocks": blocks, "warns": warns, "ready": blocks == 0}


@router.get("/datasets")
def datasets():
    d = data_root() / "datasets"
    out = []
    if d.is_dir():
        for x in d.iterdir():
            try: m = json.loads((x / "dataset.json").read_text()); out.append({"id": m["id"], "name": m["name"], "created": m["created"], "pictures": len(m["items"])})
            except (OSError, ValueError, KeyError): pass
    return {"datasets": sorted(out, key=lambda r: -r["created"])}


@router.post("/datasets")
async def create_dataset(req: Request):
    b = await _body(req)
    return report_of(_new_dataset(b.get("name", ""))["id"])


def report_of(ds_id: str, trigger: str = "", size: int | None = None) -> dict:
    return report(_ds_dir(ds_id), trigger, size)


@router.get("/datasets/{ds_id}")
def get_dataset(ds_id: str, trigger: str = "", size: int | None = None):
    return report_of(ds_id, trigger.strip(), size)


@router.post("/datasets/{ds_id}/upload")
async def upload(ds_id: str, files: list[UploadFile] = File(...)):
    """Pictures and, optionally, .txt captions with the same names."""
    ds = _ds_dir(ds_id)
    loaded = [(f.filename or "", await f.read()) for f in files]
    return await run_in_threadpool(_store_uploads, ds, ds_id, loaded)


def _store_uploads(ds: Path, ds_id: str, loaded: list) -> dict:
    with _lock:
        meta, skipped = _meta(ds), []
        for name, data in sorted(loaded, key=lambda x: x[0].lower().endswith(".txt")):    # pictures first: a caption takes the name its picture ended up with
            if name.lower().endswith(".txt"): continue
            problem = _add_picture(ds, meta, name, data)
            if problem: skipped.append(problem)
        for name, data in loaded:
            if not name.lower().endswith(".txt"): continue
            stem = os.path.splitext(_safe_name(name))[0]
            match = next((f for f in meta["items"] if os.path.splitext(f)[0] == stem), None)
            if match: _caption_path(ds, match).write_text(data.decode("utf-8", "replace").strip(), encoding="utf-8")
            else: skipped.append(f"{name}: no picture has this name")
        _write_json(ds / "dataset.json", meta)
    return {**report_of(ds_id), "skipped": skipped}


def _import_roots() -> list[str]:
    roots = [os.path.expanduser("~"), paths.comfy_input(True), paths.output_dir(True)] + [x for x in os.environ.get("STUDIO_TRAIN_IMPORT_ROOTS", "").split(":") if x]
    return [os.path.realpath(r) for r in roots if r]


def _allowed_folder(folder: str) -> Path:
    """A folder on this machine. Only inside the home, ComfyUI's input and output folders, or STUDIO_TRAIN_IMPORT_ROOTS, and never through a hidden folder such as ~/.ssh. Only pictures and .txt files are ever read."""
    folder = os.path.expanduser((folder or "").strip())
    if not os.path.isabs(folder): raise HTTPException(400, "Give the full path of a folder on this machine.")
    real = os.path.realpath(folder)
    if not os.path.isdir(real): raise HTTPException(400, "That folder does not exist on this machine.")
    if any(real == r or real.startswith(r + os.sep) for r in _import_roots()):
        parts = Path(real).parts
        if not any(p.startswith(".") or p == "Private_Backups" for p in parts): return Path(real)
    raise HTTPException(403, "That folder is outside the places the studio reads from, or inside a hidden or private one. Copy the pictures into your home folder, or drop them on the page.")


@router.post("/datasets/{ds_id}/import")
async def import_folder(ds_id: str, req: Request):
    b = await _body(req)
    return await run_in_threadpool(_import_folder, ds_id, b.get("folder", ""))


def _import_folder(ds_id: str, folder: str) -> dict:
    ds = _ds_dir(ds_id)
    src = _allowed_folder(folder)
    picked, n = [], 0
    for f in sorted(src.iterdir()):
        if n >= MAX_PICTURES * 2: break
        if f.is_file() and not f.is_symlink() and f.suffix.lower() in IMAGE_EXT + (".txt",) and f.stat().st_size <= MAX_PICTURE_BYTES:
            picked.append((f.name, f.read_bytes())); n += 1
    if not any(not p[0].lower().endswith(".txt") for p in picked): raise HTTPException(400, "No png, jpg or webp pictures directly inside that folder.")
    return _store_uploads(ds, ds_id, picked)


@router.get("/datasets/{ds_id}/thumb/{file}")
def thumb(ds_id: str, file: str):
    ds = _ds_dir(ds_id)
    p = ds / "thumbs" / (_safe_name(file) + ".jpg")
    if not p.exists(): raise HTTPException(404, "no such picture")
    return FileResponse(p, media_type="image/jpeg")


@router.post("/datasets/{ds_id}/captions")
async def set_captions(ds_id: str, req: Request):
    """{"captions": {file: text}}. Saved even when flagged, so it can be fixed; the check then shows it and Train refuses."""
    ds, b = _ds_dir(ds_id), await _body(req)
    caps = b.get("captions")
    if not isinstance(caps, dict): raise HTTPException(400, "send captions as {file: text}")
    with _lock:
        items = _meta(ds)["items"]
        for file, text in caps.items():
            if file not in items: raise HTTPException(404, f"no picture called {file}")
            if not isinstance(text, str): raise HTTPException(400, "captions must be text")
            _caption_path(ds, file).write_text(text.strip(), encoding="utf-8")
    return report_of(ds_id, str(b.get("trigger") or ""), b.get("size"))


@router.post("/datasets/{ds_id}/fix")
async def fix(ds_id: str, req: Request):
    """add_trigger: put the trigger at the front of every caption that lacks it. fill_empty: give every empty caption this text. remove: drop one picture."""
    ds, b = _ds_dir(ds_id), await _body(req)
    action, trigger = b.get("action"), str(b.get("trigger") or "").strip()
    with _lock:
        meta = _meta(ds)
        if action == "add_trigger":
            _check_trigger(trigger)
            for file in meta["items"]:
                cap = _caption(ds, file)
                if not re.search(rf"(?<!\w){re.escape(trigger)}(?!\w)", cap, re.I): _caption_path(ds, file).write_text(f"{trigger}, {cap}" if cap else trigger, encoding="utf-8")
        elif action == "fill_empty":
            text = str(b.get("text") or "").strip()
            if not text: raise HTTPException(400, "Write the text to fill empty captions with.")
            for file in meta["items"]:
                if not _caption(ds, file): _caption_path(ds, file).write_text(text, encoding="utf-8")
        elif action == "remove":
            file = b.get("file")
            if file not in meta["items"]: raise HTTPException(404, "no such picture")
            del meta["items"][file]
            (_images_dir(ds) / file).unlink(missing_ok=True); _caption_path(ds, file).unlink(missing_ok=True); (ds / "thumbs" / (file + ".jpg")).unlink(missing_ok=True)
            _write_json(ds / "dataset.json", meta)
        else: raise HTTPException(400, "unknown fix")
    return report_of(ds_id, trigger, b.get("size"))


@router.delete("/datasets/{ds_id}")
def delete_dataset(ds_id: str):
    ds = _ds_dir(ds_id)
    if any(j.get("dataset") == ds_id and j.get("state") in ACTIVE for j in _all_jobs()): raise HTTPException(409, "A training job is using this set.")
    shutil.rmtree(ds)
    return {"ok": True}


# ---------- bases: what the code can prove ----------

def read_header(path) -> dict:
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        if n > 200 * 2**20: raise ValueError("header too large")
        return json.loads(f.read(n))


def header_verdict(header: dict, needs) -> str | None:
    """None when the file is what its entry claims and unquantized. The dtype of each tensor is in the file, so this is read, not assumed."""
    keys = [k for k in header if k != "__metadata__"]
    for prefix in needs:
        if not any(k.startswith(prefix) for k in keys): return f"its tensors do not match this architecture (no {prefix}*)"
    weights = [k for k in keys if k.startswith("model.diffusion_model.")]
    dtypes = {header[k].get("dtype") for k in weights}
    if not dtypes <= FLOAT_DTYPES: return f"its weights are not plain floats ({', '.join(sorted(str(d) for d in dtypes - FLOAT_DTYPES))})"
    if any("comfy_quant" in k or "scale_weight" in k for k in keys): return "it is quantized"
    return None


def _find_checkpoint(file: str) -> str | None:
    for root in _comfy_folder("checkpoints") or [os.path.join(paths.models_root(True), "checkpoints")]:
        p = os.path.join(root, file)
        if os.path.isfile(p): return p
    return None


def measurements() -> list[dict]:
    """Real runs only: the ones shipped with the studio (train_measured.json, each from a named run) and this box's own."""
    out = []
    shipped = Path(__file__).with_name("train_measured.json")
    if shipped.exists(): out += json.loads(shipped.read_text())
    mine = data_root() / "measured.jsonl"
    if mine.exists():
        for line in mine.read_text().splitlines():
            try: out.append(json.loads(line))
            except ValueError: pass
    return out


def base_status(object_info: dict | None) -> list[dict]:
    rows = []
    options = checkpoint_options(object_info) if object_info else None
    runs = measurements()
    for base_id, b in BASES.items():
        why = None
        if options is None: why = "ComfyUI is not reachable, so nothing can be checked."
        elif b["file"] not in options: why = f"{b['file']} is not installed."
        path = _find_checkpoint(b["file"]) if not why else None
        if not why and not path: why = f"ComfyUI lists {b['file']}, but the studio cannot read it to check it."
        if path:
            try: verdict = header_verdict(read_header(path), b["needs"])
            except (OSError, ValueError, struct.error) as e: verdict = f"its header cannot be read ({type(e).__name__})"
            if verdict: why = f"{b['file']} cannot be used: {verdict}."
        proved = [r for r in runs if r.get("base") == base_id and r.get("steps")]
        proving = not proved and os.environ.get("STUDIO_TRAIN_PROVE") == base_id     # the one way a base gets its first run; set by hand, and the page says so
        if not why and not proved and not proving: why = "No training run on record for this base, so the studio will not offer it yet."
        rows.append({"id": base_id, "label": b["label"], "file": b["file"], "arch": b["arch"], "sizes": b["sizes"], "trainable": why is None, "why_not": why, "proof": _proof_line(proved[-1]) if proved else "Not proved yet: STUDIO_TRAIN_PROVE is set, so this run is the test." if proving else None})
    return rows


def _card(name: str | None) -> str:
    """ComfyUI names a device 'cuda:0 NVIDIA X : cudadevice'. This is the card's name inside that."""
    return re.sub(r"^\S+:\d+\s+|\s*:\s*\S+$", "", name or "").strip()


def _proof_line(r: dict) -> str:
    return f"Proved by a real run: {r['steps']} steps at {r['size']} px, rank {r['rank']}, on {_card(r.get('gpu')) or 'an unnamed GPU'} ({r.get('date', 'date not recorded')})."


def checkpoint_options(info: dict) -> list:
    spec = (((info.get("CheckpointLoaderSimple") or {}).get("input") or {}).get("required") or {}).get("ckpt_name") or [[]]
    if spec and spec[0] == "COMBO": return (spec[1] or {}).get("options", [])
    return spec[0] if isinstance(spec[0], list) else []


def _gpu_name() -> str | None:
    try: return (_comfy("/system_stats", timeout=3).get("devices") or [{}])[0].get("name")
    except Exception: return None


def _same_card(a: str | None, b: str | None) -> bool:
    return bool(a and b) and _card(a).lower() == _card(b).lower()


def estimate(base: str, size, rank, batch, steps, gpu: str | None = None) -> dict:
    """From measured runs on this same card, at this size and batch, or nothing. No scaling formula: a number that was not measured does not appear."""
    runs = [r for r in measurements() if r.get("base") == base and r.get("s_per_step")]
    if not runs: return {"measured": False, "note": "No run of this base is on record, so there is no time or VRAM figure. The first run measures it."}
    here = [r for r in runs if _same_card(r.get("gpu"), gpu)]
    if not here: return {"measured": False, "note": f"Measured only on {_card(runs[-1].get('gpu')) or 'another card'}. No figure for this card until it has run once here."}
    close = [r for r in here if r.get("size") == size and r.get("batch") == batch]
    if not close: return {"measured": False, "note": f"No run on this card at {size} px, batch {batch}. The first run measures it."}
    exact = [r for r in close if r.get("rank") == rank]
    r = (exact or close)[-1]
    return {"measured": True, "exact": bool(exact), "s_per_step": r["s_per_step"], "train_seconds": round(r["s_per_step"] * steps), "setup_seconds": r.get("setup_seconds"), "peak_vram_gib": r.get("peak_vram_gib"), "from": {"steps": r["steps"], "rank": r["rank"], "date": r.get("date"), "gpu": r.get("gpu")},
            "note": "Measured on this card at these settings." if exact else f"Measured on this card at rank {r['rank']}, not rank {rank}, so treat it as a close guide."}


# ---------- the graphs ----------

def training_graph(ckpt: str, folder: str, steps: int, rank: int, batch: int, learning_rate: float, seed: int, prefix: str, existing_lora: str = "[None]") -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "2": {"class_type": "LoadImageTextDataSetFromFolder", "inputs": {"folder": folder}},
        "3": {"class_type": "MakeTrainingDataset", "inputs": {"images": ["2", 0], "texts": ["2", 1], "vae": ["1", 2], "clip": ["1", 1]}},
        "4": {"class_type": "TrainLoraNode", "inputs": {"model": ["1", 0], "latents": ["3", 0], "positive": ["3", 1], "batch_size": batch, "grad_accumulation_steps": 1, "steps": steps, "learning_rate": learning_rate, "rank": rank, "optimizer": "AdamW", "loss_function": "MSE", "seed": seed, "training_dtype": "bf16", "lora_dtype": "bf16", "quantized_backward": False, "algorithm": "LoRA", "gradient_checkpointing": True, "checkpoint_depth": 1, "offloading": False, "existing_lora": existing_lora, "bucket_mode": False, "bypass_mode": False}},
        "5": {"class_type": "SaveLoRA", "inputs": {"lora": ["4", 0], "prefix": prefix, "steps": ["4", 2]}},
        "6": {"class_type": "PreviewAny", "inputs": {"source": ["4", 1]}},
    }


def ab_graph(ckpt: str, lora_name: str, prompt: str, negative: str, width: int, height: int, seed: int, strength: float, prefix: str, steps: int = 25, cfg: float = 7.0) -> dict:
    """The same seed through the same sampler, once on the base and once with the LoRA."""
    sampler = lambda model: {"model": model, "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "normal", "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0], "denoise": 1.0}
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": lora_name, "strength_model": strength}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": sampler(["1", 0])},
        "7": {"class_type": "KSampler", "inputs": sampler(["2", 0])},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix + "/base"}},
        "11": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix + "/lora"}},
    }


def validate_graph(graph: dict, info: dict) -> list[str]:
    """Every node exists, every required input is there, every link joins matching types and every value fits its widget, all read from /object_info."""
    problems = []
    for nid, node in graph.items():
        cls = node.get("class_type"); spec = info.get(cls)
        if spec is None: problems.append(f"node {nid}: {cls} is not installed"); continue
        req, opt = (spec.get("input") or {}).get("required") or {}, (spec.get("input") or {}).get("optional") or {}
        for name in req:
            if name not in node["inputs"]: problems.append(f"node {nid} {cls}: missing {name}")
        for name, val in node["inputs"].items():
            want = req.get(name) or opt.get(name)
            if want is None: problems.append(f"node {nid} {cls}: no input called {name}"); continue
            kind, cfg = want[0], want[1] if len(want) > 1 and isinstance(want[1], dict) else {}
            if isinstance(val, list):
                src = graph.get(str(val[0]))
                if src is None: problems.append(f"node {nid} {cls}: {name} links to missing node {val[0]}"); continue
                outs = (info.get(src["class_type"]) or {}).get("output") or []
                if val[1] >= len(outs): problems.append(f"node {nid} {cls}: {name} links to output {val[1]} of {src['class_type']}, which has {len(outs)}"); continue
                if kind != "*" and outs[val[1]] != "*" and outs[val[1]] != kind: problems.append(f"node {nid} {cls}: {name} wants {kind}, gets {outs[val[1]]}")
                continue
            options = cfg.get("options") if kind == "COMBO" else kind if isinstance(kind, list) else None
            if options is not None:
                if val not in options: problems.append(f"node {nid} {cls}: {name} = {val!r} is not an option")
            elif kind in ("INT", "FLOAT"):
                if isinstance(val, bool) or not isinstance(val, (int, float)) or (kind == "INT" and not isinstance(val, int)): problems.append(f"node {nid} {cls}: {name} must be {kind}")
                elif ("min" in cfg and val < cfg["min"]) or ("max" in cfg and val > cfg["max"]): problems.append(f"node {nid} {cls}: {name} = {val} is out of range")
            elif kind == "BOOLEAN" and not isinstance(val, bool): problems.append(f"node {nid} {cls}: {name} must be true or false")
            elif kind == "STRING" and not isinstance(val, str): problems.append(f"node {nid} {cls}: {name} must be text")
    return problems


# ---------- starting a job ----------

async def _body(req: Request) -> dict:
    try: b = await req.json()
    except ValueError: raise HTTPException(400, "send a JSON object") from None
    if not isinstance(b, dict): raise HTTPException(400, "send a JSON object")
    return b


def _check_trigger(trigger: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,39}", trigger or ""): raise HTTPException(400, "The trigger is one word of 2 to 40 letters and numbers, for example brasslight.")
    if flagged(trigger): raise HTTPException(400, sfw.MESSAGE)


def _whole(value, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high: raise HTTPException(400, f"{name} must be a whole number from {low} to {high}.")
    return value


def settings_from(b: dict, base: dict) -> dict:
    s = {**DEFAULTS, **{k: b[k] for k in ("steps", "rank", "batch", "learning_rate", "seed") if b.get(k) is not None}}
    s["size"] = b.get("size", base["sizes"][-1])
    if s["size"] not in base["sizes"]: raise HTTPException(400, f"Size must be one of {base['sizes']} for this base.")
    if s["rank"] not in RANKS: raise HTTPException(400, f"Rank must be one of {list(RANKS)}.")
    if s["batch"] not in BATCHES: raise HTTPException(400, f"Batch must be one of {list(BATCHES)}.")
    _whole(s["steps"], "Steps", *LIMITS["steps"]); _whole(s["seed"], "Seed", *LIMITS["seed"])
    lr = s["learning_rate"]
    if isinstance(lr, bool) or not isinstance(lr, (int, float)) or not LIMITS["learning_rate"][0] <= lr <= LIMITS["learning_rate"][1]: raise HTTPException(400, f"Learning rate must be from {LIMITS['learning_rate'][0]} to {LIMITS['learning_rate'][1]}.")
    s["learning_rate"] = float(lr)
    return s


def prepare(ds: Path, folder: Path, size: int) -> int:
    """The copy ComfyUI reads: every picture centre-cropped and scaled to one square size, numbered, with its caption beside it. Originals stay as they are."""
    meta = _meta(ds)
    folder.mkdir(parents=True, exist_ok=True)
    for i, file in enumerate(sorted(meta["items"]), 1):
        with Image.open(_images_dir(ds) / file) as im:
            ImageOps.fit(ImageOps.exif_transpose(im).convert("RGB"), (size, size), Image.LANCZOS).save(folder / f"{i:05d}.png")
        (folder / f"{i:05d}.txt").write_text(_caption(ds, file), encoding="utf-8")
    return len(meta["items"])


def _prompt(graph: dict) -> str:
    try: res = _comfy("/prompt", {"prompt": graph, "client_id": "studio-train"})
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read() or b"{}")
        except ValueError: body = {}
        err = body.get("error") if isinstance(body, dict) else None
        nodes = "; ".join(f"{k}: " + ", ".join(str(x.get("message", "")) + " " + str(x.get("details", "")) for x in v.get("errors", [])) for k, v in list((body.get("node_errors") or {}).items())[:3]) if isinstance(body, dict) else ""
        raise HTTPException(400, f"ComfyUI rejected the graph: {(err or {}).get('message', '') if isinstance(err, dict) else err} {nodes}".strip()) from None
    except OSError: raise HTTPException(503, "ComfyUI is not reachable.") from None
    if not isinstance(res, dict) or not res.get("prompt_id"): raise HTTPException(502, "ComfyUI did not return a job.")
    return res["prompt_id"]


@router.post("/jobs")
async def start(req: Request):
    return await run_in_threadpool(_start, await _body(req))


def _active() -> dict | None:
    return next((j for j in _all_jobs() if j.get("state") in ACTIVE), None)


def _start(b: dict) -> dict:
    if b.get("rights_confirmed") is not True: raise HTTPException(400, "Tick the box first: you own these pictures or have the rights to them, and no real person's likeness is being trained without their consent.")
    name, trigger = str(b.get("name") or "").strip(), str(b.get("trigger") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,39}", name): raise HTTPException(400, "Give the LoRA a name: up to 40 letters, numbers, spaces and dashes.")
    if flagged(name): raise HTTPException(400, sfw.MESSAGE)
    _check_trigger(trigger)
    base_id = b.get("base")
    if base_id not in BASES: raise HTTPException(400, "Pick a base from the list.")
    base = BASES[base_id]
    settings = settings_from(b, base)
    ds = _ds_dir(str(b.get("dataset") or ""))
    rep = report(ds, trigger, settings["size"])
    if not rep["ready"]: raise HTTPException(400, f"The picture set has {rep['blocks']} problem(s) to fix first. See the caption check.")
    with _lock:
        running = _active()
        if running: raise HTTPException(409, f"{running['name']} is training. One training job at a time: it holds the GPU.")
        try: info = _comfy("/object_info", timeout=30)
        except Exception: raise HTTPException(503, "ComfyUI is not reachable.") from None
        status = next(r for r in base_status(info) if r["id"] == base_id)
        if not status["trainable"]: raise HTTPException(400, status["why_not"])
        existing = "[None]"
        parent = None
        if b.get("continue_from"):
            parent = _load_job(str(b["continue_from"]))
            if parent.get("state") != "done" or parent.get("base") != base_id or not os.path.isfile((parent.get("lora") or {}).get("path", "")): raise HTTPException(400, "Continue needs a finished LoRA of this same base.")
            existing = parent["lora"]["name"]
        job_id = uuid.uuid4().hex[:12]
        in_dir = Path(paths.comfy_input(True))
        if not in_dir.is_dir(): raise HTTPException(503, "The studio cannot find ComfyUI's input folder on this machine, which training needs. Set STUDIO_COMFY_INPUT.")
        folder_rel = f"{INPUT_SUB}/{job_id}"
        pictures = prepare(ds, in_dir / folder_rel, settings["size"])
        graph = training_graph(base["file"], folder_rel, settings["steps"], settings["rank"], settings["batch"], settings["learning_rate"], settings["seed"], f"{OUTPUT_SUB}/{job_id}/lora", existing)
        try:
            info = _comfy("/object_info/LoadImageTextDataSetFromFolder", timeout=15) | {k: v for k, v in info.items() if k != "LoadImageTextDataSetFromFolder"}    # the folder list changed a moment ago
            problems = validate_graph(graph, info)
            if problems: raise HTTPException(400, "The graph does not fit this ComfyUI: " + "; ".join(problems[:4]))
            prompt_id = _prompt(graph)
        except Exception:
            shutil.rmtree(in_dir / folder_rel, ignore_errors=True)
            raise
        job = {"id": job_id, "kind": "train", "name": name, "trigger": trigger, "base": base_id, "base_file": base["file"], "settings": settings, "dataset": rep["id"], "dataset_name": rep["name"], "pictures": pictures, "continue_from": parent["id"] if parent else None, "prior_steps": (parent["lora"].get("total_steps") or 0) if parent else 0,
               "rights": {"confirmed": True, "at": time.time(), "text": "Owns or has rights to the pictures; no real person's likeness trained without consent."},
               "prompt_id": prompt_id, "graph": graph, "state": "queued", "created": time.time(), "submitted_iso": datetime.datetime.now().isoformat(), "running_at": None, "ended": None, "position": None, "last_seen": time.time(),
               "curve": [], "curve_source": None, "peak_vram_gib": None, "vram_before_gib": _gpu_used_gib(), "loss_nan": False, "lora": None, "error": None, "ab": None, "gpu": _gpu_name()}
        _save_job(job)
    _ensure_monitor(job_id)
    return view_job(job)


# ---------- following a job ----------

def parse_progress(entries, since_iso: str) -> list[list]:
    """[step, total, loss or None, t] for every 'Training LoRA' line ComfyUI logged since the job was sent. The numbers are copied from the line."""
    out = []
    for e in entries or []:
        t, m = e.get("t", ""), e.get("m", "")
        if t < since_iso or "Training LoRA" not in m: continue
        hit = PROGRESS.search(m)
        if not hit: continue
        try: when = datetime.datetime.fromisoformat(t).timestamp()
        except ValueError: continue
        raw = hit.group(3)
        out.append([int(hit.group(1)), int(hit.group(2)), float(raw), when])
    return out


def measured_speed(curve: list) -> float | None:
    """Seconds per step from the last stretch of real log lines. None until two different steps have been seen."""
    tail = curve[-40:]
    if len(tail) < 2 or tail[-1][0] <= tail[0][0] or tail[-1][2] <= tail[0][2]: return None
    return (tail[-1][2] - tail[0][2]) / (tail[-1][0] - tail[0][0])


def _follow_logs(job: dict) -> None:
    try: entries = _comfy("/internal/logs/raw", timeout=5).get("entries")
    except Exception: return
    last = job["curve"][-1][0] if job["curve"] else -1
    for step, total, loss, when in parse_progress(entries, job["submitted_iso"]):
        if total != job["settings"]["steps"] or step <= last: continue
        job["curve"].append([step, loss, when]); last = step
        job["curve_source"] = "live log"
        if loss != loss or loss in (float("inf"), float("-inf")): job["loss_nan"] = True


def _history_entry(prompt_id: str):
    return _comfy(f"/history/{urllib.parse.quote(prompt_id)}", timeout=15).get(prompt_id)


def _tick(job_id: str) -> dict:
    """One look at ComfyUI. Everything the page shows is decided here, from what ComfyUI answered."""
    job = _load_job(job_id)
    if job["state"] not in ACTIVE: return job
    try:
        hist = _history_entry(job["prompt_id"])
        if hist is None or not _ended(hist):
            q = _comfy("/queue", timeout=5)
            running = any(len(e) > 1 and e[1] == job["prompt_id"] for e in q.get("queue_running", []))
            pending = [i for i, e in enumerate(q.get("queue_pending", [])) if len(e) > 1 and e[1] == job["prompt_id"]]
            job["others_running"] = 0 if running else len(q.get("queue_running", []))
            if not running and not pending: hist = _history_entry(job["prompt_id"])    # it may have ended between the two questions
    except Exception:
        job["unreachable"] = True
        _commit(job)
        return job
    job["unreachable"] = False
    if hist is not None and _ended(hist):
        _finish(job, hist)
    elif running:
        if job["state"] != "cancelling": job["state"] = "running"
        job["running_at"] = job["running_at"] or time.time()
        job["position"] = 0
        job["last_seen"] = time.time()
        _follow_logs(job)
        used = _gpu_used_gib()
        if used is not None: job["peak_vram_gib"] = max(job["peak_vram_gib"] or 0, used)
    elif pending:
        if job["state"] != "cancelling": job["state"] = "queued"
        job["position"] = pending[0] + 1
        job["last_seen"] = time.time()
    elif job["state"] == "cancelling":                                                 # taken out of the queue before it started: ComfyUI keeps no history for that
        _close(job, "cancelled", None)
    elif time.time() - job["last_seen"] > VANISHED_S:
        _close(job, "lost", "ComfyUI no longer knows this job, most likely because it restarted. Nothing is running for it and no LoRA was saved.")
    _commit(job)
    return job


def _ended(hist: dict) -> bool:
    st = hist.get("status") or {}
    return bool(st.get("completed") or st.get("status_str") in ("success", "error"))


def _close(job: dict, state: str, error: str | None) -> None:
    job["state"], job["error"], job["ended"] = state, error, time.time()
    shutil.rmtree(Path(paths.comfy_input(True)) / INPUT_SUB / job["id"], ignore_errors=True)


def _finish(job: dict, hist: dict) -> None:
    messages = (hist.get("status") or {}).get("messages") or []
    if any(k == "execution_interrupted" for k, *_ in messages):
        _close(job, "cancelled", None)
        return
    if (hist.get("status") or {}).get("status_str") == "error":
        msg = next((i.get("exception_message", "") for k, i in messages if k == "execution_error"), "")
        _close(job, "error", (msg or "ComfyUI reported an error and gave no message.").strip()[:600])
        return
    _follow_logs(job)
    losses = read_loss_map(hist)
    if losses is not None:
        first_seen = job["curve"][0] if job["curve"] else None
        speed = measured_speed(job["curve"])
        job["speed_from_log"] = speed
        job["first_step_at"] = first_seen[2] if first_seen else None
        job["curve"] = [[i + 1, v, None] for i, v in enumerate(losses)]
        job["curve_source"] = "loss_map"
        job["loss_nan"] = any(v != v or v in (float("inf"), float("-inf")) for v in losses)
    else:
        job["speed_from_log"] = measured_speed(job["curve"])
    if not job["curve"]:
        _close(job, "error", "ComfyUI said the run finished, but neither its log nor its output had a single loss value. Treating it as failed.")
        return
    try: job["lora"] = _collect_lora(job)
    except FileNotFoundError as e:
        _close(job, "error", str(e))
        return
    _close(job, "done", None)
    _record_measurement(job)
    _forget_lora_cache()


def read_loss_map(hist: dict) -> list[float] | None:
    """The list TrainLoraNode built, as PreviewAny printed it. None when it is absent or not numbers: the live log samples then stand, marked as samples."""
    for out in (hist.get("outputs") or {}).values():
        for text in out.get("text") or []:
            try: v = json.loads(text)
            except (TypeError, ValueError): continue
            if isinstance(v, dict) and isinstance(v.get("loss"), list) and v["loss"] and all(isinstance(x, (int, float)) for x in v["loss"]): return [float(x) for x in v["loss"]]
    return None


def _collect_lora(job: dict) -> dict:
    """SaveLoRA writes under ComfyUI's output folder and reports nothing, so the file is looked for under this job's own prefix. If it is not there the job failed: no path is ever made up."""
    out_dir = Path(paths.output_dir(True)) / OUTPUT_SUB / job["id"]
    found = sorted(out_dir.glob("lora*_steps_*.safetensors")) if out_dir.is_dir() else []
    if not found: raise FileNotFoundError(f"The run finished, but SaveLoRA's file is not in {out_dir}.")
    src = found[-1]
    header = read_header(src)
    keys = [k for k in header if k != "__metadata__"]
    if not any("lora_up" in k for k in keys): raise FileNotFoundError(f"{src.name} has no LoRA weights in it.")
    total = int(re.search(r"_(\d+)_steps_", src.name).group(1))
    slug = re.sub(r"[^a-z0-9]+", "-", job["name"].lower()).strip("-") or "lora"
    fname = f"{slug}_{BASES[job['base']]['arch'].lower().replace(' ', '').replace('.', '')}_{total}_steps_{job['id']}.safetensors"
    target_dir = _loras_dir() / LORA_SUB
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / fname
    tmp = target.with_name(target.name + ".part")
    shutil.copyfile(src, tmp)
    os.replace(tmp, target)
    digest = hashlib.sha256()
    with open(target, "rb") as f:
        for chunk in iter(lambda: f.read(2**20), b""): digest.update(chunk)
    shutil.rmtree(out_dir, ignore_errors=True)
    return {"name": f"{LORA_SUB}/{fname}", "path": str(target), "bytes": target.stat().st_size, "sha256": digest.hexdigest(), "tensors": len(keys), "total_steps": total}


def _record_measurement(job: dict) -> None:
    """A run becomes a figure the page may quote only if its speed was seen in the log."""
    s, speed = job["settings"], job.get("speed_from_log")
    if not speed: return
    setup = round(job["first_step_at"] - job["running_at"], 1) if job.get("first_step_at") and job.get("running_at") else None
    row = {"base": job["base"], "size": s["size"], "rank": s["rank"], "batch": s["batch"], "steps": s["steps"], "s_per_step": round(speed, 4), "setup_seconds": setup, "peak_vram_gib": job.get("peak_vram_gib"), "gpu": job.get("gpu"), "date": datetime.date.today().isoformat(), "run": job["id"]}
    p = data_root() / "measured.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(p, "a") as f: f.write(json.dumps(row) + "\n")


def _forget_lora_cache() -> None:
    try:
        from studio import loras
        loras._cache["data"] = None
    except Exception: pass


def _monitor(job_id: str) -> None:
    try:
        while True:
            job = _tick(job_id)
            ab_live = (job.get("ab") or {}).get("state") in ("queued", "running")
            if job["state"] not in ACTIVE and not ab_live: return
            if ab_live: _tick_ab(job_id)
            time.sleep(POLL_S)
    except HTTPException: pass
    finally:
        with _lock: _monitors.pop(job_id, None)


def _ensure_monitor(job_id: str) -> None:
    if not AUTO_MONITOR: return
    with _lock:
        t = _monitors.get(job_id)
        if t is not None and t.is_alive(): return
        t = threading.Thread(target=_monitor, args=(job_id,), daemon=True, name=f"train-{job_id}")
        _monitors[job_id] = t
        t.start()


def _thin(curve: list) -> list:
    """Real points only: at most MAX_CURVE_POINTS of them, every Nth, never averaged. The last is always kept."""
    if len(curve) <= MAX_CURVE_POINTS: return curve
    stride = len(curve) / MAX_CURVE_POINTS
    picked = [curve[int(i * stride)] for i in range(MAX_CURVE_POINTS)]
    if picked[-1] is not curve[-1]: picked[-1] = curve[-1]
    return picked


def view_job(job: dict) -> dict:
    """The page's copy: live numbers worked out from the job's own record. A null means not measured yet."""
    curve, steps = job.get("curve") or [], job["settings"]["steps"]
    step = curve[-1][0] if curve else 0
    finite = [c[1] for c in curve if c[1] == c[1] and abs(c[1]) != float("inf")]
    speed = (job.get("speed_from_log") if job["state"] == "done" else measured_speed(curve)) or None
    v = {k: x for k, x in job.items() if k not in ("graph", "curve")}
    if v.get("ab"): v["ab"] = {k: x for k, x in v["ab"].items() if k != "graph"}
    v["curve"] = [[c[0], c[1] if c[1] == c[1] and abs(c[1]) != float("inf") else None] for c in _thin(curve)]
    v["curve_points"] = len(curve)
    v["step"] = step
    v["total"] = steps
    v["last_loss"] = finite[-1] if finite else None
    v["s_per_step"] = round(speed, 4) if speed else None
    v["eta_s"] = round(speed * (steps - step)) if speed and job["state"] in ("running", "cancelling") else None
    if job["state"] in ("running", "cancelling") and job.get("running_at"): v["elapsed_s"] = round(time.time() - job["running_at"])
    elif job.get("ended") and job.get("running_at"): v["elapsed_s"] = round(job["ended"] - job["running_at"])
    else: v["elapsed_s"] = None
    return v


@router.get("/jobs")
def jobs():
    rows = _all_jobs()
    for j in rows:
        if j["state"] in ACTIVE or (j.get("ab") or {}).get("state") in ("queued", "running"): _ensure_monitor(j["id"])
    return {"jobs": [view_job(j) for j in rows[:50]]}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = _load_job(job_id)
    if job["state"] in ACTIVE or (job.get("ab") or {}).get("state") in ("queued", "running"): _ensure_monitor(job_id)
    return view_job(job)


@router.get("/jobs/{job_id}/graph")
def job_graph(job_id: str):
    return {"graph": _load_job(job_id)["graph"]}


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: str):
    job = _load_job(job_id)
    if job["state"] not in ACTIVE: return view_job(job)
    job["state"] = "cancelling"
    _save_job(job)
    try:
        _comfy("/queue", {"delete": [job["prompt_id"]]})
        if any(len(e) > 1 and e[1] == job["prompt_id"] for e in _comfy("/queue", timeout=5).get("queue_running", [])): _comfy("/interrupt", {"prompt_id": job["prompt_id"]})    # only this job: someone else's render keeps going
    except Exception: raise HTTPException(503, "ComfyUI is not reachable, so the job could not be cancelled.") from None
    _ensure_monitor(job_id)
    return view_job(job)


@router.post("/jobs/{job_id}/ab")
async def start_ab(job_id: str, req: Request):
    return await run_in_threadpool(_start_ab, job_id, await _body(req))


def _start_ab(job_id: str, b: dict) -> dict:
    job = _load_job(job_id)
    if job["state"] != "done" or not job.get("lora") or not os.path.isfile(job["lora"]["path"]): raise HTTPException(400, "A test render needs a finished LoRA whose file is still there.")
    prompt = str(b.get("prompt") or "").strip()
    if not prompt: raise HTTPException(400, "Write a test prompt.")
    if flagged(prompt): raise HTTPException(400, sfw.MESSAGE)
    seed = _whole(b.get("seed", 1234), "Seed", *LIMITS["seed"])
    strength = b.get("strength", 1.0)
    if isinstance(strength, bool) or not isinstance(strength, (int, float)) or not 0 < strength <= 2: raise HTTPException(400, "Strength must be above 0 and at most 2.")
    size = job["settings"]["size"]
    graph = ab_graph(job["base_file"], job["lora"]["name"], prompt, "", size, size, seed, float(strength), f"{OUTPUT_SUB}_ab/{job_id}_{uuid.uuid4().hex[:6]}")
    try: info = _comfy("/object_info", timeout=30)
    except Exception: raise HTTPException(503, "ComfyUI is not reachable.") from None
    problems = validate_graph(graph, info)
    if problems: raise HTTPException(400, "The test graph does not fit this ComfyUI: " + "; ".join(problems[:4]))
    job["ab"] = {"prompt_id": _prompt(graph), "state": "queued", "prompt": prompt, "seed": seed, "strength": float(strength), "base": None, "lora": None, "pixel_diff": None, "unbound_keys": None, "error": None, "submitted_iso": datetime.datetime.now().isoformat(), "graph": graph}
    _save_job(job)
    _ensure_monitor(job_id)
    return view_job(job)


def _image_ref(hist: dict, node: str) -> dict | None:
    for it in ((hist.get("outputs") or {}).get(node) or {}).get("images") or []:
        return {"filename": it["filename"], "subfolder": it.get("subfolder", ""), "type": it.get("type", "output"), "url": "/api/view?" + urllib.parse.urlencode({"filename": it["filename"], "subfolder": it.get("subfolder", ""), "type": it.get("type", "output")})}
    return None


def pixel_difference(a_bytes: bytes, b_bytes: bytes) -> float:
    """Mean absolute difference over all pixels and channels, 0 to 255, between the two real renders."""
    import io
    a, b = Image.open(io.BytesIO(a_bytes)).convert("RGB"), Image.open(io.BytesIO(b_bytes)).convert("RGB")
    if a.size != b.size: raise ValueError("the two renders differ in size")
    return round(sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3, 3)


def _tick_ab(job_id: str) -> dict:
    job = _load_job(job_id)
    ab = job.get("ab") or {}
    if ab.get("state") not in ("queued", "running"): return job
    try:
        hist = _history_entry(ab["prompt_id"])
        if hist is None or not _ended(hist):
            q = _comfy("/queue", timeout=5)
            ab["state"] = "running" if any(len(e) > 1 and e[1] == ab["prompt_id"] for e in q.get("queue_running", [])) else "queued"
            _save_job(job)
            return job
    except Exception: return job
    if (hist.get("status") or {}).get("status_str") == "error":
        messages = (hist.get("status") or {}).get("messages") or []
        ab.update(state="error", error=next((i.get("exception_message", "") for k, i in messages if k == "execution_error"), "The test render failed.")[:400] or "The test render failed.")
    else:
        ab["base"], ab["lora"] = _image_ref(hist, "10"), _image_ref(hist, "11")
        if not ab["base"] or not ab["lora"]:
            ab.update(state="error", error="ComfyUI finished without the two pictures.")
        else:
            ab["state"] = "done"
            try:
                fetch = lambda r: _comfy("/view?" + urllib.parse.urlencode({k: r[k] for k in ("filename", "subfolder", "type")}), raw=True, timeout=60)
                ab["pixel_diff"] = pixel_difference(fetch(ab["base"]), fetch(ab["lora"]))
            except Exception: ab["pixel_diff"] = None
            try:
                logged = _comfy("/internal/logs/raw", timeout=5).get("entries") or []
                ab["unbound_keys"] = sum("lora key not loaded" in e.get("m", "") for e in logged if e.get("t", "") >= ab["submitted_iso"])
            except Exception: ab["unbound_keys"] = None
    _save_job(job)
    return job


# ---------- the library and the page's opening data ----------

@router.get("/loras")
def trained():
    """Finished LoRAs whose file is really on disk. A job whose file has gone is not listed."""
    rows = []
    for j in _all_jobs():
        lo = j.get("lora") or {}
        if j.get("state") == "done" and lo.get("path") and os.path.isfile(lo["path"]):
            v = view_job(j)
            rows.append({"job": j["id"], "name": j["name"], "trigger": j["trigger"], "base": j["base"], "base_label": BASES[j["base"]]["label"], "lora_name": lo["name"], "bytes": lo["bytes"], "sha256": lo["sha256"], "total_steps": lo["total_steps"], "last_loss": v["last_loss"], "ended": j["ended"], "ab": {k: x for k, x in (j.get("ab") or {}).items() if k != "graph"} or None})
    return {"loras": rows}


@router.get("/info")
def info():
    try: object_info = _comfy("/object_info", timeout=20)
    except Exception: object_info = None
    out = {"comfy": object_info is not None, "comfy_url": _comfy_url(), "bases": base_status(object_info), "ranks": list(RANKS), "batches": list(BATCHES), "limits": LIMITS, "defaults": DEFAULTS, "queue": None, "gpu": None, "active": None}
    if object_info is not None:
        try:
            q = _comfy("/queue", timeout=5)
            out["queue"] = {"running": len(q.get("queue_running", [])), "pending": len(q.get("queue_pending", []))}
            d = (_comfy("/system_stats", timeout=5).get("devices") or [{}])[0]
            out["gpu"] = {"name": d.get("name"), "free_gib": round(d.get("vram_free", 0) / 2**30, 1), "total_gib": round(d.get("vram_total", 0) / 2**30, 1)}
        except Exception: pass
    act = _active()
    if act:
        _ensure_monitor(act["id"])
        out["active"] = act["id"]
    return out


@router.post("/estimate")
async def post_estimate(req: Request):
    b = await _body(req)
    if b.get("base") not in BASES: raise HTTPException(400, "Pick a base from the list.")
    return estimate(b["base"], b.get("size"), b.get("rank"), b.get("batch"), int(b.get("steps") or 0), _gpu_name())


@router.post("/graph")
async def preview_graph(req: Request):
    """The graph Train would queue, checked against this ComfyUI's /object_info. The folder input is filled when the job starts, so it is a placeholder here and is not checked."""
    b = await _body(req)
    if b.get("base") not in BASES: raise HTTPException(400, "Pick a base from the list.")
    base = BASES[b["base"]]
    s = settings_from(b, base)
    graph = training_graph(base["file"], "(made when you press Train)", s["steps"], s["rank"], s["batch"], s["learning_rate"], s["seed"], f"{OUTPUT_SUB}/(job)/lora")
    try: object_info = await run_in_threadpool(_comfy, "/object_info", None, 20)
    except Exception: return {"graph": graph, "checked": False, "problems": []}
    return {"graph": graph, "checked": True, "problems": [p for p in validate_graph(graph, object_info) if "folder =" not in p]}
