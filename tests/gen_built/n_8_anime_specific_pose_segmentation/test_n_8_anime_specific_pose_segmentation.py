import torch

import n_8_anime_specific_pose_segmentation as mod
from n_8_anime_specific_pose_segmentation import (
    PSN_BandColorThresholdMask,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

RULES = ["dark_unsaturated_top60", "bright_top40", "reddish_band_30_55", "midtone_below_30"]


def _make_image(b=1, h=64, w=64, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(b, h, w, c, generator=g)


def _solid(h, w, rgb):
    return torch.tensor(rgb, dtype=torch.float32).view(1, 1, 1, 3).expand(1, h, w, 3).contiguous()


# 1. the pose node and the feature-named node are gone
assert set(NODE_CLASS_MAPPINGS) == {"PSN_BandColorThresholdMask"}
assert NODE_CLASS_MAPPINGS["PSN_BandColorThresholdMask"] is PSN_BandColorThresholdMask
assert set(NODE_DISPLAY_NAME_MAPPINGS) == set(NODE_CLASS_MAPPINGS)
assert not hasattr(mod, "PSN_Anime_Pose_Estimator")
assert not hasattr(mod, "PSN_Anime_Segmentor")
assert not hasattr(mod, "_estimate_keypoints")
assert not hasattr(mod, "_POSE_KEYPOINTS")

# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY / DESCRIPTION
it = PSN_BandColorThresholdMask.INPUT_TYPES()
assert list(it["required"]) == ["image", "rule"]
assert it["required"]["rule"][0] == RULES  # rules named for what they do
assert PSN_BandColorThresholdMask.RETURN_TYPES == ("MASK",)
assert PSN_BandColorThresholdMask.FUNCTION == "run"
assert PSN_BandColorThresholdMask.CATEGORY.startswith("ParametricStudio/")
assert "not a feature detector" in PSN_BandColorThresholdMask.DESCRIPTION.lower()

node = PSN_BandColorThresholdMask()

# 3. all rules give a MASK [B,H,W] in 0..1
img2 = _make_image(2, 32, 24, 3, seed=2)
for rule in RULES:
    (m,) = node.run(img2, rule)
    assert m.shape == (2, 32, 24)
    assert m.min() >= 0.0 and m.max() <= 1.0

# 4. real values: dark grey image selects only rows 0..59% (h=100 -> rows 0-59)
(m,) = node.run(_solid(100, 8, (0.1, 0.1, 0.1)), "dark_unsaturated_top60")
assert m[0, :60].min() == 1.0 and m[0, 60:].max() == 0.0
# saturated dark red is excluded by the saturation limit
(m,) = node.run(_solid(100, 8, (0.3, 0.0, 0.0)), "dark_unsaturated_top60")
assert m.max() == 0.0

# 5. bright pixels only in rows 0..39
(m,) = node.run(_solid(100, 8, (0.9, 0.9, 0.9)), "bright_top40")
assert m[0, :40].min() == 1.0 and m[0, 40:].max() == 0.0
(m,) = node.run(_solid(100, 8, (0.5, 0.5, 0.5)), "bright_top40")
assert m.max() == 0.0

# 6. red only in rows 30..54; a red image has no mask outside the band
(m,) = node.run(_solid(100, 8, (0.9, 0.1, 0.1)), "reddish_band_30_55")
assert m[0, 30:55].min() == 1.0 and m[0, :30].max() == 0.0 and m[0, 55:].max() == 0.0
(m,) = node.run(_solid(100, 8, (0.1, 0.1, 0.9)), "reddish_band_30_55")
assert m.max() == 0.0

# 7. midtones from row 30 down; black and white are excluded
(m,) = node.run(_solid(100, 8, (0.5, 0.5, 0.5)), "midtone_below_30")
assert m[0, 30:].min() == 1.0 and m[0, :30].max() == 0.0
assert node.run(_solid(100, 8, (0.0, 0.0, 0.0)), "midtone_below_30")[0].max() == 0.0
assert node.run(_solid(100, 8, (1.0, 1.0, 1.0)), "midtone_below_30")[0].max() == 0.0

# 8. bad input: wrong type raises TypeError, wrong shape raises ValueError
try:
    node.run("not a tensor", RULES[0])
    assert False, "expected TypeError"
except TypeError:
    pass
try:
    node.run(torch.rand(4, 4, 3), RULES[0])  # 3D, not 4D
    assert False, "expected ValueError"
except ValueError:
    pass

# 9. bad input: unknown rule (including the old feature names) raises ValueError
for bad in ("fingers", "hair", "eyes", "mouth", "body"):
    try:
        node.run(img2, bad)
        assert False, "expected ValueError"
    except ValueError:
        pass

# 10. input is not modified in place
img3 = _make_image(1, 16, 16, 3, seed=3)
before = img3.clone()
for rule in RULES:
    node.run(img3, rule)
assert torch.equal(img3, before)

# 11. 4-channel images work
assert node.run(_make_image(1, 16, 16, 4), RULES[0])[0].shape == (1, 16, 16)

print("ok")
