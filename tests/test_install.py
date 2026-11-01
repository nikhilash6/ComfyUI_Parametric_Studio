"""Installer tests: simulated hardware, an injected downloader, no network and no real installs."""
import hashlib, json, os, subprocess, sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import install

NVIDIA_12 = {"os": "linux", "gpus": [{"name": "RTX 3060", "vram_gb": 12.0, "vendor": "nvidia"}], "ram_gb": 32.0, "disk_free_gb": 500.0, "backend": "cuda", "caps": []}
BLACKWELL = {"os": "linux", "gpus": [{"name": "Blackwell", "vram_gb": 96.0, "vendor": "nvidia"}], "ram_gb": 128.0, "disk_free_gb": 900.0, "backend": "cuda", "caps": ["bf16", "fp8", "nvfp4"]}
WIN_AMD = {"os": "windows", "gpus": [{"name": "Radeon", "vram_gb": 16.0, "vendor": "amd"}], "ram_gb": 32.0, "disk_free_gb": 500.0, "backend": "rocm", "caps": []}
MAC = {"os": "mac", "gpus": [{"name": "Apple", "vram_gb": 0.0, "vendor": "apple"}], "ram_gb": 16.0, "disk_free_gb": 200.0, "backend": "mps", "caps": []}
CPU = {"os": "linux", "gpus": [], "ram_gb": 16.0, "disk_free_gb": 200.0, "backend": "cpu", "caps": []}

@pytest.fixture(scope="module")
def manifests():
    gm = install.load_json(ROOT / "studio" / "models_manifest.json"); return gm, install.to_plan_manifest(gm), install.load_json(ROOT / "channels.json")

def test_every_goal_has_a_vram_figure_and_backends(manifests):
    gm, _, _ = manifests
    assert set(gm["goals"]) <= set(install.PEAK_VRAM_GIB) and set(gm["goals"]) <= set(install.BACKENDS)

def test_venv_python_path_per_os(monkeypatch):
    monkeypatch.setattr(install.platform, "system", lambda: "Linux"); assert install.get_venv_python_path(Path("/x")) == Path("/x/venv/bin/python")
    monkeypatch.setattr(install.platform, "system", lambda: "Windows"); assert install.get_venv_python_path(Path("/x")) == Path("/x/venv/Scripts/python.exe")

@pytest.mark.parametrize("profile,index", [(NVIDIA_12, "cu130"), (WIN_AMD, "rocm"), (CPU, "whl/cpu")])
def test_torch_args_follow_the_backend(manifests, profile, index):
    _, pm, ch = manifests; r = install.plan(profile, pm, ["image"])
    cmds = install.build_commands(r, pm, ch, "stable", "/x", profile["backend"]); torch = next(c for c in cmds if "torch" in c)
    assert any(index in str(a) for a in torch)

def test_channels_pin_stable_and_follow_master(manifests):
    _, pm, ch = manifests; r = install.plan(BLACKWELL, pm, ["image"])
    clone = lambda c: next(x for x in install.build_commands(r, pm, ch, c, "/x", "cuda") if x[:2] == ["git", "clone"])
    assert "v0.43.0" in clone("stable") and "master" in clone("nightly")

def test_gated_goals_need_an_explicit_flag(manifests):
    _, pm, ch = manifests; r = install.plan(BLACKWELL, pm, ["flux3"])
    assert not [c for c in install.build_commands(r, pm, ch, "stable", "/x", "cuda") if c[0] == "download"]
    assert [c for c in install.build_commands(r, pm, ch, "stable", "/x", "cuda", include_gated=True) if c[0] == "download"]

def test_h3_is_not_offered_without_nvfp4(manifests):
    _, pm, ch = manifests; r = install.plan(NVIDIA_12, pm, ["h3_video"])
    assert r["items"][0]["mode"] == "unavailable"
    assert not [c for c in install.build_commands(r, pm, ch, "stable", "/x", "cuda") if c[0] == "download"]

def test_shared_files_are_fetched_once(manifests):
    _, pm, ch = manifests; r = install.plan(BLACKWELL, pm, ["video", "animate"])
    dl = [c[1] for c in install.build_commands(r, pm, ch, "stable", "/x", "cuda") if c[0] == "download"]
    assert len(dl) == len(set(dl)) == 3

