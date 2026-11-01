#!/usr/bin/env python3
"""Merge the Sampling Atlas fragments, check every line of evidence against the source on disk, and write the knowledge base plus the page's data.

Reads helper fragments (JSONL), measures.json and renders.json. Never imports or runs pack code: it only opens files as text.
An entry whose evidence cannot be found on disk is rejected, not softened. Usage:
  SAMPLING_COMFY=<ComfyUI dir> SAMPLING_LIBRARY=<node library dir> build_sampling_lab.py <frag dir> <packs_meta.json> <measures.json> <renders dir with renders.json> <kb out dir> <repo root>
"""
import glob, html, json, os, re, shutil, sys, collections
FRAG, META, MEASURES, RENDERS, KB, REPO = sys.argv[1:7]
CORE = os.environ["SAMPLING_COMFY"].rstrip("/") + "/"; LIB = os.environ["SAMPLING_LIBRARY"].rstrip("/") + "/"      # ComfyUI and the node library on this machine
LIVE_DIR = CORE + "custom_nodes"
ORDER = ["sampler", "scheduler", "guidance", "noise", "latent", "math", "patch"]
RISK_KEYS = {"installs software at runtime": "installs software at runtime", "runs decoded or dynamic code": "runs decoded or dynamic code", "reads credential paths or dumps env": "reads credential paths", "paid or partner API": "paid or partner API", "patches torch or ComfyUI globally": "patches torch or ComfyUI globally", "downloads models": "downloads models"}
meta = json.load(open(META))
live = set()
for n in os.listdir(LIVE_DIR):
    p = os.path.join(LIVE_DIR, n)
    if os.path.isdir(p) and n not in ("__pycache__", "comfyui_parametric_studio"): live.add(n)

OWNERS_FILE = os.path.join(REPO, "studio", "sampling_lab", "pack_owners.json")
OWNERS = json.load(open(OWNERS_FILE))["owners"] if os.path.exists(OWNERS_FILE) else {}
def author(pack):
    if pack == "core": return "Comfy Org and contributors"
    return pack.split("__", 1)[0] if "__" in pack else OWNERS.get(pack, "")
def risks(pack):
    m = meta.get(pack, {}); s = (m.get("v") or {}).get("scan") or {}
    return [w for k, w in RISK_KEYS.items() if s.get(k)]
def verdict(pack):
    v = (meta.get(pack, {}).get("v") or {}); return v.get("verdict2") or v.get("verdict") or ""
def rel(path):
    """No box paths in anything the page ships."""
    if path.startswith(CORE): return "ComfyUI/" + path[len(CORE):]
    for pre in (LIB + "repos/", LIB + "patched-installed/", LIB + "patched/"):
        if path.startswith(pre): return path[len(pre):]
    m = re.match(re.escape(LIB) + r"(?:deploy-backups/[^/]+|pool_sections/[^/]+/packs)/(.+)", path)
    if m: return m.group(1)
    return os.path.basename(path)
_lines = {}
def lines(path):
    if path not in _lines:
        try: _lines[path] = open(path, errors="replace").read().split("\n")
        except OSError: _lines[path] = None
    return _lines[path]
def check(ev):
    path, line, sym = ev.get("path", ""), ev.get("line"), str(ev.get("symbol", ""))
    if not (path.startswith(CORE) or path.startswith(LIB)): return "outside the source tree"
    L = lines(path)
    if L is None: return "file not found"
    if not isinstance(line, int) or not 1 <= line <= len(L): return "line out of range"
    if not sym: return "no symbol"
    win = "\n".join(L[max(0, line - 4):line + 3])
    return None if sym in win or sym.split(".")[-1] in win else f"symbol {sym!r} not near line {line}"
BOX = re.compile(r"/(?:m" + r"nt|ho" + r"me|tmp)/[\w./-]*|~/[\w./-]+")
def scrub(s):
    def one(m):
        path = m.group(0); tail = re.search(r"(:\d+)?$", path).group(0)
        return rel(path[: len(path) - len(tail)] if tail else path) + tail
    return BOX.sub(one, s) if isinstance(s, str) else s
def deep(v):
    if isinstance(v, str): return scrub(v)
    if isinstance(v, list): return [deep(x) for x in v]
    if isinstance(v, dict): return {k: deep(x) for k, x in v.items() if k != "path"}
    return v

