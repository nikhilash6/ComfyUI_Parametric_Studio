"""The read-only demo saves what its pages ask for: half the pages showed nothing when these answers were missing."""
import pathlib, re

SRC = (pathlib.Path(__file__).resolve().parents[1] / "scripts" / "build_pages.py").read_text(encoding="utf-8")


def test_demo_saves_the_lists_its_pages_open():
    for p in ("feature-pages", "all-graphs", "edits/catalogue", "pipelines", "3d/models", "motion", "music/models", "voices/models", "tryon/methods", "loras", "packlab/picks"):
        assert f'"{p}"' in SRC, p
    assert 'r["graph_url"][5:]' in SRC and '"prove/recipe/"' in SRC and "query=True" in SRC


def test_demo_phone_answer_has_no_address_from_the_build_machine():
    phone = re.search(r'save\("phone", (\{.*\})\)', SRC).group(1)
    assert '"url": None' in phone and '"https_url": None' in phone and "ph.get(\"url\"" not in phone and "tailscale\")" not in phone


def test_demo_shim_prefers_an_answer_saved_for_the_exact_query():
    assert "have.has(key(path + \"?\" + q))" in SRC
