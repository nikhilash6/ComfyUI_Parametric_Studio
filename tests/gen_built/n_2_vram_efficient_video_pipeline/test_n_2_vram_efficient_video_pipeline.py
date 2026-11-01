"""Tests for n_2_vram_efficient_video_pipeline.

Run with:  python3 -B test_n_2_vram_efficient_video_pipeline.py
Must print 'ok' and exit 0.
"""

import torch

from n_2_vram_efficient_video_pipeline import (
    PSN_Synthetic_Latent_Frame,
    PSN_Latent_RGB_Stack,
    PSN_Synthetic_Latent_Loop,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _latent_samples,
    _make_latent,
    _latent_rgb_frames,
)


def test_mappings():
    assert "PSN_Synthetic_Latent_Frame" in NODE_CLASS_MAPPINGS
    assert "PSN_Latent_RGB_Stack" in NODE_CLASS_MAPPINGS
    assert "PSN_Synthetic_Latent_Loop" in NODE_CLASS_MAPPINGS
    for k in NODE_CLASS_MAPPINGS:
        assert k in NODE_DISPLAY_NAME_MAPPINGS, k
        assert NODE_CLASS_MAPPINGS[k].FUNCTION == "run", k
        assert NODE_CLASS_MAPPINGS[k].CATEGORY.startswith("ParametricStudio"), k
    print("  1. mappings ok")


def test_generator_first_frame():
    gen = PSN_Synthetic_Latent_Frame()
    cur, nxt = gen.run(
        frame_index=0,
        total_frames=4,
        steps=20,
        cfg=7.0,
        seed=42,
    )
    assert isinstance(cur, dict) and "samples" in cur
    assert isinstance(nxt, dict) and "samples" in nxt
    x = cur["samples"]
    assert x.dim() == 4, "expected 4-D latent"
    assert x.shape[0] == 1, "batch should be 1"
    assert x.min() >= 0.0 and x.max() <= 1.0
    assert nxt["samples"] is not cur["samples"]
    assert torch.equal(nxt["samples"], cur["samples"])
    print("  2. generator first frame ok")


def test_generator_temporal():
    gen = PSN_Synthetic_Latent_Frame()
    prev = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    cur, nxt = gen.run(
        frame_index=1,
        total_frames=4,
        steps=20,
        cfg=7.0,
        seed=42,
        prev_latent=prev,
    )
    x = cur["samples"]
    assert x.shape == (1, 4, 8, 8)
    assert x.min() >= 0.0 and x.max() <= 1.0
    assert not torch.equal(x, prev["samples"])
    assert abs(x.mean().item() - 0.5) < 0.3
    print("  3. generator temporal ok")


def test_generator_bad_frame_index():
    gen = PSN_Synthetic_Latent_Frame()
    try:
        gen.run(
            frame_index=5,
            total_frames=4,
            steps=20,
            cfg=7.0,
                    seed=42,
        )
        assert False, "should have raised ValueError"
    except ValueError as e:
        assert "frame_index" in str(e)
    print("  4. generator bad frame_index ok")


def test_generator_bad_prev_latent():
    gen = PSN_Synthetic_Latent_Frame()
    try:
        gen.run(
            frame_index=0,
            total_frames=4,
            steps=20,
            cfg=7.0,
                    seed=42,
            prev_latent="not a latent",
        )
        assert False, "should have raised ValueError"
    except ValueError:
        pass
    print("  5. generator bad prev_latent ok")


def test_assembler_4_frames():
    loop = PSN_Synthetic_Latent_Loop()
    (latents,) = loop.run(
        total_frames=4,
        steps=20,
        cfg=7.0,
        seed=42,
    )
    assert isinstance(latents, list) and len(latents) == 4
    asm = PSN_Latent_RGB_Stack()
    (video,) = asm.run(latents)
    assert isinstance(video, torch.Tensor)
    assert video.shape == (4, 8, 8, 3), video.shape
    assert video.min() >= 0.0 and video.max() <= 1.0
    assert video.dtype == torch.float32
    print("  6. assembler 4 frames ok")


def test_assembler_single_latent():
    lat = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    asm = PSN_Latent_RGB_Stack()
    (video,) = asm.run(lat)
    assert video.shape == (1, 8, 8, 3), video.shape
    print("  7. assembler single latent ok")


def test_assembler_empty_list():
    asm = PSN_Latent_RGB_Stack()
    try:
        asm.run([])
        assert False, "should have raised ValueError"
    except ValueError as e:
        assert "empty" in str(e)
    print("  8. assembler empty list ok")


def test_assembler_mismatched_shapes():
    lat1 = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    lat2 = _make_latent(torch.full((1, 4, 16, 16), 0.5))
    asm = PSN_Latent_RGB_Stack()
    try:
        asm.run([lat1, lat2])
        assert False, "should have raised ValueError"
    except ValueError as e:
        assert "shape" in str(e)
    print("  9. assembler mismatched shapes ok")


