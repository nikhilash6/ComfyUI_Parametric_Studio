"""
Tests for psn_nodes.gen.n_8_audio_source_separation_remixing.

Covers the pure-logic core: gain-mixing math, allow-list validation,
payload coercion, and edge / bad-input handling. No files, no network,
no torch.
"""

import json
import math

import pytest

from psn_nodes.gen.n_8_audio_source_separation_remixing import (
    PSN_Sep_Plan,
    PSN_Sep_Mix,
    SPLIT_MODELS,
    STEM_NAMES,
    _mix_stems,
    _coerce_gain_list,
    _coerce_sample_list,
)


# ---------------------------------------------------------------------------
# PSN_Sep_Plan
# ---------------------------------------------------------------------------

def test_plan_valid_request_returns_plan_not_stems():
    node = PSN_Sep_Plan()
    audio = json.dumps([0.1, -0.2, 0.3, 0.0])
    out = node.run(audio, "htdemucs", sample_rate=48000)
    assert len(out) == 2  # plan_json, status; no stem outputs
    plan_json, status = out
    assert status == "request valid: nothing was separated"
    assert json.loads(plan_json) == {
        "model": "htdemucs",
        "samples": 4,
        "sample_rate": 48000,
        "stems": ["vocals", "drums", "bass", "other"],
        "default_gain": 1.0,
    }
    # the all-zero stems are gone
    assert PSN_Sep_Plan.RETURN_NAMES == ("plan_json", "status")
    assert "separates nothing" in PSN_Sep_Plan.DESCRIPTION.lower()
    import psn_nodes.gen.n_8_audio_source_separation_remixing as m
    assert "PSN_Sep_Split" not in m.NODE_CLASS_MAPPINGS
    assert m.NODE_CLASS_MAPPINGS["PSN_Sep_Plan"] is PSN_Sep_Plan


def test_plan_rejects_unknown_model():
    node = PSN_Sep_Plan()
    audio = json.dumps([0.1, 0.2])
    plan, status = node.run(audio, "not_a_model")
    assert status.startswith("error:")
    assert "not in allow-list" in status
    assert plan == ""


def test_plan_rejects_empty_audio():
    node = PSN_Sep_Plan()
    plan, status = node.run("[]", "mdx")
    assert status.startswith("error:")
    assert "empty" in status
    assert plan == ""


def test_plan_rejects_bad_json_audio():
    node = PSN_Sep_Plan()
    plan, status = node.run("not json at all", "htdemucs")
    assert status.startswith("error:")
    assert "not valid JSON" in status


def test_plan_rejects_non_numeric_sample():
    node = PSN_Sep_Plan()
    audio = json.dumps([0.1, "oops", 0.3])
    plan, status = node.run(audio, "htdemucs")
    assert status.startswith("error:")
    assert "not a number" in status


def test_plan_rejects_bad_sample_rate():
    node = PSN_Sep_Plan()
    audio = json.dumps([0.1, 0.2])
    plan, status = node.run(audio, "htdemucs", sample_rate=-5)
    assert status.startswith("error:")
    assert "sample_rate" in status


# ---------------------------------------------------------------------------
# PSN_Sep_Mix -- gain math
# ---------------------------------------------------------------------------

def test_mix_gain_application_math():
    # Two stems, gains 2.0 and 0.5.
    stems = json.dumps([[1.0, -1.0], [2.0, 2.0]])
    gains = json.dumps([2.0, 0.5])
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run(stems, gains)
    assert status.startswith("ok:")
    parsed = json.loads(mixed)
    # stem0 * 2.0 = [2.0, -2.0]; stem1 * 0.5 = [1.0, 1.0]; sum = [3.0, -1.0]
    assert parsed == [3.0, -1.0]
    assert peak == 3.0
    assert clipped is True  # 3.0 > 1.0


def test_mix_single_gain_applies_to_all_stems():
    stems = json.dumps([[1.0, 1.0], [1.0, 1.0]])
    gains = "0.5"  # single number -> applied to every stem
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run(stems, gains)
    assert status.startswith("ok:")
    parsed = json.loads(mixed)
    # each stem * 0.5 = [0.5, 0.5]; sum = [1.0, 1.0]
    assert parsed == [1.0, 1.0]
    assert peak == 1.0
    assert clipped is False


