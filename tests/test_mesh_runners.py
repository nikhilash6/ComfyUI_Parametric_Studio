"""The 3D runners' pure parts: no GPU, no network and no model loaded."""
import importlib.util, sys, types
from pathlib import Path
import pytest

R = Path(__file__).resolve().parent.parent / "studio" / "worldkit" / "runners"
def load(n):
    s = importlib.util.spec_from_file_location(n, R / f"{n}.py"); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def test_triposr_maps_old_vit_names_and_leaves_the_rest():
    T = load("triposr_image")
    sd = {"image_tokenizer.model.encoder.layer.0.attention.attention.query.weight": 1, "image_tokenizer.model.encoder.layer.0.intermediate.dense.bias": 2, "image_tokenizer.model.encoder.layer.0.output.dense.bias": 3, "image_tokenizer.model.encoder.layer.0.attention.output.dense.bias": 4, "decoder.x": 5}
    want = {"image_tokenizer.model.layers.0.attention.q_proj.weight", "image_tokenizer.model.layers.0.mlp.fc1.bias", "image_tokenizer.model.layers.0.mlp.fc2.bias", "image_tokenizer.model.layers.0.attention.o_proj.bias", "decoder.x"}
    assert set(T.new_names(sd, want)) == want


def test_triposr_never_reaches_for_the_network(tmp_path, monkeypatch):
    T = load("triposr_image"); hub = types.SimpleNamespace(hf_hub_download=None); monkeypatch.setitem(sys.modules, "huggingface_hub", hub); monkeypatch.setitem(sys.modules, "folder_paths", None); del sys.modules["folder_paths"]
    T.offline(str(tmp_path))
    assert Path(hub.hf_hub_download(repo_id="x", filename="config.json", endpoint="https://example.invalid")).read_text().startswith("{") and sys.modules["folder_paths"].models_dir == str(tmp_path)


def test_shap_e_clip_keys_lose_their_prefix(tmp_path):
    st = pytest.importorskip("safetensors.torch"); torch = pytest.importorskip("torch"); S = load("shap_e_text")
    p = tmp_path / "c.safetensors"; st.save_file({"clip_l.text_model.x": torch.zeros(1), "logit_scale": torch.zeros(1), "text_projection.weight": torch.zeros(1)}, str(p))
    assert set(S.clip_state(p)) == {"text_model.x", "text_projection.weight"}
