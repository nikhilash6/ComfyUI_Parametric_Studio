"""LoRA Showcase: built only from a run's own record, no upload anywhere, and a bundle without pictures or paths. ComfyUI is stubbed; no live ports."""
import io, json, re, zipfile
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from studio import feature_lorashow as S, train as T

WEB = Path(S.__file__).parent / "web"
FAKE_HOME = "/".join(("", "home", "someone"))       # a made-up folder, spelled so the scan for this repo's real paths stays useful


def png():
    b = io.BytesIO(); Image.new("RGB", (8, 8), (9, 9, 9)).save(b, "PNG"); return b.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_TRAIN_DIR", str(tmp_path / "train")); monkeypatch.setattr(T, "_comfy", lambda *a, **k: png())
    lora = tmp_path / "my.safetensors"; lora.write_bytes(b"w" * 2048); (tmp_path / "train" / "jobs").mkdir(parents=True)
    job = {"id": "a" * 12, "name": "Brass Lamp", "trigger": "brslmp", "state": "done", "base": "sdxl-base-1.0", "base_file": "sd_xl_base_1.0.safetensors", "created": 1, "ended": 1793000000, "running_at": 1792999000, "gpu": "cuda:0 NVIDIA X : cudaMallocAsync", "peak_vram_gib": 40.2, "settings": {"steps": 300, "rank": 8, "batch": 1, "size": 1024, "learning_rate": 0.0005, "seed": 3}, "curve": [[1, 0.5], [300, 0.1]], "speed_from_log": 0.6, "folder": FAKE_HOME + "/private/pics", "lora": {"name": "parametric_trained/my.safetensors", "path": str(lora), "bytes": 2048, "sha256": "f" * 64, "tensors": 4, "total_steps": 300},
           "ab": {"state": "done", "prompt": "brslmp on a table", "seed": 7, "strength": 1.0, "pixel_diff": 12.5, "unbound_keys": 0, "base": {"filename": "a.png", "subfolder": "", "type": "output", "url": "/x"}, "lora": {"filename": "b.png", "subfolder": "", "type": "output", "url": "/y"}, "graph": {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": FAKE_HOME + "/m/sd.safetensors"}}}}}
    (tmp_path / "train" / "jobs" / (job["id"] + ".json")).write_text(json.dumps(job))
    app = FastAPI(); app.include_router(S.router); c = TestClient(app); c.jid = job["id"]; c.path = tmp_path / "train" / "jobs" / (job["id"] + ".json"); return c


def test_the_card_comes_from_the_record(client):
    c = client.get("/api/lorashow/card/" + client.jid).json(); f = c["facts"]
    assert c["trigger"] == "brslmp" and f["steps"] == 300 and f["sha256"] == "f" * 64 and f["base_licence"]["name"].startswith("CreativeML") and c["ab"]["pixel_diff"] == 12.5 and c["licence"] is None and not c["ready"]


def test_a_card_cannot_rewrite_the_record(client):
    c = client.post("/api/lorashow/card/" + client.jid, json={"trigger": "fake", "sha256": "x", "pixel_diff": 99, "description": "Mine"}).json()
    assert c["trigger"] == "brslmp" and c["ab"]["pixel_diff"] == 12.5 and c["description"] == "Mine"


def test_no_ab_means_no_proof(client):
    j = json.loads(client.path.read_text()); j.pop("ab"); client.path.write_text(json.dumps(j)); c = client.get("/api/lorashow/card/" + client.jid).json()
    assert c["ab"]["state"] == "none" and "no proof" in c["ab"]["said"] and "No A/B test" in S.model_card(c)


@pytest.mark.parametrize("edit,word", [({"pixel_diff": 0}, "changed nothing"), ({"unbound_keys": 5}, "did not attach")])
def test_a_weak_ab_is_warned(client, edit, word):
    j = json.loads(client.path.read_text()); j["ab"].update(edit); client.path.write_text(json.dumps(j)); assert word in " ".join(client.get("/api/lorashow/card/" + client.jid).json()["ab"]["warn"])


def test_a_gone_file_or_unfinished_run_has_no_page(client):
    j = json.loads(client.path.read_text()); j["state"] = "running"; client.path.write_text(json.dumps(j)); assert client.get("/api/lorashow/card/" + client.jid).status_code == 404
    assert client.get("/api/lorashow/card/nope").status_code == 404


def test_the_licence_is_never_chosen_for_you(client):
    assert client.get(f"/api/lorashow/card/{client.jid}/bundle").status_code == 409
    assert client.post("/api/lorashow/card/" + client.jid, json={"licence": "Made Up"}).status_code == 400


def bundle(client, q=""):
    client.post("/api/lorashow/card/" + client.jid, json={"licence": "MIT", "description": "A lamp."}); r = client.get(f"/api/lorashow/card/{client.jid}/bundle{q}"); assert r.status_code == 200; return zipfile.ZipFile(io.BytesIO(r.content))


def test_the_bundle_holds_proof_and_no_paths_or_pictures(client):
    z = bundle(client); names = set(z.namelist())
    assert {"README.md", "ab/with_lora.png", "ab/without_lora.png", "ab/graph.json", "loss.csv", "record.json"} <= names and "my.safetensors" not in names
    text = " ".join(z.read(n).decode() for n in names if not n.endswith(".png")); assert FAKE_HOME not in text and not S._scrub_graph(text) != text and "brslmp" in z.read("README.md").decode() and "Training pictures are not included" in z.read("README.md").decode()


def test_weights_only_when_asked(client):
    assert "my.safetensors" in bundle(client, "?weights=true").namelist()


def test_a_comfy_that_is_away_is_said_in_the_bundle(client, monkeypatch):
    def away(*a, **k): raise OSError
    monkeypatch.setattr(T, "_comfy", away); z = bundle(client); assert "ab/with_lora.png" not in z.namelist() and "could not be fetched" in z.read("README.md").decode()


def test_nothing_here_can_upload():
    src = Path(S.__file__).read_text(); js = (WEB / "lorashow.js").read_text()
    assert "urlopen" not in src and "requests" not in src and "POST" not in src.upper().replace("POST(", "") .replace("ROUTER.POST", "") and "fetch(" not in js
    assert "Nothing is uploaded" in js and "—" not in js


def test_train_links_here():
    assert "#lorashow/" in (WEB / "train.js").read_text()
