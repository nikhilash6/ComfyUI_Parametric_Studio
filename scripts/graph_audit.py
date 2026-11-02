"""Check every graph the studio ships against a live ComfyUI's /object_info and the model files on disk, and write a table: graph, status, detail, proof.
Read-only: it GETs /object_info and never queues anything.
  python scripts/graph_audit.py --out GRAPH_AUDIT.tsv [--comfy http://127.0.0.1:8200] [--oi extra_object_info.json ...] [--snapshot tests/fixtures/graph_audit_object_info.json.gz]
--oi adds the node lists of other running servers (a family instance), so a family template is checked against the packs its own instance loads.
--snapshot writes the trimmed node list the CI test reads. PSN_NODE_INDEX and PSN_WORKER_DIR point at the pack library's node index and the worker folder, when this machine has them."""
import argparse, csv, gzip, json, os, re, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import graph_audit as GA

NODE_INDEX = os.environ.get("PSN_NODE_INDEX", "")                 # the pack library's node index (one JSON object per node: id, repo, stars): names the pack an unknown node comes from
WORKER = Path(os.environ.get("PSN_WORKER_DIR", "") or ".")          # where MODEL_USE_MAP_*.tsv and MODEL_VIEWED_*.tsv live, for the proof column


def pack_index():
    out = {}
    if not NODE_INDEX: return out
    try:
        for l in open(NODE_INDEX, encoding="utf-8"):
            try: d = json.loads(l)
            except ValueError: continue
            out.setdefault(d["id"], []).append((d.get("stars") or 0, d.get("repo") or d.get("pack")))
    except OSError: pass
    return {k: [r for _, r in sorted(v, reverse=True)] for k, v in out.items()}


def proof_text():
    """Everything that records a finished run, as {source: text}, to look graph names up in."""
    S = GA.STUDIO; out = {}
    try:
        d = json.load(open(S / "family_status.json"))
        out["family media"] = " ".join(f"{m.get('tpl')}" for r in d["families"].values() for m in r.get("media") or [] if m.get("own") and m.get("tpl"))
    except Exception: pass
    for name in ("recipe_renders.json", "music_proof.json", "motion_proof.json", "model3d_proof.json", "voice_proof.json"):
        try: out[name] = open(S / name, encoding="utf-8").read()
        except OSError: pass
    try: out["university verified"] = " ".join(k for k, v in json.load(open(S / "university" / "graphs" / "verified.json"))["graphs"].items() if v.get("ran"))
    except Exception: pass
    try: out["res4lyf results"] = " ".join(k for k, v in json.load(open(S / "web" / "res4lyf_renders" / "results.json")).items() if v.get("ok"))
    except Exception: pass
    out["res4lyf node renders"] = " ".join(p.stem for p in (S / "web" / "res4lyf_renders" / "nodes").glob("*.jpg"))
    try:
        rows = list(csv.DictReader(open(WORKER / "MODEL_USE_MAP_2026-11-01.tsv", encoding="utf-8"), delimiter="\t"))
        out["MODEL_USE_MAP"] = " ".join(r["proof"] for r in rows if r.get("status") == "rendered")
    except OSError: pass
    try: out["MODEL_VIEWED"] = " ".join(l.split("\t")[0] for l in open(WORKER / "MODEL_VIEWED_2026-11-01.tsv", encoding="utf-8") if not l.startswith("#"))
    except OSError: pass
    try:
        from studio import pipelines as P
        out["pipeline proof"] = " ".join(r["id"] for r in P.rows() if (P.proof(r["id"]) or {}).get("status") in ("ran", "rendered", "done", "passed") or (P.proof(r["id"]) or {}).get("final"))
    except Exception: pass
    return out


def proof_for(row, texts):
    names = set()
    stem = re.split(r"[:/]", row["id"])[-1]
    if row["path"]: names.add(Path(row["path"]).stem)
    if row["source"] != "recipe/pipeline steps": names.add(stem)
    if row.get("template"): names.add(row["template"])
    if row["id"].startswith("goal:"): names.add(stem)
    names = {n.replace("_api", "") for n in names} | names
    for src, t in texts.items():
        for n in names:
            if n and len(n) > 3 and re.search(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9_])", t): return f"yes ({src}: {n})"
    for u in row.get("used_by") or []:
        rid = u.split(":", 1)[1].split("#")[0]
        if re.search(r'"' + re.escape(rid) + r'"\s*:', texts.get("recipe_renders.json", "")): return f"yes (recipe_renders.json: {rid})"
        if u.startswith("pipeline:") and rid in texts.get("pipeline proof", "").split(): return f"yes (pipeline proof: {rid})"
    return "no"


