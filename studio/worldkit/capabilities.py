"""What each maker needs and whether this machine has it, from a real file check on every call (models arrive by download while the studio runs).
A file counts only at its full size: a 0-byte placeholder, a hash sidecar or a partial file is not a model. Names are relative to the models root.
Each requirement reports ready, downloading (a partial is there) or missing, and the UI shows that sentence as it stands."""
from __future__ import annotations

import os
import re
from pathlib import Path

from psn import paths

GB = 1_000_000_000
BLENDER = {"label": "Blender", "tool": "blender"}


def _anywhere(kind: str, name: str, least: int) -> list:
    """A MiniMax H3 file's usual places: the download folder, its minimax_h3 sub-folder and the assembled pipeline."""
    return [(f"{kind}/{name}", least), (f"{kind}/minimax_h3/{name}", least), (f"_complete_pipelines/MiniMax-H3/{kind}/{name}", least)]


#: label, files [(path under the models root, smallest believable size)], tool (optional)
NEEDS: dict[str, dict] = {
    "image": {"label": "FLUX.2 Klein 4B (the Image goal)", "any": True, "files": [("diffusion_models/flux-2-klein-4b.safetensors", 7 * GB), ("_complete_pipelines/Flux.1/diffusion_models/flux-2-klein-4b.safetensors", 7 * GB)],
              "also": [("text_encoders/qwen_3_4b.safetensors", 7 * GB), ("vae/flux2-vae.safetensors", 300_000_000)]},
    "krea2": {"label": "Krea 2 Turbo (text to image)", "files": [("_complete_pipelines/Krea2/diffusion_models/krea2_turbo_bf16.safetensors", 20 * GB), ("text_encoders/qwen3vl_4b_bf16.safetensors", 8 * GB), ("vae/qwen_image_vae.safetensors", 200_000_000)]},
    "picturecheck": {"label": "Picture check for character sheets", "tool": "picturecheck"},
    "cutout": {"label": "BiRefNet (background cut-out)", "files": [("background_removal/birefnet.safetensors", 100_000_000)]},
    "sam3d_objects": {"label": "SAM 3D Objects", "tool": "sam3d_objects", "files": [
        ("_complete_pipelines/SAM-3D-Objects/checkpoints/ss_generator.ckpt", 6 * GB), ("_complete_pipelines/SAM-3D-Objects/checkpoints/slat_generator.ckpt", 4 * GB),
        ("_complete_pipelines/SAM-3D-Objects/checkpoints/slat_decoder_mesh.ckpt", 300_000_000), ("_complete_pipelines/SAM-3D-Objects/checkpoints/ss_decoder.ckpt", 100_000_000),
        ("_complete_pipelines/SAM-3D-Objects/checkpoints/slat_decoder_gs.ckpt", 100_000_000), ("_libraries/models-legacy-layout/3d/sam-3d-objects/checkpoints/slat_decoder_gs_4.ckpt", 100_000_000),
        ("_libraries/models-legacy-layout/3d/moge-vitl/model.pt", GB), ("_libraries/models-legacy-layout/3d/AniGen/ckpts/dinov2/dinov2_vitl14/dinov2_vitl14_reg4_pretrain.pth", GB)]},
    "pixal3d": {"label": "Pixal3D", "family": ("Pixal3D", "3d_pixal3d_trellis2_image_to_model")},
    "hunyuan3d": {"label": "Hunyuan3D 2", "family": ("Hunyuan3D-2.1", "3d_hunyuan3d_image_to_model")},
    "trellis2": {"label": "TRELLIS.2", "family": ("TRELLIS-2-4B", "trellis2_image_to_mesh")},
    "triposplat": {"label": "TripoSplat", "family": ("TripoSplat", "3d_triposplat_image_to_gaussian_splat")},
    "anigen": {"label": "AniGen (a rigged mesh from a picture)", "tool": "anigen", "files": [("_libraries/models-legacy-layout/3d/AniGen/ckpts/anigen/ss_flow_solo/ckpts/denoiser.pt", 2 * GB), ("_libraries/models-legacy-layout/3d/AniGen/ckpts/anigen/slat_flow_auto/ckpts/denoiser.pt", 2 * GB), ("_libraries/models-legacy-layout/3d/AniGen/ckpts/dsine/dsine.pt", 250_000_000)]},
    "moge": {"label": "MoGe 2", "family": ("MoGe", "3d_moge_perspective_to_mesh")},
    "triposr": {"label": "TripoSR", "tool": "triposr", "files": [("_complete_pipelines/TripoSR/checkpoints/model.ckpt", GB)]},
    "shap_e": {"label": "Shap-E (words to mesh)", "files": [("3d/shap-e/prior/diffusion_pytorch_model.fp16.safetensors", 500_000_000), ("3d/shap-e/shap_e_renderer/diffusion_pytorch_model.bin", 700_000_000), ("text_encoders/clip-vit-large-patch14.safetensors", 1_000_000_000)]},
    "trellis2_main": {"label": "TRELLIS.2 on the main ComfyUI (a character's mesh)", "files": [("diffusion_models/3d/trellis_2_int8_convrot.safetensors", 2 * GB), ("vae/trellis_2_shape_vae_bf16.safetensors", 100_000_000), ("vae/trellis_2_texture_vae_bf16.safetensors", 100_000_000), ("text_encoders/dino_v3_L_naf_fp32.safetensors", 500_000_000), ("background_removal/birefnet.safetensors", 100_000_000)]},
    "sam3d_body": {"label": "SAM 3D Body", "files": [("detection/sam_3d_body_dinov3_bf16.safetensors", 2 * GB), ("checkpoints/SAM 3.1/sam3.1_multiplex_fp16.safetensors", GB), ("geometry_estimation/moge_2_vitl_normal_fp16.safetensors", 500_000_000)]},
    "skintokens": {"label": "SkinTokens (rig)", "tool": "skintokens", "files": [
        ("_libraries/models-legacy-layout/3d/SkinTokens/experiments/articulation_xl_quantization_256_token_4/grpo_1400.ckpt", GB),
        ("_libraries/models-legacy-layout/3d/SkinTokens/experiments/skin_vae_2_10_32768/last.ckpt", 400_000_000)]},
    "unirig": {"label": "UniRig (not wired: weights only, no runner here)", "files": [("_complete_pipelines/UniRig/checkpoints/skeleton.safetensors", GB), ("_complete_pipelines/UniRig/checkpoints/skin.safetensors", GB)], "tool": "unirig"},
    "autoremesher": {"label": "AutoRemesher (CPU tool, optional)", "tool": "autoremesher"},
    "kimodo": {"label": "Kimodo (text to motion)", "tool": "kimodo", "files": [("_libraries/models-legacy-layout/motion/kimodo/Kimodo-SOMA-RP-v1.1/model.safetensors", GB),
        ("_libraries/models-legacy-layout/motion/text-encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp/adapter_model.safetensors", 100_000_000), ("_libraries/models-legacy-layout/motion/text-encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised/adapter_model.safetensors", 100_000_000),
        ("_by_repo/NousResearch__Meta-Llama-3-8B-Instruct/model-00001-of-00004.safetensors", 4 * GB), ("_by_repo/NousResearch__Meta-Llama-3-8B-Instruct/model-00002-of-00004.safetensors", 4 * GB),
        ("_libraries/models-legacy-layout/motion/text-encoders/meta-llama/Meta-Llama-3-8B-Instruct/model-00003-of-00004.safetensors", 4 * GB), ("_libraries/models-legacy-layout/motion/text-encoders/meta-llama/Meta-Llama-3-8B-Instruct/model-00004-of-00004.safetensors", GB)]},
    "retarget": {"label": "Blender retarget tool", "tool": "retarget"},
    # Virtual Set. Each lists the places the file may be: this studio's download folders and the shared layout of a pipeline folder.
    "h3_fl2va": {"label": "MiniMax H3 first and last frame", "any": True, "files": _anywhere("diffusion_models", "minimax_h3_fl2va_pruned_int8_convrot.safetensors", 20 * GB)},
    "h3_fl2va_nvfp4": {"label": "MiniMax H3 base for depth control (FL2VA nvfp4)", "any": True, "files": _anywhere("diffusion_models", "MiniMax_H3_FL2VA_pruned_nvfp4.safetensors", 12 * GB)},
    "h3_ref2va": {"label": "MiniMax H3 reference to video", "any": True, "files": _anywhere("diffusion_models", "minimax_h3_ref2va_pruned_int8_convrot.safetensors", 20 * GB)},
    "h3_union": {"label": "MiniMax H3 Fun Union 2.0 (depth and pose control)", "any": True, "files": [("model_patches/minimax_h3_fun_controlnet_union_2.0_pruned_bf16.safetensors", 8 * GB), ("model_patches/minimax_h3/minimax_h3_fun_controlnet_union_2.0_pruned_bf16.safetensors", 8 * GB), ("_complete_pipelines/MiniMax-H3/controlnet/minimax_h3_fun_controlnet_union_2.0_pruned_bf16.safetensors", 8 * GB)]},
    "h3_turbo": {"label": "MiniMax H3 first and last frame turbo LoRA", "any": True, "files": [*_anywhere("loras", "minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors", GB), ("loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", GB)]},
    "h3_text": {"label": "MiniMax H3 text encoder", "any": True, "files": [("text_encoders/qwen/qwen3-vl-32b/qwen3-vl-32b-minimax-h3-nvfp4-awq.safetensors", 15 * GB), ("text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", 15 * GB), ("_complete_pipelines/MiniMax-H3/text_encoders/qwen3-vl-32b-minimax-h3-nvfp4-awq.safetensors", 15 * GB)]},
    "h3_vae": {"label": "MiniMax H3 video VAE", "any": True, "files": _anywhere("vae", "minimax_h3_video_vae_fp16.safetensors", 5 * GB)},
    "h3_audio_vae": {"label": "MiniMax H3 audio VAE", "any": True, "files": _anywhere("vae", "minimax_h3_audio_vae_fp32.safetensors", 500_000_000)},
    "qwen21": {"label": "Qwen-Image 2.1 (keyframe edit)", "any": True, "files": [("diffusion_models/qwen_image_2.1_bf16.safetensors", 14 * GB), ("_complete_pipelines/Qwen-Image-2.1/diffusion_models/qwen_image_2.1_bf16.safetensors", 14 * GB)]},
    "qwen21_text": {"label": "Qwen-Image 2.1 text encoder", "any": True, "files": [("text_encoders/qwen3vl_8b_bf16.safetensors", 17 * GB), ("_complete_pipelines/Qwen-Image-2.1/text_encoders/qwen3vl_8b_bf16.safetensors", 17 * GB)]},
    "qwen21_vae": {"label": "Qwen-Image 2.1 VAE", "any": True, "files": [("vae/qwen/qwen_image_2.1_vae_bf16.safetensors", 600_000_000), ("vae/qwen_image_2.1_vae_bf16.safetensors", 600_000_000), ("_complete_pipelines/Qwen-Image-2.1/vae/qwen_image_2.1_vae_bf16.safetensors", 600_000_000)]},
    "wan_fun_high": {"label": "Wan 2.2 Fun Control (high noise)", "any": True, "files": [("diffusion_models/wan2.2/wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors", 10 * GB), ("_complete_pipelines/Wan2.2/diffusion_models/wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors", 10 * GB)]},
    "wan_fun_low": {"label": "Wan 2.2 Fun Control (low noise)", "any": True, "files": [("diffusion_models/wan2.2/wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors", 10 * GB), ("_complete_pipelines/Wan2.2/diffusion_models/wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors", 10 * GB)]},
    "wan_lightx2v_high": {"label": "Wan 2.2 lightx2v LoRA (high noise)", "any": True, "files": [("loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", 500_000_000), ("loras/wan/accel/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", 500_000_000), ("_complete_pipelines/Wan2.1/loras/accel/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", 500_000_000)]},
    "wan_lightx2v_low": {"label": "Wan 2.2 lightx2v LoRA (low noise)", "any": True, "files": [("loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", 500_000_000), ("loras/wan/accel/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", 500_000_000), ("_complete_pipelines/Wan2.1/loras/accel/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", 500_000_000)]},
    "wan_text": {"label": "Wan text encoder (UMT5)", "any": True, "files": [("text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", 6 * GB)]},
    "wan_vae": {"label": "Wan 2.1 VAE", "any": True, "files": [("vae/wan_2.1_vae.safetensors", 200_000_000)]},
    # LTX-2.5 Layout to Render. No depth or pose control exists for 2.5: the LTX 2 (19b) and 2.3 control LoRAs are other models and are not listed here on purpose.
    "ltx25": {"label": "LTX-2.5 22B distilled", "any": True, "files": [("diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors", 15 * GB), ("_complete_pipelines/LTX-2.5/diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors", 15 * GB)]},
    "ltx25_text": {"label": "LTX-2.5 Gemma text encoder", "any": True, "files": [("text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors", 10 * GB), ("_complete_pipelines/LTX-2.5/text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors", 10 * GB)]},
    "ltx25_vae": {"label": "LTX-2.5 video VAE", "any": True, "files": [("vae/ltx-2.5-video-vae-conv-bf16.safetensors", GB), ("_complete_pipelines/LTX-2.5/vae/ltx-2.5-video-vae-conv-bf16.safetensors", GB)]},
    "ltx25_upscaler": {"label": "LTX-2.5 x2 latent upscaler", "any": True, "files": [("latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors", 900_000_000), ("_complete_pipelines/LTX-2.5/upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors", 900_000_000)]},
    "ltx25_layout": {"label": "LTX-2.5 Layout to Render IC-LoRA", "any": True, "files": [("loras/ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors", 1_200_000_000), ("loras/ltx/ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors", 1_200_000_000)]},
}
#: What each way of making something needs. A place's textures are not listed: with no image model it uses procedural ones.
ROUTES = {"place": [], "look": [], "prop_mesh": [], "prop_image": ["cutout", "mesh"], "prop_text": ["text_image", "cutout", "mesh"],
          "character_sheet": ["krea2", "picturecheck"], "character": ["krea2", "picturecheck", "trellis2_main", "skintokens", "kimodo", "retarget"]}
