"""Captions & Sound: caption rules, routes, the runner's contract and the proof. Stubbed: no ComfyUI, no Whisper, no live port."""
import json, re, shutil, subprocess, tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from studio import captions as C, feature_clipsound as F, foley as FO, server as S

ROOT = Path(__file__).resolve().parents[1]; WEB = ROOT / "studio" / "web"
RUNNER = (ROOT / "studio" / "worldkit" / "runners" / "caption_listen.py").read_text(encoding="utf-8")


def seg(text, start=0.0, end=2.0, words=None, ns=0.01, lp=-0.2, cr=1.1):
    if words is None:
        toks = text.split(); step = (end - start) / max(1, len(toks)); words = [[start + i * step, start + (i + 1) * step, t, 0.95] for i, t in enumerate(toks)]
    return {"start": start, "end": end, "text": text, "no_speech": ns, "logprob": lp, "compression": cr, "words": words}


@pytest.fixture
def client(): return TestClient(S.app)


@pytest.fixture
def folders(monkeypatch, tmp_path):
    (tmp_path / "in").mkdir(); (tmp_path / "out" / "video").mkdir(parents=True)
    (tmp_path / "out" / "video" / "talk.mp4").write_bytes(b"x"); (tmp_path / "in" / "up.mov").write_bytes(b"x"); (tmp_path / "out" / "secret.txt").write_text("x")
    monkeypatch.setattr(F.paths, "comfy_input", lambda *_: str(tmp_path / "in")); monkeypatch.setattr(F.paths, "output_dir", lambda *_: str(tmp_path / "out"))
    monkeypatch.setattr(F.paths, "models_root", lambda *_: str(tmp_path / "models"))
    return tmp_path


# ---------- caption rules
def test_whispers_stock_phrases_over_silence_are_dropped_and_real_speech_kept():
    fake = seg("Thank you.", ns=0.139, lp=-0.82, words=[[0.1, 0.5, "Thank", 0.5], [0.5, 0.6, "you.", 0.55]])
    assert C.why_dropped(fake) == "stock phrase over no speech"
    said = seg("Thank you.", ns=0.01, lp=-0.1, words=[[0.1, 0.5, "Thank", 0.97], [0.5, 0.6, "you.", 0.98]])
    assert C.why_dropped(said) == ""      # a clear "thank you" stays
    assert C.why_dropped(seg("no screens after 10, same wake time")) == ""
    assert C.why_dropped(seg("m-m-m-m-m-m-m-m", cr=3.1)) == "repeats itself"
    assert C.why_dropped(seg("something", ns=0.8, lp=-1.4)) == "silence read as words"
    kept, dropped = C.split_kept([fake, seg("hello there")]); assert len(kept) == 1 and dropped[0]["text"] == "Thank you."


def test_text_is_cleaned_before_it_reaches_libass():
    assert C.clean("{\\an8}<i>hi</i>\x07 there") == "(/an8)ihi/i there"
    assert C.srt(C.cues([seg("{\\b1} bold")])).count("{") == 0


def test_cues_break_at_sentences_pauses_and_length_and_never_overlap():
    a = seg("This little robot directs every shot.", 0.0, 2.5); b = seg("Whisper wrote these words down, and ffmpeg drew them in a real font.", 3.1, 7.4)
    cs = C.cues([a, b], width=42); assert [" ".join(c["lines"]) for c in cs] == [a["text"], b["text"]]
    assert all(len(line) <= 42 for c in cs for line in c["lines"]) and all(len(c["lines"]) <= 2 for c in cs)
    long = seg(" ".join(["word"] * 60), 0, 30); cs = C.cues([long], width=20)
    assert len(cs) > 3 and all(c["end"] - c["start"] <= 6.0 + 1e-6 for c in cs)
    assert all(cs[i]["end"] <= cs[i + 1]["start"] for i in range(len(cs) - 1))
    paused = C.cues([seg("one two", 0, 1), seg("three four", 3, 4)], width=42); assert len(paused) == 2
    short = C.cues([seg("hi", 1.0, 1.1)]); assert short[0]["end"] - short[0]["start"] >= 0.8 - 1e-6


def test_a_segment_without_word_times_still_makes_cues():
    cs = C.cues([{"start": 1, "end": 3, "text": "no word times here", "words": []}]); assert cs and cs[0]["start"] == 1 and " ".join(cs[0]["lines"]) == "no word times here"


