"""PSN_VRAM_Bytes_Check: arithmetic on VRAM byte counts you type.

This module does NOT import torch, does NOT query the GPU, and does NOT perform
any file/network/OS access. It accepts plain numeric inputs (allocated bytes,
reserved bytes, total bytes, required GB, batch size) typed by you or fed in by
an upstream node, and applies this rule:

    If (allocated + required_gb * 1e9) > total_memory * 0.9 -> over budget

Nothing is measured here. If allocated_bytes and reserved_bytes are both 0 (as at
the defaults), no measurement was given and the node says so instead of
reporting that the request fits.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/VRAM"

# Safety margin: we consider VRAM "full" at 90% of total.
_SAFETY_FRACTION = 0.9
# Minimum batch size we allow (0 is meaningless for a batch).
_MIN_BATCH_SIZE = 1
# Maximum batch size we will consider (guards against absurd inputs).
_MAX_BATCH_SIZE = 10_000
# Minimum required GB (negative or zero is meaningless).
_MIN_REQUIRED_GB = 0.0
# Maximum required GB we will consider (guards against absurd inputs).
_MAX_REQUIRED_GB = 1e6


def _validate_inputs(required_gb, current_batch_size, allocated_bytes,
                     reserved_bytes, total_bytes):
    """Validate all numeric inputs. Returns (ok, reason)."""
    # required_gb
    if not isinstance(required_gb, (int, float)) or isinstance(required_gb, bool):
        return False, "required_gb must be a number"
    if required_gb < _MIN_REQUIRED_GB:
        return False, "required_gb must be >= 0"
    if required_gb > _MAX_REQUIRED_GB:
        return False, "required_gb exceeds maximum allowed"

    # current_batch_size
    if not isinstance(current_batch_size, int) or isinstance(current_batch_size, bool):
        return False, "current_batch_size must be an integer"
    if current_batch_size < _MIN_BATCH_SIZE:
        return False, "current_batch_size must be >= 1"
    if current_batch_size > _MAX_BATCH_SIZE:
        return False, "current_batch_size exceeds maximum allowed"

    # allocated_bytes, reserved_bytes, total_bytes
    for name, val in (("allocated_bytes", allocated_bytes),
                      ("reserved_bytes", reserved_bytes),
                      ("total_bytes", total_bytes)):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return False, f"{name} must be a number"
        if val < 0:
            return False, f"{name} must be >= 0"

    if total_bytes <= 0:
        return False, "total_bytes must be > 0"

    if allocated_bytes > total_bytes:
        return False, "allocated_bytes cannot exceed total_bytes"

    if reserved_bytes > total_bytes:
        return False, "reserved_bytes cannot exceed total_bytes"

    return True, "ok"


def _check_vram(required_gb, current_batch_size, allocated_bytes,
                reserved_bytes, total_bytes):
    """Core byte-count check. Returns (fits, message)."""
    ok, why = _validate_inputs(required_gb, current_batch_size,
                               allocated_bytes, reserved_bytes, total_bytes)
    if not ok:
        return False, f"Invalid input: {why}"

    if allocated_bytes == 0 and reserved_bytes == 0:
        return False, (
            "No measurement given: allocated_bytes and reserved_bytes are both 0, "
            "so nothing can be said about whether the request fits"
        )

    required_bytes = required_gb * 1e9
    projected = allocated_bytes + required_bytes
    limit = total_bytes * _SAFETY_FRACTION

    if projected > limit:
        headroom = limit - projected
        return False, (
            f"Over budget: projected {projected:.3e} bytes exceeds "
            f"90% limit {limit:.3e} bytes by {-headroom:.3e} bytes "
            f"(allocated={allocated_bytes:.3e}, required={required_bytes:.3e}, "
            f"total={total_bytes:.3e}, batch={current_batch_size})"
        )

    headroom = limit - projected
    return True, (
        f"Fits: projected {projected:.3e} bytes is within "
        f"90% limit {limit:.3e} bytes (headroom={headroom:.3e} bytes, "
        f"batch={current_batch_size}), going by the numbers given"
    )


class PSN_VRAM_Bytes_Check:
    """Arithmetic check on typed VRAM byte counts. Reads no GPU.

    Inputs are plain numbers. An upstream node (or the user) must supply the
    allocated, reserved and total memory values; this node measures none of them.
    """

    DESCRIPTION = (
        "Arithmetic on allocated, reserved and total bytes you type; reads no GPU. "
        "With allocated and reserved both 0 it reports no measurement given, not a pass."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "required_gb": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1e6, "step": 0.1}),
                "current_batch_size": ("INT", {"default": 1, "min": 1, "max": 10000}),
                "allocated_bytes": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e18, "step": 1.0}),
                "reserved_bytes": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e18, "step": 1.0}),
                "total_bytes": ("FLOAT", {"default": 24e9, "min": 1.0, "max": 1e18, "step": 1.0}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("fits_budget", "message")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, required_gb, current_batch_size, allocated_bytes,
            reserved_bytes, total_bytes):
        fits, message = _check_vram(required_gb, current_batch_size,
                                    allocated_bytes, reserved_bytes,
                                    total_bytes)
        return (fits, message)


NODE_CLASS_MAPPINGS = {
    "PSN_VRAM_Bytes_Check": PSN_VRAM_Bytes_Check,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAM_Bytes_Check": "VRAM Bytes Check (typed numbers, reads no GPU)",
}
