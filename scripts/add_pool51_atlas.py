#!/usr/bin/env python3
"""Bring the Sampling Lab up to date with the node packs installed on this machine (pool 51), and list everything that runs here.

1. Adds atlas entries drafted by readers of the pack source (JSONL fragments). Every evidence line is checked on disk: the file must
   exist and the symbol must sit within 3 lines of the cited line, or that evidence is dropped; an entry left with no evidence is
   rejected. Pack code is only opened as text, never imported or run, and none of it is copied in.
2. Marks each entry live when a node it names is in this ComfyUI's /object_info.
3. Writes studio/sampling_lab/live.json: every sampler and scheduler name ComfyUI offers here, and every guidance method that runs here,
   with the pack, author, licence, the atlas entry and whether we have a render.
4. Folds the pack renders (scripts/sampling_lab_pack_renders.py) into renders.json and marks the entries they prove.

Usage: SAMPLING_LIBRARY=<node library> SAMPLING_COMFY=<ComfyUI dir> add_pool51_atlas.py <fragments dir> <object_info.json>
       <pool51 STAGED_CLASSES.tsv> <pack renders out.json> <repo root>
"""
import csv, datetime, glob, json, os, re, sys

FRAG, INFO, STAGED, PACK_RENDERS, ROOT = sys.argv[1:6]
LIB = os.environ["SAMPLING_LIBRARY"].rstrip("/") + "/"; COMFY = os.environ["SAMPLING_COMFY"].rstrip("/") + "/"
DATA = os.path.join(ROOT, "studio", "sampling_lab")
ATLAS, RENDERS, LIVE = (os.path.join(DATA, n) for n in ("atlas.json", "renders.json", "live.json"))
FAMILIES = ("sampler", "scheduler", "guidance", "noise", "latent", "math", "patch")
LABELS = ("from code", "measured here", "from pack README claim", "inference")   # an author's docstring counts as their claim
TODAY = datetime.date.today().isoformat()
# Names the readers didn't own, credited to the entries that already describe them.
KNOWN = {"sonar_euler": "sonar-momentum", "sonar_euler_ancestral": "sonar-momentum", "sonar_dpmpp_sde": "sonar-momentum"}

atlas = json.load(open(ATLAS)); info = json.load(open(INFO)); renders = json.load(open(RENDERS))
by_id = {e["id"]: e for e in atlas["entries"]}
staged = {r["link_name"]: r for r in csv.DictReader(open(STAGED), delimiter="\t")}


INSTALLED = sorted(os.listdir(COMFY + "custom_nodes"))
def canonical(pack):
    """The installed folder name for a pack the atlas may have recorded without its owner, e.g. ComfyUI-ppm -> pamparamm__ComfyUI-ppm."""
    if not pack or pack == "core" or pack in INSTALLED: return pack
    tail = pack.split("__")[-1].replace(".disabled", "")
    hits = [n for n in INSTALLED if n.split("__")[-1] == tail]
    return hits[0] if len(hits) == 1 else pack


def licence(pack):
    lic = (staged.get(pack) or {}).get("licence", "")
    lic = re.sub(r"\s*\(.*?\)", "", lic).strip()
    if lic: return lic
    for c in atlas.get("credits", []):
        if c["pack"] == pack or c["pack"].split("__")[-1] == pack.split("__")[-1]: return c.get("licence", "")
    return ""


def author(pack):
    return pack.split("__", 1)[0] if "__" in pack else (json.load(open(os.path.join(DATA, "pack_owners.json"))).get("owners", {}).get(pack, ""))


def where(path):
    """No machine paths in what ships: the pack folder and file, as the existing entries write it."""
    for pre in (LIB + "repos/", LIB + "patched-installed/", LIB + "patched/", COMFY + "custom_nodes/"):
        if path.startswith(pre): return path[len(pre):]
    m = re.match(re.escape(LIB) + r"(?:deploy-backups/[^/]+|pool_sections/[^/]+/packs)/(.+)", path)
    return m.group(1) if m else os.path.basename(path)


