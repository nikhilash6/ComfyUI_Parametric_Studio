"""
PSN StyleGAN Explore - latent-vector helpers for StyleGAN2 exploration. Runs no StyleGAN model.

This module holds three plain-Python nodes:
- PSN_StyleGAN_Path_Check: Checks a checkpoint path string's extension. Opens and loads nothing.
- PSN_StyleGAN_Slerp: Performs spherical linear interpolation (slerp) between two latent vectors.
- PSN_StyleGAN_Generate_Spec: Checks latent frame shapes and returns a JSON spec. Generates no image.

NOTE: This implementation does NOT use torch, ComfyUI, or any GPU operations.
It operates on plain Python lists/tuples representing latent vectors.
The slerp function works on 1D vectors (flattened latents) and returns a list of interpolated vectors.
"""

import math
import json

CAT = "ParametricStudio/StyleGAN"

# Allowed model path extensions for validation
ALLOWED_MODEL_EXTENSIONS = (".pt", ".pth", ".ckpt", ".bin")


def _validate_model_path(model_path):
    """Validate that model_path is a string with an allowed extension."""
    if not isinstance(model_path, str):
        return False, "model_path must be a string"
    if not model_path:
        return False, "model_path must not be empty"
    # Check extension
    lower_path = model_path.lower()
    if not any(lower_path.endswith(ext) for ext in ALLOWED_MODEL_EXTENSIONS):
        return False, f"model_path must end with one of {ALLOWED_MODEL_EXTENSIONS}"
    return True, "valid"


def _slerp_single(v1, v2, t):
    """
    Perform slerp between two 1D vectors v1 and v2 at parameter t.
    Returns a list of floats.
    """
    n = len(v1)
    if n != len(v2):
        raise ValueError("Vectors must have the same length")
    
    # Compute dot product
    dot = sum(a * b for a, b in zip(v1, v2))
    
    # Compute norms
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    
    # Handle edge cases
    if norm1 < 1e-10 or norm2 < 1e-10:
        # If either vector is near zero, fall back to linear interpolation
        return [a + t * (b - a) for a, b in zip(v1, v2)]
    
    # Normalize dot product
    dot = max(-1.0, min(1.0, dot / (norm1 * norm2)))
    
    theta = math.acos(dot)
    
    if theta < 1e-10:
        # Vectors are nearly parallel, use linear interpolation
        return [a + t * (b - a) for a, b in zip(v1, v2)]
    
    sin_theta = math.sin(theta)
    
    # Slerp formula
    result = []
    for a, b in zip(v1, v2):
        coeff1 = math.sin((1 - t) * theta) / sin_theta
        coeff2 = math.sin(t * theta) / sin_theta
        result.append(coeff1 * a + coeff2 * b)
    
    return result


def _slerp_sequence(latent_a, latent_b, num_frames, t_start, t_end):
    """
    Generate a sequence of slerp-interpolated vectors between latent_a and latent_b.
    
    Args:
        latent_a: list of floats (1D vector)
        latent_b: list of floats (1D vector)
        num_frames: int, number of frames to generate
        t_start: float, starting parameter (0.0)
        t_end: float, ending parameter (1.0)
    
    Returns:
        list of lists, each inner list is a 1D vector
    """
    if num_frames < 1:
        raise ValueError("num_frames must be at least 1")
    
    frames = []
    for i in range(num_frames):
        if num_frames == 1:
            t = t_start
        else:
            t = t_start + (t_end - t_start) * i / (num_frames - 1)
        frames.append(_slerp_single(latent_a, latent_b, t))
    
    return frames


class PSN_StyleGAN_Path_Check:
    """
    Checks that a StyleGAN2 checkpoint path string ends in an allowed extension.
    Does not open the file, load a model or check that the file exists.
    """

    DESCRIPTION = "Validates a StyleGAN checkpoint path string (extension only); loads nothing and does not check the file exists."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_path": ("STRING", {"default": "stylegan2.pt", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("path_check_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_path):
        valid, reason = _validate_model_path(model_path)
        if not valid:
            raise ValueError(f"Invalid model path: {reason}")

        result = json.dumps({
            "path": model_path,
            "extension_ok": True,
            "file_opened": False,
        })
        return (result,)


