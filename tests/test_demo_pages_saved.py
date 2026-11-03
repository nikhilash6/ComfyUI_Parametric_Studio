"""The read-only demo (scripts/build_pages.py) saves the server's GET answers as files. A page whose opening GET is not saved shows only
"no saved answer" on GitHub Pages; six feature pages shipped like that. Every literal GET path in the front end is saved, or listed here with why not."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOT_SAVED = {
    "fit/detect": "this machine's GPU: the demo would show the author's card as the visitor's",
    "gamebuilder/status": "this machine's Godot and model readiness",
    "models/attach": "this machine's ComfyUI address",
    "printify": "a print-on-demand account; not part of the demo",
    "probe": "needs an uploaded file",
}


def _front_end_gets():
    out = {}
    for f in list((ROOT / "studio" / "web").glob("*.js")) + list((ROOT / "studio" / "web").glob("*/*.js")):
        s = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'api\(\s*[`"](/api/[^"`$?]*)(\?[^"`$]*)?["`]\s*(,\s*\{[^}]*method)?', s):
            p = m.group(1)[5:]
            if not m.group(3) and p and not p.endswith("/"):
                out.setdefault(p, f.name)
    return out


def test_every_opening_get_is_saved_for_the_demo():
    src = (ROOT / "scripts" / "build_pages.py").read_text(encoding="utf-8")
    missing = {p: f for p, f in _front_end_gets().items() if p not in NOT_SAVED and f'"{p}"' not in src and f'"{p}?' not in src}
    assert not missing, missing


def test_the_scan_finds_the_pages_it_guards():
    gets = _front_end_gets()
    assert {"campath", "words", "finish", "dub/models", "commercials/proof"} <= set(gets)
