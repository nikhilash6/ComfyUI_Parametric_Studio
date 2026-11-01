#!/usr/bin/env python3
"""The Sampling Lab proof sweep: fixed seed and prompt, one change at a time, on ComfyUI core nodes only.

One render at a time on the box's shared GPU, with a lock file that pauses the family rotation. The lock always goes, even on failure.
Usage: sampling_lab_renders.py <pause file> <out.json> [--plan-only]
"""
import json, os, sys, time, urllib.request, uuid

COMFY = "http://127.0.0.1:8200"; STUDIO = "http://127.0.0.1:8322"; TURN_LIMIT = 12 * 60; MIN_FREE_MIB = 4096
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "studio"))
from sampling_graph import MODELS, PROMPT, NEGATIVE, SEED, STEPS, build as graph  # noqa: E402

def plan():
    rows = []
    def add(set_, method, model, sampler="euler", scheduler="normal", cfg=7.0, patches=(), guider=None, note=""):
        rows.append({"id": f"{set_}-{method}", "set": set_, "method": method, "model": model, "sampler": sampler, "scheduler": scheduler, "cfg": cfg, "patches": list(patches), "guider": guider, "note": note})
    for s in ("euler", "euler_ancestral", "heun", "dpmpp_2m", "dpmpp_sde", "dpmpp_2m_sde", "dpmpp_3m_sde", "ddim", "lcm", "uni_pc", "res_multistep", "gradient_estimation", "er_sde", "seeds_2", "sa_solver"):
        add("sampler", s, "sd15", s, "karras")
    for s in ("normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform", "beta", "linear_quadratic", "kl_optimal"):
        add("scheduler", s, "sdxl", "dpmpp_2m", s)
    add("guidance", "cfg-7", "sdxl", note="Baseline for the other guidance renders.")
    add("guidance", "cfg-14", "sdxl", cfg=14.0, note="Deliberately too high, so the fixes below have something to fix.")
    add("guidance", "rescale-14", "sdxl", cfg=14.0, patches=[["RescaleCFG", {"multiplier": 0.7}]])
    add("guidance", "cfgnorm-14", "sdxl", cfg=14.0, patches=[["CFGNorm", {"strength": 1.0}]])
    add("guidance", "apg-14", "sdxl", cfg=14.0, patches=[["APG", {"eta": 1.0, "norm_threshold": 5.0, "momentum": 0.0}]])
    add("guidance", "tcfg-7", "sdxl", patches=[["TCFG", {}]])
    add("guidance", "cfgzerostar-7", "sdxl", patches=[["CFGZeroStar", {}]])
    add("guidance", "mahiro-7", "sdxl", patches=[["Mahiro", {}]])
    add("guidance", "pag-7", "sdxl", patches=[["PerturbedAttentionGuidance", {"scale": 3.0}]], note="One extra model call per step.")
    add("guidance", "sag-7", "sdxl", patches=[["SelfAttentionGuidance", {"scale": 0.5, "blur_sigma": 2.0}]], note="One extra model call per step.")
    add("guidance", "perpneg-7", "sdxl", guider="PerpNegGuider", note="Three conditionings per step: positive, negative, empty.")
    add("guidance", "cfgpp-1", "sdxl", "euler_cfg_pp", cfg=1.0, note="CFG++ works on a 0 to 1 style scale, so 7 is not the comparable value.")
    for s, sc in (("euler", "simple"), ("dpmpp_2m", "simple"), ("er_sde", "simple"), ("euler", "beta"), ("euler", "kl_optimal"), ("euler", "karras")):
        add("flow", f"{s}-{sc}", "sd35", s, sc, cfg=4.5)
    add("flow", "slg", "sd35", "euler", "simple", cfg=4.5, patches=[["SkipLayerGuidanceSD3", {"layers": "7, 8, 9", "scale": 3.0, "start_percent": 0.01, "end_percent": 0.15}]])
    add("flow", "cfgzerostar", "sd35", "euler", "simple", cfg=4.5, patches=[["CFGZeroStar", {}]])
    return rows

