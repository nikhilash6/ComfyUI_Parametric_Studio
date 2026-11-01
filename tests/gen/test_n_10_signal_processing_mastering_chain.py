"""Tests for PSN_Audio_Json_Smooth_Gain_Normalize."""

import json
import math

import pytest

import psn_nodes.gen.n_10_signal_processing_mastering_chain as mod
from psn_nodes.gen.n_10_signal_processing_mastering_chain import (
    PSN_Audio_Json_Smooth_Gain_Normalize as Node,
    _parse_audio,
    _smooth,
    _apply_half_gains,
    _normalize,
)


def _make_audio(samples, sample_rate=44100):
    return json.dumps({"samples": samples, "sample_rate": sample_rate})


def _run(samples, smooth=False, first=0.0, second=0.0, normalize=True):
    out = Node().run(_make_audio(samples), smooth=smooth, gain_first_half_db=first,
                     gain_second_half_db=second, normalize=normalize)
    return json.loads(out[0])


def test_registration_and_honest_names():
    assert list(mod.NODE_CLASS_MAPPINGS) == ["PSN_Audio_Json_Smooth_Gain_Normalize"]
    assert "PSN_Sig_Process" not in mod.NODE_CLASS_MAPPINGS
    assert not hasattr(mod, "_apply_eq") and not hasattr(mod, "_denoise")
    req = Node.INPUT_TYPES()["required"]
    assert set(req) == {"audio", "smooth", "gain_first_half_db", "gain_second_half_db", "normalize"}
    assert "not a frequency EQ" in Node.DESCRIPTION


def test_normalize_brings_peak_to_one():
    data = _run([0.5, -0.5, 0.25, -0.25, 0.75])
    assert abs(max(abs(s) for s in data["samples"]) - 1.0) < 1e-9
    assert data["samples"] == pytest.approx([2 / 3, -2 / 3, 1 / 3, -1 / 3, 1.0])
    assert data["sample_rate"] == 44100.0


def test_normalize_zero_audio():
    assert _run([0.0, 0.0, 0.0])["samples"] == [0.0, 0.0, 0.0]


def test_half_gain_is_by_time_position_not_frequency():
    # +6 dB on the first half, 0 dB on the second half
    data = _run([1.0, 1.0, 1.0, 1.0], first=6.0, second=0.0, normalize=False)
    g = 10.0 ** (6.0 / 20.0)
    assert data["samples"] == pytest.approx([g, g, 1.0, 1.0])
    # a 1 Hz-like low tone and a fast alternating tone are treated identically:
    # only the position in the stream matters
    slow = [1.0] * 4
    fast = [1.0, -1.0, 1.0, -1.0]
    s = _run(slow, first=6.0, normalize=False)["samples"]
    f = _run(fast, first=6.0, normalize=False)["samples"]
    assert [abs(x) for x in f] == pytest.approx([abs(x) for x in s])


def test_smooth_is_moving_average_with_known_values():
    out = _smooth([0.0, 0.0, 10.0, 0.0, 0.0], window=5)
    # centred 5-wide mean with edge truncation
    assert out == pytest.approx([10 / 3, 10 / 4, 10 / 5, 10 / 4, 10 / 3])
    noisy = [0.5 + (0.1 if i % 2 == 0 else -0.1) for i in range(20)]
    sm = _smooth(noisy)
    mean_o = sum(noisy) / len(noisy)
    mean_s = sum(sm) / len(sm)
    assert sum((x - mean_s) ** 2 for x in sm) < sum((x - mean_o) ** 2 for x in noisy)


def test_bad_audio_json_raises():
    with pytest.raises(ValueError):
        Node().run("not valid json", smooth=False, gain_first_half_db=0.0,
                   gain_second_half_db=0.0, normalize=True)


def test_bad_audio_type_raises():
    with pytest.raises(ValueError):
        Node().run(12345, smooth=False, gain_first_half_db=0.0,
                   gain_second_half_db=0.0, normalize=True)


def test_empty_samples():
    assert _run([], smooth=True, first=3.0, second=-3.0)["samples"] == []


def test_parse_audio_list_format():
    samples, sr = _parse_audio("[1.0, 2.0, 3.0]")
    assert samples == [1.0, 2.0, 3.0]
    assert sr == 44100


def test_parse_audio_non_numeric_sample():
    with pytest.raises(ValueError):
        _parse_audio('["a", 1.0]')


def test_full_chain_order():
    """smooth -> half gain -> normalize ends with peak 1.0."""
    data = _run([0.1, -0.1, 0.2, -0.2, 0.3, -0.3], smooth=True, first=2.0, second=-2.0)
    assert abs(max(abs(s) for s in data["samples"]) - 1.0) < 1e-9
