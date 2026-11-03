#!/usr/bin/env python3
"""ComfyUniversity builder. Lessons live here, one folder per course: <level>/<code>-<slug>/{course.json, lesson.md, lab.py, lab_output.txt, quiz.json}.
python studio/university/build.py            checks every lesson, writes catalogue.json and CATALOGUE.md
python studio/university/build.py --labs     also runs every lab twice on the CPU, requires identical output and under 60 s, stores lab_output.txt
python studio/university/build.py --labs --only CU-101 CU-102
Standard library only, plus torch inside the labs themselves."""
import argparse, ast, concurrent.futures as cf, hashlib, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent; LIMIT = 60
META = lambda: json.loads((HERE / "meta.json").read_text()); GRAPHS = HERE / "graphs"; WEB = HERE.parent / "web"
def SOURCES():
    """sources.json, plus any fragments in sources.d/ so lessons can add sources without touching one shared file."""
    out = json.loads((HERE / "sources.json").read_text())
    for f in sorted((HERE / "sources.d").glob("*.json")) if (HERE / "sources.d").is_dir() else []: out.update(json.loads(f.read_text()))
    return out
def TRACKS(): return json.loads((HERE / "tracks.json").read_text())
def DEFS(): return json.loads((HERE / "node_defs.json").read_text()) if (HERE / "node_defs.json").exists() else {}
def VERIFIED(): return json.loads((GRAPHS / "verified.json").read_text()).get("graphs", {}) if (GRAPHS / "verified.json").exists() else {}
def graph_sha(g): return hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest()[:16]
def load_graph(gid):
    """One graph file -> {id, meta, graph, verified, defs}, or None. Only classes the graph uses travel with it."""
    if not re.fullmatch(r"[a-z0-9_]+", gid or ""): return None
    p = GRAPHS / f"{gid}.json"
    if not p.exists(): return None
    d = json.loads(p.read_text()); defs = DEFS(); row = VERIFIED().get(gid) or {}
    if row.get("sha") != graph_sha(d["graph"]): row = {}
    return {"id": gid, "meta": d["meta"], "graph": d["graph"], "verified": {k: row.get(k) for k in ("validate", "ran", "ran_seconds", "file_menus_skipped") if k in row}, "defs": {c: defs[c] for c in {n["class_type"] for n in d["graph"].values()} if c in defs}}
def all_graph_ids(): return sorted(p.stem for p in GRAPHS.glob("*.json") if p.name != "verified.json")
def lesson_directives(md):
    """-> what a lesson embeds: {play: [...], graph: [...], media: [...]}."""
    out = {"play": [], "graph": [], "media": []}
    for kind, body in re.findall(r"^\{\{(play|graph|wipe|video|audio):([^}]*)\}\}\s*$", md, re.M):
        if kind == "play": out["play"].append(body.strip().split()[0])
        elif kind == "graph": out["graph"].append(body.strip())
        elif kind == "wipe": out["media"] += [x.strip() for x in body.split("|")[:2]]
        elif kind == "video": out["media"] += [x.strip() for x in body.split("|")[:3:2] if x.strip()]   # the clip, and its poster when one is given
        else: out["media"].append(body.split("|")[0].strip())
    out["media"] += re.findall(r"^!\[[^\]]*\]\(([^)\s]+)\)\s*$", md, re.M)
    return out
def play_names():
    """Names in the PLAYS table of the page."""
    out = set()
    for f in WEB.glob("university_plays*.js"): out |= set(re.findall(r"^  ([a-z0-9_]+): \{ title:", f.read_text(), re.M))
    return out
def symbol_exists(src, ref):
    """code_refs entries are file:symbol, where symbol is a name or Class.method. Looks it up with the parser, then falls back to the text for plain names and constants."""
    f, _, sym = ref.partition(":"); p = Path(src) / f
    if not p.exists(): return False
    text = p.read_text(errors="replace")
    if "." not in sym: return re.search(r"(?<![\w])" + re.escape(sym) + r"(?![\w])", text) is not None
    try: tree = ast.parse(text)
    except SyntaxError: return False
    head, *rest = sym.split(".")
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == head:
            member = rest[0]
            for b in ast.walk(node):
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) and b.name == member: return True
                if isinstance(b, ast.Assign) and any(isinstance(t, ast.Name) and t.id == member for t in b.targets): return True
                if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name) and b.target.id == member: return True
            return False
    return not head[0].isupper() and sym in text  # self.x or module.x, read as text
