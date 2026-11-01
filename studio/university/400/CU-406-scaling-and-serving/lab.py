# CU-406 lab: a small simulator of jobs, workers and model loads. All costs are made up by us: read the shape, not the numbers. CPU, no server.
import heapq, random
random.seed(0)
# 1. One server process runs one job at a time, in order of a number. The heap below is what PromptQueue does, and "front" means a negative number.
q = []; n = 0
for name, front in (("a", False), ("b", False), ("urgent", True), ("c", False)):
    n += 1; heapq.heappush(q, (-n if front else n, name))
print("run order with front on one job:", [heapq.heappop(q)[1] for _ in range(4)])
# 2. Batch size: a fixed cost for each job plus a cost per image, and a memory cap.
def job(bs, fixed=2.0, per=1.0): return fixed + per * bs
print("\nbatch  seconds per job  images per second  seconds until you see anything")
for bs in (1, 2, 4, 8, 16): print(f"{bs:<6d} {job(bs):<16.1f} {bs / job(bs):<18.2f} {job(bs):.1f}")
assert 16 / job(16) > 1 / job(1)
# 3. Workers and model loads. Each job needs one of 3 models. Loading costs 20 s, a job costs 5 s. Sticky routing sends a job to a worker that has its model.
def simulate(workers, route, jobs=300, gap=2.5, load=20.0, run=5.0, seed=1):
    r = random.Random(seed); free = [0.0] * workers; have = [None] * workers; waits = []; loads = 0; t = 0.0; rr = 0
    for j in range(jobs):
        t += r.expovariate(1 / gap); m = r.randrange(3)
        if route == "round robin": w = rr % workers; rr += 1
        elif route == "least busy": w = min(range(workers), key=lambda i: free[i])
        else: w = min(range(workers), key=lambda i: (free[i] + (0 if have[i] == m else load)))
        start = max(t, free[w]); cost = run
        if have[w] != m: cost += load; have[w] = m; loads += 1
        free[w] = start + cost; waits.append(free[w] - t)
    waits.sort(); return sum(waits) / len(waits), waits[int(.95 * len(waits))], loads
print("\nworkers  routing        mean wait s  95th pct s  model loads")
res = {}
for w in (2, 4):
    for rt in ("round robin", "least busy", "sticky"):
        m, p, l = simulate(w, rt); res[(w, rt)] = (m, l); print(f"{w:<8d} {rt:<14s} {m:<12.1f} {p:<11.1f} {l}")
assert res[(4, "sticky")][1] < res[(4, "round robin")][1] and res[(4, "sticky")][0] < res[(4, "round robin")][0]
# 4. Load: at what arrival rate does a queue stop being usable? Above 100% busy it grows without limit.
print("\none worker, one model, 5 s per job\none job every   busy   mean wait s")
for gap in (20, 10, 6, 5.5, 4.5):
    r = random.Random(2); free = 0.0; t = 0.0; ws = []
    for _ in range(2000):
        t += r.expovariate(1 / gap); s = max(t, free); free = s + 5; ws.append(free - t)
    print(f"{gap:<15.1f} {5 / gap:<6.0%} {sum(ws) / len(ws):.1f}")
assert 5 / 4.5 > 1