MESH_ROUTES = ("sam3d_objects", "trellis2", "pixal3d", "hunyuan3d", "triposr")
TEXT_MESH_ROUTES = ("shap_e",)
TEXT_IMAGE_ROUTES = ("image", "krea2")
PARTIAL = (".part", ".tmp", ".incomplete", ".partial", ".aria2", ".lock")


def models_root() -> Path:
    return Path(paths.models_root())


def tool_home(tool: str) -> Path:
    """A tool's folder: STUDIO_TOOL_<NAME>, or under the home folder where the earlier studio's installers put it."""
    default = {"sam3d_objects": paths.home("tools", "sam3d-objects"), "skintokens": paths.home("tools", "skintokens"), "autoremesher": paths.home("tools", "autoremesher"),
               "kimodo": paths.home("tools", "kimodo"), "retarget": paths.home("tools", "blender-retarget"), "unirig": paths.home("ai", "UniRig"), "picturecheck": paths.home("tools", "picturecheck"),
               "anigen": paths.home("tools", "anigen"), "triposr": os.path.join(paths.setting("PSN_REPO_LIB", default=paths.home("nodepack_library", "repos")), "MixLabPro__comfyui-mixlab-nodes", "nodes", "tsr")}[tool]
    return Path(os.path.expanduser(paths.setting(f"STUDIO_TOOL_{tool.upper()}", default=default)))


