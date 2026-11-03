import pytest
import shutil
"""The blepping page credits Sonar, OCS and bleh honestly: our own labelled renders with their graphs, the packs not bundled, no code copied, nothing loaded from outside."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
WEB = ROOT / "studio" / "web"
PAGE = (WEB / "blepping.js").read_text()
LOGIC = (WEB / "blepping_logic.js").read_text()
CSS = (WEB / "blepping.css").read_text()
PACK_NODES = {"sonar": ("Sonar", "SamplerSonar", "SamplerConfigOverride", "FreeUExtreme"), "ocs": ("OCS",), "bleh": ("Bleh",), "skoogeer": ()}
PACK_SAMPLERS = ("sonar_euler", "sonar_euler_ancestral", "sonar_dpmpp_sde")


def data():
    return json.loads((WEB / "blepping_data.js").read_text().split("export const DATA = ", 1)[1].rstrip().rstrip(";"))


def test_the_page_is_wired_in():
    app = (WEB / "app.js").read_text()
    assert 'import { Blepping } from "./blepping.js"' in app
    assert '["blepping", "blepping"]' in app and "blepping: [" in app and "<${Blepping}/>" in app
    assert 'href="blepping.css"' in (WEB / "index.html").read_text()


def test_nothing_loads_from_outside():
    assert not re.search(r"https?://|//cdn\.|@import|url\(", CSS)
    assert not re.search(r"https?://", (WEB / "blepping_data.js").read_text())
    assert not re.search(r"<(video|audio|iframe|script|link)\b|fetch\(|\bapi\(|\bpost\(", PAGE + LOGIC)


def test_every_outside_link_is_marked_and_points_at_the_author():
    assert 'target="_blank" rel="noopener noreferrer"' in PAGE
    links = set(re.findall(r'https?://[^\s"`]+', PAGE + LOGIC))
    assert links and all(re.match(r"https://github\.com/blepping(/[\w.-]+)?/?$", u) for u in links), links


def test_every_picture_is_our_own_file_with_its_graph():
    d = data(); rows = d["renders"]
    assert len([r for r in rows if r["pack"] != "core"]) >= 40
    for r in rows:
        assert (WEB / r["graph"]).exists(), r["id"]
        if r.get("src"): assert r["src"].startswith("blepping_renders/") and (WEB / r["src"]).exists(), r["id"]
        if r["ok"]: assert r.get("src"), r["id"]
        else: assert r.get("error"), r["id"]
        assert "/mnt/" not in r.get("error", ""), r["id"]


def test_pack_renders_really_used_the_pack():
    for r in data()["renders"]:
        if r["pack"] in ("core",) or r["pack"] == "skoogeer": continue
        if r["id"] == "bleh-sdxl-batch4-preview": continue   # bleh swaps the previewer as it loads, so this graph is plain core on purpose
        g = json.loads((WEB / r["graph"]).read_text()); kinds = {n["class_type"] for n in g.values()}
        names = {n["inputs"].get("sampler_name") for n in g.values()}
        assert any(k.startswith(PACK_NODES[r["pack"]]) for k in kinds) or names & set(PACK_SAMPLERS), r["id"]


def test_core_baselines_are_core_only():
    import sys
    sys.path.insert(0, str(ROOT / "studio"))
    import sampling_graph as G
    for r in data()["renders"]:
        if r["pack"] != "core" or not r["id"].startswith("core-"): continue
        g = json.loads((WEB / r["graph"]).read_text())
        assert all(not n["class_type"].startswith(("Sonar", "OCS", "Bleh")) for n in g.values()), r["id"]
        assert all(n["inputs"].get("sampler_name", "euler") in G.CORE_SAMPLERS for n in g.values()), r["id"]


def test_the_page_says_the_packs_are_not_bundled():
    assert "These packs don't ship with Parametric Studio." in PAGE and "throwaway ComfyUI" in PAGE and "don't bundle any of them" in PAGE


def test_licences_named_on_the_page_match_the_data():
    d = data()
    assert d["packs"]["sonar"]["licence"] == "MIT" and d["packs"]["ocs"]["licence"] == "MIT" and d["packs"]["bleh"]["licence"] == "Apache-2.0"
    assert "Sonar and Overly Complicated Sampling are MIT, bleh is Apache-2.0" in PAGE and "not legal advice" in PAGE


def test_quotes_are_the_readmes_words():
    for q in ("This started out as an implementation of Sonar sampling and has evolved into something more like a noise toybox.", "I can move code around but sampling math and creating samplers generally beyond my ability.", "Experimental and mathematically unsound (but fun!)"):
        assert q in PAGE, q


def test_the_global_attention_patch_was_never_loaded():
    for r in data()["renders"]:
        g = json.loads((WEB / r["graph"]).read_text())
        assert all(n["class_type"] != "BlehGlobalSageAttention" for n in g.values()), r["id"]
    assert "We didn't load <code>BlehGlobalSageAttention</code>" in PAGE


def test_no_pack_files_were_copied_in():
    for name in ("ComfyUI-bleh", "ComfyUI-sonar", "comfyui_overly_complicated_sampling", "Skoogeer-Noise"):
        assert not (WEB / name).exists() and not (ROOT / name).exists()
    src = (ROOT / "scripts" / "build_blepping_page.py").read_text() + (ROOT / "scripts" / "add_blepping_atlas.py").read_text()
    assert "import_module" not in src and not re.search(r"\b(exec|eval)\(", src)


def test_no_em_dashes_or_guessed_pronouns():
    for text in (PAGE, LOGIC, CSS):
        assert "—" not in text
    assert not re.search(r"\b(he|him|his|she|her|hers)\b", PAGE.split("export function Blepping")[1], re.I)


def test_components_close_with_the_short_form_and_targets_are_big_enough():
    assert "</${" not in PAGE
    assert re.search(r"\.bp-chip\{[^}]*min-height:44px", CSS) and re.search(r"\.bp \.btn\{[^}]*min-height:44px", CSS)
    assert re.search(r"\.bp \.bp-toc a\{[^}]*min-height:44px", CSS) and "min-height:40px" in CSS


def test_motion_only_when_allowed_and_focus_is_visible():
    assert "prefers-reduced-motion:no-preference" in CSS and "prefers-reduced-motion:reduce" in CSS and ":focus-visible" in CSS and "calm()" in PAGE


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_logic_runs_without_a_browser(tmp_path):
    probe = tmp_path / "probe.mjs"
    probe.write_text(f"""import * as L from {json.dumps(str(WEB / 'blepping_logic.js'))};
