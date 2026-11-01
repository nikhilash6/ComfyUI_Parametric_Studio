"""The Processes page: every filter and honest status stays."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "studio" / "web" / "processes.js").read_text()


def test_processes_keeps_status_filters_and_labels():
    for word in ('"Tested here"', '"Opens here"', '"Closest match"', '"Coming soon"', "setKind", "setStatus", "readDoc", "Back to processes", "our own renders, not yours"):
        assert word in JS, word


def test_no_new_external_files():
    assert "http://" not in JS.replace("https?:\\/\\/", "") and "<script" not in JS
