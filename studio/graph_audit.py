"""A static check of every graph the studio ships, against a ComfyUI /object_info: unknown node types, required inputs left empty, links to nodes or outputs that are not there, links of the wrong type, values outside their choices or range, and model files that are not on disk.
Nothing is queued and no model loads. `check()` is pure; `collect()` finds the graphs: the workflows folder, the studio's family templates, every family template /api/family-graphs lists, the edit tools and apps, the steps of recipes and pipelines, the University and RES4LYF graphs and the pipeline graphs.
A graph that cannot run here for a reason outside the graph (a pack that is not installed, weights that are not downloaded) says so in its metadata, under "needs": an API graph in a node's `_meta`, a UI graph in `extra`, a family template in its index entry. scripts/graph_audit.py writes the table; tests/test_graph_audit.py runs the check in CI on a saved snapshot."""
import glob, json, os, re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent; STUDIO = REPO / "studio"
MODEL_FILE = re.compile(r"\.(safetensors|sft|ckpt|pt|pth|gguf|bin|onnx|pkl)$", re.I)
PH = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}")
UPLOAD_LOADERS = {"LoadImage", "LoadImageMask", "LoadVideo", "LoadAudio", "LoadImageOutput", "Load3D", "Load3DAnimation", "VHS_LoadVideo", "VHS_LoadAudioUpload", "LoadImageSetFromFolderNode"}
ANY = {"*", "COMFY_MATCHTYPE_V3", "COMFY_AUTOGROW_V3", "ANY", "any", "any_type", "AnyType"}
SELF_VALIDATING = {("CustomCombo", "choice")}       # a node whose validate_inputs takes the input: ComfyUI skips its choice list
CORE_MODULES = ("nodes", "comfy_extras", "comfy_api_nodes", "comfy_api")
COMMON_PACKS = ("comfyui_parametric_studio", "kijai__ComfyUI-KJNodes")


# ---------------------------------------------------------------- the check
def _spec_type(spec):
    if not isinstance(spec, list) or not spec: return None
    return spec[0]


def _spec_opts(spec):
    if not isinstance(spec, list) or not spec: return None
    if isinstance(spec[0], list): return spec[0]
    if len(spec) > 1 and isinstance(spec[1], dict) and spec[0] in ("COMBO",) and isinstance(spec[1].get("options"), list): return spec[1]["options"]
    return None


def _extra(spec): return spec[1] if isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict) else {}


def types_ok(received, wanted):
    """ComfyUI's validate_node_input, non-strict, read from /object_info (which loses a pack's AnyType trick, so unknown 'any' names pass)."""
    if received == wanted or (isinstance(received, str) and received in ANY) or (isinstance(wanted, str) and wanted in ANY): return True
    if isinstance(received, list): return wanted == "COMBO" or isinstance(wanted, list)
    if isinstance(wanted, list): return received in ("COMBO", "STRING") or received in ANY
    if not isinstance(received, str) or not isinstance(wanted, str): return False
    if received in ANY or wanted in ANY or "*" in (received, wanted): return True
    return bool(set(x.strip() for x in received.split(",")) & set(x.strip() for x in wanted.split(",")))


def _placeholder(v): return isinstance(v, str) and bool(PH.search(v))


def is_api(g): return isinstance(g, dict) and bool(g) and all(isinstance(v, dict) and "class_type" in v for v in g.values())


