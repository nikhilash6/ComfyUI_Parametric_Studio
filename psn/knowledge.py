"""Answers from the studio's knowledge files, with evidence. Every row says where it came from (file:line), and nothing here calls a model, a server or the network.
Public data ships in this repo: the sampling atlas, the University, recipes and processes, crew notes. Larger private ledgers are read only when a folder is named:
PSN_KNOWLEDGE_WORKER (pack picks, node audit, model use map, copilot recipes) and PSN_KNOWLEDGE_LIBRARY (pack sources, Round 2 data). Without them those lookups say the data is missing, rather than guess.
Usage: python3 -m psn.knowledge <command> <words> [--max N] [--json]. Standard library only."""
import argparse, csv, glob, json, os, re, sys
from functools import lru_cache

from psn import paths

csv.field_size_limit(10 ** 9)
PICKS = "PACK_PICKS_2026-11-01"; AUDIT = "NODE_AUDIT_2026-11-01.tsv"; USE_MAP = "MODEL_USE_MAP_2026-11-01.tsv"; READS = "STUDIO_READ_2026-11-01"
LICENCE_NAMES = re.compile(r"^(licen[cs]e|copying|notice|eula)([._-].*)?$", re.I)
RESTRICTIVE = re.compile(r"non-?commercial|research[- ]only|cc-by-nc|all rights reserved|no commercial|not for commercial|commercial\s[^.]{0,300}?(?:prohibited|forbidden|not (?:permitted|allowed))|(?:prohibit\w*|forbid\w*)\s[^.]{0,120}?commercial|separate commercial licen[cs]e", re.I)


def repo(*parts): return os.path.join(paths.REPO, *parts)
def worker_dir(): return paths.setting("PSN_KNOWLEDGE_WORKER")
def library_dir(): return paths.setting("PSN_KNOWLEDGE_LIBRARY")
def worker(*parts): return os.path.join(worker_dir(), *parts) if worker_dir() else ""
def library(*parts): return os.path.join(library_dir(), *parts) if library_dir() else ""


def _words(query):
    """Lower-case search words; a row matches when it holds every word."""
    return [w for w in re.findall(r"[\w.+-]+", str(query).lower()) if w]


def _hit(words, text):
    low = text.lower()
    return bool(words) and all(w in low for w in words)


def _where(path, line=None):
    """A path for evidence: relative when it is inside this repo, so public answers name no folder of this machine."""
    p = os.path.relpath(path, paths.REPO) if os.path.abspath(path).startswith(paths.REPO + os.sep) else path
    return f"{p}:{line}" if line else p


def _result(rows, missing=None, note=None, limit=25):
    out = {"rows": rows[:limit], "total": len(rows)}
    if missing: out["missing"] = missing
    if note: out["note"] = note
    return out


def _missing(label, path):
    return {"rows": [], "total": 0, "missing": f"{label} is not available" + ("" if path else ": its data folder is not set")}


def _read_tsv(path):
    """Rows of a TSV with the real line number of each."""
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return [(reader.line_num, dict(r)) for r in reader]


@lru_cache(maxsize=16)
def _tsv_cached(path, mtime): return _read_tsv(path)
def _tsv(path): return _tsv_cached(path, os.path.getmtime(path))


@lru_cache(maxsize=8)
def _json_cached(path, mtime):
    with open(path, encoding="utf-8") as f: return json.load(f)
def _json(path): return _json_cached(path, os.path.getmtime(path))


def _line_of(path, needle):
    """First line of a file holding this text, or None."""
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if needle in line: return i
    return None


# ---- sampling --------------------------------------------------------------------------------------------------------------------------------------------------------
ATLAS = "studio/sampling_lab/atlas.json"
def atlas_entries(): return _json(repo(ATLAS))["entries"]


