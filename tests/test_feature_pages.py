"""The slot for pages that are one file each: nothing lists them, so one can merge without touching another. No live ports."""
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"


def test_the_shell_loads_feature_pages_and_keeps_its_own_tabs():
    app = (WEB / "app.js").read_text()
    assert 'import { loadFeaturePages } from "./fx.js"' in app and "const tabs = [...TABS" in app and "page.Page" in app
    assert 'href="fx.css"' in (WEB / "index.html").read_text()


def test_the_server_finds_feature_files_by_name():
    src = (WEB.parent / "server.py").read_text()
    assert 'ROOT.glob("feature_*.py")' in src and '"/api/feature-pages"' in src


def test_a_page_that_fails_to_load_is_left_out():
    src = (WEB / "fx.js").read_text()
    assert "catch (e)" in src and "filter((p) => p && p.Page)" in src
