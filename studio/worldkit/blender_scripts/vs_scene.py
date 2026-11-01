"""blender -b --factory-startup --python vs_scene.py -- PAYLOAD.json   (payload: vset/passes.py scene_payload + out_dir)
The Virtual Set shot: the place, the props at their transforms and any cast (each walking its marks, its clip looping; the clip's own ground travel is cancelled so the marks decide where the character goes), under the look,
the camera on its per-frame keys. Renders shaded/####.png (the look), depth/####.png (near = white, far and sky = black, via a material override; data colour management) and ids/####.png (one flat colour per object), and writes
pose3d.json (the cast's humanoid bones in world space per frame, plus each member's facing). Depth and ids are data: one sample, no denoiser, no dither, and a sharp pixel filter on the ids so a border is never a blend of two colours.
PPWK {"ok", "frames", "engine"}."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Quaternion, Vector  # noqa: E402

import _wk  # noqa: E402


def _root(objs, name):
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None:
            o.parent = root
    return root


def _hide_colliders(objs):
    for o in objs:
        if _wk.is_collider(o):
            o.hide_render = True


def _cast(c, n):
    sc = bpy.context.scene
    objs = _wk.import_model(c["path"])
    _hide_colliders(objs)
    root = _root(objs, "cast")
    arm = next((o for o in objs if o.type == "ARMATURE"), None)
    drift = [(0.0, 0.0)] * n
    hips = c["slots"].get("hips")
    if arm is not None:
        _wk.play_clip(arm, c["clip"], c["repeat"])
        if hips in arm.pose.bones:                 # measure the clip's own ground travel, then cancel it
            rest = arm.matrix_world @ arm.data.bones[hips].head_local
            drift = []
            for f in range(1, n + 1):
                sc.frame_set(f)
                hp = arm.matrix_world @ arm.pose.bones[hips].head
                drift.append((hp.x - rest.x, hp.y - rest.y))
    for f in range(1, n + 1):
        (x, y), yaw = c["positions"][f - 1], math.radians(c["yaw_deg"][f - 1])
        dx, dy = drift[f - 1]
        root.location = (x - (dx * math.cos(yaw) - dy * math.sin(yaw)), y - (dx * math.sin(yaw) + dy * math.cos(yaw)), 0)
        root.rotation_euler = (0.0, 0.0, yaw)
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
    if c.get("hidden"):
        for o in objs:
            o.hide_render = True
    return arm, root, c["slots"]


def _camera(keys):
    cam = bpy.data.objects.new("shot_cam", bpy.data.cameras.new("shot_cam"))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.sensor_fit, cam.data.sensor_width = "AUTO", 36.0
    cam.data.clip_start, cam.data.clip_end = 0.05, 500.0
    cam.rotation_mode = "QUATERNION"
    for f, k in enumerate(keys, 1):
        pos, look = Vector(k["pos"]), Vector(k["look"])
        cam.location = pos
        cam.rotation_quaternion = (look - pos).to_track_quat("-Z", "Y") @ Quaternion(
            (0.0, 0.0, 1.0), math.radians(k.get("roll_deg", 0.0)))
        cam.data.lens = k["lens_mm"]
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        cam.data.keyframe_insert("lens", frame=f)
    bpy.context.scene.camera = cam


def _emission(name, wire):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em, out = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    wire(nt, em)
    return m


def _depth_material(near, far):
    def wire(nt, em):
        cam, mr = nt.nodes.new("ShaderNodeCameraData"), nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = near, far
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0
        mr.clamp = True
        z = cam.outputs.get("View Z Depth") or cam.outputs[1]
        nt.links.new(z, mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], em.inputs["Color"])
    return _emission("vs_depth", wire)


def _id_material():
    def wire(nt, em):
        info, hsv = nt.nodes.new("ShaderNodeObjectInfo"), nt.nodes.new("ShaderNodeCombineColor")
        hsv.mode = "HSV"
        nt.links.new(info.outputs["Random"], hsv.inputs[0])
        hsv.inputs[1].default_value, hsv.inputs[2].default_value = 0.85, 1.0
        nt.links.new(hsv.outputs["Color"], em.inputs["Color"])
    return _emission("vs_ids", wire)


def _data_quality(sc):
    sc.render.dither_intensity = 0.0             # Blender dithers 8-bit output by default: one id colour would come out as many, and every pixel would read as a border
    if sc.render.engine == "CYCLES":
        sc.cycles.samples, sc.cycles.use_denoising = 1, False
        sc.cycles.pixel_filter_type, sc.cycles.filter_width = "BOX", 0.01


def _sequence(sc, out_dir, name, colour="RGB"):
    os.makedirs(os.path.join(out_dir, name), exist_ok=True)
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = colour
    sc.render.image_settings.color_depth = "8"
    sc.render.filepath = os.path.join(out_dir, name, "####")
    bpy.ops.render.render(animation=True)


def run(p):
    _wk.reset()
    sc = bpy.context.scene
    n, (w, h) = int(p["frames"]), p["size"]
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = int(w), int(h), 100
    sc.render.fps, sc.frame_start, sc.frame_end = int(p["fps"]), 1, n
    _hide_colliders(_wk.import_model(p["place"]))
    for pr in p.get("props") or []:
        objs = _wk.import_model(pr["path"])
        _hide_colliders(objs)
        root = _root(objs, "prop")
        root.location = pr["pos"]
        root.rotation_euler = [math.radians(a) for a in pr.get("rot_deg", [0, 0, 0])]
        root.scale = (pr.get("scale", 1.0),) * 3
    rigs = [_cast(c, n) for c in p["cast"]]
    _camera(p["camera"])
    _wk.apply_look(p["look"])
    _wk.set_engine(sc, p.get("engine", "cycles"), int(p.get("samples", 16)))
    frames = []
    for f in range(1, n + 1):
        sc.frame_set(f)
        people = []
        for arm, root, slots in rigs:
            if arm is None or not slots:
                people.append(None)
                continue
            mw = arm.matrix_world
            pts = {s: [list(mw @ arm.pose.bones[b].head), list(mw @ arm.pose.bones[b].tail)]
                   for s, b in slots.items() if b in arm.pose.bones}
            fwd = (root.matrix_world.to_3x3() @ Vector((0.0, -1.0, 0.0))).normalized()
            people.append({"slots": pts, "forward": list(fwd)})
        frames.append({"cast": people})
    os.makedirs(p["out_dir"], exist_ok=True)
    with open(os.path.join(p["out_dir"], "pose3d.json"), "w", encoding="utf-8") as fh:
        json.dump({"frames": frames}, fh)
    _sequence(sc, p["out_dir"], "shaded")
    look_world = sc.world
    if p.get("clay"):                            # a grey clay viewport of the same shot, for LTX-2.5 Layout to Render
        grey = bpy.data.worlds.new("clay")
        grey.use_nodes = True
        grey.node_tree.nodes["Background"].inputs["Color"].default_value = (0.32, 0.32, 0.32, 1.0)
        sc.world = grey
        clay = bpy.data.materials.new("vs_clay")
        clay.use_nodes = True
        bsdf = clay.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value, bsdf.inputs["Roughness"].default_value = (0.5, 0.5, 0.5, 1.0), 0.8
        bpy.context.view_layer.material_override = clay
        _sequence(sc, p["out_dir"], "clay")
        bpy.context.view_layer.material_override = None
    black = bpy.data.worlds.new("black")
    black.use_nodes = True
    black.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    sc.world = black
    before = _wk.colour_raw(sc)
    _data_quality(sc)
    vl = bpy.context.view_layer
    vl.material_override = _depth_material(*p["depth_range"])
    _sequence(sc, p["out_dir"], "depth", "BW")
    vl.material_override = _id_material()
    _sequence(sc, p["out_dir"], "ids")
    vl.material_override = None
    _wk.colour_restore(sc, before)
    sc.world = look_world
    _wk.done(frames=n, engine=sc.render.engine)


_wk.main(run)
