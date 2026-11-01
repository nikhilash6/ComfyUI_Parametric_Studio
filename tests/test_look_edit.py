"""The Edit page: real renders, and an honest list when ComfyUI is away. No live ports."""
import re
from pathlib import Path

import pytest
from fastapi import HTTPException

from studio import edits

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"


def _down():
    raise OSError("connection refused")


def test_edit_catalogue_answers_with_comfyui_down(monkeypatch):
    monkeypatch.setattr(edits.A, "object_info", _down)
    monkeypatch.setattr(edits, "_path", lambda name: None)
    d = edits.edits_catalogue()
    ids = {t["id"] for t in d["tools"]}
    assert "void" in ids and "bgremove" not in ids
    assert all(set(t) == {"id", "category", "category_label", "label", "blurb", "installed"} for t in d["tools"])
    assert not any("ready" in t or "runnable" in t for t in d["tools"])


def test_edit_form_says_comfyui_is_away(monkeypatch, tmp_path):
    monkeypatch.setattr(edits.A, "object_info", _down)
    monkeypatch.setattr(edits, "_find", lambda tid: (("void", "remove", "x", "t", "b"), str(tmp_path / "t.json")))
    with pytest.raises(HTTPException) as e:
        edits.edits_get("void")
    assert e.value.status_code == 503 and "not reachable" in e.value.detail


def test_edit_art_named_on_the_page_exists():
    text = (WEB / "pages2.js").read_text() + (WEB / "extras.js").read_text()
    for rel in set(re.findall(r"edit_art/[\w.]+\.(?:mp4|webp)", text)):
        assert (WEB / rel).is_file(), rel


def test_every_edit_with_a_render_has_a_chosen_frame():
    import json
    for tid in json.loads((WEB / "edit_art" / "index.json").read_text()):
        assert (WEB / "edit_art" / f"{tid}.webp").stat().st_size < 120_000, tid
        assert (WEB / "edit_art" / f"{tid}.mp4").is_file(), tid


def test_frames_are_labelled_and_the_clip_stays_reachable():
    text = (WEB / "pages2.js").read_text()
    assert "These are our own renders, not yours." in text and "still" in text
    assert "Play the clip" in (WEB / "look.js").read_text()
