"""Dub & Voice: mastering and ducking (real ffmpeg on made-up tones), the word error rate, the DubIt graph, the routes and jobs, the runner's contract. Stubbed: no ComfyUI, no speech model, no live port."""
import json, re, shutil, subprocess, tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from studio import audio_master as AM, feature_dub as F, server as S

ROOT = Path(__file__).resolve().parents[1]; WEB = ROOT / "studio" / "web"
RUNNER = (ROOT / "studio" / "worldkit" / "runners" / "dub_steps.py").read_text(encoding="utf-8")
HAVE_FFMPEG = bool(shutil.which("ffmpeg") or (Path.home() / ".local" / "bin" / "ffmpeg").exists()) and bool(shutil.which("ffprobe"))


@pytest.fixture
def client(): return TestClient(S.app)


@pytest.fixture
def folders(monkeypatch, tmp_path):
    (tmp_path / "in").mkdir(); (tmp_path / "out" / "video").mkdir(parents=True); (tmp_path / "models").mkdir()
    (tmp_path / "out" / "video" / "talk.mp4").write_bytes(b"x"); (tmp_path / "in" / "me.wav").write_bytes(b"x"); (tmp_path / "out" / "score.m4a").write_bytes(b"x")
    for mod in (F, ):
        monkeypatch.setattr(mod.paths, "comfy_input", lambda *_: str(tmp_path / "in")); monkeypatch.setattr(mod.paths, "output_dir", lambda *_: str(tmp_path / "out"))
        monkeypatch.setattr(mod.paths, "models_root", lambda *_: str(tmp_path / "models"))
    return tmp_path


# ---------- loudness and ducking
SUMMARY = """[Parsed_ebur128_0 @ 0x1] t: 1.2 M: -20.0 S: -21.0 I: -30.0 LUFS
[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:         -14.2 LUFS
    Threshold: -24.3 LUFS

  Loudness range:
    LRA:         5.1 LU

  True peak:
    Peak:       -1.4 dBFS"""


def test_the_ebur128_summary_is_read_not_the_running_lines():
    assert AM.parse_ebur128(SUMMARY) == {"lufs": -14.2, "lra": 5.1, "true_peak": -1.4}
    assert AM.parse_ebur128(SUMMARY.replace("-14.2 LUFS", "-inf LUFS"))["lufs"] == float("-inf")


def test_speech_sections_come_from_the_silences_and_short_pauses_are_joined():
    text = "silence_start: 0\nsilence_end: 0.5\nsilence_start: 2.5\nsilence_end: 2.8\nsilence_start: 4.0\nsilence_end: 5.5\n"
    assert AM.parse_silences(text, 7.0) == [(0.5, 2.5), (2.8, 4.0), (5.5, 7.0)]
    assert AM.merge([(0.5, 2.5), (2.8, 4.0), (5.5, 7.0)]) == [(0.5, 4.0), (5.5, 7.0)]
    assert AM.parse_silences("silence_start: 3.0\n", 5.0) == [(0.0, 3.0)]


def test_the_duck_curve_is_full_inside_and_ramps_outside():
    e = AM.duck_expression([(1.0, 2.0)], 0.25, ramp=0.25); assert e.startswith("1-(1-0.250000)*") and "clip(" in e
    f = lambda t: eval(e.replace("clip", "_c").replace("min", "min"), {"_c": lambda x, a, b: max(a, min(b, x)), "t": t, "min": min, "max": max})
    assert f(1.5) == pytest.approx(0.25) and f(0.0) == pytest.approx(1.0) and f(3.0) == pytest.approx(1.0) and 0.25 < f(0.875) < 1.0
    assert AM.duck_expression([], 0.5) == "1" and AM.duck_expression([(0, 1), (2, 3), (4, 5)], 0.5).count("max(") == 2


def test_the_plan_puts_the_music_at_the_asked_depth():
    p = AM.plan(-20.0, -10.0, depth=12, bed=6)
    assert p["bed_gain_db"] == -16.0 and p["duck_gain"] == pytest.approx(10 ** (-6 / 20), rel=1e-4)


