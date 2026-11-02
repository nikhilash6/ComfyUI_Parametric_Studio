"""Train's bases and external trainers, with no live port and no GPU. ComfyUI is the stand-in from test_train; the trainer is a small script started as a real process."""
import json, os, signal, sys, time
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio import train, train_bases, trainers
from studio.trainers import aitoolkit
from studio.trainers.base import trainer_paths, proc_start_ticks
from test_train import env, dataset, st_file, GOOD, FIXTURE  # noqa: F401  (env is a fixture)


FAKE_TRAINER = r'''
import sys, time, pathlib, yaml, signal
cfg = yaml.safe_load(open(sys.argv[1]))["config"]
p = cfg["process"][0]; name = cfg["name"]; out = pathlib.Path(p["training_folder"]) / name; (out / "samples").mkdir(parents=True, exist_ok=True)
from PIL import Image
steps = p["train"]["steps"]
start = 0
old = sorted(out.glob(name + "_*.safetensors"))
if old: start = int(old[-1].stem.rsplit("_", 1)[1]); print("#### IMPORTANT RESUMING FROM", old[-1], flush=True)
head = b'{"diffusion_model.a.lora_A.weight":{"dtype":"BF16","shape":[0],"data_offsets":[0,0]},"diffusion_model.a.lora_B.weight":{"dtype":"BF16","shape":[0],"data_offsets":[0,0]}}'
import struct
def save(path): open(path, "wb").write(struct.pack("<Q", len(head)) + head)
Image.new("RGB", (16, 16), (10, 10, 10)).save(out / "samples" / "1__000000000_0.jpg")
for s in range(start + 1, steps + 1):
    print(f"\r{name}: {s*100//steps}%| | {s}/{steps} [00:01<00:01, 0.10s/it, lr: 1.0e-04 loss: {1.0/s:.3e}]", end="", flush=True)
    time.sleep(float(p.get("sleep", 0.02)))
    if s == 2: save(out / f"{name}_000000002.safetensors")
    if len(sys.argv) > 2 and s == 3: time.sleep(30)
Image.new("RGB", (16, 16), (240, 240, 240)).save(out / "samples" / f"2__{steps:09d}_0.jpg")
save(out / f"{name}.safetensors")
print("\nDone", flush=True)
'''

BASE = {"label": "Test FLUX", "family": "Test", "file": "pipe", "arch": "Test", "load": {}, "sample": {}, "licence": {"name": "Apache-2.0", "url": "u", "note": "n"}, "peak_gib": 10, "media": "image", "sizes": [512], "lr": 1e-4, "trainer": "ai-toolkit", "needs": (), "repo": None, "ab_from_samples": True, "aitk": {"template": "flux_dev.yaml", "arch": "flux", "files": {"pipeline": ("diffusers", "pipe")}}}


@pytest.fixture
def ext(env, tmp_path, monkeypatch):
    fake, c, tmp = env
    t = tmp_path / "toolkit"; (t / "jobs").mkdir(parents=True); (t / "run.py").write_text(FAKE_TRAINER)
    (tmp / "models" / "diffusers" / "pipe").mkdir(parents=True)
    monkeypatch.setenv("STUDIO_TRAINER_AI_TOOLKIT_DIR", str(t)); monkeypatch.setenv("STUDIO_TRAINER_AI_TOOLKIT_PYTHON", sys.executable)
    monkeypatch.delenv("STUDIO_TRAIN_WRAP", raising=False)
    monkeypatch.setitem(train.BASES, "test-ext", BASE)
    return fake, c, tmp


def go(c, **over):
    return c.post("/api/train/jobs", json={**GOOD, "base": "test-ext", "size": 512, "steps": 4, "dataset": dataset(c), "first_run": True, **over})


def until_done(job_id, limit=20):
    t0 = time.time()
    while time.time() - t0 < limit:
        j = train._tick(job_id)
        if j["state"] not in train.ACTIVE: return j
        time.sleep(0.05)
    raise AssertionError("the stand-in trainer did not finish")


# ---------- the registry ----------

