"""PSN_ValueAnimationMask: Creates masks from how much brightness or colour changes between frames.

This module implements the pure-logic portion of the ValueAnimationMask node.
It works with plain Python lists representing pixel data (no torch, no ComfyUI imports).

Data representation:
- video: list of frames, where each frame is a list of rows, each row is a list of
  pixels, and each pixel is a list of channel values (e.g., [R, G, B] or [L]).
- value_mask: list of frames, where each frame is a list of rows, each row is a list
  of 0.0 or 1.0 values indicating whether the pixel's value changed by at least the
  threshold since the previous frame.

For every pixel a value is computed: for "brightness" mode the mean of all channels,
for "color" mode the maximum channel deviation from the mean (saturation-like measure).
The mask for frame i (i > 0) is 1.0 where abs(value_i - value_{i-1}) >= threshold.
Frame 0 has no previous frame, so its change is 0.0 everywhere (the mask is all 0.0
unless threshold is 0.0).

Inputs:
- video (list): batch of frames as nested lists of pixel channel values
- value_type (str): "brightness" or "color"
- threshold (float): minimum frame-to-frame change for mask activation

Outputs:
- value_mask (list): batch of masks as nested lists of 0.0/1.0 values
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Video"

# Allowed value types
_VALUE_TYPES = ["brightness", "color"]


def _compute_brightness(pixel):
    """Compute brightness (mean of all channels) for a single pixel.

    Args:
        pixel: list of channel values (e.g., [R, G, B])

    Returns:
        float: mean of all channel values
    """
    if not pixel:
        return 0.0
    return sum(pixel) / len(pixel)


def _compute_color_deviation(pixel):
    """Compute color deviation (max deviation from mean) for a single pixel.

    This measures how 'colorful' a pixel is by looking at the maximum
    deviation of any channel from the mean channel value.

    Args:
        pixel: list of channel values (e.g., [R, G, B])

    Returns:
        float: maximum absolute deviation from the mean
    """
    if not pixel:
        return 0.0
    mean_val = sum(pixel) / len(pixel)
    max_dev = 0.0
    for ch in pixel:
        dev = abs(ch - mean_val)
        if dev > max_dev:
            max_dev = dev
    return max_dev


def _analyze_frame(frame, value_type):
    """Analyze a single frame and return a 2D list of value metrics.

    Args:
        frame: list of rows, each row is a list of pixels (each pixel is a list of channels)
        value_type: "brightness" or "color"

    Returns:
        list: 2D list of float values (one per pixel)
    """
    if value_type == "brightness":
        func = _compute_brightness
    elif value_type == "color":
        func = _compute_color_deviation
    else:
        raise ValueError("value_type must be 'brightness' or 'color'")

    result = []
    for row in frame:
        result_row = []
        for pixel in row:
            result_row.append(func(pixel))
        result.append(result_row)
    return result


def _frame_change(prev_values, cur_values):
    """Per-pixel absolute change between two 2D lists of values.

    With no previous frame (None) the change is 0.0 everywhere.
    """
    if prev_values is None:
        return [[0.0 for _ in row] for row in cur_values]
    if len(prev_values) != len(cur_values) or any(len(p) != len(c) for p, c in zip(prev_values, cur_values)):
        raise ValueError("all frames must have the same height and width")
    return [[abs(c - p) for p, c in zip(prow, crow)] for prow, crow in zip(prev_values, cur_values)]


def _apply_threshold(values_2d, threshold):
    """Apply threshold to a 2D list of values, producing a binary mask.

    Args:
        values_2d: 2D list of float values
        threshold: float threshold

    Returns:
        list: 2D list of 0.0 or 1.0 values
    """
    mask = []
    for row in values_2d:
        mask_row = []
        for val in row:
            mask_row.append(1.0 if val >= threshold else 0.0)
        mask.append(mask_row)
    return mask


class PSN_ValueAnimationMask:
    """Creates masks from the frame-to-frame change in brightness or colour.

    Computes a value per pixel, takes the absolute difference from the previous
    frame, and marks pixels whose change reaches the threshold. Frame 0 has no
    previous frame. Works with plain Python lists representing pixel data.
    """

    DESCRIPTION = (
        "Masks of pixels whose brightness or colour changed by at least the threshold since the previous frame; "
        "frame 0 has no previous frame so its change is zero."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("LIST", {"default": []}),
                "value_type": (_VALUE_TYPES,),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("value_mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, video, value_type, threshold):
        """Analyze video frames and generate frame-to-frame change masks.

        Args:
            video: list of frames; each frame is a list of rows; each row is a list
                   of pixels; each pixel is a list of channel values (floats 0.0-1.0)
            value_type: "brightness" or "color"
            threshold: float threshold for mask activation

        Returns:
            tuple: (value_mask,) where value_mask is a list of frames; each frame is
                   a list of rows; each row is a list of 0.0 or 1.0 values
        """
        # Validate value_type
        if value_type not in _VALUE_TYPES:
            raise ValueError("value_type must be one of: {}".format(_VALUE_TYPES))

        # Validate threshold
        if not isinstance(threshold, (int, float)):
            raise TypeError("threshold must be a number")
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")

        # Validate video structure
        if not isinstance(video, list):
            raise TypeError("video must be a list of frames")

        value_mask = []
        prev_values = None
        for frame in video:
            if not isinstance(frame, list):
                raise TypeError("each frame must be a list of rows")
            frame_values = _analyze_frame(frame, value_type)
            change = _frame_change(prev_values, frame_values)
            value_mask.append(_apply_threshold(change, threshold))
            prev_values = frame_values

        return (value_mask,)


NODE_CLASS_MAPPINGS = {
    "PSN_ValueAnimationMask": PSN_ValueAnimationMask,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ValueAnimationMask": "Value Animation Mask",
}
