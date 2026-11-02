"""blender -b --factory-startup --python gb_gameready.py -- PAYLOAD.json
payload {"model": glb/obj/fbx, "out": glb, "faces": int, "texture": int, "colour_only": bool}
A generated mesh made fit for a game: every part joined into one static object, reduced to a face budget, its textures shrunk (colour to `texture`, normal and roughness to half), pivot at the bottom centre, standing on the origin. Scale is left alone: the kit sets it from the spec. No collider: a kit makes its own from the object's bounds. With "keep_scale_only" nothing is joined or reduced. CPU, no render."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import _wk  # noqa: E402


def _shrink_images(limit: int) -> None:
    for img in bpy.data.images:
        if img.size[0] <= 1 or img.type != "IMAGE":
            continue
        colour = "base" in img.name.lower() or "albedo" in img.name.lower() or img.colorspace_settings.name == "sRGB"
        want = limit if colour else max(limit // 2, 256)
        if max(img.size) > want:
            img.scale(want, want)
            img.pack()


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
    faces = len(obj.data.polygons)
    want = int(p.get("faces") or 0)
    if want and faces > want:
        mod = obj.modifiers.new("gb", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = want / faces
        bpy.ops.object.modifier_apply(modifier=mod.name)
    lo, hi = _wk.world_bounds([obj])
    base = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
    obj.data.transform(Matrix.Translation(-base))
    obj.data.update()
    obj.location = (0, 0, 0)
    obj.name = "mesh"
    _shrink_images(int(p.get("texture") or 1024))
    _wk.export_glb(p["out"])
    _wk.reset()
    _wk.done(inspect=_wk.inspect(_wk.import_model(p["out"])), faces_in=faces)


_wk.main(run)
