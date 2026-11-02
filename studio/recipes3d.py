"""3D recipes: one model from the 3D page as one step of a recipe, with a turntable so a card can show what it made. A `model3d` step runs what /api/3d/run runs and adds a clip: a mesh gets a Blender turntable, a motion gets a stick figure drawn from its BVH."""
import json, re, shutil, struct, subprocess, tempfile
from pathlib import Path
import numpy as np
from fastapi import APIRouter
from PIL import Image, ImageDraw
from psn import paths
from studio import model3d as M, recipes as R

router = APIRouter()  # the steps join the recipe engine; the runs go through /api/recipes
TURN_FRAMES, TURN_FPS, TURN_SIZE, TURN_SAMPLES = 72, 24, 512, 16

def _out_file(path, kind):
    """A file in the studio's output folder, as a step's result."""
    path = Path(path); rel = path.relative_to(paths.output_dir(True))
    return {"filename": path.name, "subfolder": str(rel.parent) if str(rel.parent) != "." else "", "type": "output", "kind": kind, "local": str(path), "url": f"/api/view?filename={path.name}&subfolder={rel.parent}&type=output"}

def glb_facts(path):
    """Counts read from a GLB's own JSON chunk: nothing here trusts a model's claim of a skeleton."""
    with open(path, "rb") as f:
        head = f.read(12)
        if head[:4] != b"glTF": return {}
        n, kind = struct.unpack("<II", f.read(8))
        if kind != 0x4E4F534A: return {}
        d = json.loads(f.read(n))
    skins = d.get("skins") or []
    return {"meshes": len(d.get("meshes") or []), "skins": len(skins), "bones": max((len(s.get("joints") or []) for s in skins), default=0), "animations": len(d.get("animations") or []), "textures": len(d.get("textures") or [])}

def turntable(glb, out_mp4, work):
    """A Blender turntable of one mesh, on the CPU, without touching the mesh."""
    from studio.worldkit import blender as B, looks, media
    frames = Path(work) / "frames"; frames.mkdir(parents=True, exist_ok=True)
    B.render("wk_turntable.py", {"model": str(glb), "look": looks.resolve("day_clear"), "frames": TURN_FRAMES, "size": TURN_SIZE, "out_dir": str(frames), "interior": False, "fit": False, "elevation": 0.35, "kit": "", "samples": TURN_SAMPLES}, work=Path(work), name="turntable", timeout=3600)
    if not list(frames.glob("*.png")): raise R.StepError("Blender wrote no turntable frames")
    shutil.copy2(media.encode(frames, TURN_FPS, Path(work) / "preview.mp4"), out_mp4)

# ---------- a BVH as a stick figure
def parse_bvh(text):
    """-> (names, parents, offsets, channels per joint, frames array, frame time)."""
    names, parents, offsets, chans = [], [], [], []; stack = []; toks = text.split(); i = 0
    while toks[i] != "MOTION":
        t = toks[i]
        if t in ("ROOT", "JOINT"): names.append(toks[i + 1]); parents.append(stack[-1] if stack else -1); offsets.append(None); chans.append([]); stack.append(len(names) - 1); i += 2
        elif t == "End": names.append(names[stack[-1]] + "_end"); parents.append(stack[-1]); offsets.append(None); chans.append([]); stack.append(len(names) - 1); i += 2
        elif t == "OFFSET": offsets[stack[-1]] = [float(x) for x in toks[i + 1:i + 4]]; i += 4
        elif t == "CHANNELS": n = int(toks[i + 1]); chans[stack[-1]] = toks[i + 2:i + 2 + n]; i += 2 + n
        elif t == "}": stack.pop(); i += 1
        else: i += 1
    n = int(toks[i + 2]); ft = float(toks[i + 5]); data = np.array(toks[i + 6:], dtype=float).reshape(n, -1)
    return names, parents, np.array(offsets), chans, data, ft

def _rot(axis, deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    return {"X": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]), "Y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]), "Z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]

