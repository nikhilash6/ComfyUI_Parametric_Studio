"""The shared page look: local files only, plain copy, and pages that still say something true when ComfyUI is away. No live ports."""
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"


def test_stylesheet_is_linked_after_the_pages_it_builds_on():
    index = (WEB / "index.html").read_text()
    assert index.index('href="shotboard.css"') < index.index('href="looks.css"')
    assert index.index('href="skin.css"') < index.index('href="looks.css"')


@pytest.mark.parametrize("name", ["look.js", "looks.css"])
def test_local_files_only_and_no_long_dashes(name):
    text = (WEB / name).read_text()
    assert "—" not in text
    assert not re.findall(r"""(?:src|href)=["']https?:|url\(["']?https?:|@import""", text)


def test_reduced_motion_is_honoured_by_the_shared_media():
    assert "prefers-reduced-motion" in (WEB / "look.js").read_text()


def test_learn_and_recipes_stay_off_the_shared_look():
    look = re.search(r"const LOOK = new Set\(\[(.*?)\]\)", (WEB / "app.js").read_text()).group(1)
    assert '"university"' not in look and '"recipes"' not in look
