"""Approved World Kit assets to build shots on (metas written directly; glbs are stand-ins unless given), a fake studio for the job flow, and an offline check of a filled graph against ComfyUI's node definitions."""
import json
import shutil
from pathlib import Path

from studio.vset import shot as SH
from studio.worldkit import library as L, rigmap

SUBSET = Path(__file__).with_name("data") / "object_info_subset.json"


def _approved(lib, meta, glb=None):
    meta.update(status="approved", files={"asset.glb": True})
    meta["build"]["state"] = "done"
    lib.create(meta)
    dest = lib.path(meta["id"], "asset.glb")
    if glb:
        shutil.copy(glb, dest)
    else:
        dest.write_bytes(b"glTF")
    return meta["id"]


def make_set(lib, *, place_glb=None, prop_glb=None, char_glb=None, slots=None, clips=None, character=False) -> dict:
    place = L.new_meta("place", "Fixture block", source={"kind": "brief", "brief": "a street"}, recipe={"kit": "street", "brief": "a quiet street", "look": {"preset": "day_clear"}})
    place["inspect"] = {"loaded": True, "lo": [-6, -6, 0], "hi": [6, 6, 3], "dims_m": [12, 12, 3], "height_m": 3, "colliders": 2}
    prop = L.new_meta("prop", "Bench", source={"kind": "text", "prompt": "bench"})
    prop["inspect"] = {"loaded": True, "dims_m": [1.8, 0.5, 0.8], "colliders": 1}
    ids = {"place": _approved(lib, place, place_glb), "prop": _approved(lib, prop, prop_glb)}
    if character:
        char = L.new_meta("character", "Ada 3D", source={"kind": "character", "character_id": "savedchar", "name": "Ada", "description": "tall, auburn hair"})
        char.update(rig={"bones": 23, "standard": "skintokens", "slots": slots or {s: f"bone_{i}" for i, s in enumerate(rigmap.SLOTS)}},
                    clips=clips or [{"name": "walk", "frames": 24, "fps": 24}, {"name": "idle", "frames": 48, "fps": 24}], inspect={"loaded": True, "height_m": 1.7, "dims_m": [0.6, 0.3, 1.7]})
        ids["char"] = _approved(lib, char, char_glb)
    return ids


def good_shot(ids, **kw) -> dict:
    """A shot with props and a place alone: no character."""
    fields = dict(set={"place": ids["place"], "props": [{"asset": ids["prop"], "pos": [1, 1, 0], "rot_deg": [0, 0, 30], "scale": 1.0}]}, cast=[], marks=[[0, 0], [0, -3]],
                  camera={"preset": "push_in", "params": {}}, format={"aspect": "16:9", "seconds": 5}, look={"preset": "golden_hour"}, mode="C", mode_settings={}, seed=4242,
                  prompt="the camera moves down the empty street past the bench", session_id="s1", name="Street move")
    fields.update(kw)
    return SH.new_shot(**fields)


def cast_of(ids, marks=None):
    return [{"asset": ids["char"], "clip": "walk", "marks": marks or [[0, 0], [0, -3]]}]


SCENE_OUTPUTS = {k: {"path": f"/o/{k}.{'png' if k in ('first', 'last') else 'mp4'}"} for k in ("depth", "pose", "edges", "shaded", "clay", "first", "last")}


class FakeStudio:
    """submit records the job request; wait answers with an output of the kind the graph saves, or the next scripted error for that template. to_input records what was uploaded, under a name that says what it was."""
    def __init__(self, fail=None):
        self.reqs, self.fail, self.uploads = [], {k: list(v) for k, v in (fail or {}).items()}, []

    def submit(self, req):
        self.reqs.append(req)
        return f"j{len(self.reqs)}"

    def wait(self, jid):
        req = self.reqs[int(jid[1:]) - 1]
        errs = self.fail.get(req["template"])
        if errs:
            return {"status": "failed", "error": errs.pop(0), "artifacts": []}
        image = req["template"] == "vset_keyframe_edit_api.json"
        return {"status": "done", "error": "", "artifacts": [{"path": f"/o/{jid}.{'png' if image else 'mp4'}", "media_type": "image" if image else "video"}]}

    def to_input(self, path, stem=""):
        self.uploads.append(str(path))
        return Path(path).name

    def seams(self):
        return {"submit": self.submit, "wait": self.wait, "to_input": self.to_input}


