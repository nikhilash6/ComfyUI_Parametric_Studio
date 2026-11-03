#!/usr/bin/env python3
"""The counts the demo videos show, written to docs/demos/numbers.json with how each one was counted. The videos use only these.
Repo figures are counted from this checkout's files. The rest come from a running studio of this checkout (its own API, read-only GETs) and from a ComfyUI's /object_info (a read-only GET).
tests/test_demos.py holds every figure that can be counted from the files to "no more than the tree has", so a later merge can only make the claim more modest, never false.
Usage: python scripts/build_demo_numbers.py --studio http://127.0.0.1:8310 --comfy http://127.0.0.1:8188 [--tests N] [--out docs/demos/numbers.json]"""
import argparse, json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; WEB = ROOT / "studio" / "web"; OUT = ROOT / "docs" / "demos" / "numbers.json"
VIDEO, AUDIO, MODEL3D, IMAGE = {".mp4", ".webm", ".mov"}, {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".opus"}, {".glb", ".ply", ".splat"}, {".webp", ".png", ".jpg", ".jpeg", ".gif"}
NOT_RENDERS = ("icons", "vendor", "mesh_tools", "site_examples", "pack_lab_demos")      # UI icons, third-party code, tool icons, screenshots of built websites, an empty demo folder
STILL = re.compile(r"poster|thumb|sheet|guide", re.I)


def get(base, path, timeout=120):
    with urllib.request.urlopen(base.rstrip("/") + path, timeout=timeout) as r: return json.load(r)


def tabs_in_shell():
    """The fixed tabs: the TABS list in studio/web/app.js."""
    src = (WEB / "app.js").read_text(encoding="utf-8"); m = re.search(r"const TABS = (\[\[.*?\]\]);", src)
    return json.loads(m.group(1))


def rendered_media():
    """Rendered files in studio/web, by folder. A video's poster frame, a contact sheet, a thumbnail or a guide image is a still of something already counted, so it isn't counted again."""
    by = {}
    for d in sorted(p for p in WEB.iterdir() if p.is_dir() and p.name not in NOT_RENDERS):
        n = 0
        for root, _, files in os.walk(d):
            stems = {os.path.splitext(f)[0] for f in files if os.path.splitext(f)[1].lower() in VIDEO | AUDIO | MODEL3D}
            for f in files:
                s, e = os.path.splitext(f); e = e.lower(); base = re.sub(r"(\.poster|_poster|_thumb|\.thumb)$", "", s)
                if e in VIDEO | AUDIO | MODEL3D: n += 1
                elif e in IMAGE and not (base in stems or STILL.search(s) or (d.name == "commercials" and re.match(r"shot\d", s))): n += 1
        if n: by[d.name] = n
    return by


def families_with_render():
    """The Families page's own figure, "rendered by the author": families whose last test level is render. Also how many have a render's media shipped."""
    fams = json.loads((ROOT / "studio" / "family_status.json").read_text(encoding="utf-8"))["families"]
    media = [name for name, f in fams.items() if any((WEB / m["src"]).is_file() for m in f.get("media") or [])]
    return sum(1 for f in fams.values() if f.get("level") == "render"), len(fams), len(media)


def crew_notes():
    return sorted(str(p.relative_to(ROOT / "studio" / "crew_notes")) for p in (ROOT / "studio" / "crew_notes").rglob("*.md") if p.name != "README.md")


def file_counts():
    """Every figure that needs no server, so the tests can recount them."""
    fam, fam_all, fam_media = families_with_render(); media = rendered_media(); recipes = json.loads((ROOT / "studio" / "recipe_renders.json").read_text(encoding="utf-8"))["renders"]
    runs = sorted(p.parent.name for p in (WEB / "pipelines").glob("*/proof.json"))
    return {"families_with_render": fam, "families_listed": fam_all, "families_with_media": fam_media, "rendered_media": sum(media.values()), "rendered_media_by_folder": media, "recipe_renders": len(recipes),
            "pipelines_with_run": len(runs), "crew_notes": len(crew_notes()), "shell_tabs": len(tabs_in_shell()), "feature_modules": len(list((ROOT / "studio").glob("feature_*.py")))}


