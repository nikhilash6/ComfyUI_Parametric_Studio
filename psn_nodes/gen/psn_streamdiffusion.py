"""PSN_StreamDiffusion: step-counter and noise-level schedule bookkeeping for a StreamDiffusion-style loop.

This module runs no model. It does not denoise, decode or produce any image, and it
touches no GPU or ComfyUI tensor. It manages a JSON-serializable "stream_state"
dictionary holding a step counter, the chosen noise-level schedule and a prompt
history, and validates every step.

The node wrappers take plain values (numbers, strings, JSON text) and return
plain values (numbers, strings, dicts). No sockets, no files, no network, no
subprocess, no eval/exec.

Data flow:
    PSN_Stream_Init -> PSN_Stream_Schedule_Step (looped)

PSN_Stream_Schedule_Step emits a JSON status text (step index, noise level on the
schedule, whether the schedule is used up). It is not an image.
"""

import json
import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Allowed modes for the incremental schedule
_SCHEDULE_MODES = ("linear", "cosine", "exponential")

# Maximum number of history entries kept, to prevent unbounded memory
_MAX_HISTORY_ENTRIES = 1024

# Maximum allowed steps to prevent runaway loops
_MAX_STEPS = 1024

# Minimum / maximum guidance scale
_MIN_GUIDANCE = 0.0
_MAX_GUIDANCE = 100.0

# Minimum / maximum steps
_MIN_STEPS = 1
_MAX_STEPS_ALLOWED = 1024

# ---------------------------------------------------------------------------
# Internal helpers (pure logic only)
# ---------------------------------------------------------------------------


def _validate_steps(steps):
    """Validate and clamp steps to a safe integer range."""
    if not isinstance(steps, int):
        raise ValueError("steps must be an integer")
    if steps < _MIN_STEPS or steps > _MAX_STEPS_ALLOWED:
        raise ValueError(
            "steps must be between {} and {}".format(_MIN_STEPS, _MAX_STEPS_ALLOWED)
        )
    return steps


def _validate_guidance(guidance_scale):
    """Validate guidance scale is a finite float in the allowed range."""
    if not isinstance(guidance_scale, (int, float)):
        raise ValueError("guidance_scale must be a number")
    if isinstance(guidance_scale, float) and (math.isnan(guidance_scale) or math.isinf(guidance_scale)):
        raise ValueError("guidance_scale must be a finite number")
    g = float(guidance_scale)
    if g < _MIN_GUIDANCE or g > _MAX_GUIDANCE:
        raise ValueError(
            "guidance_scale must be between {} and {}".format(_MIN_GUIDANCE, _MAX_GUIDANCE)
        )
    return g


def _validate_prompt(prompt):
    """Validate prompt is a non-empty string of reasonable length."""
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    if len(prompt) == 0:
        raise ValueError("prompt must not be empty")
    if len(prompt) > 4096:
        raise ValueError("prompt must be at most 4096 characters")
    return prompt


def _compute_noise_level(step_index, total_steps, mode):
    """Compute the noise level for a given step index using the chosen schedule.

    Returns a float in [0.0, 1.0] where 1.0 is fully noisy and 0.0 is clean.
    """
    if total_steps <= 0:
        raise ValueError("total_steps must be positive")
    if step_index < 0 or step_index >= total_steps:
        raise ValueError("step_index out of range")

    t = step_index / float(total_steps)  # 0.0 .. <1.0

    if mode == "linear":
        return 1.0 - t
    elif mode == "cosine":
        # Cosine schedule: starts high, ends low
        return 0.5 * (1.0 + math.cos(math.pi * t))
    elif mode == "exponential":
        # Exponential decay
        return math.exp(-3.0 * t)
    else:
        raise ValueError("unknown schedule mode: {}".format(mode))


