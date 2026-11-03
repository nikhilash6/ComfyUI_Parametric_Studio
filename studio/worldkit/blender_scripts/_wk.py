"""Shared helpers for the World Kit / Virtual Set Blender scripts. A script puts this folder on sys.path and imports it;
only Blender's own Python is used (bpy, mathutils, numpy). Contract: read the payload file named after "--", do the
work, print one `PPWK {json}` line (main() prints {"ok": false, "error"} and exits 1 on any exception). Nothing here
installs or downloads anything: the looks use Blender's bundled studio-light HDRIs."""
import json
import math
import os
import sys
import traceback

import bpy

TAG = "PPWK "
COLLIDER_SUFFIXES = ("-colonly", "-convcolonly", "-col")
BACKDROP = ("backdrop", "sea")          # scenery out to the horizon: in the file and the render, but not part of the asset's size


def payload() -> dict:
    with open(sys.argv[-1], encoding="utf-8") as fh:                # last, so Cycles' own --cycles-device can sit after "--" too
        return json.load(fh)


def done(**data) -> None:
    print(TAG + json.dumps({"ok": True, **data}), flush=True)


def main(fn) -> None:
    try:
        fn(payload())
    except Exception as exc:
        traceback.print_exc()
        print(TAG + json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:800]}), flush=True)
        sys.exit(1)


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def is_collider(o) -> bool:
    return o.name.lower().split(".")[0].endswith(COLLIDER_SUFFIXES)


def import_model(path: str) -> list:
    """Import one model file; returns its new objects (the glTF importer's bone-display icosphere removed)."""
    before = set(bpy.data.objects)
    ext = path.lower().rsplit(".", 1)[-1]
    if ext in ("glb", "gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == "fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == "obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == "bvh":
        bpy.ops.import_anim.bvh(filepath=path)
    else:
        raise ValueError(f"unsupported model type: {ext}")
    new = [o for o in bpy.data.objects if o not in before]
    shapes = {pb.custom_shape for o in new if o.type == "ARMATURE" for pb in o.pose.bones if pb.custom_shape}
    keep = [o for o in new if o not in shapes]
    for o in shapes:
        bpy.data.objects.remove(o, do_unlink=True)
    return keep


def meshes(objs) -> list:
    return [o for o in objs if o.type == "MESH" and len(o.data.polygons) and not is_collider(o)]


def is_backdrop(o) -> bool:
    return o.name.lower().split(".")[0].startswith(BACKDROP)


def solids(objs) -> list:
    """The meshes that count as the asset: no colliders, no backdrop."""
    return [o for o in meshes(objs) if not is_backdrop(o)]


def world_bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    if not pts:
        raise ValueError("no vertices to measure")
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def sphere_radius(objs, centre) -> float:
    """The farthest vertex of `objs` from `centre`, in world space: the radius of the sphere the turntable frames."""
    import numpy as np
    bpy.context.view_layer.update()
    c = np.array(centre[:3], dtype=np.float64)
    best = 0.0
    for o in objs:
        n = len(o.data.vertices)
        if not n:
            continue
        co = np.empty(n * 3, dtype=np.float32)
        o.data.vertices.foreach_get("co", co)
        m = np.array(o.matrix_world, dtype=np.float64)
        pts = co.reshape(-1, 3).astype(np.float64) @ m[:3, :3].T + m[:3, 3]
        best = max(best, float(np.sqrt(((pts - c) ** 2).sum(axis=1)).max()))
    return best


def bones(objs) -> list:
    out = []
    for a in [o for o in objs if o.type == "ARMATURE"]:
        mw = a.matrix_world
        for b in a.data.bones:
            out.append({"name": b.name, "parent": b.parent.name if b.parent else "",
                        "head": [round(c, 5) for c in mw @ b.head_local],
                        "tail": [round(c, 5) for c in mw @ b.tail_local]})
    return out


def inspect(objs) -> dict:
    ms = meshes(objs)
    lo, hi = world_bounds(solids(objs) or ms) if ms else ([0.0] * 3, [0.0] * 3)
    dims = [hi[i] - lo[i] for i in range(3)]
    return {"loaded": True, "meshes": len(ms),
            "tris": sum(len(p.vertices) - 2 for o in ms for p in o.data.polygons),
            "lo": [round(x, 4) for x in lo], "hi": [round(x, 4) for x in hi],
            "dims_m": [round(x, 4) for x in dims], "height_m": round(dims[2], 4),
            "armatures": sum(1 for o in objs if o.type == "ARMATURE"), "bones": bones(objs),
            "colliders": sum(1 for o in objs if o.type == "MESH" and is_collider(o)),
            "actions": sorted(a.name for a in bpy.data.actions)}


def export_glb(path: str, *, animations: bool = False, lights: bool = False) -> None:
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True, export_apply=False, export_lights=lights,
                              export_animations=animations,
                              export_animation_mode="NLA_TRACKS" if animations else "ACTIONS")


def use_slot(holder, act) -> None:
    """Blender 4.4+ slotted actions: point an NLA strip (or animation data) at the action's first slot."""
    slots = getattr(act, "slots", None)
    if slots is not None and len(slots) and hasattr(holder, "action_slot"):
        try:
            holder.action_slot = slots[0]
        except (AttributeError, TypeError, RuntimeError):
            pass


