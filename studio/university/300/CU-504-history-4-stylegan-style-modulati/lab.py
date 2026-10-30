# CU-504 lab: what a style does to a feature map. AdaIN (StyleGAN, 2018), the (1 + scale) form used by DiT blocks and ComfyUI's modulate(), and weight demodulation (StyleGAN2, 2019).
# Run: python lab.py  (CPU only, about 3 s). Prints the same numbers every time.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64

def smooth_noise(c, n):                                                     # a spatial pattern: white noise blurred by a 3x3 box, so neighbouring pixels agree
    z = torch.randn(c, 1, n + 2, n + 2, dtype=D); return torch.nn.functional.avg_pool2d(z, 3, 1)[:, 0]
def adain(x, ys, yb):                                                       # AdaIN(x_i, y) = y_s,i (x_i - mean(x_i)) / std(x_i) + y_b,i, per feature map i
    mu = x.mean((1, 2), keepdim=True); sd = x.std((1, 2), unbiased=False, keepdim=True)
    return ys[:, None, None] * (x - mu) / sd + yb[:, None, None]
def modulate(x, shift, scale): return shift[:, None, None] + x * (1 + scale[:, None, None])   # the form in ComfyUI's mmdit.py, per feature map

# 1. AdaIN replaces the per-channel mean and standard deviation of a feature map with the style's, and keeps the spatial pattern.
x = smooth_noise(4, 16) * torch.tensor([1., 5., .2, 3.], dtype=D)[:, None, None] + torch.tensor([0., 7., -2., 40.], dtype=D)[:, None, None]
ys, yb = torch.tensor([.5, 2., 1., 3.], dtype=D), torch.tensor([1., -1., 0., 4.], dtype=D)
y = adain(x, ys, yb)
print("channel  input mean  input std   style y_b  style y_s   output mean  output std  correlation with input")
for c in range(4):
    r = torch.corrcoef(torch.stack([x[c].flatten(), y[c].flatten()]))[0, 1]
    print(f"{c}        {x[c].mean():+8.3f}    {x[c].std(unbiased=False):7.3f}     {yb[c]:+6.2f}     {ys[c]:6.2f}       {round(y[c].mean().item(), 6) + 0.0:+6.3f}      {y[c].std(unbiased=False):6.3f}      {r:+.4f}")
assert torch.allclose(y.mean((1, 2)), yb) and torch.allclose(y.std((1, 2), unbiased=False), ys)

# 2. What AdaIN forgets, against what (1 + scale) keeps. Give both the same pattern with different per-channel mean and standard deviation.
a, b = torch.tensor([1., 4., 9., .5], dtype=D)[:, None, None], torch.tensor([3., -6., 20., 0.], dtype=D)[:, None, None]
x2 = a * x + b; shift, scale = torch.tensor([.3, -.2, 0., .1], dtype=D), torch.tensor([.5, -.4, .2, 1.], dtype=D)
d_adain = (adain(x2, ys, yb) - adain(x, ys, yb)).abs().max(); d_mod = (modulate(x2, shift, scale) - modulate(x, shift, scale)).abs().max()
print(f"\ninputs that differ only by a per-channel scale and offset: largest output difference  AdaIN {d_adain:.1e}   shift + x(1 + scale) {d_mod:.1f}")
zero = torch.zeros(4, dtype=D); d_id = (modulate(x, zero, zero) - x).abs().max(); d_ad = (adain(x, torch.ones(4, dtype=D), zero) - x).abs().max()
print(f"style set to 'do nothing' (scale 0, shift 0, or y_s 1, y_b 0): largest change to the input  shift + x(1 + scale) {d_id:.1f}   AdaIN {d_ad:.1f}")
assert d_adain < 1e-9 and d_mod > 1 and d_id == 0

# 3. StyleGAN2: scaling the input feature maps by a style is the same as scaling the convolution weights, and the output scale is predictable.
n_in, n_out = 6, 8; w = torch.randn(n_out, n_in, 3, 3, dtype=D); s = torch.tensor([.2, 1., 5., .5, 2., 8.], dtype=D)       # a style whose entries differ by 40x
xin = torch.randn(256, n_in, 34, 34, dtype=D)                                                                          # independent unit-variance inputs
out_a = torch.nn.functional.conv2d(xin * s[None, :, None, None], w)                                                    # modulate the activations
wm = w * s[None, :, None, None]; out_b = torch.nn.functional.conv2d(xin, wm)                                           # modulate the weights: w'_ijk = s_i w_ijk
sigma = (wm ** 2).sum((1, 2, 3)).sqrt()                                                                                # predicted output std, sigma_j
wd = wm / ((wm ** 2).sum((1, 2, 3), keepdim=True) + 1e-8).sqrt(); out_d = torch.nn.functional.conv2d(xin, wd)           # demodulated weights
print(f"\nmodulating activations against modulating weights: largest difference {(out_a - out_b).abs().max():.1e}")
print("output map j          0       1       2       3       4       5       6       7")
print("predicted std     " + " ".join(f"{v:7.2f}" for v in sigma.tolist()))
print("measured std      " + " ".join(f"{v:7.2f}" for v in out_b.std((0, 2, 3)).tolist()))
print("after demodulation" + " ".join(f"{v:7.3f}" for v in out_d.std((0, 2, 3)).tolist()))
assert (out_a - out_b).abs().max() < 1e-9 and (out_b.std((0, 2, 3)) / sigma - 1).abs().max() < .02 and (out_d.std((0, 2, 3)) - 1).abs().max() < .02

# 4. The assumption behind demodulation is independent inputs. Give it blurred inputs of the same unit variance and it no longer delivers 1.
xc = torch.nn.functional.avg_pool2d(xin, 3, 1); xc = xc / xc.std((0, 2, 3), keepdim=True)
sd_c = torch.nn.functional.conv2d(xc, wd).std((0, 2, 3))
print(f"\ndemodulated outputs for smooth inputs: smallest std {sd_c.min():.3f}, largest {sd_c.max():.3f}  (independent inputs gave {out_d.std((0, 2, 3)).min():.3f} to {out_d.std((0, 2, 3)).max():.3f})")
assert (sd_c - 1).abs().max() > .1
