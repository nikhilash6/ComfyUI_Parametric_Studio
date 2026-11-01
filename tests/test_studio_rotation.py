"""Model rotation. No network: the remote is a local folder, driven by the real rclone when it is installed and by a small stand-in when it is not. ComfyUI is stubbed."""
import hashlib, json, os, shutil, subprocess, urllib.error
import pytest
os.environ.setdefault("COMFYUI_URL", "http://127.0.0.1:9")
from fastapi.testclient import TestClient
from studio import rotation as Rot, server as S

SIZE = Rot.MIN_SIZE + 1024

def _fake_rclone(args):
    """Enough of rclone for these tests when the binary is absent: copyto, lsf, check, listremotes."""
    cmd = args[0]; ok = lambda out="", err="": subprocess.CompletedProcess(args, 0, out, err); bad = lambda err: subprocess.CompletedProcess(args, 3, "", err)
    if cmd == "copyto":
        if not os.path.exists(args[1]): return bad("not found")
        os.makedirs(os.path.dirname(args[2]), exist_ok=True); shutil.copyfile(args[1], args[2]); return ok()
    if cmd == "lsf": return ok(f"{os.path.getsize(args[-1])}\n") if os.path.exists(args[-1]) else bad("not found")
    if cmd == "check":
        name = open(args[args.index("--files-from-raw") + 1]).read().strip(); a, b = os.path.join(args[1], name), os.path.join(args[2], name)
        same = os.path.exists(b) and open(a, "rb").read() == open(b, "rb").read()
        return ok("", "0 differences found\n1 matching files\n") if same else bad("1 differences found")
    if cmd == "listremotes": return ok()
    return bad(f"unknown {cmd}")

@pytest.fixture
def box(tmp_path, monkeypatch):
    """A model root, a folder standing in for the cloud, and a config, all in tmp_path."""
    root, cloud, conf = tmp_path / "models", tmp_path / "cloud", tmp_path / "conf"
    root.mkdir(); cloud.mkdir(); conf.mkdir()
    monkeypatch.setenv("STUDIO_CONFIG_DIR", str(conf))
    (conf / "rotation.json").write_text(json.dumps({"remote": str(cloud), "remote_dir": "rot", "roots": [str(root)], "min_free_gb": 150}))
    monkeypatch.setattr(Rot, "_job", {"state": "idle"}); monkeypatch.setattr(Rot, "open_files", lambda: set())
    if not shutil.which("rclone"): monkeypatch.setattr(Rot, "run", _fake_rclone)
    return root, cloud, conf

def model(root, name="a.safetensors", fill=b"x"):
    p = root / name; p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f: f.write(fill * SIZE)
    return p

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

# ---------- off by default
@pytest.mark.parametrize("cfg", [None, "{}", "not json", '{"remote": ""}', '{"remote": "x:"}', '{"remote": "x:", "roots": []}'])
def test_no_remote_means_off(tmp_path, monkeypatch, cfg):
    monkeypatch.setenv("STUDIO_CONFIG_DIR", str(tmp_path))
    if cfg is not None: (tmp_path / "rotation.json").write_text(cfg)
    assert Rot.config() is None and Rot.status() == {"enabled": False} and Rot.cloud_only({"1": {"inputs": {"m": "a.safetensors"}}}) == []
    Rot.touch({"1": {"inputs": {"m": "a.safetensors"}}}); assert not (tmp_path / "rotation_manifest.json").exists()
    with pytest.raises(Rot.RotationError): Rot.offload("/x")

