"""SAM 3D Body's BVH (ComfyUI's Build Pose File) names its joints joint_001 .. joint_126. The motion fit reads SOMA names (Hips, LeftLeg, LeftShin, Chest ...), so this finds those joints by where they sit in the first frame and renames them; every other joint keeps its number.
How: forward kinematics on frame 0 (BVH Z-X-Y Euler degrees, Y up). Legs are the two chains from the hips that reach lowest, the spine the chain that reaches highest, the arms the two chains that leave the spine sideways. Left is the side the character's left is on, from which way the hips face. Standard library only."""
from __future__ import annotations

import math
import re
from pathlib import Path

MARK = re.compile(r"^\s*(ROOT|JOINT)\s+(\S+)", re.M)


class Joint:
    def __init__(self, name, parent):
        self.name, self.parent, self.kids, self.offset, self.channels = name, parent, [], (0.0, 0.0, 0.0), []


def parse(text: str):
    """-> (joints in file order, frame-0 values)."""
    joints, stack, pending = [], [], None
    lines = text.splitlines()
    for k, ln in enumerate(lines):
        t = ln.split()
        if not t: continue
        if t[0] in ("ROOT", "JOINT"):
            pending = Joint(t[1], next((x for x in reversed(stack) if x is not None), None))
            if pending.parent: pending.parent.kids.append(pending)
            joints.append(pending)
        elif t[0] == "End": pending = None
        elif t[0] == "{": stack.append(pending); pending = None
        elif t[0] == "}": stack.pop()
        elif t[0] == "OFFSET" and stack and stack[-1] is not None: stack[-1].offset = tuple(float(x) for x in t[1:4])
        elif t[0] == "CHANNELS" and stack and stack[-1] is not None: stack[-1].channels = t[2:]
        elif t[0] == "Frame" and t[1] == "Time:":
            return joints, [float(x) for x in lines[k + 1].split()]
    raise ValueError("no motion in this file")


def _rot(axis, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return {"X": ((1, 0, 0), (0, c, -s), (0, s, c)), "Y": ((c, 0, s), (0, 1, 0), (-s, 0, c)), "Z": ((c, -s, 0), (s, c, 0), (0, 0, 1))}[axis]


def _mul(a, b):
    return tuple(tuple(sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)) for r in range(3))


def _app(m, v):
    return tuple(sum(m[r][k] * v[k] for k in range(3)) for r in range(3))


def frame0(joints, values):
    """{name: world position} for the first frame."""
    pos, rot, at = {}, {}, 0
    I = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    for j in joints:
        local, t = I, (0.0, 0.0, 0.0)
        for ch in j.channels:
            v = values[at]; at += 1
            if ch.endswith("position"): t = tuple(v if ch[0] == a else t[n] for n, a in enumerate("XYZ"))
            else: local = _mul(local, _rot(ch[0], v))
        if j.parent is None:
            pos[j.name] = tuple(o + d for o, d in zip(j.offset, t)); rot[j.name] = local
        else:
            pr = rot[j.parent.name]; pos[j.name] = tuple(p + d for p, d in zip(pos[j.parent.name], _app(pr, j.offset))); rot[j.name] = _mul(pr, local)
    return pos


def _sub(j):
    out = [j]
    for k in j.kids: out += _sub(k)
    return out


def _chain(start, pick):
    """From a joint down the child whose subtree has the best pick() value, dropping joints that sit on their parent (twist helpers)."""
    path, j = [start], start
    while j.kids:
        j = max(j.kids, key=lambda k: max(pick(x) for x in _sub(k)))
        if math.dist((0, 0, 0), j.offset) > 0.5: path.append(j)
    return path


