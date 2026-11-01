"""Tests for psn_nodes.gen.n_3_artifact_cleanup_stage (NAFNet settings check)."""

import json

from psn_nodes.gen.n_3_artifact_cleanup_stage import (
    PSN_NAFNet_Config_Check,
    NODE_CLASS_MAPPINGS,
    validate_denoise_config,
    ALLOWED_MODELS,
)


def _meta(width=512, height=512, channels=3):
    return json.dumps({"width": width, "height": height, "channels": channels})


def test_valid_config_is_normalized_and_nothing_invented():
    ok, reason, config = validate_denoise_config(0.1, "nafnet_srgb", _meta())
    assert ok is True
    assert reason == "ok"
    assert config == {"model_path": "nafnet_srgb", "noise_level": 0.1,
                      "width": 512, "height": 512, "channels": 3}
    for gone in ("gains", "blur_kernel", "preview", "preview_shape"):
        assert gone not in config


def test_node_is_renamed_and_takes_no_image():
    assert "PSN_NAFNet_Denoise" not in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_NAFNet_Config_Check"] is PSN_NAFNet_Config_Check
    assert PSN_NAFNet_Config_Check.RETURN_NAMES == ("ok", "reason", "config_json")
    assert "denoises nothing" in PSN_NAFNet_Config_Check.DESCRIPTION
    assert "IMAGE" not in str(PSN_NAFNet_Config_Check.INPUT_TYPES())
def test_invalid_noise_level_out_of_range():
    ok, reason, config = validate_denoise_config(1.5, "nafnet_srgb", _meta())
    assert ok is False
    assert config is None
    assert "out of range" in reason


def test_invalid_noise_level_non_numeric():
    ok, reason, config = validate_denoise_config("0.1", "nafnet_srgb", _meta())
    assert ok is False
    assert config is None
    assert "must be a number" in reason


def test_invalid_model_path_not_in_allowlist():
    ok, reason, config = validate_denoise_config(0.1, "nafnet_unknown", _meta())
    assert ok is False
    assert config is None
    assert "allow-list" in reason


def test_invalid_image_meta_bad_json():
    ok, reason, config = validate_denoise_config(0.1, "nafnet_srgb", "not json {")
    assert ok is False
    assert config is None
    assert "not valid JSON" in reason


def test_invalid_image_meta_bad_dimension():
    bad = json.dumps({"width": 0, "height": 512, "channels": 3})
    ok, reason, config = validate_denoise_config(0.1, "nafnet_srgb", bad)
    assert ok is False
    assert config is None
    assert "out of range" in reason


def test_node_run_returns_json_config():
    node = PSN_NAFNet_Config_Check()
    ok, reason, config_json = node.run(0.2, "nafnet_yuv", _meta(width=256, height=128, channels=1))
    assert ok is True
    assert reason == "ok"
    assert json.loads(config_json) == {"model_path": "nafnet_yuv", "noise_level": 0.2,
                                       "width": 256, "height": 128, "channels": 1}


def test_node_run_failure_returns_empty_config_json():
    node = PSN_NAFNet_Config_Check()
    ok, reason, config_json = node.run(0.2, "bad_model", _meta())
    assert ok is False
    assert config_json == ""
    assert "allow-list" in reason


def test_all_allowed_models_accepted():
    for model in ALLOWED_MODELS:
        ok, reason, config = validate_denoise_config(0.3, model, _meta())
        assert ok is True, (model, reason)
        assert config["model_path"] == model