const R = [{{id: "core-x", pack: "core", src: "a.jpg", ok: true}}, {{id: "p", pack: "sonar", base: "core-x", src: "b.jpg", ok: true}}, {{id: "q", pack: "ocs", ok: false}}];
const out = {{ pair: L.pairFor(R, "p").a.id, none: L.pairFor(R, "q"), counts: L.counts(R), s0: L.stage0Verdict([{{same_pixels: true}}, {{same_pixels: true}}]).ok, s0bad: L.stage0Verdict([{{same_pixels: false}}]).ok, same: L.samePixels({{pixels: "x"}}, {{pixels: "x"}}), notsame: L.samePixels({{pixels: "x"}}, {{}}), step: L.stepMethod("rk4 (3)"), diff: L.diffWord(0) }};
console.log(JSON.stringify(out));""")
    out = json.loads(subprocess.run(["node", str(probe)], capture_output=True, text=True, check=True).stdout)
    assert out == {"pair": "core-x", "none": None, "counts": {"all": 2, "ok": 1, "failed": 1}, "s0": True, "s0bad": False, "step": {"name": "rk4", "calls": "3"}, "diff": "identical pixels", "same": True, "notsame": False}


def test_sampling_lab_has_ocs_and_skoogeer_and_points_here():
    a = json.loads((ROOT / "studio" / "sampling_lab" / "atlas.json").read_text())
    ocs = [e for e in a["entries"] if any(p["pack"] == "comfyui_overly_complicated_sampling" for p in e["providers"])]
    sko = [e for e in a["entries"] if any(p["pack"] == "Skoogeer-Noise" for p in e["providers"])]
    assert len(ocs) >= 15 and len(sko) >= 12
    assert all(p.get("blepping") for e in ocs for p in e["providers"]) and not any(e["rendered"] for e in ocs + sko)
    assert '#blepping' in (WEB / "samplinglab_method.js").read_text() and '#blepping' in (WEB / "samplinglab.js").read_text()


def test_the_unsafe_expression_was_refused():
    r = next(x for x in data()["renders"] if x["id"] == "ocs-unsafe-refused")
    assert not r["ok"] and r["expected_refusal"] and "Unsafe Torch access not allowed" in r["error"]