def snapshot_of(oi, used):
    keep = json.loads(json.dumps({k: v for k, v in oi.items() if k in used}))
    for cls, v in keep.items():
        for k in ("description", "display_name", "category", "search_aliases", "essentials_category"): v.pop(k, None)
        for sec in ("required", "optional"):
            for name, spec in ((v.get("input") or {}).get(sec) or {}).items():
                if isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict): spec[1].pop("tooltip", None)
                o = GA._spec_opts(spec)
                if o is not None and (GA._model_list(o) or len(o) > 300 or cls in GA.UPLOAD_LOADERS or name in ("folder", "image", "video", "audio", "file", "model_file")):
                    if isinstance(spec[0], list): spec[0] = ["__files__"]
                    else: spec[1]["options"] = ["__files__"]
    return keep


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--comfy", default="http://127.0.0.1:8200"); ap.add_argument("--oi", nargs="*", default=[]); ap.add_argument("--snapshot"); ap.add_argument("--json"); ap.add_argument("--lane", help="the object_info of a lane with every pack the studio's pages use, for the snapshot")
    a = ap.parse_args()
    oi = json.load(urllib.request.urlopen(a.comfy + "/object_info", timeout=120)); union = dict(oi)
    for p in a.oi: union.update({k: v for k, v in json.load(open(p)).items() if k not in union})
    from studio import recipe_check as C, families_api as F
    files = C.model_files(); fscan = F.scan(True); packs = pack_index(); texts = proof_text()
    rows = GA.collect(oi); out = []; used = set(); views = {}
    for r in rows:
        fam = r.get("family"); target = r["target"]; fixes = []
        use = GA.server_oi(union, GA.family_packs(fam)) if target == "family" and fam else oi
        api, conv, fmt = GA.to_api(r, use)
        probs = [("bad-input", "convert: " + c) for c in conv]
        if r.get("build_error"): probs.append(("bad-input", r["build_error"]))
        if api is None and fmt in ("missing",) and not r.get("build_error"): probs.append(("bad-input", "graph file is missing"))
        if api is not None:
            used |= {n.get("class_type") for n in api.values()}
            ffiles = files if not (target == "family" and fam) else {**files, **(fscan.get(fam) or {})}
            extra = views.setdefault(fam, GA.family_view(fam)) if target == "family" and fam else set()
            fixes = []; notes = []; probs += GA.check(api, use, ffiles, extra_names=extra, fixes=fixes, resolves=r.get("resolves", True), notes=notes)
        st = GA.status(probs, "api" if api is not None else fmt)
        if fmt == "other": st = "not-api-format"
        detail = []
        for k, t in probs:
            if k == "missing-node":
                cls = t.split(":", 1)[1].rsplit(" is not installed", 1)[0]; src = packs.get(cls)
                loaded = {GA.module_pack(v) for kk, v in union.items() if kk == cls}
                t += f" (pack: {loaded.pop()}, not loaded on this server)" if loaded else (f" (pack: {src[0]})" if src else " (no known pack)")
            detail.append(t)
        if api is not None and notes: detail += ["swapped: " + "; ".join(dict.fromkeys(notes))]
        nd = GA.needs(r.get("graph"), r.get("meta"))
        if nd: detail.insert(0, "needs: " + "; ".join(nd))
        if r.get("used_by"): detail.append("used by " + ", ".join(r["used_by"][:4]) + (f" +{len(r['used_by']) - 4}" if len(r["used_by"]) > 4 else ""))
        out.append({"graph": r["id"], "status": st, "detail": " | ".join(dict.fromkeys(detail))[:1500], "proof": proof_for(r, texts), "source": r["source"], "path": r["path"], "family": fam or "", "problems": probs, "fixes": fixes if api is not None else [], "fmt": fmt})
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n"); w.writerow(["graph", "status", "detail", "proof", "source", "path", "family"])
        for o in out: w.writerow([o["graph"], o["status"], o["detail"].replace("\t", " ").replace("\n", " "), o["proof"], o["source"], o["path"], o["family"]])
    if a.json: json.dump(out, open(a.json, "w"), indent=1)
    if a.snapshot:
        lane = json.load(open(a.lane)) if a.lane else union
        snap = {"comfyui": "v0.43.0", "note": "Trimmed /object_info for tests/test_graph_audit.py: the node types the studio's graphs use. main is 127.0.0.1:8200; lane is a ComfyUI with 8200's packs plus the family and page packs (RES4LYF, RyanOnTheInside, AnimateDiff-Evolved, IC-Light, CCSR, LivePortraitKJ) and this tree's own nodes. Model, upload and folder choice lists are this machine's files and are replaced by __files__.",
                "main": snapshot_of(oi, used), "lane": snapshot_of(lane, used)}
        with gzip.open(a.snapshot, "wt", encoding="utf-8") as f: json.dump(snap, f, separators=(",", ":"))      # key order is widget order: never sort it
    from collections import Counter
    print(Counter(o["status"] for o in out), len(out))


if __name__ == "__main__": main()