LAB_IMPORTS = {"torch", "math", "random", "json", "itertools", "collections", "struct", "zlib", "io", "hashlib", "heapq", "functools", "re", "dataclasses", "typing", "base64", "asyncio", "pickle", "copy", "uuid", "urllib"}
REQUIRED = ["Objective", "## Lab", "## Sources"]

def courses():
    """Every course folder on disk, in teaching order: level, then the code. status "draft" means imported from the earlier model-written set and not yet audited."""
    rows = []
    for f in HERE.glob("[1-4]00/CU-*/course.json"):
        c = json.loads(f.read_text()); c["path"] = str(f.parent.relative_to(HERE)); c["dir"] = f.parent; rows.append(c)
    return sorted(rows, key=lambda c: (c["level"], c["code"]))

def lab_env(threads=1): return {"PATH": "/usr/bin:/bin", "CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": str(threads), "MKL_NUM_THREADS": str(threads), "PYTHONHASHSEED": "0", "HOME": tempfile.gettempdir()}

def run_lab(path, py=None, timeout=LIMIT):
    """Run one lab in a throw-away folder with no GPU. -> (ok, stdout, seconds, stderr tail)."""
    code = Path(path).read_text(); t = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="cu_lab_") as wd:
        (Path(wd) / "lab.py").write_text(code)
        try: p = subprocess.run([py or sys.executable, "-I", "lab.py"], cwd=wd, capture_output=True, text=True, timeout=timeout, env=lab_env())
        except subprocess.TimeoutExpired: return False, "", time.perf_counter() - t, f"timed out after {timeout} s"
    return p.returncode == 0, p.stdout, time.perf_counter() - t, "\n".join(p.stderr.splitlines()[-12:])

def lab_imports(code):
    """Top-level names of everything a lab imports, parsed properly, so 'import a, b' counts both."""
    out = set()
    for n in ast.walk(ast.parse(code)):
        if isinstance(n, ast.Import): out |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level: out.add(n.module.split(".")[0])
    return out

def quiz_right(q, o, i):
    """The same rule the web page uses to mark an option right (Quiz in studio/web/app.js)."""
    a = str(q.get("answer") or "").strip(); lo = o.lower(); la = a.lower()
    return a == o or la.startswith(chr(97 + i) + ")") or la.startswith(chr(97 + i) + ".") or a == chr(65 + i) or (len(a) > 3 and la in lo) or (len(o) > 3 and lo in la)

def lesson_links(md): return re.findall(r"\[([^\]]+)\]\((https?:[^)\s]+)\)", md)

