#!/usr/bin/env python3
"""Pack what Prove It needs from the renders' own records into studio/prove_it.json.gz: each render's exact step graphs, seeds and values, the hash of its original output, the hash of every model file it read, and how far the small web copy already is from that original.
Nothing is estimated. A run folder that has gone leaves its graphs out and the page says so. Fails if a graph holds a folder path.
Usage: build_prove_it.py --results results.jsonl --media DIR --runs DIR [--runs DIR ...] --models DIR --hardware hardware.json [--hash-cache FILE]"""
import argparse, glob, gzip, hashlib, io, json, os, re, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "studio" / "prove_it.json.gz"; WEB = ROOT / "studio" / "web"
MODEL = re.compile(r"\.(safetensors|gguf|ckpt|pt|pth|bin|sft)$", re.I); FRAME_AT = (0.1, 0.5, 0.9); PATHY = re.compile(r"(^|[\s\"'])(/home/|/mnt/|/Users/|[A-Z]:\\)")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(2**22), b""): h.update(c)
    return h.hexdigest()


def pixels_sha(im): return hashlib.sha256(f"{im.size[0]}x{im.size[1]}:".encode() + im.convert("RGB").tobytes()).hexdigest()


def mean_diff(a, b): return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean) / 3


def frame_at(path, seconds):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "f.png"); subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{seconds:.3f}", "-i", str(path), "-frames:v", "1", out], check=True)
        return Image.open(out).convert("RGB").copy()


def duration(path): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip())


def pcm_sha(path): return hashlib.sha256(subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "22050", "-f", "s16le", "-"], capture_output=True, check=True).stdout).hexdigest()


def measure(kind, original, web_copy):
    """The hash of the original, and how far our own web copy is from it: nothing a viewer compares against can read closer than that."""
    if kind == "audio": return {"pcm_sha256": pcm_sha(original)}
    if kind == "video":
        dur, floors = duration(original), []
        for at in FRAME_AT:
            o, w = frame_at(original, dur * at), frame_at(web_copy, min(dur * at, duration(web_copy) - 0.05))
            floors.append(mean_diff(o.resize(w.size, Image.LANCZOS), w))
        return {"seconds": round(dur, 3), "noise_floor": round(max(floors), 3)}
    o, w = Image.open(original).convert("RGB"), Image.open(web_copy).convert("RGB")
    return {"pixels_sha256": pixels_sha(o), "original_size": list(o.size), "noise_floor": round(mean_diff(o.resize(w.size, Image.LANCZOS), w), 3)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--results", required=True); ap.add_argument("--media", required=True); ap.add_argument("--runs", action="append", required=True); ap.add_argument("--models", required=True); ap.add_argument("--hardware", required=True); ap.add_argument("--hash-cache"); a = ap.parse_args()
    results = {}
    for line in open(a.results):
        r = json.loads(line)
        if r.get("status") == "pass": results[r["recipe"]] = r
    renders = json.load(open(ROOT / "studio" / "recipe_renders.json"))["renders"]; rows, names = {}, set()
    for rid, x in renders.items():
        d = next((Path(r) / x["run"] for r in a.runs if (Path(r) / x["run"] / "run.json").is_file()), None); rec = results.get(rid) or {}; row = {"run": x["run"], "kind": x["kind"], "seeds": x.get("seeds") or ({"": x["seed"]} if x.get("seed") is not None else {}), "steps": [], "graphs_kept": bool(d), "values": None, "uploads": bool(rec.get("source"))}
        if d:
            run = json.load(open(d / "run.json")); row.update(values=run.get("values"), uploads=bool(run.get("uploads")) or row["uploads"], seed_add=run.get("seed_add") or 0)
            for st in run.get("steps") or []:
                gp = d / f"{st['id']}.graph.json"; g = json.load(open(gp)) if gp.is_file() else None; row["steps"].append({"id": st["id"], "label": st.get("label"), "type": st.get("type"), "seed": st.get("seed"), "graph_hash": st.get("graph_hash"), "graph": g})
                if g and PATHY.search(json.dumps(g)): sys.exit(f"{rid}/{st['id']}: a graph holds a folder path")
                for n in (g or {}).values():
                    for v in (n.get("inputs") or {}).values():
                        if isinstance(v, str) and MODEL.search(v): names.add(os.path.basename(v))
        original = Path(a.media) / os.path.basename(str(rec.get("media") or "")); copy = WEB / x["file"]
        if rec.get("media") and original.is_file() and copy.is_file():
            try: row.update(measure(x["kind"], original, copy))
            except Exception as e: print("not measured:", rid, type(e).__name__, str(e)[:120])
        rows[rid] = row
    cache = json.load(open(a.hash_cache)) if a.hash_cache and os.path.isfile(a.hash_cache) else {}; models = {}; where = {}
    for dp, _, fn in os.walk(a.models, followlinks=True):
        for f in fn:
            if f in names: where.setdefault(f, os.path.join(dp, f))
    for f in sorted(names):
        p = where.get(f)
        if not p: models[f] = None; continue
        s = os.stat(p); key = f"{f}:{s.st_size}"
        if key not in cache:
            cache[key] = sha256_file(p); print("hashed", f, flush=True)
            if a.hash_cache: json.dump(cache, open(a.hash_cache, "w"))
        models[f] = {"sha256": cache[key], "bytes": s.st_size}
    hw = json.load(open(a.hardware))
    with gzip.GzipFile(OUT, "wb", mtime=0) as f: f.write(json.dumps({"about": "Our render records: the exact graphs, seeds and hashes. Model hashes are of the files those renders read, as they are on the rendering machine when this file was built.", "hardware": hw, "models": models, "renders": rows}, separators=(",", ":")).encode())
    print(len(rows), "renders,", sum(r["graphs_kept"] for r in rows.values()), "with graphs,", len(models), "models,", OUT.stat().st_size >> 10, "KB")


if __name__ == "__main__": main()
