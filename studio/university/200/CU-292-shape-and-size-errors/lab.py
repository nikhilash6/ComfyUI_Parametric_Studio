# CU-292 lab: the shape errors torch really raises, made here with plain torch. The wording comes from torch itself. The lesson pairs each with a real ComfyUI traceback where we could trigger one with core nodes.
import torch
torch.set_num_threads(1)
def show(name, fn):
    try:
        r = fn(); print(f"{name}\n   no error: {tuple(r.shape)}"); return None
    except RuntimeError as e:
        m = str(e).split("\n")[0]; print(f"{name}\n   RuntimeError: {m}"); return m
a = show("add a 4-channel latent and a 16-channel latent", lambda: torch.zeros(1, 4, 8, 8) + torch.zeros(1, 16, 8, 8))
assert "size of tensor a (4) must match the size of tensor b (16) at non-singleton dimension 1" in a
b = show("batch a 4-channel latent with a 16-channel latent", lambda: torch.cat([torch.zeros(1, 4, 8, 8), torch.zeros(1, 16, 8, 8)]))
assert "Expected size 4 but got size 16" in b
c = show("feed 16 channels to a VAE layer that wants 4", lambda: torch.nn.Conv2d(4, 8, 3)(torch.zeros(1, 16, 8, 8)))
assert "expected input[1, 16, 8, 8] to have 4 channels" in c
d = show("text encoder width 2048 into a cross-attention layer that wants 768", lambda: torch.nn.Linear(768, 320)(torch.zeros(1, 77, 2048)))
assert "mat1 and mat2" in d and "77x2048" in d and "768x320" in d
e = show("image in the wrong axis order for a layer (BHWC, not BCHW)", lambda: torch.nn.Conv2d(3, 8, 3)(torch.zeros(1, 64, 64, 3)))
assert "to have 3 channels" in e
f = show("a batch of 2 against a batch of 3", lambda: torch.zeros(2, 4, 8, 8) + torch.zeros(3, 4, 8, 8))
assert "non-singleton dimension 0" in f
g = show("a batch of 1 against a batch of 3: no error, it broadcasts", lambda: torch.zeros(1, 4, 8, 8) + torch.zeros(3, 4, 8, 8))
assert g is None
print("\nthe axes")
AX = {"IMAGE": "batch, height, width, channels", "MASK": "batch, height, width", "LATENT": "batch, channels, height / 8, width / 8"}
for k, v in AX.items(): print(f"{k:7} {v}")
img = torch.zeros(1, 512, 768, 3); lat = torch.zeros(1, 4, 512 // 8, 768 // 8); print("a 768 wide by 512 tall image:", tuple(img.shape), " its SD latent:", tuple(lat.shape))
# Why a core node hides it. reshape_latent_to in nodes_latent.py resizes the second latent to the first, with no warning.
small, big = torch.ones(1, 4, 8, 8), torch.ones(1, 4, 16, 16)
out = small + torch.nn.functional.interpolate(big, size=small.shape[-2:], mode="bilinear"); print("\nLatentAdd's idea, 8 by 8 and 16 by 16:", tuple(out.shape)); assert out.shape == small.shape