entries = {}; rejected = []; ev_ok = ev_bad = 0; dup_ids = 0
for f in sorted(glob.glob(FRAG + "/*.jsonl")):
    for ln, raw in enumerate(open(f, errors="replace"), 1):
        raw = raw.strip()
        if not raw: continue
        try: e = json.loads(raw)
        except ValueError: rejected.append({"file": os.path.basename(f), "line": ln, "why": "not JSON"}); continue
        if e.get("id") in entries and not e.get("math"):      # a later pass adding only a provider for a method already read
            o = entries[e["id"]]; seen = {p.get("pack") for p in o.get("providers") or []}
            o.setdefault("providers", []).extend(p for p in e.get("providers") or [] if p.get("pack") not in seen)
            o["evidence"] += [ev for ev in e.get("evidence") or [] if not check(ev)]; continue
        if not e.get("id") or not e.get("name") or e.get("family") not in ORDER: rejected.append({"file": os.path.basename(f), "line": ln, "id": e.get("id"), "why": "missing id, name or family"}); continue
        good = []; bad = []
        for ev in e.get("evidence") or []:
            why = check(ev)
            if why: bad.append({**ev, "why": why}); ev_bad += 1
            else: good.append(ev); ev_ok += 1
        if not good: rejected.append({"file": os.path.basename(f), "line": ln, "id": e["id"], "why": "no evidence checks out", "bad": bad[:3]}); continue
        if not (e.get("plain") and e.get("math")): rejected.append({"file": os.path.basename(f), "line": ln, "id": e["id"], "why": "no explanation or no math"}); continue
        e["evidence"] = good; e["_bad_evidence"] = len(bad)
        if e["id"] in entries:
            dup_ids += 1; o = entries[e["id"]]
            seen = {p.get("pack") for p in o.get("providers") or []}
            o.setdefault("providers", []).extend(p for p in e.get("providers") or [] if p.get("pack") not in seen)
            o["evidence"] += good
            if os.path.basename(f).startswith("second_"):      # the second pass opened the code the first pass only named
                for k in ("plain", "math", "props", "label", "surprise", "subfamily", "name"):
                    if e.get(k): o[k] = e[k]
        else: entries[e["id"]] = e

# ---- a second, independent reader: its corrections replace the first draft, and its notes stay visible
audit = {}
for f in sorted(glob.glob(os.path.dirname(FRAG.rstrip("/")) + "/audit_result*.jsonl")):
    for l in open(f, errors="replace"):
        try: r = json.loads(l)
        except ValueError: continue
        a = audit.setdefault(r.get("id"), {"verdict": r.get("verdict"), "problem": ""})
        if r.get("verdict") and not (a.get("fixed") and r["verdict"] == "correct"): a["verdict"] = r["verdict"]
        if r.get("problem"): a["problem"] = r["problem"]
        e = entries.get(r.get("id"))
        if e and (r.get("fix_plain") or r.get("fix_math")):
            if r.get("fix_plain"): e["plain"] = r["fix_plain"]
            if r.get("fix_math"): e["math"] = r["fix_math"]
            a["fixed"] = True

# ---- renders: what we saw ourselves is written by hand in renders_notes; the numbers come from renders.json
rd = json.load(open(RENDERS + "/renders.json"))
by_sampler = collections.defaultdict(list); by_sched = collections.defaultdict(list); by_patch = collections.defaultdict(list); by_guider = collections.defaultdict(list)
for r in rd["renders"]:
    if r.get("status") != "rendered": continue
    if r["set"] == "sampler" or (r["set"] == "guidance" and r["sampler"] != "euler"): by_sampler[r["sampler"]].append(r["id"])
    if r["set"] == "flow" and not r["patches"]: by_sampler[r["sampler"]].append(r["id"]); by_sched[r["scheduler"]].append(r["id"])
    if r["set"] == "scheduler": by_sched[r["scheduler"]].append(r["id"])
    for p in r["patches"]: by_patch[p[0]].append(r["id"])
    if r.get("guider"): by_guider[r["guider"]].append(r["id"])
