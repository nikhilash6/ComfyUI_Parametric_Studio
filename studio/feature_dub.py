"""Dub & Voice: say a clip's words in another language, clone a voice you may use, and lay a voiceover on music at a mastered loudness.
Dub: Whisper large-v3 writes down what is said; the local LLM (or you) translates it; then one of three ways to say it:
  dubit  LTX-2.3's DubIt IC-LoRA on LTX-2.5 redraws the mouth and speaks the new line in the speaker's own voice, from the clip's sound as reference (workflows/dub_ltx_api.json);
  voice  Qwen3-TTS reads the line (a stock voice, or a clone of the clip's voice with a yes), fitted to the clip's length and laid on it; the mouth is untouched;
  relip  the same voice, then the Motion page's LatentSync route redraws the mouth, called over HTTP.
Every dub is listened to again by Whisper in the new language, and the word error rate against the line it was given is kept with the result.
Speech models run in their own process (worldkit/runners/dub_steps.py), never inside ComfyUI. Mastering is studio/audio_master.py. What ran on this machine is in dub_proof.json."""
import json, math, os, re, shutil, subprocess, sys, tempfile, threading, time, unicodedata, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths
from studio import audio_master as AM

router = APIRouter(prefix="/api/dub")
PAGE = {"tab": "dub", "label": "Dub & Voice", "title": ["Dub & Voice", "Same face. Another language.", "Whisper writes down what is said, you or the local model translate it, and LTX redraws the mouth to say it. A voiceover is ducked under nothing it shouldn't be and mastered to -14 LUFS. Every number here was measured by a program; no person has listened yet."], "module": "dub.js", "export": "Dub", "css": "dub.css"}
ROOT = Path(__file__).resolve().parent; RUNNERS = ROOT / "worldkit" / "runners"; STEPS = RUNNERS / "dub_steps.py"; LISTEN = RUNNERS / "caption_listen.py"
GRAPH = ROOT.parent / "workflows" / "dub_ltx_api.json"
DUBIT = "ltx/_ic_DubIt/ltx-2.3-22b-ic-lora-dubit-0.9.safetensors"; DUBIT_MIN_BYTES = 1_000_000_000      # the real file is 2.47 GB; anything small is a cache stub
LTX_FILES = ["diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors", "text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors", "vae/ltx-2.5-video-vae-conv-bf16.safetensors", "vae/ltx-2.5-audio-vae-bf16.safetensors"]
LANGS = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ja": "Japanese", "ko": "Korean", "zh": "Chinese"}
SPEAKERS = ("Ryan", "Aiden", "Vivian", "Serena", "Dylan", "Eric")
MODES = ("dubit", "voice", "relip"); CONSENT = ("own", "permission", "synthetic")
DUBIT_PEAK_GIB, TTS_PEAK_GIB = 44.0, 5.5      # TTS: Qwen3-TTS 1.7B measured 4.3-4.9 GiB on this card (Voices page runs)
MAX_SECONDS, FPS, LONGEST = 5.05, 24, 768      # 121 frames, the length DubIt's example graph uses
NEG = "worst quality, inconsistent motion, blurry, jittery, distorted, watermark, text, letters, subtitles, logo, music"
LICENCES = {"dubit": "LTX-2 Community License (DubIt IC-LoRA and LTX-2.5). Generated content must be labelled.", "qwen3": "Apache-2.0 (Qwen3-TTS)", "latentsync": "Code Apache-2.0, weights OpenRAIL++; its face finder (InsightFace buffalo_l) is non-commercial"}
NO_CONSENT = "Cloning copies a voice. Confirm it is your own voice, that you have the speaker's permission, or that it is a made-up (synthetic) voice."
JOBS: dict = {}; _cache: dict = {}


def proof():
    p = ROOT / "dub_proof.json"; mt = p.stat().st_mtime if p.exists() else 0
    if _cache.get("p", (None,))[0] != mt:
        try: _cache["p"] = (mt, json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError): _cache["p"] = (mt, {})
    return _cache["p"][1]


def models_root(): return Path(paths.models_root() or "/nonexistent")


