"""The Models page: every section survives the move to tabs, and downloads still need the tick."""
from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "studio" / "web" / "app.js").read_text()


def test_models_keeps_every_section_and_the_download_guard():
    body = APP[APP.index("function Models()"):APP.index("/* ---------- Pro ---------- */")]
    for word in ("GoalTiles", "CloudCard", "AttachCard", "CalibrateCard", "civitai", "huggingface", "CIVITAI_TOKEN", "disabled=${!ok}", "confirm: ok"):
        assert word in body, word
