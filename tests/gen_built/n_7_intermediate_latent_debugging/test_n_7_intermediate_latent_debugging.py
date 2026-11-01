import torch

import n_7_intermediate_latent_debugging as mod
from n_7_intermediate_latent_debugging import (
    PSN_Peek_Visualizer,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_mappings():
    assert list(NODE_CLASS_MAPPINGS) == ["PSN_Peek_Visualizer"]
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Peek_Visualizer"] == "PSN Peek Visualizer"
    # the fake sampler and its helpers are gone
    assert not hasattr(mod, "PSN_Peek_Sampler")
    assert not hasattr(mod, "_default_denoise")
    assert not hasattr(mod, "_default_decode")
    assert "PSN_Peek_Sampler" not in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types():
    it2 = PSN_Peek_Visualizer.INPUT_TYPES()
    assert list(it2["required"]) == ["peeks"]
    assert PSN_Peek_Visualizer.RETURN_TYPES == ("IMAGE",)
    assert PSN_Peek_Visualizer.FUNCTION == "run"
    assert PSN_Peek_Visualizer.CATEGORY.startswith("ParametricStudio/")


def test_visualizer_grid_1x3():
    """3 peek images [3,8,8,3] -> grid [1,8,24,3] (1 row, 3 cols)."""
    node = PSN_Peek_Visualizer()
    peeks = torch.randn(3, 8, 8, 3)
    grid = node.run(peeks=peeks)[0]
    assert grid.shape == (1, 8, 24, 3)


def test_visualizer_single_image():
    node = PSN_Peek_Visualizer()
    peeks = torch.randn(1, 4, 4, 3)
    grid = node.run(peeks=peeks)[0]
    assert grid.shape == (1, 4, 4, 3)
    assert torch.equal(grid[0], peeks[0])


def test_visualizer_empty_peeks():
    """Empty peeks tensor should raise."""
    node = PSN_Peek_Visualizer()
    try:
        node.run(peeks=torch.zeros((0, 8, 8, 3)))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_visualizer_bad_dim():
    """3D tensor should raise."""
    node = PSN_Peek_Visualizer()
    try:
        node.run(peeks=torch.randn(8, 8, 3))
        assert False, "expected ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    test_module_mappings()
    test_input_types()
    test_visualizer_grid_1x3()
    test_visualizer_single_image()
    test_visualizer_empty_peeks()
    test_visualizer_bad_dim()
    print("ok")
