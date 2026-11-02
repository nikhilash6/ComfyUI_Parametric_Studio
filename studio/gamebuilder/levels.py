"""Levels are numbers made here, from a seed and a size, and checked here: a model never places anything. Each kit reads the JSON as it stands. solvable() proves a level can be finished from the kit's own movement numbers before a game is ever built."""
from __future__ import annotations

import math
import random

#: The hero's real jump, from core/player3p.gd: jump speed, gravity up and falling, run speed.
JUMP_V, G_UP, FALL_MULT, RUN = 10.0, 24.0, 1.45, 7.5
MAX_GAP, MAX_RISE = 3.9, 1.3


def jump_reach(rise: float) -> float:
    """How far a full jump carries flat, ending `rise` metres above where it began. Negative when it can't get that high."""
    apex = JUMP_V ** 2 / (2 * G_UP)
    if rise > apex:
        return -1.0
    up = JUMP_V / G_UP
    down = math.sqrt(2 * (apex - rise) / (G_UP * FALL_MULT))
    return RUN * (up + down)


def _r(v, n=2):
    return [round(float(x), n) for x in v]


def platformer(spec: dict) -> dict:
    size = spec["level"]["size"]
    diff = spec["level"]["difficulty"]
    rng = random.Random(spec["level"]["seed"])
    n = {"small": 16, "medium": 24, "large": 34}[size]
    stars_n = {"small": 6, "medium": 9, "large": 12}[size]
    hardness = {"easy": 0.75, "normal": 0.88, "hard": 1.0}[diff]
    plats, route, coins, stars, foes, checks, decor = [], [], [], [], [], [], []

    def add(pos, sz, kind="ground", **more):
        plats.append({"pos": _r(pos), "size": _r(sz), "kind": kind, **more})
        return len(plats) - 1

    def visit(i, off=(0, 0)):
        p = plats[i]
        route.append({"p": i, "off": _r([off[0], p["size"][1] / 2, off[1]]), "near": 1.2})

    start = add((0, -2, 0), (13, 4, 13))
    visit(start)
    x, y, z = 0.0, 0.0, 0.0                 # the top surface of the last platform
    heading = 0.0
    half_last = 6.5
    hub_every = 5
    star_slots = []
    for k in range(1, n + 1):
        heading += rng.uniform(-0.5, 0.5)
        heading = max(-1.1, min(1.1, heading))
        dirx, dirz = math.sin(heading), -math.cos(heading)
        hub = k % hub_every == 0
        last = k == n
        moving = (not hub and not last and k % 4 == 3 and diff != "easy")
        w = 13.0 if last else rng.uniform(8.5, 10.5) if hub else rng.uniform(4.2, 6.0)
        gap = rng.uniform(1.8, MAX_GAP * hardness) if not moving else rng.uniform(1.4, 2.2)
        rise = rng.uniform(-0.8, MAX_RISE * hardness)
        # Measure the jump along the larger axis so a platform seen on the diagonal is still the gap it says.
        step = half_last + gap + w / 2
        nx, nz = x + dirx * step, z + dirz * step
        ny = y + rise
        thick = 3.0 if hub or last else 1.1
        if moving:
            side = (dirz, -dirx)
            amp = rng.uniform(1.6, 2.4)
            i = add((nx, ny - thick / 2, nz), (w, thick, w), "moving", move=_r((side[0] * amp, 0, side[1] * amp)), period=round(rng.uniform(4.5, 6.0), 2))
        else:
            i = add((nx, ny - thick / 2, nz), (w, thick, w))
        # Coins sit along the jump, showing the arc to take.
        for t in (0.3, 0.5, 0.7):
            cx, cz = x + (nx - x) * (half_last + gap * t) / step, z + (nz - z) * (half_last + gap * t) / step
            coins.append(_r((cx, y + rise * t + 1.5 * math.sin(math.pi * t) + 0.5, cz)))
        visit(i)
        if hub:
            checks.append(_r((nx - dirx * (w / 2 - 1.2), ny, nz - dirz * (w / 2 - 1.2))))
            if spec.get("enemies"):
                ax, az = -dirz, dirx
                foes.append({"pos": _r((nx + ax * w * 0.3, ny + 0.2, nz + az * w * 0.3)), "patrol": [_r((nx + ax * w * 0.34, ny, nz + az * w * 0.34)), _r((nx - ax * w * 0.34, ny, nz - az * w * 0.34))]})
            # On the far corners, off the line you arrive and leave by.
            for sx in (1, -1):
                ax, az = -dirz, dirx
                reach = w / 2 * 0.62
                decor.append({"prop": rng.randrange(6), "pos": _r((nx + sx * ax * reach + dirx * reach, ny, nz + sx * az * reach + dirz * reach)), "yaw": round(rng.uniform(0, 6.28), 2), "scale": round(rng.uniform(0.75, 1.0), 2)})
        if not last and not moving:
            star_slots.append((i, (nx, ny, nz)))
        x, y, z = nx, ny, nz
        half_last = w / 2
    goal = _r((x, y, z))
    # Two side islands off the path, each with a star: there and back is the same jump.
    for hub_i in [i for i, p in enumerate(plats) if p["size"][0] > 8 and 0 < i < len(plats) - 1][:2]:
        p = plats[hub_i]
        top = p["pos"][1] + p["size"][1] / 2
        side = 1 if rng.random() < 0.5 else -1
        w = 4.5
        off = p["size"][0] / 2 + 2.6 + w / 2
        rise = 0.9
        j = add((p["pos"][0] + side * off, top + rise - 0.55, p["pos"][2]), (w, 1.1, w))
        stars.append(_r((plats[j]["pos"][0], top + rise + 0.35, plats[j]["pos"][2])))
        at = next(ix for ix, r in enumerate(route) if r["p"] == hub_i)
        route[at + 1:at + 1] = [{"p": j, "off": _r([0, 0.55, 0]), "near": 1.2}, {"p": hub_i, "off": _r([0, p["size"][1] / 2, 0]), "near": 1.2}]
    picks = star_slots[:: max(1, len(star_slots) // max(1, stars_n - len(stars)))][: stars_n - len(stars)]
    for _, (sx, sy, sz_) in picks:
        stars.append(_r((sx, sy + 0.35, sz_)))
    for sx, sz_ in ((-4.5, 4.5), (4.5, 4.5)):
        decor.append({"prop": rng.randrange(6), "pos": _r((sx, 0, sz_)), "yaw": round(rng.uniform(0, 6.28), 2), "scale": 1.0})
    decor.append({"prop": 0, "pos": _r((x - 4.5, y, z + 4.5)), "yaw": 0.0, "scale": 1.0})
    decor.append({"prop": 1, "pos": _r((x + 4.5, y, z + 4.5)), "yaw": 1.0, "scale": 1.0})
    decor = [d for d in decor if not _in_the_way(d, route, plats)]
    low = min(p["pos"][1] for p in plats)
    return {"start": [0, 0.3, 2], "start_yaw": 0.0, "platforms": plats, "route": route, "stars": stars, "coins": coins, "enemies": foes, "checkpoints": checks, "goal": goal, "decor": decor, "kill_y": round(low - 9, 1), "jump_reach": round(MAX_GAP + 0.5, 2)}


def _dist_to_segment(p, a, b) -> float:
    ax, az, bx, bz = a[0], a[2], b[0], b[2]
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[2] - az) * dz) / max(dx * dx + dz * dz, 1e-6)))
    return math.hypot(p[0] - (ax + dx * t), p[2] - (az + dz * t))


