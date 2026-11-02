"""Pipelines: productions where several model families make one result. One JSON file in studio/pipelines is one pipeline, in the recipe format (recipes.py runs it), and the page reads what a real run left in web/pipelines/<id>/proof.json. To add one see docs/ADDING_A_PIPELINE.md.
Two step types join the recipe engine here, so a World Kit asset and a Virtual Set shot chain like any other step: `worldkit` builds an asset and `vset` renders a shot, through the same functions as their pages."""
import json, re, shutil, time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from studio import recipes as R

HERE = Path(__file__).resolve().parent; DIR = HERE / "pipelines"; WEB = HERE / "web" / "pipelines"; SAFE = re.compile(r"^[a-z0-9][a-z0-9_-]*$"); POLL = 3.0; LIMIT = 5400
VISIBLE = {"preview.mp4": "video", "thumb.jpg": "image", "asset.glb": "mesh"}; _CACHE = {"sig": None, "rows": []}
router = APIRouter()

def rows():
    """Every pipeline file, in page order. A file is re-read when it changes, so a new pipeline needs no restart."""
    files = sorted(DIR.glob("*.json")); sig = tuple((f.name, f.stat().st_mtime) for f in files)
    if _CACHE["sig"] != sig: _CACHE.update(sig=sig, rows=sorted((json.loads(f.read_text(encoding="utf-8")) for f in files), key=lambda r: (r.get("order", 99), r["id"])))
    return _CACHE["rows"]
def get(pid): return next((r for r in rows() if r["id"] == pid), None)
def proof(pid):
    """What a real run left behind, or None: a pipeline with no run says so on the page."""
    try: return json.loads((WEB / pid / "proof.json").read_text(encoding="utf-8"))
    except (OSError, ValueError): return None
def problems():
    """Everything a new pipeline can get wrong, as sentences. A test keeps this empty."""
    from studio import edits as E
    bad = list(R.validate({"recipes": rows()}))
    for r in rows():
        pid = r["id"]; names = {m["name"] for m in r.get("models", [])}
        if not SAFE.match(pid): bad.append(f"{pid}: bad id")
        for k in ("order", "kicker"):
            if k not in r: bad.append(f"{pid}: no {k}")
        for s in r.get("steps", []):
            sid = f"{pid}/{s.get('id')}"
            if s.get("type") != "cpu" and s.get("model") not in names: bad.append(f"{sid}: its model {s.get('model')!r} is not in the pipeline's models, so the page could not show its licence")
            if s.get("type") == "template" and not E._path(s.get("template", "")): bad.append(f"{sid}: no template {s.get('template')}")
        pr = proof(pid)
        if pr:
            if pr.get("status") not in ("passed", "partial", "failed"): bad.append(f"{pid}: proof has status {pr.get('status')}")
            for st in pr.get("stages", []):
                for m in st.get("media", []):
                    if not (WEB / pid / m["src"]).is_file(): bad.append(f"{pid}: proof names {m['src']}, not in the web folder")
    return bad

# ---------- the two step types
def _local_file(run, st_id, src, kind):
    """A built file copied beside the run, so it stays reachable and the next step can use it."""
    d = R._root() / run["run"]; d.mkdir(parents=True, exist_ok=True); dst = d / f"{st_id}_{Path(src).name}"; shutil.copy2(src, dst)
    return {"filename": dst.name, "subfolder": "", "type": "recipe", "kind": kind, "local": str(dst), "url": f"/api/recipes/files/{run['run']}/{dst.name}"}
def _note_progress(st, run, done, total, name=""):
    st["note"] = f"{name or 'Working'}: {done} of {total}" if total else name; R._save(run)
def _fill_refs(value, run, ctx):
    """'@step' in a World Kit source is a file that step made, uploaded to ComfyUI's input folder; '@step' in a shot is the asset that step built."""
    if isinstance(value, dict): return {k: _fill_refs(v, run, ctx) for k, v in value.items()}
    if isinstance(value, list): return [_fill_refs(v, run, ctx) for v in value]
    if isinstance(value, str): return R._fill(value, ctx["values"])
    return value
