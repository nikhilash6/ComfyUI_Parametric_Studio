"""Every model file the repository uses has a download row, and scripts/get_models.py plans and fetches them without touching a real account or the network.

The manifest's "files" list is written by scripts/build_model_links.py from studio/model_inventory.py. If a graph gains a model, the first test fails until
that script is run again. The helper tests stub the network: a dry run must not open a socket, and a real run goes through a fake opener."""
import hashlib
import io
import json
import re
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from studio import model_inventory as mi  # noqa: E402
import get_models  # noqa: E402

MAN = json.loads((ROOT / "studio" / "models_manifest.json").read_text(encoding="utf-8"))
FILES = {f["filename"]: f for f in MAN["files"]}


def test_every_graph_model_file_is_in_the_manifest():
    missing = []
    for rel in mi.graph_files(ROOT):
        doc = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        for name, _folder in mi.graph_uses(doc):
            if mi.key_for(name) not in FILES: missing.append((rel, name))
    assert not missing, f"{len(missing)} graph model files have no manifest row; run scripts/build_model_links.py: {missing[:10]}"


def test_every_used_file_is_in_the_manifest_with_its_users():
    inv = mi.inventory(ROOT)
    assert set(inv) <= set(FILES), sorted(set(inv) - set(FILES))[:20]
    for key, row in inv.items():
        assert row["used_by"] <= set(FILES[key]["used_by"]), key


def test_the_inventory_reads_every_kind_of_source():
    users = {u.split(":")[0] if ":" in u else u.split("/")[0] for f in MAN["files"] for u in f["used_by"]}
    for kind in ("workflows", "studio", "family", "goal", "lora-recipe", "music", "voice", "feature"): assert kind in users, kind
    assert len(mi.graph_files(ROOT)) > 500


def test_rows_carry_link_size_hash_licence_and_folder():
    need = {"filename", "folder", "url", "size", "sha256", "licence", "gated", "used_by", "source", "family", "dest"}
    for f in MAN["files"]:
        assert need <= set(f), (f["filename"], need - set(f))
        assert f["used_by"], f["filename"]
        if f["source"] == "huggingface":
            assert re.match(r"^https://huggingface\.co/[\w.-]+/[\w.-]+/resolve/main/\S+$", f["url"]), f["url"]
            assert isinstance(f["size"], int) and f["size"] > 0, f["filename"]
            assert f["sha256"] is None or re.fullmatch(r"[0-9a-f]{64}", f["sha256"]), f["filename"]
            assert f["licence"] and f["licence_url"].startswith("https://"), f["filename"]
            assert isinstance(f["gated"], bool) and isinstance(f["noncommercial"], bool)
            if f["dest"]: assert f["dest"].split("/")[0] in mi.KNOWN_FOLDERS, (f["filename"], f["dest"])
            else: assert f["where"] and all(u.startswith(("feature:", "music:", "voice:")) for u in f["used_by"]), f["filename"]
        elif f["source"] == "github":
            assert f["url"].startswith("https://github.com/") and "/releases/download/" in f["url"] and f["size"] and f["dest"].split("/")[0] in mi.KNOWN_FOLDERS, f["filename"]
        elif f["source"] == "modelscope":
            assert f["url"].startswith("https://modelscope.cn/models/") and re.fullmatch(r"[0-9a-f]{64}", f["sha256"]), f["filename"]
        else:
            assert f["note"] and f["source"] in ("none", "civitai", "other", "trained here"), f["filename"]
            if f.get("civitai_url"):
                assert re.match(r"^https://civitai\.com/models/\d+\?modelVersionId=\d+$", f["civitai_url"]) and f["civitai_checked"] in ("SHA-256", "file name and size")
    hf = sum(1 for f in MAN["files"] if f["source"] == "huggingface")
    assert hf / len(MAN["files"]) > 0.7


def test_the_goal_files_keep_their_published_hashes():
    for goal in MAN["goals"].values():
        for g in goal["files"]:
            row = FILES[Path(g["path"]).name]               # the repo may have been renamed since (Hugging Face redirects the old name), so compare the bytes
            assert row["source"] == "huggingface" and Path(row["path"]).name == Path(g["path"]).name, (g["path"], row.get("repo"))
            if g.get("sha256"): assert row["sha256"] == g["sha256"], g["path"]


def test_no_machine_paths_or_secrets_in_the_rows():
    text = json.dumps(MAN["files"])
    for bad in ("/mnt/", "/home/", "_complete_pipelines", "_by_repo", "_libraries/", "token="):
        assert bad not in text, bad
    assert not re.search(r"hf_[A-Za-z0-9]{30,}", text)


def test_models_md_is_generated_from_the_manifest():
    import build_model_links as b
    md = (ROOT / "MODELS.md").read_text(encoding="utf-8")
    assert b.models_md_section(MAN["files"], MAN["files_built"]) in md
    for fam in {f["family"] for f in MAN["files"]}: assert f"### {fam}\n" in md, fam


def test_the_installers_and_readme_point_at_the_helper():
    ps1 = (ROOT / "scripts" / "install_windows.ps1").read_text(encoding="utf-8")
    assert "get_models.py" in ps1 and "--dry-run" in ps1[ps1.index("get_models.py"):] and "-Models" in ps1
    assert "scripts/get_models.py" in (ROOT / "README.md").read_text(encoding="utf-8")


# ---------- the download helper, offline


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*a, **k): raise AssertionError("the network was touched")
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(get_models.resumable.urllib.request, "urlopen", refuse)
    monkeypatch.delenv("HF_TOKEN", raising=False)