def _in_the_way(d: dict, route: list, plats: list, clear: float = 2.6) -> bool:
    """A prop standing on the line from one stop to the next would block the way, however finishable the jumps are."""
    return any(_dist_to_segment(d["pos"], plats[a["p"]]["pos"], plats[b["p"]]["pos"]) < clear for a, b in zip(route, route[1:]))


def platformer_problems(lv: dict) -> list[str]:
    """Every step of the route has to be a jump the hero can really make, and each moving platform has to come within reach."""
    bad = []
    route = lv["route"]
    for a, b in zip(route, route[1:]):
        pa, pb = lv["platforms"][a["p"]], lv["platforms"][b["p"]]
        if a["p"] == b["p"]:
            continue
        ax, az, bx, bz = pa["pos"][0], pa["pos"][2], pb["pos"][0], pb["pos"][2]
        dx = max(abs(ax - bx) - (pa["size"][0] + pb["size"][0]) / 2, 0.0)
        dz = max(abs(az - bz) - (pa["size"][2] + pb["size"][2]) / 2, 0.0)
        gap = math.hypot(dx, dz)
        rise = (pb["pos"][1] + pb["size"][1] / 2) - (pa["pos"][1] + pa["size"][1] / 2)
        reach = jump_reach(rise)
        if reach < 0 or gap > reach - 0.6:
            bad.append(f"platform {a['p']} to {b['p']}: a gap of {gap:.1f} m with a rise of {rise:.1f} m is more than the jump's {reach:.1f} m")
    if not lv["stars"]:
        bad.append("no stars")
    if any(_in_the_way(d, route, lv["platforms"]) for d in lv["decor"]):
        bad.append("a prop stands in the way of the route")
    tops = [(p["pos"], p["size"]) for p in lv["platforms"]]
    for s in lv["stars"]:
        if not any(abs(s[0] - pos[0]) <= sz[0] / 2 + 0.1 and abs(s[2] - pos[2]) <= sz[2] / 2 + 0.1 for pos, sz in tops):
            bad.append(f"a star at {s} floats over nothing")
    return bad


