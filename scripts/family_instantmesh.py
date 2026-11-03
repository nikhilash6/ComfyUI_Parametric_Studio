"""The InstantMesh family render (runner:instantmesh): TencentARC's InstantMesh, offline, with the official code as jtydhr88/ComfyUI-InstantMesh carries it.
Zero123++ v1.2 (with InstantMesh's white-background UNet) makes six views, the large LRM turns them into a textured mesh, written as GLB for a turntable.
Its ComfyUI node can't serve as a family pack (it hardcodes the main ComfyUI's custom_nodes and pulls Zero123++ from the Hub at run time), so this runs the same code with local folders.
python scripts/family_instantmesh.py --code <pack folder> --zero123 <sudo-ai/zero123plus-v1.2 folder> --dino <facebook/dino-vitb16 folder> --instantmesh <folder with diffusion_pytorch_model.bin and instant_mesh_large.ckpt> --image in.png --out out_dir [--seed 42] [--steps 75]"""
import argparse, json, os, sys, time


def main():
    a = argparse.ArgumentParser()
    for k in ("code", "zero123", "dino", "instantmesh", "image", "out"): a.add_argument("--" + k, required=True)
    a.add_argument("--seed", type=int, default=42); a.add_argument("--steps", type=int, default=75); a = a.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, a.code)
    import transformers.pytorch_utils as _pu
    if not hasattr(_pu, "find_pruneable_heads_and_indices"):        # gone in transformers 5; InstantMesh's ViT imports it only for head pruning, which inference never calls
        def _no_pruning(*_a, **_k): raise NotImplementedError("head pruning is not used here")
        _pu.find_pruneable_heads_and_indices = _no_pruning
    from transformers import PreTrainedModel
    if not hasattr(PreTrainedModel, "get_head_mask"):                 # also gone in transformers 5; with no head mask it was a list of Nones
        def _no_head_mask(self, head_mask, num_hidden_layers, is_attention_chunked=False):
            if head_mask is None: return [None] * num_hidden_layers
            raise NotImplementedError("head masks are not used here")
        PreTrainedModel.get_head_mask = _no_head_mask
    import numpy as np, torch, rembg, trimesh
    from PIL import Image
    from einops import rearrange
    from omegaconf import OmegaConf
    from torchvision.transforms import v2
    from diffusers import EulerAncestralDiscreteScheduler
    from src.utils.train_util import instantiate_from_config
    from src.utils.camera_util import get_zero123plus_input_cameras
    from src.utils.infer_util import remove_background, resize_foreground
    t0 = time.time(); os.makedirs(a.out, exist_ok=True); dev = torch.device("cuda")
    torch.manual_seed(a.seed)
    cfg = OmegaConf.load(os.path.join(a.code, "configs", "instant-mesh-large.yaml")); cfg.model_config.params.encoder_model_name = a.dino
    from zero123plus.pipeline import Zero123PlusPipeline                       # the pack's copy of Zero123++'s pipeline, imported as plain code rather than as diffusers "remote code"
    pipe = Zero123PlusPipeline.from_pretrained(a.zero123, torch_dtype=torch.float16, local_files_only=True)
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
    pipe.unet.load_state_dict(torch.load(os.path.join(a.instantmesh, "diffusion_pytorch_model.bin"), map_location="cpu", weights_only=True), strict=True)
    pipe = pipe.to(dev)
    img = resize_foreground(remove_background(Image.open(a.image), rembg.new_session()), 0.85); img.save(os.path.join(a.out, "input_cutout.png"))
    views = pipe(img, num_inference_steps=a.steps, generator=torch.Generator("cuda").manual_seed(a.seed)).images[0]; views.save(os.path.join(a.out, "views.png"))
    del pipe; torch.cuda.empty_cache()
    model = instantiate_from_config(cfg.model_config)
    sd = torch.load(os.path.join(a.instantmesh, "instant_mesh_large.ckpt"), map_location="cpu", weights_only=False)["state_dict"]
    model.load_state_dict({k[14:]: v for k, v in sd.items() if k.startswith("lrm_generator.")}, strict=True)
    model = model.to(dev); model.init_flexicubes_geometry(dev, fovy=30.0); model = model.eval()
    x = torch.from_numpy(np.asarray(views, dtype=np.float32) / 255.0).permute(2, 0, 1).contiguous()
    x = rearrange(x, "c (n h) (m w) -> (n m) c h w", n=3, m=2).unsqueeze(0).to(dev)
    x = v2.functional.resize(x, 320, interpolation=3, antialias=True).clamp(0, 1)
    cams = get_zero123plus_input_cameras(batch_size=1, radius=4.0).to(dev)
    with torch.no_grad():
        planes = model.forward_planes(x, cams)
        verts, faces, colors = model.extract_mesh(planes, use_texture_map=False, **cfg.infer_config)
    verts = np.asarray(verts)[:, [1, 2, 0]]                     # to glTF axes (y up), as the official InstantMesh export does
    glb = os.path.join(a.out, "mesh.glb"); trimesh.Trimesh(vertices=verts, faces=np.asarray(faces), vertex_colors=np.asarray(colors, dtype=np.uint8), process=False).export(glb)
    json.dump({"seconds": round(time.time() - t0, 1), "vertices": int(len(verts)), "faces": int(len(faces)), "seed": a.seed, "steps": a.steps, "peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 1)}, open(os.path.join(a.out, "report.json"), "w"), indent=1)
    print(open(os.path.join(a.out, "report.json")).read())


if __name__ == "__main__": main()
