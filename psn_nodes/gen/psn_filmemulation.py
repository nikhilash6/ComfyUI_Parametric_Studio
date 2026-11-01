"""PSN_FilmGrainLUT: builds a film-stock tone LUT, a seeded grain-noise mask and a halation threshold from numbers.

It takes no image and processes no image. What it returns:
- a 256-entry tone LUT for the selected stock and ISO (a list of floats, as JSON)
- a flat width*height list of uniform noise scaled by a grain strength (seeded, repeatable)
- the grain scale and the highlight threshold at which halation would start

It does NOT build a halation mask: halation follows the highlights of an image, and with no image
there is nothing to follow. The module also holds stock-preset validation, clamping and a LUT lookup.
It does not touch torch, numpy, ComfyUI, files, sockets, or the network.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Film"

FILM_STOCKS = ["Kodak_Portra_400", "Fuji_Velvia_50", "Ilford_HP5", "Custom"]

# Per-stock base LUT (256 entries, 0..1 floats) and spectral sensitivity weights (R,G,B)
_STOCK_LUTS = {
    "Kodak_Portra_400": {
        "lut": [min(1.0, max(0.0, (i / 255.0) ** 0.92)) for i in range(256)],
        "sensitivity": (1.0, 1.0, 0.95),
        "base_grain": 0.10,
        "halation_bias": 0.05,
    },
    "Fuji_Velvia_50": {
        "lut": [min(1.0, max(0.0, (i / 255.0) ** 1.15)) for i in range(256)],
        "sensitivity": (1.05, 1.0, 0.90),
        "base_grain": 0.04,
        "halation_bias": 0.02,
    },
    "Ilford_HP5": {
        "lut": [min(1.0, max(0.0, (i / 255.0) ** 1.0)) for i in range(256)],
        "sensitivity": (1.0, 1.0, 1.0),
        "base_grain": 0.18,
        "halation_bias": 0.08,
    },
    "Custom": {
        "lut": [i / 255.0 for i in range(256)],
        "sensitivity": (1.0, 1.0, 1.0),
        "base_grain": 0.08,
        "halation_bias": 0.04,
    },
}

ISO_MIN = 25
ISO_MAX = 12800
GRAIN_MIN = 0.0
GRAIN_MAX = 1.0
HALATION_MIN = 0.0
HALATION_MAX = 1.0


def _clamp(value, lo, hi):
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def validate_film_stock(film_stock):
    """Return (ok, reason). film_stock must be a string in the allow-list."""
    if not isinstance(film_stock, str):
        return False, "film_stock must be a string"
    if film_stock not in FILM_STOCKS:
        return False, "film_stock not in allow-list: %s" % film_stock
    return True, "ok"


def validate_iso(iso):
    """Return (ok, clamped_iso, reason). iso must be an int in [ISO_MIN, ISO_MAX]."""
    if not isinstance(iso, int) or isinstance(iso, bool):
        return False, ISO_MIN, "iso must be an integer"
    clamped = _clamp(iso, ISO_MIN, ISO_MAX)
    if clamped != iso:
        return True, clamped, "iso clamped to %d" % clamped
    return True, clamped, "ok"


def validate_grain(grain_amount):
    """Return (ok, clamped, reason). grain_amount must be a number in [0,1]."""
    if not isinstance(grain_amount, (int, float)) or isinstance(grain_amount, bool):
        return False, 0.0, "grain_amount must be a number"
    clamped = _clamp(float(grain_amount), GRAIN_MIN, GRAIN_MAX)
    if clamped != float(grain_amount):
        return True, clamped, "grain_amount clamped to %.4f" % clamped
    return True, clamped, "ok"


def validate_halation(halation):
    """Return (ok, clamped, reason). halation must be a number in [0,1]."""
    if not isinstance(halation, (int, float)) or isinstance(halation, bool):
        return False, 0.0, "halation must be a number"
    clamped = _clamp(float(halation), HALATION_MIN, HALATION_MAX)
    if clamped != float(halation):
        return True, clamped, "halation clamped to %.4f" % clamped
    return True, clamped, "ok"


def get_stock_params(film_stock):
    """Return the stock parameter dict for a validated film stock."""
    ok, _ = validate_film_stock(film_stock)
    if not ok:
        raise ValueError("invalid film stock: %r" % (film_stock,))
    return _STOCK_LUTS[film_stock]


def build_lut(film_stock, iso):
    """Return a 256-entry LUT (list of floats 0..1) adjusted for ISO.

    Higher ISO slightly lifts shadows and compresses highlights to mimic
    film response at higher sensitivity.
    """
    params = get_stock_params(film_stock)
    base = params["lut"]
    iso_factor = _clamp((iso - ISO_MIN) / float(ISO_MAX - ISO_MIN), 0.0, 1.0)
    shadow_lift = 0.02 * iso_factor
    highlight_compression = 1.0 - 0.10 * iso_factor
    out = []
    for v in base:
        lifted = v + shadow_lift * (1.0 - v)
        compressed = lifted * highlight_compression
        out.append(_clamp(compressed, 0.0, 1.0))
    return out


def compute_grain_scale(iso, grain_amount, width, height):
    """Return a resolution-aware grain scale factor.

    Grain should not look artificially large on high-res images, so we
    scale by the square root of pixel count relative to a 1024x1024 reference.
    """
    if width <= 0 or height <= 0:
        return 1.0
    ref_pixels = 1024 * 1024
    pixels = width * height
    res_factor = (pixels / float(ref_pixels)) ** 0.5
    iso_factor = _clamp((iso - ISO_MIN) / float(ISO_MAX - ISO_MIN), 0.0, 1.0)
    return _clamp(grain_amount * (0.5 + 0.5 * iso_factor) * res_factor, 0.0, 1.0)


def compute_halation_threshold(halation, stock_halation_bias):
    """Return the highlight threshold (0..1) above which halation is applied.

    Higher halation intensity lowers the threshold (more pixels affected).
    """
    base = 0.85
    lowered = base - halation * 0.5 - stock_halation_bias
    return _clamp(lowered, 0.0, 1.0)


def _deterministic_seed(film_stock, iso, width, height, grain_amount, halation):
    """Derive a deterministic integer seed from the inputs (no hashing of secrets)."""
    h = 0
    for ch in film_stock:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    h = (h * 31 + iso) & 0xFFFFFFFF
    h = (h * 31 + width) & 0xFFFFFFFF
    h = (h * 31 + height) & 0xFFFFFFFF
    h = (h * 31 + int(round(grain_amount * 1000))) & 0xFFFFFFFF
    h = (h * 31 + int(round(halation * 1000))) & 0xFFFFFFFF
    return h


def _lcg_next(state):
    """Return (next_state, value) where value is a repeatable noise float in [0,1)."""
    next_state = (state * 1103515245 + 12345) & 0x7FFFFFFF
    return next_state, next_state / float(0x7FFFFFFF)


def generate_grain_mask(width, height, grain_scale, seed):
    """Return a flat list of length width*height with grain intensities in [0,1]."""
    if width <= 0 or height <= 0:
        return []
    state = seed & 0xFFFFFFFF
    out = []
    for _ in range(width * height):
        state, val = _lcg_next(state)
        out.append(_clamp(val * grain_scale, 0.0, 1.0))
    return out


def combine_masks(grain_mask, halation_mask):
    """Return a combined mask (max of grain and halation per pixel)."""
    n = min(len(grain_mask), len(halation_mask))
    out = []
    for i in range(n):
        out.append(max(grain_mask[i], halation_mask[i]))
    return out


def apply_lut_to_pixel(pixel, lut):
    """Apply a 256-entry LUT to a single pixel value in [0,1]. Returns [0,1]."""
    if not isinstance(pixel, (int, float)) or isinstance(pixel, bool):
        return 0.0
    v = _clamp(float(pixel), 0.0, 1.0)
    idx = int(round(v * 255.0))
    idx = _clamp(idx, 0, 255)
    return _clamp(lut[idx], 0.0, 1.0)


class PSN_FilmGrainLUT:
    """Builds a tone LUT, a seeded grain-noise mask and a halation threshold from numbers.
    Takes no image and processes no image; makes no halation mask. No GPU, no torch, no I/O."""

    DESCRIPTION = ("Builds a film-stock tone LUT, a seeded uniform grain-noise mask (width*height values) and the "
                   "highlight threshold where halation would start, all from numbers. It processes no image and "
                   "makes no halation mask.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "film_stock": (list(FILM_STOCKS),),
                "iso": ("INT", {"default": 400, "min": ISO_MIN, "max": ISO_MAX, "step": 1}),
                "grain_amount": ("FLOAT", {"default": 0.5, "min": GRAIN_MIN, "max": GRAIN_MAX, "step": 0.01}),
                "halation": ("FLOAT", {"default": 0.3, "min": HALATION_MIN, "max": HALATION_MAX, "step": 0.01}),
                "width": ("INT", {"default": 1024, "min": 1, "max": 8192, "step": 1}),
                "height": ("INT", {"default": 1024, "min": 1, "max": 8192, "step": 1}),
            },
            "optional": {
                "seed_override": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFF, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "FLOAT")
    RETURN_NAMES = ("lut_json", "grain_mask_json", "grain_scale", "halation_threshold")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, film_stock, iso, grain_amount, halation, width, height, seed_override=0):
        import json

        ok_stock, why_stock = validate_film_stock(film_stock)
        if not ok_stock:
            return ("{}", "[]", 0.0, 0.0)

        ok_iso, iso_c, why_iso = validate_iso(iso)
        if not ok_iso:
            return ("{}", "[]", 0.0, 0.0)

        ok_grain, grain_c, why_grain = validate_grain(grain_amount)
        if not ok_grain:
            return ("{}", "[]", 0.0, 0.0)

        ok_hal, hal_c, why_hal = validate_halation(halation)
        if not ok_hal:
            return ("{}", "[]", 0.0, 0.0)

        if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
            return ("{}", "[]", 0.0, 0.0)
        if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
            return ("{}", "[]", 0.0, 0.0)

        params = get_stock_params(film_stock)
        lut = build_lut(film_stock, iso_c)
        grain_scale = compute_grain_scale(iso_c, grain_c, width, height)
        hal_threshold = compute_halation_threshold(hal_c, params["halation_bias"])

        if isinstance(seed_override, int) and not isinstance(seed_override, bool) and seed_override > 0:
            seed = seed_override & 0xFFFFFFFF
        else:
            seed = _deterministic_seed(film_stock, iso_c, width, height, grain_c, hal_c)

        grain_mask = generate_grain_mask(width, height, grain_scale, seed)
        return (json.dumps(lut), json.dumps(grain_mask), grain_scale, hal_threshold)


NODE_CLASS_MAPPINGS = {"PSN_FilmGrainLUT": PSN_FilmGrainLUT}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_FilmGrainLUT": "Film Grain + Tone LUT (no image input)"}
