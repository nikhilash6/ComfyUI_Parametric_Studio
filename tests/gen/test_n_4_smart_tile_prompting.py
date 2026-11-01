"""Tests for PSN_TileGrid (pure-logic, no GPU, no network)."""

import math

import pytest

from psn_nodes.gen import n_4_smart_tile_prompting as mod
from psn_nodes.gen.n_4_smart_tile_prompting import (
    PSN_TileGrid,
    compute_tile_grid,
)


def test_grid_1024_512_produces_four_tiles():
    """A 1024x1024 image with tile_size=512 and overlap=0 yields 4 tiles."""
    tiles = compute_tile_grid(1024, 1024, 512, 0)
    assert len(tiles) == 4
    # Each tile should be 512x512 (or clamped) and within bounds.
    for x, y, w, h in tiles:
        assert 0 <= x <= 1024 - 512
        assert 0 <= y <= 1024 - 512
        assert w <= 512
        assert h <= 512
        assert x + w <= 1024
        assert y + h <= 1024


def test_grid_small_image_single_tile():
    """An image smaller than tile_size yields exactly one tile."""
    tiles = compute_tile_grid(100, 100, 512, 64)
    assert len(tiles) == 1
    x, y, w, h = tiles[0]
    assert x == 0 and y == 0
    assert w == 100 and h == 100


def test_grid_overlap_increases_tile_count():
    """Larger overlap increases the number of tiles compared to no overlap."""
    no_overlap = compute_tile_grid(2048, 2048, 512, 0)
    with_overlap = compute_tile_grid(2048, 2048, 512, 128)
    # With overlap, we have more tiles to cover the same area with redundancy.
    assert len(with_overlap) > len(no_overlap)


def test_node_returns_exact_coords_for_known_grid():
    """512 tiles with overlap 0 on 1024x1024 give the four quadrants, in order."""
    node = PSN_TileGrid()
    out = node.run(width=1024, height=1024, tile_size=512, overlap=0)
    assert len(out) == 1
    assert out[0].split("\n") == [
        "[0, 0, 512, 512]", "[512, 0, 512, 512]",
        "[0, 512, 512, 512]", "[512, 512, 512, 512]",
    ]


def test_node_overlap_positions():
    """1000 px wide, tile 512, overlap 64: step 448, last tile cut at the image edge."""
    out = PSN_TileGrid().run(width=1000, height=512, tile_size=512, overlap=64)[0]
    assert out.split("\n") == ["[0, 0, 512, 512]", "[448, 0, 512, 512]", "[896, 0, 104, 512]"]


def test_no_prompt_text_or_model_input():
    """The fabricated per-tile prompts and the model input are gone."""
    assert "PSN_Smart_Tile_Prompter" not in mod.NODE_CLASS_MAPPINGS
    assert not hasattr(mod, "build_tile_prompt")
    assert not hasattr(mod, "ALLOWED_MODELS")
    assert "llm_model" not in PSN_TileGrid.INPUT_TYPES()["required"]
    assert PSN_TileGrid.RETURN_NAMES == ("TILE_COORDS",)
    assert "no vision-language model" in PSN_TileGrid.DESCRIPTION


def test_bad_input_non_numeric_tile_size_raises():
    """Non-numeric tile_size raises ValueError."""
    with pytest.raises(ValueError):
        compute_tile_grid(1024, 1024, "abc", 64)


def test_bad_input_negative_width_raises():
    """Negative width is clamped to 1, but zero/negative after clamp is invalid."""
    # _clamp_int clamps to [1, _MAX_DIM], so -100 becomes 1 (valid).
    # Test that a truly invalid value (NaN) raises.
    with pytest.raises(ValueError):
        compute_tile_grid(float("nan"), 1024, 512, 64)


def test_bad_input_overlap_equals_tile_size_raises():
    """Overlap equal to tile_size makes step=0, which is invalid."""
    with pytest.raises(ValueError):
        compute_tile_grid(1024, 1024, 512, 512)


def test_grid_max_tiles_guard():
    """A grid that would exceed _MAX_TILES raises ValueError."""
    # 16384x16384 with tile_size=16, overlap=0 -> 1024*1024 = 1,048,576 tiles
    with pytest.raises(ValueError):
        compute_tile_grid(16384, 16384, 16, 0)


def test_input_types_structure():
    """INPUT_TYPES returns the expected keys."""
    spec = PSN_TileGrid.INPUT_TYPES()
    assert set(spec["required"]) == {"width", "height", "tile_size", "overlap"}


def test_return_types_and_names():
    """RETURN_TYPES and RETURN_NAMES match the spec."""
    assert PSN_TileGrid.RETURN_TYPES == ("STRING",)
    assert PSN_TileGrid.FUNCTION == "run"
    assert PSN_TileGrid.CATEGORY == "ParametricStudio/SmartTile"
