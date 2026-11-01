"""The shot runner with fakes: scene -> mode -> QC, one reroll with a new seed, then review. No Blender, no ComfyUI."""
import threading

import pytest
from PIL import Image

from studio.vset import passes, qc, runner as R, shot as SH, shotlist as SL
from studio.worldkit import library as L
from tests.vset.helpers import SCENE_OUTPUTS, FakeStudio, cast_of, good_shot, make_set


@pytest.fixture(autouse=True)
def scene(monkeypatch):
    calls = []

    def fake(shot, ctx):
        calls.append(shot["id"])
        return {k: dict(v) for k, v in SCENE_OUTPUTS.items()}
    monkeypatch.setattr(passes, "scene_step_outputs", fake)
    return calls


@pytest.fixture
def qc_says(monkeypatch):
    answers = []

    def judge(video, **kw):
        return answers.pop(0) if answers else {"ok": True, "face": None, "flicker": 1.0, "reasons": []}
    monkeypatch.setattr(qc, "judge", judge)
    return answers


def _shot(lib, **kw):
    return SH.save(good_shot(make_set(lib), **kw))


def test_a_shot_renders_scene_then_mode_then_qc(qc_says, scene):
    lib, st = L.Library(), FakeStudio()
    s = _shot(lib)
    state = R.run_shot(s["id"], library=lib, seams_=st.seams())
    assert state["state"] == "done" and state["qc"]["ok"] and state["rerolls"] == 0 and scene == [s["id"]]
    assert [r["template"] for r in st.reqs] == ["vset_keyframe_edit_api.json", "vset_keyframe_edit_api.json", "h3_fl2v_api.json"]
    assert SH.load_state(s["id"])["state"] == "done"


def test_passes_only_needs_no_job_and_a_later_render_can_keep_them(qc_says, scene):
    lib, st = L.Library(), FakeStudio()
    s = _shot(lib)
    state = R.run_shot(s["id"], library=lib, seams_=st.seams(), passes_only=True)
    assert state["state"] == "done" and state["scope"] == "passes" and st.reqs == [] and [r["name"] for r in state["steps"]] == ["scene"]
    state = R.run_shot(s["id"], library=lib, seams_=st.seams())
    assert state["state"] == "done" and len(scene) == 1 and len(st.reqs) == 3                  # the passes were kept


def test_a_failed_video_rerolls_once_with_a_new_seed_and_keeps_the_passes(qc_says, scene):
    lib, st = L.Library(), FakeStudio(fail={"h3_fl2v_api.json": ["ComfyUI ran out of memory"]})
    s = _shot(lib)
    state = R.run_shot(s["id"], library=lib, seams_=st.seams())
    assert state["state"] == "done" and state["rerolls"] == 1 and len(scene) == 1
    templates = [r["template"] for r in st.reqs]
    assert templates.count("vset_keyframe_edit_api.json") == 2
    assert [r["values"]["seed"] for r in st.reqs if r["template"] == "h3_fl2v_api.json"] == [4242, 4243]
    assert SH.load(s["id"])["seed"] == 4243                       # shot.json recreates the final video


def test_a_second_failure_waits_for_review_or_fails(qc_says):
    lib = L.Library()
    bad = {"ok": False, "face": None, "flicker": 20.0, "reasons": ["flicker 20.0 > 6.0"]}
    qc_says.extend([bad, dict(bad)])
    state = R.run_shot(_shot(lib)["id"], library=lib, seams_=FakeStudio().seams())
    assert state["state"] == "review" and state["rerolls"] == 1 and state["qc"]["reasons"]
    st = FakeStudio(fail={"h3_fl2v_api.json": ["boom", "boom again"]})
    state = R.run_shot(_shot(lib)["id"], library=lib, seams_=st.seams())
    assert state["state"] == "failed" and state["rerolls"] == 1


def test_qc_that_cannot_run_waits_for_review_without_a_reroll(monkeypatch):
    lib = L.Library()

    def broken(video, **kw):
        raise RuntimeError("ffmpeg is missing")
    monkeypatch.setattr(qc, "judge", broken)
    state = R.run_shot(_shot(lib)["id"], library=lib, seams_=FakeStudio().seams())
    assert state["state"] == "review" and state["rerolls"] == 0 and "could not run" in state["qc"]["reasons"][0]


def test_qc_gets_no_face_check_without_a_classifier_even_with_a_cast(qc_says, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    seen = {}

    def judge(video, **kw):
        seen.update(kw)
        return {"ok": True, "face": None, "flicker": 1.0, "reasons": []}
    monkeypatch.setattr(qc, "judge", judge)
    lib = L.Library()
    ids = make_set(lib, character=True)
    s = SH.save(good_shot(ids, cast=cast_of(ids)))
    R.run_shot(s["id"], library=lib, seams_=FakeStudio().seams())
    assert seen["anchor"] == "" and seen["classify"] is None and seen["edges"] == "/o/edges.mp4"


def test_render_refuses_when_an_asset_was_archived_after_saving(qc_says, scene):
    lib, st = L.Library(), FakeStudio()
    ids = make_set(lib)
    s = SH.save(good_shot(ids))
    lib.archive(ids["place"])
    state = R.run_shot(s["id"], library=lib, seams_=st.seams())
    assert state["state"] == "failed" and "archived or missing" in state["error"] and st.reqs == [] and scene == []


def test_a_cancelled_render_stops_and_does_not_reroll(qc_says):
    lib, st = L.Library(), FakeStudio(fail={"h3_fl2v_api.json": ["cancelled"]})
    ev = threading.Event()
    orig = st.wait

    def wait(jid):
        if st.reqs[int(jid[1:]) - 1]["template"] == "h3_fl2v_api.json":
            ev.set()
        return orig(jid)
    s = _shot(lib)
    state = R.run_shot(s["id"], library=lib, seams_={**st.seams(), "wait": wait}, cancel=ev)
    assert state["state"] == "failed" and state["rerolls"] == 0


def test_a_list_renders_every_shot_then_scores_set_consistency(qc_says, monkeypatch, tmp_path):
    lib = L.Library()
    ids = make_set(lib)
    shots = [SH.save(good_shot(ids, prompt=f"line {i}")) for i in range(2)]
    lst = SL.save_list(SL.new_list("Two", [s["id"] for s in shots], base={}))
    png = tmp_path / "f.png"
    Image.new("RGB", (16, 16), (120, 80, 40)).save(png)
    monkeypatch.setattr(qc, "sample_frames", lambda video, out_dir, n=12, run=None: [png])
    res = R.run_list(lst["id"], library=lib, seams_=FakeStudio().seams())
    assert set(res["shots"].values()) == {"done"} and res["consistency"]["ok"] is True
    assert SL.load_list(lst["id"])["state"]["consistency"]["min"] == pytest.approx(1.0)