_files = {}
def check(ev):
    path, line, sym = ev.get("path", ""), ev.get("line"), str(ev.get("symbol", "")).strip()
    real = os.path.realpath(path)
    if not (real.startswith(LIB) or real.startswith(COMFY)): return None, "outside the source tree"
    if real not in _files:
        try: _files[real] = open(real, errors="replace").read().split("\n")
        except OSError: _files[real] = None
    L = _files[real]
    if L is None: return None, "file not found"
    if not isinstance(line, int) or not 1 <= line <= len(L): return None, "line out of range"
    if not sym: return None, "no symbol"
    win = "\n".join(L[max(0, line - 4):line + 3])
    if sym in win or sym.split("(")[0].split(".")[-1] in win: return {"where": f"{where(real)}:{line}", "symbol": sym}, None
    return None, f"symbol not near line {line}"


def provider(pack, nodes, names, note=""):
    return {"pack": pack, "author": author(pack), "licence": licence(pack), "kind": "original", "verdict": "", "risks": [], "res4lyf": False,
            "nodes": nodes or [], "names": names or [], "note": note or "Read as text from the copy installed on this machine; evidence checked on disk."}


added, extended, rejected, skipped = [], [], [], []
for f in sorted(glob.glob(os.path.join(FRAG, "*.jsonl"))):
    for n, raw in enumerate(open(f, errors="replace"), 1):
        raw = raw.strip()
        if not raw: continue
        try: d = json.loads(raw)
        except ValueError: rejected.append((os.path.basename(f), n, "not JSON")); continue
        if "skipped" in d: skipped += [s for s in d["skipped"] if isinstance(s, list)]; continue
        pack = d.get("pack", "")
        if d.get("add_provider"):
            e = by_id.get(d.get("id"))
            if not e: rejected.append((os.path.basename(f), n, f"no entry {d.get('id')}")); continue
            p = next((p for p in e["providers"] if p["pack"] == pack or p["pack"].split("__")[-1] == pack.split("__")[-1]), None)
            if p: p["nodes"] = sorted(set(p.get("nodes") or []) | set(d.get("nodes") or [])); p["names"] = sorted(set(p.get("names") or []) | set(d.get("names") or []))
            else:
                e["providers"].append(provider(pack, d.get("nodes"), d.get("names"), d.get("note", ""))); e["providers_n"] = len(e["providers"])
                e["licences"] = sorted({p["licence"] for p in e["providers"] if p.get("licence")})
            extended.append(e["id"]); continue
        if not d.get("id") or not d.get("name") or d.get("family") not in FAMILIES or not pack:
            rejected.append((os.path.basename(f), n, "missing id, name, family or pack")); continue
        evs = []
        for ev in d.get("evidence") or []:
            ok, why = check(ev)
            if ok: evs.append(ok)
            else: rejected.append((os.path.basename(f), n, f"{d['id']}: evidence dropped, {why}"))
        if not evs: rejected.append((os.path.basename(f), n, f"{d['id']}: no evidence left, entry rejected")); continue
        eid = d["id"] if d["id"] not in by_id else d["id"] + "-p51"
        p = provider(pack, d.get("nodes"), d.get("names"))
        e = {"id": eid, "name": d["name"], "family": d["family"], "subfamily": d.get("subfamily", ""), "plain": d.get("plain", ""), "math": d.get("math", ""),
             "props": d.get("props") or {}, "evidence": evs, "providers": [p], "providers_n": 1, "in_core": False, "live": False, "needs_pack": True,
             "core_ref": {}, "family_fit": [], "claims": [{"text": c["text"], "label": c.get("label") if c.get("label") in LABELS else "from pack README claim"} for c in d.get("claims") or [] if isinstance(c, dict) and c.get("text")], "label": "from code",
             "surprise": d.get("surprise", ""), "rendered": False, "rendered_ids": [], "risks": [], "flagged_providers": 0,
             "licences": [p["licence"]] if p["licence"] else [], "verdicts": [], "audit": None, "run_patch": "", "run_guider": "", "prefer_model": ""}
        atlas["entries"].append(e); by_id[eid] = e; added.append(eid)

# Every sampler and scheduler name this ComfyUI offers.
def combo(cls, key):
    t = info[cls]["input"]["required"][key]
    return t[0] if isinstance(t[0], list) else t[1].get("options", [])
samplers, schedulers = combo("KSampler", "sampler_name"), combo("KSampler", "scheduler")
offered = set(samplers) | set(schedulers)