class PSN_StyleGAN_Slerp:
    """
    Performs spherical linear interpolation (slerp) between two latent vectors.
    Input latents are expected as JSON strings representing 1D vectors (lists of floats).
    Output is a JSON string representing a list of interpolated vectors.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent_a": ("STRING", {"default": "[1.0, 0.0, 0.0]", "multiline": False}),
                "latent_b": ("STRING", {"default": "[0.0, 1.0, 0.0]", "multiline": False}),
                "num_frames": ("INT", {"default": 10, "min": 1, "max": 1000, "step": 1}),
                "t_start": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "t_end": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("latents",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, latent_a, latent_b, num_frames, t_start, t_end):
        # Parse JSON vectors
        try:
            vec_a = json.loads(latent_a)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("latent_a must be a valid JSON array of numbers")
        
        try:
            vec_b = json.loads(latent_b)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("latent_b must be a valid JSON array of numbers")
        
        # Validate vectors
        if not isinstance(vec_a, list) or not all(isinstance(x, (int, float)) for x in vec_a):
            raise ValueError("latent_a must be a JSON array of numbers")
        if not isinstance(vec_b, list) or not all(isinstance(x, (int, float)) for x in vec_b):
            raise ValueError("latent_b must be a JSON array of numbers")
        if len(vec_a) != len(vec_b):
            raise ValueError("latent_a and latent_b must have the same length")
        if len(vec_a) == 0:
            raise ValueError("Latent vectors must not be empty")
        
        # Validate t range
        if t_start < 0.0 or t_start > 1.0:
            raise ValueError("t_start must be between 0.0 and 1.0")
        if t_end < 0.0 or t_end > 1.0:
            raise ValueError("t_end must be between 0.0 and 1.0")
        
        # Perform slerp
        frames = _slerp_sequence(vec_a, vec_b, num_frames, t_start, t_end)
        
        # Return as JSON string
        return (json.dumps(frames),)


class PSN_StyleGAN_Generate_Spec:
    """
    Checks the shape of a list of latent vectors and returns a JSON spec of them.
    Generates no image: no StyleGAN model runs.
    """

    DESCRIPTION = "Builds a generation spec (frame count and latent size) from latent vectors; generates no image."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path_check_json": ("STRING", {"default": "{}", "multiline": False}),
                "latents": ("STRING", {"default": "[]", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("generation_spec_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, path_check_json, latents):
        # Validate the path-check JSON
        try:
            model_data = json.loads(path_check_json)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("path_check_json must be a valid JSON object")

        if not isinstance(model_data, dict):
            raise ValueError("path_check_json must be a JSON object")

        # Validate latents
        try:
            latent_frames = json.loads(latents)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("latents must be a valid JSON array")

        if not isinstance(latent_frames, list):
            raise ValueError("latents must be a JSON array")

        if len(latent_frames) == 0:
            raise ValueError("latents must contain at least one frame")

        # Validate each frame is a list of numbers of the same length
        for i, frame in enumerate(latent_frames):
            if not isinstance(frame, list):
                raise ValueError(f"Frame {i} must be a JSON array of numbers")
            if not all(isinstance(x, (int, float)) for x in frame):
                raise ValueError(f"Frame {i} must contain only numbers")
            if len(frame) != len(latent_frames[0]):
                raise ValueError(f"Frame {i} has a different length from frame 0")

        spec = json.dumps({
            "model_path": model_data.get("path"),
            "num_frames": len(latent_frames),
            "latent_dim": len(latent_frames[0]),
        })
        return (spec,)


NODE_CLASS_MAPPINGS = {
    "PSN_StyleGAN_Path_Check": PSN_StyleGAN_Path_Check,
    "PSN_StyleGAN_Slerp": PSN_StyleGAN_Slerp,
    "PSN_StyleGAN_Generate_Spec": PSN_StyleGAN_Generate_Spec,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_StyleGAN_Path_Check": "PSN StyleGAN Checkpoint Path Check (loads nothing)",
    "PSN_StyleGAN_Slerp": "PSN StyleGAN Slerp",
    "PSN_StyleGAN_Generate_Spec": "PSN StyleGAN Generation Spec (makes no image)",
}
