"""Camera presets -> per-frame camera keys. Pure maths in Blender coordinates (metres, Z up). A key is {"pos": [x, y, z], "look": [x, y, z], "lens_mm", "roll_deg"}; Blender (vs_scene.py),
the pose projection (passes.py) and the page's plan view all read the same keys. The camera follows a subject that walks a path of marks at constant speed: the first cast member, or with no cast an empty
point in the set (shot.subject_marks). A standing subject faces -Y, a walking one faces where it walks. "In front" is along that facing direction (the camera looks back at it)."""
from __future__ import annotations

import math
import random

CHEST_M = 1.3
LENS_MM = 35.0                 # full-frame equivalent
SENSOR_MM = 36.0
LENS_RANGE = (10.0, 200.0)
EASINGS = ("linear", "ease_in", "ease_out", "ease_in_out")
PRESETS = ("push_in", "orbit", "walk_along", "pov", "handheld", "static", "custom")
DEFAULTS: dict[str, dict] = {
    "push_in": {"from_m": 4.0, "to_m": 1.8, "height_m": 1.5, "angle_deg": 0.0, "easing": "ease_in_out"},
    "orbit": {"radius_m": 2.6, "start_deg": -45.0, "sweep_deg": 90.0, "height_m": 1.5, "easing": "ease_in_out"},
    "walk_along": {"side_m": 2.2, "lead_m": 0.3, "height_m": 1.45},
    "pov": {"eye_m": 1.6, "ahead_m": 6.0},
    "handheld": {"dist_m": 2.6, "height_m": 1.5, "angle_deg": 0.0, "amp_m": 0.02, "amp_deg": 0.6},
    "static": {"dist_m": 3.0, "height_m": 1.5, "angle_deg": 0.0},
    "custom": {"easing": "ease_in_out"},
}


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _mul(a, k):
    return tuple(x * k for x in a)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(v):
    n = math.sqrt(_dot(v, v))
    return tuple(x / n for x in v) if n > 1e-12 else tuple(v)


def _rot2(v, deg):
    a = math.radians(deg)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def _lerp(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def ease(name: str, t: float) -> float:
    t = min(1.0, max(0.0, float(t)))
    if name == "linear":
        return t
    if name == "ease_in":
        return t * t
    if name == "ease_out":
        return 1 - (1 - t) * (1 - t)
    if name == "ease_in_out":
        return t * t * (3 - 2 * t)
    raise ValueError(f"easing must be one of {', '.join(EASINGS)}")


def along(marks, frames: int) -> list[tuple[float, float]]:
    pts = [(float(x), float(y)) for x, y in marks]
    if frames < 1 or not pts:
        raise ValueError("a path needs at least one mark and one frame")
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    if total == 0 or frames == 1:
        return [pts[0]] * frames
    out = []
    for f in range(frames):
        d, i = total * f / (frames - 1), 0
        while i < len(seg) - 1 and d > seg[i]:
            d -= seg[i]
            i += 1
        k = 0.0 if seg[i] == 0 else min(1.0, d / seg[i])
        out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k))
    return out


def headings(path) -> list[tuple[float, float]]:
    n, raw = len(path), []
    for f in range(n):
        a, b = path[max(0, f - 1)], path[min(n - 1, f + 1)]
        d = (b[0] - a[0], b[1] - a[1])
        ln = math.hypot(*d)
        raw.append((d[0] / ln, d[1] / ln) if ln > 1e-9 else None)
    last = next((h for h in raw if h), (0.0, -1.0))
    out = []
    for h in raw:
        last = h or last
        out.append(last)
    return out


def _vec3(v) -> bool:
    return isinstance(v, list) and len(v) == 3 and all(_num(x) for x in v)


def problems(camera) -> list[str]:
    if not isinstance(camera, dict) or camera.get("preset") not in PRESETS:
        return [f"camera preset must be one of {', '.join(PRESETS)}"]
    preset, bad = camera["preset"], []
    params = camera.get("params") or {}
    if not isinstance(params, dict):
        return ["camera params must be an object"]
    for k, v in params.items():
        if k not in DEFAULTS[preset]:
            bad.append(f"camera {preset} has no setting {k!r}")
        elif k == "easing":
            if v not in EASINGS:
                bad.append(f"easing must be one of {', '.join(EASINGS)}")
        elif not _num(v):
            bad.append(f"camera {k} must be a number")
    lens = camera.get("lens_mm", params.get("lens_mm", LENS_MM))
    lo, hi = LENS_RANGE
    if not _num(lens) or not lo <= lens <= hi:
        bad.append(f"lens_mm is {lo:.0f}-{hi:.0f}")
    if preset == "custom":
        path = camera.get("path")
        if not (isinstance(path, dict) and all(isinstance(path.get(e), dict) and _vec3(path[e].get("pos"))
                                               and _vec3(path[e].get("look")) for e in ("start", "end"))):
            bad.append("a custom camera needs path.start and path.end, each with pos and look [x, y, z]")
        elif path.get("easing", "ease_in_out") not in EASINGS:
            bad.append(f"easing must be one of {', '.join(EASINGS)}")
    return bad


