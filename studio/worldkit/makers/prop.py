"""Prop / vehicle maker. From a studio mesh: straight to the Blender cleanup. From a picture or a text prompt: (text -> the Image goal) -> a background cut-out (core BiRefNet, unless the
picture already has one) -> a mesh (SAM 3D Objects, or a family template that can do the job). Text to image is FLUX.2 Klein, or Krea 2 Turbo when Klein is not here -> Blender cleanup (CPU): real-world size (the longest side, from the recipe or a size hint in the
name), pivot at the bottom centre, a box collider. A step whose model is not on this machine stops with a sentence saying which one."""
from __future__ import annotations

import re
from pathlib import Path

from psn import paths
from studio.worldkit import capabilities as C
from studio.worldkit import jobs
from studio.worldkit import library as L
from studio.worldkit import safety
from studio.worldkit import steps as S
from studio.worldkit import tools

IMAGE_GOAL = "image"
KREA_GRAPH = "worldkit_krea2_t2i_api.json"
CUTOUT_GRAPH = "worldkit_cutout_api.json"
BUILD_STEP = "cleanup"
TEXT_TO_IMAGE = ("{text}, a single object, the whole object in view, centred, plain light grey studio background, "
                 "soft even light, product photo")
#: The longest side in metres of common props (typical real sizes; the user can type any size_m).
SIZE_HINTS = {"car": 4.5, "van": 5.0, "truck": 7.0, "bus": 12.0, "bike": 1.8, "bicycle": 1.8, "motorbike": 2.1,
              "motorcycle": 2.1, "scooter": 1.8, "boat": 6.0, "chair": 0.9, "armchair": 0.95, "stool": 0.75,
              "table": 1.2, "desk": 1.4, "sofa": 2.0, "couch": 2.0, "bed": 2.0, "lamp": 1.6, "bench": 1.8,
              "cup": 0.1, "mug": 0.1, "bottle": 0.3, "phone": 0.15, "laptop": 0.35, "bag": 0.45, "plant": 0.8,
              "tree": 5.0, "umbrella": 2.2, "sign": 2.0}
DEFAULT_SIZE_M = 1.0


def default_size(name: str) -> float:
    for w in re.findall(r"[a-z]+", str(name or "").lower()):
        if w in SIZE_HINTS:
            return SIZE_HINTS[w]
        if w.endswith("s") and w[:-1] in SIZE_HINTS:
            return SIZE_HINTS[w[:-1]]
    return DEFAULT_SIZE_M


def recipe(given: dict | None, name: str) -> tuple[dict, list[str]]:
    given = dict(given or {})
    as_prop_of = given.pop("as_prop_of", None)
    r = {"size_m": default_size(name), **given}
    bad = []
    lo, hi = L.PROP_SIZE_M
    s = r["size_m"]
    if isinstance(s, bool) or not isinstance(s, (int, float)) or not lo <= s <= hi:
        bad.append(f"size_m is {lo}-{hi} m (the object's longest side)")
    if as_prop_of is not None:
        if isinstance(as_prop_of, str) and as_prop_of.strip():
            r["as_prop_of"] = as_prop_of.strip()
        else:
            bad.append("as_prop_of is the id of the character used as a prop")
    return r, bad


def source_problem(source: dict) -> str:
    kind = (source or {}).get("kind")
    if kind == "text":
        return "" if str(source.get("prompt") or "").strip() else "describe the object"
    if kind == "image":
        img = source.get("image")
        return "" if isinstance(img, str) and img.strip() else "drop or pick an image of the object"
    if kind == "mesh":
        m = source.get("mesh")
        return "" if isinstance(m, str) and m.strip() else "mesh is a .glb from the studio's outputs"
    return "a prop is made from an image, a text prompt or a mesh"


def _under(root, rel, suffixes) -> Path:
    """A name the browser sent, as a file inside `root`, or a refusal."""
    base = Path(root).resolve()
    p = (base / str(rel)).resolve()
    if base not in p.parents or p.suffix.lower() not in suffixes or not p.is_file():
        raise S.StepError(f"{Path(str(rel)).name} is not a usable file in the studio's folders")
    return p


def picture_path(name: str) -> Path:
    """An uploaded picture lives in ComfyUI's input folder (the name /api/upload gave back)."""
    return _under(paths.comfy_input(True), name, (".png", ".jpg", ".jpeg", ".webp"))


