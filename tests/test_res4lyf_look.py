"""The feature layout of the RES4LYF page keeps its promises: nothing from outside, real labelled renders, plain licence up top, and no invented claims in the new copy."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
WEB = ROOT / "studio" / "web"
PAGE = (WEB / "res4lyf.js").read_text()
FEATURE = (WEB / "res4lyf_feature.js").read_text()
LOGIC = (WEB / "res4lyf_logic.js").read_text()
CSS = (WEB / "res4lyf.css").read_text()


def gallery():
    return json.loads((WEB / "res4lyf_gallery.js").read_text().split("export const GALLERY = ", 1)[1].rstrip().rstrip(";"))


def test_every_section_and_note_is_still_there():
    for text in ("This pack doesn't ship with Parametric Studio", "Counted by reading the source at commit", '"The idea"', '"How it works"', '"Our renders with it"', '"Samplers"', '"Try the arithmetic"', '"What it can do"', "In the author's words", '"Every node"', '"More from the author"', '"Install it yourself"', '"Licence"', "A picture means the graph ran", "Our reading of the code at that commit", "A safety note", "doesn't match", "not legal advice"):
        assert text in PAGE, text
    for name in ("CostLab", "BetaLab", "SamplerAtlas", "Gallery", "NodeList", "StageArt"):
        assert f"<${{{name}}}/>" in PAGE, name


def test_licence_is_plain_near_the_top():
    assert PAGE.index("r4-licnote") < PAGE.index('title="The idea"')
    assert "prohibits using it for a commercial service" in PAGE and "we link to it and don't bundle it" in PAGE


def test_the_feature_file_loads_nothing_from_outside():
    assert not re.search(r"https?://|<(video|audio|iframe|script|link)\b|fetch\(|\bapi\(|\bpost\(", FEATURE)
    assert not re.search(r"https?://|//cdn\.|@import|url\(", CSS)


def test_no_em_dashes_or_guessed_pronouns_in_the_copy():
    for text in (PAGE, FEATURE, CSS):
        assert "—" not in text
    assert not re.search(r"\b(he|him|his|she|her|hers)\b", FEATURE, re.I)


def test_comparisons_name_real_renders_and_say_what_they_are():
    names = {r["name"] for r in gallery()}
    pairs = re.findall(r'a: "(\w+)", b: "(\w+)"', FEATURE)
    assert len(pairs) >= 6
    for a, b in pairs:
        assert a in names and b in names, (a, b)
    assert "a.what" in FEATURE and "b.what" in FEATURE and "not as a ranking" in FEATURE
    assert 'a.graph} download' in FEATURE and 'b.graph} download' in FEATURE


def test_comparison_text_matches_the_graphs():
    for fam in ("sd15", "sdxl", "flux"):
        graph = lambda name: json.loads((WEB / "res4lyf_renders" / "graphs" / f"{fam}_{name}.json").read_text())
        pack = next(n for n in graph("res_3s").values() if n["class_type"] == "ClownsharKSampler_Beta")["inputs"]
        assert pack["sampler_name"].endswith("res_3s") and pack["scheduler"] == "beta57" and pack["eta"] == 0.5 and pack["bongmath"] is True
        plain = next(n for n in graph("control").values() if n["class_type"] == "KSampler")["inputs"]
        assert plain["sampler_name"] == "euler" and plain["scheduler"] == "normal" and plain["seed"] == pack["seed"]
        style = next(n for n in graph("style").values() if n["class_type"] == "ClownGuide_Style_Beta")["inputs"]
        assert style["method"] == "WCT"
        chain = [n["inputs"]["sampler_name"] for n in graph("chain").values() if "sampler_name" in n["inputs"]]
        assert chain[0].endswith("res_2m") and chain[1].endswith("res_3s")
        modes = [n["inputs"]["sampler_mode"] for n in graph("unsample").values() if "sampler_mode" in n["inputs"]]
        assert modes == ["unsample", "resample"]


def test_toy_says_what_it_is():
    assert "It uses the published formulas, not the pack's code" in FEATURE and "It says nothing about pictures" in FEATURE
    assert "not measured values" in FEATURE
    assert "not the pack's code" in LOGIC


def test_motion_only_when_allowed_and_focus_is_visible():
    assert "prefers-reduced-motion:no-preference" in CSS and "prefers-reduced-motion:reduce" in CSS
    assert ":focus-visible" in CSS and "aria-label=" in FEATURE
    assert "calm()" in PAGE


def test_no_new_media_was_added_for_the_look():
    assert not re.search(r"\.(jpe?g|png|webp|gif|mp4|webm)\"", FEATURE)
