"""The Sampling Lab's latent walk shows only what was rendered and checked here. No test reaches a GPU or a live port."""
import json, re
from pathlib import Path

from fastapi.testclient import TestClient

from studio import sampling_lab as L, sfw

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "studio" / "web"
WALK = json.loads((ROOT / "studio" / "sampling_lab" / "walk.json").read_text(encoding="utf8"))
BOX = ["/" + "mnt/", "/" + "home/"]
CORE = {"CheckpointLoaderSimple", "CLIPTextEncode", "BasicScheduler", "KSamplerAdvanced", "KSampler", "VAEDecode", "SaveImage", "EmptyLatentImage", "ConditioningAverage", "RandomNoise", "CFGGuider", "KSamplerSelect", "SplitSigmas", "SamplerCustomAdvanced"}


def test_every_picture_is_on_disk_and_the_ends_match_an_ordinary_render():
    files = [f["img"] for f in WALK["seed_walk"]["frames"] + WALK["prompt_walk"]["frames"]] + [WALK["blend"]["slerp"], WALK["blend"]["lerp"]] + [x for s in WALK["strip"]["steps"] for x in (s["x"], s["x0"])]
    for f in files: assert (WEB / "sampling_lab" / "walk" / f).is_file(), f
    assert [f["t"] for f in WALK["seed_walk"]["frames"]] == [i / 8 for i in range(9)] and len(WALK["strip"]["steps"]) == WALK["settings"]["steps"]
    assert WALK["seed_walk"]["check"]["t0_vs_plain"] < 3 and WALK["seed_walk"]["check"]["t1_vs_plain"] < 3 and WALK["strip"]["check"]["last_vs_plain"] < 3
    n = WALK["blend"]["noise"]; assert abs(n["norm"]["slerp"] - n["norm"]["a"]) / n["norm"]["a"] < 0.05 and n["norm"]["lerp"] < 0.8 * n["norm"]["a"]


def test_it_was_measured_on_a_lane_of_its_own_with_the_main_comfyuis_nodes():
    m = WALK["measured"]; assert 0 < m["peak_vram_gib"] <= m["declared_gib"] and "--disable-cuda-malloc" in m["flags"]
    used = {n["class_type"] for g in WALK["graphs"].values() for n in g.values()}
    assert used - CORE == {"GenerateNoise", "PSN_LatentSlerp", "PSN_LatentMath"}
    src = (ROOT / "scripts" / "latent_walk_renders.py").read_text(); assert "(8200, 8322)" in src and "gate.acquire" in src and "gate.release" in src


def test_invented_subjects_and_no_box_paths():
    for p in [WALK["seed_walk"]["prompt"], *WALK["prompt_walk"]["prompts"], WALK["strip"]["prompt"]]: assert not sfw.flagged(p)
    t = json.dumps(WALK); assert not any(x in t for x in BOX)


def test_the_view_is_wired_and_the_demo_saves_it(monkeypatch, tmp_path):
    from studio import server as S
    c = TestClient(S.app); assert c.get("/api/sampling/walk").json()["model"]["id"] == "sd15"
    monkeypatch.setattr(L, "DATA", tmp_path); L._cache.pop("walk.json", None); assert c.get("/api/sampling/walk").status_code == 404
    assert '"walk"' in (WEB / "samplinglab_logic.js").read_text() and 'import { Walk } from "./samplinglab_walk.js"' in (WEB / "samplinglab.js").read_text()
    assert '"sampling/walk"' in (ROOT / "scripts" / "build_pages.py").read_text()
    assert not re.search(r"https?://", (WEB / "samplinglab_walk.js").read_text())