def keys(camera: dict, marks, frames: int, *, seed: int = 0) -> list[dict]:
    bad = problems(camera)
    if bad:
        raise ValueError("; ".join(bad))
    preset = camera["preset"]
    p = {**DEFAULTS[preset], **(camera.get("params") or {})}
    lens = float(camera.get("lens_mm") or p.get("lens_mm") or LENS_MM)
    path = along(marks, frames)
    head = headings(path)
    h0 = head[0]
    rnd = random.Random(int(seed))
    phase = [rnd.uniform(0.0, 2 * math.pi) for _ in range(4)]
    out = []
    for f in range(frames):
        t = f / (frames - 1) if frames > 1 else 0.0
        (sx, sy), (hx, hy) = path[f], head[f]
        chest, roll = (sx, sy, CHEST_M), 0.0
        if preset == "push_in":
            fx, fy = _rot2(h0, p["angle_deg"])
            d = p["from_m"] + (p["to_m"] - p["from_m"]) * ease(p["easing"], t)
            pos, look = (sx + fx * d, sy + fy * d, p["height_m"]), chest
        elif preset == "orbit":
            fx, fy = _rot2(h0, p["start_deg"] + p["sweep_deg"] * ease(p["easing"], t))
            pos, look = (sx + fx * p["radius_m"], sy + fy * p["radius_m"], p["height_m"]), chest
        elif preset == "walk_along":
            lx, ly = -hy, hx                                    # the subject's left
            pos = (sx + lx * p["side_m"] + hx * p["lead_m"], sy + ly * p["side_m"] + hy * p["lead_m"], p["height_m"])
            look = chest
        elif preset == "pov":
            pos = (sx + hx * 0.12, sy + hy * 0.12, p["eye_m"])
            look = (sx + hx * p["ahead_m"], sy + hy * p["ahead_m"], p["eye_m"] - 0.15)
        elif preset in ("static", "handheld"):
            fx, fy = _rot2(h0, p["angle_deg"])
            bx, by = path[0]
            pos = (bx + fx * p["dist_m"], by + fy * p["dist_m"], p["height_m"])
            look = (bx, by, CHEST_M) if preset == "static" else chest
            if preset == "handheld":
                s = f / 24.0

                def w(a, b, ph):
                    return math.sin(2 * math.pi * a * s + ph) * 0.6 + math.sin(2 * math.pi * b * s + ph * 1.7) * 0.4
                pos = (pos[0] + p["amp_m"] * w(0.7, 1.9, phase[0]), pos[1] + p["amp_m"] * w(0.5, 1.3, phase[1]),
                       pos[2] + p["amp_m"] * w(0.9, 2.3, phase[2]))
                roll = p["amp_deg"] * w(0.4, 1.1, phase[3])
        else:                                                   # custom
            cp = camera["path"]
            k = ease(cp.get("easing", p["easing"]), t)
            pos, look = _lerp(cp["start"]["pos"], cp["end"]["pos"], k), _lerp(cp["start"]["look"], cp["end"]["look"], k)
        out.append({"pos": [round(c, 5) for c in pos], "look": [round(c, 5) for c in look], "lens_mm": lens,
                    "roll_deg": round(roll, 4)})
    return out


def basis(key: dict):
    """(position, forward, right, up) of a key, as Blender orients a camera: to_track_quat('-Z', 'Y'), then the roll."""
    pos, look = tuple(key["pos"]), tuple(key["look"])
    f = _unit(_sub(look, pos))
    r = _cross(f, (0.0, 0.0, 1.0))
    r = _unit(r) if _dot(r, r) > 1e-12 else (1.0, 0.0, 0.0)
    u = _cross(r, f)
    a = math.radians(key.get("roll_deg", 0.0))
    if a:
        r, u = _add(_mul(r, math.cos(a)), _mul(u, math.sin(a))), _sub(_mul(u, math.cos(a)), _mul(r, math.sin(a)))
    return pos, f, r, u


def project(point, key: dict, size) -> tuple[float, float, float] | None:
    """Pixel (x, y) and depth of a world point; None behind the camera. Blender's sensor fit AUTO puts the 36 mm sensor
    across the image's longer side."""
    w, h = size
    pos, f, r, u = basis(key)
    v = _sub(tuple(point), pos)
    z = _dot(v, f)
    if z <= 0.05:
        return None
    fp = key["lens_mm"] / SENSOR_MM * max(w, h)
    return (w / 2 + fp * _dot(v, r) / z, h / 2 - fp * _dot(v, u) / z, z)
