#!/usr/bin/env python3
"""The narrated walkthrough: docs/demos/walkthrough_script.md read aloud by Kokoro 82M's built-in male voice (am_michael, Apache-2.0) on the CPU, over screen passes of the studio and real renders.
  voice    speak every sentence (cached), lay them out with pauses, and write the timing; then Whisper (faster-distil-whisper large-v3, CPU) hears it back and the word error rate is checked
  plan     the tabs to record and how long each must be held, for scripts/record_studio_tour.py --plan
  video    cut the shots to the narration, burn in the captions, duck the studio's own music under the voice, level to -16 LUFS, and write the master and the web copy
Usage: python scripts/build_walkthrough.py voice|plan|video --cut full|short --work DIR [--kokoro DIR] [--whisper DIR] [--tour DIR] [--phone-tour DIR] [--studio URL] [--chrome PATH]"""
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_demo_videos as V      # noqa: E402

ROOT = V.ROOT; WEB = V.WEB; DEMOS = V.DEMOS; FPS = V.FPS; W, H = 1920, 1080
SCRIPT = DEMOS / "walkthrough_script.md"; VOICE = "am_michael"; SR = 24000
PACE = {"full": dict(speed=1.1, sentence=0.28, para=0.6, section=0.9), "short": dict(speed=1.15, sentence=0.2, para=0.4, section=0.55)}      # about 150 words a minute with the pauses
LEAD_IN, TAIL = 0.6, 1.8
# How the voice should say what the captions show. The captions keep the written form.
SAY = [(r"\bComfyUI\b", "Comfy U I"), (r"\bLTX-2\.5\b", "L T X two point five"), (r"\bLTX\b", "L T X"), (r"\bH3\b", "H three"), (r"\bIC-LoRAs?\b", lambda m: "I C Laura" + ("s" if m.group(0).endswith("s") else "")),
       (r"\bLoRAs?\b", lambda m: "Laura" + ("s" if m.group(0).endswith("s") else "")), (r"\bAGPL\b", "A G P L"), (r"\bSDR\b", "S D R"), (r"\bHLG\b", "H L G"), (r"\bEXR\b", "E X R"),
       (r"\bProRes\b", "Pro Rez"), (r"\bTailscale\b", "Tail scale"), (r"\bdeblurs\b", "dee-blurs"), (r"\bLightricks\b", "Light tricks"), (r"\bFLUX\.2\b", "Flux two"), (r"\bFLUX\b", "Flux"), (r"\bQwen-Image\b", "Kwen Image"), (r"\bACE-Step\b", "Ace Step"), (r"\bControlFoley\b", "Control Foley"),
       (r"\bffmpeg\b", "F F mpeg"), (r"\bHTTPS\b", "H T T P S"), (r"\bQR\b", "Q R"), (r"\bAPI\b", "A P I"), (r"\b3D\b", "three D"), (r"\bGPU\b", "G P U"), (r"\bTV\b", "T V"), (r"Pool 51", "Pool fifty-one"),
       (r"\bVFX\b", "V F X"), (r"\bComfyUniversity\b", "Comfy University"), (r"\bOpenjutsu\b", "Open jutsu")]
MUSIC_BED = ("families/mini-max-music3_0.mp3", "families/ace-step-1-5_0.mp3")      # the same instrumental brief, by MiniMax Music 3 and by ACE-Step 1.5 XL Base
MUSIC_CREDIT = "Music: one instrumental brief (warm cello and soft piano), made in the studio with MiniMax-Music3 (MiniMax-Music3 Community License) and ACE-Step 1.5 XL Base (MIT)."


def say(text):
    for rx, rep in SAY: text = re.sub(rx, rep, text)
    return text


def parse(cut):
    """-> [{title, shots, paras: [[sentence, ...], ...]}] for the full walkthrough or the short cut."""
    md = SCRIPT.read_text(encoding="utf-8"); part = md.split("# Full walkthrough", 1)[1].split("# Short cut")[0 if cut == "full" else 1]
    if cut == "short": part = md.split("# Short cut", 1)[1]
    out = []
    for block in re.split(r"^## ", part, flags=re.M)[1:]:
        lines = block.strip().splitlines(); title = lines[0].strip(); shots = []; paras = []; cur = []
        for l in lines[1:]:
            if l.startswith("Picture:"): shots = [x.strip() for x in l[8:].split(",") if x.strip()]
            elif l.strip(): cur.append(l.strip())
            elif cur: paras.append(" ".join(cur)); cur = []
        if cur: paras.append(" ".join(cur))
        out.append({"title": title, "shots": shots, "paras": [re.split(r"(?<=[.?!])\s+(?=[A-Z])", p) for p in paras]})
    return out


