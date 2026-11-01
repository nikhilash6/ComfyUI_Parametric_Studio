"""Graph Doctor: real answers from a stubbed /object_info, nothing applied unless named, and the language model only rewords. No live ports."""
import base64, io, json, re
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin
from studio import feature_doctor as D

OI = {
    "CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [["sd_xl_base_1.0.safetensors", "other.safetensors"]]}}, "output": ["MODEL", "CLIP", "VAE"]},
    "CLIPTextEncode": {"input": {"required": {"text": ["STRING", {"multiline": True}], "clip": ["CLIP"]}}, "output": ["CONDITIONING"]},
    "EmptyLatentImage": {"input": {"required": {"width": ["INT", {"default": 512, "min": 16, "max": 16384}], "height": ["INT", {"default": 512, "min": 16, "max": 16384}], "batch_size": ["INT", {"default": 1, "min": 1, "max": 4096}]}}, "output": ["LATENT"]},
    "KSampler": {"input": {"required": {"model": ["MODEL"], "seed": ["INT", {"default": 0, "min": 0}], "steps": ["INT", {"default": 20, "min": 1, "max": 10000}], "cfg": ["FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0}], "sampler_name": [["euler", "euler_ancestral", "dpmpp_2m"]], "scheduler": [["normal", "karras"]], "positive": ["CONDITIONING"], "negative": ["CONDITIONING"], "latent_image": ["LATENT"], "denoise": ["FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0}]}}, "output": ["LATENT"]},
    "VAEDecode": {"input": {"required": {"samples": ["LATENT"], "vae": ["VAE"]}}, "output": ["IMAGE"]},
    "SaveImage": {"input": {"required": {"images": ["IMAGE"], "filename_prefix": ["STRING", {"default": "ComfyUI"}]}}, "output": [], "output_node": True},
    "LoadImage": {"input": {"required": {"image": [["a.png"]]}}, "output": ["IMAGE", "MASK"]},
}


def good():
    return {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}}, "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "x", "clip": ["1", 1]}}, "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["1", 1]}}, "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
            "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0], "seed": 7, "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}}, "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}}, "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "x"}}}


def rules(g): return {p["rule"] for p in D.diagnose(g, OI)}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(D, "object_info", lambda: OI)
    app = FastAPI(); app.include_router(D.router); return TestClient(app)


def test_a_good_graph_has_no_problems(): assert D.diagnose(good(), OI) == []


@pytest.mark.parametrize("edit,rule,fixable", [
    (lambda g: g["5"]["inputs"].update(sampler_name="eular"), "not_a_choice", True),
    (lambda g: g["5"]["inputs"].update(sampler_name="zzzz"), "not_a_choice", False),
    (lambda g: g["5"]["inputs"].update(denoise=1.5), "too_high", True),
    (lambda g: g["4"]["inputs"].update(width=1), "too_low", True),
    (lambda g: g["4"]["inputs"].update(width="1024"), "text_number", True),
    (lambda g: g["4"]["inputs"].update(width="wide"), "not_a_number", False),
    (lambda g: g["4"]["inputs"].update(width=512.5), "not_whole", True),
    (lambda g: g["3"]["inputs"].update(clip=["1", 9]), "slot_gone", True),
    (lambda g: g["6"]["inputs"].update(vae=["1", 0]), "wrong_type", True),
    (lambda g: g["2"]["inputs"].update(clip=["99", 0]), "link_gone", True),
    (lambda g: g["5"]["inputs"].pop("model"), "missing_link", True),
    (lambda g: g["5"]["inputs"].pop("positive"), "missing_link", False),
    (lambda g: g["5"]["inputs"].update(bogus=1), "unknown_input", True),
    (lambda g: g["1"]["inputs"].update(ckpt_name="nope_never.safetensors"), "model_missing", False),
    (lambda g: g["7"].update(class_type="SaveImagee"), "unknown_node", True),
    (lambda g: g["7"].update(class_type="SomePacksNode"), "unknown_node", False),
    (lambda g: g.pop("7"), "no_output", True),
    (lambda g: g.update({"8": {"class_type": "LoadImage", "inputs": {"image": "a.png"}}}), "idle_nodes", False),
    (lambda g: g.update({"8": {"class_type": "LoadImage", "inputs": {"image": "mine.png"}}}), "input_file", False),
    (lambda g: g["4"].pop("class_type"), "no_class", True),
])
def test_each_rule(edit, rule, fixable):
    g = good(); edit(g); hit = [p for p in D.diagnose(g, OI) if p["rule"] == rule]
    assert hit, D.diagnose(g, OI)
    assert bool(hit[0]["fix"]) is fixable and hit[0]["title"] and hit[0]["why"] and hit[0]["source"] == "rule"
    assert hit[0]["how"], "every problem says what to do"


