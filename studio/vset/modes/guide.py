"""Mode A, guide passes: the shot's exact Blender depth or pose pass drives the video. H3 Fun Union 2.0 is the default because its weights are here; its source input is the pass itself, which it never sees because the regeneration mask
covers every pixel. Wan 2.2 Fun Control is the other engine: 81 frames at 16 fps with the first shaded still as its reference picture, and it needs its own weights (needs.py). A pose pass needs a cast.
LTX-2.5 Layout to Render is the third engine. Its card asks for a grey clay viewport clip, not a depth or edge pass, plus a first frame that sets the art direction and is never the grey frame itself, so it takes the clay pass and the first shaded still made photoreal by Qwen-Image 2.1 (or the shaded still as it is with keyframes = "raw"). Not yet run."""
from __future__ import annotations

from studio.vset import shot as SH
from studio.vset.modes import common
from studio.worldkit import steps as S

H3_TEMPLATE = "vset_h3_union_api.json"
WAN_TEMPLATE = "vset_wan22_funcontrol_api.json"
LTX_TEMPLATE = "vset_ltx25_layout_api.json"
STRENGTH = 1.0                    # the one strength measured in the earlier studio


def union_values(shot: dict, ctx: dict, *, source: str, control: str, prompt: str) -> dict:
    w, h = SH.size(shot)
    return {"source": source, "control": control, "prompt": prompt, "width": w, "height": h, "length": SH.frames(shot), "strength": STRENGTH}


def steps(shot: dict, *, library) -> list[S.Step]:
    ms = shot.get("mode_settings") or {}
    control, engine = ms.get("control", "depth"), ms.get("engine", "h3")
    prompt = common.video_prompt(shot, library=library)

    def h3(ctx):
        name = common.uploaded(ctx, "scene", control)
        return common.request(shot, ctx, H3_TEMPLATE, "Virtual Set guide (H3)", union_values(shot, ctx, source=name, control=name, prompt=prompt))

    def wan(ctx):
        w, h = SH.size(shot)
        return common.request(shot, ctx, WAN_TEMPLATE, "Virtual Set guide (Wan)", {"ref": common.uploaded(ctx, "scene", "first"), "control": common.uploaded(ctx, "scene", control), "prompt": prompt, "width": w, "height": h})

    if engine == "ltx":
        return ltx_steps(shot, ms, prompt, library=library)
    label = "Video (Wan Fun Control)" if engine == "wan" else "Video (H3 Fun Union)"
    return [S.Step("video", label, request=wan if engine == "wan" else h3, pick=S.pick_first(media_type=("video",)))]


def ltx_steps(shot: dict, ms: dict, prompt: str, *, library) -> list[S.Step]:
    from studio.vset.modes import keyframes as K
    raw = ms.get("keyframes", "qwen") == "raw"
    who = common.key_person(shot, library=library)

    def key(ctx):
        if raw:
            return None
        return common.request(shot, ctx, K.KEY_TEMPLATE, "Virtual Set first frame", {"image": common.uploaded(ctx, "scene", "first"), "prompt": K.KEY_PROMPT.format(who=who), "negative": K.KEY_NEGATIVE, "resolution": K.KEY_RESOLUTION})

    def video(ctx):
        w, h = SH.size(shot)
        first = common.uploaded(ctx, "key_first") if "key_first" in ctx["outputs"] else common.uploaded(ctx, "scene", "first")
        return common.request(shot, ctx, LTX_TEMPLATE, "Virtual Set layout to render (LTX-2.5)", {"layout": common.uploaded(ctx, "scene", "clay"), "first": first, "prompt": prompt, "width": w, "height": h, "length": SH.frames(shot)})

    return [S.Step("key_first", "First frame (Qwen edit)", request=key, pick=S.pick_first(media_type=("image",))),
            S.Step("video", "Video (LTX-2.5 Layout to Render)", request=video, pick=S.pick_first(media_type=("video",)))]
