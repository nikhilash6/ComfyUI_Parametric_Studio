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


def _soma_bvh(path):
    """A small BVH with Kimodo's joint names and, like Kimodo's, a zero pose that is not a person standing: the arms and legs lie along their own X. Two seconds' worth of frames, walking toward -Y."""
    chain = [("Root", None, (0, 0, 0)), ("Hips", "Root", (0, 95, 0)), ("Spine1", "Hips", (10, 0, 0)), ("Chest", "Spine1", (30, 0, 0)), ("Neck1", "Chest", (15, 0, 0)), ("Head", "Neck1", (10, 0, 0)), ("HeadEnd", "Head", (15, 0, 0))]
    for s, x in (("Left", 1), ("Right", -1)):
        chain += [(f"{s}Shoulder", "Chest", (10, 0, x * 3)), (f"{s}Arm", f"{s}Shoulder", (x * 14, 0, 0)), (f"{s}ForeArm", f"{s}Arm", (x * 28, 0, 0)), (f"{s}Hand", f"{s}ForeArm", (x * 25, 0, 0)), (f"{s}HandMiddle2", f"{s}Hand", (x * 8, 0, 0)),
                  (f"{s}Leg", "Hips", (0, 0, x * 10)), (f"{s}Shin", f"{s}Leg", (x * 43, 0, 0)), (f"{s}Foot", f"{s}Shin", (x * 42, 0, 0)), (f"{s}ToeBase", f"{s}Foot", (x * 14, 0, 0))]
    kids = {}
    for n, p, _ in chain:
        kids.setdefault(p, []).append(n)
    off = {n: o for n, _, o in chain}
    order = []

    def write(n, ind, root=False):
        order.append(n)
        t = " " * ind
        rows = [f"{t}{'ROOT' if root else 'JOINT'} {n}", t + "{", f"{t}  OFFSET {off[n][0]} {off[n][1]} {off[n][2]}", f"{t}  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation"]
        for k in kids.get(n, []):
            rows += write(k, ind + 2)
        if not kids.get(n):
            rows += [t + "  End Site", t + "  {", t + "    OFFSET 1 0 0", t + "  }"]
        return rows + [t + "}"]

    lines = ["HIERARCHY", *write("Root", 0, True), "MOTION", "Frames: 48", "Frame Time: 0.03333333333333333"]
    for f in range(48):
        vals = []
        for n in order:
            pos = [0, 0, f * 4.0] if n == "Root" else [0, 0, 0]
            rot = [0, 0, 0]
            if n == "Hips":                       # stands the zero pose up: spine along +Y of the BVH
                rot = [90, 0, 0]
            vals += [*pos, *rot]
        lines.append(" ".join(str(v) for v in vals))
    path.write_text("\n".join(lines) + "\n")
    return path


def test_a_kimodo_motion_is_fitted_from_joint_positions_and_assembles(wk_fixtures, tmp_path):
    from pathlib import Path
    from studio.worldkit import blender as B
    motion = _soma_bvh(tmp_path / "soma.bvh")
    assert tools._src_map(motion).endswith("soma77_slots.json")
    out = tmp_path / "clip.fbx"
    res = B.run("wk_fit_motion.py", {"motion": str(motion), "rig": str(wk_fixtures / "char.glb"), "out": str(out)}, work=tmp_path / "fit", name="fit", timeout=300, gpu=False)
    assert res["frames"] == 48 and Path(out).stat().st_size > 0
    lib = L.Library()
    meta = lib.create(L.new_meta("character", "fixture", source={"kind": "character", "character_id": "x"}, recipe={"clips": [{"name": "walk", "text": "walks"}]}))
    main = CH.assemble(_ctx(lib, meta, tmp_path, wk_fixtures / "char.glb", out))["main"]
    assert glb.facts(main["path"])["animations"] == ["walk"] and main["clips"][0]["fps"] == 30
