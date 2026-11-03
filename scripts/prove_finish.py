"""Proof renders for LTX Finish, on AI-generated clips only (the studio's own showcase renders, degraded on purpose with ffmpeg).
Each GPU batch waits its turn at the shared VRAM gate (gpu_gate.py, found through GPU_GATE_TOOLS), holds one reservation for the batch, and records model, seed, time and peak VRAM.
Nothing here judges a picture: look at every output (the `sheets` step draws them side by side) before `pack` puts it on the page.

  FINISH_COMFYUI_URL=http://127.0.0.1:<lane> FINISH_LANE_OUTPUT=<lane output dir> python scripts/prove_finish.py <step>
  steps: inputs  render [effect ...]  seedvr2  page [effect clip]  fresh [effect ...]  measure  sheets  pack
Work files go to $FINISH_PROOF_WORK (default ./finish_proof_work). `pack` writes studio/finish_proof.json and copies the shown media to studio/web/finish/."""
import argparse, json, os, re, shutil, subprocess, sys, threading, time, urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO))
if os.environ.get("GPU_GATE_TOOLS"): sys.path.insert(0, os.environ["GPU_GATE_TOOLS"])
from studio import feature_finish as F, finish_measure as M

WORK = Path(os.environ.get("FINISH_PROOF_WORK") or REPO / "finish_proof_work"); LOG = WORK / "log.json"; INP = WORK / "inputs"; OUT = WORK / "renders"
SHOW = REPO / "studio" / "web" / "showcase"; WEB = REPO / "studio" / "web" / "finish"
LANE_OUT = Path(os.environ.get("FINISH_LANE_OUTPUT") or "")
C = F.Comfy(); PORT = urllib.parse.urlparse(C.url).port
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
GH = "a vast glass greenhouse glowing bright green at night, thin fog rolling over the ground, a single warm lamp beside the door, one small figure standing in front, deep blue night sky"
TP = "a dense tropical jungle around an overgrown stone temple ruin, sun rays through the canopy, giant ferns and hanging vines"
TP_COLORS = "a dense tropical jungle in lush deep greens around an overgrown grey stone temple ruin, warm golden sun rays and orange light through the canopy, giant green ferns and brown hanging vines"
#: effect: input clip (made by `inputs`), the clean original it is measured against, scene words, colour words, seed. Seed 42 is the cards' own production seed.
PLAN = {
    "restore": {"input": "gh_mixed.mp4", "clean": "gh_clean.mp4", "scene": GH, "damage": "Gaussian blur (sigma 2.5), film-grain noise (14) and H.264 CRF 40"},
    "deblur": {"input": "gh_blur.mp4", "clean": "gh_clean.mp4", "scene": GH, "damage": "Gaussian blur, sigma 4"},
    "decompress": {"input": "gh_crf45.mp4", "clean": "gh_clean.mp4", "scene": GH, "damage": "H.264 at CRF 45"},
    "colorize": {"input": "tp_grey.mp4", "clean": "tp_clean.mp4", "scene": TP, "colors": TP_COLORS, "damage": "every colour taken out (ffmpeg hue=s=0)"},
    "upscale": {"input": "gh_half.mp4", "clean": "gh_clean.mp4", "scene": GH, "damage": "shrunk to half size, 480x272"},
    "hdr": {"input": "fl_sdr.mp4", "clean": None, "scene": "", "damage": "none: an ordinary SDR BT.709 clip"},
    # the same three repairs on a clip full of fine detail, where a soft original can't flatter the numbers
    "restore@temple": {"effect": "restore", "input": "tp_mixed.mp4", "clean": "tp_clean.mp4", "scene": TP, "damage": "Gaussian blur (sigma 2.5), film-grain noise (14) and H.264 CRF 40"},
    "deblur@temple": {"effect": "deblur", "input": "tp_blur.mp4", "clean": "tp_clean.mp4", "scene": TP, "damage": "Gaussian blur, sigma 4"},
    "decompress@temple": {"effect": "decompress", "input": "tp_crf45.mp4", "clean": "tp_clean.mp4", "scene": TP, "damage": "H.264 at CRF 45"},
}
SOURCES = {"gh": "v_ltx_greenhouse.mp4", "tp": "v_wan_temple.mp4", "fl": "vfx_flood.mp4"}
NO_TEXT = "no signs, no text, no lettering, no logos, no watermark"
NEG_T2V = "worst quality, inconsistent motion, blurry, jittery, distorted, watermark, text, letters, logo, signage, nudity"
#: The varied set: one fresh LTX-2.5 text-to-video clip per effect (invented, fully clothed adults; no lettering), damaged here with ffmpeg so the before/after is honest.
#: key: the clean source's prompt and seed, the scene words the repair gets, the damage (an ffmpeg filter chain and CRF) and what to call it on the page.
FRESH = {
    "colorize": {"seed": 1101, "t2v": "A cobblestone city street in the 1950s on an overcast morning, invented adults in long wool coats and hats walking past shop fronts with red and green striped awnings, a green and cream tram passing slowly, a woman in a blue coat crossing the street, fully clothed, realistic film look, " + NO_TEXT,
                 "scene": "a cobblestone city street in the 1950s, adults in long coats and hats walking past shop fronts with striped awnings, a tram passing", "colors": "red and green striped awnings, a green and cream tram, a woman in a blue coat, brown and grey wool coats, grey cobblestones, pale overcast sky",
                 "vf": "hue=s=0", "crf": 6, "damage": "every colour taken out (ffmpeg hue=s=0) from a fresh colour render"},
    "restore": {"seed": 1102, "t2v": "A family picnic on a sunny lawn in the 1970s, three invented adults in fully clothed summer clothes of the era laughing on a red checked blanket, a wicker basket and lemonade, leafy trees behind, warm afternoon light, handheld home-movie framing, " + NO_TEXT,
                "scene": "a family picnic on a sunny lawn in the 1970s, three adults in summer clothes laughing on a red checked blanket, a wicker basket, leafy trees, warm afternoon light",
                "vf": "colorchannelmixer=.50:.40:.15:0:.38:.45:.12:0:.25:.30:.25,eq=contrast=0.78:brightness=0.06:saturation=0.75:eval=frame,eq=brightness='0.035*sin(n*1.9)':eval=frame,gblur=sigma=1.8,noise=alls=18:allf=t",
                "crf": 34, "scratches": True, "damage": "an old home-movie look added with ffmpeg to a fresh render: faded sepia colour, flicker, soft focus, grain, two moving scratches and CRF 34 compression"},
    "deblur": {"seed": 1103, "t2v": "A cyclist in a bright red jacket and black helmet riding along a sunny seaside promenade, palm trees and a blue sea behind, white railings, the camera tracking smoothly alongside, crisp sharp detail, fully clothed adult, " + NO_TEXT,
               "scene": "a cyclist in a bright red jacket and black helmet riding along a sunny seaside promenade, palm trees, white railings and a blue sea",
               "vf": "gblur=sigma=4", "crf": 6, "damage": "lens-style defocus (Gaussian blur, sigma 4) added to a fresh render. The Deblur card covers defocus, not motion blur, so this is defocus"},
    # a night market came out with sign boards of made-up glyphs (seed 1104), against our no-lettering rule, so the blocky night scene is floating lanterns instead
    "decompress": {"seed": 1114, "t2v": "Hundreds of glowing paper lanterns floating on a dark river at night, warm orange light rippling on the water, invented adults in plain dark coats kneeling at the stone bank releasing more lanterns, sparks of light drifting, slow camera glide along the bank, " + NO_TEXT,
                   "scene": "hundreds of glowing paper lanterns floating on a dark river at night, warm light rippling on the water, adults in dark coats releasing lanterns from a stone bank",
                   "vf": "null", "crf": 45, "damage": "H.264 at CRF 45 on a fresh render: heavy macroblocking"},
    "hdr": {"seed": 1105, "t2v": "A small fishing harbour at sunset, wooden boats bobbing on the water, the sun low and blazing on the horizon, glittering golden reflections on the waves, a warm orange and violet sky, gulls flying, slow pan, " + NO_TEXT,
            "scene": "", "vf": "null", "crf": 10, "damage": "none: a fresh SDR BT.709 render"},
    "upscale": {"seed": 1106, "t2v": "Macro close-up of a hand-woven wool tapestry in deep indigo and gold rippling gently in a breeze beside bright green fern fronds, every thread and leaf vein in sharp focus, soft daylight, " + NO_TEXT,
                "scene": "macro close-up of a hand-woven wool tapestry in deep indigo and gold rippling beside green fern fronds, every thread visible",
                "vf": "scale=480:272:flags=area", "crf": 6, "damage": "shrunk to half size, 480x272, from a fresh 960x544 render"},
}