def mesh_path(rel: str, library=None) -> Path:
    """A studio 3D result is a .glb under the output folder (as /api/models3d lists it), or inside this library."""
    if library is not None and str(rel).startswith(("/", "lib:")):
        return _under(library.root, str(rel).removeprefix("lib:").lstrip("/"), (".glb", ".obj", ".fbx"))
    return _under(paths.output_dir(True), rel, (".glb", ".obj", ".fbx"))


def _has_alpha(path: Path) -> bool:
    from PIL import Image
    with Image.open(path) as im:
        return im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 250


def steps(meta: dict) -> list[S.Step]:
    src = meta["source"]
    bad = source_problem(src)
    if bad:
        raise ValueError(bad)

    def image(ctx):
        if src["kind"] != "text":
            return None
        route = ctx["text_route"]() if ctx.get("text_route") else C.text_image_route()
        prompt = TEXT_TO_IMAGE.format(text=src["prompt"].strip())
        if route == "krea2":
            bad = safety.text_problem(prompt)
            if bad:
                raise S.StepError(bad)
            return jobs.graph(KREA_GRAPH, {"prompt": prompt, "width": 1024, "height": 1024, "seed": int(ctx.get("seed") or 42), "prefix": f"worldkit/prop_{meta['id']}"}, f"World Kit picture: {meta['name']}")
        tools.require("image")
        return jobs.goal(IMAGE_GOAL, prompt, {"aspect": "1:1", "mode": "fast"})

    def _picture(ctx) -> Path:
        return Path(S.out_path(ctx, "image")) if "image" in ctx["outputs"] else picture_path(src["image"])

    def cutout(ctx):
        """A mesh model has to be told which object to build, so the object is cut out first and its alpha is the mask. A picture with its own cut-out and a mesh skip this."""
        if src["kind"] == "mesh" or _has_alpha(_picture(ctx)):
            return None
        tools.require("cutout")
        name = (ctx.get("to_input") or jobs.to_input)(_picture(ctx))
        return jobs.graph(CUTOUT_GRAPH, {"image": name}, f"World Kit cut-out: {meta['name']}")

    def mesh(ctx):
        if src["kind"] == "mesh":
            return None
        route = ctx["mesh_route"]() if ctx.get("mesh_route") else C.mesh_route()
        if not route:
            raise S.StepError(C.route("prop_image")["problems"][-1])
        pic = S.out_path(ctx, "cutout") if "cutout" in ctx["outputs"] else str(_picture(ctx))
        work = ctx["work"] / "mesh"
        if route == "sam3d_objects":
            path = (ctx.get("sam3d") or tools.sam3d_objects)(pic, work)
        else:
            fam, tid = C.NEEDS[route]["family"]
            res = ctx["wait"](ctx["submit"](jobs.family(fam, tid, image=pic)))
            if res.get("status") != "done":
                raise S.StepError(res.get("error") or f"{C.NEEDS[route]['label']} ended {res.get('status')}")
            path = S.pick_first(suffix=(".glb",))(res.get("artifacts") or [], ctx)["main"]["path"]
        return {"main": {"path": str(path), "route": route}}

    return [S.Step("image", "Image (text to image)", request=image, pick=S.pick_first(media_type=("image",))),
            S.Step("cutout", "Cut-out (BiRefNet)", request=cutout, pick=S.pick_first(media_type=("image",))),
            S.Step("mesh", "Mesh (picture to 3D)", local=mesh),
            S.Step(BUILD_STEP, "Cleanup (Blender)", local=cleanup)]


def cleanup(ctx: dict, *, blender=None) -> dict:
    """One static object at its real size, pivot at the bottom centre, a box collider (Blender, CPU only)."""
    from studio.worldkit import blender as B
    bl = blender or ctx.get("blender") or B
    meta, lib = ctx["asset"], ctx["library"]
    r, _ = recipe(meta.get("recipe"), meta["name"])
    model = S.out_path(ctx, "mesh") if "mesh" in ctx["outputs"] else str(mesh_path(meta["source"]["mesh"], lib))
    work = ctx["work"] / BUILD_STEP
    out = work / "prop.glb"
    work.mkdir(parents=True, exist_ok=True)
    with B.cpu_only():
        res = bl.run("wk_cleanup.py", {"model": model, "size_m": r["size_m"], "name": meta["name"], "out": str(out)},
                     work=work, name="cleanup", timeout=600, gpu=False)
    ins = dict(res["inspect"])
    ins.pop("bones", None)
    return {"main": {"path": str(out), "inspect": ins, "source_mesh": Path(model).name}}


__all__ = ["steps", "recipe", "default_size", "source_problem", "cleanup"]
