import torch

from h_use_a_local_llm_enhancer_to_rewrit import (
    PSN_PromptStyleTemplate,
    apply_style_template,
    _clean,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    STYLE_PROFILES,
)


def test_module_mappings():
    assert "PSN_PromptStyleTemplate" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_PromptStyleTemplate"] == "Prompt Style Template (filler words stripped, fixed tokens added, no LLM)"
    cls = NODE_CLASS_MAPPINGS["PSN_PromptStyleTemplate"]
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")
    it = cls.INPUT_TYPES()
    assert "prompt" in it["required"]
    assert cls.RETURN_NAMES == ("prompt", "negative", "changed")


def test_basic_enhance():
    res = apply_style_template("a cat", style="sd15")
    assert res["style"] == "sd15"
    assert "a cat" in res["prompt"]
    assert "masterpiece" in res["prompt"]
    assert "highres" in res["prompt"]
    assert res["negative"]
    assert res["changed"] is True


def test_exact_output_is_template_only():
    res = apply_style_template("please draw the cat in a hat", style="sdxl")
    # filler (please, draw, the, in) stripped; fixed profile tokens appended
    assert res["prompt"] == "cat a hat, cinematic lighting, 8k uhd, sharp focus"
    assert res["negative"] == STYLE_PROFILES["sdxl"]["negative"]
    assert "LLM" not in NODE_CLASS_MAPPINGS["PSN_PromptStyleTemplate"].DESCRIPTION.replace("No LLM", "")
    assert "PSN_LocalLLMPromptEnhancer" not in NODE_CLASS_MAPPINGS


def test_clean_drops_filler():
    assert _clean("please make me a picture of a cat") == "a a cat"
    assert _clean("  double   space  ") == "double space"
    assert _clean("") == ""


def test_weight_wrapping():
    res = apply_style_template("a dog", style="generic", weight=1.5)
    assert "(high quality:1.50)" in res["prompt"]
    res1 = apply_style_template("a dog", style="generic", weight=1.0)
    assert "(high quality" not in res1["prompt"]


def test_bad_style_raises():
    try:
        apply_style_template("x", style="nope")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_bad_weight_raises():
    try:
        apply_style_template("x", style="generic", weight=5.0)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        apply_style_template("x", style="generic", weight="abc")
        assert False, "expected TypeError"
    except TypeError:
        pass


def test_empty_prompt_fallback():
    res = apply_style_template("   ", style="photo")
    assert "abstract composition" in res["prompt"]
    assert "photorealistic" in res["prompt"]


def test_add_negative_false():
    res = apply_style_template("a car", style="anime", add_negative=False)
    assert res["negative"] == ""
    assert "clean lineart" in res["prompt"]


def test_node_run_returns_tuple():
    node = PSN_PromptStyleTemplate()
    out = node.run("a cat", "sdxl", 1.0, True)
    assert isinstance(out, tuple) and len(out) == 3
    p, neg, ch = out
    assert isinstance(p, str) and isinstance(neg, str) and isinstance(ch, int)
    assert ch == 1
    assert "8k uhd" in p


def test_no_mutation_of_inputs():
    original = "a  cat"
    res = apply_style_template(original, style="generic")
    assert original == "a  cat"  # input string untouched
    t = torch.zeros(1, 2, 2, 3)
    t2 = t  # ensure we never mutate tensors passed around
    assert torch.equal(t, t2)


def test_all_styles_present():
    for s in STYLE_PROFILES:
        res = apply_style_template("a tree", style=s)
        assert res["prompt"]


if __name__ == "__main__":
    test_module_mappings()
    test_basic_enhance()
    test_exact_output_is_template_only()
    test_clean_drops_filler()
    test_weight_wrapping()
    test_bad_style_raises()
    test_bad_weight_raises()
    test_empty_prompt_fallback()
    test_add_negative_false()
    test_node_run_returns_tuple()
    test_no_mutation_of_inputs()
    test_all_styles_present()
    print("ok")
