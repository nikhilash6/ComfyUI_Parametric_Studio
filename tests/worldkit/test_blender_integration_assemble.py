"""wk_assemble.py on the CPU: the fixture rig + its walk as FBX -> one glb with a 'walk' animation, scaled to 1.70 m. The retarget leg runs too when that tool is installed."""
import pytest

from studio import glb
from studio.worldkit import capabilities as C, library as L, rigmap, tools
from studio.worldkit.makers import character as CH
from tests.worldkit.conftest import needs_blender
from tests.worldkit.helpers import ctx_for

pytestmark = needs_blender


def _ctx(lib, meta, tmp_path, rig, clip):
    return ctx_for(lib, meta, tmp_path, {"rig": {"main": {"path": str(rig)}}, "retarget_walk": {"main": {"path": str(clip)}}})


def test_assemble_bakes_the_clip_onto_the_rig_and_scales_it(wk_fixtures, tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("character", "fixture", source={"kind": "character", "character_id": "x"},
                                 recipe={"height_m": 1.7, "clips": [{"name": "walk", "text": "walks"}]}))
    main = CH.assemble(_ctx(lib, meta, tmp_path, wk_fixtures / "char.glb", wk_fixtures / "walk.fbx"))["main"]
    assert glb.facts(main["path"])["animations"] == ["walk"] and glb.facts(main["path"])["skins"] == 1
    assert abs(main["inspect"]["height_m"] - 1.70) < 0.02 and abs(main["inspect"]["lo"][2]) < 0.01
    assert main["clips"][0]["name"] == "walk" and main["clips"][0]["frames"] >= 24
    assert set(main["rig"]["slots"]) == set(rigmap.SLOTS)


@pytest.mark.skipif(C.tool_problem("retarget") != "", reason="the retarget tool is not installed")
def test_a_bvh_retargets_onto_the_rig_and_assembles(wk_fixtures, tmp_path):
    fbx = tools.retarget(wk_fixtures / "walk.bvh", wk_fixtures / "char.glb", tmp_path / "rt")
    lib = L.Library()
    meta = lib.create(L.new_meta("character", "fixture", source={"kind": "character", "character_id": "x"}, recipe={"clips": [{"name": "walk", "text": "walks"}]}))
    main = CH.assemble(_ctx(lib, meta, tmp_path, wk_fixtures / "char.glb", fbx))["main"]
    assert glb.facts(main["path"])["animations"] == ["walk"]