def test_the_master_commands_use_linear_loudnorm_and_an_oversampled_limiter():
    m = {"input_i": "-30.1", "input_tp": "-12.0", "input_lra": "4.0", "input_thresh": "-40.5", "target_offset": "0.2"}
    c = " ".join(AM.master_command("a.wav", "b.wav", m)); assert "linear=true" in c and "measured_I=-30.1" in c and "I=-14.0" in c
    f = " ".join(AM.fix_command("a.wav", "b.wav", 1.5)); assert "aresample=192000" in f and "alimiter" in f and "volume=1.50dB" in f
    assert AM.within({"lufs": -14.3, "true_peak": -1.2}) and not AM.within({"lufs": -13.2, "true_peak": -1.2}) and not AM.within({"lufs": -14.0, "true_peak": -0.8})


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")
def test_a_voiceover_on_noise_meets_the_target_and_the_depth(tmp_path):
    ff = AM.ffmpeg()
    subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=300:d=2", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=1", "-f", "lavfi", "-i", "sine=f=420:d=2.5",
                    "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1,volume=0.3", str(tmp_path / "v.wav")], check=True)
    subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "anoisesrc=c=pink:d=8:a=0.3", str(tmp_path / "m.wav")], check=True)
    r = AM.voiceover(tmp_path / "v.wav", tmp_path / "m.wav", tmp_path / "out.wav")
    assert len(r["sections"]) == 2 and r["ducking"]["passes"] and r["ducking"]["depth_db"] >= 8 and r["master"]["passes"]
    m = AM.measure(tmp_path / "out.wav"); assert abs(m["lufs"] + 14) <= 0.5 and m["true_peak"] <= -1.0


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")
def test_a_hot_file_is_limited_under_the_true_peak_ceiling(tmp_path):
    subprocess.run([AM.ffmpeg(), "-y", "-v", "error", "-f", "lavfi", "-i", "anoisesrc=c=white:d=4:a=0.05", "-af", "volume='if(lt(mod(t,1),0.02),40,1)':eval=frame", str(tmp_path / "hot.wav")], check=True)
    r = AM.master(tmp_path / "hot.wav", tmp_path / "out.wav"); assert r["passes"], r
    assert AM.measure(tmp_path / "out.wav")["true_peak"] <= -1.0


# ---------- words
def test_word_error_rate():
    assert F.wer("Hola, ¿qué tal?", "hola que tal") == pytest.approx(1 / 3, abs=1e-3)      # qué and que are different words
    assert F.wer("the sky is clear", "The sky is clear.") == 0.0 and F.wer("the sky is clear", "the sky clear") == 0.25 and F.wer("", "") == 0.0
    assert F.wer("今天天气很好", "今天天气好", "zh") == pytest.approx(1 / 6, abs=1e-3)


def test_lengths_and_sizes_for_ltx():
    assert F.frames_for(5.08) == 121 and F.frames_for(3.24) == 73 and F.frames_for(20) == 121 and F.frames_for(0.1) == 9
    assert all((F.frames_for(s) - 1) % 8 == 0 for s in (0.5, 1.7, 2.2, 4.9))
    assert F.size_for(600, 600) == (768, 768) and F.size_for(1920, 1080) == (768, 448) and F.size_for(1080, 1920) == (448, 768)


# ---------- the DubIt graph
def test_the_dubit_graph_fills_and_keeps_the_voice_reference():
    g = F.graph(F.dub_values("clip.mp4", {"seconds": 5.08, "width": 600, "height": 600}, "Hola a todos", "Spanish", "A woman talks", seed=9))
    assert not re.search(r"\$\{", json.dumps(g))
    assert g["lora"]["class_type"] == "LTXICLoRALoaderModelOnly" and g["lora"]["inputs"]["lora_name"] == F.DUBIT
    assert g["aref"] == {"class_type": "LTXVAudioVAEEncode", "inputs": {"audio": ["comp", 1], "audio_vae": ["avae", 0]}}
    assert g["reft"]["class_type"] == "LTXVSetAudioRefTokens" and g["guider"]["inputs"]["positive"] == ["reft", 0] and g["guider"]["inputs"]["negative"] == ["reft", 1]
    assert g["guide"]["inputs"]["latent_downscale_factor"] == 1.0 and g["trim"]["inputs"]["length"] == 121 and g["noise"]["inputs"]["noise_seed"] == 9
    assert 'saying: "Hola a todos"' in g["pos"]["inputs"]["text"] and "Spanish" in g["pos"]["inputs"]["text"] and g["mk"]["inputs"]["audio"] == ["adec", 0]
    assert all(not str(n["class_type"]).startswith(("Gemma", "LTXVAPI")) and "API" not in n["class_type"] for n in g.values())      # open weights only: no API text encoder