TOOL_FILES = {"sam3d_objects": ("run_sam3d.sh", ".venv/bin/python"), "skintokens": ("run_skintokens.sh", ".venv/bin/python"), "autoremesher": ("run_autoremesher.sh", "build/autoremesher"),
              "kimodo": ("run_kimodo.sh", ".venv/bin/kimodo_gen"), "retarget": ("retarget.py",), "unirig": ("pp_run.py", ".venv/bin/python"), "picturecheck": ("run_picturecheck.sh",), "triposr": ("system.py", "config.yaml"), "anigen": ("run_anigen.sh", ".venv/bin/python")}
#: Files in a tool's folder that name where it reads its weights from. A launcher that points at a folder that is gone will fail, whatever is on disk elsewhere.
TOOL_ENV = {"sam3d_objects": ("env.sh",), "skintokens": ("run_skintokens.sh",), "kimodo": ("env.sh",)}
_ENV_PATH = re.compile(r"""(?:^|[\s;])(?:export\s+)?(?:\w*(?:WEIGHTS|MOGE|DINOV2_REPO|CHECKPOINT_DIR|TEXT_ENCODERS_DIR)\w*|W)=["']?(/[^\s"';]+)""", re.M)


def tool_problem(tool: str) -> str:
    """"" when a tool's runner is installed and its launcher points at folders that exist."""
    home = tool_home(tool)
    for rel in TOOL_FILES[tool]:
        if not (home / rel).exists():
            return f"its runner is not installed ({rel} is missing in {home})"
    for rel in TOOL_ENV.get(tool, ()):
        try:
            text = (home / rel).read_text(errors="replace")
        except OSError:
            continue
        for found in _ENV_PATH.findall(text):
            if not Path(found).exists() and not Path(found).parent.exists():
                return f"its launcher ({rel}) reads weights from {found}, which does not exist; it has to be pointed at the models folder"
    return ""


