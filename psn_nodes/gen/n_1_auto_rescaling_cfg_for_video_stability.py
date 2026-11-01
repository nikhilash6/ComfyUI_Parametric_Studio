"""
PSN_CFG_Rescale_Calculator: arithmetic that reduces a CFG number inside a step window.

Given a base CFG, a step window and a noise magnitude that you type in, this
computes a reduced CFG value (linear, exponential or clamp mode) and says why.
It takes no MODEL, patches no model, hooks no sampler and measures no noise:
the step and the noise magnitude are plain inputs, so nothing here runs per
sampling step on its own.

The node takes plain values (numbers, strings) and returns the calculated CFG
value, a boolean saying whether a reduction was applied, and a human-readable
reason.

Dependencies: Pure Python standard library only.
"""

import math

# Category for the node
CAT = "ParametricStudio/Video"

# Allowed modes for rescaling behavior
_MODES = ("linear", "exponential", "clamp")


def _compute_reduced_cfg(
    base_cfg: float,
    rescale_strength: float,
    step: int,
    start_step: int,
    end_step: int,
    noise_magnitude: float,
    threshold: float,
    mode: str,
) -> tuple[float, bool, str]:
    """
    Compute a reduced CFG value for a given step and typed-in noise magnitude.

    Args:
        base_cfg: The initial CFG scale.
        rescale_strength: How aggressively to rescale (0.0 to 1.0).
        step: Current sampling step index.
        start_step: Step index to begin rescaling.
        end_step: Step index to stop rescaling.
        noise_magnitude: Magnitude of the predicted noise.
        threshold: Dynamic threshold for noise magnitude.
        mode: Rescaling mode ("linear", "exponential", "clamp").

    Returns:
        Tuple of (reduced_cfg, reduction_applied, reason).
    """
    # Validate inputs
    if not (0.0 <= rescale_strength <= 1.0):
        raise ValueError("rescale_strength must be between 0.0 and 1.0")
    if step < 0:
        raise ValueError("step must be non-negative")
    if start_step < 0:
        raise ValueError("start_step must be non-negative")
    if end_step < start_step:
        raise ValueError("end_step must be >= start_step")
    if base_cfg < 0:
        raise ValueError("base_cfg must be non-negative")
    if noise_magnitude < 0:
        raise ValueError("noise_magnitude must be non-negative")
    if threshold < 0:
        raise ValueError("threshold must be non-negative")
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}")

    # If we're outside the rescaling window, return base_cfg unchanged
    if step < start_step or step > end_step:
        return (base_cfg, False, "Outside rescaling window")

    # If noise magnitude is below threshold, no rescaling needed
    if noise_magnitude <= threshold:
        return (base_cfg, False, "Noise magnitude below threshold")

    # Compute the excess ratio: how much the noise exceeds the threshold
    excess_ratio = (noise_magnitude - threshold) / threshold if threshold > 0 else 1.0

    # Compute the scale factor based on mode
    if mode == "linear":
        # Linear reduction: scale_factor = 1 - rescale_strength * min(excess_ratio, 1.0)
        scale_factor = 1.0 - rescale_strength * min(excess_ratio, 1.0)
    elif mode == "exponential":
        # Exponential reduction: scale_factor = exp(-rescale_strength * excess_ratio)
        scale_factor = math.exp(-rescale_strength * excess_ratio)
    else:  # clamp
        # Clamp: if excess_ratio > 1, scale to (1 - rescale_strength), else linear
        if excess_ratio >= 1.0:
            scale_factor = 1.0 - rescale_strength
        else:
            scale_factor = 1.0 - rescale_strength * excess_ratio

    # Ensure scale_factor is in [0, 1]
    scale_factor = max(0.0, min(1.0, scale_factor))

    effective_cfg = base_cfg * scale_factor

    reason = (
        f"Reduced from {base_cfg:.4f} to {effective_cfg:.4f} "
        f"(mode={mode}, excess_ratio={excess_ratio:.4f}, scale_factor={scale_factor:.4f})"
    )

    return (effective_cfg, True, reason)


class PSN_CFG_Rescale_Calculator:
    """
    Calculates a reduced CFG number from base_cfg, a step window and a noise
    magnitude you type in.

    It does not patch a model or run per sampling step: wire its output into
    a sampler's cfg yourself, for the step you want.
    """

    DESCRIPTION = (
        "Computes a reduced CFG number from base_cfg, a step window and a "
        "typed-in noise magnitude. It does not patch a model or run per "
        "sampling step."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "rescale_strength": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "start_step": ("INT", {"default": 10, "min": 0, "max": 10000}),
                "end_step": ("INT", {"default": 50, "min": 0, "max": 10000}),
                "step": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "noise_magnitude": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1e6, "step": 0.001}),
                "threshold": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1e6, "step": 0.001}),
                "mode": (list(_MODES),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("calculated_cfg", "reduction_applied", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        base_cfg: float,
        rescale_strength: float,
        start_step: int,
        end_step: int,
        step: int,
        noise_magnitude: float,
        threshold: float,
        mode: str,
    ) -> tuple[float, bool, str]:
        """
        Compute the reduced CFG value for the given step and noise magnitude.

        Args:
            base_cfg: The initial CFG scale.
            rescale_strength: How aggressively to rescale (0.0 to 1.0).
            start_step: Step index to begin rescaling.
            end_step: Step index to stop rescaling.
            step: Current sampling step index.
            noise_magnitude: Magnitude of the predicted noise.
            threshold: Dynamic threshold for noise magnitude.
            mode: Rescaling mode ("linear", "exponential", "clamp").

        Returns:
            Tuple of (reduced_cfg, reduction_applied, reason).
        """
        return _compute_reduced_cfg(
            base_cfg=base_cfg,
            rescale_strength=rescale_strength,
            step=step,
            start_step=start_step,
            end_step=end_step,
            noise_magnitude=noise_magnitude,
            threshold=threshold,
            mode=mode,
        )


# Module-level mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_CFG_Rescale_Calculator": PSN_CFG_Rescale_Calculator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CFG_Rescale_Calculator": "CFG Rescale Calculator",
}
