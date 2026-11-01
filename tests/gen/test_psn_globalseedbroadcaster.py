"""Tests for PSN_Seed_Source (psn_globalseedbroadcaster module)."""

import hashlib
import json

import pytest
from psn_nodes.gen import psn_globalseedbroadcaster as mod
from psn_nodes.gen.psn_globalseedbroadcaster import PSN_Seed_Source, psn_seed_hash


class TestPsnSeedHash:
    def test_known_value(self):
        expected = hashlib.sha256(json.dumps({"seed": 123}, sort_keys=True).encode()).hexdigest()
        assert psn_seed_hash(123) == expected

    def test_different_seeds_different_hashes(self):
        assert psn_seed_hash(123) != psn_seed_hash(456)

    def test_returns_64_char_hex(self):
        h = psn_seed_hash(0)
        assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)

    def test_rejects_non_int(self):
        with pytest.raises(TypeError):
            psn_seed_hash("123")
        with pytest.raises(TypeError):
            psn_seed_hash(123.0)


class TestPSNSeedSource:
    def test_outputs_seed_and_its_hash(self):
        assert PSN_Seed_Source().run(seed=123) == (123, psn_seed_hash(123))

    def test_negative_seed(self):
        assert PSN_Seed_Source().run(seed=-50) == (-50, psn_seed_hash(-50))

    def test_non_int_seed(self):
        with pytest.raises(TypeError):
            PSN_Seed_Source().run(seed="123")

    def test_no_mode_input_and_no_broadcast_helper(self):
        it = PSN_Seed_Source.INPUT_TYPES()
        assert list(it["required"]) == ["seed"]
        assert not hasattr(mod, "psn_broadcast_seed") and not hasattr(mod, "_MODES")

    def test_return_types_description_mappings(self):
        assert PSN_Seed_Source.RETURN_TYPES == ("INT", "STRING")
        assert PSN_Seed_Source.RETURN_NAMES == ("seed_out", "seed_hash")
        assert "does not reach other nodes" in PSN_Seed_Source.DESCRIPTION
        assert list(mod.NODE_CLASS_MAPPINGS) == ["PSN_Seed_Source"]
