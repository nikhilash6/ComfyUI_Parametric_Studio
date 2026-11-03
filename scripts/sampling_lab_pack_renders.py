#!/usr/bin/env python3
"""Sampling Lab pack renders: methods from node packs now installed on this machine's ComfyUI, one change from a core baseline.

Same seed, prompt, steps and model as the core proof sweep (studio/sampling_graph.py), so a pack render reads against its core baseline.
Each set re-renders its own core baseline first, on the same ComfyUI, which also shows whether the installed packs changed core output.
Every graph is checked against ComfyUI's own /object_info before it is queued. Renders take their turn through the shared GPU gate,
one at a time, with the measured peak recorded. Nothing here installs, restarts or patches anything.
Usage: sampling_lab_pack_renders.py <comfy url> <object_info.json> <out.json> <jpeg dir> [--plan-only] [--gate <gpu_gate.py dir>]
"""
import hashlib, io, json, os, subprocess, sys, threading, time, urllib.parse, urllib.request, uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "studio"))
from sampling_graph import PROMPT, SEED, STEPS, build as core_graph  # noqa: E402

SDXL_PEAK_GIB = 12.0      # declared for the gate; the measured peak replaces it once known
SETS = {"pack-sampler": "Pack samplers", "pack-scheduler": "Pack schedulers", "pack-guidance": "Pack guidance"}


def plan():
    rows = []
    def add(set_, method, label, sampler="euler", scheduler="normal", cfg=7.0, patches=(), wrap=None, baseline=False, pack="core", note=""):
        rows.append({"id": f"{set_}-{method}", "set": set_, "method": method, "label": label, "model": "sdxl", "sampler": sampler, "scheduler": scheduler, "cfg": cfg,
                     "patches": [list(p) for p in patches], "wrap": wrap, "guider": None, "baseline": baseline, "pack": pack, "note": note})
    # Samplers: picked by name from the normal sampler list, against core euler with the normal schedule.
    add("pack-sampler", "euler", "euler (core)", baseline=True, note="Core baseline, re-rendered today with all the packs installed.")
    add("pack-sampler", "hfe_auto", "hfe_auto", "hfe_auto", pack="WASasquatch__RES4SHO")
    add("pack-sampler", "hfx_detail", "hfx_detail", "hfx_detail", pack="WASasquatch__RES4SHO")
    add("pack-sampler", "hfx_spectral", "hfx_spectral", "hfx_spectral", pack="WASasquatch__RES4SHO")
    add("pack-sampler", "Distance", "Distance", "Distance", pack="Extraltodeus__DistanceSampler")
    add("pack-sampler", "er_sde_cns", "er_sde_cns", "er_sde_cns", pack="sorryhyun__ComfyUI-Spectrum-KSampler")
    add("pack-sampler", "detail-daemon", "Detail Daemon", wrap=["DetailDaemonSamplerNode", {}], pack="Jonseed__ComfyUI-Detail-Daemon", note="Core euler wrapped by Detail Daemon at its defaults.")
    # Schedulers: picked by name from the normal scheduler list, against core dpmpp_2m with the normal schedule.
    add("pack-scheduler", "normal", "normal (core)", "dpmpp_2m", "normal", baseline=True, note="Core baseline, re-rendered today with all the packs installed.")
    add("pack-scheduler", "sigmoid_offset", "sigmoid_offset", "dpmpp_2m", "sigmoid_offset", pack="silveroxides__ComfyUI_SigmoidOffsetScheduler")
    add("pack-scheduler", "beta_57", "beta_57", "dpmpp_2m", "beta_57", pack="silveroxides__ComfyUI_PowerShiftScheduler")
    add("pack-scheduler", "ays+", "ays+", "dpmpp_2m", "ays+", pack="pamparamm__ComfyUI-ppm")
    add("pack-scheduler", "atan_detail", "atan_detail", "dpmpp_2m", "atan_detail", pack="WASasquatch__RES4SHO")
    add("pack-scheduler", "kumaraswamy", "kumaraswamy", "dpmpp_2m", "kumaraswamy", pack="WASasquatch__RES4SHO")
    # Guidance: model patches at CFG 14, against plain CFG 14, the same test the core fixes got.
    add("pack-guidance", "cfg-14", "CFG 14 (core)", cfg=14.0, baseline=True, note="Core baseline, re-rendered today with all the packs installed.")
    add("pack-guidance", "skimmed-14", "Skimmed CFG", cfg=14.0, patches=[["CFGP_SkimmedCFG", {}]], pack="AbstractEyes__comfy-cfg-megapack")
    add("pack-guidance", "reinhard-14", "Reinhard CFG", cfg=14.0, patches=[["CFGP_ReinhardCFG", {}]], pack="AbstractEyes__comfy-cfg-megapack")
    add("pack-guidance", "fdg-14", "Frequency-decoupled (FDG)", cfg=14.0, patches=[["CFGP_FDG", {}]], pack="AbstractEyes__comfy-cfg-megapack")
    return rows


