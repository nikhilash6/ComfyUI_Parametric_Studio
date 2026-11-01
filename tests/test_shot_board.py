"""Shot Board's export: paths stay inside the studio's folders, the grid is right, and a real ffmpeg run gives a video. No ComfyUI or GPU."""
import shutil
import subprocess
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from studio import shot_board as S

ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def clip(p, seconds=1, size="320x180"):
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=d={seconds}:s={size}:r=24", "-pix_fmt", "yuv420p", str(p)], check=True)


@pytest.fixture
def client(tmp_path, monkeypatch):
    out, inp = tmp_path / "out", tmp_path / "in"; out.mkdir(); inp.mkdir()
    monkeypatch.setattr(S.paths, "output_dir", lambda *_: str(out)); monkeypatch.setattr(S.paths, "comfy_input", lambda *_: str(inp))
    app = FastAPI(); app.include_router(S.router); c = TestClient(app); c.out, c.inp = out, inp; return c


@pytest.mark.parametrize("n,grid", [(2, (2, 1)), (4, (2, 2)), (5, (3, 2)), (8, (3, 3)), (16, (4, 4))])
def test_grid(n, grid): assert S.grid_for(n) == grid


def test_filter_layout_and_captions_are_files_not_text():
    fc, last = S.build_filter(3, 2.0, ["/tmp/a", "/tmp/b", "/tmp/c"])
    assert last == "[out]" and "xstack=inputs=3" in fc and "0_0|640_0|0_360" in fc and "tpad=stop_mode=clone" in fc


def test_needs_two_clips(client): assert client.post("/api/shotboard/export", json={"items": []}).status_code == 400


@pytest.mark.parametrize("item,code", [({"filename": "../../etc/passwd"}, 404), ({"filename": "x.mp4", "subfolder": "../.."}, 404), ({"filename": "x.mp4", "type": "temp"}, 400), ({"nope": 1}, 400)])
def test_rejects_paths_outside_the_studio(client, item, code):
    with pytest.raises(HTTPException) as e: S.resolve_item(item)
    assert e.value.status_code == code


@ffmpeg
def test_exports_a_captioned_video_with_awkward_labels(client):
    clip(client.inp / "src.mp4", 2); (client.out / "a").mkdir(); clip(client.out / "a" / "one.mp4", 1, "180x320")
    r = client.post("/api/shotboard/export", json={"items": [{"filename": "src.mp4", "type": "input", "label": "Source: it's 100% 'quoted'"}, {"filename": "one.mp4", "subfolder": "a", "label": "VFX: a,b;c"}]})
    assert r.status_code == 200, r.text
    d = r.json(); p = client.out / d["subfolder"] / d["filename"]
    info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height:format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.split()
    assert info[0] == "1280,360" and abs(float(info[1]) - 2) < 0.2


def test_opened_graphs_stay_pinned_in_pro():
    src = (S.Path(__file__).parent.parent / "studio" / "web" / "app.js").read_text()
    assert "setPinned(e.detail)" in src and "<${Pro} draft=${pinned || draft}" in src and "setDraft(e.detail)" not in src


def test_a_job_result_is_never_its_uploaded_source():
    src = (S.Path(__file__).parent.parent / "studio" / "web" / "shotboard.js").read_text()
    assert 'f.type !== "input"' in src and "/^studio_/" in src
