"""Mode D, motion copy: the shot's shaded render is the reference clip of H3 Ref2VA, so H3 copies its camera move and blocking. The reference picture is the first shaded still, which stands in for a saved character's sheet because a shot works with a place and props alone.
The rule learnt on H3 template shots in the earlier studio: the prompt STARTS with a plain description of the clip's opening shot (camera, place, subject), otherwise H3 opens on the reference picture. Not yet run on Blender renders."""
from __future__ import annotations

from studio.vset import shot as SH
from studio.vset.modes import common
from studio.worldkit import steps as S

TEMPLATE = "vset_h3_motion_api.json"
CAMERA_WORDS = {"push_in": "a slow push in toward", "orbit": "a slow orbit around", "walk_along": "a tracking shot moving alongside", "pov": "a first-person view of", "handheld": "a handheld shot of", "static": "a static shot of", "custom": "a moving camera on"}


def opening(shot: dict, *, library) -> str:
    cam = CAMERA_WORDS.get((shot.get("camera") or {}).get("preset", "custom"), "a moving camera on")
    what = common.who(shot, library=library)
    return f"The clip opens on {cam} {what + ' in ' if what else ''}{common.where(shot, library=library)}, framed exactly as in the reference video."


def steps(shot: dict, *, library) -> list[S.Step]:
    prompt = f"{opening(shot, library=library)} {common.video_prompt(shot, library=library)}"

    def video(ctx):
        w, h = SH.size(shot)
        return common.request(shot, ctx, TEMPLATE, "Virtual Set motion copy (H3)", {"template": common.uploaded(ctx, "scene", "shaded"), "image": common.uploaded(ctx, "scene", "first"), "prompt": prompt, "width": w, "height": h, "frames": SH.frames(shot)})

    return [S.Step("video", "Video (H3 copies the 3D shot)", request=video, pick=S.pick_first(media_type=("video",)))]
