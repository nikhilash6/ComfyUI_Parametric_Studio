"""Every node in a shipped graph has a plain-language note in the 3D Pro view (studio/web/graph3d_math.js CLASS_INFO).

Without one, the inspector shows only the class name. This used to live in test_studio_live.py, which the release suite skips, so it drifted."""
import glob, json, os, re

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _api_graphs():
    for pat in ("workflows/*.json", "studio/family_templates/**/*.json"):
        for f in glob.glob(os.path.join(ROOT, pat), recursive=True):
            try:
                d = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            if isinstance(d, dict) and isinstance(d.get("prompt"), dict):
                d = d["prompt"]
            if isinstance(d, dict) and "nodes" not in d:
                yield f, d


def test_every_shipped_graph_class_has_an_explanation():
    src = open(os.path.join(ROOT, "studio", "web", "graph3d_math.js"), encoding="utf-8").read()
    missing = {}
    for f, g in _api_graphs():
        for v in g.values():
            if isinstance(v, dict) and v.get("class_type"):
                c = v["class_type"]
                if not re.search(r'(^|[\s{,"])' + re.escape(c) + r'"?: I\(', src):
                    missing.setdefault(c, os.path.relpath(f, ROOT))
    assert not missing, sorted(missing.items())


def test_the_check_sees_both_folders():
    files = [os.path.relpath(f, ROOT) for f, _ in _api_graphs()]
    assert sum(f.startswith("workflows") for f in files) > 20 and sum("family_templates" in f for f in files) > 20
