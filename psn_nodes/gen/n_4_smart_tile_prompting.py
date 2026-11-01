"""PSN_TileGrid (pure-logic, secure-by-design).

Computes the overlapping tile grid for an image from its width/height, tile
size and overlap, and returns one ``[x, y, w, h]`` line per tile. That is all
it does: it reads no image, makes no prompts and runs no vision-language model.

Pure Python (standard library only): no torch/comfy imports, no network, no
file/OS access, no eval/exec.
"""

import math

CAT = "ParametricStudio/SmartTile"

# Hard bounds for tile geometry (defensive, secure-by-design).
_MIN_TILE = 16
_MAX_TILE = 4096
_MAX_DIM = 16384
_MAX_TILES = 4096


def _clamp_int(value, low, high):
    """Coerce a value to an int clamped into [low, high].

    Raises ValueError for non-numeric / non-finite input.
    """
    if isinstance(value, bool):
        raise ValueError("tile/overlap values must be numbers, not bool")
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError("tile/overlap values must be numeric")
    if not math.isfinite(num):
        raise ValueError("tile/overlap values must be finite")
    as_int = int(num)
    if as_int < low:
        return low
    if as_int > high:
        return high
    return as_int


def compute_tile_grid(width, height, tile_size, overlap):
    """Compute the tile grid for an image.

    Returns a list of (x, y, w, h) tuples. The grid is deterministic:
    tiles are laid out left-to-right, top-to-bottom. The last tile in each
    axis is clamped so it never exceeds the image bounds.

    Raises ValueError for invalid geometry.
    """
    width = _clamp_int(width, 1, _MAX_DIM)
    height = _clamp_int(height, 1, _MAX_DIM)
    tile_size = _clamp_int(tile_size, _MIN_TILE, _MAX_TILE)
    overlap = _clamp_int(overlap, 0, tile_size - 1)

    if width <= 0 or height <= 0:
        raise ValueError("image width and height must be positive")

    step = tile_size - overlap
    if step <= 0:
        raise ValueError("overlap must be smaller than tile_size")

    def _positions(dim):
        if dim <= tile_size:
            return [0]
        positions = []
        pos = 0
        while True:
            positions.append(pos)
            if pos + tile_size >= dim:
                break
            pos += step
        # Ensure the final tile covers the right/bottom edge.
        last = dim - tile_size
        if last > positions[-1]:
            positions.append(last)
        return positions

    xs = _positions(width)
    ys = _positions(height)

    tiles = []
    for y in ys:
        for x in xs:
            w = min(tile_size, width - x)
            h = min(tile_size, height - y)
            tiles.append((x, y, w, h))

    if len(tiles) > _MAX_TILES:
        raise ValueError("tile grid exceeds maximum tile count")

    return tiles


class PSN_TileGrid:
    """Compute the tile coordinates for an image size. Makes no prompts."""

    DESCRIPTION = ("Computes overlapping tile coordinates [x, y, w, h] for an "
                   "image size. It reads no image, writes no prompts and runs "
                   "no vision-language model.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 1024, "min": 1, "max": _MAX_DIM, "step": 1}),
                "height": ("INT", {"default": 1024, "min": 1, "max": _MAX_DIM, "step": 1}),
                "tile_size": ("INT", {"default": 512, "min": _MIN_TILE, "max": _MAX_TILE, "step": 1}),
                "overlap": ("INT", {"default": 64, "min": 0, "max": _MAX_TILE - 1, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("TILE_COORDS",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, width, height, tile_size, overlap):
        tiles = compute_tile_grid(width, height, tile_size, overlap)
        coords_text = "\n".join(
            "[{x}, {y}, {w}, {h}]".format(x=x, y=y, w=w, h=h)
            for (x, y, w, h) in tiles
        )
        return (coords_text,)


NODE_CLASS_MAPPINGS = {
    "PSN_TileGrid": PSN_TileGrid,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_TileGrid": "Tile Grid Coordinates (PSN)",
}
