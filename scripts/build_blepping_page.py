#!/usr/bin/env python3
"""Builds the blepping page's data from our own lab run: smaller copies of each render, the graph that made it, and the numbers.

Reads the throwaway lab folder (results_core.jsonl from the run with no packs, results_packs.jsonl from the run with the four packs,
the jobs files with the graphs, and object_info_packs.json for node and option names). Writes studio/web/blepping_renders/ and
studio/web/blepping_data.js. Pack code is never imported or run here; only names and counts are taken from the lab's /object_info.
Usage: build_blepping_page.py <lab dir> <repo root>
"""
import hashlib, json, pathlib, re, sys

from PIL import Image, ImageChops, ImageStat

LAB, ROOT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
WEB = ROOT / "studio" / "web"; OUT = WEB / "blepping_renders"; GRAPHS = OUT / "graphs"
MODELS = {"sd15": "SD 1.5", "sdxl": "SDXL base 1.0", "sd35": "SD 3.5 Medium"}
PACKS = {"ComfyUI-bleh": ("bleh", "1c2bc62", "Apache-2.0"), "ComfyUI-sonar": ("sonar", "6c4ae67", "MIT"), "comfyui_overly_complicated_sampling": ("ocs", "d8574ba", "MIT"), "Skoogeer-Noise": ("skoogeer", "86d3d20", "MIT")}


def rows(name):
    p = LAB / name
    if not p.exists(): return {}
    out = {}
    for line in p.read_text().splitlines():
        r = json.loads(line); out[r["id"]] = r          # a later line for the same id is a retry after a stop, never a re-roll
    return out


def mean_diff(a, b):
    """Mean absolute pixel difference, 0 to 255, over RGB; None if the sizes differ."""
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size: return None
    return round(sum(ImageStat.Stat(ImageChops.difference(ia, ib)).mean) / 3, 2)


def pixels(path):
    """sha256 of the decoded RGB pixels. The PNG files themselves differ even for identical pictures, because each one embeds its own graph."""
    return hashlib.sha256(Image.open(path).convert("RGB").tobytes()).hexdigest()


def main():
    jobs = {j["id"]: j for f in ("jobs_core.json", "jobs_packs.json") for j in json.loads((LAB / f).read_text())}
    res = {**rows("results_core.jsonl"), **rows("results_packs.jsonl")}
    OUT.mkdir(exist_ok=True); GRAPHS.mkdir(exist_ok=True)
    renders = []
    for jid, j in jobs.items():
        r = res.get(jid)
        if r is None: continue
        g = json.loads(json.dumps(j["graph"]))
        (GRAPHS / f"{jid}.json").write_text(json.dumps(g, indent=1) + "\n")
        row = {"id": jid, "pack": j["pack"], "model": MODELS[j["model"]], "what": j["what"], "base": j.get("base"), "ok": bool(r.get("ok")), "seconds": r.get("seconds"),
               "peak": r.get("peak_gib"), "graph": f"blepping_renders/graphs/{jid}.json", "run": "no packs loaded" if j.get("mode") == "core" else "all four packs loaded"}
        if not r.get("ok"): row["error"] = re.sub(r"/\S*?/custom_nodes/", "", r.get("error") or "")[:400]   # no local paths on the page
        if jid == "ocs-unsafe-refused": row["expected_refusal"] = True   # a negative test: refusing is the pass
        if r.get("retry"): row["retry"] = r["retry"]
        if r.get("file"):
            im = Image.open(r["file"]).convert("RGB"); row["size"] = list(im.size); row["pixels"] = pixels(r["file"])
            if r.get("images", 1) > 1:   # a batch: show the first four side by side
                ims = [im] + [Image.open(str(r["file"]).replace(".png", f"_{i}.png")).convert("RGB") for i in range(1, min(4, r["images"]))]
                w, h = ims[0].size; sheet = Image.new("RGB", (w * 2, h * 2))
                for i, x in enumerate(ims): sheet.paste(x, ((i % 2) * w, (i // 2) * h))
                im = sheet
            im.thumbnail((768, 768)); im.save(OUT / f"{jid}.jpg", quality=82)
            row["src"] = f"blepping_renders/{jid}.jpg"; row["sha256"] = r.get("sha256")
            b = res.get(j.get("base") or "")
            if b and b.get("file"): row["diff"] = mean_diff(r["file"], b["file"])
        if "preview_frames" in r: row["preview_frames"] = r["preview_frames"]
        if r.get("last_preview"):
            p = pathlib.Path(r["last_preview"])
            try:
                import io
                pi = Image.open(io.BytesIO(p.read_bytes())); row["preview_size"] = list(pi.size)
                pi.convert("RGB").save(OUT / f"{jid}_preview.jpg", quality=82); row["preview_src"] = f"blepping_renders/{jid}_preview.jpg"
            except Exception as e:  # noqa: BLE001
                row["preview_error"] = str(e)[:200]
        renders.append(row)
    info = json.loads((LAB / "object_info_packs.json").read_text())
    nodes = {}
    for k, v in info.items():
        mod = str(v.get("python_module") or "")
        if mod.startswith("custom_nodes."): nodes.setdefault(mod.split(".")[1], []).append(k)
    noise = info["SonarCustomNoise"]["input"]["required"]["noise_type"][0]
    steps = info["OCS Substeps"]["input"]["required"]["step_method"][0]
    merges = info["OCS Group"]["input"]["required"]["merge_method"][0]
    samplers = info["KSampler"]["input"]["required"]["sampler_name"][0]
    stage0 = [{"id": r["id"], "base": r["base"], "same_pixels": bool(r.get("pixels")) and r.get("pixels") == next((x.get("pixels") for x in renders if x["id"] == r["base"]), None), "diff": r.get("diff")} for r in renders if r["id"].startswith("s0-")]
    data = {"packs": {PACKS[p][0]: {"folder": p, "commit": PACKS[p][1], "licence": PACKS[p][2], "nodes": len(n)} for p, n in nodes.items() if p in PACKS},
            "noise_types": noise, "step_methods": steps, "merge_methods": merges, "added_samplers": [s for s in samplers if s.startswith(("sonar_", "bleh_"))],
            "stage0": stage0, "renders": renders, "seed": 424242, "steps": 20,
            "prompt": "a weathered brass astrolabe on an oak table beside a stack of old sea charts, warm window light, shallow depth of field, fine engraving detail, photograph"}
    (WEB / "blepping_data.js").write_text("// Generated by scripts/build_blepping_page.py from our own lab run. Names and counts only; no code from the packs.\nexport const DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print(len(renders), "renders,", sum(1 for r in renders if r["ok"]), "ok")


if __name__ == "__main__":
    main()
