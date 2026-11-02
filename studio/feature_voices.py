"""The Voices page: every speech model the studio can run, reading one original line, side by side with its time, peak memory, licence and proof.
Facts live in voice_models.json, measurements in voice_proof.json (scripts/build_voices_page.py). Audio is in web/voices/. Speech only: songs belong to the Music page.
A route that takes reference audio needs a yes that it is the user's own voice or that they have permission. Text goes through the same SFW check as every other page. Models run in their own process, not inside ComfyUI, so nothing here touches a running graph."""
import json, os, re, subprocess, sys, threading, time, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths

router = APIRouter(prefix="/api/voices")
PAGE = {"tab": "voices", "label": "Voices", "title": ["Voices", "One line. Every voice on this machine.", "Each model read the same line. Whisper checked the words and a script checked level and length. No person has listened yet."], "module": "voices.js", "export": "Voices", "css": "voices.css"}
ROOT = Path(__file__).resolve().parent; RUNNER = ROOT / "worldkit" / "runners" / "voice_speak.py"
CONSENT = ("own", "permission"); LIMIT = 800; JOBS: dict = {}; _cache: dict = {}
NO_CONSENT = "This model copies the voice in the clip you give it. Confirm it is your own voice or that you have the speaker's permission."


def _read(name):
    p = ROOT / name; mt = p.stat().st_mtime if p.exists() else 0
    if _cache.get(name, (None,))[0] != mt:
        try: _cache[name] = (mt, json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError): _cache[name] = (mt, {})
    return _cache[name][1]


def catalogue(): return _read("voice_models.json")
def proof(): return _read("voice_proof.json")
def model(mid):
    for m in catalogue().get("models") or []:
        if m["id"] == mid: return m
    raise HTTPException(404, "no such voice model")


def missing(m, root=None):
    """The files this model reads that aren't in the models folder, looked at now."""
    root = paths.models_root() if root is None else root
    return [f for f in m.get("files") or [] if not (root and os.path.isfile(os.path.join(root, f)))]


def state(m, root=None):
    """rendered: a render on this box passed. blocked: what it needs isn't on this box, and it says what. ready: the files are here, nobody has run it here. missing: the weights aren't here."""
    done = (proof().get("renders") or {}).get(m["id"]) or {}
    if done.get("audio") or done.get("text"): return "rendered"
    if m.get("blocked"): return "blocked"
    return "missing" if missing(m, root) else "ready"


def listing():
    return [{**m, "state": state(m), "proof": (proof().get("renders") or {}).get(m["id"]) or {"status": "not run"}} for m in catalogue().get("models") or []]


def runnable(): return [m for m in catalogue().get("models") or [] if not m.get("blocked") and m["kind"] in ("speech", "design", "reference", "convert")]


@router.get("/models")
def models_get(): return {"line": proof().get("line"), "about": catalogue().get("about"), "measured": proof().get("measured"), "kokoro": proof().get("kokoro") or {}, "models": listing()}


def _reference(b, m):
    """A clip the user gave, checked: only a name in the input folder, only with a yes. A model that needs one refuses without it."""
    name = os.path.basename(str(b.get("reference") or ""))
    if m["reference"] == "required" and not name: raise HTTPException(400, f"{m['label']} only speaks in the voice of a clip you give it. Upload one first.")
    if not name: return None, None
    if m["reference"] == "none": raise HTTPException(400, f"{m['label']} doesn't take a reference clip.")
    if str(b.get("consent") or "") not in CONSENT: raise HTTPException(400, NO_CONSENT)
    root = paths.comfy_input(True); p = os.path.join(root, name) if root else ""
    if not p or not os.path.isfile(p): raise HTTPException(400, "That clip isn't in the input folder. Upload it first.")
    return p, str(b.get("consent"))


def command(m, b, out):
    """The runner's command line for a request, after every check. Raises rather than guesses."""
    text = str(b.get("text") or "").strip()[:LIMIT]
    if not text: raise HTTPException(400, "Write a line for it to read.")
    voice = re.sub(r"\s+", " ", str(b.get("voice") or m.get("voice_default") or "")).strip()[:300]
    ref_text = str(b.get("reference_text") or "").strip()[:LIMIT]
    from studio import sfw
    sfw.check(text, voice, ref_text)
    ref, consent = _reference(b, m)
    cmd = [os.environ.get("STUDIO_VOICE_PYTHON") or sys.executable, str(RUNNER), "--model", m["id"], "--text", text, "--out", str(out), "--seed", str(max(0, min(2**31, int(b.get("seed") or 7))))]
    if voice: cmd += ["--voice", voice]
    if ref: cmd += ["--reference", ref, "--reference-consent", consent] + (["--reference-text", ref_text] if ref_text else [])
    return cmd


def _worker(rec, cmd, out):
    t0 = time.time()
    try:
        env = {**os.environ, "PSN_MODELS_ROOT": paths.models_root() or ""}
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
        if r.returncode: rec.update(status="error", error=(r.stderr or r.stdout)[-600:])
        else: rec.update(status="done", file=str(Path(out).relative_to(Path(paths.output_dir(True)))), seconds=round(time.time() - t0, 1))
    except Exception as e: rec.update(status="error", error=f"{e}"[:600])


@router.post("/run")
def run(b: dict = None):
    """Read a line with one model. Runs in its own process. Poll /api/voices/jobs/{job}."""
    b = b or {}; m = model(str(b.get("model") or ""))
    if m not in runnable(): raise HTTPException(409, m.get("blocked") or f"{m['label']} isn't a model that reads a line. It's on this page for its proof.")
    gone = missing(m)
    if gone: raise HTTPException(409, f"{m['label']} needs files this machine doesn't have: " + ", ".join(gone[:4]))
    jid = "voice-" + uuid.uuid4().hex[:10]; d = Path(paths.output_dir(True)) / "voices"; out = d / f"{jid}.wav"
    cmd = command(m, b, out); d.mkdir(parents=True, exist_ok=True)
    rec = {"job": jid, "model": m["id"], "status": "running", "started": time.time()}; JOBS[jid] = rec
    threading.Thread(target=_worker, args=(rec, cmd, out), daemon=True, name=jid).start(); return rec


@router.get("/jobs/{jid}")
def job_get(jid: str):
    r = JOBS.get(jid)
    if not r: raise HTTPException(404, "no such job")
    return r
