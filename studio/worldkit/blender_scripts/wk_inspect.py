"""blender -b --factory-startup --python wk_inspect.py -- PAYLOAD.json     payload {"model": path}
Loads the model headless and reports what library validation needs : PPWK {"ok", "inspect"}. CPU, no render."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _wk  # noqa: E402


def run(p):
    _wk.reset()
    _wk.done(inspect=_wk.inspect(_wk.import_model(p["model"])))


_wk.main(run)
