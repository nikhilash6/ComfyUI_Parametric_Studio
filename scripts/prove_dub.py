"""Proof runs for Dub & Voice, on AI-made voices and invented people only. Each GPU step waits at the shared VRAM gate (gpu_gate.py, found through GPU_GATE_TOOLS) and records its own peak.
Speech steps run in the voice venv (STUDIO_VOICE_PYTHON) as their own processes; Whisper runs on the CPU; the DubIt step needs a ComfyUI lane of your own (DUB_COMFYUI_URL), never :8200 or :8322.
  python scripts/prove_dub.py master|clone|voice_dub|dubit|relip|pack
Work files go to $DUB_PROOF_WORK. `pack` writes studio/dub_proof.json and copies what the page shows to studio/web/dub/. Look at and listen to every output before packing."""
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO))
if os.environ.get("GPU_GATE_TOOLS"): sys.path.insert(0, os.environ["GPU_GATE_TOOLS"])
from studio import audio_master as AM, feature_dub as D

WORK = Path(os.environ.get("DUB_PROOF_WORK") or REPO / "dub_proof_work"); LOG = WORK / "log.json"; WEB = REPO / "studio" / "web"
SOURCE = WEB / "motion" / "latentsync_0.mp4"          # an invented woman made with Wan 2.2, her voice Kokoro-82M's built-in bf_emma (motion_proof.json)
MUSIC = WEB / "showcase" / "a_score.m4a"             # an instrumental made here with MiniMax Music 3 (showcase.json)
PY = os.environ.get("STUDIO_VOICE_PYTHON") or sys.executable


def log(): return json.loads(LOG.read_text()) if LOG.exists() else {}


def put(key, rec):
    d = log(); d[key] = rec; WORK.mkdir(parents=True, exist_ok=True); LOG.write_text(json.dumps(d, indent=1, ensure_ascii=False)); print(key, json.dumps(rec, ensure_ascii=False)[:900], flush=True)


def _tree(root):
    kids = {}
    for p in os.listdir("/proc"):
        if p.isdigit():
            try: kids.setdefault(int(open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()[1]), []).append(int(p))
            except OSError: pass
    out = [root]; i = 0
    while i < len(out): out += kids.get(out[i], []); i += 1
    return set(out)