# ---------- the voice ----------
def voice(a):
    os.environ["CUDA_VISIBLE_DEVICES"] = ""; os.environ["HF_HUB_OFFLINE"] = "1"      # the CPU only, and nothing fetched
    import numpy as np, soundfile as sf, torch
    from kokoro import KModel, KPipeline
    secs = parse(a.cut); cache = a.work / "walk" / "say"; cache.mkdir(parents=True, exist_ok=True); kdir = Path(a.kokoro)
    model = KModel(config=str(kdir / "config.json"), model=str(kdir / "kokoro-v1_0.pth")).eval(); pipe = KPipeline(lang_code="a", model=model, repo_id="hexgrad/Kokoro-82M")
    vpack = torch.load(kdir / "voices" / f"{VOICE}.pt", weights_only=True); pieces, t, timing = [], LEAD_IN, []; pace = PACE[a.cut]
    pieces.append(np.zeros(int(LEAD_IN * SR), np.float32))
    for si, sec in enumerate(secs):
        sec_start = t; sents = []
        for pi, para in enumerate(sec["paras"]):
            for k, s in enumerate(para):
                f = cache / (hashlib.sha1((f"{VOICE}|{pace['speed']}|" + say(s)).encode()).hexdigest()[:16] + ".wav")
                if not f.exists():
                    audio = np.concatenate([x.numpy() for _, _, x in pipe(say(s), voice=vpack, speed=pace["speed"])]); sf.write(str(f), audio, SR)
                audio, _ = sf.read(str(f), dtype="float32"); pieces.append(audio); sents.append({"text": s, "start": round(t, 3), "end": round(t + len(audio) / SR, 3)}); t += len(audio) / SR
                gap = pace["sentence"] if k < len(para) - 1 else (pace["para"] if pi < len(sec["paras"]) - 1 else (pace["section"] if si < len(secs) - 1 else TAIL))
                pieces.append(np.zeros(int(gap * SR), np.float32)); t += gap
        timing.append({"title": sec["title"], "shots": sec["shots"], "start": round(sec_start, 3), "end": round(t, 3), "sentences": sents})
    out = a.work / "walk" / f"narration_{a.cut}.wav"; sf.write(str(out), np.concatenate(pieces), SR)
    (a.work / "walk" / f"timing_{a.cut}.json").write_text(json.dumps({"voice": f"Kokoro 82M, {VOICE}", "seconds": round(t, 3), "sections": timing}, indent=1))
    words = sum(len(s["text"].split()) for x in timing for s in x["sentences"]); print(f"{a.cut}: {t:.1f} s, {words} words, {words / t * 60:.0f} words a minute")
    hear(a, out, timing)


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def spell(n):
    n = int(n)
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000: return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " and " + spell(n % 100))
    if n < 10**6: return spell(n // 1000) + " thousand" + ("" if n % 1000 == 0 else (" and " if n % 1000 < 100 else " ") + spell(n % 1000))
    return str(n)


SAME = [("comfy u i", "comfyui"), ("comfy university", "comfyuniversity"), ("comfy ui", "comfyui"), ("mini max", "minimax"), ("laura", "lora"), ("license", "licence"), ("control foley", "controlfoley"), ("re-shoot", "reshoot"), ("re shoot", "reshoot"),
        ("shootout", "shoot out"), ("lightrix", "lightricks"), ("i see lora", "ic lora"), ("light tricks", "lightricks"), ("fast api", "fastapi"), ("open jutsu", "openjutsu"), ("ic-lora", "ic lora"), ("a g p l", "agpl"), ("tail scale", "tailscale")]      # the same word spelled two ways, not a mistake


def norm(text):
    t = text.lower()
    for x, y in SAME: t = t.replace(x, y)
    t = re.sub(r"(\d),(\d{3})", r"\1\2", t); t = re.sub(r"[-–—/]", " ", t); t = re.sub(r"\d+", lambda m: " " + spell(m.group(0)) + " ", t)
    t = re.sub(r"[^a-z' ]", " ", t); t = t.replace(" and ", " ").replace("'s", "s"); return [HOMOPHONE.get(w, w) for w in t.split()]


HOMOPHONE = {"cue": "queue", "mat": "matte", "sinks": "syncs", "sighted": "cited", "chute": "shoot"}      # words that sound the same: Whisper cannot tell them apart, so they are not errors


def wer(ref, hyp):
    r, h = norm(ref), norm(hyp); d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1): prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
    return d[len(h)] / max(1, len(r))