def atlas_entry_text(e):
    """All the prose of one atlas entry: what an answer may quote from it."""
    claims = " ".join(str(c.get("text", "")) for c in e.get("claims") or [])
    return "\n".join(str(e.get(k) or "") for k in ("name", "plain", "math", "surprise")) + "\n" + claims


def _atlas_row(e):
    return {"id": e["id"], "name": e["name"], "family": e["family"], "label": e["label"], "plain": e.get("plain", ""), "in_core": bool(e.get("in_core")), "live": bool(e.get("live")), "needs_pack": bool(e.get("needs_pack")),
            "audit": (e.get("audit") or {}).get("verdict", "not checked by a second reader"), "code": [x.get("where") for x in e.get("evidence") or []][:4], "evidence": f"{ATLAS}#{e['id']}"}


def sampling(query, limit=25):
    """Atlas entries matching every word, closest names first. Labels stay with the row: from code, inference, or pack README claim."""
    words = _words(query); rows = []
    for e in atlas_entries():
        name = (e["id"] + " " + e["name"]).lower()
        if _hit(words, name): rows.append((0, e))
        elif _hit(words, atlas_entry_text(e)): rows.append((1, e))
    rows.sort(key=lambda t: (t[0], t[1]["id"]))
    return _result([_atlas_row(e) for _, e in rows], limit=limit)


def sampling_entry(entry_id):
    """One atlas entry in full, or None."""
    return next((e for e in atlas_entries() if e["id"] == entry_id), None)


# ---- University ------------------------------------------------------------------------------------------------------------------------------------------------------
UNI = repo("studio", "university")
@lru_cache(maxsize=1)
def _lessons_cached(stamp):
    out = {}
    for course in sorted(glob.glob(os.path.join(UNI, "[0-9]*", "CU-*", "course.json"))):
        with open(course, encoding="utf-8") as f: c = json.load(f)
        lesson = os.path.join(os.path.dirname(course), "lesson.md")
        with open(lesson, encoding="utf-8", errors="replace") as f: text = f.read()
        out[c["code"]] = {"code": c["code"], "title": c["title"], "level": c["level"], "track": c.get("track", ""), "second_read": "checked" if isinstance(c.get("second_read"), dict) else "pending", "errors_fixed": (c.get("second_read") or {}).get("errors_fixed") if isinstance(c.get("second_read"), dict) else None, "unchecked": c.get("unchecked") or [], "path": lesson, "text": text}
    return out
def lessons(): return _lessons_cached(os.path.getmtime(UNI))


def lesson_search(query, limit=25):
    """Lessons holding every word; the first matching line of each is the evidence. Titles rank first. A second-read mark says a second reader checked the lesson, not that every word is proven."""
    words = _words(query); rows = []
    for c in lessons().values():
        blob = c["title"] + "\n" + c["text"]
        if not _hit(words, blob): continue
        line = next((i for i, ln in enumerate(c["text"].splitlines(), 1) if any(w in ln.lower() for w in words)), 1)
        rows.append((0 if _hit(words, c["title"]) else 1, {"code": c["code"], "title": c["title"], "level": c["level"], "track": c["track"], "second_read": c["second_read"], "line": c["text"].splitlines()[line - 1].strip()[:200], "evidence": _where(c["path"], line)}))
    rows.sort(key=lambda t: (t[0], t[1]["code"]))
    return _result([r for _, r in rows], limit=limit)


def lesson_read(code):
    """One lesson in full plus its marks, or None."""
    return lessons().get(str(code).strip().upper())


# ---- recipes and processes -------------------------------------------------------------------------------------------------------------------------------------------
def _recipe_files(): return sorted(glob.glob(repo("studio", "recipe_library", "*.json"))) + [repo("studio", "recipes.json")]


