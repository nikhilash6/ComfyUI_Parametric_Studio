"""Write one ready-to-run ComfyUI API graph per LTX-2.5 VFX effect to workflows/vfx/, from the same code the studio sends.
workflows/ltx25_vfx_api.json is the template with ${placeholders}; these are it filled with the studio's defaults, so a graph loads
and runs in ComfyUI as it is: put your clip in ComfyUI's input folder as input_video.mp4. Model names are the plain file names the
installer writes (models/<folder>/<file>), not this box's sub-folders. Needs the Parametric Studio node pack for PSN_FPSResampler.
  python scripts/export_vfx_workflows.py          write the files
  python scripts/export_vfx_workflows.py --check  exit 1 if a file is out of date"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from studio import goals as Go
from studio.graph_template import fill

OUT = os.path.join(ROOT, "workflows", "vfx")
CLIP = {"width": 1280, "height": 720, "duration": 5.2}     # a 16:9 clip of at least 5 seconds, so the graph is the studio's default 960x544, 121 frames
MODEL_INPUTS = ("unet_name", "lora_name", "clip_name", "vae_name")
TITLES = {"src": "Your clip: ComfyUI input/input_video.mp4", "srcA": "First clip: ComfyUI input/input_video.mp4", "srcB": "Second clip: ComfyUI input/input_video_2.mp4", "pos": "Prompt", "lora": "LTX-2.5 IC-LoRA for this effect", "noise": "Seed", "save": "Save the result"}


def graph_for(effect):
    """effect: a VFX_EFFECTS key, or "transition" (input_video.mp4 flows into input_video_2.mp4)."""
    real = Go.probe_input; Go.probe_input = lambda name: dict(CLIP)
    goal, tpl = ("ltx_transition", "ltx25_transition_api.json") if effect == "transition" else ("vfx_ltx", "ltx25_vfx_api.json")
    try: v, o = Go.values_for(goal, {"video": "input_video.mp4", "video_b": "input_video_2.mp4", "seed": 42, "options": {} if effect == "transition" else {"effect": effect}})
    finally: Go.probe_input = real
    g = fill(json.load(open(os.path.join(Go.WF, tpl))), v)
    for nid, n in g.items():
        for k in MODEL_INPUTS:
            if isinstance(n["inputs"].get(k), str): n["inputs"][k] = os.path.basename(n["inputs"][k])
        if nid in TITLES: n["_meta"] = {"title": TITLES[nid]}
    g["save"]["inputs"]["filename_prefix"] = f"vfx/{effect}"
    return g


EFFECTS = (*Go.VFX_EFFECTS, "transition")


def main(check=False):
    os.makedirs(OUT, exist_ok=True); stale = []
    for effect in EFFECTS:
        p, text = os.path.join(OUT, f"ltx25_vfx_{effect}.json"), json.dumps(graph_for(effect), indent=1) + "\n"
        if check:
            if not os.path.exists(p) or open(p).read() != text: stale.append(p)
        else: open(p, "w").write(text); print("wrote", os.path.relpath(p, ROOT))
    if stale: print("out of date:", *stale, sep="\n  "); sys.exit(1)


if __name__ == "__main__": main("--check" in sys.argv)
