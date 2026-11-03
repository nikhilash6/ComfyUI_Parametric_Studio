"""H3 song lock: the graph keeps the song's latent locked, the goal fills it, and the cut keeps the song bit-exact.
The media tests make their own short clips with ffmpeg; nothing here talks to ComfyUI."""
import json, shutil, subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException

from studio import goals, recipes as R, song_lock as SL
from studio.graph_template import fill, placeholders

ROOT = Path(__file__).resolve().parent.parent
GRAPH = json.loads((ROOT / "workflows" / "h3_song_lock_api.json").read_text())
needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def test_graph_locks_the_song_latent():
    by = {k: v for k, v in GRAPH.items()}
    assert by["143"]["class_type"] == "SolidMask" and by["143"]["inputs"]["value"] == 0.0
    assert by["144"]["inputs"] == {"samples": ["142", 0], "mask": ["143", 0]}
    assert by["145"]["class_type"] == "LTXVConcatAVLatent" and by["145"]["inputs"]["audio_latent"] == ["144", 0]
    assert by["125"]["inputs"]["latent_image"] == ["145", 0]
    assert by["141"]["class_type"] == "MiniMaxH3AddGuide" and by["141"]["inputs"]["audio"] == ["trim", 0]
    assert by["126"]["inputs"]["conditioning"] == ["141", 0]
    # the saved video carries the song itself, not H3's decode of it; H3's decode is saved apart for checking
    assert by["130"]["inputs"]["audio"] == ["trim", 0]
    assert by["h3_audio"]["inputs"]["audio"] == ["121", 0]


def test_turbo_switches_are_lazy_branches():
    for nid in ("sw_model", "sw_sampler", "sw_steps"):
        assert GRAPH[nid]["class_type"] == "ComfySwitchNode" and GRAPH[nid]["inputs"]["switch"] == ["turbo", 0]
    assert GRAPH["steps_fast"]["inputs"]["value"] == 8 and GRAPH["139"]["class_type"] == "LoraLoaderModelOnly" and not any(v["class_type"].startswith("MiniMaxH3Turbo") for v in GRAPH.values()) and GRAPH["steps_slow"]["inputs"]["value"] == 20


def test_goal_fills_every_placeholder(monkeypatch):
    monkeypatch.setattr(SL, "probe_song", lambda name: 60.0)
    v, o = goals.values_for("song_lock", {"prompt": "stands on a pier", "audio": "song.flac", "target": "a man in a grey coat", "lyrics": "carry me home", "start": "2", "seed": 5}, "p.png")
    assert not placeholders(GRAPH) - set(v)
    g = fill(GRAPH, v)
    assert g["137"]["inputs"]["image"] == "p.png" and g["ga"]["inputs"]["audio"] == "song.flac"
    assert v["frames"] == 124 and abs(v["seconds"] - 124 / 24) < 1e-5 and v["start"] == 2.0 and v["turbo"] is True
    assert "<d>[English] carry me home.</d>" in v["prompt"] and "a man in a grey coat" in v["prompt"]


def test_parts_follow_each_other(monkeypatch):
    monkeypatch.setattr(SL, "probe_song", lambda name: 60.0)
    starts = [goals.values_for("song_lock", {"audio": "s.wav", "start": "10", "options": {"part": k}, "seed": 1}, "p.png")[0]["start"] for k in (1, 2, 3)]
    assert starts == pytest.approx([10.0, 10 + 124 / 24, 10 + 2 * 124 / 24], abs=1e-5)


def test_goal_refuses_bad_input(monkeypatch):
    monkeypatch.setattr(SL, "probe_song", lambda name: 8.0)
    with pytest.raises(HTTPException): goals.values_for("song_lock", {"seed": 1}, "p.png")                                  # no song
    with pytest.raises(HTTPException): goals.values_for("song_lock", {"audio": "a.txt", "seed": 1}, "p.png")               # not audio
    with pytest.raises(HTTPException): goals.values_for("song_lock", {"audio": "a.wav", "seed": 1}, None)                  # no performer
    with pytest.raises(HTTPException): goals.values_for("song_lock", {"audio": "a.wav", "start": "nope", "seed": 1}, "p.png")
    with pytest.raises(HTTPException): goals.values_for("song_lock", {"audio": "a.wav", "start": "5", "seed": 1}, "p.png")  # runs past the end of an 8 s song


