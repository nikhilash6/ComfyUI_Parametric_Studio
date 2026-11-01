"""blender -b --factory-startup --python wk_cleanup.py -- PAYLOAD.json
payload {"model": glb/obj/fbx, "size_m": float, "name": str, "out": glb}
A prop: every mesh joined into one static object (armatures and
their modifiers dropped, transforms applied), scaled so its longest side is size_m, the pivot at its bottom centre on
the origin, plus a "<name>-colonly" box collider (Godot's import convention). PPWK {"ok", "inspect"} of the written
file. CPU, no render."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import _wk  # noqa: E402


def _slug(name) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(name or "").lower()).strip("_")[:40] or "prop"


def run(p):
    _wk.reset()
    objs = _wk.import_model(p["model"])
    ms = _wk.meshes(objs)
    if not ms:
        raise ValueError("no mesh with faces in the file")
    bpy.context.view_layer.update()
    for o in ms:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        for m in [m for m in o.modifiers if m.type == "ARMATURE"]:
            o.modifiers.remove(m)
    for o in [o for o in bpy.data.objects if o not in ms]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in ms:
        o.select_set(True)
    bpy.context.view_layer.objects.active = ms[0]
    if len(ms) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    lo, hi = _wk.world_bounds([obj])
    size = max(hi[i] - lo[i] for i in range(3))
    if size <= 0:
        raise ValueError("the mesh has no size")
    base = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
    obj.data.transform(Matrix.Scale(float(p["size_m"]) / size, 4) @ Matrix.Translation(-base))
    obj.data.update()
    obj.name = _slug(p.get("name"))
    lo, hi = _wk.world_bounds([obj])
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=[(lo[i] + hi[i]) / 2 for i in range(3)])
    col = bpy.context.active_object
    col.name = f"{obj.name}-colonly"
    col.scale = [max(hi[i] - lo[i], 0.01) for i in range(3)]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _wk.export_glb(p["out"])
    _wk.reset()
    _wk.done(inspect=_wk.inspect(_wk.import_model(p["out"])))


_wk.main(run)
