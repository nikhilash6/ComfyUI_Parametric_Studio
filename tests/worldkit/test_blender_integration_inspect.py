"""Blender on the CPU: the shared helpers load what the makers will produce, and a hung Blender dies by its pid."""
import subprocess

import pytest

from studio.worldkit import blender as B, rigmap
from tests.worldkit.conftest import needs_blender

pytestmark = needs_blender


def test_inspect_reports_height_bones_actions_and_colliders(wk_fixtures, tmp_path):
    ins = B.inspect(wk_fixtures / "char.glb", work=tmp_path)
    assert ins["loaded"] and abs(ins["height_m"] - 1.70) < 0.1 and ins["armatures"] == 1
    assert len(ins["bones"]) == 23 and all(b["name"].startswith("bone_") for b in ins["bones"])
    assert set(rigmap.slots(ins["bones"])) == set(rigmap.SLOTS)          # geometry survives the glTF round trip
    assert any(a.startswith("walk") for a in ins["actions"])
    place = B.inspect(wk_fixtures / "place.glb", work=tmp_path)
    assert place["colliders"] == 2 and max(place["dims_m"][:2]) > 11.9 and place["meshes"] == 2
    prop = B.inspect(wk_fixtures / "prop.glb", work=tmp_path)
    assert abs(max(prop["dims_m"]) - 0.37) < 0.01 and prop["colliders"] == 0


def test_a_hung_blender_is_killed_through_its_own_process_group(tmp_path, monkeypatch):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "sleep.py").write_text("import time\ntime.sleep(300)\n")
    monkeypatch.setattr(B, "SCRIPTS", scripts)
    procs = []

    def popen(*a, **kw):
        procs.append(subprocess.Popen(*a, **kw))
        return procs[-1]

    with pytest.raises(B.BlenderFailed, match="timed out"):
        B.run("sleep.py", {}, work=tmp_path, timeout=8, popen=popen)
    assert procs[0].poll() is not None                                      # gone, killed by pid, not by name
