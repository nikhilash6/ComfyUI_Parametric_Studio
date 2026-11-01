import torch

import n_7_multi_gpu_video_upscaling as mod
from n_7_multi_gpu_video_upscaling import (
    PSN_SplitBatchForGPU,
    PSN_NearestUpscaleBatch,
    PSN_MergeUpscaledBatches,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_batch(b, h, w, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand((b, h, w, c), generator=g)


# 1. Split 4-frame batch into 2 sub-batches of 2 frames each.
img = make_batch(4, 8, 8)
parts = PSN_SplitBatchForGPU().run(img, 2)
assert parts[0].shape == (2, 8, 8, 3), parts[0].shape
assert parts[1].shape == (2, 8, 8, 3), parts[1].shape
assert torch.equal(parts[0], img[0:2])
assert torch.equal(parts[1], img[2:4])

# 2. Uneven split: 5 frames into 2 -> sizes 3 and 2.
img5 = make_batch(5, 4, 4)
p5 = PSN_SplitBatchForGPU().run(img5, 2)
assert p5[0].shape[0] == 3 and p5[1].shape[0] == 2
assert torch.equal(p5[0], img5[0:3])
assert torch.equal(p5[1], img5[3:5])

# 3. Bad input: num_gpus > batch size raises.
try:
    PSN_SplitBatchForGPU().run(make_batch(2, 4, 4), 4)
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# 4. Bad input: non-tensor image raises TypeError.
try:
    PSN_SplitBatchForGPU().run("not a tensor", 2)
    raise AssertionError("expected TypeError")
except TypeError:
    pass

# 5. Bad input: wrong ndim raises ValueError.
try:
    PSN_NearestUpscaleBatch().run(torch.rand(4, 4, 3), 2)
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# 6. Upscale doubles spatial dims and preserves values (nearest = pick pixel).
small = make_batch(2, 4, 4)
res = PSN_NearestUpscaleBatch().run(small, 2)
assert len(res) == 1  # no gpu_id echo output
up = res[0]
assert up.shape == (2, 8, 8, 3), up.shape
# nearest-neighbour: upsampled pixel (0,0) equals original (0,0)
assert torch.equal(up[0, 0, 0], small[0, 0, 0])
assert torch.equal(up[0, 1, 1], small[0, 0, 0])
# input not modified in place
assert small.shape == (2, 4, 4, 3)

# 6b. every output pixel is its source pixel repeated scale x scale, scale=3.
tri, = PSN_NearestUpscaleBatch().run(small, 3)
assert tri.shape == (2, 12, 12, 3)
for y in range(12):
    for x in range(12):
        assert torch.equal(tri[1, y, x], small[1, y // 3, x // 3])
# the model/gpu_id inputs and the fabricated gpu_id output are gone
it = PSN_NearestUpscaleBatch.INPUT_TYPES()
assert list(it["required"]) == ["image_batch", "scale"] and "optional" not in it
assert PSN_NearestUpscaleBatch.RETURN_NAMES == ("upscaled_batch",)
assert not hasattr(mod, "PSN_UpscaleOnGPU")
try:
    PSN_NearestUpscaleBatch().run(small, 0)
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# 7. scale=1 is a no-op (values identical, new tensor).
up1, = PSN_NearestUpscaleBatch().run(small, 1)
assert up1.shape == small.shape
assert torch.equal(up1, small)

# 8. Full pipeline: split -> upscale each -> merge restores frame order.
img = make_batch(4, 6, 6)
parts = PSN_SplitBatchForGPU().run(img, 2)
up0, = PSN_NearestUpscaleBatch().run(parts[0], 2)
up1, = PSN_NearestUpscaleBatch().run(parts[1], 2)
merged = PSN_MergeUpscaledBatches().run(up0, extra_1=up1)[0]
assert merged.shape == (4, 12, 12, 3), merged.shape
assert torch.equal(merged[0], up0[0])
assert torch.equal(merged[3], up1[1])

# 9. Merge with empty sub-batch skips it.
empty = torch.empty((0, 12, 12, 3))
m2 = PSN_MergeUpscaledBatches().run(up0, extra_1=empty)[0]
assert m2.shape == (2, 12, 12, 3)

# 10. Merge mismatched spatial shapes raises.
try:
    PSN_MergeUpscaledBatches().run(up0, extra_1=torch.rand(1, 5, 5, 3))
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# 11. Module-level mappings exist and are consistent.
assert set(NODE_CLASS_MAPPINGS) == {"PSN_SplitBatchForGPU", "PSN_NearestUpscaleBatch", "PSN_MergeUpscaledBatches"}
for name, cls in NODE_CLASS_MAPPINGS.items():
    assert name in NODE_DISPLAY_NAME_MAPPINGS
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")
    assert hasattr(cls, "INPUT_TYPES") and callable(cls.INPUT_TYPES)
    it = cls.INPUT_TYPES()
    assert "required" in it

# 12. Split with num_gpus == batch size gives one frame each.
one = PSN_SplitBatchForGPU().run(make_batch(3, 2, 2), 3)
assert all(p.shape[0] == 1 for p in one[:3])

print('ok')
