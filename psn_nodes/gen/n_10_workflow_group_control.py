"""ParametricStudio - Workflow Group Control.

PSN_Group_Bypass turns a group name and an enabled flag into a single
BOOLEAN (True when the group is disabled).  It only emits that value.  There
is no node here that gates or disables other nodes: a node cannot stop
upstream nodes from running.  To disable a branch use ComfyUI's own
bypass/mute, or a switch node with lazy inputs.

No external dependencies beyond torch (CPU) and the Python stdlib.
"""

import torch

CAT = "ParametricStudio/GroupControl"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _as_bool(value):
    """Coerce a value to a strict Python bool (rejects ambiguous inputs)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value in (0, 1):
            return bool(value)
        raise ValueError("bypass_signal must be 0/1 or a bool, got %r" % (value,))
    if isinstance(value, torch.Tensor):
        if value.numel() != 1:
            raise ValueError("bypass_signal tensor must be a scalar")
        v = value.item()
        if v in (0, 1):
            return bool(v)
        raise ValueError("bypass_signal tensor must be 0/1, got %r" % (v,))
    raise TypeError("bypass_signal must be bool/0/1, got %s" % type(value).__name__)


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

class PSN_Group_Bypass:
    """Emit a bypass signal for a named workflow group.

    The output is True when `enabled` is False and False when `enabled` is
    True.  It is only a boolean value; wiring it somewhere does not stop any
    node from running.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "group_id": ("STRING", {"default": "group_a", "multiline": False}),
                "enabled": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("bypass_signal",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, group_id, enabled):
        if not isinstance(group_id, str):
            raise TypeError("group_id must be a string")
        if not group_id.strip():
            raise ValueError("group_id must be a non-empty string")
        enabled = _as_bool(enabled)
        # bypass = group is disabled
        return (not enabled,)


NODE_CLASS_MAPPINGS = {
    "PSN_Group_Bypass": PSN_Group_Bypass,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Group_Bypass": "Group Bypass (ParametricStudio)",
}