def check_course(c, codes, sources):
    """-> list of problems with one course. Everything here is checked again by tests/test_university.py."""
    d = c["dir"]; pr = []; md = (d / "lesson.md").read_text() if (d / "lesson.md").exists() else ""
    for n in ("lesson.md", "lab.py", "lab_output.txt", "quiz.json"):
        if not (d / n).exists(): pr.append("missing " + n)
    if pr: return pr
    if not md.startswith(f"# {c['code']} - {c['title']}\n"): pr.append("first line must be the code and title")
    for s in REQUIRED:
        if s not in md: pr.append("lesson lacks " + s)
    if re.search(r"\$[^$\n]{1,80}\$|\\frac|\\sigma|\\epsilon", md): pr.append("LaTeX in lesson: the page has no maths renderer, write Unicode")
    prose = re.sub(r"```.*?```", "", md, flags=re.S); prose = re.sub(r"`[^`\n]*`", "", prose); prose = prose.replace("**", "")
    if "*" in prose: pr.append("stray * in prose: the page's markdown would turn it into emphasis")
    for w in ("UNVERIFIED", "Qwen3.8", "/" + "mnt/fast", "/" + "home/", ":82" + "00", ":83" + "22", ":80" + "02", "\u2014"):
        if w in md: pr.append("banned text in lesson: " + w)
    links = lesson_links(md[md.find("## Sources"):])
    if not links: pr.append("no linked sources")
    for _, u in links:
        if u.rstrip("/") not in sources: pr.append("source not in sources.json: " + u)
    out = (d / "lab_output.txt").read_text().splitlines(); lab = md[md.find("## Lab"):]; lab = lab[:lab.find("\n## ", 6)]
    for block in re.findall(r"```text\n(.*?)```", lab, re.S):
        for l in block.splitlines():
            if l.strip() and l.strip() != "..." and l.rstrip() not in [x.rstrip() for x in out]: pr.append("lab line not in lab_output.txt: " + l[:70])
    bad = lab_imports((d / "lab.py").read_text()) - LAB_IMPORTS
    if bad: pr.append(f"lab imports {sorted(bad)}")
    if "assert " not in (d / "lab.py").read_text(): pr.append("lab has no assert")
    if any(isinstance(n, (ast.Attribute, ast.Name)) and getattr(n, "attr", getattr(n, "id", "")) in ("urlopen", "urlretrieve") for n in ast.walk(ast.parse((d / "lab.py").read_text()))): pr.append("a lab must not touch the network")
    qs = json.loads((d / "quiz.json").read_text()).get("questions", [])
    if len(qs) < 3: pr.append("fewer than 3 quiz questions")
    for q in qs:
        if not q.get("why"): pr.append("quiz answer without a reason: " + q["q"][:50])
        if q.get("options"):
            right = [o for i, o in enumerate(q["options"]) if quiz_right(q, o, i)]
            if len(right) != 1: pr.append(f"quiz question marks {len(right)} options right: " + q["q"][:50])
    for p in c.get("prereq", []):
        if p not in codes: pr.append("unknown prerequisite " + p)
    pr += check_embeds(c, md)
    return pr

def check_embeds(c, md):
    """Everything a lesson embeds must be real: labs on the page, graphs on disk, pictures in the web folder."""
    pr = []; e = lesson_directives(md); plays = play_names()
    for n in e["play"]:
        if n not in plays: pr.append("unknown browser lab " + n)
    for g in set(e["graph"]) | set(c.get("graphs", [])):
        if not (GRAPHS / f"{g}.json").exists(): pr.append("unknown graph " + g)
    for m in e["media"]:
        if m.startswith(("http:", "https:", "/")) or ".." in m or not (WEB / m).exists(): pr.append("media not found in the web folder: " + m)
    tr = {t["slug"] for t in TRACKS()["tracks"]}
    if c.get("track") not in tr: pr.append("unknown track " + str(c.get("track")))
    return pr

KIT = ("## What goes wrong",)
def kit_gaps(c, md=None):
    """What a finished lesson still lacks: a graph, a hands-on check beyond reading, a section on common mistakes, and an account of what was checked."""
    md = md if md is not None else (c["dir"] / "lesson.md").read_text(); e = lesson_directives(md); gaps = []
    if not (set(e["graph"]) | set(c.get("graphs", []))): gaps.append("no graph")
    if not e["play"]: gaps.append("no browser lab")
    for k in KIT:
        if k not in md: gaps.append("no " + k)
    if not c.get("verified"): gaps.append("no verified list")
    return gaps

def complete(c): return all((c["dir"] / n).exists() for n in ("lesson.md", "lab.py", "lab_output.txt", "quiz.json")) and bool(json.loads((c["dir"] / "quiz.json").read_text()).get("questions"))

def reading_minutes(md): return max(1, round(len(re.sub(r"\{\{[^}]*\}\}", "", re.sub(r"```.*?```", "", md, flags=re.S)).split()) / 200))

