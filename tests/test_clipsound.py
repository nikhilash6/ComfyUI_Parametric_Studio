"""Captions & Sound: caption rules, routes, the runner's contract and the proof. Stubbed: no ComfyUI, no Whisper, no live port."""
import json, re, shutil, subprocess, tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from studio import captions as C, feature_clipsound as F, server as S

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
assert.equal(L.heroControls(false, false), false); assert.equal(L.heroControls(true, false), true); assert.equal(L.heroControls(false, true), true);
console.log("ok");
'''
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(WEB / "clipsound_logic.js", t); (Path(t) / "x.mjs").write_text(code)
        p = subprocess.run(["node", str(Path(t) / "x.mjs")], cwd=t, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and "ok" in p.stdout, p.stderr
