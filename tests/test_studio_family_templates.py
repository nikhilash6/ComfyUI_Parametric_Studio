"""The studio's own family templates: API-format graphs load, show a usable form, build, and never need a live port or a partner node."""
import json
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import apps as A
from studio import families_api as F

D = Path(A.__file__).resolve().parent / "family_templates"
INDEX = json.load(open(D / "index.json"))["templates"]
OI = {"LoadImage": {"input": {"required": {"image": [["a.png"]]}}, "output": ["IMAGE", "MASK"]},
      "CLIPTextEncode": {"input": {"required": {"text": ["STRING", {}], "clip": ["CLIP", {}]}}, "output": ["CONDITIONING"]},
      "KSampler": {"input": {"required": {"seed": ["INT", {}]}}, "output": ["LATENT"]},
      "UNETLoader": {"input": {"required": {"unet_name": [["here.safetensors"]]}}, "output": ["MODEL"]},
      "SaveVideo": {"input": {"required": {"video": ["VIDEO", {}]}}, "output": [], "output_node": True}}
G = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "here.safetensors"}}, "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a boat", "clip": ["1", 0]}},
     "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "low quality, blurry", "clip": ["1", 0]}}, "4": {"class_type": "KSampler", "inputs": {"seed": 7}},
     "5": {"class_type": "LoadImage", "inputs": {"image": "a.png"}}, "6": {"class_type": "SaveVideo", "inputs": {"video": ["4", 0]}}}

@pytest.fixture()
def graph(tmp_path):
    p = tmp_path / "g.json"; p.write_text(json.dumps(G)); return str(p)

def test_an_api_graph_is_recognised_and_a_ui_workflow_is_not():
    assert A.is_api_graph(G) and not A.is_api_graph({"nodes": [], "links": []}) and not A.is_api_graph({})

def test_the_form_has_media_positive_prompt_and_seed_but_not_the_negative(graph):
    d = A.describe("g", graph, OI); keys = {i["key"]: i["type"] for i in d["inputs"]}
    assert keys == {"2|text": "text", "4|seed": "number", "5|image": "image"} and not d["unknown_nodes"] and not d["problems"] and d["runnable"]

def test_a_node_missing_from_the_server_is_reported(graph):
    oi = {k: v for k, v in OI.items() if k != "KSampler"}; d = A.describe("g", graph, oi)
    assert d["unknown_nodes"] == ["KSampler"] and not d["runnable"]

def test_build_applies_values_and_rejects_an_unknown_node(graph):
    g = A.build_graph(graph, {"2|text": "a lamp", "5|image": "b.png"}, OI)
    assert g["2"]["inputs"]["text"] == "a lamp" and g["5"]["inputs"]["image"] == "b.png" and g["6"]["inputs"]["format"] == "auto"
    with pytest.raises(ValueError): A.build_graph(graph, {"99|text": "x"}, OI)

def test_every_indexed_template_has_a_graph_real_fields_and_no_partner_node():
    assert INDEX
    for t in INDEX:
        g = json.load(open(D / (t["name"] + ".json")))
        assert A.is_api_graph(g) and t["family"] and t["title"] and t["media"] in ("image", "video", "audio", "3d") and isinstance(t["models"], list)
        assert not [n for n in g.values() if n["class_type"].startswith(("Bria", "Kling", "Runway", "Luma", "Veo", "OpenAI", "Stability", "Gemini"))]
        for m in t["models"]: assert m["name"] and m["dir"]

@pytest.fixture()
def client(tmp_path, monkeypatch):
    st = tmp_path / "family_status.json"; st.write_text(json.dumps({"families": {"Fam": {"slug": "fam", "kind": "image", "templates": [{"name": "official", "models": []}]}, "Bare": {"slug": "bare", "kind": "image"}}}))
    ex = tmp_path / "extra"; ex.mkdir(); (ex / "t1.json").write_text(json.dumps(G))
    (ex / "index.json").write_text(json.dumps({"templates": [{"family": "Bare", "name": "t1", "title": "T", "models": []}, {"family": "Nobody", "name": "t2", "models": []}]}))
    monkeypatch.setattr(F, "STATUS", st); monkeypatch.setattr(F, "EXTRA", ex); F._st.update(m=0.0, d={"families": {}})
    monkeypatch.setattr(F, "_family", lambda s: {"fam": "Fam", "bare": "Bare"}[s]); monkeypatch.setattr(A, "object_info", lambda *a, **k: OI)
    app = FastAPI(); app.include_router(F.router); yield TestClient(app), ex
    F._st.update(m=0.0, d={"families": {}})

def test_studio_templates_merge_into_their_family_only(client):
    d = F.status_data()["families"]
    assert [t["name"] for t in d["Bare"]["templates"]] == ["t1"] and d["Bare"]["templates"][0]["studio"] and [t["name"] for t in d["Fam"]["templates"]] == ["official"] and "Nobody" not in d

def test_tpl_finds_the_studio_file_and_a_missing_graph_is_an_error(client):
    _, ex = client; F.status_data(); t, p = F._tpl("Bare", "t1"); assert t["title"] == "T" and p == str(ex / "t1.json")
    (ex / "t1.json").unlink()
    with pytest.raises(F.HTTPException): F._tpl("Bare", "t1")