def test_mix_zero_gain_mutes_stem():
    stems = json.dumps([[1.0, 1.0], [5.0, 5.0]])
    gains = json.dumps([1.0, 0.0])
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run(stems, gains)
    parsed = json.loads(mixed)
    assert parsed == [1.0, 1.0]
    assert peak == 1.0
    assert clipped is False


def test_mix_no_clipping_when_within_range():
    stems = json.dumps([[0.2, 0.3], [0.4, 0.5]])
    gains = json.dumps([1.0, 1.0])
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run(stems, gains)
    parsed = json.loads(mixed)
    # Use math.isclose to handle floating point precision
    assert len(parsed) == 2
    assert math.isclose(parsed[0], 0.6, rel_tol=1e-9)
    assert math.isclose(parsed[1], 0.8, rel_tol=1e-9)
    assert math.isclose(peak, 0.8, rel_tol=1e-9)
    assert clipped is False


def test_mix_rejects_gain_length_mismatch():
    stems = json.dumps([[1.0, 1.0], [1.0, 1.0]])
    gains = json.dumps([1.0])  # only one gain for two stems
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run(stems, gains)
    assert status.startswith("error:")
    assert "length" in status
    assert mixed == ""


def test_mix_rejects_gain_out_of_range():
    stems = json.dumps([[1.0, 1.0]])
    gains = json.dumps([1e9])  # exceeds MAX_GAIN
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run(stems, gains)
    assert status.startswith("error:")
    assert "out of range" in status


def test_mix_rejects_negative_gain():
    stems = json.dumps([[1.0, 1.0]])
    gains = json.dumps([-0.5])
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run(stems, gains)
    assert status.startswith("error:")
    assert "out of range" in status


def test_mix_rejects_mismatched_stem_lengths():
    stems = json.dumps([[1.0, 1.0], [1.0]])  # different lengths
    gains = json.dumps([1.0, 1.0])
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run(stems, gains)
    assert status.startswith("error:")
    assert "length" in status


def test_mix_rejects_empty_stems():
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run("[]", "1.0")
    assert status.startswith("error:")
    assert "empty" in status


def test_mix_rejects_bad_json_stems():
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run("not json", "1.0")
    assert status.startswith("error:")
    assert "not valid JSON" in status


def test_mix_rejects_non_numeric_in_stem():
    stems = json.dumps([[1.0, "bad"]])
    gains = json.dumps([1.0])
    node = PSN_Sep_Mix()
    mixed, peak, clipped, status = node.run(stems, gains)
    assert status.startswith("error:")
    assert "not a number" in status


# ---------------------------------------------------------------------------
# Helper-level unit tests
# ---------------------------------------------------------------------------

def test_mix_stems_helper_math():
    stem_lists = [[1.0, 2.0], [3.0, 4.0]]
    gains = [2.0, 0.5]
    mixed, peak, clipped = _mix_stems(stem_lists, gains)
    # [1*2 + 3*0.5, 2*2 + 4*0.5] = [2+1.5, 4+2] = [3.5, 6.0]
    assert mixed == [3.5, 6.0]
    assert peak == 6.0
    assert clipped is True


def test_coerce_gain_list_single_number():
    gains = _coerce_gain_list(0.5, 3)
    assert gains == [0.5, 0.5, 0.5]


def test_coerce_gain_list_none_defaults_to_ones():
    gains = _coerce_gain_list(None, 2)
    assert gains == [1.0, 1.0]


def test_coerce_sample_list_from_json_text():
    samples = _coerce_sample_list("[1, 2, 3]", "audio")
    assert samples == [1.0, 2.0, 3.0]


def test_coerce_sample_list_rejects_bool():
    with pytest.raises(ValueError):
        _coerce_sample_list([True, False], "audio")


def test_split_models_allow_list_matches_spec():
    assert set(SPLIT_MODELS) == {"htdemucs", "mdx"}
    assert STEM_NAMES == ("vocals", "drums", "bass", "other")