def log(): return json.loads(LOG.read_text()) if LOG.exists() else {}


def put(key, rec):
    d = log(); d[key] = rec; WORK.mkdir(parents=True, exist_ok=True); LOG.write_text(json.dumps(d, indent=1)); print(key, json.dumps(rec)[:500], flush=True)


def ff(*args):
    r = subprocess.run([FFMPEG, "-v", "error", "-y", *map(str, args)], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-800:])


def step_inputs():
    """The clean originals (97 frames, 960x544, lossless) and their damaged copies."""
    INP.mkdir(parents=True, exist_ok=True); x = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-an"]
    ff("-i", SHOW / SOURCES["gh"], "-frames:v", 97, "-c:v", "libx264", "-qp", 0, "-pix_fmt", "yuv420p", "-an", INP / "gh_clean.mp4")
    ff("-i", INP / "gh_clean.mp4", "-vf", "gblur=sigma=4", *x, "-crf", 6, INP / "gh_blur.mp4")
    ff("-i", INP / "gh_clean.mp4", *x, "-crf", 45, INP / "gh_crf45.mp4")
    ff("-i", INP / "gh_clean.mp4", "-vf", "gblur=sigma=2.5,noise=alls=14:allf=t", *x, "-crf", 40, INP / "gh_mixed.mp4")
    ff("-i", INP / "gh_clean.mp4", "-vf", "scale=480:272:flags=area", *x, "-crf", 6, INP / "gh_half.mp4")
    ff("-i", SHOW / SOURCES["tp"], "-frames:v", 97, "-vf", "scale=990:544:flags=lanczos,crop=960:544", "-c:v", "libx264", "-qp", 0, "-pix_fmt", "yuv420p", "-an", INP / "tp_clean.mp4")
    ff("-i", INP / "tp_clean.mp4", "-vf", "hue=s=0", *x, "-crf", 6, INP / "tp_grey.mp4")
    ff("-i", SHOW / SOURCES["fl"], "-frames:v", 97, "-c:v", "libx264", "-crf", 10, "-pix_fmt", "yuv420p", "-c:a", "copy", INP / "fl_sdr.mp4")
    put("inputs", {k: str(INP / k) for k in sorted(os.listdir(INP))})