def get(url, timeout=20):
    with urllib.request.urlopen(url, timeout=timeout) as f: return json.load(f)
def post(url, body, timeout=30):
    q = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(q, timeout=timeout) as f:
        raw = f.read(); return json.loads(raw) if raw else {}
def idle():
    q = get(COMFY + "/queue"); fam = get(STUDIO + "/api/families", 30)
    return not q["queue_running"] and not q["queue_pending"] and not any(f.get("up") for f in fam["families"])
def free_mib():
    import subprocess
    return int(subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], text=True).split()[0])
def take_lock(path):
    while True:
        try: os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)); return
        except FileExistsError: time.sleep(20)
def one(r):
    t = time.time(); res = post(COMFY + "/prompt", {"prompt": graph(r), "client_id": "sampling-lab-" + uuid.uuid4().hex[:8]}); pid = res["prompt_id"]
    while time.time() - t < 400:
        time.sleep(1.5); h = get(COMFY + "/history/" + pid)
        if pid in h:
            e = h[pid]; st = e.get("status", {})
            if st.get("status_str") == "error":
                msg = next((m[1] for m in st.get("messages", []) if m[0] == "execution_error"), {})
                return {"status": "failed", "error": f"{msg.get('node_type')}: {str(msg.get('exception_message'))[:200]}"}
            files = [i for o in e["outputs"].values() for i in o.get("images", [])]
            return {"status": "rendered", "file": files[0]["subfolder"] + "/" + files[0]["filename"], "seconds": round(time.time() - t, 1)}
    return {"status": "failed", "error": "timed out after 400 s"}

def main():
    pause, out = sys.argv[1:3]; rows = plan()
    if "--plan-only" in sys.argv: print(len(rows)); return
    done = json.load(open(out)) if os.path.exists(out) else {}
    while True:
        todo = [r for r in rows if done.get(r["id"], {}).get("status") != "rendered" and done.get(r["id"], {}).get("tries", 0) < 2]
        if not todo: break
        take_lock(pause)
        try:
            for _ in range(240):
                try:
                    if idle(): break
                except Exception as e: print("waiting:", e, flush=True)
                time.sleep(15)
            else: raise SystemExit("never idle")
            t0 = time.time()
            for r in todo:
                if time.time() - t0 > TURN_LIMIT: break
                try:
                    q = get(COMFY + "/queue")
                    if q["queue_running"] or q["queue_pending"]: print("someone else queued, ending this turn", flush=True); break
                except Exception: pass
                fm = free_mib()
                if fm < MIN_FREE_MIB and not done:          # the first queue moves Qwen to RAM; before that a low number only means Qwen is up
                    print("free MiB", fm, "(Qwen handoff frees it at queue time)", flush=True)
                res = one(r); res["tries"] = done.get(r["id"], {}).get("tries", 0) + 1; res["free_mib_after"] = free_mib()
                done[r["id"]] = {**r, **res}; json.dump(done, open(out, "w"), indent=1)
                print(r["id"], res.get("status"), res.get("seconds"), res.get("error", ""), res["free_mib_after"], flush=True)
                if res["free_mib_after"] < MIN_FREE_MIB: print("under the 4 GB floor, ending this turn", flush=True); break
            try: post(COMFY + "/free", {"unload_models": True, "free_memory": True})
            except Exception as e: print("free failed", e, flush=True)
        finally:
            try: os.remove(pause)
            except FileNotFoundError: pass
        if [r for r in rows if done.get(r["id"], {}).get("status") != "rendered" and done.get(r["id"], {}).get("tries", 0) < 2]: time.sleep(90)
    print("done", sum(1 for d in done.values() if d["status"] == "rendered"), "of", len(rows))

if __name__ == "__main__": main()
