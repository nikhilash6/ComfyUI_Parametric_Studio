"""A drawn camera path for Wan 2.2 Fun Camera. Original code, AGPL-3.0-or-later.
ComfyUI's own WanCameraEmbedding only knows nine presets (pan, zoom, roll). This node takes the keyframes a person drew on the Camera Paths page,
builds one camera-to-world pose per frame from them, and hands the poses to ComfyUI core's own Plücker-ray step (comfy_extras.nodes_camera_trajectory),
so the result is the same WAN_CAMERA_EMBEDDING tensor that WanCameraImageToVideo already takes.

Path JSON: {"keys": [{"t": 0..1, "pos": [x, y, z]}, ...], "look_at": [x, y, z] or null, "yaw"/"pitch"/"roll" per key in degrees when look_at is null}.
Axes are the camera's own at frame 0 (OpenCV: x right, y down, z forward). One unit is two thirds of the distance ComfyUI's presets travel at speed 1."""
import json, math
import numpy as np

CAT = "ParametricStudio/Camera"
MAX_KEYS = 64


def parse_path(text):
    """-> (keys sorted by t, look_at or None). Raises ValueError with a plain reason."""
    try: d = json.loads(text) if isinstance(text, str) else text
    except ValueError: raise ValueError("the camera path is not JSON") from None
    if isinstance(d, list): d = {"keys": d}
    if not isinstance(d, dict) or not isinstance(d.get("keys"), list): raise ValueError("the camera path needs a list of keys")
    keys = []
    for k in d["keys"][:MAX_KEYS]:
        if not isinstance(k, dict): raise ValueError("each key is an object")
        pos = k.get("pos")
        if not (isinstance(pos, (list, tuple)) and len(pos) == 3 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in pos)): raise ValueError("each key needs pos: [x, y, z]")
        if any(abs(v) > 20 for v in pos): raise ValueError("a key is more than 20 units away: draw a smaller path")
        t = float(k.get("t", len(keys)))
        keys.append({"t": t, "pos": [float(v) for v in pos], "yaw": float(k.get("yaw", 0)), "pitch": float(k.get("pitch", 0)), "roll": float(k.get("roll", 0))})
    if len(keys) < 2: raise ValueError("a camera path needs at least two keys")
    keys.sort(key=lambda k: k["t"]); t0, t1 = keys[0]["t"], keys[-1]["t"]
    if t1 <= t0: raise ValueError("the keys need different times")
    for k in keys: k["t"] = (k["t"] - t0) / (t1 - t0)
    look = d.get("look_at")
    if look is not None and not (isinstance(look, (list, tuple)) and len(look) == 3 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in look)): raise ValueError("look_at is [x, y, z] or null")
    return keys, ([float(v) for v in look] if look is not None else None)


def _catmull(p0, p1, p2, p3, u):
    """Centripetal-free uniform Catmull-Rom between p1 and p2: passes through every key, no overshoot for evenly spaced keys."""
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)


def sample(keys, n):
    """n frames along the path -> (positions [n,3], angles [n,3] in degrees as yaw, pitch, roll)."""
    ts = np.array([k["t"] for k in keys]); P = np.array([k["pos"] for k in keys]); A = np.array([[k["yaw"], k["pitch"], k["roll"]] for k in keys])
    pos, ang = np.zeros((n, 3)), np.zeros((n, 3))
    for i in range(n):
        t = i / max(1, n - 1); j = int(np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(keys) - 2))
        u = 0.0 if ts[j + 1] == ts[j] else (t - ts[j]) / (ts[j + 1] - ts[j])
        pos[i] = _catmull(P[max(j - 1, 0)], P[j], P[j + 1], P[min(j + 2, len(keys) - 1)], u)
        ang[i] = A[j] + (A[j + 1] - A[j]) * u
    return pos, ang


def rot(yaw, pitch, roll):
    """Degrees -> 3x3, in ComfyUI's preset order R = Rz(roll) Ry(yaw) Rx(pitch). Positive yaw turns the camera to its right."""
    y, p, r = (math.radians(v) for v in (yaw, pitch, roll))
    Rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def look_rot(pos, target):
    """The camera at pos looking at target, horizon level (world y is down)."""
    f = np.asarray(target, float) - np.asarray(pos, float); nf = np.linalg.norm(f)
    if nf < 1e-6: raise ValueError("a key sits on the look-at point")
    f /= nf; x = np.cross([0.0, 1.0, 0.0], f); nx = np.linalg.norm(x)
    if nx < 1e-6: raise ValueError("the camera looks straight up or down at the look-at point; tilt the path a little")
    x /= nx; y = np.cross(f, x)
    return np.stack([x, y, f], axis=1)


