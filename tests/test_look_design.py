"""The Designers page: the form stays whole and the sample is labelled."""
from pathlib import Path

EX = (Path(__file__).resolve().parents[1] / "studio" / "web" / "extras.js").read_text()


def test_designers_keep_form_and_labels():
    body = EX[EX.index("export function Designers("):EX.index("/* ---------- Apps:")]
    for word in ("Views in the sheet", "Make ${views.length || 1}", "no brands, logos", "PrintifyCard", "Our own render from this designer, not yours", "No sheet can be made until it is back", "All designers"):
        assert word in body, word
