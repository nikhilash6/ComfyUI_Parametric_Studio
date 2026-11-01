import numpy as np
import pytest
from PIL import Image

from studio.worldkit import library as L, looks, steps as S, textures
from studio.worldkit.makers import place as PL
from tests.worldkit.helpers import ctx_for, glb_file


def test_looks_resolve_presets_with_time_and_weather():
    assert looks.problems("golden_hour") == [] and looks.problems("disco")
    assert looks.problems("day_clear", time="noonish") and looks.problems("day_clear", weather="snow")
    rain = looks.resolve("day_clear", weather="rain")
    assert rain["wet"] > 0.5 and rain["fog"] > 0 and rain["sun"] is None and rain["weather"] == "rain"
    night = looks.resolve("golden_hour", time="night")
    assert night["night"] is True and night["sun"] is None and night["world"] == "night"
    assert looks.resolve("interior_day", time="night")["world"] == "interior"
    assert {x["id"] for x in looks.public()} == set(looks.LOOKS)


def test_plan_reads_kit_time_and_weather_from_the_brief():
    r = PL.plan("rainy downtown block at night")
    assert (r["kit"], r["time"], r["weather"]) == ("street", "night", "rain")
    assert r["look"] == {"preset": "rainy", "time": "night", "weather": "rain"} and "wet" in r["materials"]["ground"]
    cafe = PL.plan("cosy beach café interior, golden hour")
    assert cafe["kit"] == "interior" and cafe["look"]["preset"] == "interior_day" and cafe["time"] == "golden"
    beach = PL.plan("sunny beach boardwalk")
    assert beach["kit"] == "beach" and beach["look"]["preset"] == "day_clear"
    odd = PL.plan("somewhere nice")
    assert odd["kit"] == "street" and "no kit word" in odd["note"]
    assert PL.plan("a street", seed=7)["seed"] == 7 and PL.plan("a street")["seed"] == PL.plan("a street")["seed"]
    assert PL.recipe_problems(r) == [] and PL.recipe_problems({**r, "kit": "moon"})
    assert PL.recipe_problems(PL.plan("a street", overrides={"size_m": [2, 2]}))
    assert PL.recipe_problems(PL.plan("a street", overrides={"textures": "magic"}))


def test_make_tileable_matches_its_own_edges(tmp_path):
    grad = np.tile(np.linspace(0, 255, 64, dtype=np.float32), (64, 1))
    src = tmp_path / "g.png"
    Image.fromarray(np.stack([grad] * 3, -1).astype(np.uint8)).save(src)
    out = np.asarray(Image.open(textures.make_tileable(src, tmp_path / "t.png", size=64)).convert("L"), dtype=np.float32)
    assert abs(out[:, 0] - out[:, -1]).mean() < 6 and abs(grad[:, 0] - grad[:, -1]).mean() > 200


@pytest.mark.parametrize("what,kind", [("red brick wall", "brick"), ("asphalt road surface", "tarmac"), ("oak wood floorboards", "plank"), ("concrete paving slabs", "paving"),
                                       ("fine pale beach sand", "sand"), ("painted plaster wall", "plaster"), ("sea water", "water"), ("something else", "plaster")])
def test_procedural_textures_read_the_words_and_repeat_exactly(what, kind, tmp_path):
    assert textures.kind_of(what) == kind
    a = textures.procedural(what, tmp_path / "a.png", size=64, seed=5)
    b = textures.procedural(what, tmp_path / "b.png", size=64, seed=5)
    assert a.read_bytes() == b.read_bytes() and Image.open(a).size == (64, 64)
    assert np.asarray(Image.open(a)).std() > 0.5                                 # a real pattern, not a flat fill


def test_procedural_noise_wraps_at_the_edges(tmp_path):
    n = textures._noise(np.random.default_rng(1), 128, 8)
    assert abs(n[:, 0] - n[:, -1]).mean() < 0.05 and abs(n[0] - n[-1]).mean() < 0.05


class Studio:
    def __init__(self, tmp_path, fail=()):
        self.reqs, self.tmp, self.fail = [], tmp_path, set(fail)

    def submit(self, req):
        self.reqs.append(req)
        return f"j{len(self.reqs)}"

    def wait(self, jid):
        req = self.reqs[int(jid[1:]) - 1]
        if any(w in req["prompt"] for w in self.fail):
            return {"status": "failed", "error": "busy", "artifacts": []}
        p = self.tmp / f"{jid}.png"
        Image.new("RGB", (32, 32), (90, 90, 90)).save(p)
        return {"status": "done", "error": "", "artifacts": [{"path": str(p), "media_type": "image"}]}


