"""The container: the Dockerfile asks install.py only for flags it has, plans CUDA PyTorch with no GPU at build time, keeps secrets and history out of the image, and runs as a user on 127.0.0.1.
No image is built here and nothing is downloaded; docker's own linter runs only when the base image is already on this machine."""
import json, re, shutil, subprocess, sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import install

DF = (ROOT / "Dockerfile").read_text(encoding="utf-8"); IGNORE = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()


def test_the_base_is_pinned_and_the_image_runs_as_a_user():
    assert re.search(r"^FROM ubuntu:24\.04$", DF, re.M) and "latest" not in DF.split("FROM", 1)[1].split("\n", 1)[0]
    users = re.findall(r"^USER (\S+)", DF, re.M); assert users and users[-1] != "root"
    assert 'ENTRYPOINT ["/usr/bin/tini", "--"]' in DF and "EXPOSE 8310" in DF


def test_every_install_flag_the_dockerfile_uses_exists():
    a = install.parse_args(["--yes", "--no-models", "--channel", "stable", "--profile-json", "p.json", "--dir", "/opt/runtime"])
    assert a.yes and a.no_models and a.profile_json == "p.json"
    for flag in set(re.findall(r"install\.py\"? ([^\n']*)", DF)[0].split()) | {"--goals", "--include-gated"}:
        if flag.startswith("--"): assert flag in install.parse_args.__code__.co_consts or flag in (ROOT / "install.py").read_text(), flag


def test_the_build_profile_plans_cuda_pytorch_without_a_gpu():
    tmpl = re.search(r"printf '(\{\"os\".*?\})\\n' \"\$VRAM_GB\"", DF).group(1)
    profile = json.loads(tmpl.replace("%s", "24"))
    gm = install.load_json(ROOT / "studio" / "models_manifest.json"); pm = install.to_plan_manifest(gm); ch = install.load_json(ROOT / "channels.json")
    r = install.plan(profile, pm, ["anime"]); cmds = install.build_commands(r, pm, ch, "stable", "/opt/runtime", profile["backend"], False, False)
    torch = next(c for c in cmds if "torch" in c); assert any("cu1" in str(x) for x in torch) and not any("whl/cpu" in str(x) for x in torch)


def test_the_start_script_keeps_the_engine_local_and_reuses_downloads():
    start = re.search(r"RUN printf '%s\\n' '#!/bin/sh'(.*?)> \"\$RUNTIME/start.sh\"", DF, re.S).group(1)
    assert "--listen 127.0.0.1 --port 8200" in start and "-m studio.server" in start and 'install.py" --yes --goals "$PSN_GOALS"' in start
    assert "STUDIO_HOST=127.0.0.1" in DF and "PSN_MODELS_ROOT" in start
    assert 'VOLUME ["/opt/runtime/ComfyUI/models", "/opt/runtime/ComfyUI/output"]' in DF


def test_the_healthcheck_asks_a_route_the_server_has():
    assert "/api/health" in DF and '@app.get("/api/health")' in (ROOT / "studio" / "server.py").read_text(encoding="utf-8")


def test_history_secrets_and_work_folders_stay_out_of_the_image():
    for x in (".git", ".env", "*.env", "**/__pycache__", "*_work", "*_proof_work"): assert x in IGNORE, x
    assert "HF_TOKEN=" not in DF.replace("-e HF_TOKEN=...", "") and "COPY . " not in DF.replace("COPY --chown=studio:studio . ", "")


