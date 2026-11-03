#!/usr/bin/env python3
"""Renders the Sampling Lab's latent walk on SD 1.5: a walk between two seeds (the starting noise slerped), a walk between two prompts (the conditioning lerped), a straight blend against slerp at the midpoint, and a strip showing every sampler step.
It runs on a ComfyUI lane of your own (never the studio's main one) and takes a turn from the shared GPU gate, declaring its peak first and recording the measured one after.
Every graph uses the main ComfyUI's nodes: core samplers, KJNodes' GenerateNoise for the seeded noise, and the studio pack's PSN_LatentSlerp and PSN_LatentMath for the blends.
Usage: latent_walk_renders.py --comfy http://127.0.0.1:PORT [--gate DIR_WITH_gpu_gate.py] [--out-json studio/sampling_lab/walk.json] [--out-img studio/web/sampling_lab/walk]
The gate's folder can come from $PSN_GPU_GATE."""
import argparse, datetime, hashlib, io, json, math, os, re, subprocess, sys, threading, time, urllib.parse, urllib.request, uuid

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CKPT, SIZE, STEPS, CFG, SAMPLER, SCHED = "v1-5-pruned-emaonly.safetensors", 512, 20, 7.0, "euler", "normal"
NEG = "blurry, low quality, text, watermark"
SEED_PROMPT, SEEDS = "a brass lighthouse on a mossy sea cliff at dusk, warm window light, oil painting", (1101, 2202)
PROMPTS, PROMPT_SEED = ("a small stone cottage with a green door in a meadow, watercolor", "a small wooden sailboat with a green sail on a calm sea, watercolor"), 3303
STRIP_PROMPT, STRIP_SEED = "a red paper lantern floating above a misty lake at night", 4404
TS = [i / 8 for i in range(9)]
DECLARED_GIB, KEY = 6.0, "nnanatomy:latent_walk_sd15"


def sd15_sigma_max():
    """SD 1.5's largest sigma, from its linear beta schedule (0.00085 to 0.012 over 1000 steps), as ComfyUI computes it."""
    b0, b1, n = math.sqrt(0.00085), math.sqrt(0.012), 1000; acp = 1.0
    for i in range(n): b = (b0 + (b1 - b0) * i / (n - 1)) ** 2; acp *= 1 - b
    return math.sqrt((1 - acp) / acp)


SMAX = sd15_sigma_max()
NOISE_MULT = math.sqrt(1 + SMAX ** 2) / SMAX      # GenerateNoise scales by sigma_max; a full denoise starts at sqrt(1 + sigma_max^2) times the noise


def get(base, path, timeout=30):
    with urllib.request.urlopen(base + path, timeout=timeout) as r: return r.read()


def post(base, path, body):
    q = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(q, timeout=60) as r: return json.loads(r.read())


class Graph:
    def __init__(self): self.g, self.n = {}, 0
    def add(self, cls, **inputs):
        self.n += 1; k = str(self.n); self.g[k] = {"class_type": cls, "inputs": inputs}; return k
    def base(self, pos, neg=NEG):
        m = self.add("CheckpointLoaderSimple", ckpt_name=CKPT)
        return m, self.add("CLIPTextEncode", text=pos, clip=[m, 1]), self.add("CLIPTextEncode", text=neg, clip=[m, 1])
    def save(self, image, name):
        return self.add("SaveImage", images=image, filename_prefix="nnwalk/" + name)


def noise(G, m, seed, sig):
    return G.add("GenerateNoise", width=SIZE, height=SIZE, batch_size=1, seed=seed, multiplier=NOISE_MULT, constant_batch_noise=False, normalize=False, model=[m, 0], sigmas=[sig, 0], latent_channels="4", shape="BCHW")


def sample_from(G, m, pos, neg, latent, seed=0, add_noise="disable"):
    return G.add("KSamplerAdvanced", model=[m, 0], add_noise=add_noise, noise_seed=seed, steps=STEPS, cfg=CFG, sampler_name=SAMPLER, scheduler=SCHED, positive=[pos, 0], negative=[neg, 0], latent_image=[latent, 0], start_at_step=0, end_at_step=10000, return_with_leftover_noise="disable")


def decode(G, m, lat, idx=0): return G.add("VAEDecode", samples=[lat, idx], vae=[m, 2])


