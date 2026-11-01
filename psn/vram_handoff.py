"""Hand the GPU between a local vLLM server and ComfyUI: the LLM's weights move to RAM when a render is queued, and come back once ComfyUI has been idle.
Off unless PSN_VRAM_HANDOFF_LLM_URL is set, and that URL must be local. Requests sent to the LLM during a render wait in its queue and run after the wake.
vLLM needs --enable-sleep-mode and VLLM_SERVER_DEV_MODE=1. Level 1 only: level 2 discards the weights, and the wake then returned garbage when measured on 2026-10-31."""
import json, logging, os, threading, time, urllib.error, urllib.parse, urllib.request

log = logging.getLogger("psn.vram_handoff")
LOCAL = ("127.0.0.1", "localhost", "::1")


def llm_url(env=os.environ):
    url = env.get("PSN_VRAM_HANDOFF_LLM_URL", "").strip().rstrip("/")
    if not url: return ""
    if urllib.parse.urlparse(url).hostname not in LOCAL: raise ValueError("PSN_VRAM_HANDOFF_LLM_URL must be a local address")
    return url


def _post(url, timeout):
    urllib.request.urlopen(urllib.request.Request(url, data=b"", method="POST"), timeout=timeout).read()


def _sleeping(base):
    return bool(json.load(urllib.request.urlopen(base + "/is_sleeping", timeout=5)).get("is_sleeping"))


class Handoff:
    """asleep is True while this handoff is holding the LLM in RAM. tasks_remaining and free_vram are callables supplied by ComfyUI, so this file imports nothing from it."""

    def __init__(self, base, tasks_remaining, free_vram, idle_s=30.0, wait_s=90.0, poll_s=2.0, clock=time.monotonic):
        self.base, self.tasks_remaining, self.free_vram = base, tasks_remaining, free_vram
        self.idle_s, self.wait_s, self.poll_s, self.clock = idle_s, wait_s, poll_s, clock
        self.lock = threading.Lock()
        self.asleep = False
        self.idle_since = None

    def adopt(self):
        """If ComfyUI restarted while the LLM was asleep, take over waking it."""
        try:
            with self.lock:
                self.asleep = _sleeping(self.base)
                self.idle_since = None
        except (OSError, ValueError) as e:
            log.warning("LLM not reachable at startup: %s", e)

    def before_render(self):
        """Runs as a job is queued. In-flight LLM requests get wait_s to finish, then are aborted, because a render beside the awake LLM runs out of VRAM. Never raises: a down LLM must not stop a render."""
        with self.lock:
            self.idle_since = None
            if self.asleep: return
            try:
                if _sleeping(self.base):
                    self.asleep = True
                    return
                try:
                    _post(f"{self.base}/sleep?level=1&mode=wait", self.wait_s)
                except (TimeoutError, urllib.error.URLError) as e:
                    log.warning("LLM still busy after %ss (%s), aborting its requests for the render", self.wait_s, e)
                    _post(f"{self.base}/sleep?level=1&mode=abort", 60)
                self.asleep = True
                log.info("LLM moved to RAM for a render")
            except (OSError, ValueError) as e:
                log.warning("Could not move the LLM to RAM: %s", e)

    def tick(self):
        """One watcher step. Wakes the LLM once nothing has been queued or running for idle_s, after ComfyUI releases the VRAM."""
        with self.lock:
            if not self.asleep: return False
            if self.tasks_remaining() > 0:
                self.idle_since = None
                return False
            now = self.clock()
            if self.idle_since is None:
                self.idle_since = now
                return False
            if now - self.idle_since < self.idle_s: return False
            try:
                self.free_vram()
                _post(self.base + "/wake_up", 120)
                self.asleep = False
                self.idle_since = None
                log.info("LLM back on the GPU")
                return True
            except (OSError, ValueError) as e:
                log.warning("Could not wake the LLM, will retry: %s", e)
                return False

    def run(self):
        while True:
            time.sleep(self.poll_s)
            try:
                self.tick()
            except Exception:
                log.exception("handoff watcher step failed")


def install():
    """Register with a running ComfyUI. Does nothing when the setting is absent or ComfyUI isn't importable."""
    base = llm_url()
    if not base: return None
    try:
        import server
        import comfy.model_management as mm
    except ImportError:
        return None
    ps = server.PromptServer.instance

    def free_vram():
        mm.unload_all_models()
        mm.soft_empty_cache(True)

    h = Handoff(base, ps.prompt_queue.get_tasks_remaining, free_vram, idle_s=float(os.environ.get("PSN_VRAM_HANDOFF_IDLE_S", "30")))

    def on_prompt(json_data):
        h.before_render()
        return json_data

    ps.add_on_prompt_handler(on_prompt)
    h.adopt()
    threading.Thread(target=h.run, name="psn-vram-handoff", daemon=True).start()
    log.info("VRAM handoff active for %s", base)
    return h
