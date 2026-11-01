"""The Designers page: the render is real and labelled, empty views say so, and the prompt comes from the composer. No live ports."""
import json, re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"
EX = (WEB / "extras.js").read_text()
BODY = EX[EX.index("/* The reel:"):EX.index("/* ---------- Apps:")]


def test_each_designer_has_its_real_render_and_record():
    rows = json.loads((WEB / "designer_art" / "art.json").read_text())
    assert len(rows) >= 13
    for r in rows:
        assert (WEB / "designer_art" / f"{r['id']}.webp").is_file(), r["id"]
        assert r["prompt"] and r["seed"] is not None and r["model"]


def test_every_sheet_image_is_a_recorded_render():
    rows = json.loads((WEB / "designer_art" / "sheets.json").read_text())
    assert len({r["id"] for r in rows}) >= 26 and len(rows) >= 120
    for r in rows:
        assert (WEB / r["file"]).is_file(), r["file"]
        assert r["prompt"] and r["seed"] is not None and r["model"] and r["kind"] in ("view", "choice"), r["file"]
    assert sum((WEB / r["file"]).stat().st_size for r in rows) < 8_000_000


def test_sample_pictures_say_they_are_not_yours():
    assert BODY.count("not yours") >= 3 and "Only that choice differs" in BODY and "Same seed and same words" in BODY


def test_prompt_comes_from_the_composer():
    assert re.search(r"/api/packs/\$\{pack\.id\}/compose", BODY) and "This exact text goes to the model" in BODY


def test_designers_keep_form_and_labels():
    for word in ("Views in the sheet", "Make ${views.length || 1}", "no brands, logos", "PrintifyCard", "No sheet can be made until it is back", "All designers", "How this picture was made"):
        assert word in BODY, word


def test_reel_works_by_keyboard_and_honours_reduced_motion():
    assert "ArrowRight" in BODY and "prefers-reduced-motion" in BODY and "Previous designer" in BODY


def test_no_sample_image_has_been_kept_after_review_with_text_on_it():
    rows = json.loads((WEB / "designer_art" / "sheets.json").read_text())
    files = {r["file"] for r in rows}
    for bad in ("creature/v-field-sketch", "jewellery/v-maker-s-sketch", "sneaker/v-pair-from-above", "architecture/v-section-drawing", "perfume/v-with-its-packaging", "stage/v-designer-s-scale-model"):
        assert f"designer_art/sheets/{bad}.webp" not in files, bad
    assert not (WEB / "designer_art" / "sheets" / "tattoo").exists()


def test_new_designers_have_generic_choices_and_a_tile():
    from studio import packs as P
    d = P.load()
    assert len(d) >= 28
    for a in json.loads((WEB / "designer_art" / "art.json").read_text()):
        assert a["id"] in d and (WEB / "designer_art" / f"{a['id']}.webp").is_file()
