"""blender -b --factory-startup --python wk_turntable.py -- PAYLOAD.json
payload {"model": glb or "" (a look: a test scene), "look", "frames", "size", "out_dir", "interior": bool,
         "elevation": camera height over its horizontal distance (0.35 looks down about 19 degrees), "kit": a place's kit (frames the orbit on the place),
         "fit": show a character in its rest pose, not caught in a clip, "samples", "engine"}
out_dir/0001.png .. NNNN.png: the camera circles the asset once (inside a room it turns on the spot), under the look.
An asset that is not a place is framed by its bounding sphere (_fit.py), so a ring and an anchor both fill the frame;
the page's "Real scale" tag says how big it really is. Colliders are hidden. PPWK {"ok", "frames"}."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import _fit  # noqa: E402
import _wk  # noqa: E402

#: A place's orbit: camera height as a share of the footprint's half diagonal, and how much of the footprint fits the frame (under 1 crops in).
PLACE_VIEW = {"street": (0.85, 0.88), "beach": (0.30, 0.72)}


def _mat(name, colour, metal=0.0, rough=0.5, glow=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1.0)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if glow:
        b.inputs["Emission Color"].default_value = (*colour, 1.0)
        b.inputs["Emission Strength"].default_value = glow
    return m


def _test_scene(look: dict) -> list:
    """A look has nothing of its own to show, so it is shown on a small street corner: ground, three blocks of different
    heights and colours, a matte and a mirror ball. A night look gets the lamps a place's builder would add, since a night sky
    lights almost nothing; fog goes in a box around the set, as world fog with nothing to stop it turns the whole frame black."""
    out = []
    bpy.ops.mesh.primitive_plane_add(size=9.0)
    g = bpy.context.active_object
    g.data.materials.append(_mat("ground", (0.32, 0.32, 0.33), rough=max(0.08, 0.7 - 0.6 * float(look.get("wet", 0.0)))))
    out.append(g)
    for (x, y, w, d, h), col in (((-2.0, 2.2, 1.6, 1.4, 2.8), (0.62, 0.30, 0.22)), ((0.0, 2.6, 1.8, 1.2, 1.8), (0.85, 0.80, 0.68)), ((2.1, 2.0, 1.3, 1.5, 3.6), (0.20, 0.42, 0.45))):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, h / 2))
        o = bpy.context.active_object
        o.scale = (w, d, h)
        o.data.materials.append(_mat("block", col, rough=0.8))
        out.append(o)
    for loc, col, metal, rough in (((-0.7, 0, 0.5), (0.80, 0.80, 0.80), 0.0, 0.6), ((0.7, 0, 0.5), (0.90, 0.90, 0.90), 1.0, 0.05)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=loc)
        o = bpy.context.active_object
        o.data.materials.append(_mat("ball", col, metal, rough))
        out.append(o)
    if look.get("night"):
        for x, y in ((-3.1, 1.0), (1.0, 1.3), (3.4, 0.9)):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=2.4, location=(x, y, 1.2))
            out.append(bpy.context.active_object)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(x, y, 2.45))
            bulb = bpy.context.active_object
            bulb.data.materials.append(_mat("bulb", (1.0, 0.75, 0.45), glow=20.0))
            lamp = bpy.data.objects.new("lamp", bpy.data.lights.new("lamp", "POINT"))
            lamp.data.energy, lamp.data.color, lamp.location = 250.0, (1.0, 0.75, 0.45), (x, y, 2.3)
            bpy.context.scene.collection.objects.link(lamp)
    fog = float(look.get("fog", 0.0))
    if fog > 0:
        bpy.ops.mesh.primitive_cube_add(size=40.0, location=(0, 0, 10))
        box = bpy.context.active_object
        m = bpy.data.materials.new("fog")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Density"].default_value = fog * 20
        nt.links.new(vol.outputs["Volume"], nt.nodes["Material Output"].inputs["Volume"])
        box.data.materials.append(m)
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
        ms = _test_scene(p["look"])
    body = _wk.solids(ms) or ms
    lo, hi = _wk.world_bounds(body)
    _wk.apply_look({**p["look"], "fog": 0.0} if not p.get("model") else p["look"])
    c = Vector([(lo[i] + hi[i]) / 2 for i in range(3)])
    dims = [hi[i] - lo[i] for i in range(3)]
    cam = bpy.data.objects.new("turn_cam", bpy.data.cameras.new("turn_cam"))
    sc.collection.objects.link(cam)
    sc.camera, cam.rotation_mode, cam.data.lens, cam.data.clip_end = cam, "QUATERNION", 18.0 if p.get("interior") else 35.0, _fit.CLIP_END
    _wk.set_engine(sc, p.get("engine", "cycles"), int(p.get("samples", 16)))
    sc.render.resolution_x = sc.render.resolution_y = int(p["size"])
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    os.makedirs(p["out_dir"], exist_ok=True)
    fov = _fit.view_angle(cam.data.lens, cam.data.sensor_width, sc.render.resolution_x, sc.render.resolution_y)
    radius = _wk.sphere_radius(body, c)
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
        elif not p.get("model"):
            # a look's street corner: the camera swings to and fro in front of the blocks, low, so the sky and the light both show, and the clip loops
            b = 0.4 * math.pi * math.sin(a)
            pos = Vector((math.sin(b) * 6.5, -math.cos(b) * 6.5, 1.5))
            look = Vector((0, 1.2, 1.1))
        else:
            # a prop, a figure, a character or a look's test scene: its bounding sphere fills the frame from every side
            xyz, cam.data.clip_start, cam.data.clip_end = _fit.orbit(c, radius, dims, fov, a, float(p.get("elevation", 0.35)))
            pos, look = Vector(xyz), c
        cam.location = pos
        cam.rotation_quaternion = (look - pos).to_track_quat("-Z", "Y")
        sc.render.filepath = os.path.join(p["out_dir"], f"{i + 1:04d}.png")
        bpy.ops.render.render(write_still=True)
    _wk.done(frames=n)


_wk.main(run)