def file_state(rel: str, least: int, root: Path | None = None) -> str:
    """ready, downloading or missing, for one model file."""
    p = (root or models_root()) / rel
    try:
        if p.is_file() and p.stat().st_size >= least:
            return "ready"
        if p.exists() and p.stat().st_size > 0:
            return "downloading"
    except OSError:
        return "missing"
    try:
        names = os.listdir(p.parent)
    except OSError:
        return "missing"
    return "downloading" if any(n.startswith(p.name) and n.endswith(PARTIAL) for n in names) else "missing"


def _template_state(family: str, template: str) -> dict:
    """A family template's own check: studio/families_api knows which files the template lists and where the instance looks."""
    try:
        from studio import families_api as F
        t = next((x for x in F._meta(family).get("templates", []) if x.get("name") == template), None)
        if t is None:
            return {"state": "missing", "missing": [template], "problem": ""}
        s = F.tpl_state(t, F.scan().get(family, {}))
        return {"state": "ready" if s["ready"] else "missing", "missing": [m["name"] for m in s["missing"]], "problem": ""}
    except Exception as exc:
        return {"state": "missing", "missing": [template], "problem": f"{type(exc).__name__}: {exc}"[:200]}


def need(key: str, root: Path | None = None) -> dict:
    """{key, label, state: ready|downloading|missing|tool, missing: [names], problem, message}."""
    spec = NEEDS[key]
    state, missing, problem = "ready", [], ""
    if spec.get("family"):
        got = _template_state(*spec["family"])
        state, missing, problem = got["state"], got["missing"], got["problem"]
    else:
        files = spec.get("files", [])
        if spec.get("any"):
            states = [file_state(r, n, root) for r, n in files]
            first = "ready" if "ready" in states else "downloading" if "downloading" in states else "missing"
            rows = [(files[0][0], first)]
        else:
            rows = [(r, file_state(r, n, root)) for r, n in files]
        rows += [(r, file_state(r, n, root)) for r, n in spec.get("also", [])]
        missing = [os.path.basename(r) for r, s in rows if s != "ready"]
        if any(s == "downloading" for _, s in rows):
            state = "downloading"
        elif missing:
            state = "missing"
    if spec.get("tool") and spec["tool"] != "blender":
        problem = problem or tool_problem(spec["tool"])
        if problem and state == "ready":
            state = "tool"
    label = spec["label"]
    if state == "ready":
        message = f"{label}: ready"
    elif state == "tool":
        message = f"{label}: the model is here but {problem}"
    else:
        why = "still downloading or incomplete" if state == "downloading" else "still downloading or missing"
        message = f"{label}: model {why} ({', '.join(missing[:4])})" + (f"; also, {problem}" if problem else "")
    return {"key": key, "label": label, "state": state, "missing": missing, "problem": problem, "message": message}


