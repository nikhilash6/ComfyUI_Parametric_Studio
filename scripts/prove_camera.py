"""Proof runs for Camera Paths, on AI-generated inputs only (no real person; scenes without people where the move allows).
GPU steps wait their turn at the shared VRAM gate (gpu_gate.py, found through GPU_GATE_TOOLS), free this lane's models first so the peak recorded is this run's, and record
model, seed, time, peak VRAM and faults in $CAMPATH_PROOF_WORK/log.json. Nothing here judges a picture: look at every output before `pack` puts it on the page.

  CAMPATH_COMFYUI_URL=http://127.0.0.1:<lane> python scripts/prove_camera.py <step> ...     steps: gpu (stills, track, wanpath, director in one gate turn) confusion pack
The thresholds in studio/camera_verify.py were written before any clip here was measured, and `confusion` never changes them: failures are reported as they come."""
import json, math, os, shutil, subprocess, sys, threading, time, urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO))
if os.environ.get("GPU_GATE_TOOLS"): sys.path.insert(0, os.environ["GPU_GATE_TOOLS"])
from studio import camera_verify as V, feature_camera as F, goals

WORK = Path(os.environ.get("CAMPATH_PROOF_WORK") or REPO / "campath_proof_work"); LOG = WORK / "log.json"; SHOW = REPO / "studio" / "web" / "showcase"
C = F.Comfy(); PORT = urllib.parse.urlparse(C.url).port; OWNER = "gap-p5"


def log(): return json.loads(LOG.read_text()) if LOG.exists() else {}


def put(key, rec):
    d = log(); d[key] = rec; WORK.mkdir(parents=True, exist_ok=True); LOG.write_text(json.dumps(d, indent=1)); print(key, json.dumps(rec)[:500], flush=True)


#: Honest peaks per job, GiB: measured on this box where a number exists (gate peaks.json), otherwise the nearest measured relative.
PEAKS = {"klein4b": (22.0, False), "ltx_track": (42.0, True), "wan_path": (48.0, True), "h3_director": (42.0, True)}


class Turn:
    """Each job takes its own gate reservation with its own declared peak, so a small job can backfill and nothing holds more than it uses. Each job frees the lane first and records its own peak."""
    def __init__(self, hold=None): self.hold, self.held = hold, None      # hold: keys to run under ONE reservation at the largest of their peaks, so the run does not re-queue per job

    def _acquire(self, key, peak, heavy):
        G = self.G; rid = None
        while rid is None:
            rid, why = G.acquire(OWNER, key, peak, heavy, port=PORT)
            if rid is None: print(time.strftime("%H:%M:%S"), f"gate ({key}, {peak} GiB):", why, flush=True); time.sleep(20)
        print(time.strftime("%H:%M:%S"), f"gate: our turn for {key} ({peak} GiB)", flush=True); return rid

    def __enter__(self):
        import gpu_gate as G
        self.G = G
        if self.hold:
            peak = max(G.expected("campath:" + k, *PEAKS[k]) for k in self.hold); self.held = self._acquire("campath-run", peak, any(PEAKS[k][1] for k in self.hold))
        return self

    def job(self, key, fn):
        """-> (result, seconds, peak GiB of this lane's process during fn)."""
        G = self.G; declared, heavy = PEAKS[key]
        rid = None if self.held else self._acquire(key, G.expected("campath:" + key, declared, heavy), heavy)
        C.free(); time.sleep(3); top = [0.0]; stop = threading.Event(); watch = G.FloorWatch()

        def poll():
            while not stop.is_set():
                top[0] = max(top[0], G.PROBE.used_by_port(PORT))
                if watch.tripped(): print("floor: the card stayed under 4 GiB; cancelling this lane's job", flush=True); C.cancel()
                time.sleep(1)
        th = threading.Thread(target=poll, daemon=True); th.start(); t0 = time.time()
        try: res = fn()
        finally:
            stop.set(); th.join(5); C.free()
            if rid: G.release(rid)
        G.record_peak("campath:" + key, top[0]); return res, round(time.time() - t0, 1), round(top[0], 1)

    def __exit__(self, *a):
        C.free()
        if self.held: self.G.release(self.held)