def dubit_state(root=None):
    """'' when DubIt can run here, else what is missing, in words."""
    root = Path(root) if root else models_root(); f = root / "loras" / DUBIT
    try: size = f.stat().st_size
    except OSError: return "needs download: the DubIt IC-LoRA (Lightricks/LTX-2.3-22b-IC-LoRA-DubIt, 2.47 GB, gated: accept its licence on Hugging Face)"
    if size < DUBIT_MIN_BYTES: return f"needs download: only a {size // 1024} KB stub of the DubIt IC-LoRA is here, not the 2.47 GB file"
    gone = [Path(x).name for x in LTX_FILES if not (root / x).is_file()]
    return "needs download: " + ", ".join(gone) if gone else ""


VAE_FORCED = "DubIt keeps the speaker's voice by encoding the clip's sound, and ComfyUI's LTX audio encoder stops with a bf16/float mismatch when the VAE is forced to half precision (this ComfyUI was started with {flag}). Start the ComfyUI used for dubbing with --fp32-vae, or pick 'New voice, then LatentSync'."


def vae_problem(url=None, get=None):
    """'' unless the ComfyUI that would run DubIt forces a half-precision VAE, which breaks the audio encoder (found on this box's ComfyUI 0.43.0, 2026-11-02)."""
    url = (url or Comfy().url).rstrip("/")
    if get is None:
        def get(u):
            with urllib.request.urlopen(u, timeout=3) as r: return json.load(r)
    try: argv = (get(url + "/system_stats").get("system") or {}).get("argv") or []
    except Exception: return ""
    flag = next((f for f in ("--bf16-vae", "--fp16-vae") if f in argv), "")
    return VAE_FORCED.format(flag=flag) if flag else ""


def tts_state(root=None):
    from studio import feature_voices as V
    gone = sorted({f for mid in ("qwen3_custom_17", "qwen3_base_17", "qwen3_design_17") for f in V.missing(V.model(mid), root)})
    return "needs download: " + ", ".join(gone[:3]) if gone else ""


# ---------- words: normalising and the word error rate
def norm_words(text, lang="en"):
    """Lower case, no punctuation; Chinese, Japanese and Korean are compared by character, since they don't put spaces between words."""
    t = unicodedata.normalize("NFKC", str(text or "")).lower()
    t = "".join(ch if (unicodedata.category(ch)[0] in "LN" or ch.isspace()) else " " for ch in t)
    if lang in ("zh", "ja", "ko"): return [ch for ch in t if not ch.isspace()]
    return t.split()


def wer(ref, hyp, lang="en"):
    """Word error rate (character error rate for zh/ja/ko): edits to turn what was heard into what was asked, over the length asked. 0 is perfect."""
    r, h = norm_words(ref, lang), norm_words(hyp, lang)
    if not r: return 0.0 if not h else 1.0
    prev = list(range(len(h) + 1))
    for i, a in enumerate(r, 1):
        cur = [i] + [0] * len(h)
        for j, b in enumerate(h, 1): cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a != b))
        prev = cur
    return round(prev[-1] / len(r), 4)


# ---------- the clip
def clip_path(it):
    from studio import feature_clipsound as CS
    return CS.clip_path(it)


def probe(p, run=subprocess.run):
    from studio import feature_clipsound as CS
    return CS.probe(p, run)


