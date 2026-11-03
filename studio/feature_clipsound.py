"""Captions & Sound: speech captions for any clip, as SRT and WebVTT files and, if asked, drawn onto a copy of the clip; and sound for a silent clip from ControlFoley.
Whisper runs in its own process (studio/worldkit/runners/caption_listen.py), on the CPU unless STUDIO_CAPTION_DEVICE=cuda, so it never touches a running graph.
The words on screen are set by ffmpeg and libass from a font, not painted by a model. Clips come only from the studio's input and output folders.
What each model is and its licence come from voice_models.json, the Voices page's catalogue; what ran here is in clipsound_proof.json.
Add sound runs ControlFoley as a ComfyUI graph (workflows/clipsound_foley_api.json). Its weights are non-commercial, so a run is refused unless the person says the result is for non-commercial use (studio/foley.py)."""
import json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths
from studio import captions as C, foley as FO
from studio.graph_template import fill, placeholders

router = APIRouter(prefix="/api/clipsound")
PAGE = {"tab": "clipsound", "label": "Captions & Sound", "title": ["Captions & Sound", "Your clip. Its words on screen, and sound for a silent one.", "Whisper writes down what is said, and ffmpeg sets it in a real font, so the letters are never a model's guess. ControlFoley watches a silent clip and makes sound for it, for non-commercial use. Every result here was measured by a program. No person has listened yet."], "module": "clipsound.js", "export": "ClipSound", "css": "clipsound.css"}
ROOT = Path(__file__).resolve().parent; WF = ROOT.parent / "workflows"; RUNNER = ROOT / "worldkit" / "runners" / "caption_listen.py"
LISTENERS = ("whisper_ct2_distil", "whisper_ct2_large3", "whisper_ct2_tiny")
VIDEO = re.compile(r"\.(mp4|webm|mov|mkv)$", re.I)
MAX_SECONDS = 15 * 60; JOBS: dict = {}; _cache: dict = {}


def _read(name):
    p = ROOT / name; mt = p.stat().st_mtime if p.exists() else 0
    if _cache.get(name, (None,))[0] != mt:
        try: _cache[name] = (mt, json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError): _cache[name] = (mt, {})
    return _cache[name][1]


def proof(): return _read("clipsound_proof.json")


def listeners(root=None):
    """The Whisper models captions can use, with the Voices page's licence and card, and whether their weights are here."""
    from studio import feature_voices as V
    by = {m["id"]: m for m in V.catalogue().get("models") or []}
    out = []
    for i in LISTENERS:
        m = by.get(i)
        if not m: continue
        gone = V.missing(m, root)
        out.append({"id": i, "label": m["label"], "maker": m["maker"], "licence": m.get("licence"), "card": m.get("card"), "english_only": i == "whisper_ct2_distil", "ready": not gone, "missing": gone})
    return out


def _root(kind):
    if kind == "input": return Path(paths.comfy_input(True)).resolve()
    if kind == "output": return Path(paths.output_dir(True)).resolve()
    raise HTTPException(400, "a clip must come from the studio's input or output folder")


def clip_path(it):
    """A clip the page named, only inside the input or output folder."""
    if not isinstance(it, dict) or not isinstance(it.get("filename"), str) or not it["filename"]: raise HTTPException(400, "pick a clip first")
    root = _root(it.get("type") or "output"); p = (root / str(it.get("subfolder") or "") / it["filename"]).resolve()
    if root not in p.parents or not p.is_file(): raise HTTPException(404, f"no such clip: {it['filename']}")
    if not VIDEO.search(p.name): raise HTTPException(400, "captions go on a video clip: mp4, webm, mov or mkv")
    return p


def probe(p, run=subprocess.run):
    """{seconds, width, height, audio} from ffprobe. audio is the first audio codec, or None."""
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height", "-of", "json", str(p)], capture_output=True, text=True, timeout=30)
    try: d = json.loads(r.stdout or "{}")
    except ValueError: d = {}
    ss = d.get("streams") or []; v = next((s for s in ss if s.get("codec_type") == "video"), None); a = next((s for s in ss if s.get("codec_type") == "audio"), None)
    if not v: raise HTTPException(400, f"{p.name} isn't a readable video")
    try: secs = float((d.get("format") or {}).get("duration") or 0)
    except ValueError: secs = 0.0
    return {"seconds": round(secs, 3), "width": v.get("width"), "height": v.get("height"), "audio": a and a.get("codec_name")}


def _view(rel):
    sub, name = os.path.split(rel)
    return {"filename": name, "subfolder": sub, "type": "output", "url": "/api/view?" + urllib.parse.urlencode({"filename": name, "subfolder": sub, "type": "output"})}


