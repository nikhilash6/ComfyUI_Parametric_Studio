"""PSN_Seed_Source: outputs the seed you give it, plus the SHA-256 hash of that seed.

It does not find or change seed widgets elsewhere in the graph: wire `seed_out` to each sampler's
seed input yourself. The hash is only a label for the seed value (handy to compare two runs); it does
not make a run reproducible by itself. No sockets, no files, no GPU/torch/ComfyUI internals.
"""

import hashlib
import json

CAT = "ParametricStudio/Seed"


def psn_seed_hash(seed: int) -> str:
    """Compute a deterministic hex hash string for a given integer seed.

    Uses SHA-256 of the JSON-encoded seed value to produce a stable,
    reproducible hash string.

    Args:
        seed: An integer seed value.

    Returns:
        A 64-character hexadecimal string representing the SHA-256 hash.
    """
    if not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    payload = json.dumps({"seed": seed}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PSN_Seed_Source:
    """Outputs the given seed and its SHA-256 hash. Wire seed_out to samplers by hand; it reaches no other node."""

    DESCRIPTION = ("Outputs the seed you set and the SHA-256 hash of it. It does not reach other nodes: "
                   "wire seed_out to each sampler's seed input yourself.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": -2**31, "max": 2**31 - 1, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("seed_out", "seed_hash")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, seed: int):
        """Return (seed, sha256 hex of the seed)."""
        if not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        return (seed, psn_seed_hash(seed))


NODE_CLASS_MAPPINGS = {
    "PSN_Seed_Source": PSN_Seed_Source,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Seed_Source": "Seed Source (wire to samplers by hand)",
}
