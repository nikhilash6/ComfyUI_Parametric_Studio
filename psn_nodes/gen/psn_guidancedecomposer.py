"""PSN_Vector2D_Decompose: plain 2-D vector arithmetic on numbers you type in.

It takes no guidance tensor and is not connected to CFG or any sampler: the vector and the axis are
JSON text such as "[3.0, 4.0]". No GPU/torch/ComfyUI internals, no network, no file/OS access, no
eval/exec.

The node splits a 2D vector [x, y] into these results:
  1. Magnitude   - the length of the vector
  2. Angle       - the direction angle in radians
  3. Direction   - the unit direction vector [dx, dy]
  4. Scale       - a scale factor (magnitude relative to a reference)
  5. Projection  - scalar projection onto a user-supplied axis
  6. Residual    - the component orthogonal to the projection axis
  7. Composite   - a JSON summary of all of the above

All inputs are plain Python numbers or JSON strings. No external dependencies.
"""

import json
import math

CAT = "ParametricStudio/Guidance"

# Result names, in order
STAGES = (
    "Magnitude",
    "Angle",
    "Direction",
    "Scale",
    "Projection",
    "Residual",
    "Composite",
)

# Allowed modes for the scale reference
SCALE_MODES = ("absolute", "normalized", "clamped")


def _parse_vector(vec_json):
    """Parse a JSON string or list into a 2-element float vector [x, y].

    Returns (x, y) as floats. Raises ValueError on bad input.
    """
    if isinstance(vec_json, str):
        try:
            data = json.loads(vec_json)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("vec_json must be valid JSON")
    elif isinstance(vec_json, (list, tuple)):
        data = list(vec_json)
    else:
        raise ValueError("vec_json must be a JSON string or a list/tuple")

    if not isinstance(data, (list, tuple)) or len(data) != 2:
        raise ValueError("Vector must have exactly 2 components")

    try:
        x = float(data[0])
        y = float(data[1])
    except (TypeError, ValueError):
        raise ValueError("Vector components must be numeric")

    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError("Vector components must be finite numbers")

    return x, y


def _parse_axis(axis_json):
    """Parse a JSON string or list into a 2-element float axis [ax, ay].

    Returns (ax, ay) as floats. Raises ValueError on bad input.
    """
    if isinstance(axis_json, str):
        try:
            data = json.loads(axis_json)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("axis_json must be valid JSON")
    elif isinstance(axis_json, (list, tuple)):
        data = list(axis_json)
    else:
        raise ValueError("axis_json must be a JSON string or a list/tuple")

    if not isinstance(data, (list, tuple)) or len(data) != 2:
        raise ValueError("Axis must have exactly 2 components")

    try:
        ax = float(data[0])
        ay = float(data[1])
    except (TypeError, ValueError):
        raise ValueError("Axis components must be numeric")

    if not (math.isfinite(ax) and math.isfinite(ay)):
        raise ValueError("Axis components must be finite numbers")

    return ax, ay


def _magnitude(x, y):
    """Compute the Euclidean magnitude of vector (x, y)."""
    return math.hypot(x, y)


def _angle(x, y):
    """Compute the angle in radians of vector (x, y) from the positive x-axis."""
    return math.atan2(y, x)


def _direction(x, y, mag):
    """Compute the unit direction vector. Returns (0.0, 0.0) if magnitude is zero."""
    if mag < 1e-12:
        return 0.0, 0.0
    return x / mag, y / mag


def _scale(mag, reference, mode):
    """Compute the scale factor based on the chosen mode.

    - absolute:   mag / reference  (reference must be > 0)
    - normalized: mag / (reference + mag)  (always in [0, 1) for mag >= 0)
    - clamped:    min(mag / reference, 1.0)  (reference must be > 0)
    """
    if mode == "absolute":
        if reference <= 0:
            raise ValueError("reference must be > 0 for absolute scale mode")
        return mag / reference
    elif mode == "normalized":
        denom = reference + mag
        if denom < 1e-12:
            return 0.0
        return mag / denom
    elif mode == "clamped":
        if reference <= 0:
            raise ValueError("reference must be > 0 for clamped scale mode")
        return min(mag / reference, 1.0)
    else:
        raise ValueError("Unknown scale mode: %s" % mode)


