import math

import torch

from n_1_text_to_motion_pipeline_validation import (
    PSN_Random_Motion_Test_Fixture,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    STATUS_OK,
    STATUS_BAD_DURATION,
    STATUS_BAD_SEED,
    NUM_JOINTS,
    FPS,
)

node = PSN_Random_Motion_Test_Fixture()

# 1. Basic successful run: check output types, shapes, and status
motion_data, bvh_string, status = node.run(duration=2.0, seed=42)

assert status == STATUS_OK, "status should be 0 on success, got %r" % status
assert isinstance(motion_data, dict), "motion_data should be a dict"
assert "rotations" in motion_data, "motion_data must contain 'rotations'"
assert "translations" in motion_data, "motion_data must contain 'translations'"

rot = motion_data["rotations"]
trans = motion_data["translations"]

expected_frames = int(round(2.0 * FPS))
assert rot.shape == (expected_frames, NUM_JOINTS, 3), \
    "rotations shape mismatch: %s" % (rot.shape,)
assert trans.shape == (expected_frames, NUM_JOINTS, 3), \
    "translations shape mismatch: %s" % (trans.shape,)
assert isinstance(rot, torch.Tensor), "rotations should be a torch.Tensor"
assert isinstance(trans, torch.Tensor), "translations should be a torch.Tensor"

# 2. BVH string is non-empty and structurally valid
assert isinstance(bvh_string, str), "bvh_string should be a str"
assert len(bvh_string) > 0, "bvh_string should not be empty"
assert bvh_string.startswith("HIERARCHY"), "BVH should start with HIERARCHY"
assert "MOTION" in bvh_string, "BVH should contain MOTION section"
assert "Frames: %d" % expected_frames in bvh_string, \
    "BVH should declare the correct frame count"

# 3. Reproducibility: same seed + params -> identical output
md1, bvh1, st1 = node.run(1.0, 123)
md2, bvh2, st2 = node.run(1.0, 123)
assert st1 == STATUS_OK and st2 == STATUS_OK
assert torch.equal(md1["rotations"], md2["rotations"]), \
    "same seed should give identical rotations"
assert torch.equal(md1["translations"], md2["translations"]), \
    "same seed should give identical translations"
assert bvh1 == bvh2, "same seed should give identical BVH string"

# 4. Different seed -> different output
md3, _, _ = node.run(1.0, 999)
assert not torch.equal(md1["rotations"], md3["rotations"]), \
    "different seeds should give different rotations"

# 7. Bad duration (zero) -> STATUS_BAD_DURATION
_, _, st = node.run(0.0, 42)
assert st == STATUS_BAD_DURATION, "zero duration should give STATUS_BAD_DURATION, got %r" % st

# 8. Bad duration (negative) -> STATUS_BAD_DURATION
_, _, st = node.run(-1.0, 42)
assert st == STATUS_BAD_DURATION, "negative duration should give STATUS_BAD_DURATION, got %r" % st

# 10. Bad seed (negative) -> STATUS_BAD_SEED
_, _, st = node.run(2.0, -1)
assert st == STATUS_BAD_SEED, "negative seed should give STATUS_BAD_SEED, got %r" % st

# 11. Output is exactly the seeded noise: re-derive it independently and compare
g = torch.Generator(device="cpu"); g.manual_seed(42)
expect = torch.randn(30, NUM_JOINTS, 6, generator=g) * 0.25
md, bvh, st = node.run(1.0, 42)
assert torch.equal(md["rotations"], expect[:, :, :3]), "rotations must equal the seeded noise"
assert torch.equal(md["translations"], expect[:, :, 3:]), "translations must equal the seeded noise"
# BVH first frame carries the hips Zrotation from that noise
first = bvh.strip().split("\n")[-30].split()
assert abs(float(first[0]) - float(expect[0, 0, 2])) < 1e-5

# 12. Node registration: NODE_CLASS_MAPPINGS and DISPLAY_NAME_MAPPINGS
assert "PSN_Random_Motion_Test_Fixture" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_Random_Motion_Test_Fixture"] is PSN_Random_Motion_Test_Fixture
assert "PSN_Random_Motion_Test_Fixture" in NODE_DISPLAY_NAME_MAPPINGS

# 13. INPUT_TYPES classmethod returns expected structure
it = PSN_Random_Motion_Test_Fixture.INPUT_TYPES()
assert "required" in it
assert set(it["required"]) == {"duration", "seed"}, "ignored prompt/model_type inputs must be gone"

# 14. RETURN_TYPES and RETURN_NAMES
assert PSN_Random_Motion_Test_Fixture.RETURN_TYPES == ("RANDOM_MOTION_DICT", "STRING", "INT")
assert PSN_Random_Motion_Test_Fixture.RETURN_NAMES == ("random_motion", "bvh_text", "status")
assert "not real motion" in PSN_Random_Motion_Test_Fixture.DESCRIPTION
assert "PSN_TextToMotion_Generate" not in NODE_CLASS_MAPPINGS
assert PSN_Random_Motion_Test_Fixture.FUNCTION == "run"
assert PSN_Random_Motion_Test_Fixture.CATEGORY == "ParametricStudio/Motion"

# 15. Inputs are not modified in place
orig_duration = 3.0
md, bvh, st = node.run(orig_duration, 7)
assert st == STATUS_OK
assert orig_duration == 3.0, "duration was modified in place"

# 16. Edge case: very short duration (0.1s -> 3 frames)
md, bvh, st = node.run(0.1, 0)
assert st == STATUS_OK
expected_frames = max(1, int(round(0.1 * FPS)))
assert md["rotations"].shape[0] == expected_frames, \
    "frame count for 0.1s should be %d, got %d" % (expected_frames, md["rotations"].shape[0])

# 17. Edge case: seed = 0 is valid
_, _, st = node.run(1.0, 0)
assert st == STATUS_OK, "seed=0 should be valid"

# 18. BVH frame data line count matches expected frames
md, bvh, st = node.run(1.0, 55)
assert st == STATUS_OK
lines = bvh.strip().split("\n")
motion_idx = None
for i, line in enumerate(lines):
    if line.strip() == "MOTION":
        motion_idx = i
        break
assert motion_idx is not None, "BVH should have a MOTION section"
frames_line = lines[motion_idx + 1]
assert frames_line.startswith("Frames:"), "line after MOTION should be Frames:"
declared_frames = int(frames_line.split(":")[1].strip())
data_lines = lines[motion_idx + 3:]
data_lines = [l for l in data_lines if l.strip()]
assert len(data_lines) == declared_frames, \
    "BVH data lines (%d) should match declared frames (%d)" % (len(data_lines), declared_frames)

print("ok")