def _ffmpeg(): return shutil.which("ffmpeg") or str(Path.home() / ".local" / "bin" / "ffmpeg")


def listen_command(model, wav, out, language=""):
    cmd = [os.environ.get("STUDIO_CAPTION_PYTHON") or os.environ.get("STUDIO_VOICE_PYTHON") or sys.executable, str(RUNNER), "--audio", str(wav), "--out", str(out), "--model", model,
           "--device", "cuda" if os.environ.get("STUDIO_CAPTION_DEVICE") == "cuda" else "cpu"]
    return cmd + (["--language", language] if language else [])


def caption_job(rec, clip, opts, run=subprocess.run):
    """Clip -> audio -> Whisper -> cues -> SRT, VTT and, if asked, a burned copy. Fills rec as it goes; never raises."""
    t0 = time.time()
    try:
        info = rec["clip_info"]; out_dir = Path(paths.output_dir(True)) / "captions"; out_dir.mkdir(parents=True, exist_ok=True)
        stem = re.sub(r"[^\w-]+", "_", clip.stem)[:48] + "_" + rec["job"][-6:]
        with tempfile.TemporaryDirectory() as td:
            wav, words = Path(td) / "speech.wav", Path(td) / "words.json"
            rec["step"] = "taking the sound out of the clip"
            r = run(C.audio_command(_ffmpeg(), clip, wav), capture_output=True, text=True, timeout=600)
            if r.returncode: raise RuntimeError("ffmpeg couldn't read the sound: " + (r.stderr or "")[-300:])
            rec["step"] = "Whisper is listening"
            env = {**os.environ, "PSN_MODELS_ROOT": paths.models_root() or ""}
            r = run(listen_command(opts["model"], wav, words, opts["language"]), capture_output=True, text=True, env=env, timeout=1800)
            if r.returncode: raise RuntimeError((r.stderr or r.stdout or "Whisper stopped")[-600:])
            heard = json.loads(words.read_text(encoding="utf-8"))
            kept, dropped = C.split_kept(heard.get("segments"))
            pt, chars = C.layout(info.get("width"), info.get("height"), opts["size"]); cs = C.cues(kept, width=chars)
            (out_dir / f"{stem}.srt").write_text(C.srt(cs), encoding="utf-8"); (out_dir / f"{stem}.vtt").write_text(C.vtt(cs), encoding="utf-8")
            (out_dir / f"{stem}.words.json").write_text(json.dumps(heard, ensure_ascii=False), encoding="utf-8")
            files = {"srt": _view(f"captions/{stem}.srt"), "vtt": _view(f"captions/{stem}.vtt"), "words": _view(f"captions/{stem}.words.json")}
            if opts["burn"] and cs:
                rec["step"] = "drawing the captions onto a copy"
                shutil.copy(out_dir / f"{stem}.srt", Path(td) / "c.srt"); dest = out_dir / f"{stem}_captioned.mp4"
                r = run(C.burn_command(_ffmpeg(), clip, "c.srt", dest, opts["style"], pt, opts["place"]), capture_output=True, text=True, timeout=1800, cwd=td)
                if r.returncode: r = run(C.burn_command(_ffmpeg(), clip, "c.srt", dest, opts["style"], pt, opts["place"], copy_audio=False), capture_output=True, text=True, timeout=1800, cwd=td)
                if r.returncode: raise RuntimeError("ffmpeg couldn't draw the captions: " + (r.stderr or "")[-300:])
                files["video"] = _view(f"captions/{stem}_captioned.mp4")
        rec.update(status="done", step="", files=files, cues=cs, dropped=dropped, text=C.transcript(cs), language=heard.get("language"), speech_seconds=heard.get("speech_seconds"),
                   whisper_s=heard.get("wall_s"), seconds=round(time.time() - t0, 1), note="" if cs else "Whisper heard no speech in this clip, so there are no captions to draw.")
    except Exception as e: rec.update(status="error", step="", error=f"{e}"[:700])


def options(b):
    """The request, checked. Unknown style words are refused here rather than reaching ffmpeg."""
    model = str(b.get("model") or LISTENERS[0])
    if model not in LISTENERS: raise HTTPException(400, "pick one of the Whisper models listed")
    lang = str(b.get("language") or "").strip().lower()
    if lang and not re.fullmatch(r"[a-z]{2,3}", lang): raise HTTPException(400, "a language is a two- or three-letter code, like en or es")
    style, size, place = str(b.get("style") or "outline"), str(b.get("size") or "medium"), str(b.get("place") or "bottom")
    if style not in C.STYLES or size not in C.SIZES or place not in C.PLACES: raise HTTPException(400, "unknown caption style, size or place")
    return {"model": model, "language": lang, "burn": bool(b.get("burn")), "style": style, "size": size, "place": place}


