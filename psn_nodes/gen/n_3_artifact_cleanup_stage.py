"""PSN_NAFNet_Config_Check: validates NAFNet denoise settings for the Artifact Cleanup pipeline.

This module only checks configuration.  It takes no image, runs no NAFNet model and
denoises nothing.  It does not import torch, torchvision, or any ComfyUI internals,
and it performs no network, file, or OS access.  It:

  * validates the noise level (a number in 0..1),
  * checks the model name against an allow-list of NAFNet variants (the weights
    are not looked for or loaded),
  * validates image metadata (width, height, channels) given as JSON text, and
  * reports pass/fail with a human-readable reason and the normalized settings.
"""

import json

# Allow-list of supported NAFNet model variants (secure-by-design: reject unknowns).
ALLOWED_MODELS = ("nafnet_srgb", "nafnet_yuv", "nafnet_gray")

# Bounds for the noise level parameter.
NOISE_MIN = 0.0
NOISE_MAX = 1.0

# Image metadata bounds.
DIM_MIN = 1
DIM_MAX = 4096
CHANNELS_MIN = 1
CHANNELS_MAX = 4


def _validate_noise_level(noise_level):
    """Return (ok, reason). noise_level must be a finite number in [NOISE_MIN, NOISE_MAX]."""
    if not isinstance(noise_level, (int, float)) or isinstance(noise_level, bool):
        return False, "noise_level must be a number"
    if noise_level != noise_level:  # NaN check
        return False, "noise_level must be finite"
    if noise_level < NOISE_MIN or noise_level > NOISE_MAX:
        return False, "noise_level out of range [%.1f, %.1f]" % (NOISE_MIN, NOISE_MAX)
    return True, "ok"


def _validate_model_path(model_path):
    """Return (ok, reason). model_path must be a non-empty string in the allow-list."""
    if not isinstance(model_path, str):
        return False, "model_path must be a string"
    if not model_path.strip():
        return False, "model_path must be non-empty"
    if model_path not in ALLOWED_MODELS:
        return False, "model_path not in allow-list: %s" % (", ".join(ALLOWED_MODELS))
    return True, "ok"


def _validate_image_meta(image_meta):
    """Return (ok, reason, normalized_meta). image_meta is a JSON text object with
    width, height, channels. All must be ints within bounds."""
    if not isinstance(image_meta, str):
        return False, "image_meta must be a JSON string", None
    try:
        data = json.loads(image_meta)
    except (ValueError, TypeError):
        return False, "image_meta is not valid JSON", None
    if not isinstance(data, dict):
        return False, "image_meta must be a JSON object", None
    meta = {}
    for key in ("width", "height", "channels"):
        val = data.get(key)
        if not isinstance(val, int) or isinstance(val, bool):
            return False, "image_meta.%s must be an integer" % key, None
        if key == "channels":
            lo, hi = CHANNELS_MIN, CHANNELS_MAX
        else:
            lo, hi = DIM_MIN, DIM_MAX
        if val < lo or val > hi:
            return False, "image_meta.%s out of range [%d, %d]" % (key, lo, hi), None
        meta[key] = val
    return True, "ok", meta


def validate_denoise_config(noise_level, model_path, image_meta):
    """Validate the settings and return their normalized form.

    Returns (ok, reason, config). config is a dict (or None) with:
      model_path, noise_level, width, height, channels.
    """
    ok, why = _validate_noise_level(noise_level)
    if not ok:
        return False, why, None
    ok, why = _validate_model_path(model_path)
    if not ok:
        return False, why, None
    ok, why, meta = _validate_image_meta(image_meta)
    if not ok:
        return False, why, None

    config = {
        "model_path": model_path,
        "noise_level": float(noise_level),
        "width": meta["width"],
        "height": meta["height"],
        "channels": meta["channels"],
    }
    return True, "ok", config


CAT = "ParametricStudio/ArtifactCleanup"


class PSN_NAFNet_Config_Check:
    """Check NAFNet model name, noise level and image-size settings; denoise nothing.

    No image input, no model run, no GPU, no I/O. Takes plain values, returns
    plain values (a boolean, a reason string, and the normalized settings as JSON).
    """

    DESCRIPTION = ("Validates a NAFNet model name, noise level and image width/height/channels "
                   "and returns the normalized settings as JSON. It takes no image, runs no "
                   "model and denoises nothing.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "noise_level": ("FLOAT", {"default": 0.1, "min": NOISE_MIN, "max": NOISE_MAX, "step": 0.01}),
                "model_path": (list(ALLOWED_MODELS),),
                "image_meta": ("STRING", {"default": '{"width": 512, "height": 512, "channels": 3}', "multiline": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("ok", "reason", "config_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, noise_level, model_path, image_meta):
        ok, reason, config = validate_denoise_config(noise_level, model_path, image_meta)
        config_json = json.dumps(config) if config is not None else ""
        return (ok, reason, config_json)


NODE_CLASS_MAPPINGS = {
    "PSN_NAFNet_Config_Check": PSN_NAFNet_Config_Check,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_NAFNet_Config_Check": "NAFNet Settings Check (denoises nothing)",
}
