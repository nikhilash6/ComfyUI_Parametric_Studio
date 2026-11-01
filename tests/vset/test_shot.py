import pytest

from studio.vset import shot as SH
from studio.worldkit import library as L
from tests.vset.helpers import cast_of, good_shot, make_set


def test_frames_size_and_fps_per_mode():
    s = SH.new_shot(mode="A", mode_settings={"engine": "wan"}, format={"aspect": "9:16", "seconds": 5})
    assert (SH.fps(s), SH.frames(s), SH.size(s)) == (16, 81, (480, 832))
    h = SH.new_shot(mode="A", format={"aspect": "9:16", "seconds": 5})
    assert (SH.fps(h), SH.frames(h), SH.size(h)) == (24, 124, (768, 1344))
    c = SH.new_shot(mode="C", format={"aspect": "16:9", "seconds": 8})
    assert SH.fps(c) == 24 and SH.frames(c) == 192 and SH.size(c) == (1344, 768)
    assert SH.frames(SH.new_shot(mode="D", format={"aspect": "1:1", "seconds": 10})) == 243
    assert all((SH.frames(SH.new_shot(mode="C", format={"aspect": "1:1", "seconds": n})) - 5) % 17 == 0 for n in (5, 8, 10))     # H3's own rule


def test_a_shot_works_with_a_place_and_props_alone():
    lib = L.Library()
    s = good_shot(make_set(lib))
    assert s["cast"] == [] and SH.problems(s, library=lib) == []
    assert SH.subject_marks(s) == [[0, 0], [0, -3]]


def test_the_cast_needs_the_character_maker_switched_on(monkeypatch):
    lib = L.Library()
    ids = make_set(lib, character=True)
    s = good_shot(ids, cast=cast_of(ids))
    assert any("character maker is off" in p for p in SH.problems(s, library=lib))
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    assert SH.problems(s, library=lib) == [] and SH.subject_marks(s) == s["cast"][0]["marks"]


def test_mode_limits_are_refused_with_the_reason():
    lib = L.Library()
    ids = make_set(lib)
    assert "mode A renders 5 s" in " | ".join(SH.problems(good_shot(ids, mode="A", format={"aspect": "9:16", "seconds": 10}), library=lib))
    assert "renders 9:16, 16:9 only" in " ".join(SH.problems(good_shot(ids, mode="A", mode_settings={"engine": "wan"}, format={"aspect": "1:1", "seconds": 5}), library=lib))
    assert SH.problems(good_shot(ids, mode="A", format={"aspect": "1:1", "seconds": 5}), library=lib) == []          # H3 takes square
    assert SH.problems(good_shot(ids, format={"aspect": "9:16", "seconds": 10}), library=lib) == []
    assert "5-15 s" in " ".join(SH.problems(good_shot(ids, format={"aspect": "9:16", "seconds": 20}), library=lib))
    assert "control" in " ".join(SH.problems(good_shot(ids, mode="A", mode_settings={"control": "lidar"}), library=lib))
    assert "engine" in " ".join(SH.problems(good_shot(ids, mode="A", mode_settings={"engine": "sora"}), library=lib))
    assert "use the depth pass" in " ".join(SH.problems(good_shot(ids, mode="A", mode_settings={"control": "pose"}), library=lib))
    assert "keyframes" in " ".join(SH.problems(good_shot(ids, mode_settings={"keyframes": "magic"}), library=lib))


def test_assets_must_be_approved_right_type_and_present():
    lib = L.Library()
    ids = make_set(lib)
    lib.update(ids["place"], status="draft")
    assert any("Fixture block" in p and "approved" in p for p in SH.problems(good_shot(ids), library=lib))
    lib.archive(ids["prop"])
    assert any(ids["prop"] in p and "archived" in p for p in SH.problems(good_shot(ids), library=lib))
    assert any("not a place" in p for p in SH.problems(good_shot({"place": make_set(lib)["prop"], "prop": ids["prop"]}), library=lib))


def test_a_character_without_a_rig_or_the_clip_cannot_act(monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    lib = L.Library()
    ids = make_set(lib, character=True, slots={"head": "bone_5"})
    probs = " | ".join(SH.problems(good_shot(ids, cast=cast_of(ids)), library=lib))
    assert "has no rig" in probs and "static prop" in probs
    ids2 = make_set(lib, character=True)
    probs = " | ".join(SH.problems(good_shot(ids2, cast=[{"asset": ids2["char"], "clip": "backflip", "marks": [[0, 0]]}]), library=lib))
    assert "no clip 'backflip'" in probs and "walk" in probs


def test_marks_camera_look_prompt_and_seed_are_checked():
    lib = L.Library()
    ids = make_set(lib)
    assert "outside the place" in " ".join(SH.problems(good_shot(ids, marks=[[0, 0], [40, 0]]), library=lib))
    assert "marks is a path" in " ".join(SH.problems(good_shot(ids, marks="here"), library=lib))
    assert "camera preset" in " ".join(SH.problems(good_shot(ids, camera={"preset": "drone"}), library=lib))
    assert "look must be" in " ".join(SH.problems(good_shot(ids, look={"preset": "disco"}), library=lib))
    assert "describe the action" in " ".join(SH.problems(good_shot(ids, prompt=" "), library=lib))
    assert "seed" in " ".join(SH.problems(good_shot(ids, seed=-1), library=lib))
    assert "up to 2 cast" in " ".join(SH.problems(good_shot(ids, cast=["a", "b", "c"]), library=lib))


@pytest.mark.parametrize("field", ["prompt", "name"])
def test_the_words_of_a_shot_go_through_the_safe_for_work_check(field):
    lib = L.Library()
    ids = make_set(lib)
    assert any("safe-for-work" in p for p in SH.problems(good_shot(ids, **{field: "a nude figure on the street"}), library=lib))
    assert any("safe-for-work" in p for p in SH.problems(good_shot(ids, **{field: "a schoolgirl in lingerie"}), library=lib))


def test_look_can_be_a_preset_or_a_look_asset():
    lib = L.Library()
    ids = make_set(lib)
    look = L.new_meta("look", "Wet night", source={"kind": "preset", "preset": "night_city"}, look={"preset": "night_city", "weather": "rain"})
    look.update(status="approved")
    look["build"]["state"] = "done"
    lib.create(look)
    s = good_shot(ids, look={"asset": look["id"]})
    assert SH.problems(s, library=lib) == [] and SH.look_of(s, lib)["weather"] == "rain"
    assert SH.look_of(good_shot(ids), lib)["preset"] == "golden_hour"


def test_storage_round_trip_and_state(tmp_path):
    lib = L.Library()
    s = good_shot(make_set(lib))
    SH.save(s)
    assert (tmp_path / "vset" / "shots" / s["id"] / "shot.json").is_file()
    assert SH.load(s["id"])["prompt"] == s["prompt"] and [x["id"] for x in SH.list_shots()] == [s["id"]]
    assert SH.load_state(s["id"]) == {}
    SH.save_state(s["id"], {"state": "done", "steps": []})
    assert SH.load_state(s["id"])["state"] == "done"
    with pytest.raises(SH.ShotError):
        SH.load("abcdefghijkl")
    with pytest.raises(SH.ShotError):
        SH.load("../../etc")
