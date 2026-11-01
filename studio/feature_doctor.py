"""Graph Doctor: paste a broken ComfyUI workflow and read what is wrong, in plain words, with a concrete fix for each problem.
Order of work: rules against this ComfyUI's real /object_info decide what is wrong and what the fix is. The Sampling Atlas then adds facts about the samplers and schedulers in the graph. The language model is optional, and only rewords: it cannot add, remove or change a fix.
Nothing is ever applied by itself. Every fix is listed with its before and after, and /api/doctor/fix applies only the ones named in the request, after the same check has found them again."""
import base64, binascii, copy, difflib, hashlib, io, json, os, re, urllib.request
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from studio.model_sources import source
from studio.names import MODEL_FILE, same_model, swap_ok

router = APIRouter(prefix="/api/doctor")
PAGE = {"tab": "doctor", "label": "Graph Doctor", "title": ["Graph Doctor", "A broken graph in. A plain answer out.", "Paste or drop a ComfyUI workflow. It is checked against the nodes this ComfyUI really has, and nothing changes until you say so."], "module": "doctor.js", "export": "GraphDoctor", "css": "doctor.css"}
ATLAS = Path(__file__).resolve().parent / "sampling_lab" / "atlas.json"
MAX_BYTES = 8 * 2**20; MAX_NODES = 5000; NAME_CUTOFF = 0.8; ORDER = {"error": 0, "warning": 1, "info": 2}
_cache: dict = {}


def _comfy_url() -> str: return os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/")


def object_info():
    """The real node list, or None when ComfyUI cannot be asked. Nothing here falls back to a stored copy: a stale list would give wrong answers."""
    try:
        with urllib.request.urlopen(_comfy_url() + "/object_info", timeout=30) as r: return json.load(r)
    except Exception: return None


# ---------- reading what was pasted ----------
def read_text(text: str):
    """-> (object, None) or (None, problem words)."""
    t = (text or "").strip()
    if not t: return None, "There is nothing here yet. Paste a workflow, or drop its JSON or PNG file."
    try: return json.loads(t), None
    except ValueError as e: return None, f"This is not valid JSON: {e.msg}, at line {e.lineno}, column {e.colno}. A cut-off paste is the usual reason; copy the whole file."


def read_png(data: bytes):
    """A ComfyUI PNG keeps its graph in text chunks. -> (object, None) or (None, why)."""
    from PIL import Image, UnidentifiedImageError
    try: info = Image.open(io.BytesIO(data)).info
    except (UnidentifiedImageError, OSError): return None, "This file is not a readable picture."
    for k in ("prompt", "workflow"):
        if isinstance(info.get(k), str): return read_text(info[k])
    return None, "This picture has no graph in it. ComfyUI saves one in PNGs it writes, but sites and editors usually strip it."


def shape(obj):
    """-> ('api', graph) / ('ui', workflow) / (None, why)."""
    if not isinstance(obj, dict): return None, "A ComfyUI workflow is a JSON object, and this is a list or a single value."
    if isinstance(obj.get("nodes"), list): return "ui", obj
    if isinstance(obj.get("prompt"), dict): return shape(obj["prompt"])
    if isinstance(obj.get("workflow"), dict): return shape(obj["workflow"])
    nodes = {k: v for k, v in obj.items() if isinstance(v, dict) and "class_type" in v}
    if nodes and len(nodes) == len(obj): return "api", obj
    if nodes: return "api", nodes
    return None, "This JSON does not look like a ComfyUI workflow: it has neither nodes with a class_type nor a nodes list."


# ---------- reading /object_info ----------
def _inputs(info: dict, group=None) -> dict:
    i = info.get("input") or {}
    return i.get(group) or {} if group else {**(i.get("required") or {}), **(i.get("optional") or {})}


def _options(spec):
    if isinstance(spec, list) and spec:
        if isinstance(spec[0], list): return spec[0]
        if spec[0] == "COMBO" and len(spec) > 1 and isinstance(spec[1], dict): return spec[1].get("options")
    return None


