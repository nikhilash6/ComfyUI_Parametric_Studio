"""H3 song lock: a performer lip-syncs to a song you bring, and the song itself comes out unchanged.

How the lock works (workflows/h3_song_lock_api.json): the song window goes through H3's audio VAE into the audio half of
the latent with a noise mask of 0 (VAEEncodeAudio -> SetLatentNoiseMask(SolidMask 0) -> LTXVConcatAVLatent), plus a
MiniMaxH3AddGuide audio keyframe at frame 0. The sampler never changes the audio latent, so H3 only draws a picture that
sings what is already there. The method comes from the owner's earlier studio (pp/h3.py, "lock" mode).

Why the audio is still swapped afterwards: what H3 decodes is the song after a round trip through its audio VAE, and
SaveVideo encodes AAC. Neither is the song. So the studio cuts the window from the original file sample-exactly, joins
the H3 pictures without re-encoding them, and muxes that window as FLAC (lossless). The decoded samples of the result are
hashed against the decoded samples of the window: equal hashes mean bit-exact audio, and the cut step says so either way.

A lossy upload (MP3, M4A, Opus) is decoded once; the result then matches the decoded song, which is all a lossy file can
promise, and the facts say that too."""
from __future__ import annotations

import hashlib, json, math, os, re, subprocess, sys, tempfile, time
from pathlib import Path

FPS = 24
AUDIO_RE = re.compile(r"\.(wav|flac|mp3|m4a|aac|ogg|opus|aif|aiff)$", re.I)
LOSSLESS = {"pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_s16be", "pcm_s24be", "pcm_f32le", "pcm_u8", "flac", "alac", "wavpack"}
RAW = {"s16": "s16le", "s32": "s32le", "flt": "f32le", "dbl": "f64le", "u8": "u8", "s64": "s64le"}
WAV_CODEC = {"s16": "pcm_s16le", "s32": "pcm_s32le", "flt": "pcm_f32le", "dbl": "pcm_f64le", "u8": "pcm_u8"}
FLAC_OK = {"s16", "s32"}                       # FLAC stores integers only; it is what browsers play inside an MP4
MAX_SHOTS, SHOT_SECONDS = 8, [5, 6, 7, 8]
#: The camera moves a singing shot can take. Slow ones: a fast move pulls the face out of frame and the mouth with it.
CAMERAS = {
    "locked": "static shot, medium close-up",
    "push_in": "slow push in with small amplitude",
    "arc": "slow arc shot around the singer",
    "track": "slow tracking shot alongside the singer",
    "handheld": "handheld camera with a light natural sway",
}
LOCK_TAIL = "One continuous take with no cuts."
OPENING = ("The target video is cinematic and filmic: anamorphic widescreen feel, shallow depth of field, motivated "
           "practical lighting, slow deliberate camera movement.")
SOUND = "The song carries the scene; under it only a faint room tone."
MUSIC = "The song in the audio track, kept exactly as it is."
DEFAULT_WHO = "the singer in the picture"
DEFAULT_PLACE = "stands in a softly lit room"


class LockError(RuntimeError):
    """A song-lock step could not do its job; the message says why in plain words."""


def frames_for(seconds, have_seconds=None):
    """H3 clip lengths are 17k+5 frames at 24 fps (124 frames is the proven 5.17 s)."""
    from studio.goals import h3_ref_frames
    return h3_ref_frames(float(seconds), have_seconds)


def _end(words):
    w = " ".join(str(words or "").split())
    return w if not w or w[-1] in ".?!" else w + "."