def mesh_route(root: Path | None = None) -> str:
    """The first picture-to-mesh route that is ready, or ""."""
    return next((k for k in MESH_ROUTES if need(k, root)["state"] == "ready"), "")


def text_image_route(root: Path | None = None) -> str:
    """The first text-to-image model that is ready, or ""."""
    return next((k for k in TEXT_IMAGE_ROUTES if need(k, root)["state"] == "ready"), "")


def route(name: str, root: Path | None = None) -> dict:
    """{ready, problems: [plain sentences], needs: [...]} for one way of making something."""
    return route_of(ROUTES[name], root)


def route_of(keys, root: Path | None = None) -> dict:
    rows = []
    for key in keys:
        if key == "mesh":
            options = [need(k, root) for k in MESH_ROUTES]
            ok = next((o for o in options if o["state"] == "ready"), None)
            rows.append(ok or {"key": "mesh", "label": "a picture-to-mesh model", "state": "missing", "missing": [], "problem": "",
                               "message": "Picture to mesh: no model ready yet. " + " ".join(o["message"] + "." for o in options)})
        elif key == "text_image":
            options = [need(k, root) for k in TEXT_IMAGE_ROUTES]
            ok = next((o for o in options if o["state"] == "ready"), None)
            rows.append(ok or {"key": "text_image", "label": "a text-to-image model", "state": "missing", "missing": [], "problem": "",
                               "message": "Text to image: no model ready yet. " + " ".join(o["message"] + "." for o in options)})
        else:
            rows.append(need(key, root))
    return {"ready": all(r["state"] == "ready" for r in rows), "problems": [r["message"] for r in rows if r["state"] != "ready"], "needs": rows}


