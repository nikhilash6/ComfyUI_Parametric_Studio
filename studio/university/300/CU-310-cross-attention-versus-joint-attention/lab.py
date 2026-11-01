# CU-310 lab: cross-attention and joint attention side by side. Small hand-made versions following CrossAttention (comfy/ldm/modules/attention.py) and _block_mixing (mmdit.py) and DoubleStreamBlock (flux/layers.py). Random weights.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = 8
def attn(q, k, v): return torch.softmax(q @ k.transpose(-2, -1) / math.sqrt(D), -1) @ v
class Proj:
    def __init__(self): self.q, self.k, self.v = torch.randn(D, D) * .3, torch.randn(D, D) * .3, torch.randn(D, D) * .3
img_p, txt_p = Proj(), Proj()
def cross(img, txt): return attn(img @ img_p.q, txt @ txt_p.k, txt @ txt_p.v), txt            # the text passes through untouched
def joint(img, txt):
    q = torch.cat((txt @ txt_p.q, img @ img_p.q), 1); k = torch.cat((txt @ txt_p.k, img @ img_p.k), 1); v = torch.cat((txt @ txt_p.v, img @ img_p.v), 1)
    out = attn(q, k, v); n = txt.shape[1]; return out[:, n:], out[:, :n]                        # split back into two streams
img = torch.randn(1, 4, D); txt = torch.randn(1, 3, D)
ci, ct = cross(img, txt); ji, jt = joint(img, txt)
print("4 image tokens and 3 text tokens")
print("cross-attention:  image out", list(ci.shape), "  text out", list(ct.shape), "  text changed:", not torch.equal(ct, txt))
print("joint attention:  image out", list(ji.shape), "  text out", list(jt.shape), "  text changed:", not torch.equal(jt, txt))
assert torch.equal(ct, txt) and not torch.equal(jt, txt) and ci.shape == ji.shape
def scores(q, k): return q.shape[1] * k.shape[1]
print("\nwhat can a token see, as a share of all attention weight? one row of each weight table")
w_c = torch.softmax((img @ img_p.q) @ (txt @ txt_p.k).transpose(-2, -1) / math.sqrt(D), -1)[0, 0]; print("cross, image token 0 over the 3 text tokens:", [round(v, 3) for v in w_c.tolist()])
q = torch.cat((txt @ txt_p.q, img @ img_p.q), 1); k = torch.cat((txt @ txt_p.k, img @ img_p.k), 1); w_j = torch.softmax(q @ k.transpose(-2, -1) / math.sqrt(D), -1)[0, 3]
print("joint, image token 0 over 3 text + 4 image:  ", [round(v, 3) for v in w_j.tolist()])
assert abs(w_c.sum().item() - 1) < 1e-5 and abs(w_j.sum().item() - 1) < 1e-5
img2 = img.clone(); img2[0, 3] = torch.randn(D); print("\nchange image token 3 only. Does image token 0's output move?")
print("cross:", (cross(img2, txt)[0][0, 0] - ci[0, 0]).norm().item() > 0, "  joint:", (joint(img2, txt)[0][0, 0] - ji[0, 0]).norm().item() > 0)
assert (cross(img2, txt)[0][0, 0] - ci[0, 0]).norm() == 0 and (joint(img2, txt)[0][0, 0] - ji[0, 0]).norm() > 0
print("\nwhy the U-Net also has self-attention: cross alone never lets image tokens see each other. Its block runs attn1 (self) then attn2 (cross).")
print("\nnumber of query-key pairs per block, 64 by 64 image tokens")
I = 64 * 64
for name, n in (("SD 1.5 style: self + cross, 77 text tokens", I * I + I * 77), ("Flux style: joint, 256 text tokens", (I + 256) ** 2), ("Flux style: joint, 512 text tokens", (I + 512) ** 2), ("joint, text left out, for scale", I * I)):
    print(f"{name:<46} {n / 1e6:.2f} million")
assert (I + 256) ** 2 > I * I + I * 77
