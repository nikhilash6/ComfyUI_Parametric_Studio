"""Can this recipe run on this machine? A real check, offline: every step's graph is built the way a run builds it and read against ComfyUI's /object_info (node types, required inputs, links, choices) and the model files on disk (present and not a stub). Nothing is queued and no model loads."""
import json, os, time
from psn import paths
from studio import apps as A
from studio.goals import GOALS, values_for, WF
from studio.graph_template import fill
from studio.names import MODEL_FILE, resolve_names
FILE_TTL = 60; MIN_BYTES = 4096; _files = {"t": 0, "d": None}; _cache = {}
UPLOAD_LOADERS = ("LoadImage", "LoadVideo", "LoadAudio")
def model_files(root=None, min_bytes=MIN_BYTES):
    """{file name: largest size} of the model files under the models root, following links. A name with no real file behind it is not here."""
    root = root or paths.models_root(True); out = {}
    for dp, _, fn in os.walk(root, followlinks=True):
        for f in fn:
            if MODEL_FILE.search(f):
                try: s = os.stat(os.path.join(dp, f)).st_size
                except OSError: continue
                if s >= min_bytes: out[f] = max(out.get(f, 0), s)
    return out
def context():
    """(object_info or None, model files), cached."""
    try: oi = A.object_info()
    except Exception: oi = None
    if _files["d"] is None or time.time() - _files["t"] > FILE_TTL: _files.update(d=model_files(), t=time.time())
    return oi, _files["d"]
def _options(spec):
    if isinstance(spec, list) and spec:
        if isinstance(spec[0], list): return spec[0]
        if spec[0] == "COMBO" and len(spec) > 1 and isinstance(spec[1], dict): return spec[1].get("options")
    return None
def check_graph(graph, oi, files):
    """Problems in one API graph: what ComfyUI's own validation would refuse, plus model files that are not really on disk."""
    probs = []
    for nid, n in graph.items():
        cls = n.get("class_type"); info = oi.get(cls)
        if not info: probs.append(f"node type {cls} is not installed"); continue
        want = {**((info.get("input") or {}).get("required") or {}), **((info.get("input") or {}).get("optional") or {})}; ins = n.get("inputs") or {}
        for k, spec in ((info.get("input") or {}).get("required") or {}).items():
            if k not in ins and not any(i.startswith(k + ".") for i in ins) and not (isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict) and "default" in spec[1]): probs.append(f"{cls}: required input {k} is empty")
        for k, v in ins.items():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[1], int):
                if str(v[0]) not in graph: probs.append(f"{cls}.{k} is linked to a node that is not in the graph")
                continue
            if not isinstance(v, str): continue
            opts = _options(want.get(k))
            if opts is None: continue
            if MODEL_FILE.search(v):
                if v not in opts: probs.append(f"model {os.path.basename(v)} is not known to ComfyUI")
                elif os.path.basename(v) not in files: probs.append(f"model {os.path.basename(v)} is not on disk")
            elif cls not in UPLOAD_LOADERS and v not in opts: probs.append(f"{cls}.{k}: {v!r} is not one of its choices")
    return probs
def _goal_graph(spec, values):
    from studio import recipes as R
    b = R.goal_body(spec, values); g = GOALS[spec["goal"]]; b["video"] = "check.mp4"; b["last_image"] = "check.png"
    vals, _ = values_for(spec["goal"], b, "check.png"); graph = fill(json.load(open(os.path.join(WF, g["template"]))), {**{k: "" for k in ()}, **vals})
    if b.get("lora"):
        from studio import loras
        graph = loras.apply_to_graph(graph, b["lora"])
    return graph
def _template_graph(spec, oi):
    from studio import edits as E, recipes as R
    path = E._path(spec["template"])
    if not path: return None
    vals = {k: ("check.png" if isinstance(v, str) and v.startswith("@") else v) for k, v in (spec.get("values") or {}).items()}
    return R.template_graph({**spec, "set": spec.get("set") or {}}, vals, oi, path)
