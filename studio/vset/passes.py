"""The scene step. Blender (vs_scene.py) renders the shot's shaded frames (the look's lighting), a depth pass (near = white, through a material override: no compositor) and a flat-colour id pass, and dumps any cast's humanoid
bones per frame. Here the edges are drawn from depth and id discontinuities, and the OpenPose skeletons from the bones, projected with the same camera maths the render used (camera.project), then every pass is encoded and its
frames counted. The passes stay with the shot, so it can go through a different model later. Outputs: depth, pose, edges, shaded (videos); first, last (stills); clay (a video, only for a shot on LTX-2.5 Layout to Render). With no cast the pose pass is black frames."""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from studio.vset import camera
from studio.worldkit import media

PASSES = ("depth", "pose", "edges", "shaded")
STILLS = ("first", "last")
NEAR_M = 0.3
FAR_MAX_M = 80.0
SAMPLES = 16
RENDER_TIMEOUT_S = 6 * 3600
#: OpenPose BODY_18 (COCO order): 0 nose, 1 neck, 2-4 right arm, 5-7 left arm, 8-10 right leg, 11-13 left leg, 14/15 right/left eye, 16/17 right/left ear; the limbs and colours of the reference renderer the control models trained on.
OPENPOSE_LIMBS = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13), (1, 0), (0, 14), (14, 16), (0, 15), (15, 17)]
OPENPOSE_COLOURS = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0), (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255), (0, 0, 255),
                    (85, 0, 255), (170, 0, 255), (255, 0, 255), (255, 0, 170), (255, 0, 85)]
_BODY = ["neck", "r_upperarm", "r_forearm", "r_hand", "l_upperarm", "l_forearm", "l_hand", "r_thigh", "r_shin", "r_foot", "l_thigh", "l_shin", "l_foot"]


def depth_range(keys, lo, hi) -> tuple[float, float]:
    corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    far = max(math.dist(k["pos"], c) for k in keys for c in corners)
    return NEAR_M, min(FAR_MAX_M, max(far, NEAR_M + 1.0))


def _v(a, b, k=1.0):
    return tuple(x + y * k for x, y in zip(a, b))


def keypoints3d(person: dict) -> list:
    """The 18 OpenPose points in world space. Body points are the rig's joints; the face (nose, eyes, ears) is placed on the head from the neck->head direction and the facing, with fixed adult proportions in metres."""
    s, fwd = person["slots"], tuple(person["forward"])

    def head(n):
        return tuple(s[n][0]) if n in s else None

    body = [head(n) for n in _BODY]
    face = [None] * 5
    if "head" in s and "neck" in s:
        up = _v(s["head"][0], s["neck"][0], -1.0)
        n = math.sqrt(sum(x * x for x in up)) or 1.0
        up = tuple(x / n for x in up)
        left = (up[1] * fwd[2] - up[2] * fwd[1], up[2] * fwd[0] - up[0] * fwd[2], up[0] * fwd[1] - up[1] * fwd[0])
        centre = _v(head("head"), up, 0.10)
        eyes = _v(_v(centre, up, 0.03), fwd, 0.075)
        face = [_v(centre, fwd, 0.09), _v(eyes, left, -0.032), _v(eyes, left, 0.032), _v(centre, left, -0.075), _v(centre, left, 0.075)]
    return [face[0], *body, *face[1:]]


def project_people(frame: dict, key: dict, size) -> list[list]:
    w, h = size
    out = []
    for person in frame.get("cast") or []:
        if not person:
            continue
        pts = []
        for p in keypoints3d(person):
            q = camera.project(p, key, size) if p is not None else None
            pts.append((q[0], q[1]) if q is not None and 0 <= q[0] < w and 0 <= q[1] < h else None)
        out.append(pts)
    return out


def draw_pose(people: list, size) -> Image.Image:
    img = Image.new("RGB", tuple(size), (0, 0, 0))
    d = ImageDraw.Draw(img)
    stick, rad = max(2, round(min(size) / 160)), max(2, round(min(size) / 120))
    for kps in people:
        for i, (a, b) in enumerate(OPENPOSE_LIMBS):
            if kps[a] and kps[b]:
                d.line([kps[a], kps[b]], fill=tuple(int(c * 0.6) for c in OPENPOSE_COLOURS[i]), width=stick)
        for k, p in enumerate(kps):
            if p:
                d.ellipse([p[0] - rad, p[1] - rad, p[0] + rad, p[1] + rad], fill=OPENPOSE_COLOURS[k])
    return img


def edges_from(depth: np.ndarray, ids: np.ndarray, step: int = 8) -> np.ndarray:
    d = depth.astype(np.int16)
    e = (np.abs(np.diff(d, axis=1, prepend=d[:, :1])) > step) | (np.abs(np.diff(d, axis=0, prepend=d[:1, :])) > step)
    k = (ids[..., 0].astype(np.int32) << 16) | (ids[..., 1].astype(np.int32) << 8) | ids[..., 2].astype(np.int32)
    e |= (np.diff(k, axis=1, prepend=k[:, :1]) != 0) | (np.diff(k, axis=0, prepend=k[:1, :]) != 0)
    return (e * 255).astype(np.uint8)