def test_install_py_points_at_the_container():
    r = subprocess.run([sys.executable, str(ROOT / "install.py"), "--docker"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "docker build -t parametric-studio ." in r.stdout and "--network host" in r.stdout


@pytest.mark.skipif(not shutil.which("docker"), reason="docker not installed")
def test_dockers_own_linter_passes():
    if subprocess.run(["docker", "image", "inspect", "ubuntu:24.04"], capture_output=True, timeout=30).returncode: pytest.skip("base image not on this machine; the check would download it")
    r = subprocess.run(["docker", "buildx", "build", "--check", str(ROOT)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "no warnings found" in (r.stdout + r.stderr), (r.stdout + r.stderr)[-800:]


# ---------- the small-card runner (scripts/measure_small_card.py): stubbed ComfyUI, no GPU
import importlib.util
_spec = importlib.util.spec_from_file_location("measure_small_card", ROOT / "scripts" / "measure_small_card.py"); MSC = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(MSC)


class FakeComfy:
    def __init__(self, results): self.results = list(results); self.graphs = []; self.freed = 0
    def upload(self, p): return "up_" + Path(p).name
    def run(self, g): self.graphs.append(g); return self.results.pop(0)
    def free(self): self.freed += 1


def test_the_small_card_runner_records_pass_oom_and_free_memory(tmp_path):
    c = FakeComfy([("done", ""), ("error", "torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB"), ("error", "some other fault")])
    held = []
    import contextlib
    @contextlib.contextmanager
    def hold(goal): held.append(goal); yield
    e = MSC.measure(24, c, ["vfx_ltx", "recast", "reshoot"], reserve=72, used=lambda: 20.5, free=lambda: 60.0, graph=lambda b: b, hold=hold)
    assert [r["result"] for r in e["runs"]] == ["pass", "oom", "error"] and held == ["vfx_ltx", "recast", "reshoot"] and c.freed == 3
    assert e["runs"][0]["free_at_start_gib"] == 60.0 and e["reserve_vram_gb"] == 72 and c.graphs[1]["video"] == "up_vfx_same_src.mp4" and c.graphs[1]["image"] == "up_s_portrait.webp"
    d = MSC.save(e, tmp_path / "m.json"); t = MSC.table(d)
    assert "| vfx_ltx | pass" in t and "| recast | out of memory |" in t and "| reshoot | failed |" in t and "24 GB" in t.splitlines()[0]
    assert MSC.table({}) == "Not measured yet."


def test_the_small_card_runner_refuses_the_main_comfyui():
    for port in (8200, 8322):
        with pytest.raises(SystemExit): MSC.main(["run", "--cap", "24", "--comfy", f"http://127.0.0.1:{port}"])


def test_the_small_card_requests_build_real_graphs():
    from studio import goals
    for job, body in MSC.JOBS.items():
        assert body["goal"] in goals.GOALS, job
        for k, v in body.get("options", {}).items(): assert v in goals.GOALS[body["goal"]]["options"][k], (job, k, v)
    assert all(p.is_file() for p in MSC.INPUTS.values())


# ---------- the Windows installer (scripts/install_windows.ps1): read, never run here
PS1 = (ROOT / "scripts" / "install_windows.ps1").read_text(encoding="utf-8")


def test_the_windows_script_says_it_is_untested_and_dry_runs_first():
    assert PS1.count("UNTESTED ON WINDOWS") >= 2 and PS1.index("--dry-run") < PS1.index("@installArgs --yes") and "Read-Host" in PS1
    assert "$args =" not in PS1 and "Set-StrictMode" in PS1 and "py -3.12" in PS1.replace('"py", "-3.12"', "py -3.12")
    for flag in ("--goals", "--channel", "--dir", "--no-models", "--yes", "--dry-run"): assert flag in (ROOT / "install.py").read_text(), flag


@pytest.mark.skipif(not shutil.which("pwsh"), reason="PowerShell not installed")
def test_the_windows_script_passes_psscriptanalyzer():
    r = subprocess.run(["pwsh", "-NoProfile", "-Command", f"if (Get-Module -ListAvailable PSScriptAnalyzer) {{ Invoke-ScriptAnalyzer -Path '{ROOT / 'scripts' / 'install_windows.ps1'}' -Severity Error | Measure-Object | % Count }} else {{ 'none' }}"], capture_output=True, text=True, timeout=120)
    if r.stdout.strip() == "none": pytest.skip("PSScriptAnalyzer not installed")
    assert r.stdout.strip() == "0", r.stdout + r.stderr