def _asset_of(ctx, ref):
    files = ctx["out"].get(ref[1:]) or []
    aid = next((f["asset"] for f in files if f.get("asset")), None)
    if not aid: raise R.StepError(f"step {ref[1:]} built no World Kit asset to use")
    return aid
def _run_worldkit(run, st, spec, ctx):
    from studio.worldkit import api as WK, library as L, runner, characters as CS
    lib = L.Library(); b = _fill_refs(spec["asset"], run, ctx); src = b.get("source") or {}
    if isinstance(src.get("image"), str) and src["image"].startswith("@"): src["image"] = R._input_name(run, ctx, src["image"], "image")
    if isinstance(src.get("mesh"), str) and src["mesh"].startswith("@"):
        f = R._pick(ctx, src["mesh"], "mesh"); src["mesh"] = str(Path(f.get("subfolder") or "") / f["filename"])
    if str(src.get("character_id", "")).startswith("@"):
        src["character_id"] = next((f["character"] for f in ctx["out"].get(src["character_id"][1:]) or [] if f.get("character")), "")
    code, body = WK.create(lib, b, get_character=CS.get, start=lambda aid: runner.start(aid, library=lib))
    if code >= 400: raise R.StepError(body.get("error") or f"World Kit refused the asset ({code})")
    aid = body["asset"]["id"]; st["asset"] = aid; t0 = time.time(); seed_note = (spec["asset"].get("recipe") or {}).get("seed")
    if seed_note is not None: st["seed"] = seed_note
    while time.time() - t0 < LIMIT:
        time.sleep(POLL)
        if run.get("_cancel"):
            try: runner.cancel(aid)
            except Exception: pass
            raise R.Cancelled()
        meta = lib.require(aid); build = meta.get("build") or {}; steps = build.get("steps") or []
        _note_progress(st, run, sum(1 for r in steps if r["status"] in ("done", "skipped")), len(steps), next((r["name"] for r in steps if r["status"] == "running"), ""))
        if runner.is_running(aid): continue
        if build.get("state") != "done": raise R.StepError(f"{next((r['name'] for r in steps if r['status'] == 'failed'), 'A step')}: {build.get('error') or 'the build stopped'}")
        st["build"] = [{"name": r["name"], "status": r["status"], "seconds": r.get("seconds")} for r in steps]; st.pop("note", None)
        out = [{**_local_file(run, st["id"], lib.path(aid, name), kind), "asset": aid} for name, kind in VISIBLE.items() if lib.path(aid, name).is_file()]
        if not out: raise R.StepError("the asset is built but holds no files")
        return out
    raise R.StepError(f"gave up after {LIMIT // 60} minutes")
