#!/usr/bin/env python3
"""Builds the "how big is it" demo videos from media already in this repo: no GPU, only ffmpeg and a headless Chromium for the type.
  reel   a 70 s highlight reel, cut on the beats of the studio's own Music 3 song, a lower third on every clip naming the model or graph from that clip's own record
  wall   a 10x10 wall of different renders filling in while a counter runs up to the real number of rendered files
  tour   the studio tour (and --phone pass) from scripts/record_studio_tour.py frames, with a caption naming each tab
Every figure comes from docs/demos/numbers.json (scripts/build_demo_numbers.py). Every label comes from a record in the repo, and the edit list with each label's source
is written next to the video (docs/demos/*_edl.json), so each one can be checked. Masters are 1080p H.264; --web writes the small copies for docs/media.
Usage: python scripts/build_demo_videos.py reel|wall|tour --work DIR [--studio URL] [--films DIR] [--tour DIR] [--chrome PATH]     (Playwright for the type; ffmpeg on PATH)"""
import argparse, asyncio, json, os, random, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; WEB = ROOT / "studio" / "web"; STUDIO = ROOT / "studio"; DEMOS = ROOT / "docs" / "demos"
FPS = 30; W, H = 1920, 1080
def _font(name):      # inlined: a page loaded with set_content has no origin that may read file:// fonts
    import base64; return "data:font/woff2;base64," + base64.b64encode((WEB / "vendor" / "fonts" / name).read_bytes()).decode()
MUSIC = {"reel": ("music/music3.m4a", 0.0, 70.0), "wall": ("music/ace15_xl_base.m4a", 20.0, 25.0), "phone": ("music/ace15_turbo.m4a", 30.0, 20.0)}
CREDIT = {"music/music3.m4a": "“Paper Boats”, made in the studio with MiniMax-Music3 (seed 7701, MiniMax-Music3 Community License)",
          "music/ace15_xl_base.m4a": "“Paper Boats”, made in the studio with ACE-Step 1.5 XL Base (seed 7701, MIT)",
          "music/ace15_turbo.m4a": "“Paper Boats”, made in the studio with ACE-Step 1.5 Turbo (seed 7701, MIT)",
          "music/ace15_xl_turbo.m4a": "“Paper Boats”, made in the studio with ACE-Step 1.5 XL Turbo (seed 7701, MIT)",
          "music/diffsynth_music.m4a": "“Paper Boats” again, made in the studio with DiffSynth-Music (seed 7701, Apache-2.0)"}


def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode: raise SystemExit(f"failed: {' '.join(map(str, cmd))[:400]}\n{r.stderr[-1500:]}")
    return r


def probe(p):
    j = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", p]).stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), {}); return {"w": v.get("width"), "h": v.get("height"), "dur": float(j["format"].get("duration") or 0)}


def jl(p): return json.loads((STUDIO / p).read_text(encoding="utf-8"))


def fmt(n): return f"{n:,}"


# ---------- labels, each from the clip's own record ----------
FRIENDLY = [(r"flux-2-klein-base-4b|flux-2-klein-4b", "FLUX.2 Klein 4B"), (r"(?i)minimax_h3_ref2va", "MiniMax H3 Ref2VA"), (r"(?i)minimax_h3", "MiniMax H3"), (r"krea2", "Krea 2"),
            (r"qwen_image_edit", "Qwen-Image-Edit"), (r"qwen_image", "Qwen-Image"), (r"wan2\.1_t2v_14B", "Wan 2.1 T2V 14B"), (r"wan2\.1_t2v_1\.3B", "Wan 2.1 T2V 1.3B"), (r"wan2\.1_i2v", "Wan 2.1 I2V"),
            (r"z_image_turbo", "Z-Image Turbo"), (r"anima-base", "Anima"), (r"SCAIL_2", "Wan SCAIL 2"), (r"ltx-2\.5", "LTX-2.5"), (r"ltxv-13b", "LTXV 13B 0.9.8"), (r"wan2\.2_ti2v_5B", "Wan 2.2 TI2V 5B"),
            (r"wan2\.2_fun_camera", "Wan 2.2 Fun Camera 14B"), (r"wan2\.2_fun_control_high", "Wan 2.2 Fun Control 14B"), (r"wan2\.2_fun_control_5B", "Wan 2.2 Fun Control 5B"), (r"wan2\.2_fun_inpaint", "Wan 2.2 Fun Inpaint 5B"),
            (r"Wan2_2-T2V-A14B", "Wan 2.2 T2V A14B"), (r"kandinsky5lite", "Kandinsky 5 Lite"), (r"svd_xt", "SVD XT 1.1"), (r"DreamShaper_8", "DreamShaper 8 (SD 1.5)"), (r"sd_xl_base", "SDXL base"), (r"causal_forcing", "Causal Forcing"), (r"^anigen$", "AniGen"), (r"^triposplat$", "TripoSplat"), (r"^triposr$", "TripoSR"), (r"^skintokens$", "SkinTokens"), (r"^moge$", "MoGe"), (r"^kimodo$", "Kimodo")]


def friendly(m):
    m = str(m).strip()
    for rx, name in FRIENDLY:
        if re.search(rx, m): return name
    return re.sub(r"\.(safetensors|ckpt|gguf)$", "", m)


def lora_name(f):
    s = re.sub(r"\.(safetensors|ckpt)$", "", f).replace("_", " ").strip(); return s if len(s) <= 44 else s[:42].rstrip() + "…"


def chain(names):
    out = []
    for n in names:
        if n and n not in out and n.lower() not in ("ffmpeg", "none", "made on the cpu"): out.append(n)
    return " → ".join(out)