def test_srt_and_vtt_are_well_formed():
    cs = [{"start": 0.05, "end": 2.57, "lines": ["This little robot", "directs every shot."]}, {"start": 3661.5, "end": 3662.0, "lines": ["Tom & Jerry"]}]
    s = C.srt(cs); assert s.startswith("1\n00:00:00,050 --> 00:00:02,570\nThis little robot\ndirects every shot.\n\n2\n01:01:01,500 --> 01:01:02,000\n")
    v = C.vtt(cs); assert v.startswith("WEBVTT\n\n00:00:00.050 --> 00:00:02.570\n") and "Tom &amp; Jerry" in v
    assert C.transcript(cs) == "This little robot directs every shot. Tom & Jerry"


def test_a_tall_clip_gets_smaller_type_and_shorter_lines():
    wide, tall = C.layout(1280, 720), C.layout(672, 1216)
    assert tall[0] < wide[0] and tall[1] < wide[1] and wide[1] == 42
    for size in C.SIZES:
        pt, chars = C.layout(672, 1216, size); assert 4 <= pt <= 30 and 12 <= chars <= 42
    assert C.layout(0, 0) == C.layout(16, 9)


def test_the_burn_command_keeps_paths_out_of_the_filter_and_the_sound_untouched():
    cmd = C.burn_command("ffmpeg", "/a b/clip.mp4", "c.srt", "/x/out.mp4", "box", 18, "top")
    vf = cmd[cmd.index("-vf") + 1]; assert vf.startswith("subtitles=filename=c.srt:") and "Alignment=8" in vf and "BorderStyle=3" in vf
    assert cmd[cmd.index("-c:a") + 1] == "copy" and "/a b/clip.mp4" in cmd
    assert "aac" in C.burn_command("ffmpeg", "c.mp4", "c.srt", "o.mp4", copy_audio=False)
    for bad in ("../c.srt", "c.srt:force_style=x", "c'.srt", "c.ass"):
        with pytest.raises(ValueError): C.burn_command("ffmpeg", "c.mp4", bad, "o.mp4")
    assert "Alignment=2" in C.force_style("nope", 18, "nowhere") and "Fontsize=60" in C.force_style("box", 900)


# ---------- routes
def test_models_lists_the_listeners_with_their_licences(client, monkeypatch):
    monkeypatch.setattr("studio.feature_voices.missing", lambda m, root=None: [])
    d = client.get("/api/clipsound/models").json()
    ids = [m["id"] for m in d["listeners"]]; assert ids == list(F.LISTENERS)
    for m in d["listeners"]: assert m["licence"]["name"] and m["card"].startswith("https://") and m["ready"]
    assert next(m for m in d["listeners"] if m["id"] == "whisper_ct2_distil")["english_only"]
    assert d["styles"] == list(C.STYLES) and "captions" in d["proof"]


def test_a_clip_must_be_a_video_inside_the_studio_folders(client, folders, monkeypatch):
    monkeypatch.setattr("studio.feature_voices.missing", lambda m, root=None: [])
    for clip, code in (({"filename": "../../etc/passwd", "type": "output"}, 404), ({"filename": "talk.mp4", "subfolder": "..", "type": "output"}, 404),
                       ({"filename": "secret.txt", "type": "output"}, 400), ({"filename": "talk.mp4", "subfolder": "video", "type": "temp"}, 400), (None, 400)):
        r = client.post("/api/clipsound/captions", json={"clip": clip}); assert r.status_code == code, (clip, r.text)


def test_bad_options_are_refused_before_anything_runs(client, folders):
    good = {"filename": "talk.mp4", "subfolder": "video"}
    for body in ({"model": "whisper_huge"}, {"style": "neon"}, {"size": "giant"}, {"place": "middle"}, {"language": "english; rm"}):
        r = client.post("/api/clipsound/captions", json={"clip": good, **body}); assert r.status_code == 400, body


def test_a_silent_clip_and_a_wrong_language_are_refused(client, folders, monkeypatch):
    monkeypatch.setattr("studio.feature_voices.missing", lambda m, root=None: [])
    monkeypatch.setattr(F, "probe", lambda p: {"seconds": 5, "width": 640, "height": 360, "audio": None})
    r = client.post("/api/clipsound/captions", json={"clip": {"filename": "talk.mp4", "subfolder": "video"}}); assert r.status_code == 400 and "no sound" in r.json()["detail"]
    monkeypatch.setattr(F, "probe", lambda p: {"seconds": 5, "width": 640, "height": 360, "audio": "aac"})
    r = client.post("/api/clipsound/captions", json={"clip": {"filename": "talk.mp4", "subfolder": "video"}, "language": "es"}); assert r.status_code == 400 and "English" in r.json()["detail"]


def test_missing_weights_say_which_file(client, folders, monkeypatch):
    monkeypatch.setattr("studio.feature_voices.missing", lambda m, root=None: ["_by_repo/x/model.bin"])
    r = client.post("/api/clipsound/captions", json={"clip": {"filename": "talk.mp4", "subfolder": "video"}}); assert r.status_code == 409 and "model.bin" in r.json()["detail"]


