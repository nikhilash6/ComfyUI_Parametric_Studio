"""The Families page: state filters and the honest state labels stay, and the stage only takes the author's own renders."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "studio" / "web" / "families.js").read_text()


def test_families_keeps_filters_and_honest_notes():
    for word in ("setSt", "setKind", "search families", "On one side only", "with their real state", "rendered by the author", "not yours", "No render yet"):
        assert word in JS, word


def test_stage_skips_library_samples():
    assert 'f.level === "render" && !f.media_library' in JS