def play_clip(arm, clip: str, repeat: float = 1.0):
    """Play one clip of a World Kit character on loop: imported NLA tracks are cleared and the clip's action becomes one
    strip repeated `repeat` times (a clip shorter than the shot loops; it never freezes on its last pose)."""
    ad = arm.animation_data or arm.animation_data_create()
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    ad.action = None
    act = bpy.data.actions.get(clip) or next((a for a in bpy.data.actions if a.name.startswith(clip)), None)
    if act is None:
        raise ValueError(f"the character has no clip {clip!r} (it has {sorted(a.name for a in bpy.data.actions)})")
    track = ad.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, int(act.frame_range[0]), act)
    use_slot(strip, act)
    strip.repeat = max(1.0, float(repeat))
    strip.extrapolation = "HOLD_FORWARD"
    return strip


def armature_height(arm) -> float:
    zs = [(arm.matrix_world @ b.head_local).z for b in arm.data.bones]
    zs += [(arm.matrix_world @ b.tail_local).z for b in arm.data.bones]
    return max(zs) - min(zs) if zs else 0.0


def force_cpu(sc) -> None:
    """Cycles on the CPU, by every switch there is: the scene's device and the add-on's compute device."""
    sc.cycles.device = "CPU"
    try:
        bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "NONE"
    except (KeyError, AttributeError, TypeError):
        pass


def set_engine(sc, engine: str, samples: int = 16) -> None:
    if engine == "eevee":
        sc.render.engine = "BLENDER_EEVEE"
        try:
            sc.eevee.taa_render_samples = int(samples)
        except AttributeError:
            pass
    else:
        sc.render.engine = "CYCLES"
        force_cpu(sc)
        sc.cycles.samples = int(samples)
        sc.cycles.use_denoising = True                              # Open Image Denoise, CPU: low samples stay clean
        sc.cycles.denoiser = "OPENIMAGEDENOISE"


def _studio_world(name: str) -> str:
    base = bpy.utils.system_resource("DATAFILES", path=os.path.join("studiolights", "world")) or ""
    path = os.path.join(base, f"{name}.exr")
    return path if name and os.path.isfile(path) else ""


def apply_look(look: dict) -> None:
    """A look (worldkit/looks.py resolve()): a bundled HDRI world (Blender's own studio lights), an optional sun, fog
    and exposure. Wet surfaces and night practicals are the scene builder's business."""
    sc = bpy.context.scene
    world = bpy.data.worlds.new("look")
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = float(look.get("world_strength", 1.0))
    hdri = _studio_world(str(look.get("world", "")))
    if hdri:
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri)
        sky = look.get("sky_colour")
        if sky:                                 # the HDRI lights the scene; the camera and anything mirror-like (sea, glass, wet road) see plain sky: an HDRI shows its own location, windows and all
            ray = nt.nodes.new("ShaderNodeLightPath")
            seen = nt.nodes.new("ShaderNodeMath")
            seen.operation = "MAXIMUM"
            nt.links.new(ray.outputs["Is Camera Ray"], seen.inputs[0])
            nt.links.new(ray.outputs["Is Glossy Ray"], seen.inputs[1])
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.inputs["B"].default_value = (*sky, 1.0)
            nt.links.new(seen.outputs["Value"], mix.inputs[0])
            nt.links.new(env.outputs["Color"], mix.inputs["A"])
            nt.links.new(mix.outputs["Result"], bg.inputs["Color"])
        else:
            nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    else:
        bg.inputs["Color"].default_value = (*look.get("sky_colour", (0.5, 0.6, 0.7)), 1.0)
    fog = float(look.get("fog", 0.0))
    if fog > 0:
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Density"].default_value = fog
        nt.links.new(vol.outputs["Volume"], nt.nodes["World Output"].inputs["Volume"])
    sc.world = world
    sun = look.get("sun") or look.get("moon")
    if sun:
        light = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sc.collection.objects.link(light)
        light.data.energy = float(sun.get("strength", 3.0))
        light.data.color = tuple(sun.get("colour", (1.0, 0.97, 0.92)))
        light.rotation_euler = (math.radians(90.0 - float(sun.get("elevation_deg", 45.0))), 0.0,
                                math.radians(float(sun.get("azimuth_deg", 135.0))))
    sc.view_settings.exposure = float(look.get("exposure", 0.0))


def colour_raw(sc) -> dict:
    """Data passes (depth, ids) are written as rendered: no view transform, look or exposure. Returns what to restore."""
    vs = sc.view_settings
    before = {"view_transform": vs.view_transform, "look": vs.look, "exposure": vs.exposure, "gamma": vs.gamma}
    try:
        vs.view_transform = "Raw"
    except TypeError:
        vs.view_transform = "Standard"
    vs.look, vs.exposure, vs.gamma = "None", 0.0, 1.0
    return before


def colour_restore(sc, before: dict) -> None:
    for k, v in before.items():
        setattr(sc.view_settings, k, v)
