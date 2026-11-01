"""The Apps page: search, sections, the graph panel and the run form all stay."""
from pathlib import Path

EX = (Path(__file__).resolve().parents[1] / "studio" / "web" / "extras.js").read_text()


def test_apps_keeps_its_parts():
    body = EX[EX.index("export function Apps()"):]
    for word in ("GraphPanel", "Search graphs", "setSec", "Download missing files", "Needs custom nodes", "Run app", "our own renders, not yours", "Hub apps"):
        assert word in body, word
