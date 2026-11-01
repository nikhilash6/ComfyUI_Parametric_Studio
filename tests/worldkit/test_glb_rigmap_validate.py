import pytest

from studio import glb
from studio.worldkit import library as L, rigmap
from tests.worldkit.helpers import HUMANOID, bones, make_glb

DOC = {"asset": {"version": "2.0"}, "nodes": [{"name": "body"}, {"name": "Armature"}, {"name": "box-colonly"}],
       "meshes": [{}], "skins": [{"joints": list(range(23))}], "animations": [{"name": "walk"}, {"name": "idle"}]}


def test_glb_facts_read_the_json_chunk(tmp_path):
    p = tmp_path / "a.glb"
    p.write_bytes(make_glb(DOC))
    assert glb.facts(p) == {"nodes": 3, "meshes": 1, "skins": 1, "joints": 23, "animations": ["walk", "idle"],
                            "colliders": 1}


def test_a_non_glb_is_refused(tmp_path):
    p = tmp_path / "a.glb"
    p.write_bytes(b"PK\x03\x04 not a glb at all....")
    with pytest.raises(glb.GlbError, match="not a glTF binary"):
        glb.facts(p)


def test_rig_map_finds_every_slot_from_geometry():
    s = rigmap.slots(bones())
    assert s == {"hips": "hips", "spine": "spine1", "chest": "chest", "neck": "neck", "head": "head",
                 "l_upperarm": "l_arm", "l_forearm": "l_forearm", "l_hand": "l_hand",
                 "r_upperarm": "r_arm", "r_forearm": "r_forearm", "r_hand": "r_hand",
                 "l_thigh": "l_upleg", "l_shin": "l_leg", "l_foot": "l_foot",
                 "r_thigh": "r_upleg", "r_shin": "r_leg", "r_foot": "r_foot"}
    assert set(s) == set(rigmap.SLOTS)


def test_rig_map_ignores_names_and_uses_the_characters_own_left():
    swap = {n: ("r_" + n[2:] if n.startswith("l_") else "l_" + n[2:]) for n, *_ in HUMANOID if n[:2] in ("l_", "r_")}
    s = rigmap.slots(bones(rename=swap))
    assert s["l_hand"] == "r_hand" and s["r_thigh"] == "l_upleg"     # the +X arm is the left arm, whatever its name


def test_rig_map_refuses_what_is_not_a_humanoid():
    with pytest.raises(rigmap.RigMapError, match="too few"):
        rigmap.slots(bones()[:10])
    armless = [b for b in bones() if not any(k in b["name"] for k in ("shoulder", "arm", "hand"))]
    with pytest.raises(rigmap.RigMapError, match="arm"):
        rigmap.slots(armless)


def _asset(lib, tmp_path, type_, inspect, doc=DOC, **meta):
    m = L.new_meta(type_, "x", source={"kind": "text", "prompt": "x"})
    m.update(inspect=inspect, **meta)
    m["build"]["state"] = "done"
    lib.create(m)
    p = lib.path(m["id"], "asset.glb")
    p.write_bytes(make_glb(doc))
    return m, p


def test_validate_a_good_character(tmp_path):
    lib = L.Library()
    rig = {"bones": 23, "standard": "any", "slots": rigmap.slots(bones())}
    m, p = _asset(lib, tmp_path, "character", {"loaded": True, "height_m": 1.7, "dims_m": [0.6, 0.3, 1.7]}, rig=rig)
    assert L.validate(m, p) == []


def test_validate_names_each_problem(tmp_path):
    lib = L.Library()
    tall, p = _asset(lib, tmp_path, "character", {"loaded": True, "height_m": 2.4, "dims_m": [0.6, 0.3, 2.4]})
    bad = " | ".join(L.validate(tall, p))
    assert "1.5-2.0 m tall" in bad and "needs a rig" in bad and "humanoid map" in bad
    no_col = {**DOC, "nodes": [{"name": "body"}]}
    prop, p2 = _asset(lib, tmp_path, "prop", {"loaded": True, "height_m": 0.9, "dims_m": [0.5, 0.5, 0.9]}, doc=no_col)
    assert any("collider" in b for b in L.validate(prop, p2))
    place, p3 = _asset(lib, tmp_path, "place", {"loaded": True, "height_m": 3, "dims_m": [2.0, 3.0, 3.0]})
    assert any("at least 4" in b for b in L.validate(place, p3))
    unloaded, p4 = _asset(lib, tmp_path, "prop", {}, doc=DOC)
    assert any("headless Blender" in b for b in L.validate(unloaded, p4))
    assert L.validate(prop, tmp_path / "missing.glb") == ["no asset.glb yet"]


def test_approve_needs_a_finished_valid_build(tmp_path):
    lib = L.Library()
    m, _ = _asset(lib, tmp_path, "prop", {"loaded": True, "height_m": 0.9, "dims_m": [0.5, 0.5, 0.9]})
    assert lib.approve(m["id"])["status"] == "approved"
    building = L.new_meta("prop", "y", source={"kind": "text", "prompt": "y"})
    lib.create(building)
    with pytest.raises(L.AssetError, match="still building"):
        lib.approve(building["id"])
    bad, _ = _asset(lib, tmp_path, "prop", {"loaded": True, "height_m": 40, "dims_m": [40, 1, 1]})
    with pytest.raises(L.AssetError, match="0.02-30"):
        lib.approve(bad["id"])
