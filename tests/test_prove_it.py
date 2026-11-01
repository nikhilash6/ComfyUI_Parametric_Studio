"""Prove It: measured comparisons, honest refusals, and a run that only starts from a click. No live ports: ComfyUI and the recipe runner are stubbed."""
import gzip, json, re
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from studio import feature_prove as P

WEB = Path(P.__file__).parent / "web"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(P.paths, "models_root", lambda *_: str(tmp_path / "models"))
    (tmp_path / "models").mkdir()
    app = FastAPI(); app.include_router(P.router); return TestClient(app)


def test_the_data_file_holds_real_records_and_no_folders():
    raw = gzip.open(P.DATA, "rt", encoding="utf-8").read(); d = json.loads(raw)
    assert not re.search(r"/home/|/mnt/|/Users/", raw)
    assert len(d["renders"]) > 500 and d["hardware"]["gpu"] and all(m is None or len(m["sha256"]) == 64 for m in d["models"].values())
    kept = [r for r in d["renders"].values() if r["graphs_kept"]]
    assert kept and all(any(s["graph"] for s in r["steps"]) for r in kept if r["kind"] == "picture")


def test_identical_pixels_compare_as_zero():
    a = Image.new("RGB", (32, 32), (10, 20, 30)); c, heat = P.compare_images(a, a.copy())
    assert c == {"mean_diff": 0.0, "pct_off": 0.0, "off_by": P.OFF_BY, "resized": False} and heat.size == (32, 32)


def test_a_different_size_is_scaled_and_said():
    c, _ = P.compare_images(Image.new("RGB", (32, 32)), Image.new("RGB", (64, 64)))
    assert c["resized"] and c["mean_diff"] == 0


def test_pct_off_counts_pixels_past_the_threshold():
    a, b = Image.new("RGB", (10, 10), (0, 0, 0)), Image.new("RGB", (10, 10), (0, 0, 0))
    for x in range(10): b.putpixel((x, 0), (200, 200, 200))
    c, _ = P.compare_images(a, b)
    assert c["pct_off"] == 10.0 and c["mean_diff"] == 20.0


@pytest.mark.parametrize("identical,mean,floor,word", [(True, 0, 0.4, "Identical"), (False, 0.4, 0.4, "Indistinguishable here"), (False, 2.0, 0.4, "Close, not the same"), (False, 30, 0.4, "Different"), (False, None, None, "Not compared"), (False, 15, 18.0, "Too coarse to tell"), (False, 60, 18.0, "Different")])
def test_verdict_words(identical, mean, floor, word):
    assert P.verdict(identical, mean, floor)["word"] == word


def test_only_a_hash_match_says_identical():
    assert "not proof" in P.verdict(False, 0.1, 0.4)["text"]


def test_nothing_starts_without_the_click(client, monkeypatch):
    from studio import recipes as R
    monkeypatch.setattr(R, "recipe_run", lambda *a, **k: pytest.fail("ran without a click"))
    rid = next(iter(R.renders()))
    assert client.post(f"/api/prove/recipe/{rid}/start", json={}).status_code == 400
    assert client.post(f"/api/prove/recipe/{rid}/start", json={"confirm": "yes"}).status_code == 400


def test_a_showcase_render_with_no_seed_is_refused_plainly(client):
    rows = json.loads(P.SHOWCASE.read_text()); d = client.get("/api/prove/showcase/" + rows[0]["id"]).json()
    assert d["provable"] is False and "seed" in d["why"] and d["seeds"] is None


def test_a_render_from_a_file_we_do_not_ship_is_refused():
    ok, why = P.provable("x", {"seeds": {"a": 1}, "uploads": True})
    assert not ok and "do not ship" in why


def test_no_record_and_no_seed_are_refused():
    assert not P.provable("x", None)[0] and not P.provable("x", {"seeds": {}, "steps": []})[0]


def test_start_runs_the_recorded_values_and_seed_offset(client, monkeypatch):
    from studio import recipes as R, backends
    rid = next(k for k, r in P.data()["renders"].items() if P.provable(k, r)[0] and r.get("values") is not None)
    seen = {}
    monkeypatch.setattr(backends, "use_sdk", lambda: False)
    monkeypatch.setattr(R, "recipe_run", lambda i, b: seen.update(i=i, b=b) or {"run": "a" * 12})
    d = client.post(f"/api/prove/recipe/{rid}/start", json={"confirm": True}).json()
    assert seen["i"] == rid and seen["b"].values == P.data()["renders"][rid]["values"] and seen["b"].seed_add == 0 and d["state"] == "running"


