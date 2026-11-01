"""The API page keeps its code samples, filters and graph body."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "studio" / "web" / "apipage.js").read_text()


def test_api_keeps_its_parts():
    for word in ("setSec", "Search every graph", "Fill it in live", "Open it", "Copy", "GraphBody", "Comfy SDK", "No account, no key", "A call only renders once it is back"):
        assert word in JS, word
