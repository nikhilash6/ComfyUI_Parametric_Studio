import pytest

from studio.worldkit import library as L


def _meta(type_="prop", name="Red chair", **kw):
    return L.new_meta(type_, name, source={"kind": "text", "prompt": "a red chair"}, tags=["Furniture", "red"], **kw)


def test_ids_are_twelve_lowercase_letters_never_digits():
    ids = {L.new_id() for _ in range(300)}
    assert len(ids) == 300 and all(len(i) == 12 and i.isalpha() and i.islower() for i in ids)
    assert L.valid_id("abcdefghijkl") and not L.valid_id("abc123defghi") and not L.valid_id("../../etc/pw")


def test_new_meta_is_valid_and_has_every_spec_field():
    m = _meta()
    assert L.meta_problems(m) == []
    for key in ("id", "type", "name", "source_jobs", "source_images", "scale_m", "rig", "colliders", "clips",
                "licence_class", "status", "created", "updated"):
        assert key in m
    assert m["status"] == "draft" and m["licence_class"] == "UNK" and m["tags"] == ["furniture", "red"]
    assert m["build"] == {"state": "pending", "steps": [], "error": ""}


def test_meta_problems_name_every_bad_field():
    m = _meta()
    m.update(type="dragon", name="", status="live", licence_class="FREE", scale_m=-1, id="ABC123")
    bad = "; ".join(L.meta_problems(m))
    for word in ("type", "name", "status", "licence_class", "scale_m", "id"):
        assert word in bad
    assert L.meta_problems("nope") == ["meta must be an object"]


def test_create_get_update_and_the_folder_layout(tmp_path):
    lib = L.Library()
    m = lib.create(_meta())
    assert (tmp_path / "worldkit" / "prop" / m["id"] / "meta.json").is_file()
    assert lib.get(m["id"])["name"] == "Red chair"
    lib.update(m["id"], scale_m=0.9)
    assert lib.get(m["id"])["scale_m"] == 0.9
    with pytest.raises(L.AssetError, match="never change"):
        lib.update(m["id"], type="place")
    with pytest.raises(L.AssetError):
        lib.update(m["id"], status="live")
    with pytest.raises(L.AssetError, match="exists"):
        lib.create(dict(m))
    assert lib.get("nosuchassetx") is None and lib.get("../../etc") is None
    with pytest.raises(L.AssetError, match="no asset"):
        lib.require("abcdefghijkl")


def test_list_searches_by_type_tag_name_and_status():
    lib = L.Library()
    a = lib.create(_meta("prop", "Red chair", now=1.0))
    b = lib.create(L.new_meta("place", "Rainy downtown block", source={"kind": "brief", "brief": "rainy downtown"},
                              tags=["street"], now=2.0))
    lib.update(b["id"], status="approved")
    assert [m["id"] for m in lib.list(type_="place")] == [b["id"]]
    assert [m["id"] for m in lib.list(tag="RED")] == [a["id"]]
    assert [m["id"] for m in lib.list(q="downtown rainy")] == [b["id"]]
    assert [m["id"] for m in lib.list(status="approved")] == [b["id"]]
    assert [m["id"] for m in lib.list()] == [b["id"], a["id"]]          # newest first


def test_a_broken_meta_file_is_skipped_not_fatal(tmp_path):
    lib = L.Library()
    good = lib.create(_meta())
    bad = tmp_path / "worldkit" / "prop" / "brokenbroken"
    bad.mkdir(parents=True)
    (bad / "meta.json").write_text("{not json")
    assert [m["id"] for m in lib.list()] == [good["id"]]


def test_put_file_and_subdir_stay_inside_the_asset(tmp_path):
    lib = L.Library()
    m = lib.create(_meta())
    src = tmp_path / "x.glb"
    src.write_bytes(b"glTF")
    dest = lib.put_file(m["id"], "asset.glb", src)
    assert dest.read_bytes() == b"glTF" and dest.parent.name == m["id"]
    with pytest.raises(L.AssetError):
        lib.put_file(m["id"], "../evil.glb", src)
    assert lib.subdir(m["id"], "textures").is_dir()
    with pytest.raises(L.AssetError):
        lib.subdir(m["id"], "../x")


def test_archive_moves_the_folder_and_never_deletes(tmp_path):
    lib = L.Library()
    m = lib.create(_meta())
    dest = lib.archive(m["id"])
    assert lib.get(m["id"]) is None and (dest / "meta.json").is_file()
    assert dest.parent == tmp_path / "worldkit" / "_archive" / "prop"


def test_the_root_is_a_setting_and_never_a_retired_folder(tmp_path, monkeypatch):
    from studio import worldkit
    assert worldkit.root() == tmp_path / "worldkit" and L.Library().root == tmp_path / "worldkit"
    monkeypatch.delenv(worldkit.SETTING)
    monkeypatch.setenv("PSN_SETTINGS", str(tmp_path / "none.env"))
    assert "camp" not in str(worldkit.root())
    monkeypatch.setenv(worldkit.SETTING, str(tmp_path / "elsewhere"))
    assert L.Library().root == tmp_path / "elsewhere"
    assert worldkit.work_root() == tmp_path / "wk_work"
