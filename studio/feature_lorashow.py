"""LoRA Showcase: a page for each LoRA you trained, with its A/B proof, model card, trigger words, licence and base model, and a bundle to share however you like.
Every figure comes from Train's own run record. A run with no A/B test says so rather than showing anything else. The trigger, base and hash are the run's, and cannot be edited. Licence and description are yours to write: nothing is chosen for you.
The bundle is a zip you download. Nothing here uploads anything anywhere. It never holds your training pictures, their captions, or a folder path."""
import csv, datetime, io, json, os, re, threading, zipfile
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

router = APIRouter(prefix="/api/lorashow")
PAGE = {"tab": "lorashow", "label": "LoRA Showcase", "title": ["LoRA Showcase", "You trained it. Now show it.", "A/B proof, model card, trigger words, licence and base model, from the run's own record. A bundle to share yourself: nothing uploads."], "module": "lorashow.js", "export": "LoraShowcase", "css": "lorashow.css"}
BASE_LICENCE = {"sdxl-base-1.0": {"name": "CreativeML Open RAIL++-M", "url": "https://stability.ai/news/stable-diffusion-sdxl-1-announcement"}, "sd-1.5": {"name": "CreativeML Open RAIL-M", "url": "https://stability.ai/news/stable-diffusion-public-release"}}
LICENCES = ["CreativeML Open RAIL-M", "CreativeML Open RAIL++-M", "Apache-2.0", "MIT", "CC BY 4.0", "CC BY-NC 4.0", "All rights reserved", "Other (say which in the description)"]
MAX_TEXT = 4000; _lock = threading.Lock()


def _T():
    from studio import train
    return train


def _job(job_id: str) -> dict:
    T = _T(); j = T._load_job(job_id); lo = j.get("lora") or {}
    if j.get("state") != "done" or not lo.get("path") or not os.path.isfile(lo["path"]): raise HTTPException(404, "This run has no finished LoRA whose file is still there.")
    return j


def _card_path(job_id: str) -> Path: return _T().data_root() / "showcase" / f"{job_id}.json"


def saved(job_id: str) -> dict:
    try: return json.loads(_card_path(job_id).read_text())
    except (OSError, ValueError): return {}


def _ab(j: dict) -> dict:
    """The A/B test as the run recorded it. Words only for what the numbers really say."""
    a = j.get("ab") or {}
    if a.get("state") != "done": return {"state": a.get("state") or "none", "error": a.get("error"), "prompt": a.get("prompt"), "said": "No A/B test has finished for this LoRA, so there is no proof to show yet."}
    pd, unbound = a.get("pixel_diff"), a.get("unbound_keys")
    warn = []
    if pd == 0: warn.append("The two pictures are identical: this LoRA changed nothing at this strength.")
    if unbound: warn.append(f"{unbound} of its keys did not attach to the model, so part of it was not used.")
    return {"state": "done", "prompt": a.get("prompt"), "seed": a.get("seed"), "strength": a.get("strength"), "pixel_diff": pd, "unbound_keys": unbound, "base": a.get("base"), "lora": a.get("lora"), "warn": warn, "same_seed": True, "said": "Same prompt, same seed, same model: the only change is the LoRA. One seed shows one result, not how it always behaves."}


def _facts(j: dict) -> dict:
    T = _T(); v = T.view_job(j); s = j["settings"]; lo = j["lora"]; base = T.BASES.get(j.get("base")) or {}
    return {"steps": lo.get("total_steps"), "rank": s.get("rank"), "size": s.get("size"), "batch": s.get("batch"), "learning_rate": s.get("learning_rate"), "seed": s.get("seed"), "s_per_step": v.get("s_per_step"), "elapsed_s": v.get("elapsed_s"), "last_loss": round(v["last_loss"], 4) if v.get("last_loss") is not None else None, "peak_vram_gib": j.get("peak_vram_gib"), "gpu": _T()._card(j.get("gpu")) if j.get("gpu") else None, "pictures": j.get("pictures") or j.get("dataset_pictures"), "tensors": lo.get("tensors"), "bytes": lo.get("bytes"), "sha256": lo.get("sha256"), "file": os.path.basename(lo.get("name") or ""), "base_id": j.get("base"), "base": base.get("label"), "arch": base.get("arch"), "base_file": j.get("base_file"), "base_licence": BASE_LICENCE.get(j.get("base")), "finished": datetime.date.fromtimestamp(j["ended"]).isoformat() if j.get("ended") else None, "rights": (j.get("rights") or {}).get("text") if (j.get("rights") or {}).get("confirmed") else None}