@pytest.mark.parametrize("base_id", list(train_bases.BASES))
def test_every_base_says_who_trains_it_and_its_licence(base_id):
    b = train_bases.BASES[base_id]
    assert b["trainer"] in train_bases.TRAINERS and b["licence"]["name"] and b["sizes"] and b["peak_gib"] > 0 and b["file"]
    assert b["load"] or b["trainer"] != "comfy"


def test_no_box_paths_in_configs():
    d = Path(train.__file__).parent / "train_configs"
    for f in d.rglob("*.yaml"):
        text = f.read_text()
        assert "/home/" not in text and "/mnt/" not in text, f


@pytest.mark.parametrize("name", ["flux_dev.yaml", "ltx25.yaml", "h3.yaml", "qwen2.yaml", "hidream_o1.yaml"])
def test_templates_become_valid_yaml(name, tmp_path):
    import yaml
    b = {"aitk": {"template": name, "arch": "x", "files": {}}}
    s = {"steps": 100, "rank": 8, "batch": 1, "learning_rate": 1e-4, "size": 512, "seed": 1}
    text = aitoolkit.AiToolkit()._render(None, b, s, {"pipeline": "/p", "dit": "/d", "te": "/t", "vae": "/v", "audio_vae": "/a", "adapter": "/x"}, "/run", "qz", "a prompt")
    assert "{{" not in text
    cfg = yaml.safe_load(text)["config"]["process"][0]
    assert cfg["train"]["steps"] == 100 and cfg["network"]["linear"] == 8 and cfg["save"]["save_every"] == 25


# ---------- the graphs ----------

def _info_with(names):
    info = json.loads(json.dumps(FIXTURE))
    info["UNETLoader"] = {"input": {"required": {"unet_name": [names.get("unet", [])], "weight_dtype": [["default", "fp8_e4m3fn"]]}}, "output": ["MODEL"]}
    info["CLIPLoader"] = {"input": {"required": {"clip_name": [names.get("clip", [])], "type": [["flux2", "lumina2"]], "device": [["default"]]}}, "output": ["CLIP"]}
    info["VAELoader"] = {"input": {"required": {"vae_name": [names.get("vae", [])]}}, "output": ["VAE"]}
    return info


def test_split_files_wire_a_unet_a_clip_and_a_vae():
    load = train_bases.BASES["flux2-klein-base-4b"]["load"]
    g = train.training_graph(load, "f", 10, 8, 1, 1e-4, 1, "p")
    assert g["1"]["class_type"] == "UNETLoader" and g["21"]["class_type"] == "CLIPLoader" and g["22"]["class_type"] == "VAELoader"
    assert g["3"]["inputs"]["clip"] == ["21", 0] and g["3"]["inputs"]["vae"] == ["22", 0] and g["4"]["inputs"]["model"] == ["1", 0]
    info = _info_with({"unet": [load["unet"]], "clip": load["clip"], "vae": [load["vae"]]})
    assert [p for p in train.validate_graph(g, info) if "folder" not in p] == []


def test_a_checkpoint_keeps_its_old_graph():
    g = train.training_graph("sd_xl_base_1.0.safetensors", "f", 10, 8, 1, 1e-4, 1, "p")
    assert g["3"]["inputs"]["clip"] == ["1", 1] and "21" not in g


def test_ab_uses_the_bases_own_sampler_and_shift():
    b = train_bases.BASES["z-image"]
    g = train.ab_graph(b["load"], "x.safetensors", "p", "", 512, 512, 1, 1.0, "ab", sample=b["sample"])
    assert g["23"]["class_type"] == "ModelSamplingAuraFlow" and g["23"]["inputs"]["shift"] == 3.0
    assert g["6"]["inputs"]["model"] == ["23", 0] and g["2"]["inputs"]["model"] == ["23", 0] and g["6"]["inputs"]["sampler_name"] == "res_multistep"
    assert g["5"]["class_type"] == "EmptySD3LatentImage" and g["6"]["inputs"]["seed"] == g["7"]["inputs"]["seed"]


def test_a_video_base_samples_one_frame_through_its_vae():
    b = train_bases.BASES["wan2.2-5b"]
    g = train.ab_graph(b["load"], "x.safetensors", "p", "", 512, 512, 1, 1.0, "ab", sample=b["sample"])
    assert g["5"]["inputs"]["vae"] == ["22", 0] and g["5"]["inputs"]["length"] == 1