def test_assembler_values_are_raw_latent_channels():
    samples = torch.zeros(1, 4, 2, 2)
    samples[:, 0] = 0.1
    samples[:, 1] = 0.5
    samples[:, 2] = 2.0   # out of range: clamped
    samples[:, 3] = 0.9   # 4th channel is dropped
    (img,) = PSN_Latent_RGB_Stack().run(_make_latent(samples))
    assert img.shape == (1, 2, 2, 3)
    assert torch.allclose(img[0, 0, 0], torch.tensor([0.1, 0.5, 1.0]))
    assert PSN_Latent_RGB_Stack.RETURN_TYPES == ("IMAGE",), "output is not a decoded VIDEO"
    assert "fps" not in PSN_Latent_RGB_Stack.INPUT_TYPES()["required"]
    assert "no VAE decode" in PSN_Latent_RGB_Stack.DESCRIPTION
    print(" 10. assembler raw channels ok")


def test_generator_values_and_dropped_inputs():
    gen = PSN_Synthetic_Latent_Frame()
    req = PSN_Synthetic_Latent_Frame.INPUT_TYPES()["required"]
    assert "sampler_name" not in req and "scheduler" not in req
    assert "sampler_name" not in PSN_Synthetic_Latent_Loop.INPUT_TYPES()["required"]
    # same inputs -> same latent; different seed -> different latent
    a, _ = gen.run(frame_index=0, total_frames=4, steps=20, cfg=7.0, seed=1)
    b, _ = gen.run(frame_index=0, total_frames=4, steps=20, cfg=7.0, seed=1)
    c, _ = gen.run(frame_index=0, total_frames=4, steps=20, cfg=7.0, seed=2)
    assert torch.equal(a["samples"], b["samples"]) and not torch.equal(a["samples"], c["samples"])
    # cfg 0 removes the noise: frame 0 is exactly 0.5 + 0.3 * 0 = 0.5
    z, _ = gen.run(frame_index=0, total_frames=4, steps=20, cfg=0.0, seed=1)
    assert torch.allclose(z["samples"], torch.full((1, 4, 8, 8), 0.5))
    # frame_index 3 of 4, cfg 0, with prev 0.5: 0.7*0.5 + 0.3*1.0 = 0.65
    prev = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    n, _ = gen.run(frame_index=3, total_frames=4, steps=20, cfg=0.0, seed=1, prev_latent=prev)
    assert torch.allclose(n["samples"], torch.full((1, 4, 8, 8), 0.65), atol=1e-6)
    for cls in (PSN_Synthetic_Latent_Frame, PSN_Synthetic_Latent_Loop):
        assert "runs no model" in cls.DESCRIPTION.lower() or "no model" in cls.DESCRIPTION
    for old in ("PSN_Video_Frame_Generator", "PSN_Video_Assembler", "PSN_Video_Frame_Loop"):
        assert old not in NODE_CLASS_MAPPINGS
    print(" 10b. generator values ok")


def test_loop_single_frame():
    loop = PSN_Synthetic_Latent_Loop()
    (latents,) = loop.run(
        total_frames=1,
        steps=10,
        cfg=5.0,
        seed=99,
    )
    assert len(latents) == 1
    x = latents[0]["samples"]
    assert x.dim() == 4
    assert x.min() >= 0.0 and x.max() <= 1.0
    print(" 11. loop single frame ok")


def test_no_inplace_mutation():
    gen = PSN_Synthetic_Latent_Frame()
    prev = _make_latent(torch.full((1, 4, 8, 8), 0.5))
    prev_orig = prev["samples"].clone()
    cur, nxt = gen.run(
        frame_index=1,
        total_frames=4,
        steps=20,
        cfg=7.0,
        seed=42,
        prev_latent=prev,
    )
    cur["samples"].fill_(0.0)
    assert torch.equal(prev["samples"], prev_orig)
    assert nxt["samples"].min() > 0.0
    print(" 12. no inplace mutation ok")


def test_input_types():
    for name, cls in NODE_CLASS_MAPPINGS.items():
        it = cls.INPUT_TYPES()
        assert "required" in it, name
        assert isinstance(cls.RETURN_TYPES, tuple), name
        assert isinstance(cls.RETURN_NAMES, tuple), name
        assert len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES), name
    print(" 13. input types ok")


def main():
    test_mappings()
    test_generator_first_frame()
    test_generator_temporal()
    test_generator_bad_frame_index()
    test_generator_bad_prev_latent()
    test_assembler_4_frames()
    test_assembler_single_latent()
    test_assembler_empty_list()
    test_assembler_mismatched_shapes()
    test_assembler_values_are_raw_latent_channels()
    test_generator_values_and_dropped_inputs()
    test_loop_single_frame()
    test_no_inplace_mutation()
    test_input_types()
    print("ok")


if __name__ == "__main__":
    main()