def hear(a, wav, timing):
    """Whisper hears each spoken sentence on its own (no 30-second windows to stitch, so nothing is heard twice), and the word error rate is measured against the script.
    Anything Whisper hears twice in a row that the script does not say twice is listed as a repeat."""
    import numpy as np, soundfile as sf
    from faster_whisper import WhisperModel
    w16 = Path(str(wav)[:-4] + "_16k.wav"); V.run(["ffmpeg", "-y", "-hide_banner", "-i", wav, "-ar", "16000", "-ac", "1", w16]); audio, sr = sf.read(str(w16), dtype="float32")      # decoded here, not by Whisper's own reader
    m = WhisperModel(a.whisper, device="cpu", compute_type="int8"); rows, refs, hyps, repeats = [], [], [], []
    for sec in timing:
        for s in sec["sentences"]:
            x = audio[max(0, int((s["start"] - 0.15) * sr)):int((s["end"] + 0.15) * sr)]; segs, _ = m.transcribe(x, language="en", beam_size=5, vad_filter=False)
            hyp = " ".join(z.text.strip() for z in segs); r, h = norm(s["text"]), norm(hyp); refs.append(s["text"]); hyps.append(hyp)
            for n in (2, 3, 4):
                for i in range(len(h) - 2 * n + 1):
                    if h[i:i + n] == h[i + n:i + 2 * n] and " ".join(h[i:i + 2 * n]) not in " ".join(r): repeats.append({"said": s["text"], "heard": hyp})
            rows.append({"section": sec["title"], "said": s["text"], "heard": hyp, "wer": round(wer(s["text"], hyp), 3)})
    res = {"model": "faster-distil-whisper large-v3, CPU, int8, one sentence at a time", "wer": round(wer(" ".join(refs), " ".join(hyps)), 4), "repeats": repeats, "sentences": rows}
    (a.work / "walk" / f"heard_{a.cut}.json").write_text(json.dumps(res, indent=1)); print(f"WER {res['wer']:.1%}, {len(repeats)} repeats")
    for r in rows:
        if r["wer"] > 0: print(f"  {r['wer']:.0%}  said: {r['said']}\n        heard: {r['heard']}")


# ---------- the picture ----------
def shot_times(timing):
    """Each section's stretch split evenly across its shots: -> [(section, shot, start, end)]."""
    out = []
    for k, sec in enumerate(timing["sections"]):
        s0 = 0.0 if k == 0 else sec["start"]; n = len(sec["shots"]); d = (sec["end"] - s0) / n      # the first shot also covers the lead-in
        for i, s in enumerate(sec["shots"]): out.append((sec, s, s0 + i * d, s0 + (i + 1) * d))
    return out


def shot_ref(shot):
    kind, _, rest = shot.partition(":"); src, _, at = rest.partition("@"); return kind, src, float(at) if at else None


def plan(a):
    timing = json.loads((a.work / "walk" / f"timing_{a.cut}.json").read_text()); need = {}
    for _, shot, t0, t1 in shot_times(timing):
        kind, src, at = shot_ref(shot)
        if kind == "tab": need[src] = max(need.get(src, 0), (at or 0) + (t1 - t0) + 0.6 + 0.8)      # the tour cuts 0.6 s of loading off the start of each tab
    out = a.work / "walk" / f"plan_{a.cut}.json"; out.write_text(json.dumps({k: round(v, 1) for k, v in need.items()}, indent=1)); print(out, sum(need.values()), "s to record")


def caption_chunks(sents, maxc=96):
    """Sentences into caption-sized pieces, timed by their share of the sentence's letters."""
    out = []
    for s in sents:
        parts, cur = [], ""
        for w in re.split(r"(?<=[,:;])\s+", s["text"]):
            if cur and len(cur) + 1 + len(w) > maxc: parts.append(cur); cur = w
            else: cur = (cur + " " + w).strip()
        if cur: parts.append(cur)
        fine = []
        for p in parts:
            while len(p) > maxc + 20:
                cut = p.rfind(" ", 0, maxc); fine.append(p[:cut]); p = p[cut + 1:]
            fine.append(p)
        total = sum(len(p) for p in fine); t = s["start"]
        for p in fine: d = (s["end"] - s["start"]) * len(p) / total; out.append({"text": p, "start": round(t, 3), "end": round(t + d, 3)}); t += d
    return out


