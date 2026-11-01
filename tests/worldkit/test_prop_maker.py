from pathlib import Path

import pytest
from PIL import Image

from studio.worldkit import library as L, steps as S
from studio.worldkit.makers import prop as P
from tests.worldkit.helpers import ctx_for, glb_file


def test_default_sizes_come_from_the_name():
    assert P.default_size("Red sports car") == 4.5 and P.default_size("two wooden chairs") == 0.9
    assert P.default_size("a strange sculpture") == 1.0
    assert P.recipe({"size_m": 50}, "x")[1] and P.recipe(None, "office desk") == ({"size_m": 1.4}, [])


def test_source_problems():
    assert P.source_problem({"kind": "text", "prompt": "a red chair"}) == ""
    assert P.source_problem({"kind": "image", "image": "chair.png"}) == ""
    assert P.source_problem({"kind": "mesh", "mesh": "runs/a.glb"}) == ""
    assert "describe" in P.source_problem({"kind": "text", "prompt": " "})
    assert "image" in P.source_problem({"kind": "image"})
    assert P.source_problem({"kind": "brief"}).startswith("a prop is made from")


class FakeBlender:
    def __init__(self):
        self.calls = []

    def run(self, script, payload, **kw):
        self.calls.append((script, payload, kw))
        Path(payload["out"]).write_bytes(b"glTF")
        return {"ok": True, "inspect": {"loaded": True, "dims_m": [4.5, 1.8, 1.4], "colliders": 1, "bones": []}}


class Studio:
    def __init__(self, tmp_path):
        self.reqs, self.tmp = [], tmp_path

    def submit(self, req):
        self.reqs.append(req)
        return f"j{len(self.reqs)}"

    def wait(self, jid):
        req = self.reqs[int(jid[1:]) - 1]
        p = self.tmp / f"{jid}.png"
        Image.new("RGBA" if req["kind"] == "graph" else "RGB", (16, 16), (200, 0, 0, 120) if req["kind"] == "graph" else (200, 0, 0)).save(p)
        return {"status": "done", "error": "", "artifacts": [{"path": str(p), "media_type": "image"}]}


def _input_picture(tmp_path, name="chair.png", mode="RGB"):
    d = tmp_path / "input"
    d.mkdir(exist_ok=True)
    Image.new(mode, (16, 16), (10, 20, 30, 100) if mode == "RGBA" else (10, 20, 30)).save(d / name)
    return name


def _run(tmp_path, source, recipe=None):
    lib = L.Library()
    meta = lib.create(L.new_meta("prop", "Red chair", source=source, recipe=recipe))
    st, fb, sam = Studio(tmp_path), FakeBlender(), []

    def sam3d(pic, work):
        sam.append(pic)
        return glb_file(Path(work) / "object.glb")
    ctx = ctx_for(lib, meta, tmp_path, blender=fb, sam3d=sam3d, mesh_route=lambda: "sam3d_objects", to_input=lambda p: Path(p).name, submit=st.submit, wait=st.wait)
    return meta, st, fb, sam, S.run({}, P.steps(meta), ctx=ctx, submit=st.submit, wait=st.wait, save=lambda s: None)


def _models(tmp_path, monkeypatch):
    from studio.worldkit import tools
    monkeypatch.setattr(tools, "require", lambda key: None)


def test_a_text_prop_makes_a_picture_then_a_cutout_then_a_mesh(tmp_path, monkeypatch):
    _models(tmp_path, monkeypatch)
    meta, st, fb, sam, state = _run(tmp_path, {"kind": "text", "prompt": "a red velvet armchair"})
    assert state["state"] == "done", state["error"]
    assert [r["kind"] for r in st.reqs] == ["goal", "graph"] and st.reqs[0]["goal"] == "image"
    assert st.reqs[0]["prompt"].startswith("a red velvet armchair, a single object")
    assert st.reqs[1]["template"] == P.CUTOUT_GRAPH and st.reqs[1]["values"] == {"image": "j1.png"}
    assert sam == [str(tmp_path / "j2.png")]                                   # the mesh model gets the cut-out, never the plain picture
    assert fb.calls[0][0] == "wk_cleanup.py" and fb.calls[0][1]["model"].endswith("object.glb") and fb.calls[0][1]["size_m"] == 0.9 and fb.calls[0][2]["gpu"] is False


