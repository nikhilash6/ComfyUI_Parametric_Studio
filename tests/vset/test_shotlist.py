import pytest

from studio.vset import shotlist as SL


def test_split_script_strips_numbering_and_blank_lines():
    text = "Shot 1: the door opens\n\n2) steam rises from the cup\n- rain runs down the glass\n   \n• the lights go out"
    assert SL.split_script(text) == ["the door opens", "steam rises from the cup", "rain runs down the glass", "the lights go out"]


def test_camera_words_pick_presets_and_the_rest_rotate():
    assert SL.camera_for("tracking down the street", 0) == "walk_along"
    assert SL.camera_for("slow orbit around the fountain", 0) == "orbit"
    assert SL.camera_for("POV: the road ahead", 0) == "pov"
    assert [SL.camera_for("the lights come on", i) for i in range(4)] == ["push_in", "walk_along", "orbit", "push_in"]


def test_from_script_makes_one_shot_per_line_in_one_set():
    base = {"set": {"place": "placeplacepl", "props": []}, "marks": [[0, 0]], "look": {"preset": "golden_hour"}, "mode": "C", "format": {"aspect": "9:16", "seconds": 5}, "session_id": "s1", "seed": 100}
    shots = SL.from_script("the door opens\norbit the counter\nthe lights go out", base=base, name="Cafe")
    assert [s["prompt"] for s in shots] == ["the door opens", "orbit the counter", "the lights go out"]
    assert [s["seed"] for s in shots] == [100, 201, 302] and shots[1]["camera"]["preset"] == "orbit"
    assert all(s["set"] == base["set"] and s["session_id"] == "s1" for s in shots) and shots[2]["name"] == "Cafe #3"
    shots[0]["marks"].append([1, 1])
    assert shots[1]["marks"] == [[0, 0]]                             # deep copies
    with pytest.raises(ValueError, match="no lines"):
        SL.from_script("  \n ", base=base)
    with pytest.raises(ValueError, match="at most 12"):
        SL.from_script("\n".join(f"line {i}" for i in range(13)), base=base)


def test_lists_store():
    lst = SL.save_list(SL.new_list("L", ["aaaaaaaaaaaa", "bbbbbbbbbbbb"], base={}))
    assert SL.load_list(lst["id"])["shots"] == ["aaaaaaaaaaaa", "bbbbbbbbbbbb"] and [x["id"] for x in SL.list_lists()] == [lst["id"]]
