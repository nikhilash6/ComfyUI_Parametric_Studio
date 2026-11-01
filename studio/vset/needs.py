"""What each mode needs and whether this machine has it, from a real file check on every call (worldkit/capabilities.py: a marker file, a hash sidecar or a config is not a weight). The page shows these sentences as they stand."""
from __future__ import annotations

from studio.vset import shot as SH
from studio.worldkit import capabilities as C

H3_COMMON = ("h3_text", "h3_vae", "h3_audio_vae")
H3_CONTROL = ("h3_fl2va_nvfp4", "h3_union", *H3_COMMON)
H3_KEYS = ("h3_fl2va", "h3_turbo", *H3_COMMON)
LTX_LAYOUT = ("ltx25", "ltx25_text", "ltx25_vae", "ltx25_upscaler", "ltx25_layout")
ROUTES = {"A": H3_CONTROL, "A_wan": ("wan_fun_high", "wan_fun_low", "wan_lightx2v_high", "wan_lightx2v_low", "wan_text", "wan_vae"), "A_ltx": ("qwen21", "qwen21_text", "qwen21_vae", *LTX_LAYOUT), "A_ltx_raw": LTX_LAYOUT, "B": H3_CONTROL,
          "C": ("qwen21", "qwen21_text", "qwen21_vae", *H3_KEYS), "C_raw": H3_KEYS, "D": ("h3_ref2va", *H3_COMMON)}
#: ComfyUI nodes a route needs beyond core, each with the pack that provides it. ComfyUI is asked only when it answers.
LTX_NODE = ("LTXICLoRALoaderModelOnly", "ComfyUI-LTXVideo")
NODES = {"A": ("MiniMaxH3FunUnion2ApplyEXPT8", "comfyui-minimax-h3-audio-T8"), "B": ("MiniMaxH3FunUnion2ApplyEXPT8", "comfyui-minimax-h3-audio-T8"), "A_ltx": LTX_NODE, "A_ltx_raw": LTX_NODE}


def route_name(shot: dict) -> str:
    ms = shot.get("mode_settings") or {}
    if shot["mode"] == "A" and ms.get("engine", "h3") == "wan":
        return "A_wan"
    if shot["mode"] == "A" and ms.get("engine", "h3") == "ltx":
        return "A_ltx_raw" if ms.get("keyframes", "qwen") == "raw" else "A_ltx"
    if shot["mode"] == "C" and ms.get("keyframes", "qwen") == "raw":
        return "C_raw"
    return shot["mode"]


def _node_problem(name: str) -> str:
    want = NODES.get(name)
    if want is None:
        return ""
    from studio.worldkit import jobs
    try:
        S = jobs.server()
        if not S.comfy_up():
            return ""
        return "" if S.comfy(f"/object_info/{want[0]}", timeout=5) else f"ComfyUI has no {want[0]} node: the {want[1]} pack is not installed"
    except Exception:
        return ""


def route(name: str, root=None) -> dict:
    r = C.route_of(ROUTES[name], root)
    bad = _node_problem(name)
    return {**r, "ready": r["ready"] and not bad, "problems": [*r["problems"], *([bad] if bad else [])]}


def render_problems(shot: dict, root=None) -> list[str]:
    """Why this shot's video step cannot start now, in plain sentences. The passes need only Blender."""
    blender = C.blender_problem()
    return [*([blender] if blender else []), *route(route_name(shot), root)["problems"]]


def report(root=None) -> dict:
    return {"blender": C.blender_problem(), "comfyui": C.comfy_up(), "routes": {n: route(n, root) for n in ROUTES}, "characters_on": not _characters_off(), "wan_sizes": {k: list(v) for k, v in SH.WAN_SPEC["sizes"].items()}, "ltx_sizes": {k: list(v) for k, v in SH.LTX_SPEC["sizes"].items()}}


def _characters_off() -> str:
    from studio.worldkit import safety
    return safety.character_problem()
