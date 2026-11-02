"""Each mode's job requests with fakes: which graph, which pass, which words. Every filled graph is also checked offline against ComfyUI's node definitions (a subset saved from object_info)."""
import json
from pathlib import Path

import pytest

from studio.graph_template import fill, placeholders
from studio.vset import shot as SH
from studio.vset.modes import common
from studio.worldkit import library as L
from tests.vset.helpers import FakeStudio, cast_of, good_shot, graph_problems, load_object_info, make_set, run_mode

WF = Path(__file__).parents[2] / "workflows"
#: Weights that are not on the machine the subset was saved on: the Wan graph can only pass once they are added.
ABSENT = ("wan2.2_fun_control", "wan2.2_i2v_lightx2v", "ltx-2.5", "gemma4-12b")


def _check(req, uploads):
    g = json.loads((WF / req["template"]).read_text(encoding="utf-8"))
    assert placeholders(g) <= set(req["values"]), placeholders(g) - set(req["values"])
    bad = graph_problems(fill(g, req["values"]), load_object_info(), uploads=uploads)
    return [b for b in bad if not any(a in b for a in ABSENT)]


def test_mode_a_sends_the_chosen_pass_to_h3_union():
    lib = L.Library()
    ids = make_set(lib, character=True)
    for ctl, shot in (("depth", good_shot(ids, mode="A")), ("pose", good_shot(ids, mode="A", mode_settings={"control": "pose"}, cast=cast_of(ids)))):
        st, state = run_mode(shot, lib)
        req = st.reqs[-1]
        assert state["state"] == "done" and req["template"] == "vset_h3_union_api.json"
        assert st.uploads == [f"/o/{ctl}.mp4"] and req["values"]["control"] == req["values"]["source"] == f"{ctl}.mp4"
        assert (req["values"]["width"], req["values"]["height"], req["values"]["length"]) == (1344, 768, 124)
        assert req["values"]["seed"] == 4242 and _check(req, st.uploads and [f"{ctl}.mp4"]) == []


def test_mode_a_can_use_wan_fun_control():
    lib = L.Library()
    st, state = run_mode(good_shot(make_set(lib), mode="A", mode_settings={"engine": "wan"}), lib)
    req = st.reqs[-1]
    assert state["state"] == "done" and req["template"] == "vset_wan22_funcontrol_api.json"
    assert req["values"]["ref"] == "first.png" and req["values"]["control"] == "depth.mp4" and (req["values"]["width"], req["values"]["height"]) == (832, 480)
    assert _check(req, ["first.png", "depth.mp4"]) == []


def test_mode_a_on_ltx_sends_the_clay_pass_and_a_first_frame_that_is_never_grey():
    lib = L.Library()
    s = good_shot(make_set(lib), mode="A", mode_settings={"engine": "ltx"})
    st, state = run_mode(s, lib)
    assert state["state"] == "done" and [r["template"] for r in st.reqs] == ["vset_keyframe_edit_api.json", "vset_ltx25_layout_api.json"]
    req = st.reqs[-1]
    assert req["values"]["layout"] == "clay.mp4" and req["values"]["first"] != "clay.mp4" and (req["values"]["width"], req["values"]["height"], req["values"]["length"]) == (960, 544, 121)
    assert (req["values"]["length"] - 1) % 8 == 0 and req["values"]["width"] * 2 % 64 == 0 and req["values"]["height"] * 2 % 64 == 0      # the card: 8k+1 frames, 1920x1088 out
    assert _check(req, ["clay.mp4", req["values"]["first"]]) == []
    st, state = run_mode(good_shot(make_set(lib), mode="A", mode_settings={"engine": "ltx", "keyframes": "raw"}), lib)
    assert state["state"] == "done" and [r["template"] for r in st.reqs] == ["vset_ltx25_layout_api.json"] and st.reqs[-1]["values"]["first"] == "first.png"


def test_the_ltx_graph_follows_the_cards_two_stages_and_names_no_older_control_lora():
    g = json.loads((WF / "vset_ltx25_layout_api.json").read_text(encoding="utf-8"))
    text = json.dumps(g)
    assert "ltx-2-19b" not in text and "ltx-2.3" not in text and "depth" not in text.lower()
    assert g["lora"]["inputs"]["lora_name"] == "ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors" and g["lora"]["inputs"]["strength_model"] == 1.0
    assert g["ksel"]["inputs"]["sampler_name"] == "euler_ancestral" and g["guid1"]["inputs"]["cfg"] == g["guid2"]["inputs"]["cfg"] == 1.0
    assert len(g["sig1"]["inputs"]["sigmas"].split(",")) - 1 == 8 and len(g["sig2"]["inputs"]["sigmas"].split(",")) - 1 == 3
    assert [g[k]["inputs"]["frame_idx"] for k in ("g1v", "g1s", "g2v", "g2s")] == [0, -1, 0, -1]


