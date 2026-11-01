# CU-385 lab: a decision ladder in code. The facts in the table were read in ComfyUI v0.43.0 and in each pack's source, as text. No pack was run.
RUNGS = ["core does it", "core lacks a real part of it", "side effects you can't accept", "licence blocks your use"]
NEEDS = [
 {"need": "perturbed-attention guidance", "core": "PerturbedAttentionGuidance", "core_enough": True, "pack": "pamparamm/sd-perturbed-attention (MIT)", "adds": "per-block PAG, and methods core lacks, such as token perturbation", "bad": False, "lic": True},
 {"need": "token perturbation guidance", "core": None, "core_enough": False, "pack": "pamparamm/sd-perturbed-attention (MIT)", "adds": "tpg_nodes.py", "bad": False, "lic": True},
 {"need": "a step cache", "core": "EasyCache, LazyCache", "core_enough": True, "pack": "duckyshell/ComfyUI-MiniMaxH3-FirstBlockCache (MIT)", "adds": "a first-block check for one model family", "bad": False, "lic": True},
 {"need": "a labelled sweep grid with video", "core": "ImageGrid, ImageCompare", "core_enough": False, "pack": "embedding-shapes/ComfyUI-SweepGrid (MIT)", "adds": "sweep axes and video grids", "bad": False, "lic": True},
 {"need": "an idea from a pack that patches every job", "core": None, "core_enough": False, "pack": "a made-up example", "adds": "a good idea", "bad": True, "lic": True},
 {"need": "code from a pack with no licence", "core": None, "core_enough": False, "pack": "a made-up example", "adds": "a good function", "bad": False, "lic": False},
]
def decide(n):
    if n["core_enough"]: return "use core, and measure before looking further"
    if not n["lic"]: return "do not copy. Write your own from the idea"
    if n["bad"]: return "borrow the idea, not the pack"
    return "read it, test it in a sandbox, then decide"
for n in NEEDS:
    print(f"{n['need']:44s} core: {str(n['core']):28s}\n  -> {decide(n)}")
assert decide(NEEDS[0]).startswith("use core") and decide(NEEDS[3]).startswith("read it") and decide(NEEDS[5]).startswith("do not copy")
print("\ncost of a dependency: packs multiply what must keep working")
for k in (1, 5, 20):
    print(f"  {k:2d} packs, each with a 2% chance of breaking per ComfyUI update: {1 - 0.98 ** k:5.1%} chance something breaks. The 2% is an example, not a measurement.")
assert abs((1 - 0.98 ** 20) - 0.3324) < 0.001
print("\nwhat speed claims need before they count")
for c in ("whose number is it", "same graph and seed with and without", "first run left out", "picture compared, not just the clock"): print(f"  {c}")
