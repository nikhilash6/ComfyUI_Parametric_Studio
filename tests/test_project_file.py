"""One-file project: round trip, what never goes in, and what a stranger's file cannot do. ComfyUI is stubbed; no live ports."""
import io, json, os, re, stat, zipfile
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin
from studio import feature_project as P

G = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux2-vae.safetensors"}}, "2": {"class_type": "LoadImage", "inputs": {"image": "start.png"}}, "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": "x"}}}
OI = {"UNETLoader": {"input": {"required": {"unet_name": [["flux2-vae.safetensors"]]}}, "output": ["MODEL"]}, "LoadImage": {"input": {"required": {"image": [["start.png"]]}}, "output": ["IMAGE", "MASK"]}, "SaveImage": {"input": {"required": {"images": ["IMAGE"], "filename_prefix": ["STRING", {"default": "c"}]}}, "output": [], "output_node": True}}


@pytest.fixture
def box(tmp_path, monkeypatch):
    out, inp, models = tmp_path / "out", tmp_path / "in", tmp_path / "models"
    for d in (out, inp, models): d.mkdir()
    monkeypatch.setenv("STUDIO_STATE_DIR", str(tmp_path / "state")); monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(P.paths, "output_dir", lambda *_: str(out)); monkeypatch.setattr(P.paths, "comfy_input", lambda *_: str(inp)); monkeypatch.setattr(P.paths, "models_root", lambda *_: str(models))
    (models / "flux2-vae.safetensors").write_bytes(b"weights" * 800)
    info = PngImagePlugin.PngInfo(); info.add_text("prompt", '{"secret":"x"}'); Image.new("RGB", (4, 4), (1, 2, 3)).save(inp / "start.png", "PNG", pnginfo=info); Image.new("RGB", (4, 4)).save(out / "made.png")
    app = FastAPI(); app.include_router(P.router); c = TestClient(app); c.box = tmp_path; return c


def shot(g=G, **k): return {"id": "a", "label": "A", "goal": "image", "seed": 7, "status": "done", "graph_source": "as it ran", "graph": json.loads(json.dumps(g)), "outputs": [{"filename": "made.png", "type": "output"}], **k}


def pack(box, media=True, g=G):
    m, files, _ = P.build_project("Test", [shot(g)], media); out = box.box / "t.psproject"; P.write_zip(m, files, out); return m, out


def test_round_trip_keeps_graph_seed_model_hash_and_source(box):
    m, out = pack(box); got, media = P.read_project(out); row = got["models"][0]
    assert got["shots"][0]["graph"] == G and got["shots"][0]["seed"] == 7 and len(row["sha256"]) == 64 and "huggingface.co" in row["url"] and sorted(media) == ["made.png", "start.png"] and got["contains"]["weights"] is False


def test_no_weights_ever_go_in(box):
    assert P.media_path("flux2-vae.safetensors", "", "input") is None
    (box.box / "in" / "w.safetensors").write_bytes(b"x")
    assert P.media_path("w.safetensors", "", "input") is None
    _, out = pack(box)
    with zipfile.ZipFile(out) as z:
        assert not [n for n in z.namelist() if P.MODEL_FILE.search(n)] and sum(i.file_size for i in z.infolist()) < 20000


