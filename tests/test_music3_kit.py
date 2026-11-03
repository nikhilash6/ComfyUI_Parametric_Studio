"""The Music 3 style kit: 16 ntc-ai slider LoRAs and the turbo LoRA on the Music page, and the screened lyrics in the style library."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException

from studio import feature_music as F, music_styles as MS
from studio.graph_template import placeholders

ROOT = Path(__file__).resolve().parent.parent; WEB = ROOT / "studio" / "web"
KIT = json.loads((ROOT / "studio" / "music3_kit.json").read_text())
GRAPH = json.loads((ROOT / "workflows" / "music_music3_kit_api.json").read_text())
LYR = json.loads((ROOT / "studio" / "music3_lyrics.json").read_text())


def test_kit_has_the_sixteen_sliders_and_turbo_with_sources():
    s = KIT["sliders"]; assert len(s) == 16 and len({x["id"] for x in s}) == 16
    assert sum(x["group"] == "voice" for x in s) == 2 and sum(x["group"] == "genre" for x in s) == 14
    assert all(x["file"].startswith("minimax/music3/ntc_") and len(x["sha256"]) == 64 for x in s)
    assert KIT["turbo"]["file"].endswith("minimax_music3_turbo_lora_8step.safetensors") and KIT["turbo"]["steps"] == 8
    assert KIT["sources"]["sliders"]["licence"] == "MIT" and KIT["sources"]["turbo"]["licence"] == "Apache-2.0"
    assert all("huggingface.co/" in KIT["sources"][k]["url"] for k in ("sliders", "turbo"))
    assert not any("fiona" in x["file"] for x in s) and any("fiona" in x["file"] for x in KIT["left_out"])
    assert KIT["strength"]["min"] == 0 and KIT["strength"]["max"] <= 1.5      # no negative strength: the card says it is not a trained opposite


def test_kit_graph_leaves_the_dit_alone_for_sliders_and_switches_turbo():
    assert placeholders(GRAPH) == {"caption", "lyrics", "duration", "seed", "slider", "slider_strength", "turbo"}
    sl = GRAPH["kit:slider"]["inputs"]; assert GRAPH["kit:slider"]["class_type"] == "LoraLoader" and sl["strength_model"] == 0.0 and sl["strength_clip"] == "${slider_strength}"
    te = next(v for v in GRAPH.values() if v["class_type"] == "MiniMaxMusic3TextEncode"); assert te["inputs"]["clip"] == ["kit:slider", 1] and te["inputs"]["cfg_scale"] == ["kit:te_cfg", 0]
    ks = next(v for v in GRAPH.values() if v["class_type"] == "KSampler"); assert ks["inputs"]["model"] == ["kit:model", 0] and ks["inputs"]["steps"] == ["kit:steps", 0]
    assert GRAPH["kit:turbo"]["class_type"] == "LoraLoaderModelOnly"
    # the proven plain graph is untouched
    assert "kit:slider" not in json.loads((ROOT / "workflows" / "music3_api.json").read_text())


def test_build_fills_the_kit_safely():
    g = F.build("music_music3_kit_api.json", {"style": "country", "seconds": 30, "slider": "country", "slider_strength": 9, "turbo": True})
    assert g["kit:slider"]["inputs"]["lora_name"].endswith("ntc_country_step1000_fusedqkv.safetensors") and g["kit:slider"]["inputs"]["strength_clip"] == 1.5 and g["kit:turbo_on"]["inputs"]["value"] is True
    g = F.build("music_music3_kit_api.json", {"style": "pop", "seconds": 30})
    assert g["kit:slider"]["inputs"]["strength_clip"] == 0.0 and g["kit:turbo_on"]["inputs"]["value"] is False
    g = F.build("music_music3_kit_api.json", {"style": "pop", "seconds": 30, "slider": "female", "slider_strength": -1, "turbo": "yes"})
    assert g["kit:slider"]["inputs"]["strength_clip"] == 0.0 and g["kit:turbo_on"]["inputs"]["value"] is False      # clamped; only a real true turns turbo on
    with pytest.raises(HTTPException): F.build("music_music3_kit_api.json", {"style": "pop", "seconds": 30, "slider": "../../evil"})
    assert F.kit_get()["graph"] == "music_music3_kit_api.json"


def test_lyrics_counts_add_up_and_dropped_text_is_gone():
    c = LYR["counts"]; assert c["with_lyrics"] == 256 and c["kept"] + c["dropped"] == 256 and c["kept"] == len(LYR["sets"]) and c["dropped"] == len(LYR["dropped"])
    assert all("lyrics" not in d and d["why"] for d in LYR["dropped"])
    assert LYR["screened"]["human_read"] is False
    dropped = {d["style_id"] for d in LYR["dropped"]}; assert {"hip-hop-boom-bap", "hip-hop-boom-bap-with-jazz-influences"} <= dropped


def test_every_kept_set_passes_the_rules_and_is_in_the_library():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bl", ROOT / "scripts" / "build_music3_lyrics.py"); bl = importlib.util.module_from_spec(spec); spec.loader.exec_module(bl)
    lib = {st["id"] for f in json.loads((ROOT / "studio" / "music3_styles.json").read_text())["families"] for st in f["styles"]}
    for sid, s in LYR["sets"].items():
        assert sid in lib and not bl.rule_problems(s["lyrics"]), sid
        assert "heavy is the crown" not in s["lyrics"].lower()
    assert bl.rule_problems("we sang like Taylor Swift tonight") and bl.rule_problems("cocaine on the table") and not bl.rule_problems("Queen of the night\nshe dances")


def test_style_api_serves_lyrics():
    L = MS.styles_list(); assert L["with_lyrics"] == LYR["counts"]["kept"]
    sid = next(iter(LYR["sets"])); d = MS.style_detail(sid); assert d["lyrics_set"]["lyrics"] == LYR["sets"][sid]["lyrics"] and d["lyrics_set"]["screened"]
    row = next(st for f in L["families"] for st in f["styles"] if st["id"] == sid); assert row["lyrics"] is True and "lyrics_set" not in row


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_run_body_switches_to_the_kit_graph_only_when_asked():
    code = """import * as L from "./music_logic.js"; import assert from "node:assert";
const m = { graph: "music3_api.json", takes: "caption", lyrics: true, id: "music3" };
const plain = L.runBody(m, { style: "calm", lyrics: "la", seconds: 30, slider: "none", turbo: false }); assert.equal(plain.graph, "music3_api.json"); assert.equal(plain.slider, undefined);
const kit = L.runBody(m, { style: "calm", lyrics: "la", seconds: 30, slider: "country", strength: 3, turbo: true }); assert.equal(kit.graph, "music_music3_kit_api.json"); assert.equal(kit.slider, "country"); assert.equal(kit.slider_strength, 1.5); assert.equal(kit.turbo, true);
const turbo = L.runBody(m, { style: "calm", seconds: 30, turbo: true }); assert.equal(turbo.graph, "music_music3_kit_api.json"); assert.equal(turbo.slider, "none"); assert.equal(turbo.slider_strength, undefined);
const other = L.runBody({ graph: "g", takes: "prompt", lyrics: true, id: "ace15_turbo" }, { style: "calm", seconds: 30, slider: "country", turbo: true }); assert.equal(other.graph, "g");
console.log("ok");"""
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(WEB / "music_logic.js", t); (Path(t) / "x.mjs").write_text(code)
        p = subprocess.run(["node", str(Path(t) / "x.mjs")], cwd=t, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and "ok" in p.stdout, p.stderr
