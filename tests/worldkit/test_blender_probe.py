"""Blender runs headless on the CPU here and uses no GPU."""
from studio.worldkit import blender as B
from tests.worldkit.conftest import needs_blender


@needs_blender
def test_probe_renders_one_frame_on_the_cpu(tmp_path):
    out = tmp_path / "probe.png"
    res = B.run("wk_probe.py", {"engine": "cycles", "out": str(out)}, work=tmp_path, timeout=300)
    assert res["ok"] and res["engine"] == "CYCLES" and out.is_file() and out.stat().st_size > 100
    assert res["version"].startswith("5.2")