def sounders(root=None, comfy=None, hub=None):
    """The sound models, each with every licence it carries and what this machine lacks to run it."""
    gone = FO.missing(root, comfy, hub)
    return [{**m, "ready": not gone, "missing": gone, "steps": list(FO.STEPS), "max_seconds": FO.MAX_SECONDS} for m in FO.MODELS]


@router.get("/models")
def models_get(): return {"listeners": listeners(), "sounders": sounders(), "styles": list(C.STYLES), "sizes": list(C.SIZES), "places": list(C.PLACES), "proof": proof()}


@router.get("/clips")
def clips(limit: int = 40):
    """The newest video clips in the output folder, for the picker. Whether each has sound is checked when it is picked."""
    root = Path(paths.output_dir(True)); rows = []
    if root.is_dir():
        for p in root.rglob("*"):
            if VIDEO.search(p.name) and p.is_file() and "captions" not in p.relative_to(root).parts[:1]:
                rows.append((p.stat().st_mtime, p))
    rows.sort(key=lambda x: -x[0])
    return {"clips": [{"filename": p.name, "subfolder": "" if p.parent == root else p.parent.relative_to(root).as_posix(), "type": "output"} for _, p in rows[:max(1, min(200, limit))]]}


@router.post("/captions")
def captions_run(b: dict = None):
    """Caption one clip. Runs in the background: poll /api/clipsound/jobs/{job}."""
    b = b or {}; opts = options(b); clip = clip_path(b.get("clip"))
    m = next((x for x in listeners() if x["id"] == opts["model"]), None)
    if not m or not m["ready"]: raise HTTPException(409, f"{opts['model']} needs files this machine doesn't have: " + ", ".join((m or {}).get("missing", [])[:3]))
    if opts["language"] and m["english_only"] and opts["language"] != "en": raise HTTPException(400, f"{m['label']} only hears English. Pick large-v3 for other languages.")
    info = probe(clip)
    if not info["audio"]: raise HTTPException(400, f"{clip.name} has no sound track, so there are no words to caption.")
    if info["seconds"] > MAX_SECONDS: raise HTTPException(400, f"{clip.name} is over {MAX_SECONDS // 60} minutes. Cut it shorter first.")
    jid = "cap-" + uuid.uuid4().hex[:10]
    rec = {"job": jid, "kind": "captions", "status": "running", "step": "starting", "started": time.time(), "clip": clip.name, "clip_info": info, "options": opts}; JOBS[jid] = rec
    threading.Thread(target=caption_job, args=(rec, clip, opts), daemon=True, name=jid).start(); return rec


@router.get("/jobs/{jid}")
def job_get(jid: str):
    r = JOBS.get(jid)
    if not r: raise HTTPException(404, "no such job")
    return r


# ---------- add sound (ControlFoley)
def comfy_url(): return os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/")


def _comfy(path, payload=None, timeout=30):
    req = urllib.request.Request(comfy_url() + path, data=json.dumps(payload).encode() if payload is not None else None, headers={"Content-Type": "application/json"} if payload is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read() or b"{}")


def sound_graph(clip, seconds, opts, prefix, root=None):
    tpl = json.loads((WF / FO.GRAPH).read_text(encoding="utf-8")); v = FO.graph_values(clip, seconds, opts, prefix, root)
    miss = placeholders(tpl) - set(v)
    if miss: raise RuntimeError(f"graph needs {sorted(miss)}")
    return fill(tpl, v)


def _wait(pid, comfy=None, sleep=time.sleep, limit=3600):
    """Poll ComfyUI's history until the prompt is done. -> its history entry. Raises with ComfyUI's own message on failure."""
    comfy = comfy or _comfy; t0 = time.time()
    while time.time() - t0 < limit:
        h = (comfy(f"/history/{urllib.parse.quote(pid)}") or {}).get(pid)
        st = (h or {}).get("status") or {}
        if st.get("status_str") == "error":
            msg = next((i.get("exception_message", "") for k, i in st.get("messages", []) if k == "execution_error"), "")
            raise RuntimeError("ControlFoley failed: " + (msg.strip()[:500] or "the graph stopped"))
        if h and (st.get("completed") or st.get("status_str") == "success"): return h
        sleep(2)
    raise RuntimeError("ControlFoley took over an hour; the job was left in ComfyUI's queue")


