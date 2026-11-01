"""Seed hash vector (pure-logic, secure-by-design).

This module maps an integer seed to two deterministic, reproducible float
vectors using only the Python standard library (``hashlib`` + ``struct``). It
does NOT import torch, ComfyUI, numpy, or any model weights, and it performs no
file, network, or OS access.

The vectors are hash and LCG output, not CLIP embeddings: no text and no model
is involved, and the result cannot drive sampling as it is.  The node emits
them as plain JSON text (``vector_json``) plus a human-readable ``summary``.
The ``size_preset`` input only picks the vector lengths (sd15: 768 and 768;
sdxl: 2048 and 1280), matching the shapes of those models' CLIP outputs.

Strategies:
  * A - Anchor-weighted: SHA-256-derived weights (no external anchor file is
        read; the "anchors" are derived from the seed).
  * B - Hash-based: raw SHA-256 digest bytes mapped to floats.
  * C - LCG-based: linear congruential generator seeded by the integer seed.
  * D - Mixed: combines B and C for extra diffusion.

All strategies are pure functions of (seed, strategy, size_preset), so the same
inputs always yield byte-identical outputs.
"""

import hashlib
import json
import struct

CAT = "ParametricStudio/Conditioning"

_STRATEGIES = ["A", "B", "C", "D"]
_SIZE_PRESETS_NAMES = ["sd15", "sdxl"]

# (dim_a, dim_b) per size preset.
# sd15: 768 and 768. sdxl: 2048 and 1280.
_SIZE_PRESETS = {
    "sd15": (768, 768),
    "sdxl": (2048, 1280),
}

# Number of "anchor" slots used by strategy A.
_ANCHOR_SLOTS = 16


def _digest_bytes(seed, strategy, salt):
    """Return 32 raw digest bytes for the given seed/strategy/salt."""
    payload = "{}|{}|{}".format(seed, strategy, salt).encode("utf-8")
    return hashlib.sha256(payload).digest()


def _bytes_to_floats(raw, count):
    """Map raw bytes to `count` floats in [-1, 1] deterministically."""
    out = []
    for i in range(count):
        # Take 4 bytes at a time (wrapping) and interpret as a signed 32-bit int.
        idx = (i * 4) % len(raw)
        chunk = raw[idx:idx + 4]
        # Pad if the tail is short (should not happen with 32-byte digests,
        # but be safe for very large counts by cycling).
        while len(chunk) < 4:
            chunk += raw[: 4 - len(chunk)]
        value = struct.unpack(">i", chunk)[0]
        # Normalize signed 32-bit int to [-1, 1].
        out.append(value / 2147483648.0)
    return out


def _lcg_floats(seed, count):
    """Generate `count` floats in [-1, 1] using a 64-bit LCG."""
    # Constants (Numerical Recipes style).
    a = 6364136223846793005
    c = 1442695040888963407
    m = 1 << 64
    state = (seed & (m - 1)) or 1  # avoid 0 state
    out = []
    for _ in range(count):
        state = (a * state + c) % m
        # Take the high 32 bits as a signed int for better distribution.
        hi = (state >> 32) & 0xFFFFFFFF
        if hi >= 0x80000000:
            hi -= 0x100000000
        out.append(hi / 2147483648.0)
    return out


def _anchor_weights(seed, slots):
    """Strategy A: derive `slots` anchor weights in [0, 1] from the seed."""
    raw = _digest_bytes(seed, "A", "anchor")
    weights = []
    for i in range(slots):
        idx = (i * 4) % len(raw)
        chunk = raw[idx:idx + 4]
        while len(chunk) < 4:
            chunk += raw[: 4 - len(chunk)]
        value = struct.unpack(">I", chunk)[0]
        weights.append(value / 4294967296.0)
    return weights


