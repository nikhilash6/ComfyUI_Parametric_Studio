"""The Library page: an empty list and an unreachable ComfyUI are different things, and the page says which."""
from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "studio" / "web" / "app.js").read_text()


def test_library_tells_empty_from_offline():
    body = APP[APP.index("function Library()"):APP.index("/* ---------- Models ---------- */")]
    assert "Your work can't be listed" in body and "Nothing here yet" in body and "Your files are not gone" in body


def test_library_keeps_its_actions():
    body = APP[APP.index("function Library()"):APP.index("/* ---------- Models ---------- */")]
    for word in ("TrainedLoras", "Masonry", "ShareButton", "Download", "Recreate", "Open the graph", "<audio"):
        assert word in body, word


def test_library_start_art_exists():
    web = Path(__file__).resolve().parents[1] / "studio" / "web"
    for name in ("s_temple.webp", "v_h3_dragon.webp", "a_score.webp", "v_h3_foundry.webp"):
        assert (web / "showcase" / name).is_file(), name
