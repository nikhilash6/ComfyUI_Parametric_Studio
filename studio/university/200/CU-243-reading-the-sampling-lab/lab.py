# CU-243 lab: the numbers behind the Sampling Lab's pages, recomputed the way the page and its build scripts compute them. The tables are copied from atlas.json, measures.json and renders.json.
import math
ATLAS = dict(total=720, family={'sampler': 164, 'scheduler': 114, 'guidance': 174, 'noise': 79, 'latent': 91, 'math': 12, 'patch': 86}, label={'from code': 692, 'inference': 26, 'from pack README claim': 2}, core=183, live=13, rendered=44, second_reader={'correct': 296, 'minor': 68, 'wrong': 14}, read_again=378, fixed=69)
RENDERS = 44; PACK_RENDERED = 0; PACK_TRIED = 6
KARRAS = [14.61464, 11.72537, 9.3402, 7.38362, 5.78941, 4.49983, 3.46475, 2.64084, 1.99092, 1.48321, 1.09079, 0.79095, 0.56472, 0.39639, 0.27304, 0.18417, 0.12134, 0.07786, 0.04848, 0.02917, 0.0]
LQ = [14.61464, 14.5781, 14.54157, 14.50503, 14.4685, 14.43196, 14.39542, 14.35888, 14.32235, 14.28581, 14.24928, 14.0739, 13.62084, 12.89011, 11.8817, 10.59562, 9.03185, 7.1904, 5.07128, 2.67448, 0.0]
EULER = {5: 0.3150001, 10: 0.1548467, 20: 0.0768204, 40: 0.0384046}; STORED_SLOPE = -1.01
HEUN = { 9: 0.3193589, 19: 0.0558371, 39: 0.0113833, 79: 0.0022932 }; HEUN_SLOPE = -2.24
SPECTRUM = [0.941, 1.006, 1.016, 1.005, 1.017, 1.003, 1.009, 1.005, 0.983, 0.988, 1.012, 0.991, 1.009, 0.996, 1.007, 1.011]
ANC_STEP_1 = [14.6146, 11.7254, 9.4073, 6.9991]
print(f"atlas: {ATLAS['total']} methods; {ATLAS['core']} in core; {ATLAS['live']} in a live pack only; {ATLAS['total'] - ATLAS['core'] - ATLAS['live']} need a pack; {ATLAS['rendered']} rendered")
print("by family:", ", ".join(f"{k} {v}" for k, v in sorted(ATLAS["family"].items())))
print("by label:", ", ".join(f"{k} {v}" for k, v in sorted(ATLAS["label"].items())))
s = ATLAS["second_reader"]; n = s["correct"] + s["minor"] + s["wrong"]
print(f"second reader looked at {n}: {s['correct']} right, {s['minor']} imprecise, {s['wrong']} wrong, so {(s['minor'] + s['wrong']) / n:.0%} needed a fix or a caveat. Share of all methods checked this way: {n / ATLAS['total']:.0%}")
print(f"of those {s['minor'] + s['wrong']}, corrected in the atlas: {ATLAS['fixed']}")
assert sum(ATLAS["label"].values()) == ATLAS["total"] == sum(ATLAS["family"].values())
print(f"renders: {RENDERS} real, all in core. Pack methods proven by a render: {PACK_RENDERED} of {PACK_TRIED} tried")
print("\nCurves page: 'Sigma here' is the list at a step, 'Last before 0' is the last non-zero value")
last = lambda v: [x for x in v if x > 0][-1]
print(f"karras step 0: {KARRAS[0]}  step 10: {KARRAS[10]}  last before 0: {last(KARRAS)}")
print(f"linear_quadratic step 0: {LQ[0]}  step 10: {LQ[10]}  last before 0: {last(LQ)}")
assert last(KARRAS) == .02917 and last(LQ) == 2.67448
print("\nBench page: slope is the straight-line fit of log error against log calls, at 10, 20 and 40 steps")
def slope(rows):
    use = list(rows.items())[1:]; xs = [math.log(k) for k, v in use]; ys = [math.log(v) for k, v in use]; mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
print(f"euler: {slope(EULER):.2f}, stored {STORED_SLOPE}.  Double the calls and the error is multiplied by {2 ** slope(EULER):.2f}")
print(f"heun:  {slope(HEUN):.2f}, stored {HEUN_SLOPE}.  Double the calls and the error is multiplied by {2 ** slope(HEUN):.2f}")
assert abs(slope(EULER) - STORED_SLOPE) < .01 and abs(slope(HEUN) - HEUN_SLOPE) < .01
print("\nnoise panel: a bar at 1.00 holds its fair share of power")
print(f"bands {len(SPECTRUM)}, lowest {min(SPECTRUM)}, highest {max(SPECTRUM)}, mean {sum(SPECTRUM) / len(SPECTRUM):.3f}")
print("ancestral panel, karras, first step [from, to, sigma down, sigma up]:", ANC_STEP_1)
assert abs(ANC_STEP_1[2] ** 2 + ANC_STEP_1[3] ** 2 - ANC_STEP_1[1] ** 2) < .01