def test_a_good_request_starts_a_job_on_the_cpu_by_default(client, folders, monkeypatch):
    monkeypatch.setattr("studio.feature_voices.missing", lambda m, root=None: [])
    monkeypatch.setattr(F, "probe", lambda p: {"seconds": 5, "width": 640, "height": 360, "audio": "aac"}); started = []
    monkeypatch.setattr(F.threading, "Thread", lambda target, args, **k: type("T", (), {"start": lambda self: started.append(args)})())
    r = client.post("/api/clipsound/captions", json={"clip": {"filename": "up.mov", "type": "input"}, "model": "whisper_ct2_large3", "language": "es", "burn": True}); assert r.status_code == 200, r.text
    job = r.json(); assert job["status"] == "running" and client.get("/api/clipsound/jobs/" + job["job"]).json()["clip"] == "up.mov"
    cmd = F.listen_command("whisper_ct2_large3", "a.wav", "o.json", "es"); assert cmd[cmd.index("--device") + 1] == "cpu" and cmd[-2:] == ["--language", "es"]
    monkeypatch.setenv("STUDIO_CAPTION_DEVICE", "cuda"); assert "cuda" in F.listen_command("whisper_ct2_tiny", "a", "b")
    assert client.get("/api/clipsound/jobs/nope").status_code == 404


def test_the_job_writes_srt_vtt_and_a_burned_copy(folders, monkeypatch):
    heard = {"language": "en", "speech_seconds": 4.0, "wall_s": 1.0, "segments": [seg("Thank you.", 0, 0.5, ns=0.2, lp=-0.9), seg("Hello there, this is a test.", 1.0, 3.0)]}
    calls = []
    def run(cmd, **kw):
        calls.append((cmd, kw))
        if "--out" in cmd: Path(cmd[cmd.index("--out") + 1]).write_text(json.dumps(heard))
        if "-vf" in cmd: assert (Path(kw["cwd"]) / "c.srt").read_text().startswith("1\n"); Path(cmd[-1]).write_bytes(b"mp4")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    clip = folders / "out" / "video" / "talk.mp4"; rec = {"job": "cap-abcdef123456", "clip_info": {"width": 1280, "height": 720}}
    F.caption_job(rec, clip, F.options({"burn": True}), run=run)
    assert rec["status"] == "done", rec.get("error")
    assert rec["text"] == "Hello there, this is a test." and rec["dropped"][0]["text"] == "Thank you." and set(rec["files"]) == {"srt", "vtt", "words", "video"}
    out = folders / "out" / "captions"; srt = next(out.glob("*.srt")).read_text(); assert "Hello there" in srt and "Thank you" not in srt
    assert next(out.glob("*.vtt")).read_text().startswith("WEBVTT") and next(out.glob("*_captioned.mp4")).exists()
    assert rec["files"]["video"]["url"].startswith("/api/view?") and "subfolder=captions" in rec["files"]["video"]["url"]


def test_no_speech_means_no_burn_and_a_plain_note(folders):
    def run(cmd, **kw):
        if "--out" in cmd: Path(cmd[cmd.index("--out") + 1]).write_text(json.dumps({"segments": []}))
        assert "-vf" not in cmd; return subprocess.CompletedProcess(cmd, 0, "", "")
    rec = {"job": "cap-000000000000", "clip_info": {"width": 640, "height": 360}}; F.caption_job(rec, folders / "out" / "video" / "talk.mp4", F.options({"burn": True}), run=run)
    assert rec["status"] == "done" and "no speech" in rec["note"] and "video" not in rec["files"]


def test_a_failing_step_is_an_error_not_a_crash(folders):
    rec = {"job": "cap-111111111111", "clip_info": {}}
    F.caption_job(rec, folders / "out" / "video" / "talk.mp4", F.options({}), run=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "boom"))
    assert rec["status"] == "error" and "boom" in rec["error"]


def test_the_picker_lists_only_videos_and_not_the_captions_folder(client, folders):
    (folders / "out" / "captions").mkdir(); (folders / "out" / "captions" / "x_captioned.mp4").write_bytes(b"x"); (folders / "out" / "top.webm").write_bytes(b"x")
    rows = client.get("/api/clipsound/clips").json()["clips"]
    assert {(r["subfolder"], r["filename"]) for r in rows} == {("video", "talk.mp4"), ("", "top.webm")}


# ---------- the runner
def test_the_runner_reads_local_weights_only_and_knows_every_listener():
    assert set(re.findall(r'"(whisper_ct2_\w+)": \(', RUNNER)) == set(F.LISTENERS)
    assert "WhisperModel(folder(" in RUNNER and "download_root" not in RUNNER and "vad_filter=True" in RUNNER and "word_timestamps=True" in RUNNER
    assert "from voice_speak import m, view" in RUNNER