def test_nothing_private_goes_in(box):
    home = str(Path.home())
    g = {**G, "4": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": home + "/secret/run", "note": "/".join(("", "mnt", "disk", "model.safetensors"))}}}
    m, out = pack(box, g=g)
    text = zipfile.ZipFile(out).read("project.json").decode()
    assert home not in text and "/".join(("", "mnt", "")) not in text and not P.leaks(json.loads(text))
    assert "cut down" in " ".join(m["notes"])


def test_it_refuses_rather_than_write_a_leak(box, monkeypatch):
    monkeypatch.setattr(P, "scrub", lambda v, home=None: (v, 0))
    with pytest.raises(P.HTTPException): P.build_project("x", [shot({**G, "9": {"class_type": "N", "inputs": {"p": str(Path.home()) + "/x"}}})])


@pytest.mark.parametrize("text,bad", [("/".join(("", "home", "ann", "a.png")), True), ("C:\\Users\\ann\\a.png", True), ("~/a.png", True), ("a sunset over " + "/".join(("", "mnt", "x")), True), ("loras/style.safetensors", False), ("a dog, 16/9 ratio", False), ("https://huggingface.co/a/b", False)])
def test_what_counts_as_a_path(text, bad):
    assert bool(P.leaks(text, home="/nowhere/person")) is bad


def test_media_metadata_is_removed(box):
    _, out = pack(box)
    with zipfile.ZipFile(out) as z: data = z.read("media/start.png")
    assert b"secret" not in data and not Image.open(io.BytesIO(data)).info.get("prompt")


def test_without_media_it_says_what_was_left_out(box):
    m, out = pack(box, media=False)
    assert zipfile.ZipFile(out).namelist() == ["README.txt", "project.json"] and m["shots"][0]["inputs"][0]["included"] is False


def bad_zip(tmp, members, link=None):
    p = tmp / "bad.psproject"
    with zipfile.ZipFile(p, "w") as z:
        for n, d in members.items(): z.writestr(n, d)
        if link:
            i = zipfile.ZipInfo(link); i.external_attr = (stat.S_IFLNK | 0o777) << 16; z.writestr(i, "/etc/passwd")
    return p


OK = json.dumps({"format": P.FORMAT, "version": 1, "shots": []})


@pytest.mark.parametrize("members,word", [({"x.txt": "a"}, "no project.json"), ({"project.json": "{"}, "cannot be read"), ({"project.json": "{}"}, "not a Parametric"), ({"project.json": OK, "media/../../evil.png": "x"}, "never does"), ({"project.json": OK, "media/run.sh": "x"}, "never does"), ({"project.json": OK, "media/w.safetensors": "x"}, "never does"), ({"project.json": OK, "evil.py": "x"}, "never does"), ({"project.json": json.dumps({"format": P.FORMAT, "version": 99, "shots": []})}, "newer studio")])
def test_a_bad_file_is_refused(tmp_path, members, word):
    with pytest.raises(P.HTTPException) as e: P.read_project(bad_zip(tmp_path, members))
    assert word in e.value.detail


def test_a_link_inside_the_zip_is_refused(tmp_path):
    with pytest.raises(P.HTTPException) as e: P.read_project(bad_zip(tmp_path, {"project.json": OK}, link="media/a.png"))
    assert "link" in e.value.detail


def test_not_a_zip(tmp_path):
    p = tmp_path / "a.psproject"; p.write_text("hello")
    with pytest.raises(P.HTTPException): P.read_project(p)


def open_it(box, out, oi=OI, monkeypatch=None):
    with open(out, "rb") as f: return box.post("/api/project/open", files={"file": ("x.psproject", f)})


def stub_comfy(monkeypatch, oi=OI, sent=None):
    def fake(path, payload=None, timeout=30):
        if path == "/object_info": return oi
        if path == "/prompt": sent.append(payload) if sent is not None else None; return {"prompt_id": "abc"}
        return {}
    monkeypatch.setattr(P, "_comfy", fake)


def test_opening_says_what_is_missing(box, monkeypatch):
    _, out = pack(box, media=False); stub_comfy(monkeypatch)
    from studio import recipe_check as C
    monkeypatch.setattr(C, "model_files", lambda *a, **k: {})
    (box.box / "in" / "start.png").unlink()
    d = open_it(box, out).json(); s = d["report"]["shots"][0]
    assert s["ready"] is False and any("start.png" in p for p in s["problems"]) and any("not on disk" in p for p in s["problems"]) and d["report"]["missing_models"] == ["flux2-vae.safetensors"] and "huggingface.co" in d["report"]["models"][0]["url"]


def test_comfy_away_checks_nothing_and_says_so(box, monkeypatch):
    _, out = pack(box); d = open_it(box, out).json()
    assert d["report"]["comfy_up"] is False and d["report"]["shots"][0]["ready"] is False and "not checked" in d["report"]["shots"][0]["problems"][0]


def ready(box, monkeypatch, sent=None):
    _, out = pack(box); stub_comfy(monkeypatch, sent=sent)
    from studio import recipe_check as C
    monkeypatch.setattr(C, "model_files", lambda *a, **k: {"flux2-vae.safetensors": 1})
    return open_it(box, out).json()


def test_a_ready_shot_renders_only_on_a_click(box, monkeypatch):
    sent = []; d = ready(box, monkeypatch, sent); assert d["report"]["shots"][0]["ready"] and not sent, "opening a file must not render it"
    from studio import server as S
    monkeypatch.setattr(S, "_upload", lambda data, fn, ct: {"name": "studio_new.png"})
    assert box.post(f"/api/project/open/{d['id']}/render", json={"shot": "a"}).status_code == 400 and not sent
    r = box.post(f"/api/project/open/{d['id']}/render", json={"shot": "a", "confirm": True}); assert r.status_code == 200 and sent[0]["prompt"]["2"]["inputs"]["image"] == "studio_new.png"


def test_a_strangers_save_path_blocks_the_shot(box, monkeypatch):
    g = json.loads(json.dumps(G)); g["3"]["inputs"]["filename_prefix"] = "../../../.config/x"
    m, _, _ = P.build_project("x", [shot(g)]); out = box.box / "s.psproject"; P.write_zip(m, [], out); stub_comfy(monkeypatch)
    from studio import recipe_check as C
    monkeypatch.setattr(C, "model_files", lambda *a, **k: {"flux2-vae.safetensors": 1})
    d = open_it(box, out).json(); assert d["report"]["shots"][0]["ready"] is False and "outside the output folder" in " ".join(d["report"]["shots"][0]["problems"])
    assert box.post(f"/api/project/open/{d['id']}/render", json={"shot": "a", "confirm": True}).status_code == 409


def test_board_shots_prefer_the_graph_that_ran(monkeypatch):
    monkeypatch.setattr(P, "graph_as_ran", lambda j: {"1": {"class_type": "X", "inputs": {}}} if j == "yes" else None); monkeypatch.setattr(P, "rebuild", lambda b: {"2": {"class_type": "Y", "inputs": {"seed": b["seed"]}}})
    s = P.board_shots({"jobs": [{"id": "r", "job": "yes", "seed": 1, "body": {"goal": "image"}}, {"id": "n", "seed": 2, "body": {"goal": "image"}}, {"id": "u", "body": {"goal": "image"}}, "junk"]})
    assert s[0]["graph_source"] == "as it ran" and s[1]["graph_source"] == "rebuilt from the board" and s[1]["graph"]["2"]["inputs"]["seed"] == 2 and s[2]["graph"] is None


def test_nothing_to_pack_is_said(box):
    import time
    jid = box.post("/api/project/export", json={"board": {"jobs": []}}).json()["id"]
    for _ in range(50):
        j = box.get("/api/project/export/" + jid).json()
        if j["state"] != "working": break
        time.sleep(0.05)
    assert j["state"] == "error" and "nothing to pack" in j["error"] and "path" not in j


def test_page():
    web = Path(P.__file__).parent / "web"; js = (web / "project.js").read_text()
    assert "Never in the file" in js and "—" not in js and "confirm: true" in js and "#project" in (web / "shotboard_view.js").read_text()