def recipe(query, limit=25):
    """Recipes matching every word, with the proof the repo really holds: a stored render, or none. Library recipes were ported; a stored render is the only proof they ran here."""
    words = _words(query); rows = []; renders = _json(repo("studio", "recipe_renders.json")).get("renders", {})
    for path in _recipe_files():
        doc = _json(path)
        for r in doc.get("recipes", []):
            if not _hit(words, " ".join(str(r.get(k, "")) for k in ("id", "title", "pitch", "why", "group", "tags"))): continue
            run = renders.get(r["id"])
            rows.append({"id": r["id"], "kind": r.get("kind", doc.get("kind", "")), "title": r.get("title", ""), "rating": r.get("rating", ""), "models": [m.get("name") for m in r.get("models", []) if isinstance(m, dict)], "steps": len(r.get("steps", [])), "rendered": bool(run), "seconds": (run or {}).get("seconds"), "peak_vram_gib": (run or {}).get("peak_vram_gib"), "evidence": _where(path, _line_of(path, f'"{r["id"]}"'))})
    return _result(rows, limit=limit)


def process(query, limit=25):
    """Process guides matching every word, with their status as the catalogue states it."""
    words = _words(query); path = repo("studio", "processes.json"); rows = []
    for p in _json(path)["processes"]:
        if not _hit(words, " ".join(str(p.get(k, "")) for k in ("id", "name", "kind", "description", "models"))): continue
        guide = repo("studio", "processes", p["id"] + ".md")
        rows.append({"id": p["id"], "name": p["name"], "kind": p.get("kind"), "status": p.get("status"), "description": p.get("description", ""), "models": p.get("models", []), "guide": _where(guide) if os.path.isfile(guide) else None, "evidence": _where(path, _line_of(path, f'"{p["id"]}"'))})
    return _result(rows, limit=limit)


# ---- packs ------------------------------------------------------------------------------------------------------------------------------------------------------------
def _picks(*parts): return worker(PICKS, *parts)


def do_not_install():
    """{pack: entry} from the do-not-install list."""
    p = _picks("data", "DO_NOT_INSTALL_2026-11-01.json")
    return {e["pack"]: e for e in _json(p)} if p and os.path.isfile(p) else {}


def _pack_row(line, r, path):
    keep = {k: r.get(k, "") for k in ("pack", "verdict", "tier", "sandbox", "stars", "isfork", "fam_original", "name_original", "license", "lab", "live", "patched", "sections", "page", "why")}
    return {**keep, "evidence": _where(path, line)}


def pack(query, limit=25):
    """Packs matching every word, popular first, SKIP last. Adds the do-not-install entry and any risk flags. Verdicts are the local model's and generous: a TRY means nothing looked wrong in part of the text."""
    path = _picks("data", "PACK_INDEX_2026-11-01.tsv")
    if not path or not os.path.isfile(path): return _missing("The pack index", worker_dir())
    words = _words(query); bad = do_not_install(); rows = []
    stars = lambda r: int(r["stars"]) if str(r.get("stars", "")).isdigit() else 0
    for line, r in _tsv(path):
        if _hit(words, r["pack"] + " " + r.get("why", "")): rows.append((line, r))
    rows.sort(key=lambda t: (t[1]["verdict"] == "SKIP", t[1]["pack"] not in bad, -stars(t[1]), t[1]["pack"]))
    out = []
    for line, r in rows[:limit]:
        row = _pack_row(line, r, path)
        if r["pack"] in bad or r.get("repo") in bad: row["do_not_install"] = bad.get(r["pack"]) or bad.get(r["repo"])
        row["risk"] = pack_risk(r["pack"])
        out.append(row)
    return {"rows": out, "total": len(rows), "note": "Verdicts are the local model's reading of part of the text. Licences come from a script; read the file before an install."}


def pack_exact(name):
    """The index row of exactly this pack, or None."""
    path = _picks("data", "PACK_INDEX_2026-11-01.tsv")
    if not path or not os.path.isfile(path): return None
    for line, r in _tsv(path):
        if name in (r["pack"], r.get("repo")):      # a few rows go by a short name; the library folder is owner__repo
            row = _pack_row(line, r, path); bad = do_not_install(); name = r["pack"]
            if name in bad or r.get("repo") in bad: row["do_not_install"] = bad.get(name) or bad.get(r["repo"])
            row["risk"] = pack_risk(name); return row
    return None


