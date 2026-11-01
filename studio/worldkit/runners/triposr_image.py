"""TripoSR picture to mesh: python triposr_image.py --image a.png --out x.glb [--code DIR_WITH_tsr] [--ckpt model.ckpt] [--resolution 256]
TripoSR has no ComfyUI node here. Its code is the upstream `tsr` package (MIT), found in a pack library folder; only that package is imported, nothing from the pack around it. An image with an alpha channel keeps its cut-out, others get a plain grey matte; run the background cut-out first for a clean result."""
import argparse, json, os, sys, tempfile, types

#: facebook/dino-vitb16's config.json: TripoSR builds the shape of its image encoder from it, the weights are in model.ckpt. Kept here so a run needs no network.
DINO_VITB16 = {"architectures": ["ViTModel"], "attention_probs_dropout_prob": 0.0, "hidden_act": "gelu", "hidden_dropout_prob": 0.0, "hidden_size": 768, "image_size": 224, "initializer_range": 0.02, "intermediate_size": 3072, "layer_norm_eps": 1e-12, "model_type": "vit", "num_attention_heads": 12, "num_channels": 3, "num_hidden_layers": 12, "patch_size": 16, "qkv_bias": True}


def offline(tmp):
    """The library copy of tsr asks ComfyUI's folder_paths for a folder and a mirror site for the config. Neither is wanted here: answer both locally before it is imported."""
    import huggingface_hub
    path = os.path.join(tmp, "config.json"); json.dump(DINO_VITB16, open(path, "w"))
    huggingface_hub.hf_hub_download = lambda *a, **k: path
    sys.modules.setdefault("folder_paths", types.SimpleNamespace(models_dir=tmp, get_folder_paths=lambda *_: [tmp]))


VIT_NAMES = (("attention.attention.query", "attention.q_proj"), ("attention.attention.key", "attention.k_proj"), ("attention.attention.value", "attention.v_proj"), ("attention.output.dense", "attention.o_proj"), ("intermediate.dense", "mlp.fc1"), ("output.dense", "mlp.fc2"))


def new_names(sd, wanted):
    """The checkpoint names its ViT layers the older transformers way (encoder.layer.N...). This venv's transformers calls them layers.N... -> a state dict with the names the model has; nothing else changes."""
    out = {}
    for k, v in sd.items():
        n = k.replace(".model.encoder.layer.", ".model.layers.")
        if n != k:
            for old, new in VIT_NAMES: n = n.replace(old, new)
        out[n if n in wanted else k] = v
    return out


def build(S, code, ckpt):
    """TSR with the checkpoint's weights, or a clear stop if any weight does not land."""
    import torch
    from omegaconf import OmegaConf
    cfg = OmegaConf.load(os.path.join(code, "config.yaml")); OmegaConf.resolve(cfg); model = S.TSR(cfg)
    sd = torch.load(ckpt, map_location="cpu", weights_only=True)
    res = model.load_state_dict(new_names(sd, set(model.state_dict())), strict=False)
    if res.missing_keys or res.unexpected_keys: raise SystemExit(f"TripoSR weights do not fit: missing {res.missing_keys[:4]}, extra {res.unexpected_keys[:4]}")
    return model


def run(a):
    import numpy as np, torch
    from PIL import Image
    offline(tempfile.mkdtemp(prefix="triposr_"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(a.code)))      # the config names its classes tsr.models...: the folder has to be importable as tsr
    import importlib
    S = importlib.import_module("tsr.system")
    im = Image.open(a.image); s = 512
    if im.mode == "RGBA":
        arr = np.asarray(im).astype("float32") / 255; rgb = arr[..., :3] * arr[..., 3:] + 0.5 * (1 - arr[..., 3:]); ys, xs = np.where(arr[..., 3] > 0.5)
        if len(xs):                                         # the object at 85% of the frame, as the model was trained
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max(); side = int(max(x1 - x0, y1 - y0) / 0.85); cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            canvas = np.full((side, side, 3), 0.5, "float32"); ox, oy = side // 2 - cx, side // 2 - cy
            sy0, sx0 = max(0, -oy), max(0, -ox); dy0, dx0 = max(0, oy), max(0, ox); h, w = min(rgb.shape[0] - sy0, side - dy0), min(rgb.shape[1] - sx0, side - dx0)
            canvas[dy0:dy0 + h, dx0:dx0 + w] = rgb[sy0:sy0 + h, sx0:sx0 + w]; rgb = canvas
        im = Image.fromarray((rgb * 255).astype("uint8"))
    im = im.convert("RGB").resize((s, s))
    model = build(S, a.code, a.ckpt); model.renderer.set_chunk_size(8192); model.to("cuda")
    with torch.no_grad(): codes = model([im], device="cuda")
    meshes = model.extract_mesh(codes, resolution=a.resolution)
    m = meshes[0]
    if not len(m.faces): raise SystemExit("TripoSR produced an empty mesh")
    import trimesh.transformations as TT                    # TripoSR works Z up; a GLB is Y up, facing +Z
    m.apply_transform(TT.rotation_matrix(-np.pi / 2, [1, 0, 0])); m.apply_transform(TT.rotation_matrix(np.pi / 2, [0, 1, 0]))
    m.export(a.out); print(f"{len(m.vertices)} vertices, {len(m.faces)} faces -> {a.out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--image", required=True); p.add_argument("--out", required=True); p.add_argument("--resolution", type=int, default=256)
    p.add_argument("--code", required=True); p.add_argument("--ckpt", required=True); run(p.parse_args())
