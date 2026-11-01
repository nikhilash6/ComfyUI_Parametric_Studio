"""Pack Lab: the do-not-install list holds, no Docker means refusal, and the sandbox command is sealed. Docker and git are stubbed; no real container and no live ports."""
import json, re
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import feature_packlab as L

WEB = Path(L.__file__).parent / "web"
FAKE_HOME = "/".join(("", "home", "someone"))       # a made-up folder, spelled so the scan for this repo's real paths stays useful


class R:
    def __init__(self, rc=0, out="", err=""): self.returncode, self.stdout, self.stderr = rc, out, err


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_PACK_SANDBOX_DIR", str(tmp_path / "box"))
    monkeypatch.setattr(L, "_run", lambda *a, **k: pytest.fail("touched Docker in a test that should not"))
    app = FastAPI(); app.include_router(L.router); c = TestClient(app); c.tmp = tmp_path; return c


def candidate(): return next(p["pack"] for p in L.picks()["picks"] if p["action"] == "install-candidate")


def docker_ok(monkeypatch, tmp):
    (tmp / "comfy").mkdir(exist_ok=True); (tmp / "comfy" / "main.py").write_text(""); py = tmp / "venv" / "bin" / "python"; py.parent.mkdir(parents=True, exist_ok=True); py.write_text("")
    monkeypatch.setattr(L, "comfy_paths", lambda: (str(tmp / "comfy"), str(py))); monkeypatch.setattr(L.shutil, "which", lambda n: "/usr/bin/" + n); monkeypatch.setattr(L.platform, "system", lambda: "Linux")


def test_the_catalogue_is_clean():
    text = L.DATA.read_text(); d = json.loads(text)
    assert len(d["picks"]) > 100 and not re.search(r"/mnt/|/home/|[Ff]ounder|nodepack_library", text)
    assert "blocked" not in d and "category" not in text and len(d["flag_salt"]) == 32 and d["flagged"] and all(re.fullmatch(r"[0-9a-f]{64}", h) for h in d["flagged"]), "flagged packs are hashes only"
    assert "not exhaustive" in d["about"]
    assert not any(L.is_flagged(p["pack"]) for p in d["picks"]), "a flagged pack is not listed as a pick"


def test_no_page_or_note_calls_a_pack_safe():
    js = (WEB / "packlab.js").read_text(); src = L.Path(L.__file__).read_text()
    assert not re.search(r"\b(is|are|it's) safe\b|safe to install|verified safe", js + src, re.I)
    assert "does not mean safe" in src and "d.flag_note" in js and "d.blocked" not in js


@pytest.mark.parametrize("system,which,why", [("Windows", True, "only runs on Linux"), ("Linux", False, "no working Docker")])
def test_no_docker_refuses_plainly(client, monkeypatch, system, which, why):
    monkeypatch.setattr(L.platform, "system", lambda: system); monkeypatch.setattr(L.shutil, "which", lambda n: "/x" if which else None)
    r = client.post("/api/packlab/sandbox", json={"pack": candidate(), "understood": True})
    assert r.status_code == 409 and why in r.json()["detail"] and "never install into your live ComfyUI" in r.json()["detail"]
    d = client.get("/api/packlab/picks").json(); assert d["can"]["ok"] is False and d["picks"]


def test_a_docker_that_does_not_answer_refuses(client, monkeypatch):
    monkeypatch.setattr(L.platform, "system", lambda: "Linux"); monkeypatch.setattr(L.shutil, "which", lambda n: "/x"); monkeypatch.setattr(L, "_run", lambda *a, **k: R(1))
    assert L.can_sandbox()["ok"] is False


def test_unknown_comfy_folders_refuse_rather_than_guess(monkeypatch):
    monkeypatch.setattr(L.platform, "system", lambda: "Linux"); monkeypatch.setattr(L.shutil, "which", lambda n: "/x"); monkeypatch.setattr(L, "_run", lambda *a, **k: R(0, "27.0")); monkeypatch.setattr(L, "comfy_paths", lambda: ("", ""))
    c = L.can_sandbox(); assert not c["ok"] and "STUDIO_COMFY_ROOT" in c["why"]


