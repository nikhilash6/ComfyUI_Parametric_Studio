"""
PSN Matrix-Game parameter check (pure logic)

This module checks the shape of a model path string and a device string. It does
NOT load models, look for the path on disk, access the network, open files, or
use GPU/torch/ComfyUI internals. It generates no video.

PSN_MatrixGame_ParamCheck: validates the model_path and device strings only and
returns them as a small dict with a status string.

All functions take plain values (strings) and return plain values. No side
effects, no I/O, no external dependencies.
"""

# Allowed devices for model loading
ALLOWED_DEVICES = ["cuda", "cpu"]


def _validate_model_path(model_path: str) -> tuple[bool, str]:
    """
    Validate model path string.
    Returns (is_valid, reason).
    """
    if not isinstance(model_path, str):
        return False, "model_path must be a string"
    if not model_path.strip():
        return False, "model_path cannot be empty"
    # Basic sanity: no null bytes, reasonable length
    if "\x00" in model_path:
        return False, "model_path contains null bytes"
    if len(model_path) > 512:
        return False, "model_path too long"
    # Disallow path traversal patterns (basic check)
    if ".." in model_path:
        return False, "model_path contains path traversal"
    return True, "ok"


def _validate_device(device: str) -> tuple[bool, str]:
    """
    Validate device string.
    Returns (is_valid, reason).
    """
    if not isinstance(device, str):
        return False, "device must be a string"
    if device not in ALLOWED_DEVICES:
        return False, f"device must be one of {ALLOWED_DEVICES}"
    return True, "ok"


class PSN_MatrixGame_ParamCheck:
    """
    Checks that a model path string and a device string are well-formed.
    Loads nothing and does not look for the path on disk.
    """

    DESCRIPTION = ("Validates the model_path and device strings only and returns them as a dict. "
                   "It loads nothing and does not check that the file exists.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_path": ("STRING", {"default": "models/matrix_game_17b.safetensors", "multiline": False}),
                "device": (ALLOWED_DEVICES,),
            }
        }

    RETURN_TYPES = ("DICT", "STRING")
    RETURN_NAMES = ("checked_params", "check_status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/MatrixGame"

    def run(self, model_path: str, device: str) -> tuple[dict, str]:
        """
        Validate inputs and return the checked values and a status string.
        """
        path_ok, path_reason = _validate_model_path(model_path)
        if not path_ok:
            return ({"error": path_reason}, f"FAIL: {path_reason}")

        dev_ok, dev_reason = _validate_device(device)
        if not dev_ok:
            return ({"error": dev_reason}, f"FAIL: {dev_reason}")

        params = {"model_path": model_path, "device": device}
        return (params, "OK: strings are well-formed (path not checked on disk, nothing loaded)")


NODE_CLASS_MAPPINGS = {
    "PSN_MatrixGame_ParamCheck": PSN_MatrixGame_ParamCheck,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MatrixGame_ParamCheck": "MatrixGame Parameter Check (loads nothing)",
}
