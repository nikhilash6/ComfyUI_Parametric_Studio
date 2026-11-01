"""PSN_VRAM_Budget_Compare: compares one number you type against another.

This module compares a VRAM usage value in GB that you (or an upstream node)
supply against a budget value in GB. It does NOT read the GPU, read system
memory, open sockets, or perform any I/O, so it measures nothing: the answer is
only as true as the usage number put in.

Inputs (plain values):
    budget_gb (float, GB) - maximum allowed usage.
    usage_gb (float, GB)  - usage value supplied by you or an upstream node.

Outputs:
    within_budget (bool) - True when usage_gb <= budget_gb.
    message (str)        - text when over budget or on bad input, else "".
"""

import math

CAT = "ParametricStudio/Guard"


def _validate_finite_number(value, name):
    """Return (ok, reason, coerced_value).

    Accepts int/float (not bool), rejects NaN/Inf, and coerces to float.
    """
    if isinstance(value, bool):
        return False, f"{name} must be a number, got bool", None
    if isinstance(value, (int, float)):
        num = float(value)
        if math.isnan(num) or math.isinf(num):
            return False, f"{name} must be finite, got {value!r}", None
        return True, "", num
    if isinstance(value, str):
        try:
            num = float(value.strip())
        except (ValueError, AttributeError):
            return False, f"{name} could not be parsed as a number: {value!r}", None
        if math.isnan(num) or math.isinf(num):
            return False, f"{name} must be finite, got {value!r}", None
        return True, "", num
    return False, f"{name} must be a number, got {type(value).__name__}", None


class PSN_VRAM_Budget_Compare:
    """Compare a typed VRAM usage number against a typed budget number. Reads no GPU."""

    DESCRIPTION = "Compares a usage number you type against a budget number you type; reads no GPU."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "budget_gb": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 1e9, "step": 0.1}),
                "usage_gb": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("within_budget", "message")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, budget_gb, usage_gb):
        ok_t, why_t, thr = _validate_finite_number(budget_gb, "budget_gb")
        if not ok_t:
            return (False, f"Invalid input: {why_t}")

        ok_u, why_u, usage = _validate_finite_number(usage_gb, "usage_gb")
        if not ok_u:
            return (False, f"Invalid input: {why_u}")

        if thr < 0.0:
            return (False, f"Invalid input: budget_gb must be >= 0, got {thr}")
        if usage < 0.0:
            return (False, f"Invalid input: usage_gb must be >= 0, got {usage}")

        if usage > thr:
            message = (
                f"usage {usage:.3f} GB (as given) exceeds budget {thr:.3f} GB "
                f"(over by {usage - thr:.3f} GB)."
            )
            return (False, message)

        return (True, "")


NODE_CLASS_MAPPINGS = {
    "PSN_VRAM_Budget_Compare": PSN_VRAM_Budget_Compare,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAM_Budget_Compare": "VRAM Budget Compare (typed numbers, reads no GPU)",
}