# ---------- proof and page
def test_the_proof_is_measured_says_nobody_listened_and_its_files_are_there():
    p = F.proof(); rows = [p["captions"], *p["captions_more"]]
    for r in rows:
        assert (WEB / r["src"]).is_file() and (WEB / r["poster"]).is_file() and r["alt"]
        assert "Nobody has listened" in r["measured"] and r["device"] == "cpu" and r["peak_vram_gib"] == 0 and 0 < r["ocr_match_pct"] <= 100 and r["audio_same"] is True
    assert p["captions"]["word_match_pct"] >= 90 and "synthetic" in p["captions"]["voice"]
    assert "No person has listened" in F.PAGE["title"][2]


def test_no_box_path_in_what_ships():
    for f in (ROOT / "studio" / "feature_clipsound.py", ROOT / "studio" / "captions.py", ROOT / "studio" / "clipsound_proof.json", WEB / "clipsound.js", WEB / "clipsound_logic.js", ROOT / "studio" / "worldkit" / "runners" / "caption_listen.py"):
        t = f.read_text(encoding="utf-8"); assert "/mnt/" not in t and "/home/" not in t, f.name


def test_the_page_closes_components_the_house_way():
    t = (WEB / "clipsound.js").read_text(encoding="utf-8"); assert "<//>" in t and not re.search(r"</\$\{", t)