def gpu_hold(key, declared, fn):
    """Run fn(watch) holding one gate reservation; the floor watch cancels this lane's job if the card stays under 4 GiB."""
    import gpu_gate as G
    peak = G.expected("finish:" + key, declared, True); rid = None
    while rid is None:
        rid, why = G.acquire("gap-p1", key, peak, True, port=PORT)
        if rid is None: print("gate:", why, flush=True); time.sleep(20)
    print("gate: acquired", rid, "declared", peak, flush=True)
    C.free(); time.sleep(3); top = [0.0]; stop = threading.Event(); watch = G.FloorWatch()

    def poll():
        while not stop.is_set():
            top[0] = max(top[0], G.PROBE.used_by_port(PORT))
            if watch.tripped(): print("floor: the card stayed under 4 GiB; cancelling this lane's job", flush=True); C.cancel()
            time.sleep(1)
    th = threading.Thread(target=poll, daemon=True); th.start()
    try: return fn(top)
    finally:
        stop.set(); th.join(5); G.release(rid); C.free(); G.record_peak("finish:" + key, top[0])


def render_one(key, top):
    p = PLAN[key]; effect = p.get("effect", key); safe = key.replace("@", "_"); src = INP / p["input"]; info = F.probe(src); name = C.upload(src); stem = f"proof_{safe}"
    vals = F.values(effect, info, seconds=info["seconds"], scene=p["scene"], colors=p.get("colors", ""), seed=42, video=name, stem=stem)
    top[0] = 0.0; t0 = time.time(); h = C.run(F.graph(effect, vals, prefix=f"finish/{stem}")); secs = round(time.time() - t0, 1)
    rec = {"model": "LTX-2.5 22B distilled int8 + " + F.EFFECTS[effect]["repo"].split("/")[1], "lora": F.EFFECTS[effect]["lora"], "strength": vals.get("strength", 1.0), "seed": 42, "frames": vals["frames"],
           "size": [vals["width"], vals["height"]], "guide_size": [vals.get("guide_width", vals["width"]), vals.get("guide_height", vals["height"])], "prompt": vals.get("prompt", "(scene embedding, no prompt)"),
           "input": p["input"], "damage": p["damage"], "seconds": secs, "peak_vram_gib": round(top[0], 1), "when": time.strftime("%Y-%m-%d %H:%M %Z")}
    OUT.mkdir(parents=True, exist_ok=True)
    if effect == "hdr":
        rec["hlg"] = str(C.fetch(F.outputs(h, "save")[0], OUT / "hdr_hlg.mp4")); rec["sdr_view"] = str(C.fetch(F.outputs(h, "saves")[0], OUT / "hdr_sdrview.mp4"))
        rec["exr_dir"] = str(LANE_OUT / vals["exr_dir"]); rec["png16_dir"] = str(LANE_OUT / Path(vals["hlg16_prefix"]).parent)
    else: rec["file"] = str(C.fetch(F.outputs(h, "save")[0], OUT / f"{safe}.mp4"))
    put("render:" + key, rec)