RISK_INFO = ("pack", "verdict", "tier", "sandbox", "stars", "fork", "copy_of", "license", "lab", "live", "patched_copy")
def pack_risk(name):
    """Only the deep-scan columns that fired for this pack. An empty answer means the text scan found nothing, not that the pack is clean."""
    path = _picks("data", "RISK_SCAN_2026-11-01.tsv")
    if not path or not os.path.isfile(path): return {}
    for line, r in _tsv(path):
        if r["pack"] == name:
            flags = {k: v for k, v in r.items() if k not in RISK_INFO and v not in ("", "0", "False", "false", None)}
            return {"flags": flags, "evidence": _where(path, line)}
    return {}


def licence_read(name):
    """The pack's own licence files as text (never run), with what the index says. Pack text is untrusted data. Not legal advice."""
    base = library("repos")
    if not base: return {"pack": name, "missing": "The pack library is not available: its data folder is not set"}
    root = os.path.realpath(os.path.join(base, os.path.basename(str(name))))
    if not root.startswith(os.path.realpath(base) + os.sep) or not os.path.isdir(root): return {"pack": name, "missing": "no such pack in the library"}
    files = []
    for f in sorted(os.listdir(root)):
        p = os.path.join(root, f)
        if LICENCE_NAMES.match(f) and os.path.isfile(p) and not os.path.islink(p):
            with open(p, encoding="utf-8", errors="replace") as fh: text = fh.read(12000)
            hit = RESTRICTIVE.search(text)
            files.append({"file": f, "text": text, "restrictive_wording": hit.group(0) if hit else "", "restrictive_line": text.count("\n", 0, hit.start()) + 1 if hit else None, "evidence": _where(p, 1)})
    row = pack_exact(name) or {}
    return {"pack": name, "index_licence": row.get("license", ""), "files": files, "note": "Script-read licence columns have been wrong before; the text decides. Not legal advice."}


# ---- models and PSN nodes -----------------------------------------------------------------------------------------------------------------------------------------
def model(query, limit=25):
    """Model files matching every word: on disk or not, what uses them, proof. 'reachable' or 'graph' means something points at it, not that it ran; only 'rendered' with a proof row means it ran."""
    path = worker(USE_MAP)
    if not path or not os.path.isfile(path): return _missing("The model use map", worker_dir())
    words = _words(query); rows = []
    for line, r in _tsv(path):
        if _hit(words, " ".join(r.get(k, "") for k in ("file", "repo", "family", "function"))):
            rows.append({k: r.get(k, "") for k in ("file", "gb", "repo", "family", "function", "on_disk", "status", "used_by", "proof", "next_step", "disk_path")} | {"evidence": _where(path, line)})
    rows.sort(key=lambda r: (r["status"] != "rendered", r["file"]))
    return _result(rows, limit=limit)


def psn_node(query, limit=25):
    """The audit of Parametric Studio's own nodes. hollow or broken does not count as coverage."""
    path = worker(AUDIT)
    if not path or not os.path.isfile(path): return _missing("The node audit", worker_dir())
    words = _words(query)
    return _result([{**r, "evidence": _where(path, line)} for line, r in _tsv(path) if _hit(words, r.get("node", "") + " " + r.get("module", ""))], limit=limit)


