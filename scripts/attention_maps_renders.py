#!/usr/bin/env python3
"""Proof renders for "Which word painted what": real SD 1.5 and SDXL renders with the PSN attention recorder, checked against the picture.

For each model it renders the same graph without the recorder first, to show the picture does not change, then once more on another seed so the
recorder's cost is timed on a warm model. Each check says how much of a word's attention falls on pixels of a colour the prompt names, against how
much of the picture those pixels cover. A check that fails is written down as failing. Peak VRAM is read from nvidia-smi for the ComfyUI process.

Usage: attention_maps_renders.py <comfyui url> [--only id,id] [--out studio/sampling_lab/attention.json]
Needs numpy and Pillow. Talks only to the ComfyUI you name; run it on a ComfyUI that has this pack's PSN attention nodes."""
import base64, colorsys, io, json, os, subprocess, sys, threading, time, urllib.parse, urllib.request, uuid
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "studio"))
from words_graph import MODELS, NEGATIVE, SEED, STEPS, CFG, SAMPLER, SCHEDULER, PICTURE, SHEET, build  # noqa: E402
from sampling_graph import PROMPT as ASTROLABE  # noqa: E402
WEB = os.path.join(ROOT, "studio", "web"); IMG_DIR = "sampling_lab/attn"; SHOW_PX = 512

PLAN = [
    {"id": "sd15-redhat", "model": "sd15", "prompt": "a red hat on a wooden table", "checks": [["hat", "red", "high"], ["red", "red", "high"], ["table", "red", "low"]], "proof": True},
    {"id": "sd15-duck", "model": "sd15", "prompt": "a yellow rubber duck next to a blue teacup", "checks": [["duck", "yellow", "high"], ["teacup", "blue", "high"], ["duck", "blue", "low"], ["teacup", "yellow", "low"]]},
    {"id": "sdxl-redhat", "model": "sdxl", "prompt": "a red hat on a wooden table", "checks": [["hat", "red", "high"], ["red", "red", "high"], ["table", "red", "low"]], "proof": True},
    {"id": "sdxl-duck", "model": "sdxl", "prompt": "a yellow rubber duck next to a blue teacup", "checks": [["duck", "yellow", "high"], ["teacup", "blue", "high"], ["duck", "blue", "low"], ["teacup", "yellow", "low"]]},
    {"id": "sdxl-astrolabe", "model": "sdxl", "prompt": ASTROLABE, "checks": []},
]
# Colour regions by hue, saturation and value, all 0 to 1. Plain thresholds, written for these prompts and checked by eye on the renders.
REGIONS = {"red": lambda h, s, v: ((h < 0.04) | (h > 0.95)) & (s > 0.45) & (v > 0.25), "yellow": lambda h, s, v: (h > 0.10) & (h < 0.19) & (s > 0.45) & (v > 0.45),
           "blue": lambda h, s, v: (h > 0.52) & (h < 0.72) & (s > 0.30) & (v > 0.20)}
HIGH, LOW = 1.5, 1.0     # a "high" check passes when the word's attention is at least 1.5 times as dense on the region as on the whole picture; a "low" one when it is less dense
# The first check, set before any render, reads raw attention. The first SDXL run showed every word's map sitting on a floor of 65 to 90% of its peak,
# which drowns any region in raw terms, so a second number reads only what rises above the floor. It was added after that run, and is judged by the same thresholds.


def call(base, path, payload=None, timeout=60, raw=False):
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode() if payload is not None else None, headers={"Content-Type": "application/json"} if payload is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r: b = r.read()
    return b if raw else json.loads(b or b"{}")


class Peak:
    """The most VRAM the ComfyUI process on this port held while the block ran, from nvidia-smi, in GiB."""
    def __init__(self, port): self.port = str(port); self.top = 0.0; self.on = False
    def pid(self):
        for p in os.listdir("/proc"):
            if not p.isdigit(): continue
            try: a = open(f"/proc/{p}/cmdline", "rb").read().split(b"\0")
            except OSError: continue
            a = [x.decode("utf8", "replace") for x in a if x]
            if "--port" in a[:-1] and a[a.index("--port") + 1] == self.port and any(x.endswith("main.py") for x in a[:3]): return int(p)
    def read(self, pid):
        try:
            for l in subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout.splitlines():
                a, m = [x.strip() for x in l.split(",")[:2]]
                if a == str(pid): return int(m) / 1024
        except Exception: pass
        return 0.0
    def __enter__(self):
        self.top = 0.0; self.on = True; pid = self.pid()
        def loop():
            while self.on: self.top = max(self.top, self.read(pid) if pid else 0.0); time.sleep(0.25)
        self.t = threading.Thread(target=loop, daemon=True); self.t.start(); return self
    def __exit__(self, *a): self.on = False; self.t.join(2)