def fake_scene_step():
    from studio.worldkit import steps as S
    return S.Step("scene", "Blender passes", local=lambda ctx: {k: dict(v) for k, v in SCENE_OUTPUTS.items()})


def run_mode(shot, lib, studio=None):
    """The mode's job steps after a stand-in scene step, with no Blender and no QC."""
    from studio.vset import modes
    from studio.worldkit import steps as S
    st = studio or FakeStudio()
    state = S.run({}, [fake_scene_step(), *modes.steps(shot, library=lib)], ctx={"seed": shot["seed"], "to_input": st.to_input, "work": Path("/nonexistent")}, submit=st.submit, wait=st.wait, save=lambda s: None)
    return st, state


def load_object_info(path=SUBSET) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _options(spec):
    t = spec[0]
    if isinstance(t, list):
        return t
    return (spec[1] or {}).get("options") if len(spec) > 1 and isinstance(spec[1], dict) and t == "COMBO" else None


def graph_problems(graph: dict, oi: dict, *, uploads=()) -> list[str]:
    """What ComfyUI's own validation would refuse in a filled API-format graph: unknown nodes, missing required inputs, a link to a missing node or the wrong type, a value outside a list or a range.
    A value in `uploads` stands for a file the job uploads first, so it is not looked up in a LoadImage or LoadVideo list."""
    bad = []
    for nid, node in graph.items():
        ct = node.get("class_type")
        info = oi.get(ct)
        if info is None:
            bad.append(f"{nid}: no node {ct}")
            continue
        spec = {**(info["input"].get("required") or {}), **(info["input"].get("optional") or {})}
        given = node["inputs"]
        for k in info["input"].get("required") or {}:
            kinds = spec[k][0]
            dynamic = kinds in ("COMFY_AUTOGROW_V3", "COMFY_DYNAMICCOMBO_V3", "COMFY_MATCHTYPE_V3")
            if k not in given and not (dynamic and any(g.startswith(k + ".") for g in given)) and not (kinds == "COMFY_MATCHTYPE_V3"):
                bad.append(f"{nid} ({ct}): required input {k} is missing")
        for k, v in given.items():
            base = k.split(".")[0]
            s = spec.get(k) or spec.get(base)
            if s is None:
                bad.append(f"{nid} ({ct}): no input {k}")
                continue
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                src = graph.get(v[0])
                if src is None:
                    bad.append(f"{nid}.{k}: links to missing node {v[0]}")
                    continue
                out = (oi.get(src["class_type"]) or {}).get("output") or []
                want = s[0]
                if v[1] >= len(out):
                    bad.append(f"{nid}.{k}: {src['class_type']} has no output {v[1]}")
                elif isinstance(want, str) and not want.startswith("COMFY_") and want != "*" and out[v[1]] != "*" and not str(out[v[1]]).startswith("COMFY_") and want != out[v[1]] and want not in str(out[v[1]]).split(","):
                    bad.append(f"{nid}.{k}: wants {want}, gets {out[v[1]]} from {src['class_type']}")
                continue
            opts = _options(s)
            if opts is not None and base == k:
                if v not in opts and v not in uploads:
                    bad.append(f"{nid} ({ct}).{k}: {v!r} is not in its list")
                continue
            cfg = s[1] if len(s) > 1 and isinstance(s[1], dict) else {}
            if s[0] in ("INT", "FLOAT") and isinstance(v, (int, float)) and not isinstance(v, bool):
                if ("min" in cfg and v < cfg["min"]) or ("max" in cfg and v > cfg["max"]):
                    bad.append(f"{nid} ({ct}).{k}: {v} is outside {cfg.get('min')}..{cfg.get('max')}")
            elif s[0] in ("INT", "FLOAT") and not isinstance(v, (int, float)):
                bad.append(f"{nid} ({ct}).{k}: {v!r} is not a number")
            elif s[0] == "STRING" and "${" in str(v):
                bad.append(f"{nid} ({ct}).{k}: an unfilled placeholder {v!r}")
    return bad