def check(graph, oi, files=None, model_opts=True, upload_ok=True, extra_names=(), fixes=None, resolves=True, notes=None):
    """-> [(kind, text)] where kind is missing-node, bad-input or missing-model. `files` is {basename: bytes} of the model files on disk; None skips the disk test (CI).
    model_opts False skips choice lists that are model files (a snapshot from another machine lists that machine's files).
    resolves True: the page that runs it maps a portable file name onto the sub-folder this ComfyUI keeps it in (names.resolve_names), so that is not a problem. A name in a sub-folder no installer makes is still a stale name, fixed in the file."""
    out = []
    if not is_api(graph): return [("not-api-format", "not an API-format graph")]
    outputs = False
    for nid, n in graph.items():
        cls = n.get("class_type"); info = oi.get(cls)
        if not info: out.append(("missing-node", f"{nid}:{cls} is not installed")); continue
        if info.get("output_node"): outputs = True
        req = (info.get("input") or {}).get("required") or {}; opt = (info.get("input") or {}).get("optional") or {}; want = {**req, **opt}
        ins = n.get("inputs") or {}
        for k, spec in req.items():
            if _spec_type(spec) == "COMFY_AUTOGROW_V3" and not (_extra(spec).get("template") or {}).get("min"): continue      # a growing list with no minimum may be empty
            if k not in ins and not any(i.startswith(k + ".") for i in ins): out.append(("bad-input", f"{nid}:{cls} required input {k} is empty"))
        for k, v in ins.items():
            spec = want.get(k) or want.get(k.split(".")[0])
            if isinstance(v, list) and len(v) == 2 and not isinstance(v[0], (list, dict)) and isinstance(v[1], int):
                src = graph.get(str(v[0]))
                if src is None: out.append(("bad-input", f"{nid}:{cls}.{k} links to node {v[0]}, which is not in the graph")); continue
                sinfo = oi.get(src.get("class_type"))
                if not sinfo: continue
                outs = sinfo.get("output") or []
                if v[1] >= len(outs) or v[1] < 0: out.append(("bad-input", f"{nid}:{cls}.{k} links to output {v[1]} of {src.get('class_type')}, which has {len(outs)}")); continue
                if spec is not None and k in want and not types_ok(outs[v[1]], _spec_type(spec)): out.append(("bad-input", f"{nid}:{cls}.{k} wants {_spec_type(spec) if not isinstance(_spec_type(spec), list) else 'a choice'}, gets {outs[v[1]]} from {src.get('class_type')}"))
                continue
            if k not in want: continue          # ComfyUI ignores an input it does not know (dynamic inputs land here too)
            if _placeholder(v): continue        # filled when the page runs it
            t = _spec_type(spec); ex = _extra(spec); opts = _spec_opts(spec)
            if isinstance(v, dict) and "__value__" in v: v = v["__value__"]
            if t in ("INT", "FLOAT") and not isinstance(v, bool):
                try: x = float(v)
                except (TypeError, ValueError): out.append(("bad-input", f"{nid}:{cls}.{k}={v!r} is not a number")); continue
                if "min" in ex and isinstance(ex["min"], (int, float)) and x < ex["min"]: out.append(("bad-input", f"{nid}:{cls}.{k}={v} is under its minimum {ex['min']}"))
                if "max" in ex and isinstance(ex["max"], (int, float)) and x > ex["max"]: out.append(("bad-input", f"{nid}:{cls}.{k}={v} is over its maximum {ex['max']}"))
                continue
            if (cls, k) in SELF_VALIDATING: continue
            if opts is None:
                if isinstance(v, str) and MODEL_FILE.search(v) and files is not None and os.path.basename(v) not in files and "/" not in v[:1]: out.append(("missing-model", f"{nid}:{cls}.{k} names {os.path.basename(v)}, not on disk"))
                continue
            if opts == ["__files__"]: continue        # a saved snapshot: this machine's files, not checked elsewhere
            vals = v if isinstance(v, list) and ex.get("multiselect") else [v]
            for x in vals:
                if x in opts:
                    if isinstance(x, str) and MODEL_FILE.search(x) and files is not None and os.path.basename(x) not in files: out.append(("missing-model", f"{nid}:{cls}.{k} {os.path.basename(x)} is listed by ComfyUI but its file is a stub or a broken link"))
                    continue
                if isinstance(x, str) and MODEL_FILE.search(x):
                    if x in extra_names: continue
                    sub = _substitute(x)
                    if resolves and sub in opts:
                        if notes is not None: notes.append(f"{x.split('/')[-1]} runs as {sub} (names.SUBSTITUTE)")
                        continue
                    same = [o for o in opts if isinstance(o, str) and o.split("/")[-1] == x.split("/")[-1]]
                    if same and resolves:            # the page maps it onto the file this ComfyUI lists; an installer may well keep it in that folder
                        if notes is not None: notes.append(f"{x} runs as {same[0]} (names.resolve_names)")
                        continue
                    if same and model_opts:
                        out.append(("missing-model", f"{nid}:{cls}.{k} stale name {x}: ComfyUI lists the same file as {same[0]}"))
                        if fixes is not None: fixes.append((nid, k, x, same[0]))
                    elif model_opts: out.append(("missing-model", f"{nid}:{cls}.{k} {x} is not on disk"))
                elif cls in UPLOAD_LOADERS or (isinstance(x, str) and re.search(r"\.(png|jpe?g|webp|mp4|webm|mov|wav|mp3|flac|glb|obj)$", x, re.I)):
                    if not upload_ok: out.append(("bad-input", f"{nid}:{cls}.{k} {x!r} is not in the input folder"))
                elif model_opts or not _model_list(opts): out.append(("bad-input", f"{nid}:{cls}.{k}={x!r} is not one of its {len(opts)} choices" + (f" ({', '.join(map(str, opts[:6]))})" if len(opts) <= 6 else "")))
    if not outputs and not any(k == "missing-node" for k, _ in out): out.append(("bad-input", "no output node: ComfyUI refuses a graph with nothing to save or show"))
    return out


