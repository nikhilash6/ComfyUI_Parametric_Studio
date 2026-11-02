"""Mode C, keyframes: the 3D set composes the start and end stills (the shot's first and last shaded frames). By default Qwen-Image 2.1 turns each into a photograph, then H3 first -> last frame fills in between. With the setting keyframes = "raw" the
Blender stills go straight to H3, which needs no image model. A reroll redoes only the video: the keyframes are kept."""
from __future__ import annotations

from studio import goals
from studio.vset.modes import common
from studio.worldkit import steps as S

KEY_TEMPLATE = "vset_keyframe_edit_api.json"
VIDEO_TEMPLATE = "h3_fl2v_api.json"
KEY_PROMPT = "Turn this 3D render into a real photograph. Keep the exact framing, camera angle, set layout and light direction. Real materials on every surface.{who}"
KEY_NEGATIVE = "cartoon, 3D render, CGI, blurry, watermark, text, mannequin, bare skin"
KEY_RESOLUTION = 1024
MEGAPIXELS = goals.H3_QUALITY["high"]


def steps(shot: dict, *, library) -> list[S.Step]:
    fmt = shot["format"]
    raw = (shot.get("mode_settings") or {}).get("keyframes", "qwen") == "raw"
    key_prompt = KEY_PROMPT.format(who=common.key_person(shot, library=library))
    prompt = common.video_prompt(shot, library=library)

    def key(which):
        def req(ctx):
            if raw:
                return None
            return common.request(shot, ctx, KEY_TEMPLATE, f"Virtual Set {which} keyframe", {"image": common.uploaded(ctx, "scene", which), "prompt": key_prompt, "negative": KEY_NEGATIVE, "resolution": KEY_RESOLUTION})
        return req

    def still(ctx, which):
        step = f"key_{which}"
        return common.uploaded(ctx, step) if step in ctx["outputs"] else common.uploaded(ctx, "scene", which)

    def video(ctx):
        return common.request(shot, ctx, VIDEO_TEMPLATE, "Virtual Set first to last (H3)", {"image": still(ctx, "first"), "last_image": still(ctx, "last"), "prompt": prompt, "aspect": goals.H3_ASPECTS[fmt["aspect"]],
                                                                                            "megapixels": MEGAPIXELS, "seconds": float(fmt["seconds"]), "turbo": True})

    return [S.Step("key_first", "First keyframe (Qwen edit)", request=key("first"), pick=S.pick_first(media_type=("image",))),
            S.Step("key_last", "Last keyframe (Qwen edit)", request=key("last"), pick=S.pick_first(media_type=("image",))),
            S.Step("video", "Video (H3 first to last)", request=video, pick=S.pick_first(media_type=("video",)))]
