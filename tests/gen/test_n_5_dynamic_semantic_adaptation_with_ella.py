"""
Tests for PSN_ELLA_Request_Formatter.

All tests use only the Python standard library. No files, no network,
no torch, no comfy imports.
"""

import json
import pytest

from psn_nodes.gen.n_5_dynamic_semantic_adaptation_with_ella import (
    PSN_ELLA_Request_Formatter,
    _validate_sigma,
    _validate_strength,
    _validate_model,
    _redact_sensitive,
    _format_request_payload,
    _parse_response,
    _ella_rate_limiter,
    ALLOWED_ELLA_MODELS,
    NODE_CLASS_MAPPINGS,
)
from psn_nodes.gen import n_5_dynamic_semantic_adaptation_with_ella as mod


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the rate limiter before each test to avoid cross-test interference."""
    _ella_rate_limiter.reset()
    yield


class TestValidation:
    def test_validate_sigma_valid(self):
        ok, reason = _validate_sigma(0.5)
        assert ok is True
        assert reason == "ok"

    def test_validate_sigma_negative(self):
        ok, reason = _validate_sigma(-0.1)
        assert ok is False
        assert "non-negative" in reason

    def test_validate_sigma_nan(self):
        ok, reason = _validate_sigma(float("nan"))
        assert ok is False
        assert "finite" in reason

    def test_validate_sigma_inf(self):
        ok, reason = _validate_sigma(float("inf"))
        assert ok is False
        assert "finite" in reason

    def test_validate_sigma_non_numeric(self):
        ok, reason = _validate_sigma("0.5")
        assert ok is False
        assert "number" in reason

    def test_validate_strength_valid(self):
        ok, reason = _validate_strength(0.7)
        assert ok is True

    def test_validate_strength_out_of_range_high(self):
        ok, reason = _validate_strength(1.5)
        assert ok is False
        assert "[0, 1]" in reason

    def test_validate_strength_out_of_range_low(self):
        ok, reason = _validate_strength(-0.1)
        assert ok is False
        assert "[0, 1]" in reason

    def test_validate_model_valid(self):
        ok, reason = _validate_model("ella_v1_small")
        assert ok is True

    def test_validate_model_not_in_allowlist(self):
        ok, reason = _validate_model("unknown_model")
        assert ok is False
        assert "allow-list" in reason

    def test_validate_model_non_string(self):
        ok, reason = _validate_model(123)
        assert ok is False
        assert "string" in reason


class TestRedaction:
    def test_redact_sensitive_fields(self):
        payload = {"api_key": "secret123", "sigma": 0.5, "token": "abc"}
        redacted = _redact_sensitive(payload)
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["token"] == "***REDACTED***"
        assert redacted["sigma"] == 0.5

    def test_redact_no_sensitive_fields(self):
        payload = {"sigma": 0.5, "strength": 0.3}
        redacted = _redact_sensitive(payload)
        assert redacted == payload

    def test_redact_nested_sensitive_fields(self):
        payload = {"conditioning": {"api_key": "nested_secret", "value": 1.0}}
        redacted = _redact_sensitive(payload)
        assert redacted["conditioning"]["api_key"] == "***REDACTED***"
        assert redacted["conditioning"]["value"] == 1.0


class TestFormatRequestPayload:
    def test_format_includes_required_fields(self):
        payload = _format_request_payload({"a": 1}, 0.5, 0.3, "ella_v1_small")
        parsed = json.loads(payload)
        assert parsed["type"] == "ella_semantic_connector"
        assert parsed["model"] == "ella_v1_small"
        assert parsed["sigma"] == 0.5
        assert parsed["strength"] == 0.3
        assert parsed["conditioning"] == {"a": 1}

    def test_format_redacts_sensitive(self):
        payload = _format_request_payload({"api_key": "xyz"}, 0.5, 0.3, "ella_v1_small")
        parsed = json.loads(payload)
        assert parsed["conditioning"]["api_key"] == "***REDACTED***"


class TestParseResponse:
    def test_parse_valid_response(self):
        resp = json.dumps({"conditioning": {"a": 1.0}, "status": "ok"})
        ok, result = _parse_response(resp)
        assert ok is True
        assert result["conditioning"] == {"a": 1.0}

    def test_parse_invalid_json(self):
        ok, result = _parse_response("not json")
        assert ok is False
        assert "invalid JSON" in result

    def test_parse_missing_conditioning(self):
        resp = json.dumps({"status": "ok"})
        ok, result = _parse_response(resp)
        assert ok is False
        assert "conditioning" in result

    def test_parse_non_string(self):
        ok, result = _parse_response(123)
        assert ok is False
        assert "string" in result


def _run(node, conditioning="{}", sigma=0.5, ella_model="ella_v1_small", strength=0.5):
    return node.run(conditioning=conditioning, sigma=sigma,
                    ella_model=ella_model, strength=strength)


class TestNodeRun:
    def test_run_formats_exact_payload(self):
        node = PSN_ELLA_Request_Formatter()
        out = _run(node, json.dumps({"a": 1.0, "b": 2.0}), 0.5, "ella_v1_small", 0.25)
        assert len(out) == 1
        # Conditioning is copied unchanged (no hash-scaled numbers).
        assert json.loads(out[0]) == {
            "type": "ella_semantic_connector",
            "model": "ella_v1_small",
            "sigma": 0.5,
            "strength": 0.25,
            "conditioning": {"a": 1.0, "b": 2.0},
        }

    def test_run_redacts_sensitive_fields(self):
        node = PSN_ELLA_Request_Formatter()
        (payload,) = _run(node, json.dumps({"api_key": "xyz", "v": 3}))
        assert "xyz" not in payload
        assert json.loads(payload)["conditioning"]["api_key"] == "***REDACTED***"

    def test_run_invalid_sigma(self):
        with pytest.raises(ValueError, match="non-negative"):
            _run(PSN_ELLA_Request_Formatter(), sigma=-1.0)

    def test_run_invalid_strength(self):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            _run(PSN_ELLA_Request_Formatter(), strength=2.0)

    def test_run_invalid_model(self):
        with pytest.raises(ValueError, match="allow-list"):
            _run(PSN_ELLA_Request_Formatter(), ella_model="bad_model")

    def test_run_invalid_conditioning_json(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            _run(PSN_ELLA_Request_Formatter(), conditioning="not valid json")

    def test_run_conditioning_not_object(self):
        with pytest.raises(ValueError, match="JSON object"):
            _run(PSN_ELLA_Request_Formatter(), conditioning="[1, 2, 3]")

    def test_run_rate_limit(self):
        node = PSN_ELLA_Request_Formatter()
        for _ in range(10):
            _run(node)
        with pytest.raises(ValueError, match="rate limit exceeded"):
            _run(node)

    def test_sigma_does_not_alter_conditioning(self):
        node = PSN_ELLA_Request_Formatter()
        cond = json.dumps({"a": 1.0})
        (p1,) = _run(node, cond, 0.1)
        (p2,) = _run(node, cond, 0.9)
        assert json.loads(p1)["conditioning"] == json.loads(p2)["conditioning"] == {"a": 1.0}

    def test_run_empty_conditioning(self):
        (payload,) = _run(PSN_ELLA_Request_Formatter())
        assert json.loads(payload)["conditioning"] == {}


class TestHonestNaming:
    def test_renamed_and_fabricated_parts_gone(self):
        assert "PSN_ELLA_Semantic_Connector" not in NODE_CLASS_MAPPINGS
        assert "PSN_ELLA_Request_Formatter" in NODE_CLASS_MAPPINGS
        assert not hasattr(mod, "_deterministic_transform")
        assert not hasattr(mod, "hashlib")
        assert PSN_ELLA_Request_Formatter.RETURN_NAMES == ("request_payload",)
        assert "does not run ELLA" in PSN_ELLA_Request_Formatter.DESCRIPTION