def _substitute(name):
    try:
        from studio.names import SUBSTITUTE, UPGRADE
        b = name.split("/")[-1]; return SUBSTITUTE.get(name) or SUBSTITUTE.get(b) or UPGRADE.get(name) or UPGRADE.get(b)
    except Exception: return None


def _model_list(opts): return bool(opts) and sum(1 for o in opts if isinstance(o, str) and MODEL_FILE.search(o)) >= max(1, len(opts) // 2)


def status(problems, fmt="api"):
    if fmt != "api" and not problems: return "not-api-format"
    kinds = {k for k, _ in problems}
    for k in ("not-api-format", "missing-node", "bad-input", "missing-model"):
        if k in kinds: return k
    return "ok"


def needs(graph, meta=None):
    """What a graph says it needs, from its metadata: a node's _meta, a UI graph's extra, or the entry that lists it (a family template's index entry, a University lesson's meta). [text]"""
    out = [str(x) for x in ((meta or {}).get("needs") or [])]
    if not isinstance(graph, dict): return out
    if is_api(graph):
        for n in graph.values(): out += [str(x) for x in ((n.get("_meta") or {}).get("needs") or [])]
    else: out += [str(x) for x in ((graph.get("extra") or {}).get("needs") or [])]
    return list(dict.fromkeys(out))


# ---------------------------------------------------------------- per-server node lists
def module_pack(info):
    m = (info.get("python_module") or "").split(".")
    return m[1] if len(m) > 1 and m[0] == "custom_nodes" else m[0]


def server_oi(oi, packs):
    """The node list a family instance has: core ComfyUI plus the common packs plus its own (psn.instances FAMILY_PACKS)."""
    keep = set(COMMON_PACKS) | set(packs or [])
    return {k: v for k, v in oi.items() if module_pack(v) in CORE_MODULES or module_pack(v) in keep or module_pack(v).startswith("websocket")}


def family_packs(family):
    """The pack folders a family instance links, under the names their links carry."""
    try:
        from psn import instances as I
        return [I.PACK_LINK_AS.get(p, p) for p in I.FAMILY_PACKS.get(family, [])]
    except Exception: return []


# ---------------------------------------------------------------- finding the graphs
def _load(p):
    try: return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError): return None


def _row(gid, source, path, target="main", graph=None, fmt=None, build=None, family=None, extra=None, resolves=True):
    return {"id": gid, "source": source, "path": str(path) if path else "", "target": target, "family": family, "graph": graph, "fmt": fmt, "build": build, "resolves": resolves, **(extra or {})}


