# CU-303 lab: the moving parts of a DiT block with toy sizes: patches, adaLN modulation with a zero start, and a joint text and image attention. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# 1. Patchify as comfy/ldm/flux/model.py does it: rearrange "b c (h ph) (w pw) -> b (h w) (c ph pw)".
lat = torch.arange(4 * 16 * 16, dtype=torch.float32).reshape(1, 4, 16, 16); p = 2
def patchify(x, p):
    b, c, h, w = x.shape; return x.reshape(b, c, h // p, p, w // p, p).permute(0, 2, 4, 1, 3, 5).reshape(b, (h // p) * (w // p), c * p * p)
def unpatchify(t, c, h, w, p):
    b = t.shape[0]; return t.reshape(b, h // p, w // p, c, p, p).permute(0, 3, 1, 4, 2, 5).reshape(b, c, h, w)
t = patchify(lat, p); print(f"latent {tuple(lat.shape)} -> tokens {tuple(t.shape)}, back again identical: {torch.equal(unpatchify(t, 4, 16, 16, p), lat)}"); assert torch.equal(unpatchify(t, 4, 16, 16, p), lat)
print("image      latent side   patch  tokens   token pairs")
for side, pp in ((512, 2), (1024, 2), (2048, 2), (1024, 1)):
    n = (side // 8 // pp) ** 2; print(f"{side:<10d} {side // 8:<13d} {pp:<6d} {n:<8,d} {n * n:,d}")
# 2. adaLN: the time vector makes scale and shift for the whole block. Same formula as modulate() in mmdit.py: shift + x (1 + scale).
def modulate(x, shift, scale): return shift.unsqueeze(1) + x * (1 + scale.unsqueeze(1))
D = 32; x = torch.randn(1, 64, D); mlp = torch.nn.Linear(D, 3 * D); c = torch.randn(1, D)
shift, scale, gate = mlp(torch.nn.functional.silu(c)).chunk(3, 1)
y = modulate(x, shift, scale); gap = (y[0, :, 0] - (x[0, :, 0] * (1 + scale[0, 0]) + shift[0, 0])).abs().max().item()
print(f"\none scale and one shift per channel, the same for all {x.shape[1]} tokens: largest gap from that formula {gap:.1e}"); assert gap < 1e-5
# Different time vector, different modulation: the only way this block learns the noise level.
y2 = modulate(x, *mlp(torch.nn.functional.silu(torch.randn(1, D))).chunk(3, 1)[:2]); print("another time vector changes the output:", not torch.equal(y, y2)); assert not torch.equal(y, y2)
# adaLN-Zero (the DiT paper): start the gate at zero and the whole block is the identity at step one of training.
torch.nn.init.zeros_(mlp.weight); torch.nn.init.zeros_(mlp.bias); shift, scale, gate = mlp(torch.nn.functional.silu(c)).chunk(3, 1)
attn_out = torch.randn(1, 64, D); out = x + gate.unsqueeze(1) * attn_out
print("zero-initialised gate: the block returns its input:", torch.equal(out, x)); assert torch.equal(out, x) and torch.equal(modulate(x, shift, scale), x)
# 3. Joint attention, as in _block_mixing (SD3) and DoubleStreamBlock (FLUX): text and image tokens in one sequence, each with its own projections.
def attend(q, k, v): return ((q @ k.transpose(-1, -2)) / math.sqrt(k.shape[-1])).softmax(-1) @ v
T, I = torch.randn(1, 8, D), torch.randn(1, 64, D); Wt, Wi = [torch.randn(D, D) for _ in range(3)], [torch.randn(D, D) for _ in range(3)]
def joint(T, I):
    qkv = [torch.cat([T @ a, I @ b], 1) for a, b in zip(Wt, Wi)]; o = attend(*qkv); return o[:, :T.shape[1]], o[:, T.shape[1]:]
ot, oi = joint(T, I); T2 = T.clone(); T2[0, 3] += 1.0; ot2, oi2 = joint(T2, I); I2 = I.clone(); I2[0, 3] += 1.0; ot3, oi3 = joint(T, I2)
print(f"\njoint attention: {T.shape[1]} text + {I.shape[1]} image tokens -> a matrix of {(T.shape[1] + I.shape[1]) ** 2:,d} pairs")
print(f"change one text token: image output moves by {(oi2 - oi).abs().max():.3f}.  change one image token: text output moves by {(ot3 - ot).abs().max():.3f}.  so it runs both ways")
assert (oi2 - oi).abs().max() > 0 and (ot3 - ot).abs().max() > 0
def cross(I, T): return attend(I @ Wi[0], T @ Wt[1], T @ Wt[2])
c1 = cross(I, T); c2 = cross(I, T2); print(f"plain cross-attention, for contrast: {I.shape[1]} queries x {T.shape[1]} keys = {I.shape[1] * T.shape[1]} pairs, and the text tokens get no new values from it")
