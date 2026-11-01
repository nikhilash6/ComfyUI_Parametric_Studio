# CU-114 lab: which folder feeds which menu, and how to read what a file is from its tensor names. Standard library only, no real models.
# The table is copied from folder_paths.py and nodes.py in ComfyUI v0.43.0. A run of the real functions on a throw-away folder gave the same menus as part 2.

EXT = {".ckpt", ".pt", ".pt2", ".bin", ".pth", ".safetensors", ".pkl", ".sft"}     # supported_pt_extensions
FOLDERS = {"checkpoints": ["checkpoints"], "diffusion_models": ["unet", "diffusion_models"], "text_encoders": ["text_encoders", "clip"], "vae": ["vae"], "loras": ["loras"], "controlnet": ["controlnet", "t2i_adapter"], "clip_vision": ["clip_vision"], "upscale_models": ["upscale_models"], "embeddings": ["embeddings"]}
LEGACY = {"unet": "diffusion_models", "clip": "text_encoders"}                     # map_legacy
LOADERS = [("CheckpointLoaderSimple", "checkpoints", "MODEL, CLIP, VAE"), ("UNETLoader", "diffusion_models", "MODEL"), ("CLIPLoader", "text_encoders", "CLIP"), ("VAELoader", "vae", "VAE"), ("LoraLoader", "loras", "MODEL, CLIP"), ("ControlNetLoader", "controlnet", "CONTROL_NET"), ("CLIPVisionLoader", "clip_vision", "CLIP_VISION"), ("UpscaleModelLoader", "upscale_models", "UPSCALE_MODEL")]
print(f"{'loader node':<25}{'folder name':<19}{'looks in models/':<28}gives")
for node, name, gives in LOADERS: print(f"{node:<25}{name:<19}{', '.join(FOLDERS[name]):<28}{gives}")

# 2. A menu lists every file with a known extension under any folder of that name, with subfolders in the name.
DISK = ["checkpoints/a.safetensors", "checkpoints/sub/b.ckpt", "checkpoints/c.gguf", "checkpoints/d.txt", "checkpoints/e.sft", "unet/u1.safetensors", "diffusion_models/u2.safetensors", "clip/t1.safetensors", "text_encoders/t2.safetensors", "clip/same.safetensors", "text_encoders/same.safetensors"]
def menu(name):
    name = LEGACY.get(name, name); out = set()
    for folder in FOLDERS[name]:
        for f in DISK:
            if f.startswith(folder + "/") and ("." + f.rsplit(".", 1)[-1]).lower() in EXT: out.add(f[len(folder) + 1:])
    return sorted(out)
def full_path(name, file):
    for folder in FOLDERS[LEGACY.get(name, name)]:
        if f"{folder}/{file}" in DISK: return f"models/{folder}/{file}"
print("\ncheckpoints menu:     ", menu("checkpoints"))
print("diffusion_models menu:", menu("diffusion_models"))
print("text_encoders menu:   ", menu("text_encoders"))
print("same name in two folders loads:", full_path("text_encoders", "same.safetensors"))
print("the old name unet gives the same list:", menu("unet") == menu("diffusion_models"))
assert "c.gguf" not in menu("checkpoints") and "d.txt" not in menu("checkpoints") and "sub/b.ckpt" in menu("checkpoints")
assert menu("unet") == ["u1.safetensors", "u2.safetensors"] and full_path("text_encoders", "same.safetensors") == "models/text_encoders/same.safetensors"

# 3. Read what a file is from its names. Prefixes and keys are those ComfyUI's own loaders look for; the lists are shortened, and the test is ours, not ComfyUI's.
def kind(keys):
    has = lambda s: any(k.startswith(s) for k in keys)
    if has("model.diffusion_model."):
        parts = ["denoiser"] + (["text encoder"] if has("cond_stage_model.") or has("conditioner.") else []) + (["VAE"] if has("first_stage_model.") else [])
        return ("checkpoint" if len(parts) > 1 else "denoiser with a prefix"), parts
    if any(".lora_down." in k or ".lora_A." in k for k in keys): return "LoRA", ["changes to another model"]
    if has("input_blocks.") or has("double_blocks.") or has("blocks."): return "denoiser only", ["denoiser"]
    if has("control_model.") or has("input_hint_block."): return "ControlNet", ["control"]
    if has("text_model.encoder.") or has("encoder.block."): return "text encoder", ["text encoder"]
    if has("decoder.") and has("encoder."): return "VAE", ["VAE"]
    return "unknown", []
FILES = {"file_1": ["model.diffusion_model.input_blocks.0.0.weight", "cond_stage_model.transformer.text_model.encoder.layers.0.mlp.fc1.weight", "first_stage_model.decoder.conv_in.weight"],
         "file_2": ["double_blocks.0.img_attn.norm.key_norm.scale", "img_in.weight"],
         "file_3": ["model.diffusion_model.input_blocks.0.0.weight"],
         "file_4": ["encoder.block.0.layer.0.SelfAttention.k.weight"],
         "file_5": ["text_model.encoder.layers.11.mlp.fc1.weight"],
         "file_6": ["encoder.down.0.block.0.conv1.weight", "decoder.conv_in.weight"],
         "file_7": ["lora_unet_down_blocks_0_attentions_0_proj_in.lora_down.weight"],
         "file_8": ["control_model.input_hint_block.0.weight"]}
print(f"\n{'file':<8}{'what the names say':<24}holds")
want = {"file_1": "checkpoint", "file_2": "denoiser only", "file_3": "denoiser with a prefix", "file_4": "text encoder", "file_5": "text encoder", "file_6": "VAE", "file_7": "LoRA", "file_8": "ControlNet"}
for f, keys in FILES.items():
    k, parts = kind(keys); print(f"{f:<8}{k:<24}{', '.join(parts)}"); assert k == want[f]

# 4. What each pairing does, from load_checkpoint_guess_config and load_diffusion_model in comfy/sd.py.
OUT = [("whole checkpoint", "CheckpointLoaderSimple", "MODEL, CLIP and VAE"), ("denoiser only", "CheckpointLoaderSimple", "warns, gives a MODEL; using CLIP or VAE then fails"), ("whole checkpoint", "UNETLoader", "takes the denoiser out of it; you still need the other two"), ("denoiser only", "UNETLoader", "gives a MODEL"), ("file of no known kind", "either", "Could not detect model type")]
print(f"\n{'the file':<24}{'the loader':<25}what happens")
for a, b, c in OUT: print(f"{a:<24}{b:<25}{c}")