def file_rows():
    """Graph files in the repo, as stored."""
    rows = []
    for p in sorted((REPO / "workflows").glob("*.json")): rows.append(_row("workflow:" + p.name, "workflows", p.relative_to(REPO), graph=_load(p)))
    idx = {t["name"]: t for t in (_load(STUDIO / "family_templates" / "index.json") or {}).get("templates", [])}
    for p in sorted((STUDIO / "family_templates").glob("*.json")):
        if p.name == "index.json": continue
        t = idx.get(p.stem) or {}
        if t.get("family"): continue            # listed by family_rows, on its family's own server
        rows.append(_row("family_template:" + p.stem, "family_templates", p.relative_to(REPO), target="family" if t.get("family") else "main", family=t.get("family"), graph=_load(p), extra={"indexed": bool(t)}))
    for p in sorted((STUDIO / "pipelines" / "graphs").glob("*.json")): rows.append(_row("pipeline_graph:" + p.stem, "pipelines/graphs", p.relative_to(REPO), graph=_load(p)))
    for p in sorted((STUDIO / "web" / "pipelines").glob("*/graphs/*.json")): rows.append(_row(f"pipeline_proof:{p.parent.parent.name}/{p.stem}", "web/pipelines", p.relative_to(REPO), graph=_load(p), resolves=False))
    for p in sorted((STUDIO / "university" / "graphs").glob("*.json")):
        d = _load(p)
        if p.name == "verified.json" or not isinstance(d, dict): continue
        rows.append(_row("university:" + p.stem, "university", p.relative_to(REPO), graph=d.get("graph") if "graph" in d else d, extra={"meta": d.get("meta") or {}}, resolves=False))
    for sub in ("graphs", "nodes"):
        for p in sorted((STUDIO / "web" / "res4lyf_renders" / sub).glob("*.json")): rows.append(_row(f"res4lyf_{sub[:-1]}:{p.stem}", "res4lyf_renders/" + sub, p.relative_to(REPO), graph=_load(p), resolves=False))
    return rows


def family_rows():
    """Every template /api/family-graphs lists, with its file: the studio's own (family_templates) or ComfyUI's template package."""
    from studio import families_api as F, apps as A
    rows = []; tdir = A.template_dir()
    for f, r in (F.status_data().get("families") or {}).items():
        for t in r.get("templates") or []:
            if not isinstance(t, dict): continue
            if t.get("studio"): p = STUDIO / "family_templates" / (t["name"] + ".json")
            else: p = Path(tdir) / (t["name"] + ".json") if tdir else None
            rows.append(_row(f"family:{r.get('slug') or f}/{t['name']}", "family-graphs" + (" (studio)" if t.get("studio") else " (ComfyUI templates)"), p if p and p.exists() else (p or ""), target="family", family=f, graph=_load(p) if p and p.exists() else None, extra={"declared_models": t.get("models") or [], "tpl": t, "meta": t}))
    return rows


def tool_rows():
    """The edit tools (Create's edit page) and the apps (linear-mode workflows)."""
    from studio import edits as E, apps as A
    rows = []
    for tid, _cat, label, tpl, _b in E.TOOLS:
        p = E._path(tpl); rows.append(_row(f"edit:{tid}", "edits", p or "", graph=_load(p) if p else None, extra={"label": label, "template": tpl}))
    try:
        for aid, p in A.find_apps({}).items(): rows.append(_row("app:" + aid, "apps", p, graph=_load(p)))
    except Exception: pass
    return rows