def frames_for(seconds, fps=FPS, cap=MAX_SECONDS):
    """LTX wants 8k+1 frames. The longest whole count that fits the clip, at most `cap` seconds."""
    n = int((min(seconds, cap) * fps - 1) // 8) * 8 + 1
    return max(9, n)


def size_for(w, h, longest=LONGEST, step=32):
    k = longest / max(w, h)
    return max(step, round(w * k / step) * step), max(step, round(h * k / step) * step)


def dub_prompt(text, language, scene=""):
    """DubIt is told the exact words in their own script; it does not translate (its example graph's notes)."""
    scene = " ".join(str(scene or "").split())[:300]
    lead = f"{scene.rstrip('.')}. " if scene else ""
    return (f"{lead}The person speaks {language} to the camera, saying: \"{text}\" The same person, clothes, framing, lighting, camera movement and background as the reference; "
            f"only the mouth and the voice change. Clear speech, no music.")


def graph(values):
    from studio.graph_template import fill
    return fill(json.loads(GRAPH.read_text(encoding="utf-8")), values)


def dub_values(clip_name, info, text, language, scene="", seed=7, strength=1.0):
    w, h = size_for(info.get("width") or 768, info.get("height") or 768); n = frames_for(info.get("seconds") or MAX_SECONDS)
    return {"video": clip_name, "slice_seconds": round(n / FPS + 0.05, 3), "frames": n, "width": w, "height": h, "lora": DUBIT, "strength": float(strength),
            "prompt": dub_prompt(text, language, scene), "negative": NEG, "seed": int(seed)}


# ---------- helpers that run programs
def _py(): return os.environ.get("STUDIO_VOICE_PYTHON") or sys.executable


def _env(): return {**os.environ, "PSN_MODELS_ROOT": paths.models_root() or ""}


def steps(args, run=subprocess.run, timeout=1800):
    """One dub_steps.py call -> its JSON line."""
    r = run([_py(), str(STEPS), *map(str, args)], capture_output=True, text=True, env=_env(), timeout=timeout)
    if r.returncode: raise RuntimeError((r.stderr or r.stdout or "the speech step stopped")[-600:])
    return json.loads((r.stdout or "").strip().splitlines()[-1])


def listen(wav16, out, language="", run=subprocess.run):
    """Whisper large-v3 on a 16 kHz mono file -> its words JSON."""
    from studio import feature_clipsound as CS
    r = run(CS.listen_command("whisper_ct2_large3", wav16, out, language), capture_output=True, text=True, env=_env(), timeout=1800)
    if r.returncode: raise RuntimeError((r.stderr or r.stdout or "Whisper stopped")[-600:])
    heard = json.loads(Path(out).read_text(encoding="utf-8"))
    return {"language": heard.get("language"), "text": " ".join(s.get("text", "") for s in heard.get("segments") or []).strip(), "segments": heard.get("segments") or []}


def to16k(src, dst, run=subprocess.run):
    AM._run([AM.ffmpeg(), "-y", "-hide_banner", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst)], run)
    return Path(dst)


def fit_command(voice, dst, seconds, voice_seconds):
    """Stretch the voice to the clip without changing its pitch (atempo stays inside 0.8-1.25 so it still sounds like speech), then pad or cut to the clip's length."""
    k = min(1.25, max(0.8, voice_seconds / max(0.1, seconds)))
    return [AM.ffmpeg(), "-y", "-hide_banner", "-i", str(voice), "-af", f"atempo={k:.4f},apad,atrim=0:{seconds:.3f}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(dst)], round(k, 4)


def lay_command(clip, audio, dst):
    return [AM.ffmpeg(), "-y", "-hide_banner", "-i", str(clip), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(dst)]


# ---------- translation
def llm_translate(text, to, frm="", endpoint=None, post=None):
    """The local LLM (vLLM, llama-server or Ollama, found by llm_tiers) translates one line, kept near the original's length for lip-sync. None when no LLM is running."""
    from studio import llm_tiers
    ep = (endpoint or llm_tiers.endpoint)()
    if not ep: return None
    msg = (f"Translate this spoken line{' from ' + frm if frm else ''} into {to}. Write it in {to}'s own script. Keep it about as long as the original when spoken, so it fits the same lip movements. "
           f"Reply with the translation only, no quotes or notes.\n\n{text}")
    body = {"model": ep["model"], "messages": [{"role": "user", "content": msg}], "temperature": 0.2, "max_tokens": 400, "chat_template_kwargs": {"enable_thinking": False}}
    if post is None:
        def post(url, data):
            with urllib.request.urlopen(urllib.request.Request(url, json.dumps(data).encode(), {"Content-Type": "application/json"}), timeout=180) as r: return json.load(r)
    out = post(ep["url"].rstrip("/") + "/chat/completions", body)
    t = (out.get("choices") or [{}])[0].get("message", {}).get("content", "")
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip().strip('"“”').strip()
    return {"text": t, "by": ep["model"]}


# ---------- the local ComfyUI
class Comfy:
    """The few calls the DubIt graph needs. Tests pass a fake with the same methods."""
    def __init__(self, url=None): self.url = (url or os.environ.get("DUB_COMFYUI_URL") or os.environ.get("COMFYUI_URL") or "http://127.0.0.1:8200").rstrip("/")

    def upload(self, path):
        p = Path(path); b = uuid.uuid4().hex
        body = f'--{b}\r\nContent-Disposition: form-data; name="image"; filename="{p.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + p.read_bytes() + f'\r\n--{b}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{b}--\r\n'.encode()
        with urllib.request.urlopen(urllib.request.Request(self.url + "/upload/image", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=300) as r: return json.loads(r.read())["name"]

    def run(self, g, timeout=7200):
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url + "/prompt", json.dumps({"prompt": g, "client_id": "dub"}).encode(), {"Content-Type": "application/json"}), timeout=120) as r: pid = json.loads(r.read())["prompt_id"]
        except urllib.error.HTTPError as e: raise RuntimeError("ComfyUI refused the graph: " + e.read().decode(errors="replace")[:600]) from None
        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(2)
            with urllib.request.urlopen(f"{self.url}/history/{pid}", timeout=60) as r: h = json.load(r).get(pid)
            if not h: continue
            st = h.get("status") or {}
            if st.get("status_str") == "error":
                raise RuntimeError("ComfyUI stopped: " + next((i.get("exception_message", "") for k, i in st.get("messages", []) if k == "execution_error"), "").strip()[:500])
            if st.get("completed"): return h
        self.cancel(); raise RuntimeError(f"timed out after {timeout} s")

    def cancel(self):
        try: urllib.request.urlopen(urllib.request.Request(self.url + "/interrupt", b"{}", {"Content-Type": "application/json"}), timeout=10)
        except Exception: pass

    def fetch(self, item, dest):
        q = urllib.parse.urlencode({"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": item.get("type", "output")})
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"{self.url}/view?{q}", timeout=300) as r: Path(dest).write_bytes(r.read())
        return Path(dest)