def test_dry_run_plans_a_goal_offline(tmp_path, capsys, no_network):
    assert get_models.main(["--for", "image", "--dry-run", "--models-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "flux-2-klein-4b.safetensors" in out and "3 to download" in out
    assert not any(tmp_path.iterdir())


def test_dry_run_for_all_and_a_family_and_a_graph(tmp_path, capsys, no_network):
    assert get_models.main(["--for", "all", "--dry-run", "--models-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "with no public source" in out and "gated and skipped" in out
    assert get_models.main(["--for", "family:Anima", "--dry-run", "--models-dir", str(tmp_path)]) == 0
    assert "anima" in capsys.readouterr().out.lower()
    assert get_models.main(["--for", "workflows/music3_api", "--dry-run", "--models-dir", str(tmp_path)]) == 0
    assert "minimax_music3_dit_fp16.safetensors" in capsys.readouterr().out
    assert get_models.main(["--for", "no-such-thing", "--dry-run", "--models-dir", str(tmp_path)]) == 2
    assert get_models.main(["--list"]) == 0


class _Resp(io.BytesIO):
    def __init__(self, data, start=0):
        super().__init__(data[start:])
        self.status = 206 if start else 200
        self.headers = {"Content-Length": str(len(data) - start)} | ({"Content-Range": f"bytes {start}-{len(data) - 1}/{len(data)}"} if start else {})


def _fake_manifest(tmp_path, data, gated=False):
    row = {"filename": "tiny.safetensors", "folder": "loras", "dest": "loras/tiny.safetensors", "url": "https://huggingface.co/acme/tiny/resolve/main/tiny.safetensors",
           "repo": "acme/tiny", "path": "tiny.safetensors", "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "licence": "apache-2.0",
           "licence_url": "https://huggingface.co/acme/tiny", "noncommercial": False, "gated": gated, "used_by": ["goal:tiny"], "family": "Tiny", "source": "huggingface"}
    none = {"filename": "lost.safetensors", "folder": "loras", "dest": "loras/lost.safetensors", "url": None, "size": None, "sha256": None, "licence": None,
            "gated": None, "used_by": ["goal:tiny"], "family": "Tiny", "source": "none", "note": "no public source found"}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"goals": {"tiny": {"files": []}}, "files": [row, none]}))
    return p


def test_download_resumes_checks_the_hash_and_skips_what_exists(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    data = bytes(range(256)) * 64
    man = _fake_manifest(tmp_path, data)
    models = tmp_path / "models"
    (models / "loras").mkdir(parents=True)
    (models / "loras" / "tiny.safetensors.part").write_bytes(data[:1000])      # an earlier run stopped here
    seen = []

    def opener(req):
        seen.append((req.full_url, dict(req.header_items())))
        rng = req.get_header("Range")
        return _Resp(data, int(rng.split("=")[1].rstrip("-")) if rng else 0)

    assert get_models.main(["--for", "tiny", "--models-dir", str(models), "--manifest", str(man)], opener=opener) == 0
    assert (models / "loras" / "tiny.safetensors").read_bytes() == data
    assert seen[0][1].get("Range") == "bytes=1000-" and "Authorization" not in seen[0][1]
    assert get_models.main(["--for", "tiny", "--models-dir", str(models), "--manifest", str(man)], opener=opener) == 0
    assert len(seen) == 1 and "1 already in place" in capsys.readouterr().out


def test_a_bad_hash_is_thrown_away(tmp_path, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    data = b"x" * 5000
    man = _fake_manifest(tmp_path, data)
    models = tmp_path / "models"
    assert get_models.main(["--for", "tiny", "--models-dir", str(models), "--manifest", str(man)], opener=lambda req: _Resp(b"y" * 5000)) == 1
    assert not (models / "loras" / "tiny.safetensors").exists() and not (models / "loras" / "tiny.safetensors.part").exists()


def test_gated_needs_a_token_from_the_environment_only(tmp_path, capsys, monkeypatch):
    data = b"z" * 2048
    man = _fake_manifest(tmp_path, data, gated=True)
    models = tmp_path / "models"
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert get_models.main(["--for", "tiny", "--models-dir", str(models), "--manifest", str(man)], opener=lambda req: pytest.fail("fetched without a token")) == 0
    assert "gated" in capsys.readouterr().out
    monkeypatch.setenv("HF_TOKEN", "test-token-not-real")
    seen = []
    assert get_models.main(["--for", "tiny", "--models-dir", str(models), "--manifest", str(man)], opener=lambda req: seen.append(req.get_header("Authorization")) or _Resp(data)) == 0
    assert seen == ["Bearer test-token-not-real"]
    gh = json.loads(man.read_text()); gh["files"][0].update(url="https://github.com/acme/tiny/releases/download/v1/tiny.safetensors", source="github", gated=False)
    man.write_text(json.dumps(gh)); (models / "loras" / "tiny.safetensors").unlink()
    seen.clear()
    assert get_models.main(["--for", "tiny", "--models-dir", str(models), "--manifest", str(man)], opener=lambda req: seen.append(req.get_header("Authorization")) or _Resp(data)) == 0
    assert seen == [None]                                    # never sent anywhere but Hugging Face
    assert "test-token-not-real" not in "".join(p.read_text(errors="ignore") for p in tmp_path.rglob("*") if p.is_file() and p.suffix in (".json", ".txt"))