def plant_flag(monkeypatch, pack):
    import hashlib
    d = {**L.picks(), "flag_salt": "s", "flagged": [hashlib.sha256(f"s:{pack.lower()}".encode()).hexdigest()]}; monkeypatch.setitem(L._cache, "d", d)


@pytest.mark.parametrize("asked", ["someone__Flagged", "SOMEONE__flagged"])
def test_a_flagged_pack_is_refused_in_general_words(client, monkeypatch, asked):
    plant_flag(monkeypatch, "someone__flagged"); monkeypatch.setattr(L, "can_sandbox", lambda: pytest.fail("should stop first"))
    r = client.post("/api/packlab/sandbox", json={"pack": asked, "understood": True})
    assert r.status_code == 403 and r.json()["detail"] == L.FLAGGED and "someone" not in r.json()["detail"]


def test_a_flagged_pick_is_not_offered(client, monkeypatch):
    pack = candidate(); plant_flag(monkeypatch, pack); monkeypatch.setattr(L, "can_sandbox", lambda: {"ok": False, "why": "x"})
    d = client.get("/api/packlab/picks").json(); assert not next(p for p in d["picks"] if p["pack"] == pack)["installable"]
    assert "not exhaustive" in d["flag_note"] and "blocked" not in d and "flagged" not in d


def test_only_reviewed_candidates_install(client, monkeypatch):
    monkeypatch.setattr(L, "can_sandbox", lambda: pytest.fail("should stop first"))
    assert client.post("/api/packlab/sandbox", json={"pack": "someone__unknown", "understood": True}).status_code == 404
    idea = next(p["pack"] for p in L.picks()["picks"] if p["action"] != "install-candidate")
    assert client.post("/api/packlab/sandbox", json={"pack": idea, "understood": True}).status_code == 409
    assert client.post("/api/packlab/sandbox", json={"pack": candidate()}).status_code == 400
    assert client.post("/api/packlab/sandbox", json={"pack": "../../etc", "understood": True}).status_code == 400


def sealed(tmp): return L.container_args("a__b", tmp / "d", "/opt/comfy", "/opt/venv/bin/python")


def test_the_container_is_sealed(tmp_path):
    a = sealed(tmp_path); t = " ".join(a)
    assert L.isolation_problems(a) == [] and "--read-only" in a and "--cap-drop ALL" in t and "no-new-privileges" in t and f"--network {L.NETWORK}" in t and "--cpu" in a
    assert "--device" not in a and "--gpus" not in a and "comfyui_models" not in t and str(Path.home()) not in t
    assert a[a.index("--name") + 1] == L.PREFIX + "a-b" and "pack-lab" != a[a.index("--name") + 1]
    assert "/opt/comfy:/comfy:ro" in a and "--base-directory" in a and a[a.index("--base-directory") + 1] == "/sandbox"


@pytest.mark.parametrize("add", [["--privileged"], ["--device", "/dev/nvidia0"], ["--gpus", "all"], ["-p", "8188:8188"], ["-v", "/var/run/docker.sock:/var/run/docker.sock:ro"], ["-v", str(Path.home()) + ":/h:ro"], ["-v", "/opt:/opt"]])
def test_anything_looser_is_caught(tmp_path, add):
    assert L.isolation_problems(sealed(tmp_path) + add)


def test_a_missing_seal_is_caught(tmp_path):
    a = [x for x in sealed(tmp_path) if x != "--read-only"]; assert "missing --read-only" in L.isolation_problems(a)


def fake_docker(calls, internet="blocked", import_fail=False, home="hidden"):
    def run(args, timeout=60, **k):
        calls.append(args); s = " ".join(args)
        if "version" in args: return R(0, "27.0")
        if args[:3] == ["docker", "network", "inspect"]: return R(0, "true")
        if args[:3] == ["docker", "image", "inspect"]: return R(0)
        if args[:2] == ["docker", "run"]: return R(0, "id")
        if args[:2] == ["docker", "exec"]: return R(0, internet) if "1.1.1.1" in s else R(0, home) if ".ssh" in s else R(0, json.dumps({"KSampler": {"python_module": "nodes"}, "MyNode": {"python_module": "custom_nodes." + L_PACK[0]}}))
        if args[:2] == ["docker", "inspect"]: return R(0, "true")
        if args[:2] == ["docker", "logs"]: return R(0, "IMPORT FAILED " + L_PACK[0] if import_fail else "ok " + FAKE_HOME + "/x")
        if args[0] == "git": Path(args[-1]).mkdir(parents=True, exist_ok=True); (Path(args[-1]) / "__init__.py").write_text(""); return R(0)
        return R(0)
    return run


