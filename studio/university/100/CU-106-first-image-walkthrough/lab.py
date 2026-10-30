# CU-106 lab: one image through checkpoint, text encoder, sampler and VAE, as numbers. Standard library only, about a second.
# Run: python lab.py
# Part 1 is shape arithmetic for the classic graph. Part 2 rebuilds the sigma list that the SD 1.x "normal" scheduler gives and checks it against the
# 20-step list printed in ComfyUI's documentation. Part 3 walks a toy sampler down that list, with no network, to see what each step does.
import math, random

# 1. The hand-offs of the classic text-to-image graph, for a 512 x 512 image.
W = H = 512
lat_c, ratio, ctx, width = 4, 8, 77, 768                      # SD 1.x: 4 latent channels, VAE factor 8, CLIP-L 77 positions of width 768
lat = lat_c * (H // ratio) * (W // ratio); img = 3 * H * W
print("node                       output       shape                numbers")
for name, out, shp, n in (("CLIPTextEncode", "CONDITIONING", f"[1, {ctx}, {width}]", ctx * width),
                          ("EmptyLatentImage", "LATENT", f"[1, {lat_c}, {H // ratio}, {W // ratio}]", lat),
                          ("KSampler", "LATENT", f"[1, {lat_c}, {H // ratio}, {W // ratio}]", lat),
                          ("VAEDecode", "IMAGE", f"[1, {H}, {W}, 3]", img)):
    print(f"{name:<27}{out:<13}{shp:<21}{n:,d}")
print(f"the sampler works on {lat:,d} numbers, the picture has {img:,d}: {img // lat}x more")

# 2. Sigma list of an SD 1.x model: scaled-linear betas, 1000 steps, sigma = sqrt((1 - abar) / abar).
betas = [(math.sqrt(0.00085) + (math.sqrt(0.012) - math.sqrt(0.00085)) * i / 999) ** 2 for i in range(1000)]
abar, p = [], 1.0
for b in betas: p *= 1 - b; abar.append(p)
SIG = [math.sqrt((1 - a) / a) for a in abar]; LOG = [math.log(s) for s in SIG]
def sigma_at(t):                                               # ModelSamplingDiscrete.sigma: linear in log sigma between two neighbouring timesteps
    lo = int(math.floor(t)); hi = min(int(math.ceil(t)), 999); w = t - lo
    return math.exp((1 - w) * LOG[lo] + w * LOG[hi])
def normal_schedule(steps):                                    # the "normal" scheduler: timesteps spaced evenly from 999 down to 0, then a final 0
    return [sigma_at(999 * (1 - i / (steps - 1))) for i in range(steps)] + [0.0]
def schedule(steps, denoise=1.0):                              # KSampler.set_steps: for denoise < 1, build a longer list and keep its last steps + 1 values
    return normal_schedule(steps) if denoise > 0.9999 else normal_schedule(int(steps / denoise))[-(steps + 1):]
docs = [14.6146, 10.7468, 8.0815, 6.2049, 4.8557, 3.8654, 3.1238, 2.5572, 2.1157, 1.7648, 1.4806, 1.2458, 1.0481, 0.8784, 0.7297, 0.5964, 0.4736, 0.3555, 0.2322, 0.0292, 0.0]
sg = schedule(20)
print(f"\nsigma_max {SIG[-1]:.4f}, sigma_min {SIG[0]:.4f}")
print("20-step normal schedule:", " ".join(f"{s:.4f}" for s in sg))
print(f"same as the 20-step list in the documentation to four decimals: {[round(s, 4) for s in sg] == docs}")
assert [round(s, 4) for s in sg] == docs
print(f"\n{'denoise':<10}{'steps run':<12}{'list built with':<18}first sigma")
for dn in (1.0, 0.75, 0.5, 0.25):
    s = schedule(20, dn); print(f"{dn:<10}{len(s) - 1:<12}{f'{int(20 / dn) if dn < 1 else 20} steps':<18}{s[0]:.4f}")
assert len(schedule(20, 0.5)) == 21 and abs(schedule(20, 0.5)[0] - normal_schedule(40)[20]) < 1e-12

# 3. A toy sampler. Data: two blobs at plus and minus 2 along axis 0 (8 dimensions, spread 0.5); the exact denoiser is known, so no network is needed.
DIM, S, M, N = 8, 0.5, 2.0, 400
rng = random.Random(1234)
eps = [[rng.gauss(0, 1) for _ in range(DIM)] for _ in range(N)]
calls = 0
def denoise(x, sigma):                                         # D(x, sigma): the best guess of the clean sample
    global calls; calls += 1
    v = S * S + sigma * sigma; c = S * S / v
    return [c * x[0] + (1 - c) * M * math.tanh(M * x[0] / v)] + [c * xi for xi in x[1:]]
def euler(x, sg, trace=None):
    for i in range(len(sg) - 1):
        d_hat = denoise(x, sg[i]); d = [(a - b) / sg[i] for a, b in zip(x, d_hat)]
        if trace is not None: trace.append((x, d_hat))
        x = [a + di * (sg[i + 1] - sg[i]) for a, di in zip(x, d)]
    return x
def heun(x, sg):                                               # sample_heun: a second evaluation per step, except when the next sigma is 0
    for i in range(len(sg) - 1):
        d = [(a - b) / sg[i] for a, b in zip(x, denoise(x, sg[i]))]; dt = sg[i + 1] - sg[i]
        if sg[i + 1] == 0: x = [a + di * dt for a, di in zip(x, d)]
        else:
            x2 = [a + di * dt for a, di in zip(x, d)]; d2 = [(a - b) / sg[i + 1] for a, b in zip(x2, denoise(x2, sg[i + 1]))]
            x = [a + (d1 + d2) / 2 * dt for a, d1, d2 in zip(x, d, d2)]
    return x
runs = []
for e in eps:
    tr = []; x0 = [ei * math.sqrt(1 + sg[0] ** 2) for ei in e]; fin = euler(x0, sg, tr); runs.append((tr, fin))
dist = lambda u, v: math.sqrt(sum((a - b) ** 2 for a, b in zip(u, v)))
print(f"\n{'step':<6}{'sigma':<10}{'x to final':<13}denoised estimate to final")
for i in (0, 2, 4, 6, 8, 12, 16, 19):
    dx = sum(dist(tr[i][0], fin) for tr, fin in runs) / N; dd = sum(dist(tr[i][1], fin) for tr, fin in runs) / N
    print(f"{i:<6}{sg[i]:<10.4f}{dx:<13.3f}{dd:.3f}")
calls = 0; euler(list(eps[0]), sg); n_euler = calls
calls = 0; heun(list(eps[0]), sg); n_heun = calls
print(f"\nnetwork evaluations for 20 steps: Euler {n_euler}, Heun {n_heun}")
assert n_euler == 20 and n_heun == 39
