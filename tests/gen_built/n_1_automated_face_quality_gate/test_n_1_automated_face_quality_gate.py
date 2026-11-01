import torch

import n_1_automated_face_quality_gate as mod
from n_1_automated_face_quality_gate import (
    PSN_Image_Sharpness_Noise_Score,
    PSN_QualityGateRouter,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_sharp_image(seed=0):
    """A high-contrast checkerboard: strong edges -> high sharpness, low noise."""
    g = torch.Generator().manual_seed(seed)
    y = torch.arange(32, dtype=torch.float32).view(1, 32, 1)
    x = torch.arange(32, dtype=torch.float32).view(1, 1, 32)
    cell = ((y // 8).long() + (x // 8).long()) % 2
    base = torch.where(cell == 0, torch.ones(1, 32, 32), torch.zeros(1, 32, 32))
    return base.unsqueeze(-1).expand(1, 32, 32, 3).clone()


def make_noisy_image(seed=1):
    """A flat image with heavy noise: low sharpness, high artifact score penalty."""
    g = torch.Generator().manual_seed(seed)
    noise = torch.rand(1, 32, 32, 3, generator=g)
    return 0.5 + 0.4 * (noise - 0.5)


def test_module_mappings():
    assert "PSN_Image_Sharpness_Noise_Score" in NODE_CLASS_MAPPINGS
    assert "PSN_QualityGateRouter" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Image_Sharpness_Noise_Score"]
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_QualityGateRouter"]
    assert "PSN_FaceQualityScorer" not in NODE_CLASS_MAPPINGS
    assert not hasattr(mod, "PSN_FaceQualityScorer")
    assert not hasattr(mod, "_identity_similarity")
    desc = PSN_Image_Sharpness_Noise_Score.DESCRIPTION
    assert "no face detection" in desc and "not face identity" in desc


def test_input_types_shape():
    it = PSN_Image_Sharpness_Noise_Score.INPUT_TYPES()
    assert "IMAGE" in it["required"]
    assert "THRESHOLD" in it["required"]
    assert "CORRELATION_REFERENCE" in it["optional"]
    it2 = PSN_QualityGateRouter.INPUT_TYPES()
    assert "IMAGE" in it2["required"]
    assert "PASS" in it2["required"]
    assert "FALLBACK_IMAGE" in it2["optional"]


def test_scorer_exact_score_values():
    node = PSN_Image_Sharpness_Noise_Score()
    # flat gray image: zero Laplacian energy (sharp 0), zero noise (clean 1) -> 0.4
    flat = torch.full((1, 16, 16, 3), 0.5)
    _, score, passed = node.run(flat, 0.5)
    assert abs(score - 0.4) < 1e-6 and passed is False
    # threshold exactly at the score passes
    _, _, passed = node.run(flat, 0.4)
    assert passed is True
    # the reference adds 0.3 * correlation; identical non-flat images correlate to 1
    img = make_sharp_image()
    _, s_plain, _ = node.run(img, 0.0)
    _, s_ref, _ = node.run(img, 0.0, CORRELATION_REFERENCE=img)
    sharp, clean = mod._sharpness(mod._to_gray(img)), mod._artifact_score(mod._to_gray(img))
    assert abs(s_plain - (0.6 * sharp + 0.4 * clean)) < 1e-6
    assert abs(s_ref - (0.4 * sharp + 0.3 * clean + 0.3 * 1.0)) < 1e-5


def test_scorer_sharp_passes():
    node = PSN_Image_Sharpness_Noise_Score()
    img = make_sharp_image()
    out_img, score, passed = node.run(img, 0.5)
    assert isinstance(out_img, torch.Tensor)
    assert out_img.shape == img.shape
    assert 0.0 <= score <= 1.0
    assert passed is True
    # Input must not be modified in place.
    assert not torch.equal(out_img, img) or out_img.data_ptr() != img.data_ptr()


def test_scorer_noisy_fails():
    node = PSN_Image_Sharpness_Noise_Score()
    img = make_noisy_image()
    _, score, passed = node.run(img, 0.75)
    assert passed is False
    assert score < 0.75


def test_scorer_with_reference():
    node = PSN_Image_Sharpness_Noise_Score()
    img = make_sharp_image()
    ref = make_sharp_image()
    _, score_same, _ = node.run(img, 0.0, CORRELATION_REFERENCE=ref)
    ref2 = make_noisy_image()
    _, score_diff, _ = node.run(img, 0.0, CORRELATION_REFERENCE=ref2)
    assert score_same > score_diff


def test_scorer_bad_input():
    node = PSN_Image_Sharpness_Noise_Score()
    try:
        node.run(torch.zeros(4, 32, 32), 0.5)  # wrong dims
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        node.run(torch.zeros(1, 32, 32, 5), 0.5)  # bad channel count
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        node.run(torch.ones(1, 32, 32, 3) * 2.0, 0.5)  # out of range
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        node.run("not a tensor", 0.5)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass


def test_router_pass():
    node = PSN_QualityGateRouter()
    img = make_sharp_image()
    out = node.run(img, True)[0]
    assert torch.allclose(out, img)


def test_router_fallback():
    node = PSN_QualityGateRouter()
    img = make_noisy_image()
    fb = make_sharp_image()
    out = node.run(img, False, FALLBACK_IMAGE=fb)[0]
    assert torch.allclose(out, fb)


def test_router_no_fallback_flat_gray():
    node = PSN_QualityGateRouter()
    img = make_noisy_image()
    out = node.run(img, False)[0]
    assert out.shape == img.shape
    assert torch.allclose(out, torch.full_like(out, 0.5))


def test_batch_and_inplace_safety():
    node = PSN_Image_Sharpness_Noise_Score()
    img = make_sharp_image().repeat(3, 1, 1, 1)
    snapshot = img.clone()
    out_img, score, passed = node.run(img, 0.5)
    assert out_img.shape[0] == 3
    assert torch.equal(img, snapshot), "input was modified in place"


if __name__ == "__main__":
    test_module_mappings()
    test_input_types_shape()
    test_scorer_exact_score_values()
    test_scorer_sharp_passes()
    test_scorer_noisy_fails()
    test_scorer_with_reference()
    test_scorer_bad_input()
    test_router_pass()
    test_router_fallback()
    test_router_no_fallback_flat_gray()
    test_batch_and_inplace_safety()
    print("ok")
