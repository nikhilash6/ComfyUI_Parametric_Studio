"""The character maker with fakes: which steps it asks for, in which order, with which files. On unless STUDIO_WORLDKIT_CHARACTERS=0, and it only takes saved characters."""
import json
from pathlib import Path

import pytest

from studio.worldkit import characters as CS, library as L, picturecheck, safety, steps as S
from studio.worldkit.makers import character as CH
from tests.worldkit.helpers import bones, ctx_for, glb_file


def _save(tmp_path, cid="savedchar", name="Ada", description="tall, auburn hair", status="ready", body=True):
    d = tmp_path / "worldkit" / "_characters" / cid
    d.mkdir(parents=True, exist_ok=True)
    rec = {}
    if body:
        (d / "body_front.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        rec = {"ok": True, "version": picturecheck.VERSION, "sha256": picturecheck.sha256(d / "body_front.png")}
    (d / "character.json").write_text(json.dumps({"name": name, "description": description, "status": status, "check": rec}))
    return cid


def test_on_by_default_and_off_only_by_the_setting(monkeypatch):
    assert safety.character_problem() == "" and safety.characters_enabled()
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    assert safety.character_problem() == ""
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "0")
    assert "off" in safety.character_problem() and not safety.characters_enabled()


def test_only_a_built_saved_sheet_with_a_body_shot_passes(tmp_path):
    assert CS.sheet_problem(CS.get(_save(tmp_path))) == ""
    assert "unverified" in CS.sheet_problem(CS.get(_save(tmp_path, status="unverified")))        # the earlier studio's status: no check behind it
    assert "failed" in CS.sheet_problem(CS.get(_save(tmp_path, status="failed")))
    assert "full-body" in CS.sheet_problem(CS.get(_save(tmp_path, "nobody", body=False)))
    assert CS.sheet_problem(None) == "no such saved character"
    assert CS.get("../evil") is None and CS.get("nothing") is None


@pytest.mark.parametrize("desc", ["a teenage girl", "a child in a red coat", "she is 15 years old", "schoolgirl uniform"])
def test_a_saved_character_described_as_a_child_is_refused(tmp_path, desc):
    assert "child" in CS.sheet_problem(CS.get(_save(tmp_path, description=desc))) or "reword" in CS.sheet_problem(CS.get(_save(tmp_path, description=desc)))


def test_a_saved_character_with_a_refused_word_is_refused(tmp_path):
    assert "safe-for-work" in CS.sheet_problem(CS.get(_save(tmp_path, description="nude figure")))


def test_all_saved_lists_what_is_there_and_an_empty_store_is_fine(tmp_path):
    assert CS.all_saved() == []
    _save(tmp_path)
    assert [c.name for c in CS.all_saved()] == ["Ada"]


def test_recipe_defaults_and_problems():
    r, bad = CH.recipe(None)
    assert bad == [] and r["mesh"] == "trellis2" and r["remesh"] is False and [c["name"] for c in r["clips"]] == ["idle", "walk", "wave"]
    _, bad = CH.recipe({"mesh": "nerf", "height_m": 2.5, "clips": [{"name": "Walk!", "text": "x"}, {"name": "run", "text": " "}]})
    joined = " | ".join(bad)
    assert "mesh must be" in joined and "height_m" in joined and "lowercase" in joined and "describe the motion" in joined


class Tools:
    """Stands in for every tool step, recording the order and the files."""
    def __init__(self, tmp, fail=()):
        self.tmp, self.fail, self.calls = tmp, set(fail), []

    def _go(self, name, *args):
        self.calls.append((name, *[str(a) for a in args[:2]]))
        if name in self.fail:
            raise S.StepError(f"{name} failed")
        return glb_file(self.tmp / "made" / f"{name}_{len(self.calls)}.glb")

    def seams(self):
        return {k: (lambda *a, k=k, **kw: self._go(k, *a)) for k in ("autoremesher", "skintokens", "kimodo", "retarget", "sam3d")}


class Comfy:
    def __init__(self, tmp):
        self.reqs, self.tmp = [], tmp

    def submit(self, req):
        self.reqs.append(req)
        return "j1"

    def wait(self, jid):
        return {"status": "done", "artifacts": [{"path": glb_file(self.tmp / "made" / "body.glb"), "media_type": "file"}]}


class FB:
    def __init__(self, bones_=None):
        self.bones, self.calls = bones_ if bones_ is not None else bones(), []

    def run(self, script, payload, **kw):
        self.calls.append((script, payload, kw))
        Path(payload["out"]).write_bytes(b"glTF")
        return {"ok": True, "inspect": {"loaded": True, "height_m": 1.7, "bones": self.bones}, "clips": [{"name": "walk", "frames": 24, "fps": 24}]}