def step_render(effects):
    def go(top):
        for e in effects:
            try: render_one(e, top)
            except Exception as x: put("render:" + e, {"error": f"{type(x).__name__}: {x}"[:600], "when": time.strftime("%Y-%m-%d %H:%M %Z")})
    gpu_hold("ltx25_iclora_batch", 44, go)


def step_seedvr2():
    """The studio's own SeedVR2 3B int8 upscale (edits.py's template, used as is through the studio's API) on the same half-size clip, for the crop comparison."""
    import urllib.request
    studio = os.environ.get("FINISH_STUDIO_URL", "http://127.0.0.1:8763"); src = INP / "gh_half.mp4"; name = C.upload(src)

    def go(top):
        top[0] = 0.0; t0 = time.time()
        r = json.loads(urllib.request.urlopen(urllib.request.Request(studio + "/api/edits/seedvr2/run", json.dumps({"values": {"73|file": name}}).encode(), {"Content-Type": "application/json"}), timeout=60).read())
        pid = r["job"]
        while True:
            time.sleep(3); h = C.get(f"/history/{pid}").get(pid)
            if h and (h.get("status") or {}).get("completed"): break
            if h and (h.get("status") or {}).get("status_str") == "error": raise RuntimeError("SeedVR2 stopped")
        it = next(v for o in h["outputs"].values() for k in ("images", "videos") for v in o.get(k, []))
        out = C.fetch(it, OUT / "upscale_seedvr2.mp4")
        put("render:seedvr2", {"model": "SeedVR2 3B int8 (Comfy-Org/SeedVR2), the studio's edits.py template", "input": "gh_half.mp4", "seconds": round(time.time() - t0, 1), "peak_vram_gib": round(top[0], 1), "file": str(out), "when": time.strftime("%Y-%m-%d %H:%M %Z")})
    gpu_hold("seedvr2_video", 33, go)