# Live here: a node an entry names is in this ComfyUI's /object_info, or a sampler or scheduler name it adds is offered.
classes = set(info)
def live_nodes(e):
    return sorted({n for p in e["providers"] for n in (p.get("nodes") or []) if n in classes and p["pack"] != "core"})
became_live = 0
for e in atlas["entries"]:
    if e.get("in_core"): continue
    now = bool(live_nodes(e)) or any(n in offered for p in e["providers"] if p["pack"] != "core" for n in (p.get("names") or []))
    if now and not e.get("live"): became_live += 1
    e["live"] = now
name_entry, name_pack = {}, {}
for e in atlas["entries"]:
    ref = e.get("core_ref") or {}
    for k in ("sampler_name", "scheduler_name", "scheduler"):
        if ref.get(k) and e.get("in_core"): name_entry.setdefault(ref[k], e["id"]); name_pack.setdefault(ref[k], "core")
    for k in ("sampler_names", "scheduler_names"):
        for nm in ref.get(k) or []:
            if e.get("in_core"): name_entry.setdefault(nm, e["id"]); name_pack.setdefault(nm, "core")
    for p in e["providers"]:
        for nm in p.get("names") or []:
            if p["pack"] == "core": name_entry.setdefault(nm, e["id"]); name_pack.setdefault(nm, "core")
for e in atlas["entries"]:
    for p in e["providers"]:
        for nm in p.get("names") or []:
            if nm not in name_pack or name_pack[nm] != "core": name_entry.setdefault(nm, e["id"]); name_pack.setdefault(nm, p["pack"])
for nm, eid in KNOWN.items():
    if eid in by_id: name_entry.setdefault(nm, eid); name_pack.setdefault(nm, by_id[eid]["providers"][0]["pack"])
for nm in ("simple", "sgm_uniform", "karras", "exponential", "ddim_uniform", "beta", "normal", "linear_quadratic", "kl_optimal"):
    name_pack[nm] = "core"

# A name no entry claims: find the installed pack whose source has it as a quoted string. Text search only; a name found in
# more than one pack stays unattributed rather than guessed.
todo = [n for n in list(samplers) + list(schedulers) if n not in name_pack]
if todo:
    hits = {n: set() for n in todo}; pats = {n: re.compile(r"[\"']" + re.escape(n) + r"[\"']") for n in todo}
    cn = COMFY + "custom_nodes"
    for pack in sorted(os.listdir(cn)):
        if pack.startswith(".") or pack == "__pycache__": continue
        for dp, dn, fn in os.walk(os.path.join(cn, pack), followlinks=True):
            dn[:] = [d for d in dn if d not in (".git", "__pycache__", "node_modules", "tests", "test", "trash")]
            for f in fn:
                if not f.endswith(".py"): continue
                try:
                    if os.path.getsize(os.path.join(dp, f)) > 2_000_000: continue
                    txt = open(os.path.join(dp, f), errors="replace").read()
                except OSError: continue
                for n in todo:
                    if pats[n].search(txt): hits[n].add(pack)
    for n, packs in hits.items():
        if len(packs) == 1: name_pack[n] = packs.pop()

# Renders of pack methods, folded into renders.json.
pack_rows = json.load(open(PACK_RENDERS)) if os.path.exists(PACK_RENDERS) else {}
node_entry = {}
for e in atlas["entries"]:
    for p in e["providers"]:
        if p["pack"] != "core":
            for n in p.get("nodes") or []: node_entry.setdefault(n, e["id"])
keep = [r for r in renders["renders"] if not str(r.get("set", "")).startswith("pack-")]
new_rows = []
for rid, r in pack_rows.items():
    row = {k: r.get(k) for k in ("id", "set", "method", "label", "model", "sampler", "scheduler", "cfg", "patches", "guider", "status", "seconds", "note", "sha256",
                                 "baseline", "brightness", "contrast", "edge", "diff_to_base", "pack", "peak_gib", "error", "pixels")}
    row["seen"] = r.get("seen", ""); row["identical_to"] = []
    if r.get("status") == "rendered": row["url"] = f"sampling_lab/{rid}.jpg"
    eid = None
    if not r.get("baseline"):
        if r.get("wrap"): eid = node_entry.get(r["wrap"][0])
        elif r.get("patches"): eid = node_entry.get(r["patches"][0][0])
        elif r["set"] == "pack-sampler": eid = name_entry.get(r["sampler"])
        elif r["set"] == "pack-scheduler": eid = name_entry.get(r["scheduler"])
    row["entry"] = eid
    if eid and r.get("status") == "rendered":
        e = by_id[eid]; e["rendered"] = True; e["rendered_ids"] = sorted(set(e.get("rendered_ids") or []) | {rid})
    new_rows.append(row)
