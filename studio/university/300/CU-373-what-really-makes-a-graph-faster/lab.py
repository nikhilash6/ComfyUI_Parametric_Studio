# CU-373 lab: count before you measure, and measure before you believe. Timings below are real, from our Sampling Lab renders. One seed, one prompt, polled every 1.5 s.
import math
print("timed renders of one graph on our test machine, from sampling_lab/renders.json, seconds")
R = [("sampler-euler (first render of this model)", 66.0), ("sampler-euler_ancestral", 1.5), ("sampler-heun", 1.5), ("sampler-dpmpp_2m", 1.5), ("sampler-ddim", 1.5), ("sampler-lcm", 1.5)]
for n, s in R: print(f"  {n:44s} {s:5.1f}")
vals = [s for _, s in R]; print(f"  mean {sum(vals) / len(vals):.1f} s, median {sorted(vals)[len(vals) // 2]:.1f} s. The first run measures the loader.")
assert vals[0] / sorted(vals)[len(vals) // 2] > 40
print("\nmeasure on identical terms: with the polling used there, 1.5 s is the smallest step a timing can show, so these renders can't rank samplers")
def paired(before, after):
    """Median of each side, dropping the first run on both."""
    a = sorted(before[1:]); b = sorted(after[1:]); return a[len(a) // 2], b[len(b) // 2]
print("\nwhat each lever changes, by counting. One image, SD-like, baseline 20 steps at CFG 7, 1024 px")
def calls(steps, cfg): return steps * (1 if cfg == 1 else 2)
def area(side, batch=1): return batch * (side // 8) ** 2
base = calls(20, 7) * area(1024)
for name, c in (("baseline", calls(20, 7) * area(1024)), ("distilled: 4 steps, CFG 1", calls(4, 1) * area(1024)), ("fewer steps on a normal model: 10", calls(10, 7) * area(1024)), ("smaller latent: 768 px", calls(20, 7) * area(768)), ("smaller latent: 512 px", calls(20, 7) * area(512)), ("cached prompt: no change to sampling", calls(20, 7) * area(1024))):
    print(f"  {name:38s} calls x cells = {c:>8d}   {c / base:6.1%} of baseline")
assert calls(4, 1) * 10 == calls(20, 7) and area(512) * 4 == area(1024)
print("\ntiled VAE: get_tiled_scale_steps, ported. Memory falls with the tile, passes rise")
def steps(w, h, tx, ty, o):
    rows = 1 if h <= ty else math.ceil((h - o) / (ty - o)); cols = 1 if w <= tx else math.ceil((w - o) / (tx - o)); return rows * cols
def decode_tiled_passes(w, h, tx, ty, o): return steps(w, h, tx, ty, o) + steps(w, h, tx // 2, ty * 2, o) + steps(w, h, tx * 2, ty // 2, o)
print("  a 1024 px image is a 128 x 128 latent. decode_tiled_ decodes three times, with tiles of three shapes, and averages")
for t, o in ((64, 16), (64, 8), (32, 8)):
    print(f"  tile {t}, overlap {o}: {decode_tiled_passes(128, 128, t, t, o):3d} tile decodes, each {t * t / (128 * 128):5.1%} of the whole latent's cells")
assert steps(128, 128, 64, 64, 16) == 9
assert steps(32, 32, 64, 64, 16) == 1
print("\nfrom our own process notes, not re-run here: one video graph, 40 steps, core EasyCache at 0.2 / 0.15-0.95: 419 s to 189 s")
print(f"  that is {419 / 189:.2f} times faster on that graph, and we have no number for any other")
assert 2.2 < 419 / 189 < 2.3
print("\nan honest small report")
print("  graph, seed, steps, card, what changed, first run left out, three runs each, median, and did the picture change?")
