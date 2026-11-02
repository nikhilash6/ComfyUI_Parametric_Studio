"""Records in studio/family_status.json what the family watcher really rendered: a family's level, its test row, and small web copies with model and seed. It reads the watcher's results and each instance's job records, and it writes in the file's own format.
A render counts for a family only when the model in its graph is that family's: a Wan 2.2 clip under Matrix-3D is not a Matrix-3D render. Run with --dry-run to see the changes."""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; STATUS = ROOT / "studio" / "family_status.json"; WEB = ROOT / "studio" / "web" / "families"
#: Templates that ran under a family but whose main model belongs to another one, read from the job's graph. They prove nothing about this family.
NOT_THIS_FAMILY = {"Matrix-3D": {"video_wan2_2_5B_ti2v"}, "rife": {"utility_video_frame_interpolation"}, "Flux.1": {"image_flux2_klein_text_to_image"}, "upscale_models": {"birefnet_cutout"}, "TRELLIS-2-4B": {"3d_triposplat_image_to_gaussian_splat"}, "TripoSR": {"3d_triposplat_image_to_gaussian_splat"}}
#: Ran to the end but the picture says otherwise: Ideogram 4 returned its grey "Image blocked by safety filter" card on these neutral test prompts. Not a render.
NOT_A_RENDER = {"Ideogram4": {"ideogram4_json_t2i", "ideogram4_poster_t2i"}}
#: Fine runs of a template's own sample people; the studio's pages don't show faces we can't vouch for.
NOT_SHOWN = {"Ovis-Image": {"image_ovis_text_to_image"}, "MiniMax-H3": {"video_minimax_h3_multiframe_reference", "video_minimax_h3_r2v"}, "Kandinsky-5.0-T2I-Lite": {'video_kandinsky5_t2v'}}
MAX_NEW = 4; IMG = (".png", ".jpg", ".jpeg", ".webp"); VID = (".mp4", ".webm", ".mov"); AUD = (".wav", ".flac", ".mp3", ".ogg", ".m4a")


def dump(d):
    """The file's own format: one value per line, no indent, non-ASCII kept."""
    return json.dumps(d, indent=0, ensure_ascii=False) + "\n"


def job_records(path):
    """{template: the last finished record} from an instance's job log. A broken line is skipped."""
    out = {}
    try:
        for ln in open(path, encoding="utf-8"):
            try: r = json.loads(ln)
            except ValueError: continue
            if r.get("status") == "done": out[r.get("template")] = r
    except OSError: pass
    return out


def model_of(graph):
    """The main model a graph loads: its diffusion model or checkpoint if it has one, else the first model file."""
    names = []
    for key in ("unet_name", "ckpt_name", "model_name", "model_file", "model_name", "upscale_model"):
        for n in (graph or {}).values():
            v = (n.get("inputs") or {}).get(key)
            if isinstance(v, str) and re.search(r"\.(safetensors|ckpt|pt|pth|bin|gguf)$", v): names.append(os.path.basename(v))
        if names: break
    return names[0] if names else None


def made_here(path):
    """A file named studio_<hash> is our own upload echoed back by a loader, so the run made nothing new with that name."""
    return "studio_" not in Path(path).name


def proven(fam, rec, jobs):
    """The tries that prove this family: finished, with a file, whose model is the family's own. -> [(try, job record)]"""
    out = []
    for t in rec.get("tries") or []:
        if t.get("status") == "done" and any(made_here(f) for f in t.get("files") or []) and t["template"] not in NOT_THIS_FAMILY.get(fam, ()) and t["template"] not in NOT_A_RENDER.get(fam, ()):
            out.append((t, jobs.get(t["template"]) or {}))
    return out


def web_copy(src, dest_base, run=subprocess.run):
    """A small web copy. -> media fields, or None when the file is no media a page can show."""
    from PIL import Image
    ext = src.suffix.lower()
    if ext in IMG:
        d = dest_base.with_suffix(".webp")
        with Image.open(src) as im:
            im = im.convert("RGB"); im.thumbnail((640, 640)); im.save(d, "WEBP", quality=78); w, h = im.size
        return {"kind": "image", "src": f"families/{d.name}", "poster": f"families/{d.name}", "w": w, "h": h}
    if ext in VID:
        d, p = dest_base.with_suffix(".mp4"), dest_base.with_suffix(".webp")
        run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src), "-t", "6", "-vf", "scale='min(640,iw)':-2", "-c:v", "libx264", "-crf", "30", "-preset", "slow", "-pix_fmt", "yuv420p", "-an", str(d)], check=True)
        run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(d), "-vframes", "1", str(p)], check=True)
        return {"kind": "video", "src": f"families/{d.name}", "poster": f"families/{p.name}"}
    if ext in AUD:
        d = dest_base.with_suffix(".mp3")
        run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src), "-t", "30", "-b:a", "96k", str(d)], check=True)
        return {"kind": "audio", "src": f"families/{d.name}"}
    return None


