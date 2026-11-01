"""
PSN Conditioning Subtraction and Number-List Clamp Nodes.

Nodes:
1. PSN_Conditioning_Subtract: takes two CONDITIONING inputs and returns the
   base conditioning with the first tensor of the subtract conditioning
   (times ``strength``, optionally scaled to the base's norm) taken away from
   every base entry, using torch.  Shapes must match.
2. PSN_Number_List_Clamp: clamps a JSON list of numbers with a linear or tanh
   method.  It works on plain numbers and does not touch CONDITIONING tensors.
"""

import math
import json

import torch

# Define the category for these nodes
CAT = "ParametricStudio/Semantic"

def _subtract_conditioning(base, subtract, strength, auto_scale):
    """Return a new CONDITIONING: every base tensor minus subtract[0][0] * k.

    k is ``strength``; with auto_scale it is multiplied by the ratio of the
    base tensor's L2 norm to the subtract tensor's L2 norm.  Inputs are not
    modified.  Tensor shapes must match.
    """
    if not base or not subtract:
        raise ValueError("base and subtract conditioning must not be empty")
    sub = subtract[0][0]
    out = []
    for tensor, opts in base:
        if tensor.shape != sub.shape:
            raise ValueError("conditioning shapes must match: %s vs %s" % (tuple(tensor.shape), tuple(sub.shape)))
        s = sub.to(device=tensor.device, dtype=tensor.dtype)
        k = float(strength)
        if auto_scale:
            sub_norm = torch.linalg.vector_norm(s.float()).item()
            if sub_norm > 0:
                k *= torch.linalg.vector_norm(tensor.float()).item() / sub_norm
        out.append([tensor - s * k, dict(opts)])
    return out

# Helper function to clamp values
def _clamp_vector(vec, min_val, max_val, method):
    if min_val > max_val:
        raise ValueError("min_val must be less than or equal to max_val")
    
    clamped = []
    for v in vec:
        if method == "linear":
            # Hard clamp
            if v < min_val:
                clamped.append(min_val)
            elif v > max_val:
                clamped.append(max_val)
            else:
                clamped.append(v)
        elif method == "tanh":
            # Smooth clamp using tanh
            # Map the range [min_val, max_val] to a smooth transition
            # We use a scaled tanh to approximate clamping
            # Center the range
            center = (min_val + max_val) / 2.0
            half_range = (max_val - min_val) / 2.0
            
            if half_range == 0:
                clamped.append(center)
            else:
                # Normalize to [-1, 1]
                normalized = (v - center) / half_range
                # Apply tanh to smooth the edges
                smoothed = math.tanh(normalized)
                # Map back to [min_val, max_val]
                clamped.append(center + smoothed * half_range)
        else:
            raise ValueError(f"Unknown clamp method: {method}")
    return clamped

def _parse_vector_json(json_str):
    """
    Safely parses a JSON string representing a list of numbers.
    Returns a list of floats.
    """
    if not json_str or not json_str.strip():
        return []
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    if not isinstance(data, list):
        raise ValueError("Parsed JSON must be a list")
    
    # Ensure all elements are numbers
    parsed_vec = []
    for item in data:
        if isinstance(item, (int, float)):
            parsed_vec.append(float(item))
        else:
            raise ValueError("All elements in the vector must be numbers")
            
    return parsed_vec


class PSN_Conditioning_Subtract:
    """
    Subtracts the first tensor of one CONDITIONING from every entry of another.

    Computes: base - subtract[0][0] * strength. If auto_scale is true, the
    subtraction is scaled so its norm matches the base tensor's norm first.
    """

    DESCRIPTION = ("Subtracts the first tensor of the subtract conditioning, times strength "
                   "(optionally norm-matched to the base), from every base conditioning "
                   "tensor. Tensor shapes must match.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base": ("CONDITIONING",),
                "subtract": ("CONDITIONING",),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
                "auto_scale": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("conditioning",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, base, subtract, strength, auto_scale):
        return (_subtract_conditioning(base, subtract, strength, auto_scale),)


class PSN_Number_List_Clamp:
    """
    Clamps a JSON list of numbers to a range using a linear or tanh method.

    Works on plain numbers; it does not touch CONDITIONING tensors.
    """

    DESCRIPTION = ("Clamps a JSON list of numbers to [min, max] with a linear (hard) or tanh "
                   "(smooth) method. It does not touch CONDITIONING.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_val": ("FLOAT", {"default": -1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "max_val": ("FLOAT", {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "method": (["linear", "tanh"],),
                "vector": ("STRING", {"default": "[]", "multiline": True}),
            }
        }

    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("first_value", "result_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, min_val, max_val, method, vector="[]"):
        vec = _parse_vector_json(vector)
        result_vec = _clamp_vector(vec, min_val, max_val, method)
        first_value = result_vec[0] if result_vec else 0.0
        return (first_value, json.dumps(result_vec))


# Node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_Conditioning_Subtract": PSN_Conditioning_Subtract,
    "PSN_Number_List_Clamp": PSN_Number_List_Clamp,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Conditioning_Subtract": "Conditioning Subtract",
    "PSN_Number_List_Clamp": "Number List Clamp (not conditioning)",
}