def pipelines(root=None):
    """Weight files really on disk per assembled pipeline folder. Links are followed; tiny stubs and hash markers don't count."""
    root = root or os.path.join(paths.models_root(), "_complete_pipelines"); out = {}
    if not os.path.isdir(root): return out
    weight = re.compile(r"\.(safetensors|gguf|ckpt|pt|pth|bin|onnx)$", re.I)
    for fam in sorted(os.listdir(root)):
        base = os.path.join(root, fam)
        if not os.path.isdir(base): continue
        count, size = 0, 0
        for dp, _, fn in os.walk(base, followlinks=True):
            for f in fn:
                if weight.search(f):
                    try: s = os.stat(os.path.join(dp, f)).st_size
                    except OSError: continue
                    if s >= 4096: count += 1; size += s
        out[fam] = {"files": count, "gb": round(size / 1e9, 1)}
    return out


# ---- copilot recipes, node purposes, documents ---------------------------------------------------------------------------------------------------------------------
def copilot(query, limit=25):
    """What was salvaged from the earlier copilot: inventory row and, when ported, its validation. Proof levels are as that older studio recorded them."""
    inv, val = worker("copilot_recipes", "INVENTORY.tsv"), worker("copilot_recipes", "VALIDATION.tsv")
    if not inv or not os.path.isfile(inv): return _missing("The copilot recipe inventory", worker_dir())
    words = _words(query); checks = {r["id"]: (line, r) for line, r in _tsv(val)} if os.path.isfile(val) else {}; rows = []
    for line, r in _tsv(inv):
        if not _hit(words, r.get("name", "") + " " + r.get("note", "") + " " + r.get("models_needed", "")): continue
        row = {k: r.get(k, "") for k in ("name", "kind", "models_needed", "on_disk", "proof_level", "rating", "already_in_live", "ported_to", "runnable_now", "note")} | {"evidence": _where(inv, line)}
        ported = r.get("ported_to", "")
        if ported in checks: row["validation"] = {k: checks[ported][1].get(k) for k in ("ready", "proof", "why")} | {"evidence": _where(val, checks[ported][0])}
        rows.append(row)
    return _result(rows, limit=limit)


def node_purpose(query, limit=25):
    """What the local model said a library node does, from the Round 2 data, checked rows first. It is the model's reading, not proof; take inputs and outputs from object_info, not here."""
    path = library("knowledge_base", "training_base", "round2_node_purpose_sft.jsonl")
    if not path or not os.path.isfile(path): return _missing("The Round 2 node notes", library_dir())
    words = _words(query); rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            low = line.lower()
            if not all(w in low for w in words): continue
            d = json.loads(line); msgs = d.get("messages", [])
            q = next((m["content"] for m in msgs if m["role"] == "user"), ""); a = next((m["content"] for m in msgs if m["role"] == "assistant"), "")
            rows.append({"pack": d.get("source_pack", ""), "label_source": d.get("label_source", ""), "question": q[:200], "note": a[:500], "evidence": _where(path, i)})
    rows.sort(key=lambda r: (r["label_source"] != "qwen, checked", r["pack"]))
    return _result(rows, limit=limit, note="The local model's reading of part of the source. Not proof.")


def doc_scopes():
    """Search scopes for grep: name -> folders and patterns."""
    scopes = {"crew": [repo("studio", "crew_notes", "**", "*.md")], "processes": [repo("studio", "processes", "*.md")]}
    if worker_dir(): scopes |= {"picks": [_picks("*.md")], "reads": [worker(READS, "*.md")], "facts": [worker("FACTS.md"), worker("RELEASE_PREP_2026-11-01.md")]}
    if library_dir(): scopes |= {"atlas": [library("knowledge_base", "sampling_atlas", "*.md")], "added-packs": [library("knowledge_base", "added_packs", "*.md")], "sections": [library("knowledge_base", "sections", "*", "GUIDE.md")]}
    return scopes


def grep_docs(query, scope="crew", limit=25):
    """Lines holding every word in one scope of documents, as file:line."""
    scopes = doc_scopes()
    if scope not in scopes: return {"rows": [], "total": 0, "missing": f"unknown or unavailable scope '{scope}'; available: {sorted(scopes)}"}
    words = _words(query); rows = []
    for pat in scopes[scope]:
        for p in sorted(glob.glob(pat, recursive=True)):
            with open(p, encoding="utf-8", errors="replace") as f:
                for i, ln in enumerate(f, 1):
                    if _hit(words, ln): rows.append({"text": ln.strip()[:300], "evidence": _where(p, i)})
    return _result(rows, limit=limit)