class Labels:
    """label(src) -> {main, sub, record}: the model or graph that made the clip, and where in the repo that is written down."""
    def __init__(self, studio):
        self.rr = jl("recipe_renders.json")["renders"]; self.fam = jl("family_status.json")["families"]; self.cam = jl("camera_proof.json"); self.dub = jl("dub_proof.json")
        self.com = {s["id"]: s for s in jl("commercial_proof.json")["spots"]}; self.fin = jl("finish_proof.json"); self.cs = jl("clipsound_proof.json"); self.rec = {r["id"]: r for r in jl("recipes.json")["recipes"]}
        self.show = {x["id"]: x for x in json.loads((WEB / "showcase" / "showcase.json").read_text())}; self.music = jl("music_models.json")
        get = lambda p: json.load(__import__("urllib.request").request.urlopen(studio.rstrip("/") + p, timeout=60))
        self.goals = get("/api/goals"); self.measured = get("/api/recipes")["measured"]; self.motion = {r["id"]: r for r in get("/api/motion")["routes"]}
        self.com_models = [m["name"] for m in get("/api/commercials/genres")["models"] if m["name"] in ("FLUX.2 Klein 4B", "MiniMax H3", "MiniMax Music 3")]

    def __call__(self, src):
        if src.startswith("recipe_renders/"):
            rid = Path(src).stem.replace(".poster", ""); r = self.rr[rid]; models = [friendly(x) for x in str(r.get("model", "")).split(",")]
            loras = [x.strip() for x in str(r.get("lora") or "").split(",") if x.strip()]; turbo = [x for x in loras if "turbo_8step" in x]; own = [x for x in loras if x not in turbo]
            main = chain(models) + "".join(f" + LoRA “{lora_name(x)}”" for x in own)
            sub = f"{'LoRA recipe' if r.get('family') == 'lora' else 'Recipe'} “{rid}”" + (" with H3's 8-step turbo LoRA" if turbo else "") + (f", seed {r['seed']}" if r.get("seed") is not None else "")
            return {"main": main, "sub": sub, "record": f"studio/recipe_renders.json renders.{rid}"}
        if src.startswith(("families/", "motion/")) and any(m["src"] == src for f in self.fam.values() for m in f.get("media") or []):
            name, m = next((n, m) for n, f in self.fam.items() for m in f.get("media") or [] if m["src"] == src)
            norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower()); fm = friendly(m["model"]) if m.get("model") else ""
            main = name if not fm or len(fm) > 40 else fm if norm(name)[:5] in norm(fm) else f"{name} on {fm}"
            return {"main": main, "sub": f"{name} family test, template {m.get('tpl')}", "record": f"studio/family_status.json families.{name}.media[{m['id']}]"}
        if src.startswith("motion/"):
            r = self.motion[re.sub(r"_\d+$", "", Path(src).stem)]
            return {"main": r["label"], "sub": f"Motion page · {r['model']}", "record": f"/api/motion routes.{r['id']} (studio/feature_motion.py)"}
        if src.startswith("pipelines/"):
            pid = src.split("/")[1]; p = json.loads((WEB / "pipelines" / pid / "proof.json").read_text()); assert (p.get("final") or {}).get("src") == src.split("/")[-1], src
            return {"main": chain(s["model"] for s in p["stages"]), "sub": f"Pipeline “{pid.replace('_', ' ')}”, run {p['run']} ({p['status']})", "record": f"studio/web/pipelines/{pid}/proof.json"}
        if src.startswith("showcase/recipes/"):
            rid = Path(src).stem; r = self.rec[rid]
            return {"main": chain(m["name"].split(" (")[0] for m in r["models"] if "language model" not in m["name"]), "sub": f"Recipe “{r['title']}”", "record": f"studio/recipes.json recipes.{rid}"}
        if src.startswith("showcase/"):
            x = self.show[Path(src).stem]; g = self.goals[x["goal"]]; model = (self.measured.get(x["goal"]) or {}).get("model") or g["family"]
            return {"main": model, "sub": f"Showcase render, {g['label']} goal", "record": f"studio/web/showcase/showcase.json {x['id']} (goal {x['goal']})"}
        if src.startswith("commercials/"):
            s = self.com[src.split("/")[1]]
            return {"main": chain(self.com_models), "sub": f"“{s['title']}”, an invented brand · {s['genre_title']}", "record": f"studio/commercial_proof.json spots.{s['id']} and /api/commercials/genres models"}
        if src.startswith("campath/"):
            hit = None
            def walk(o):
                nonlocal hit
                if isinstance(o, dict):
                    if o.get("src") == src: hit = o
                    for v in o.values(): walk(v)
                elif isinstance(o, list):
                    for v in o: walk(v)
            walk(self.cam); model = (hit or {}).get("model") or (self.cam["pick"]["model"] if src in [t["src"] for t in self.cam["pick"]["takes"]] else None)
            take = next((t["take"] for t in self.cam["pick"]["takes"] if t["src"] == src), None)
            return {"main": model, "sub": f"Camera Paths, {take} of three, picked by the move" if take else "Camera Paths, the drawn move", "record": "studio/camera_proof.json"}
        if src.startswith("dub/"):
            key = {"dub_es_relip": "relip", "dub_es_dubit": "dubit", "dub_es_voice": "voice_dub"}[Path(src).stem]
            return {"main": self.dub[key]["model"], "sub": "Dub & Voice: the same clip, now in Spanish", "record": f"studio/dub_proof.json {key}"}
        if src.startswith("finish/"):
            e = next(e for e in self.fin["effects"] if src in json.dumps(e))
            return {"main": e["model"].replace("LTX-2.5-22b-IC-LoRA-", "IC-LoRA "), "sub": f"LTX Finish: {e.get('label', '')}", "record": f"studio/finish_proof.json effects.{e.get('id', '')}"}
        if src == "music/reactive.mp4":
            return {"main": "MiniMax Music 3 → FlexAudioVisualizerCircular", "sub": "Music page: the song drives the picture", "record": "studio/music_proof.json extras.visual"}
        if src == "music/wren_light_the_wreckage.mp4":
            f = self.music["film"]; return {"main": "MiniMax Music 3 → LTX-2.5 (song locked into the video)", "sub": f"{f['title']} · made before this studio", "record": "studio/music_models.json film"}
        if src == "film:A": return {"main": "MiniMax H3 · keyframes FLUX.2 Klein 9B · score MiniMax Music 3", "sub": "Film A “RUN”, released with the demo", "record": "README.md Made in Parametric Studio"}
        if src == "film:B": return {"main": "LTX-2.5 + four Lightricks IC-LoRAs · keyframes FLUX.2 Klein 9B", "sub": "Film B “ONE CLIP”, released with the demo", "record": "README.md Made in Parametric Studio"}
        if src == "docs/media/shotboard_demo.mp4": return {"main": "Screen recording of one real Shot Board run", "sub": "Its exported contact video: the source clip and seven results", "record": "README.md Demo"}
        if src.startswith("ui:"): return {"main": "Screen capture of the studio", "sub": src[3:], "record": "the studio tour recording (scripts/record_studio_tour.py)"}
        raise KeyError(src)


