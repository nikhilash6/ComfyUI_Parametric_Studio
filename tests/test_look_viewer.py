"""The 3D page: the sample is labelled a sample, and the links out go to real pages."""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"
EX = (WEB / "extras.js").read_text()


def test_viewer_says_the_sample_is_not_your_work():
    assert "you are looking at the sample, not your work" in EX and "No generated .glb files yet" in EX


def test_links_and_art_are_real():
    block = EX[EX.index("const MAKE_3D"):EX.index("export function Studio3D")]
    app = (WEB / "app.js").read_text()
    for tab in re.findall(r'"#(\w+)"', block):
        assert f'"{tab}"' in app, tab
    for rel in re.findall(r"wk_art/[\w.]+", block):
        assert (WEB / rel).is_file(), rel