def test_a_file_in_a_sub_folder_is_found_by_name():
    load, missing = train.resolve_load({"unet": "a.safetensors", "clip": ["c.safetensors"], "clip_type": "x", "vae": "v.safetensors"}, _info_with({"unet": ["sub/a.safetensors"], "clip": ["c.safetensors"], "vae": ["deep/er/v.safetensors"]}))
    assert not missing and load["unet"] == "sub/a.safetensors" and load["vae"] == "deep/er/v.safetensors"


def test_each_missing_file_is_named():
    _, missing = train.resolve_load({"unet": "a.safetensors", "clip": ["c.safetensors"], "clip_type": "x", "vae": "v.safetensors"}, _info_with({}))
    assert len(missing) == 3 and "Model a.safetensors" in missing[0] and "VAE v.safetensors" in missing[1] and "Text encoder c.safetensors" in missing[2]


# ---------- status ----------

def rows(c):
    return {r["id"]: r for r in c.get("/api/train/info").json()["bases"]}


def test_status_words(ext):
    fake, c, tmp = ext
    r = rows(c)
    assert r["sdxl-base-1.0"]["status"] == "proven"
    assert r["test-ext"]["status"] == "not_run" and r["test-ext"]["can_try"] and not r["test-ext"]["trainable"]
    k = r["flux2-klein-base-4b"]
    assert k["status"] == "blocked" and not k["can_try"] and any("flux-2-klein-base-4b.safetensors" in m for m in k["missing"])
    assert k["licence"]["name"] == "Apache-2.0" and k["trainer_label"]


def test_missing_trainer_says_how_to_install(env, monkeypatch):
    fake, c, tmp = env
    monkeypatch.delenv("STUDIO_TRAINER_AI_TOOLKIT_DIR", raising=False); monkeypatch.delenv("STUDIO_TRAINER_AI_TOOLKIT_PYTHON", raising=False)
    r = rows(c)["flux1-dev"]
    assert r["status"] == "blocked" and any("ai-toolkit checkout" in m for m in r["missing"]) and any("flux1-dev-pipeline" in m for m in r["missing"])
    assert r["install"] and any("git clone" in x for x in r["install"])


def test_a_not_run_base_needs_the_first_run_tick(ext):
    fake, c, tmp = ext
    r = go(c, first_run=False)
    assert r.status_code == 400 and "first-run" in r.text
    j = go(c).json()
    assert j["first_run"] is True and j["trainer"] == "ai-toolkit" and j["licence"]["name"] == "Apache-2.0"
    until_done(j["id"])


def test_a_base_known_to_fail_says_why(env):
    fake, c, tmp = env
    r = rows(c)["flux3-klein"]
    assert r["status"] == "blocked" and not r["can_try"] and "training node fails" in r["why_not"]


def test_a_missing_base_cannot_use_the_tick(env):
    fake, c, tmp = env
    r = c.post("/api/train/jobs", json={**GOOD, "base": "flux2-klein-base-4b", "size": 512, "dataset": dataset(c), "first_run": True})
    assert r.status_code == 400 and "not installed" in r.text


# ---------- a real process ----------

def test_parse_progress_reads_tqdm_redraws():
    text = "x\r name: 1%| | 10/100 [00:01<00:09, 1.0s/it, lr: 1.0e-04 loss: 3.210e-01]\r name: 2%| | 20/100 [00:02, lr: 1.0e-04 loss: nan]\n"
    p = aitoolkit.parse_progress(text)
    assert p[0] == [10, 100, 0.321] and p[1][0] == 20 and p[1][2] != p[1][2]


