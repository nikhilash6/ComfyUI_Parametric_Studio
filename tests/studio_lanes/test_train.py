"""The Train page's server side, on a stand-in ComfyUI. No live port is touched: _comfy is replaced, and so is every folder. The fixture object_info is copied from a real /object_info, with the model lists cut down. Loss values here are test data."""
import io, json, os, struct, sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio import train

FIXTURE = json.loads((Path(__file__).parent / "fixture_train_object_info.json").read_text())


def st_file(path, tensors):
    """A real safetensors header with zero-length data, enough for read_header."""
    head = json.dumps({k: {"dtype": v, "shape": [0], "data_offsets": [0, 0]} for k, v in tensors.items()}).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<Q", len(head)) + head)


SDXL_KEYS = {"conditioner.embedders.1.model.x": "F16", "model.diffusion_model.a": "F16", "first_stage_model.b": "F16"}


class FakeComfy:
    """The answers ComfyUI gives, for one prompt at a time."""
    def __init__(self, tmp):
        self.info = json.loads(json.dumps(FIXTURE))
        self.posted, self.interrupted, self.deleted = [], [], []
        self.queue = {"queue_running": [], "queue_pending": []}
        self.history, self.logs, self.reject = {}, [], None
        self.tmp = tmp
        self.view = {}

    def __call__(self, path, payload=None, timeout=30, raw=False):
        if path == "/object_info":
            self.info["LoadImageTextDataSetFromFolder"]["input"]["required"]["folder"][1]["options"] = self.folders()
            return self.info
        if path == "/object_info/LoadImageTextDataSetFromFolder":
            self("/object_info")
            return {"LoadImageTextDataSetFromFolder": self.info["LoadImageTextDataSetFromFolder"]}
        if path == "/internal/folder_paths":
            return {"checkpoints": [str(self.tmp / "models" / "checkpoints")], "loras": [str(self.tmp / "models" / "loras")]}
        if path == "/system_stats":
            return {"devices": [{"name": "cuda:0 Test Card : cudaMallocAsync", "vram_free": 80 * 2**30, "vram_total": 96 * 2**30}], "system": {"argv": []}}
        if path == "/prompt":
            if self.reject: raise self.reject
            self.posted.append(payload["prompt"])
            pid = f"p{len(self.posted)}"
            self.queue["queue_pending"].append([0, pid])
            return {"prompt_id": pid}
        if path == "/queue":
            if payload: self.deleted += payload.get("delete", []); self.queue["queue_pending"] = [e for e in self.queue["queue_pending"] if e[1] not in payload.get("delete", [])]; return {}
            return self.queue
        if path == "/interrupt":
            self.interrupted.append(payload.get("prompt_id")); return {}
        if path.startswith("/history/"):
            pid = path.split("/")[-1]
            return {pid: self.history[pid]} if pid in self.history else {}
        if path == "/internal/logs/raw":
            return {"entries": self.logs}
        if path.startswith("/view?"):
            return self.view[path.split("filename=")[1].split("&")[0]]
        raise AssertionError(f"unexpected call {path}")

    def folders(self):
        root = self.tmp / "input"
        return ["3d"] + [str(p.relative_to(root)) for p in root.rglob("*") if p.is_dir()] if root.is_dir() else ["3d"]

    def run(self, pid):
        self.queue["queue_pending"] = [e for e in self.queue["queue_pending"] if e[1] != pid]
        self.queue["queue_running"] = [[0, pid]]


@pytest.fixture
def env(tmp_path, monkeypatch):
    for k, v in {"STUDIO_TRAIN_DIR": "data", "STUDIO_COMFY_INPUT": "input", "STUDIO_OUTPUT_DIR": "output", "STUDIO_MODELS_ROOT": "models"}.items():
        monkeypatch.setenv(k, str(tmp_path / v))
    (tmp_path / "input").mkdir()
    st_file(tmp_path / "models" / "checkpoints" / "sd_xl_base_1.0.safetensors", SDXL_KEYS)
    fake = FakeComfy(tmp_path)
    monkeypatch.setattr(train, "_comfy", fake)
    monkeypatch.setattr(train, "_gpu_used_gib", lambda: 12.5)
    monkeypatch.setattr(train, "AUTO_MONITOR", False)
    monkeypatch.setattr(train, "measurements", lambda: [{"base": "sdxl-base-1.0", "size": 1024, "rank": 8, "batch": 1, "steps": 200, "s_per_step": 0.5, "peak_vram_gib": 14.0, "setup_seconds": 9.0, "gpu": "cuda:0 Test Card : cudaMallocAsync", "date": "2026-11-01"}])
    app = FastAPI(); app.include_router(train.router)
    return fake, TestClient(app), tmp_path