def test_the_graph_route_returns_the_api_graph_unchanged(client):
    c, _ = client; F.status_data(); j = c.get("/api/family-graphs/bare/t1").json(); assert j["format"] == "api" and j["graph"]["2"]["inputs"]["text"] == "a boat"

def test_a_broken_index_leaves_the_status_alone(tmp_path, monkeypatch):
    ex = tmp_path / "e"; ex.mkdir(); (ex / "index.json").write_text("{not json"); monkeypatch.setattr(F, "EXTRA", ex); d = {"families": {"A": {}}}
    assert F._with_extra(d) == {"families": {"A": {}}}

def test_a_wrapped_file_that_lands_later_refreshes_a_stopped_instance_only(tmp_path, monkeypatch):
    models, inst = tmp_path / "m", tmp_path / "i"; (models / "diffusion_models").mkdir(parents=True); (inst / "fam" / "models" / "checkpoints").mkdir(parents=True)
    monkeypatch.setattr(F.I, "MODELS", str(models)); monkeypatch.setattr(F.I, "INSTANCES", str(inst)); monkeypatch.setitem(F.I.WRAPS, "Fam", {"files": [("checkpoints", "c.safetensors", "diffusion_models/c.safetensors")]})
    info = {"slug": "fam", "port": 9}; up = {"v": False}; monkeypatch.setattr(F.I, "is_up", lambda p: up["v"])
    assert not F._wrap_stale("Fam", info)
    (models / "diffusion_models" / "c.safetensors").write_bytes(b"x"); assert F._wrap_stale("Fam", info)
    up["v"] = True; assert not F._wrap_stale("Fam", info); up["v"] = False
    (inst / "fam" / "models" / "checkpoints" / "c.safetensors").symlink_to(models / "diffusion_models" / "c.safetensors"); assert not F._wrap_stale("Fam", info)

FIBO_OI = {"UNETLoader": {"input": {"required": {"unet_name": [["fibo2_dev_int8_convrot.safetensors"]]}}, "output": ["MODEL"]}, "CLIPLoader": {"input": {"required": {"clip_name": [["qwen3vl_4b_bf16.safetensors"]], "type": [["fibo2"]]}}, "output": ["CLIP"]}, "VAELoader": {"input": {"required": {"vae_name": [["flux2-vae.safetensors"]]}}, "output": ["VAE"]},
           "TextEncodeFibo2": {"input": {"required": {"clip": ["CLIP", {}], "prompt": ["STRING", {}], "negative_prompt": ["STRING", {}]}}, "output": ["CONDITIONING", "CONDITIONING", "LATENT"]}, "KSampler": {"input": {"required": {"seed": ["INT", {}]}}, "output": ["LATENT"]}, "VAEDecode": {"input": {"required": {}}, "output": ["IMAGE"]}, "SaveImage": {"input": {"required": {}}, "output": [], "output_node": True}}

def test_fibo2_says_it_is_non_commercial_everywhere_a_user_reads_it():
    root = D.parent; fam = json.load(open(root / "family_status.json", encoding="utf8"))["families"]["Fibo-2.0"]
    assert "non-commercial" in fam["licence"].lower() and "CC-BY-NC-4.0" in fam["licence"] and "non-commercial" in fam["what"].lower() and fam["slug"] == "fibo-2-0" and fam["level"] == "render"  # rendered 2026-11-01
    assert [t["name"] for t in fam["templates"]] == ["image_fibo2_edit_dev_pe", "image_fibo2_edit_turbo_pe"] and all(m["gb"] for t in fam["templates"] for m in t["models"])
    t2i = next(t for t in INDEX if t["name"] == "fibo2_dev_t2i"); assert t2i["family"] == "Fibo-2.0" and "non-commercial" in t2i["desc"].lower()
    atlas = next(m for m in json.load(open(root / "atlas_models.json", encoding="utf8"))["models"] if m["family"] == "Fibo-2.0"); assert atlas["licence_class"] == "noncommercial"
    assert {n for _, n, _ in F.I.WRAPS["Fibo-2.0"]["files"]} == {"qwen3vl_4b_bf16.safetensors", "qwen3vl_8b_int8_convrot.safetensors", "flux2-vae.safetensors"} and "non-commercial" in F.I.WRAPS["Fibo-2.0"]["note"]

def test_fibo2_text_to_image_needs_no_reference_image_and_its_prompt_is_on_the_form():
    p = str(D / "fibo2_dev_t2i.json"); g = json.load(open(p)); d = A.describe("fibo2_dev_t2i", p, FIBO_OI)
    assert {i["key"]: i["type"] for i in d["inputs"]} == {"4|prompt": "text", "5|seed": "number"} and d["runnable"] and not d["unknown_nodes"]
    assert g["2"]["inputs"]["type"] == "fibo2" and g["5"]["inputs"]["latent_image"] == ["4", 2] and g["5"]["inputs"]["negative"] == ["4", 1] and (g["5"]["inputs"]["steps"], g["5"]["inputs"]["cfg"]) == (50, 5.0)
    assert not [k for k in g["4"]["inputs"] if k.startswith("images")] and "vae" not in g["4"]["inputs"] and A.build_graph(p, {"4|prompt": "a lamp"}, FIBO_OI)["4"]["inputs"]["prompt"] == "a lamp"