def video_output(history, node="save"):
    o = (history.get("outputs") or {}).get(node) or {}
    items = o.get("images") or o.get("videos") or o.get("gifs") or []
    if not items: raise RuntimeError("the graph finished with no video")
    return items[0]


# ---------- Motion over HTTP
def studio_url(): return (os.environ.get("STUDIO_SELF_URL") or f"http://127.0.0.1:{os.environ.get('STUDIO_PORT', '8322')}").rstrip("/")


def motion_relip(video_name, audio_name, seed=1247, base=None, get=None, post=None, wait_s=3600):
    """LatentSync through the Motion page's own route: the same checks, mark and receipt. Both files must be in the studio's input folder. -> the result's path under the output folder."""
    base = base or studio_url()
    if post is None:
        def post(url, data):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, json.dumps(data).encode(), {"Content-Type": "application/json"}), timeout=60) as r: return json.load(r)
            except urllib.error.HTTPError as e: raise RuntimeError("Motion refused: " + e.read().decode(errors="replace")[:400]) from None
    if get is None:
        def get(url):
            with urllib.request.urlopen(url, timeout=60) as r: return json.load(r)
    job = post(base + "/api/motion/run", {"route": "latentsync", "video": video_name, "audio": audio_name, "seed": seed, "permission": True})["job"]; t0 = time.time()
    while time.time() - t0 < wait_s:
        rec = get(f"{base}/api/motion/jobs/{job}")
        if rec.get("status") == "done": return rec["file"]
        if rec.get("status") == "error": raise RuntimeError("LatentSync: " + str(rec.get("error"))[:500])
        time.sleep(3)
    raise RuntimeError("LatentSync took too long")


# ---------- jobs
def _out_dir(): d = Path(paths.output_dir(True)) / "dub"; d.mkdir(parents=True, exist_ok=True); return d


def _view(p):
    rel = Path(p).resolve().relative_to(Path(paths.output_dir(True)).resolve()).as_posix(); sub, name = os.path.split(rel)
    return {"filename": name, "subfolder": sub, "type": "output", "url": "/api/view?" + urllib.parse.urlencode({"filename": name, "subfolder": sub, "type": "output"})}


def _consent_file(out, consent, reference, model, extra=None):
    """Beside a cloned voice: whose voice it is said to be, the yes given, and a hash of the clip it was cloned from."""
    from studio import likeness
    rec = {"consent": consent, "meaning": {"own": "the user said it is their own voice", "permission": "the user said the speaker gave permission", "synthetic": "the reference voice was itself made by a model, so no real person's voice is copied"}[consent],
           "reference_sha256": likeness._hash(reference) if reference and os.path.isfile(reference) else None, "model": model, "made": time.strftime("%Y-%m-%d %H:%M:%S"), "ai_generated": True, **(extra or {})}
    p = Path(str(out) + ".consent.json"); p.write_text(json.dumps(rec, indent=1), encoding="utf-8"); return p


