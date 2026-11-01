"""The Site builder page: real pages from the real builder, a live preview that runs no model, and a colour the builder can use. No live ports."""
import json, re
from pathlib import Path

import pytest

from psn.sitebuilder import check_site
from studio import site_api

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"
EX = (WEB / "extras.js").read_text()
SITES = json.loads((WEB / "site_examples" / "index.json").read_text())


def test_six_sample_sites_exist_and_pass_the_builders_checks():
    assert len(SITES) == 6
    for s in SITES:
        d = WEB / "site_examples" / s["slug"]
        assert check_site(str(d)) == [], s["slug"]
        assert (WEB / "site_examples" / f"{s['slug']}_desktop.webp").is_file() and (WEB / "site_examples" / f"{s['slug']}_phone.webp").is_file()


def test_sample_sites_stay_small():
    size = sum(p.stat().st_size for p in (WEB / "site_examples").rglob("*") if p.is_file())
    assert size < 2_000_000


def test_samples_say_what_they_are():
    for word in ("invented briefs", "wrote their words by hand", "our own renders", "sample"):
        assert word in EX, word


def test_the_colour_goes_to_the_builder_and_the_voice_does_not():
    assert "voice: brand, brand: colour" in EX
    body = re.search(r"const SITE_NOTE.*?/\* ---------- 3D", EX, re.S).group(0)
    assert 'type="color"' in body


def test_preview_uses_the_brief_and_writes_nothing_new():
    h = site_api.preview_html({"name": "A<b>B", "voice": "calm", "brand": "#336699", "pages": ["home", "about"], "facts": {"Hours": "9 to 5"}})
    assert "A&lt;b&gt;B" in h and "9 to 5" in h and "About" in h and "written when you press Build" in h
    assert "<script" not in h and "http://" not in h.replace("http://www.w3.org", "") and "https://" not in h


@pytest.mark.parametrize("brand", ["warm, handmade", "", None, "red"])
def test_preview_survives_a_colour_that_is_not_one(brand):
    assert "<!doctype html>" in site_api.preview_html({"name": "x", "brand": brand})


def test_preview_route_refuses_non_sfw(monkeypatch):
    r = site_api.site_preview(site_api.BuildRequest(brief={"name": "x", "voice": "explicit nude photos"}))
    assert r.status_code == 400


def test_site_keeps_its_controls():
    for word in ("It never invents details", "/api/site/build", 'sandbox=""', "Open in a tab", "fill(x)"):
        assert word in EX, word