def _make_state(steps, guidance_scale, schedule_mode):
    """Create a fresh stream state dictionary."""
    _validate_steps(steps)
    _validate_guidance(guidance_scale)
    if schedule_mode not in _SCHEDULE_MODES:
        raise ValueError("schedule_mode must be one of {}".format(_SCHEDULE_MODES))

    state = {
        "steps": int(steps),
        "guidance_scale": float(guidance_scale),
        "schedule_mode": schedule_mode,
        "current_step": 0,
        "completed": False,
        "history": [],
    }
    return state


def _step_state(state, prompt, image_json=None):
    """Advance the step counter and read the noise level for that step.

    Returns (status_json, updated_state). Nothing is denoised.
    """
    if not isinstance(state, dict):
        raise ValueError("stream_state must be a dict")

    required_keys = {"steps", "guidance_scale", "schedule_mode", "current_step", "completed", "history"}
    missing = required_keys - set(state.keys())
    if missing:
        raise ValueError("stream_state missing keys: {}".format(sorted(missing)))

    if state["completed"]:
        raise ValueError("stream is already completed; call PSN_Stream_Init to reset")

    prompt = _validate_prompt(prompt)

    current = int(state["current_step"])
    total = int(state["steps"])
    mode = state["schedule_mode"]

    if current >= total:
        raise ValueError("current_step {} >= total steps {}".format(current, total))

    noise_level = _compute_noise_level(current, total, mode)

    new_step = current + 1
    completed = new_step >= total

    history = list(state["history"])
    history.append({
        "step": current,
        "noise_level": round(noise_level, 6),
        "prompt": prompt,
    })
    # Keep history bounded
    if len(history) > _MAX_HISTORY_ENTRIES:
        history = history[-_MAX_HISTORY_ENTRIES:]

    new_state = {
        "steps": total,
        "guidance_scale": float(state["guidance_scale"]),
        "schedule_mode": mode,
        "current_step": new_step,
        "completed": completed,
        "history": history,
    }

    # Status text only: where the counter and schedule are. No pixels.
    status_payload = {
        "step": current,
        "total_steps": total,
        "noise_level": round(noise_level, 6),
        "guidance_scale": float(state["guidance_scale"]),
        "schedule_mode": mode,
        "prompt": prompt,
        "has_image_input": bool(image_json),
        "schedule_finished": completed,
    }
    status_json = json.dumps(status_payload, sort_keys=True)

    return status_json, new_state


# ---------------------------------------------------------------------------
# Node classes
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/StreamDiffusion"


class PSN_Stream_Init:
    """Initialize a StreamDiffusion-style step-schedule state.

    Creates a JSON-serializable state dict holding the step count, schedule
    mode, guidance scale value and a prompt history. Runs no model, no GPU work.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 4, "min": _MIN_STEPS, "max": _MAX_STEPS_ALLOWED, "step": 1}),
                "guidance_scale": ("FLOAT", {"default": 1.0, "min": _MIN_GUIDANCE, "max": _MAX_GUIDANCE, "step": 0.1}),
                "schedule_mode": (list(_SCHEDULE_MODES),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("stream_state",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, steps, guidance_scale, schedule_mode):
        state = _make_state(steps, guidance_scale, schedule_mode)
        return (state,)


class PSN_Stream_Schedule_Step:
    """Advance a step counter and noise-level schedule; emit a JSON status.

    Does not denoise and does not produce an image. It moves the stream state
    forward by one step, reads the noise level for that step from the chosen
    schedule, and returns that as JSON text plus the updated state.
    """

    DESCRIPTION = (
        "Advances a StreamDiffusion-style step counter and noise-level schedule and emits a JSON status; "
        "does not denoise or produce an image."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "stream_state": ("DICT",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "image": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "DICT")
    RETURN_NAMES = ("step_status_json", "stream_state")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, stream_state, prompt, image=None):
        status_json, new_state = _step_state(stream_state, prompt, image)
        return (status_json, new_state)


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Stream_Init": PSN_Stream_Init,
    "PSN_Stream_Schedule_Step": PSN_Stream_Schedule_Step,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Stream_Init": "PSN Stream Init",
    "PSN_Stream_Schedule_Step": "PSN Stream Step Counter and Noise Schedule (no denoising)",
}
