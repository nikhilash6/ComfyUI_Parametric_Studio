"""Starts the studio on this runner with no GPU and no ComfyUI, then asks it for the pages' data. Fails if it does not come up or a page's data is missing."""
import json, os, subprocess, sys, time, urllib.request
env = {**os.environ, "STUDIO_PORT": "8399", "PYTHONUTF8": "1"}
p = subprocess.Popen([sys.executable, "-m", "studio.server"], env=env)
try:
    for _ in range(90):
        try: urllib.request.urlopen("http://127.0.0.1:8399/api/goals", timeout=5); break
        except Exception:
            if p.poll() is not None: sys.exit("the studio exited early")
            time.sleep(1)
    else: sys.exit("the studio did not answer within 90 s")
    for path in ("health", "goals", "graphs", "recipes", "processes", "family-graphs", "university", "atlas"):
        d = json.load(urllib.request.urlopen(f"http://127.0.0.1:8399/api/{path}", timeout=30)); assert d, path; print("ok", path, flush=True)
    html = urllib.request.urlopen("http://127.0.0.1:8399/", timeout=30).read(); assert b"importmap" in html
    print("the studio boots and serves its pages on", sys.platform)
finally:
    p.terminate()
