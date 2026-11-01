"""wk_place.py on the CPU at 64 px: every kit builds, exports with colliders and renders four views."""
import pytest
from PIL import Image

from studio import glb
from studio.worldkit import blender as B, looks
from studio.worldkit.makers import place as PL
from tests.worldkit.conftest import needs_blender

pytestmark = needs_blender


@pytest.mark.parametrize("brief", ["rainy downtown block at night", "beach café interior", "sunny beach boardwalk"])
def test_each_kit_builds_and_renders(brief, tmp_path):
    r = PL.plan(brief)
    tex = tmp_path / "ground.png"
    Image.new("RGB", (16, 16), (120, 110, 100)).save(tex)
    out, views = tmp_path / "place.glb", tmp_path / "views"
    res = B.run("wk_place.py", {"recipe": r, "textures": {"ground": str(tex)}, "look": looks.resolve(**r["look"]), "out": str(out), "views": str(views),
                                "size": 64, "samples": 1, "engine": "cycles"}, work=tmp_path, timeout=900)
    ins = res["inspect"]
    assert out.is_file() and glb.facts(out)["colliders"] >= 5 and ins["colliders"] >= 5
    assert max(ins["dims_m"][:2]) >= 4.0 and all((views / f"view_{i}.png").is_file() for i in range(4))
    w, d = r["size_m"]
    assert ins["dims_m"][0] <= w + 0.5 and (r["kit"] != "beach" or ins["dims_m"][1] <= d + 0.5)      # the sea and the backdrop are not the asset's size


def test_a_mirror_shows_the_plain_sky_not_the_hdris_location(tmp_path):
    """The boardwalk bug: the sea mirrored the HDRI's windows into frame 1. A mirror plane filling the frame under a look with a sky colour must be nearly one colour."""
    import json, os, subprocess
    import numpy as np
    from tests.worldkit.conftest import BLENDER
    out = tmp_path / "mirror.glb"
    script = tmp_path / "mirror.py"
    script.write_text(f"""import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_plane_add(size=500.0)
m = bpy.data.materials.new("mirror")
m.use_nodes = True
b = m.node_tree.nodes["Principled BSDF"]
b.inputs["Roughness"].default_value = 0.0
b.inputs["Base Color"].default_value = (1, 1, 1, 1)
b.inputs["Metallic"].default_value = 1.0
bpy.context.active_object.data.materials.append(m)
bpy.ops.export_scene.gltf(filepath={str(out)!r}, export_format="GLB")
""")
    subprocess.run([BLENDER, "-b", "--factory-startup", "--python", str(script)], check=True, capture_output=True, timeout=300, env={**os.environ, "CUDA_VISIBLE_DEVICES": ""})
    B.run("wk_turntable.py", {"model": str(out), "look": looks.resolve("overcast"), "frames": 1, "size": 96, "out_dir": str(tmp_path / "t"), "interior": False, "elevation": 0.5, "samples": 4, "engine": "cycles"}, work=tmp_path, name="t", timeout=300)
    a = np.asarray(Image.open(tmp_path / "t" / "0001.png").convert("RGB"), dtype=np.float32)
    assert float(a.std(axis=(0, 1)).max()) < 6.0, a.std(axis=(0, 1))