#: One scene per feature, each chosen to show that feature off. No people; no signs or writing.
STILLS = {
    "canyon": ("A wide photograph of a deep red sandstone canyon with tall layered rock walls. A single weathered rock pillar stands in the middle of the canyon floor, in the centre of the frame, with a thin turquoise river winding past its foot. Warm late-afternoon light, long shadows, sharp detail, no people, no writing.", 4201),
    "cathedral": ("A wide photograph inside a vast gothic cathedral nave with tall stone columns and pointed arches. A carved stone baptismal font stands in the middle of the nave, in the centre of the frame. Shafts of coloured light from abstract stained glass windows fall across the stone floor. Sharp detail, no people, no writing, no letters.", 4202),
    "paper_boat": ("A wide photograph of a clear shallow forest stream flowing from left to right over smooth pebbles between mossy banks. A single small bright red folded paper boat floats on the water near the left edge of the frame, with open water to its right. Soft morning light, ferns, sharp detail, no people, no writing.", 4203),
}
#: The drawn camera paths, one per still: the globe preset used and how it was drawn.
WAN_SHOTS = {
    "canyon": {"preset": "rise_and_circle", "drawn_as": "dragged up and 60 degrees round to the right on the globe, rising 20 degrees, looking at the rock pillar", "seed": 7201,
               "prompt": "A deep red sandstone canyon with a lone rock pillar standing on the canyon floor beside a turquoise river. The camera rises and circles around the rock pillar. Warm late-afternoon light, realistic, sharp detail."},
    "cathedral": {"preset": "orbit_left", "drawn_as": "dragged 40 degrees round to the left on the globe, level, looking at the stone font", "seed": 7202,
                  "prompt": "Inside a vast gothic cathedral nave, a carved stone baptismal font stands among tall columns, coloured light falls across the floor. The camera moves smoothly around the font. Realistic, sharp detail."},
}
#: The checker's own clips: fresh Director renders (MiniMax H3) on a city rooftop, one per requested move.
DIRECTOR = {
    "dolly_in": ("A city rooftop at dusk with old wooden water towers, antennas and a small rooftop garden, the glowing skyline behind, no signs, no writing", 5201),
    "pan_left": ("A long row of city rooftops at dusk with water towers, brick chimneys and air vents, the skyline glowing behind, no signs, no writing", 5202),
    "tilt_up": ("A brick rooftop terrace with strings of warm lights, a tall glass skyscraper rising behind it into the dusk sky, no signs, no writing", 5203),
}
#: Auto-pick: several takes of one requested move on a lighthouse coast; the checker picks the one that followed it.
PICK_MOVE = "dolly_in"
PICK = ("A white lighthouse on a rocky headland above a wild sea, waves breaking on the rocks below, golden hour, no people, no writing", (5301, 5302, 5303))
BOAT_PROMPT = "A small red paper boat drifts along a clear forest stream, carried by the current over smooth pebbles between mossy banks. The camera holds completely still. Soft morning light, realistic, sharp detail."


def red_start(png):
    """Where the red paper boat is in the still: the largest strongly red blob. -> (x, y) in 0..1 and its radius in pixels."""
    import cv2, numpy as np
    im = cv2.imread(str(png)); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (0, 120, 70), (10, 255, 255)) | cv2.inRange(hsv, (170, 120, 70), (180, 255, 255))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    if n < 2: raise RuntimeError("no red boat found in the still: look at it and place the line by hand")
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); h, w = m.shape
    return (float(cen[i][0] / w), float(cen[i][1] / h)), int(math.sqrt(st[i, cv2.CC_STAT_AREA] / math.pi))


def stream_line(start):
    """A gentle S down the stream from the boat to the right, kept inside the frame."""
    x0, y0 = start; x1 = min(0.88, x0 + 0.6)
    return [[round(x0 + (x1 - x0) * u, 4), round(min(0.95, max(0.05, y0 + 0.06 * math.sin(2 * math.pi * u))), 4)] for u in (0, 0.2, 0.4, 0.6, 0.8, 1.0)]


