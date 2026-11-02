#!/usr/bin/env python3
"""Publish one real pipeline run on the Pipelines page: small web copies of every stage's output, its graph, and proof.json with model, seed, time and peak VRAM. Run it after looking at the run. Nothing here renders.
usage: record_pipeline.py RUN_FOLDER_OR_ID --id PIPELINE --review REVIEW.json [--root OUTPUTS/recipes]
The review is yours: {"status": "passed|partial|failed", "verdict": "what you saw", "stages": {"<stage id>": {"status": "ok|flawed|failed", "note": "..."}}, "rejected": [{"what": "...", "why": "..."}]}"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent; WEB = ROOT / "studio" / "web" / "pipelines"; DATA = ROOT / "studio" / "pipelines"
LOCAL_PATH = re.compile(r"(/(?:mnt|home|tmp|root|Users|snap)/[^\s\"']*)")
IMG, VID, AUD = (".png", ".jpg", ".jpeg", ".webp"), (".mp4", ".webm", ".mov"), (".wav", ".flac", ".mp3", ".m4a", ".ogg")

def ff(*a): subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, a)], check=True, stdin=subprocess.DEVNULL)
def probe_seconds(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True); return float(r.stdout.strip() or 0)
def has_audio(p):
    return "audio" in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout
def web_copy(src, out_dir, stem, final=False):
    """-> a media row. Videos at 960 wide (a final at 1280), a webp poster from the middle of the clip."""
    ext = src.suffix.lower()
    if ext in IMG:
        dst = out_dir / f"{stem}.webp"; ff("-i", src, "-vf", "scale='min(1400,iw)':-2", "-c:v", "libwebp", "-quality", 86, dst); return {"src": dst.name, "kind": "image"}
    if ext in AUD:
        dst = out_dir / f"{stem}.mp3"; wave = out_dir / f"{stem}_wave.webp"; ff("-i", src, "-c:a", "libmp3lame", "-b:a", "160k", dst); ff("-i", src, "-filter_complex", "aformat=channel_layouts=mono,showwavespic=s=640x300:colors=0xf5c518", "-frames:v", 1, "-c:v", "libwebp", "-quality", 80, wave); return {"src": dst.name, "kind": "audio", "poster": wave.name, "seconds": round(probe_seconds(dst), 1)}
    if ext in VID:
        dst = out_dir / f"{stem}.mp4"; poster = out_dir / f"{stem}.webp"; w = 1280 if final else 960; a = ["-c:a", "aac", "-b:a", "128k"] if has_audio(src) else ["-an"]; d = probe_seconds(src)
        ff("-i", src, "-vf", f"scale='min({w},iw)':-2,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", 23 if final else 26, *a, "-movflags", "+faststart", dst)
        ff("-ss", d / 2, "-i", src, "-frames:v", 1, "-vf", f"scale='min({w},iw)':-2", "-c:v", "libwebp", "-quality", 84, poster); return {"src": dst.name, "kind": "video", "poster": poster.name, "seconds": round(d, 1)}
    return {"kind": "file", "name": src.name, "bytes": src.stat().st_size}
def scrub(obj):
    """No path of this machine reaches the page."""
    if isinstance(obj, dict): return {k: scrub(v) for k, v in obj.items()}
    if isinstance(obj, list): return [scrub(v) for v in obj]
    if isinstance(obj, str): return LOCAL_PATH.sub(lambda m: Path(m.group(1)).name, obj)
    return obj
def prompt_of(spec, st, values):
    fill = lambda t: re.sub(r"\{([a-z_][a-z0-9_]*)\}", lambda m: str(values.get(m.group(1), m.group(0))), t)
    if st.get("body", {}).get("prompt"): return st["body"]["prompt"]
    if spec.get("prompt"): return fill(spec["prompt"])
    for kv in (spec.get("set") or {}).values():
        for k in ("text", "prompt", "tags"):
            if kv.get(k): return fill(kv[k])
    a = spec.get("asset") or {}; s = spec.get("shot") or {}
    return fill((a.get("source") or {}).get("prompt") or (a.get("source") or {}).get("brief") or s.get("prompt") or "")
def _found(f, run_dir):
    """A stage's file: beside the run, or in the output folder the run sits in (ComfyUI's outputs, by the /api/view address the run kept)."""
    q = parse_qs(urlparse(f.get("url") or "").query); sub = (q.get("subfolder") or [f.get("subfolder") or ""])[0]
    for p in (run_dir / f["filename"], run_dir.parent.parent / sub / f["filename"], Path(f.get("local") or "/nonexistent")):
        if p.is_file(): return p
    return None
def record(run_dir, pid, review, web=WEB, data=DATA):
    rec = json.loads((data / f"{pid}.json").read_text(encoding="utf-8")); run = json.loads((run_dir / "run.json").read_text(encoding="utf-8")); specs = {s["id"]: s for s in rec["steps"]}
    if run["recipe"] != pid: raise SystemExit(f"that run belongs to {run['recipe']}, not {pid}")
    out = web / pid; tmp = web / f".{pid}.new"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True); (tmp / "graphs").mkdir(); licences = {m["name"]: m for m in rec["models"]}; stages = []
    for st in run["steps"]:
        spec = specs.get(st["id"], {}); media = []; n = 0
        for f in st.get("files") or []:
            p = _found(f, run_dir)
            if not p: continue
            n += 1; media.append(web_copy(p, tmp, st["id"] if n == 1 else f"{st['id']}_{n}", final=bool(st.get("final"))))
        graph = run_dir / f"{st['id']}.graph.json"; gname = ""
        if graph.is_file(): gname = f"graphs/{st['id']}.json"; (tmp / gname).write_text(json.dumps(scrub(json.loads(graph.read_text())), indent=0), encoding="utf-8")
        mine = (review.get("stages") or {}).get(st["id"]) or {}; m = licences.get(spec.get("model")) or {}
        stages.append(scrub({"id": st["id"], "label": st.get("label"), "type": st.get("type"), "does": spec.get("does", ""), "model": spec.get("model") or st.get("model") or "", "licence": m.get("licence", ""), "licence_class": m.get("licence_class", ""), "seed": st.get("seed"), "seconds": st.get("seconds"), "peak_gib": st.get("peak_gib"), "ran": st.get("status"), "status": mine.get("status") or ("ok" if st.get("status") == "done" else "failed"), "note": mine.get("note") or st.get("error") or "", "prompt": prompt_of(spec, st, run.get("values") or {}), "media": media, "graph": gname, "final": bool(st.get("final")), "build": st.get("build")}))
    final = next((s for s in reversed(stages) if s["final"] and s["media"]), None)
    proof = scrub({"id": pid, "status": review["status"], "verdict": review["verdict"], "run": run["run"], "rendered": time.strftime("%Y-%m-%d", time.localtime(run.get("finished") or time.time())), "seconds": round(sum(s["seconds"] or 0 for s in stages), 1), "wall_seconds": run.get("seconds"), "peak_vram_gib": run.get("peak_vram_gib"), "peak_note": "Peak is this run's own ComfyUI and tools, read from nvidia-smi every 2 seconds. The card was shared with other work.", "values": run.get("values"), "final": (final or {}).get("media", [None])[0], "stages": stages, "rejected": review.get("rejected") or []})
    (tmp / "proof.json").write_text(json.dumps(proof, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if out.exists(): shutil.rmtree(out)
    tmp.rename(out); return proof
def main(argv=None):
    a = argparse.ArgumentParser(); a.add_argument("run"); a.add_argument("--id", required=True); a.add_argument("--review", required=True); a.add_argument("--root", default=""); o = a.parse_args(argv)
    run_dir = Path(o.run) if os.path.isdir(o.run) else Path(o.root or os.path.join(os.environ.get("STUDIO_OUTPUT_DIR", ""), "recipes")) / o.run
    if not (run_dir / "run.json").is_file(): raise SystemExit(f"no run.json in {run_dir}")
    p = record(run_dir, o.id, json.loads(Path(o.review).read_text(encoding="utf-8")))
    size = sum(f.stat().st_size for f in (WEB / o.id).rglob("*") if f.is_file()); print(f"{o.id}: {p['status']}, {len(p['stages'])} stages, {size / 1e6:.1f} MB")
if __name__ == "__main__": sys.exit(main())
