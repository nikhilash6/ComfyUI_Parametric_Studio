"""
PSN Deterministic Camera Motion.

The curve nodes use only the Python standard library.  PSN_Camera_Apply also
uses torch (CPU is enough) to resample an image.  Nothing here does file,
network or OS access.

What it does:
  * PSN_Camera_Path_Definer: parses a JSON keyframe string, validates it, and
    builds a deterministic, multi-dimensional (x, y, z, rot) keyframed curve
    with linear / cubic (Catmull-Rom) / step interpolation. It also emits a
    small ASCII text plot of the path (a string, not an image).
  * PSN_Camera_Apply: evaluates the curve at a frame index, computes the
    affine transform (pan x/y in pixels, zoom, rotation) and applies it to the
    given IMAGE with torch affine_grid + grid_sample (bilinear, zero fill
    outside the source). It also returns the numeric parameters.

The "KEYFRAMED_CURVE" output is a plain dict (JSON-serializable) so it can be
passed between nodes without any external dependency.
"""

import json
import math

import torch
import torch.nn.functional as F

CAT = "ParametricStudio/Camera"

_INTERP_MODES = ["linear", "cubic", "step"]
_DIMS = ["x", "y", "z", "rot"]


def _clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _parse_keyframes(text):
    """Parse a JSON keyframe string into a validated, sorted list of dicts.

    Each keyframe must be a mapping with integer 'frame' and numeric
    x, y, z, rot. Returns (keyframes, error).
    """
    if not isinstance(text, str):
        return None, "keyframes must be a JSON string"
    try:
        data = json.loads(text)
    except Exception as exc:
        return None, "invalid JSON: %s" % exc

    if not isinstance(data, list):
        return None, "keyframes must be a JSON array of objects"
    if len(data) == 0:
        return None, "keyframes must contain at least one entry"

    parsed = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            return None, "keyframe %d must be an object" % i
        if "frame" not in item:
            return None, "keyframe %d missing 'frame'" % i
        frame = item["frame"]
        if isinstance(frame, bool) or not isinstance(frame, int):
            return None, "keyframe %d 'frame' must be an integer" % i
        if frame < 0:
            return None, "keyframe %d 'frame' must be >= 0" % i
        entry = {"frame": frame}
        for dim in _DIMS:
            val = item.get(dim, 0)
            if not _is_number(val):
                return None, "keyframe %d '%s' must be a number" % (i, dim)
            if math.isnan(val) or math.isinf(val):
                return None, "keyframe %d '%s' must be finite" % (i, dim)
            entry[dim] = float(val)
        parsed.append(entry)

    # Sort by frame; reject duplicate frames.
    parsed.sort(key=lambda e: e["frame"])
    for i in range(1, len(parsed)):
        if parsed[i]["frame"] == parsed[i - 1]["frame"]:
            return None, "duplicate frame %d" % parsed[i]["frame"]
    return parsed, None


def _catmull_rom(p0, p1, p2, p3, t):
    """Catmull-Rom interpolation between p1 and p2 given neighbours p0, p3."""
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2.0 * p1)
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def _interp_dim(values, frames, frame, mode):
    """Interpolate a single dimension at an absolute frame index."""
    n = len(frames)
    if frame <= frames[0]:
        return values[0]
    if frame >= frames[-1]:
        return values[-1]

    # Find the segment [i, i+1] such that frames[i] <= frame < frames[i+1].
    i = 0
    for idx in range(n - 1):
        if frames[idx] <= frame < frames[idx + 1]:
            i = idx
            break

    f0 = frames[i]
    f1 = frames[i + 1]
    span = f1 - f0
    if span == 0:
        return values[i]
    t = (frame - f0) / span

    if mode == "step":
        return values[i]
    if mode == "linear":
        return values[i] + (values[i + 1] - values[i]) * t
    # cubic (Catmull-Rom)
    p0 = values[i - 1] if i - 1 >= 0 else values[i]
    p1 = values[i]
    p2 = values[i + 1]
    p3 = values[i + 2] if i + 2 < n else values[i + 1]
    return _catmull_rom(p0, p1, p2, p3, t)


def _build_curve(keyframes, interpolation, duration_frames):
    """Build the KEYFRAMED_CURVE dict (JSON-serializable)."""
    frames = [kf["frame"] for kf in keyframes]
    dims = {d: [kf[d] for kf in keyframes] for d in _DIMS}
    return {
        "type": "KEYFRAMED_CURVE",
        "interpolation": interpolation,
        "duration_frames": int(duration_frames),
        "frames": frames,
        "dims": dims,
    }


def _evaluate_curve(curve, frame_index):
    """Evaluate the curve at a frame index -> dict of x, y, z, rot."""
    frames = curve["frames"]
    dims = curve["dims"]
    mode = curve["interpolation"]
    out = {}
    for d in _DIMS:
        out[d] = _interp_dim(dims[d], frames, frame_index, mode)
    return out


def _ascii_preview(curve, width=40, height=12):
    """Render a small ASCII plot of the x/y path over the duration."""
    duration = max(1, int(curve["duration_frames"]))
    frames = curve["frames"]
    dims = curve["dims"]
    xs = [_interp_dim(dims["x"], frames, f, curve["interpolation"]) for f in range(duration)]
    ys = [_interp_dim(dims["y"], frames, f, curve["interpolation"]) for f in range(duration)]
    if not xs:
        return "(empty)"
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xr = (xmax - xmin) or 1.0
    yr = (ymax - ymin) or 1.0
    grid = [[" "] * width for _ in range(height)]
    for f, (x, y) in enumerate(zip(xs, ys)):
        col = int(round((x - xmin) / xr * (width - 1)))
        row = int(round((1.0 - (y - ymin) / yr) * (height - 1)))
        row = _clamp(row, 0, height - 1)
        col = _clamp(col, 0, width - 1)
        grid[row][col] = "*"
    return "\n".join("".join(r) for r in grid)