def mapping(text: str) -> dict:
    """{joint_xxx: SOMA name}. Raises ValueError when the shape is not a standing body it can read."""
    joints, first = parse(text); pos = frame0(joints, first); by = {j.name: j for j in joints}
    hips = joints[0]; hy = pos[hips.name][1]
    down = sorted(hips.kids, key=lambda k: min(pos[x.name][1] for x in _sub(k)))
    legs = [k for k in down if min(pos[x.name][1] for x in _sub(k)) < hy - 40][:2]
    ups = [k for k in hips.kids if k not in legs and max(pos[x.name][1] for x in _sub(k)) > hy + 30]
    if len(legs) != 2 or not ups: raise ValueError("this motion file does not read as a standing body: two legs and a spine from the hips")
    spine = _chain(ups[0], lambda x: pos[x.name][1])
    # the chest is the spine joint the arms leave from: the first with a child whose subtree reaches far sideways
    def reach(k, c): return max(math.dist((pos[x.name][0], pos[x.name][2]), (pos[c.name][0], pos[c.name][2])) for x in _sub(k))
    chest = next((s for s in spine if sum(1 for k in s.kids if k not in spine and reach(k, s) > 25) >= 2), None)
    if chest is None: raise ValueError("no chest with two arms found in this motion file")
    arms = [k for k in chest.kids if k not in spine and reach(k, chest) > 25][:2]
    lx, rx = pos[legs[0].name], pos[legs[1].name]
    # facing: the hips' left-right axis crossed with up gives forward; the toes say which way that points
    def foot_toe(leg):
        c = _chain(leg, lambda x: -pos[x.name][1])
        if len(c) < 4: raise ValueError("a leg in this motion file is too short to read")
        return c, c[2], max(_sub(c[2])[1:] or [c[2]], key=lambda x: math.dist(pos[x.name], pos[c[2].name]))
    feet = [foot_toe(k) for k in legs]       # forward: where both feet point, ankle to toe (one foot alone can be turned out)
    fwd = tuple(sum(pos[t.name][i] - pos[f.name][i] for _, f, t in feet) for i in (0, 2))
    def left_of(p):                        # positive when p is on the character's left (Y up: left = up x forward)
        side = (fwd[1], -fwd[0])
        return (p[0] - pos[hips.name][0]) * side[0] + (p[2] - pos[hips.name][2]) * side[1]
    legs.sort(key=lambda k: -left_of(pos[k.name])); arms.sort(key=lambda k: -left_of(pos[_chain(k, lambda x: 0)[-1].name]))
    out = {hips.name: "Hips"}
    after = spine[1:spine.index(chest)] if chest in spine else []
    out[spine[0].name] = "Spine1"
    for j, n in zip(after, ("Spine2",)): out[j.name] = n
    out[chest.name] = "Chest"
    neck = spine[spine.index(chest) + 1:]
    if len(neck) < 2: raise ValueError("no neck and head found in this motion file")
    out[neck[0].name] = "Neck1"; out[neck[-2 if len(neck) > 2 else -1].name] = "Head"
    for side, leg in zip(("Left", "Right"), legs):
        p, foot, toe = foot_toe(leg)
        out.update({p[0].name: f"{side}Leg", p[1].name: f"{side}Shin", foot.name: f"{side}Foot", toe.name: f"{side}ToeBase"})
    for side, arm in zip(("Left", "Right"), arms):
        p = _chain(arm, lambda x: math.dist(pos[x.name], pos[chest.name]))
        if len(p) < 5: raise ValueError("an arm in this motion file is too short to read")
        hand = p[3]; mid = p[min(len(p) - 1, 5)]
        out.update({p[0].name: f"{side}Shoulder", p[1].name: f"{side}Arm", p[2].name: f"{side}ForeArm", hand.name: f"{side}Hand", mid.name: f"{side}HandMiddle2"})
    return out


def _frames(text):
    lines = text.splitlines(); k = next(j for j, ln in enumerate(lines) if ln.startswith("Frame Time"))
    return lines[:k + 1], [[float(x) for x in ln.split()] for ln in lines[k + 1:] if ln.strip()]


