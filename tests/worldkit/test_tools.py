"""Third-party tool runners with a fake call: the command, the VRAM gate and the plain errors. No tool runs here."""
from pathlib import Path

import pytest
from PIL import Image

from studio.worldkit import tools
from studio.worldkit.steps import StepError


@pytest.fixture
def ready(monkeypatch):
    monkeypatch.setattr(tools, "require", lambda key: None)
    monkeypatch.setattr(tools, "vram_gate", lambda tool, **k: None)


def _fake(writes, rc=0, seen=None):
    def run(cmd, log, timeout, **kw):
        if seen is not None:
            seen.append((cmd, kw))
        for p in writes(cmd):
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            Path(p).write_bytes(b"x")
        return rc
    return run


def test_a_missing_model_is_said_plainly_before_anything_runs(tmp_path):
    with pytest.raises(StepError, match="still downloading or missing"):
        tools.sam3d_objects(tmp_path / "a.png", tmp_path, run=lambda *a, **k: pytest.fail("must not run"))


def test_the_vram_gate_keeps_the_floor_and_evicts_nothing():
    with pytest.raises(StepError, match="Nothing was evicted"):
        tools.vram_gate("sam3d_objects", free=lambda: 20.0)
    tools.vram_gate("skintokens", free=lambda: 50.0)


def test_sam3d_makes_a_mask_from_the_cutout_and_refuses_a_picture_without_one(tmp_path, ready):
    pic = tmp_path / "c.png"
    Image.new("RGBA", (4, 4), (1, 2, 3, 200)).save(pic)
    seen = []
    out = tools.sam3d_objects(pic, tmp_path / "w", run=_fake(lambda c: [Path(c[c.index("--out-dir") + 1]) / "object.glb"], seen=seen))
    assert out.name == "object.glb" and (tmp_path / "w" / "mask.png").is_file() and "--mask" in seen[0][0]
    flat = tmp_path / "f.png"
    Image.new("RGB", (4, 4)).save(flat)
    with pytest.raises(StepError, match="no cut-out"):
        tools.sam3d_objects(flat, tmp_path / "w2", run=_fake(lambda c: []))


def test_a_tool_that_exits_zero_with_no_file_failed(tmp_path, ready):
    with pytest.raises(StepError, match="without rigged.glb"):
        tools.skintokens(tmp_path / "m.glb", tmp_path, run=_fake(lambda c: []))


def test_autoremesher_runs_cpu_and_kimodo_and_retarget_use_their_outputs(tmp_path, ready):
    src = tmp_path / "m.glb"
    src.write_bytes(b"glb")
    seen = []
    out = tools.autoremesher(src, tmp_path / "a", run=_fake(lambda c: [Path(c[2]) / "model_lod0_20000q.glb"], seen=seen))
    assert out.name.endswith("20000q.glb") and seen[0][1]["cpu"] is True
    assert tools.kimodo("a person  walks", tmp_path / "k", run=_fake(lambda c: [str(c[c.index("--output") + 1]) + ".bvh"])).suffix == ".bvh"
    seen = []
    assert tools.retarget(tmp_path / "w.bvh", tmp_path / "r.glb", tmp_path / "t", run=_fake(lambda c: [c[c.index("--out-fbx") + 1]], seen=seen)).suffix == ".fbx"
    cmd = seen[0][0]
    assert seen[0][1]["cpu"] is True and cmd[cmd.index("--src-map") + 1] == "detect"
    soma = tmp_path / "s.bvh"
    soma.write_text("HIERARCHY\nROOT Hips\nJOINT Spine1\nJOINT Chest\nJOINT LeftShin\nJOINT RightShin\n")
    assert tools._src_map(soma).endswith("soma77_slots.json") and Path(tools._src_map(soma)).is_file()


def test_a_tool_past_its_timeout_is_killed_by_pid(tmp_path):
    import subprocess

    class P:
        pid = 777
        dead = False

        def wait(self, timeout=None):
            if not self.dead:
                raise subprocess.TimeoutExpired("x", timeout)
            return -15

        def poll(self):
            return -15 if self.dead else None

    p, kills = P(), []

    def killpg(pid, sig):
        kills.append(pid)
        p.dead = True
    with pytest.raises(StepError, match="was killed"):
        tools.call(["/x/tool"], tmp_path / "t.log", 1, popen=lambda *a, **k: p, killpg=killpg)
    assert kills == [777]