def test_ltx_goal_brings_the_pack_its_graph_needs(manifests):
    _, pm, ch = manifests; r = install.plan(BLACKWELL, pm, ["video_ltx"])
    assert any("ComfyUI-LTXVideo" in str(a) for c in install.build_commands(r, pm, ch, "stable", "/x", "cuda", include_gated=True) for a in c)

def test_low_vram_flags_reach_the_launcher(manifests):
    _, pm, _ = manifests; r = install.plan(NVIDIA_12, pm, ["image"]); flags = install.comfy_flags(r)
    assert flags in (["--lowvram"], ["--novram"])
    sh = install.launcher_text("Linux", "/x", "/r", flags); bat = install.launcher_text("Windows", "/x", "/r", flags)
    assert flags[0] in sh and flags[0] in bat and "studio.server" in sh and "studio.server" in bat and "/x/venv/bin/python" in sh and "python.exe" in bat

class Resp:
    def __init__(self, data, status=200): self.data, self.status, self.pos = data, status, 0
    def read(self, n=-1):
        chunk = self.data[self.pos:] if n < 0 else self.data[self.pos:self.pos + n]; self.pos += len(chunk); return chunk

def test_download_verifies_the_hash(tmp_path):
    good = hashlib.sha256(b"hello").hexdigest(); dest = tmp_path / "a" / "f.bin"
    assert install.download_file("http://x", dest, good, opener=lambda req: Resp(b"hello")) and dest.read_bytes() == b"hello"
    assert install.download_file("http://x", dest, good, opener=lambda req: pytest.fail("should not re-download"))
    bad = tmp_path / "b.bin"
    assert not install.download_file("http://x", bad, "0" * 64, opener=lambda req: Resp(b"hello"))
    assert not bad.exists() and not (tmp_path / "b.bin.part").exists()

def test_download_resumes_with_range(tmp_path):
    full = b"hello world"; dest = tmp_path / "f.bin"; (tmp_path / "f.bin.part").write_bytes(full[:5]); seen = {}
    def opener(req): seen["range"] = req.get_header("Range"); return Resp(full[5:], 206)
    assert install.download_file("http://x", dest, hashlib.sha256(full).hexdigest(), opener=opener)
    assert seen["range"] == "bytes=5-" and dest.read_bytes() == full

def test_download_restarts_when_the_server_ignores_range(tmp_path):
    full = b"hello world"; dest = tmp_path / "f.bin"; (tmp_path / "f.bin.part").write_bytes(b"xxxxx")
    assert install.download_file("http://x", dest, hashlib.sha256(full).hexdigest(), opener=lambda req: Resp(full, 200)) and dest.read_bytes() == full

def test_token_is_dropped_on_a_cdn_redirect():
    import urllib.request
    req = urllib.request.Request("https://huggingface.co/a", headers={"Authorization": "Bearer t"})
    new = install._DropTokenOnRedirect().redirect_request(req, None, 302, "x", {}, "https://cdn.example.net/a")
    assert new.get_header("Authorization") is None

@pytest.mark.parametrize("profile", [NVIDIA_12, BLACKWELL, WIN_AMD, MAC, CPU])
def test_cli_dry_run_changes_nothing(tmp_path, profile):
    pf = tmp_path / "p.json"; pf.write_text(json.dumps(profile)); target = tmp_path / "rt"
    r = subprocess.run([sys.executable, str(ROOT / "install.py"), "--dry-run", "--profile-json", str(pf), "--dir", str(target), "--goals", "image"], capture_output=True, text=True)
    assert r.returncode in (0, 3), r.stderr
    assert not target.exists()

def test_cli_no_models_dry_run_on_cpu(tmp_path):
    pf = tmp_path / "p.json"; pf.write_text(json.dumps(CPU))
    r = subprocess.run([sys.executable, str(ROOT / "install.py"), "--dry-run", "--no-models", "--profile-json", str(pf), "--dir", str(tmp_path / "rt")], capture_output=True, text=True)
    assert r.returncode == 0 and "download " not in r.stdout