def card(job_id: str) -> dict:
    j = _job(job_id); c = saved(job_id); curve = (_T().view_job(j).get("curve") or [])
    return {"job": job_id, "name": j.get("name"), "trigger": j.get("trigger"), "facts": _facts(j), "ab": _ab(j), "curve": curve, "licence": c.get("licence"), "description": c.get("description") or "", "use": c.get("use") or "", "licences": LICENCES, "ready": bool(c.get("licence")), "missing": [] if c.get("licence") else ["a licence, which only you can choose"]}


def model_card(c: dict) -> str:
    """The README in the bundle. Only what the record holds, and it says what was not measured."""
    f, a = c["facts"], c["ab"]; n = lambda v, u="": f"{v}{u}" if v is not None else "not measured"; bl = f.get("base_licence") or {}
    out = [f"# {c['name']}", "", c["description"] or "", "", f"Trigger words: `{c['trigger']}`" if c.get("trigger") else "Trigger words: none set", f"Base model: {f['base'] or f['base_id']} (`{f['base_file']}`)", f"Licence of this LoRA: {c['licence'] or 'not chosen'}", f"Licence of the base model: {bl.get('name') or 'not on record'}. It still applies to anything made with it.", ""]
    if c["use"]: out += ["## How to use it", "", c["use"], ""]
    out += ["## A/B proof", ""]
    if a["state"] == "done":
        out += [a["said"], "", f"Prompt: {a['prompt']}", f"Seed: {a['seed']}", f"LoRA strength: {a['strength']}", f"Mean pixel difference, 0 to 255: {n(a['pixel_diff'])} (measured)", f"Keys that did not attach: {n(a['unbound_keys'])} (measured)", "", "Pictures: `ab/without_lora.png` and `ab/with_lora.png`. The exact graph: `ab/graph.json`.", ""] + [f"Warning: {w}" for w in a["warn"]]
    else: out += ["No A/B test finished for this LoRA, so there is no proof in this bundle.", ""]
    out += ["", "## How it was trained (from the run record)", "", f"Steps: {n(f['steps'])}", f"Rank: {n(f['rank'])}", f"Picture size: {n(f['size'])}", f"Batch: {n(f['batch'])}", f"Learning rate: {n(f['learning_rate'])}", f"Training seed: {n(f['seed'])}", f"Last loss: {n(f['last_loss'])}", f"Seconds per step: {n(f['s_per_step'])}", f"Peak video memory of the whole card: {n(f['peak_vram_gib'], ' GiB')}", f"GPU: {n(f['gpu'])}", "", f"File: `{f['file']}`", f"SHA-256: `{f['sha256']}`", "", f"What the trainer confirmed about the pictures: {f['rights']}" if f.get("rights") else "No statement about the pictures' rights is on record.", "", "Training pictures are not included. Made with Parametric Studio's Train page.", ""]
    return "\n".join(out)


def _clean_png(data: bytes) -> bytes:
    """Pictures go in without their embedded metadata."""
    from PIL import Image
    b = io.BytesIO(); Image.open(io.BytesIO(data)).convert("RGB").save(b, "PNG"); return b.getvalue()


def _view(ref: dict) -> bytes:
    import urllib.parse
    return _T()._comfy("/view?" + urllib.parse.urlencode({k: ref[k] for k in ("filename", "subfolder", "type")}), raw=True, timeout=60)