def png(color=(90, 120, 200), size=(32, 32), noise=True):
    im = Image.new("RGB", size, color)
    if noise:
        for x in range(size[0]):
            for y in range(0, size[1], 2): im.putpixel((x, y), ((x * 7) % 255, (y * 11) % 255, (x * y) % 255))
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()


def dataset(c, n=3, captions=True):
    r = c.post("/api/train/datasets", json={"name": "Lighthouses"}).json()
    files = [("files", (f"pic{i}.png", png(size=(40 + i, 40)), "image/png")) for i in range(n)]
    if captions: files += [("files", (f"pic{i}.txt", f"brasslight, a lighthouse number {i}".encode(), "text/plain")) for i in range(n)]
    assert c.post(f"/api/train/datasets/{r['id']}/upload", files=files).status_code == 200
    return r["id"]


GOOD = {"name": "Brass light", "trigger": "brasslight", "base": "sdxl-base-1.0", "size": 1024, "steps": 4, "rank": 8, "batch": 1, "learning_rate": 0.0005, "seed": 1, "rights_confirmed": True}


# ---------- the graph, against object_info ----------

def test_training_graph_fits_real_object_info():
    info = json.loads(json.dumps(FIXTURE))
    info["LoadImageTextDataSetFromFolder"]["input"]["required"]["folder"][1]["options"] = ["parametric_train/abc"]
    g = train.training_graph("sd_xl_base_1.0.safetensors", "parametric_train/abc", 300, 8, 1, 0.0005, 1, "parametric_train/abc/lora")
    assert train.validate_graph(g, info) == []
    assert {n["class_type"] for n in g.values()} >= {"TrainLoraNode", "MakeTrainingDataset", "LoadImageTextDataSetFromFolder", "SaveLoRA", "PreviewAny"}
    assert "PSN_LoRA_Train_HunYuan" not in json.dumps(g)


def test_ab_graph_fits_real_object_info():
    info = json.loads(json.dumps(FIXTURE))
    info["LoraLoaderModelOnly"]["input"]["required"]["lora_name"][0] = ["parametric_trained/x.safetensors"]
    g = train.ab_graph("sd_xl_base_1.0.safetensors", "parametric_trained/x.safetensors", "a lighthouse", "", 1024, 1024, 5, 1.0, "ab/x")
    assert train.validate_graph(g, info) == []
    assert g["6"]["inputs"]["seed"] == g["7"]["inputs"]["seed"]
    assert g["6"]["inputs"]["model"] == ["1", 0] and g["7"]["inputs"]["model"] == ["2", 0]


@pytest.mark.parametrize("change, expect", [
    (lambda g: g["4"]["inputs"].pop("rank"), "missing rank"),
    (lambda g: g["4"]["inputs"].update(steps=0), "out of range"),
    (lambda g: g["4"]["inputs"].update(optimizer="Nope"), "not an option"),
    (lambda g: g["5"]["inputs"].update(lora=["1", 0]), "wants LORA_MODEL"),
    (lambda g: g["3"]["inputs"].update(vae=["9", 0]), "missing node 9"),
    (lambda g: g["3"]["inputs"].update(vae=["1", 9]), "links to output 9"),
    (lambda g: g["4"]["inputs"].update(made_up=1), "no input called"),
    (lambda g: g["1"].update(class_type="PSN_LoRA_Train_HunYuan"), "not installed"),
])
def test_validator_catches_a_bad_graph(change, expect):
    info = json.loads(json.dumps(FIXTURE))
    info["LoadImageTextDataSetFromFolder"]["input"]["required"]["folder"][1]["options"] = ["f"]
    g = train.training_graph("sd_xl_base_1.0.safetensors", "f", 10, 8, 1, 0.0005, 1, "p")
    change(g)
    assert any(expect in p for p in train.validate_graph(g, info))