def caption_html(text):
    return f"""<div style="position:absolute;left:50%;bottom:44px;transform:translateX(-50%);max-width:1500px;text-align:center"><span style="display:inline;background:rgba(7,9,8,.82);color:#f6f6f1;font:600 36px/1.42 Inter;padding:6px 16px;border-radius:10px;-webkit-box-decoration-break:clone;box-decoration-break:clone">{text}</span></div>"""


def chip_html(kicker, main):
    return f"""<div style="position:absolute;left:40px;top:34px;max-width:1100px;padding:12px 18px 13px;border-radius:12px;background:rgba(7,9,8,.80);border:1px solid rgba(255,255,255,.12)">
<div class="disp y" style="font-size:16px;letter-spacing:.06em">{kicker}</div><div style="font-weight:700;font-size:26px;line-height:1.2;margin-top:3px">{main}</div></div>""" + V.ai_tag()


def rows_card(kicker, title, rows):
    items = "".join(f"""<div style="display:flex;gap:22px;align-items:baseline;padding:20px 0;border-top:1px solid rgba(255,255,255,.14)"><div class="disp y" style="font-size:42px;font-stretch:100%">{i + 1:02d}</div><div style="font-size:36px;font-weight:600">{r}</div></div>""" for i, r in enumerate(rows))
    return f"""<div style="position:absolute;inset:0;background:#070908;padding:0 150px 150px;display:flex;flex-direction:column;justify-content:center"><div class="disp" style="font-size:22px;letter-spacing:.18em;color:#9aa39a">{kicker}</div><div class="disp" style="font-size:88px;margin:14px 0 34px">{title}</div>{items}</div>"""


def card_html(name, nums, cut):
    if name == "built":
        return rows_card("PARAMETRIC STUDIO", "How it's built", ["The apps run real ComfyUI graphs on your local ComfyUI server", "The graph you open in 3D is the graph that runs", "A FastAPI and Preact studio, with no build step",
                         "Every custom node of ours audited, the results in docs/NODES.md", "Pool 51 node packs pinned to checked commits", "Open weights, run locally, at 0 credits"])
    if name == "checks":
        rows = ["A privacy scan of every file: private paths, secrets, private strings", "A licence check of the code and every vendored file", f"The full test suite, {V.fmt(nums['tests']['value'])} tests, on the exact tree that ships", "Every figure from the repo's own records: docs/demos/numbers.json"]
        items = "".join(f"""<div style="display:flex;gap:22px;align-items:baseline;padding:22px 0;border-top:1px solid rgba(255,255,255,.14)"><div class="disp y" style="font-size:44px;font-stretch:100%">{i + 1:02d}</div><div style="font-size:38px;font-weight:600">{r}</div></div>""" for i, r in enumerate(rows))
        return f"""<div style="position:absolute;inset:0;background:#070908;padding:0 150px 140px;display:flex;flex-direction:column;justify-content:center"><div class="disp" style="font-size:22px;letter-spacing:.18em;color:#9aa39a">BEFORE EVERY RELEASE</div><div class="disp" style="font-size:92px;margin:14px 0 40px">Held to its claims</div>{items}</div>"""
    return f"""<div style="position:absolute;inset:0;background:radial-gradient(1200px 700px at 15% 0%,rgba(245,197,24,.12),transparent 60%),#070908;display:flex;flex-direction:column;justify-content:center;padding:0 150px 140px">
<div class="disp" style="font-size:24px;letter-spacing:.18em;color:#9aa39a">PARAMETRIC STUDIO</div><div class="disp" style="font-size:104px;line-height:1.02;margin:16px 0 30px">Real graphs. Your GPU.<br><span class="y">Open weights. Zero credits.</span></div>
<div style="font-size:30px;color:#c9cec6">github.com/parametricparadigm/ComfyUI_Parametric_Studio</div>
<div style="font-size:21px;color:#aeb5ac;margin-top:44px;line-height:1.5">Narration: Kokoro 82M, its built-in voice am_michael (Apache-2.0), read on the CPU. Every render shown is AI-generated and in the repo.<br>{MUSIC_CREDIT}</div></div>"""