def _run_vset(run, st, spec, ctx):
    from studio.vset import api as VS, runner, shot as SH
    from studio.worldkit import library as L, steps as WS
    lib = L.Library(); shot = _fill_refs(spec["shot"], run, ctx); shot["seed"] = int(spec["shot"].get("seed", 4242)) + ctx["seed_add"]; st["seed"] = shot["seed"]; sets = shot.setdefault("set", {"place": "", "props": []})
    if str(sets.get("place", "")).startswith("@"): sets["place"] = _asset_of(ctx, sets["place"]); lib.approve(sets["place"])
    for p in sets.get("props") or []:
        if str(p.get("asset", "")).startswith("@"): p["asset"] = _asset_of(ctx, p["asset"])
    for c in shot.get("cast") or []:
        if str(c.get("asset", "")).startswith("@"): c["asset"] = _asset_of(ctx, c["asset"]); lib.approve(c["asset"])
    if shot.get("look_from_place") and sets.get("place"): shot["look"] = lib.require(sets["place"]).get("recipe", {}).get("look") or shot.get("look"); shot.pop("look_from_place")
    code, body = VS.save_shot({"shot": shot}, library=lib, is_running=runner.is_running)
    if code >= 400: raise R.StepError(body.get("error") or f"Virtual Set refused the shot ({code})")
    sid = body["shot"]["id"]; st["shot"] = sid
    code, body = VS.render_shot(sid, library=lib, start=lambda s, p=False: runner.start_shot(s, library=lib, passes_only=p), is_running=runner.is_running)
    if code >= 400: raise R.StepError(body.get("error") or f"Virtual Set refused the render ({code})")
    t0 = time.time(); key = f"shot:{sid}"
    while time.time() - t0 < LIMIT:
        time.sleep(POLL)
        if run.get("_cancel"):
            VS.cancel_shot(sid, is_running=runner.is_running, cancel=runner.cancel); raise R.Cancelled()
        state = SH.load_state(sid); steps = state.get("steps") or []; _note_progress(st, run, sum(1 for r in steps if r["status"] in ("done", "skipped")), len(steps), next((r["name"] for r in steps if r["status"] == "running"), ""))
        if runner.is_running(key): continue
        if state.get("state") == "failed": raise R.StepError(state.get("error") or "the shot failed")
        out = WS.outputs(state); st["qc"] = state.get("qc"); st["build"] = [{"name": r["name"], "status": r["status"], "seconds": r.get("seconds")} for r in steps]; st.pop("note", None); files = []
        for name, kind in (("video", "video"), ("key_first", "image"), ("key_last", "image")):
            got = VS.shot_file(sid, name)
            if got: files.append(_local_file(run, st["id"], got[0], kind))
        scene = out.get("scene") or {}
        for name in ("depth", "shaded"):
            got = VS.shot_file(sid, name) if name in scene else None
            if got: files.append(_local_file(run, st["id"], got[0], "video" if str(got[0]).endswith(".mp4") else "image"))
        if not files: raise R.StepError("the shot finished with no file")
        return files
    raise R.StepError(f"gave up after {LIMIT // 60} minutes")
def _run_sheet(run, st, spec, ctx):
    """A saved character from words: the sheet is drawn and must pass the picture check, or the stage fails and says why."""
    from studio.worldkit import characters as CS
    c = _fill_refs(spec["character"], run, ctx); ch, bad = CS.create(c.get("name"), c.get("description"))
    if bad or ch is None: raise R.StepError(bad or "the character was refused")
    ch = CS.build_sheet(ch.id)
    if ch is None or ch.status != "ready": raise R.StepError(f"The picture check did not pass the sheet: {(ch and ch.error) or 'no sheet'}")
    st["check"] = {k: (ch.check or {}).get(k) for k in ("ok", "why") if k in (ch.check or {})}
    return [{**_local_file(run, st["id"], ch.sheet(), "image"), "character": ch.id}]
def _run_pack(run, st, spec, ctx):
    """The built assets as one game-engine pack: glb files, a scene and a manifest, zipped."""
    from studio.worldkit import export as X, library as L
    lib = L.Library(); ids = [_asset_of(ctx, r) for r in spec["assets"]]
    for aid in ids: lib.approve(aid)
    code, body = X.build_pack(lib, {"name": R._fill(spec.get("name") or "pack", ctx["values"]), "assets": ids})
    if code >= 400: raise R.StepError(body.get("error") or f"the pack was refused ({code})")
    st["facts"] = {"assets": body["assets"], "engine": body["manifest"]["engine"], "files": [a.get("file") or a.get("path") or a.get("name") for a in body["manifest"]["assets"]]}
    return [_local_file(run, st["id"], X.export_root(lib) / body["zip"], "file")]
R.EXTRA_STEPS.update(worldkit=_run_worldkit, vset=_run_vset, worldkit_pack=_run_pack, worldkit_sheet=_run_sheet)

# ---------- API. Runs go through /api/recipes/{id}/run, the same queue as every recipe.
def _public(r):
    return {**{k: r.get(k) for k in ("id", "order", "title", "kicker", "pitch", "why", "tags", "fields", "models", "tips")}, "steps": [{k: s.get(k) for k in ("id", "label", "type", "model", "goal", "template", "op", "final", "does")} for s in r["steps"]], "proof": proof(r["id"])}
@router.get("/api/pipelines")
def pipelines_list(): return {"pipelines": [_public(r) for r in rows()]}
@router.get("/api/pipelines/{pid}")
def pipeline_get(pid: str):
    r = get(pid) if SAFE.match(pid) else None
    if not r: raise HTTPException(404, "no such pipeline")
    return _public(r)
