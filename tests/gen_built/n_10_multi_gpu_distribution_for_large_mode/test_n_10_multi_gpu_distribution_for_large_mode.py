"""Tests for n_10_multi_gpu_distribution_for_large_mode."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import n_10_multi_gpu_distribution_for_large_mode as mod
from n_10_multi_gpu_distribution_for_large_mode import (
    PSN_Device_Layer_Plan,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_device_map,
    _validate_device,
    _compute_layer_assignment,
)

# 1. registration; the fabricated parts are gone
assert list(NODE_CLASS_MAPPINGS) == ["PSN_Device_Layer_Plan"]
assert "PSN_Device_Layer_Plan" in NODE_DISPLAY_NAME_MAPPINGS
for gone in ("PSN_Distribute_Model", "PSN_Gather_Results", "_estimate_vram", "_simulate_distribution"):
    assert not hasattr(mod, gone), gone + " should be removed"
assert "does not move or split any model" in PSN_Device_Layer_Plan.DESCRIPTION

# 2. inputs / outputs
req = PSN_Device_Layer_Plan.INPUT_TYPES()["required"]
assert set(req) == {"device_map", "num_layers"}, "model and offload_threshold inputs must be gone"
assert PSN_Device_Layer_Plan.RETURN_TYPES == ("STRING",)
assert PSN_Device_Layer_Plan.RETURN_NAMES == ("layer_plan",)
assert PSN_Device_Layer_Plan.FUNCTION == "run"
assert PSN_Device_Layer_Plan.CATEGORY == "ParametricStudio/MultiGPU"

# 3. _parse_device_map
assert _parse_device_map("cuda:0,cuda:1") == ["cuda:0", "cuda:1"]
assert _parse_device_map("cpu") == ["cpu"]
assert _parse_device_map("cuda:0, cuda:1, cpu") == ["cuda:0", "cuda:1", "cpu"]
for bad in ("", None):
    try:
        _parse_device_map(bad)
        assert False, "should raise for %r" % (bad,)
    except ValueError:
        pass

# 4. _validate_device
for ok in ("cpu", "cuda:0", "cuda:1", "cuda"):
    _validate_device(ok)
for bad in ("cuda:abc", "tpu:0"):
    try:
        _validate_device(bad)
        assert False, "should raise for " + bad
    except ValueError:
        pass

# 5. round-robin assignment
assert _compute_layer_assignment(4, ["cuda:0", "cuda:1"]) == [[0, 2], [1, 3]]
assert _compute_layer_assignment(5, ["cuda:0", "cuda:1"]) == [[0, 2, 4], [1, 3]]
assert _compute_layer_assignment(1, ["cpu"]) == [[0]]
assert _compute_layer_assignment(3, ["cuda:0", "cuda:1", "cuda:2"]) == [[0], [1], [2]]

# 6. node output is exactly the text plan, with no byte estimates or offload claims
node = PSN_Device_Layer_Plan()
(plan,) = node.run("cuda:0,cuda:1", 5)
assert plan == "Device map: cuda:0, cuda:1\n  cuda:0: layers [0, 2, 4]\n  cuda:1: layers [1, 3]"
assert "bytes" not in plan and "Offloaded" not in plan

# 7. single device keeps every layer on that device, nothing is called offloaded
(plan,) = node.run("cuda:0", 3)
assert plan == "Device map: cuda:0\n  cuda:0: layers [0, 1, 2]"

# 8. bad device_map raises
for bad in ("", "tpu:0"):
    try:
        node.run(bad, 4)
        assert False, "should raise for %r" % bad
    except ValueError:
        pass

print("ok")