def poses(path_text, n):
    """-> [n, 4, 4] camera-to-world matrices, frame 0 at the origin looking down +z (the path is re-based so it starts there)."""
    keys, look = parse_path(path_text); pos, ang = sample(keys, n)
    mats = np.zeros((n, 4, 4)); mats[:, 3, 3] = 1
    for i in range(n):
        mats[i, :3, :3] = look_rot(pos[i], look) if look is not None else rot(*ang[i]); mats[i, :3, 3] = pos[i]
    base = np.linalg.inv(mats[0])
    return np.einsum("ij,njk->nik", base, mats)


def screen_motion(mats, depth=4.0):
    """What a point straight ahead at depth does on screen over the path, in units of the half-frame (for the page's preview and the verifier's expectation).
    -> {dx, dy, scale}: dx > 0 means the scene slides right, dy > 0 slides down, scale > 1 grows."""
    p = np.array([0.0, 0.0, depth, 1.0]); last = np.linalg.inv(mats[-1]) @ p
    if last[2] <= 1e-3: return {"dx": 0.0, "dy": 0.0, "scale": 1.0, "behind": True}
    return {"dx": round(float(last[0] / last[2]), 4), "dy": round(float(last[1] / last[2]), 4), "scale": round(float(depth / last[2]), 4), "behind": False}


def wan_embedding(mats, width, height, fx=0.5, fy=0.5, cx=0.5, cy=0.5):
    """Poses -> the WAN_CAMERA_EMBEDDING tensor, through ComfyUI core's own Plücker step and the same frame packing as WanCameraEmbedding."""
    import torch
    import comfy.model_management
    from comfy_extras.nodes_camera_trajectory import process_pose_params
    rows = [[0.0, fx, fy, cx, cy, 0.0, 0.0] + [float(v) for v in m.reshape(-1)] for m in mats]
    v = process_pose_params(np.array(rows), width=width, height=height)
    v = v.permute([3, 0, 1, 2]).unsqueeze(0).to(device=comfy.model_management.intermediate_device())
    v = torch.concat([torch.repeat_interleave(v[:, :, 0:1], repeats=4, dim=2), v[:, :, 1:]], dim=2).transpose(1, 2)
    b, f, c, h, w = v.shape
    v = v.contiguous().view(b, f // 4, 4, c, h, w).transpose(2, 3)
    return v.contiguous().view(b, f // 4, c * 4, h, w).transpose(1, 2)


class PSN_CameraPathEmbedding:
    """A drawn camera path (keyframes from the Camera Paths page) as Wan 2.2 Fun Camera conditioning. Plugs into WanCameraImageToVideo where WanCameraEmbedding would go."""
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"path": ("STRING", {"multiline": True, "default": '{"keys": [{"t": 0, "pos": [0, 0, 0]}, {"t": 1, "pos": [0, 0, 1]}], "look_at": null}'}),
                             "width": ("INT", {"default": 832, "min": 16, "max": 4096, "step": 16}), "height": ("INT", {"default": 480, "min": 16, "max": 4096, "step": 16}),
                             "length": ("INT", {"default": 81, "min": 5, "max": 1024, "step": 4})},
                "optional": {"fx": ("FLOAT", {"default": 0.5, "min": 0.05, "max": 2.0, "step": 0.01}), "fy": ("FLOAT", {"default": 0.5, "min": 0.05, "max": 2.0, "step": 0.01})}}
    RETURN_TYPES = ("WAN_CAMERA_EMBEDDING", "INT", "INT", "INT"); RETURN_NAMES = ("camera_embedding", "width", "height", "length"); FUNCTION = "run"; CATEGORY = CAT

    def run(self, path, width, height, length, fx=0.5, fy=0.5):
        if (length - 1) % 4: raise ValueError("length must be 4k+1 (81, 85, ...) for Wan")
        return (wan_embedding(poses(path, length), width, height, fx, fy), width, height, length)


NODE_CLASS_MAPPINGS = {"PSN_CameraPathEmbedding": PSN_CameraPathEmbedding}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_CameraPathEmbedding": "Camera Path (Wan Fun Camera)"}