def _build(tmp_path, monkeypatch, recipe=None, fail=(), fb=None):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    from studio.worldkit import tools
    monkeypatch.setattr(tools, "require", lambda key: None)
    lib = L.Library()
    meta = lib.create(L.new_meta("character", "Ada", source={"kind": "character", "character_id": _save(tmp_path)}, recipe=recipe))
    t, c, fb = Tools(tmp_path, fail), Comfy(tmp_path), fb or FB()
    ctx = ctx_for(lib, meta, tmp_path, blender=fb, to_input=lambda p: "sheet.png", **t.seams())
    return t, c, fb, S.run({}, CH.steps(meta), ctx=ctx, submit=c.submit, wait=c.wait, save=lambda s: None)


def test_the_default_build_runs_the_chain_in_order(tmp_path, monkeypatch):
    t, c, fb, state = _build(tmp_path, monkeypatch)
    assert state["state"] == "done", state["error"]
    assert [r["name"] for r in state["steps"]] == ["sheet", "mesh", "rig", "motion_idle", "retarget_idle", "motion_walk", "retarget_walk", "motion_wave", "retarget_wave", "assemble"]
    assert [x[0] for x in t.calls] == ["skintokens", "kimodo", "retarget", "kimodo", "retarget", "kimodo", "retarget"]
    assert c.reqs[0]["template"] == CH.TRELLIS_GRAPH and c.reqs[0]["values"]["image"] == "sheet.png"
    assert fb.calls[0][0] == "wk_assemble.py"                                                # nothing to bake: the rig takes the textured mesh as it came
    assert fb.calls[-1][0] == "wk_assemble.py" and [x["name"] for x in fb.calls[-1][1]["clips"]] == ["idle", "walk", "wave"] and fb.calls[-1][2]["gpu"] is False


def test_a_failed_clip_is_left_out_and_a_failed_rig_stops_the_build(tmp_path, monkeypatch):
    t, _, fb, state = _build(tmp_path, monkeypatch, {"clips": [{"name": "walk", "text": "walks"}]}, fail={"kimodo"})
    assert state["state"] == "done" and fb.calls[-1][1]["clips"] == [] and "retarget" not in [x[0] for x in t.calls]
    _, _, _, state = _build(tmp_path, monkeypatch, fail={"skintokens"})
    assert state["state"] == "failed" and state["error"].startswith("Rig (SkinTokens):")
    assert {r["name"]: r["status"] for r in state["steps"]}["mesh"] == "done"            # the mesh is kept


def test_a_recipe_can_ask_for_the_plain_body_which_is_baked_first(tmp_path, monkeypatch):
    t, c, fb, state = _build(tmp_path, monkeypatch, {"mesh": "sam3d_body", "clips": []})
    assert state["state"] == "done" and c.reqs[0]["template"] == CH.BODY_GRAPH and c.reqs[0]["values"] == {"image": "sheet.png"}
    assert fb.calls[0][0] == "wk_flatten.py" and fb.calls[0][1]["out"] == t.calls[0][1]      # the rig takes the plain surface, not the pose file


def test_a_recipe_can_still_ask_for_the_remesher(tmp_path, monkeypatch):
    t, _, _, state = _build(tmp_path, monkeypatch, {"remesh": True, "clips": []})
    assert state["state"] == "done" and [x[0] for x in t.calls] == ["autoremesher", "skintokens"] and "autoremesher" in t.calls[1][1]


def test_the_first_step_refuses_while_the_maker_is_off(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "0")
    lib = L.Library()
    meta = lib.create(L.new_meta("character", "Ada", source={"kind": "character", "character_id": _save(tmp_path)}))
    state = S.run({}, CH.steps(meta), ctx=ctx_for(lib, meta, tmp_path), submit=None, wait=None, save=lambda s: None)
    assert state["state"] == "failed" and "off" in state["error"] and state["steps"][1]["status"] == "pending"


def test_assemble_maps_the_rig_and_records_the_clips(tmp_path, monkeypatch):
    _, _, _, state = _build(tmp_path, monkeypatch)
    main = next(r for r in state["steps"] if r["name"] == "assemble")["outputs"]["main"]
    assert main["rig"]["bones"] == 23 and main["rig"]["slots"]["head"] == "head" and "bones" not in main["inspect"] and main["clips"][0]["name"] == "walk"
    _, _, _, state = _build(tmp_path, monkeypatch, fb=FB(bones()[:12]))
    main = next(r for r in state["steps"] if r["name"] == "assemble")["outputs"]["main"]
    assert main["rig"]["slots"] == {} and "no humanoid map" in main["note"]