def bundle_bytes(job_id: str, weights: bool) -> tuple:
    j = _job(job_id); c = card(job_id)
    if not c["ready"]: raise HTTPException(409, "Choose a licence first. Only you can.")
    notes = []; out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        a = c["ab"]
        if a["state"] == "done":
            for ref, name in ((a.get("base"), "ab/without_lora.png"), (a.get("lora"), "ab/with_lora.png")):
                try: z.writestr(name, _clean_png(_view(ref)))
                except Exception: notes.append(f"{name} could not be fetched from ComfyUI, so it is not in this bundle.")
            graph = (j.get("ab") or {}).get("graph")
            if graph: z.writestr("ab/graph.json", json.dumps(_scrub_graph(graph), indent=1))
        rows = io.StringIO(); w = csv.writer(rows); w.writerow(["step", "loss"]); [w.writerow(p) for p in (c["curve"] or [])]; z.writestr("loss.csv", rows.getvalue())
        record = {k: v for k, v in c.items() if k in ("name", "trigger", "licence", "description", "use")}; record["facts"] = {k: v for k, v in c["facts"].items()}; record["ab"] = {k: v for k, v in a.items() if k not in ("base", "lora")}
        z.writestr("record.json", json.dumps(_scrub_graph(record), indent=1))
        readme = model_card(c)
        if notes: readme += "\n" + "\n".join(notes) + "\n"
        z.writestr("README.md", readme)
        if weights: z.write(j["lora"]["path"], c["facts"]["file"], compress_type=zipfile.ZIP_STORED)
    name = re.sub(r"[^\w-]+", "_", c["name"] or "lora").strip("_") or "lora"
    return out.getvalue(), f"{name}_showcase.zip", notes


def _scrub_graph(v):
    """No folder ever goes in the bundle: a value with one keeps only its last part."""
    if isinstance(v, dict): return {k: _scrub_graph(x) for k, x in v.items()}
    if isinstance(v, list): return [_scrub_graph(x) for x in v]
    if isinstance(v, str) and re.search(r"(?<![\w.])(?:/(?:home|Users|mnt|root|media|var|tmp|opt|srv|data)/|~/|[A-Za-z]:[\\/])", v): return re.split(r"[\\/]", v.rstrip("/\\"))[-1]
    return v


@router.get("/loras")
def list_loras():
    rows = []
    for r in _T().trained()["loras"]:
        j = _T()._load_job(r["job"]); a = j.get("ab") or {}
        rows.append({"job": r["job"], "name": r["name"], "trigger": r["trigger"], "base_label": r["base_label"], "total_steps": r["total_steps"], "ab": a.get("state") or "none", "pixel_diff": a.get("pixel_diff"), "with_lora": (a.get("lora") or {}).get("url"), "licence": saved(r["job"]).get("licence")})
    return {"loras": rows}


@router.get("/card/{job_id}")
def get_card(job_id: str): return card(job_id)


@router.post("/card/{job_id}")
def set_card(job_id: str, b: dict):
    _job(job_id); c = saved(job_id); from studio import sfw
    for k in ("description", "use"):
        if k in b:
            if not isinstance(b[k], str) or len(b[k]) > MAX_TEXT: raise HTTPException(400, f"{k} must be text under {MAX_TEXT} characters.")
            sfw.check(b[k]); c[k] = b[k].strip()
    if "licence" in b:
        if b["licence"] not in LICENCES and b["licence"] is not None: raise HTTPException(400, "Choose a licence from the list.")
        c["licence"] = b["licence"]
    p = _card_path(job_id); p.parent.mkdir(parents=True, exist_ok=True); t = p.with_suffix(".tmp"); t.write_text(json.dumps(c)); os.replace(t, p); return card(job_id)


@router.get("/card/{job_id}/image/{which}")
def image(job_id: str, which: str):
    a = _ab(_job(job_id)); ref = {"without": a.get("base"), "with": a.get("lora")}.get(which)
    if not ref: raise HTTPException(404, "no such picture")
    try: return Response(_view(ref), media_type="image/png")
    except Exception: raise HTTPException(503, "ComfyUI could not give this picture back.") from None


@router.get("/card/{job_id}/readme")
def readme(job_id: str): return Response(model_card(card(job_id)), media_type="text/markdown")


@router.get("/card/{job_id}/bundle")
def bundle(job_id: str, weights: bool = False):
    data, name, _ = bundle_bytes(job_id, weights)
    return Response(data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}"'})