def test_a_picture_skips_the_text_step_and_one_with_its_own_cutout_skips_the_cutout(tmp_path, monkeypatch):
    _models(tmp_path, monkeypatch)
    _, st, _, _, state = _run(tmp_path, {"kind": "image", "image": _input_picture(tmp_path)})
    assert state["state"] == "done" and [r["kind"] for r in st.reqs] == ["graph"] and state["steps"][0]["status"] == "skipped"
    _, st, _, sam, state = _run(tmp_path, {"kind": "image", "image": _input_picture(tmp_path, "cut.png", "RGBA")})
    assert state["state"] == "done" and st.reqs == [] and sam[0].endswith("cut.png")


def test_a_mesh_from_the_studio_goes_straight_to_the_cleanup(tmp_path):
    glb_file(tmp_path / "output" / "runs" / "a.glb")
    _, st, fb, _, state = _run(tmp_path, {"kind": "mesh", "mesh": "runs/a.glb"})
    assert state["state"] == "done" and st.reqs == []
    assert [r["name"] for r in state["steps"] if r["status"] == "skipped"] == ["image", "cutout", "mesh"]
    assert fb.calls[0][1]["model"] == str((tmp_path / "output" / "runs" / "a.glb").resolve())


def test_a_mesh_path_cannot_leave_the_output_folder(tmp_path):
    glb_file(tmp_path / "secret.glb")
    _, _, _, _, state = _run(tmp_path, {"kind": "mesh", "mesh": "../secret.glb"})
    assert state["state"] == "failed" and "not a usable file" in state["error"]
    pic = tmp_path / "elsewhere.png"
    Image.new("RGB", (4, 4)).save(pic)
    with pytest.raises(S.StepError):
        P.picture_path("../elsewhere.png")


def test_a_missing_model_stops_the_step_with_a_plain_sentence(tmp_path):
    meta = L.new_meta("prop", "Red chair", source={"kind": "text", "prompt": "a red chair"})
    lib = L.Library()
    lib.create(meta)
    state = S.run({}, P.steps(meta), ctx=ctx_for(lib, meta, tmp_path), submit=None, wait=None, save=lambda s: None)
    assert state["state"] == "failed" and "still downloading or missing" in state["error"] and state["error"].startswith("Image")


def test_the_mesh_step_says_what_is_missing_when_no_route_is_ready(tmp_path, monkeypatch):
    from studio.worldkit import capabilities as C
    monkeypatch.setattr(C, "MESH_ROUTES", ("sam3d_objects",))             # family routes read the box's shared model list: keep this test off it
    glb = {"kind": "image", "image": _input_picture(tmp_path, "cut.png", "RGBA")}
    lib = L.Library()
    meta = lib.create(L.new_meta("prop", "x", source=glb))
    state = S.run({}, P.steps(meta), ctx=ctx_for(lib, meta, tmp_path, mesh_route=lambda: ""), submit=None, wait=None, save=lambda s: None)
    assert state["state"] == "failed" and state["error"].startswith("Mesh") and "no model ready" in state["error"]


def test_a_family_route_runs_through_the_job_seam(tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("prop", "x", source={"kind": "image", "image": _input_picture(tmp_path, "cut.png", "RGBA")}))
    reqs = []
    out = glb_file(tmp_path / "fam.glb")

    def submit(req):
        reqs.append(req)
        return "pixal3d/fam-1"
    ctx = ctx_for(lib, meta, tmp_path, blender=FakeBlender(), mesh_route=lambda: "pixal3d", submit=submit, wait=lambda j: {"status": "done", "artifacts": [{"path": out, "media_type": "file"}]})
    state = S.run({}, P.steps(meta), ctx=ctx, submit=submit, wait=ctx["wait"], save=lambda s: None)
    assert state["state"] == "done" and reqs[0]["kind"] == "family" and reqs[0]["family"] == "Pixal3D" and reqs[0]["image"].endswith("cut.png")


def test_recipe_keeps_as_prop_of_and_rejects_a_bad_one():
    assert P.recipe({"as_prop_of": " c1 "}, "chair") == ({"size_m": 0.9, "as_prop_of": "c1"}, [])
    assert P.recipe({"as_prop_of": ""}, "chair")[1] and P.recipe({"as_prop_of": 5}, "chair")[1]
