"""The "how big is it" demos: every figure they show is in docs/demos/numbers.json and is no more than this tree has, every label matches the clip's own record, and the web copies stay small."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; WEB = ROOT / "studio" / "web"; DEMOS = ROOT / "docs" / "demos"; MEDIA = ROOT / "docs" / "media"
sys.path.insert(0, str(ROOT / "scripts"))
import build_demo_numbers as N      # noqa: E402
import build_demo_videos as V      # noqa: E402

NUMS = json.loads((DEMOS / "numbers.json").read_text(encoding="utf-8"))
WEB_FILES = {"demo_reel.mp4": 10e6, "demo_wall.mp4": 6e6, "demo_tour.mp4": 9e6, "demo_tour_phone.mp4": 4e6, "demo_reel.webp": 400e3, "demo_wall.webp": 400e3, "demo_tour.webp": 400e3}


def test_every_figure_says_how_it_was_counted():
    for key, label in V.STATS:
        n = NUMS[key]; assert isinstance(n["value"], int) and n["value"] > 0 and len(n["how"]) > 40, key
    assert re.fullmatch(r"\d{4}-\d\d-\d\d", NUMS["as_of"])


def test_no_figure_is_more_than_the_tree_has():
    """Recounted from the files: a later merge can only make a claim more modest, never false."""
    f = N.file_counts()
    assert NUMS["families_with_render"]["value"] <= f["families_with_render"]
    assert NUMS["rendered_media"]["value"] <= f["rendered_media"]
    assert NUMS["crew_notes"]["value"] <= f["crew_notes"]
    assert NUMS["pipelines"]["with_a_run"] <= f["pipelines_with_run"]
    assert NUMS["recipes"]["rendered"] <= f["recipe_renders"]
    pages = sum(1 for p in (ROOT / "studio").glob("feature_*.py") if re.search(r"^PAGE\s*=", p.read_text(encoding="utf-8"), re.M))
    assert NUMS["tabs"]["shell"] <= f["shell_tabs"] and NUMS["tabs"]["feature_pages"] <= pages and NUMS["tabs"]["value"] == NUMS["tabs"]["shell"] + NUMS["tabs"]["feature_pages"]
    assert NUMS["node_classes"]["value"] == NUMS["node_classes"]["all_loaded"] - NUMS["node_classes"]["partner_api_nodes"]


def test_reel_labels_match_each_clips_own_record():
    edl = json.loads((DEMOS / "reel_edl.json").read_text(encoding="utf-8")); rr = json.loads((ROOT / "studio" / "recipe_renders.json").read_text())["renders"]
    fam = json.loads((ROOT / "studio" / "family_status.json").read_text())["families"]; chapters = {c["chapter"] for c in edl["clips"]}
    assert 60 <= edl["clips"][-1]["end"] + edl["close_seconds"] <= 90 and len(chapters) >= 10
    for c in edl["clips"]:
        src = c["src"]; assert 0.6 <= (c["end"] - c["start"]) <= 2.0, src
        if src.startswith(("film:", "ui:")): continue
        assert (WEB / src).is_file() or (ROOT / src).is_file(), src
        if src.startswith("recipe_renders/"):
            r = rr[Path(src).stem]
            for m in str(r["model"]).split(","):
                if V.friendly(m).lower() not in ("none", "made on the cpu"): assert V.friendly(m) in c["main"], (src, m)
            assert Path(src).stem in c["sub"]
        elif src.startswith("families/"):
            m = next(m for f in fam.values() for m in f.get("media") or [] if m["src"] == src); assert m["own"] and f"template {m['tpl']}" in c["sub"], src
        elif src.startswith("pipelines/"):
            p = json.loads((WEB / "pipelines" / src.split("/")[1] / "proof.json").read_text()); assert p["run"] in c["sub"] and p["final"]["src"] == src.split("/")[-1]
            assert all(s["model"] in c["main"] for s in p["stages"] if s["model"] != "ffmpeg"), src
        elif src.startswith("commercials/"):
            assert "invented brand" in c["sub"]
        elif "wren" in src:
            assert "before this studio" in c["sub"]


def test_the_wall_is_one_hundred_different_renders_and_counts_to_the_real_total():
    w = json.loads((DEMOS / "wall_tiles.json").read_text())
    srcs = [t["src"] for t in w["tiles"]]; assert len(srcs) == 100 == len(set(srcs)) and all((WEB / s).is_file() for s in srcs)
    assert w["counter_to"] == NUMS["rendered_media"]["value"]


def test_the_tour_visits_every_tab():
    t = json.loads((DEMOS / "tour_edl.json").read_text()); assert len(t["tabs"]) == NUMS["tabs"]["value"] and 60 <= t["tabs"][-1]["cut_end"] <= 120
    p = json.loads((DEMOS / "tour_phone_edl.json").read_text()); assert len(p["tabs"]) == 8


def test_soundtracks_are_the_studios_own_music_levelled():
    for f in ("reel_edl.json", "wall_tiles.json", "tour_edl.json", "tour_phone_edl.json"):
        m = json.loads((DEMOS / f).read_text())["music"]; assert abs(m["lufs"] + 16) <= 0.5 and m["true_peak_db"] <= -1.5 and "made in the studio" in m["credit"], f


def test_web_copies_are_small_and_the_readme_shows_them():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name, cap in WEB_FILES.items():
        p = MEDIA / name; assert p.is_file() and p.stat().st_size < cap, (name, p.stat().st_size if p.is_file() else None)
        assert f"docs/media/{name}" in readme, name
    assert "See how big it is" in readme and readme.index("See how big it is") < readme.index("## For the judges")
