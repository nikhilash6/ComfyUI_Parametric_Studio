from studio.worldkit import library as L, media, preview as PV
from tests.worldkit.conftest import needs_blender
from tests.worldkit.helpers import ctx_for

pytestmark = needs_blender


def test_turntable_of_a_character_and_of_a_look(wk_fixtures, monkeypatch, tmp_path):
    monkeypatch.setattr(PV, "TURN_FRAMES", 3)
    monkeypatch.setattr(PV, "TURN_SIZE", 64)
    lib = L.Library()
    char = lib.create(L.new_meta("character", "fixture", source={"kind": "character", "character_id": "x"}))
    out = PV.render(ctx_for(lib, char, tmp_path, {"assemble": {"main": {"path": str(wk_fixtures / "char.glb")}}}))
    assert media.frame_count(out["turntable"]["path"]) == 3 and out["turntable"]["engine"] == "cycles"
    look = lib.create(L.new_meta("look", "Night", source={"kind": "preset", "preset": "night_city"}, look={"preset": "night_city"}))
    out = PV.render(ctx_for(lib, look, tmp_path / "l"))
    assert media.frame_count(out["turntable"]["path"]) == 3