def saved_wav(hist):
    """The WAV the save node wrote, as a path in the output folder."""
    for it in ((hist.get("outputs") or {}).get("save") or {}).get("audio") or []:
        if isinstance(it, dict) and it.get("filename", "").endswith(".wav") and it.get("type") == "output":
            return Path(paths.output_dir(True)) / (it.get("subfolder") or "") / it["filename"]
    raise RuntimeError("ControlFoley finished but saved no sound")


def sound_job(rec, clip, opts, run=subprocess.run, comfy=None, sleep=time.sleep):
    """Clip -> ControlFoley in ComfyUI -> WAV -> the clip with that sound, picture copied -> loudness. Fills rec; never raises."""
    t0 = time.time(); comfy = comfy or _comfy
    try:
        stem = re.sub(r"[^\w-]+", "_", clip.stem)[:48] + "_" + rec["job"][-6:]; prefix = f"clipsound/{stem}_sound"
        rec["step"] = "ControlFoley is loading and watching the clip"
        try: res = comfy("/prompt", {"prompt": sound_graph(clip, rec["clip_info"]["seconds"], opts, prefix), "client_id": "studio-clipsound"})
        except urllib.error.HTTPError as e:
            try: why = json.loads(e.read() or b"{}").get("error", {}).get("message", "")
            except Exception: why = ""
            raise RuntimeError(f"ComfyUI rejected the graph: {why}"[:400]) from None
        rec["prompt_id"] = res["prompt_id"]; hist = _wait(res["prompt_id"], comfy, sleep); wav = saved_wav(hist)
        rec["step"] = "putting the sound on the clip"; out_dir = Path(paths.output_dir(True)) / "clipsound"; out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{stem}_with_sound.mp4"
        secs_ = rec["clip_info"]["seconds"]
        r = run(FO.level_measure_command(_ffmpeg(), wav, secs_), capture_output=True, text=True, timeout=600); level = FO.parse_level(r.stderr or "")
        r = run(FO.mux_command(_ffmpeg(), clip, wav, dest, secs_, level), capture_output=True, text=True, timeout=600)
        if r.returncode: raise RuntimeError("ffmpeg couldn't put the sound on the clip: " + (r.stderr or "")[-300:])
        r = run(FO.loudness_command(_ffmpeg(), dest), capture_output=True, text=True, timeout=600); loud = FO.parse_loudness(r.stderr or "")      # what the clip plays, after levelling
        raw = {"lufs": level["input_i"], "true_peak_db": level["input_tp"]} if level else None
        FO.receipt(out_dir / f"{stem}_with_sound.licence.json", clip, opts)
        rel = lambda p: Path(p).resolve().relative_to(Path(paths.output_dir(True)).resolve()).as_posix()
        rec.update(status="done", step="", files={"video": _view(rel(dest)), "wav": _view(rel(wav)), "licence": _view(rel(out_dir / f"{stem}_with_sound.licence.json"))}, loudness=loud, raw_loudness=raw, honest=FO.HONEST,
                   seconds=round(time.time() - t0, 1), label=FO.LABEL, terms=FO.STRICTEST, note="Levelled to about -16 LUFS with a -1.5 dBTP ceiling, then measured by ffmpeg (EBU R128). Nobody has listened to this sound.")
    except Exception as e: rec.update(status="error", step="", error=f"{e}"[:700])


@router.post("/sound")
def sound_run(b: dict = None):
    """Add sound to one clip with ControlFoley. Refused unless the person confirms non-commercial use. Runs in the background: poll /api/clipsound/jobs/{job}."""
    b = b or {}
    try: opts = FO.options(b)
    except ValueError as e: raise HTTPException(400, str(e)) from None
    clip = clip_path(b.get("clip"))
    gone = FO.missing()
    if gone: raise HTTPException(409, "ControlFoley needs files this machine doesn't have: " + "; ".join(gone[:4]) + ". The studio won't download them during a run.")
    info = probe(clip)
    if info["seconds"] and info["seconds"] > FO.MAX_SECONDS: raise HTTPException(400, f"{clip.name} is {info['seconds']:.0f} s long. ControlFoley takes up to {FO.MAX_SECONDS:.0f} s; cut it shorter first.")
    if info["seconds"] and info["seconds"] < FO.MIN_SECONDS: raise HTTPException(400, f"{clip.name} is too short: ControlFoley needs at least {FO.MIN_SECONDS} s.")
    jid = "snd-" + uuid.uuid4().hex[:10]
    rec = {"job": jid, "kind": "sound", "status": "running", "step": "starting", "started": time.time(), "clip": clip.name, "clip_info": info, "options": opts, "replaces_sound": bool(info["audio"])}; JOBS[jid] = rec
    threading.Thread(target=sound_job, args=(rec, clip, opts), daemon=True, name=jid).start(); return rec
