"""The Comfy Registry archive: what `comfy node publish` would ship, and how the pack behaves once ComfyUI-Manager installs it.
comfy-cli zips the git-tracked files minus .comfyignore (gitignore syntax); `git ls-files -ci --exclude-from=.comfyignore` lists the same left-out set."""
import ast, os, re, subprocess, sys, tomllib
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import install


def _git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


@pytest.fixture(scope="module")
def shipped():
    if _git("rev-parse", "--is-inside-work-tree").returncode:
        pytest.skip("not a git checkout")
    tracked = set(_git("ls-files").stdout.splitlines())
    left_out = set(_git("ls-files", "-ci", "--exclude-from=.comfyignore").stdout.splitlines())
    return sorted(p for p in tracked - left_out if (ROOT / p).is_file())


def test_registry_metadata_is_complete():
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project, comfy = cfg["project"], cfg["tool"]["comfy"]
    assert project["name"] == "comfyui-parametric-studio"          # immutable on the Registry
    assert re.fullmatch(r"\d+\.\d+\.\d+", project["version"])
    assert project["version"] != "0.1.0", "0.1.0 is already on the Registry and versions cannot be overwritten"
    assert project["urls"]["Repository"].startswith("https://github.com/")
    assert comfy["PublisherId"] == "parametricparadigm" and comfy["DisplayName"]
    assert project["license"] == {"file": "LICENSE"} and (ROOT / "LICENSE").is_file()


def test_the_archive_is_the_node_pack(shipped):
    for need in ("__init__.py", "pyproject.toml", "LICENSE", "README.md", "psn_nodes/logic.py", "psn/sandbox.py", "studio/goals.py", "workflows"):
        assert any(p == need or p.startswith(need + "/") for p in shipped), need
    for gone in ("install.py", "psn/sandbox_runner.py", "uv.lock"):
        assert gone not in shipped, gone
    for prefix in ("tests/", ".github/", ".ruff_cache/", "scripts/", "studio/web/", "docs/"):
        assert not any(p.startswith(prefix) for p in shipped), prefix
    size_mb = sum((ROOT / p).stat().st_size for p in shipped) / 1e6
    assert size_mb < 40, f"archive content is {size_mb:.0f} MB"


def test_no_exec_or_eval_ships(shipped):
    """Registry standards: eval/exec are prohibited, and so is installing packages through subprocess at runtime."""
    hits = []
    for p in (p for p in shipped if p.endswith(".py")):
        src = (ROOT / p).read_text(encoding="utf-8", errors="replace")
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("exec", "eval"):
                hits.append(f"{p}:{node.lineno} {node.func.id}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("run", "Popen", "call", "check_call", "check_output"):
                words = [a.value for a in ast.walk(node) if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                if "pip" in words and "install" in words:
                    hits.append(f"{p}:{node.lineno} pip install")
    assert not hits, hits


def test_the_sandbox_node_is_left_out_when_its_runner_is_not_there(tmp_path):
    code = ("import sys; sys.path.insert(0, sys.argv[1]); from psn import sandbox; sandbox.RUNNER = sys.argv[2]\n"
            "from psn_nodes import logic\n"
            "r = sandbox.run('result = 1')\n"
            "print('PSN_SandboxScript' in logic.NODE_CLASS_MAPPINGS, 'PSN_Expression' in logic.NODE_CLASS_MAPPINGS, r['ok'], 'Registry' in r['error'])")
    out = subprocess.run([sys.executable, "-c", code, str(ROOT), str(tmp_path / "missing.py")], capture_output=True, text=True, timeout=60)
    assert out.stdout.split() == ["False", "True", "False", "True"], out.stderr[-500:]


def test_install_py_does_nothing_when_comfyui_manager_runs_it(tmp_path):
    """ComfyUI-Manager runs `python install.py` from custom_nodes/<pack> after a git (nightly) install, with stdin still on the server's terminal."""
    pack = tmp_path / "ComfyUI" / "custom_nodes" / "comfyui-parametric-studio"
    pack.mkdir(parents=True)
    (pack / "install.py").write_bytes((ROOT / "install.py").read_bytes())
    for name in ("studio", "channels.json"):
        (pack / name).symlink_to(ROOT / name)
    r = subprocess.run([sys.executable, "install.py"], cwd=pack, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60,
                       env={**os.environ, "COMFYUI_PATH": str(tmp_path / "ComfyUI")})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "does nothing when ComfyUI-Manager or comfy-cli runs it" in r.stdout and "Proceed?" not in r.stdout
    assert not (tmp_path / "ComfyUI" / "custom_nodes" / "parametric-studio-runtime").exists()


def test_install_py_still_runs_for_people(tmp_path):
    nodes = tmp_path / "ComfyUI" / "custom_nodes"
    nodes.mkdir(parents=True)
    assert not install.started_by_comfyui(["--dry-run"], env={}, repo=nodes / "x")      # options given: a person ran it
    assert not install.started_by_comfyui([], env={}, repo=tmp_path / "checkout")      # a plain checkout, as INSTALL.md says
    assert install.started_by_comfyui([], env={}, repo=nodes / "x")
    checkout = tmp_path / "checkout"; checkout.mkdir()
    (nodes / "comfyui_parametric_studio").symlink_to(checkout)                        # README's symlinked custom node
    assert install.started_by_comfyui([], env={"COMFYUI_PATH": str(tmp_path / "ComfyUI")}, repo=checkout)
    assert not install.started_by_comfyui([], env={"COMFYUI_PATH": str(tmp_path / "elsewhere")}, repo=checkout)