def run_klein(turn, name, prompt, seed):
    def go():
        g = F.graph("flux2_klein4b_t2i_api.json", {"unet": "flux-2-klein-4b.safetensors", "prompt": prompt, "negative": "", "width": 1280, "height": 768, "steps": 4, "cfg": 1.0, "seed": seed})
        for n in g.values():
            if n["class_type"] == "SaveImage": n["inputs"]["filename_prefix"] = f"campath_proof/{name}"
        h = C.run(g); return C.fetch(F.outputs(h, "13")[0], WORK / "inputs" / f"{name}.png")
    out, s, pk = turn.job("klein4b", go)
    put("still:" + name, {"model": "FLUX.2 Klein 4B (Apache-2.0)", "prompt": prompt, "seed": seed, "seconds": s, "peak_vram_gib": pk, "file": str(out)})


def run_track(turn):
    still = Path(log()["still:paper_boat"]["file"]); start, radius = red_start(still); line = stream_line(start); seed = 6201
    tj = F.tracks_json([line]); name = C.upload(still)
    def go():
        h = C.run(F.graph(F.LTX["graph"], F.ltx_values(name, tj, BOAT_PROMPT, seed), "campath_proof/ltx_track"))
        return C.fetch(F.outputs(h, "save")[0], WORK / "track" / "ltx_track_boat.mp4"), C.fetch(F.outputs(h, "trks")[0], WORK / "track" / "ltx_track_boat_guide.mp4")
    (out, guide), s, pk = turn.job("ltx_track", go)
    m = measure_track(out, start, line)
    put("track", m | {"model": F.LTX["model"], "lora": "ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors (strength 1.0)", "subject": "a red paper boat on a forest stream", "prompt": BOAT_PROMPT, "seed": seed, "seconds": s, "peak_vram_gib": pk,
                  "line": line, "start": start, "radius_px_in_still": radius, "file": str(out), "guide": str(guide)})


def red_track(clip):
    """An independent check on the follower: the red boat's own centroid on every frame (largest strongly red blob)."""
    import cv2, numpy as np
    cap = cv2.VideoCapture(str(clip)); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV); m = cv2.inRange(hsv, (0, 120, 70), (10, 255, 255)) | cv2.inRange(hsv, (170, 120, 70), (180, 255, 255))
        n, lab, st, cen = cv2.connectedComponentsWithStats(m)
        out.append(None if n < 2 else (float(cen[1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))][0] / f.shape[1]), float(cen[1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))][1] / f.shape[0])))
    cap.release(); return out


def measure_track(clip, start, line):
    """Distance from the drawn line per frame, by the page's own follower (template matching) and by the boat's colour."""
    drawn = json.loads(F.tracks_json([line]))[0]; trk = F.centroid_track(clip, start); red = red_track(clip)
    pts = lambda tr: [None if p is None else [round(p[0], 4), round(p[1], 4)] for p in tr]
    return {"follow": F.follow_error(trk, drawn, F.LTX["size"]), "follow_by_colour": F.follow_error(red, drawn, F.LTX["size"]), "followed": pts(trk), "followed_by_colour": pts(red)}


def step_retrack():
    """Re-measure a finished track render (CPU only) after a change to the follower; the render is not repeated."""
    t = log()["track"]; put("track", t | measure_track(t["file"], t["start"], t["line"]) | {"remeasured": time.strftime("%Y-%m-%d %H:%M")})


