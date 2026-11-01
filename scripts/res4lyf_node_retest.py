#!/usr/bin/env python3
"""Second chance for nodes that failed res4lyf_node_check.py because of how that test was set up, not necessarily because of the node.

The first pass runs everything on SD1.5 with few inputs wired. Here a failed node runs again on the model family it asks for, on a latent
that has been through a sampler, or with every optional input wired. A node that passes records which setup it needed ("via"); one that
still fails keeps its first error and notes what else was tried. Nothing here proves a node is broken in every setup.
Usage: res4lyf_node_retest.py http://127.0.0.1:8683 /path/to/instance flux|wan|sd35|sampled|wired
"""
import json
import sys

import res4lyf_node_check as C

ALL_INPUTS = set(C.SOURCES)
VARIANTS = {
    "flux": {"label": "FLUX.1 schnell", "steps": 6, "cfg": 1.0, "latent": "EmptySD3LatentImage", "nodes": [
        "ReFluxPatcher", "ReFluxPatcherAdvanced", "TorchCompileModelFluxAdv", "TorchCompileModels", "FluxOrthoCFGPatcher", "FluxGuidanceDisable", "LayerPatcher",
        "ModelSamplingAdvanced", "ModelSamplingAdvancedResolution", "ModelTimestepPatcher", "CLIPTextEncodeFluxUnguided", "ClownStyle_Boost", "ClownGuide_AdaIN_MMDiT_Beta"]},
    "wan": {"label": "Wan 2.2 TI2V 5B", "steps": 6, "cfg": 5.0, "video": True, "nodes": [
        "ReWanPatcher", "ReWanPatcherAdvanced", "ClownpileModelWanVideo", "Frame Select Latent", "Frame Select Latent Raw", "Frames Latent ReverseOrder",
        "Frames Slice Latent", "Frames Slice Latent Raw", "Frames Concat Latent Raw"]},
    "sd35": {"label": "SD 3.5 medium", "steps": 8, "cfg": 4.5, "latent": "EmptySD3LatentImage", "nodes": [
        "ReSD35Patcher", "ReSD35PatcherAdvanced", "TorchCompileModelSD35", "ConditioningTruncate"]},
    "sampled": {"label": "a latent from an earlier sampler", "sampled": True, "nodes": [
        "ClownsharkChainsampler_Beta", "SharkChainsampler_Beta", "Latent Transfer State Info", "Latent CropGuides State Info"]},
    "wired": {"label": "every optional input wired", "all_inputs": True},
}
OTHER_FAMILY = ("for regional conditioning for AuraFl", "for regional conditioning for Chroma", "for regional conditioning for HiDrea", "for regional conditioning for LTXV")
# A patcher swaps block classes on the loaded model, and that stays on the copy in memory, so the next node on that model can fail because of it.
CLEAN = {"flux": ["FluxGuidanceDisable", "FluxOrthoCFGPatcher", "ModelSamplingAdvanced", "LayerPatcher"],
         "wan": ["ReWanPatcher", "ReWanPatcherAdvanced", "Frames Latent ReverseOrder", "Frames Slice Latent"]}
LOADERS = {
    "flux": {"ck": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-schnell.safetensors", "weight_dtype": "default"}},
             "ck_clip": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp16.safetensors", "type": "flux"}},
             "ck_vae": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}}},
    "wan": {"ck": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}},
            "ck_clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan"}},
            "ck_vae": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}}},
    "sd35": {"ck": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd3/sd3.5_medium.safetensors"}},
             "ck_clip": {"class_type": "TripleCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "clip_g.safetensors", "clip_name3": "t5xxl_fp16.safetensors"}}},
}


def adapt(graph, key, v):
    """Moves a graph built for SD1.5 onto this variant's model."""
    if key in LOADERS:
        for node in graph.values():
            for arg, val in node["inputs"].items():
                if val == ["ck", 1]:
                    node["inputs"][arg] = ["ck_clip", 0]
                elif val == ["ck", 2] and "ck_vae" in LOADERS[key]:
                    node["inputs"][arg] = ["ck_vae", 0]
        graph.update(json.loads(json.dumps(LOADERS[key])))
    video = {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["ck_vae", 0], "width": C.SIZE, "height": C.SIZE, "length": 9, "batch_size": 1}}
    if "empty" in graph:
        if v.get("video"):
            graph["empty"] = json.loads(json.dumps(video))
        elif v.get("latent"):
            graph["empty"]["class_type"] = v["latent"]
    if v.get("video") and "src" in graph:
        graph["src"] = json.loads(json.dumps(video))
    for node in graph.values():
        if node["class_type"] in ("ClownsharKSampler_Beta", "SharkSampler_Beta") and "steps" in v:
            node["inputs"].update(steps=v["steps"], cfg=v["cfg"])
    return graph


def main():
    url, inst, key = sys.argv[1].rstrip("/"), C.pathlib.Path(sys.argv[2]), sys.argv[3]
    if C.urllib.parse.urlparse(url).port in C.LIVE_PORTS:
        raise SystemExit("refusing a live port")
    v = VARIANTS[key]
    if v.get("all_inputs"):
        C.OPTIONAL_WIRED = ALL_INPUTS
    if v.get("sampled"):
        C.BASE["first"] = C.sampler(steps_to_run=C.STEPS // 2)
        C.SOURCES["LATENT"] = ("first", 0)
    info = C.call(url, "/object_info")
    device = C.call(url, "/system_stats")["devices"][0]["name"]
    results = json.loads(C.OUT.read_text())
    listed = {n for x in VARIANTS.values() for n in x.get("nodes", [])}
    clean = "--clean" in sys.argv
    names = CLEAN[key] if clean else v.get("nodes") or [n for n, r in results.items() if n not in listed and r["state"] in ("error", "timeout") and not any(m in r["detail"] for m in OTHER_FAMILY)]
    done = 0
    for name in names:
        r = results.get(name)
        if not r or r["state"] not in ("error", "rejected", "timeout") or name not in info:
            continue
        if key + "_clean" in r.get("tried", {}) or (not clean and key in r.get("tried", {})):
            continue
        graph, wired, why = C.graph_for(name, info[name])
        if graph is None:
            r.setdefault("tried", {})[key] = why
        else:
            graph = adapt(graph, key, v)
            if clean:
                C.restart(url, inst)
            state, detail, img = C.run(url, graph, wait=240)
            if C.DTYPE.search(detail):
                C.restart(url, inst)
                state, detail, img = C.run(url, graph, wait=240)
            if "Precision" in name or state == "timeout" or C.DTYPE.search(detail):
                C.restart(url, inst)
            else:
                done += 1
                if done % C.FREE_EVERY == 0:
                    C.call(url, "/free", {"unload_models": True, "free_memory": True})
            if state == "ran" or img:
                (C.THUMBS / f"{C.safe(name)}.json").write_text(json.dumps(graph, indent=1))
                r.update(state="rendered" if img else "ran", detail="", wired=wired, device=device, via=v["label"], first_error=r["detail"], graph=f"res4lyf_renders/nodes/{C.safe(name)}.json")
                if img:
                    C.thumb(url, name, img, r)
            else:
                r.setdefault("tried", {})[key + "_clean" if clean else key] = detail
        C.OUT.write_text(json.dumps(results, indent=0, sort_keys=True))
        print(name, r["state"], (r.get("tried", {}).get(key + "_clean" if clean else key) or "")[:110], flush=True)
    counts = {}
    for r in results.values():
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    print(counts)


if __name__ == "__main__":
    main()