class PSN_Camera_Path_Definer:
    """Parse keyframed camera data and build a deterministic KEYFRAMED_CURVE."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "keyframes": ("STRING", {"default": "[{\"frame\":0,\"x\":0,\"y\":0,\"z\":0,\"rot\":0}]"}),
                "interpolation": (_INTERP_MODES,),
                "duration_frames": ("INT", {"default": 100, "min": 1, "max": 100000, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("KEYFRAMED_CURVE", "STRING")
    RETURN_NAMES = ("camera_curve", "preview_image")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, keyframes, interpolation, duration_frames):
        parsed, err = _parse_keyframes(keyframes)
        if err is not None:
            # Return an empty/invalid curve plus the error as the preview text.
            empty = {
                "type": "KEYFRAMED_CURVE",
                "interpolation": interpolation,
                "duration_frames": int(duration_frames),
                "frames": [],
                "dims": {d: [] for d in _DIMS},
                "error": err,
            }
            return (empty, "ERROR: " + err)
        curve = _build_curve(parsed, interpolation, duration_frames)
        preview = _ascii_preview(curve)
        return (curve, preview)


def _affine_theta(width, height, pan_x, pan_y, zoom, rotation_deg):
    """Build the 2x3 affine_grid theta for a camera move.

    Content is scaled by zoom (>1 zooms in), turned clockwise on screen by
    rotation_deg about the image centre, then shifted by (pan_x, pan_y)
    pixels (+x right, +y down).  affine_grid wants the inverse map from output
    to input in normalised coordinates; the maths is done in pixel space so
    non-square images do not shear.
    """
    a = math.radians(rotation_deg)
    c, s = math.cos(a), math.sin(a)
    # inverse content rotation (y-down screen coordinates)
    inv = [[c, s], [-s, c]]
    sx, sy = width / 2.0, height / 2.0
    A = [[inv[0][0] / zoom, inv[0][1] / zoom * sy / sx],
         [inv[1][0] / zoom * sx / sy, inv[1][1] / zoom]]
    # b = -S^-1 * inv * t / zoom
    tx = inv[0][0] * pan_x + inv[0][1] * pan_y
    ty = inv[1][0] * pan_x + inv[1][1] * pan_y
    b = [-tx / zoom / sx, -ty / zoom / sy]
    return torch.tensor([[A[0][0], A[0][1], b[0]], [A[1][0], A[1][1], b[1]]], dtype=torch.float32)


def _apply_camera(image, pan_x, pan_y, zoom, rotation_deg):
    """Resample an IMAGE tensor [B,H,W,C] with the camera transform."""
    if not isinstance(image, torch.Tensor) or image.dim() != 4:
        raise ValueError("base_image must be an IMAGE tensor [B,H,W,C]")
    b, h, w, _ = image.shape
    theta = _affine_theta(w, h, pan_x, pan_y, zoom, rotation_deg).to(image.device, image.dtype)
    theta = theta.unsqueeze(0).expand(b, 2, 3)
    chw = image.permute(0, 3, 1, 2)
    grid = F.affine_grid(theta, list(chw.shape), align_corners=False)
    out = F.grid_sample(chw, grid, mode="bilinear", padding_mode="zeros", align_corners=False)
    return out.permute(0, 2, 3, 1).contiguous()


class PSN_Camera_Apply:
    """Evaluate a KEYFRAMED_CURVE at a frame and apply the camera move to an image."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "camera_curve": ("KEYFRAMED_CURVE",),
                "frame_index": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "base_image": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "FLOAT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("transformed_image", "pan_x", "pan_y", "zoom", "rotation_deg")
    FUNCTION = "run"
    CATEGORY = CAT
    DESCRIPTION = ("Evaluates the camera curve at a frame and resamples the image with it: "
                   "x/y pan in pixels, z as zoom factor (1.0 = none, must be above 0), rot as "
                   "degrees clockwise. Bilinear; areas outside the source are black.")

    def run(self, camera_curve, frame_index, base_image):
        if not isinstance(camera_curve, dict) or camera_curve.get("type") != "KEYFRAMED_CURVE":
            raise ValueError("invalid camera_curve")
        if not camera_curve.get("frames"):
            raise ValueError("empty camera_curve")
        state = _evaluate_curve(camera_curve, int(frame_index))
        # z is treated as a zoom factor (1.0 == no zoom); 0 means "unset".
        zoom = state["z"] if state["z"] != 0.0 else 1.0
        if zoom < 0.0:
            raise ValueError("zoom (z) must be above 0, got %r" % zoom)
        image = _apply_camera(base_image, state["x"], state["y"], zoom, state["rot"])
        return (image, state["x"], state["y"], zoom, state["rot"])


NODE_CLASS_MAPPINGS = {
    "PSN_Camera_Path_Definer": PSN_Camera_Path_Definer,
    "PSN_Camera_Apply": PSN_Camera_Apply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Camera_Path_Definer": "PSN Camera Path Definer",
    "PSN_Camera_Apply": "PSN Camera Apply",
}
