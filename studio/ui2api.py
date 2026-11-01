"""Convert a ComfyUI UI-format workflow (a 'template' JSON: nodes, links, widgets_values, optional sub-graphs) into an API-format graph, using the server's /object_info to map widget values onto input names.
Sub-graphs are inlined recursively (their promoted values travel in the instance node's `proxyWidgets` + `widgets_values`; ids -10 / -20 are the sub-graph's input / output boundary). Reroutes are resolved, notes dropped,
muted nodes dropped. Anything it cannot resolve is returned in `problems`, never silently mangled. ui_to_api(ui, oi) -> (graph, problems)."""
import ast
SKIP = {"Reroute", "MarkdownNote", "Note", "PrimitiveNode"}
WIDGET_TYPES = ("INT", "FLOAT", "STRING", "BOOLEAN", "COMBO", "COLOR", "LOAD_3D")      # COLOR and LOAD_3D store a value in widgets_values like any other widget (RenderSplat.background, Save3DAdvanced.viewport_state)
class Const:
    def __init__(self, v): self.v = v
def _widget_names(info):
    names = []
    for group in ("required", "optional"):
        for name, spec in (info.get("input", {}).get(group) or {}).items():
            t = spec[0]; opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
            if opts.get("forceInput"): continue
            if isinstance(t, list) or t in WIDGET_TYPES: names.append((name, bool(opts.get("control_after_generate"))))
    return names
DYNAMIC = "COMFY_DYNAMICCOMBO_V3"
def _assign_widgets(info, wv, inputs):
    """Stored widget values go in widget order. A V3 dynamic combo stores its choice, then that choice's own widgets: those go in as parent.child, the name the server reads."""
    i = 0
    def take(spec_inputs, prefix=""):
        nonlocal i
        for group in ("required", "optional"):
            for name, spec in (spec_inputs.get(group) or {}).items():
                t = spec[0]; opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}; key = prefix + name
                if opts.get("forceInput") or i >= len(wv): continue
                if t == DYNAMIC:
                    val = wv[i]; i += 1; inputs.setdefault(key, val)
                    for o in opts.get("options") or []:
                        if o.get("key") == val: take(o.get("inputs") or {}, key + ".")
                elif isinstance(t, list) or t in WIDGET_TYPES:
                    inputs.setdefault(key, wv[i]); i += 1
                    if opts.get("control_after_generate"): i += 1
    take(info.get("input", {}))
def _dynamic_defaults(info, inputs):
    """A required dynamic combo the template left implicit takes its default or first option, and that option's required widgets their defaults."""
    for name, spec in (info.get("input", {}).get("required") or {}).items():
        opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
        if spec[0] != DYNAMIC or not opts.get("options"): continue
        cur = inputs.get(name, opts.get("default", opts["options"][0].get("key"))); inputs.setdefault(name, cur)
        for o in opts["options"]:
            if o.get("key") != cur: continue
            for sub, sp in ((o.get("inputs") or {}).get("required") or {}).items():
                so = sp[1] if len(sp) > 1 and isinstance(sp[1], dict) else {}; ch = sp[0] if isinstance(sp[0], list) else so.get("options")
                if "default" in so: inputs.setdefault(f"{name}.{sub}", so["default"])
                elif ch: inputs.setdefault(f"{name}.{sub}", ch[0])
def promoted_widgets(S):
    """Names of a sub-graph's inputs that feed a widget on an inner node, in order."""
    inner = {x["id"]: x for x in S.get("nodes", [])}; L = _norm_links(S.get("links")); out = []
    for slot, si in enumerate(S.get("inputs", [])):
        for (o, os_, t, ts) in L.values():
            if o == -10 and os_ == slot and t in inner and ts < len(inner[t].get("inputs") or []) and inner[t]["inputs"][ts].get("widget"): out.append(si["name"]); break
    return out
