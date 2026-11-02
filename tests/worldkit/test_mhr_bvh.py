"""SAM 3D Body's numbered BVH joints read as SOMA names. The fixture is four frames captured here from a dance on an invented 3D character. No GPU, no Blender."""
import math
from pathlib import Path
import pytest
from studio.worldkit import mhr_bvh as H, tools

BVH = Path(__file__).resolve().parents[1] / "data" / "mhr_capture_4frames.bvh"
NEED = {"Hips", "Spine1", "Chest", "Neck1", "Head", *(f"{s}{p}" for s in ("Left", "Right") for p in ("Leg", "Shin", "Foot", "ToeBase", "Shoulder", "Arm", "ForeArm", "Hand", "HandMiddle2"))}


def test_it_is_known_as_a_capture_and_a_soma_clip_is_not():
    assert H.is_mhr(BVH.read_text()) and not H.is_mhr("HIERARCHY\nROOT Hips\n{\n JOINT Spine1\n}\n")


def test_every_joint_the_fit_reads_is_found_once():
    m = H.mapping(BVH.read_text()); assert set(m.values()) >= NEED and len(set(m.values())) == len(m)


def test_left_is_the_characters_left_and_the_limbs_hang_right():
    t = BVH.read_text(); m = {v: k for k, v in H.mapping(t).items()}; j, f = H.parse(t); p = H.frame0(j, f)
    for s in ("Left", "Right"):
        assert p[m[s + "Leg"]][1] > p[m[s + "Shin"]][1] > p[m[s + "Foot"]][1]          # hip above knee above ankle
        assert p[m[s + "Arm"]][1] > p[m[s + "Hand"]][1] - 30
    assert p[m["Chest"]][1] > p[m["Spine1"]][1] and p[m["Head"]][1] > p[m["Neck1"]][1]


def test_leveled_clip_stands_up_and_faces_forward(tmp_path):
    out = H.rename(BVH, tmp_path / "s.bvh"); t = out.read_text(); assert "JOINT LeftShin" in t and "JOINT Chest" in t
    j, _ = H.parse(t); _, rows = H._frames(t); ups = []
    for r in rows:
        p = H.frame0(j, r); a = [(p["LeftFoot"][i] + p["RightFoot"][i]) / 2 for i in range(3)]; d = [p["Neck1"][i] - a[i] for i in range(3)]
        ups.append([x / math.sqrt(sum(y * y for y in d)) for x in d])
    mean = [sum(u[i] for u in ups) / len(ups) for i in range(3)]; assert math.degrees(math.acos(mean[1] / math.sqrt(sum(x * x for x in mean)))) < 2
    p = H.frame0(j, rows[0]); assert p["LeftLeg"][0] - p["RightLeg"][0] > 8                  # facing +Z, the left hip is on +X
    assert len(rows) == 4 and tools._src_map(out).endswith("soma77_slots.json")


def test_a_shape_it_cannot_read_says_so():
    with pytest.raises(ValueError): H.mapping("HIERARCHY\nROOT Hips\n{\n OFFSET 0 0 0\n CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation\n}\nMOTION\nFrames: 1\nFrame Time: 0.04\n0 0 0 0 0 0\n")
