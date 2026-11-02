"""blender -b --factory-startup --python wk_clip_film.py -- PAYLOAD.json
payload {"character": a rigged glb with clips, "clip": its name, "out_dir", "size": [w, h], "samples", "every": render every Nth frame, "view": "front" or "three_quarter", "floor": true}
out_dir/0001.png..: the clip played on the character on a marked floor, the camera steady and following the hips sideways only, so sliding feet show against the marks. PPWK {"ok", "frames", "fps"}."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import _wk  # noqa: E402


def _floor():
    bpy.ops.mesh.primitive_plane_add(size=40.0)
    o = bpy.context.active_object
    m = bpy.data.materials.new("floor")
    m.use_nodes = True
    t = m.node_tree
    tex = t.nodes.new("ShaderNodeTexChecker")
    tex.inputs["Scale"].default_value = 80.0        # half-metre squares on a 40 m plane
    tex.inputs["Color1"].default_value = (.46, .47, .49, 1)
    tex.inputs["Color2"].default_value = (.38, .39, .41, 1)
    t.links.new(tex.outputs[0], t.nodes["Principled BSDF"].inputs["Base Color"])
    t.nodes["Principled BSDF"].inputs["Roughness"].default_value = .85
    o.data.materials.append(m)


def run(p):
    _wk.reset()
    sc = bpy.context.scene
    objs = _wk.import_model(p["character"])
    arm = next(o for o in objs if o.type == "ARMATURE")
    root = next(b.name for b in arm.data.bones if b.parent is None)
    _wk.play_clip(arm, p["clip"])
    act = bpy.data.actions.get(p["clip"]) or next(a for a in bpy.data.actions if a.name.startswith(p["clip"]))
    f0, f1 = (int(x) for x in act.frame_range)
    _wk.force_cpu(sc)
    sc.render.engine = "CYCLES"
    sc.cycles.samples = int(p.get("samples", 16))
    sc.cycles.use_denoising = True
    w, h = p.get("size") or [720, 960]
    sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
    sc.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.62, .65, .7, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .75
    sc.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(25))
    sc.collection.objects.link(sun)
    if p.get("floor", True):
        _floor()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens = 50
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.frame_set(f0)
    bpy.context.view_layer.update()
    mesh = next(o for o in objs if o.type == "MESH")
    tall = max((mesh.matrix_world @ Vector(c)).z for c in mesh.bound_box)
    angle = math.radians({"three_quarter": 30, "side": 90}.get(p.get("view"), 0))
    dist = max(2.6, tall * 1.95)
    os.makedirs(p["out_dir"], exist_ok=True)
    frames = list(range(f0, f1 + 1, int(p.get("every", 1))))
    for i, f in enumerate(frames, 1):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        hip = arm.matrix_world @ arm.pose.bones[root].head
        at = Vector((hip.x, hip.y, tall * .52))
        cam.location = at + Vector((math.sin(angle) * dist, -math.cos(angle) * dist, tall * .08))
        cam.rotation_euler = (at - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(p["out_dir"], f"{i:04d}.png")
        bpy.ops.render.render(write_still=True)
    _wk.done(frames=len(frames), fps=sc.render.fps / sc.render.fps_base / int(p.get("every", 1)))


_wk.main(run)
