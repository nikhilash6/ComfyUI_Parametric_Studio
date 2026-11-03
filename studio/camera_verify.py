"""Did the take do the camera move that was asked for? CPU only: sparse optical flow (OpenCV Lucas-Kanade with a forward-backward check) between
neighbouring frames, a robust similarity fit per frame pair for the whole picture, and separate medians for the centre of the frame and its edges.
The verdict is MATCH, MISMATCH or INCONCLUSIVE. INCONCLUSIVE is never a pass: it means the clip did not give enough evidence either way
(too few trackable points, the scene moving more than the camera, a cut, or a move this method cannot read).

The rules come from what each move does to the picture, written before any test clip was measured, and they are not tuned to the test set:
- pan/tilt: the whole picture slides one way, centre and edges together. Panning left slides the picture right.
- crane: like a tilt in screen terms (crane up slides the picture down); parallax is not required. A crane that tilts to keep the subject in frame can slide a
  far background the other way, so the opposite direction is INCONCLUSIVE for a crane, never MISMATCH.
- dolly in/out: the picture grows or shrinks from the centre.
- orbit: the subject in the centre stays put while the edges slide. Orbiting right slides the background right (far points move with the turn).
- tracking: centre held, edges slide either way. handheld: small shaky motion with little net travel. locked: nothing moves.
Screen motion is measured in fractions of the frame (x by width, y by height); scale as a log ratio."""
import math, subprocess
from pathlib import Path
import numpy as np

VERDICTS = ("MATCH", "MISMATCH", "INCONCLUSIVE")
WIDTH = 384                     # frames are analysed at this width
MIN_POINTS, MIN_INLIERS, MIN_PAIRS = 40, 0.45, 8
SLIDE, SLIDE_CLEAR, OPPOSITE = 0.10, 0.20, 0.05      # a slide of 10% of the frame counts; 20% is clear; 5% the other way contradicts
GROW, OPP_GROW = 0.08, 0.04                           # 8% growth counts as a dolly; 4% the other way contradicts
STILL, STILL_SCALE, STILL_ROLL = 0.03, 0.03, 1.5      # under 3% of the frame and 3% growth: nothing moved
HELD = 0.5                                            # the centre moves under half as far as the edges: it is held
SHAKE = 0.004                                         # handheld: mean frame-to-frame wobble of at least 0.4% of the frame after smoothing
CUT_JUMP = 0.35                                       # a frame pair where under 35% of points survive is read as a cut

#: what each move must do on screen. axis: which measure carries it; sign: which way it must go (+1 picture right/down/grows).
MOVES = {
    "locked": {"kind": "still"},
    "pan_left": {"kind": "slide", "axis": "x", "sign": +1}, "pan_right": {"kind": "slide", "axis": "x", "sign": -1},
    "tilt_up": {"kind": "slide", "axis": "y", "sign": +1}, "tilt_down": {"kind": "slide", "axis": "y", "sign": -1},
    "crane_up": {"kind": "slide", "axis": "y", "sign": +1, "parallax_ok": True}, "crane_down": {"kind": "slide", "axis": "y", "sign": -1, "parallax_ok": True},
    "dolly_in": {"kind": "grow", "sign": +1}, "dolly_out": {"kind": "grow", "sign": -1},
    "zoom_in": {"kind": "grow", "sign": +1}, "zoom_out": {"kind": "grow", "sign": -1},
    "orbit_left": {"kind": "orbit", "sign": -1}, "orbit_right": {"kind": "orbit", "sign": +1},
    "tracking": {"kind": "track"}, "handheld": {"kind": "shake"},
    "dolly_zoom": {"kind": "unreadable", "why": "a dolly zoom keeps the subject the same size, which flow over the whole frame cannot separate from a still shot"},
    "roll_left": {"kind": "roll", "sign": -1}, "roll_right": {"kind": "roll", "sign": +1},
}
#: Wan Fun Camera's preset names, read as the moves above (its "Pan" presets move the camera sideways, which reads on screen like a pan).
WAN_POSE_MOVES = {"Pan Left": "pan_left", "Pan Right": "pan_right", "Pan Up": "tilt_up", "Pan Down": "tilt_down", "Zoom In": "dolly_in", "Zoom Out": "dolly_out", "Anti Clockwise (ACW)": "roll_left", "ClockWise (CW)": "roll_right", "Static": "locked"}


