#!/usr/bin/env python3
"""The Pool 51 catalogue: the node packs the studio installs beside ComfyUI, sorted into the 51 sections of the pack review, into studio/pool51_catalogue.json.
Each pack: repository, pinned commit (checked file by file against the copy that was reviewed and load-tested), sections, licence as stated, the node ids it added on a
test ComfyUI, what it adds, pip packages it needs, and the small patch applied over that commit if there is one (copied to studio/pool51_patches/).
install.py --packs pool51 installs exactly this list. Stays out: the reviewer's own packs, notes on where things live on the build machine, and any sentence naming a
private folder, port or person. Fails if a folder path survives.
Usage: build_pool51_catalogue.py SOURCE_JSON PATCH_DIR"""
import json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "studio" / "pool51_catalogue.json"; PATCHES = ROOT / "studio" / "pool51_patches"
SECTIONS = {
    "01": "3D, mesh and camera", "02": "Audio and voice utilities", "03": "Audio-reactive, keyframing and animation curves", "04": "Batch, list and data handling",
    "05": "Cloud, API and remote connectors", "06": "Computer vision and classical image analysis", "07": "Conditioning ops and regional prompts", "08": "Conditioning, text encode and CLIP",
    "09": "Config, settings and pipe objects", "10": "ControlNet preprocessors", "11": "Cryptography, hashing and encoding", "12": "Data science: tables, plots and stats",
    "13": "Data structures: dict, list, JSON, bytes", "14": "Debug, monitoring and workflow helpers", "15": "External app bridges", "16": "Face and person tools",
    "17": "Flow control, loops and routing", "18": "Games, simulations and toys", "19": "Image colour, tone and grading", "20": "Image filters and effects",
    "21": "Image resize, crop, pad and composite", "22": "LLM prompt writing and captioning", "23": "LLM agents and frameworks", "24": "Latent ops",
    "25": "LoRA and adapter tools", "26": "Loaders: images, files, datasets", "27": "Masks and segmentation", "28": "Math, logic and control flow",
    "29": "Model loaders and checkpoint tools", "30": "Model patches and attention", "31": "Model utilities: inspect, extract, merge", "32": "Motion capture, rigging and retargeting",
    "33": "Other", "34": "Prompt builders, wildcards and composers", "35": "PyTorch and training toolkits", "36": "Sampling: guidance and CFG",
    "37": "Sampling: noise", "38": "Sampling: samplers", "39": "Sampling: schedulers and sigmas", "40": "Save, preview and export",
    "41": "Science and bioinformatics", "42": "Scripting and programmatic logic", "43": "Storyboard and shot planning", "44": "Text and string utilities",
    "45": "UI widgets and workflow organisation", "46": "Upscale and restore", "47": "VAE encode and decode", "48": "Vector graphics, shaders and procedural art",
    "49": "Video frames, timing and assembly", "50": "Documents, OCR and search", "51": "XY plots, grids and comparisons"}
EMPTY_WHY = {"05": "Left empty on purpose: the studio runs open weights on your own machine, and the packs here call paid or remote services.",
             "15": "Nothing passed review: the bridges need apps or SDKs from other platforms, or write outside their own folder.",
             "18": "Toys only; nothing a studio feature uses.", "23": "Nothing passed review: cloud-first, or they start or unload servers on their own.",
             "32": "Nothing passed review: the candidates install software or pip packages when they load, or clash with nodes already installed.",
             "41": "Nothing passed review: the candidates pin old library versions or call a cloud service.",
             "42": "Nothing passed review: every candidate runs code typed into a workflow, or controls processes."}
PRIVATE = re.compile(r"/mnt/|/home/|~/|\bvenv\b|nodepack|camp-?b|:\d{4}\b|\b8200\b|\b8322\b|\bbox\b|founder|\bowner|Pack Lab|patched/", re.I)
NOTE_WORDS = {"downloads weights on first use": "downloads model weights the first time a node runs", "needs a browser tab for part of it": "part of it works only with a browser tab open",
              "runs a subprocess at run time": "starts a helper program when a node runs", "registers HTTP routes": "adds HTTP routes to ComfyUI's server",
              "licence declared without a LICENSE file": "licence stated in its metadata, with no LICENSE file", "GPL": "copyleft licence (GPL)", "AGPL-3.0": "copyleft licence (AGPL-3.0)"}
# Packs whose model weights carry their own, narrower licence: shown on the page and printed by install.py.
WEIGHTS = {"spacepxl__ComfyUI-Depth-Pro": "Apple ML Research licence, research use only"}
# Packs kept out of the open edition's set: listed apart, never installed by --packs pool51 and not counted.
OPTIONAL = {"Comfy-Org__ComfyUI_Nvidia_VFX_Nodes": "needs nvidia-vfx, NVIDIA's closed-source Video Effects SDK",
            "tritant__ComfyUI_NVIDIA_RTX_VSR_Long_Video": "needs nvidia-vfx, NVIDIA's closed-source Video Effects SDK",
            "cOkieeman__ComfyUI-Soda-Storyboard": "its pip package (soda-storyboard) states no licence"}
