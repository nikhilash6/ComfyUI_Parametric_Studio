# CU-411 lab: two flicker scores on synthetic clips where we know the answer. flicker_score follows studio/vset/qc.py: mean |f(t+1) - 2 f(t) + f(t-1)| on 0-255 luma. CPU, seeded.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1); g = torch.Generator().manual_seed(0)
S, N = 64, 32
yy, xx = torch.meshgrid(torch.arange(S, dtype=torch.float32), torch.arange(S, dtype=torch.float32), indexing="ij")
tex = torch.nn.functional.avg_pool2d(torch.randn(1, 1, S * 3 + 8, S * 3 + 8, generator=g), 9, stride=1)[0, 0]; tex = (tex - tex.min()) / (tex.max() - tex.min()) * 255
def pan(speed): return torch.stack([tex[10:10 + S, int(t * speed):int(t * speed) + S] for t in range(N)])
still = pan(0)
clips = {
 "still frame": still,
 "slow pan, 1 pixel a frame": pan(1),
 "fast pan, 4 pixels a frame": pan(4),
 "fade to black": torch.stack([still[0] * (1 - t / N) for t in range(N)]),
 "brightness strobes 4%": torch.stack([still[0] * (1 + 0.04 * (-1) ** t) for t in range(N)]),
 "texture boils, noise 5 levels": still + 5 * torch.randn(N, S, S, generator=g),
 "scene cut in the middle": torch.cat([still[:N // 2], 255 - still[N // 2:]]),
}
def variance_score(v): return v.var(dim=0, unbiased=False).mean().item()
def flicker_score(v): return (v[2:] - 2 * v[1:-1] + v[:-2]).abs().mean().item()
def aligned_score(v, r=6):
    """second difference after alignment, on three neighbouring frames at a time, so a pan does not run off the picture"""
    tot = []
    for t in range(1, v.shape[0] - 1):
        def best(a, b): return min(range(-r, r + 1), key=lambda d: (a[:, r:-r] - torch.roll(b, d, 1)[:, r:-r]).abs().mean().item())
        p = torch.roll(v[t - 1], best(v[t], v[t - 1]), 1); n = torch.roll(v[t + 1], best(v[t], v[t + 1]), 1)
        tot.append((n - 2 * v[t] + p)[:, r:-r].abs().mean().item())
    return sum(tot) / len(tot)
print("clip                             temporal variance   second difference (qc.py)   second difference after aligning")
R = {}
for k, v in clips.items():
    R[k] = (variance_score(v), flicker_score(v), aligned_score(v)); print(f"{k:32s} {R[k][0]:<19.2f} {R[k][1]:<27.3f} {R[k][2]:.3f}")
assert R["still frame"][1] == 0 and R["fade to black"][1] < 0.01
assert R["fast pan, 4 pixels a frame"][0] > R["brightness strobes 4%"][0]              # variance calls the pan far worse than the strobe
assert R["fast pan, 4 pixels a frame"][1] > R["brightness strobes 4%"][1]              # so does the plain second difference, on a strongly textured pan
assert R["fast pan, 4 pixels a frame"][2] < 0.01 and R["brightness strobes 4%"][2] > 10 and R["texture boils, noise 5 levels"][2] > 5
# How the score scales with what it measures: strobing amplitude a on mean level L gives 4 a L for the second difference.
L = still[0].mean().item(); print(f"\nmean luma {L:.1f}. A strobe of amplitude a scores 4 a L on the second difference:")
for a in (0.01, 0.02, 0.04):
    v = torch.stack([still[0] * (1 + a * (-1) ** t) for t in range(N)]); print(f"a = {a:<5} measured {flicker_score(v):<7.3f} predicted {4 * a * L:.3f}"); assert abs(flicker_score(v) - 4 * a * L) < 0.01
# Range: scoring 0-1 images with a 0-255 threshold.
v = clips["brightness strobes 4%"]; print(f"\nsame clip on 0-1 numbers instead of 0-255: second difference {flicker_score(v / 255):.4f} (divided by 255), variance {variance_score(v / 255):.6f} (divided by 255 squared)")
# Few frames. With 2 frames the second difference does not exist. qc.py returns 0.0 below 3 frames, which reads as perfect.
print("fewer than 3 frames: qc.py returns 0.0, which is not a pass, only no measurement")
# One bad frame in many. The mean hides it.
b = still.clone(); b[16] = b[16] * 1.2; d2 = (b[2:] - 2 * b[1:-1] + b[:-2]).abs().mean(dim=(1, 2)); print(f"\none frame 20% too bright in {N}: mean {d2.mean():.3f}, worst moment {d2.max():.3f}")
assert d2.max() > 3 * d2.mean()