CORE_PATCHES = set(re.findall(r'"(\w+)": \{', re.search(r"CORE_PATCHES = \{(.*?)\n\}", open(REPO + "/studio/sampling_graph.py").read(), re.S).group(1)))
out = []
for e in entries.values():
    provs = []; seen = set()
    for p in e.get("providers") or []:
        pk = p.get("pack") or ""
        if pk in seen: continue
        seen.add(pk)
        m = meta.get(pk, {})
        provs.append({"pack": pk, "author": author(pk), "licence": "GPL-3.0" if pk == "core" else (m.get("licence") or ""), "kind": p.get("kind", ""), "nodes": (p.get("nodes") or [])[:8], "note": scrub(p.get("note", ""))[:300], "verdict": verdict(pk), "risks": [] if pk == "core" else risks(pk), "res4lyf": "RES4LYF" in pk})
    in_core = bool(e.get("in_core")); is_live = not in_core and any(p["pack"] in live for p in provs)
    ref = dict(e.get("core_ref") or {})
    node = ref.get("node") or ""; run_patch = node if node in CORE_PATCHES else ""; run_guider = node if node == "PerpNegGuider" else ""
    ids = []
    if in_core:
        names = [ref.get("sampler_name")] + list(ref.get("sampler_names") or [])
        for n in names:
            if n: ids += by_sampler.get(n, [])
        if ref.get("scheduler"): ids += by_sched.get(ref["scheduler"], [])
        if node: ids += by_patch.get(node, []) + by_guider.get(node, [])
    ids = sorted(set(ids))
    rk = sorted({x for p in provs for x in p["risks"]}); flagged = sum(1 for p in provs if p["risks"])
    fams = [deep(f) for f in e.get("family_fit") or [] if isinstance(f, dict)]
    out.append({"id": e["id"], "name": e["name"], "family": e["family"], "subfamily": e.get("subfamily", ""), "plain": scrub(e["plain"]), "math": scrub(e["math"]), "props": deep(e.get("props") or {}), "evidence": [{"where": f"{rel(ev['path'])}:{ev['line']}", "symbol": ev.get("symbol", "")} for ev in e["evidence"]], "providers": provs, "providers_n": len(provs), "in_core": in_core, "live": is_live, "needs_pack": not in_core and not is_live, "core_ref": {k: v for k, v in ref.items() if v}, "family_fit": fams, "claims": [deep(c) for c in e.get("claims") or [] if isinstance(c, dict)], "label": e.get("label", "from code"), "surprise": scrub(e.get("surprise", "")), "rendered": bool(ids), "rendered_ids": ids, "risks": rk, "flagged_providers": flagged, "licences": sorted({p["licence"] for p in provs if p["licence"]}), "verdicts": sorted({p["verdict"] for p in provs if p["verdict"]}), "audit": {"verdict": audit[e["id"]]["verdict"], "fixed": bool(audit[e["id"]].get("fixed")), "note": scrub(audit[e["id"]]["problem"])[:700]} if e["id"] in audit else None, "run_patch": run_patch, "run_guider": run_guider, "prefer_model": "sd35" if node == "SkipLayerGuidanceSD3" else ("sdxl" if run_patch or run_guider else "")})
out.sort(key=lambda e: (ORDER.index(e["family"]), not e["in_core"], e["name"].lower()))

# ---- copy check: long verbatim runs from a pack's README or evidence file mean the words aren't ours
def shingles(t, n=12):
    w = re.findall(r"[a-z0-9_]+", t.lower()); return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}
copied = []
for e, raw in ((x, entries[x["id"]]) for x in out):
    if e["in_core"]: continue
    mine = shingles(e["plain"] + " " + " ".join(c.get("text", "") for c in e["claims"]))
    if not mine: continue
    src = ""
    for ev in raw["evidence"]:
        L = lines(ev["path"]); src += "\n".join(L or []) + "\n"
    for pv in e["providers"]:
        for base in [(meta.get(pv["pack"]) or {}).get("path") or ""]:
            for nm in ("README.md", "readme.md", "README.MD"):
                if base and os.path.exists(base + "/" + nm): src += open(base + "/" + nm, errors="replace").read()
    hit = mine & shingles(src)
    if hit: copied.append({"id": e["id"], "run": sorted(hit)[0]})

# ---- credits
cred = collections.defaultdict(lambda: {"methods": 0})
for e in out:
    for p in e["providers"]:
        c = cred[p["pack"]]; c.update(pack=p["pack"], author=p["author"], licence=p["licence"], verdict=p["verdict"]); c["methods"] += 1; c["risks"] = risks(p["pack"])
credits = sorted(cred.values(), key=lambda c: (c["pack"] != "core", -c["methods"], c["pack"].lower()))