def seed_walk():
    G = Graph(); m, pos, neg = G.base(SEED_PROMPT); sig = G.add("BasicScheduler", model=[m, 0], scheduler=SCHED, steps=STEPS, denoise=1.0)
    a, b = noise(G, m, SEEDS[0], sig), noise(G, m, SEEDS[1], sig); names = {}
    for t in TS:
        x = G.add("PSN_LatentSlerp", latent_a=[a, 0], latent_b=[b, 0], t=t); names[G.save([decode(G, m, sample_from(G, m, pos, neg, x)), 0], f"seed_{t:.3f}")] = ("seed", t)
    mid = G.add("PSN_LatentMath", latent_a=[a, 0], latent_b=[b, 0], op="lerp", strength=0.5); names[G.save([decode(G, m, sample_from(G, m, pos, neg, mid)), 0], "lerp_0.500")] = ("lerp", 0.5)
    empty = G.add("EmptyLatentImage", width=SIZE, height=SIZE, batch_size=1)          # the check: an ordinary KSampler at each seed
    for s in SEEDS:
        ks = G.add("KSampler", model=[m, 0], seed=s, steps=STEPS, cfg=CFG, sampler_name=SAMPLER, scheduler=SCHED, positive=[pos, 0], negative=[neg, 0], latent_image=[empty, 0], denoise=1.0)
        names[G.save([decode(G, m, ks), 0], f"plain_{s}")] = ("plain", s)
    return G.g, names


def prompt_walk():
    G = Graph(); m = G.add("CheckpointLoaderSimple", ckpt_name=CKPT)
    a, b, neg = (G.add("CLIPTextEncode", text=t, clip=[m, 1]) for t in (*PROMPTS, NEG)); empty = G.add("EmptyLatentImage", width=SIZE, height=SIZE, batch_size=1); names = {}
    for t in TS:
        c = G.add("ConditioningAverage", conditioning_to=[a, 0], conditioning_from=[b, 0], conditioning_to_strength=round(1 - t, 6))
        ks = G.add("KSampler", model=[m, 0], seed=PROMPT_SEED, steps=STEPS, cfg=CFG, sampler_name=SAMPLER, scheduler=SCHED, positive=[c, 0], negative=[neg, 0], latent_image=[empty, 0], denoise=1.0)
        names[G.save([decode(G, m, ks), 0], f"prompt_{t:.3f}")] = ("prompt", t)
    return G.g, names


def strip():
    G = Graph(); m, pos, neg = G.base(STRIP_PROMPT); names = {}
    sig = G.add("BasicScheduler", model=[m, 0], scheduler=SCHED, steps=STEPS, denoise=1.0)
    nz = G.add("RandomNoise", noise_seed=STRIP_SEED); gd = G.add("CFGGuider", model=[m, 0], positive=[pos, 0], negative=[neg, 0], cfg=CFG); sp = G.add("KSamplerSelect", sampler_name=SAMPLER)
    empty = G.add("EmptyLatentImage", width=SIZE, height=SIZE, batch_size=1)
    for k in range(1, STEPS + 1):
        part = G.add("SplitSigmas", sigmas=[sig, 0], step=k)
        sa = G.add("SamplerCustomAdvanced", noise=[nz, 0], guider=[gd, 0], sampler=[sp, 0], sigmas=[part, 0], latent_image=[empty, 0])
        names[G.save([decode(G, m, sa, 0), 0], f"strip_x_{k:02d}")] = ("x", k); names[G.save([decode(G, m, sa, 1), 0], f"strip_x0_{k:02d}")] = ("x0", k)
    ks = G.add("KSampler", model=[m, 0], seed=STRIP_SEED, steps=STEPS, cfg=CFG, sampler_name=SAMPLER, scheduler=SCHED, positive=[pos, 0], negative=[neg, 0], latent_image=[empty, 0], denoise=1.0)
    names[G.save([decode(G, m, ks), 0], "strip_plain")] = ("plain", STEPS)
    return G.g, names