def defaults(info, cls, given):
    """Fill every required widget the plan leaves out with the node's own default, read from /object_info. Links stay as given."""
    out = dict(given)
    for k, t in (info[cls]["input"].get("required") or {}).items():
        if k in out: continue
        if isinstance(t[0], list): out[k] = (t[1] or {}).get("default", t[0][0]) if len(t) > 1 else t[0][0]
        elif t[0] == "COMBO": out[k] = t[1].get("default", t[1]["options"][0])
        elif len(t) > 1 and isinstance(t[1], dict) and "default" in t[1]: out[k] = t[1]["default"]
    return out


def graph(r, info):
    patches = []
    for c, i in r["patches"]:
        filled = defaults(info, c, {"model": "link", **i}); filled.pop("model")   # build() wires the model link itself
        patches.append([c, filled])
    g = core_graph({**r, "patches": patches, "id": r["id"]})
    if r.get("wrap"):
        cls, inputs = r["wrap"]; g["30"] = {"class_type": cls, "inputs": defaults(info, cls, {"sampler": ["9", 0], **inputs})}; g["11"]["inputs"]["sampler"] = ["30", 0]
    return g


def check(g, info):
    """Every class exists, every required input is set, every combo value is allowed."""
    bad = []
    for nid, n in g.items():
        spec = info.get(n["class_type"])
        if not spec: bad.append(f"{nid}: no class {n['class_type']}"); continue
        for k, t in (spec["input"].get("required") or {}).items():
            if k not in n["inputs"]: bad.append(f"{nid} {n['class_type']}: missing {k}"); continue
            v = n["inputs"][k]; opts = t[0] if isinstance(t[0], list) else (t[1].get("options") if t[0] == "COMBO" else None)
            if opts is not None and not isinstance(v, list) and v not in opts: bad.append(f"{nid} {n['class_type']}: {k}={v!r} not allowed")
    return bad


def req(url, body=None, timeout=60):
    q = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, {"Content-Type": "application/json"})
    with urllib.request.urlopen(q, timeout=timeout) as f:
        raw = f.read(); return json.loads(raw) if raw else {}


def metrics(png, base_png):
    from PIL import Image, ImageChops, ImageFilter, ImageStat
    im = Image.open(io.BytesIO(png)).convert("RGB"); L = im.convert("L")
    m = {"brightness": round(ImageStat.Stat(L).mean[0], 1), "contrast": round(ImageStat.Stat(L).stddev[0], 1), "edge": round(ImageStat.Stat(L.filter(ImageFilter.FIND_EDGES)).mean[0], 2),
         "pixels": hashlib.sha256(im.tobytes()).hexdigest()[:16]}
    if base_png is not None:
        b = Image.open(io.BytesIO(base_png)).convert("RGB")
        m["diff_to_base"] = round(sum(ImageStat.Stat(ImageChops.difference(im, b)).mean) / 3, 2) if b.size == im.size else None
    return m, im


