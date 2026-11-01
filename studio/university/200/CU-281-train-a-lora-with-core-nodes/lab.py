# CU-281 lab: reading the real loss list of our 300-step run. LOSS is copied from studio/web/train_example.js (job 4d13a830507c, SDXL base 1.0, 12 pictures, rank 8, 1024 px).
import random
LOSS = [0.5354,0.055,0.1164,0.0282,0.0562,0.5771,0.1122,0.1058,0.1702,0.1446,0.1066,0.0849,0.0826,0.004,0.1547,0.2901,0.0095,0.2588,0.2849,0.1975,0.0036,0.1818,0.0395,0.0603,0.0276,0.0651,0.15,0.4633,0.3737,0.1371,0.2431,0.0641,0.3974,0.1934,0.2157,0.2127,0.2722,0.0591,0.1817,0.4858,0.1446,0.3208,0.1417,0.0198,0.2284,0.0712,0.0977,0.229,0.0264,0.1812,0.1687,0.0597,0.197,0.0271,0.1451,0.0835,0.136,0.1535,0.4799,0.1441,0.4147,0.0807,0.214,0.2366,0.0445,0.0886,0.3907,0.3075,0.2323,0.2308,0.1659,0.1356,0.2028,0.1956,0.2157,0.2553,0.0832,0.1557,0.2488,0.2777,0.2463,0.1357,0.2547,0.1982,0.0681,0.2243,0.2639,0.1732,0.2589,0.2463,0.1039,0.2686,0.4747,0.1831,0.2007,0.263,0.3093,0.0833,0.3002,0.0412,0.1956,0.1897,0.1878,0.196,0.0589,0.3138,0.3882,0.2447,0.2614,0.0942,0.2921,0.3654,0.2878,0.3377,0.1907,0.2986,0.2173,0.2213,0.3943,0.3101,0.2813,0.1507,0.2543,0.0871,0.3959,0.2154,0.2018,0.1953,0.2462,0.2636,0.1101,0.1307,0.2463,0.019,0.18,0.215,0.1088,0.171,0.2471,0.411,0.2319,0.2501,0.379,0.0069,0.4081,0.1013,0.2083,0.0693,0.0017,0.4156,0.1289,0.2276,0.0309,0.3192,0.3459,0.0137,0.0985,0.0041,0.3918,0.0458,0.3376,0.1801,0.0989,0.3962,0.0878,0.2158,0.2615,0.098,0.2315,0.0576,0.0701,0.1882,0.4352,0.3815,0.0981,0.34,0.0122,0.1572,0.0868,0.2474,0.0343,0.2955,0.0413,0.3278,0.5559,0.3872,0.3948,0.1359,0.1223,0.2569,0.1954,0.0509,0.3344,0.1787,1.1148,0.5897,0.2903,0.017,0.0016,0.4266,0.1369,0.0203,0.3834,0.388,0.2108,0.2916,0.0073,0.2824,0.2534,0.1287,0.1896,0.3551,0.1426,0.051,0.3584,0.0936,0.3836,0.2721,0.2693,0.1858,0.0706,0.0022,0.3702,0.0871,0.0958,0.2051,0.3295,0.2689,0.082,0.2361,0.2737,0.0883,0.0337,0.3557,0.1301,0.1291,0.2483,0.2569,0.2034,0.1262,0.2262,0.2196,0.3297,0.3017,0.214,0.0633,0.391,0.0075,0.2467,0.4051,0.213,0.1957,0.1394,0.1878,0.0354,0.3035,0.2341,0.2286,0.332,0.1168,0.1112,0.2214,0.2223,0.0659,0.243,0.2282,0.239,0.1435,0.18,0.1362,0.2419,0.1513,0.0378,0.1764,0.0154,0.2446,0.071,0.3005,0.0618,0.0577,0.2111,0.2891,0.3936,0.137,0.0562,0.2522,0.162,0.2819,0.1516,0.3825,0.2031,0.0837,0.2982,0.0056,0.1495,0.221,0.3333,0.3293,0.078,0.1693]
assert len(LOSS) == 300
mean = lambda x: sum(x) / len(x)
def sd(x):
    m = mean(x); return (sum((v - m) ** 2 for v in x) / len(x)) ** 0.5
print(f"steps {len(LOSS)}   lowest {min(LOSS):.4f}   highest {max(LOSS):.4f}   mean {mean(LOSS):.4f}   spread (sd) {sd(LOSS):.4f}")
print("\nby tenths of the run")
print("steps       mean     sd       min      max")
tenths = [LOSS[i:i + 30] for i in range(0, 300, 30)]
for i, t in enumerate(tenths):
    print(f"{i * 30 + 1:>3}-{i * 30 + 30:<7} {mean(t):<8.4f} {sd(t):<8.4f} {min(t):<8.4f} {max(t):.4f}")
first, last = mean(tenths[0]), mean(tenths[-1]); gap = last - first
print(f"\nfirst tenth {first:.4f}, last tenth {last:.4f}: it went {'up' if gap > 0 else 'down'} by {abs(gap):.4f}")
# Is that gap more than noise? Shuffle the same 300 numbers many times and count how often chance alone gives a gap as wide.
r = random.Random(0); N = 5000; hits = 0; L = LOSS[:]
for _ in range(N):
    r.shuffle(L)
    if abs(mean(L[-30:]) - mean(L[:30])) >= abs(gap): hits += 1
print(f"shuffled order, {N} tries: a gap this wide came up {hits / N:.3f} of the time")
assert first == mean(LOSS[:30]) and 0 <= hits <= N
# Rolling means: how long must a window be before the line stops jumping?
print("\nwindow   largest step between neighbouring windows (not overlapping)")
for w in (1, 5, 10, 30, 60):
    parts = [mean(LOSS[i:i + w]) for i in range(0, 300 - w + 1, w)]; print(f"{w:<8} {max(abs(a - b) for a, b in zip(parts, parts[1:])):.4f}")
print("\nthe run's other numbers, from studio/train_measured.json and train_example.js")
print("pictures 12   steps 300   average sightings per picture", 300 / 12, "at batch 1")
print("rank 8   size 1024   seconds per step 0.6155   300 x 0.6155 =", round(300 * 0.6155, 1), "s   peak memory 40.25 GiB   setup 13.8 s")
assert 300 / 12 == 25