def transcribe_job(rec, clip, run=subprocess.run):
    try:
        with tempfile.TemporaryDirectory() as td:
            rec["step"] = "Whisper is listening"; wav = to16k(clip, Path(td) / "a.wav", run)
            heard = listen(wav, Path(td) / "w.json", "", run)
            out = {"transcript": heard["text"], "language": heard["language"], "segments": [{k: s.get(k) for k in ("start", "end", "text")} for s in heard["segments"]]}
            if rec.get("english"):
                rec["step"] = "Whisper is translating into English"; tr = steps(["translate", "--audio", wav, "--out", Path(td) / "t.json"], run)
                out["english"] = json.loads((Path(td) / "t.json").read_text(encoding="utf-8")).get("text") if tr else ""
        rec.update(status="done", step="", **out)
    except Exception as e: rec.update(status="error", step="", error=f"{e}"[:700])


def speak_line(text, language, out, voice=None, clone_from=None, clone_text="", consent=None, run=subprocess.run):
    """Qwen3-TTS reads the line: a stock speaker, or a clone of clone_from (a yes is required)."""
    if clone_from:
        if consent not in CONSENT: raise HTTPException(400, NO_CONSENT)
        return steps(["speak", "--model", "qwen3_base_17", "--language", language, "--text", text, "--out", out, "--reference", clone_from, "--reference-consent", consent] + (["--reference-text", clone_text] if clone_text else []), run)
    return steps(["speak", "--model", "qwen3_custom_17", "--language", language, "--text", text, "--out", out, "--voice", voice or SPEAKERS[0]], run)


def check_dub(dubbed, text, lang, td, run=subprocess.run):
    """Whisper hears the dub in the new language; -> {heard, wer}."""
    wav = to16k(dubbed, Path(td) / "check.wav", run); heard = listen(wav, Path(td) / "check.json", lang, run)
    return {"heard": heard["text"], "heard_language": heard["language"], "wer": wer(text, heard["text"], lang)}


def dub_job(rec, clip, opts, run=subprocess.run, comfy=None, mark=None, relip=motion_relip):
    """Clip + translated line -> a dubbed clip, marked AI-generated, with a receipt and the WER of what Whisper hears in it. Fills rec; never raises."""
    from studio import likeness
    mark = mark or likeness.mark; t0 = time.time(); lang = opts["language"]; L = LANGS[lang]
    try:
        info = rec["clip_info"]; out_dir = _out_dir(); stem = re.sub(r"[^\w-]+", "_", clip.stem)[:40] + f"_{lang}_{rec['job'][-6:]}"
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            if opts["mode"] == "dubit":
                rec["step"] = "LTX is redrawing the mouth and voice"; c = comfy or Comfy(); name = c.upload(clip)
                h = c.run(graph(dub_values(name, info, opts["text"], L, opts.get("scene", ""), opts["seed"], opts.get("strength", 1.0))))
                raw = c.fetch(video_output(h), td / "raw.mp4"); model, licence = "LTX-2.5 distilled + LTX-2.3 DubIt IC-LoRA 0.9", LICENCES["dubit"]
            else:
                rec["step"] = "Qwen3-TTS is reading the line"; voice = td / "tts.wav"; ref = None
                if opts["voice"] == "clone":
                    ref = td / "ref.wav"; AM._run([AM.ffmpeg(), "-y", "-hide_banner", "-i", str(clip), "-vn", "-ac", "1", "-ar", "24000", str(ref)], run)
                said = speak_line(opts["text"], L, voice, opts["voice"], ref, opts.get("source_text", ""), opts.get("consent"), run)
                fitted = td / "fit.wav"; cmd, k = fit_command(voice, fitted, info["seconds"], said.get("seconds") or info["seconds"]); AM._run(cmd, run); rec["tempo"] = k
                raw = td / "laid.mp4"; AM._run(lay_command(clip, fitted, raw), run); model, licence = "Qwen3-TTS 1.7B " + ("Base (clone)" if ref else "CustomVoice"), LICENCES["qwen3"]
                if opts["mode"] == "relip":
                    rec["step"] = "LatentSync is redrawing the mouth (Motion page)"; inp = Path(paths.comfy_input(True)); inp.mkdir(parents=True, exist_ok=True)
                    vn, an = f"dub_{rec['job']}.mp4", f"dub_{rec['job']}.wav"; shutil.copy(clip, inp / vn); shutil.copy(fitted, inp / an)
                    raw = Path(paths.output_dir(True)) / relip(vn, an); model += " + LatentSync 1.6"; licence += "; " + LICENCES["latentsync"]
            out = out_dir / f"{stem}.mp4"
            if opts["mode"] == "relip": shutil.copy(raw, out)        # Motion already marked it
            else: mark(raw, out)
            rec["step"] = "Whisper is checking the dub"; chk = check_dub(out, opts["text"], lang, td, run)
            if opts["mode"] != "dubit" and opts["voice"] == "clone": _consent_file(out, opts["consent"], str(clip), model, {"source": clip.name})
        route = {"id": f"dub_{opts['mode']}", "model": model, "licence": licence, "commercial": "conditional" if opts["mode"] == "relip" else True}
        likeness.receipt(out, route, {"permission": opts.get("permission") is True}, {"video": clip}, seed=opts["seed"], seconds=round(time.time() - t0, 1))
        rec.update(status="done", step="", file=_view(out), model=model, licence=licence, seconds=round(time.time() - t0, 1), **chk)
    except Exception as e: rec.update(status="error", step="", error=f"{e}"[:900])


