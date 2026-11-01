"""ParametricStudio - random motion test fixture.

This module emits seeded random joint-rotation noise so a graph that consumes
motion data can be wired and tested.  It is NOT text-to-motion: no text
encoder, no MDM / Kimodo / MoMask model and no AnimoFlow backend is involved,
and nothing about the output depends on a prompt.

What it does:
* draws seeded Gaussian noise (``torch.Generator``) for a small humanoid rig,
* splits it into rotations and translations,
* writes those values into a BVH text string,
* returns the same values as an in-memory dict with keys ``rotations`` and
  ``translations`` (no ``.npz`` file is written).

The result is reproducible for a given (duration, seed) and is not real motion.
"""

import math

import torch

CAT = "ParametricStudio/Motion"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Number of joints in a simplified humanoid rig (Hips + 13 children).
NUM_JOINTS = 14

# Each joint has a 3D rotation (axis-angle) and a 3D translation.
ROT_DIM = 3
TRANS_DIM = 3

# Frames per second for the generated clip.
FPS = 30

# Status codes.
STATUS_OK = 0
STATUS_BAD_DURATION = 2
STATUS_BAD_SEED = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_duration(duration):
    """Return (ok, frames)."""
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        return False, 0
    d = float(duration)
    if not math.isfinite(d) or d <= 0.0:
        return False, 0
    frames = max(1, int(round(d * FPS)))
    return True, frames


def _validate_seed(seed):
    if isinstance(seed, bool) or not isinstance(seed, int):
        return False
    if seed < 0:
        return False
    return True


def _seeded_noise_sample(seed, frames):
    """Seeded Gaussian noise, shape [frames, NUM_JOINTS, ROT_DIM + TRANS_DIM].

    The same (seed, frames) always gives the same tensor.  Nothing conditions
    it: it is random numbers scaled to 0.25, not a motion model's output.
    """
    gen = torch.Generator(device="cpu")
    gen.manual_seed(seed)
    return torch.randn(frames, NUM_JOINTS, ROT_DIM + TRANS_DIM, generator=gen) * 0.25


def _decode_latent(latent):
    """Split the latent into rotations and translations tensors.

    Returns (rotations, translations) each of shape [frames, NUM_JOINTS, 3].
    """
    rotations = latent[:, :, :ROT_DIM].clone()
    translations = latent[:, :, ROT_DIM:ROT_DIM + TRANS_DIM].clone()
    return rotations, translations


def _build_bvh_string(rotations, translations, fps=FPS):
    """Build a BVH text string from joint rotations and translations.

    The BVH format is a text-based motion-capture format.  We produce a
    minimal but structurally valid BVH file with a Hips root joint and
    child joints, plus a MOTION section with frame data.

    Returns a string.
    """
    frames = rotations.shape[0]
    joints = rotations.shape[1]

    lines = []
    lines.append("HIERARCHY")
    lines.append("Root Hips")
    lines.append("{")
    lines.append("  OFFSET 0.0 0.0 0.0")
    lines.append("  CHANNELS 6 Zrotation Xposition Yposition Zposition Xrotation Yrotation")

    # Child joints
    for j in range(1, joints):
        lines.append("  Joint Joint_%d" % j)
        lines.append("  {")
        lines.append("    OFFSET 0.0 0.0 0.0")
        lines.append("    CHANNELS 3 Zrotation Xrotation Yrotation")
        lines.append("  }")

    lines.append("}")
    lines.append("")
    lines.append("MOTION")
    lines.append("Frames: %d" % frames)
    lines.append("Frame Time: %.6f" % (1.0 / fps))

    # Frame data: for each frame, Hips has 6 channels (Zrot, Xpos, Ypos, Zpos, Xrot, Yrot)
    # and each child joint has 3 channels (Zrot, Xrot, Yrot).
    for f in range(frames):
        vals = []
        # Hips: Zrotation, Xposition, Yposition, Zposition, Xrotation, Yrotation
        vals.append(rotations[f, 0, 2].item())  # Zrotation
        vals.append(translations[f, 0, 0].item())  # Xposition
        vals.append(translations[f, 0, 1].item())  # Yposition
        vals.append(translations[f, 0, 2].item())  # Zposition
        vals.append(rotations[f, 0, 0].item())  # Xrotation
        vals.append(rotations[f, 0, 1].item())  # Yrotation
        # Child joints: Zrotation, Xrotation, Yrotation
        for j in range(1, joints):
            vals.append(rotations[f, j, 2].item())
            vals.append(rotations[f, j, 0].item())
            vals.append(rotations[f, j, 1].item())
        lines.append(" ".join("%.6f" % v for v in vals))

    return "\n".join(lines) + "\n"


def _make_motion_dict(rotations, translations):
    """In-memory dict with the noise as ``rotations`` and ``translations``.

    No ``.npz`` file is written.
    """
    return {
        "rotations": rotations.clone(),
        "translations": translations.clone(),
    }


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_Random_Motion_Test_Fixture:
    """Seeded random joint-rotation noise as BVH text and a rotations/translations dict.

    For wiring tests only.  It is not text-to-motion and runs no model.
    """

    DESCRIPTION = ("Emits seeded random joint-rotation noise as BVH text and a "
                   "rotations/translations dict, for wiring tests. It runs no "
                   "motion model, takes no prompt, and the result is not real motion.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "duration": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 60.0, "step": 0.1}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2 ** 32 - 1}),
            }
        }

    RETURN_TYPES = ("RANDOM_MOTION_DICT", "STRING", "INT")
    RETURN_NAMES = ("random_motion", "bvh_text", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, duration, seed):
        ok, frames = _validate_duration(duration)
        if not ok:
            return ({"error": "bad duration"}, "", STATUS_BAD_DURATION)

        if not _validate_seed(seed):
            return ({"error": "bad seed"}, "", STATUS_BAD_SEED)

        latent = _seeded_noise_sample(seed, frames)
        rotations, translations = _decode_latent(latent)
        motion = _make_motion_dict(rotations, translations)
        bvh_string = _build_bvh_string(rotations, translations, FPS)

        return (motion, bvh_string, STATUS_OK)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Random_Motion_Test_Fixture": PSN_Random_Motion_Test_Fixture,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Random_Motion_Test_Fixture": "Random Motion Test Fixture (seeded noise, not real motion)",
}