def arena(spec: dict) -> dict:
    size = spec["level"]["size"]
    diff = spec["level"]["difficulty"]
    rng = random.Random(spec["level"]["seed"])
    n = {"small": 5, "medium": 7, "large": 9}[size]
    scale = {"easy": 0.75, "normal": 1.0, "hard": 1.3}[diff]
    half = {"small": 18.0, "medium": 22.0, "large": 26.0}[size]
    waves = [{"count": int(round((6 + i * 4) * scale)), "speed": round(3.5 + i * 0.36 * scale, 2), "hp": 2 + i // 3, "gap": round(max(0.26, 0.62 - i * 0.08), 2)} for i in range(n)]
    obstacles = []
    for i in range(8):
        a = i / 8 * math.tau + rng.uniform(-0.2, 0.2)
        r = half * rng.uniform(0.45, 0.72)
        obstacles.append({"prop": i, "pos": _r((math.cos(a) * r, 0, math.sin(a) * r)), "yaw": round(rng.uniform(0, 6.28), 2), "scale": round(rng.uniform(0.7, 1.0), 2)})
    spawns = [_r((x * (half - 2), 0.2, z * (half - 2))) for x in (-1, 0, 1) for z in (-1, 0, 1) if x or z]
    return {"half": half, "waves": waves, "obstacles": obstacles, "spawns": spawns}


def _closed_curve(rng, target_len, points_every=4.0):
    k = [(rng.uniform(0.10, 0.22), rng.choice([2, 3]), rng.uniform(0, 6.28)), (rng.uniform(0.05, 0.14), rng.choice([3, 4, 5]), rng.uniform(0, 6.28))]
    sx, sz = rng.uniform(1.0, 1.45), rng.uniform(0.75, 1.0)
    raw = []
    n = 720
    for i in range(n):
        t = i / n * math.tau
        r = 1.0 + sum(a * math.sin(f * t + p) for a, f, p in k)
        raw.append((math.cos(t) * r * sx, math.sin(t) * r * sz))
    length = sum(math.dist(raw[i], raw[(i + 1) % n]) for i in range(n))
    scale = target_len / length
    raw = [(x * scale, z * scale) for x, z in raw]
    out, acc = [raw[0]], 0.0
    for i in range(1, n):
        acc += math.dist(raw[i], raw[i - 1])
        if acc >= points_every:
            out.append(raw[i])
            acc = 0.0
    return out


def tightest_radius(c) -> float:
    n, best = len(c), 1e9
    for i in range(n):
        a, b, d = c[(i - 3) % n], c[i], c[(i + 3) % n]
        ab, bd, ad = math.dist(a, b), math.dist(b, d), math.dist(a, d)
        area = abs((b[0] - a[0]) * (d[1] - a[1]) - (d[0] - a[0]) * (b[1] - a[1])) / 2
        if area > 1e-6:
            best = min(best, ab * bd * ad / (4 * area))
    return best


def kart(spec: dict) -> dict:
    size = spec["level"]["size"]
    diff = spec["level"]["difficulty"]
    rng = random.Random(spec["level"]["seed"])
    target = {"small": 900.0, "medium": 1300.0, "large": 1800.0}[size]
    width = 11.5
    for _ in range(40):
        c = _closed_curve(rng, target)
        if tightest_radius(c) > 17.0:
            break
    n = len(c)
    gate_n = 6
    gates = [int(i * n / gate_n) for i in range(gate_n)]
    length = sum(math.dist(c[i], c[(i + 1) % n]) for i in range(n))
    curvy = sorted(range(n), key=lambda i: abs(_turn(c, i)))
    boosts, taken = [], []
    for i in curvy:
        if all(min(abs(i - t), n - abs(i - t)) > n // 5 for t in taken) and min(abs(i - gates[0]), n - abs(i - gates[0])) > 6:
            boosts.append(i)
            taken.append(i)
        if len(boosts) == 3:
            break
    laps = 3
    pace = {"easy": 1.2, "normal": 1.0, "hard": 0.88}[diff]
    # Measured from the bot's clean laps: about 28 m/s on average, boost strips included, no drifting. Gold asks for a clean race; the limit forgives a messy one.
    # Gold asks for drifts and boosts: the bot's clean line without them comes in about 6% over it.
    gold = round(length * laps / 28.0 * pace, 1)
    silver = round(gold * 1.1, 1)
    limit = round(gold * 1.55, 1)
    decor = []
    half = max(max(abs(x), abs(z)) for x, z in c) + 26
    tries = 0
    while len(decor) < 34 and tries < 800:
        tries += 1
        i = rng.randrange(n)
        side = rng.choice((-1, 1))
        px, pz = _normal(c, i)
        off = width / 2 + rng.uniform(12.0, 24.0)
        x, z = c[i][0] + px * off * side, c[i][1] + pz * off * side
        if min(math.dist((x, z), q) for q in c) < width / 2 + 10.5:
            continue
        decor.append({"prop": rng.randrange(6), "pos": _r((x, 0, z)), "yaw": round(rng.uniform(0, 6.28), 2), "scale": round(rng.uniform(0.8, 1.6), 2)})
    grid_n = 72
    grid_size = round((half + 80) * 2, 1)
    near = c[::3]
    p1, p2, p3 = rng.uniform(0, 6.28), rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    grid = []
    rise = width / 2 + 16
    for iz in range(grid_n):
        for ix in range(grid_n):
            x, z = ix / (grid_n - 1) * grid_size - grid_size / 2, iz / (grid_n - 1) * grid_size - grid_size / 2
            d = min(math.dist((x, z), q) for q in near)
            t = max(0.0, min(1.0, (d - rise) / 45.0))
            t = t * t * (3 - 2 * t)
            wob = 0.55 + 0.25 * math.sin(x * 0.021 + p1) * math.cos(z * 0.017 + p2) + 0.2 * math.sin((x + z) * 0.05 + p3)
            grid.append(round(t * 26.0 * wob, 1))
    return {"grid": grid, "grid_n": grid_n, "grid_size": grid_size, "center": [_r(p) for p in c], "width": width, "length": round(length, 1), "gates": gates, "boosts": boosts, "laps": laps, "gold": gold, "silver": silver, "limit": limit, "decor": decor, "half": round(half, 1)}


def _normal(c, i):
    n = len(c)
    a, b = c[(i - 1) % n], c[(i + 1) % n]
    dx, dz = b[0] - a[0], b[1] - a[1]
    l = math.hypot(dx, dz) or 1.0
    return -dz / l, dx / l


def _turn(c, i):
    n = len(c)
    a, b, d = c[(i - 4) % n], c[i], c[(i + 4) % n]
    return math.atan2(d[1] - b[1], d[0] - b[0]) - math.atan2(b[1] - a[1], b[0] - a[0])


def kart_problems(lv: dict) -> list[str]:
    bad = []
    c = [tuple(p) for p in lv["center"]]
    if tightest_radius(c) < 15.0:
        bad.append(f"a corner of radius {tightest_radius(c):.1f} m is too tight")
    n = len(c)
    # No part of the road may touch another: closest distance between points far apart along the track.
    for i in range(0, n, 3):
        for j in range(i + 12, n, 3):
            if min(j - i, n - (j - i)) < 12:
                continue
            if math.dist(c[i], c[j]) < lv["width"] + 8:
                bad.append("the track runs into itself")
                return bad
    if lv["limit"] <= lv["gold"]:
        bad.append("the limit must allow more than gold")
    return bad


def quest(spec: dict) -> dict:
    size = spec["level"]["size"]
    diff = spec["level"]["difficulty"]
    rng = random.Random(spec["level"]["seed"])
    half = {"small": 62.0, "medium": 80.0, "large": 96.0}[size]
    n = {"small": 3, "medium": 4, "large": 5}[size]
    guards = {"easy": 1, "normal": 2, "hard": 3}[diff]
    camps = []
    start = rng.uniform(0, 6.28)
    for i in range(n):
        a = start + i / n * math.tau + rng.uniform(-0.25, 0.25)
        r = half * rng.uniform(0.45, 0.62)
        camps.append({"x": round(math.cos(a) * r, 1), "z": round(math.sin(a) * r, 1), "guards": guards})
    scatter = []
    tries = 0
    while len(scatter) < 44 and tries < 2000:
        tries += 1
        x, z = rng.uniform(-half * 0.8, half * 0.8), rng.uniform(-half * 0.8, half * 0.8)
        if math.hypot(x, z) < 12 or math.hypot(x, z) > half * 0.8:
            continue
        if any(math.hypot(x - c["x"], z - c["z"]) < 9 for c in camps) or any(math.hypot(x - s["x"], z - s["z"]) < 6 for s in scatter):
            continue
        scatter.append({"prop": rng.randrange(6), "x": round(x, 1), "z": round(z, 1), "yaw": round(rng.uniform(0, 6.28), 2), "scale": round(rng.uniform(0.7, 1.5), 2)})
    hearts = []
    for c in camps[:3]:
        hearts.append({"x": round(c["x"] * 0.6, 1), "z": round(c["z"] * 0.6, 1)})
    return {"half": half, "amp": 7.0, "seed": spec["level"]["seed"] % 100000, "camps": camps, "scatter": scatter, "hearts": hearts}


def mystery(spec: dict) -> dict:
    """A walled yard with sheds and hedges to walk round, or a World Kit place when the pipeline has one. Spots are hopes: at runtime each goes to the nearest cell the hero can really walk to."""
    rng = random.Random(spec["level"]["seed"])
    w, d = {"small": (36.0, 28.0), "medium": (46.0, 36.0), "large": (56.0, 44.0)}[spec["level"]["size"]]
    blocks, decor = [], []
    for ix in (-1, 0, 1):
        for iz in (-1, 1):
            if rng.random() < 0.8:
                sx, sz = rng.uniform(5, 9), rng.uniform(4, 7)
                blocks.append({"pos": _r((ix * w * 0.29 + rng.uniform(-2, 2), 0, iz * d * 0.28 + rng.uniform(-2, 2))), "size": _r((sx, rng.uniform(2.6, 4.2), sz))})
    for i in range(6):
        decor.append({"prop": i, "pos": _r((rng.uniform(-w * 0.42, w * 0.42), 0, rng.choice((-1, 1)) * rng.uniform(d * 0.06, d * 0.14))), "yaw": round(rng.uniform(0, 6.28), 2), "scale": round(rng.uniform(0.6, 1.0), 2)})
    story = spec["story"]
    n = len(story["suspects"]) + len(story["clues"])
    spots = []
    for i in range(n):
        a = i / n * math.tau + rng.uniform(-0.2, 0.2)
        spots.append(_r((math.cos(a) * w * rng.uniform(0.25, 0.44), 0, math.sin(a) * d * rng.uniform(0.25, 0.44))))
    rng.shuffle(spots)
    for row, spot in zip([*story["suspects"], *story["clues"]], spots):
        row["spot"] = spot
    return {"size": [w, d], "start": [0, 0.2, 0], "blocks": blocks, "decor": decor, "floor_y": 0.0, "place": ""}


MAKERS = {"platformer": platformer, "arena": arena, "kart": kart, "quest": quest, "mystery": mystery}


def build(spec: dict) -> dict:
    return MAKERS[spec["kit"]](spec)


def problems(spec: dict, lv: dict) -> list[str]:
    if spec["kit"] == "platformer":
        return platformer_problems(lv)
    if spec["kit"] == "kart":
        return kart_problems(lv)
    if spec["kit"] == "arena":
        return [] if lv["waves"] else ["no waves"]
    if spec["kit"] == "quest":
        return [] if lv["camps"] else ["no camps"]
    return [] if spec["story"]["clues"] else ["no clues"]