def next_index(media, slug):
    n = -1
    for m in media:
        x = re.match(rf"families/{re.escape(slug)}_(\d+)\.", m.get("src") or "")
        if x: n = max(n, int(x.group(1)))
    return n + 1


def apply_family(fam, row, rec, jobs, *, web=WEB, copy=web_copy, today="2026-11-01"):
    """Updates one row in place. -> what changed, in words."""
    good = proven(fam, rec, jobs); said = []; slug = row["slug"]; media = row.setdefault("media", [])
    listed = {m.get("tpl") for m in media if m.get("own")}; i = next_index(media, slug); new = []
    for t, job in good:
        if t["template"] in listed or t["template"] in NOT_SHOWN.get(fam, ()) or len(new) >= MAX_NEW: continue
        src = next((Path(f) for f in t["files"] if Path(f).suffix.lower() in IMG + VID + AUD and made_here(f)), None)
        if src is None or not src.exists(): continue
        fields = copy(src, web / f"{slug}_{i}")
        if not fields: continue
        new.append({"id": f"fam_{slug}_{i}", "prompt": job.get("prompt") or t["template"], "seconds": t.get("wall_s"), "tpl": t["template"], "own": True, **fields, "model": model_of(job.get("graph")), "seed": job.get("seed"), **({"peak_vram_gib": t["peak_gib"]} if t.get("peak_gib") else {})}); listed.add(t["template"]); i += 1
    if new:
        lib = [m for m in media if m.get("library")]; row["media"] = [m for m in media if not m.get("library")] + new + ([] if good else lib); said.append(f"{len(new)} new web copies")
    if good and row.get("level") != "render":
        t, job = good[0]; test = row.setdefault("test", {}); test.update(tpl=t["template"], render="ok", tested=today, secs=t.get("wall_s"), note=f"{t['template']} rendered on this box {today} (seed {job.get('seed')}, model {model_of(job.get('graph'))})")
        if t.get("peak_gib"): test["peak_gib"] = t["peak_gib"]
        said.append(f"level {row.get('level')} -> render"); row["level"] = "render"
    return said


def demote(row, why):
    """A 'render' that the graph shows was another family's model is not a render of this one."""
    row["level"] = "nodes"; row["media"] = [m for m in row.get("media") or [] if not m.get("own")]
    row["test"] = {k: v for k, v in (row.get("test") or {}).items() if k in ("nodes", "psn", "tested")} | {"note": why}


#: Corrected by hand after reading each job's graph.
DEMOTE = {"Matrix-3D": "Earlier test ran Wan 2.2 5B text to video, which reads none of Matrix-3D's own weights, so that proved nothing about this model. No runner for Matrix-3D's panorama video and LRM checkpoints exists here yet."}


def main(argv=None):
    a = argparse.ArgumentParser(); a.add_argument("--all-json", required=True); a.add_argument("--instances", required=True); a.add_argument("--dry-run", action="store_true"); a = a.parse_args(argv)
    d = json.load(open(STATUS, encoding="utf-8")); res = json.load(open(a.all_json))["families"]; by = {r["slug"]: f for f, r in d["families"].items()}
    for fam, why in DEMOTE.items(): demote(d["families"][fam], why); print(fam, "demoted")
    for slug, rec in res.items():
        fam = by.get(slug)
        if not fam: print("no row for", slug); continue
        said = apply_family(fam, d["families"][fam], rec, job_records(os.path.join(a.instances, slug, "studio_jobs.jsonl")), copy=(lambda s, b: {"kind": "dry", "src": str(b)}) if a.dry_run else web_copy)
        if said: print(fam, said)
    if not a.dry_run: STATUS.write_text(dump(d), encoding="utf-8")
    lv = {}
    for r in d["families"].values(): lv[r.get("level")] = lv.get(r.get("level"), 0) + 1
    print(lv)


if __name__ == "__main__": main()
