import json
import math
import pytest
from psn_nodes.gen.psn_latentinterpolator import PSN_LatentInterpolator

class TestPSN_LatentInterpolator:
    def setup_method(self):
        self.node = PSN_LatentInterpolator()

    def test_lerp_basic(self):
        # Test basic lerp between two scalars
        result, valid, reason, latent_json = self.node.run(0.0, 1.0, 0.5, "lerp")
        assert valid is True
        assert reason == "Success"
        assert abs(result - 0.5) < 1e-6

    def test_lerp_vectors(self):
        # Test lerp between two vectors
        vec_a = "[1.0, 2.0, 3.0]"
        vec_b = "[4.0, 5.0, 6.0]"
        result, valid, reason, latent_json = self.node.run(0.0, 0.0, 0.5, "lerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is True
        assert reason == "Success"
        # First element should be (1+4)/2 = 2.5
        assert abs(result - 2.5) < 1e-6

    def test_slerp_basic(self):
        # Test slerp between two orthogonal unit vectors
        vec_a = "[1.0, 0.0]"
        vec_b = "[0.0, 1.0]"
        result, valid, reason, latent_json = self.node.run(0.0, 0.0, 0.5, "slerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is True
        assert reason == "Success"
        # Slerp of orthogonal vectors at t=0.5 should be [1/sqrt(2), 1/sqrt(2)]
        expected = 1.0 / math.sqrt(2)
        assert abs(result - expected) < 1e-6

    def test_slerp_parallel_vectors(self):
        # Test slerp with parallel vectors (should fall back to lerp)
        vec_a = "[1.0, 0.0]"
        vec_b = "[2.0, 0.0]"
        result, valid, reason, latent_json = self.node.run(0.0, 0.0, 0.5, "slerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is True
        assert reason == "Success"
        # Should be lerp: (1+2)/2 = 1.5
        assert abs(result - 1.5) < 1e-6

    def test_invalid_vector_lengths(self):
        # Test with mismatched vector lengths
        vec_a = "[1.0, 2.0]"
        vec_b = "[1.0, 2.0, 3.0]"
        result, valid, reason, latent_json = self.node.run(0.0, 0.0, 0.5, "lerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is False
        assert "Vector lengths must match" in reason

    def test_invalid_t_value(self):
        # Test with t out of range
        result, valid, reason, latent_json = self.node.run(0.0, 1.0, 1.5, "lerp")
        assert valid is False
        assert "t must be between 0 and 1" in reason

    def test_invalid_method(self):
        # Test with unknown method
        result, valid, reason, latent_json = self.node.run(0.0, 1.0, 0.5, "invalid_method")
        assert valid is False
        assert "Unknown method" in reason

    def test_zero_vector_slerp(self):
        # Test slerp with zero vector (should fall back to lerp)
        vec_a = "[0.0, 0.0]"
        vec_b = "[1.0, 0.0]"
        result, valid, reason, latent_json = self.node.run(0.0, 0.0, 0.5, "slerp", latent_a_list=vec_a, latent_b_list=vec_b)
        assert valid is True
        assert reason == "Success"
        # Should be lerp: (0+1)/2 = 0.5
        assert abs(result - 0.5) < 1e-6


    def test_full_vector_is_returned_as_json_lerp(self):
        result, valid, reason, latent_json = self.node.run(
            0.0, 0.0, 0.25, "lerp", latent_a_list="[0.0, 4.0, 8.0]", latent_b_list="[4.0, 8.0, 0.0]")
        out = json.loads(latent_json)
        assert out == pytest.approx([1.0, 5.0, 6.0])
        assert result == out[0]

    def test_full_vector_is_returned_as_json_slerp(self):
        _, valid, _, latent_json = self.node.run(
            0.0, 0.0, 0.5, "slerp", latent_a_list="[1.0, 0.0]", latent_b_list="[0.0, 1.0]")
        out = json.loads(latent_json)
        assert valid is True
        assert out == pytest.approx([math.sqrt(0.5), math.sqrt(0.5)])
        assert math.sqrt(sum(x * x for x in out)) == pytest.approx(1.0)

    def test_scalar_inputs_give_one_element_json(self):
        _, _, _, latent_json = self.node.run(0.0, 1.0, 0.5, "lerp")
        assert json.loads(latent_json) == [0.5]

    def test_invalid_cases_return_empty_json_list(self):
        for args, kw in [((0.0, 1.0, 1.5, "lerp"), {}), ((0.0, 1.0, 0.5, "nope"), {}),
                         ((0.0, 0.0, 0.5, "lerp"), {"latent_a_list": "[1,2]", "latent_b_list": "[1,2,3]"})]:
            result, valid, reason, latent_json = self.node.run(*args, **kw)
            assert valid is False and latent_json == "[]" and result == 0.0

    def test_return_names(self):
        assert PSN_LatentInterpolator.RETURN_NAMES == ("latent_out_first", "valid", "reason", "latent_out_json")
        assert PSN_LatentInterpolator.RETURN_TYPES == ("FLOAT", "BOOLEAN", "STRING", "STRING")