def read_frames(path, width=WIDTH, max_frames=400):
    """Grey frames at the analysis width, every frame up to max_frames. -> (list of uint8 arrays, fps)."""
    import cv2
    cap = cv2.VideoCapture(str(path)); fps = cap.get(cv2.CAP_PROP_FPS) or 24.0; out = []
    try:
        while len(out) < max_frames:
            ok, f = cap.read()
            if not ok: break
            h, w = f.shape[:2]; g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            out.append(cv2.resize(g, (width, max(16, round(h * width / w))), interpolation=cv2.INTER_AREA))
    finally: cap.release()
    return out, float(fps)


def _pair(a, b):
    """One frame pair -> dict of per-pair motion, or None when it cannot be read."""
    import cv2
    h, w = a.shape
    p0 = cv2.goodFeaturesToTrack(a, maxCorners=400, qualityLevel=0.01, minDistance=7, blockSize=7)
    found = 0 if p0 is None else len(p0)
    if found < MIN_POINTS: return {"ok": False, "points": found, "found": found, "survive": 0.0}
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(21, 21), maxLevel=3)
    pb, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, winSize=(21, 21), maxLevel=3)
    good = (st.reshape(-1) == 1) & (st2.reshape(-1) == 1) & (np.linalg.norm((pb - p0).reshape(-1, 2), axis=1) < 1.0)
    survive = float(good.mean())
    if good.sum() < MIN_POINTS // 2: return {"ok": False, "points": int(good.sum()), "found": found, "survive": survive}
    q0, q1 = p0.reshape(-1, 2)[good], p1.reshape(-1, 2)[good]
    c = np.array([w / 2, h / 2]); M, inl = cv2.estimateAffinePartial2D(q0 - c, q1 - c, method=cv2.RANSAC, ransacReprojThreshold=1.5, maxIters=2000, confidence=0.99)
    if M is None: return {"ok": False, "points": int(good.sum()), "found": found, "survive": survive}
    s = math.hypot(M[0, 0], M[1, 0]); rotd = math.degrees(math.atan2(M[1, 0], M[0, 0]))
    d = q1 - q0; rel = (q0 - c) / c                                   # -1..1 across the frame
    centre = (np.abs(rel[:, 0]) < 0.35) & (np.abs(rel[:, 1]) < 0.35); edge = (np.abs(rel[:, 0]) > 0.55) | (np.abs(rel[:, 1]) > 0.55)
    med = lambda m: (float(np.median(d[m, 0]) / w), float(np.median(d[m, 1]) / h)) if m.sum() >= 6 else None
    return {"ok": True, "points": int(good.sum()), "found": found, "survive": survive, "inliers": float(inl.mean()) if inl is not None else 0.0,
            "tx": float(M[0, 2] / w), "ty": float(M[1, 2] / h), "log_s": math.log(max(s, 1e-6)), "rot": rotd, "centre": med(centre), "edge": med(edge)}