def test_dubit_says_what_is_missing(tmp_path):
    assert F.dubit_state(tmp_path).startswith("needs download: the DubIt IC-LoRA")
    f = tmp_path / "loras" / F.DUBIT; f.parent.mkdir(parents=True); f.write_bytes(b"x" * 8192)
    assert "8 KB stub" in F.dubit_state(tmp_path)
    with open(f, "wb") as h: h.truncate(F.DUBIT_MIN_BYTES + 1)
    assert "ltx-2.5-22b-distilled" in F.dubit_state(tmp_path)
    for x in F.LTX_FILES: (tmp_path / x).parent.mkdir(parents=True, exist_ok=True); (tmp_path / x).write_bytes(b"x")
    assert F.dubit_state(tmp_path) == ""


# ---------- translation
def test_the_llm_translates_without_thinking_and_none_when_absent():
    seen = {}
    def post(url, body): seen.update(url=url, body=body); return {"choices": [{"message": {"content": "<think>x</think>\n\"Hola a todos.\""}}]}
    r = F.llm_translate("Hello everyone.", "Spanish", endpoint=lambda: {"url": "http://127.0.0.1:8002/v1", "model": "q"}, post=post)
    assert r == {"text": "Hola a todos.", "by": "q"} and seen["url"].endswith("/v1/chat/completions") and seen["body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert F.llm_translate("x", "Spanish", endpoint=lambda: None) is None


def test_translate_route_says_to_type_it_when_no_llm(client, monkeypatch):
    monkeypatch.setattr(F, "llm_translate", lambda *a, **k: None)
    r = client.post("/api/dub/translate", json={"text": "Hello", "to": "es"}); assert r.status_code == 503 and "Type the translation" in r.json()["detail"]
    assert client.post("/api/dub/translate", json={"text": "Hello", "to": "xx"}).status_code == 400


# ---------- routes
def test_models_lists_languages_modes_and_readiness(client, folders):
    d = client.get("/api/dub/models").json()
    assert d["languages"]["es"] == "Spanish" and d["modes"] == ["dubit", "voice", "relip"] and d["dubit"]["ready"] is False and "needs download" in d["dubit"]["why_not"]
    assert d["master"] == {"lufs": -14.0, "tp": -1.0, "depth": 12.0}


def test_bad_dub_requests_are_refused_before_anything_runs(client, folders, monkeypatch):
    clip = {"filename": "talk.mp4", "subfolder": "video", "type": "output"}
    assert client.post("/api/dub/run", json={"clip": clip, "mode": "x", "language": "es", "text": "hola"}).status_code == 400
    assert client.post("/api/dub/run", json={"clip": clip, "mode": "voice", "language": "es", "text": ""}).status_code == 400
    r = client.post("/api/dub/run", json={"clip": clip, "mode": "voice", "voice": "clone", "language": "es", "text": "hola"}); assert r.status_code == 400 and "Cloning copies a voice" in r.json()["detail"]
    r = client.post("/api/dub/run", json={"clip": clip, "mode": "dubit", "language": "es", "text": "hola"}); assert r.status_code == 409 and "needs download" in r.json()["detail"]
    monkeypatch.setattr(F, "vae_problem", lambda *a, **k: ""); monkeypatch.setattr(F, "dubit_state", lambda *a: ""); monkeypatch.setattr(F, "probe", lambda p, run=None: {"seconds": 5.0, "width": 600, "height": 600, "audio": None})
    r = client.post("/api/dub/run", json={"clip": clip, "mode": "dubit", "language": "es", "text": "hola"}); assert r.status_code == 400 and "has none" in r.json()["detail"]


def test_a_dub_needs_the_permission_tick(client, folders, monkeypatch):
    monkeypatch.setattr(F, "vae_problem", lambda *a, **k: ""); monkeypatch.setattr(F, "dubit_state", lambda *a: ""); monkeypatch.setattr(F, "probe", lambda p, run=None: {"seconds": 5.0, "width": 600, "height": 600, "audio": "aac"})
    started = []; monkeypatch.setattr(F, "_start", lambda *a, **k: started.append(a) or {"job": "j"})
    clip = {"filename": "talk.mp4", "subfolder": "video", "type": "output"}
    r = client.post("/api/dub/run", json={"clip": clip, "mode": "dubit", "language": "es", "text": "hola"}); assert r.status_code == 400 and "permission" in r.json()["detail"] and not started
    from studio import likeness
    monkeypatch.setattr(likeness, "video_problem", lambda *a, **k: "")
    assert client.post("/api/dub/run", json={"clip": clip, "mode": "dubit", "language": "es", "text": "hola", "permission": True}).status_code == 200 and started


def test_clone_requires_a_yes_for_a_real_voice_and_none_for_a_designed_one(client, folders, monkeypatch):
    monkeypatch.setattr(F, "tts_state", lambda *a: ""); started = []; monkeypatch.setattr(F, "_start", lambda kind, fn, opts, **k: started.append(opts) or {"job": "j"})
    r = client.post("/api/dub/clone", json={"text": "hello", "reference": "me.wav"}); assert r.status_code == 400 and "own voice" in r.json()["detail"]
    r = client.post("/api/dub/clone", json={"text": "hello", "reference": "me.wav", "consent": "synthetic"}); assert r.status_code == 400      # a real recording can't be called synthetic
    assert client.post("/api/dub/clone", json={"text": "hello", "reference": "nope.wav", "consent": "own"}).status_code == 400
    assert client.post("/api/dub/clone", json={"text": "hello", "reference": "../../etc/passwd", "consent": "own"}).status_code == 400
    assert client.post("/api/dub/clone", json={"text": "hello", "reference": "me.wav", "consent": "own"}).status_code == 200 and started[-1]["consent"] == "own"
    assert client.post("/api/dub/clone", json={"text": "hello", "design": "a calm adult voice"}).status_code == 200 and started[-1]["consent"] == "synthetic"


def test_voiceover_checks_its_numbers_and_files(client, folders, monkeypatch):
    monkeypatch.setattr(F, "tts_state", lambda *a: ""); started = []; monkeypatch.setattr(F, "_start", lambda kind, fn, opts, **k: started.append(opts) or {"job": "j"})
    assert client.post("/api/dub/voiceover", json={"text": "hi", "music": {"filename": "nope.m4a", "type": "output"}}).status_code == 404
    assert client.post("/api/dub/voiceover", json={"text": "", "music": {"filename": "score.m4a", "type": "output"}}).status_code == 400
    assert client.post("/api/dub/voiceover", json={"text": "hi", "music": {"filename": "score.m4a", "type": "output"}, "lufs": -40, "depth": 2}).status_code == 200
    assert started[-1]["lufs"] == -24.0 and started[-1]["depth"] == 8.0 and started[-1]["tp"] == -1.0
    assert client.get("/api/dub/audio").json()["audio"][0]["filename"] == "score.m4a"


# ---------- jobs, stubbed
class FakeComfy:
    def __init__(self): self.graphs = []
    def upload(self, p): return "up_" + Path(p).name
    def run(self, g): self.graphs.append(g); return {"outputs": {"save": {"images": [{"filename": "ltx_dubit_00001.mp4", "subfolder": "dub", "type": "output"}]}}}
    def fetch(self, item, dest): Path(dest).write_bytes(b"video"); return Path(dest)


def test_a_dubit_job_marks_checks_and_writes_a_receipt(folders, monkeypatch):
    clip = folders / "out" / "video" / "talk.mp4"
    monkeypatch.setattr(F, "to16k", lambda src, dst, run=None: Path(dst)); monkeypatch.setattr(F, "listen", lambda w, o, lang="", run=None: {"language": "es", "text": "Hola a todos", "segments": []})
    c = FakeComfy(); rec = {"job": "dub-abc123", "clip_info": {"seconds": 5.0, "width": 600, "height": 600}}
    F.dub_job(rec, clip, {"mode": "dubit", "language": "es", "text": "Hola a todos", "seed": 3, "permission": True}, comfy=c, mark=lambda a, b: shutil.copy(a, b))
    assert rec["status"] == "done", rec.get("error"); assert rec["wer"] == 0.0 and rec["file"]["subfolder"] == "dub" and "DubIt" in rec["model"]
    assert c.graphs[0]["src"]["inputs"]["file"] == "up_talk.mp4" and c.graphs[0]["noise"]["inputs"]["noise_seed"] == 3
    receipt = json.loads((folders / "out" / "dub" / (rec["file"]["filename"] + ".json")).read_text()); assert receipt["ai_generated"] and receipt["permission_confirmed"]


def test_a_cloned_voice_dub_keeps_the_consent_beside_it(folders, monkeypatch):
    clip = folders / "out" / "video" / "talk.mp4"; calls = []
    monkeypatch.setattr(F, "to16k", lambda src, dst, run=None: Path(dst)); monkeypatch.setattr(F, "listen", lambda w, o, lang="", run=None: {"language": "es", "text": "hola", "segments": []})
    monkeypatch.setattr(F, "steps", lambda args, run=None, timeout=0: calls.append(args) or {"seconds": 5.5})
    def run(cmd, **k):
        Path(cmd[-1]).write_bytes(b"x"); return subprocess.CompletedProcess(cmd, 0, "", "")
    rec = {"job": "dub-xyz789", "clip_info": {"seconds": 5.0, "width": 600, "height": 600}}
    F.dub_job(rec, clip, {"mode": "voice", "voice": "clone", "consent": "permission", "language": "es", "text": "hola", "seed": 7, "source_text": "hello"}, run=run, mark=lambda a, b: shutil.copy(a, b))
    assert rec["status"] == "done", rec.get("error"); assert calls[0][:4] == ["speak", "--model", "qwen3_base_17", "--language"] and "--reference-consent" in calls[0] and rec["tempo"] == 1.1
    c = json.loads((folders / "out" / "dub" / (rec["file"]["filename"] + ".consent.json")).read_text()); assert c["consent"] == "permission" and c["ai_generated"]


def test_a_failing_step_is_an_error_not_a_crash(folders):
    rec = {"job": "dub-err000", "clip_info": {"seconds": 5.0}}
    class Bad(FakeComfy):
        def run(self, g): raise RuntimeError("ComfyUI stopped: out of memory")
    F.dub_job(rec, folders / "out" / "video" / "talk.mp4", {"mode": "dubit", "language": "es", "text": "x", "seed": 1}, comfy=Bad(), mark=lambda a, b: None)
    assert rec["status"] == "error" and "out of memory" in rec["error"]


def test_relip_goes_through_the_motion_route_over_http():
    calls = []
    def post(url, data): calls.append((url, data)); return {"job": "mot-1"}
    states = iter([{"status": "running"}, {"status": "done", "file": "motion/latentsync_x.mp4"}])
    out = F.motion_relip("v.mp4", "a.wav", base="http://studio", get=lambda url: next(states), post=post)
    assert out == "motion/latentsync_x.mp4" and calls[0][0] == "http://studio/api/motion/run" and calls[0][1]["route"] == "latentsync" and calls[0][1]["permission"] is True


# ---------- the runner and what ships
def test_the_runner_reads_local_weights_only_and_needs_a_yes_to_clone():
    assert "import voice_speak as V" in RUNNER and "download" not in RUNNER.split('"""', 2)[2].lower().replace("nothing is downloaded", "")
    assert 'raise SystemExit("a reference clip needs --reference-consent' in RUNNER and 'task="translate"' in RUNNER and 'choices=["own", "permission", "synthetic"]' in RUNNER


def test_no_box_path_in_what_ships():
    for f in (ROOT / "studio" / "feature_dub.py", ROOT / "studio" / "audio_master.py", WEB / "dub.js", WEB / "dub_logic.js", WEB / "dub.css", ROOT / "studio" / "worldkit" / "runners" / "dub_steps.py", ROOT / "workflows" / "dub_ltx_api.json"):
        t = f.read_text(encoding="utf-8"); assert "/mnt/" not in t and "/home/" not in t, f.name
    p = ROOT / "studio" / "dub_proof.json"
    if p.exists(): t = p.read_text(encoding="utf-8"); assert "/mnt/" not in t and "/home/" not in t


def test_the_proof_media_are_there_and_say_nobody_listened():
    p = F.proof()
    if not p: pytest.skip("no proof yet")
    assert "Nobody has listened" in p["note"] and "no person has listened" in F.PAGE["title"][2].lower()
    for v in (p.get("media") or {}).values(): assert (WEB / v).is_file(), v
    if p.get("master"): assert p["master"]["report"]["master"]["passes"] and p["master"]["report"]["ducking"]["depth_db"] >= 8


def test_the_page_closes_components_the_house_way():
    t = (WEB / "dub.js").read_text(encoding="utf-8"); assert "<//>" in t and not re.search(r"</\$\{", t)


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_the_page_logic():
    code = r'''
import * as L from "./dub_logic.js"; import assert from "node:assert";
assert.equal(L.werWord(0.25), "75% of words heard as written (WER 0.25)"); assert.equal(L.werWord(null), "not measured");
const rep = {master: {final: {lufs: -14.1, true_peak: -1.3}, target_lufs: -14, target_tp: -1, tolerance: 0.5}, ducking: {depth_db: 12}};
assert.deepEqual(L.masterChecks(rep).map((c) => c.ok), [true, true, true]);
rep.master.final.true_peak = -0.7; rep.ducking.depth_db = 6; assert.deepEqual(L.masterChecks(rep).map((c) => c.ok), [true, false, false]);
const f = {mode: "voice", voice: "clone", consent: "", text: "hola", language: "es", permission: true};
assert.equal(L.dubBlocked("c", f, {tts: {ready: true}}), "Say whose voice it is before cloning it.");
assert.equal(L.dubBlocked("c", {...f, consent: "own"}, {tts: {ready: true}}), "");
assert.equal(L.dubBlocked("c", {...f, mode: "dubit"}, {dubit: {ready: false, why_not: "needs download: x"}}), "needs download: x");
assert.equal(L.dubBlocked("", f, {}), "Pick a clip first.");
const b = L.dubBody({filename: "a.mp4"}, {...f, consent: "own", scene: "x"}); assert.equal(b.voice, "clone"); assert.equal(b.consent, "own"); assert.equal(b.scene, undefined);
assert.equal(L.dubBody({}, {...f, mode: "dubit", scene: " s "}).scene, "s");
assert.match(L.lengthNote("we chart by the stars", "navegamos por las estrellas cuando los instrumentos se callan"), /longer/);
assert.equal(L.lengthNote("hello there", "hola amigo"), "Close to the original's length.");
'''
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(WEB / "dub_logic.js", t); (Path(t) / "x.mjs").write_text(code)
        p = subprocess.run(["node", str(Path(t) / "x.mjs")], cwd=t, capture_output=True, text=True, timeout=60)
        assert p.returncode == 0, p.stderr


def test_a_comfyui_with_a_forced_half_precision_vae_is_refused_for_dubit():
    got = lambda argv: (lambda u: {"system": {"argv": argv}})
    assert "--bf16-vae" in F.vae_problem("http://x", get=got(["main.py", "--bf16-vae"])) and "--fp32-vae" in F.vae_problem("http://x", get=got(["main.py", "--fp16-vae"]))
    assert F.vae_problem("http://x", get=got(["main.py", "--fp32-vae"])) == "" and F.vae_problem("http://x", get=lambda u: (_ for _ in ()).throw(OSError())) == ""
