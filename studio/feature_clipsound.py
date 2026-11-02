"""Captions & Sound: speech captions for any clip, as SRT and WebVTT files and, if asked, drawn onto a copy of the clip.
Whisper runs in its own process (studio/worldkit/runners/caption_listen.py), on the CPU unless STUDIO_CAPTION_DEVICE=cuda, so it never touches a running graph.
The words on screen are set by ffmpeg and libass from a font, not painted by a model. Clips come only from the studio's input and output folders.
What each model is and its licence come from voice_models.json, the Voices page's catalogue; what ran here is in clipsound_proof.json."""
import json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.parse, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths
from studio import captions as C

router = APIRouter(prefix="/api/clipsound")
PAGE = {"tab": "clipsound", "label": "Captions & Sound", "title": ["Captions & Sound", "Your clip. Its words on screen.", "Whisper writes down what is said, and ffmpeg sets it in a real font, so the letters are never a model's guess. Every result here was measured by a program. No person has listened yet."], "module": "clipsound.js", "export": "ClipSound", "css": "clipsound.css"}
ROOT = Path(__file__).resolve().parent; RUNNER = ROOT / "worldkit" / "runners" / "caption_listen.py"
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


@router.get("/models")
def models_get(): return {"listeners": listeners(), "styles": list(C.STYLES), "sizes": list(C.SIZES), "places": list(C.PLACES), "proof": proof()}


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
