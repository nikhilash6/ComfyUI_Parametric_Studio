import inspect

import torch

import n_1_automated_lora_dataset_captioning as mod
from n_1_automated_lora_dataset_captioning import (
    PSN_Image_Stats_Caption,
    PSN_Caption_Auditor,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _image_stats,
)


def make_image(b=1, h=8, w=8, c=3, value=0.5):
    return torch.full((b, h, w, c), value, dtype=torch.float32)


# ---------------------------------------------------------------------------
# 1. Module-level registration; the VLM claim and its fabricated outputs are gone
# ---------------------------------------------------------------------------
assert "PSN_Image_Stats_Caption" in NODE_CLASS_MAPPINGS
assert "PSN_Caption_Auditor" in NODE_CLASS_MAPPINGS
assert "PSN_VLM_Caption_Generator" not in NODE_CLASS_MAPPINGS
assert not hasattr(mod, "PSN_VLM_Caption_Generator")
for gone in ("_confidence_score", "_build_system_prompt", "_parse_caption"):
    assert not hasattr(mod, gone), gone
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Image_Stats_Caption"] == "Image Stats Caption (no VLM)"
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Caption_Auditor"] == "Caption Auditor"
assert "No vision-language model runs" in PSN_Image_Stats_Caption.DESCRIPTION

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES
# ---------------------------------------------------------------------------
it = PSN_Image_Stats_Caption.INPUT_TYPES()
assert set(it["required"]) == {"image", "caption_style"}
assert "optional" not in it  # llm_handle and negative_prompt_hint removed
assert PSN_Image_Stats_Caption.RETURN_TYPES == ("STRING",)
assert PSN_Image_Stats_Caption.RETURN_NAMES == ("caption",)
assert PSN_Image_Stats_Caption.FUNCTION == "run"
assert PSN_Image_Stats_Caption.CATEGORY.startswith("ParametricStudio/")
assert "llm_handle" not in inspect.signature(PSN_Image_Stats_Caption.run).parameters

it2 = PSN_Caption_Auditor.INPUT_TYPES()
assert "caption" in it2["required"]
assert PSN_Caption_Auditor.RETURN_TYPES == ("BOOLEAN", "STRING")

# ---------------------------------------------------------------------------
# 3. Template captions: exact text from known statistics
# ---------------------------------------------------------------------------
gen = PSN_Image_Stats_Caption()
(caption,) = gen.run(make_image(value=0.3), "detailed")
assert caption == (
    "A dim image of size 8x8. The overall lighting is dim with low contrast. "
    "The dominant color tone is neutral."
)
assert "VLM" not in caption

(caption,) = gen.run(make_image(value=0.3), "concise")
assert caption == "A dim image with low contrast, neutral tones."
(caption,) = gen.run(make_image(value=0.3), "natural_language")
assert caption == "This is a dim image (8x8) with low contrast and neutral color tones."

# ---------------------------------------------------------------------------
# 4. booru_tags style: lowercase, underscore tags
# ---------------------------------------------------------------------------
(caption_b,) = gen.run(make_image(value=0.8), "booru_tags")
assert caption_b == "image, 8x8, very_bright, low_contrast"
red_img = torch.zeros(1, 4, 4, 3, dtype=torch.float32)
red_img[..., 0] = 0.9
red_img[..., 1] = 0.1
red_img[..., 2] = 0.1
(caption_r,) = gen.run(red_img, "booru_tags")
assert caption_r.endswith("red_tone")
assert "red" in gen.run(red_img, "concise")[0]

# ---------------------------------------------------------------------------
# 7. Bad input raises
# ---------------------------------------------------------------------------
try:
    gen.run(torch.zeros(4, 4, 3), "detailed")  # 3D, not 4D
    assert False, "expected ValueError for 3D tensor"
except ValueError:
    pass
try:
    gen.run("not a tensor", "detailed")
    assert False, "expected TypeError for non-tensor"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 10. Caption auditor: valid caption
# ---------------------------------------------------------------------------
aud = PSN_Caption_Auditor()
is_valid, suggestion = aud.run("a cat sitting on a mat", allowed_terms="cat, dog", banned_terms="nsfw, gore")
assert is_valid is True
assert suggestion == ""

# ---------------------------------------------------------------------------
# 11. Caption auditor: banned term present -> invalid
# ---------------------------------------------------------------------------
is_valid2, suggestion2 = aud.run("a cat with gore", allowed_terms="", banned_terms="gore, nsfw")
assert is_valid2 is False
assert "gore" in suggestion2

# ---------------------------------------------------------------------------
# 12. Caption auditor: no allowed term present -> invalid
# ---------------------------------------------------------------------------
is_valid3, suggestion3 = aud.run("a bird in the sky", allowed_terms="cat, dog", banned_terms="")
assert is_valid3 is False
assert "cat" in suggestion3 or "dog" in suggestion3

# ---------------------------------------------------------------------------
# 13. Caption auditor: empty caption -> invalid
# ---------------------------------------------------------------------------
is_valid4, suggestion4 = aud.run("", allowed_terms="", banned_terms="")
assert is_valid4 is False
assert "empty" in suggestion4

# ---------------------------------------------------------------------------
# 14. Caption auditor: case-insensitive banned match
# ---------------------------------------------------------------------------
is_valid5, _ = aud.run("A CAT with GORE", allowed_terms="", banned_terms="gore")
assert is_valid5 is False

# ---------------------------------------------------------------------------
# 17. Image stats: bright vs dark image
# ---------------------------------------------------------------------------
stats_bright = _image_stats(make_image(value=0.9))
stats_dark = _image_stats(make_image(value=0.1))
assert stats_bright["mean_brightness"] > stats_dark["mean_brightness"]
assert stats_bright["dominant_hue"] == "neutral"

# ---------------------------------------------------------------------------
# 18. Image stats: red-dominant image
# ---------------------------------------------------------------------------
red_img = torch.zeros(1, 4, 4, 3, dtype=torch.float32)
red_img[..., 0] = 0.9  # red channel high
red_img[..., 1] = 0.1
red_img[..., 2] = 0.1
stats_red = _image_stats(red_img)
assert stats_red["dominant_hue"] == "red"

# ---------------------------------------------------------------------------
# 19. Batch image works
# ---------------------------------------------------------------------------
(caption_batch,) = gen.run(make_image(b=3, value=0.5), "concise")
assert caption_batch == "A bright image with low contrast, neutral tones."

# ---------------------------------------------------------------------------
# 20. Input not modified in place
# ---------------------------------------------------------------------------
img_orig = make_image(value=0.5)
img_copy = img_orig.clone()
gen.run(img_orig, "detailed")
assert torch.equal(img_orig, img_copy), "input image was modified in place"

print("ok")