def test_placeholders_and_v3_dynamic_parts_are_left_alone():
    g = good(); g["5"]["inputs"]["sampler_name"] = "${sampler}"; g["4"]["inputs"]["width"] = "${w}"
    assert D.diagnose(g, OI) == []
    oi = {**OI, "Grow": {"input": {"required": {"values": ["COMFY_AUTOGROW_V3", {}]}}, "output": ["IMAGE"]}}
    g = good(); g["8"] = {"class_type": "Grow", "inputs": {"values.a": ["6", 0]}}; g["7"]["inputs"]["images"] = ["8", 0]
    assert D.diagnose(g, oi) == []


def test_a_cycle_is_found():
    g = good(); g["2"]["inputs"]["clip"] = ["5", 0]; g["5"]["inputs"]["latent_image"] = ["6", 0]; g["6"]["inputs"]["samples"] = ["5", 0]
    assert "cycle" in rules(g)


def test_a_different_model_is_never_offered():
    p = next(p for p in D.diagnose({**good(), "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "dreamshaper.safetensors"}}}, OI) if p["rule"] == "model_missing")
    assert p["fix"] is None and "not swap" in p["why"]


def test_the_same_model_in_another_precision_is_offered_as_a_choice():
    oi = {"UNETLoader": {"input": {"required": {"unet_name": [["wan2.2_t2v_fp16.safetensors"]]}}, "output": ["MODEL"]}}
    p = D._model_problem("1", "UNETLoader", "unet_name", "wan2.2_t2v_fp8.safetensors", oi["UNETLoader"]["input"]["required"]["unet_name"][0])
    assert p["rule"] == "model_precision" and p["fix"]["after"] == "wan2.2_t2v_fp16.safetensors"


def test_a_missing_model_names_its_download_when_known():
    p = D._model_problem("1", "VAELoader", "vae_name", "flux2-vae.safetensors", ["other.safetensors"])
    assert "huggingface.co" in p["how"]


def test_a_model_in_another_folder_gets_the_listed_path():
    p = D._model_problem("1", "CheckpointLoaderSimple", "ckpt_name", "sd_xl_base_1.0.safetensors", ["xl/sd_xl_base_1.0.safetensors"])
    assert p["rule"] == "model_folder" and p["fix"]["after"] == "xl/sd_xl_base_1.0.safetensors"


def test_apply_changes_only_what_is_named_and_not_the_original():
    g = good(); g["5"]["inputs"]["denoise"] = 1.5; g["5"]["inputs"]["sampler_name"] = "eular"; before = json.dumps(g, sort_keys=True); ps = D.diagnose(g, OI); pick = next(p for p in ps if p["rule"] == "too_high")
    new, changes = D.apply_fixes(g, ps, {pick["id"]})
    assert json.dumps(g, sort_keys=True) == before and new["5"]["inputs"]["denoise"] == 1.0 and new["5"]["inputs"]["sampler_name"] == "eular" and len(changes) == 1 and changes[0]["before"] == 1.5


def test_check_shows_fixes_and_changes_nothing(client):
    g = good(); g["5"]["inputs"]["denoise"] = 1.5; d = client.post("/api/doctor/check", json={"text": json.dumps(g)}).json()
    assert d["graph"] == g and d["errors"] == 1 and d["fixable"] == 1 and d["problems"][0]["fix"]["before"] == 1.5


def test_fix_needs_a_named_change(client):
    t = json.dumps(good())
    assert client.post("/api/doctor/fix", json={"text": t}).status_code == 400
    assert client.post("/api/doctor/fix", json={"text": t, "fixes": []}).status_code == 400


def test_fix_refuses_a_fix_that_no_longer_applies(client):
    assert client.post("/api/doctor/fix", json={"text": json.dumps(good()), "fixes": ["deadbeef00"]}).status_code == 409


def test_a_fixed_graph_then_passes(client):
    g = json.loads(client.get("/api/doctor/example").json()["text"])
    g["7"] = good()["7"]; g["1"]["inputs"]["ckpt_name"] = "sd_xl_base_1.0.safetensors"; t = json.dumps(g); d = client.post("/api/doctor/check", json={"text": t}).json()
    assert d["fixable"] >= 4
    f = client.post("/api/doctor/fix", json={"text": t, "fixes": [p["id"] for p in d["problems"] if p.get("fix")]}).json()
    assert f["errors_left"] == 0 and f["graph"]["5"]["inputs"]["sampler_name"] == "euler" and f["graph"]["5"]["inputs"]["denoise"] == 1.0 and f["graph"]["3"]["inputs"]["clip"] == ["1", 1]


def test_comfy_away_says_so_and_checks_nothing(client, monkeypatch):
    monkeypatch.setattr(D, "object_info", lambda: None)
    r = client.post("/api/doctor/check", json={"text": json.dumps(good())})
    assert r.status_code == 503 and "not checked" in r.json()["detail"]


@pytest.mark.parametrize("text,word", [("", "nothing here"), ("{not json", "not valid JSON"), ("[1,2]", "JSON object"), ('{"a": 1}', "does not look like")])
def test_bad_input_gets_words(client, text, word):
    r = client.post("/api/doctor/check", json={"text": text}); assert r.status_code == 400 and word in r.json()["detail"]


def test_wrappers_are_understood():
    assert D.shape({"prompt": good()})[0] == "api" and D.shape({"workflow": {"nodes": [], "links": []}})[0] == "ui"


def test_png_with_a_graph_is_read(client):
    info = PngImagePlugin.PngInfo(); info.add_text("prompt", json.dumps(good())); b = io.BytesIO(); Image.new("RGB", (4, 4)).save(b, "PNG", pnginfo=info)
    d = client.post("/api/doctor/check", json={"png": base64.b64encode(b.getvalue()).decode()}).json(); assert d["nodes"] == 7


def test_png_with_no_graph_says_so(client):
    b = io.BytesIO(); Image.new("RGB", (4, 4)).save(b, "PNG")
    r = client.post("/api/doctor/check", json={"png": base64.b64encode(b.getvalue()).decode()}); assert r.status_code == 400 and "no graph" in r.json()["detail"]


def test_a_canvas_file_is_converted(client):
    ui = {"nodes": [{"id": 1, "type": "LoadImage", "mode": 0, "widgets_values": ["a.png"], "inputs": [], "outputs": []}], "links": []}
    d = client.post("/api/doctor/check", json={"text": json.dumps(ui)}).json(); assert d["converted"] and d["format"] == "ui" and d["graph"]["1"]["class_type"] == "LoadImage"


def test_atlas_facts_carry_their_label():
    f = D.atlas_facts(good()); assert f and all(x["label"] and x["plain"] and x["source"] == "atlas" for x in f) and any(x["for"] == "euler" for x in f)


def test_the_language_model_only_rewords_and_may_be_off():
    ps = D.diagnose({**good(), "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 1, "height": 512, "batch_size": 1}}}, OI); saved = json.dumps(ps)
    r = D.reword(ps, chat=lambda m: json.dumps({ps[0]["id"]: "Too small.", "made-up": "Replace the model."}))
    assert r["words"] == {ps[0]["id"]: "Too small."} and json.dumps(ps) == saved
    def off(m): raise RuntimeError("no language model")
    off_r = D.reword(ps, chat=off); assert off_r["available"] is False and off_r["words"] == {} and "off" in off_r["why"]


def test_page_never_changes_without_a_tick():
    js = (Path(D.__file__).parent / "web" / "doctor.js").read_text()
    assert "Nothing has changed yet" in js and "disabled=${!chosen.length" in js and "—" not in js and not re.search(r"https?://", js)