def lock_prompt(who="", place="", words="", camera="locked", language="English"):
    """H3 Ref2VA prompt for one singing shot. The structure (subject, summary, retention, description, sound, music) is
    H3's reference format; the sung words go in the dialogue tag so the mouth shapes follow them."""
    who = " ".join(str(who or "").split()).rstrip(".") or DEFAULT_WHO
    place = " ".join(str(place or "").split()).rstrip(".") or DEFAULT_PLACE
    cam = CAMERAS.get(camera, CAMERAS["locked"])
    action = (f"<Subject 1> {place}, singing the song with clear, expressive mouth movements that follow every word, "
              f"{cam}. {LOCK_TAIL}")
    sung = f" <Subject 1> (S1) says: <d>[{language}] {_end(words)}</d>" if str(words or "").strip() else ""
    return ("subject_definitions:\n"
            f"<Subject 1>: {who}, appearing in <Picture 1>.\n\n"
            "summary:\n[reference generation] A composed cinematic shot of <Subject 1> singing to the camera.\n\n"
            "retention_analysis:\n<Picture 1>: fully_preserved - <Subject 1>'s face, hair, skin texture, clothing and body "
            "proportions are carried over exactly as shown.\n\n"
            f"detailed_description:\n{OPENING}\n[Shot 1] {action}{sung}\n\n"
            f"overall_soundscape:\n{SOUND}\n\nnon_diegetic_music:\n{MUSIC}\n")


# ------------------------------------------------------------------------------------------------ audio facts
def stream_info(path):
    """The first audio stream: codec, sample rate, channels, sample format (planar marker dropped), duration."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                        "stream=codec_name,sample_rate,channels,sample_fmt:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, timeout=30)
    try: d = json.loads(r.stdout or "{}"); s = (d.get("streams") or [None])[0]
    except ValueError: s = None
    if not s: raise LockError(f"{Path(path).name} has no audio stream that can be read")
    fmt = str(s.get("sample_fmt") or "s16").rstrip("p")
    return {"codec": s.get("codec_name"), "rate": int(s.get("sample_rate") or 0), "channels": int(s.get("channels") or 0),
            "sample_fmt": fmt, "duration": float((d.get("format") or {}).get("duration") or 0)}


def pcm(path, fmt):
    """Every decoded sample of the first audio stream, raw, in its own sample format: no resampling, no remixing."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-f", RAW.get(fmt, "s32le"), "-"],
                       capture_output=True, timeout=600)
    if r.returncode != 0: raise LockError("could not decode the audio: " + r.stderr.decode(errors="replace")[-200:])
    return r.stdout


def identity(path):
    """sha256 of the decoded samples, with what they are. Two files with equal identities carry the same audio, bit for bit."""
    info = stream_info(path); raw = pcm(path, info["sample_fmt"]); width = {"u8": 1, "s16": 2, "s32": 4, "flt": 4, "dbl": 8, "s64": 8}.get(info["sample_fmt"], 4)
    return {"sha256": hashlib.sha256(raw).hexdigest(), "samples": len(raw) // max(1, width * info["channels"]), "rate": info["rate"],
            "channels": info["channels"], "sample_fmt": info["sample_fmt"], "codec": info["codec"]}


def _ff(args, timeout=900):
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0: raise LockError("ffmpeg failed: " + (r.stderr or "").strip()[-300:])


def cut_window(src, out, start, seconds):
    """[start, start+seconds) of a song, sample-exact, as a WAV in the song's own sample format. A lossless song keeps
    every sample as it was; a lossy one is decoded once. -> facts about the window."""
    info = stream_info(src); sr = info["rate"]
    if sr <= 0: raise LockError("the song's sample rate can't be read")
    a = int(round(float(start) * sr)); n = int(round(float(seconds) * sr))
    if a < 0: raise LockError("the window starts before the song")
    if info["duration"] and (a + n) / sr > info["duration"] + 1e-3:
        raise LockError(f"the song is {info['duration']:.1f} s long; a {seconds:.2f} s window from {start:.2f} s runs past its end")
    fmt = info["sample_fmt"] if info["sample_fmt"] in WAV_CODEC else "s32"
    _ff(["-i", str(src), "-map", "0:a:0", "-af", f"atrim=start_sample={a}:end_sample={a + n},asetpts=N/SR/TB",
         "-c:a", WAV_CODEC[fmt], "-f", "wav", str(out)])
    got = identity(out)
    if got["samples"] != n: raise LockError(f"the window came out {got['samples']} samples long instead of {n}")
    return {"start": round(a / sr, 6), "seconds": round(n / sr, 6), "start_sample": a, "samples": n, "rate": sr, "channels": info["channels"],
            "sample_fmt": fmt, "source_codec": info["codec"], "source_lossless": info["codec"] in LOSSLESS, "sha256": got["sha256"]}


