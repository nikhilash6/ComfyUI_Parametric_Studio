"""Mode B, restyle: H3 Fun Union 2.0 repaints the shot from the prompt and follows the exact Blender depth pass, so the layout and the camera move hold. The shaded render goes in as the source clip. The regeneration mask is solid white, so H3 sees
the source masked out: what steers this mode is the depth pass and the words, not the colours of the render. H3's control has no identity input."""
from __future__ import annotations

from studio.vset.modes import common, guide
from studio.worldkit import steps as S


def steps(shot: dict, *, library) -> list[S.Step]:
    prompt = common.video_prompt(shot, library=library)

    def video(ctx):
        return common.request(shot, ctx, guide.H3_TEMPLATE, "Virtual Set restyle (H3)", guide.union_values(shot, ctx, source=common.uploaded(ctx, "scene", "shaded"), control=common.uploaded(ctx, "scene", "depth"), prompt=prompt))

    return [S.Step("video", "Video (H3 depth restyle)", request=video, pick=S.pick_first(media_type=("video",)))]
