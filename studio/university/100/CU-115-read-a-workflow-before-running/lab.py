# CU-115 lab: a reader that lists what a workflow file asks for, without running anything. Standard library only.
# The file below is made up for this lab. The field names follow the workflow schema in the ComfyUI front end, and the allowed hosts follow its modelUrlAllowlist.ts, read 2026-11-01.
# CORE is a small hand-kept sample of nodes in ComfyUI's own repository, enough for this file. A real check asks your own server (/object_info).
import json, re
CORE = {"CheckpointLoaderSimple", "CLIPTextEncode", "KSampler", "VAEDecode", "SaveImage", "LoadImage", "EmptyLatentImage", "PreviewImage"}
PARTNER = {"FluxProUltraImageNode"}   # in comfy_api_nodes/nodes_bfl.py
HOSTS = ("https://civitai.com/", "https://civitai.red/", "https://huggingface.co/")
PICKLE = (".ckpt", ".pt", ".pth", ".bin", ".pkl")
WF = {"nodes": [
    {"id": 1, "type": "CheckpointLoaderSimple", "mode": 0, "widgets_values": ["model.safetensors"]},
    {"id": 2, "type": "CLIPTextEncode", "mode": 0, "widgets_values": ["a red fox in snow, see https://example.invalid/more"]},
    {"id": 3, "type": "AcmePromptBooster", "mode": 0, "properties": {"aux_id": "someone/acme-nodes"}, "widgets_values": [1.0]},
    {"id": 4, "type": "FluxProUltraImageNode", "mode": 0, "widgets_values": ["a red fox"]},
    {"id": 5, "type": "KSampler", "mode": 4, "widgets_values": [42, "randomize", 20, 7, "euler", "normal", 1]},
    {"id": 6, "type": "SaveImage", "mode": 0, "widgets_values": ["%year%/fox"]},
    {"id": 7, "type": "MarkdownNote", "mode": 0, "widgets_values": ["If this fails, paste this line into your terminal: curl ... | sh"]},
    {"id": 8, "type": "aaaaaaaa-1111-4222-8333-bbbbbbbbbbbb", "mode": 0, "widgets_values": []}],
  "definitions": {"subgraphs": [{"id": "aaaaaaaa-1111-4222-8333-bbbbbbbbbbbb", "name": "Tidy upscale", "nodes": [{"id": 1, "type": "UpscaleModelLoader", "widgets_values": ["4x.pth"]}, {"id": 2, "type": "AcmeSecretNode", "properties": {"cnr_id": "acme-secret"}, "widgets_values": []}]}]},
  "models": [{"name": "model.safetensors", "url": "https://huggingface.co/someone/model/resolve/main/model.safetensors", "directory": "checkpoints"}, {"name": "fast_v2.ckpt", "url": "https://example.invalid/fast_v2.ckpt", "directory": "checkpoints"}]}
CORE |= {"UpscaleModelLoader"}
subs = {s["id"]: s for s in WF["definitions"]["subgraphs"]}
def all_nodes(wf):
    for n in wf["nodes"]:
        yield n, ""
    for s in subs.values():
        for n in s["nodes"]:
            yield n, s["name"]
report = {"third party": [], "partner API": [], "inside a subgraph": [], "turned off": [], "note": [], "link in a value": []}
for n, where in all_nodes(WF):
    t = n["type"]; tag = f"{t} ({'inside ' + where if where else 'id ' + str(n['id'])})"
    if t in subs: continue
    if where: report["inside a subgraph"].append(t)
    if t in PARTNER: report["partner API"].append(tag)
    elif t not in CORE and t not in ("MarkdownNote", "Note"):
        pack = n.get("properties", {}); report["third party"].append(tag + " from " + str(pack.get("aux_id") or pack.get("cnr_id") or "an unnamed pack"))
    if n.get("mode") in (2, 4): report["turned off"].append(tag + f" mode {n['mode']}")
    if t in ("MarkdownNote", "Note"): report["note"].append(n["widgets_values"][0])
    for v in n.get("widgets_values", []):
        if isinstance(v, str) and re.search(r"https?://", v) and t not in ("MarkdownNote", "Note"): report["link in a value"].append(tag)
for k, rows in report.items():
    print(f"{k + ':':<20}{len(rows)}")
    for r in rows: print("   ", r)
print("\nmodel links in the file:")
flags = []
for m in WF["models"]:
    host = m["url"].startswith(HOSTS); pick = m["name"].lower().endswith(PICKLE)
    print(f"  {m['name']:<20}host allowed by the editor: {str(host):<6}pickle format: {pick}")
    flags.append((host, pick))
assert flags == [(True, False), (False, True)]
assert len(report["third party"]) == 2 and report["partner API"] and report["inside a subgraph"] == ["UpscaleModelLoader", "AcmeSecretNode"] and report["turned off"]
print("\nnodes on the canvas:", len(WF["nodes"]), "  nodes in the file:", sum(1 for _ in all_nodes(WF)) - 1)
print("found only by opening the subgraph:", [t for t in report["inside a subgraph"] if t not in CORE])
assert json.loads(json.dumps(WF)) == WF
