# CU-235 lab: choosing a scheduler. The lists are copied from measures.json, made by ComfyUI's own code. The two ports at the top are checked against them.
import math, torch
torch.set_num_threads(1)
SD = {'simple': [14.61464, 10.90424, 8.3028, 6.44296, 5.08776, 4.08173, 3.32108, 2.73547, 2.27646, 1.91025, 1.61289, 1.36717, 1.16058, 0.98382, 0.82986, 0.6932, 0.56928, 0.45382, 0.34167, 0.223, 0.0], 'sgm_uniform': [14.61464, 10.90732, 8.30717, 6.44769, 5.09241, 4.08608, 3.32507, 2.73908, 2.27973, 1.91321, 1.61558, 1.36964, 1.16286, 0.98596, 0.83188, 0.69515, 0.57119, 0.45574, 0.3437, 0.22545, 0.0], 'karras': [14.61464, 11.72537, 9.3402, 7.38362, 5.78941, 4.49983, 3.46475, 2.64084, 1.99092, 1.48321, 1.09079, 0.79095, 0.56472, 0.39639, 0.27304, 0.18417, 0.12134, 0.07786, 0.04848, 0.02917, 0.0], 'exponential': [14.61464, 10.53631, 7.59607, 5.47632, 3.94811, 2.84636, 2.05206, 1.47942, 1.06657, 0.76894, 0.55436, 0.39966, 0.28813, 0.20773, 0.14976, 0.10797, 0.07784, 0.05612, 0.04046, 0.02917, 0.0], 'ddim_uniform': [11.02833, 8.39069, 6.5064, 5.13443, 4.1167, 3.34776, 2.7562, 2.29285, 1.92344, 1.62369, 1.37618, 1.16822, 0.99041, 0.83565, 0.6984, 0.57405, 0.45833, 0.34619, 0.22815, 0.04131, 0.0], 'beta': [14.61464, 13.5157, 11.54277, 9.38892, 7.37184, 5.68659, 4.3728, 3.37472, 2.61524, 2.04731, 1.61828, 1.28462, 1.02733, 0.82122, 0.65489, 0.51539, 0.39551, 0.29128, 0.19906, 0.11142, 0.0], 'normal': [14.61464, 10.7468, 8.08152, 6.20494, 4.85565, 3.86538, 3.12376, 2.55717, 2.11566, 1.76482, 1.48058, 1.24581, 1.04814, 0.87843, 0.72972, 0.59643, 0.47358, 0.35555, 0.23216, 0.02917, 0.0], 'linear_quadratic': [14.61464, 14.5781, 14.54157, 14.50503, 14.4685, 14.43196, 14.39542, 14.35888, 14.32235, 14.28581, 14.24928, 14.0739, 13.62084, 12.89011, 11.8817, 10.59562, 9.03185, 7.1904, 5.07128, 2.67448, 0.0], 'kl_optimal': [14.61463, 6.80715, 4.40147, 3.22191, 2.51469, 2.03866, 1.69282, 1.42737, 1.21493, 1.03914, 0.88961, 0.75942, 0.64374, 0.53908, 0.44283, 0.35298, 0.26794, 0.18636, 0.10711, 0.02917, 0.0]}
FLOW = {'simple': [1.0, 0.98276, 0.96429, 0.94444, 0.92308, 0.9, 0.875, 0.84783, 0.81818, 0.78571, 0.75, 0.71053, 0.66667, 0.61765, 0.5625, 0.5, 0.42857, 0.34615, 0.25, 0.13636, 0.0], 'sgm_uniform': [1.0, 0.98281, 0.9644, 0.94463, 0.92334, 0.90036, 0.87547, 0.84842, 0.81892, 0.78663, 0.75112, 0.71189, 0.66833, 0.61966, 0.56495, 0.50299, 0.43223, 0.35065, 0.25559, 0.14338, 0.0], 'karras': [1.0, 0.80982, 0.65152, 0.52052, 0.41278, 0.32475, 0.25333, 0.19582, 0.14988, 0.11351, 0.08498, 0.06283, 0.04583, 0.03293, 0.02328, 0.01616, 0.011, 0.00732, 0.00475, 0.00299, 0.0], 'exponential': [1.0, 0.7365, 0.54243, 0.3995, 0.29423, 0.2167, 0.1596, 0.11754, 0.08657, 0.06376, 0.04696, 0.03458, 0.02547, 0.01876, 0.01382, 0.01018, 0.00749, 0.00552, 0.00407, 0.00299, 0.0], 'ddim_uniform': [0.98347, 0.96505, 0.94527, 0.92396, 0.90096, 0.87604, 0.84896, 0.81942, 0.78707, 0.7515, 0.71218, 0.66851, 0.61972, 0.56484, 0.50266, 0.43162, 0.34969, 0.25415, 0.1413, 0.00598, 0.0], 'beta': [1.0, 0.99563, 0.9863, 0.97294, 0.95534, 0.93353, 0.90758, 0.87708, 0.84095, 0.79907, 0.75075, 0.69441, 0.63094, 0.55897, 0.47959, 0.39217, 0.29808, 0.20242, 0.11368, 0.04086, 0.0], 'normal': [1.0, 0.98187, 0.96239, 0.94137, 0.91865, 0.894, 0.86717, 0.83785, 0.80569, 0.77024, 0.73097, 0.68724, 0.63824, 0.58295, 0.52007, 0.44794, 0.36435, 0.26633, 0.14979, 0.00893, 0.0], 'linear_quadratic': [1.0, 0.9975, 0.995, 0.9925, 0.99, 0.9875, 0.985, 0.9825, 0.98, 0.9775, 0.975, 0.963, 0.932, 0.882, 0.813, 0.725, 0.618, 0.492, 0.347, 0.183, 0.0], 'kl_optimal': [1.0, 0.92086, 0.8475, 0.77909, 0.71494, 0.65446, 0.59715, 0.5426, 0.49043, 0.44033, 0.39202, 0.34524, 0.29977, 0.25542, 0.21198, 0.1693, 0.12721, 0.08556, 0.0442, 0.00299, 0.0]}
# Render measures from renders.json, one seed: SDXL with dpmpp_2m (mean difference from the normal render, brightness, edge) and SD 3.5 with euler.
RENDER_SDXL = {'normal': (0.0, 87.4, 13.35), 'karras': (23.26, 86.5, 14.86), 'exponential': (19.21, 86.0, 13.09), 'sgm_uniform': (13.19, 87.5, 13.64), 'simple': (13.28, 87.5, 13.56), 'ddim_uniform': (37.87, 106.6, 16.09), 'beta': (19.62, 90.4, 14.12), 'linear_quadratic': (34.74, 75.6, 22.11), 'kl_optimal': (28.79, 77.1, 11.78)}
RENDER_FLOW = {'simple': (0.0, 94.9, 11.27), 'beta': (39.32, 92.1, 14.3), 'kl_optimal': (34.89, 96.5, 7.85), 'karras': (37.0, 95.3, 7.9)}
D = torch.float64
beta = torch.linspace(.00085 ** .5, .012 ** .5, 1000, dtype=D) ** 2; ab = torch.cumprod(1 - beta, 0); SIG = ((1 - ab) / ab).sqrt()
def ddim_uniform(steps):                              # ddim_scheduler in comfy/samplers.py
    ss = max(1000 // steps, 1); out = [0.]; x = 1
    while x < 1000: out.append(SIG[x].item()); x += ss
    return out[::-1]
def linear_quadratic(steps, smax, threshold=.025):    # linear_quadratic_schedule
    ls = steps // 2; lin = [i * threshold / ls for i in range(ls)]; diff = ls - threshold * steps; qs = steps - ls; qc = diff / (ls * qs ** 2); lc = threshold / ls - 2 * diff / qs ** 2; c = qc * ls ** 2
    return [(1 - x) * smax for x in lin + [qc * i ** 2 + lc * i + c for i in range(ls, steps)] + [1.]]
a = ddim_uniform(20); b = linear_quadratic(20, SIG[-1].item())
assert all(abs(x - y) < 1e-3 for x, y in zip(a, SD["ddim_uniform"])) and all(abs(x - y) < 1e-3 for x, y in zip(b, SD["linear_quadratic"]))
print("ports of ddim_uniform and linear_quadratic match the stored lists from ComfyUI's code: True")
print(f"ddim_uniform takes every {1000 // 20}th table entry from index 1, so its top is index {1 + 19 * 50} of 999: sigma {SIG[951]:.3f}, not {SIG[-1]:.3f}")
print("ddim_uniform steps asked for and returned:", [(n, len(ddim_uniform(n)) - 1) for n in (20, 25, 30)])
def table(name, S, top):
    print(f"\n{name}, 20 steps")
    print(f"scheduler         first    step 10   last before 0   steps above sigma {top}")
    for k, v in S.items():
        print(f"{k:17s} {v[0]:<8.3f} {v[10]:<9.3f} {v[-2]:<15.4f} {sum(x > top for x in v[:-1])}")
table("SD and SDXL noise prediction", SD, 1.0)
table("SD 3.5, flow, shift 3", FLOW, .5)
assert abs(SD["linear_quadratic"][-2] - 2.67448) < 1e-4 and abs(SD["ddim_uniform"][0] - 11.02833) < 1e-4 and FLOW["karras"][10] < .1 < FLOW["simple"][10]
print("\nrenders on one seed, difference from the baseline, brightness, edge strength")
for k, v in RENDER_SDXL.items(): print(f"SDXL {k:17s} {v[0]:<7} {v[1]:<7} {v[2]}")
for k, v in RENDER_FLOW.items(): print(f"SD3.5 {k:16s} {v[0]:<7} {v[1]:<7} {v[2]}")
gap = lambda p, q: sum(abs(x - y) for x, y in zip(SD[p], SD[q])) / len(SD[p])
print(f"\nsgm_uniform and simple, mean gap between lists {gap('sgm_uniform', 'simple'):.4f}; karras and exponential {gap('karras', 'exponential'):.4f}; normal and karras {gap('normal', 'karras'):.4f}")
