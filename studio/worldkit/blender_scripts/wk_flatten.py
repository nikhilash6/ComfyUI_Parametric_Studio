"""blender -b --factory-startup --python wk_flatten.py -- PAYLOAD.json
payload {"mesh": a body glb from SAM 3D Body, "out"}
SAM 3D Body's glb is a pose file: one mesh with face shape keys, skinned to its own armature. The remesher and the rigger want a plain surface, so this bakes what the mesh shows now (the pose and the face) into plain geometry and drops the armature, the shape keys and any animation. CPU, no render."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

import _wk  # noqa: E402


def run(p):
    _wk.reset()
    objs = _wk.import_model(p["mesh"])
    sources = _wk.meshes(objs)
    if not sources:
        raise ValueError("the body file has no mesh")
    dg = bpy.context.evaluated_depsgraph_get()
    plain = []
    for o in sources:
        ev = o.evaluated_get(dg)
        new = bpy.data.objects.new(o.name + "_plain", bpy.data.meshes.new_from_object(ev, depsgraph=dg))
        new.matrix_world = o.matrix_world.copy()
        plain.append(new)
    for o in [o for o in bpy.data.objects if o not in plain]:
        bpy.data.objects.remove(o, do_unlink=True)
    for o in plain:
        bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    _wk.export_glb(p["out"], animations=False)
    _wk.reset()
    _wk.done(inspect=_wk.inspect(_wk.import_model(p["out"])))


_wk.main(run)