def step_page(effect="hdr", clip="fl_sdr.mp4"):
    """One run through the page's own route (POST /api/finish/run on a studio pointed at this lane), to prove the button works end to end, the HDR masters included."""
    import urllib.request
    studio = os.environ.get("FINISH_STUDIO_URL", "http://127.0.0.1:8763"); name = C.upload(INP / clip)

    def go(top):
        top[0] = 0.0; body = {"effect": effect, "clip": {"type": "input", "subfolder": "", "filename": name}, "seconds": 4}
        rec = json.loads(urllib.request.urlopen(urllib.request.Request(studio + "/api/finish/run", json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=60).read())
        while rec.get("status") == "running":
            time.sleep(3); rec = json.loads(urllib.request.urlopen(f"{studio}/api/finish/jobs/{rec['job']}", timeout=30).read())
        put("page:" + effect, {k: rec.get(k) for k in ("status", "error", "files", "seconds", "size", "frames", "ai_generated")} | {"peak_vram_gib": round(top[0], 1), "when": time.strftime("%Y-%m-%d %H:%M %Z")})
    gpu_hold("ltx25_iclora_batch", 44, go)


def scratch(src, dest, crf, seed=7):
    """Old-film scratches: two thin vertical lines per frame that wander, one light and one dark, plus a few dust specks. Drawn here with numpy, so the damage is ours and known."""
    import numpy as np
    from studio import finish_measure as Mm
    rng = np.random.default_rng(seed); s = Mm.size(src); w, h = s["width"], s["height"]; frames = Mm.frames_rgb(src, 1)
    p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", "24", "-i", "-", "-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p", str(dest)], stdin=subprocess.PIPE)
    x1, x2 = w * 0.3, w * 0.7
    for fr in frames:
        a = fr.astype(np.int16); x1 = (x1 + rng.normal(0, 6)) % w; x2 = (x2 + rng.normal(0, 9)) % w
        a[:, int(x1):int(x1) + 2] += 90; a[:, int(x2)] -= 80
        for _ in range(rng.integers(3, 9)):
            y, x = rng.integers(0, h - 3), rng.integers(0, w - 3); a[y:y + rng.integers(1, 4), x:x + rng.integers(1, 4)] = rng.choice([20, 235])
        p.stdin.write(np.clip(a, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError("ffmpeg could not write the scratched clip")
    return dest


def step_fresh(keys):
    """For each effect: a fresh clean clip from LTX-2.5 text to video, damaged here with ffmpeg, then repaired. All in one gate reservation, so the models stay loaded."""
    import json as _j
    t2v = _j.loads((REPO / "workflows" / "ltx25_core_t2v_api.json").read_text())
    from studio.graph_template import fill

    def go(top):
        for k in keys:
            f = FRESH[k]; key = f"{k}@fresh"
            try:
                top[0] = 0.0; t0 = time.time()
                g = fill(t2v, {"prompt": f["t2v"], "negative": NEG_T2V, "fps": 24, "width": 960, "height": 544, "frames": 97, "seed": f["seed"]})
                g["21"]["inputs"]["filename_prefix"] = f"finish/fresh_src_{k}"
                h = C.run(g); clean = C.fetch(F.outputs(h, "21")[0], INP / f"fresh_{k}_clean.mp4")
                put("source:" + k, {"model": "LTX-2.5 22B distilled int8, text to video", "prompt": f["t2v"], "seed": f["seed"], "seconds": round(time.time() - t0, 1), "peak_vram_gib": round(top[0], 1), "file": str(clean)})
                dmg = INP / f"fresh_{k}_damaged.mp4"
                if f.get("scratches"):
                    tmp = INP / f"fresh_{k}_look.mp4"; ff("-i", clean, "-vf", f["vf"], "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", 4, "-an", tmp); scratch(tmp, dmg, f["crf"])
                else: ff("-i", clean, "-vf", f["vf"], "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", f["crf"], *(["-c:a", "copy"] if k == "hdr" else ["-an"]), dmg)
                PLAN[key] = {"effect": k, "input": dmg.name, "clean": None if k == "hdr" else clean.name, "scene": f["scene"], "colors": f.get("colors", ""), "damage": f["damage"]}
                render_one(key, top)
            except Exception as x: put("render:" + key, {"error": f"{type(x).__name__}: {x}"[:600], "when": time.strftime("%Y-%m-%d %H:%M %Z")})
    gpu_hold("ltx25_iclora_batch", 44, go)


def _fresh_plan():
    """The fresh entries the log knows about, so measure, sheets and pack see them in a later run."""
    for k, f in FRESH.items():
        PLAN.setdefault(f"{k}@fresh", {"effect": k, "input": f"fresh_{k}_damaged.mp4", "clean": None if k == "hdr" else f"fresh_{k}_clean.mp4", "scene": f["scene"], "colors": f.get("colors", ""), "damage": f["damage"]})


def step_measure():
    lg = log(); res = {}
    for e, p in PLAN.items():
        r = lg.get("render:" + e) or {}; kind = p.get("effect", e)
        if not r or r.get("error"): continue
        if kind == "hdr":
            master = WORK / "masters" / "hdr_prores4444.mov"; M.prores_from_png16(r["png16_dir"], master, fps=24)
            res[e] = M.hdr_report(r["hlg"], r["exr_dir"], master)
        elif kind == "colorize": res[e] = M.colour_report(INP / p["input"], r["file"], INP / p["clean"])
        elif kind == "upscale": sv = (lg.get("render:seedvr2") or {}).get("file"); sv = sv if sv and M.size(sv)["width"] == 2 * M.size(INP / p["input"])["width"] else None; res[e] = M.upscale_report(INP / p["input"], r["file"], INP / p["clean"], WORK / f"{e.replace('@', '_')}_lanczos.mp4", sv)
        else: res[e] = M.fidelity_report(INP / p["input"], r["file"], INP / p["clean"])
        put("measure:" + e, res[e])


def step_sheets():
    """Side-by-side frames and clips to look at: damaged | LTX Finish | clean original."""
    lg = log(); d = WORK / "sheets"; d.mkdir(parents=True, exist_ok=True)
    for e, p in PLAN.items():
        r = lg.get("render:" + e) or {}
        if not r or r.get("error"): continue
        e = e.replace("@", "_")
        if p.get("effect", e) == "hdr":
            hm = M.headroom_clip(r["exr_dir"], d / f"{e}_headroom.mp4")
            M.side_by_side([INP / p["input"], r["sdr_view"], hm], d / f"{e}.mp4", d / f"{e}.jpg", ["SDR source", "HDR result, tone-mapped back to SDR", "Brighter than SDR white: yellow 1x to red 8x"])
        else:
            files = [INP / p["input"], r["file"]] + ([INP / p["clean"]] if p["clean"] else [])
            M.side_by_side(files, d / f"{e}.mp4", d / f"{e}.jpg", ["Damaged input", "LTX Finish", "Clean original"])
        if p.get("effect", e) == "upscale":
            lz = WORK / f"{e}_lanczos.mp4"; rs = M.size(r["file"])
            if lz.exists(): M.crop_sheet([lz, r["file"], INP / p["clean"]], d / f"{e}_crops.jpg", (380, 140, 240, 180), size_to=(rs["width"], rs["height"]))
        print("sheet", d / f"{e}.jpg", flush=True)


def _entry(key, p, r, m, lk):
    safe = key.replace("@", "_"); sheet, poster = WORK / "sheets" / f"{safe}.mp4", WORK / "sheets" / f"{safe}.jpg"
    shutil.copy(sheet, WEB / f"{safe}.mp4"); shutil.copy(poster, WEB / f"{safe}.jpg")
    crops = WORK / "sheets" / f"{safe}_crops.jpg"; extra = {}
    if crops.exists(): shutil.copy(crops, WEB / crops.name); extra["crops"] = {"src": f"finish/{crops.name}", "panes": ["Lanczos x2", "LTX x2", "Original"], "alt": lk.get("crops_alt", "The same crop from a plain Lanczos x2, the LTX x2 and the original, enlarged pixel for pixel.")}
    return extra | {"src": f"finish/{safe}.mp4", "poster": f"finish/{safe}.jpg", "alt": lk["alt"], "looked": lk["note"], "fault": lk.get("fault", ""), "damage": p["damage"], "clip": SOURCES.get(p["input"][:2]) or "a fresh LTX-2.5 text-to-video render made for this proof", "fresh": p["input"].startswith("fresh_"),
            "model": r["model"], "seed": r["seed"], "frames": r["frames"], "size": r["size"], "seconds": r["seconds"], "peak_vram_gib": r["peak_vram_gib"], "when": r["when"], "prompt": r["prompt"], "measured": m, "ai_generated": True}


def step_pack():
    """finish_proof.json and the shown media. Only renders with a measurement and a look note (looked.json, written after looking at the sheets) go on the page.
    A key like restore@temple is a second clip for the same effect and goes under that effect's "more"."""
    lg = log(); looked = json.loads((WORK / "looked.json").read_text()) if (WORK / "looked.json").exists() else {}
    WEB.mkdir(parents=True, exist_ok=True)
    out = {"note": "Every number was measured by scripts/prove_finish.py on this machine, on AI-generated showcase clips damaged on purpose with ffmpeg. PSNR, SSIM and VMAF compare each frame with the clean original: PSNR punishes any re-drawn detail, VMAF is Netflix's perceptual score. The look notes are ours, from watching every result.", "licence": F.LICENCE, "effects": {}}
    order = lambda k: (0 if k.endswith("@fresh") else 1 if "@" not in k else 2)      # the fresh, varied clip leads; the showcase-clip runs stay as technical evidence
    for key in sorted(PLAN, key=order):
        p = PLAN[key]; effect = p.get("effect", key); r, m, lk = lg.get("render:" + key), lg.get("measure:" + key), looked.get(key)
        if not r or r.get("error") or not m or not lk: continue
        e = _entry(key, p, r, m, lk)
        if effect in out["effects"]: out["effects"][effect].setdefault("more", []).append(e); continue
        out["effects"][effect] = {"label": F.EFFECTS[effect]["label"], **e}
        still = r.get("sdr_view") or r.get("file"); thumb = WEB / f"{effect}_thumb.jpg"      # the result alone, for the hero grid
        ff("-ss", "2", "-i", still, "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", thumb); out["effects"][effect]["thumb"] = f"finish/{thumb.name}"
        src = lg.get("source:" + effect) if key.endswith("@fresh") else None
        if src: out["effects"][effect]["source"] = {k: src.get(k) for k in ("model", "prompt", "seed", "seconds", "peak_vram_gib")}
    up = out["effects"].get("upscale"); sv = lg.get("render:seedvr2") or {}
    if up and sv.get("file"):
        up["seedvr2_note"] = "We also ran the studio's own SeedVR2 tool (edits.py) on the same half-size clip: it handed back the input unchanged (identical frames, 480x272), so there is no SeedVR2 comparison here. That tool needs fixing; it is not part of LTX Finish."
    (REPO / "studio" / "finish_proof.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"); print("packed", {k: len(v.get("more", [])) for k, v in out["effects"].items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("step"); ap.add_argument("effects", nargs="*"); a = ap.parse_args(); _fresh_plan()
    if a.step == "inputs": step_inputs()
    elif a.step == "render": step_render(a.effects or list(PLAN))
    elif a.step == "seedvr2": step_seedvr2()
    elif a.step == "page": step_page(*(a.effects or []))
    elif a.step == "fresh": step_fresh(a.effects or list(FRESH))
    elif a.step == "measure": step_measure()
    elif a.step == "sheets": step_sheets()
    elif a.step == "pack": step_pack()
    else: ap.error("unknown step")