def _kind(spec):
    return spec[0] if isinstance(spec, list) and spec and isinstance(spec[0], str) else "COMBO" if _options(spec) is not None else None


def _opts(spec) -> dict: return spec[1] if isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict) else {}


WIDGET = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}


def _is_link(v): return isinstance(v, list) and len(v) == 2 and isinstance(v[1], int) and isinstance(v[0], (str, int))


def _fits(have, want) -> bool:
    if have in (None, "*") or want in (None, "*") or str(have).startswith("COMFY_") or str(want).startswith("COMFY_"): return True      # a V3 match-type output takes its type from what it is wired to
    return bool(set(str(have).split(",")) & set(str(want).split(",")))


def _outs(info) -> list: return [o if isinstance(o, str) else "COMBO" for o in info.get("output") or []]


def _sid(*parts) -> str: return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:10]


def _problem(rule, severity, node, cls, title, why, fix=None, inp=None, how=""):
    return {"id": _sid(rule, node, inp, cls), "rule": rule, "severity": severity, "node": node, "class": cls, "input": inp, "title": title, "why": why, "how": how, "fix": fix, "source": "rule"}


# ---------- the rules ----------
def _sole_source(graph, oi, want, skip):
    """The one output in the graph with this type. Two or more means a person has to choose, so there is no fix to offer."""
    found = []
    for nid, n in graph.items():
        if nid == skip: continue
        for slot, t in enumerate(_outs(oi.get(n.get("class_type")) or {})):
            if t == want: found.append((nid, slot, n.get("class_type")))
    return found[0] if len(found) == 1 else None


def _same_model_choice(cls, v, opts):
    fit = [o for o in opts if isinstance(o, str) and same_model(v, o) and swap_ok(cls, v, o)]
    return max(fit, key=lambda o: difflib.SequenceMatcher(None, v, o).ratio()) if fit else None


def _model_problem(nid, cls, k, v, opts):
    name = str(v).replace("\\", "/").split("/")[-1]; base_match = [o for o in opts if isinstance(o, str) and o.replace("\\", "/").split("/")[-1] == name]
    if base_match: return _problem("model_folder", "error", nid, cls, f"{name} is in a different folder here", f"This ComfyUI lists it as {base_match[0]}. The graph asks for {v}, so ComfyUI will refuse it.", {"op": "set", "node": nid, "input": k, "before": v, "after": base_match[0]}, k, "Use the path this ComfyUI lists.")
    same = _same_model_choice(cls, v, opts)
    if same: return _problem("model_precision", "error", nid, cls, f"{name} is not installed, but the same model is", f"{same} is the same model in another precision. It is your choice whether that is close enough: results can differ.", {"op": "set", "node": nid, "input": k, "before": v, "after": same}, k, f"Switch to {same}.")
    src = source(name)
    if src: how = f"Download it from {src['url']}" + (f" into your {src['dir']} folder" if src.get("dir") else "") + (" (you have to accept its licence first)" if src.get("gated") else "") + ", then check again."
    else: how = "The studio does not know where this file comes from. Look for it under its exact name on the site you got the workflow from, then check again."
    return _problem("model_missing", "error", nid, cls, f"{name} is not installed", f"{cls}.{k} needs this file and ComfyUI cannot find it. The doctor will not swap in a different model.", None, k, how)