class FakeBlender:
    def __init__(self):
        self.calls = []

    def render(self, script, payload, *, work, **kw):
        from pathlib import Path
        self.calls.append((script, payload))
        Path(payload["views"]).mkdir(parents=True, exist_ok=True)
        for i in range(4):
            Image.new("RGB", (8, 8), (40 * i, 0, 0)).save(Path(payload["views"]) / f"view_{i}.png")
        Path(payload["out"]).write_bytes(b"glTF")
        return {"ok": True, "engine": "cycles", "fallback_note": "rendered on the CPU: short", "inspect": {"loaded": True, "dims_m": [40, 30, 3], "colliders": 12, "bones": []}}


def _ctx(lib, meta, tmp_path, **kw):
    fb = FakeBlender()
    return fb, ctx_for(lib, meta, tmp_path, blender=fb, **kw)


def test_a_generated_build_makes_textures_then_tiles_and_a_failed_picture_becomes_procedural(tmp_path):
    lib = L.Library()
    r = PL.plan("rainy downtown block")
    meta = lib.create(L.new_meta("place", "Downtown", source={"kind": "brief", "brief": r["brief"]}, recipe=r))
    st = Studio(tmp_path, fail=("brick",))
    fb, ctx = _ctx(lib, meta, tmp_path, textures_generated=lambda: True)
    state = S.run({}, PL.steps(meta), ctx=ctx, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert state["state"] == "done"
    assert [q["goal"] for q in st.reqs] == ["image"] * 4
    assert all(q["prompt"].startswith("seamless tileable texture of") and q["options"]["aspect"] == "1:1" for q in st.reqs)
    assert sorted(p.name for p in lib.subdir(meta["id"], "textures").glob("*.png")) == ["ground.png", "sidewalk.png", "wall.png", "wall2.png"]
    tiles = next(s for s in state["steps"] if s["name"] == "tiles")["outputs"]["main"]["materials"]
    assert tiles == {"ground": "generated", "sidewalk": "generated", "wall": "procedural", "wall2": "generated"}
    assert fb.calls[0][0] == "wk_place.py" and set(fb.calls[0][1]["textures"]) == set(tiles)
    build = next(s for s in state["steps"] if s["name"] == "build")["outputs"]
    assert Image.open(build["views"]["path"]).size == (1024, 1024) and "bones" not in build["main"]["inspect"]
    assert "short" in build["main"]["note"]


def test_with_no_model_or_no_comfyui_a_place_builds_on_procedural_textures_alone(tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("place", "Beach", source={"kind": "brief", "brief": "beach"}, recipe=PL.plan("sunny beach")))
    st = Studio(tmp_path)
    fb, ctx = _ctx(lib, meta, tmp_path, textures_generated=lambda: False)
    state = S.run({}, PL.steps(meta), ctx=ctx, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert state["state"] == "done" and st.reqs == []
    tiles = next(s for s in state["steps"] if s["name"] == "tiles")["outputs"]["main"]["materials"]
    assert set(tiles.values()) == {"procedural"}
    assert [s["status"] for s in state["steps"] if s["name"].startswith("tex_")] == ["skipped"] * 3


def test_textures_procedural_never_asks_comfyui_even_when_it_could(tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("place", "B", source={"kind": "brief", "brief": "b"}, recipe=PL.plan("sunny beach", overrides={"textures": "procedural"})))
    st = Studio(tmp_path)
    _, ctx = _ctx(lib, meta, tmp_path, textures_generated=lambda: pytest.fail("not asked"))
    assert S.run({}, PL.steps(meta), ctx=ctx, submit=st.submit, wait=st.wait, save=lambda s: None)["state"] == "done" and st.reqs == []


def test_a_look_asset_validates_and_approves_by_its_preset():
    lib = L.Library()
    good = lib.create(L.new_meta("look", "Golden", source={"kind": "preset"}, look=looks.resolve("golden_hour")))
    assert L.validate(good, None) == []
    lib.update(good["id"], build={"state": "done", "steps": []})
    assert lib.approve(good["id"])["status"] == "approved"
    bad = lib.create(L.new_meta("look", "Disco", source={"kind": "preset"}, look={"preset": "disco"}))
    assert L.validate(bad, None)
    lib.update(bad["id"], build={"state": "done", "steps": []})
    with pytest.raises(L.AssetError):
        lib.approve(bad["id"])


def test_a_real_glb_validates_as_a_place(tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("place", "P", source={"kind": "brief", "brief": "b"}, recipe=PL.plan("a street")))
    p = lib.path(meta["id"], "asset.glb")
    glb_file(p, {"asset": {"version": "2.0"}, "nodes": [{"name": "road"}, {"name": "road-colonly"}], "meshes": [{}]})
    meta["inspect"] = {"loaded": True, "dims_m": [40, 24, 10]}
    assert L.validate(meta, p) == []