def write_catalogue(rows, meta):
    """Only finished lessons reach the page. A course folder still missing its lesson or quiz stays off the catalogue. Every count is worked out here, never typed."""
    pub = []
    for c in rows:
        if not complete(c): continue
        md = (c["dir"] / "lesson.md").read_text(); e = lesson_directives(md)
        pub.append({**{k: c[k] for k in ("code", "title", "level", "prereq", "char", "hook")}, "status": c.get("status", "audited"), "path": c["path"], "track": c.get("track"), "order": c.get("order", 999), "plays": sorted(set(e["play"])), "graphs": sorted(set(e["graph"]) | set(c.get("graphs", []))), "minutes": reading_minutes(md), "second_read": c.get("second_read")})
    t = TRACKS(); ver = VERIFIED(); tracks = []
    for tr in t["tracks"]:
        codes = [x["code"] for x in sorted((x for x in pub if x["track"] == tr["slug"]), key=lambda x: (x["order"], x["code"]))]
        if codes: tracks.append({**tr, "codes": codes})
    gids = all_graph_ids(); used = {g for x in pub for g in x["graphs"]}
    counts = {"lessons": len(pub), "audited": sum(x["status"] != "draft" for x in pub), "draft": sum(x["status"] == "draft" for x in pub), "second_read": sum(bool(x["second_read"]) for x in pub), "second_read_pending": sum(not x["second_read"] and x["status"] != "draft" for x in pub), "errors_fixed": sum((x["second_read"] or {}).get("errors_fixed", 0) for x in pub), "plays": len({p for x in pub for p in x["plays"]}), "graphs": len(gids), "graphs_ran": sum(1 for g in gids if ver.get(g, {}).get("ran")), "graphs_used": len(used), "code_refs": sum(len(c.get("code_refs", [])) for c in rows if complete(c))}
    (HERE / "catalogue.json").write_text(json.dumps({"levels": meta["levels"], "characters": meta["characters"], "tracks": tracks, "art": t.get("hero", []), "counts": counts, "courses": pub}, indent=1, ensure_ascii=False) + "\n")
    with open(HERE / "CATALOGUE.md", "w") as f:
        f.write(f"# ComfyUniversity course catalogue\n\n{counts['lessons']} lessons in {len(tracks)} tracks. {counts['second_read']} have had an independent second read, which found and fixed {counts['errors_fixed']} errors. {counts['second_read_pending']} are checked by their author, with the second read pending. {counts['draft']} are labelled Draft. Every lesson has a CPU lab with stored output and a quiz. Rebuild with `python studio/university/build.py --labs`.\n")
        by = {x["code"]: x for x in pub}
        for tr in tracks:
            f.write(f"\n## {tr['title']}\n\n{tr['blurb']}\n\n")
            for code in tr["codes"]:
                c = by[code]; f.write(f"- **{c['code']}** ({c['level']}) [{c['title']}]({c['path']}/lesson.md). {c['hook']}" + (" *Draft.*" if c["status"] == "draft" else "" if c["second_read"] else " *Author-checked, second read pending.*") + (f" Needs {', '.join(c['prereq'])}." if c["prereq"] else "") + "\n")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--labs", action="store_true"); ap.add_argument("--only", nargs="*", default=[]); ap.add_argument("--workers", type=int, default=6); ap.add_argument("--py", default=sys.executable); ap.add_argument("--check-only", action="store_true", help="check, but do not rewrite the catalogue"); a = ap.parse_args()
    rows = courses(); codes = {c["code"] for c in rows}; bad = 0
    if a.labs:
        todo = [c for c in rows if not a.only or c["code"] in a.only]
        def one(c):
            r1 = run_lab(c["dir"] / "lab.py", a.py); r2 = run_lab(c["dir"] / "lab.py", a.py) if r1[0] else r1
            ok = r1[0] and r2[0] and r1[1] == r2[1] and max(r1[2], r2[2]) < LIMIT
            if ok: (c["dir"] / "lab_output.txt").write_text(r1[1])
            return c, ok, r1, r2
        with cf.ThreadPoolExecutor(a.workers) as ex:
            for c, ok, r1, r2 in ex.map(one, todo):
                print(f"{c['code']} lab {'ok' if ok else 'FAILED'} {max(r1[2], r2[2]):.1f} s" + ("" if ok else ("\n" + r1[3] if not r1[0] else " output differs between runs" if r1[1] != r2[1] else " too slow")), flush=True); bad += not ok
    sources = {k.rstrip("/"): v for k, v in SOURCES().items()}
    for c in rows:
        if c.get("status") == "draft" and not complete(c): print(c["code"], "draft is incomplete, left off the catalogue"); continue
        if c.get("status") == "draft": continue
        if not complete(c): print(c["code"], "not finished, left off the catalogue"); continue
        for p in check_course(c, codes, sources): print(c["code"], p); bad += 1
    if not a.check_only: write_catalogue(rows, META())
    print(f"{len(rows)} courses, {bad} problems"); sys.exit(1 if bad else 0)

if __name__ == "__main__": main()