def run(base, graph, limit=900):
    """Queue, wait, and return the history entry and its run time from ComfyUI's own start and success stamps."""
    jid = call(base, "/prompt", {"prompt": graph, "client_id": "attn-proof-" + uuid.uuid4().hex[:6]})["prompt_id"]; t0 = time.time()
    while time.time() - t0 < limit:
        h = call(base, f"/history/{jid}").get(jid)
        st = (h or {}).get("status") or {}
        if st.get("status_str") == "error": raise RuntimeError(json.dumps(st.get("messages"))[-800:])
        if h and st.get("completed"):
            ts = {k: i.get("timestamp") for k, i in st.get("messages", []) if k in ("execution_start", "execution_success")}
            secs = (ts["execution_success"] - ts["execution_start"]) / 1000 if all(ts.get(k) for k in ("execution_start", "execution_success")) else None
            return h, secs
        time.sleep(0.5)
    raise TimeoutError(jid)


def picture(base, h, node):
    f = h["outputs"][node]["images"][0]
    return Image.open(io.BytesIO(call(base, "/view?" + urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")}), raw=True))).convert("RGB")


def u8(b64, hw): return np.frombuffer(base64.b64decode(b64), dtype=np.uint8).reshape(hw)


def region(img, name, hw):
    """The share of each map cell covered by the named colour."""
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255; hsv = np.vectorize(colorsys.rgb_to_hsv, otypes=[np.float32, np.float32, np.float32])
    h, s, v = hsv(a[..., 0], a[..., 1], a[..., 2]); m = Image.fromarray((REGIONS[name](h, s, v) * 255).astype(np.uint8))
    return np.asarray(m.resize((hw[1], hw[0]), Image.BOX), dtype=np.float32) / 255


def check(data, img, word, colour, expect):
    hw = tuple(data["map_size"]); w = next((x for x in data["words"] if x["word"] == word), None)
    if w is None: return {"word": word, "region": colour, "expect": expect, "ok": False, "why": "word not in the prompt's tokens"}
    up = u8(w["map"], hw).astype(np.float32) / 255; m = w["floor"] + up * (w["peak"] - w["floor"]); r = region(img, colour, hw); area = float(r.mean())
    judge = lambda lift: area > 0.005 and (lift >= HIGH if expect == "high" else lift < LOW)
    inside = float((m * r).sum() / max(m.sum(), 1e-12)); lift = inside / area if area > 0 else 0.0
    above = float((up * r).sum() / max(up.sum(), 1e-12)); lift2 = above / area if area > 0 else 0.0
    return {"word": word, "region": colour, "expect": expect, "attention_inside": round(inside, 4), "picture_share": round(area, 4), "lift": round(lift, 2), "ok": judge(lift),
            "above_floor_inside": round(above, 4), "lift_above_floor": round(lift2, 2), "ok_above_floor": judge(lift2)}


def sprite(data, shown):
    """One grey PNG: a row per shown word, columns overall, early, middle, late, each scaled to its own peak."""
    h, w = data["map_size"]; out = np.zeros((h * len(shown), w * 4), np.uint8)
    for r, i in enumerate(shown):
        wd = data["words"][i]; cols = [wd["map"]] + wd["phases"]
        for c, b in enumerate(cols):
            if b: out[r * h:(r + 1) * h, c * w:(c + 1) * w] = u8(b, (h, w))
    bio = io.BytesIO(); Image.fromarray(out, "L").save(bio, "PNG", optimize=True); return bio.getvalue()


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"): print(__doc__); return 2
    base = a[0].rstrip("/"); port = urllib.parse.urlparse(base).port or 80
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(ROOT, "studio", "sampling_lab", "attention.json")
    try: old = {r["id"]: r for r in json.load(open(out)).get("renders", [])}
    except (OSError, ValueError): old = {}
    os.makedirs(os.path.join(WEB, IMG_DIR), exist_ok=True)
    info = call(base, "/object_info/PSN_AttentionRecord")
    if "PSN_AttentionRecord" not in info: print("This ComfyUI has no PSN_AttentionRecord node."); return 1
    stats = call(base, "/system_stats"); gpu = ((stats.get("devices") or [{}])[0].get("name") or "").split(" : ")[0].replace("cuda:0 ", "")
    rows = []; last_model = None
    for p in PLAN:
        if only and p["id"] not in only: continue
        if p["model"] != last_model: call(base, "/free", {"unload_models": True, "free_memory": True}); time.sleep(2); last_model = p["model"]
        r = {**p, "seed": SEED, "steps": STEPS, "cfg": CFG, "sampler": SAMPLER, "scheduler": SCHEDULER, "negative": NEGATIVE, "size": MODELS[p["model"]]["size"], "ckpt": MODELS[p["model"]]["ckpt"]}
        proof = {}
        with Peak(port) as pk:
            if p.get("proof"):
                hp, _ = run(base, build(r, record=False)); plain = picture(base, hp, PICTURE)
            h, secs = run(base, build(r))
            if p.get("proof"):
                hw, warm = run(base, build({**r, "seed": SEED + 1, "id": r["id"] + "-timing"}, record=False))
        img = picture(base, h, PICTURE); data = h["outputs"]["10"]["psn_attention"][0]
        if p.get("proof"):
            d = np.abs(np.asarray(img, np.int16) - np.asarray(plain, np.int16))
            proof = {"same_picture_mean_abs": round(float(d.mean()), 4), "same_picture_max_abs": int(d.max()), "pixels_differing": round(float((d.max(-1) > 0).mean()), 5),
                     "pixels_off_by_over_10": round(float((d.max(-1) > 10).mean()), 5), "same_picture_p99": float(np.percentile(d.max(-1), 99)),
                     "seconds_recorded": round(secs, 2) if secs else None, "seconds_plain_warm": round(warm, 2) if warm else None}
        shown = [i for i, w in enumerate(data["words"]) if not w["punct"]]
        img.resize((SHOW_PX, SHOW_PX), Image.LANCZOS).save(os.path.join(WEB, IMG_DIR, r["id"] + ".jpg"), quality=90)
        open(os.path.join(WEB, IMG_DIR, r["id"] + ".maps.png"), "wb").write(sprite(data, shown))
        if r["id"] == "sd15-redhat":
            sh = picture(base, h, SHEET); sh.thumbnail((1280, 1280)); sh.save(os.path.join(WEB, IMG_DIR, r["id"] + ".sheet.jpg"), quality=85)
        checks = [check(data, img, *c) for c in p["checks"]]
        rows.append({k: r[k] for k in ("id", "model", "prompt", "negative", "seed", "steps", "cfg", "sampler", "scheduler", "size", "ckpt")} | {
            "image": f"{IMG_DIR}/{r['id']}.jpg", "maps": f"{IMG_DIR}/{r['id']}.maps.png", "map_size": data["map_size"], "latent": data.get("latent"), "layers": data.get("layers"), "calls": data.get("calls"),
            "steps_recorded": data["steps"], "start_share": data["start_share"], "end_share": data["end_share"],
            "words": [{k: data["words"][i][k] for k in ("word", "tokens", "share", "floor", "peak")} for i in shown],
            "checks": checks, "proof": proof, "seconds": round(secs, 2) if secs else None, "peak_vram_gib": round(pk.top, 2), "ran_on": gpu, "when": time.strftime("%Y-%m-%d")})
        print(r["id"], "peak", round(pk.top, 2), "GiB", [(c["word"], c["region"], c.get("lift"), c["ok"], c.get("lift_above_floor"), c.get("ok_above_floor")) for c in checks], proof, flush=True)
    for r in rows: old[r["id"]] = r
    order = [p["id"] for p in PLAN]; done = sorted(old.values(), key=lambda r: order.index(r["id"]) if r["id"] in order else 99)
    doc = {"about": "Real renders with the PSN attention recorder. Each map is a mean over heads, cross-attention layers and steps, of the cond half of the batch, stored stretched between its own floor and peak.", "high": HIGH, "low": LOW, "renders": done,
           "sheet": f"{IMG_DIR}/sd15-redhat.sheet.jpg" if os.path.exists(os.path.join(WEB, IMG_DIR, "sd15-redhat.sheet.jpg")) else None}
    tmp = out + ".tmp"; json.dump(doc, open(tmp, "w"), indent=1); os.replace(tmp, out); print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
