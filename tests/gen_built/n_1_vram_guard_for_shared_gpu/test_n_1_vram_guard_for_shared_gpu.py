"""Tests for n_1_vram_guard_for_shared_gpu (CPU only, no pytest)."""

import math
import torch

from n_1_vram_guard_for_shared_gpu import (
    PSN_VRAM_Budget_Gate,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _estimate_step_gb,
    _current_vram_gb,
)


def _latent(b=1, c=4, h=8, w=8):
    return {"samples": torch.zeros(b, c, h, w)}


def _tiny_model():
    return torch.nn.Linear(4, 4)


def test_registry():
    assert "PSN_VRAM_Budget_Gate" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_VRAM_Budget_Gate"] is PSN_VRAM_Budget_Gate
    assert "PSN_VRAM_Budget_Gate" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_VRAM_Budget_Gate"], str)


def test_input_types_shape():
    it = PSN_VRAM_Budget_Gate.INPUT_TYPES()
    assert "required" in it and "optional" in it
    for k in ("model", "latent", "max_vram_gb", "run_id"):
        assert k in it["required"], k
    assert it["required"]["model"] == ("MODEL",)
    assert it["required"]["latent"] == ("LATENT",)
    assert PSN_VRAM_Budget_Gate.RETURN_TYPES == ("MODEL", "LATENT", "FLOAT")
    assert PSN_VRAM_Budget_Gate.RETURN_NAMES == ("model", "latent", "vram_usage_gb")
    assert PSN_VRAM_Budget_Gate.FUNCTION == "run"
    assert PSN_VRAM_Budget_Gate.CATEGORY.startswith("ParametricStudio/")


def test_pass_through_when_budget_ok():
    node = PSN_VRAM_Budget_Gate()
    m = _tiny_model()
    lat = _latent()
    out_m, out_lat, usage = node.run(m, lat, max_vram_gb=100.0, run_id="t1", probe_gb=1.0)
    # budget respected -> model unchanged (same object), latent dict is a copy
    assert out_m is m
    assert out_lat is not lat
    assert torch.equal(out_lat["samples"], lat["samples"])
    assert usage == 1.0


def test_offload_when_budget_breached():
    node = PSN_VRAM_Budget_Gate()
    m = _tiny_model()
    lat = _latent()
    # probe_gb huge -> projected > max -> offload path
    out_m, out_lat, usage = node.run(m, lat, max_vram_gb=0.5, run_id="t2", probe_gb=100.0)
    assert usage == 100.0
    # model must be on CPU (it already was, but the call path must not crash)
    assert isinstance(out_m, torch.nn.Module)
    # latent still intact
    assert torch.equal(out_lat["samples"], lat["samples"])


def test_hard_stop_raises():
    node = PSN_VRAM_Budget_Gate()
    m = _tiny_model()
    lat = _latent()
    try:
        node.run(m, lat, max_vram_gb=0.5, run_id="t3", hard_stop=True, probe_gb=100.0)
    except RuntimeError as e:
        msg = str(e)
        assert "VRAM budget exceeded" in msg
        assert "t3" in msg
    else:
        raise AssertionError("expected RuntimeError")


def test_bad_latent_not_dict():
    node = PSN_VRAM_Budget_Gate()
    try:
        node.run(_tiny_model(), "not-a-dict", max_vram_gb=10.0, run_id="t4")
    except ValueError as e:
        assert "latent" in str(e)
    else:
        raise AssertionError("expected ValueError for non-dict latent")


def test_bad_latent_samples_not_tensor():
    node = PSN_VRAM_Budget_Gate()
    try:
        node.run(_tiny_model(), {"samples": [1, 2, 3]}, max_vram_gb=10.0, run_id="t5")
    except ValueError as e:
        assert "samples" in str(e)
    else:
        raise AssertionError("expected ValueError for non-tensor samples")


def test_bad_latent_wrong_dims():
    node = PSN_VRAM_Budget_Gate()
    bad = {"samples": torch.zeros(2, 3)}  # 2-D, not 4-D
    try:
        node.run(_tiny_model(), bad, max_vram_gb=10.0, run_id="t6")
    except ValueError as e:
        assert "[B, C, H, W]" in str(e)
    else:
        raise AssertionError("expected ValueError for wrong-dim samples")