def _family_graph(spec):
    from studio import recipes_family as F
    return F.build_graph({**spec, "seed": 1}, {"prompt": "check"})
def _h3ref_graph(spec):
    from studio import recipes_family as F
    return F.h3_reference_graph({**spec, "seed": 1}, {"scene": "check"}, ["check.png" for _ in spec.get("pictures") or []], "check.mp4" if spec.get("video") else None)
def _step_key(s):
    if s["type"] == "h3_reference": return ("h3_reference", s["lora"], s.get("sampler"), s.get("scheduler"))
    if s["type"] == "family_lora": return ("family_lora", s["template"], json.dumps(s.get("loras")))
    if s["type"] == "goal": return ("goal", s["goal"], json.dumps(s.get("options") or {}, sort_keys=True), json.dumps(s.get("lora") or {}, sort_keys=True))
    if s["type"] == "template": return ("template", s["template"], json.dumps(s.get("swap") or {}, sort_keys=True), json.dumps(s.get("insert") or [], sort_keys=True), json.dumps({n: {k: v for k, v in kv.items() if k == "lora_name"} for n, kv in (s.get("set") or {}).items()}, sort_keys=True))
    return (s["type"], s.get("op"), s.get("model"), ((s.get("asset") or {}).get("recipe") or {}).get("mesh_model"))
def _world_problems(s):
    """A World Kit asset or a 3D model has no graph to check here: what it needs on this machine is what its own page checks."""
    from studio import model3d as M
    from studio.worldkit import capabilities as C
    if s["type"] == "model3d": need = [M.model(s["model"])["need"]]
    else:
        a = s.get("asset") or {}; pick = (a.get("recipe") or {}).get("mesh_model")
        need = [pick] if pick else []
    return [C.need(n)["message"] for n in need if C.need(n)["state"] != "ready"]
def check_step(s, oi, files, values=None):
    """Problems of one step, cached on what shapes its graph: most recipes share a few."""
    key = (id(oi), id(files)) + _step_key(s)
    if key in _cache: return _cache[key]
    probs = []
    try:
        if s["type"] == "cpu":
            import shutil
            if s.get("op") != "sound" and not shutil.which("ffmpeg"): probs.append("ffmpeg is not installed")
        elif s["type"] in ("worldkit", "model3d"): probs += _world_problems(s)
        elif s["type"] != "plan":
            g = _goal_graph(s, values or {}) if s["type"] == "goal" else _family_graph(s) if s["type"] == "family_lora" else _h3ref_graph(s) if s["type"] == "h3_reference" else _template_graph(s, oi)
            if g is None: probs.append(f"the ComfyUI template {s['template']} is not installed")
            else:
                g, rep = resolve_names(g, oi); probs += [f"model {os.path.basename(str(r['was']))} is not installed" for r in rep if r["now"] is None]; probs += check_graph(g, oi, files)
    except Exception as e: probs.append(f"its graph could not be built: {str(getattr(e, 'detail', '') or e)[:160]}")
    if len(_cache) > 2000: _cache.clear()
    _cache[key] = sorted(set(probs)); return _cache[key]
def check_recipe(rec, oi, files):
    """{"ready": True / False / None, "why": text, "problems": [...]}. None means ComfyUI could not be asked, so nothing is claimed."""
    if rec.get("reference"): return {"ready": False, "why": rec.get("why_not") or "A reference card: it cannot run here yet.", "problems": [], "waiting": rec.get("waiting")}
    needs_comfy = any(s["type"] not in ("cpu", "plan") for s in rec["steps"])
    if needs_comfy and oi is None: return {"ready": None, "why": "ComfyUI could not be asked, so this was not checked.", "problems": []}
    values = {f["key"]: f.get("default", "") for f in rec.get("fields", [])}; probs = []
    for s in rec["steps"]: probs += check_step(s, oi, files, values)
    probs = sorted(set(probs))
    return {"ready": not probs, "why": "Every node, choice and model file checked." if not probs else "; ".join(probs[:4]), "problems": probs}
