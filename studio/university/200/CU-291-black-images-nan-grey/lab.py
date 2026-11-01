# CU-291 lab: what one bad number does, in plain torch on a CPU. No model runs. The save step follows SaveImage in nodes.py, and the lesson reports what the real node did with NaN. The convolution stands in for any layer of a VAE.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
x = torch.rand(1, 3, 32, 32); x[0, 0, 10, 12] = float("nan")
c = torch.nn.Conv2d(3, 3, 3, padding=1, bias=False); torch.nn.init.constant_(c.weight, 1 / 27)
print(f"start: {int(x.isnan().sum())} NaN of {x.numel()} values")
y = x
with torch.no_grad():
    for i in range(1, 25):
        y = c(y)
        if i in (1, 2, 4, 8, 16, 24): print(f"after {i:2} layers: {int(y.isnan().sum()):5} NaN of {y.numel()}")
assert y.isnan().all()
# The decode clamp and the save do not repair it.
v = torch.tensor([float("nan"), -5.0, 5.0, 0.5])
cl = torch.clamp((v + 1) / 2, 0, 1); print("\nclamp((v + 1) / 2, 0, 1) of nan, -5, 5, 0.5:", cl.tolist())
assert cl[0].isnan()
print("to 8 bits, torch:", (255 * torch.tensor(float("nan"))).to(torch.uint8).item(), " so NaN pixels land on 0: black")
# How a VAE reaches NaN in fp16: the largest fp16 value is 65504, and a bigger one becomes inf.
big = torch.tensor([60000.0, 70000.0]); print("\nin fp16:", big.to(torch.float16).tolist(), " in bf16:", big.to(torch.bfloat16).tolist(), " in fp32:", big.tolist())
inf = torch.tensor(70000.0).to(torch.float16); print("inf - inf:", (inf - inf).item(), "  inf * 0:", (inf * 0).item())
assert inf.isinf() and (inf - inf).isnan() and torch.tensor(70000.0).to(torch.bfloat16).isfinite()
# Wrong VAE scale. These factors are from comfy/latent_formats.py.
SD15, SDXL = 0.18215, 0.13025
z = torch.randn(1, 4, 8, 8)
print(f"\nlatent scale, SD15 {SD15}  SDXL {SDXL}: decoding through the wrong one multiplies the latent by {SD15 / SDXL:.3f} or {SDXL / SD15:.3f}")
assert abs(SD15 / SDXL - 1.398) < 0.001
# Denoise on an empty latent: how much noise the sampler starts with. Karras schedule, as in get_sigmas_karras in comfy/k_diffusion/sampling.py, with SD 1.5's limits.
def karras(n, smin=0.0292, smax=14.6146, rho=7.0):
    r = [i / (n - 1) for i in range(n)]
    return [(smax ** (1 / rho) + a * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho for a in r] + [0.0]
print("\nempty latent, denoise d, 20 steps: the noise it starts from")
for d in (1.0, 0.75, 0.5, 0.25):
    total = int(20 / d); s = karras(total)[-(20 + 1):]; print(f"d={d:<5} start sigma {s[0]:7.3f}  of a possible {karras(20)[0]:.3f}")     # KSampler.set_steps in comfy/samplers.py
assert karras(20)[0] > 14 and karras(80)[-21] < 1