def run_wanpath(turn, key):
    shot = WAN_SHOTS[key]; still = Path(log()["still:" + key]["file"]); path = F.PRESETS[shot["preset"]]["path"]; plan = F.path_plan(path); name = C.upload(still)
    def go():
        h = C.run(F.graph(F.WAN["graph"], F.wan_values(name, path, shot["prompt"], shot["seed"]), f"campath_proof/wan_{key}"))
        return C.fetch(F.outputs(h, "save")[0], WORK / "wanpath" / f"wan_{key}.mp4")
    out, s, pk = turn.job("wan_path", go)
    chk = V.verify(out, plan["expect"])
    put("wanpath:" + key, {"model": F.WAN["model"], "path": path, "preset": shot["preset"], "drawn_as": shot["drawn_as"], "expect": plan["expect"], "predicted": {"subject": plan["subject"], "background": plan["background"]},
                           "prompt": shot["prompt"], "seed": shot["seed"], "seconds": s, "peak_vram_gib": pk, "verdict": chk["verdict"], "why": chk["why"], "said": chk["said"], "measured": chk["measured"], "file": str(out)})


def run_h3(turn, idea, move, seed, key, quality="high"):
    o = {**goals.DIRECTOR_DEFAULTS, "camera": move, "aspect": "16:9", "quality": quality, "seconds": 5, "speed": "fast"}
    v = goals.flagship_values("director", {"prompt": idea}, None, o, seed)
    def go():
        h = C.run(F.graph("h3_t2v_api.json", v, f"campath_proof/{key}")); return C.fetch(F.outputs(h, "92")[0], WORK / "director" / f"{key}.mp4")
    out, s, pk = turn.job("h3_director", go)
    put(key, {"model": f"MiniMax H3 (Director goal, fast, {quality})", "prompt": v["prompt"], "idea": idea, "move": move, "seed": seed, "seconds": s, "peak_vram_gib": pk, "file": str(out)})


def step_gpu():
    with Turn(hold=list(PEAKS)) as t:
        for k, (p, s) in STILLS.items():
            if "still:" + k not in log(): run_klein(t, k, p, s)
        if "track" not in log(): run_track(t)
        for k in WAN_SHOTS:
            if "wanpath:" + k not in log(): run_wanpath(t, k)
        for mv, (idea, seed) in DIRECTOR.items():
            if "director:" + mv not in log(): run_h3(t, idea, mv, seed, "director:" + mv)
        for i, seed in enumerate(PICK[1]):
            if f"pick:{i}" not in log(): run_h3(t, PICK[0], PICK_MOVE, seed, f"pick:{i}", quality="standard")


#: Our own showcase clips with a known requested move, kept as technical evidence. What the camera did by eye is added at pack time.
KNOWN = [("reshoot_orbit_take", SHOW / "reshoot_orbit_take.mp4", "orbit_right"), ("director_wide", SHOW / "director_wide.mp4", "crane_up"),
         ("director_portrait", SHOW / "director_portrait.mp4", "orbit_right"), ("director_keyframes_bloom", SHOW / "director_keyframes_bloom.mp4", "pan_left")]


def step_confusion():
    rows = []; d = log()
    clips = list(KNOWN) + [(f"rooftop_{mv}", Path(d["director:" + mv]["file"]), mv) for mv in DIRECTOR if "director:" + mv in d]
    clips += [(f"wan_{k}", Path(d["wanpath:" + k]["file"]), d["wanpath:" + k]["expect"]) for k in WAN_SHOTS if "wanpath:" + k in d]
    for name, p, mv in clips:
        r = V.verify(p, mv); rows.append({"clip": name, "requested": mv, "verdict": r["verdict"], "why": r["why"], "said": r["said"], "measured": {k: r["measured"][k] for k in ("x", "y", "scale", "roll", "centre", "edge", "shake", "inliers_mean", "points_median", "cuts")}})
    v_wan = V.verify(SHOW / "v_wan_camera.mp4", "orbit_right")
    put("confusion", {"rows": rows, "unknown_request": {"clip": "v_wan_camera", "note": "its preset was not recorded (prompt: 'The camera slowly circles the subject'), so it is measured but not counted", "said": v_wan["said"], "as_orbit_right": v_wan["verdict"]}})
    takes = [(f"take {i + 1}", Path(d[f"pick:{i}"]["file"])) for i in range(len(PICK[1])) if f"pick:{i}" in d]
    if len(takes) >= 2:
        r = V.pick(takes, PICK_MOVE)
        put("pick", {"move": PICK_MOVE, "picked": r["picked"], "why": r["why"], "results": [{k: x[k] for k in ("take", "verdict", "why", "said", "strength")} for x in r["results"]]})