def _zxy(m):
    """A rotation matrix -> BVH Z, X, Y degrees (R = Rz Rx Ry)."""
    b = math.asin(max(-1.0, min(1.0, m[2][1])))
    return math.degrees(math.atan2(-m[0][1], m[1][1])), math.degrees(b), math.degrees(math.atan2(-m[2][0], m[2][2]))


def level(text: str, m: dict) -> str:
    """One camera sees a body from above or below, so the whole clip leans. Turn it as one piece so that, on average over the clip, the line from the ankles to the neck stands straight up."""
    joints, _ = parse(text); head, rows = _frames(text); name = {v: k for k, v in m.items()}
    ux = uy = uz = 0.0
    for r in rows:
        p = frame0(joints, r); a = [(p[name["LeftFoot"]][i] + p[name["RightFoot"]][i]) / 2 for i in range(3)]; n = p[name["Neck1"]]
        d = [n[i] - a[i] for i in range(3)]; L = math.sqrt(sum(x * x for x in d)) or 1.0; ux, uy, uz = ux + d[0] / L, uy + d[1] / L, uz + d[2] / L
    L = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0; u = (ux / L, uy / L, uz / L)
    axis = (-u[2], 0.0, u[0]); s_ = math.sqrt(axis[0] ** 2 + axis[2] ** 2)          # u x Y
    R0 = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    if s_ > 1e-6:
        k = (axis[0] / s_, 0.0, axis[2] / s_); ang = math.atan2(s_, u[1]); c, sn = math.cos(ang), math.sin(ang)
        K = ((0, -k[2], k[1]), (k[2], 0, -k[0]), (-k[1], k[0], 0)); K2 = _mul(K, K)
        R0 = tuple(tuple((1 if r == q else 0) + sn * K[r][q] + (1 - c) * K2[r][q] for q in range(3)) for r in range(3))
    # then turn it to face +Z at the start, as a clip made from words does: forward from the hips' left-right line
    p = frame0(joints, rows[0]); lr = _app(R0, tuple(p[name["LeftLeg"]][i] - p[name["RightLeg"]][i] for i in range(3)))
    fx, fz = -lr[2], lr[0]; phi = math.atan2(-fx, fz)
    R0 = _mul(((math.cos(phi), 0, math.sin(phi)), (0, 1, 0), (-math.sin(phi), 0, math.cos(phi))), R0)
    root = joints[0]; pi = [i for i, ch in enumerate(root.channels) if ch.endswith("position")]; ri = [i for i, ch in enumerate(root.channels) if ch.endswith("rotation")]
    out = []
    for r in rows:
        pos = _app(R0, tuple(r[i] for i in pi)); R = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        for i in ri: R = _mul(R, _rot(root.channels[i][0], r[i]))
        z, x, y = _zxy(_mul(R0, R)); r = list(r)
        for i, v in zip(pi, pos): r[i] = v
        for i in ri: r[i] = {"Z": z, "X": x, "Y": y}[root.channels[i][0]]
        out.append(" ".join(f"{v:.6f}" for v in r))
    return "\n".join(head + out) + "\n"


def is_mhr(text: str) -> bool:
    names = MARK.findall(text)
    return bool(names) and names[0][1] == "Hips" and sum(1 for _, n in names[1:] if n.startswith("joint_")) >= 50


def rename(src, dst) -> Path:
    """A copy of an MHR BVH with the joints the fit reads under their SOMA names."""
    text = Path(src).read_text(errors="replace"); m = mapping(text)
    root = parse(text)[0][0]
    if [c[0] for c in root.channels if c.endswith("rotation")] == ["Z", "X", "Y"]: text = level(text, m)
    Path(dst).write_text(MARK.sub(lambda g: g.group(0).replace(g.group(2), m.get(g.group(2), g.group(2))), text), encoding="utf-8")
    return Path(dst)