def gpu_steps(key, peak, args):
    """One dub_steps.py call holding a gate reservation; the peak is the summed VRAM of its process tree. -> (json, seconds, peak GiB)"""
    import gpu_gate as G
    want = G.expected("dub:" + key, peak); rid = None
    while rid is None:
        rid, why = G.acquire("gap-p6", key, want)
        if rid is None: print("gate:", why, flush=True); time.sleep(20)
    t0 = time.time(); top = 0.0
    try:
        p = subprocess.Popen([PY, str(D.STEPS), *map(str, args)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=D._env())
        out_box = {}; th = threading.Thread(target=lambda: out_box.update(zip(("out", "err"), p.communicate())), daemon=True); th.start()
        while p.poll() is None:
            pids = _tree(p.pid); top = max(top, sum(v for k, v in G.PROBE.apps().items() if k in pids)); time.sleep(1)
        th.join(30)
    finally: G.release(rid)
    if top: G.record_peak("dub:" + key, top)
    if p.returncode: raise SystemExit(f"{key} failed: " + (out_box.get("err") or "")[-1500:])
    return json.loads(out_box["out"].strip().splitlines()[-1]), round(time.time() - t0, 1), round(top, 1)


def heard(path, lang=""):
    with tempfile.TemporaryDirectory() as td:
        w = D.to16k(path, Path(td) / "a.wav"); return D.listen(w, Path(td) / "w.json", lang)


SCRIPT = "Some places keep their secrets until the light is right. Tonight, the old harbour opens its doors, and every lantern on the water tells a story of its own."


def step_master():
    v = WORK / "vo_voice.wav"
    said, secs, peak = gpu_steps("vo_voice", D.TTS_PEAK_GIB, ["speak", "--model", "qwen3_custom_17", "--language", "English", "--text", SCRIPT, "--out", v, "--voice", "Ryan", "--seed", 7])
    t0 = time.time(); out = WORK / "voiceover.wav"; rep = AM.voiceover(v, MUSIC, out, stems_dir=WORK / "vo_stems"); mt = round(time.time() - t0, 1)
    after = AM.measure(out); h = heard(v, "en")
    put("master", {"voice": {"model": "Qwen3-TTS 1.7B CustomVoice", "speaker": "Ryan", "seed": 7, "seconds": secs, "peak_vram_gib": peak, "audio_seconds": said.get("seconds"), "wer": D.wer(SCRIPT, h["text"]), "heard": h["text"]},
                   "music": MUSIC.name, "report": rep, "remeasured": after, "master_seconds": mt, "file": str(out)})


def step_clone():
    design = "A warm, low-voiced adult man in his fifties, unhurried, a slight rasp, speaking close to the microphone."
    ref_line = "Every morning the baker opens the blue door and sweeps the step before the street wakes up."
    line = "The tide comes in twice a day, and twice a day the harbour remembers what it is for."
    ref = WORK / "clone_designed.wav"; out = WORK / "clone_voice.wav"; recs = {}
    _, recs["design_s"], recs["design_peak"] = gpu_steps("clone_design", D.TTS_PEAK_GIB, ["speak", "--model", "qwen3_design_17", "--language", "English", "--text", ref_line, "--out", ref, "--voice", design, "--seed", 11])
    said, recs["clone_s"], recs["clone_peak"] = gpu_steps("clone_base", D.TTS_PEAK_GIB, ["speak", "--model", "qwen3_base_17", "--language", "English", "--text", line, "--out", out, "--reference", ref, "--reference-text", ref_line, "--reference-consent", "synthetic", "--seed", 11])
    D._consent_file(out, "synthetic", str(ref), "Qwen3-TTS 1.7B Base", {"designed_from": design})
    sim = D.steps(["similar", "--a", ref, "--b", out])
    other = WORK / "clone_other.wav"
    _, _, _ = gpu_steps("clone_other", D.TTS_PEAK_GIB, ["speak", "--model", "qwen3_custom_17", "--language", "English", "--text", line, "--out", other, "--voice", "Vivian", "--seed", 11])
    sim_other = D.steps(["similar", "--a", ref, "--b", other])
    h = heard(out, "en")
    put("clone", {"design": design, "reference_line": ref_line, "line": line, **recs, "audio_seconds": said.get("seconds"), "similarity": sim["cosine"], "similarity_to_a_different_voice": sim_other["cosine"], "encoder": sim["encoder"],
                  "wer": D.wer(line, h["text"]), "heard": h["text"], "consent": json.loads(Path(str(out) + ".consent.json").read_text()), "files": [str(ref), str(out), str(other)]})


SPANISH = "Navegamos por las estrellas cuando los instrumentos se callan. Esta noche el cielo está despejado."


def step_voice_dub():
    src = heard(SOURCE); info = D.probe(SOURCE); ref = WORK / "src_ref.wav"
    AM._run([AM.ffmpeg(), "-y", "-hide_banner", "-i", str(SOURCE), "-vn", "-ac", "1", "-ar", "24000", str(ref)])
    tts = WORK / "dub_es_tts.wav"
    said, secs, peak = gpu_steps("dub_es_clone", D.TTS_PEAK_GIB, ["speak", "--model", "qwen3_base_17", "--language", "Spanish", "--text", SPANISH, "--out", tts, "--reference", ref, "--reference-text", src["text"], "--reference-consent", "synthetic", "--seed", 7])
    fitted = WORK / "dub_es_fit.wav"; cmd, k = D.fit_command(tts, fitted, info["seconds"], said["seconds"]); AM._run(cmd)
    laid = WORK / "dub_es_laid.mp4"; AM._run(D.lay_command(SOURCE, fitted, laid))
    from studio import likeness
    out = WORK / "dub_es_voice.mp4"; likeness.mark(laid, out)
    D._consent_file(out, "synthetic", str(ref), "Qwen3-TTS 1.7B Base", {"source": SOURCE.name, "why_synthetic": "the source voice is Kokoro-82M's built-in bf_emma"})
    h = heard(out, "es"); sim = D.steps(["similar", "--a", ref, "--b", fitted])
    put("voice_dub", {"source": SOURCE.name, "source_heard": src["text"], "source_language": src["language"], "translation": SPANISH, "translated_by": "typed by hand (no local LLM was running)", "language": "es",
                      "model": "Qwen3-TTS 1.7B Base, cloning the clip's voice", "seconds": secs, "peak_vram_gib": peak, "tempo": k, "heard": h["text"], "heard_language": h["language"], "wer": D.wer(SPANISH, h["text"], "es"),
                      "voice_similarity_to_source": sim["cosine"], "file": str(out)})


def step_dubit():
    """DubIt on LTX-2.5: the same clip and the same Spanish line, the mouth and voice redrawn. Needs DUB_COMFYUI_URL on a lane of your own."""
    import gpu_gate as G
    c = D.Comfy(); port = urllib.parse.urlparse(c.url).port
    if port in (8200, 8322): raise SystemExit("never :8200 or :8322: start a lane of your own and set DUB_COMFYUI_URL")
    if D.dubit_state(): raise SystemExit(D.dubit_state())
    info = D.probe(SOURCE); scene = "A woman in a dark coat speaks to the camera, turning her head slightly"
    want = G.expected("dub:dubit", D.DUBIT_PEAK_GIB, True); rid = None
    while rid is None:
        rid, why = G.acquire("gap-p6", "dubit", want, True, port=port)
        if rid is None: print("gate:", why, flush=True); time.sleep(20)
    top = [0.0]; stop = threading.Event(); watch = G.FloorWatch()
    def poll():
        while not stop.is_set():
            top[0] = max(top[0], G.PROBE.used_by_port(port))
            if watch.tripped(): print("floor: under 4 GiB; cancelling this lane's job", flush=True); c.cancel()
            time.sleep(1)
    th = threading.Thread(target=poll, daemon=True); th.start(); t0 = time.time()
    try:
        name = c.upload(SOURCE); vals = D.dub_values(name, info, SPANISH, "Spanish", scene, seed=7); h = c.run(D.graph(vals))
        raw = c.fetch(D.video_output(h), WORK / "dubit_raw.mp4")
    finally:
        stop.set(); th.join(5); G.release(rid)
    secs = round(time.time() - t0, 1); G.record_peak("dub:dubit", top[0])
    from studio import likeness
    out = WORK / "dub_es_dubit.mp4"; likeness.mark(raw, out); hh = heard(out, "es")
    put("dubit", {"source": SOURCE.name, "translation": SPANISH, "language": "es", "model": "LTX-2.5 distilled int8 + LTX-2.3 DubIt IC-LoRA 0.9", "seed": 7, "frames": vals["frames"], "size": [vals["width"], vals["height"]],
                  "seconds": secs, "peak_vram_gib": round(top[0], 1), "heard": hh["text"], "heard_language": hh["language"], "wer": D.wer(SPANISH, hh["text"], "es"), "file": str(out)})


def step_relip():
    """The same Spanish voice as voice_dub, then the Motion page's LatentSync route over HTTP on a dev studio of your own (DUB_STUDIO_URL, its PID DUB_STUDIO_PID, its input and output folders DUB_STUDIO_INPUT and DUB_STUDIO_OUTPUT)."""
    import gpu_gate as G
    base = os.environ["DUB_STUDIO_URL"].rstrip("/"); port = urllib.parse.urlparse(base).port
    if port in (8200, 8322, 8310): raise SystemExit("a dev studio of your own, never the released one")
    fitted = WORK / "dub_es_fit.wav"
    if not fitted.is_file(): raise SystemExit("run voice_dub first: it makes the fitted Spanish voice")
    inp = Path(os.environ["DUB_STUDIO_INPUT"]); outdir = Path(os.environ["DUB_STUDIO_OUTPUT"]); vn, an = "dub_relip_src.mp4", "dub_relip_es.wav"
    shutil.copy(SOURCE, inp / vn); shutil.copy(fitted, inp / an)
    spid = int(os.environ.get("DUB_STUDIO_PID") or 0) or None      # the dev studio's PID: LatentSync runs as its child, so its tree holds the peak
    want = G.expected("dub:relip", 16.0); rid = None
    while rid is None:
        rid, why = G.acquire("gap-p6", "relip", want)
        if rid is None: print("gate:", why, flush=True); time.sleep(20)
    top = [0.0]; stop = threading.Event()
    def poll():
        while not stop.is_set():
            if spid: pids = _tree(spid); top[0] = max(top[0], sum(v for k, v in G.PROBE.apps().items() if k in pids))
            time.sleep(1)
    th = threading.Thread(target=poll, daemon=True); th.start(); t0 = time.time()
    try: rel = D.motion_relip(vn, an, base=base)
    finally: stop.set(); th.join(5); G.release(rid)
    secs = round(time.time() - t0, 1)
    if top[0]: G.record_peak("dub:relip", top[0])
    out = WORK / "dub_es_relip.mp4"; shutil.copy(outdir / rel, out); h = heard(out, "es")
    put("relip", {"source": SOURCE.name, "translation": SPANISH, "language": "es", "model": "Qwen3-TTS 1.7B Base (clone) + LatentSync 1.6 through the Motion route", "seconds": secs, "peak_vram_gib": round(top[0], 1),
                  "heard": h["text"], "heard_language": h["language"], "wer": D.wer(SPANISH, h["text"], "es"), "file": str(out)})


def step_pack():
    L = log(); d = WEB / "dub"; d.mkdir(parents=True, exist_ok=True); shown = {}
    def ship(src, name, audio=False):
        dst = d / name
        if audio: AM._run([AM.ffmpeg(), "-y", "-hide_banner", "-i", str(src), "-c:a", "aac", "-b:a", "160k", "-metadata", "comment=AI-generated voice. Made with Parametric Studio.", str(dst)])
        else: shutil.copy(src, dst)
        return "dub/" + name
    if "master" in L: shown["voiceover"] = ship(L["master"]["file"], "voiceover.m4a", True)
    if "clone" in L: shown["clone_reference"], shown["clone"] = ship(L["clone"]["files"][0], "clone_designed.m4a", True), ship(L["clone"]["files"][1], "clone_voice.m4a", True)
    if "voice_dub" in L: shown["voice_dub"] = ship(L["voice_dub"]["file"], "dub_es_voice.mp4")
    if "dubit" in L: shown["dubit"] = ship(L["dubit"]["file"], "dub_es_dubit.mp4")
    if "relip" in L: shown["relip"] = ship(L["relip"]["file"], "dub_es_relip.mp4")
    for k in ("master", "clone", "voice_dub", "dubit", "relip"):
        if k in L: L[k] = {kk: v for kk, v in L[k].items() if kk not in ("file", "files")}
    (REPO / "studio" / "dub_proof.json").write_text(json.dumps({"made": time.strftime("%Y-%m-%d"), "machine": "RTX PRO 6000 Blackwell 96 GB, shared; speech in its own process, Whisper large-v3 on the CPU",
        "measured_with": {"loudness": "ffmpeg ebur128 (true peak)", "words": "faster-whisper large-v3, word error rate by our own Levenshtein", "voice likeness": "cosine of Chatterbox voice-encoder embeddings"},
        "note": "Nobody has listened yet: every number was measured by a program.", "source": {"clip": "motion/latentsync_0.mp4", "about": "an invented woman made with Wan 2.2, her voice Kokoro-82M's built-in bf_emma"},
        "music": {"file": "showcase/a_score.m4a", "about": "an instrumental made here with MiniMax Music 3"}, "media": shown, **L}, indent=1, ensure_ascii=False) + "\n")
    print("packed", shown)


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    {"master": step_master, "clone": step_clone, "voice_dub": step_voice_dub, "dubit": step_dubit, "relip": step_relip, "pack": step_pack}[sys.argv[1]]()
