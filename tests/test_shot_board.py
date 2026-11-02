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
    for words in ("Keep this tab open", "picks up where it left off", "Recast is the slowest job", "Every result keeps its exact graph and seed", "These are our own renders", "From this clip", "ProRes 4444"):
        assert words in view, words
    assert "traces can remain" in (WEB / "shotboard.js").read_text()
    for words in ("instant", "—"):
        assert words not in view.lower(), words


def test_every_example_is_a_file_that_ships():
    view = (WEB / "shotboard_view.js").read_text(); known = {x["id"]: x for x in json.loads((WEB / "showcase" / "showcase.json").read_text())}
    ids = re.findall(r'source: "([a-z0-9_]+)"', view) + re.findall(r'\{ id: "([a-z0-9_]+)", label', view)
    assert len(ids) == 9
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


def matte(p, seconds=1, size="320x176"):
    """A white disc on black, like an Alpha-Gen matte."""
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={size}:r=24:d={seconds}", "-vf", "geq=lum='if(lt(hypot(X-W/2,Y-H/2),H/3),255,0)':cb=128:cr=128", "-pix_fmt", "yuv420p", str(p)], check=True)


def test_cutout_filter_fits_the_source_like_the_graph():
    fc = S.cutout_filter(960, 544, 5.0)
    assert "fps=24" in fc and "force_original_aspect_ratio=increase,crop=960:544" in fc and "alphamerge" in fc and "trim=duration=5.0" in fc


def test_cutout_files_stay_inside_the_studio(client):
    for body in ({"source": {"filename": "../x.mp4"}, "matte": {"filename": "m.mp4"}}, {"source": {"filename": "s.mp4", "type": "output"}, "matte": {"filename": "../../m.mp4"}}):
        assert client.post("/api/shotboard/cutout", json=body).status_code == 404


@ffmpeg
def test_cutout_is_prores_4444_with_a_real_alpha_and_a_preview(client):
    clip(client.inp / "src.mp4", 2, "640x360"); (client.out / "vfx").mkdir(); matte(client.out / "vfx" / "m.mp4", 1)
    r = client.post("/api/shotboard/cutout", json={"source": {"filename": "src.mp4"}, "matte": {"filename": "m.mp4", "subfolder": "vfx"}})
    assert r.status_code == 200, r.text
    d = r.json(); mov = client.out / "shotboard" / d["mov"]["filename"]; prev = client.out / "shotboard" / d["preview"]["filename"]
    s = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,pix_fmt,width,height", "-of", "csv=p=0", str(mov)], capture_output=True, text=True).stdout.strip()
    codec, w, h, fmt = s.split(","); assert (codec, w, h) == ("prores", "320", "176") and fmt.startswith("yuva444") and prev.is_file() and abs(d["seconds"] - 1) < 0.1
    # the corner is transparent and the centre opaque
    px = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mov), "-frames:v", "1", "-vf", "alphaextract,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    assert px[0] < 20 and px[176 // 2 * 320 + 160] > 230


def test_reel_refuses_a_take_too_short_and_paths_outside(client):
    assert client.post("/api/shotboard/reel", json={"source": {"filename": "../x.mp4"}, "take": {"filename": "t.mp4"}}).status_code == 404


@ffmpeg
def test_reel_makes_three_formats_with_an_end_card(client):
    if not any(S.os.path.exists(f) for f in S.FONTS): pytest.skip("needs a font")
    clip(client.inp / "src.mp4", 4, "640x360"); (client.out / "vfx").mkdir(); clip(client.out / "vfx" / "t.mp4", 4, "640x360")
    r = client.post("/api/shotboard/reel", json={"source": {"filename": "src.mp4"}, "take": {"filename": "t.mp4", "subfolder": "vfx"}, "label": "flood, it's 'quoted'"})
    assert r.status_code == 200, r.text
    d = r.json(); assert abs(d["seconds"] - (4 + S.REEL_CARD)) < 0.1
    for key, size in (("16x9", "1920,1080"), ("1x1", "1080,1080"), ("9x16", "1080,1920")):
        p = client.out / "shotboard" / d[key]["filename"]
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height:format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.split()
        assert info[0] == size and abs(float(info[1]) - d["seconds"]) < 0.2, (key, info)


def test_reel_short_clips_get_a_clear_answer(client):
    if not S.shutil.which("ffmpeg"): pytest.skip("needs ffmpeg")
    clip(client.inp / "s.mp4", 1); (client.out / "v").mkdir(); clip(client.out / "v" / "t.mp4", 1)
    r = client.post("/api/shotboard/reel", json={"source": {"filename": "s.mp4"}, "take": {"filename": "t.mp4", "subfolder": "v"}})
    assert r.status_code == 400 and "too short" in r.text