def main():
    comfy, info_path, out, jpg_dir = sys.argv[1:5]
    info = json.load(open(info_path)); rows = plan()
    problems = {r["id"]: check(graph(r, info), info) for r in rows}
    for k, v in problems.items():
        if v: print("BAD", k, v)
    if any(problems.values()): sys.exit("graphs don't match this ComfyUI; nothing queued")
    if "--plan-only" in sys.argv:
        print(len(rows), "graphs checked"); return
    port = int(urllib.parse.urlparse(comfy).port)
    gate_dir = sys.argv[sys.argv.index("--gate") + 1]; sys.path.insert(0, gate_dir); import gpu_gate as gate  # noqa: E402
    done = json.load(open(out)) if os.path.exists(out) else {}
    pngs = {}
    os.makedirs(jpg_dir, exist_ok=True); os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    key = "sampling-lab-pool51:sdxl"; peak_decl = gate.expected(key, SDXL_PEAK_GIB); watch = gate.FloorWatch()
    while True:
        rid, why = gate.acquire("sampling-lab-pool51", key, peak_decl, port=port)
        if rid: break
        print(time.strftime("%H:%M:%S"), "gate waits:", why, flush=True); time.sleep(20)
    measured = 0.0
    try:
        for r in rows:
            if done.get(r["id"], {}).get("status") == "rendered":
                continue
            g = graph(r, info); t0 = time.time(); pk = [0.0]; stop = [False]; pid_gpu = gate.PROBE.pid_of_port(port)
            def sample():
                while not stop[0]:
                    try:
                        o = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5).stdout
                        pk[0] = max(pk[0], sum(int(m) for p, m in (l.split(",")[:2] for l in o.splitlines() if "," in l) if p.strip() == str(pid_gpu)) / 1024)
                    except Exception: pass
                    time.sleep(0.25)
            th = threading.Thread(target=sample, daemon=True); th.start()
            res = {"status": "failed"}
            try:
                pid = req(comfy + "/prompt", {"prompt": g, "client_id": "sampling-lab-" + uuid.uuid4().hex[:8]})["prompt_id"]
                while time.time() - t0 < 900:
                    if watch.tripped():
                        req(comfy + "/interrupt", {}); res = {"status": "failed", "error": "stopped: the card went under the 4 GiB floor"}; break
                    time.sleep(1.0); h = req(comfy + "/history/" + pid)
                    if pid not in h: continue
                    st = h[pid].get("status", {})
                    if st.get("status_str") == "error":
                        msg = next((m[1] for m in st.get("messages", []) if m[0] == "execution_error"), {})
                        res = {"status": "failed", "error": f"{msg.get('node_type')}: {str(msg.get('exception_message'))[:300]}"}; break
                    im = [i for o in h[pid]["outputs"].values() for i in o.get("images", [])][0]
                    png = urllib.request.urlopen(comfy + "/view?" + urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"], "type": im["type"]}), timeout=60).read()
                    base_id = next(x["id"] for x in rows if x["set"] == r["set"] and x["baseline"])
                    m, pic = metrics(png, pngs.get(base_id) if not r["baseline"] else None)
                    pngs[r["id"]] = png; open(os.path.join(os.path.dirname(out), r["id"] + ".png"), "wb").write(png)
                    pic.thumbnail((768, 768)); pic.save(os.path.join(jpg_dir, r["id"] + ".jpg"), quality=86)
                    res = {"status": "rendered", "seconds": round(time.time() - t0, 1), "sha256": hashlib.sha256(png).hexdigest()[:16], **m}
                    if r["baseline"]: res["diff_to_base"] = 0.0
                    break
                else:
                    res = {"status": "failed", "error": "timed out after 900 s"}
            except Exception as e:  # noqa: BLE001
                res = {"status": "failed", "error": f"{type(e).__name__}: {str(e)[:300]}"}
            stop[0] = True; th.join(2)
            res["peak_gib"] = round(pk[0], 2); measured = max(measured, pk[0])
            done[r["id"]] = {**r, **res, "graph": g, "when": time.strftime("%Y-%m-%d %H:%M:%S")}
            json.dump(done, open(out, "w"), indent=1)
            print(time.strftime("%H:%M:%S"), r["id"], res["status"], res.get("seconds"), res.get("peak_gib"), res.get("diff_to_base"), res.get("error", ""), flush=True)
            if "floor" in res.get("error", ""): break
    finally:
        gate.release(rid)
        if measured: gate.record_peak(key, measured)
        try:
            q = req(comfy + "/queue")
            if not q.get("queue_running") and not q.get("queue_pending"): req(comfy + "/free", {"unload_models": True, "free_memory": True})
        except Exception: pass
    print("done", sum(1 for d in done.values() if d["status"] == "rendered"), "of", len(rows))


if __name__ == "__main__":
    main()
