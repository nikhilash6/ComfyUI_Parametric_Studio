"""Tests for psn_nodes.gen.n_3_deterministic_seed_based_conditioning."""

import json

import pytest

from psn_nodes.gen.n_3_deterministic_seed_based_conditioning import (
    PSN_SeedHashVector,
    generate_seed_vectors,
    _SIZE_PRESETS,
    _STRATEGIES,
    _SIZE_PRESETS_NAMES,
)


def test_deterministic_same_seed_same_output():
    """seed=123 must always produce identical values."""
    a = generate_seed_vectors(123, "B", "sd15")
    b = generate_seed_vectors(123, "B", "sd15")
    assert a == b
    assert a["vector_a"] == b["vector_a"]
    assert a["vector_b"] == b["vector_b"]


def test_shape_sd15():
    """SD1.5 clip dim = 768, pooled dim = 768."""
    payload = generate_seed_vectors(42, "A", "sd15")
    assert len(payload["vector_a"]) == 768
    assert len(payload["vector_b"]) == 768
    assert payload["dim_a"] == 768
    assert payload["dim_b"] == 768


def test_shape_sdxl():
    """SDXL clip dim = 2048, pooled dim = 1280."""
    payload = generate_seed_vectors(42, "C", "sdxl")
    assert len(payload["vector_a"]) == 2048
    assert len(payload["vector_b"]) == 1280
    assert payload["dim_a"] == 2048
    assert payload["dim_b"] == 1280


def test_different_seeds_differ():
    """Different seeds should (almost certainly) produce different vectors."""
    a = generate_seed_vectors(1, "B", "sd15")
    b = generate_seed_vectors(2, "B", "sd15")
    assert a["vector_a"] != b["vector_a"]


def test_all_strategies_produce_valid_output():
    """Every strategy must produce the correct shape and finite floats."""
    for strategy in _STRATEGIES:
        for size_preset in _SIZE_PRESETS_NAMES:
            payload = generate_seed_vectors(99, strategy, size_preset)
            dim_a, dim_b = _SIZE_PRESETS[size_preset]
            assert len(payload["vector_a"]) == dim_a
            assert len(payload["vector_b"]) == dim_b
            for v in payload["vector_a"]:
                assert -1.0 <= v <= 1.0
            for v in payload["vector_b"]:
                assert -1.0 <= v <= 1.0


def test_node_run_returns_valid_json():
    """The node's run() must return parseable JSON with expected keys."""
    node = PSN_SeedHashVector()
    vector_json, summary = node.run(seed=123, strategy="D", size_preset="sdxl")
    data = json.loads(vector_json)
    assert data["seed"] == 123
    assert data["strategy"] == "D"
    assert data["size_preset"] == "sdxl"
    assert len(data["vector_a"]) == 2048
    assert len(data["vector_b"]) == 1280
    assert "seed=123" in summary
    assert "size_preset=sdxl" in summary


def test_bad_strategy_raises():
    """An invalid strategy must raise ValueError."""
    with pytest.raises(ValueError, match="strategy"):
        generate_seed_vectors(1, "X", "sd15")


def test_bad_size_preset_raises():
    """An invalid size_preset must raise ValueError."""
    with pytest.raises(ValueError, match="size_preset"):
        generate_seed_vectors(1, "A", "flux")


def test_non_integer_seed_raises():
    """A non-integer seed (e.g. float or bool) must raise ValueError."""
    with pytest.raises(ValueError, match="seed"):
        generate_seed_vectors(1.5, "A", "sd15")
    with pytest.raises(ValueError, match="seed"):
        generate_seed_vectors(True, "A", "sd15")


def test_negative_seed_works():
    """Negative seeds are valid integers and must produce deterministic output."""
    a = generate_seed_vectors(-42, "C", "sd15")
    b = generate_seed_vectors(-42, "C", "sd15")
    assert a == b
    assert len(a["vector_a"]) == 768


def test_renamed_honest_node_and_exact_hash_values():
    import hashlib, struct
    from psn_nodes.gen import n_3_deterministic_seed_based_conditioning as m
    assert "PSN_ZeroCLIPConditioner" not in m.NODE_CLASS_MAPPINGS
    assert m.NODE_CLASS_MAPPINGS["PSN_SeedHashVector"] is PSN_SeedHashVector
    assert PSN_SeedHashVector.RETURN_NAMES == ("vector_json", "summary")
    assert "not a CLIP embedding" in PSN_SeedHashVector.DESCRIPTION
    payload = generate_seed_vectors(7, "B", "sd15")
    assert set(payload) == {"vector_a", "vector_b", "seed", "strategy", "size_preset", "dim_a", "dim_b"}
    # strategy B is the SHA-256 digest bytes read as signed 32-bit ints
    raw = hashlib.sha256(b"7|B|vector_a").digest()
    expected = [round(struct.unpack(">i", raw[i * 4:i * 4 + 4])[0] / 2147483648.0, 6) for i in range(8)]
    assert payload["vector_a"][:8] == expected