def _norm_links(links):
    out = {}
    for l in links or []:
        if isinstance(l, dict): out[l["id"]] = (l["origin_id"], l["origin_slot"], l["target_id"], l["target_slot"])
        else: out[l[0]] = (l[1], l[2], l[3], l[4])
    return out
def ui_to_api(ui, oi, exposed=None):
    """exposed (optional dict) is filled with {(top_level_node_id, widget_name): [(api_node_id, input_name), ...]} so callers can set the values an app exposes."""
    problems = []; api = {}; subs = {s["id"]: s for s in (ui.get("definitions", {}).get("subgraphs") or [])}
    def convert(nodes_list, links, prefix, boundary_in, overrides):
        by_id = {n["id"]: n for n in nodes_list}; L = _norm_links(links); memo = {}
        def link_src(link_id, depth=0):
            if link_id is None or link_id not in L or depth > 60: return None
            o, os_ = L[link_id][0], L[link_id][1]; return src(o, os_, depth + 1)
        def src(o, os_, depth=0):
            if o == -10: return boundary_in(os_)
            n = by_id.get(o)
            if n is None: return None
            if n["type"] == "Reroute":
                ins = n.get("inputs") or []; return link_src(ins[0].get("link"), depth + 1) if ins else None
            if n["type"] == "PrimitiveNode":
                wv = n.get("widgets_values") or []; return Const(wv[0] if wv else None)
            if n.get("mode") == 4:                                       # a bypassed node hands its matching input straight through
                outs = n.get("outputs") or []; want = outs[os_].get("type") if os_ < len(outs) else None
                for inp in n.get("inputs") or []:
                    if inp.get("type") == want and inp.get("link") is not None: return link_src(inp["link"], depth + 1)
                return None
            if n["type"] in subs:
                if o not in memo: memo[o] = expand(n)
                outs = memo[o]; return outs[os_] if os_ < len(outs) else None
            return [prefix + str(o), os_]
        def expand(n):
            S = subs[n["type"]]; proxy = (n.get("properties") or {}).get("proxyWidgets") or []
            if isinstance(proxy, str):
                try: proxy = ast.literal_eval(proxy)
                except Exception: proxy = []
            vals = n.get("widgets_values") or []; subvals = {}; ov = {}
            for idx, pair in enumerate(proxy):
                if idx >= len(vals) or not pair or len(pair) < 2: continue
                nid_s, name = pair[0], pair[1]
                if str(name).startswith("control_after_g"): continue
                if str(nid_s) == "-1": subvals[name] = vals[idx]
                else: ov[(int(nid_s), name)] = vals[idx]
            if not proxy:                                                # newer templates keep no proxy list: the values follow the sub-graph's own inputs that feed a widget
                idx = 0
                for name in promoted_widgets(S):
                    if idx >= len(vals): break
                    subvals[name] = vals[idx]; idx += 1
                    if idx < len(vals) and vals[idx] in ("fixed", "increment", "decrement", "randomize"): idx += 1     # a seed's control_after_generate takes a slot too
            ext = {i["name"]: i.get("link") for i in (n.get("inputs") or []) if i.get("link") is not None}
            def boundary(slot):
                name = S["inputs"][slot]["name"] if slot < len(S.get("inputs", [])) else None
                if name in ext: return link_src(ext[name])
                return Const(subvals[name]) if name in subvals else None
            inner_L = _norm_links(S.get("links")); outs_src = {}
            if exposed is not None and prefix == "":
                inner_nodes = {x["id"]: x for x in S.get("nodes", [])}
                for (o, os_, t, ts) in inner_L.values():
                    if o == -10 and os_ < len(S.get("inputs", [])) and t in inner_nodes:
                        ins = inner_nodes[t].get("inputs") or []
                        if ts < len(ins): exposed.setdefault((str(n["id"]), S["inputs"][os_]["name"]), []).append((f"{n['id']}:{t}", ins[ts]["name"]))
                for (idx, pair) in enumerate(proxy):
                    if pair and len(pair) >= 2 and str(pair[0]) != "-1": exposed.setdefault((str(n["id"]), pair[1]), []).append((f"{n['id']}:{pair[0]}", pair[1]))
            def inner_out(slot):
                for (o, os_, t, ts) in inner_L.values():
                    if t == -20 and ts == slot: return (o, os_)
                return None
            res = convert(S.get("nodes", []), S.get("links", []), f"{prefix}{n['id']}:", boundary, ov)
            outs = []
            for j in range(len(S.get("outputs", []))):
                io = inner_out(j)
                outs.append(res(io[0], io[1]) if io else None)
            return outs
        for nid, n in by_id.items():
            t = n["type"]
            if t in SKIP or t in subs or n.get("mode") in (2, 4): continue
            if t not in oi: problems.append(f"{prefix}{nid}: unknown node type {t}"); continue
            inputs = {}
            for inp in n.get("inputs") or []:
                if inp.get("link") is not None:
                    s = link_src(inp["link"])
                    if isinstance(s, Const): inputs[inp["name"]] = s.v
                    elif s: inputs[inp["name"]] = s
            wv = n.get("widgets_values") or []
            if isinstance(wv, dict): inputs.update({k: v for k, v in wv.items() if k not in inputs}); wv = []
            _assign_widgets(oi[t], wv, inputs)
            for name, _ctl in _widget_names(oi[t]):                      # widgets the template left implicit get the node's own default
                spec = (oi[t].get("input", {}).get("required") or {}).get(name)
                if spec is not None and name not in inputs:
                    opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
                    choices = spec[0] if isinstance(spec[0], list) else opts.get("options")
                    if "default" in opts: inputs[name] = opts["default"]
                    elif choices: inputs[name] = choices[0]
            _dynamic_defaults(oi[t], inputs)
            for (oid, wname), val in overrides.items():
                if oid == nid and wname in {w for w, _ in _widget_names(oi[t])}: inputs[wname] = val
            api[prefix + str(nid)] = {"class_type": t, "inputs": inputs}
            if exposed is not None:
                for wname, _c in _widget_names(oi[t]): exposed.setdefault((str(nid), wname), []).append((prefix + str(nid), wname))
        for nid, n in by_id.items():                       # instances nobody referenced still need expanding (e.g. an output node inside)
            if n["type"] in subs and nid not in memo and n.get("mode") not in (2, 4): memo[nid] = expand(n)
        if exposed is not None:                            # a PrimitiveNode's value is editable through every input it feeds (following reroutes)
            def fan(node_id, depth=0):
                out = []
                for (o, os_, t, ts) in L.values():
                    if o != node_id or t not in by_id or depth > 20: continue
                    if by_id[t]["type"] == "Reroute": out += fan(t, depth + 1)
                    else: out.append((t, ts))
                return out
            for pid, pn in by_id.items():
                if pn["type"] != "PrimitiveNode": continue
                for (t, ts) in fan(pid):
                    tn = by_id[t]; ins = tn.get("inputs") or []; iname = ins[ts]["name"] if ts < len(ins) else None
                    if not iname: continue
                    targets = list(exposed.get((str(t), iname), [])) if tn["type"] in subs else [(prefix + str(t), iname)]
                    for key in ("value", iname): exposed.setdefault((str(pid), key), []).extend(targets)
        return lambda o, os_: src(o, os_)
    convert(ui.get("nodes", []), ui.get("links", []), "", lambda slot: None, {})
    outs = [k for k, v in api.items() if oi.get(v["class_type"], {}).get("output_node")]       # keep only what feeds an output node
    keep, stack = set(), list(outs)
    while stack:
        k = stack.pop()
        if k in keep or k not in api: continue
        keep.add(k); stack += [v[0] for v in api[k]["inputs"].values() if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str)]
    if outs: api = {k: v for k, v in api.items() if k in keep}
    for nid, node in api.items():
        for k, v in node["inputs"].items():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0] not in api: problems.append(f"{nid}.{k} points at {v[0]} which was not converted")
    return api, problems