def clone_job(rec, opts, run=subprocess.run):
    """A voice you may use: your own clip (with a yes) or a voice designed from words. Reads the line in it, stores the yes beside the file, and scores how alike the two voices are."""
    t0 = time.time()
    try:
        out_dir = _out_dir() / "voices"; out_dir.mkdir(parents=True, exist_ok=True); stem = f"clone_{rec['job'][-8:]}"; L = LANGS[opts["language"]]
        ref, ref_text, consent = opts.get("reference"), opts.get("reference_text", ""), opts["consent"]
        if opts.get("design"):
            rec["step"] = "Qwen3-TTS is designing the voice"; ref = str(out_dir / f"{stem}_designed.wav"); ref_text = opts["design_line"]
            steps(["speak", "--model", "qwen3_design_17", "--language", L, "--text", ref_text, "--out", ref, "--voice", opts["design"]], run); consent = "synthetic"
        rec["step"] = "Qwen3-TTS is cloning"; out = out_dir / f"{stem}.wav"
        said = steps(["speak", "--model", "qwen3_base_17", "--language", L, "--text", opts["text"], "--out", out, "--reference", ref, "--reference-consent", consent] + (["--reference-text", ref_text] if ref_text else []), run)
        _consent_file(out, consent, ref, "Qwen3-TTS 1.7B Base", {"designed_from": opts.get("design") or None})
        rec["step"] = "measuring how alike the voices are"
        try: sim = steps(["similar", "--a", ref, "--b", out], run)
        except Exception as e: sim = {"cosine": None, "error": f"{e}"[:200]}
        files = {"voice": _view(out), "consent": _view(str(out) + ".consent.json")}
        if opts.get("design"): files["reference"] = _view(ref)
        rec.update(status="done", step="", files=files, seconds=round(time.time() - t0, 1), voice_seconds=said.get("seconds"), similarity=sim, consent=consent)
    except Exception as e: rec.update(status="error", step="", error=f"{e}"[:900])


def voiceover_job(rec, opts, run=subprocess.run):
    t0 = time.time()
    try:
        out_dir = _out_dir() / "voiceover"; out_dir.mkdir(parents=True, exist_ok=True); stem = f"vo_{rec['job'][-8:]}"; voice = opts.get("voice_file")
        if not voice:
            rec["step"] = "Qwen3-TTS is reading the script"; voice = str(out_dir / f"{stem}_voice.wav")
            steps(["speak", "--model", "qwen3_custom_17", "--language", LANGS[opts["language"]], "--text", opts["text"], "--out", voice, "--voice", opts["speaker"]], run)
        rec["step"] = "ducking the music and mastering"; out = out_dir / f"{stem}.wav"
        rep = AM.voiceover(voice, opts["music"], out, target=opts["lufs"], tp=opts["tp"], depth=opts["depth"], run=run)
        m4a = out.with_suffix(".m4a"); AM._run([AM.ffmpeg(), "-y", "-hide_banner", "-i", str(out), "-c:a", "aac", "-b:a", "256k", "-metadata", "comment=AI-generated voice. Made with Parametric Studio.", str(m4a)], run)
        rec.update(status="done", step="", files={"wav": _view(out), "m4a": _view(m4a)}, report=rep, seconds=round(time.time() - t0, 1))
    except Exception as e: rec.update(status="error", step="", error=f"{e}"[:900])


