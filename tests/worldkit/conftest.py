"""World Kit tests: the library and every work folder live under tmp_path, no ComfyUI or other live port is reached, and Blender integration tests run on the CPU and skip without Blender."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

BLENDER = os.environ.get("STUDIO_BLENDER") or "/snap/bin/blender"


def blender_available() -> bool:
    return Path(BLENDER).exists() or shutil.which(BLENDER) is not None


needs_blender = pytest.mark.skipif(not blender_available(), reason="Blender is not installed here")


@pytest.fixture(autouse=True)
def _worldkit_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_ROOT", str(tmp_path / "worldkit"))
    monkeypatch.setenv("STUDIO_WORLDKIT_WORK", str(tmp_path / "wk_work"))
    monkeypatch.setenv("STUDIO_WORLDKIT_THREADS", "4")
    monkeypatch.setenv("STUDIO_MODELS_ROOT", str(tmp_path / "models"))
    monkeypatch.setenv("STUDIO_OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("STUDIO_COMFY_INPUT", str(tmp_path / "input"))
    monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:9")          # nothing listens there: a test that reached for ComfyUI fails rather than touching a real one
    monkeypatch.delenv("STUDIO_WORLDKIT_CHARACTERS", raising=False)
    monkeypatch.delenv("STUDIO_WORLDKIT_GPU", raising=False)
    yield


@pytest.fixture(scope="session")
def wk_fixtures(tmp_path_factory):
    """char.glb, walk.fbx, walk.bvh, place.glb, prop.glb, built once per session by Blender on the CPU."""
    if not blender_available():
        pytest.skip("Blender is not installed here")
    from tests.worldkit.helpers import HUMANOID
    out = tmp_path_factory.mktemp("wk_fixtures")
    payload = out / "payload.json"
    payload.write_text(json.dumps({"out": str(out), "skeleton": HUMANOID}))
    script = Path(__file__).with_name("blender_fixtures") / "make_fixtures.py"
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
    p = subprocess.run([BLENDER, "-b", "--factory-startup", "--python", str(script), "--", str(payload)], capture_output=True, text=True, timeout=600, env=env)
    assert p.returncode == 0 and "PPWK" in p.stdout, (p.stdout[-3000:], p.stderr[-2000:])
    return out
