# CU-470 lab: how to compare two samplers. Part 1 uses numbers from this course's Sampling Lab measurements, copied here. Parts 2 to 5 are simulated.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# measures.json, solvers.<name>.eps: steps -> (model calls, rmse to the exact answer of the toy problem).
M = {"euler": {5: (5, .3150001), 10: (10, .1548467), 20: (20, .0768204), 40: (40, .0384046)}, "heun": {5: (9, .3193589), 10: (19, .0558371), 20: (39, .0113833), 40: (79, .0022932)}, "dpmpp_2m": {5: (5, .0630924), 10: (10, .0540504), 20: (20, .0119132), 40: (40, .002343)}}
print("toy problem, model calls and error (from the Sampling Lab)")
print("sampler    steps  calls  rmse")
for s in M:
    for st in (10, 20): print(f"{s:<10s} {st:<6d} {M[s][st][0]:<6d} {M[s][st][1]:.4f}")
print(f"\nsame steps (20): heun {M['heun'][20][1]:.4f} beats euler {M['euler'][20][1]:.4f}, for {M['heun'][20][0]} calls against {M['euler'][20][0]}")
print(f"same calls (about 20): heun at 10 steps {M['heun'][10][1]:.4f}, euler at 20 steps {M['euler'][20][1]:.4f}, dpmpp_2m at 20 steps {M['dpmpp_2m'][20][1]:.4f}")
assert M['dpmpp_2m'][20][1] < M['heun'][10][1] < M['euler'][20][1]
# Renders: one prompt, one seed, renders.json. "edge" is a simple detail measure and "seconds" includes model load for the first one.
R = {"euler": (102.4, 72.1, 20.17, 66.0), "heun": (106.4, 80.5, 23.38, 1.5), "dpmpp_2m": (105.1, 77.2, 22.93, 1.5), "euler_ancestral": (81.6, 51.7, 12.16, 1.5)}
print("\none seed, one prompt (from the Sampling Lab renders)\nsampler           brightness  contrast  edge    seconds")
for k, v in R.items(): print(f"{k:<17s} {v[0]:<11.1f} {v[1]:<9.1f} {v[2]:<7.2f} {v[3]}")
print("seconds are polled every 1.5 s, and euler's 66 includes loading the model, so these can't rank speed")
# Simulation: a score per render = seed effect + sampler effect + small noise. Seeds differ more than samplers do. All sizes are chosen by us.
def sim(n, diff, seed_sd=5.0, noise_sd=1.0, g=None):
    s = seed_sd * torch.randn(n, generator=g); a = s + noise_sd * torch.randn(n, generator=g); b = s + diff + noise_sd * torch.randn(n, generator=g)
    return a, b, seed_sd * torch.randn(n, generator=g) + noise_sd * torch.randn(n, generator=g) + diff            # b at the same seeds as a, and b at different seeds
def ci(x):
    return x.mean().item(), 2 * x.std().item() / math.sqrt(len(x))
g = torch.Generator().manual_seed(1)
print("\ntrue difference 1.0, seed effect sd 5, noise sd 1, a score for each render")
print("seeds per sampler   same seeds: diff +/- range   different seeds: diff +/- range")
for n in (1, 4, 16, 64, 256):
    if n == 1: a, b, c = sim(1, 1.0, g=g); print(f"1                   {(b - a).item():+.2f}, no range               {(c - a).item():+.2f}, no range"); continue
    a, b, c = sim(n, 1.0, g=g); m1, r1 = ci(b - a); m2 = (c.mean() - a.mean()).item(); r2 = 2 * math.sqrt(c.var().item() / n + a.var().item() / n); print(f"{n:<19d} {m1:+.2f} +/- {r1:<17.2f} {m2:+.2f} +/- {r2:.2f}")
# Using the same seed removes the seed effect from the comparison, which is why it needs far fewer seeds.
def need(diff, sd): return math.ceil(round((2 * sd / diff) ** 2, 9))     # round first: (2 * sqrt(2)) ** 2 comes out a hair over 8 in floats
print(f"\nseeds for a range of +/- the true difference: same seeds (sd of difference {math.sqrt(2):.2f}): {need(1, math.sqrt(2))}, different seeds (sd {math.sqrt(2 * 26):.2f}): {need(1, math.sqrt(2 * 26))}"); assert need(1, math.sqrt(2)) < need(1, math.sqrt(2 * 26))
# How often one seed picks the wrong winner.
g = torch.Generator().manual_seed(2); x = 2.0 ** .5 * torch.randn(200000, generator=g) + 1.0; print(f"same seed, one render each, true difference +1 in favour of b: a looks better {(x < 0).float().mean().item():.0%} of the time")
assert .2 < (x < 0).float().mean() < .3
# Shopping: 15 samplers with no true difference at all, 8 seeds each, keep the best one.
g = torch.Generator().manual_seed(3); t = torch.randn(20000, 15, 8, generator=g).mean(2).max(1).values.mean().item(); print(f"15 equal samplers, 8 seeds each, noise sd 1: the winner's lead over the true mean averages {t:.2f}, so test the winner again on new seeds")
assert t > .4