def check_values(nid, n, info, graph, oi) -> list:
    """Inputs of one node that exists, against its real schema."""
    out = []; cls = n.get("class_type"); ins = n.get("inputs") if isinstance(n.get("inputs"), dict) else {}; want = _inputs(info)
    for k, spec in _inputs(info, "required").items():
        if k in ins or any(i.startswith(k + ".") for i in ins): continue
        kind, o = _kind(spec), _opts(spec)
        if "default" in o: continue
        options = _options(spec)
        if options is not None and len(options) == 1: out.append(_problem("missing_choice", "error", nid, cls, f"{cls} is missing {k}", "It has only one possible choice here.", {"op": "set", "node": nid, "input": k, "before": None, "after": options[0]}, k, f"Set it to {options[0]}."))
        elif options is not None: out.append(_problem("missing_choice", "error", nid, cls, f"{cls} is missing {k}", "It is a required choice with no default, and the doctor will not pick for you.", None, k, "Pick one of: " + ", ".join(map(str, options[:8])) + ("." if len(options) <= 8 else ", and more.")))
        elif kind not in WIDGET:
            s = _sole_source(graph, oi, kind, nid)
            if s: out.append(_problem("missing_link", "error", nid, cls, f"{cls} has nothing plugged into {k}", f"It needs a {kind}. Only one node in this graph makes one: {s[2]} (node {s[0]}).", {"op": "set", "node": nid, "input": k, "before": None, "after": [s[0], s[1]]}, k, f"Connect it to {s[2]}."))
            else: out.append(_problem("missing_link", "error", nid, cls, f"{cls} has nothing plugged into {k}", f"It needs a {kind}, and either no node here makes one or several do.", None, k, f"Add or choose a node that outputs {kind} and connect it."))
        else: out.append(_problem("missing_value", "error", nid, cls, f"{cls} is missing {k}", f"It needs a {kind} value and has no default.", None, k, f"Type a {kind.lower()} value for {k}."))
    for k, v in ins.items():
        spec = want.get(k.split(".")[0] if "." in k else k)
        if spec is None:
            if "." not in k and _inputs(info): out.append(_problem("unknown_input", "warning", nid, cls, f"{cls} has no input called {k}", "The node may have changed since this workflow was saved. ComfyUI ignores it, so it does nothing.", {"op": "remove", "node": nid, "input": k, "before": v, "after": None}, k, f"Remove {k}."))
            continue
        if isinstance(v, str) and "${" in v: continue                         # a placeholder a page fills in later: not a value yet
        kind, o, options = _kind(spec), _opts(spec), _options(spec)
        if "." in k or str(kind).startswith("COMFY_"): kind, options = None, None     # the parts of a V3 dynamic input have types of their own, which /object_info does not spell out here
        if _is_link(v):
            src = graph.get(str(v[0])); wanted = kind
            if src is None:
                s = _sole_source(graph, oi, wanted, nid) if wanted else None
                out.append(_problem("link_gone", "error", nid, cls, f"{cls}.{k} is plugged into a node that is not there", f"It points at node {v[0]}, which is not in this graph." + (f" Only {s[2]} (node {s[0]}) makes a {wanted} here." if s else ""), {"op": "set", "node": nid, "input": k, "before": v, "after": [s[0], s[1]]} if s else None, k, f"Connect it to {s[2]}." if s else f"Connect it to a node that outputs {wanted}.")); continue
            info2 = oi.get(src.get("class_type"))
            if not info2: continue
            outs = _outs(info2)
            if v[1] >= len(outs) or v[1] < 0:
                fit = next((i for i, t in enumerate(outs) if _fits(t, wanted)), None)
                out.append(_problem("slot_gone", "error", nid, cls, f"{cls}.{k} reads output {v[1]} of {src['class_type']}, which has {len(outs)}", "Output numbers start at 0, and old workflows sometimes keep a number from before a node changed.", {"op": "set", "node": nid, "input": k, "before": v, "after": [v[0], fit]} if fit is not None else None, k, f"Use output {fit} ({outs[fit]})." if fit is not None else "Connect it to another output.")); continue
            if not _fits(outs[v[1]], wanted) and not (options is not None and outs[v[1]] in ("STRING", "COMBO")):
                fit = next((i for i, t in enumerate(outs) if _fits(t, wanted)), None); s = None if fit is not None else _sole_source(graph, oi, wanted, nid)
                after = [v[0], fit] if fit is not None else [s[0], s[1]] if s else None
                out.append(_problem("wrong_type", "error", nid, cls, f"{cls}.{k} wants {wanted} but gets {outs[v[1]]}", f"{src['class_type']} output {v[1]} is {outs[v[1]]}.", {"op": "set", "node": nid, "input": k, "before": v, "after": after} if after else None, k, f"Use output {fit} of the same node." if fit is not None else f"Connect it to {s[2]}." if s else f"Connect it to a node that outputs {wanted}."))
            continue
        if options is not None and not isinstance(v, list):
            if v in options: continue
            if isinstance(v, str) and MODEL_FILE.search(v): out.append(_model_problem(nid, cls, k, v, options)); continue
            close = difflib.get_close_matches(str(v), [str(x) for x in options], 1, NAME_CUTOFF)
            if not any(isinstance(x, str) for x in options): continue
            if cls in ("LoadImage", "LoadVideo", "LoadAudio"): out.append(_problem("input_file", "warning", nid, cls, f"{v} is not in your input folder", "This is the file the workflow's author used. It did not come with the workflow.", None, k, "Upload your own file, or pick one you have.")); continue
            out.append(_problem("not_a_choice", "error", nid, cls, f"{v!r} is not a choice for {cls}.{k}", "ComfyUI will refuse this value.", {"op": "set", "node": nid, "input": k, "before": v, "after": close[0]} if close else None, k, f"Use {close[0]}." if close else "Pick one of: " + ", ".join(map(str, options[:8])) + ("." if len(options) <= 8 else ", and more.")))
            continue
        if kind in ("INT", "FLOAT"):
            if isinstance(v, str) and v.strip() and "${" not in v:
                try: num = int(v) if kind == "INT" else float(v)
                except ValueError: out.append(_problem("not_a_number", "error", nid, cls, f"{cls}.{k} should be a number", f"It holds the text {v!r}.", None, k, f"Type a whole number for {k}." if kind == "INT" else f"Type a number for {k}.")); continue
                out.append(_problem("text_number", "warning", nid, cls, f"{cls}.{k} is a number stored as text", f"It holds {v!r}. ComfyUI usually copes, but other tools do not.", {"op": "set", "node": nid, "input": k, "before": v, "after": num}, k, f"Store it as {num}.")); v = num
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                lo, hi = o.get("min"), o.get("max")
                if kind == "INT" and isinstance(v, float) and not v.is_integer(): out.append(_problem("not_whole", "error", nid, cls, f"{cls}.{k} must be a whole number", f"It holds {v}.", {"op": "set", "node": nid, "input": k, "before": v, "after": round(v)}, k, f"Use {round(v)}."))
                elif lo is not None and v < lo: out.append(_problem("too_low", "error", nid, cls, f"{cls}.{k} is below its minimum", f"It holds {v} and the node allows {lo} at least.", {"op": "set", "node": nid, "input": k, "before": v, "after": lo}, k, f"Use {lo}."))
                elif hi is not None and v > hi: out.append(_problem("too_high", "error", nid, cls, f"{cls}.{k} is above its maximum", f"It holds {v} and the node allows {hi} at most.", {"op": "set", "node": nid, "input": k, "before": v, "after": hi}, k, f"Use {hi}."))
    return out