def test_cli_unknown_goal_fails(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "install.py"), "--dry-run", "--goals", "nope", "--dir", str(tmp_path / "rt")], capture_output=True, text=True)
    assert r.returncode == 4

def _git_repo(path):
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty", "-m", "x"], check=True)

def test_a_rerun_keeps_a_checkout_and_finishes(tmp_path, monkeypatch):
    """A second run over a finished install must not stop at git clone: it is how an install resumes and how goals get added."""
    base = tmp_path / "rt"; _git_repo((base / "ComfyUI").mkdir(parents=True) or base / "ComfyUI")
    (base / "venv" / "bin").mkdir(parents=True); (base / "venv" / "bin" / "python").write_text("")
    ran = []; monkeypatch.setattr(install, "run_step", lambda cmd, **k: ran.append(cmd) or True); monkeypatch.setattr(install, "detect", lambda path=".": dict(BLACKWELL))
    assert install.main(["--no-models", "--yes", "--dir", str(base)]) == 0
    assert not [c for c in ran if c[:2] == ["git", "clone"]] and (base / "run_studio.sh").exists()

def test_a_folder_that_is_not_a_checkout_still_gets_cloned(tmp_path):
    (tmp_path / "ComfyUI").mkdir(); assert not install.already_cloned(tmp_path / "ComfyUI")

def test_a_failed_network_step_is_tried_again_then_stops(monkeypatch):
    calls = []
    def run(cmd, check): calls.append(cmd); raise subprocess.CalledProcessError(1, cmd)
    monkeypatch.setattr(install.subprocess, "run", run); waits = []
    assert not install.run_step(["pip"], sleep=waits.append) and len(calls) == install.NETWORK_TRIES and len(waits) == install.NETWORK_TRIES - 1

@pytest.mark.parametrize("dry, code", [(True, 0), (False, 4)])
def test_not_enough_disk_is_said_before_anything_is_changed(tmp_path, capsys, dry, code):
    small = {**BLACKWELL, "disk_free_gb": 20.0}; pf = tmp_path / "p.json"; pf.write_text(json.dumps(small)); target = tmp_path / "rt"
    assert install.main(["--yes", "--profile-json", str(pf), "--dir", str(target), "--goals", "image", *(["--dry-run"] if dry else [])]) == code
    out = capsys.readouterr().out; assert "Not enough disk space" in out and "25 GB needed" in out and not target.exists()

def test_install_docs_quote_the_real_sizes_and_order():
    doc = (ROOT / "INSTALL.md").read_text(encoding="utf-8"); goals = install.load_json(ROOT / "studio" / "models_manifest.json")["goals"]
    size = {g: sum(f["size_gb"] for f in e["files"]) for g, e in goals.items()}; smallest = min(size, key=size.get)
    assert f"`{smallest}` at {size[smallest]:.1f} GB" in doc and f"`image` goal is {size['image']:.0f} GB" in doc and f"about {install.SOFTWARE_GB:.0f} GB for the software" in doc
    linux = doc[doc.index("## Linux"):doc.index("## macOS")]; assert linux.index("apt update") < linux.index("apt install") < linux.index("git clone")
    assert "<this repository's URL>" not in doc

def test_the_last_thing_the_installer_says_is_the_studio(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(install, "run_step", lambda cmd, **k: True); monkeypatch.setattr(install, "detect", lambda path=".": dict(BLACKWELL))
    assert install.main(["--no-models", "--yes", "--dir", str(tmp_path / "rt")]) == 0
    assert "open the studio at http://127.0.0.1:8310" in capsys.readouterr().out

def test_the_launcher_needs_no_compiler_and_lets_you_opt_back_in():
    sh = install.launcher_text("Linux", "/x", "/r", []); bat = install.launcher_text("Windows", "/x", "/r", [])
    assert 'TORCH_DISABLE_NATIVE_JIT="${TORCH_DISABLE_NATIVE_JIT:-1}"' in sh and sh.index("TORCH_DISABLE_NATIVE_JIT") < sh.index("main.py") and "if not defined TORCH_DISABLE_NATIVE_JIT" in bat