def test_a_run_through_the_process_files_a_lora_with_its_curve_and_samples(ext):
    fake, c, tmp = ext
    j = go(c).json()
    cfg = Path(j["run_dir"]) / "config.yaml"
    assert cfg.is_file() and (Path(j["run_dir"]) / "models_path" / "diffusers" / "pipe").is_symlink()
    done = until_done(j["id"])
    assert done["state"] == "done", done["error"]
    assert [p[0] for p in done["curve"]] == [1, 2, 3, 4] and done["curve_source"] == "trainer log"
    assert done["lora"]["name"].startswith("parametric_trained/") and os.path.isfile(done["lora"]["path"])
    assert [s["step"] for s in done["samples"]] == [0, 4]
    v = c.get(f"/api/train/jobs/{j['id']}").json()
    assert v["trainer_label"] == "ostris ai-toolkit" and v["base_label"] == "Test FLUX" and "proc" not in v
    assert c.get(v["samples"][0]["url"]).status_code == 200 and c.get(f"/api/train/jobs/{j['id']}/sample/nope.jpg").status_code == 404
    # A/B from the trainer's own samples, with a real difference
    a = c.post(f"/api/train/jobs/{j['id']}/ab", json={"prompt": "qz, a boat"}).json()["ab"]
    assert a["state"] == "done" and a["source"] == "trainer samples" and a["pixel_diff"] > 100 and a["base"]["step"] == 0 and a["lora"]["step"] == 4
    # it is measured, and the page lists it
    assert any(r["job"] == j["id"] and r["trainer"] == "ai-toolkit" for r in c.get("/api/train/loras").json()["loras"])


def test_a_failed_trainer_shows_its_last_words(ext):
    fake, c, tmp = ext
    (tmp / "toolkit" / "run.py").write_text("raise SystemExit('out of memory on the card')")
    j = go(c).json()
    done = until_done(j["id"])
    assert done["state"] == "error" and "out of memory" in done["error"]


def test_cancel_stops_this_process_and_resume_continues_from_its_save(ext, monkeypatch):
    fake, c, tmp = ext
    src = (tmp / "toolkit" / "run.py").read_text()
    (tmp / "toolkit" / "run.py").write_text(src.replace('len(sys.argv) > 2 and s == 3', 's == 3'))
    j = go(c).json()
    t0 = time.time()
    while time.time() - t0 < 20:
        cur = train._tick(j["id"])
        if cur.get("checkpoints") and cur["curve"] and cur["curve"][-1][0] >= 3: break
        time.sleep(0.05)
    assert cur["checkpoints"], cur
    pid = cur["proc"]["pid"]
    assert proc_start_ticks(pid)
    v = c.post(f"/api/train/jobs/{j['id']}/cancel").json()
    assert v["state"] == "cancelling"
    done = until_done(j["id"])
    assert done["state"] == "cancelled" and train.view_job(done)["can_resume"]
    # the plain copy finishes when resumed, from step 3 on
    (tmp / "toolkit" / "run.py").write_text(src)
    assert c.post(f"/api/train/jobs/{j['id']}/resume").status_code == 200
    done = until_done(j["id"])
    assert done["state"] == "done" and done["curve"][-1][0] == 4
    assert "RESUMING" in Path(done["proc"]["log"]).read_text()


def test_stop_never_signals_a_recycled_pid(ext, monkeypatch):
    sent = []
    monkeypatch.setattr(os, "killpg", lambda *a: sent.append(a))
    t = trainers.get("ai-toolkit")
    t.stop({"proc": {"pid": os.getpid(), "ticks": "not-the-real-start-time", "log": ""}})
    assert sent == []


def test_comfy_runs_do_not_claim_resume(env):
    fake, c, tmp = env
    r = c.post("/api/train/jobs", json={**GOOD, "dataset": dataset(c)}).json()
    assert c.post(f"/api/train/jobs/{r['id']}/resume").status_code == 400


def test_the_wrap_goes_in_front_of_the_command(ext, monkeypatch):
    fake, c, tmp = ext
    monkeypatch.setenv("STUDIO_TRAIN_WRAP", f"{sys.executable} {tmp}/wrap.py {{key}} {{peak}}")
    (tmp / "wrap.py").write_text("import sys,subprocess;open(sys.argv[0]+'.seen','w').write(' '.join(sys.argv[1:3]));sys.exit(subprocess.call(sys.argv[3:]))")
    done = until_done(go(c).json()["id"])
    assert done["state"] == "done" and (tmp / "wrap.py.seen").read_text() == "test-ext 10"