def check_flow(graph, oi) -> list:
    """Across the graph: a cycle, no output at all, nodes nothing reads."""
    out = []; links = {nid: [str(v[0]) for v in (n.get("inputs") or {}).values() if _is_link(v) and str(v[0]) in graph] for nid, n in graph.items() if isinstance(n, dict)}
    seen, stack = set(), set()
    def walk(x):
        if x in stack: return x
        if x in seen: return None
        seen.add(x); stack.add(x)
        for y in links.get(x, []):
            hit = walk(y)
            if hit: return hit
        stack.discard(x); return None
    import sys
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 2 * len(graph) + 100))
    for nid in links:
        hit = walk(nid)
        if hit: out.append(_problem("cycle", "error", hit, graph[hit].get("class_type"), f"Node {hit} feeds back into itself", "ComfyUI runs nodes in order, so a loop in the wiring can never start.", None, None, "Break the loop by disconnecting one link in it.")); break
    known = {nid: oi.get(n.get("class_type")) for nid, n in graph.items() if isinstance(n, dict)}
    sinks = [nid for nid, i in known.items() if i and i.get("output_node")]
    if not sinks and all(known.values()):
        used = {(str(v[0]), v[1]) for n in graph.values() for v in (n.get("inputs") or {}).values() if _is_link(v)}
        free = [(nid, slot) for nid, i in known.items() for slot, t in enumerate(_outs(i)) if t == "IMAGE" and (nid, slot) not in used]
        fix = None; how = "Add a save or preview node at the end."
        if len(free) == 1 and "SaveImage" in oi:
            new = str(max([int(k) for k in graph if str(k).isdigit()] or [0]) + 1); fix = {"op": "add", "node": new, "input": None, "before": None, "after": {"class_type": "SaveImage", "inputs": {"images": [free[0][0], free[0][1]], "filename_prefix": "ComfyUI"}}}; how = f"Add a SaveImage node reading node {free[0][0]}."
        out.append(_problem("no_output", "error", None, None, "Nothing in this graph saves or shows a result", "ComfyUI only runs what leads to an output node, so it would refuse this graph.", fix, None, how))
    elif sinks:
        reach, todo = set(), list(sinks)
        while todo:
            x = todo.pop()
            if x not in reach: reach.add(x); todo += links.get(x, [])
        idle = [nid for nid in links if nid not in reach]
        if idle: out.append(_problem("idle_nodes", "info", None, None, f"{len(idle)} {'node does' if len(idle) == 1 else 'nodes do'} not lead to a result", "ComfyUI skips them. That is fine if you meant it: " + ", ".join(f"{graph[x].get('class_type')} ({x})" for x in idle[:6]) + ".", None, None, "Connect them, or leave them."))
    return out