# ---- surprises: helper notes, kept short, scrubbed, each one already read in code by the helper who wrote it
surprises = []
for f in sorted(glob.glob(FRAG + "/*_surprises.md")):
    for line in open(f, errors="replace"):
        line = line.strip()
        if line.startswith(("-", "*")) and len(line) > 30:
            m = re.findall(r"/[\w./+-]+:\d+", line); txt = line.lstrip("-* ")
            for x in m: txt = txt.replace(x, "")
            txt = re.sub(r"[\s,;]+$", "", scrub(txt)); surprises.append({"text": txt, "where": " ".join(rel(x.rsplit(":", 1)[0]) + ":" + x.rsplit(":", 1)[1] for x in m[:3]), "source": os.path.basename(f).replace("_surprises.md", "")})
surprises = rd.get("seen", []) + surprises

# ---- coverage, honest about what wasn't opened
RANK = ["skipped", "skim-name-only", "not-a-method", "read-part", "read"]
best = {}
for f in sorted(glob.glob(FRAG + "/*_coverage.tsv")):
    for line in open(f, errors="replace"):
        c = line.rstrip("\n").split("\t")
        if len(c) < 3: continue
        st = next((r for r in RANK if c[2].strip().startswith(r)), None)
        if st is None: continue
        key = (c[0], c[1].split(":")[0], (c[3] if len(c) > 3 else "") if not c[1] else "")      # one row per pack and file, whichever pass got furthest with it
        if key not in best or RANK.index(st) > RANK.index(best[key][0]): best[key] = (st, "\t".join(c[:4]))
cov = collections.Counter(v[0] for v in best.values()); unread = sorted(v[1] for v in best.values() if v[0] in ("skim-name-only", "skipped"))
packs_total = len(meta); with_src = sum(1 for m in meta.values() if m.get("has_source"))
counts = collections.Counter(e["family"] for e in out)
coverage = {"packs_in_sections": packs_total, "packs_with_source": with_src, "packs_no_source_on_box": packs_total - with_src, "static_scan": "every .py file of every pack with source was parsed (AST only, never run)", "helpers_read": dict(cov), "evidence_lines_checked_ok": ev_ok, "evidence_lines_rejected": ev_bad, "second_reader": dict(collections.Counter(e["audit"]["verdict"] for e in out if e["audit"])), "second_reader_fixed": sum(1 for e in out if e["audit"] and e["audit"]["fixed"]), "second_reader_total": sum(1 for e in out if e["audit"]), "entries_rejected": len(rejected), "copy_check_hits": len(copied)}
tail = []
tf = os.path.join(os.path.dirname(FRAG), "tail.jsonl")
if os.path.exists(tf):
    for l in open(tf, errors="replace"):
        try: tail.append(json.loads(l))
        except ValueError: pass
    coverage["qwen_tail"] = len(tail)
data = {"built": "2026-11-01", "note": "Facts and equations in our own words. No pack code or README text. Labels: from code, from pack README claim, measured here, inference.", "counts": dict(counts), "coverage": coverage, "credits": credits, "surprises": surprises, "entries": out}

# ---- write
os.makedirs(KB, exist_ok=True); lab = REPO + "/studio/sampling_lab"; os.makedirs(lab, exist_ok=True)
json.dump({**data, "qwen_tail_unverified": tail, "rejected": rejected, "copy_check": copied}, open(KB + "/ATLAS.json", "w"), ensure_ascii=False, indent=1)
json.dump(data, open(lab + "/atlas.json", "w"), ensure_ascii=False, separators=(",", ":"))
shutil.copy(MEASURES, lab + "/measures.json"); shutil.copy(MEASURES, KB + "/measures.json"); shutil.copy(RENDERS + "/renders.json", lab + "/renders.json"); shutil.copy(RENDERS + "/renders.json", KB + "/renders.json")
TITLES = {"sampler": "Samplers and solvers", "scheduler": "Schedulers and sigma shapers", "guidance": "Guidance and CFG", "noise": "Noise", "latent": "Latent operations", "math": "Math and logic", "patch": "Model patches and attention"}
def block(e):
    o = [f"## {e['name']}", f"`{e['id']}` · {'in ComfyUI core' if e['in_core'] else 'live pack here' if e['live'] else 'needs a pack'} · label: {e['label']}" + (" · rendered here" if e["rendered"] else ""), "", e["plain"], "", "```text", e["math"], "```"]
    pr = [f"{k.replace('_', ' ')}: {v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)}" for k, v in e["props"].items() if v not in ("", None, {}, [])]
    if pr: o += ["", "Properties: " + "; ".join(pr)]
    o += ["", "Evidence: " + ", ".join(f"`{x['where']}` ({x['symbol']})" for x in e["evidence"][:6])]
    o += ["", "Providers: " + "; ".join(f"{p['pack']}" + (f" by {p['author']}" if p['author'] else "") + (f", {p['licence']}" if p['licence'] else "") + (f", {p['kind']}" if p['kind'] else "") + (f", Qwen verdict {p['verdict']}" if p['verdict'] else "") for p in e["providers"])]
    for f in e["family_fit"]: o.append(f"- Fit, {f.get('family')}: {f.get('why')} [{f.get('label')}]")
    for c in e["claims"]: o.append(f"- Claim: {c.get('text')} [{c.get('label')}]")
    for p in e["providers"]:
        if p["risks"]: o.append(f"- Script scan, {p['pack']}: " + ", ".join(p["risks"]))
    if e["surprise"]: o.append("- Worth knowing: " + e["surprise"])
    if e["audit"]: o.append(f"- Second reader: {e['audit']['verdict']}" + (", corrected above" if e["audit"]["fixed"] else "") + (f". {e['audit']['note']}" if e["audit"]["note"] else ""))
    return "\n".join(o) + "\n"