def step_pack():
    """studio/camera_proof.json and the media the page shows. Run only after looking at every output; notes come from CAMPATH_LOOKED (a JSON file: faults, edits, eye, looked by key)."""
    d = log(); notes = json.loads(Path(os.environ["CAMPATH_LOOKED"]).read_text()) if os.environ.get("CAMPATH_LOOKED") else {}
    web = REPO / "studio" / "web" / "campath"; web.mkdir(parents=True, exist_ok=True)
    from studio import likeness

    def show(src, name):
        likeness.mark(src, web / name); return f"campath/{name}"

    def poster(src, name):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.5", "-i", str(src), "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "70", str(web / name)], check=True); return f"campath/{name}"
    conf = json.loads(json.dumps(d.get("confusion"))) if d.get("confusion") else None
    for r in (conf or {}).get("rows", []): r["eye"] = notes.get("eye", {}).get(r["clip"], "")
    out = {"checked": time.strftime("%Y-%m-%d"), "faults": notes.get("faults", []), "edits": notes.get("edits", []), "confusion": conf, "verifier": {"thresholds_written_before_measuring": True, "source": "studio/camera_verify.py"}}
    looked = notes.get("looked", {})
    if "track" in d:
        t = d["track"]; out["track"] = {k: t[k] for k in ("model", "lora", "subject", "prompt", "seed", "seconds", "peak_vram_gib", "line", "follow", "follow_by_colour")} | {"src": show(t["file"], "track_boat.mp4"), "poster": poster(t["file"], "track_boat.webp"), "guide": show(t["guide"], "track_boat_guide.mp4"), "looked": looked.get("track", "")}
    out["wanpath"] = {k: {x: d["wanpath:" + k][x] for x in ("model", "path", "preset", "drawn_as", "expect", "predicted", "prompt", "seed", "seconds", "peak_vram_gib", "verdict", "why", "said")} | {"src": show(d["wanpath:" + k]["file"], f"wan_{k}.mp4"), "poster": poster(d["wanpath:" + k]["file"], f"wan_{k}.webp"), "looked": looked.get("wanpath:" + k, "")} for k in WAN_SHOTS if "wanpath:" + k in d}
    out["director"] = {mv: {k: d["director:" + mv][k] for k in ("model", "prompt", "seed", "seconds", "peak_vram_gib")} | {"src": show(d["director:" + mv]["file"], f"rooftop_{mv}.mp4"), "poster": poster(d["director:" + mv]["file"], f"rooftop_{mv}.webp"), "verdict": next((r["verdict"] for r in (conf or {}).get("rows", []) if r["clip"] == f"rooftop_{mv}"), None), "looked": looked.get("director:" + mv, "")} for mv in DIRECTOR if "director:" + mv in d}
    if "pick" in d:
        p = d["pick"]; out["pick"] = p | {"takes": [{"take": f"take {i + 1}", "seed": d[f"pick:{i}"]["seed"], "src": show(d[f"pick:{i}"]["file"], f"lighthouse_take{i + 1}.mp4"), "poster": poster(d[f"pick:{i}"]["file"], f"lighthouse_take{i + 1}.webp"), "seconds": d[f"pick:{i}"]["seconds"], "peak_vram_gib": d[f"pick:{i}"]["peak_vram_gib"]} for i in range(len(PICK[1])) if f"pick:{i}" in d], "prompt": d["pick:0"]["prompt"], "model": d["pick:0"]["model"], "looked": looked.get("pick", "")}
    out["stills"] = {k.split(":")[1]: {x: d[k][x] for x in ("model", "prompt", "seed", "seconds", "peak_vram_gib")} for k in d if k.startswith("still:") and k.split(":")[1] in STILLS}
    (REPO / "studio" / "camera_proof.json").write_text(json.dumps(out, indent=1)); print("wrote studio/camera_proof.json")


if __name__ == "__main__":
    for st in sys.argv[1:] or ["gpu", "confusion"]: globals()["step_" + st]()