# ---------- bases ----------

GPU = "cuda:0 Test Card : cudaMallocAsync"


def test_only_an_unquantized_proven_base_on_disk_is_offered(env):
    fake, c, tmp = env
    rows = {r["id"]: r for r in c.get("/api/train/info").json()["bases"]}
    assert rows["sdxl-base-1.0"]["trainable"] and "Proved by a real run" in rows["sdxl-base-1.0"]["proof"]
    assert not rows["sd-1.5"]["trainable"]        # listed by ComfyUI in the fixture, but the file is not on this disk


def test_a_quantized_or_mislabelled_file_is_refused(env, monkeypatch):
    fake, c, tmp = env
    st_file(tmp / "models" / "checkpoints" / "sd_xl_base_1.0.safetensors", {**SDXL_KEYS, "model.diffusion_model.a": "F8_E4M3"})
    row = next(r for r in c.get("/api/train/info").json()["bases"] if r["id"] == "sdxl-base-1.0")
    assert not row["trainable"] and "not plain floats" in row["why_not"]
    st_file(tmp / "models" / "checkpoints" / "sd_xl_base_1.0.safetensors", {"model.diffusion_model.a": "F16"})
    row = next(r for r in c.get("/api/train/info").json()["bases"] if r["id"] == "sdxl-base-1.0")
    assert not row["trainable"] and "do not match" in row["why_not"]


def test_a_base_with_no_run_on_record_is_not_offered(env, monkeypatch):
    fake, c, tmp = env
    monkeypatch.setattr(train, "measurements", lambda: [])
    row = next(r for r in c.get("/api/train/info").json()["bases"] if r["id"] == "sdxl-base-1.0")
    assert not row["trainable"] and "No training run on record" in row["why_not"]


def test_a_first_run_needs_the_setting_and_says_so(env, monkeypatch):
    fake, c, tmp = env
    monkeypatch.setattr(train, "measurements", lambda: [])
    monkeypatch.setenv("STUDIO_TRAIN_PROVE", "sdxl-base-1.0")
    row = next(r for r in c.get("/api/train/info").json()["bases"] if r["id"] == "sdxl-base-1.0")
    assert row["trainable"] and "Not proved yet" in row["proof"]
    assert train.estimate("sdxl-base-1.0", 1024, 8, 1, 300, GPU)["measured"] is False


# ---------- estimates ----------

GPU = "cuda:0 Test Card : cudaMallocAsync"


def test_estimate_only_from_measurement(env):
    e = train.estimate("sdxl-base-1.0", 1024, 8, 1, 300, GPU)
    assert e["measured"] and e["exact"] and e["train_seconds"] == 150 and e["peak_vram_gib"] == 14.0
    near = train.estimate("sdxl-base-1.0", 1024, 16, 1, 300, GPU)
    assert near["measured"] and not near["exact"] and "not rank 16" in near["note"]
    for args in (("sdxl-base-1.0", 768, 8, 1, 300, GPU), ("sdxl-base-1.0", 1024, 8, 2, 300, GPU), ("sdxl-base-1.0", 1024, 8, 1, 300, "cuda:0 Another : x"), ("sd-1.5", 512, 8, 1, 300, GPU)):
        e = train.estimate(*args)
        assert e["measured"] is False and "train_seconds" not in e and "peak_vram_gib" not in e


# ---------- word checks and the tick ----------

@pytest.mark.parametrize("text", ["nude", "nude_01", "my-nsfw-set", "NSFW.png", "explicit shot", "loli style", "underage_girl", "porn2"])
def test_word_check_reads_names_too(text):
    assert train.flagged(text)


@pytest.mark.parametrize("text", ["Essex lighthouse", "brass_light_01", "a child's kite on a beach", ""])
def test_word_check_passes_clean_text(text):
    assert not train.flagged(text)


def test_flagged_caption_blocks_and_can_be_fixed(env):
    fake, c, tmp = env
    ds = dataset(c)
    r = c.post(f"/api/train/datasets/{ds}/captions", json={"captions": {"pic0.png": "a nude figure"}}).json()
    assert not r["ready"] and any(p["code"] == "word_list" for p in r["items"][0]["problems"])
    assert c.post("/api/train/jobs", json={**GOOD, "dataset": ds}).status_code == 400
    assert fake.posted == []
    r = c.post(f"/api/train/datasets/{ds}/captions", json={"captions": {"pic0.png": "a lighthouse"}}).json()
    assert r["ready"]


