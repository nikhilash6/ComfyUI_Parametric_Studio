"""FASHN VTON 1.5 try-on (Apache-2.0): python fashn_tryon.py --person a.png --garment b.png --out c.png --code DIR_WITH_fashn_vton --weights MODEL_DIR --pose DIR_WITH_DWPOSE_ONNX --parser HUMAN_PARSER_DIR [--category tops|bottoms|one-pieces] [--photo model|flat-lay] [--seed 42] [--steps 30] [--guidance 1.5]
Only the fashn_vton package is imported from the pack library folder, nothing from the node around it. It asks ComfyUI for the device, so that one question is answered here, and all weights are local: a run needs no network."""
import argparse, os, sys, tempfile, types


def stubs():
    """Just enough of comfy for fashn_vton's imports: which device, and a progress bar."""
    import torch
    mm = types.ModuleType("comfy.model_management"); mm.get_torch_device = lambda: torch.device("cuda"); mm.should_use_bf16 = lambda *a, **k: True; mm.should_use_fp16 = lambda *a, **k: False; mm.soft_empty_cache = torch.cuda.empty_cache; mm.throw_exception_if_processing_interrupted = lambda: None
    ut = types.ModuleType("comfy.utils")
    class Bar:
        def __init__(self, *a): pass
        def update(self, *a): pass
    ut.ProgressBar = Bar
    root = types.ModuleType("comfy"); root.model_management, root.utils = mm, ut
    sys.modules.update({"comfy": root, "comfy.model_management": mm, "comfy.utils": ut})


def weights_dir(weights, pose):
    """The layout the pipeline wants: the model and dwpose/ side by side, as links."""
    d = tempfile.mkdtemp(prefix="fashn_"); os.symlink(os.path.join(weights, "model.safetensors"), os.path.join(d, "model.safetensors")); os.symlink(pose, os.path.join(d, "dwpose")); return d


def run(a):
    from PIL import Image
    stubs(); sys.path.insert(0, a.code)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    import fashn_human_parser as H
    orig = H.FashnHumanParser.__init__
    def local(self, *x, **k):
        k["model_id"] = a.parser; return orig(self, *x, **k)
    H.FashnHumanParser.__init__ = local
    from fashn_vton import TryOnPipeline
    import torch
    pipe = TryOnPipeline(weights_dir(a.weights, a.pose)); dev = torch.device("cuda")      # it loads on the CPU and leaves the move to its caller
    pipe.tryon_model.to(dev)
    if hasattr(pipe, "hp_model"): pipe.hp_model.model.to(dev); pipe.hp_model.device = dev
    out = pipe(Image.open(a.person).convert("RGB"), Image.open(a.garment).convert("RGB"), category=a.category, garment_photo_type=a.photo, num_samples=1, num_timesteps=a.steps, guidance_scale=a.guidance, seed=a.seed)
    im = out.images[0] if hasattr(out, "images") else out[0]
    im.save(a.out); print("->", a.out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for n in ("--person", "--garment", "--out", "--code", "--weights", "--pose", "--parser"): p.add_argument(n, required=True)
    p.add_argument("--category", default="tops", choices=("tops", "bottoms", "one-pieces")); p.add_argument("--photo", default="flat-lay", choices=("model", "flat-lay")); p.add_argument("--seed", type=int, default=42); p.add_argument("--steps", type=int, default=30); p.add_argument("--guidance", type=float, default=1.5); run(p.parse_args())