# ---- node inputs and outputs from a saved or live object_info -------------------------------------------------------------------------------------------------------
def spec_options(spec):
    """Allowed values of a COMBO input in either form, or None."""
    if isinstance(spec, (list, tuple)) and spec:
        if isinstance(spec[0], list): return spec[0]
        if spec[0] == "COMBO" and len(spec) > 1 and isinstance(spec[1], dict): return spec[1].get("options")
    return None


def node_summary(name, info):
    """One node's inputs and outputs in a short form, for a person or a model to wire from."""
    def one(spec):
        t = spec[0] if isinstance(spec, (list, tuple)) and spec else spec
        opts = spec_options(spec); extra = spec[1] if isinstance(spec, (list, tuple)) and len(spec) > 1 and isinstance(spec[1], dict) else {}
        d = {"type": "COMBO" if opts is not None else t}
        if opts is not None: d["choices"] = opts[:40]; d["choices_total"] = len(opts)
        for k in ("default", "min", "max"):
            if k in extra: d[k] = extra[k]
        return d
    ins = info.get("input") or {}
    return {"class": name, "required": {k: one(v) for k, v in (ins.get("required") or {}).items()}, "optional": {k: one(v) for k, v in (ins.get("optional") or {}).items()}, "outputs": list(zip(info.get("output_name") or info.get("output") or [], info.get("output") or []))}


def node_io(query, object_info_path=None, limit=25):
    """Classes in an object_info file whose name holds every word, with inputs and outputs. Default file: the small snapshot the University ships."""
    path = object_info_path or repo("studio", "university", "node_defs.json")
    words = _words(query); oi = _json(path)
    return _result([{**node_summary(k, v), "evidence": _where(path) + "#" + k} for k, v in sorted(oi.items()) if _hit(words, k)], limit=limit)


COMMANDS = {"sampling": sampling, "lesson": lesson_search, "recipe": recipe, "process": process, "pack": pack, "model": model, "node": psn_node, "copilot": copilot, "purpose": node_purpose, "nodeio": node_io}


def show(rows):
    for r in rows:
        print(r.get("evidence", ""))
        for k, v in r.items():
            if k != "evidence" and v not in ("", None, [], {}): print(f"  {k}: {v if isinstance(v, str) else json.dumps(v, default=str)}"[:400])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=[*COMMANDS, "licence", "docs", "pipelines"]); ap.add_argument("words", nargs="*"); ap.add_argument("--max", type=int, default=15); ap.add_argument("--json", action="store_true"); ap.add_argument("--scope", default="crew")
    a = ap.parse_args(argv); q = " ".join(a.words)
    if a.command == "pipelines": res = {"rows": [{"family": k, **v, "evidence": k} for k, v in pipelines().items()]}; res["total"] = len(res["rows"])
    elif a.command == "licence": res = licence_read(q)
    elif a.command == "docs": res = grep_docs(q, a.scope, limit=a.max)
    else: res = COMMANDS[a.command](q, limit=a.max)
    if a.json: print(json.dumps(res, indent=1, default=str)); return 0
    if res.get("missing"): print(res["missing"], file=sys.stderr); return 2
    if "rows" not in res:
        for f in res.get("files", []): print(f["evidence"], "| restrictive wording:", f["restrictive_wording"] or "none"); print(f["text"][:800])
        print("index says:", res.get("index_licence") or "(no row)"); print(res.get("note", "")); return 0
    print(f"{res['total']} matches, showing {len(res['rows'])}. {res.get('note', '')}".strip()); show(res["rows"]); return 0


if __name__ == "__main__": sys.exit(main())
