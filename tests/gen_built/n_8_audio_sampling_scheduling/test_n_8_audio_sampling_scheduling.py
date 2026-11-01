"""Tests for n_8_audio_sampling_scheduling."""

import torch

import n_8_audio_sampling_scheduling as mod
from n_8_audio_sampling_scheduling import (
    PSN_AudioScheduler,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_scheduler_linear():
    node = PSN_AudioScheduler()
    (sigmas,) = node.run(steps=10, scheduler_type="Linear", sigma_max=1.0, sigma_min=0.001)
    assert isinstance(sigmas, torch.Tensor)
    assert sigmas.dim() == 1
    assert sigmas.numel() == 11  # steps + 1
    assert sigmas[0].item() == 1.0
    assert sigmas[-1].item() == 0.0
    # Monotonically decreasing
    for i in range(len(sigmas) - 1):
        assert sigmas[i].item() >= sigmas[i + 1].item()


def test_scheduler_karras():
    node = PSN_AudioScheduler()
    (sigmas,) = node.run(steps=20, scheduler_type="Karras", sigma_max=1.0, sigma_min=0.001)
    assert sigmas.numel() == 21
    assert sigmas[0].item() == 1.0
    assert sigmas[-1].item() == 0.0
    for i in range(len(sigmas) - 1):
        assert sigmas[i].item() >= sigmas[i + 1].item()


def test_scheduler_audio_optimized():
    node = PSN_AudioScheduler()
    (sigmas,) = node.run(steps=15, scheduler_type="AudioOptimized", sigma_max=1.0, sigma_min=0.001)
    assert sigmas.numel() == 16
    assert sigmas[0].item() == 1.0
    assert sigmas[-1].item() == 0.0
    for i in range(len(sigmas) - 1):
        assert sigmas[i].item() >= sigmas[i + 1].item()


def test_scheduler_bad_steps():
    node = PSN_AudioScheduler()
    try:
        node.run(steps=0, scheduler_type="Linear", sigma_max=1.0, sigma_min=0.001)
        assert False, "should have raised"
    except ValueError:
        pass


def test_scheduler_bad_sigma():
    node = PSN_AudioScheduler()
    try:
        node.run(steps=10, scheduler_type="Linear", sigma_max=0.5, sigma_min=0.5)
        assert False, "should have raised"
    except ValueError:
        pass


def test_linear_values():
    """Linear schedule: exact evenly spaced values then a final 0."""
    (sigmas,) = PSN_AudioScheduler().run(steps=5, scheduler_type="Linear", sigma_max=1.0, sigma_min=0.2)
    assert torch.allclose(sigmas, torch.tensor([1.0, 0.8, 0.6, 0.4, 0.2, 0.0]), atol=1e-6)


def test_node_mappings():
    assert list(NODE_CLASS_MAPPINGS) == ["PSN_AudioScheduler"]
    assert list(NODE_DISPLAY_NAME_MAPPINGS) == ["PSN_AudioScheduler"]
    # the ramp-producing sampler and its helpers are gone
    assert not hasattr(mod, "PSN_AudioSampler")
    assert not hasattr(mod, "_latent_samples")


def test_input_types():
    it = PSN_AudioScheduler.INPUT_TYPES()
    assert "required" in it
    assert "steps" in it["required"]
    assert "scheduler_type" in it["required"]


if __name__ == "__main__":
    test_scheduler_linear()
    test_scheduler_karras()
    test_scheduler_audio_optimized()
    test_scheduler_bad_steps()
    test_scheduler_bad_sigma()
    test_linear_values()
    test_node_mappings()
    test_input_types()
    print("ok")