def measure(path, frames=None):
    """The clip's screen motion, summed over the shot. -> dict of measures plus quality numbers."""
    if frames is None: frames, fps = read_frames(path)
    else: fps = 24.0
    pairs = [_pair(frames[i], frames[i + 1]) for i in range(len(frames) - 1)]
    ok = [p for p in pairs if p["ok"]]
    cuts = sum(1 for p in pairs if p.get("found", 0) >= MIN_POINTS and p["survive"] < CUT_JUMP)
    m = {"frames": len(frames), "fps": round(fps, 2), "pairs": len(pairs), "pairs_read": len(ok), "cuts": cuts,
         "points_median": int(np.median([p["points"] for p in pairs])) if pairs else 0,
         "inliers_mean": round(float(np.mean([p["inliers"] for p in ok])), 3) if ok else 0.0}
    if not ok: return m | {"x": 0.0, "y": 0.0, "scale": 0.0, "roll": 0.0, "centre": None, "edge": None, "shake": 0.0}
    tx, ty = np.array([p["tx"] for p in ok]), np.array([p["ty"] for p in ok])
    m.update(x=round(float(tx.sum()), 4), y=round(float(ty.sum()), 4), scale=round(float(sum(p["log_s"] for p in ok)), 4), roll=round(float(sum(p["rot"] for p in ok)), 2))
    cs = [p["centre"] for p in ok if p["centre"] and p["edge"]]; es = [p["edge"] for p in ok if p["centre"] and p["edge"]]
    m["centre"] = [round(float(sum(c[0] for c in cs)), 4), round(float(sum(c[1] for c in cs)), 4)] if cs else None
    m["edge"] = [round(float(sum(e[0] for e in es)), 4), round(float(sum(e[1] for e in es)), 4)] if es else None
    k = 5                                                            # wobble: per-pair motion minus its 5-pair running mean
    if len(tx) > k * 2:
        ker = np.ones(k) / k; rx, ry = tx - np.convolve(tx, ker, "same"), ty - np.convolve(ty, ker, "same")
        m["shake"] = round(float(np.mean(np.hypot(rx, ry)[k:-k])), 5)
    else: m["shake"] = 0.0
    return m


def describe(m):
    """The measured motion in words, for the page and the proof."""
    if not m.get("pairs_read"): return "No motion could be read."
    bits = []
    if abs(m["x"]) >= STILL: bits.append(f"the picture slid {'right' if m['x'] > 0 else 'left'} {abs(m['x']) * 100:.0f}% of the width")
    if abs(m["y"]) >= STILL: bits.append(f"{'down' if m['y'] > 0 else 'up'} {abs(m['y']) * 100:.0f}% of the height")
    if abs(m["scale"]) >= STILL_SCALE: bits.append(f"{'grew' if m['scale'] > 0 else 'shrank'} {abs(math.expm1(m['scale'])) * 100:.0f}%")
    if abs(m["roll"]) >= STILL_ROLL: bits.append(f"turned {abs(m['roll']):.0f} degrees {'clockwise' if m['roll'] > 0 else 'anticlockwise'}")
    if m.get("centre") and m.get("edge"):
        cn, en = math.hypot(*m["centre"]), math.hypot(*m["edge"])
        if en >= SLIDE and cn < HELD * en: bits.append("the centre stayed put while the edges moved")
    return ("; ".join(bits) or "almost nothing moved") + "."


def _held(m):
    if not (m.get("centre") and m.get("edge")): return None
    cn, en = math.hypot(*m["centre"]), math.hypot(*m["edge"])
    return en >= SLIDE and cn < HELD * en