# ---------- type, drawn by Chromium in the studio's own fonts ----------
BASE_CSS = f"""@font-face{{font-family:Archivo;src:url({_font("archivo-latin-wdth-normal.woff2")}) format("woff2");font-weight:100 900;font-stretch:62% 125%}}
@font-face{{font-family:Inter;src:url({_font("inter-latin-wght-normal.woff2")}) format("woff2");font-weight:100 900}}
*{{box-sizing:border-box;margin:0}} html,body{{background:transparent;color:#f6f6f1;font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased}}
.disp{{font-family:Archivo,Inter,sans-serif;font-stretch:125%;font-weight:900;text-transform:uppercase;letter-spacing:-.01em}} .y{{color:#f5c518}} .g{{color:#27e07f}} .m{{color:#9aa39a}}"""


async def _shots(jobs, w, h, chrome=None, opaque=False):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=chrome) if chrome else await p.chromium.launch()
        async def page():
            pg = await b.new_page(viewport={"width": w, "height": h}); await pg.set_content(f"<!doctype html><meta charset=utf-8><style>{BASE_CSS}</style><body></body>"); return pg
        pg, last = await page(), None
        for body, out in jobs:
            for attempt in range(3):
                try:
                    if body != last: await pg.evaluate("(h) => { document.body.innerHTML = h; return document.fonts.ready.then(() => 1); }", body); last = body
                    await pg.screenshot(path=str(out), omit_background=not opaque); break
                except Exception:
                    if attempt == 2: raise
                    await pg.close(); pg, last = await page(), None
        await b.close()


def shots(jobs, w=W, h=H, chrome=None, opaque=False): asyncio.run(_shots(jobs, w, h, chrome, opaque))


def lower_third(kicker, main, sub, scale=1.0, left=64, bottom=60, top=None):
    s = scale; where = f"top:{top*s}px" if top is not None else f"bottom:{bottom*s}px"
    return f"""<div style="position:absolute;left:{left*s}px;{where};max-width:{1300*s}px;padding:{16*s}px {24*s}px {17*s}px;border-radius:{14*s}px;background:rgba(7,9,8,.78);border:1px solid rgba(255,255,255,.12);box-shadow:0 10px 30px rgba(0,0,0,.45)">
<div class="disp y" style="font-size:{18*s}px;letter-spacing:.06em">{kicker}</div><div style="font-weight:700;font-size:{36*s}px;line-height:1.16;margin-top:{5*s}px">{main}</div><div style="color:#c9cec6;font-size:{21*s}px;margin-top:{5*s}px">{sub}</div></div>"""


def ai_tag(s=1.0): return f"""<div style="position:absolute;right:{40*s}px;top:{34*s}px;font:600 {15*s}px Inter;letter-spacing:.08em;color:rgba(246,246,241,.75);background:rgba(7,9,8,.55);padding:{6*s}px {11*s}px;border-radius:{8*s}px">AI-GENERATED</div>"""


STATS = [("node_classes", "ComfyUI node classes loaded"), ("graphs", "ComfyUI graphs that open in the studio"), ("recipes", "recipes in the library"), ("families_with_render", "model families rendered here"),
         ("pipelines", "multi-model pipelines"), ("lessons", "ComfyUniversity lessons"), ("tabs", "studio tabs and pages"), ("rendered_media", "rendered files shipped in the repo"), ("crew_notes", "crew notes with sources"), ("tests", "tests in the suite")]


def counts_card(nums, k=1.0, foot="", title="See how big it is", top="PARAMETRIC STUDIO", tsize=110):
    """k in 0..1 runs the numbers up (eased); each figure starts a little after the one before."""
    cells = []
    for i, (key, label) in enumerate(STATS):
        kk = min(1, max(0, (k - i * 0.04) / 0.6)); kk = 1 - (1 - kk) ** 3; v = round(nums[key]["value"] * kk)
        cells.append(f"""<div style="padding:22px 0 0;border-top:1px solid rgba(255,255,255,.14)"><div class="disp y" style="font-size:104px;line-height:1;font-stretch:88%;font-variant-numeric:tabular-nums">{fmt(v)}</div><div style="font-size:25px;color:#c9cec6;margin-top:12px;line-height:1.25">{label}</div></div>""")
    return f"""<div style="position:absolute;inset:0;background:radial-gradient(1200px 700px at 15% 0%,rgba(245,197,24,.10),transparent 60%),radial-gradient(900px 600px at 100% 100%,rgba(39,224,127,.08),transparent 60%),#070908;padding:0 110px 120px;display:flex;flex-direction:column;justify-content:center">
<div class="disp" style="font-size:22px;letter-spacing:.18em;color:#9aa39a">{top}</div><div class="disp" style="font-size:{tsize}px;line-height:1;margin:16px 0 64px;white-space:nowrap">{title}</div>
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:56px 48px">{''.join(cells)}</div>
<div style="position:absolute;left:110px;right:110px;bottom:52px;font-size:21px;line-height:1.45;color:#aeb5ac">{foot}</div></div>"""