def test_the_hero_keeps_its_controls_off_the_burned_captions():
    """The native bar only shows on hover or focus; a 44 px play button below the frame is always there."""
    js = (WEB / "clipsound.js").read_text(encoding="utf-8"); css = (WEB / "clipsound.css").read_text(encoding="utf-8")
    hero = js[js.index("function HeroVideo"):js.index("function Hero(")]
    assert "controls=${heroControls(hover, focus)}" in hero and not re.search(r"<video[^>]* controls[ >]", hero)
    assert 'tabindex="0"' in hero and "onFocus=" in hero and "onBlur=" in hero and '<button type="button" class="cs-play"' in hero and "aria-pressed=" in hero
    rule = re.search(r"\.cs-play\{([^}]*)\}", css).group(1); assert "min-height:44px" in rule and "min-width:44px" in rule


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_the_page_logic():
    code = r'''
import * as L from "./clipsound_logic.js"; import assert from "node:assert";
assert.equal(L.clock(75.25), "1:15.3"); assert.equal(L.clock(-1), "0:00.0"); assert.equal(L.clock(3.04), "0:03.0");
assert.deepEqual(L.licenceWord({ commercial: true }), ["Commercial use OK", "ok"]); assert.equal(L.licenceWord(null)[1], "warn"); assert.equal(L.licenceWord({ name: "x" })[1], "warn");
const c = [{ start: 0, end: 2, lines: ["a"] }, { start: 2, end: 3, lines: ["b"] }]; assert.equal(L.cueAt(c, 2).lines[0], "b"); assert.equal(L.cueAt(c, 5), null);
assert.deepEqual(L.clipRef("output:video/sub/a.mp4"), { type: "output", subfolder: "video/sub", filename: "a.mp4" }); assert.deepEqual(L.clipRef("input:x.mov"), { type: "input", subfolder: "", filename: "x.mov" });
assert.equal(L.clipKey({ type: "output", subfolder: "video", filename: "a.mp4" }), "output:video/a.mp4"); assert.equal(L.clipRef(""), null);
const en = L.captionBody("output:a.mp4", { id: "whisper_ct2_distil", english_only: true }, { language: "ES", burn: 1, style: "box", size: "large", place: "top" }); assert.equal(en.language, ""); assert.equal(en.burn, true);
assert.equal(L.captionBody("output:a.mp4", { id: "x", english_only: false }, { language: " ES " }).language, "es");
assert.equal(L.canCaption("", { ready: true }), false); assert.equal(L.canCaption("output:a.mp4", { ready: false }), false); assert.equal(L.canCaption("output:a.mp4", { ready: true }), true);
assert.ok(L.viewUrl({ filename: "a b.mp4", subfolder: "v", type: "input" }).includes("a%20b.mp4")); assert.equal(L.secs(4.44), "4.4 s"); assert.equal(L.secs(null), "not measured");
const sm = { id: "controlfoley", ready: true };
assert.equal(L.canSound("output:a.mp4", sm, { noncommercial: false }), false); assert.equal(L.canSound("output:a.mp4", sm, { noncommercial: "yes" }), false); assert.equal(L.canSound("output:a.mp4", sm, { noncommercial: true }), true);
assert.equal(L.canSound("output:a.mp4", { ready: false }, { noncommercial: true }), false); assert.equal(L.soundBody("output:a.mp4", sm, { noncommercial: 1 }).noncommercial, false);
const sb = L.soundBody("output:v/a.mp4", sm, { prompt: " rain ", seed: "", steps: "40", noncommercial: true }); assert.equal(sb.prompt, "rain"); assert.equal(sb.seed, 42); assert.equal(sb.steps, 40); assert.equal(sb.noncommercial, true);
assert.equal(L.lufs(-23.04), "-23 LUFS"); assert.equal(L.lufs(null), "not measured");
assert.equal(L.heroControls(false, false), false); assert.equal(L.heroControls(true, false), true); assert.equal(L.heroControls(false, true), true);
console.log("ok");
'''
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(WEB / "clipsound_logic.js", t); (Path(t) / "x.mjs").write_text(code)
        p = subprocess.run(["node", str(Path(t) / "x.mjs")], cwd=t, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and "ok" in p.stdout, p.stderr


# ---------- add sound (ControlFoley)
GRAPH = json.loads((ROOT / "workflows" / FO.GRAPH).read_text(encoding="utf-8"))
LEVEL = """[Parsed_loudnorm_0 @ 0x1]
{
	"input_i" : "-12.36",
	"input_tp" : "0.52",
	"input_lra" : "0.60",
	"input_thresh" : "-22.40",
	"output_i" : "-16.02",
	"target_offset" : "0.02"
}
"""
EBUR = """[Parsed_ebur128_0 @ 0x1] t: 7.9  M: -20.1 S: -21.0 I: -22.0 LUFS
[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:         -23.4 LUFS
    Threshold: -33.9 LUFS

  Loudness range:
    LRA:         5.2 LU

  True peak:
    Peak:       -3.1 dBFS
"""


@pytest.fixture
def ready(tmp_path, monkeypatch):
    """A machine with the source, weights and Hugging Face cache ControlFoley needs, all fake."""
    comfy, models, hub = tmp_path / "comfy", tmp_path / "models", tmp_path / "hub"
    (comfy / "controlfoley" / "controlfoley").mkdir(parents=True); (comfy / "controlfoley" / "demo.py").write_text(""); (comfy / "controlfoley" / "controlfoley" / "inference_utils.py").write_text("")
    for f in FO.WEIGHTS: (models / "controlfoley" / "model_weights" / f).parent.mkdir(parents=True, exist_ok=True); (models / "controlfoley" / "model_weights" / f).write_bytes(b"w")
    monkeypatch.setattr(FO, "_cached", lambda repo, hub: True)
    monkeypatch.setattr(FO, "comfy_dir", lambda: comfy); monkeypatch.setattr(FO, "hf_hub", lambda: hub); monkeypatch.setattr(FO.paths, "models_root", lambda *_: str(models))
    return tmp_path


def good_sound(**kw): return {"clip": {"filename": "talk.mp4", "subfolder": "video"}, "noncommercial": True, **kw}


def test_sound_is_refused_without_the_noncommercial_promise():
    for b in ({}, {"noncommercial": False}, {"noncommercial": "true"}, {"noncommercial": 1}):
        with pytest.raises(ValueError, match="non-commercial"): FO.options(b)
    o = FO.options({"noncommercial": True}); assert o == {"model": "controlfoley", "prompt": "", "negative": "", "seed": 42, "steps": 25, "cfg": 4.5, "noncommercial": True}
    for bad in ({"seed": -1}, {"seed": "x"}, {"steps": 7}, {"cfg": 50}, {"model": "mmaudio"}):
        with pytest.raises(ValueError): FO.options({"noncommercial": True, **bad})
    assert FO.options({"noncommercial": True, "prompt": "rain ${x} {\\b1}\x07 on glass"})["prompt"] == "rain x b1 on glass"


def test_the_model_is_never_a_default_and_shows_every_licence():
    m = FO.MODELS[0]; assert m["default"] is False and m["commercial"] is False and m["label_short"] == "Non-commercial (CC BY-NC 4.0)"
    names = {l["name"]: l for l in m["licences"]}; cf = m["licences"][0]; assert cf["what"].startswith("ControlFoley weights")
    assert cf["url"].startswith("https://creativecommons.org/licenses/by-nc/4.0") and "CC BY-NC 4.0" in cf["quote"] and cf["commercial"] is False
    apple = names["Apple Machine Learning Research Model License"]; assert apple["research_only"] and apple["url"].endswith("DFN5B-CLIP-ViT-H-14-384/blob/main/LICENSE") and "commercial product" in apple["quote"]
    assert all(l["url"].startswith("https://") for l in m["licences"]) and "non-commercial" in m["strictest"].lower()
    for f in (ROOT / "studio" / "goals.py", ROOT / "studio" / "recipes.json", ROOT / "studio" / "edits.py", ROOT / "studio" / "feature_oneclick.py"):
        assert "controlfoley" not in f.read_text(encoding="utf-8").lower(), f.name      # no default flow reaches it


def test_readiness_names_what_is_missing_and_never_downloads(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    gone = FO.missing(tmp_path / "m", tmp_path / "c", tmp_path / "h")
    assert gone[0].startswith("ControlFoley source code") and "controlfoley/model_weights/weights/controlfoley.pth" in gone and "Hugging Face cache: apple/DFN5B-CLIP-ViT-H-14-384" in gone and len(gone) == 1 + len(FO.WEIGHTS) + len(FO.HF_REPOS)
    asked = []; import huggingface_hub
    def probe(repo_id, cache_dir, local_files_only):
        asked.append((repo_id, local_files_only))
        if repo_id == "t5-base": raise FileNotFoundError("incomplete snapshot")
        d = Path(cache_dir) / repo_id.replace("/", "--"); d.mkdir(parents=True, exist_ok=True)
        (d / ("tokenizer.json" if repo_id == "roberta-base" else "model.safetensors")).write_text("x"); return str(d)
    monkeypatch.setattr(huggingface_hub, "snapshot_download", probe)
    assert [g for g in FO.missing(tmp_path / "m", tmp_path / "c", tmp_path / "h") if g.startswith("Hugging Face")] == ["Hugging Face cache: roberta-base", "Hugging Face cache: t5-base"]       # a tokenizer-only cache is not enough
    assert {r for r, _ in asked} == set(FO.HF_REPOS) and all(lf is True for _, lf in asked)       # the node's own offline question, never a download


def test_ready_machine(ready): assert FO.missing() == []


def test_the_graph_is_local_only_and_fully_filled():
    n = {k: v["class_type"] for k, v in GRAPH.items()}
    assert n == {"model": "LoadControlFoleyModel", "video": "LoadControlFoleyVideo", "gen": "ControlFoleyGenerate", "save": "SaveControlFoleyAudio", "unload": "UnloadControlFoleyModel"}
    mi = GRAPH["model"]["inputs"]; assert mi["auto_fetch_source"] is False and mi["low_vram"] is False and mi["device"] == "cuda" and mi["model_weights_dir"] == "${weights_dir}"
    assert GRAPH["unload"]["inputs"]["after"] == ["save", 0] and GRAPH["gen"]["inputs"]["reference_audio_path"] == ""
    txt = json.dumps(GRAPH); assert "/mnt/" not in txt and "/home/" not in txt
    o = FO.options({"noncommercial": True, "prompt": "rain"}); g = F.sound_graph("/x/clip.mp4", 41.0, o, "clipsound/x_sound", root="/models")
    assert "${" not in json.dumps(g) and g["video"]["inputs"]["duration"] == FO.MAX_SECONDS and g["gen"]["inputs"]["seed"] == 42 and g["gen"]["inputs"]["num_inference_steps"] == "25"
    assert g["model"]["inputs"]["model_weights_dir"] == str(Path("/models") / "controlfoley" / "model_weights") and g["gen"]["inputs"]["prompt"] == "rain"
    assert F.sound_graph("/x/c.mp4", 0.2, o, "p")["video"]["inputs"]["duration"] == FO.MIN_SECONDS


def test_the_sound_is_muxed_without_touching_the_picture_and_loudness_is_read():
    cmd = FO.mux_command("ffmpeg", "/a/clip.mp4", "/a/s.wav", "/a/o.mp4", 5.0416)
    assert cmd[cmd.index("-c:v") + 1] == "copy" and ["-map", "0:v:0"] == cmd[cmd.index("-map"):cmd.index("-map") + 2] and "1:a:0" in cmd
    assert "-shortest" not in cmd and cmd[cmd.index("-af") + 1].startswith("atrim=end=5.042,loudnorm=I=-16.0:TP=-1.5")      # -shortest with a copied picture drops its last frames
    assert FO.parse_level(LEVEL) == {"input_i": -12.36, "input_tp": 0.52, "input_lra": 0.6, "input_thresh": -22.4, "target_offset": 0.02} and FO.parse_level("no json") is None
    assert FO.parse_level(LEVEL.replace('"-12.36"', '"-inf"')) is None and "print_format=json" in FO.level_measure_command("ffmpeg", "s.wav", 5)[6]
    assert FO.parse_loudness(EBUR) == {"lufs": -23.4, "lra": 5.2, "true_peak_db": -3.1} and FO.parse_loudness("") == {"lufs": None, "lra": None, "true_peak_db": None}
    assert "ebur128=peak=true" in FO.loudness_command("ffmpeg", "s.wav")


def test_models_route_lists_the_sounder(client, ready):
    s = client.get("/api/clipsound/models").json()["sounders"]; assert len(s) == 1 and s[0]["id"] == "controlfoley" and s[0]["ready"] and s[0]["label_short"].startswith("Non-commercial")


def test_sound_route_refusals(client, folders, ready, monkeypatch):
    r = client.post("/api/clipsound/sound", json={"clip": {"filename": "talk.mp4", "subfolder": "video"}}); assert r.status_code == 400 and "non-commercial" in r.json()["detail"]
    r = client.post("/api/clipsound/sound", json=good_sound(clip={"filename": "../../etc/passwd"})); assert r.status_code == 404
    monkeypatch.setattr(F, "probe", lambda p: {"seconds": 45.0, "width": 640, "height": 360, "audio": None})
    r = client.post("/api/clipsound/sound", json=good_sound()); assert r.status_code == 400 and "30 s" in r.json()["detail"]
    monkeypatch.setattr(FO, "missing", lambda *a: ["Hugging Face cache: nvidia/bigvgan_v2_44khz_128band_512x"])
    r = client.post("/api/clipsound/sound", json=good_sound()); assert r.status_code == 409 and "bigvgan" in r.json()["detail"] and "won't download" in r.json()["detail"]


def test_a_good_sound_request_starts_a_job(client, folders, ready, monkeypatch):
    monkeypatch.setattr(F, "probe", lambda p: {"seconds": 8.0, "width": 640, "height": 360, "audio": "aac"}); started = []
    monkeypatch.setattr(F.threading, "Thread", lambda target, args, **k: type("T", (), {"start": lambda self: started.append((target, args))})())
    r = client.post("/api/clipsound/sound", json=good_sound(prompt="footsteps")); assert r.status_code == 200, r.text
    job = r.json(); assert job["kind"] == "sound" and job["replaces_sound"] is True and job["options"]["noncommercial"] is True and started[0][0] is F.sound_job


def test_the_sound_job_runs_the_graph_muxes_and_writes_a_licence_note(folders, ready):
    out = folders / "out"; (out / "clipsound").mkdir(); wav = out / "clipsound" / "talk_sound_00001_.wav"; wav.write_bytes(b"RIFF")
    sent, calls = [], []
    def comfy(path, payload=None, timeout=30):
        if path == "/prompt": sent.append(payload["prompt"]); return {"prompt_id": "p1"}
        return {"p1": {"status": {"completed": True, "status_str": "success"}, "outputs": {"save": {"audio": [{"filename": wav.name, "subfolder": "clipsound", "type": "output"}]}}}}
    def run(cmd, **kw):
        calls.append(cmd)
        if "-c:v" in cmd: Path(cmd[-1]).write_bytes(b"mp4")
        lev = any("print_format=json" in str(c) for c in cmd)
        return subprocess.CompletedProcess(cmd, 0, "", EBUR if "ebur128=peak=true" in cmd else LEVEL if lev else "")
    clip = out / "video" / "talk.mp4"; rec = {"job": "snd-abcdef123456", "clip_info": {"seconds": 8.0}}
    F.sound_job(rec, clip, FO.options({"noncommercial": True}), run=run, comfy=comfy, sleep=lambda s: None)
    assert rec["status"] == "done", rec.get("error")
    assert sent[0]["video"]["inputs"]["video_path"] == str(clip) and sent[0]["save"]["inputs"]["filename_prefix"].startswith("clipsound/talk_")
    assert rec["loudness"]["lufs"] == -23.4 and "Nobody has listened" in rec["note"] and rec["label"] == FO.LABEL and set(rec["files"]) == {"video", "wav", "licence"}
    mux = next(c for c in calls if "-c:v" in c); af = mux[mux.index("-af") + 1]
    assert "measured_I=-12.36" in af and "measured_TP=0.52" in af and "TP=-1.5" in af and "I=-16.0" in af and rec["raw_loudness"] == {"lufs": -12.36, "true_peak_db": 0.52}
    assert next(c for c in calls if "ebur128=peak=true" in c)[4].endswith("_with_sound.mp4") and rec["honest"] == FO.HONEST      # loudness of what plays, not the raw take
    note = json.loads(next((out / "clipsound").glob("*.licence.json")).read_text()); assert note["noncommercial_confirmed"] and note["listened"] is False and any("Apple" in l["name"] for l in note["licences"])


def test_a_comfy_failure_is_reported_in_its_own_words(folders, ready):
    def comfy(path, payload=None, timeout=30):
        if path == "/prompt": return {"prompt_id": "p2"}
        return {"p2": {"status": {"status_str": "error", "messages": [["execution_error", {"exception_message": "CUDA out of memory"}]]}}}
    rec = {"job": "snd-000000000000", "clip_info": {"seconds": 5.0}}
    F.sound_job(rec, folders / "out" / "video" / "talk.mp4", FO.options({"noncommercial": True}), run=None, comfy=comfy, sleep=lambda s: None)
    assert rec["status"] == "error" and "CUDA out of memory" in rec["error"]


def test_the_page_puts_the_licence_beside_the_model_picker_and_leaves_the_box_unticked():
    js = (WEB / "clipsound.js").read_text(encoding="utf-8"); snd = js[js.index("function Sound("):js.index("export function ClipSound")]
    assert snd.index("Model<select") < snd.index("<${Licences} m=${m}/>") < snd.index("non-commercial use")
    assert "noncommercial: false" in snd and "canSound(clip, m, f)" in snd and "m.label_short" in js and "l.url" in js and "<q>${l.quote}</q>" in js
    assert "<${Sound} d=${d} clips=${clips}/>" in js
    for f in (ROOT / "studio" / "foley.py", ROOT / "workflows" / FO.GRAPH): t = f.read_text(encoding="utf-8"); assert "/mnt/" not in t and "/home/" not in t, f.name


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg not installed")
def test_the_mux_keeps_every_frame_of_the_picture(tmp_path):
    """A 121-frame clip and a longer, hot sound: the result has the same 121 video packets, byte for byte (the -shortest bug cut 3 or 4),
    and the sound comes out near -16 LUFS with its true peak at or under -1.5 dBTP."""
    clip, wav, out = tmp_path / "c.mp4", tmp_path / "s.wav", tmp_path / "o.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x96:rate=24", "-frames:v", "121", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=5.3", "-af", "volume=7.9", "-ar", "44100", str(wav)], check=True)     # lavfi's sine is 1/8 of full scale; this makes it hot
    level = FO.parse_level(subprocess.run(FO.level_measure_command("ffmpeg", wav, 121 / 24), capture_output=True, text=True).stderr); assert level and level["input_tp"] > -1.0
    subprocess.run(FO.mux_command("ffmpeg", clip, wav, out, 121 / 24, level), check=True)
    loud = FO.parse_loudness(subprocess.run(FO.loudness_command("ffmpeg", out), capture_output=True, text=True).stderr)
    assert abs(loud["lufs"] - FO.TARGET_LUFS) <= 1.0 and loud["true_peak_db"] <= FO.TARGET_TP + 0.05, loud
    pk = lambda f: subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-map", "0:v", "-c", "copy", "-f", "framemd5", "-"], capture_output=True, text=True).stdout.splitlines()
    rows = lambda f: [l.split(",")[-1].strip() for l in pk(f) if l and not l.startswith("#")]
    assert len(rows(clip)) == 121 and rows(out) == rows(clip)
    a = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout)
    assert a <= 121 / 24 + 0.05


def test_the_sound_proof_is_measured_says_nobody_listened_and_states_its_faults():
    p = F.proof(); rows = p["sound"]; assert {r["src"] for r in rows} == {"clipsound/sound_waves.mp4", "clipsound/sound_void.mp4"}
    for r in rows:
        assert (WEB / r["src"]).is_file() and (WEB / r["poster"]).is_file() and r["alt"] and r["listened"] is False and r["picture_same"] is True
        assert "Nobody has listened" in r["measured"] and r["fault"] and 0 < r["peak_vram_gib"] < 96 and r["lufs"] < 0 and r["event_peaks"] and 0 <= r["xcorr"]["p_vs_shifted"] <= 1
    waves = next(r for r in rows if "waves" in r["src"]); assert waves["events_s"] == [4.29, 4.63, 4.92] and "No measurable sync" in waves["fault"]
    for r in rows: assert r["levelled"] and r["true_peak_db"] <= -1.5 and abs(r["lufs"] + 16) <= 1.0 and r["raw_lufs"] is not None
    void = next(r for r in rows if "void" in r["src"]); assert void["raw_true_peak_db"] > 0 and void["true_peak_db"] < 0      # it clipped as generated; it doesn't now
    assert p["sound_honest"] == FO.HONEST == "Generated ambience for the whole clip. It doesn't place sounds on visible events (measured: no better than chance)."
    page = (WEB / "clipsound.js").read_text(encoding="utf-8"); assert FO.MODELS[0]["honest"] == FO.HONEST and "${m.honest}" in page and "${p.sound_honest}" in page
    assert "non-commercial" in p["sound_note"]
    js = (WEB / "clipsound.js").read_text(encoding="utf-8"); assert "<${SoundProof} p=${d.proof}/>" in js and "Measured, not listened to." in js
