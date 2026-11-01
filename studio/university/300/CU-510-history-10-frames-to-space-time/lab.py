# CU-510 lab: what makes a video model's parts work on time. A causal convolution tested for leaks, the frame grid it produces, and the token counts that decide between factorised and joint attention. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# 1. A causal 3D convolution, tested by differentiating. Same weights, kernel 3 in time, on 9 frames. Which input frames does output frame 4 read?
conv = torch.nn.Conv3d(1, 1, (3, 1, 1), bias=False)
def causal(x): return conv(torch.cat((torch.zeros_like(x[:, :, :2]), x), 2))                                   # zeros on the past side only, as CausalConv3d in comfy/ldm/wan/vae.py
def causal_rep(x): return conv(torch.cat((x[:, :, :1].repeat(1, 1, 2, 1, 1), x), 2))                            # the first frame repeated, as comfy/ldm/cosmos and comfy/ldm/lightricks do
def centred(x): return conv(torch.cat((torch.zeros_like(x[:, :, :1]), x, torch.zeros_like(x[:, :, :1])), 2))    # an ordinary centred convolution
def reads(pad, out_frame=4):
    x = torch.randn(1, 1, 9, 1, 1, requires_grad=True); y = pad(x); assert y.shape[2] == 9
    g, = torch.autograd.grad(y[0, 0, out_frame].sum(), x); return [j for j in range(9) if g[0, 0, j].abs().sum() > 0]
print("output frame 4 reads input frames"); print("centred convolution      ", reads(centred)); print("causal, zero padding      ", reads(causal)); print("causal, first frame copied", reads(causal_rep))
assert reads(causal) == [2, 3, 4] and reads(centred) == [3, 4, 5]
# Change the future and watch the past.
x = torch.randn(1, 1, 9, 1, 1); x2 = x.clone(); x2[0, 0, 6:] += 5.
print(f"change frames 6 to 8: outputs 0 to 5 move by {(causal(x2) - causal(x))[0, 0, :6].abs().max().item():.1f} with causal padding, {(centred(x2) - centred(x))[0, 0, :6].abs().max().item():.2f} with centred")
assert (causal(x2) - causal(x))[0, 0, :6].abs().max() == 0
# 2. Stride makes the frame grid. Two causal stride-2 layers: pad kernel - 1 frames on the past side, keep the first frame's position.
def strided(T, layers, k=3, s=2):
    n = T
    for _ in range(layers):
        y = torch.nn.functional.conv1d(torch.zeros(1, 1, n + (k - 1)), torch.ones(1, 1, k), stride=s); n = y.shape[2]
    return n
print("\nframes in   latent frames, two stride-2 layers   ((T - 1) // 4) + 1   decoded back, 4 L - 3")
for T in (1, 5, 17, 48, 49, 81, 82):
    L = strided(T, 2); f = (T - 1) // 4 + 1; print(f"{T:<11d} {L:<36d} {f:<20d} {4 * f - 3}"); assert L == f
# 3. Why factorise? Tokens and attention pairs for one clip. (time, height, width) after the VAE and patching. Sizes follow the source: Wan's latent is (T-1)//4+1, h//8, w//8 with patch (1, 2, 2); LTX's is (T-1)//8+1, h//32, w//32 with patch 1.
print("\nclip                     latent grid after patching   tokens    joint pairs     spatial + temporal pairs   joint / factorised")
out = []
for name, (t, h, w) in (("Wan 832x480, 81 frames", (21, 30, 52)), ("Wan 832x480, 161 frames", (41, 30, 52)), ("LTX 768x512, 121 frames", (16, 16, 24))):
    n = t * h * w; joint = n * n; fact = t * (h * w) ** 2 + h * w * t ** 2; out.append((n, joint / fact))
    print(f"{name:<24s} {t} x {h} x {w:<19d} {n:<9,d} {joint:<15.3e} {fact:<26.3e} {joint / fact:.1f}")
assert out[0][0] == 32760 and abs(out[1][0] / out[0][0] - 41 / 21) < 1e-9
print(f"double the frames, joint pairs grow {(41 / 21) ** 2:.2f} times; the same clip at twice the side grows them 16 times")