def diagnose(graph, oi) -> list:
    out = []
    for nid, n in graph.items():
        if not isinstance(n, dict) or not n.get("class_type"): out.append(_problem("no_class", "error", nid, None, f"Node {nid} has no class_type", "Without one, ComfyUI cannot tell what the node is.", {"op": "remove_node", "node": nid, "input": None, "before": n, "after": None}, None, "Remove the node.")); continue
        info = oi.get(n["class_type"])
        if info: out += check_values(nid, n, info, graph, oi); continue
        close = difflib.get_close_matches(n["class_type"], list(oi), 1, 0.88); cls = n["class_type"]
        fits = close and set(_inputs(oi[close[0]], "required")) <= set(n.get("inputs") or {}) | {k for k, s in _inputs(oi[close[0]], "required").items() if "default" in _opts(s)}
        out.append(_problem("unknown_node", "error", nid, cls, f"{cls} is not installed", (f"It looks like {close[0]}, whose inputs fit." if fits else "It comes from a node pack this ComfyUI does not have, or an old name.") + " A graph with a missing node type cannot run.", {"op": "rename", "node": nid, "input": None, "before": cls, "after": close[0]} if fits else None, None, f"Use {close[0]}." if fits else f"Find the pack that provides {cls}. If you install one, try it in Pack Lab first, not on your main ComfyUI."))
    out += check_flow(graph, oi)
    return sorted(out, key=lambda p: (ORDER[p["severity"]], str(p["node"])))


