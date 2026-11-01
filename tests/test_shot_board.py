"""Shot Board's export: paths stay inside the studio's folders, the grid is right, and a real ffmpeg run gives a video. No ComfyUI or GPU."""
import io
import json
import re
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


WEB = S.Path(__file__).parent.parent / "studio" / "web"
PAGE = ("shotboard.js", "shotboard_view.js", "shotboard_film.js", "shotboard.css")


def test_the_page_loads_nothing_from_outside():
    html = (WEB / "index.html").read_text()
    assert 'href="shotboard.css"' in html
    for name in PAGE:
        assert not re.search(r"https?://(?!www\.w3\.org/)|//cdn\.|@import", (WEB / name).read_text()), name


def test_the_honest_notes_stay_on_the_page():
    view = (WEB / "shotboard_view.js").read_text()
    for words in ("Keep this tab open", "picks up where it left off", "Recast is the slowest job", "Every result keeps its exact graph and seed", "These are our own renders", "From another clip"):
        assert words in view, words
    assert "traces can remain" in (WEB / "shotboard.js").read_text()
    for words in ("instant", "—"):
        assert words not in view.lower(), words


def test_every_example_is_a_file_that_ships():
    view = (WEB / "shotboard_view.js").read_text(); known = {x["id"]: x for x in json.loads((WEB / "showcase" / "showcase.json").read_text())}
    ids = re.findall(r'(?:source: |id: )"([a-z0-9_]+)"', view)
    assert len(ids) == 5
    for i in ids:
        assert i in known and known[i]["kind"] == "video" and (WEB / "showcase" / f"{i}.mp4").exists() and (WEB / "showcase" / f"{i}.webp").exists()


def test_the_recast_time_on_the_page_matches_the_recorded_render():
    recast = next(x for x in json.loads((WEB / "showcase" / "showcase.json").read_text()) if x["id"] == "recast_chef")
    assert 8.5 <= recast["seconds"] / 60 <= 9.5 and recast["options"]["seconds"] == 5


@pytest.mark.parametrize("header,forwarded,status", [("bytes=0-9", "bytes=0-9", 206), (None, None, 200), ("bytes=0-9\r\nX: y", None, 200), ("items=1-2", None, 200)])
def test_view_passes_byte_ranges_so_videos_can_scrub(monkeypatch, header, forwarded, status):
    from studio import server
    seen = {}
    class Answer(io.BytesIO):
        def __init__(self, status):
            super().__init__(b"0123456789"); self.status = status
            self.headers = {"Content-Type": "video/mp4", "Accept-Ranges": "bytes", "Content-Length": "10", **({"Content-Range": "bytes 0-9/99"} if status == 206 else {})}
    def fake(req, timeout=None):
        seen["range"] = req.get_header("Range"); return Answer(206 if seen["range"] else 200)
    monkeypatch.setattr(server.urllib.request, "urlopen", fake)
    r = TestClient(server.app).get("/api/view?filename=a.mp4", headers={"Range": header.replace("\r\n", " ")} if header else {})
    assert seen["range"] == (forwarded if header != "bytes=0-9\r\nX: y" else None) and r.status_code == status and r.headers["accept-ranges"] == "bytes" and r.content == b"0123456789"
    if status == 206: assert r.headers["content-range"] == "bytes 0-9/99"
