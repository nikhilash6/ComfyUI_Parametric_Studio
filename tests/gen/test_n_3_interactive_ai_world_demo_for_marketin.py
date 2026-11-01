"""
Tests for PSN Matrix-Game parameter check (pure logic)
"""

import pytest

from psn_nodes.gen import n_3_interactive_ai_world_demo_for_marketin as mod
from psn_nodes.gen.n_3_interactive_ai_world_demo_for_marketin import (
    PSN_MatrixGame_ParamCheck,
    _validate_model_path,
    _validate_device,
    ALLOWED_DEVICES,
)


class TestPSN_MatrixGame_ParamCheck:
    """Tests for PSN_MatrixGame_ParamCheck node."""

    def test_valid_params(self, tmp_path):
        """Valid strings come back as-is; the path is not required to exist and nothing is claimed loaded."""
        node = PSN_MatrixGame_ParamCheck()
        params, status = node.run("models/matrix_game_17b.safetensors", "cuda")
        assert params == {"model_path": "models/matrix_game_17b.safetensors", "device": "cuda"}
        assert status.startswith("OK")
        assert "nothing loaded" in status
        for fabricated in ("loaded", "status", "param_count"):
            assert fabricated not in params

    def test_description_and_registry(self):
        assert "loads nothing" in PSN_MatrixGame_ParamCheck.DESCRIPTION
        assert PSN_MatrixGame_ParamCheck.RETURN_NAMES == ("checked_params", "check_status")
        assert set(mod.NODE_CLASS_MAPPINGS) == {"PSN_MatrixGame_ParamCheck"}
        assert "loads nothing" in mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_MatrixGame_ParamCheck"]

    def test_generate_node_is_gone(self):
        assert not hasattr(mod, "PSN_MatrixGame_Generate")
        assert not hasattr(mod, "PSN_MatrixGame_Load")
        assert "PSN_MatrixGame_Generate" not in mod.NODE_CLASS_MAPPINGS

    def test_invalid_device(self):
        node = PSN_MatrixGame_ParamCheck()
        params, status = node.run("models/matrix_game_17b.safetensors", "gpu")
        assert params == {"error": "device must be one of ['cuda', 'cpu']"}
        assert "FAIL" in status
        assert "device" in status.lower()

    def test_empty_model_path(self):
        node = PSN_MatrixGame_ParamCheck()
        params, status = node.run("", "cpu")
        assert "error" in params
        assert "FAIL" in status

    def test_path_traversal(self):
        node = PSN_MatrixGame_ParamCheck()
        params, status = node.run("../etc/passwd", "cpu")
        assert "error" in params
        assert "traversal" in status.lower()

    def test_non_string_model_path(self):
        node = PSN_MatrixGame_ParamCheck()
        params, status = node.run(12345, "cpu")
        assert "error" in params
        assert "FAIL" in status


class TestValidationHelpers:
    """Tests for validation helper functions."""

    def test_validate_model_path_valid(self):
        ok, reason = _validate_model_path("models/test.safetensors")
        assert ok is True
        assert reason == "ok"

    def test_validate_model_path_null_byte(self):
        ok, reason = _validate_model_path("models/test\x00.safetensors")
        assert ok is False
        assert "null" in reason.lower()

    def test_validate_device_valid(self):
        for dev in ALLOWED_DEVICES:
            ok, reason = _validate_device(dev)
            assert ok is True

    def test_validate_device_invalid(self):
        ok, reason = _validate_device("tpu")
        assert ok is False