# ---------- audio ----------
def level(src_wav, out, start, dur, fade_in=0.0, fade_out=1.5, extra=None):
    """Trim, fade, then two-pass loudnorm to -16 LUFS integrated, -1.5 dBTP. extra: a ready filter chain instead of trim, for joined tracks."""
    pre = extra or f"atrim={start}:{start + dur},asetpts=PTS-STARTPTS"
    pre += (f",afade=t=in:d={fade_in}" if fade_in else "") + f",afade=t=out:st={dur - fade_out}:d={fade_out}"
    r = run(["ffmpeg", "-hide_banner", "-i", src_wav, "-af", pre + ",loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    ln = f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
    run(["ffmpeg", "-y", "-hide_banner", "-i", src_wav, "-af", pre + "," + ln + ",aresample=48000,alimiter=limit=0.6:level=false:attack=1:release=50", "-ar", "48000", "-c:a", "pcm_s16le", out])      # the limiter leaves headroom: AAC overshoots the peaks a little
    return measure(out)


def measure(p):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"]); t = r.stderr[r.stderr.rindex("Summary:"):]
    return {"lufs": float(re.search(r"I:\s+(-?[\d.]+) LUFS", t).group(1)), "true_peak_db": float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", t).group(1)), "lra": float(re.search(r"LRA:\s+(-?[\d.]+) LU", t).group(1))}


def mux(video, audio, master, web=None, web_w=1280, web_crf=28, web_abr="128k", web_kbps=None):
    run(["ffmpeg", "-y", "-hide_banner", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "256k",
         "-shortest", "-map_metadata", "-1", "-metadata", "title=Parametric Studio demo", "-movflags", "+faststart", master])
    if web and web_kbps:      # two passes at a fixed rate, 24 fps: a screen recording is mostly still, so the budget goes to the scrolls
        log = str(Path(web).with_suffix("")) + "_2pass"; vf = ["-vf", f"scale={web_w}:-2:flags=lanczos,fps=24", "-c:v", "libx264", "-preset", "slower", "-b:v", f"{web_kbps}k"]
        run(["ffmpeg", "-y", "-hide_banner", "-i", master, *vf, "-pass", "1", "-passlogfile", log, "-an", "-f", "mp4", os.devnull])
        run(["ffmpeg", "-y", "-hide_banner", "-i", master, *vf, "-pass", "2", "-passlogfile", log, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", web_abr, "-ac", "2", "-map_metadata", "-1", "-movflags", "+faststart", web])
        for f in Path(web).parent.glob(Path(log).name + "*"): f.unlink()
    elif web:
        run(["ffmpeg", "-y", "-hide_banner", "-i", master, "-vf", f"scale={web_w}:-2:flags=lanczos", "-c:v", "libx264", "-preset", "slower", "-crf", str(web_crf), "-pix_fmt", "yuv420p", "-profile:v", "high",
             "-c:a", "aac", "-b:a", web_abr, "-ac", "2", "-map_metadata", "-1", "-movflags", "+faststart", web])


def wav(src, work):
    out = work / (Path(src).stem + ".wav")
    if not out.exists(): run(["ffmpeg", "-y", "-hide_banner", "-i", WEB / src, "-ar", "48000", "-ac", "2", out])
    return out


def beats(wav_path):
    import librosa
    y, sr = librosa.load(str(wav_path), sr=22050); _, b = librosa.beat.beat_track(y=y, sr=sr); return [round(float(t), 3) for t in librosa.frames_to_time(b, sr=sr)]


# ---------- one clip, normalised to 1920x1080 at 30 fps ----------
def segment(src_path, out, frames, t_in, overlay_png, still=False, w=W, h=H):
    dur = frames / FPS; info = probe(src_path); wide = info["w"] and abs(info["w"] / info["h"] - w / h) < 0.04
    if still:
        inp = ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur + 0.1}", "-i", src_path]
        fg = f"scale={int(w*1.06)}:-2:force_original_aspect_ratio=increase,crop={w}:{h}:x='(iw-{w})*t/{dur}':y='(ih-{h})/2'" if wide else None
    else:
        loop = ["-stream_loop", "-1"] if info["dur"] < t_in + dur + 0.05 else []
        inp = loop + ["-ss", f"{t_in:.3f}", "-i", src_path]; fg = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}" if wide else None
    if fg: graph = f"[0:v]fps={FPS},{fg},setsar=1[v]"
    else: graph = (f"[0:v]fps={FPS},split[a][b];[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=40:3,eq=brightness=-0.18:saturation=0.8[bg];"
                   f"[b]scale={w}:{h}:force_original_aspect_ratio=decrease,setsar=1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v]")
    run(["ffmpeg", "-y", "-hide_banner", *inp, "-i", overlay_png, "-filter_complex", graph + ";[v][1:v]overlay=0:0,format=yuv420p[o]", "-map", "[o]", "-frames:v", str(frames), "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-r", str(FPS), out])


def frames_to_video(pattern_or_list, out, frames=None, still=False):
    if still: run(["ffmpeg", "-y", "-hide_banner", "-loop", "1", "-framerate", str(FPS), "-i", pattern_or_list, "-frames:v", str(frames), "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", out])
    else: run(["ffmpeg", "-y", "-hide_banner", "-framerate", str(FPS), "-i", pattern_or_list, "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", out])


def concat(parts, out):
    lst = out.with_suffix(".txt"); lst.write_text("".join(f"file '{p}'\n" for p in parts)); run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])


def contact_sheets(video, outdir, name, every=1.0, per=10):
    """One sheet per 10 s: a frame each second with its time, for looking at every label."""
    outdir.mkdir(parents=True, exist_ok=True); d = probe(video)["dur"]; sheets = []
    for i in range(int((d + per - 0.01) // per)):
        o = outdir / f"{name}_{i * per:03d}s.jpg"
        run(["ffmpeg", "-y", "-hide_banner", "-ss", str(i * per + 0.5), "-t", str(per), "-i", video, "-vf", f"fps=1/{every},scale=640:-2,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='%{{pts\\:hms\\:{i * per + 0.5}}}':x=6:y=6:fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=2x5", "-frames:v", "1", o])
        sheets.append(o)
    return sheets


# ---------- the reel ----------
TOP, TOP_OWN_TAG = {"top": True}, {"top": True, "own_tag": True}      # the clip has its own words at the bottom; and its own AI-generated mark
# (chapter, source, in-point in s or None for 30% in, beats on screen[, options]). Picked by eye from every clip's middle frame: no real people, nothing unreleased, invented brands only.
REEL = [
    ("Model families", "families/ltx-2-5_4.mp4", 0.5, 4), ("Model families", "families/minimax-h3_6.mp4", None, 4), ("Model families", "families/wan2-2_8.mp4", None, 3),
    ("Model families", "families/mochi_1.mp4", None, 3), ("Model families", "families/allegro_0.mp4", None, 3), ("Model families", "families/animatediff_3.mp4", None, 3),
    ("Model families", "families/kandinsky-5-0-t2i-lite_2.mp4", None, 3), ("Model families", "families/wan2-2_3.mp4", None, 3), ("Model families", "families/wan2-1_1.mp4", None, 3),
    ("Recipes", "recipe_renders/tl_scene_building_goes_up.mp4", 0.5, 4), ("Recipes", "recipe_renders/lora_34bc6691f9.mp4", None, 3), ("Recipes", "recipe_renders/lora_097db59dc3.mp4", None, 3),
    ("Recipes", "recipe_renders/vid_short_comedy_mime.mp4", None, 3), ("Recipes", "recipe_renders/tl_scene_storm_rolls_in.mp4", None, 3), ("Recipes", "recipe_renders/lora_ec7c9295a9.mp4", None, 3),
    ("Recipes", "showcase/recipes/anime_opening.mp4", None, 4),
    ("Pipelines", "pipelines/room_century/final.mp4", 3.0, 4), ("Pipelines", "pipelines/anime_short/final.mp4", 2.0, 4), ("Pipelines", "pipelines/song_to_video/cut.mp4", 4.0, 4), ("Pipelines", "pipelines/world_flood/final.mp4", 6.0, 3),
    ("Showcase", "showcase/v_h3_dragon.mp4", None, 4), ("Showcase", "showcase/v_ltx_ink.mp4", None, 3), ("Showcase", "showcase/v_ltx_shatter.mp4", None, 3), ("Showcase", "showcase/director_wide.mp4", None, 3),
    ("3D", "recipe_renders/r3d_pic_trellis2.mp4", None, 3), ("3D", "recipe_renders/r3d_rig_anigen.mp4", None, 3), ("3D", "recipe_renders/r3d_place_sunny_street.mp4", None, 3), ("3D", "recipe_renders/r3d_splat_triposplat.mp4", None, 3),
    ("Commercials", "commercials/airline_moonferry/commercial.mp4", 2.0, 4, TOP_OWN_TAG), ("Commercials", "commercials/big_game_thunder/commercial.mp4", 9.0, 4, TOP_OWN_TAG), ("Commercials", "commercials/perfume_nocturne/commercial.mp4", 12.0, 4, TOP_OWN_TAG),
    ("Shot Board", "docs/media/shotboard_demo.mp4", 90.5, 5, TOP), ("Shot Board", "showcase/vfx_same_water.mp4", None, 3), ("Shot Board", "showcase/vfx_same_night.mp4", None, 3), ("Shot Board", "showcase/vfx_same_cutout.mp4", None, 3),
    ("Story & Takes", "campath/lighthouse_take1.mp4", None, 2), ("Story & Takes", "campath/lighthouse_take2.mp4", None, 2), ("Story & Takes", "campath/lighthouse_take3.mp4", None, 2), ("Story & Takes", "campath/wan_canyon.mp4", None, 3),
    ("Music & voices", "music/reactive.mp4", 8.0, 3), ("Music & voices", "dub/dub_es_relip.mp4", None, 4), ("Music & voices", "motion/infinitetalk_0.mp4", None, 4), ("Music & voices", "motion/wan_animate2_1.mp4", None, 3),
    ("University", "ui:university", None, 5), ("University", "ui:sampling", None, 4),
    ("Films", "film:A", 59.6, 5), ("Films", "film:B", 45.0, 5, TOP), ("Films", "music/wren_light_the_wreckage.mp4", 42.0, 5),
]


def reel(a):
    work = a.work / "reel"; (work / "seg").mkdir(parents=True, exist_ok=True); nums = json.loads((DEMOS / "numbers.json").read_text()); L = Labels(a.studio)
    music, m0, mdur = MUSIC["reel"]; mw = wav(music, a.work); bt = [b for b in beats(mw) if b < mdur]
    films = {"film:A": Path(a.films) / "ParametricStudio_FilmA_RUN_MiniMaxH3.mp4", "film:B": Path(a.films) / "ParametricStudio_FilmB_ONE_CLIP_LTX25.mp4"} if a.films else {}
    tour = json.loads((Path(a.tour) / "timeline_cut.json").read_text()) if a.tour else None
    start_i = min(range(len(bt)), key=lambda i: abs(bt[i] - 4.4)); idx = start_i; edl = []; chapters = list(dict.fromkeys(c for c, *_ in REEL))
    for chap, src, t_in, nb, *opt in REEL:
        t0, t1 = bt[idx], bt[idx + nb]; idx += nb; lab = L(src); f0, f1 = round(t0 * FPS), round(t1 * FPS)
        edl.append({"chapter": chap, "src": src, "t_in": t_in, "start": f0 / FPS, "end": f1 / FPS, "frames": f1 - f0, **lab, **(opt[0] if opt else {})})
    open_f = round(edl[0]["start"] * FPS); end_f = round(mdur * FPS); close_f = end_f - round(edl[-1]["end"] * FPS)
    # overlays
    jobs = []
    for i, e in enumerate(edl):
        k = f"{chapters.index(e['chapter']) + 1}/{len(chapters)}  {e['chapter']}"
        e["png"] = str(work / f"lt_{i:02d}.png"); jobs.append((lower_third(k.upper(), e["main"], e["sub"], top=52 if e.get("top") else None) + ("" if e.get("own_tag") else ai_tag()), e["png"]))
    foot_open = f"Counted from this release on {nums['as_of']}: node classes from our ComfyUI 0.43.0 (partner API nodes left out), the rest from the repo and the studio's own pages."
    foot_close = f"Every clip is AI-generated and already in the repo or the demo release. Each label names the model or graph from that clip's own record. Wren Halloway was made before the studio, and says so.<br>Music: {CREDIT[music]}."
    for f in range(open_f): jobs.append((counts_card(nums, min(1, f / (open_f * 0.75)), foot_open), work / f"open_{f:04d}.png"))
    for f in range(min(close_f, 45)): jobs.append((counts_card(nums, 1, foot_close if f > 12 else "", title="That was a few of them", tsize=92), work / f"close_{f:04d}.png"))
    shots(jobs, chrome=a.chrome, opaque=False)
    for p in work.glob("open_*.png"): pass
    parts = []
    frames_to_video(work / "open_%04d.png", work / "seg" / "000_open.mp4"); parts.append(work / "seg" / "000_open.mp4")
    for i, e in enumerate(edl):
        out = work / "seg" / f"{i + 1:03d}.mp4"; src = e["src"]
        if src.startswith("ui:"):
            t = next(x for x in tour if x["tab"] == src[3:]); path, t_in = Path(a.tour) / "tour_clean.mp4", t["cut_start"] + 0.3
            e["sub"] = f"{t['title']} tab: {t['sub']}" if t.get("sub") else f"{t['title']} tab"; shots([(lower_third(f"{chapters.index(e['chapter']) + 1}/{len(chapters)}  {e['chapter']}".upper(), e["main"], e["sub"]) + ai_tag(), e["png"])], chrome=a.chrome)
        elif src in films: path, t_in = films[src], e["t_in"]
        elif src.startswith("docs/"): path, t_in = ROOT / src, e["t_in"]
        else: path = WEB / src; t_in = e["t_in"] if e["t_in"] is not None else max(0.0, min(probe(path)["dur"] * 0.3, probe(path)["dur"] - e["frames"] / FPS - 0.05))
        e["t_in"] = round(t_in, 3); segment(path, out, e["frames"], t_in, e["png"], still=src.endswith((".webp", ".jpg", ".png"))); parts.append(out)
    frames_to_video(work / "close_%04d.png", work / "seg" / "998_close_a.mp4")
    frames_to_video(work / f"close_{min(close_f, 45) - 1:04d}.png", work / "seg" / "999_close_b.mp4", frames=close_f - min(close_f, 45), still=True)
    parts += [work / "seg" / "998_close_a.mp4", work / "seg" / "999_close_b.mp4"]; concat(parts, work / "video.mp4")
    lv = level(mw, work / "music.wav", m0, mdur, fade_out=2.0)
    master, web = a.out / "ParametricStudio_Demo_Reel.mp4", ROOT / "docs" / "media" / "demo_reel.mp4"; mux(work / "video.mp4", work / "music.wav", master, web, web_crf=a.web_crf)
    for e in edl: e.pop("png", None)
    DEMOS.mkdir(parents=True, exist_ok=True)
    (DEMOS / "reel_edl.json").write_text(json.dumps({"music": {"file": music, "credit": CREDIT[music], **lv}, "beats_used": bt[start_i:idx + 1], "open_seconds": open_f / FPS, "close_seconds": close_f / FPS, "clips": edl}, indent=1, ensure_ascii=False) + "\n")
    print(master, probe(master)["dur"], lv)


# ---------- the wall ----------
WALL_SKIP = re.compile(r"^edit_art/|^dub/|political|latentsync|guide|_depth|_edges|matte|cutout|_ba_|shot_2|shot_4|shot_3|clay|shaded|interpolat|decompress|deblur|restore|hdr|upscale|colorize|track_boat|sam3d_capture_1|"
                       r"hy-motion|knot|reactive|wren|join|smooth|/move|/p[123]\.mp4|captions|frame-interpolation|seedvr2|flashvsr|upscale-models|master\.talk|ltx-2-5_2|minimax-h3_2|wan2-2_2")


def wall_pick(n=100, seed=7):
    """n different renders: every folder gets a share, near-duplicates and technical passes (mattes, depth, guides, before/after strips) left out.
    Edit and Dub & Voice are left out too: every one of their clips is the same source clip edited, so they look alike on a wall."""
    vids = sorted(str(p.relative_to(WEB)) for p in WEB.rglob("*.mp4") if not WALL_SKIP.search(str(p.relative_to(WEB))))
    by = {}
    for v in vids: by.setdefault(v.split("/")[0], []).append(v)
    rnd = random.Random(seed); out = []
    for k in by: rnd.shuffle(by[k])
    while len(out) < n and any(by.values()):
        for k in sorted(by, key=lambda k: -len(by[k])):
            if by[k] and len(out) < n: out.append(by[k].pop())
    return out


def wall(a):
    work = a.work / "wall"; work.mkdir(parents=True, exist_ok=True); nums = json.loads((DEMOS / "numbers.json").read_text()); total = nums["rendered_media"]["value"]
    picks = wall_pick(); rnd = random.Random(11); order = list(range(100)); rnd.shuffle(order)
    D, fill0, fill1, card_at = 25.0, 0.3, 15.0, 19.5; tw, th = W // 10, H // 10
    starts = {pos: fill0 + (fill1 - fill0) * k / 99 for k, pos in enumerate(order)}      # tile `pos` (row-major) appears at starts[pos]
    inputs, chains = [], []
    for pos, v in enumerate(picks):
        inputs += ["-stream_loop", "-1", "-t", str(card_at + 1.5), "-i", WEB / v]
        chains.append(f"[{pos}:v]fps={FPS},scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},setsar=1,trim=duration={card_at + 1.5},setpts=PTS-STARTPTS,fade=in:st={starts[pos]:.3f}:d=0.35[t{pos}]")
    layout = "|".join(f"{(i % 10) * tw}_{(i // 10) * th}" for i in range(100))
    graph = ";".join(chains) + ";" + "".join(f"[t{i}]" for i in range(100)) + f"xstack=inputs=100:layout={layout}:fill=black,format=yuv420p[v]"
    if not (work / "grid.mp4").exists() or a.fresh: run(["ffmpeg", "-y", "-hide_banner", *inputs, "-filter_complex", graph, "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-r", str(FPS), work / "grid.mp4"])
    # the counter: it reaches the real total as the last tile lands, and says that only 100 of them fit
    jobs, last = [], None
    for f in range(int((card_at + 1.5) * FPS)):
        t = f / FPS; k = min(1, max(0, (t - fill0) / (fill1 - fill0))); v = round(total * (1 - (1 - k) ** 2)); shown = sum(1 for s in starts.values() if s <= t)
        body = f"""<div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);text-align:center;background:rgba(7,9,8,.80);border:1px solid rgba(255,255,255,.14);border-radius:22px;padding:30px 54px 32px;box-shadow:0 20px 60px rgba(0,0,0,.6)">
<div class="disp y" style="font-size:150px;line-height:1;font-stretch:100%;font-variant-numeric:tabular-nums">{fmt(v)}</div><div style="font-size:30px;font-weight:600;margin-top:12px">rendered files shipped in the repo</div>
<div class="m" style="font-size:21px;margin-top:8px">{shown} of them on this wall, each a different render</div></div>{ai_tag()}"""
        jobs.append((body, work / f"c_{f:04d}.png"))
    shots(jobs, chrome=a.chrome)
    foot = f"Counted from this release on {nums['as_of']}. Each tile is a different render already in the repo; the list is in docs/demos/wall_tiles.json.<br>Music: {CREDIT[MUSIC['wall'][0]]}."
    shots([(counts_card(nums, 1, foot), work / "card.png")], chrome=a.chrome, opaque=True)
    n_over = int((card_at + 1.5) * FPS)
    run(["ffmpeg", "-y", "-hide_banner", "-i", work / "grid.mp4", "-framerate", str(FPS), "-i", work / "c_%04d.png", "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p[v]", "-map", "[v]",
         "-frames:v", str(n_over), "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-r", str(FPS), work / "grid_counted.mp4"])
    frames_to_video(work / "card.png", work / "card.mp4", frames=int((D - card_at + 1) * FPS), still=True)
    run(["ffmpeg", "-y", "-hide_banner", "-i", work / "grid_counted.mp4", "-i", work / "card.mp4", "-filter_complex",
         f"[0:v]settb=1/{FPS},setsar=1[a];[1:v]settb=1/{FPS},setsar=1[b];[a][b]xfade=transition=fade:duration=0.8:offset={card_at},format=yuv420p[v]", "-map", "[v]", "-frames:v", str(int(D * FPS)),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-r", str(FPS), work / "video.mp4"])
    music, m0, mdur = MUSIC["wall"]; lv = level(wav(music, a.work), work / "music.wav", m0, mdur, fade_in=0.4, fade_out=2.5)
    master, web = a.out / "ParametricStudio_Demo_Wall.mp4", ROOT / "docs" / "media" / "demo_wall.mp4"; mux(work / "video.mp4", work / "music.wav", master, web, web_crf=a.web_crf + 2)
    (DEMOS / "wall_tiles.json").write_text(json.dumps({"music": {"file": music, "credit": CREDIT[music], **lv}, "counter_to": total, "counter_from": "numbers.json rendered_media",
                                                      "tiles": [{"pos": i, "row": i // 10, "col": i % 10, "src": v, "appears": round(starts[i], 3)} for i, v in enumerate(picks)]}, indent=1) + "\n")
    print(master, probe(master)["dur"], lv)


# ---------- the tour ----------
LEAD = 0.6      # each tab is cut in this long after it opened, so the page's own fade and loading never show


def tour_frames_video(tdir, out, segs):
    """segs: (from, to) times in the recording, joined with hard cuts. Each frame is held until the next one, as the screencast sends a frame only when the page changes."""
    tl = json.loads((tdir / "timeline.json").read_text()); fr = tl["frames"]; lines = []
    for a0, a1 in segs:
        i = max([k for k, t in enumerate(fr) if t <= a0] or [0])
        while i < len(fr) and (fr[i] if fr[i] > a0 else a0) < a1:
            t = max(fr[i], a0); nxt = min(a1, fr[i + 1]) if i + 1 < len(fr) else a1
            lines.append(f"file '{tdir / 'frames' / f'{i:06d}.jpg'}'\nduration {max(0.001, nxt - t):.4f}\n"); i += 1
    lines.append(lines[-1].split("\n")[0] + "\n"); lst = out.with_suffix(".txt"); lst.write_text("".join(lines))
    sz = tl["size"]; w, h = (sz["width"] * 2, sz["height"] * 2) if tl["phone"] else (sz["width"], sz["height"]); total = sum(b - a for a, b in segs)
    run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"scale={w}:{h},fps={FPS},format=yuv420p", "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", out])
    return total


def tour(a):
    tdir = Path(a.tour); work = a.work / ("phone" if a.phone else "tour"); work.mkdir(parents=True, exist_ok=True)
    tl = json.loads((tdir / "timeline.json").read_text()); segs = [(t["start"] + (LEAD if i else 0), t["end"]) for i, t in enumerate(tl["tabs"])]
    clean = work / "clean.mp4"; end = tour_frames_video(tdir, clean, segs); n = len(tl["tabs"])
    acc = 0.0
    for t, (s0, s1) in zip(tl["tabs"], segs): t["cut_start"], t["cut_end"], t["rec_from"] = round(acc, 3), round(acc + s1 - s0, 3), round(s0, 3); acc += s1 - s0
    if not a.phone: (tdir / "tour_clean.mp4").write_bytes(clean.read_bytes()); (tdir / "timeline_cut.json").write_text(json.dumps(tl["tabs"], indent=1))      # the reel's University chapter cuts from this
    if a.phone: w, h, s = 1080, 1920, 1.0
    else: w, h, s = 1440, 900, 0.78
    music_note = "Music: " + (CREDIT[MUSIC["phone"][0]] if a.phone else f"{CREDIT['music/ace15_xl_turbo.m4a']}, then {CREDIT['music/diffsynth_music.m4a']}") + "."
    jobs, spans = [], []
    for i, t in enumerate(tl["tabs"]):
        kick = f"{i + 1} / {n}  ·  {'phone, 390 px wide' if a.phone else 'studio tour'}"
        main = t["label"] if t["label"].lower() == t["title"].lower() else f"{t['label']} · {t['title']}"
        if a.phone: body = lower_third(kick.upper(), main, t.get("sub") or "", scale=1.5, left=40, bottom=70)
        else: body = lower_third(kick.upper(), main, t.get("sub") or "", scale=s, left=120, bottom=26)
        jobs.append((body, work / f"cap_{i:02d}.png")); spans.append((t["cut_start"], t["cut_end"]))
    intro = ("A preview of this release with no GPU attached, so nothing generates: every page, every render and every number is real, read from the repo."
             if not a.phone else "The same studio on a phone: eight key tabs.")
    top = f"""<div style="position:absolute;left:{120 if not a.phone else 40}px;right:{40}px;top:{18 if not a.phone else 60}px;background:rgba(7,9,8,.85);border:1px solid rgba(245,197,24,.5);border-radius:12px;padding:12px 18px;font-size:{17 if not a.phone else 30}px;line-height:1.4">{intro}</div>"""
    outro = f"""<div style="position:absolute;left:{120 if not a.phone else 40}px;right:40px;top:{18 if not a.phone else 60}px;background:rgba(7,9,8,.85);border:1px solid rgba(255,255,255,.2);border-radius:12px;padding:12px 18px;font-size:{15 if not a.phone else 26}px;line-height:1.4;color:#c9cec6">{music_note}</div>"""
    jobs += [(top, work / "intro.png"), (outro, work / "outro.png")]; shots(jobs, w, h, chrome=a.chrome)
    if a.phone:      # the phone screen sits in a 1080x1920 frame with room for the captions
        base = f"[0:v]scale=-2:1560,pad={w}:{h}:(ow-iw)/2:150:color=0x070908,setsar=1[b]"
    else: base = "[0:v]setsar=1[b]"
    inputs = ["-i", clean] + sum([["-i", p] for _, p in jobs], []); g = [base]; last = "b"
    for i, (st, en) in enumerate(spans):
        g.append(f"[{last}][{i + 1}:v]overlay=0:0:enable='between(t,{st:.3f},{en - 0.001:.3f})'[o{i}]"); last = f"o{i}"
    k = len(spans) + 1
    g.append(f"[{last}][{k}:v]overlay=0:0:enable='between(t,0,3.5)'[oi]"); g.append(f"[oi][{k + 1}:v]overlay=0:0:enable='between(t,{end - 4:.3f},{end:.3f})',format=yuv420p[v]")
    run(["ffmpeg", "-y", "-hide_banner", *inputs, "-filter_complex", ";".join(g), "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-r", str(FPS), work / "video.mp4"])
    if a.phone:
        music, m0, _ = MUSIC["phone"]; lv = level(wav(music, a.work), work / "music.wav", m0, end, fade_in=0.3, fade_out=2.0); credit = CREDIT[music]
        master, web = a.out / "ParametricStudio_Demo_Tour_Phone.mp4", ROOT / "docs" / "media" / "demo_tour_phone.mp4"; mux(work / "video.mp4", work / "music.wav", master, web, web_w=540, web_crf=a.web_crf + 2, web_abr="96k")
    else:      # ACE-Step 1.5 XL Turbo's own ending, crossfaded into DiffSynth-Music's opening
        w1, w2 = wav("music/ace15_xl_turbo.m4a", a.work), wav("music/diffsynth_music.m4a", a.work); joined = work / "joined.wav"
        run(["ffmpeg", "-y", "-hide_banner", "-i", w1, "-i", w2, "-filter_complex", "[0:a]atrim=0:68,asetpts=PTS-STARTPTS[a];[1:a]asetpts=PTS-STARTPTS[b];[a][b]acrossfade=d=5:c1=tri:c2=tri[o]", "-map", "[o]", joined])
        lv = level(joined, work / "music.wav", 0, end, fade_out=2.5); credit = f"{CREDIT['music/ace15_xl_turbo.m4a']}, then {CREDIT['music/diffsynth_music.m4a']}"
        master, web = a.out / "ParametricStudio_Demo_Tour.mp4", ROOT / "docs" / "media" / "demo_tour.mp4"; mux(work / "video.mp4", work / "music.wav", master, web, web_w=1280, web_abr="96k", web_kbps=480)
    DEMOS.mkdir(parents=True, exist_ok=True)
    (DEMOS / ("tour_phone_edl.json" if a.phone else "tour_edl.json")).write_text(json.dumps({"music": {"credit": credit, **lv}, "recorded_on": "a preview studio of this release, ComfyUI not attached",
        "tabs": [{k: t[k] for k in ("tab", "label", "title", "cut_start", "cut_end")} for t in tl["tabs"]]}, indent=1, ensure_ascii=False) + "\n")
    print(master, probe(master)["dur"], lv)


def posters(a):
    """Poster stills for the README, from the masters: the dragon in the reel, the full wall, and the Families tab in the tour."""
    tour = json.loads((DEMOS / "tour_edl.json").read_text()); fam = next(t for t in tour["tabs"] if t["tab"] == "families")
    for master, t, name in (("ParametricStudio_Demo_Reel.mp4", 29.6, "demo_reel.webp"), ("ParametricStudio_Demo_Wall.mp4", 17.0, "demo_wall.webp"), ("ParametricStudio_Demo_Tour.mp4", fam["cut_start"] + 0.4, "demo_tour.webp")):
        run(["ffmpeg", "-y", "-hide_banner", "-ss", str(t), "-i", a.out / master, "-frames:v", "1", "-vf", "scale=1280:-2:flags=lanczos", "-c:v", "libwebp", "-quality", "78", "-map_metadata", "-1", ROOT / "docs" / "media" / name])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("what", choices=("reel", "wall", "tour", "sheets", "posters")); ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, help="where the 1080p masters go (default WORK/masters)"); ap.add_argument("--studio", default="http://127.0.0.1:8310"); ap.add_argument("--films", help="folder with the two released film masters")
    ap.add_argument("--tour", help="a scripts/record_studio_tour.py output folder"); ap.add_argument("--phone", action="store_true"); ap.add_argument("--chrome"); ap.add_argument("--web-crf", type=int, default=27); ap.add_argument("--fresh", action="store_true", help="wall: rebuild the grid even if it is there")
    ap.add_argument("--video", type=Path, help="sheets: the video to make contact sheets of"); a = ap.parse_args(argv)
    a.out = a.out or a.work / "masters"; a.out.mkdir(parents=True, exist_ok=True); (ROOT / "docs" / "media").mkdir(parents=True, exist_ok=True)
    if a.what == "sheets": print(contact_sheets(a.video, a.work / "sheets", a.video.stem)); return 0
    {"reel": reel, "wall": wall, "tour": tour, "posters": posters}[a.what](a); return 0


if __name__ == "__main__":
    sys.exit(main())