def scene_payload(shot: dict, *, library, frames: int | None = None, size=None, samples: int = SAMPLES) -> dict:
    from studio.vset import shot as SH
    n = int(frames or SH.frames(shot))
    w, h = size or SH.size(shot)
    place = library.require(shot["set"]["place"])
    cast = []
    for i, c in enumerate(shot.get("cast") or []):
        meta = library.require(c["asset"])
        path = camera.along(c["marks"], n)
        heads = camera.headings(path)
        clip = next((x for x in meta.get("clips") or [] if x.get("name") == c["clip"]), {})
        cast.append({"path": str(library.path(c["asset"], "asset.glb")), "clip": c["clip"], "repeat": max(1, math.ceil(n / max(1, int(clip.get("frames") or 1)))),
                     "positions": [[round(x, 5), round(y, 5)] for x, y in path], "yaw_deg": [round(math.degrees(math.atan2(hx, -hy)), 4) + 0.0 for hx, hy in heads],
                     "slots": dict((meta.get("rig") or {}).get("slots") or {}), "hidden": shot["camera"]["preset"] == "pov" and i == 0})
    keys = camera.keys(shot["camera"], SH.subject_marks(shot), n, seed=shot["seed"])
    ins = place.get("inspect") or {}
    near, far = depth_range(keys, ins.get("lo") or [-10, -10, 0], ins.get("hi") or [10, 10, 5])
    return {"size": [int(w), int(h)], "frames": n, "fps": SH.fps(shot), "place": str(library.path(place["id"], "asset.glb")),
            "props": [{"path": str(library.path(p["asset"], "asset.glb")), "pos": p["pos"], "rot_deg": p.get("rot_deg", [0, 0, 0]), "scale": p.get("scale", 1.0)} for p in shot["set"].get("props") or []],
            "cast": cast, "camera": keys, "look": SH.look_of(shot, library), "depth_range": [near, far], "samples": int(samples), "clay": SH.is_ltx(shot)}


def render_scene(shot: dict, *, library, work, blender=None, frames=None, size=None, samples: int = SAMPLES, encode=None):
    """-> ({pass or still: path}, Blender's result). Without a stand-in encoder, each encoded pass has its frames counted: a short pass would fail later inside a model with a worse message."""
    from studio.worldkit import blender as B
    bl, enc = blender or B, encode or media.encode
    work = Path(work)
    fd = work / "frames"
    payload = scene_payload(shot, library=library, frames=frames, size=size, samples=samples)
    res = bl.render("vs_scene.py", {**payload, "out_dir": str(fd)}, work=work, name="scene", timeout=RENDER_TIMEOUT_S)
    n, sz = payload["frames"], tuple(payload["size"])
    shaded, depth, ids = (sorted((fd / k).glob("*.png")) for k in ("shaded", "depth", "ids"))
    if not len(shaded) == len(depth) == len(ids) == n:
        raise RuntimeError(f"Blender wrote {len(shaded)}/{len(depth)}/{len(ids)} of {n} frames")
    (fd / "edges").mkdir(parents=True, exist_ok=True)
    (fd / "pose").mkdir(parents=True, exist_ok=True)
    for i, (dp, ip) in enumerate(zip(depth, ids), 1):
        with Image.open(dp) as a, Image.open(ip) as b:
            e = edges_from(np.asarray(a.convert("L")), np.asarray(b.convert("RGB")))
        Image.fromarray(e).save(fd / "edges" / f"{i:04d}.png")
    pose3d = json.loads((fd / "pose3d.json").read_text())
    for i, (fr, key) in enumerate(zip(pose3d["frames"], payload["camera"]), 1):
        draw_pose(project_people(fr, key, sz), sz).save(fd / "pose" / f"{i:04d}.png")
    made = (*PASSES, "clay") if payload["clay"] else PASSES
    files = {k: enc(fd / k, payload["fps"], work / f"{k}.mp4") for k in made}
    if encode is None:
        for k in made:
            got = media.frame_count(files[k])
            if got != n:
                raise RuntimeError(f"the {k} pass came out with {got} frames, not {n}")
    for name, src in (("first", shaded[0]), ("last", shaded[-1])):
        files[name] = work / f"{name}.png"
        shutil.copy(src, files[name])
    (work / "camera.json").write_text(json.dumps(payload["camera"]))
    return files, res


def scene_step_outputs(shot: dict, ctx: dict) -> dict:
    """The scene step's outputs. The passes live with the shot, so they outlast the build's scratch."""
    from studio.vset import shot as SH
    files, res = render_scene(shot, library=ctx["library"], work=SH.shot_dir(shot["id"], ctx.get("root")) / "passes", blender=ctx.get("blender"))
    out = {k: {"path": str(p)} for k, p in files.items()}
    out["shaded"]["engine"] = res.get("engine", "")
    if res.get("fallback_note"):
        out["shaded"]["note"] = res["fallback_note"]
    return out