def test_mode_b_gives_h3_the_shaded_render_and_the_exact_depth():
    lib = L.Library()
    st, state = run_mode(good_shot(make_set(lib), mode="B"), lib)
    req = st.reqs[-1]
    assert state["state"] == "done" and req["template"] == "vset_h3_union_api.json"
    assert req["values"]["source"] == "shaded.mp4" and req["values"]["control"] == "depth.mp4" and req["values"]["strength"] == 1.0
    assert _check(req, ["shaded.mp4", "depth.mp4"]) == []


def test_the_union_graph_has_no_preprocessor_the_pass_goes_in_as_rendered():
    g = json.loads((WF / "vset_h3_union_api.json").read_text(encoding="utf-8"))
    assert not [n for n in g.values() if "Depth" in n["class_type"]]
    assert g["u2"]["inputs"]["control_video"] == ["d2", 0] and g["d2"]["inputs"]["image"] == ["c2", 0]
    assert g["m1"]["inputs"]["value"] == 1.0


def test_mode_c_edits_both_stills_then_h3_fills_between():
    lib = L.Library()
    s = good_shot(make_set(lib), format={"aspect": "16:9", "seconds": 8})
    st, state = run_mode(s, lib)
    assert state["state"] == "done" and [r["template"] for r in st.reqs] == ["vset_keyframe_edit_api.json", "vset_keyframe_edit_api.json", "h3_fl2v_api.json"]
    first, last, video = st.reqs
    assert first["values"]["image"] == "first.png" and last["values"]["image"] == "last.png" and "Keep the exact framing" in first["values"]["prompt"] and "person" not in first["values"]["prompt"]
    assert video["values"]["image"] == "j1.png" and video["values"]["last_image"] == "j2.png"
    assert video["values"]["aspect"] == "16:9 (Widescreen)" and video["values"]["seconds"] == 8.0 and video["values"]["turbo"] is True
    assert _check(first, ["first.png"]) == [] and _check(video, ["j1.png", "j2.png"]) == []


def test_mode_c_raw_sends_the_blender_stills_straight_to_h3():
    lib = L.Library()
    st, state = run_mode(good_shot(make_set(lib), mode_settings={"keyframes": "raw"}), lib)
    assert state["state"] == "done" and [r["template"] for r in st.reqs] == ["h3_fl2v_api.json"]
    assert st.reqs[0]["values"]["image"] == "first.png" and st.reqs[0]["values"]["last_image"] == "last.png"
    assert {r["name"]: r["status"] for r in state["steps"]}["key_first"] == "skipped"


def test_the_prompt_says_where_the_action_and_the_look_and_who_only_when_there_is_a_cast():
    lib = L.Library()
    ids = make_set(lib, character=True)
    p = common.video_prompt(good_shot(ids), library=lib)
    assert p.startswith("the camera moves down the empty street past the bench.") and "a quiet street" in p and "golden hour" in p and "skin" not in p
    assert common.video_prompt(good_shot(ids, cast=cast_of(ids)), library=lib).startswith("Ada, tall, auburn hair. Fully clothed exactly as described, from start to finish. the camera")


def test_words_from_an_asset_cannot_pass_into_a_job_unchecked():
    lib = L.Library()
    ids = make_set(lib)
    lib.update(ids["place"], name="A nude beach", recipe={})
    st, state = run_mode(good_shot(ids, mode="B"), lib)
    assert state["state"] == "failed" and "safe-for-work" in state["error"] and st.reqs == []


def test_only_the_files_a_mode_uses_are_uploaded():
    lib = L.Library()
    st = FakeStudio()
    run_mode(good_shot(make_set(lib), mode="B"), lib, st)
    assert sorted(st.uploads) == ["/o/depth.mp4", "/o/shaded.mp4"]


@pytest.mark.parametrize("name", ["vset_h3_union_api.json", "vset_wan22_funcontrol_api.json", "vset_keyframe_edit_api.json", "vset_h3_motion_api.json", "vset_ltx25_layout_api.json"])
def test_new_graphs_have_no_private_paths_and_save_under_a_placeholder(name):
    text = (WF / name).read_text(encoding="utf-8")
    assert "/home/" not in text and "/mnt/" not in text and "${prefix}" in text


def test_mode_d_sends_the_shaded_render_as_the_reference_clip_and_opens_with_the_template_rule():
    lib = L.Library()
    s = good_shot(make_set(lib), mode="D", camera={"preset": "orbit"}, format={"aspect": "16:9", "seconds": 8})
    st, state = run_mode(s, lib)
    req = st.reqs[-1]
    assert state["state"] == "done" and req["template"] == "vset_h3_motion_api.json"
    assert req["values"]["template"] == "shaded.mp4" and req["values"]["image"] == "first.png"
    assert (req["values"]["width"], req["values"]["height"], req["values"]["frames"]) == (1344, 768, 192)
    assert req["values"]["prompt"].startswith("The clip opens on a slow orbit around a quiet street")
    assert _check(req, ["shaded.mp4", "first.png"]) == []


