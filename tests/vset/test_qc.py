import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from studio.vset import qc


def _frames(values):
    return [np.full((8, 8), float(v), np.float32) for v in values]


def test_flicker_ignores_smooth_change_and_catches_strobing():
    assert qc.flicker_score(_frames([10, 20, 30, 40, 50])) == 0.0
    assert qc.flicker_score(_frames([0, 200, 0, 200, 0])) > qc.FLICKER_MAX
    assert qc.flicker_score(_frames([5, 6])) == 0.0


def _pngs(tmp_path, colours, name="f"):
    out = []
    for i, c in enumerate(colours):
        p = tmp_path / f"{name}{i}.png"
        Image.new("RGB", (32, 32), c).save(p)
        out.append(p)
    return out


def test_face_score_is_the_median_match_and_none_without_faces(tmp_path):
    frames = _pngs(tmp_path, [(0, 0, 0)] * 3)
    sims = iter([0.9, 0.3, 0.7])
    classify = lambda imgs, ref: {i: {"faces": [{"sim": next(sims), "age": 30}]} for i in imgs}  # noqa: E731
    assert qc.face_score(frames, "/c/head.png", classify=classify) == pytest.approx(0.7)
    assert qc.face_score(frames, "/c/head.png", classify=lambda imgs, ref: {i: {"faces": []} for i in imgs}) is None


def test_judge_reports_each_failure(tmp_path, monkeypatch):
    spread = _pngs(tmp_path, [(90, 90, 90)] * 4, "s")
    steady = _pngs(tmp_path, [(100, 100, 100)] * 6, "r")
    strobe = _pngs(tmp_path, [(0, 0, 0), (250, 250, 250)] * 3, "x")
    monkeypatch.setattr(qc, "sample_frames", lambda video, out_dir, n=12, run=None: spread)
    good = lambda imgs, ref: {i: {"faces": [{"sim": 0.8, "age": 30}]} for i in imgs}       # noqa: E731
    bad = lambda imgs, ref: {i: {"faces": [{"sim": 0.2, "age": 30}]} for i in imgs}        # noqa: E731
    monkeypatch.setattr(qc, "run_frames", lambda video, out_dir, n=24, run=None: steady)
    assert qc.judge("/o/v.mp4", anchor="/c/head.png", classify=good, work=tmp_path / "w")["ok"] is True
    res = qc.judge("/o/v.mp4", anchor="/c/head.png", classify=bad, work=tmp_path / "w")
    assert res["ok"] is False and "face match 0.2" in res["reasons"][0]
    monkeypatch.setattr(qc, "run_frames", lambda video, out_dir, n=24, run=None: strobe)
    res = qc.judge("/o/v.mp4", anchor="", classify=good, work=tmp_path / "w")
    assert res["face"] is None and res["reasons"] == [f"flicker {res['flicker']:.1f} > {qc.FLICKER_MAX}"]


def test_the_face_match_stays_off_without_a_character_and_a_classifier(tmp_path, monkeypatch):
    steady = _pngs(tmp_path, [(100, 100, 100)] * 6, "r")
    monkeypatch.setattr(qc, "run_frames", lambda video, out_dir, n=24, run=None: steady)
    for kw in ({}, {"anchor": "/c/head.png"}, {"classify": lambda i, r: {}}):
        res = qc.judge("/o/v.mp4", work=tmp_path / "w", **kw)
        assert res["ok"] is True and res["face"] is None and res["face_checked"] is False


def test_set_score_and_list_consistency(tmp_path):
    a = _pngs(tmp_path, [(200, 120, 40)] * 2, "a")
    b = _pngs(tmp_path, [(200, 120, 40)] * 2, "b")
    c = _pngs(tmp_path, [(20, 60, 220)] * 2, "c")
    assert qc.set_score(a, b) == pytest.approx(1.0) and qc.set_score(a, c) < qc.SET_MIN
    res = qc.list_consistency({"one": a, "two": b, "three": c})
    assert res["scores"]["two"] == pytest.approx(1.0) and res["ok"] is False and res["min"] < qc.SET_MIN
    assert qc.list_consistency({"one": a}) == {"scores": {}, "min": None, "ok": True}


def test_layout_score_rewards_matching_structure(tmp_path):
    img = np.zeros((64, 64), np.uint8)
    img[16:48, 16:48] = 255
    Image.fromarray(img).save(tmp_path / "o.png")
    edges = np.zeros((64, 64), np.uint8)
    edges[16, 16:48] = edges[47, 16:48] = edges[16:48, 16] = edges[16:48, 47] = 255
    Image.fromarray(edges).save(tmp_path / "e.png")
    Image.fromarray(np.zeros((64, 64), np.uint8)).save(tmp_path / "blank.png")
    assert qc.layout_score([tmp_path / "o.png"], [tmp_path / "e.png"]) > 0.2
    assert qc.layout_score([tmp_path / "blank.png"], [tmp_path / "e.png"]) == 0.0


def test_layout_score_sees_one_pixel_lines_in_a_big_frame(tmp_path):
    """A Blender edge pass at full size: thin lines must survive being shrunk."""
    img = np.zeros((768, 1344), np.uint8)
    img[200:600, 300:1000] = 255
    Image.fromarray(img).save(tmp_path / "o.png")
    edges = np.zeros((768, 1344), np.uint8)
    edges[200, 300:1000] = edges[599, 300:1000] = edges[200:600, 300] = edges[200:600, 999] = 255
    Image.fromarray(edges).save(tmp_path / "e.png")
    assert qc.layout_score([tmp_path / "o.png"], [tmp_path / "e.png"]) > 0.3


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_sampling_reads_a_real_video(tmp_path):
    from studio.worldkit import media
    d = tmp_path / "frames"
    d.mkdir()
    for i in range(1, 49):
        Image.new("RGB", (64, 64), (i * 5, 0, 0)).save(d / f"{i:04d}.png")
    video = media.encode(d, 24, tmp_path / "v.mp4")
    assert 4 <= len(qc.sample_frames(video, tmp_path / "s", n=6)) <= 6
    assert len(qc.run_frames(video, tmp_path / "r", n=10)) == 10