L_PACK = [""]


def run_install(client, monkeypatch, **k):
    docker_ok(monkeypatch, client.tmp); L_PACK[0] = candidate(); calls = []; monkeypatch.setattr(L, "_run", fake_docker(calls, **k)); monkeypatch.setattr(L, "_setting", lambda n: "")
    L._save(L_PACK[0], state="fetching"); L._install(L_PACK[0]); return L.state(L_PACK[0]), calls


def test_a_full_install_loads_lists_nodes_and_cleans_up(client, monkeypatch):
    s, calls = run_install(client, monkeypatch)
    assert s["state"] == "loaded" and s["nodes"] == ["MyNode"] and s["no_internet"] is True and s["home_hidden"] is True and FAKE_HOME not in s["log"]
    assert ["docker", "rm", "-f", L.PREFIX + L.slug(L_PACK[0])] in calls
    git = next(c for c in calls if c[0] == "git"); assert "--no-recurse-submodules" in git and "core.hooksPath=/dev/null" in git and git[-2].startswith("https://github.com/")
    assert not any("pip" == x for c in calls for x in c), "nothing is pip-installed"


def test_internet_inside_shuts_it_down(client, monkeypatch):
    monkeypatch.setattr(L.time, "sleep", lambda s: None); s, calls = run_install(client, monkeypatch, internet="REACHABLE")
    assert s["state"] == "failed" and "internet" in s["note"] and calls[-1][:3] == ["docker", "rm", "-f"]


def test_a_docker_timeout_says_so_without_the_command(client, monkeypatch):
    docker_ok(monkeypatch, client.tmp); L_PACK[0] = candidate(); real = fake_docker([])
    def slow(args, timeout=60, **k):
        if args[:2] == ["docker", "run"]: raise L.subprocess.TimeoutExpired(args, timeout)
        return real(args, timeout, **k)
    monkeypatch.setattr(L, "_run", slow); monkeypatch.setattr(L, "_setting", lambda n: ""); L._save(L_PACK[0], state="fetching"); L._install(L_PACK[0]); s = L.state(L_PACK[0])
    assert s["state"] == "failed" and "too long" in s["note"] and "docker run" not in s["note"] and "--read-only" not in s["note"]


def test_a_visible_home_shuts_it_down(client, monkeypatch):
    s, calls = run_install(client, monkeypatch, home="FOUND"); assert s["state"] == "failed" and "home folder" in s["note"] and calls[-1][:3] == ["docker", "rm", "-f"]


def test_an_import_failure_is_reported(client, monkeypatch):
    s, _ = run_install(client, monkeypatch, import_fail=True); assert s["state"] == "failed" and "failed to import" in s["note"]


def test_delete_only_touches_its_own_folder_and_name(client, monkeypatch):
    docker_ok(monkeypatch, client.tmp); calls = []; monkeypatch.setattr(L, "_run", lambda a, t=60, **k: calls.append(a) or R(0)); L._save("a__b", state="loaded")
    assert client.delete("/api/packlab/sandbox/a__b").status_code == 200 and calls == [["docker", "rm", "-f", L.PREFIX + "a-b"]] and not L.sandbox_dir("a__b").exists()
    assert client.delete("/api/packlab/sandbox/pack-lab").status_code == 404


def test_links_in_a_pack_are_dropped(tmp_path, monkeypatch):
    src = tmp_path / "lib" / "a__b"; src.mkdir(parents=True); (src / "n.py").write_text(""); (src / "evil").symlink_to("/etc/passwd")
    monkeypatch.setattr(L, "_setting", lambda n: str(tmp_path / "lib")); L.fetch("a__b", tmp_path / "out" / "a__b")
    assert (tmp_path / "out" / "a__b" / "n.py").exists() and not (tmp_path / "out" / "a__b" / "evil").exists()