def test_the_motion_graph_has_no_character_swap_lora():
    text = (WF / "vset_h3_motion_api.json").read_text(encoding="utf-8")
    assert "character_swap" not in text and "Video Slice" not in text


def test_a_missing_wan_fun_control_never_maps_onto_another_model():
    """resolve_names at a loose threshold would swap it for Fun Camera, because the names are close. A portable job keeps the exact name, so ComfyUI refuses it."""
    from studio import names
    from studio.worldkit import jobs
    g = json.loads((WF / "vset_wan22_funcontrol_api.json").read_text(encoding="utf-8"))
    oi = {"UNETLoader": {"input": {"required": {"unet_name": [["wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors", "wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors"]]}}}}
    out, report = names.resolve_names(g, oi, threshold=jobs.PORTABLE_MATCH)
    assert out["unet_h"]["inputs"]["unet_name"].startswith("wan2.2/wan2.2_fun_control") and report[0]["now"] is None


def test_the_same_file_under_another_folder_still_maps():
    from studio import names
    from studio.worldkit import jobs
    g = {"c": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen/qwen3-vl-32b/qwen3-vl-32b-minimax-h3-nvfp4-awq.safetensors"}}, "l": {"class_type": "L", "inputs": {"lora_name": "minimax_h3/minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors"}}}
    oi = {"CLIPLoader": {"input": {"required": {"clip_name": [["qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"]]}}}, "L": {"input": {"required": {"lora_name": [["minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"]]}}}}
    out, _ = names.resolve_names(g, oi, threshold=jobs.PORTABLE_MATCH)
    assert out["c"]["inputs"]["clip_name"] == "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors" and out["l"]["inputs"]["lora_name"] == "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"


def test_every_job_of_every_mode_is_marked_portable():
    lib = L.Library()
    for kw in (dict(mode="A"), dict(mode="B"), dict(mode="C"), dict(mode="D")):
        st, _ = run_mode(good_shot(make_set(lib), **kw), lib)
        assert st.reqs and all(r["portable"] for r in st.reqs)


def test_every_video_and_keyframe_prompt_carries_the_whole_description_and_the_clothed_line(monkeypatch, tmp_path):
    """A plain body must not reach a video model with no words for its clothes: the wording at the end of a long description used to be cut off at 200 letters."""
    from studio.vset.modes import guide, keyframes, motioncopy, restyle
    from studio.worldkit import steps as S
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    lib = L.Library()
    ids = make_set(lib, character=True)
    tail = "wearing a long sand-coloured coat, a scarf, cargo trousers and scuffed boots"
    desc = "a lean courier in his thirties with a short beard, sun-worn skin and a slow, careful walk that has crossed a good many miles of open ground, " * 2 + tail
    meta = lib.require(ids["char"])
    lib.update(ids["char"], source={**meta["source"], "description": desc})
    assert len(desc) > 200
    seen = []
    def ctx():
        class Out(dict):
            def __contains__(self, k): return True
            def __getitem__(self, k): return {"main": {"path": "x.png"}, "first": {"path": "x.png"}, "last": {"path": "x.png"}, "shaded": {"path": "x.mp4"}, "depth": {"path": "x.mp4"}, "pose": {"path": "x.mp4"}, "clay": {"path": "x.mp4"}}
        return {"outputs": Out(), "to_input": lambda p, stem="": "x", "seed": 1}
    shots = [(keyframes, good_shot(ids, cast=cast_of(ids), mode="C")), (motioncopy, good_shot(ids, cast=cast_of(ids), mode="D")), (restyle, good_shot(ids, cast=cast_of(ids), mode="B")),
             (guide, good_shot(ids, cast=cast_of(ids), mode="A")), (guide, good_shot(ids, cast=cast_of(ids), mode="A", mode_settings={"engine": "ltx"}))]
    for mod, shot in shots:
        for st in mod.steps(shot, library=lib):
            if st.request is None:
                continue
            req = st.request(ctx())
            if req and "prompt" in req["values"]:
                seen.append(st.name)
                assert tail in req["values"]["prompt"] and common.CLOTHED in req["values"]["prompt"], (mod.__name__, st.name)
    assert {"key_first", "key_last", "video"} <= set(seen)
    no_cast = common.video_prompt(good_shot(ids), library=lib)
    assert common.CLOTHED not in no_cast and "mannequin" in keyframes.KEY_NEGATIVE