def apply_fixes(graph: dict, problems: list, ids) -> tuple:
    """Applies only the named fixes. -> (new graph, what changed). A copy: the input stays as it was."""
    new = copy.deepcopy(graph); changes = []
    for p in problems:
        f = p.get("fix")
        if p["id"] not in ids or not f: continue
        if f["op"] == "set": new[f["node"]].setdefault("inputs", {})[f["input"]] = f["after"]
        elif f["op"] == "remove": new[f["node"]]["inputs"].pop(f["input"], None)
        elif f["op"] == "rename": new[f["node"]]["class_type"] = f["after"]
        elif f["op"] == "add": new[f["node"]] = f["after"]
        elif f["op"] == "remove_node": new.pop(f["node"], None)
        changes.append({"problem": p["id"], "title": p["title"], **f})
    return new, changes


# ---------- second: facts from the Sampling Atlas ----------
def atlas_index() -> dict:
    if "atlas" in _cache: return _cache["atlas"]
    idx = {}
    try:
        for e in json.loads(ATLAS.read_text(encoding="utf-8")).get("entries", []):
            if not e.get("in_core"): continue
            ref = e.get("core_ref") or {}
            for key in ("sampler_name", "scheduler", "node"):
                if ref.get(key): idx.setdefault(str(ref[key]), e)
            if e.get("family") == "scheduler": idx.setdefault(str(e.get("name")), e)
    except (OSError, ValueError): pass
    _cache["atlas"] = idx; return idx


def atlas_facts(graph) -> list:
    """What the atlas says about the samplers, schedulers and sampling nodes in this graph, with its own proof label."""
    idx, out, seen = atlas_index(), [], set()
    for nid, n in graph.items():
        if not isinstance(n, dict): continue
        for name in [n.get("class_type"), *[v for k, v in (n.get("inputs") or {}).items() if k in ("sampler_name", "scheduler") and isinstance(v, str)]]:
            e = idx.get(str(name))
            if e and e["id"] not in seen:
                seen.add(e["id"]); out.append({"entry": e["id"], "name": e.get("name"), "for": str(name), "node": nid, "plain": e.get("plain"), "note": e.get("surprise") or "", "label": e.get("label"), "source": "atlas", "family": e.get("family")})
    return out[:12]


# ---------- third, optional: rewording ----------
def _chat(messages):
    from studio import crew
    return crew.default_chat(messages)


def reword(problems: list, chat=None) -> dict:
    """Asks the language model for one simpler sentence per problem. It gets the words only, its answer goes through json, and it can change nothing but the wording shown beside each problem."""
    chat = chat or _chat; want = [{"id": p["id"], "title": p["title"], "why": p["why"]} for p in problems][:30]
    if not want: return {"available": True, "words": {}}
    try: raw = chat([{"role": "system", "content": 'Rewrite each ComfyUI problem as one short, friendly sentence for a beginner. Never suggest a different fix. Reply with one JSON object {"id": "sentence"}.'}, {"role": "user", "content": json.dumps(want)}])
    except Exception: return {"available": False, "words": {}, "why": "The language model is off, so these are the rule's own words. Nothing else depends on it."}
    m = re.search(r"\{.*\}", raw or "", re.S)
    try: got = json.loads(m.group(0)) if m else {}
    except ValueError: got = {}
    ids = {p["id"] for p in problems}
    return {"available": True, "words": {k: str(v)[:300] for k, v in got.items() if k in ids and isinstance(v, str)}}


# ---------- the routes ----------
def load(b: dict):
    """The request's text or file -> (format, graph or workflow). Raises what the page shows."""
    if isinstance(b.get("png"), str):
        try: data = base64.b64decode(b["png"], validate=True)
        except (ValueError, binascii.Error): raise HTTPException(400, "The file did not arrive whole. Try it again.") from None
        if len(data) > 64 * 2**20: raise HTTPException(413, "That picture is over 64 MB.")
        obj, why = read_png(data)
    else:
        if not isinstance(b.get("text"), str): raise HTTPException(400, "Paste a workflow.")
        if len(b["text"]) > MAX_BYTES: raise HTTPException(413, "That is over 8 MB, far bigger than a workflow.")
        obj, why = read_text(b["text"])
    if why: raise HTTPException(400, why)
    fmt, got = shape(obj)
    if fmt is None: raise HTTPException(400, got)
    if len(got if fmt == "api" else got["nodes"]) > MAX_NODES: raise HTTPException(413, f"That has over {MAX_NODES} nodes.")
    return fmt, got


