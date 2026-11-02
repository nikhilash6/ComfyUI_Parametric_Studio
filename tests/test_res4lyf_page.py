"""The RES4LYF page credits the pack honestly: right licence words, no bundled code or images, facts that match the repo."""
import importlib.util
import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
WEB = ROOT / "studio" / "web"
PACK = Path(os.environ.get("RES4LYF_PACK", "/nonexistent"))
PAGE = (WEB / "res4lyf.js").read_text()


def data():
    return json.loads((WEB / "res4lyf_data.js").read_text().split("export const DATA = ", 1)[1].rstrip().rstrip(";"))


def test_the_page_is_wired_in():
    app = (WEB / "app.js").read_text()
    assert 'import { Res4lyf } from "./res4lyf.js"' in app
    assert '["res4lyf", "RES4LYF"]' in app and "res4lyf: [" in app and "<${Res4lyf}/>" in app
    assert 'href="res4lyf.css"' in (WEB / "index.html").read_text()


def test_nothing_loads_from_outside():
    # Links out are plain anchors the visitor chooses to open. Nothing is fetched by the page itself.
    assert not re.search(r"https?://|//cdn\.|@import", (WEB / "res4lyf.css").read_text())
    assert not re.search(r"https?://", (WEB / "res4lyf_data.js").read_text())
    assert not re.search(r"<(video|audio|iframe|script|link)\b|fetch\(|\bapi\(|\bpost\(", PAGE)
    assert '<img src=${r.src}' in PAGE and '<img src=${n.t}' in PAGE


def test_every_image_is_our_own_file_and_labelled():
    from_gallery = json.loads((WEB / "res4lyf_gallery.js").read_text().split("export const GALLERY = ", 1)[1].rstrip().rstrip(";"))
    assert from_gallery
    for r in from_gallery:
        assert r["src"].startswith("res4lyf_renders/") and (WEB / r["src"]).exists() and (WEB / r["graph"]).exists()
    graphs = [json.loads((WEB / r["graph"]).read_text()) for r in from_gallery if r["name"] != "control"]
    for g in graphs:
        # Every picture credited to the pack really went through one of its nodes.
        assert any(n["class_type"] in ("ClownsharKSampler_Beta", "ClownsharkChainsampler_Beta") for n in g.values())
    assert "Made by us with this pack" in PAGE


def nodes():
    return json.loads((WEB / "res4lyf_nodes.js").read_text().split("export const NODES = ", 1)[1].rstrip().rstrip(";"))


def test_every_loaded_node_has_notes_and_an_honest_state():
    rows = nodes()
    assert len(rows) == 299 and len({r["n"] for r in rows}) == 299
    for r in rows:
        assert r["d"] and r["g"] and re.match(r"[\w/.]+\.py:\d+", r["src"]), r["n"]
        if r["s"] == "rendered":
            assert r["t"] and (WEB / r["t"]).exists(), r["n"]
        else:
            assert not r["t"], r["n"]


def test_the_counts_on_the_page_come_from_the_data():
    assert "COUNTS.rendered" in PAGE and "A picture means the graph ran" in PAGE


def test_every_outside_link_is_marked_and_points_at_the_author():
    assert 'target="_blank" rel="noopener noreferrer"' in PAGE
    links = set(re.findall(r'https?://[^\s"`/]+/?[^\s"`]*', PAGE))
    assert {"https://github.com/ClownsharkBatwing/RES4LYF/", "https://github.com/ClownsharkBatwing/UltraCascade", "https://huggingface.co/ClownsharkBatwing/CSBW_Style"} <= links
    assert all(re.match(r"https://(github\.com|huggingface\.co)/ClownsharkBatwing/[\w.-]+/?$", u) for u in links), links


def test_the_authors_other_work_says_we_have_not_run_it():
    assert "More from ClownsharkBatwing" in PAGE and "We haven't run any of these." in PAGE and "KIN_ASOF" in PAGE


def test_the_page_says_the_pack_is_not_part_of_the_studio():
    assert "doesn't ship with Parametric Studio" in PAGE and "separate ComfyUI" in PAGE


def test_no_pronoun_is_guessed_for_the_author():
    assert not re.search(r"\b(he|him|his|she|her|hers)\b", PAGE.split("export function Res4lyf")[1], re.I)


def test_no_pack_files_were_copied_in():
    assert not (WEB / "RES4LYF").exists() and not (WEB / "res4lyf").exists() and not (ROOT / "RES4LYF").exists()
    assert "rk_coeff" not in (WEB / "res4lyf_data.js").read_text()


def test_build_script_only_parses():
    src = (ROOT / "scripts" / "build_res4lyf_page.py").read_text()
    assert "ast.parse" in src and "import_module" not in src and "exec(" not in src and "eval(" not in src.replace("literal_eval(", "")


needs_pack = pytest.mark.skipif(not PACK.exists(), reason="no local copy of the pack")


@needs_pack
def test_licence_words_match_the_file():
    head = " ".join((PACK / "LICENSE").read_text().split("GNU AFFERO")[0].split())
    assert head in " ".join(PAGE.split())
    assert "GNU AFFERO GENERAL PUBLIC" in (PACK / "LICENSE").read_text()
    assert 'license = "MIT"' in (PACK / "pyproject.toml").read_text()


@needs_pack
def test_data_matches_the_repo_and_quotes_are_real():
    spec = importlib.util.spec_from_file_location("b", ROOT / "scripts" / "build_res4lyf_page.py")
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    assert b.build(PACK) == data()
    readme = " ".join((PACK / "README.md").read_text().split())
    for q in re.findall(r'q: "([^"]+)"', PAGE):
        assert q.rstrip(".") in readme, q
    for q in ("Much of this work remains experimental and is subject to further changes.", "a horde of pickleshark cannibals come storming out of a nearby bar", "if you wish to demonstrate your commitment to climate change (and image quality)", "69 different selectible samplers"):
        assert q in readme, q


@needs_pack
def test_example_links_name_real_workflows():
    names = set(data()["examples"])
    linked = {x for group in re.findall(r"ex: \[([^\]]+)\]", PAGE) for x in re.findall(r'"([^"]+)"', group)}
    assert linked and linked <= names
    assert "intro to clownsampling" in names