def count_tests():
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
    m = re.search(r"(\d+) tests? collected", r.stdout) or re.search(r"^(\d+) tests?", r.stdout, re.M)
    if not m: raise SystemExit("could not read the collected test count:\n" + r.stdout[-800:])
    return int(m.group(1))


def build(studio, comfy, tests=None, when=None):
    f = file_counts()
    oi = get(comfy, "/object_info", 300); partner = sum(1 for v in oi.values() if str(v.get("python_module") or "").startswith("comfy_api_nodes"))
    graphs = get(studio, "/api/all-graphs")["counts"]; lib = get(studio, "/api/recipe-library?limit=5000"); pipes = get(studio, "/api/pipelines")
    uni = get(studio, "/api/university")["counts"]; pages = get(studio, "/api/feature-pages")["pages"]
    tests = tests if tests is not None else count_tests()
    n = {
        "as_of": when or time.strftime("%Y-%m-%d"),
        "node_classes": {"value": len(oi) - partner, "all_loaded": len(oi), "partner_api_nodes": partner,
                         "how": "GET /object_info on our ComfyUI 0.43.0 (read-only). value leaves out the partner API nodes (python_module comfy_api_nodes), which the open edition hides; all_loaded counts them too."},
        "families_with_render": {"value": f["families_with_render"], "listed": f["families_listed"], "with_media_shipped": f["families_with_media"],
                                 "how": "studio/family_status.json: families whose test level is render, the figure the Families page shows as rendered by the author. with_media_shipped counts the families with any media file in studio/web, some from a template's own example run."},
        "graphs": {"value": graphs["graph"], "rows": graphs["all"], "by_source": {k: v for k, v in graphs.items() if k not in ("all", "graph", "not_graph")},
                   "how": "GET /api/all-graphs on a studio of this checkout: counts.graph, the rows that open as a ComfyUI graph (goals, family templates, recipes, workflows, motion, voices, 3D). rows also counts the tools that run without a graph."},
        "recipes": {"value": lib["total"], "rendered": lib["rendered"],
                    "how": "GET /api/recipe-library: total recipes in the library, and rendered, the ones with our own passed render shipped (studio/recipe_renders.json)."},
        "pipelines": {"value": len(pipes["pipelines"]), "with_a_run": f["pipelines_with_run"],
                      "how": "GET /api/pipelines: every pipeline the page lists; with_a_run counts studio/web/pipelines/*/proof.json, the ones with a recorded run (passed or partial)."},
        "lessons": {"value": uni["lessons"], "how": "GET /api/university: counts.lessons, the ComfyUniversity lessons."},
        "tabs": {"value": f["shell_tabs"] + len(pages), "shell": f["shell_tabs"], "feature_pages": len(pages),
                 "how": "The TABS list in studio/web/app.js plus GET /api/feature-pages (one page per studio/feature_*.py that has a PAGE)."},
        "rendered_media": {"value": f["rendered_media"], "by_folder": f["rendered_media_by_folder"],
                           "how": "Files in studio/web: every video, sound and 3D file, and every picture that is not a still of one of those (poster frames, contact sheets, thumbnails, guides, and a commercial's shot frames are left out). Folders left out: " + ", ".join(NOT_RENDERS) + "."},
        "crew_notes": {"value": f["crew_notes"], "how": "Markdown notes in studio/crew_notes/ (model family dossiers, studio topics), README.md not counted."},
        "tests": {"value": tests, "how": "python -m pytest --collect-only -q in this checkout: the tests collected."},
    }
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("--studio", default="http://127.0.0.1:8310"); ap.add_argument("--comfy", default="http://127.0.0.1:8188")
    ap.add_argument("--tests", type=int, help="the collected test count, if you already have it"); ap.add_argument("--out", type=Path, default=OUT); a = ap.parse_args(argv)
    n = build(a.studio, a.comfy, a.tests); a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(n, indent=1) + "\n", encoding="utf-8")
    print({k: v["value"] for k, v in n.items() if isinstance(v, dict)}); return 0


if __name__ == "__main__":
    sys.exit(main())