def judge(m, move):
    """-> {verdict, why, strength}. strength is how far past the bar a MATCH went (for picking takes); 0 otherwise."""
    rule = MOVES.get(move)
    if rule is None: return {"verdict": "INCONCLUSIVE", "why": f"'{move}' is not a move this checker knows", "strength": 0.0}
    if rule["kind"] == "unreadable": return {"verdict": "INCONCLUSIVE", "why": rule["why"], "strength": 0.0}
    if m.get("pairs_read", 0) < MIN_PAIRS: return {"verdict": "INCONCLUSIVE", "why": f"only {m.get('pairs_read', 0)} frame pairs could be tracked (needs {MIN_PAIRS})", "strength": 0.0}
    if m["points_median"] < MIN_POINTS: return {"verdict": "INCONCLUSIVE", "why": f"too few trackable points ({m['points_median']}); flat or dark frames", "strength": 0.0}
    if m["cuts"] > 0: return {"verdict": "INCONCLUSIVE", "why": f"{m['cuts']} frame pair(s) look like a cut or a flash", "strength": 0.0}
    if m["inliers_mean"] < MIN_INLIERS: return {"verdict": "INCONCLUSIVE", "why": f"the scene moves more than the camera: only {m['inliers_mean']:.0%} of points follow one motion", "strength": 0.0}
    x, y, s, r = m["x"], m["y"], m["scale"], m["roll"]; still = abs(x) < STILL and abs(y) < STILL and abs(s) < STILL_SCALE and abs(r) < STILL_ROLL
    k = rule["kind"]
    if k == "still":
        if still: return {"verdict": "MATCH", "why": "nothing moved", "strength": 1.0}
        if max(abs(x), abs(y)) >= SLIDE or abs(s) >= GROW: return {"verdict": "MISMATCH", "why": "the camera moved: " + describe(m), "strength": 0.0}
        return {"verdict": "INCONCLUSIVE", "why": "a little drift, too much for locked and too little to call a move", "strength": 0.0}
    if still and k != "shake": return {"verdict": "MISMATCH", "why": "almost nothing moved", "strength": 0.0}
    if k == "slide":
        v, other = (x, y) if rule["axis"] == "x" else (y, x); v *= rule["sign"]
        if v <= -OPPOSITE:
            if rule.get("parallax_ok"): return {"verdict": "INCONCLUSIVE", "why": "the picture slid the other way, which a crane that tilts to keep the subject can also do when the background fills the frame: " + describe(m), "strength": 0.0}
            return {"verdict": "MISMATCH", "why": "it went the other way: " + describe(m), "strength": 0.0}
        if v >= SLIDE and v >= abs(other) and v >= 2 * abs(s):
            held = _held(m)
            if held and not rule.get("parallax_ok") and v < SLIDE_CLEAR: return {"verdict": "INCONCLUSIVE", "why": "the edges slid but the centre held, which reads more like an orbit or tracking shot", "strength": 0.0}
            return {"verdict": "MATCH", "why": describe(m), "strength": round(v - SLIDE, 4)}
        if abs(other) >= SLIDE_CLEAR and abs(other) > 2 * max(v, 0): return {"verdict": "MISMATCH", "why": "it moved along the other axis: " + describe(m), "strength": 0.0}
        if abs(s) >= 2 * GROW and abs(s) > 2 * max(v, 0): return {"verdict": "MISMATCH", "why": "it moved in or out instead: " + describe(m), "strength": 0.0}
        return {"verdict": "INCONCLUSIVE", "why": "some motion the right way, under the bar: " + describe(m), "strength": 0.0}
    if k == "grow":
        v = s * rule["sign"]
        if v <= -OPP_GROW: return {"verdict": "MISMATCH", "why": "it went the other way: " + describe(m), "strength": 0.0}
        if v >= GROW: return {"verdict": "MATCH", "why": describe(m), "strength": round(v - GROW, 4)}
        if max(abs(x), abs(y)) >= SLIDE_CLEAR: return {"verdict": "MISMATCH", "why": "it slid instead of moving in or out: " + describe(m), "strength": 0.0}
        return {"verdict": "INCONCLUSIVE", "why": "growth under the bar: " + describe(m), "strength": 0.0}
    if k == "roll":
        v = r * rule["sign"]
        if v >= 5: return {"verdict": "MATCH", "why": describe(m), "strength": round((v - 5) / 45, 4)}
        if v <= -2: return {"verdict": "MISMATCH", "why": "it turned the other way: " + describe(m), "strength": 0.0}
        return {"verdict": "INCONCLUSIVE", "why": "little or no turn: " + describe(m), "strength": 0.0}
    if k in ("orbit", "track"):
        e = m.get("edge"); held = _held(m)
        if not e: return {"verdict": "INCONCLUSIVE", "why": "not enough points at the edges of the frame", "strength": 0.0}
        ex = e[0] if k == "track" else e[0] * rule["sign"]
        if k == "orbit" and ex <= -OPPOSITE and abs(e[0]) >= SLIDE: return {"verdict": "MISMATCH", "why": "the background went the other way: " + describe(m), "strength": 0.0}
        if (abs(ex) if k == "track" else ex) >= SLIDE and held: return {"verdict": "MATCH", "why": describe(m), "strength": round((abs(ex) if k == "track" else ex) - SLIDE, 4)}
        if abs(s) >= 2 * GROW and abs(s) > 2 * abs(e[0]): return {"verdict": "MISMATCH", "why": "it moved in or out instead: " + describe(m), "strength": 0.0}
        if abs(e[1]) >= SLIDE_CLEAR and abs(e[1]) > 2 * abs(e[0]): return {"verdict": "MISMATCH", "why": "it moved up or down instead: " + describe(m), "strength": 0.0}
        return {"verdict": "INCONCLUSIVE", "why": ("the picture slid but the centre moved with it, which reads like a pan" if held is False and abs(e[0]) >= SLIDE else "sideways motion under the bar") + ": " + describe(m), "strength": 0.0}
    if k == "shake":
        if m["shake"] >= SHAKE and max(abs(x), abs(y)) < SLIDE_CLEAR: return {"verdict": "MATCH", "why": f"a light wobble ({m['shake'] * 100:.2f}% of the frame per frame)", "strength": round(m["shake"] - SHAKE, 5)}
        if still and m["shake"] < SHAKE / 2: return {"verdict": "MISMATCH", "why": "the camera is steady", "strength": 0.0}
        return {"verdict": "INCONCLUSIVE", "why": f"wobble {m['shake'] * 100:.2f}% of the frame per frame; " + describe(m), "strength": 0.0}
    return {"verdict": "INCONCLUSIVE", "why": "no rule", "strength": 0.0}