def test_cloud_mode_is_refused(client, monkeypatch):
    from studio import recipes as R, backends
    monkeypatch.setattr(backends, "use_sdk", lambda: True)
    assert client.post(f"/api/prove/recipe/{next(iter(R.renders()))}/start", json={"confirm": True}).status_code == 400


def test_graph_diff_lists_each_input_and_explains_a_handed_on_file():
    a = {"1": {"class_type": "KSampler", "inputs": {"seed": 1, "image": "studio_aaaaaaaaaa.png"}}}; b = {"1": {"class_type": "KSampler", "inputs": {"seed": 2, "image": "studio_bbbbbbbbbb.png"}}, "2": {"class_type": "X", "inputs": {}}}
    rows = P.diff_graphs(a, b)
    assert {r["input"] for r in rows} == {"seed", "image", "(whole node)"} and next(r for r in rows if r["input"] == "image")["note"]
    assert P.diff_graphs(a, a) == []


def test_model_row_says_missing_and_same_and_different(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_STATE_DIR", str(tmp_path / "s")); root = tmp_path / "m"; root.mkdir(); (root / "a.safetensors").write_bytes(b"abc")
    assert P.model_row("nope.safetensors", {"sha256": "x"}, root=str(root))["state"] == "missing"
    st = (root / "a.safetensors").stat(); key = f"a.safetensors:{st.st_size}:{int(st.st_mtime)}"
    P._hash_cache_path().parent.mkdir(parents=True); P._hash_cache_path().write_text(json.dumps({key: "x"}))
    assert P.model_row("a.safetensors", {"sha256": "x"}, root=str(root))["state"] == "same"
    assert P.model_row("a.safetensors", {"sha256": "y"}, root=str(root))["state"] == "different"


def test_hardware_rows_never_guess():
    rows = P.hardware_rows({"gpu": "A", "driver": "1"}, {"gpu": "A", "driver": None})
    assert rows[0]["same"] is True and next(r for r in rows if r["what"] == "GPU driver")["same"] is None


def test_hardware_with_comfy_away_stays_null(monkeypatch):
    monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:9")
    h = P.your_hardware(); assert h["comfy_up"] is False and h["gpu"] is None


def test_a_full_comparison_writes_the_three_images(tmp_path):
    a = tmp_path / "a.png"; b = tmp_path / "b.png"; Image.new("RGB", (16, 16), (9, 9, 9)).save(a); Image.new("RGB", (16, 16), (9, 9, 9)).save(b)
    im = Image.open(b).convert("RGB"); r = P.compare_files("image", a, b, {"pixels_sha256": P.pixels_sha(im), "noise_floor": 0.2}, tmp_path / "o")
    assert r["verdict"]["word"] == "Identical" and all((tmp_path / "o" / f"{n}_0.png").is_file() for n in ("ours", "yours", "diff"))


ffmpeg = pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="needs ffmpeg")


@ffmpeg
def test_a_video_compares_three_frames(tmp_path):
    import subprocess
    a = tmp_path / "a.mp4"; subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=d=1:s=64x64:r=10", "-pix_fmt", "yuv420p", str(a)], check=True)
    r = P.compare_files("video", a, a, {"noise_floor": 0.5}, tmp_path / "o")
    assert len(r["frames"]) == 3 and r["figures"]["mean_diff"] == 0 and r["verdict"]["word"] == "Indistinguishable here"     # never called identical without a hash


@ffmpeg
def test_audio_compares_by_samples(tmp_path):
    import hashlib, subprocess
    a = tmp_path / "a.wav"; subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", str(a)], check=True)
    r = P.compare_files("audio", a, a, {"pcm_sha256": hashlib.sha256(P._pcm(a)).hexdigest()}, tmp_path / "o")
    assert r["figures"]["identical"] and r["verdict"]["word"] == "Identical" and r["frames"] == []
    r = P.compare_files("audio", a, a, {}, tmp_path / "o")
    assert not r["figures"]["identical"] and r["verdict"]["word"] == "Not the same"


def test_the_same_machine_record_is_small_and_says_so():
    assert "too few to promise" in P.same_machine()


@pytest.mark.parametrize("bad", ["../x", "abc", "ZZZZZZZZZZZZ"])
def test_proof_ids_are_checked(client, bad):
    assert client.get(f"/api/prove/runs/{bad}").status_code == 404


def test_page_hooks():
    assert "#prove/recipe/" in (WEB / "recipes.js").read_text()
    app = (WEB / "app.js").read_text()
    assert "#prove/showcase/" in app and "seed: 11" not in app       # a seed we never recorded must not be shown
    js = (WEB / "prove.js").read_text() + (WEB / "prove_wipe.js").read_text()
    assert 'type="range"' in js and "—" not in js and "measured" in js and not re.search(r"https?://", js)