def loudest_start(src, seconds, step=0.5):
    """Where the loudest stretch of `seconds` begins: usually a chorus, where the singing is. Falls back to 0."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-f", "f32le", "-ac", "1", "-ar", "8000", "-"], capture_output=True, timeout=300)
    x = np.frombuffer(r.stdout, dtype=np.float32) if r.returncode == 0 else np.zeros(0, np.float32)
    total = len(x) / 8000
    if total <= seconds: return 0.0
    hop = 2000; rms = np.sqrt(np.convolve(x.astype(np.float64) ** 2, np.ones(hop) / hop, mode="same")[::hop] + 1e-12); cum = np.concatenate([[0.0], np.cumsum(rms)])
    best, bt, t = -1.0, 0.0, 0.0
    while t + seconds <= total - 0.05:
        i, j = int(t * 4), int((t + seconds) * 4); v = (cum[j] - cum[i]) / max(1, j - i)
        if v > best: best, bt = v, t
        t += step
    return round(bt, 3)


def _probe_video(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=codec_name,width,height,nb_read_packets,r_frame_rate",
                        "-of", "json", str(path)], capture_output=True, text=True, timeout=60)
    try: s = json.loads(r.stdout)["streams"][0]
    except (ValueError, KeyError, IndexError): raise LockError(f"{Path(path).name} has no readable video") from None
    return {"codec": s.get("codec_name"), "width": int(s["width"]), "height": int(s["height"]), "frames": int(s.get("nb_read_packets") or 0), "rate": s.get("r_frame_rate")}


def lock_cut(clips, window, out):
    """The singing shots one after another, their pictures untouched, with the song window under them, lossless.
    Then the proof: the decoded samples of the result against those of the window."""
    if not clips: raise LockError("no shots to cut")
    vids = [_probe_video(c) for c in clips]; frames = sum(v["frames"] for v in vids); w = identity(window)
    if w["sample_fmt"] not in FLAC_OK:
        raise LockError(f"the window is {w['sample_fmt']} audio, which FLAC can't hold exactly; cut it again as integer PCM")
    want = frames / FPS; have = w["samples"] / w["rate"]
    if abs(want - have) > 1.0 / FPS: raise LockError(f"the shots last {want:.3f} s but the song window lasts {have:.3f} s")
    same = len({(v["codec"], v["width"], v["height"], v["rate"]) for v in vids}) == 1
    with tempfile.TemporaryDirectory() as td:
        lst = Path(td) / "clips.txt"; lst.write_text("".join(f"file '{Path(c).resolve()}'\n" for c in clips))
        vcopy = same
        try:
            if not same: raise LockError("the shots differ in size or codec")
            _ff(["-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(window), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "flac",
                 "-movflags", "+faststart", str(out)])
        except LockError:
            vcopy = False; args = []
            for c in clips: args += ["-i", str(c)]
            ins = "".join(f"[{i}:v]scale={vids[0]['width']}:{vids[0]['height']},setsar=1,fps={FPS},format=yuv420p[v{i}];" for i in range(len(clips)))
            _ff(args + ["-i", str(window), "-filter_complex", ins + "".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[vo]",
                        "-map", "[vo]", "-map", f"{len(clips)}:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "flac",
                        "-movflags", "+faststart", str(out)])
    o = identity(out); v = _probe_video(out)
    match = o["sha256"] == w["sha256"] and o["samples"] == w["samples"] and o["rate"] == w["rate"] and o["channels"] == w["channels"]
    return {"file": str(out), "kind": "video",
            "note": (f"{len(clips)} singing shots, {v['frames'] / FPS:.2f} s; the song is bit-exact (sha256 of the decoded samples matches)" if match
                     else f"{len(clips)} singing shots, {v['frames'] / FPS:.2f} s; WARNING: the audio does not match the song window"),
            "facts": {"shots": len(clips), "frames": v["frames"], "seconds": round(v["frames"] / FPS, 3), "video_copied": vcopy, "audio_codec": o["codec"],
                      "audio_sha256_in": w["sha256"], "audio_sha256_out": o["sha256"], "audio_samples": o["samples"], "audio_rate": o["rate"],
                      "audio_channels": o["channels"], "audio_bit_exact": match}}


# ------------------------------------------------------------------------------------------------ sung words
def words_in(transcript, a, b):
    """The words Whisper heard whose middle falls in [a, b) seconds of the window, as one line."""
    out = []
    for s in (transcript or {}).get("segments") or []:
        for w in s.get("words") or []:
            if a <= (float(w[0]) + float(w[1])) / 2 < b: out.append(str(w[2]))
    return re.sub(r"\s+([,.!?])", r"\1", " ".join(out)).strip()


def listen(wav, out_json, language=""):
    """Whisper's timed words for the window, in its own process on the CPU (the Captions page's runner). -> (transcript or None, why not).
    The runner needs the models root and STUDIO_VOICE_CODE (Whisper's config files), like the Captions page."""
    from studio import feature_clipsound as C
    with tempfile.TemporaryDirectory() as td:
        mono = Path(td) / "mono16k.wav"
        try:
            _ff(["-i", str(wav), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(mono)])
            r = subprocess.run(C.listen_command("whisper_ct2_distil" if language in ("", "en", "English") else "whisper_ct2_large3", mono, out_json),
                               capture_output=True, text=True, timeout=900)
            if r.returncode != 0 or not Path(out_json).is_file():
                tail = [ln for ln in ((r.stderr or "") + (r.stdout or "")).strip().splitlines() if ln.strip()]
                return None, (tail[-1] if tail else f"exit {r.returncode}")[:200]
            return json.loads(Path(out_json).read_text(encoding="utf-8")), ""
        except Exception as e: return None, f"{type(e).__name__}: {str(e)[:160]}"


# ------------------------------------------------------------------------------------------------ the goal
def goal_values(req, image_name, o, seed):
    """${values} for workflows/h3_song_lock_api.json from a Create request or a recipe step."""
    from fastapi import HTTPException
    from studio import goals as GL
    audio = os.path.basename(str(req.get("audio") or "").strip())
    if not audio: raise HTTPException(400, "add your song first")
    if not AUDIO_RE.search(audio): raise HTTPException(400, "the song must be an uploaded wav, flac, mp3, m4a, ogg, opus or aiff file")
    if not image_name: raise HTTPException(400, "add a picture of the performer")
    try: start = float(req.get("start") or 0)
    except (TypeError, ValueError): raise HTTPException(400, "start must be a number of seconds") from None
    if not (0 <= start <= 3600) or math.isnan(start): raise HTTPException(400, "start must be between 0 and 3600 seconds")
    frames = frames_for(o["seconds"]); secs = frames / FPS; start = round(start + (int(o["part"]) - 1) * secs, 6)
    have = probe_song(audio)
    if have is not None and start + secs > have + 1e-3:
        raise HTTPException(400, f"your song is {have:.1f} s long, and this shot needs {secs:.2f} s from {start:.2f} s")
    w, h = (GL.H3_DRAFT_SIZES if o["quality"] == "draft" else GL.H3_VIDEO_SIZES)[o["aspect"]]
    prompt = lock_prompt(req.get("target"), req.get("prompt"), req.get("lyrics"), o["camera"])
    return {"image": image_name, "audio": audio, "start": start, "seconds": round(secs, 6), "frames": frames, "width": w, "height": h,
            "prompt": prompt, "seed": seed, "turbo": o["speed"] == "fast"}


def probe_song(name):
    """Seconds of an uploaded song in ComfyUI's input folder, or None when it can't be read from here."""
    from psn import paths
    try: return stream_info(os.path.join(paths.comfy_input(True), os.path.basename(name)))["duration"] or None
    except Exception: return None


# ------------------------------------------------------------------------------------------------ recipe steps
def _R():
    from studio import recipes as R
    return R


def _run_window(run, st, spec, ctx):
    """The stretch of the song the shots will sing: `shots` x one H3 clip length, from `start` (a field, seconds) or,
    when that is empty or 'auto', from the loudest stretch. Then Whisper's words for it, for the dialogue lines."""
    R = _R(); a = spec.get("args") or {}; d = R._root() / run["run"]; d.mkdir(parents=True, exist_ok=True)
    src = R._pick(ctx, spec["audio"], "audio")["local"]; shots = max(1, min(MAX_SHOTS, int(a.get("shots", 3)))); frames = frames_for(a.get("seconds", 5)); total = shots * frames / FPS
    want = str(R._fill(str(a.get("start", "auto")), ctx["values"])).strip().lower()
    try: start = float(want) if want not in ("", "auto") else None
    except ValueError: raise R.StepError(f"start must be a number of seconds or 'auto', not {want!r}") from None
    if start is None: start = loudest_start(src, total)
    out = d / f"{spec['id']}.wav"
    try: facts = cut_window(src, out, start, total)
    except LockError as e: raise R.StepError(str(e)) from None
    heard, why = listen(out, d / f"{spec['id']}.words.json", a.get("language", ""))
    facts.update(shots=shots, frames_per_shot=frames, words_heard=bool(heard))
    if why: facts["words_error"] = why
    if heard: facts["parts"] = [words_in(heard, k * frames / FPS, (k + 1) * frames / FPS) for k in range(shots)]
    st["note"] = f"{total:.2f} s from {facts['start']:.2f} s of the song, cut sample-exactly" + ("" if heard else f"; Whisper could not run ({why}), so the shots get no dialogue lines")
    st["facts"] = facts
    return [{"filename": out.name, "subfolder": "", "type": "recipe", "kind": "audio", "local": str(out), "url": f"/api/recipes/files/{run['run']}/{out.name}", "facts": facts}]


def _run_shot(run, st, spec, ctx):
    """One singing shot: the song_lock goal on part `part` of the window, with the words Whisper heard in that part."""
    R = _R(); S = R._srv(); wf = R._pick(ctx, spec["audio"], "audio"); facts = wf.get("facts") or {}; part = int((spec.get("options") or {}).get("part", 1))
    b = R.goal_body({**spec, "goal": "song_lock"}, ctx["values"], ctx["seed_add"]); parts = facts.get("parts") or []
    if "lyrics" not in spec and len(parts) >= part: b["lyrics"] = parts[part - 1]
    b["image"] = R._input_name(run, ctx, spec["image"], "image"); b["audio"] = R._input_name(run, ctx, spec["audio"], "audio")
    import asyncio
    try: j = asyncio.run(S.generate(R._Req(b)))
    except Exception as e: raise R.StepError(R._detail(e)) from None
    st["seed"] = j.get("seed"); st["graph_hash"] = j.get("graph_hash"); b["seed"] = j.get("seed"); st["body"] = b
    R._keep_graph(run, st, lambda: S._graph("song_lock", b, b.get("image"))[0])
    return R._wait_job(run, st, j["job"])


def _run_cut(run, st, spec, ctx):
    R = _R(); d = R._root() / run["run"]; d.mkdir(parents=True, exist_ok=True); out = d / f"{spec['id']}.mp4"
    clips = [R._pick(ctx, c, "video")["local"] for c in spec["clips"]]; window = R._pick(ctx, spec["audio"], "audio")["local"]
    try: r = lock_cut(clips, window, out)
    except LockError as e: raise R.StepError(str(e)) from None
    if not r["facts"]["audio_bit_exact"]: raise R.StepError("the cut's audio does not match the song window, so it is not kept as a song-lock result")
    st["note"] = r["note"]; st["facts"] = r["facts"]
    return [{"filename": out.name, "subfolder": "", "type": "recipe", "kind": "video", "local": str(out), "url": f"/api/recipes/files/{run['run']}/{out.name}"}]


PROOF = Path(__file__).resolve().parent / "song_lock_proof.json"
try:
    from fastapi import APIRouter
    router = APIRouter()

    @router.get("/api/song-lock")
    def about():
        """What the song-lock goal and recipe need, and the measured proof render, if there is one."""
        try: proof = json.loads(PROOF.read_text(encoding="utf-8"))
        except (OSError, ValueError): proof = None
        return {"cameras": CAMERAS, "shot_seconds": SHOT_SECONDS, "max_shots": MAX_SHOTS, "proof": proof}
except ImportError:      # the module also runs from scripts without FastAPI
    router = None


def register():
    R = _R(); R.EXTRA_STEPS.update(songlock_window=_run_window, songlock_shot=_run_shot, songlock_cut=_run_cut); R.CPU_KINDS |= {"songlock_window", "songlock_cut"}


register()