for fam in ORDER:
    rows = [e for e in out if e["family"] == fam]
    open(f"{KB}/{fam}.md", "w").write(f"# {TITLES[fam]} ({len(rows)})\n\nFrom the Sampling Atlas. Labels: from code, from pack README claim, measured here, inference.\n\n" + "\n".join(block(e) for e in rows))
open(KB + "/SURPRISES.md", "w").write("# What surprised us\n\n" + "\n".join(f"- {s['text']}" + (f" (`{s['where']}`)" if s.get("where") else "") for s in surprises) + "\n")
open(KB + "/COVERAGE.md", "w").write("# What was read, and what wasn't\n\n" + "\n".join(f"- {k}: {v}" for k, v in coverage.items()) + "\n\n## Not opened by a reader (name skim or skipped)\n\n" + "\n".join(unread) + "\n\n## Packs with no source on this box\n\n" + "\n".join(sorted(p for p, m in meta.items() if not m.get("has_source"))) + "\n\n## Rejected entries\n\n" + "\n".join(json.dumps(r, ensure_ascii=False) for r in rejected) + "\n")
open(KB + "/CREDITS.md", "w").write("# Credits and licences\n\nLicences as found in each repository. Qwen verdicts are a reading, not a safety guarantee.\n\n| pack | author | licence | methods | Qwen | scan flags |\n|---|---|---|---|---|---|\n" + "\n".join(f"| {c['pack']} | {c['author'] or 'not stated'} | {c['licence'] or 'none found'} | {c['methods']} | {c['verdict'] or 'not reviewed'} | {', '.join(c.get('risks') or [])} |" for c in credits) + "\n")
open(KB + "/README.md", "w").write(f"""# Sampling Atlas

Every distinct sampling method we could read the source of, in ComfyUI core and the node pack library. Built 2026-11-01.

- `ATLAS.json`: all entries plus coverage, rejected entries and the unverified Qwen tail.
- {', '.join(f'`{f}.md` ({counts[f]})' for f in ORDER)}.
- `SURPRISES.md`, `COVERAGE.md`, `CREDITS.md`, `measures.json`, `renders.json`.

How to read a label: **from code** was read in the source and has a file:line that a script found on disk. **from pack README claim** is what an author says and was not checked. **measured here** ran on this box. **inference** is our reasoning. Entries with no evidence that checks out were rejected, and the Qwen tail is unverified and never goes into training data. A found line proves the code exists there, not that the words are right, so a second reader checked part of the atlas against the code: see `second_reader` in `COVERAGE.md`. Entries with no second-reader line had one reader, and the checked sample found errors, so treat them as a good first read.

Pack code and READMEs are not copied here: facts and our own equations only, with credit. RES4LYF's licence bars commercial services without permission, so it gets short entries and its own tribute page (`feat/res4lyf-page`).

Rebuild: `scripts/build_sampling_lab.py` in the studio repo.
""")
print(json.dumps({"entries": len(out), "counts": counts, "evidence_ok": ev_ok, "evidence_bad": ev_bad, "rejected": len(rejected), "dup_ids": dup_ids, "copy_hits": copied[:12], "core": sum(e["in_core"] for e in out), "live": sum(e["live"] for e in out), "rendered": sum(e["rendered"] for e in out), "credits": len(credits)}, indent=0, default=str))