def blender_problem() -> str:
    from studio.worldkit import blender as B
    import shutil
    p = B.blender_path()
    return "" if Path(p).exists() or shutil.which(p) else "Blender is not installed. World Kit and Virtual Set use it for 3D. Install it (on Ubuntu: sudo snap install blender --classic) and restart the studio, or set STUDIO_BLENDER to where it is."


def comfy_up() -> bool:
    from studio.worldkit import jobs
    try:
        return bool(jobs.server().comfy_up())
    except Exception:
        return False


def textures_generated(root: Path | None = None) -> bool:
    """Whether a place's textures can come from the Image goal now. Otherwise the procedural ones are used."""
    return need("image", root)["state"] == "ready" and comfy_up()


def report() -> dict:
    from studio.worldkit import safety
    blender = blender_problem()
    makers = {n: route(n) for n in ROUTES}
    if blender:
        for n, r in makers.items():
            if n != "character_sheet":          # a sheet is a picture and a check: no Blender in it
                r["ready"], r["problems"] = False, [blender, *r["problems"]]
    why_off = safety.character_problem()
    if why_off:
        for n in ("character", "character_sheet"):
            makers[n].update(ready=False, problems=[why_off, *makers[n]["problems"]])
    return {"blender": blender, "characters_on": not why_off, "gpu": False if not _gpu() else True, "makers": makers, "textures_generated": textures_generated(), "autoremesher": need("autoremesher"), "unirig": need("unirig")}


def _gpu() -> bool:
    from studio.worldkit import blender as B
    return B.gpu_allowed()
