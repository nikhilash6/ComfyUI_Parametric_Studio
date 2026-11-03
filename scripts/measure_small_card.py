"""The small-card table, measured: three heavy goals on a ComfyUI that is held to a smaller card with --reserve-vram, pass or out-of-memory and time for each, into studio/smallcard_measured.json.
The ComfyUI to measure must be one you started for this (a family instance with --reserve-vram set so that about CAP GB is left to it), never the main one: this script only queues graphs and reads answers.
On a shared card other programs count too, so the free memory at the start of every run is recorded beside it.
  python scripts/measure_small_card.py run --cap 24 --comfy http://127.0.0.1:PORT [--reserve 72] [--goals vfx_ltx,recast,reshoot]
  python scripts/measure_small_card.py table           the README table, from the JSON
Inputs are the studio's own AI-generated showcase clips and an invented person, so no real person is used."""
import argparse, json, os, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO))
OUT = REPO / "studio" / "smallcard_measured.json"; SHOW = REPO / "studio" / "web" / "showcase"
FORBIDDEN_PORTS = {8200, 8322}
#: what each goal is asked; ${clip} and ${person} are uploaded first. Prompts describe invented, clothed adults.
JOBS = {
    "vfx_ltx": {"goal": "vfx_ltx", "video": "${clip}", "options": {"effect": "water", "quality": "standard", "seconds": 5}, "seed": 7, "prompt": ""},
    "recast": {"goal": "recast", "video": "${clip}", "image": "${person}", "options": {"quality": "draft", "seconds": 5}, "seed": 7, "prompt": "A person in a black space suit and helmet doing the same movement as the person in the clip."},
    "reshoot": {"goal": "reshoot", "video": "${clip}", "options": {"quality": "draft", "seconds": 5}, "seed": 7, "prompt": "The same scene, the camera slowly orbits to the right."},
}
INPUTS = {"clip": SHOW / "vfx_same_src.mp4", "person": SHOW / "s_portrait.webp"}
OOM = re.compile(r"out of memory|OutOfMemory|CUDA error: out of memory|Allocation on device|torch\.OutOfMemoryError", re.I)


def classify(status, error=""):
    """pass, oom or error, from how the run ended."""
    if status == "done": return "pass"
    return "oom" if OOM.search(error or "") else "error"


def free_gib(run=subprocess.run):
    try: return round(int(run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits", "-i", "0"], capture_output=True, text=True, timeout=10).stdout.strip()) / 1024, 1)
    except Exception: return None


class Comfy:
    def __init__(self, url): self.url = url.rstrip("/")

    def upload(self, path):
        p = Path(path); b = uuid.uuid4().hex
        body = f'--{b}\r\nContent-Disposition: form-data; name="image"; filename="{p.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + p.read_bytes() + f'\r\n--{b}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{b}--\r\n'.encode()
        with urllib.request.urlopen(urllib.request.Request(self.url + "/upload/image", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=300) as r: return json.loads(r.read())["name"]

    def run(self, graph, timeout=5400):
        """-> (status, error). Never raises for a failed render: that is a measurement."""
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url + "/prompt", json.dumps({"prompt": graph, "client_id": "smallcard"}).encode(), {"Content-Type": "application/json"}), timeout=120) as r: pid = json.loads(r.read())["prompt_id"]
        except urllib.error.HTTPError as e: return "error", "refused: " + e.read().decode(errors="replace")[:400]
        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(3)
            with urllib.request.urlopen(f"{self.url}/history/{pid}", timeout=60) as r: h = json.load(r).get(pid)
            st = (h or {}).get("status") or {}
            if st.get("status_str") == "error": return "error", next((i.get("exception_message", "") for k, i in st.get("messages", []) if k == "execution_error"), "")[:600]
            if st.get("completed"): return "done", ""
        self.free(); return "error", f"timed out after {timeout} s"

    def free(self):
        try: urllib.request.urlopen(urllib.request.Request(self.url + "/free", json.dumps({"unload_models": True, "free_memory": True}).encode(), {"Content-Type": "application/json"}), timeout=60)
        except Exception: pass


def body_for(job, names):
    return json.loads(json.dumps(JOBS[job]).replace("${clip}", names["clip"]).replace("${person}", names["person"]))


def graph_for(body):
    from studio import server as S
    g, vals, opts = S._graph(body["goal"], body, body.get("image"), running=True); return g


def measure(cap, comfy, goals, reserve=None, used=None, free=free_gib, graph=graph_for, now=time.time, hold=None):
    """Run each goal once on this capped ComfyUI. used() reads the instance's VRAM now and is polled through the run for its peak; hold(goal) is a context that holds the GPU gate.
    -> {cap_gb, reserve_vram_gb, measured, runs: [{goal, result, seconds, peak_gib, free_at_start_gib, error}]}"""
    import contextlib, threading
    names = {k: comfy.upload(p) for k, p in INPUTS.items()}; rows = []
    for goal in goals:
        with (hold(goal) if hold else contextlib.nullcontext()):
            comfy.free(); f0 = free(); t0 = now(); top = [0.0]; stop = threading.Event()
            def poll():
                while used and not stop.is_set(): top[0] = max(top[0], used() or 0.0); time.sleep(1)
            th = threading.Thread(target=poll, daemon=True); th.start()
            try: status, err = comfy.run(graph(body_for(goal, names)))
            finally: stop.set(); th.join(5)
        rows.append({"goal": goal, "result": classify(status, err), "seconds": round(now() - t0, 1), "peak_gib": round(top[0], 1) if used else None, "free_at_start_gib": f0, "error": err[:300] if err else ""})
    return {"cap_gb": cap, "reserve_vram_gb": reserve, "measured": time.strftime("%Y-%m-%d %H:%M"), "runs": rows}


def save(entry, path=OUT):
    d = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"about": "Three heavy goals on a ComfyUI held to a smaller card with --reserve-vram. Pass means the render finished; oom means it ran out of memory. Free memory at each start is recorded because the card was shared.", "caps": {}}
    d["caps"][str(entry["cap_gb"])] = entry; path.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8"); return d


