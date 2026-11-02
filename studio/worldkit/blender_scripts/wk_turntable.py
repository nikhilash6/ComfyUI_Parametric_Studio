"""blender -b --factory-startup --python wk_turntable.py -- PAYLOAD.json
payload {"model": glb or "" (a look: a test scene), "look", "frames", "size", "out_dir", "interior": bool,
         "elevation": camera height as a share of the asset's size, "kit": a place's kit (frames the orbit on the place), "fit": fill the frame with the asset, in its rest pose (a character), "samples", "engine"}
out_dir/0001.png .. NNNN.png: the camera circles the asset once (inside a room it turns on the spot), under the look.
Colliders are hidden. PPWK {"ok", "frames"}."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import _wk  # noqa: E402

#: A place's orbit: camera height as a share of the footprint's half diagonal, and how much of the footprint fits the frame (under 1 crops in).
PLACE_VIEW = {"street": (0.85, 0.88), "beach": (0.30, 0.72)}
FIT_MARGIN = 1.04


def _test_scene() -> list:
    out = []
    bpy.ops.mesh.primitive_plane_add(size=6.0)
    out.append(bpy.context.active_object)
    for loc, metal in (((0, 0, 0.5), 0.0), ((1.2, 0, 0.5), 1.0)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=loc)
        o = bpy.context.active_object
        m = bpy.data.materials.new("ball")
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = metal
        o.data.materials.append(m)
        out.append(o)
    bpy.ops.mesh.primitive_cube_add(size=0.6, location=(-1.2, 0, 0.3))
    out.append(bpy.context.active_object)
    return out


def run(p):
    _wk.reset()
    sc = bpy.context.scene
    if p.get("model"):
        objs = _wk.import_model(p["model"])
        for o in objs:
            if _wk.is_collider(o):
                o.hide_render = True
        ms = _wk.meshes(objs)
        if p.get("fit"):                       # the turntable shows the character as built, not caught in the first frame of a clip
            for a in [o for o in objs if o.type == "ARMATURE" and o.animation_data]:
                a.animation_data.use_nla = False
                a.animation_data.action = None
                for pb in a.pose.bones:        # dropping the clip leaves its last pose on the bones
                    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
                    pb.rotation_euler = (0, 0, 0)
            bpy.context.view_layer.update()
    else:
        ms = _test_scene()
    lo, hi = _wk.world_bounds(_wk.solids(ms) or ms)
    _wk.apply_look(p["look"])
    c = Vector([(lo[i] + hi[i]) / 2 for i in range(3)])
    r = max(hi[i] - lo[i] for i in range(3))
    cam = bpy.data.objects.new("turn_cam", bpy.data.cameras.new("turn_cam"))
    sc.collection.objects.link(cam)
    sc.camera, cam.rotation_mode, cam.data.lens, cam.data.clip_end = cam, "QUATERNION", 18.0 if p.get("interior") else 35.0, 8000.0
    _wk.set_engine(sc, p.get("engine", "cycles"), int(p.get("samples", 16)))
    sc.render.resolution_x = sc.render.resolution_y = int(p["size"])
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    os.makedirs(p["out_dir"], exist_ok=True)
    n = int(p["frames"])
    for i in range(n):
        a = 2 * math.pi * i / n
        if p.get("interior"):
            pos = Vector((c.x, c.y, 1.6))
            look = pos + Vector((math.cos(a), math.sin(a), -0.1))
        elif p.get("kit"):
            # a place: close enough that it fills the frame, low enough to see its fronts and the horizon, aimed at the ground it stands on
            foot = math.hypot(hi[0] - lo[0], hi[1] - lo[1]) / 2
            high, near = PLACE_VIEW.get(p["kit"], (0.3, 0.85))
            dist = foot * near / math.tan(cam.data.angle / 2)
            pos = Vector((c.x + math.sin(a) * dist, c.y - math.cos(a) * dist, lo[2] + foot * high))
            look = Vector((c.x, c.y, lo[2] + min(hi[2] - lo[2], 6.0) * 0.3))
        elif p.get("fit"):
            half = (Vector(hi) - Vector(lo)).length / 2
            dist = half * FIT_MARGIN / math.tan(cam.data.angle / 2)
            pos = c + Vector((math.sin(a) * dist, -math.cos(a) * dist, r * float(p.get("elevation", 0.1))))
            look = c
        else:
            dist = r * 1.6 + 0.5
            pos = c + Vector((math.sin(a) * dist, -math.cos(a) * dist, r * float(p.get("elevation", 0.35)) + 0.3))
            look = c
        cam.location = pos
        cam.rotation_quaternion = (look - pos).to_track_quat("-Z", "Y")
        sc.render.filepath = os.path.join(p["out_dir"], f"{i + 1:04d}.png")
        bpy.ops.render.render(write_still=True)
    _wk.done(frames=n)


_wk.main(run)
