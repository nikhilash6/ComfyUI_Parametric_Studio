"""The Site builder page: the examples still fill the form, and the pictures are labelled as not being websites."""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"
EX = (WEB / "extras.js").read_text()


def test_site_art_exists_and_is_labelled():
    block = re.search(r"const SITE_ART = \[(.*?)\]", EX).group(1)
    for rel in re.findall(r'"([^"]+)"', block):
        assert (WEB / rel).is_file(), rel
    assert "our own renders, not websites" in EX


def test_site_keeps_its_rules_and_controls():
    for word in ("It never invents details", "fill(x)", "/api/site/build", 'sandbox=""', "Open in a tab"):
        assert word in EX, word