def verify(path, move, frames=None):
    """One clip, one requested move -> {move, verdict, why, strength, measured, said}."""
    m = measure(path, frames)
    return {"move": move, **judge(m, move), "measured": m, "said": describe(m)}


def pick(takes, move):
    """The take that best followed the move. takes: [path, ...] or [(name, path), ...]. Only a MATCH can be picked; an INCONCLUSIVE take never beats a MATCH and is never picked.
    -> {picked: name or None, why, results: [{take, verdict, ...}] in the order given}."""
    rows = []
    for t in takes:
        name, p = (t if isinstance(t, (list, tuple)) else (Path(t).name, t))
        rows.append({"take": name, **verify(p, move)})
    best = max((r for r in rows if r["verdict"] == "MATCH"), key=lambda r: r["strength"], default=None)
    if best: return {"picked": best["take"], "why": f"{best['take']} followed {move.replace('_', ' ')} most clearly: {best['said']}", "results": rows}
    inc = sum(r["verdict"] == "INCONCLUSIVE" for r in rows)
    return {"picked": None, "why": f"No take clearly followed {move.replace('_', ' ')}" + (f"; {inc} could not be read either way." if inc else "."), "results": rows}


def expected_from_path(screen):
    """A drawn path's predicted screen motion (psn_nodes.camera_path.screen_motion) -> the move name the verifier should check."""
    dx, dy, sc = screen["dx"], screen["dy"], screen["scale"]; ls = math.log(max(sc, 1e-6))
    if max(abs(dx), abs(dy)) < 0.05 and abs(ls) < 0.05: return "locked"
    if abs(ls) > max(abs(dx), abs(dy)): return "dolly_in" if ls > 0 else "dolly_out"
    if abs(dx) >= abs(dy): return "pan_left" if dx > 0 else "pan_right"
    return "tilt_up" if dy > 0 else "tilt_down"


def clip_seconds(path):
    try: return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True, timeout=30).stdout.strip())
    except (ValueError, OSError, subprocess.TimeoutExpired): return None