def _start(kind, target, *args, **extra):
    jid = f"dub-{kind}-" + uuid.uuid4().hex[:10]; rec = {"job": jid, "kind": kind, "status": "running", "step": "starting", "started": time.time(), **extra}; JOBS[jid] = rec
    threading.Thread(target=target, args=(rec, *args), daemon=True, name=jid).start(); return rec


def _lang(v):
    v = str(v or "").strip().lower()
    if v not in LANGS: raise HTTPException(400, "pick one of the listed languages")
    return v


def _input_file(name, what="clip"):
    root = Path(paths.comfy_input(True)).resolve(); p = (root / os.path.basename(str(name or ""))).resolve()
    if not name or root not in p.parents or not p.is_file(): raise HTTPException(400, f"That {what} isn't in the input folder. Upload it first.")
    return p


def _audio_file(it):
    """A music or voice file the page named: in the input or output folder, by name."""
    if isinstance(it, str): return _input_file(it, "audio file")
    if not isinstance(it, dict) or not it.get("filename"): raise HTTPException(400, "pick an audio file")
    root = Path(paths.comfy_input(True) if it.get("type") == "input" else paths.output_dir(True)).resolve(); p = (root / str(it.get("subfolder") or "") / it["filename"]).resolve()
    if root not in p.parents or not p.is_file(): raise HTTPException(404, f"no such file: {it['filename']}")
    if not re.search(r"\.(wav|mp3|m4a|flac|ogg|aac)$", p.name, re.I): raise HTTPException(400, "pick an audio file: wav, mp3, m4a, flac, ogg or aac")
    return p


# ---------- routes
@router.get("/models")
def models_get():
    llm = None
    try:
        from studio import llm_tiers
        ep = llm_tiers.endpoint(); llm = ep and ep["model"]
    except Exception: pass
    dw = dubit_state() or vae_problem()
    return {"languages": LANGS, "speakers": list(SPEAKERS), "modes": list(MODES), "max_seconds": MAX_SECONDS, "dubit": {"ready": not dw, "why_not": dw, "licence": LICENCES["dubit"]},
            "tts": {"ready": not tts_state(), "why_not": tts_state(), "licence": LICENCES["qwen3"]}, "llm": llm, "master": {"lufs": AM.TARGET_LUFS, "tp": AM.TARGET_TP, "depth": AM.DEPTH_DB}, "proof": proof()}


@router.get("/clips")
def clips(limit: int = 40):
    from studio import feature_clipsound as CS
    return CS.clips(limit)


@router.get("/audio")
def audio_list(limit: int = 40):
    """The newest audio files in the output folder (music renders, voices), for the voiceover's pickers."""
    root = Path(paths.output_dir(True)); rows = []
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_file() and re.search(r"\.(wav|mp3|m4a|flac|ogg)$", p.name, re.I): rows.append((p.stat().st_mtime, p))
    rows.sort(key=lambda x: -x[0])
    return {"audio": [{"filename": p.name, "subfolder": "" if p.parent == root else p.parent.relative_to(root).as_posix(), "type": "output"} for _, p in rows[:max(1, min(200, limit))]]}


@router.post("/transcribe")
def transcribe(b: dict = None):
    """What the clip says and in which language (Whisper large-v3). english: true also asks Whisper for its own English translation."""
    b = b or {}; clip = clip_path(b.get("clip")); info = probe(clip)
    if not info["audio"]: raise HTTPException(400, f"{clip.name} has no sound track, so there are no words to dub.")
    return _start("listen", transcribe_job, clip, clip=clip.name, english=bool(b.get("english")))


@router.post("/translate")
def translate(b: dict = None):
    b = b or {}; text = " ".join(str(b.get("text") or "").split())[:1200]; to = LANGS[_lang(b.get("to"))]
    if not text: raise HTTPException(400, "nothing to translate")
    from studio import sfw
    sfw.check(text)
    try: got = llm_translate(text, to, LANGS.get(str(b.get("from") or "").lower(), ""))
    except (urllib.error.URLError, OSError, ValueError) as e: raise HTTPException(503, f"the local LLM didn't answer: {e}") from None
    if not got: raise HTTPException(503, "No local LLM is running. Type the translation yourself, or ask Whisper for English.")
    return got


