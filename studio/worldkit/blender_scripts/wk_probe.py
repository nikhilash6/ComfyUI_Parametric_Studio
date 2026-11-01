"""blender -b --factory-startup --python wk_probe.py -- PAYLOAD.json   payload {"engine": "eevee"|"cycles", "out": png}

Probe: a cube, a camera and a sun, one 64 x 64 frame with the asked engine, written to payload["out"]. Prints one
PPWK {"ok", "engine", "gpu_backend", "version", "seconds"} line (gpu_backend is "" when Blender has no GPU context)."""
import json
import sys
import time

import bpy


def main():
    p = json.loads(open(sys.argv[-1], encoding="utf-8").read())
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.location, cam.rotation_euler = (0.0, -4.0, 1.5), (1.25, 0.0, 0.0)
    sc.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sc.collection.objects.link(sun)
    if p["engine"] == "eevee":
        sc.render.engine = "BLENDER_EEVEE"
    else:
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "NONE"
        sc.cycles.samples = 1
    sc.render.resolution_x = sc.render.resolution_y = 64
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = p["out"]
    bpy.ops.render.render(write_still=True)
    backend = ""
    try:
        import gpu
        backend = str(gpu.platform.backend_type_get())
    except Exception:                       # no GPU context headless: that is a finding, not a failure
        backend = ""
    print("PPWK " + json.dumps({"ok": True, "engine": sc.render.engine, "gpu_backend": backend,
                                "version": bpy.app.version_string, "seconds": round(time.time() - t0, 2)}), flush=True)


try:
    main()
except Exception as exc:
    print("PPWK " + json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}), flush=True)
    sys.exit(1)