def test_flagged_file_name_blocks(env):
    fake, c, tmp = env
    ds = dataset(c)
    c.post(f"/api/train/datasets/{ds}/upload", files=[("files", ("nude_01.png", png(), "image/png")), ("files", ("nude_01.txt", b"a lighthouse", "text/plain"))])
    assert not c.get(f"/api/train/datasets/{ds}").json()["ready"]


@pytest.mark.parametrize("change", [{"rights_confirmed": False}, {"rights_confirmed": "yes"}, {"rights_confirmed": None}])
def test_training_needs_the_tick(env, change):
    fake, c, tmp = env
    r = c.post("/api/train/jobs", json={**GOOD, "dataset": dataset(c), **change})
    assert r.status_code == 400 and "rights" in r.json()["detail"] and fake.posted == []


@pytest.mark.parametrize("change", [{"name": "nude set"}, {"trigger": "porn"}, {"trigger": "two words"}, {"name": ""}, {"base": "PSN_LoRA_Train_HunYuan"}, {"steps": 0}, {"steps": 1.5}, {"rank": 7}, {"size": 999}, {"learning_rate": 5}])
def test_bad_settings_are_refused(env, change):
    fake, c, tmp = env
    r = c.post("/api/train/jobs", json={**GOOD, "dataset": dataset(c), **change})
    assert r.status_code == 400 and fake.posted == []


# ---------- datasets ----------

def test_upload_keeps_pictures_and_rejects_the_rest(env):
    fake, c, tmp = env
    ds = c.post("/api/train/datasets", json={"name": "x"}).json()["id"]
    r = c.post(f"/api/train/datasets/{ds}/upload", files=[("files", ("../../evil.png", png(), "image/png")), ("files", ("fake.png", b"not a picture", "image/png")), ("files", ("a.gif", b"GIF89a", "image/gif")), ("files", ("orphan.txt", b"hello", "text/plain"))]).json()
    assert [i["file"] for i in r["items"]] == ["evil.png"]
    assert len(r["skipped"]) == 3
    assert (tmp / "data" / "datasets" / ds / "images" / "evil.png").exists()
    assert not (tmp / "data" / "evil.png").exists()


def test_caption_fixes(env):
    fake, c, tmp = env
    ds = dataset(c, captions=False)
    r = c.get(f"/api/train/datasets/{ds}").json()
    assert not r["ready"] and r["blocks"] == 3
    r = c.post(f"/api/train/datasets/{ds}/fix", json={"action": "fill_empty", "text": "a lighthouse"}).json()
    assert r["ready"] and r["items"][0]["caption"] == "a lighthouse"
    r = c.post(f"/api/train/datasets/{ds}/fix", json={"action": "add_trigger", "trigger": "brasslight"}).json()
    assert r["items"][0]["caption"] == "brasslight, a lighthouse"
    r = c.post(f"/api/train/datasets/{ds}/fix", json={"action": "add_trigger", "trigger": "brasslight"}).json()
    assert r["items"][0]["caption"] == "brasslight, a lighthouse"     # not twice
    r = c.post(f"/api/train/datasets/{ds}/fix", json={"action": "remove", "file": "pic0.png"}).json()
    assert [i["file"] for i in r["items"]] == ["pic1.png", "pic2.png"]


def test_check_warns_about_small_flat_duplicate_and_trigger(env):
    fake, c, tmp = env
    ds = c.post("/api/train/datasets", json={"name": "x"}).json()["id"]
    flat = png((10, 10, 10), noise=False)
    c.post(f"/api/train/datasets/{ds}/upload", files=[("files", ("a.png", flat, "image/png")), ("files", ("b.png", flat, "image/png")), ("files", ("a.txt", b"one", "text/plain")), ("files", ("b.txt", b"two", "text/plain"))])
    r = c.get(f"/api/train/datasets/{ds}?trigger=brasslight&size=1024").json()
    codes = {p["code"] for i in r["items"] for p in i["problems"]}
    assert codes == {"flat", "duplicate", "small", "no_trigger"} and r["ready"]
    assert {p["code"] for p in r["problems"]} == {"few"}


