"""The 3D page: real meshes, labels that say whose they are, numbers read from the file, and family meshes behind a path check. No live ports."""
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from psn import instances as I
from studio import server

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"
JS = (WEB / "studio3d.js").read_text()


def test_shelf_files_exist_and_stay_small():
    rows = json.loads((WEB / "mesh_art" / "index.json").read_text())
    assert len(rows) >= 4
    for r in rows:
        f = WEB / "mesh_art" / r["file"]
        assert f.is_file() and f.read_bytes()[:4] == b"glTF", r["id"]
        assert (WEB / "mesh_art" / r["thumb"]).is_file(), r["id"]
    assert sum(p.stat().st_size for p in (WEB / "mesh_art").iterdir()) < 6_500_000


def test_labels_and_honest_notes_stay():
    for word in ("Our test build", "does not know its real size", "not your work", "from its build record", "Clay", "Wireframe", "Normals", "Textured", "prefers-reduced-motion"):
        assert word in JS, word
    assert "Math.random" not in JS


@pytest.fixture
def instances(tmp_path, monkeypatch):
    d = tmp_path / "bear-family" / "output" / "3d"; d.mkdir(parents=True); (d / "bear.glb").write_bytes(b"glTF....")
    (tmp_path / "secret.glb").write_bytes(b"glTF....")
    monkeypatch.setattr(I, "INSTANCES", str(tmp_path))
    return tmp_path


def test_family_meshes_are_listed(instances):
    rows = server._family_glbs()
    assert [r["family"] for r in rows] == ["bear-family"] and rows[0]["url"].startswith("/api/family3d?")


def test_family_mesh_is_served(instances):
    assert str(server.family3d("bear-family", "3d/bear.glb").path).endswith("bear.glb")


@pytest.mark.parametrize("family,path", [("bear-family", "../../secret.glb"), ("..", "secret.glb"), ("bear-family", "3d/nope.glb"), ("no-such", "3d/bear.glb"), ("bear-family", "../output/3d/bear.txt")])
def test_family_mesh_path_is_checked(instances, family, path):
    with pytest.raises(HTTPException):
        server.family3d(family, path)
