import pytest
import json
import math
import torch
from psn_nodes.gen.n_2_semantic_conditioning_subtraction_for_ import (
    PSN_Conditioning_Subtract,
    PSN_Number_List_Clamp,
    NODE_CLASS_MAPPINGS,
    _clamp_vector,
    _parse_vector_json
)


def _cond(values, opts=None):
    return [[torch.tensor(values, dtype=torch.float32).reshape(1, 1, -1), dict(opts or {})]]


class TestPSN_Conditioning_Subtract:
    def test_basic_subtraction_on_tensors(self):
        base = _cond([1.0, 2.0, 3.0], {"pooled": 1})
        sub = _cond([0.5, 0.5, 0.5])
        (out,) = PSN_Conditioning_Subtract().run(base, sub, 1.0, False)
        assert torch.allclose(out[0][0], torch.tensor([0.5, 1.5, 2.5]).reshape(1, 1, 3))
        assert out[0][1] == {"pooled": 1}

    def test_strength_scales_subtraction(self):
        base = _cond([1.0, 2.0, 3.0])
        sub = _cond([0.5, 0.5, 0.5])
        (out,) = PSN_Conditioning_Subtract().run(base, sub, 2.0, False)
        assert torch.allclose(out[0][0], torch.tensor([0.0, 1.0, 2.0]).reshape(1, 1, 3))

    def test_auto_scale_matches_norm(self):
        base = _cond([2.0, 2.0])   # norm sqrt(8)
        sub = _cond([1.0, 1.0])    # norm sqrt(2); factor 2
        (out,) = PSN_Conditioning_Subtract().run(base, sub, 1.0, True)
        assert torch.allclose(out[0][0], torch.zeros(1, 1, 2), atol=1e-6)

    def test_inputs_not_modified_and_every_entry_processed(self):
        base = _cond([1.0, 1.0]) + _cond([4.0, 4.0])
        sub = _cond([1.0, 0.0])
        before = [b[0].clone() for b in base]
        (out,) = PSN_Conditioning_Subtract().run(base, sub, 1.0, False)
        assert len(out) == 2
        assert torch.allclose(out[1][0], torch.tensor([3.0, 4.0]).reshape(1, 1, 2))
        assert all(torch.equal(b[0], x) for b, x in zip(base, before))

    def test_shape_mismatch_and_empty_rejected(self):
        with pytest.raises(ValueError, match="shapes must match"):
            PSN_Conditioning_Subtract().run(_cond([1.0, 2.0]), _cond([1.0]), 1.0, False)
        with pytest.raises(ValueError, match="must not be empty"):
            PSN_Conditioning_Subtract().run([], _cond([1.0]), 1.0, False)

    def test_types_and_dead_inputs_gone(self):
        it = PSN_Conditioning_Subtract.INPUT_TYPES()["required"]
        assert it["base"] == ("CONDITIONING",) and it["subtract"] == ("CONDITIONING",)
        assert "base_conditioning" not in it and "subtract_conditioning" not in it
        assert PSN_Conditioning_Subtract.RETURN_TYPES == ("CONDITIONING",)


class TestPSN_Number_List_Clamp:
    def test_linear_clamp(self):
        node = PSN_Number_List_Clamp()
        vec = "[-2.0, 0.5, 3.0]"
        min_val = -1.0
        max_val = 1.0
        method = "linear"
        
        result_float, result_json = node.run(
            min_val=min_val,
            max_val=max_val,
            method=method,
            vector=vec
        )
        
        expected = [-1.0, 0.5, 1.0]
        parsed_result = json.loads(result_json)
        assert parsed_result == expected
        assert result_float == -1.0

    def test_tanh_clamp(self):
        node = PSN_Number_List_Clamp()
        vec = "[-2.0, 0.0, 2.0]"
        min_val = -1.0
        max_val = 1.0
        method = "tanh"
        
        result_float, result_json = node.run(
            min_val=min_val,
            max_val=max_val,
            method=method,
            vector=vec
        )
        
        # tanh(-2) ≈ -0.9640, tanh(0) = 0, tanh(2) ≈ 0.9640
        # Center = 0, half_range = 1
        # Result: [0 + tanh(-2)*1, 0 + tanh(0)*1, 0 + tanh(2)*1]
        expected = [math.tanh(-2.0), 0.0, math.tanh(2.0)]
        parsed_result = json.loads(result_json)
        assert len(parsed_result) == len(expected)
        for r, e in zip(parsed_result, expected):
            assert abs(r - e) < 1e-6
        assert abs(result_float - math.tanh(-2.0)) < 1e-6

    def test_invalid_range(self):
        node = PSN_Number_List_Clamp()
        vec = "[1.0]"
        min_val = 2.0
        max_val = 1.0
        method = "linear"
        
        with pytest.raises(ValueError, match="min_val must be less than or equal to max_val"):
            node.run(
                min_val=min_val,
                max_val=max_val,
                method=method,
                vector=vec
            )

    def test_invalid_method(self):
        node = PSN_Number_List_Clamp()
        vec = "[1.0]"
        min_val = -1.0
        max_val = 1.0
        method = "invalid"
        
        with pytest.raises(ValueError, match="Unknown clamp method"):
            node.run(
                min_val=min_val,
                max_val=max_val,
                method=method,
                vector=vec
            )


class TestRenamedClamp:
    def test_registry_and_output_names(self):
        assert "PSN_Conditioning_Clamp" not in NODE_CLASS_MAPPINGS
        assert NODE_CLASS_MAPPINGS["PSN_Number_List_Clamp"] is PSN_Number_List_Clamp
        assert PSN_Number_List_Clamp.RETURN_NAMES == ("first_value", "result_json")
        assert "does not touch CONDITIONING" in PSN_Number_List_Clamp.DESCRIPTION


class TestHelperFunctions:
    def test_clamp_vector_linear(self):
        vec = [-2.0, 0.5, 3.0]
        result = _clamp_vector(vec, -1.0, 1.0, "linear")
        expected = [-1.0, 0.5, 1.0]
        assert result == expected

    def test_clamp_vector_tanh(self):
        vec = [-1.0, 0.0, 1.0]
        result = _clamp_vector(vec, -1.0, 1.0, "tanh")
        expected = [math.tanh(-1.0), 0.0, math.tanh(1.0)]
        assert len(result) == len(expected)
        for r, e in zip(result, expected):
            assert abs(r - e) < 1e-6

    def test_parse_vector_json_valid(self):
        vec_str = "[1.0, 2.0, 3.0]"
        result = _parse_vector_json(vec_str)
        assert result == [1.0, 2.0, 3.0]

    def test_parse_vector_json_empty(self):
        result = _parse_vector_json("")
        assert result == []
        result = _parse_vector_json("[]")
        assert result == []

    def test_parse_vector_json_invalid_json(self):
        with pytest.raises(ValueError, match="Invalid JSON format"):
            _parse_vector_json("{invalid}")

    def test_parse_vector_json_not_list(self):
        with pytest.raises(ValueError, match="Parsed JSON must be a list"):
            _parse_vector_json("123")

    def test_parse_vector_json_non_numeric(self):
        with pytest.raises(ValueError, match="All elements in the vector must be numbers"):
            _parse_vector_json("[1.0, \"two\"]")