class PeakWatch(threading.Thread):
    """The lane's own memory on the card, polled from nvidia-smi while it works."""
    def __init__(self, port):
        super().__init__(daemon=True); self.port, self.peak, self.on = port, 0.0, True
    def pid(self):
        for p in os.listdir("/proc"):
            if not p.isdigit(): continue
            try: a = open(f"/proc/{p}/cmdline", "rb").read().split(b"\0")
            except OSError: continue
            if b"--port" in a and a[a.index(b"--port") + 1] == str(self.port).encode() and any(x.endswith(b"main.py") for x in a[:3]): return int(p)
    def run(self):
        pid = self.pid()
        while self.on:
            try:
                for l in subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout.splitlines():
                    p, mem = [x.strip() for x in l.split(",")[:2]]
                    if p == str(pid): self.peak = max(self.peak, int(mem) / 1024)
            except Exception: pass
            time.sleep(0.5)


def free_gib():
    return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.split()[0]) / 1024


def run(base, graph, names, img_dir):
    """Queue one graph, wait, and save each output as a JPEG. -> ({name: file}, seconds)"""
    from PIL import Image
    t0 = time.time(); pid = post(base, "/prompt", {"prompt": graph, "client_id": "nnwalk-" + uuid.uuid4().hex[:8]})["prompt_id"]
    while True:
        time.sleep(1.0); h = json.loads(get(base, "/history/" + pid))
        if pid in h: break
        if free_gib() < 4.0: post(base, "/interrupt", {}); raise RuntimeError("the card went under the 4 GiB floor, so the walk stopped")
        if time.time() - t0 > 900: raise RuntimeError("the walk took longer than 15 minutes")
    e = h[pid]; st = e.get("status", {})
    if st.get("status_str") != "success": raise RuntimeError(f"ComfyUI said {st.get('status_str')}: {json.dumps(st.get('messages', []))[:600]}")
    out = {}
    for node, o in e["outputs"].items():
        name = graph[node]["inputs"]["filename_prefix"].split("/")[-1]; im = o["images"][0]
        raw = get(base, "/view?" + urllib.parse.urlencode({k: im[k] for k in ("filename", "subfolder", "type")}), 60)
        pic = Image.open(io.BytesIO(raw)).convert("RGB"); f = name + ".jpg"
        if name.startswith("strip_"): pic = pic.resize((256, 256), Image.LANCZOS)
        pic.save(os.path.join(img_dir, f), "JPEG", quality=84, optimize=True); out[name] = f
    return out, round(time.time() - t0, 1)


def mean_abs(a, b, img_dir):
    from PIL import Image, ImageChops, ImageStat
    x, y = Image.open(os.path.join(img_dir, a)), Image.open(os.path.join(img_dir, b))
    return round(sum(ImageStat.Stat(ImageChops.difference(x, y)).mean) / 3, 2)