# A pack set's re-rendered core baseline should match the old core render pixel for pixel when the old one was made the same way.
renders["renders"] = keep + sorted(new_rows, key=lambda r: (r["set"], not r.get("baseline"), r["id"]))
for k, v in {"pack-sampler": "pack-sampler-euler", "pack-scheduler": "pack-scheduler-normal", "pack-guidance": "pack-guidance-cfg-14"}.items():
    if any(r["set"] == k for r in new_rows): renders["bases"][k] = v
ok = [r for r in new_rows if r["status"] == "rendered" and not r.get("baseline")]
renders["packs"] = {"rendered": len(ok), "attempted": len([r for r in new_rows if not r.get("baseline")]), "entries": len({r["entry"] for r in ok if r.get("entry")}),
                    "date": TODAY, "how": "On this machine's own ComfyUI with the packs installed, through the shared GPU gate, one at a time. Same seed, prompt and model as the core renders; each set re-rendered its core baseline first."}

# A name counts as rendered only when a render picked that exact name (not merely another name in the same entry).
shot_s, shot_k = {}, {}
for r in renders["renders"]:
    if r.get("status") != "rendered" or r.get("patches") or r.get("wrap") or r.get("guider"): continue
    if r.get("set") in ("sampler", "pack-sampler", "flow"): shot_s.setdefault(r["sampler"], r["id"])
    if r.get("set") in ("scheduler", "pack-scheduler", "flow"): shot_k.setdefault(r["scheduler"], r["id"])
def row(nm, kind):
    pack = canonical(name_pack.get(nm, "")); eid = name_entry.get(nm); shot = (shot_s if kind == "sampler" else shot_k).get(nm)
    return {"name": nm, "pack": pack, "author": "Comfy Org and contributors" if pack == "core" else author(pack) if pack else "", "licence": "GPL-3.0" if pack == "core" else licence(pack) if pack else "",
            "entry": eid, "rendered": bool(shot), "render": shot}
guid = []
for e in atlas["entries"]:
    if e["family"] != "guidance" or not (e.get("in_core") or e.get("live")): continue
    p = next((q for q in e["providers"] if q["pack"] != "core" and set(q.get("nodes") or []) & classes), e["providers"][0]) if not e.get("in_core") else e["providers"][0]
    cp = canonical(p["pack"])
    guid.append({"entry": e["id"], "name": e["name"], "pack": "core" if e.get("in_core") else cp, "author": p.get("author") or author(cp),
                 "licence": "GPL-3.0" if e.get("in_core") else p.get("licence") or licence(cp), "nodes": (p.get("nodes") or [])[:6] if e.get("in_core") else live_nodes(e)[:6], "rendered": bool(e.get("rendered"))})
live = {"built": TODAY, "comfyui": info.get("SystemStats", {}).get("comfyui_version", "") if isinstance(info.get("SystemStats"), dict) else "",
        "classes": len(info), "packs": len({str(v.get("python_module", "")).split(".")[1] for v in info.values() if str(v.get("python_module", "")).startswith("custom_nodes.")}),
        "note": "What this machine's ComfyUI offered when the page was built. Another install will have its own list.",
        "samplers": [row(n, "sampler") for n in samplers], "schedulers": [row(n, "scheduler") for n in schedulers], "guidance": sorted(guid, key=lambda g: (g["pack"] != "core", g["pack"], g["name"]))}
json.dump(live, open(LIVE, "w"), ensure_ascii=False, separators=(",", ":"))