SPECIAL = {"spacepxl__ComfyUI-Depth-Pro": ["the patch makes its loader use only Apple's official DepthPro weights (apple/DepthPro on Hugging Face) instead of a third-party copy",
                                           "weights: Apple ML Research licence, research use only",
                                           "last updated upstream in October 2024"],
           "Fannovel16__comfyui_controlnet_aux": ["installed as custom_nodes/comfyui_controlnet_aux, the folder name other packs import it by",
                                                  "the patch swaps a SciPy import removed in SciPy 2.0, so DWPose and OpenPose load"],
           "zhuyanan__Comfy-FilmSimulator": ["the patch fixes the film pipeline node's preset list and seeds film grain from an input so re-runs match"],
           "PozzettiAndrea__ComfyUI-PanoPack": ["the patch makes it build its isolated environment once, with `comfy-env install` in its folder, and reuse it: starting ComfyUI never downloads or installs anything, and the nodes that need that environment are skipped until it exists",
                                                "the patch also stops it cloning two other node packs on install and copying sample files into ComfyUI's input folder at every start",
                                                "the isolated environment is large (its own PyTorch, Open3D and VTK)"],
           "ssitu__ComfyUI_UltimateSDUpscale": ["installed with its git submodule, so it never downloads code when it loads"],
           "xmarre__ComfyUI-AutoGuidance": ["the patch makes its detailer hook's wrapper around ComfyUI's sampling function one-shot, so it never stays in place for other renders"],
           "Extraltodeus__DistanceSampler": ["the patch removes a reload of ComfyUI's k-diffusion module at load, which could undo other packs' changes to it; its samplers still register"],
           "rgthree__rgthree-comfy": ["its LoRA info panel can look a file up on Civitai when you ask it to"],
           "Zehong-Ma__ComfyUI-MagCache": ["the patch guards an import removed from ComfyUI core and adds the Wan 2.2 model types"]}


def clean(text):
    keep = [s for s in re.split(r"(?<=[.;])\s+", text or "") if s and not PRIVATE.search(s)]
    return " ".join(keep).strip()


def notes_of(row):
    out = []
    for n in (row.get("notes") or "").split(";"):
        n = n.strip()
        if n in NOTE_WORDS: out.append(NOTE_WORDS[n])
        elif n.startswith("waits for a UI click"): out.append("waits for a click in the editor")
    return out + SPECIAL.get(row["pack"], [])


def main(source, patch_dir):
    src = json.load(open(source, encoding="utf-8")); rows = []; optional = []
    for r in src["rows"]:
        if not re.fullmatch(r"[0-9a-f]{40}", r.get("commit") or ""): sys.exit(f"{r['pack']} has no pinned commit")
        if not r.get("commit_check"): sys.exit(f"{r['pack']}'s commit was not checked against the reviewed copy")
        row = {"pack": r["pack"], "folder": r["link_name"], "repo": r["repo"], "url": f"https://github.com/{r['repo']}", "commit": r["commit"],
                     "sections": sorted(r["sections"]), "licence": re.sub(r"^pyproject:(\S+)", r"\1 (stated in pyproject.toml only)", clean(r["licence"])) or "as stated in its repository", "adds": clean(r["adds"]),
                     "nodes": r["nodes"], "node_count": len(r["nodes"]), "pip": r["pip"], "pip_no_deps": bool(r["pip_no_deps"]) and bool(r["pip"]),
                     "patch": r["patch"], "notes": notes_of(r), **({"submodules": True} if r.get("submodules") else {}), **({"weights_licence": WEIGHTS[r["pack"]]} if r["pack"] in WEIGHTS else {})}
        if r["pack"] in OPTIONAL: optional.append({**row, "why": OPTIONAL[r["pack"]]})
        else: rows.append(row)
    rows.sort(key=lambda x: x["pack"].lower())
    secs = []
    for sid, name in SECTIONS.items():
        packs = [p["pack"] for p in rows if p["sections"][0] == sid]; also = [p["pack"] for p in rows if sid in p["sections"][1:]]
        secs.append({"id": sid, "name": name, "packs": packs, "also": also, "nodes": sum(p["node_count"] for p in rows if p["pack"] in packs), **({"empty_why": EMPTY_WHY[sid]} if not packs and sid in EMPTY_WHY else {})})
    data = {"made": src["made"], "about": "Node packs reviewed from their code, then loaded together on a test ComfyUI beside the studio's own nodes: none failed to import and no two register the same node id. A pack's licence is as its repository states it. Reviewed and load-tested is not the same as safe: read a pack before relying on it.",
            "how": "install.py --packs pool51 clones each pack at the commit listed here, applies its patch if it has one, and installs the pip packages listed. Nothing else is fetched at install time; some packs download model weights the first time one of their nodes runs.",
            "sections": secs, "packs": rows,
            "optional_about": "Not part of the open edition and not installed by --packs pool51: each needs something that is not open source. Install one yourself if you accept that.",
            "optional": sorted(optional, key=lambda x: x["pack"].lower())}
    text = json.dumps(data, indent=0, ensure_ascii=False)
    if re.search(r"/mnt/|/home/|\\\\Users", text): sys.exit("a folder path survived")
    PATCHES.mkdir(exist_ok=True)
    for old in PATCHES.glob("*.diff"): old.unlink()
    for p in rows + optional:
        if p["patch"]:
            b = (Path(patch_dir) / p["patch"]).read_bytes()          # bytes: a pack with CRLF files needs its CRs kept in the patch
            if re.search(rb"/mnt/|/home/", b): sys.exit(f"a folder path in {p['patch']}")
            (PATCHES / p["patch"]).write_bytes(b)
    OUT.write_text(text, encoding="utf-8")
    print(len(rows), "packs,", sum(p["node_count"] for p in rows), "nodes,", sum(1 for s in secs if s["packs"]), "of 51 sections with packs,", sum(1 for p in rows if p["patch"]), "patched,", OUT.stat().st_size >> 10, "KB")


if __name__ == "__main__": main(*sys.argv[1:3])
