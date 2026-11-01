"""Game-engine pack export (no server, no Blender, no GPU)."""
import json
import zipfile

from studio.worldkit import api, export as X, library as L


def _asset(lib, type_, name, *, approved=True, glb=b"glTF-bytes", **changes):
    meta = lib.create(L.new_meta(type_, name, source={"kind": "text", "prompt": name} if type_ == "prop" else {"kind": "brief", "brief": name}))
    if glb is not None:
        lib.path(meta["id"], "asset.glb").write_bytes(glb)
    return lib.update(meta["id"], status="approved" if approved else "draft", scale_m=1.2, colliders=1, clips=[{"name": "idle"}], **changes)


def test_transform_maps_blender_z_up_to_godot_y_up():
    assert X.transform([1, 2, 3]) == "Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 3, -2)"
    assert X.transform([0, 0, 0], 90, 2).startswith("Transform3D(0, 0, 2, 0, 2, 0, -2, 0, 0,")


def test_export_writes_glbs_manifest_scene_and_zip():
    lib = L.Library()
    place = _asset(lib, "place", "Rainy block")
    chair = _asset(lib, "prop", "Red chair")
    _asset(lib, "prop", "Not approved", approved=False)
    code, body = api.export_pack(lib, {"name": "My Game!"})
    assert code == 200 and body["assets"] == 2 and body["pack"].startswith("my-game-")
    pack = lib.root / "_exports" / body["pack"]
    assert (pack / f"assets/place/rainy-block-{place['id'][:4]}.glb").read_bytes() == b"glTF-bytes"
    man = json.loads((pack / "manifest.json").read_text())
    assert man["schema"] == X.SCHEMA and {a["name"] for a in man["assets"]} == {"Rainy block", "Red chair"}
    tscn = (pack / "scenes/main.tscn").read_text()
    assert tscn.startswith("[gd_scene load_steps=3 format=3]") and f'res://{body["pack"]}/assets/prop/' in tscn
    assert "instance=ExtResource(" in tscn and "{pack}" not in tscn
    with zipfile.ZipFile(lib.root / "_exports" / body["zip"]) as z:
        assert f"{body['pack']}/manifest.json" in z.namelist()
    assert api.exports_payload(lib)[1]["exports"][0]["zip"] == body["zip"]
    assert X.zip_path(lib, body["zip"]).read_bytes()[:2] == b"PK"
    assert chair["id"] in {a["id"] for a in man["assets"]}


def test_export_placements_and_refusals():
    lib = L.Library()
    a = _asset(lib, "prop", "Lamp")
    d = _asset(lib, "prop", "Draft lamp", approved=False)
    place = [{"asset": a["id"], "pos": [2, 3, 0], "yaw_deg": 90}]
    code, body = api.export_pack(lib, {"assets": [a["id"]], "placements": place})
    assert code == 200 and body["manifest"]["assets"][0]["placements"][0]["pos"] == [2.0, 3.0, 0.0]
    tscn = (lib.root / "_exports" / body["pack"] / "scenes/main.tscn").read_text()
    assert "Transform3D(0, 0, 1, 0, 1, 0, -1, 0, 0, 2, 0, -3)" in tscn
    code, refused = api.export_pack(lib, {"assets": [d["id"]]})
    assert code == 400 and "Draft lamp" in refused["error"]
    assert api.export_pack(lib, {"assets": ["abcdefghijkl"]})[0] == 404
    assert api.export_pack(lib, {"assets": [a["id"]], "placements": [{"asset": d["id"]}]})[0] == 400
    assert api.export_pack(lib, {"assets": [a["id"]], "placements": [{"asset": a["id"], "scale": 0}]})[0] == 400
    assert X.zip_path(lib, "../x.zip") is None


def test_nothing_approved_means_nothing_to_export(tmp_path):
    assert api.export_pack(L.Library(tmp_path / "empty"), {})[0] == 400


def test_a_look_in_a_pack_has_no_file():
    lib = L.Library()
    look = lib.create(L.new_meta("look", "Golden", source={"kind": "preset"}, look={"preset": "golden_hour"}))
    lib.update(look["id"], status="approved")
    code, body = api.export_pack(lib, {})
    assert code == 200 and body["manifest"]["assets"][0]["file"] == ""