# What the readers of these packs found surprising, each tied to its entry. Written from their notes on the code; not run unless it says so.
SURPRISES = [
    ("res4sho-hfx-boost", "hfx_boost, hfx_boost_s2, _s3 and _s4 apply the same gain once their ramp is full: every in-step change is capped at 10% of the stage's size, so only _s1 stays under the cap."),
    ("res4sho-sched-atan", "RES4SHO's two-stage schedules return N+1 steps when asked for N, and put about 60% of them above the linear midpoint of the sigma range (about 7.3 on SD-style models). On our SDXL render, atan_detail left the picture unfinished and kumaraswamy gave no picture at all."),
    ("sched-aligned-timesteps", "In ComfyUI-ppm, ays_30 uses the same table as ays, and ays+ the same as ays_30+: two pairs of names for two schedules."),
    ("sched-diffusers-flowmatch", "Picked from the scheduler list, FlowMatchEulerDiscreteScheduler always gives the same 1 to 0.001 straight line plus a final 0, whatever the model; the node's shift inputs don't change it."),
    ("extraltodeus-distance", "Loading the Distance sampler pack reloads ComfyUI's k-diffusion sampling module, which can undo another pack's patches to it, depending on load order."),
    ("autoguidance-xmarre", "The AutoGuidance detailer hook replaces comfy.samplers.sample for the whole server while it is in use, not just for its own node."),
    ("ms-flow-shift", "DemonAlone's enhanced KSampler defaults to a shift of 3.0, which switches any model, including SD 1.5 and SDXL, to flow-style sampling unless you set the shift to 0."),
    ("seedlab-per-step-noise-seeds", "SeedLab's schedule, inject and reseed samplers reuse one seed for many noise calls, so the \"fresh\" noise is the same tensor step after step."),
    ("tbg-dual-model-sampler", "TBG's dual-model sampler builds a modified low-noise schedule and then never uses it: both passes ask ComfyUI for the standard schedule by name."),
    ("ddrk-schedules", "In DDRK Omega the names don't match the maths: ddrk_edm_simple is log-linear, and ddrk_beta is a Kumaraswamy warp, not a beta curve."),
]
atlas["surprises"] = [x for x in atlas.get("surprises", []) if x.get("source") != "pool51"]
for eid, text in SURPRISES:
    e = by_id.get(eid)
    if e: atlas["surprises"].append({"text": text, "id": eid, "name": e["name"], "where": " ".join(ev["where"] for ev in e["evidence"][:2]), "source": "pool51"})

# Counts, credits and a note of what this pass did.
atlas["counts"] = {f: sum(1 for e in atlas["entries"] if e["family"] == f) for f in FAMILIES}
cred = {c["pack"]: c for c in atlas.get("credits", [])}
for e in atlas["entries"]:
    for p in e["providers"]:
        if p["pack"] == "core": continue
        c = cred.setdefault(p["pack"], {"methods": 0, "pack": p["pack"], "author": p.get("author", ""), "licence": p.get("licence", ""), "verdict": p.get("verdict", ""), "risks": []})
for c in cred.values(): c["methods"] = sum(1 for e in atlas["entries"] if any(p["pack"] == c["pack"] for p in e["providers"]))
atlas["credits"] = sorted(cred.values(), key=lambda c: (-c["methods"], c["pack"]))
atlas.setdefault("additions", []).append({"by": "add_pool51_atlas.py", "date": TODAY, "entries": sorted(added), "providers_added_to": sorted(set(extended)),
    "note": "Pool 51 packs installed on this machine, read as text with evidence lines checked on disk. Not run through the full atlas build or its second reader. Live flags recomputed from this ComfyUI's /object_info."})
json.dump(atlas, open(ATLAS, "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(renders, open(RENDERS, "w"), ensure_ascii=False, indent=1)
named = sum(1 for r in live["samplers"] + live["schedulers"] if r["entry"])
print(f"added {len(added)}, extended {len(set(extended))}, rejected {len(rejected)}, skipped {len(skipped)}; live entries {sum(1 for e in atlas['entries'] if e.get('live'))} (+{became_live}); "
      f"names {len(samplers)} samplers {len(schedulers)} schedulers, {named} explained; guidance live {len(guid)}; pack renders {len(ok)}")
for r in rejected: print("REJECTED", *r)
print("unexplained:", [r["name"] for r in live["samplers"] + live["schedulers"] if not r["entry"]])