def test_prompt_shape():
    p = SL.lock_prompt("", "", "", "arc")
    assert SL.DEFAULT_WHO in p and "<d>" not in p and SL.CAMERAS["arc"] in p and SL.LOCK_TAIL in p
    for field in ("subject_definitions:", "summary:", "retention_analysis:", "detailed_description:", "overall_soundscape:", "non_diegetic_music:"):
        assert field in p


def test_words_in_window():
    t = {"segments": [{"words": [[0.1, 0.4, "Carry", 0.9], [0.5, 0.8, "me", 0.9], [5.3, 5.6, "home,", 0.9], [5.7, 6.0, "now", 0.9]]}]}
    assert SL.words_in(t, 0, 5.1667) == "Carry me" and SL.words_in(t, 5.1667, 10.33) == "home, now" and SL.words_in(None, 0, 5) == ""


def test_recipe_is_valid_and_its_steps_exist():
    assert R.validate() == []
    rec = R.find("song_lock_video")
    kinds = [s["type"] for s in rec["steps"]]
    assert kinds.count("songlock_shot") == 3 and kinds[-1] == "songlock_cut"
    for k in ("songlock_window", "songlock_shot", "songlock_cut"): assert k in R.EXTRA_STEPS
    assert {"songlock_window", "songlock_cut"} <= R.CPU_KINDS and "songlock_shot" not in R.CPU_KINDS
    assert all(s.get("peak_gib") for s in rec["steps"] if s["type"] == "songlock_shot")
    song = rec["steps"][0]; assert song["swappable"] and song["accepts"] == "audio"


def _song(path, seconds=20, rate=44100, fmt="s16"):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate={rate}:duration={seconds}", "-f", "lavfi", "-i",
                    f"anoisesrc=d={seconds}:r={rate}:a=0.1", "-filter_complex", "[0][1]amix=inputs=2,aformat=channel_layouts=stereo", "-sample_fmt", fmt, str(path)], check=True)


def _clip(path, frames=124):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size=320x192:rate=24", "-f", "lavfi", "-i", "sine=frequency=200:duration=10",
                    "-frames:v", str(frames), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path)], check=True)


@needs_ffmpeg
def test_cut_window_is_sample_exact(tmp_path):
    song = tmp_path / "song.flac"; _song(song)
    f = SL.cut_window(song, tmp_path / "w.wav", 2.0, 3 * 124 / 24)
    assert f["samples"] == round(3 * 124 / 24 * 44100) and f["source_lossless"] and f["sample_fmt"] == "s16"
    # the window's samples are the song's samples, from the start sample on
    raw = SL.pcm(song, "s16"); width = 2 * 2
    assert SL.pcm(tmp_path / "w.wav", "s16") == raw[f["start_sample"] * width:(f["start_sample"] + f["samples"]) * width]
    with pytest.raises(SL.LockError): SL.cut_window(song, tmp_path / "x.wav", 18.0, 5.0)


@needs_ffmpeg
def test_lock_cut_keeps_the_song_bit_exact(tmp_path):
    song = tmp_path / "song.flac"; _song(song)
    clips = [tmp_path / f"c{i}.mp4" for i in range(3)]
    for c in clips: _clip(c)
    w = SL.cut_window(song, tmp_path / "w.wav", 1.0, 3 * 124 / 24)
    r = SL.lock_cut(clips, tmp_path / "w.wav", tmp_path / "out.mp4")
    assert r["facts"]["audio_bit_exact"] and r["facts"]["audio_sha256_out"] == w["sha256"] and r["facts"]["frames"] == 372 and r["facts"]["audio_codec"] == "flac"
    assert r["facts"]["video_copied"]


@needs_ffmpeg
def test_lock_cut_refuses_a_window_of_the_wrong_length(tmp_path):
    song = tmp_path / "song.flac"; _song(song)
    clips = [tmp_path / "c0.mp4"]; _clip(clips[0])
    SL.cut_window(song, tmp_path / "w.wav", 0.0, 8.0)
    with pytest.raises(SL.LockError): SL.lock_cut(clips, tmp_path / "w.wav", tmp_path / "out.mp4")


@needs_ffmpeg
def test_identity_tells_changed_audio_apart(tmp_path):
    a, b = tmp_path / "a.flac", tmp_path / "b.wav"; _song(a, 3)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(a), "-af", "volume=0.999", "-c:a", "pcm_s16le", str(b)], check=True)
    assert SL.identity(a)["sha256"] != SL.identity(b)["sha256"]