def _projection(x, y, ax, ay):
    """Project vector (x, y) onto axis (ax, ay). Returns the scalar projection length."""
    axis_mag = math.hypot(ax, ay)
    if axis_mag < 1e-12:
        return 0.0
    # Unit axis
    ux = ax / axis_mag
    uy = ay / axis_mag
    # Dot product gives the scalar projection
    return x * ux + y * uy


def _residual(x, y, ax, ay):
    """Compute the residual (orthogonal) component of vector (x, y) relative to axis (ax, ay).

    Returns (rx, ry) as the residual vector.
    """
    axis_mag = math.hypot(ax, ay)
    if axis_mag < 1e-12:
        return x, y
    ux = ax / axis_mag
    uy = ay / axis_mag
    # Projection vector
    proj_scalar = x * ux + y * uy
    px = proj_scalar * ux
    py = proj_scalar * uy
    # Residual = original - projection
    return x - px, y - py


def _composite(magnitude, angle, dir_x, dir_y, scale, proj, res_x, res_y):
    """Build a JSON string summarizing all stages."""
    summary = {
        "Magnitude": magnitude,
        "Angle": angle,
        "Direction": [dir_x, dir_y],
        "Scale": scale,
        "Projection": proj,
        "Residual": [res_x, res_y],
    }
    return json.dumps(summary, sort_keys=True)


class PSN_Vector2D_Decompose:
    """Decompose a typed 2-D vector into magnitude, angle, direction, scale, projection, residual and a JSON summary.
    Not tied to CFG; it reads no tensor.

    Results:
      1. Magnitude   - Euclidean length of the vector
      2. Angle       - Direction angle in radians
      3. Direction   - Unit direction vector [dx, dy]
      4. Scale       - Normalized scale factor relative to a reference
      5. Projection  - Scalar projection onto a user-supplied axis
      6. Residual    - Orthogonal component vector [rx, ry]
      7. Composite   - JSON summary of all stages

    All inputs are plain values (numbers, strings, JSON text). No GPU, network,
    file, or OS access is performed.
    """

    DESCRIPTION = ("Computes magnitude, angle, unit direction, scale, projection onto an axis and residual of a "
                   "2-D vector typed as JSON. It reads no guidance tensor and is not connected to CFG.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "vec_json": ("STRING", {"default": "[1.0, 0.0]", "multiline": False}),
                "axis_json": ("STRING", {"default": "[1.0, 0.0]", "multiline": False}),
                "reference": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1e9, "step": 0.001}),
                "scale_mode": (list(SCALE_MODES),),
            },
            "optional": {},
        }

    RETURN_TYPES = (
        "FLOAT",   # Magnitude
        "FLOAT",   # Angle
        "STRING",  # Direction as JSON "[dx, dy]"
        "FLOAT",   # Scale
        "FLOAT",   # Projection
        "STRING",  # Residual as JSON "[rx, ry]"
        "STRING",  # Composite JSON
    )
    RETURN_NAMES = (
        "magnitude",
        "angle",
        "direction",
        "scale",
        "projection",
        "residual",
        "composite",
    )
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, vec_json, axis_json, reference, scale_mode):
        x, y = _parse_vector(vec_json)
        ax, ay = _parse_axis(axis_json)

        mag = _magnitude(x, y)
        ang = _angle(x, y)
        dx, dy = _direction(x, y, mag)
        scale = _scale(mag, reference, scale_mode)
        proj = _projection(x, y, ax, ay)
        rx, ry = _residual(x, y, ax, ay)
        comp = _composite(mag, ang, dx, dy, scale, proj, rx, ry)

        direction_str = json.dumps([dx, dy])
        residual_str = json.dumps([rx, ry])

        return (mag, ang, direction_str, scale, proj, residual_str, comp)


NODE_CLASS_MAPPINGS = {
    "PSN_Vector2D_Decompose": PSN_Vector2D_Decompose,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Vector2D_Decompose": "2D Vector Decompose (typed numbers, not CFG)",
}