def bvh_positions(names, parents, offsets, chans, data):
    """World position of every joint in every frame: frames x joints x 3."""
    out = np.zeros((len(data), len(names), 3))
    for f, row in enumerate(data):
        k = 0; R_ = [None] * len(names)
        for j in range(len(names)):
            local = np.eye(3); pos = offsets[j].copy()
            for c in chans[j]:
                v = row[k]; k += 1
                if c.endswith("position"): pos["XYZ".index(c[0])] = v
                else: local = local @ _rot(c[0], v)
            if parents[j] < 0: R_[j] = local; out[f, j] = pos
            else: R_[j] = R_[parents[j]] @ local; out[f, j] = out[f, parents[j]] + R_[parents[j]] @ pos
    return out

def bvh_preview(bvh, out_mp4, *, size=512, fps=24):
    """A plain stick figure from the BVH's own numbers, seen from the front and a little to the side. It shows the motion file as it is, with no mesh and no retargeting."""
    names, parents, offsets, chans, data, ft = parse_bvh(Path(bvh).read_text()); P = bvh_positions(names, parents, offsets, chans, data)
    step = max(1, round(1 / (ft * fps))); P = P[::step]; up = int(np.argmax(np.ptp(P[0], axis=0))); side = [a for a in range(3) if a != up]
    a = np.radians(30); X = P[..., side[0]] * np.cos(a) + P[..., side[1]] * np.sin(a); Y = P[..., up]
    lo, hi = np.array([X.min(), Y.min()]), np.array([X.max(), Y.max()]); span = float(max(hi - lo)) * 1.15 or 1.0; mid = (lo + hi) / 2
    with tempfile.TemporaryDirectory() as d:
        for f in range(len(P)):
            im = Image.new("RGB", (size, size), (20, 22, 24)); dr = ImageDraw.Draw(im); pt = lambda j: ((X[f, j] - mid[0]) / span * size + size / 2, size / 2 - (Y[f, j] - mid[1]) / span * size)
            ground = size / 2 - (Y.min() - mid[1]) / span * size; dr.line([(0, ground), (size, ground)], fill=(70, 74, 78), width=2)
            for j, p in enumerate(parents):
                if p >= 0: dr.line([pt(p), pt(j)], fill=(245, 200, 60), width=4)
            im.save(f"{d}/{f:05d}.png")
        subprocess.run(["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-framerate", str(fps), "-i", f"{d}/%05d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_mp4)], check=True)
    return {"joints": len([n for n in names if not n.endswith("_end")]), "frames": len(data)}

# ---------- the step
def _run_model3d(run, st, spec, ctx):
    m = M.model(spec["model"]); body = {"seed": int(spec.get("seed") or 42) + ctx["seed_add"], "seconds": spec.get("seconds") or 5}; st["seed"] = body["seed"]
    if spec.get("prompt"): body["prompt"] = R._fill(spec["prompt"], ctx["values"])
    if spec.get("image"): body["image"] = R._input_name(run, ctx, spec["image"], "image")
    if spec.get("mesh"):
        f = R._pick(ctx, spec["mesh"], "mesh"); body["mesh"] = str(Path(f.get("subfolder") or "") / f["filename"])
    work = R._root() / run["run"] / f"work_{st['id']}"; work.mkdir(parents=True, exist_ok=True)
    try: out = Path(M.execute(m, body, work))
    except (RuntimeError, ValueError) as e: raise R.StepError(f"{m['label']}: {str(e)[:400]}") from None
    if not out.is_file() or out.stat().st_size < 1024: raise R.StepError(f"{m['label']} left no real file")
    clip = out.with_suffix(".mp4"); files = []; suffix = out.suffix.lower()
    if suffix == ".bvh": st["facts"] = bvh_preview(out, clip); kind = "motion"
    elif suffix == ".glb": st["facts"] = glb_facts(out); kind = "mesh"; turntable(out, clip, work) if not clip.is_file() else None
    else: kind = "splat"
    if clip.is_file(): files.append(_out_file(clip, "video"))
    files.append(_out_file(out, kind)); return files
R.EXTRA_STEPS.update(model3d=_run_model3d)
