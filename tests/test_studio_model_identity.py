"""A close file name is not the same model. Graphs must not count as ready, or run, on another model; a precision swap is fine only where the loader handles it. ComfyUI is stubbed."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from studio import apps as A, families_api as F, names as N, server as S
from studio.goals import GOALS

@pytest.mark.parametrize("a,b", [
    ("flux-2-klein-4b.safetensors", "flux-2-klein-9b.safetensors"), ("flux-2-klein-4b.safetensors", "flux-2-klein-base-4b.safetensors"), ("qwen_3_4b.safetensors", "qwen_3_8b.safetensors"),
    ("wan_2.1_vae.safetensors", "wan2.2_vae.safetensors"), ("clip_vision_g.safetensors", "clip_vision_h.safetensors"), ("z_image_int8_convrot.safetensors", "mage_flow_int8_convrot.safetensors"),
    ("qwen_image_2.1_int8_convrot.safetensors", "qwen_image_edit_2509_int8_convrot.safetensors"), ("wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"),
    ("minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", "minimax_h3_ref2v_turbo_8step_v1.0_comfyui_bf16.safetensors"), ("z_image_turbo_bf16.safetensors", "z_image_bf16.safetensors"),
    ("wan2.1_i2v_480p_14B_fp16.safetensors", "wan2.1_i2v_720p_14B_fp16.safetensors"), ("model_fp8.safetensors", "model_fp8.gguf"),
])
def test_another_model_is_not_a_match(a, b):
    assert not N.same_model(a, b) and not A.variant_ok(a, b)

@pytest.mark.parametrize("a,b", [
    ("flux3-klein/flux3_image_klein_bf16.safetensors", "a/flux3-image-klein-bf16.safetensors"), ("z_image_int8_convrot.safetensors", "z_image_bf16.safetensors"), ("wan_2.2_vae.safetensors", "wan2.2_vae.safetensors"),
    ("minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", "minimax_h3/minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors"), ("qwen3.5_9b_pe_i2i.int8_convrot.safetensors", "qwen3.5_9b_pe_i2i_fp16.safetensors"),
])
def test_the_same_model_in_another_folder_precision_or_packaging_matches(a, b):
    assert N.same_model(a, b)

@pytest.mark.parametrize("was,now", list(N.SUBSTITUTE.items()))
def test_the_intended_substitutes_are_the_same_model(was, now):
    assert N.same_model(was, now)

def oi(cls, inp, opts): return {cls: {"input": {"required": {inp: [opts, {}]}}}}
def one(cls, inp, was, opts, **extra):
    g = {"1": {"class_type": cls, "inputs": {inp: was, **extra}}}; g, rep = N.resolve_names(g, oi(cls, inp, opts)); return rep[0]["now"] if rep else g["1"]["inputs"][inp]

def test_the_resolver_finds_the_same_model_even_when_another_model_has_a_closer_name():
    assert one("UNETLoader", "unet_name", "z_image_int8_convrot.safetensors", ["mage_flow_int8_convrot.safetensors", "z_image_bf16.safetensors"]) == "z_image_bf16.safetensors"

def test_the_resolver_leaves_a_look_alike_alone():
    assert one("UNETLoader", "unet_name", "flux-2-klein-4b.safetensors", ["flux-2-klein-9b.safetensors"]) is None

def test_the_resolver_prefers_the_same_precision():
    assert one("UNETLoader", "unet_name", "x_bf16.safetensors", ["x_fp8_scaled.safetensors", "other/x_bf16.safetensors"]) == "other/x_bf16.safetensors"

def test_a_threshold_can_only_narrow_the_match():
    g = lambda: {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_int8_convrot.safetensors"}}}; o = oi("UNETLoader", "unet_name", ["z_image_bf16.safetensors", "mage_flow_int8_convrot.safetensors"])
    assert N.resolve_names(g(), o, threshold=0.5)[1][0]["now"] == "z_image_bf16.safetensors" and N.resolve_names(g(), o, threshold=0.99)[1][0]["now"] is None

def test_precision_swaps_follow_the_loader():
    assert one("UNETLoader", "unet_name", "x_bf16.safetensors", ["x_int8_convrot.safetensors"]) == "x_int8_convrot.safetensors"           # the loader reads quantization metadata
    assert one("UNETLoader", "unet_name", "x_bf16.safetensors", ["x_int8_convrot.safetensors"], weight_dtype="fp8_e4m3fn") is None         # a forced dtype over a quantized file is not a tested path
    assert one("CLIPLoader", "clip_name", "x_bf16.safetensors", ["x_fp8_scaled.safetensors"]) == "x_fp8_scaled.safetensors"
    assert one("CLIPLoader", "clip_name", "x_bf16.safetensors", ["x_int8_convrot.safetensors"]) is None                                    # only named text encoders have quantized ops
    assert one("VAELoader", "vae_name", "x_fp16.safetensors", ["x_int8_convrot.safetensors"]) is None
    assert one("WanVideoModelLoader", "model", "x_bf16.safetensors", ["x_fp8_scaled.safetensors"]) is None                                 # a pack loader has its own precision settings
    assert one("WanVideoModelLoader", "model", "x_bf16.safetensors", ["sub/x_bf16.safetensors"]) == "sub/x_bf16.safetensors"

def test_substitutes_still_apply():
    assert one("VAELoader", "vae_name", "minimax_h3_video_vae_int8_convrot.safetensors", ["minimax_h3_video_vae_fp16.safetensors"]) == "minimax_h3_video_vae_fp16.safetensors"
    assert one("CLIPLoader", "clip_name", "minimax_music3_text_encoder_pruned_bf16.safetensors", ["minimax_music3_text_encoder_pruned_int8_convrot.safetensors"]) == "minimax_music3_text_encoder_pruned_int8_convrot.safetensors"

# ---- a goal: /api/generate
GRAPH = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-4b.safetensors"}}, "2": {"class_type": "SaveImage", "inputs": {"prefix": "${prompt}"}}}

@pytest.fixture
def box(monkeypatch, tmp_path):
    tpl = tmp_path / "g.json"; tpl.write_text(json.dumps(GRAPH)); posted = []; b = {"opts": [], "posted": posted}
    monkeypatch.setitem(GOALS, "tgoal", {**GOALS["image"], "template": str(tpl)}); monkeypatch.setattr(S, "WF", "/")
    monkeypatch.setattr(S, "values_for", lambda goal, req, img: ({"prompt": "a cat", "seed": 1}, {}))
    def comfy(path, payload=None, **k):
        if path == "/object_info": return oi("UNETLoader", "unet_name", b["opts"])
        if path == "/prompt": posted.append(payload["prompt"]); return {"prompt_id": "p1"}
        return {}
    monkeypatch.setattr(S, "comfy", comfy); monkeypatch.setattr(S, "comfy_up", lambda: True)
    b["client"] = TestClient(S.app); return b

def test_a_goal_does_not_run_on_another_model(box):
    box["opts"] = ["flux-2-klein-9b.safetensors"]; r = box["client"].post("/api/generate", json={"goal": "tgoal", "prompt": "a cat"})
    assert r.status_code == 400 and "flux-2-klein-4b.safetensors" in r.json()["detail"] and not box["posted"]

def test_a_goal_runs_on_another_precision_of_its_model(box):
    box["opts"] = ["flux-2-klein-9b.safetensors", "sub/flux-2-klein-4b-fp8.safetensors"]; r = box["client"].post("/api/generate", json={"goal": "tgoal", "prompt": "a cat"})
    assert r.status_code == 200 and box["posted"][0]["1"]["inputs"]["unet_name"] == "sub/flux-2-klein-4b-fp8.safetensors"

def test_showing_the_graph_never_refuses(box):
    box["opts"] = ["flux-2-klein-9b.safetensors"]; r = box["client"].post("/api/graph", json={"goal": "tgoal", "prompt": "a cat"})
    assert r.status_code == 200 and r.json()["graph"]["1"]["inputs"]["unet_name"] == "flux-2-klein-4b.safetensors"

# ---- a family template: readiness and the app form
@pytest.fixture
def shared(monkeypatch):
    b = {"d": {}}; monkeypatch.setattr(F, "shared_files", lambda: b["d"]); F._look.update(a=None, b=None, d={}); F._keys.update(id=None, d={}); yield b
    F._look.update(a=None, b=None, d={}); F._keys.update(id=None, d={})

@pytest.mark.parametrize("want,folder,have,ready", [
    ("flux-2-klein-4b.safetensors", "diffusion_models", "flux-2-klein-9b.safetensors", False), ("flux-2-klein-4b.safetensors", "diffusion_models", "flux-2-klein-4b-fp8.safetensors", True),
    ("z_image_int8_convrot.safetensors", "diffusion_models", "z_image_bf16.safetensors", True), ("x_bf16.safetensors", "text_encoders", "x_int8_convrot.safetensors", False), ("x_bf16.safetensors", "controlnet", "x_fp16.safetensors", False),
    ("x_fp8.safetensors", "diffusion_models", "x.gguf", False), ("minimax_h3_video_vae_int8_convrot.safetensors", "vae", "minimax_h3_video_vae_fp16.safetensors", True), ("exact.safetensors", "controlnet", "exact.safetensors", True),
])
def test_template_readiness_matches_what_the_run_would_load(shared, want, folder, have, ready):
    s = F.tpl_state({"models": [{"name": want, "dir": folder}]}, {have: 1000})
    assert s["ready"] is ready and bool(s["missing"]) is not ready

def test_an_app_on_a_look_alike_is_not_runnable(tmp_path):
    ui = {"nodes": [{"id": 1, "type": "UNETLoader", "widgets_values": ["flux-2-klein-4b.safetensors", "default"], "inputs": [], "outputs": []}], "links": [], "extra": {"linearMode": True, "linearData": {"inputs": [], "outputs": []}}}
    p = tmp_path / "a.json"; p.write_text(json.dumps(ui)); o = {"UNETLoader": {"input": {"required": {"unet_name": [["flux-2-klein-9b.safetensors"], {}], "weight_dtype": [["default"], {}]}}, "input_order": {"required": ["unet_name", "weight_dtype"]}, "output": ["MODEL"]}}
    d = A.describe("a", str(p), o); assert d["missing_models"] == ["flux-2-klein-4b.safetensors"] and not d["runnable"]

ROOT = Path(A.__file__).resolve().parent
def template_models():
    rows = [(t["name"], m) for f in json.load(open(ROOT / "family_status.json"))["families"].values() for t in f.get("templates", []) for m in t.get("models", [])]
    idx = ROOT / "family_templates" / "index.json"
    if idx.exists(): rows += [(t["name"], m) for t in json.load(open(idx))["templates"] for m in t.get("models", [])]
    return rows

def test_every_template_is_ready_when_its_own_files_are_installed(shared):
    rows = template_models(); assert rows; files = {m["name"].split("/")[-1]: 1 for _, m in rows}
    assert not [(n, m["name"]) for n, m in rows if F._have(files, m["name"], m.get("dir")) != m["name"].split("/")[-1]]
