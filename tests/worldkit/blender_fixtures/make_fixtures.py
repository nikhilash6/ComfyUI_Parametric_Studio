"""Blender side of the World Kit test fixtures (tests/worldkit/conftest.py wk_fixtures; CPU, a few seconds).
payload {"out": dir, "skeleton": tests.worldkit.helpers.HUMANOID}. Writes:
  char.glb   a 1.70 m humanoid: 23 bones named bone_N (like an auto-rigged character), an envelope-skinned body of boxes, and a
             24-frame "walk" (thighs and arms swing) as an NLA track
  walk.fbx   the same armature + walk as FBX (a stand-in for a clip retargeted onto the rig)
  walk.bvh   the walk as BVH (the retarget tool's input)
  place.glb  a 12 x 12 m ground and a 2 x 2 x 3 m block, each with a "-colonly" collider
  prop.glb   a 0.37 x 0.20 x 0.12 m box away from the origin (cleanup must scale and centre it)"""
import json
import os
import sys

import bpy
from mathutils import Vector

P = json.load(open(sys.argv[-1], encoding="utf-8"))
OUT, SK = P["out"], P["skeleton"]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def cube(name, loc, scale):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name, o.scale = name, scale
    return o


def slot(holder, act):
    slots = getattr(act, "slots", None)
    if slots is not None and len(slots) and hasattr(holder, "action_slot"):
        holder.action_slot = slots[0]


def char():
    reset()
    data = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    names = {}
    for i, (n, parent, h, t) in enumerate(SK):
        b = data.edit_bones.new(f"bone_{i}")
        b.head, b.tail = Vector(h), Vector(t)
        if parent:
            b.parent = data.edit_bones[names[parent]]
        names[n] = b.name
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = []
    for n, parent, h, t in SK:
        hv, tv = Vector(h), Vector(t)
        o = cube(f"part_{n}", (hv + tv) / 2, (0.07, 0.07, max((tv - hv).length, 0.03)))
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = (tv - hv).to_track_quat("Z", "Y")
        parts.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = "body"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    body.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
    ad = arm.animation_data_create()
    act = bpy.data.actions.new("walk")
    ad.action = act
    for f, a in ((1, 0.4), (12, -0.4), (24, 0.4)):
        for n, sign in (("l_upleg", 1), ("r_upleg", -1), ("l_arm", -1), ("r_arm", 1)):
            pb = arm.pose.bones[names[n]]
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (sign * a, 0.0, 0.0)
            pb.keyframe_insert("rotation_euler", frame=f)
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 24
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    body.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "walk.fbx"), use_selection=True, bake_anim=True,
                             add_leaf_bones=False, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_anim.bvh(filepath=os.path.join(OUT, "walk.bvh"), frame_start=1, frame_end=24)
    track = ad.nla_tracks.new()
    track.name = "walk"
    strip = track.strips.new("walk", 1, act)
    slot(strip, act)
    ad.action = None
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "char.glb"), export_format="GLB", export_animations=True,
                              export_animation_mode="NLA_TRACKS")


def place():
    reset()
    bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0, 0, 0))
    bpy.context.active_object.name = "ground"
    cube("ground-colonly", (0, 0, -0.05), (12, 12, 0.1))
    cube("block", (3, 3, 1.5), (2, 2, 3))
    cube("block-colonly", (3, 3, 1.5), (2, 2, 3))
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "place.glb"), export_format="GLB")


def prop():
    reset()
    cube("box", (5, 2, 1), (0.37, 0.20, 0.12))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "prop.glb"), export_format="GLB")


char()
place()
prop()
print("PPWK " + json.dumps({"ok": True, "files": sorted(os.listdir(OUT))}), flush=True)
