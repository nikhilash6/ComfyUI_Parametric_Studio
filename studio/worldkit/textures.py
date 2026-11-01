"""Seamless textures for places. An image model does not tile, so make_tileable() shifts the picture by half (its borders then wrap onto each
other seamlessly) and cross-fades the unshifted picture back over the middle, where the shifted copy has its seam.
procedural() makes a tiling texture from numbers alone (brick, planks, paving, tarmac, sand, plaster), with no model, for a machine or a
moment where no image model can run. It wraps at the edges by construction."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def make_tileable(src, dest, size: int = 1024, blend: float = 0.25) -> Path:
    with Image.open(src) as im:
        a = np.asarray(im.convert("RGB").resize((size, size), Image.LANCZOS), dtype=np.float32)
    shifted = np.roll(a, (size // 2, size // 2), axis=(0, 1))
    edge = np.minimum(np.arange(size), np.arange(size)[::-1]) / max(1.0, size * blend)
    w = np.clip(edge, 0.0, 1.0)
    m = np.outer(w, w)[..., None]
    out = a * m + shifted * (1.0 - m)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dest, format="PNG")
    return dest


def _noise(rng, size: int, cells: int) -> np.ndarray:
    """Smooth noise in 0..1 that wraps: random values on a wrapping coarse grid, interpolated."""
    g = rng.random((cells, cells))
    x = np.arange(size) * cells / size
    i = x.astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    j = (i + 1) % cells
    a = g[i][:, i] * (1 - f)[None, :] + g[i][:, j] * f[None, :]
    b = g[j][:, i] * (1 - f)[None, :] + g[j][:, j] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]


def _fractal(rng, size: int, base: int = 4, octaves: int = 5) -> np.ndarray:
    out, amp, total = np.zeros((size, size)), 1.0, 0.0
    for o in range(octaves):
        out += amp * _noise(rng, size, min(base * 2 ** o, size))
        total += amp
        amp *= 0.55
    return out / total


def _courses(rng, size, rows, cols, mortar, base, vary, shift=0.5):
    """Bricks or slabs in running bond: every other course moved by half a unit. Rows and cols are whole, so it wraps."""
    y, x = np.mgrid[0:size, 0:size] / size
    row = (y * rows).astype(int)
    u = (x * cols + (row % 2) * shift) % cols
    col = u.astype(int)
    fy, fx = (y * rows) % 1.0, u % 1.0
    table = rng.random((rows, cols))
    tone = table[row % rows, col % cols]
    joint = (fy < mortar) | (fx < mortar * rows / cols)
    img = np.ones((size, size, 3)) * np.array(base)[None, None]
    img *= (1 - vary + 2 * vary * tone)[..., None]
    return img, joint


def _planks(rng, size, rows, base):
    y, x = np.mgrid[0:size, 0:size] / size
    row = (y * rows).astype(int)
    grain = _fractal(rng, size, 3)
    streak = np.roll(_noise(rng, size, size // 4 or 1), 0, 0)
    tone = rng.random(rows)[row % rows]
    img = np.ones((size, size, 3)) * np.array(base)[None, None]
    img *= (0.75 + 0.4 * tone + 0.25 * (grain - 0.5) + 0.12 * (streak - 0.5))[..., None]
    joint = ((y * rows) % 1.0) < 0.05
    img[joint] *= 0.35
    return img


KINDS = ("brick", "plank", "paving", "tarmac", "sand", "plaster", "water")
#: Words in a material's description -> the pattern that reads as it. First match wins.
WORDS = (("water", "water"), ("brick", "brick"), ("plank", "plank"), ("board", "plank"), ("wood", "plank"), ("walnut", "plank"), ("oak", "plank"),
         ("paving", "paving"), ("slab", "paving"), ("tile", "paving"), ("asphalt", "tarmac"), ("road", "tarmac"), ("tarmac", "tarmac"),
         ("sand", "sand"), ("plaster", "plaster"), ("paint", "plaster"), ("concrete", "paving"))
COLOURS = {"brick": (0.50, 0.25, 0.18), "plank": (0.45, 0.31, 0.19), "paving": (0.58, 0.57, 0.54), "tarmac": (0.17, 0.17, 0.18),
           "sand": (0.60, 0.48, 0.31), "plaster": (0.78, 0.74, 0.66), "water": (0.03, 0.22, 0.30)}


def kind_of(what: str) -> str:
    text = str(what or "").lower()
    return next((k for w, k in WORDS if w in text), "plaster")


def procedural(what: str, dest, *, size: int = 512, seed: int = 0) -> Path:
    """A tiling PNG for a material described in words ("red brick wall"). The same words and seed give the same picture."""
    kind = kind_of(what)
    rng = np.random.default_rng(abs(int(seed)) % 2**32)
    base = COLOURS[kind]
    text = str(what or "").lower()
    if kind == "plank" and ("dark" in text or "walnut" in text):
        base = (0.22, 0.14, 0.09)
    if kind == "plank" and ("white" in text or "painted" in text):
        base = (0.82, 0.80, 0.76)
    fine = _fractal(rng, size, 8)
    if kind == "brick":
        img, joint = _courses(rng, size, 16, 8, 0.1, base, 0.22)
        img *= (0.85 + 0.3 * fine)[..., None]
        img[joint] = (np.array((0.42, 0.40, 0.37))[None, None] * (0.8 + 0.4 * fine)[..., None])[joint]
    elif kind == "paving":
        img, joint = _courses(rng, size, 6, 6, 0.025, base, 0.07, shift=0.0)
        img *= (0.82 + 0.36 * fine)[..., None]
        img[joint] *= 0.45
    elif kind == "plank":
        img = _planks(rng, size, 6, base)
    elif kind == "tarmac":
        speck = rng.random((size, size))
        img = np.ones((size, size, 3)) * np.array(base)[None, None]
        img *= (0.72 + 0.5 * _fractal(rng, size, 6) + 0.5 * (speck - 0.5))[..., None]
    elif kind == "sand":
        ripple = _fractal(rng, size, 3, 3)
        speck = rng.random((size, size))
        img = np.ones((size, size, 3)) * np.array(base)[None, None]
        img *= (0.82 + 0.25 * ripple + 0.14 * (speck - 0.5))[..., None]
    elif kind == "water":
        swell = _fractal(rng, size, 3, 3)
        chop = _fractal(rng, size, 24, 3)
        img = np.ones((size, size, 3)) * np.array(base)[None, None]
        img *= (0.72 + 0.35 * swell + 0.5 * (chop - 0.5))[..., None]
        img[chop > np.quantile(chop, 0.985)] = (0.45, 0.55, 0.58)     # small flecks of white on the top of the chop
    else:
        img = np.ones((size, size, 3)) * np.array(base)[None, None]
        img *= (0.9 + 0.2 * _fractal(rng, size, 5))[..., None]
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    srgb = np.clip(img, 0, 1) ** (1 / 2.2)                           # the colours above are linear; a PNG is sRGB
    Image.fromarray((srgb * 255).astype(np.uint8)).save(dest, format="PNG")
    return dest