def video(a):
    timing = json.loads((a.work / "walk" / f"timing_{a.cut}.json").read_text()); nums = json.loads((DEMOS / "numbers.json").read_text())
    work = a.work / "walk" / a.cut; (work / "seg").mkdir(parents=True, exist_ok=True); L = V.Labels(a.studio)
    tour = Path(a.tour); tl = json.loads((tour / "timeline.json").read_text()); tabs = {t["tab"]: t for t in tl["tabs"]}
    shots = shot_times(timing); jobs, parts, edl = [], [], []
    for i, (sec, shot, t0, t1) in enumerate(shots):
        f0, f1 = round(t0 * FPS), round(t1 * FPS); kind, src, at = shot_ref(shot); png = work / f"chip_{i:03d}.png"
        if kind == "clip":
            lab = L(src if not src.startswith("docs/") else "docs/media/shotboard_demo.mp4"); jobs.append((chip_html(sec["title"].upper(), "Render: " + lab["main"]), png))
        elif kind == "tab": jobs.append((chip_html(sec["title"].upper(), tabs[src]["title"] + " tab"), png)); lab = {"main": "screen capture", "record": "tour"}
        elif kind == "phone": jobs.append((chip_html(sec["title"].upper(), "The studio at 390 px wide"), png)); lab = {"main": "screen capture, phone", "record": "phone tour"}
        else: jobs.append(("", png)); lab = {"main": "card", "record": "this script"}
        edl.append({"section": sec["title"], "shot": shot, "start": round(f0 / FPS, 3), "end": round(f1 / FPS, 3), "label": lab["main"], "record": lab.get("record")})
    V.shots(jobs, chrome=a.chrome)
    cards = {}
    for name in {shot_ref(s)[1] for _, s, _, _ in shots if s.startswith("card:")}:
        cards[name] = work / f"card_{name}.png"; V.shots([(card_html(name, nums, a.cut), cards[name])], chrome=a.chrome, opaque=True)
    for i, (sec, shot, t0, t1) in enumerate(shots):
        f0, f1 = round(t0 * FPS), round(t1 * FPS); frames = f1 - f0; kind, src, at = shot_ref(shot); png = work / f"chip_{i:03d}.png"; out = work / "seg" / f"{i:03d}.mp4"
        if kind == "clip":
            path = ROOT / src if src.startswith("docs/") else WEB / src; d = V.probe(path)["dur"]
            V.segment(path, out, frames, at if at is not None else max(0.0, min(d * 0.2, d - frames / FPS - 0.05)), png)
        elif kind == "tab":
            t = tabs[src]; a0 = t["start"] + 0.6 + (at or 0); clean = work / f"tab_{i:03d}.mp4"
            a0 += max(0.0, min(1.2, t["end"] - a0 - frames / FPS - 0.1))      # spend any spare recorded time on letting the page settle, not on its first frames
            V.tour_frames_video(tour, clean, [(a0, min(t["end"], a0 + frames / FPS + 0.2))])
            V.segment(clean, out, frames, 0.0, png)
        elif kind == "phone":
            ptl = json.loads((Path(a.phone_tour) / "timeline.json").read_text()); clean = work / "phone_clean.mp4"
            segs = [(x["start"] + (0.6 if k else 0), x["end"]) for k, x in enumerate(ptl["tabs"])]; V.tour_frames_video(Path(a.phone_tour), clean, segs)
            V.segment(clean, out, frames, 0.0, png)
        else:
            V.frames_to_video(cards[src], out, frames=frames, still=True)
        parts.append(out)
    concat = work / "picture.mp4"; V.concat(parts, concat)
    # captions: one transparent PNG per piece, made into a single alpha track and laid over the picture once
    chunks = caption_chunks([s for sec in timing["sections"] for s in sec["sentences"]]); cj = []
    for k, c in enumerate(chunks): cj.append((caption_html(c["text"]), work / f"cap_{k:03d}.png"))
    V.shots(cj + [("", work / "cap_none.png")], chrome=a.chrome)
    lines, t = [], 0.0
    for k, c in enumerate(chunks):
        if c["start"] > t: lines.append(f"file '{work / 'cap_none.png'}'\nduration {c['start'] - t:.3f}\n")
        lines.append(f"file '{work / f'cap_{k:03d}.png'}'\nduration {c['end'] - c['start']:.3f}\n"); t = c["end"]
    total = timing["seconds"]; lines.append(f"file '{work / 'cap_none.png'}'\nduration {max(0.1, total - t):.3f}\nfile '{work / 'cap_none.png'}'\n")
    (work / "caps.txt").write_text("".join(lines))
    run = V.run
    run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", work / "caps.txt", "-vf", f"fps={FPS},format=rgba", "-t", f"{total:.3f}", "-c:v", "qtrle", work / "caps.mov"])
    run(["ffmpeg", "-y", "-hide_banner", "-i", concat, "-i", work / "caps.mov", "-filter_complex", "[0:v]setsar=1[p];[p][1:v]overlay=0:0,format=yuv420p[v]", "-map", "[v]", "-t", f"{total:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-r", str(FPS), work / "video.mp4"])
    # sound: the narration over the studio's own instrumental bed, ducked under the voice, then levelled
    nar = a.work / "walk" / f"narration_{a.cut}.wav"; bed = work / "bed.wav"; w1, w2 = (V.wav(m, a.work) for m in MUSIC_BED)
    reps = int(total // 36) + 2; inputs = sum([["-i", w1, "-i", w2] for _ in range(reps)], [])
    chain = "".join(f"[{k}:a]" for k in range(2 * reps)); xf = "[0:a]"; g = []
    for k in range(1, 2 * reps): g.append(f"{xf}[{k}:a]acrossfade=d=2.5:c1=tri:c2=tri[x{k}]"); xf = f"[x{k}]"
    run(["ffmpeg", "-y", "-hide_banner", *inputs, "-filter_complex", ";".join(g), "-map", xf, "-t", f"{total:.3f}", bed])
    mix = work / "mix.wav"
    run(["ffmpeg", "-y", "-hide_banner", "-i", nar, "-i", bed, "-filter_complex",
         f"[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,asplit[v][sc];[1:a]aresample=48000,volume=-14dB,afade=t=in:d=1.5,afade=t=out:st={total - 3:.3f}:d=3[b];"
         "[b][sc]sidechaincompress=threshold=0.02:ratio=8:attack=30:release=600[bd];[v][bd]amix=inputs=2:duration=first:normalize=0[m]", "-map", "[m]", mix])
    lv = V.level(mix, work / "music.wav", 0, total, fade_out=0.6, limit=0.75)
    name = "ParametricStudio_Walkthrough" + ("_Short" if a.cut == "short" else ""); master = a.out / f"{name}.mp4"
    web = ROOT / "docs" / "media" / ("walkthrough_short.mp4" if a.cut == "short" else "walkthrough_full_preview.mp4")
    V.mux(work / "video.mp4", work / "music.wav", master, web if a.cut == "short" else None, web_w=1280, web_abr="96k", web_kbps=450, master_crf=21)      # a screen recording at crf 17 runs to 400 MB for ten minutes
    pick = next(e for e in edl if e["shot"] == "clip:showcase/recipes/recast_character.mp4"); poster = ROOT / "docs" / "media" / ("walkthrough_short.webp" if a.cut == "short" else "walkthrough.webp")
    run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{(pick['start'] + pick['end']) / 2:.2f}", "-i", master, "-frames:v", "1", "-vf", "scale=1280:-2:flags=lanczos", "-c:v", "libwebp", "-quality", "78", "-map_metadata", "-1", poster])
    heard = json.loads((a.work / "walk" / f"heard_{a.cut}.json").read_text())
    (DEMOS / f"walkthrough_{a.cut}_edl.json").write_text(json.dumps({"voice": timing["voice"] + " (Apache-2.0), on the CPU", "music": MUSIC_CREDIT, **lv, "seconds": total,
        "whisper": {"model": heard["model"], "wer": heard["wer"], "repeats": len(heard["repeats"])}, "shots": edl, "captions": chunks}, indent=1, ensure_ascii=False) + "\n")
    print(master, V.probe(master)["dur"], lv)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("what", choices=("voice", "plan", "video")); ap.add_argument("--cut", choices=("full", "short"), default="full")
    ap.add_argument("--work", type=Path, required=True); ap.add_argument("--out", type=Path); ap.add_argument("--kokoro", help="folder with config.json, kokoro-v1_0.pth and voices/")
    ap.add_argument("--whisper", help="a faster-whisper model folder"); ap.add_argument("--tour"); ap.add_argument("--phone-tour"); ap.add_argument("--studio", default="http://127.0.0.1:8310"); ap.add_argument("--chrome")
    a = ap.parse_args(argv); a.out = a.out or a.work / "masters"; a.out.mkdir(parents=True, exist_ok=True); (a.work / "walk").mkdir(parents=True, exist_ok=True)
    {"voice": voice, "plan": plan, "video": video}[a.what](a); return 0


if __name__ == "__main__":
    sys.exit(main())
