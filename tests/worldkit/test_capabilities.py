from psn import paths
from pathlib import Path
"""The real file check behind 'model still downloading or missing'. No live port: a fake models folder under tmp_path."""
from studio.worldkit import capabilities as C


def _put(root, rel, size):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as fh:
        fh.truncate(size)
    return p


def test_a_file_counts_only_at_its_full_size(tmp_path):
    root = tmp_path / "m"
    assert C.file_state("a/b.ckpt", 100, root) == "missing"
    _put(root, "a/b.ckpt.sha256-ok", 64)
    assert C.file_state("a/b.ckpt", 100, root) == "missing"            # a hash sidecar is not a model
    _put(root, "a/b.ckpt", 0)
    assert C.file_state("a/b.ckpt", 100, root) == "missing"            # nor is a 0-byte placeholder
    _put(root, "a/b.ckpt", 50)
    assert C.file_state("a/b.ckpt", 100, root) == "downloading"
    _put(root, "a/b.ckpt", 100)
    assert C.file_state("a/b.ckpt", 100, root) == "ready"
    _put(root, "c/d.ckpt.part", 10)
    assert C.file_state("c/d.ckpt", 100, root) == "downloading"


def test_the_message_says_it_plainly_and_changes_when_the_files_land(tmp_path, monkeypatch):
    root = tmp_path / "models"
    home = tmp_path / "skin"
    monkeypatch.setenv("STUDIO_TOOL_SKINTOKENS", str(home))
    n = C.need("skintokens")
    assert n["state"] == "missing" and "still downloading or missing" in n["message"] and "grpo_1400.ckpt" in n["message"]
    for rel, size in C.NEEDS["skintokens"]["files"]:
        _put(root, rel, size)
    assert C.need("skintokens")["state"] == "tool" and "runner is not installed" in C.need("skintokens")["message"]
    _put(home, "run_skintokens.sh", 10)
    _put(home, ".venv/bin/python", 10)
    assert C.need("skintokens")["state"] == "ready"


def test_skintokens_has_a_portable_default_and_a_setting_still_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("PSN_SETTINGS", str(tmp_path / "none.env"))
    monkeypatch.delenv("STUDIO_TOOL_SKINTOKENS", raising=False)
    assert C.tool_home("skintokens") == Path(paths.home("tools", "skintokens"))
    monkeypatch.setenv("STUDIO_TOOL_SKINTOKENS", str(tmp_path / "skin"))
    assert C.tool_home("skintokens") == tmp_path / "skin"


def test_a_launcher_pointing_at_a_folder_that_is_gone_is_named(tmp_path, monkeypatch):
    home = tmp_path / "kim"
    monkeypatch.setenv("STUDIO_TOOL_KIMODO", str(home))
    _put(home, "run_kimodo.sh", 10)
    _put(home, ".venv/bin/kimodo_gen", 10)
    (home / "env.sh").write_text(f"export CHECKPOINT_DIR={tmp_path}/gone/models/motion/kimodo   # note\nexport HF_HUB_OFFLINE=1\n")
    assert "reads weights from" in C.tool_problem("kimodo")
    (home / "env.sh").write_text(f"export CHECKPOINT_DIR={tmp_path}/models\n")
    (tmp_path / "models").mkdir(exist_ok=True)
    assert C.tool_problem("kimodo") == ""


def test_a_mesh_route_is_picked_only_when_it_is_truly_ready(tmp_path, monkeypatch):
    home = tmp_path / "sam"
    monkeypatch.setenv("STUDIO_TOOL_SAM3D_OBJECTS", str(home))
    monkeypatch.setattr(C, "_template_state", lambda f, t: {"state": "missing", "missing": [t], "problem": ""})
    assert C.mesh_route() == ""
    assert "no model ready" in C.route("prop_image")["problems"][-1]
    for rel, size in C.NEEDS["sam3d_objects"]["files"]:
        _put(tmp_path / "models", rel, size)
    _put(home, "run_sam3d.sh", 10)
    _put(home, ".venv/bin/python", 10)
    assert C.mesh_route() == "sam3d_objects"
    assert any("BiRefNet" in p for p in C.route("prop_image")["problems"])


def test_the_image_goal_is_ready_from_either_place_it_can_be(tmp_path):
    root = tmp_path / "models"
    assert C.need("image")["state"] == "missing"
    _put(root, "_complete_pipelines/Flux.1/diffusion_models/flux-2-klein-4b.safetensors", 7 * C.GB)
    _put(root, "text_encoders/qwen_3_4b.safetensors", 7 * C.GB)
    _put(root, "vae/flux2-vae.safetensors", 300_000_000)
    assert C.need("image")["state"] == "ready"
    assert C.textures_generated() is False                              # the model is here but nothing answers at the test's ComfyUI address


def test_the_wan_route_turns_ready_on_the_files_where_the_queues_land_them(tmp_path):
    """Names copied from fetch_prio_now_plan.tsv and fetch_small_now_plan.tsv. The graph's own names resolve onto them by the same-model rule."""
    from studio.names import resolve_names
    from studio.vset import needs
    import json
    root = tmp_path / "wan"
    assert C.route_of(needs.ROUTES["A_wan"], root)["ready"] is False
    landed = {"_complete_pipelines/Wan2.2/diffusion_models/wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors": 14296064656,
              "_complete_pipelines/Wan2.2/diffusion_models/wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors": 14296064656,
              "loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors": 1226977424, "loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors": 1226977424,
              "text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors": 6735906897, "vae/wan_2.1_vae.safetensors": 253815318}
    for rel, size in landed.items():
        _put(root, rel, size)
    assert C.route_of(needs.ROUTES["A_wan"], root)["ready"] is True
    g = json.loads((Path(__file__).parents[2] / "workflows" / "vset_wan22_funcontrol_api.json").read_text())
    names = sorted(Path(r).name for r in landed)
    combo = {"UNETLoader": "unet_name", "LoraLoaderModelOnly": "lora_name", "CLIPLoader": "clip_name", "VAELoader": "vae_name"}
    oi = {c: {"input": {"required": {k: [names]}}} for c, k in combo.items()}
    fixed, report = resolve_names(g, oi)
    assert report and all(r["now"] for r in report)                                    # every file name the graph asks for has an installed file of the same model
    assert {fixed[n]["inputs"][combo[fixed[n]["class_type"]]] for n in fixed if fixed[n]["class_type"] in combo} == set(names)


def test_the_ltx_layout_route_reports_missing_until_its_lora_and_upscaler_land(tmp_path):
    from studio.vset import needs
    root = tmp_path / "ltx"
    for key in ("ltx25", "ltx25_text", "ltx25_vae"):
        rel, size = C.NEEDS[key]["files"][0]
        _put(root, rel, size)
    r = C.route_of(needs.ROUTES["A_ltx_raw"], root)
    assert r["ready"] is False and any("Layout to Render" in p and "still downloading or missing" in p for p in r["problems"]) and any("upscaler" in p for p in r["problems"])
    for key in ("ltx25_upscaler", "ltx25_layout"):
        rel, size = C.NEEDS[key]["files"][0]
        _put(root, rel, size)
    assert C.route_of(needs.ROUTES["A_ltx_raw"], root)["ready"] is True
    assert not any("19b" in r or "ltx-2.3" in r for k in needs.LTX_LAYOUT for r, _ in C.NEEDS[k]["files"])
