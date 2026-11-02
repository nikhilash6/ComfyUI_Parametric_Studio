"""Humanoid slots from a rig's rest pose, by geometry alone (an auto-rigger may name its bones bone_0..N). The character faces
-Y (Blender's front view; glTF's +Z forward), so its left is +X. Only bone HEADS (joint positions) are trusted: glTF
stores joints, and the importer invents tails. Used for the OpenPose pass (Virtual Set) and for validation (a
character needs every slot)."""
from __future__ import annotations

import math
import statistics

SLOTS = ("hips", "spine", "chest", "neck", "head", "l_upperarm", "l_forearm", "l_hand", "r_upperarm", "r_forearm",
         "r_hand", "l_thigh", "l_shin", "l_foot", "r_thigh", "r_shin", "r_foot")
MIN_BONES = 15


class RigMapError(ValueError):
    pass


def slots(bones: list[dict]) -> dict[str, str]:
    by = {b["name"]: b for b in bones}
    if len(by) < MIN_BONES:
        raise RigMapError(f"{len(by)} bones is too few for a humanoid rig (at least {MIN_BONES})")
    kids: dict[str, list[str]] = {n: [] for n in by}
    for b in bones:
        if (b.get("parent") or "") in by:
            kids[b["parent"]].append(b["name"])
    zs = [b["head"][2] for b in bones]
    zmin, zmax = min(zs), max(zs)
    h = zmax - zmin
    if h <= 0:
        raise RigMapError("the rig has no height")
    cx = statistics.fmean(b["head"][0] for b in bones)

    def chain(leaf: str) -> list[str]:
        out = [leaf]
        while (by[out[-1]].get("parent") or "") in by:
            out.append(by[out[-1]]["parent"])
        return out[::-1]

    def tipx(n: str) -> float:
        return by[n]["head"][0] - cx

    def tipz(n: str) -> float:
        return by[n]["head"][2] - zmin

    def seglen(n: str) -> float:
        c = kids[n]
        return math.dist(by[n]["head"], by[c[0]]["head"]) if len(c) == 1 else math.dist(by[n]["head"], by[n]["tail"])

    def common(a: list[str], b: list[str]) -> str:
        last = ""
        for x, y in zip(a, b):
            if x != y:
                break
            last = x
        if not last:
            raise RigMapError("the rig's limbs do not share a parent")
        return last

    def after(ch: list[str], anc: str) -> list[str]:
        return ch[ch.index(anc) + 1:]

    def inward(n: str) -> bool:
        """A bone that starts on the centre line and runs sideways more than down is a clavicle, however long the rigger made it."""
        c = kids[n]
        if len(c) != 1:
            return False
        a, b = by[n]["head"], by[c[0]]["head"]
        return abs(a[0] - cx) < 0.05 * h and abs(b[0] - a[0]) > abs(b[2] - a[2])

    def limb(seg: list[str], what: str) -> list[str]:
        seg = list(seg)
        while len(seg) > 3 and (seglen(seg[0]) < 0.6 * seglen(seg[1]) or inward(seg[0])):     # a clavicle / pelvis side bone
            seg.pop(0)
        if len(seg) < 3:
            raise RigMapError(f"the {what} has fewer than three bones")
        return seg[:3]

    leaves = [n for n in by if not kids[n]]
    feet = [n for n in leaves if tipz(n) < 0.25 * h]
    lf, rf = [n for n in feet if tipx(n) > 0], [n for n in feet if tipx(n) < 0]
    if not lf or not rf:
        raise RigMapError("no left and right foot near the ground: not a two-legged humanoid")
    lleg, rleg = chain(min(lf, key=tipz)), chain(min(rf, key=tipz))
    hips = common(lleg, rleg)
    tops = [n for n in leaves if abs(tipx(n)) < 0.15 * h and tipz(n) > 0.75 * h]
    if not tops:
        raise RigMapError("no head bone at the top of the rig")
    hchain = chain(max(tops, key=tipz))
    hands = [n for n in leaves if n not in hchain and tipz(n) > 0.3 * h and abs(tipx(n)) > 0.1 * h]
    la, ra = [n for n in hands if tipx(n) > 0], [n for n in hands if tipx(n) < 0]
    if not la or not ra:
        raise RigMapError("no left and right arm: not a two-armed humanoid")
    larm, rarm = chain(max(la, key=tipx)), chain(min(ra, key=tipx))
    chest = common(larm, rarm)
    if chest not in hchain or hips not in hchain or hchain.index(chest) <= hchain.index(hips):
        raise RigMapError("the arms do not branch from the spine above the hips")
    spine_seg = hchain[hchain.index(hips) + 1:hchain.index(chest) + 1]
    top = after(hchain, chest)
    while len(top) > 1 and zmax - by[top[-1]]["head"][2] < 0.04 * h:     # a head_end / nub bone at the very top
        top.pop()
    if not top:
        raise RigMapError("no neck or head above the chest")
    out = {"hips": hips, "spine": spine_seg[0], "chest": chest, "head": top[-1],
           "neck": top[-2] if len(top) >= 2 else chest}
    for side, arm, leg in (("l", larm, lleg), ("r", rarm, rleg)):
        out[f"{side}_upperarm"], out[f"{side}_forearm"], out[f"{side}_hand"] = limb(after(arm, chest), f"{side} arm")
        out[f"{side}_thigh"], out[f"{side}_shin"], out[f"{side}_foot"] = limb(after(leg, hips), f"{side} leg")
    return {k: out[k] for k in SLOTS}