def test_bad_max_vram():
    node = PSN_VRAM_Budget_Gate()
    lat = _latent()
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        try:
            node.run(_tiny_model(), lat, max_vram_gb=bad, run_id="t7")
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for max_vram_gb={bad!r}")


def test_bad_run_id():
    node = PSN_VRAM_Budget_Gate()
    try:
        node.run(_tiny_model(), _latent(), max_vram_gb=10.0, run_id=123)
    except ValueError as e:
        assert "run_id" in str(e)
    else:
        raise AssertionError("expected ValueError for non-string run_id")


def test_estimate_monotonic_in_latent_size():
    small = _estimate_step_gb(_latent(b=1, c=4, h=4, w=4), _tiny_model())
    big = _estimate_step_gb(_latent(b=4, c=16, h=32, w=32), _tiny_model())
    assert big > small > 0.0


def test_no_in_place_mutation():
    node = PSN_VRAM_Budget_Gate()
    m = _tiny_model()
    lat = _latent()
    original = lat["samples"].clone()
    node.run(m, lat, max_vram_gb=100.0, run_id="t8", probe_gb=0.1)
    assert torch.equal(lat["samples"], original)
    assert set(lat.keys()) == {"samples"}


def test_usage_is_device_wide_not_process_allocated():
    # total 96 GB, free 30 GB -> 66 GB used by all processes; this process allocated 0
    gb = 1024.0 ** 3
    orig_avail, orig_info, orig_alloc = torch.cuda.is_available, torch.cuda.mem_get_info, torch.cuda.memory_allocated
    torch.cuda.is_available = lambda: True
    torch.cuda.mem_get_info = lambda *a, **k: (int(30 * gb), int(96 * gb))
    torch.cuda.memory_allocated = lambda *a, **k: 0
    try:
        assert abs(_current_vram_gb() - 66.0) < 1e-6
        node = PSN_VRAM_Budget_Gate()
        _, _, usage = node.run(_tiny_model(), _latent(), max_vram_gb=100.0, run_id="t9")
        assert abs(usage - 66.0) < 1e-6
        try:
            node.run(_tiny_model(), _latent(), max_vram_gb=60.0, run_id="t9b", hard_stop=True)
        except RuntimeError as e:
            assert "current=66.000" in str(e)
        else:
            raise AssertionError("66 GB used card-wide must breach a 60 GB budget")
    finally:
        torch.cuda.is_available, torch.cuda.mem_get_info, torch.cuda.memory_allocated = orig_avail, orig_info, orig_alloc


def test_offload_only_for_module_and_reports_otherwise():
    class Recorder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.l = torch.nn.Linear(2, 2)
            self.moved_to = None

        def to(self, *a, **k):
            self.moved_to = a[0]
            return self

    node = PSN_VRAM_Budget_Gate()
    rec = Recorder()
    out, _, _ = node.run(rec, _latent(), max_vram_gb=0.5, run_id="t10", probe_gb=100.0)
    assert out is rec and rec.moved_to == "cpu", "an nn.Module is offloaded to cpu on breach"
    patcher = object()  # stands in for a ComfyUI ModelPatcher: not an nn.Module
    out2, _, usage = node.run(patcher, _latent(), max_vram_gb=0.5, run_id="t11", probe_gb=100.0)
    assert out2 is patcher and usage == 100.0, "non-Module MODEL is passed through, breach only reported"
    assert "ModelPatcher" in PSN_VRAM_Budget_Gate.DESCRIPTION


def main():
    test_registry()
    test_input_types_shape()
    test_pass_through_when_budget_ok()
    test_offload_when_budget_breached()
    test_hard_stop_raises()
    test_bad_latent_not_dict()
    test_bad_latent_samples_not_tensor()
    test_bad_latent_wrong_dims()
    test_bad_max_vram()
    test_bad_run_id()
    test_estimate_monotonic_in_latent_size()
    test_no_in_place_mutation()
    test_usage_is_device_wide_not_process_allocated()
    test_offload_only_for_module_and_reports_otherwise()
    print("ok")


if __name__ == "__main__":
    main()
