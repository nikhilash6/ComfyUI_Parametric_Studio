"""PSN_Audio_Json_Smooth_Gain_Normalize: moving-average smoothing, per-half gain and
peak normalization on audio samples carried as JSON text.

This is plain-Python arithmetic on a list of samples.  It is NOT a frequency-domain
EQ or a spectral denoiser:

  * audio is passed in as JSON text (a list of float samples, or a dict with a
    "samples" key and optional "sample_rate"),
  * smoothing is a 5-sample moving average in the time domain,
  * the gain stage multiplies the first half of the samples (in time) by one dB
    value and the second half by another; no filtering by frequency happens,
  * normalization scales the peak to 0 dBFS (i.e. peak magnitude == 1.0).

No torch, no ComfyUI imports, no network, no file/OS access, no eval/exec.
All functions take and return plain values (strings, numbers, lists, dicts).
"""

import json
import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Signal"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_audio(audio_json):
    """Parse the audio JSON text into a list of float samples.

    Accepts either a JSON list of numbers or a JSON object with a "samples" key.
    Returns (samples, sample_rate).  Raises ValueError on bad input.
    """
    if not isinstance(audio_json, str):
        raise ValueError("audio must be a JSON string")
    try:
        data = json.loads(audio_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("audio is not valid JSON: %s" % exc)

    if isinstance(data, list):
        samples = data
        sample_rate = 44100
    elif isinstance(data, dict):
        if "samples" not in data:
            raise ValueError("audio dict must contain a 'samples' key")
        samples = data["samples"]
        sample_rate = data.get("sample_rate", 44100)
    else:
        raise ValueError("audio must be a JSON list or object with 'samples'")

    if not isinstance(samples, list):
        raise ValueError("samples must be a list")

    out = []
    for i, s in enumerate(samples):
        if not isinstance(s, (int, float)):
            raise ValueError("sample %d is not a number: %r" % (i, s))
        out.append(float(s))
    return out, float(sample_rate)


def _smooth(samples, window=5):
    """Time-domain moving average (smooths; does not remove noise by frequency)."""
    if len(samples) < window:
        return list(samples)
    out = []
    for i in range(len(samples)):
        lo = max(0, i - window // 2)
        hi = min(len(samples), i + window // 2 + 1)
        chunk = samples[lo:hi]
        out.append(sum(chunk) / len(chunk))
    return out


def _apply_half_gains(samples, gain_first_db, gain_second_db):
    """Gain by position in time, not by frequency.

    The first half of the samples is multiplied by gain_first_db (dB), the
    second half by gain_second_db (dB).
    """
    n = len(samples)
    if n == 0:
        return samples
    mid = n // 2
    g_first = 10.0 ** (gain_first_db / 20.0)
    g_second = 10.0 ** (gain_second_db / 20.0)
    out = list(samples)
    for i in range(mid):
        out[i] = samples[i] * g_first
    for i in range(mid, n):
        out[i] = samples[i] * g_second
    return out


def _normalize(samples):
    """Peak normalization to 0 dBFS (peak magnitude == 1.0)."""
    if not samples:
        return samples
    peak = max(abs(s) for s in samples)
    if peak == 0.0:
        return list(samples)
    scale = 1.0 / peak
    return [s * scale for s in samples]


def _to_json(samples, sample_rate):
    return json.dumps({"samples": samples, "sample_rate": sample_rate})


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_Audio_Json_Smooth_Gain_Normalize:
    """Moving-average smoothing, per-half gain and peak normalization on JSON samples."""

    DESCRIPTION = (
        "Applies a 5-sample moving average, a dB gain to the first half and a "
        "dB gain to the second half of the samples (by time position), and "
        "peak normalization, on audio given as JSON text. It is not a "
        "frequency EQ or a spectral denoiser."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("STRING", {"default": "[]", "multiline": True}),
                "smooth": ("BOOLEAN", {"default": False}),
                "gain_first_half_db": ("FLOAT", {"default": 0.0, "min": -60.0, "max": 60.0, "step": 0.5}),
                "gain_second_half_db": ("FLOAT", {"default": 0.0, "min": -60.0, "max": 60.0, "step": 0.5}),
                "normalize": ("BOOLEAN", {"default": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("processed_audio",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, audio, smooth, gain_first_half_db, gain_second_half_db, normalize):
        samples, sample_rate = _parse_audio(audio)
        if smooth:
            samples = _smooth(samples)
        if gain_first_half_db != 0.0 or gain_second_half_db != 0.0:
            samples = _apply_half_gains(samples, gain_first_half_db, gain_second_half_db)
        if normalize:
            samples = _normalize(samples)
        return (_to_json(samples, sample_rate),)


NODE_CLASS_MAPPINGS = {"PSN_Audio_Json_Smooth_Gain_Normalize": PSN_Audio_Json_Smooth_Gain_Normalize}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Audio_Json_Smooth_Gain_Normalize": "Audio JSON Smooth, Half Gain and Normalize"
}
