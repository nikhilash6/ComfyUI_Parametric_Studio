"""The Atlas page: honest status and filters stay after the redesign."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "studio" / "web" / "atlas.js").read_text()


def test_atlas_keeps_its_filters_and_notes():
    for word in ("setKind", "setTested", "setRuns", "search the atlas", "setView", "Coverage", "Date not verified", "Licence unverified", "Earlier notes", "anything not checked says so", "not yours"):
        assert word in JS, word