def noise_numbers():
    """The two noises, their slerp and their straight blend at the midpoint, measured on the CPU with the generator ComfyUI uses."""
    import torch
    a, b = (torch.randn([1, 4, SIZE // 8, SIZE // 8], generator=torch.manual_seed(s), dtype=torch.float32) for s in SEEDS)
    af, bf = a.flatten(), b.flatten(); om = torch.acos((af / af.norm()).dot(bf / bf.norm()).clamp(-1, 1))
    sl = (torch.sin(0.5 * om) / torch.sin(om)) * (af + bf); le = 0.5 * (af + bf)
    r = lambda v: round(float(v), 3)
    return {"angle_degrees": r(om * 180 / math.pi), "norm": {"a": r(af.norm()), "b": r(bf.norm()), "slerp": r(sl.norm()), "lerp": r(le.norm())}, "std": {"a": r(af.std()), "b": r(bf.std()), "slerp": r(sl.std()), "lerp": r(le.std())}, "elements": af.numel()}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--comfy", required=True); ap.add_argument("--gate", default=os.environ.get("PSN_GPU_GATE", "")); ap.add_argument("--out-json", default=os.path.join(ROOT, "studio", "sampling_lab", "walk.json")); ap.add_argument("--out-img", default=os.path.join(ROOT, "studio", "web", "sampling_lab", "walk")); a = ap.parse_args()
    base = a.comfy.rstrip("/"); port = int(urllib.parse.urlparse(base).port); stats = json.loads(get(base, "/system_stats"))
    if port in (8200, 8322): sys.exit("This walk runs on a lane of its own, never on the studio's main ComfyUI.")
    sys.path.insert(0, a.gate); import gpu_gate as gate
    os.makedirs(a.out_img, exist_ok=True)
    jobs = [("seed_walk", seed_walk()), ("prompt_walk", prompt_walk()), ("strip", strip())]
    rid = None
    while rid is None:
        rid, why = gate.acquire("nnanatomy", KEY, gate.expected(KEY, DECLARED_GIB), heavy=False, port=port)
        if rid is None: print("waiting for the gate:", why, flush=True); time.sleep(20)
    watch = PeakWatch(port); watch.start(); files, secs = {}, {}
    try:
        for name, (g, _) in jobs:
            f, s = run(base, g, _, a.out_img); files.update(f); secs[name] = s; print(name, s, "s", flush=True)
    finally:
        watch.on = False; time.sleep(0.6); gate.release(rid)
    if watch.peak: gate.record_peak(KEY, watch.peak)
    dev = (stats.get("devices") or [{}])[0]; flags = [x for x in stats["system"]["argv"] if x in ("--disable-cuda-malloc", "--bf16-vae", "--bf16-text-enc", "--reserve-vram")]
    sh = lambda g: hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest()[:12]
    walk = {
        "model": {"id": "sd15", "name": "SD 1.5", "ckpt": CKPT, "licence": "CreativeML OpenRAIL-M", "kind": "eps"},
        "settings": {"steps": STEPS, "cfg": CFG, "sampler": SAMPLER, "scheduler": SCHED, "size": SIZE, "negative": NEG, "sigma_max": round(SMAX, 4), "noise_multiplier": round(NOISE_MULT, 6)},
        "seed_walk": {"prompt": SEED_PROMPT, "seeds": list(SEEDS), "frames": [{"t": t, "img": files[f"seed_{t:.3f}"]} for t in TS], "graph_hash": sh(jobs[0][1][0]),
                      "check": {"t0_vs_plain": mean_abs(files["seed_0.000"], files[f"plain_{SEEDS[0]}"], a.out_img), "t1_vs_plain": mean_abs(files["seed_1.000"], files[f"plain_{SEEDS[1]}"], a.out_img), "plain": [files[f"plain_{s}"] for s in SEEDS]}},
        "blend": {"t": 0.5, "slerp": files["seed_0.500"], "lerp": files["lerp_0.500"], "noise": noise_numbers(), "pixel_diff": mean_abs(files["seed_0.500"], files["lerp_0.500"], a.out_img)},
        "prompt_walk": {"prompts": list(PROMPTS), "seed": PROMPT_SEED, "frames": [{"t": t, "img": files[f"prompt_{t:.3f}"]} for t in TS], "graph_hash": sh(jobs[1][1][0])},
        "strip": {"prompt": STRIP_PROMPT, "seed": STRIP_SEED, "steps": [{"k": k, "x": files[f"strip_x_{k:02d}"], "x0": files[f"strip_x0_{k:02d}"]} for k in range(1, STEPS + 1)], "graph_hash": sh(jobs[2][1][0]),
                  "check": {"last_vs_plain": mean_abs(files[f"strip_x_{STEPS:02d}"], files["strip_plain"], a.out_img), "plain": files["strip_plain"]}},
        "measured": {"date": datetime.date.today().isoformat(), "seconds": secs, "peak_vram_gib": round(watch.peak, 2), "declared_gib": DECLARED_GIB, "gpu": re.sub(r"^cuda:\d+\s*|\s*:\s*\w+$", "", dev.get("name", "")).strip(), "comfyui": stats["system"].get("comfyui_version"), "flags": flags, "packs": ["ComfyUI core", "KJNodes: GenerateNoise", "Parametric Studio: PSN_LatentSlerp, PSN_LatentMath"]},
        "graphs": {"seed_walk": jobs[0][1][0], "prompt_walk": jobs[1][1][0], "strip": jobs[2][1][0]},
    }
    os.makedirs(os.path.dirname(a.out_json), exist_ok=True)
    with open(a.out_json, "w", encoding="utf8") as f: json.dump(walk, f, indent=1)
    print("saved", a.out_json, "peak", walk["measured"]["peak_vram_gib"], "GiB", "checks", walk["seed_walk"]["check"], walk["strip"]["check"])


if __name__ == "__main__": main()