def _build_vector_a(seed, strategy, dim_a):
    """Build the first vector (length dim_a) for the given strategy."""
    if strategy == "A":
        # Anchor-weighted: blend anchor weights with hash-based values.
        anchors = _anchor_weights(seed, _ANCHOR_SLOTS)
        base = _bytes_to_floats(_digest_bytes(seed, "A", "vector_a"), dim_a)
        # Weight each element by the nearest anchor weight.
        out = []
        for i, v in enumerate(base):
            w = anchors[i % _ANCHOR_SLOTS]
            out.append(v * (0.5 + 0.5 * w))
        return out
    elif strategy == "B":
        return _bytes_to_floats(_digest_bytes(seed, "B", "vector_a"), dim_a)
    elif strategy == "C":
        return _lcg_floats(seed, dim_a)
    elif strategy == "D":
        # Mixed: average of B and C.
        b = _bytes_to_floats(_digest_bytes(seed, "D", "vector_a"), dim_a)
        c = _lcg_floats(seed, dim_a)
        return [(x + y) * 0.5 for x, y in zip(b, c)]
    raise ValueError("Unknown strategy: {}".format(strategy))


def _build_vector_b(seed, strategy, dim_b):
    """Build the second vector (length dim_b) for the given strategy."""
    if strategy == "A":
        anchors = _anchor_weights(seed, _ANCHOR_SLOTS)
        base = _bytes_to_floats(_digest_bytes(seed, "A", "vector_b"), dim_b)
        out = []
        for i, v in enumerate(base):
            w = anchors[i % _ANCHOR_SLOTS]
            out.append(v * (0.5 + 0.5 * w))
        return out
    elif strategy == "B":
        return _bytes_to_floats(_digest_bytes(seed, "B", "vector_b"), dim_b)
    elif strategy == "C":
        return _lcg_floats(seed + 1, dim_b)  # offset seed for the second vector
    elif strategy == "D":
        b = _bytes_to_floats(_digest_bytes(seed, "D", "vector_b"), dim_b)
        c = _lcg_floats(seed + 1, dim_b)
        return [(x + y) * 0.5 for x, y in zip(b, c)]
    raise ValueError("Unknown strategy: {}".format(strategy))


def _round_floats(vec, decimals=6):
    """Round floats to a fixed number of decimals for stable JSON output."""
    return [round(v, decimals) for v in vec]


def generate_seed_vectors(seed, strategy, size_preset):
    """Pure-logic core: produce the two seed vectors as a dict.

    Returns a dict with keys:
      * ``vector_a``: list of floats (length = dim_a)
      * ``vector_b``: list of floats (length = dim_b)
      * ``seed``: the input seed
      * ``strategy``: the strategy used
      * ``size_preset``: the model type
      * ``dim_a``: int
      * ``dim_b``: int
    """
    if strategy not in _STRATEGIES:
        raise ValueError("strategy must be one of {}".format(_STRATEGIES))
    if size_preset not in _SIZE_PRESETS_NAMES:
        raise ValueError("size_preset must be one of {}".format(_SIZE_PRESETS_NAMES))
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")

    dim_a, dim_b = _SIZE_PRESETS[size_preset]
    vec_a = _build_vector_a(seed, strategy, dim_a)
    vec_b = _build_vector_b(seed, strategy, dim_b)

    return {
        "vector_a": _round_floats(vec_a),
        "vector_b": _round_floats(vec_b),
        "seed": seed,
        "strategy": strategy,
        "size_preset": size_preset,
        "dim_a": dim_a,
        "dim_b": dim_b,
    }


class PSN_SeedHashVector:
    """Derive deterministic hash-based float vectors from an integer seed.

    Not a CLIP embedding and cannot drive sampling: no text or model is
    involved.  Outputs the vectors as JSON text (``vector_json``) and a short
    human-readable ``summary``.
    """

    DESCRIPTION = ("Derives deterministic hash-based float vectors from a seed and returns "
                   "them as JSON text. It is not a CLIP embedding and cannot drive sampling; "
                   "size_preset only picks the vector lengths.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": -2**63, "max": 2**63 - 1, "step": 1}),
                "strategy": (_STRATEGIES,),
                "size_preset": (_SIZE_PRESETS_NAMES,),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("vector_json", "summary")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, seed, strategy, size_preset):
        payload = generate_seed_vectors(seed, strategy, size_preset)
        vector_json = json.dumps(payload, separators=(",", ":"))
        summary = (
            "seed={} strategy={} size_preset={} dim_a={} dim_b={}".format(
                seed, strategy, size_preset, payload["dim_a"], payload["dim_b"]
            )
        )
        return (vector_json, summary)


NODE_CLASS_MAPPINGS = {
    "PSN_SeedHashVector": PSN_SeedHashVector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SeedHashVector": "Seed Hash Vector (not a CLIP embedding)",
}
