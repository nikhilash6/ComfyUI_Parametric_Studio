"""The Create page: the shell title stays hidden and the offline note stays plain."""
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"


def test_create_title_stays_hidden_with_the_shared_look():
    css = (WEB / "looks.css").read_text()
    assert "body.on-look:not(.on-create):not(.on-pro) main>.top" in css


def test_create_offline_note_is_plain():
    assert "Start it, then try again." in (WEB / "app.js").read_text()