def test_too_few_pictures_blocks(env):
    fake, c, tmp = env
    assert not c.get(f"/api/train/datasets/{dataset(c, n=1)}").json()["ready"]


def test_folder_import_limits(env, monkeypatch):
    fake, c, tmp = env
    monkeypatch.setenv("STUDIO_TRAIN_IMPORT_ROOTS", str(tmp / "ok"))
    monkeypatch.setenv("HOME", str(tmp / "home"))
    (tmp / "ok" / ".hidden").mkdir(parents=True); (tmp / "ok" / "pics").mkdir(); (tmp / "elsewhere").mkdir()
    (tmp / "ok" / "pics" / "a.png").write_bytes(png()); (tmp / "ok" / "pics" / "a.txt").write_text("cap"); (tmp / "ok" / "pics" / "secret.env").write_text("X=1")
    (tmp / "ok" / ".hidden" / "a.png").write_bytes(png()); (tmp / "elsewhere" / "a.png").write_bytes(png())
    ds = c.post("/api/train/datasets", json={"name": "x"}).json()["id"]
    assert c.post(f"/api/train/datasets/{ds}/import", json={"folder": str(tmp / "elsewhere")}).status_code == 403
    assert c.post(f"/api/train/datasets/{ds}/import", json={"folder": str(tmp / "ok" / ".hidden")}).status_code == 403
    assert c.post(f"/api/train/datasets/{ds}/import", json={"folder": "relative"}).status_code == 400
    r = c.post(f"/api/train/datasets/{ds}/import", json={"folder": str(tmp / "ok" / "pics")}).json()
    assert [(i["file"], i["caption"]) for i in r["items"]] == [("a.png", "cap")]


def test_a_bad_id_or_file_name_never_reaches_a_path(env):
    fake, c, tmp = env
    assert c.get("/api/train/datasets/..%2f..").status_code == 404
    assert c.get("/api/train/jobs/notanid").status_code == 404
    ds = dataset(c)
    assert c.get(f"/api/train/datasets/{ds}/thumb/..%2f..%2fdataset.json").status_code == 404


# ---------- a whole run ----------

def log_line(step, total, loss, t="2099-01-01T00:00:{:02d}"):
    return {"t": t.format(step), "m": f"\rTraining LoRA:  {step * 100 // total}%|##   | {step}/{total} [00:0{step}<00:01,  2.00it/s, loss={loss}]"}


def started(env, **over):
    fake, c, tmp = env
    r = c.post("/api/train/jobs", json={**GOOD, "dataset": dataset(c), **over})
    assert r.status_code == 200, r.text
    return r.json()


def finish_ok(fake, tmp, job, pid="p1", losses=(0.5, 0.4, 0.3, 0.2), steps=4):
    out = tmp / "output" / "parametric_train" / job["id"]
    st_file(out / f"lora_{steps}_steps_00001_.safetensors", {"diffusion_model.a.lora_up.weight": "BF16", "diffusion_model.a.lora_down.weight": "BF16"})
    fake.queue["queue_running"] = []
    fake.history[pid] = {"status": {"status_str": "success", "completed": True, "messages": []}, "outputs": {"6": {"text": [json.dumps({"loss": list(losses)}, indent=4)]}}}


def test_start_prepares_a_square_copy_and_queues_the_validated_graph(env):
    fake, c, tmp = env
    job = started(env)
    assert job["state"] == "queued" and job["rights"]["confirmed"] is True
    g = fake.posted[0]
    folder = g["2"]["inputs"]["folder"]
    prepared = sorted(p.name for p in (tmp / "input" / folder).iterdir())
    assert prepared == ["00001.png", "00001.txt", "00002.png", "00002.txt", "00003.png", "00003.txt"]
    assert Image.open(tmp / "input" / folder / "00001.png").size == (1024, 1024)
    assert (tmp / "input" / folder / "00001.txt").read_text() == "brasslight, a lighthouse number 0"
    assert g["4"]["inputs"]["steps"] == 4 and g["5"]["inputs"]["prefix"] == f"parametric_train/{job['id']}/lora"


