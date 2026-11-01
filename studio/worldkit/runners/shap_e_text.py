"""Shap-E text to mesh: python shap_e_text.py --prompt "a red chair" --out x.glb [--seed 7] [--steps 64] [--guidance 15] [--root MODELS]
The pipeline comes from 3d/shap-e. The repo's text encoder weights are not on this box: Shap-E uses CLIP ViT-L/14 (its text_encoder/config.json), so they are read from text_encoders/clip-vit-large-patch14.safetensors, the same repo's encoder with its projection, and any key that does not match stops the run rather than leaving random weights."""
import argparse, os, re, sys


def clip_state(path):
    """A ComfyUI CLIP-L file -> the state dict CLIPTextModelWithProjection expects."""
    from safetensors.torch import load_file
    sd = load_file(path); out = {}
    for k, v in sd.items():
        k = re.sub(r"^(clip_l\.|cond_stage_model\.transformer\.|transformer\.)", "", k)
        if k == "logit_scale" or k.endswith(".position_ids"): continue
        out[k] = v
    return out


def load(root, device):
    import torch
    from diffusers import ShapEPipeline
    from transformers import CLIPTextConfig, CLIPTextModelWithProjection
    base = os.path.join(root, "3d", "shap-e")
    cfg = CLIPTextConfig.from_pretrained(os.path.join(base, "text_encoder"))
    te = CLIPTextModelWithProjection(cfg); sd = clip_state(os.path.join(root, "text_encoders", "clip-vit-large-patch14.safetensors"))
    if "text_projection.weight" not in sd and "text_projection" in sd: sd["text_projection.weight"] = sd.pop("text_projection").T
    miss, extra = te.load_state_dict(sd, strict=False)
    miss = [m for m in miss if "position_ids" not in m]
    if miss: raise SystemExit(f"clip-vit-large-patch14 does not fill the Shap-E text encoder; missing {miss[:6]}")
    from diffusers import HeunDiscreteScheduler, PriorTransformer
    from diffusers.pipelines.shap_e import ShapERenderer
    from transformers import CLIPTokenizer
    prior = PriorTransformer.from_pretrained(os.path.join(base, "prior"), variant="fp16", use_safetensors=True, torch_dtype=torch.float32, local_files_only=True)
    renderer = ShapERenderer.from_pretrained(os.path.join(base, "shap_e_renderer"), use_safetensors=False, local_files_only=True)  # only this .bin holds the mesh decoder: not fp16, kept at its own precision
    pipe = ShapEPipeline(prior=prior, text_encoder=te, tokenizer=CLIPTokenizer.from_pretrained(os.path.join(base, "tokenizer")), scheduler=HeunDiscreteScheduler.from_pretrained(os.path.join(base, "scheduler")), shap_e_renderer=renderer)
    return pipe.to(device)


def run(a):
    import numpy as np, torch, trimesh
    pipe = load(a.root, "cuda"); g = torch.Generator("cuda").manual_seed(a.seed)
    m = pipe(a.prompt, num_inference_steps=a.steps, guidance_scale=a.guidance, frame_size=64, output_type="mesh", generator=g).images[0]
    verts = m.verts.detach().cpu().numpy(); faces = m.faces.detach().cpu().numpy()
    if not len(faces): raise SystemExit("Shap-E produced an empty mesh")
    col = np.stack([m.vertex_channels[c].detach().cpu().numpy() for c in "RGB"], 1)
    mesh = trimesh.Trimesh(vertices=verts @ np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]), faces=faces, vertex_colors=(np.clip(col, 0, 1) * 255).astype("uint8"), process=False)
    mesh.export(a.out); print(f"{len(verts)} vertices, {len(faces)} faces -> {a.out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--prompt", required=True); p.add_argument("--out", required=True); p.add_argument("--seed", type=int, default=7); p.add_argument("--steps", type=int, default=64); p.add_argument("--guidance", type=float, default=15.0)
    p.add_argument("--root", required=True); run(p.parse_args())
