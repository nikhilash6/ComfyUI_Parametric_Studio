"""
PSN Audio Notification cue selector (pure-logic, secure-by-design).

This module PLAYS NOTHING and ships no audio. The WAV files named below are
not part of this repository; the paths are only the names a player would look
for. It does no audio playback, file I/O, or OS access. It:
- Validates the requested `sound_type` against an allow-list.
- Validates the `volume` range.
- Returns the expected asset path (a string, never opened) for the cue.
- Returns a `valid` boolean and a human-readable `reason` string.

It never opens a socket, never reads/writes files, and never imports audio
libraries.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Audio"

# Allow-list of supported sound cues and the asset path a player would use.
# The files are not shipped here; paths are returned as strings only and never
# opened.
_SOUND_ASSETS = {
    "success": "assets/sounds/success.wav",
    "error": "assets/sounds/error.wav",
    "info": "assets/sounds/info.wav",
}

_SOUND_TYPES = list(_SOUND_ASSETS.keys())


def _select_asset(sound_type: str) -> str:
    """Return the expected asset path for a valid sound_type, or raise ValueError."""
    if sound_type not in _SOUND_ASSETS:
        raise ValueError(f"Unknown sound_type: {sound_type!r}. Allowed: {_SOUND_TYPES}")
    return _SOUND_ASSETS[sound_type]


def _validate_volume(volume: float) -> bool:
    """Return True if volume is within [0.0, 1.0]."""
    return 0.0 <= volume <= 1.0


class PSN_Notif_Select:
    """
    Picks a cue name and its expected asset path from an allow-list and checks
    the volume. Plays nothing and ships no audio.

    Inputs:
        sound_type: One of "success", "error", "info".
        volume:     Intended volume in [0.0, 1.0] (only range-checked).

    Outputs:
        valid:               True if the sound_type is allowed and volume is in range.
        expected_asset_path: Path a player would use for the cue (file not shipped).
        reason:              Human-readable explanation of the check.
    """

    DESCRIPTION = ("Picks a notification cue name and expected file path from "
                   "an allow-list and range-checks the volume. It plays no "
                   "sound and ships no audio files.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sound_type": (_SOUND_TYPES,),
                "volume": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("valid", "expected_asset_path", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, sound_type: str, volume: float):
        # Validate sound_type against allow-list.
        if sound_type not in _SOUND_ASSETS:
            return (False, "", f"Invalid sound_type: {sound_type!r}")

        # Validate volume range.
        if not _validate_volume(volume):
            return (False, _SOUND_ASSETS[sound_type], f"Volume {volume} out of range [0.0, 1.0]")

        asset_path = _select_asset(sound_type)
        reason = f"Selected {sound_type} cue at volume {volume:.2f}; nothing is played"
        return (True, asset_path, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Notif_Select": PSN_Notif_Select,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Notif_Select": "PSN Audio Cue Selector (plays nothing)",
}