def table(d):
    """The README table: one row per goal, one column per cap, from what was measured only."""
    caps = sorted(d.get("caps", {}), key=float)
    if not caps: return "Not measured yet."
    goals = list(dict.fromkeys(r["goal"] for c in caps for r in d["caps"][c]["runs"]))
    cell = lambda r: "not run" if not r else ("pass, " + (f"{r['seconds'] / 60:.1f} min" if r["seconds"] >= 90 else f"{r['seconds']:.0f} s")) if r["result"] == "pass" else "out of memory" if r["result"] == "oom" else "failed"
    lines = ["| Goal | " + " | ".join(f"{c} GB" for c in caps) + " |", "|---|" + "---|" * len(caps)]
    for g in goals: lines.append(f"| {g} | " + " | ".join(cell(next((r for r in d["caps"][c]["runs"] if r["goal"] == g), None)) for c in caps) + " |")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0]); sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--cap", type=float, required=True, help="about how many GB the instance may use"); r.add_argument("--comfy", required=True)
    r.add_argument("--reserve", type=float, help="the --reserve-vram the instance was started with"); r.add_argument("--goals", default="vfx_ltx,recast,reshoot")
    sub.add_parser("table")
    a = p.parse_args(argv)
    if a.cmd == "table": print(table(json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {})); return 0
    port = urllib.parse.urlparse(a.comfy).port
    if port in FORBIDDEN_PORTS: raise SystemExit("never the main ComfyUI or the released studio: start a family instance with --reserve-vram for this")
    goals = [g for g in a.goals.split(",") if g]
    unknown = [g for g in goals if g not in JOBS]
    if unknown: raise SystemExit("unknown goals: " + ", ".join(unknown))
    if not os.environ.get("GPU_GATE_TOOLS"): raise SystemExit("set GPU_GATE_TOOLS to the folder holding gpu_gate.py: every run waits its turn at the shared GPU gate")
    sys.path.insert(0, os.environ["GPU_GATE_TOOLS"]); import contextlib, gpu_gate as G

    @contextlib.contextmanager
    def hold(goal):
        rid = None
        while rid is None:
            rid, why = G.acquire("smallcard", f"{goal}@{a.cap:g}GB", a.cap, a.cap >= G.HEAVY_GIB, port=port)
            if rid is None: print("gate:", why, flush=True); time.sleep(20)
        try: yield
        finally: G.release(rid)
    entry = measure(a.cap, Comfy(a.comfy), goals, a.reserve, lambda: G.PROBE.used_by_port(port), hold=hold); save(entry); print(json.dumps(entry, indent=1)); return 0


if __name__ == "__main__": sys.exit(main())