def test_an_install_folder_can_come_from_the_settings_file(env, monkeypatch, tmp_path):
    monkeypatch.delenv("STUDIO_TRAINER_AI_TOOLKIT_DIR", raising=False); monkeypatch.delenv("STUDIO_TRAINER_AI_TOOLKIT_PYTHON", raising=False)
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "trainers.json").write_text(json.dumps({"ai-toolkit": {"dir": "/x", "python": "/y"}}))
    assert trainer_paths("ai-toolkit") == {"dir": "/x", "python": "/y"}


# ---------- LoRA search and the showcase ----------

def test_lora_search_lists_what_train_made(ext, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from studio import loras
    fake, c, tmp = ext
    j = go(c, name="Linocut test", trigger="qzlino").json()
    until_done(j["id"])
    monkeypatch.setitem(loras._cache, "data", None)
    app = FastAPI(); app.include_router(loras.router); s = TestClient(app)
    d = s.get("/api/loras", params={"q": "linocut"}).json()
    hit = [i for i in d["items"] if i.get("trained") == j["id"]]
    assert hit and hit[0]["trigger"] == "qzlino" and hit[0]["family"] == "Test" and hit[0]["kind"] == "trained here"


def test_showcase_uses_the_runs_samples_and_licence(ext):
    from studio import feature_lorashow as show
    fake, c, tmp = ext
    j = go(c).json()
    until_done(j["id"])
    c.post(f"/api/train/jobs/{j['id']}/ab", json={"prompt": "qz, a boat"})
    card = show.card(j["id"])
    assert card["ab"]["state"] == "done" and card["facts"]["base_licence"]["name"] == "Apache-2.0" and card["facts"]["trainer"] == "ostris ai-toolkit"
    show._card_path(j["id"]).parent.mkdir(parents=True, exist_ok=True)
    show._card_path(j["id"]).write_text(json.dumps({"licence": "Apache-2.0"}))
    raw, name, notes = show.bundle_bytes(j["id"], False)
    assert len(raw) > 100 and not notes


# ---------- audio bases ----------

def _flac():
    return b"fLaC" + b"\0" * 64


def test_audio_clips_go_in_a_set_and_are_not_pictures(env):
    fake, c, tmp = env
    r = c.post("/api/train/datasets", json={"name": "Clips"}).json()
    up = c.post(f"/api/train/datasets/{r['id']}/upload", files=[("files", ("a.flac", _flac(), "audio/flac")), ("files", ("a.txt", b"qz, kalimba", "text/plain")), ("files", ("b.mp3", b"not audio", "audio/mpeg"))]).json()
    assert any("b.mp3" in x for x in up["skipped"])
    row = next(i for i in up["items"] if i["file"] == "a.flac")
    assert row["audio"] and row["caption"] == "qz, kalimba" and c.get(row["listen"]).content == _flac()
    pic = c.post("/api/train/jobs", json={**GOOD, "dataset": r["id"]})
    assert pic.status_code == 400 and "audio clips" in pic.text


def test_an_audio_base_refuses_pictures(ext, monkeypatch):
    fake, c, tmp = ext
    monkeypatch.setitem(train.BASES, "test-ext", {**BASE, "media": "audio"})
    r = go(c)
    assert r.status_code == 400 and "audio clips" in r.text


def test_simpletuner_parses_its_progress_and_says_what_is_missing(env, monkeypatch):
    from studio.trainers import simpletuner
    p = simpletuner.parse_progress("Epoch 1/1 Steps:  10%|#| 5/50 [00:05<00:45, 1.0it/s, lr=5e-05, step_loss=0.123]\r")
    assert p == [[5, 50, 0.123]]
    monkeypatch.delenv("STUDIO_TRAINER_SIMPLETUNER_PYTHON", raising=False)
    fake, c, tmp = env
    r = rows(c)["minimax-music3"]
    assert r["status"] == "blocked" and any("SimpleTuner installed" in m for m in r["missing"]) and any("MiniMax-Music3" in m for m in r["missing"])
    assert r["media"] == "audio" and any("git clone" in x for x in r["install"])