def test_api_is_quiet_when_off(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_CONFIG_DIR", str(tmp_path)); c = TestClient(S.app)
    r = c.get("/api/rotation/status"); assert r.status_code == 200 and r.json() == {"enabled": False}
    assert c.post("/api/rotation/fetch", json={"path": "/x"}).status_code == 409

# ---------- scan
def test_scan_hashes_nothing_and_skips_small_files(box, monkeypatch):
    root, _, _ = box; model(root); (root / "small.safetensors").write_bytes(b"x"); (root / "a.txt").write_bytes(b"x" * SIZE)
    monkeypatch.setattr(Rot, "sha256", lambda p: pytest.fail("scan must not hash"))
    fs = Rot.scan(); assert list(fs) == [str(root / "a.safetensors")]
    e = fs[str(root / "a.safetensors")]; assert e["state"] == "local" and e["sha256"] is None and e["pinned"] is False and "source" in e and "last_used" in e

def test_manifest_write_leaves_no_temp_file_on_failure(box, monkeypatch):
    _, _, conf = box; model(box[0]); Rot.scan(); before = (conf / "rotation_manifest.json").read_text()
    monkeypatch.setattr(Rot.json, "dump", lambda *a, **k: (_ for _ in ()).throw(ValueError("boom")))
    with pytest.raises(ValueError): Rot._save({"files": {}})
    assert (conf / "rotation_manifest.json").read_text() == before and not list(conf.glob(".rotation_*"))

# ---------- offload
def test_round_trip_restores_the_same_bytes(box):
    root, cloud, _ = box; p = model(root); want = sha(p)
    r = Rot.offload(p, yes=True); assert r["removed"] and not p.exists() and Rot.load()["files"][str(p)]["state"] == "cloud"
    assert Rot.status()["cloud"][0]["name"] == "a.safetensors" and any(cloud.rglob("a.safetensors"))
    Rot.fetch(p); assert sha(p) == want and Rot.load()["files"][str(p)]["state"] == "both"

def test_without_yes_the_local_copy_stays(box):
    p = model(box[0]); r = Rot.offload(p); assert p.exists() and not r["removed"] and Rot.load()["files"][str(p)]["state"] == "both"

@pytest.mark.parametrize("stage", ["copyto", "lsf", "check"])
def test_any_failed_step_keeps_the_local_file(box, monkeypatch, stage):
    p = model(box[0]); real = Rot.run
    monkeypatch.setattr(Rot, "run", lambda a: subprocess.CompletedProcess(a, 3, "", f"{stage} broke") if a[0] == stage else real(a))
    with pytest.raises(Rot.RotationError): Rot.offload(p, yes=True)
    assert p.exists() and Rot.load()["files"][str(p)]["state"] == "local"

def test_a_check_that_compared_nothing_is_a_failure(box, monkeypatch):
    p = model(box[0]); real = Rot.run
    monkeypatch.setattr(Rot, "run", lambda a: subprocess.CompletedProcess(a, 0, "", "0 differences found\n0 matching files\n") if a[0] == "check" else real(a))
    with pytest.raises(Rot.RotationError, match="did not compare"): Rot.offload(p, yes=True)
    assert p.exists()

def test_a_wrong_uploaded_size_keeps_the_local_file(box, monkeypatch):
    p = model(box[0]); real = Rot.run
    monkeypatch.setattr(Rot, "run", lambda a: subprocess.CompletedProcess(a, 0, "12\n", "") if a[0] == "lsf" else real(a))
    with pytest.raises(Rot.RotationError, match="size mismatch"): Rot.offload(p, yes=True)
    assert p.exists()

def test_a_crypt_remote_uses_cryptcheck(box, monkeypatch):
    root, _, conf = box; p = model(root); calls = []
    (conf / "rotation.json").write_text(json.dumps({"remote": "secret:", "remote_dir": "r", "roots": [str(root)]}))
    def fake(a):
        calls.append(a[0])
        if a[0] == "listremotes": return subprocess.CompletedProcess(a, 0, "secret:  crypt\nplain:  drive\n", "")
        if a[0] == "lsf": return subprocess.CompletedProcess(a, 0, f"{os.path.getsize(p)}\n", "")
        return subprocess.CompletedProcess(a, 0, "", "1 matching files\n")
    monkeypatch.setattr(Rot, "run", fake); Rot.offload(p)
    assert "cryptcheck" in calls and "check" not in calls

def test_uploads_stop_at_the_drive_limit(box, monkeypatch):
    p = model(box[0]); seen = []; real = Rot.run
    monkeypatch.setattr(Rot, "run", lambda a: (seen.append(a), real(a))[1]); Rot.offload(p)
    assert "--drive-stop-on-upload-limit" in next(a for a in seen if a[0] == "copyto")

@pytest.mark.parametrize("kind", ["pinned", "open", "symlink", "hardlink", "unknown_open"])
def test_refusals_keep_the_file_and_upload_nothing(box, monkeypatch, kind):
    root, cloud, _ = box; p = model(root)
    if kind == "pinned": Rot.set_pinned(p, True)
    if kind == "open": monkeypatch.setattr(Rot, "open_files", lambda: {str(p)})
    if kind == "unknown_open": monkeypatch.setattr(Rot, "open_files", lambda: None)
    if kind == "symlink": os.symlink(p, root / "link.safetensors")
    if kind == "hardlink": os.link(p, root / "other.safetensors")
    with pytest.raises(Rot.Refused): Rot.offload(p, yes=True)
    assert p.exists() and not any(cloud.rglob("*.safetensors"))

def test_something_opening_it_during_upload_stops_the_delete(box, monkeypatch):
    p = model(box[0]); n = {"calls": 0}
    def later():
        n["calls"] += 1; return {str(p)} if n["calls"] > 1 else set()
    monkeypatch.setattr(Rot, "open_files", later)
    with pytest.raises(Rot.Refused): Rot.offload(p, yes=True)
    assert p.exists()

def test_paths_outside_the_roots_are_refused(box, tmp_path):
    outside = tmp_path / "outside.safetensors"; outside.write_bytes(b"x" * SIZE)
    for fn in (Rot.offload, Rot.fetch, lambda x: Rot.set_pinned(x, True)):
        with pytest.raises(Rot.RotationError, match="not inside"): fn(outside)
    assert outside.exists()

# ---------- fetch
def _cloud_only(box):
    p = model(box[0]); Rot.offload(p, yes=True); return p

def test_interrupted_fetch_leaves_nothing_under_the_real_name(box, monkeypatch):
    p = _cloud_only(box)
    def dies(a):
        open(a[2], "wb").write(b"half"); return subprocess.CompletedProcess(a, 1, "", "connection lost")
    monkeypatch.setattr(Rot, "run", dies)
    with pytest.raises(Rot.RotationError): Rot.fetch(p)
    assert not p.exists() and not os.path.exists(str(p) + ".part") and Rot.load()["files"][str(p)]["state"] == "cloud"

def test_fetch_with_a_wrong_checksum_is_thrown_away(box, monkeypatch):
    p = _cloud_only(box)
    def wrong(a):
        open(a[2], "wb").write(b"y" * SIZE); return subprocess.CompletedProcess(a, 0, "", "")
    monkeypatch.setattr(Rot, "run", wrong)
    with pytest.raises(Rot.RotationError, match="checksum"): Rot.fetch(p)
    assert not p.exists() and not os.path.exists(str(p) + ".part")

def test_fetch_checks_free_space_first(box, monkeypatch):
    p = _cloud_only(box); monkeypatch.setattr(Rot.shutil, "disk_usage", lambda _: type("U", (), {"free": 10})())
    monkeypatch.setattr(Rot, "run", lambda a: pytest.fail("must not download"))
    with pytest.raises(Rot.RotationError, match="not enough space"): Rot.fetch(p)

# ---------- plan
def test_plan_moves_nothing_and_takes_least_recently_used_first(box, monkeypatch):
    root, _, _ = box; a, b, c = model(root, "a.safetensors"), model(root, "b.safetensors"), model(root, "c.safetensors"); Rot.scan()
    def stamp(m):
        m["files"][str(a)]["last_used"] = 300; m["files"][str(b)]["last_used"] = 100; m["files"][str(c)]["last_used"] = 200
    Rot._update(stamp); monkeypatch.setattr(Rot, "run", lambda x: pytest.fail("a plan must not touch the remote"))
    monkeypatch.setattr(Rot.shutil, "disk_usage", lambda _: type("U", (), {"free": int(150 * Rot.GB) - SIZE - 5})())
    r = Rot.plan(); assert [m["path"] for m in r["moves"]] == [str(b), str(c)] and a.exists() and b.exists() and c.exists() and r["order"] == "by recorded use"

def test_plan_says_when_it_has_no_usage_to_go_on(box, monkeypatch):
    root, _, _ = box; model(root); monkeypatch.setattr(Rot, "atime_works", lambda _: False)
    monkeypatch.setattr(Rot.shutil, "disk_usage", lambda _: type("U", (), {"free": 0})())
    r = Rot.plan(); assert "NO USE RECORDED" in r["order"] and r["moves"][0]["how"] == "never recorded" and r["disks"][0]["still_short_gb"] > 0

def test_plan_lists_what_it_refused(box, monkeypatch):
    root, _, _ = box; p = model(root); Rot.set_pinned(p, True); monkeypatch.setattr(Rot.shutil, "disk_usage", lambda _: type("U", (), {"free": 0})())
    r = Rot.plan(); assert not r["moves"] and r["refused"][0]["why"] == ["pinned"]

def test_atime_is_only_used_when_the_mount_updates_it(box, monkeypatch):
    root, _, _ = box; model(root); monkeypatch.setattr(Rot, "atime_works", lambda _: True); monkeypatch.setattr(Rot.shutil, "disk_usage", lambda _: type("U", (), {"free": 0})())
    assert Rot.plan()["moves"][0]["how"] == "atime"

# ---------- generate
GRAPH = {"1": {"inputs": {"ckpt_name": "sub/a.safetensors", "steps": 4}}}

@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(S, "comfy", lambda *a, **k: (_ for _ in ()).throw(urllib.error.URLError("down"))); monkeypatch.setattr(S, "comfy_up", lambda: True)
    monkeypatch.setattr(S, "adopt_comfy_paths", lambda: None); monkeypatch.setattr(S, "fill", lambda tpl, vals: json.loads(json.dumps(GRAPH)))
    return TestClient(S.app, raise_server_exceptions=False)

def test_generate_names_a_cloud_only_model_with_a_409(box, api):
    p = model(box[0], "sub/a.safetensors"); Rot.offload(p, yes=True)
    r = api.post("/api/generate", json={"goal": "image", "prompt": "a fox"})
    assert r.status_code == 409 and "a.safetensors" in r.json()["detail"] and "fetch" in r.json()["detail"].lower()

def test_viewing_the_graph_still_works_for_a_cloud_model(box, api):
    p = model(box[0], "sub/a.safetensors"); Rot.offload(p, yes=True)
    assert api.post("/api/graph", json={"goal": "image", "prompt": "a fox"}).status_code == 200

def test_generate_with_rotation_off_never_409s(tmp_path, monkeypatch, api):
    monkeypatch.setenv("STUDIO_CONFIG_DIR", str(tmp_path))
    assert api.post("/api/generate", json={"goal": "image", "prompt": "a fox"}).status_code != 409

def test_graph_use_is_recorded(box, api):
    p = model(box[0], "sub/a.safetensors"); Rot.scan()
    assert api.post("/api/graph", json={"goal": "image", "prompt": "a fox"}).status_code == 200
    assert Rot.load()["files"][str(p)]["last_used"]

def test_a_broken_manifest_never_stops_a_render(box, monkeypatch):
    monkeypatch.setattr(Rot, "_update", lambda fn: (_ for _ in ()).throw(OSError("disk full")))
    Rot.touch(GRAPH)

# ---------- API
def _wait(c):
    import time
    for _ in range(200):
        j = c.get("/api/rotation/status").json()["job"]
        if j["state"] != "running": return j
        time.sleep(0.05)
    raise AssertionError("job never finished")

def test_api_offload_needs_confirm_and_fetch_brings_it_back(box):
    p = model(box[0]); Rot.scan(); c = TestClient(S.app)
    assert c.post("/api/rotation/offload", json={"path": str(p)}).status_code == 400 and p.exists()
    assert c.post("/api/rotation/offload", json={"path": str(p), "confirm": True}).status_code == 200
    assert _wait(c)["state"] == "done" and not p.exists()
    row = c.get("/api/rotation/status").json()["cloud"][0]; assert row["eta_min"] >= 1 and row["path"] == str(p)
    assert c.post("/api/rotation/fetch", json={"path": str(p)}).status_code == 200
    assert _wait(c)["state"] == "done" and p.exists()

def test_api_only_touches_tracked_models(box, tmp_path):
    other = tmp_path / "secret.safetensors"; other.write_bytes(b"x" * SIZE); c = TestClient(S.app)
    assert c.post("/api/rotation/offload", json={"path": str(other), "confirm": True}).status_code == 404 and other.exists()
    assert c.post("/api/rotation/fetch", json=["x"]).status_code == 400

def test_api_refuses_a_second_job(box, monkeypatch):
    p = model(box[0]); Rot.scan(); monkeypatch.setattr(Rot, "_job", {"state": "running", "kind": "fetch", "path": "x"})
    assert TestClient(S.app).post("/api/rotation/fetch", json={"path": str(p)}).status_code == 409

def test_a_refused_api_offload_reports_why_and_keeps_the_file(box):
    p = model(box[0]); Rot.set_pinned(p, True); c = TestClient(S.app)
    assert c.post("/api/rotation/offload", json={"path": str(p), "confirm": True}).status_code == 200
    j = _wait(c); assert j["state"] == "error" and "pinned" in j["error"] and p.exists()

def test_the_page_hides_in_the_demo_and_when_off():
    src = open(os.path.join(os.path.dirname(S.__file__), "web", "models_ui.js"), encoding="utf-8").read()
    i = src.index("export function CloudCard"); body = src[i:]
    assert "window.STUDIO_DEMO" in body and "!st.enabled" in body and "In cloud, about" in body and "Fetch" in body