def test_a_second_job_waits_its_turn(env):
    fake, c, tmp = env
    started(env)
    r = c.post("/api/train/jobs", json={**GOOD, "dataset": dataset(c)})
    assert r.status_code == 409 and len(fake.posted) == 1


def test_a_rejected_graph_is_reported_and_cleaned_up(env):
    fake, c, tmp = env
    import urllib.error
    fake.reject = urllib.error.HTTPError("u", 400, "bad", {}, io.BytesIO(json.dumps({"error": {"message": "Prompt has no outputs"}, "node_errors": {}}).encode()))
    r = c.post("/api/train/jobs", json={**GOOD, "dataset": dataset(c)})
    assert r.status_code == 400 and "Prompt has no outputs" in r.json()["detail"]
    assert list((tmp / "input").glob("parametric_train/*")) == [] and c.get("/api/train/jobs").json()["jobs"] == []


def test_queue_position_then_live_curve_from_the_log_only(env):
    fake, c, tmp = env
    job = started(env)
    fake.queue["queue_pending"].insert(0, [0, "someone-else"])
    fake.queue["queue_running"] = [[0, "other"]]
    train._tick(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["state"] == "queued" and v["position"] == 2 and v["step"] == 0 and v["eta_s"] is None and v["s_per_step"] is None and v["last_loss"] is None and v["curve"] == []
    fake.queue["queue_pending"] = []
    fake.run("p1")
    fake.logs = [log_line(9, 100, 0.9)]        # another job's line: its total is not ours
    train._tick(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["state"] == "running" and v["curve"] == [] and v["eta_s"] is None and v["peak_vram_gib"] == 12.5
    fake.logs = [log_line(1, 4, 0.5), {"t": "2099-01-01T00:00:01", "m": "other text"}, log_line(2, 4, 0.25)]
    train._tick(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["curve"] == [[1, 0.5], [2, 0.25]] and v["step"] == 2 and v["last_loss"] == 0.25
    assert v["s_per_step"] == 1.0 and v["eta_s"] == 2 and v["curve_source"] == "live log"


def test_old_log_lines_are_ignored(env):
    fake, c, tmp = env
    job = started(env)
    fake.run("p1")
    fake.logs = [log_line(3, 4, 0.1, t="2000-01-01T00:00:{:02d}")]
    train._tick(job["id"])
    assert c.get(f"/api/train/jobs/{job['id']}").json()["curve"] == []


def test_finish_uses_the_nodes_loss_record_and_files_the_lora(env):
    fake, c, tmp = env
    job = started(env)
    fake.run("p1")
    fake.logs = [log_line(1, 4, 0.5), log_line(3, 4, 0.3)]
    train._tick(job["id"])
    finish_ok(fake, tmp, job)
    train._tick(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["state"] == "done" and v["curve_source"] == "loss_map" and v["curve"] == [[1, 0.5], [2, 0.4], [3, 0.3], [4, 0.2]] and v["curve_points"] == 4
    assert v["last_loss"] == 0.2 and v["s_per_step"] == 1.0
    lo = v["lora"]
    assert lo["name"].startswith("parametric_trained/brass-light_sdxl_4_steps_") and lo["total_steps"] == 4 and len(lo["sha256"]) == 64
    assert Path(lo["path"]).is_file() and Path(lo["path"]).parent == tmp / "models" / "loras" / "parametric_trained"
    assert not (tmp / "input" / "parametric_train" / job["id"]).exists()
    rows = c.get("/api/train/loras").json()["loras"]
    assert [r["job"] for r in rows] == [job["id"]]
    os.unlink(lo["path"])
    assert c.get("/api/train/loras").json()["loras"] == []          # no listing for a file that is gone


def test_a_finished_run_without_the_file_is_a_failure_not_a_path(env):
    fake, c, tmp = env
    job = started(env)
    fake.history["p1"] = {"status": {"status_str": "success", "completed": True, "messages": []}, "outputs": {"6": {"text": [json.dumps({"loss": [0.5]})]}}}
    train._tick(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["state"] == "error" and "SaveLoRA" in v["error"] and v["lora"] is None and c.get("/api/train/loras").json()["loras"] == []


def test_a_finished_run_with_no_loss_at_all_fails(env):
    fake, c, tmp = env
    job = started(env)
    out = tmp / "output" / "parametric_train" / job["id"]
    st_file(out / "lora_4_steps_00001_.safetensors", {"a.lora_up.weight": "BF16"})
    fake.history["p1"] = {"status": {"status_str": "success", "completed": True, "messages": []}, "outputs": {}}
    train._tick(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["state"] == "error" and "loss" in v["error"] and v["curve"] == []


def test_comfy_error_is_shown(env):
    fake, c, tmp = env
    job = started(env)
    fake.history["p1"] = {"status": {"status_str": "error", "messages": [["execution_error", {"exception_message": "CUDA out of memory"}]]}, "outputs": {}}
    train._tick(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["state"] == "error" and "out of memory" in v["error"]


def test_cancel_while_running_interrupts_only_this_job(env):
    fake, c, tmp = env
    job = started(env)
    fake.run("p1")
    train._tick(job["id"])
    assert c.post(f"/api/train/jobs/{job['id']}/cancel").json()["state"] == "cancelling"
    assert fake.interrupted == ["p1"]
    train._tick(job["id"])
    assert train._load_job(job["id"])["state"] == "cancelling"       # still running in ComfyUI, and a look must not undo the cancel
    fake.queue["queue_running"] = []
    fake.history["p1"] = {"status": {"status_str": "error", "messages": [["execution_interrupted", {}]]}, "outputs": {}}
    train._tick(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["state"] == "cancelled" and v["lora"] is None and v["error"] is None
    assert not (tmp / "input" / "parametric_train" / job["id"]).exists()


def test_cancel_while_queued_deletes_it_and_interrupts_nothing(env):
    fake, c, tmp = env
    job = started(env)
    c.post(f"/api/train/jobs/{job['id']}/cancel")
    assert fake.deleted == ["p1"] and fake.interrupted == []
    train._tick(job["id"])
    assert train._load_job(job["id"])["state"] == "cancelled"


def test_a_vanished_job_is_lost_not_finished(env, monkeypatch):
    fake, c, tmp = env
    job = started(env)
    fake.queue["queue_pending"] = []
    monkeypatch.setattr(train, "VANISHED_S", -1)
    train._tick(job["id"])
    v = train._load_job(job["id"])
    assert v["state"] == "lost" and "restarted" in v["error"]


def test_unreachable_comfy_changes_nothing_else(env, monkeypatch):
    fake, c, tmp = env
    job = started(env)
    monkeypatch.setattr(train, "_comfy", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    train._tick(job["id"])
    v = train._load_job(job["id"])
    assert v["state"] == "queued" and v["unreachable"] is True


def test_nan_loss_is_flagged_and_never_drawn_as_a_number(env):
    fake, c, tmp = env
    job = started(env)
    fake.run("p1")
    fake.logs = [log_line(1, 4, 0.5), log_line(2, 4, "nan")]
    train._tick(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["loss_nan"] is True and v["curve"] == [[1, 0.5], [2, None]] and v["last_loss"] == 0.5


def test_big_curves_are_thinned_with_real_points_only():
    curve = [[i + 1, i * 0.001, None] for i in range(5000)]
    t = train._thin(curve)
    assert len(t) == train.MAX_CURVE_POINTS and t[-1] == curve[-1] and all(p in curve for p in t[:5])


def test_continue_uses_the_nodes_existing_lora(env):
    fake, c, tmp = env
    job = started(env)
    finish_ok(fake, tmp, job)
    train._tick(job["id"])
    name = train._load_job(job["id"])["lora"]["name"]
    fake.info["TrainLoraNode"]["input"]["required"]["existing_lora"][1]["options"] = ["[None]", name]
    r = c.post("/api/train/jobs", json={**GOOD, "dataset": dataset(c), "continue_from": job["id"], "steps": 2})
    assert r.status_code == 200, r.text
    assert fake.posted[1]["4"]["inputs"]["existing_lora"] == name and r.json()["prior_steps"] == 4


def test_ab_measures_the_two_real_pictures(env):
    fake, c, tmp = env
    job = started(env)
    finish_ok(fake, tmp, job)
    train._tick(job["id"])
    name = train._load_job(job["id"])["lora"]["name"]
    fake.info["LoraLoaderModelOnly"]["input"]["required"]["lora_name"][0] = [name]
    assert c.post(f"/api/train/jobs/{job['id']}/ab", json={"prompt": "a nude figure"}).status_code == 400
    v = c.post(f"/api/train/jobs/{job['id']}/ab", json={"prompt": "brasslight on a cliff", "seed": 7}).json()
    assert v["ab"]["state"] == "queued" and v["ab"]["base"] is None and v["ab"]["pixel_diff"] is None
    pid = v["ab"]["prompt_id"]
    train._tick_ab(job["id"])
    a, b = png((10, 10, 10), noise=False), png((20, 10, 10), noise=False)
    fake.view = {"a.png": a, "b.png": b}
    fake.logs = [{"t": "2099-01-01T00:00:00", "m": "lora key not loaded: x"}]
    fake.history[pid] = {"status": {"status_str": "success", "completed": True, "messages": []}, "outputs": {"10": {"images": [{"filename": "a.png", "subfolder": "", "type": "output"}]}, "11": {"images": [{"filename": "b.png", "subfolder": "", "type": "output"}]}}}
    train._tick_ab(job["id"])
    v = c.get(f"/api/train/jobs/{job['id']}").json()
    assert v["ab"]["state"] == "done" and v["ab"]["pixel_diff"] == round(10 / 3, 3) and v["ab"]["unbound_keys"] == 1 and "graph" not in v["ab"]
    assert "a.png" in v["ab"]["base"]["url"] and "b.png" in v["ab"]["lora"]["url"]


def test_ab_needs_a_finished_lora(env):
    fake, c, tmp = env
    job = started(env)
    assert c.post(f"/api/train/jobs/{job['id']}/ab", json={"prompt": "x"}).status_code == 400


def test_a_finished_run_becomes_a_measurement_the_page_can_quote(env, monkeypatch):
    fake, c, tmp = env
    job = started(env)
    fake.run("p1")
    fake.logs = [log_line(1, 4, 0.5), log_line(3, 4, 0.3)]
    train._tick(job["id"])
    finish_ok(fake, tmp, job)
    train._tick(job["id"])
    row = json.loads((tmp / "data" / "measured.jsonl").read_text().splitlines()[0])
    assert row["s_per_step"] == 1.0 and row["peak_vram_gib"] == 12.5 and row["run"] == job["id"] and row["steps"] == 4


def test_parse_ignores_lines_that_are_not_training():
    assert train.parse_progress([{"t": "2099", "m": "\r 18%|##  | 7/40 [01:24<06:06, 11.11s/it]"}, {"t": "2099-01-01T00:00:00", "m": "\rTraining LoRA:   0%|  | 0/4 [00:00<?, ?it/s]"}], "2000") == []


def test_page_says_what_is_checked_and_is_registered():
    root = Path(__file__).resolve().parents[2] / "studio"
    page = (root / "web" / "train.js").read_text()
    assert "Not checked: the pictures themselves" in page and "not a safety guarantee" in page and "no real person's likeness" in page
    app = (root / "web" / "app.js").read_text()
    assert '["train", "Train"]' in app and "TITLES" in app and 't === "train"' in app
    assert '"train"' in (root / "server.py").read_text() and "train.css" in (root / "web" / "index.html").read_text()
    for name in ("train.js", "train_logic.js", "train.css"):
        assert "http://" not in (root / "web" / name).read_text() and "https://" not in (root / "web" / name).read_text()
    assert "PSN_LoRA_Train_HunYuan" not in (root / "train.py").read_text()


def test_the_look_keeps_its_notes_and_stays_local():
    web = Path(__file__).resolve().parents[2] / "studio" / "web"
    page, stage = (web / "train.js").read_text(), (web / "train_stage.js").read_text()
    assert "It does not look at what a picture shows" in page
    assert "A flat line does not mean it failed" in stage and "makes no sample pictures" in stage and "Our own run, not yours" in stage and "overfits" in stage
    for name in ("train_stage.js", "train_example.js"):
        text = (web / name).read_text()
        assert "http://" not in text and "https://" not in text and "—" not in text
    for name in ("lighthouse_base", "lighthouse_lora", "harbour_base", "harbour_lora"):
        assert f"train_art/{name}.webp" in (web / "train_example.js").read_text() and (web / "train_art" / f"{name}.webp").stat().st_size < 150_000
