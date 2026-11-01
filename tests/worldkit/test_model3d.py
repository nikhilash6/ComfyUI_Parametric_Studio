"""The 3D page's models and World Kit's choice of mesh model. Stubbed: no ComfyUI, no GPU, no live port."""
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from studio import model3d as M
from studio.worldkit import capabilities as C
from studio.worldkit.makers import prop as P


def _need(state="ready"):
    return lambda key: {"key": key, "state": state, "message": f"{key} is {state}"}


def test_every_model_names_a_real_need_and_a_known_way_to_run():
    for m in M.MODELS:
        assert m["need"] in C.NEEDS and m["via"] in ("family", "runner", "tool") and m["job"] in ("mesh_from_image", "mesh_from_text", "relief_from_image", "splat_from_image", "rigged_from_image", "rig", "motion")
        if m["via"] == "runner": assert (M.RUNNERS / m["runner"]).is_file()


def test_a_model_nobody_ran_says_so_and_one_not_here_says_why(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "PROOF", tmp_path / "none.json")
    row = next(x for x in M.listing(_need("missing")) if x["id"] == "shap_e")
    assert row["proof"] == {"status": "not run"} and row["ready"] is False and "missing" in row["why_not"]


def test_recorded_proof_is_shown(tmp_path, monkeypatch):
    p = tmp_path / "p.json"; p.write_text(json.dumps({"triposr": {"status": "ran", "seconds": 19.0, "peak_gib": 3.5}})); monkeypatch.setattr(M, "PROOF", p)
    assert next(x for x in M.listing(_need()) if x["id"] == "triposr")["proof"]["seconds"] == 19.0


def test_an_unknown_model_is_a_404():
    with pytest.raises(HTTPException): M.model("nope")


def test_a_text_job_needs_words(tmp_path):
    with pytest.raises(ValueError): M.execute(M.model("shap_e"), {"prompt": "  "}, tmp_path, runner=lambda *a: None)


def test_a_runner_job_passes_prompt_and_seed(tmp_path):
    seen = {}
    def run(m, args, out, log): seen.update(args=args, out=out); return out
    out = M.execute(M.model("shap_e"), {"prompt": "a  chair", "seed": 3}, tmp_path, runner=run)
    assert seen["args"] == ["--prompt", "a chair", "--seed", 3] and Path(out).suffix == ".glb" and Path(out).parent.name == "3d"


def test_sam3d_refuses_a_picture_with_no_cutout(tmp_path, monkeypatch):
    from PIL import Image
    p = tmp_path / "a.png"; Image.new("RGB", (4, 4)).save(p); monkeypatch.setattr(M, "_input_picture", lambda n: p)
    with pytest.raises(ValueError): M._cutout_or_refuse({"image": "a.png"})


def test_prop_recipe_takes_a_known_mesh_model_only():
    assert P.recipe({"mesh_model": "trellis2"}, "chair")[1] == []
    assert P.recipe({"mesh_model": "nope"}, "chair")[1]


def test_words_to_mesh_skips_the_picture_and_the_cutout(tmp_path):
    meta = {"id": "a", "name": "chair", "source": {"kind": "text", "prompt": "a chair"}, "recipe": {"mesh_model": "shap_e"}}
    st = {s.name: s for s in P.steps(meta)}
    assert st["image"].request({"outputs": {}}) is None and st["cutout"].request({"outputs": {}}) is None
    seen = []
    out = st["mesh"].local({"outputs": {}, "work": tmp_path, "runner": lambda r, a, w: seen.append((r, a)) or tmp_path / "m.glb"})
    assert seen[0][0] == "shap_e" and seen[0][1][:2] == ["--prompt", "a chair"] and out["main"]["route"] == "shap_e"


def test_a_chosen_picture_model_beats_the_default(tmp_path, monkeypatch):
    pic = tmp_path / "p.png"; pic.write_bytes(b"x")
    meta = {"id": "a", "name": "bear", "source": {"kind": "image", "image": "p.png"}, "recipe": {"mesh_model": "triposr"}}
    monkeypatch.setattr(P, "picture_path", lambda n: pic)
    st = {s.name: s for s in P.steps(meta)}; seen = []
    out = st["mesh"].local({"outputs": {}, "work": tmp_path, "mesh_route": lambda: "sam3d_objects", "runner": lambda r, a, w: seen.append(r) or tmp_path / "m.glb"})
    assert seen == ["triposr"] and out["main"]["route"] == "triposr"


def test_a_cut_out_goes_to_a_family_on_white_and_a_plain_picture_as_it_is(tmp_path):
    from PIL import Image
    from studio.worldkit import jobs
    a = tmp_path / "a.png"; Image.new("RGBA", (2, 2), (9, 9, 9, 0)).save(a); b = tmp_path / "b.png"; Image.new("RGB", (2, 2)).save(b)
    assert jobs._matte_on_white(a, tmp_path / "o.png") and Image.open(tmp_path / "o.png").getpixel((0, 0)) == (255, 255, 255)
    assert not jobs._matte_on_white(b, tmp_path / "p.png")


def test_anigen_lends_only_rtree_and_reads_the_file_it_made(tmp_path, monkeypatch):
    from studio.worldkit import tools as T
    monkeypatch.setattr(T, "require", lambda k: None); monkeypatch.setattr(T, "vram_gate", lambda k: None); pic = tmp_path / "bear.png"; pic.write_bytes(b"x"); seen = {}
    def run(cmd, log, timeout):
        seen["cmd"] = [str(c) for c in cmd]; d = tmp_path / "w" / "anigen" / "bear"; d.mkdir(parents=True); (d / "mesh.glb").write_bytes(b"glb"); return 0
    out = T.anigen(pic, tmp_path / "w", seed=3, run=run)
    assert out.name == "mesh.glb" and "--seed" in seen["cmd"] and str(pic) in seen["cmd"] and seen["cmd"][seen["cmd"].index("--seed") + 1] == "3"
    assert not [c for c in seen["cmd"] if c.startswith("PYTHONPATH=") and "rtree_only" not in c]
