"""blender -b --factory-startup --python wk_assemble.py -- PAYLOAD.json
payload {"rig": rigged character glb, "clips": [{"name", "path" (an FBX retargeted onto this rig)}], "height_m", "out"}
The character asset: the rigged mesh under a new root scaled to height_m (an object scale, so root motion
scales with it), feet on the ground at the origin. Each clip is transferred onto the character's own armature
rest-relative in world space, frame by frame: every bone turns away from its rest pose exactly as the same-named clip
bone turns away from its own rest (so a bone-axis difference between the FBX and glTF importers cancels out), and the
root bone also follows the clip's root travel. Each clip becomes an NLA track named after it; one glb out (animations
= NLA tracks), re-imported to report inspect facts and the clips. CPU, no render."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix  # noqa: E402

import _wk  # noqa: E402


def _transfer(arm, src, f0: int, f1: int, name: str):
    sc = bpy.context.scene
    names = [b.name for b in arm.data.bones if b.name in src.pose.bones]
    order = sorted(names, key=lambda n: len(arm.data.bones[n].parent_recursive))
    ad = arm.animation_data or arm.animation_data_create()
    act = bpy.data.actions.new(name)
    ad.action = act
    _wk.use_slot(ad, act)
    for n in order:
        arm.pose.bones[n].rotation_mode = "QUATERNION"
    inv_arm = arm.matrix_world.inverted()
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        for n in order:
            sb, db = src.pose.bones[n], arm.pose.bones[n]
            delta = (src.matrix_world @ sb.matrix) @ (src.matrix_world @ src.data.bones[n].matrix_local).inverted()
            target = delta @ (arm.matrix_world @ arm.data.bones[n].matrix_local)
            if db.parent is not None:              # rotation only: the head stays where the parent puts it
                cur = arm.matrix_world @ db.matrix
                target = Matrix.LocRotScale(cur.to_translation(), target.to_quaternion(), cur.to_scale())
            db.matrix = inv_arm @ target
            bpy.context.view_layer.update()
            db.keyframe_insert("rotation_quaternion", frame=f)
            if db.parent is None:
                db.keyframe_insert("location", frame=f)
    ad.action = None
    return act


def _clip(arm, path: str, name: str) -> dict:
    before = set(bpy.data.objects)
    new = _wk.import_model(path)
    src = next((o for o in new if o.type == "ARMATURE"), None)
    if src is None or not (src.animation_data and src.animation_data.action):
        raise ValueError(f"{os.path.basename(path)} has no animated armature")
    f0, f1 = (int(x) for x in src.animation_data.action.frame_range)
    h_src, h_dst = _wk.armature_height(src), _wk.armature_height(arm)
    if h_src > 0 and h_dst > 0:
        s = h_dst / h_src
        src.scale = (src.scale[0] * s, src.scale[1] * s, src.scale[2] * s)
    bpy.context.view_layer.update()
    act = _transfer(arm, src, f0, f1, name)
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, f0, act)
    _wk.use_slot(strip, act)
    act.use_fake_user = True
    for o in [o for o in bpy.data.objects if o not in before]:
        bpy.data.objects.remove(o, do_unlink=True)
    return {"name": name, "frames": f1 - f0 + 1}


def run(p):
    _wk.reset()
    objs = _wk.import_model(p["rig"])
    arms = [o for o in objs if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise ValueError(f"the rigged character has {len(arms)} armatures, expected 1")
    arm = arms[0]
    if arm.animation_data:                       # imported test motions are not the character's clips
        for t in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(t)
        arm.animation_data.action = None
    lo, hi = _wk.world_bounds(_wk.meshes(objs))
    height = hi[2] - lo[2]
    if height <= 0:
        raise ValueError("the character has no height")
    root = bpy.data.objects.new("root", None)
    bpy.context.scene.collection.objects.link(root)
    for o in [o for o in objs if o.parent is None]:
        o.location = (o.location[0] - (lo[0] + hi[0]) / 2, o.location[1] - (lo[1] + hi[1]) / 2, o.location[2] - lo[2])
        o.parent = root
    s = float(p["height_m"]) / height
    root.scale = (s, s, s)
    bpy.context.view_layer.update()
    clips = [_clip(arm, c["path"], c["name"]) for c in p.get("clips") or []]
    fps = bpy.context.scene.render.fps
    _wk.export_glb(p["out"], animations=bool(clips))
    _wk.reset()
    _wk.done(inspect=_wk.inspect(_wk.import_model(p["out"])), clips=[{**c, "fps": fps} for c in clips])


_wk.main(run)
