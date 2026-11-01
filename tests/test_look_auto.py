"""The Auto page: every control stays, and offline it says that no job can start."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "studio" / "web" / "pages2.js").read_text()


def test_auto_keeps_its_controls_and_says_what_is_true():
    body = JS[JS.index("export function Schedules()"):JS.index("export function CalibrateCard()")]
    for word in ("Add schedule", "run-now", "Pause", "Delete", "Most per day", "no job can start until ComfyUI is back", "our own renders, not yours"):
        assert word in body, word
