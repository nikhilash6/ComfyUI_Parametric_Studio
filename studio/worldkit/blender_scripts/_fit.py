"""Turntable framing maths, plain Python (no bpy) so the tests can check it without Blender.

The camera is fitted to the asset's bounding sphere: the sphere is centred on the bounds' centre, its radius is the
farthest vertex from that centre, and the camera stands far enough back that the sphere fits the narrower field of view
with FIT_MARGIN to spare. A sphere looks the same from every side, so the fit holds at every step of the orbit and at
any camera height, for a 5 cm ring and a 40 m tower alike. The frame therefore says nothing about real size: the
World Kit page shows that on its "Real scale" tag (the asset's longest side against a 1.8 m person)."""
import math

FIT_MARGIN = 1.12        # the sphere's radius plus 12% fills the narrower half of the frame
MIN_RADIUS = 0.002       # a degenerate asset (a point, a line) still gets a camera 2 mm away, not on top of it
FLAT = 0.25              # height under this share of the longest side: a rug, a coin, a road sign laid flat
FLAT_RISE = 0.9          # ... and the camera looks down on it at least this steeply (rise over run, about 42 degrees)
CLIP_END = 8000.0


def view_angle(lens_mm: float, sensor_mm: float, res_x: int, res_y: int) -> float:
    """The narrower field of view, in radians, of a camera whose sensor width spans the longer side of the frame
    (Blender's sensor fit AUTO)."""
    half_long = math.atan(sensor_mm / 2.0 / lens_mm)
    short, long_ = sorted((max(1, int(res_x)), max(1, int(res_y))))
    return 2.0 * math.atan(math.tan(half_long) * short / long_)


def fit_distance(radius: float, fov: float, margin: float = FIT_MARGIN) -> float:
    """How far from the sphere's centre the camera stands so a sphere of `radius` (times `margin`) just fits a view
    cone of full angle `fov`: the cone's edge is tangent to the sphere, so sin(fov / 2) = radius / distance."""
    return max(float(radius), MIN_RADIUS) * margin / math.sin(fov / 2.0)


def rise(dims, elevation: float) -> float:
    """Camera height over horizontal distance. A flat asset is looked down on, so its top shows."""
    w, d, h = (abs(float(x)) for x in dims)
    longest = max(w, d, h)
    if longest > 0 and h < FLAT * longest:
        return max(float(elevation), FLAT_RISE)
    return float(elevation)


def orbit(centre, radius: float, dims, fov: float, turn: float, elevation: float, margin: float = FIT_MARGIN):
    """The camera at `turn` radians round the asset -> (position, clip_start, clip_end). It sits `fit_distance` from
    the centre (measured along the line of sight, so raising it never crops), `rise` up, and looks at the centre."""
    dist = fit_distance(radius, fov, margin)
    up = math.atan(rise(dims, elevation))
    flat = dist * math.cos(up)
    pos = (centre[0] + math.sin(turn) * flat, centre[1] - math.cos(turn) * flat, centre[2] + dist * math.sin(up))
    r = max(float(radius), MIN_RADIUS)
    near = max(1e-5, min(0.1, (dist - r) * 0.1))        # Blender's 10 cm default would cut a ring off at 6 cm away
    return pos, near, max(CLIP_END, (dist + r) * 4.0)
