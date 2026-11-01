# CU-280 lab: which keys of a LoRA file reach the model, and what the loader writes in the log when they do not.
# load_lora follows comfy/lora.py. Key names follow model_lora_keys_unet and model_lora_keys_clip. The sum follows LoRAAdapter.calculate_weight in comfy/weight_adapter/lora.py.
import torch
def load_lora(lora, to_load):
    """-> patches, log lines. A key nobody claimed gets the same warning the real function writes."""
    patches, seen, log = {}, set(), []
    for x in to_load:
        if f"{x}.alpha" in lora: seen.add(f"{x}.alpha")
        if f"{x}.lora_up.weight" in lora:
            seen |= {f"{x}.lora_up.weight", f"{x}.lora_down.weight"}; patches[to_load[x]] = x
    for k in lora:
        if k not in seen: log.append(f"lora key not loaded: {k}")
    return patches, log
def fake_file(prefixes, layers=2):
    out = {}
    for p in prefixes:
        for i in range(layers):
            for s in ("lora_up.weight", "lora_down.weight", "alpha"): out[f"{p}_block{i}.{s}"] = 1
    return out
UNET = {f"lora_unet_block{i}": f"diffusion_model.block{i}.weight" for i in range(2)}
TE = {f"lora_te_block{i}": f"clip_l.block{i}.weight" for i in range(2)}
sd1_file = fake_file(["lora_unet", "lora_te"]); model_only = fake_file(["lora_unet"]); other = fake_file(["lora_transformer"])
print("file                          loader                 keys in file   patches   warnings")
cases = (("denoiser + text encoder", sd1_file, {**UNET, **TE}, "LoraLoader"), ("denoiser + text encoder", sd1_file, UNET, "LoraLoaderModelOnly"), ("denoiser only", model_only, {**UNET, **TE}, "LoraLoader"), ("made for another family", other, {**UNET, **TE}, "LoraLoader"))
res = []
for name, f, tl, loader in cases:
    p, log = load_lora(f, tl); res.append((len(p), len(log)))
    print(f"{name:<29} {loader:<22} {len(f):<14} {len(p):<9} {len(log)}")
assert res == [(4, 0), (2, 6), (2, 0), (0, 6)]
print("\nwhat the log says for row 2:"); print(load_lora(sd1_file, UNET)[1][0])
print("what the log says for row 4:"); print(load_lora(other, {**UNET, **TE})[1][0])

g = torch.Generator().manual_seed(0); W = torch.randn(32, 32, generator=g)
up = torch.randn(32, 4, generator=g) * 0.1; down = torch.randn(4, 32, generator=g) * 0.1
def apply(w, up, down, alpha, strength):
    scale = alpha / down.shape[0] if alpha is not None else 1.0
    return w + strength * scale * (up @ down)
print("\nthe same numbers, stored three ways, strength 1: size of the change to the weight")
print("alpha in file   scale   change")
base = (apply(W, up, down, 4.0, 1.0) - W).norm().item(); rows = []
for a in (4.0, 1.0, None):
    c = (apply(W, up, down, a, 1.0) - W).norm().item(); rows.append(c)
    print(f"{str(a):<15} {(a / 4 if a is not None else 1.0):<7} {c:.4f}")
assert abs(rows[0] - rows[2]) < 1e-5 and abs(rows[0] / rows[1] - 4) < 1e-4
up2 = torch.randn(32, 4, generator=g) * 0.1; down2 = torch.randn(4, 32, generator=g) * 0.1
ab = apply(apply(W, up, down, 4.0, 0.8), up2, down2, 4.0, 0.5); ba = apply(apply(W, up2, down2, 4.0, 0.5), up, down, 4.0, 0.8)
print("\ntwo LoRAs chained, in either order: largest difference", f"{(ab - ba).abs().max().item():.1e}", "(rounding). Chaining adds their changes.")
assert (ab - ba).abs().max() < 1e-5
# The classic wiring slip: the second text encoder patch never reaches the prompt if the prompt encoder is wired to the checkpoint's CLIP.
te = torch.randn(16, 16, generator=g); te_up = torch.randn(16, 2, generator=g) * 0.2; te_down = torch.randn(2, 16, generator=g) * 0.2; x = torch.randn(16, generator=g)
wired_right = apply(te, te_up, te_down, 2.0, 1.0) @ x; wired_past = te @ x
print("\nstrength_clip 1.0, prompt encoded through the loader's CLIP: output moved", round((wired_right - te @ x).norm().item(), 4), "  through the checkpoint's CLIP:", round((wired_past - te @ x).norm().item(), 4))
assert (wired_past - te @ x).norm() == 0 and (wired_right - te @ x).norm() > 0
# A shape mismatch: same key names, another model's width. The product cannot be reshaped; the real code logs an error and leaves the weight alone.
big = torch.randn(32, 2, generator=g); wrong = torch.randn(2, 16, generator=g); w0 = torch.randn(32, 32, generator=g); w1 = w0.clone()
try:
    w1 += (big @ wrong).reshape(w1.shape)
except Exception as e:
    msg = str(e); print("\nshape mismatch:", msg.split("\n")[0]); print("weight unchanged:", bool(torch.equal(w0, w1))); assert torch.equal(w0, w1)