def examine(fmt, got, oi) -> dict:
    extra = []; graph = got
    if fmt == "ui":
        from studio.ui2api import ui_to_api
        try: graph, probs = ui_to_api(got, oi)
        except Exception as e: raise HTTPException(400, f"This saved-from-the-canvas workflow could not be read: {type(e).__name__}: {str(e)[:200]}") from None
        extra = [_problem("ui_convert", "warning", None, None, "Part of this canvas workflow could not be converted", str(p)[:300], None, None, "Open it in ComfyUI and export it in API format.") for p in probs or []]
    problems = extra + diagnose(graph, oi)
    return {"checked_against": "this ComfyUI", "format": fmt, "nodes": len(graph), "graph": graph, "problems": problems, "fixable": sum(1 for p in problems if p.get("fix")), "errors": sum(1 for p in problems if p["severity"] == "error"), "atlas": atlas_facts(graph), "converted": fmt == "ui"}


def _check(b: dict) -> dict:
    fmt, got = load(b); oi = object_info()
    if oi is None: raise HTTPException(503, "ComfyUI is not reachable, so the graph was not checked. The doctor only answers from the nodes your ComfyUI really has. Start it and press Check again.")
    return examine(fmt, got, oi)


async def _json(req: Request) -> dict:
    try: b = await req.json()
    except ValueError: raise HTTPException(400, "Send a JSON object.") from None
    if not isinstance(b, dict): raise HTTPException(400, "Send a JSON object.")
    return b


@router.post("/check")
async def check(req: Request): return await run_in_threadpool(_check, await _json(req))


def _fix(b: dict) -> dict:
    ids = b.get("fixes")
    if not isinstance(ids, list) or not ids or not all(isinstance(x, str) for x in ids): raise HTTPException(400, "Choose at least one fix. Nothing changes unless you name it.")
    fmt, got = load(b); oi = object_info()
    if oi is None: raise HTTPException(503, "ComfyUI is not reachable, so no fix was made.")
    seen = examine(fmt, got, oi); known = {p["id"] for p in seen["problems"] if p.get("fix")}; stale = [x for x in ids if x not in known]
    if stale: raise HTTPException(409, "The graph changed since it was checked, so a chosen fix no longer applies. Press Check again.")
    new, changes = apply_fixes(seen["graph"], seen["problems"], set(ids)); after = diagnose(new, oi)
    return {"graph": new, "changes": changes, "left": after, "errors_left": sum(1 for p in after if p["severity"] == "error"), "format": "api"}


@router.post("/fix")
async def fix(req: Request): return await run_in_threadpool(_fix, await _json(req))


@router.post("/reword")
async def reword_route(req: Request):
    b = await _json(req); probs = b.get("problems")
    if not isinstance(probs, list): raise HTTPException(400, "Send the problems.")
    return await run_in_threadpool(reword, [p for p in probs if isinstance(p, dict) and isinstance(p.get("id"), str) and isinstance(p.get("title"), str) and isinstance(p.get("why"), str)])


@router.get("/example")
def example():
    """A small broken graph to try the page with. Every fault in it is the doctor's to find, none is hidden."""
    return {"name": "A picture graph with five faults", "text": json.dumps({"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}}, "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a lighthouse at dawn", "clip": ["1", 1]}}, "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["1", 9]}}, "4": {"class_type": "EmptyLatentImage", "inputs": {"width": "1024", "height": 1024, "batch_size": 1}}, "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0], "seed": 7, "steps": 20, "cfg": 7.0, "sampler_name": "eular", "scheduler": "normal", "denoise": 1.5}}, "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}}}, indent=1)}
