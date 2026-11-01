"""The World Kit and Virtual Set pages: added media stays small and local, honest notes stay on the page, nothing about what a mode has proved is hard-coded."""
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"
PAGES = ["worldkit.js", "wk_example.js", "worldkit.css", "virtualset.js", "vset_hero.js", "vset_example.js", "virtualset.css"]


def test_each_page_has_its_own_stylesheet_linked():
    index = (WEB / "index.html").read_text()
    assert 'href="worldkit.css"' in index and 'href="virtualset.css"' in index


def test_added_media_is_small_and_real_files():
    media = [*(WEB / "wk_art").iterdir(), *(WEB / "vset_art").iterdir()]
    assert sum(p.stat().st_size for p in media) < 4_000_000
    used = " ".join((WEB / n).read_text() for n in ["wk_example.js", "vset_example.js"])
    for rel in re.findall(r"(?:wk|vset)_art/[\w.]+", used):
        assert (WEB / rel).is_file(), rel
    for name in ["h3_result", "h3_shaded", "h3_depth", "h3_edges", "ltx_result", "ltx_shaded", "ltx_depth", "ltx_edges", "ltx_clay"]:
        assert (WEB / "vset_art" / f"{name}.mp4").is_file() and (WEB / "vset_art" / f"{name}.webp").is_file(), name


@pytest.mark.parametrize("name", PAGES)
def test_local_files_only_and_no_long_dashes(name):
    text = (WEB / name).read_text()
    assert "—" not in text
    assert not re.findall(r"""(?:src|href)=["']https?:|url\(["']?https?:|@import""", text)


def test_samples_and_the_test_shot_are_marked_as_ours():
    wk, vs = (WEB / "worldkit.js").read_text(), (WEB / "vset_hero.js").read_text() + (WEB / "vset_example.js").read_text()
    assert "Ours, not in your library" in wk and "Our test, not a promise" in vs and "keeps the set exact and does not make it photoreal" in vs


def test_notes_on_what_is_not_proven_stay_on_the_page():
    js = (WEB / "virtualset.js").read_text()
    for note in ["No face check ran", "Characters are off", "The checks do not judge the picture", "Keeps layout and camera, not exact props"]:
        assert note in js, note
    assert "Licences (for your information)" in (WEB / "worldkit.js").read_text()


def test_proof_status_is_read_from_the_server():
    """The page's only proof words are a mapping from the server's state; no route or mode gets a fixed verdict."""
    helpers = (WEB / "vset_helpers.js").read_text()
    assert re.search(r"const p = route\.proof", helpers)
    for name in ["virtualset.js", "vset_hero.js", "vset_example.js"]:
        text = (WEB / name).read_text()
        assert not re.search(r"proof\s*:", text) and not re.search(r"""state\s*[:=]+\s*["']passed""", text), name


def test_form_buttons_cannot_start_a_render_by_accident():
    assert '<button type="button" class="btn small" aria-pressed=${autoRotate}' in (WEB / "viewer3d.js").read_text()
    js = (WEB / "virtualset.js").read_text()
    assert len(re.findall(r'<button(?! type=)', js)) == 0 and 'e.key === "Enter" && e.target.tagName === "INPUT"' in js


def test_reduced_motion_is_respected():
    for css in ["worldkit.css", "virtualset.css"]:
        assert "prefers-reduced-motion:reduce" in (WEB / css).read_text()
    assert "prefers-reduced-motion: reduce" in (WEB / "vset_hero.js").read_text() and "prefers-reduced-motion: reduce" in (WEB / "worldkit.js").read_text() and "prefers-reduced-motion: reduce" in (WEB / "viewer3d.js").read_text()
