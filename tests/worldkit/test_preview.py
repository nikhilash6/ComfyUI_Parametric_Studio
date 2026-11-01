from pathlib import Path

from PIL import Image

from studio.worldkit import library as L, preview as PV
from tests.worldkit.helpers import ctx_for


def _encode(frames, fps, out):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(b"mp4")
    return Path(out)


class FB:
    calls = []

    @classmethod
    def render(cls, script, payload, *, work, **kw):
        cls.calls.append(payload)
        d = Path(payload["out_dir"])
        d.mkdir(parents=True, exist_ok=True)
        for i in range(1, 4):
            Image.new("RGB", (64, 64), (10 * i, 20, 30)).save(d / f"{i:04d}.png")
        return {"ok": True, "engine": "cycles", "fallback_note": "rendered on the CPU"}


def test_preview_uses_the_built_glb_and_a_look_has_none(tmp_path):
    FB.calls.clear()
    lib = L.Library()
    prop = lib.create(L.new_meta("prop", "chair", source={"kind": "text", "prompt": "chair"}))
    PV.render(ctx_for(lib, prop, tmp_path, {"cleanup": {"main": {"path": "/o/p.glb"}}}, blender=FB), encode=_encode)
    assert FB.calls[0]["model"] == "/o/p.glb" and FB.calls[0]["elevation"] == 0.35
    look = lib.create(L.new_meta("look", "Golden", source={"kind": "preset", "preset": "golden_hour"}, look={"preset": "golden_hour"}))
    PV.render(ctx_for(lib, look, tmp_path / "l", blender=FB), encode=_encode)
    assert FB.calls[1]["model"] == ""


def test_render_writes_a_turntable_and_a_jpeg_thumbnail(tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("prop", "chair", source={"kind": "text", "prompt": "chair"}))
    out = PV.render(ctx_for(lib, meta, tmp_path, {"cleanup": {"main": {"path": "/o/p.glb"}}}, blender=FB), encode=_encode)
    assert out["turntable"]["note"] == "rendered on the CPU" and out["turntable"]["frames"] == 3
    with Image.open(out["thumb"]["path"]) as im:
        assert im.format == "JPEG" and im.size == (PV.THUMB_SIZE, PV.THUMB_SIZE)


def test_ingest_copies_the_files_and_records_the_facts(tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("character", "Ada", source={"kind": "character", "character_id": "x"}))
    files = {}
    for name in ("char.glb", "turn.mp4", "thumb.jpg"):
        files[name] = tmp_path / name
        files[name].write_bytes(name.encode())
    rig = {"bones": 23, "standard": "any", "slots": {"head": "bone_5"}}
    outputs = {"assemble": {"main": {"job_id": "j9", "path": str(files["char.glb"]), "inspect": {"loaded": True, "height_m": 1.7, "colliders": 0}, "rig": rig, "clips": [{"name": "walk", "frames": 24, "fps": 24}]}},
               "preview": {"turntable": {"path": str(files["turn.mp4"])}, "thumb": {"path": str(files["thumb.jpg"])}}}
    out = PV.ingest({"library": lib, "asset": meta, "outputs": outputs})
    got = lib.get(meta["id"])
    assert out["main"]["files"] == ["asset.glb", "preview.mp4", "thumb.jpg"]
    assert lib.path(meta["id"], "asset.glb").read_bytes() == b"char.glb"
    assert got["scale_m"] == 1.7 and got["rig"] == rig and got["clips"][0]["name"] == "walk" and got["source_jobs"] == ["j9"]
    assert got["inspect"]["loaded"] is True


def test_ingest_copies_rather_than_links(tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("prop", "chair", source={"kind": "text", "prompt": "chair"}))
    for n in ("c.glb", "t.mp4", "k.jpg"):
        (tmp_path / n).write_bytes(n.encode())
    outputs = {"cleanup": {"main": {"path": str(tmp_path / "c.glb"), "inspect": {"dims_m": [1, 1, 1]}}}, "preview": {"turntable": {"path": str(tmp_path / "t.mp4")}, "thumb": {"path": str(tmp_path / "k.jpg")}}}
    PV.ingest({"library": lib, "asset": meta, "outputs": outputs})
    (tmp_path / "c.glb").write_bytes(b"changed")
    assert lib.path(meta["id"], "asset.glb").read_bytes() == b"c.glb"
