"""
Tests for psn_nodes.gen.n_5_audio_notification_system.

Covers:
- Correct asset path selection for each valid sound_type.
- valid boolean is True for valid inputs.
- valid boolean is False for out-of-range volume.
- valid boolean is False for invalid sound_type.
- Edge cases: volume at 0.0 and 1.0 boundaries.
- Bad input: non-numeric volume (should not crash, but the node expects FLOAT;
  we test the logic function directly with a bad type to ensure graceful handling
  is not required since ComfyUI enforces types, but we verify the reason string
  for an invalid sound_type string).
"""

import pytest

from psn_nodes.gen.n_5_audio_notification_system import (
    NODE_CLASS_MAPPINGS,
    PSN_Notif_Select,
    _select_asset,
    _validate_volume,
    _SOUND_ASSETS,
    _SOUND_TYPES,
)


def test_select_asset_success():
    assert _select_asset("success") == "assets/sounds/success.wav"


def test_select_asset_error():
    assert _select_asset("error") == "assets/sounds/error.wav"


def test_select_asset_info():
    assert _select_asset("info") == "assets/sounds/info.wav"


def test_select_asset_invalid_raises():
    with pytest.raises(ValueError, match="Unknown sound_type"):
        _select_asset("warning")


def test_validate_volume_in_range():
    assert _validate_volume(0.0) is True
    assert _validate_volume(0.5) is True
    assert _validate_volume(1.0) is True


def test_validate_volume_out_of_range():
    assert _validate_volume(-0.1) is False
    assert _validate_volume(1.1) is False


def test_run_valid_success():
    node = PSN_Notif_Select()
    valid, asset_path, reason = node.run("success", 0.8)
    assert valid is True
    assert asset_path == "assets/sounds/success.wav"
    assert reason == "Selected success cue at volume 0.80; nothing is played"
    assert "Play " not in reason


def test_run_valid_error():
    node = PSN_Notif_Select()
    valid, asset_path, reason = node.run("error", 0.5)
    assert valid is True
    assert asset_path == "assets/sounds/error.wav"


def test_run_valid_info():
    node = PSN_Notif_Select()
    valid, asset_path, reason = node.run("info", 1.0)
    assert valid is True
    assert asset_path == "assets/sounds/info.wav"


def test_run_volume_zero():
    node = PSN_Notif_Select()
    valid, asset_path, reason = node.run("success", 0.0)
    assert valid is True
    assert asset_path == "assets/sounds/success.wav"


def test_run_volume_one():
    node = PSN_Notif_Select()
    valid, asset_path, reason = node.run("info", 1.0)
    assert valid is True
    assert asset_path == "assets/sounds/info.wav"


def test_run_volume_out_of_range_high():
    node = PSN_Notif_Select()
    valid, asset_path, reason = node.run("success", 1.5)
    assert valid is False
    assert "out of range" in reason


def test_run_volume_out_of_range_low():
    node = PSN_Notif_Select()
    valid, asset_path, reason = node.run("error", -0.2)
    assert valid is False
    assert "out of range" in reason


def test_run_invalid_sound_type():
    node = PSN_Notif_Select()
    valid, asset_path, reason = node.run("warning", 0.5)
    assert valid is False
    assert asset_path == ""
    assert "Invalid sound_type" in reason


def test_input_types_structure():
    it = PSN_Notif_Select.INPUT_TYPES()
    assert "required" in it
    assert "sound_type" in it["required"]
    assert "volume" in it["required"]
    # sound_type is a tuple containing the list of allowed values
    assert it["required"]["sound_type"] == (_SOUND_TYPES,)
    vol_spec = it["required"]["volume"]
    assert vol_spec[0] == "FLOAT"
    assert vol_spec[1]["min"] == 0.0
    assert vol_spec[1]["max"] == 1.0


def test_return_types_and_names():
    assert PSN_Notif_Select.RETURN_TYPES == ("BOOLEAN", "STRING", "STRING")
    assert PSN_Notif_Select.RETURN_NAMES == ("valid", "expected_asset_path", "reason")
    assert PSN_Notif_Select.FUNCTION == "run"
    assert PSN_Notif_Select.CATEGORY == "ParametricStudio/Audio"


def test_renamed_and_honest():
    assert "PSN_Notif_Play" not in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Notif_Select"] is PSN_Notif_Select
    assert "plays no" in PSN_Notif_Select.DESCRIPTION
    assert "trigger" not in PSN_Notif_Select.RETURN_NAMES