@router.post("/run")
def run_dub(b: dict = None):
    """Dub one clip. Poll /api/dub/jobs/{job}."""
    from studio import likeness, sfw
    b = b or {}; mode = str(b.get("mode") or "dubit")
    if mode not in MODES: raise HTTPException(400, "mode is dubit, voice or relip")
    lang = _lang(b.get("language")); text = " ".join(str(b.get("text") or "").split())[:600]
    if not text: raise HTTPException(400, "Write the line in the new language first.")
    scene = " ".join(str(b.get("scene") or "").split())[:300]; sfw.check(text, scene)
    voice = str(b.get("voice") or SPEAKERS[0])
    if mode != "dubit" and voice != "clone" and voice not in SPEAKERS: raise HTTPException(400, "pick one of the listed voices, or clone")
    consent = str(b.get("consent") or "")
    if mode != "dubit" and voice == "clone" and consent not in CONSENT: raise HTTPException(400, NO_CONSENT)
    why = (dubit_state() or vae_problem()) if mode == "dubit" else tts_state()
    if why: raise HTTPException(409, why)
    clip = clip_path(b.get("clip")); info = probe(clip)
    if mode == "dubit" and not info["audio"]: raise HTTPException(400, "DubIt keeps the speaker's voice from the clip's sound, and this clip has none.")
    likeness.guard({"person": True}, {**b, "text": text}, {"video": clip})
    opts = {"mode": mode, "language": lang, "text": text, "scene": scene, "voice": voice, "consent": consent, "seed": max(0, min(2**31, int(b.get("seed") or 7))),
            "strength": max(0.5, min(1.5, float(b.get("strength") or 1.0))), "source_text": str(b.get("source_text") or "")[:600], "permission": b.get("permission") is True}
    return _start("dub", dub_job, clip, opts, clip=clip.name, clip_info=info, options=opts)


@router.post("/clone")
def clone(b: dict = None):
    """Clone a voice: your own uploaded clip with a yes, or a voice designed from a description (synthetic, so no real person is copied)."""
    from studio import sfw
    b = b or {}; lang = _lang(b.get("language") or "en"); text = " ".join(str(b.get("text") or "").split())[:600]
    if not text: raise HTTPException(400, "Write a line for the cloned voice to read.")
    design = " ".join(str(b.get("design") or "").split())[:300]; sfw.check(text, design)
    if tts_state(): raise HTTPException(409, tts_state())
    opts = {"language": lang, "text": text}
    if design: opts.update(design=design, design_line=str(b.get("design_line") or "Every morning the baker opens the blue door and sweeps the step before the street wakes up.")[:300], consent="synthetic")
    else:
        if str(b.get("consent") or "") not in ("own", "permission"): raise HTTPException(400, "Confirm the clip is your own voice, or that the speaker gave permission. Without that, design a voice instead.")
        opts.update(reference=str(_input_file(b.get("reference"), "voice clip")), reference_text=str(b.get("reference_text") or "")[:600], consent=str(b["consent"]))
    return _start("clone", clone_job, opts, options={k: v for k, v in opts.items() if k != "reference"})


@router.post("/voiceover")
def voiceover(b: dict = None):
    """A voice (a file, or a script read by Qwen3-TTS) over music: ducked while it speaks, mixed and mastered."""
    from studio import sfw
    b = b or {}; music = _audio_file(b.get("music")); lang = _lang(b.get("language") or "en")
    opts = {"music": str(music), "language": lang, "lufs": max(-24.0, min(-9.0, float(b.get("lufs") or AM.TARGET_LUFS))), "tp": max(-3.0, min(-0.5, float(b.get("tp") or AM.TARGET_TP))),
            "depth": max(8.0, min(24.0, float(b.get("depth") or AM.DEPTH_DB))), "speaker": str(b.get("speaker") or SPEAKERS[0])}
    if b.get("voice_file"): opts["voice_file"] = str(_audio_file(b["voice_file"]))
    else:
        text = " ".join(str(b.get("text") or "").split())[:1500]
        if not text: raise HTTPException(400, "Write the script, or pick a voice file.")
        sfw.check(text)
        if opts["speaker"] not in SPEAKERS: raise HTTPException(400, "pick one of the listed voices")
        if tts_state(): raise HTTPException(409, tts_state())
        opts["text"] = text
    return _start("voiceover", voiceover_job, opts, options={k: v for k, v in opts.items() if k not in ("music", "voice_file")})


@router.get("/jobs/{jid}")
def job_get(jid: str):
    r = JOBS.get(jid)
    if not r: raise HTTPException(404, "no such job")
    return r
