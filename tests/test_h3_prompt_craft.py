"""The H3 scenes recipe file and the H3 crew guide: every scene follows the official H3 shape and the studio's own rules, and the guide passes the label checker."""
import importlib.util, json, re
from pathlib import Path

from psn.camera import camera_moves
from studio import recipes as R, sfw

ROOT = Path(__file__).resolve().parents[1]
SCENES = json.loads((ROOT / "studio" / "recipe_library" / "h3_scenes.json").read_text(encoding="utf-8"))["recipes"]
GUIDE = ROOT / "studio" / "crew_notes" / "model_families" / "16-MiniMax-H3" / "dossier" / "GUIDE.md"
FIELDS = ("integrated_multimodal_description: ", "\n\noverall_soundscape: ", "\n\nnon_diegetic_music: ")


def filled(r):
    step = r["steps"][0]; vals = {f["key"]: f["default"] for f in r["fields"]}
    return R.goal_body(step, vals)


def test_ten_scenes_in_the_apps_own_format():
    assert len(SCENES) == 10 and R.validate({"recipes": SCENES}) == []
    ids = {r["id"] for r in R.library()}
    assert all(r["id"] in ids for r in SCENES)
    assert all(r["proof"]["level"] == "recipe" and "Never rendered" in r["proof"]["note"] for r in SCENES)


def test_each_scene_is_one_h3_shot_inside_the_goal_limits():
    from studio import goals
    g = goals.GOALS["h3_video"]
    for r in SCENES:
        assert len(r["steps"]) == 1, r["id"]; s = r["steps"][0]
        assert s["goal"] == "h3_video" and s["options"]["seconds"] in g["options"]["seconds"] and s["options"]["aspect"] in g["options"]["aspect"], r["id"]


def test_the_official_three_fields_in_order():
    for r in SCENES:
        p = filled(r)["prompt"]; at = [p.index(f) for f in FIELDS]
        assert at == sorted(at) and at[0] == 0, r["id"]
        for f in FIELDS: assert p.count(f.strip()) == 1, (r["id"], f)
        assert "{" not in p, r["id"]
        assert not sfw.flagged(p), r["id"]


def test_shots_one_move_each_and_cut_times_that_only_go_up():
    for r in SCENES:
        desc = filled(r)["prompt"].split("\n\noverall_soundscape:")[0]
        shots = re.split(r"\[Shot \d+\]", desc)[1:]
        assert shots and not re.match(r"\s*At \d", shots[0]), r["id"]            # shot 1 has no time
        times = [int(m) * 60 + float(s) for m, s in re.findall(r"\[Shot \d+\] At (\d\d):(\d\d\.\d{3}), the (?:camera|shot) cuts to", desc)]
        assert len(times) == len(shots) - 1 and times == sorted(times) and all(0 < t < r["steps"][0]["options"]["seconds"] for t in times), r["id"]
        for shot in shots: assert len(camera_moves(shot)) <= 1, (r["id"], shot, camera_moves(shot))


def test_dialogue_fits_the_time_and_every_voice_is_described():
    for r in SCENES:
        desc = filled(r)["prompt"]; lines = re.findall(r"<d>\[English\] (.*?)</d>", desc)
        assert desc.count("<d>") == len(lines), r["id"]                       # every line is tagged with its language
        words = sum(len(x.split()) for x in lines)
        assert words <= 2.6 * r["steps"][0]["options"]["seconds"], (r["id"], words)
        for m in re.finditer(r"\((S\d)\)", desc):
            before = desc[max(0, m.start() - 80):m.start()]
            assert re.search(r"voice|narrator", before), (r["id"], before)      # never a bare (S1)


def test_the_guide_passes_the_label_checker_and_credits_the_official_guides():
    spec = importlib.util.spec_from_file_location("ccn", ROOT / "scripts" / "check_crew_notes.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert GUIDE in m.note_files(ROOT)
    assert m.check_file(ROOT, GUIDE) == []
    text = GUIDE.read_text(encoding="utf-8")
    for url in ("VIDEO_PROMPT_WRITING_GUIDE_base_en.md", "VIDEO_PROMPT_WRITING_GUIDE_ref_en.md", "docs.comfy.org/tutorials/video/minimax/minimax-h3-prompt-guide"):
        assert url in text, url
    assert "studio/recipe_library/h3_scenes.json" in text


def test_the_video_family_guides_are_checked_and_cite_their_official_sources():
    spec = importlib.util.spec_from_file_location("ccn", ROOT / "scripts" / "check_crew_notes.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    fam = ROOT / "studio" / "crew_notes" / "model_families"
    want = {"30-Wan-2.2": ("alibabacloud.com/help/en/model-studio/text-to-video-prompt", "github.com/Wan-Video/Wan2.2"),
            "15-LTX-Video-LTX-2": ("huggingface.co/Lightricks/LTX-2.5", "docs.ltx.io"),
            "07-DreamX-Creator": ("arxiv.org/html/2608.31106", "github.com/AMAP-ML/DreamX-Creator"),
            "12-HunyuanVideo-FramePack": ("github.com/Tencent-Hunyuan/HunyuanVideo-1.5", "HunyuanVideo_1_5_Prompt_Handbook_EN.md")}
    for folder, urls in want.items():
        g = fam / folder / "dossier" / "GUIDE.md"
        assert g in m.note_files(ROOT) and m.check_file(ROOT, g) == [], folder
        text = g.read_text(encoding="utf-8")
        for u in urls: assert u in text, (folder, u)