def step_rows(oi):
    """The graph each recipe and pipeline step builds, the way a run builds it, one row per distinct step."""
    from studio import recipes as R, pipelines as P, recipe_check as C
    rows, seen = [], {}
    def add(owner, i, s, values):
        if s.get("type") not in ("goal", "template", "family_lora", "h3_reference"): return
        key = C._step_key(s)
        if key in seen: seen[key]["used_by"].append(f"{owner}#{i}"); return
        try:
            g = C._goal_graph(s, values) if s["type"] == "goal" else C._family_graph(s) if s["type"] == "family_lora" else C._h3ref_graph(s) if s["type"] == "h3_reference" else C._template_graph(s, oi)
            err = None if g is not None else f"no template {s.get('template')}"
        except Exception as e: g, err = None, f"its graph could not be built: {str(getattr(e, 'detail', '') or e)[:200]}"
        what = s.get("goal") or s.get("template") or s.get("lora") or s["type"]
        r = _row(f"step:{s['type']}:{what}:{len(seen)}", "recipe/pipeline steps", "", target="family" if s["type"] == "family_lora" else "main", family=s.get("family"), graph=g, extra={"used_by": [f"{owner}#{i}"], "build_error": err, "step": s}); seen[key] = r; rows.append(r)
    for r in [*R.load()["recipes"], *R.library()]:
        if r.get("reference"): continue
        vals = {f["key"]: f.get("default", "") for f in r.get("fields", [])}
        for i, s in enumerate(r.get("steps") or []): add("recipe:" + r["id"], i, s, vals)
    for r in P.rows():
        vals = {f["key"]: f.get("default", "") for f in r.get("fields", [])}
        for i, s in enumerate(r.get("steps") or []): add("pipeline:" + r["id"], i, s, vals)
    return rows


def goal_rows():
    """Each goal's graph, filled the way /api/generate fills it."""
    from studio.goals import GOALS, values_for, WF
    from studio.graph_template import fill
    rows = []
    for k, g in GOALS.items():
        try:
            b = {"prompt": "a lighthouse at dawn", "seed": 7, "lyrics": "[Verse]\nla la", "video": "check.mp4", "video_b": "check.mp4", "last_image": "check.png"}
            vals, _ = values_for(k, b, "check.png"); graph = fill(json.load(open(os.path.join(WF, g["template"]))), vals); err = None
        except Exception as e: graph, err = None, f"its graph could not be filled: {str(e)[:200]}"
        rows.append(_row("goal:" + k, "goals", "workflows/" + g["template"], graph=graph, extra={"build_error": err}))
    return rows


def collect(oi, steps=True):
    rows = file_rows() + goal_rows() + family_rows() + tool_rows()
    if steps: rows += step_rows(oi)
    return rows


def to_api(row, oi):
    """(API graph or None, conversion problems, format), built the way a run builds it: a UI graph through apps.build_graph, and a family run also through fill_dynamic."""
    g = row.get("graph")
    if g is None: return None, [], "missing"
    if is_api(g): return g, [], "api"
    if isinstance(g, dict) and isinstance(g.get("nodes"), list):
        from studio import apps as A
        from studio.ui2api import ui_to_api
        try:
            api, probs = ui_to_api(json.loads(json.dumps(g)), oi)
            if probs: return api, list(probs), "ui"
            api = A.build_graph(row["path"], {}, oi)
            if row.get("target") == "family": A.fill_dynamic(api, oi)
            return api, [], "ui"
        except Exception as e: return None, [f"the UI graph could not be converted: {str(e)[:160]}"], "ui"
    return None, [], "other"


def family_view(family, instances=None, models=None):
    """Model names a family instance lists on top of the main library: each folder its extra_model_paths.yaml adds, walked, as names relative to that folder."""
    try:
        from psn import instances as I
        instances = instances or I.INSTANCES; models = models or I.MODELS; slug = I.slug(family)
    except Exception: return set()
    out = set(); p = os.path.join(instances, slug, "extra_model_paths.yaml")
    try: lines = open(p, encoding="utf-8").read().splitlines()
    except OSError: return out
    base = models
    for l in lines:
        t = l.strip()
        if t.startswith("base_path:"): base = t.split(":", 1)[1].strip()
    for l in lines:
        t = l.strip()
        if not t or t.endswith(":") or t.endswith("|") or ":" in t or t.startswith("#"): continue
        root = os.path.join(base, t)
        for dp, _, fn in os.walk(root, followlinks=True):
            for f in fn:
                if MODEL_FILE.search(f): out.add(os.path.relpath(os.path.join(dp, f), root))
    return out
