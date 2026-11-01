# CU-370 lab: pull the useful numbers out of ComfyUI's console. The lines below are copied from one real job on our test machine, seconds past the minute in front, with repeats, file paths and lines this lab doesn't use removed, and the bar's block characters written as #.
# The patterns follow the log calls in main.py, server.py, comfy/model_management.py, comfy/model_patcher.py and comfy/sd.py at v0.43.0.
import re
LOG = """31.93 Using pytorch attention in VAE
32.11 VAE load device: cuda:0, offload device: cpu, dtype: torch.bfloat16
33.09 Requested to load AutoencoderKL
33.12 Model AutoencoderKL prepared for dynamic VRAM loading. 160MB Staged. 0 patches attached. Force pre-loaded 110 weights: 187 KB.
34.15 CLIP/text encoder model load device: cuda:0, offload device: cpu, current: cpu, dtype: torch.bfloat16
34.15 Requested to load Flux2TEModel_
34.20 Model Flux2TEModel_ prepared for dynamic VRAM loading. 8262MB Staged. 0 patches attached. Force pre-loaded 145 weights: 602 KB.
36.95 model weight dtype torch.bfloat16, manual cast: None
36.95 model_type FLUX
36.96 Requested to load Flux2
36.99 Model Flux2 prepared for dynamic VRAM loading. 17316MB Staged. 0 patches attached. Force pre-loaded 80 weights: 59 KB.
36.99   0%|          | 0/4 [00:00<?, ?it/s]
47.31 got prompt
51.13 100%|##########| 4/4 [00:04<00:00,  1.05s/it]""".splitlines()
RULES = [("queued", r"^got prompt"), ("device", r"load device: (\S+), offload device: (\S+).*dtype: (\S+)"), ("wants model", r"^Requested to load (\w+)"),
         ("staged", r"^Model (\w+) prepared for dynamic VRAM loading\. (\d+)MB Staged\. (\d+) patches"), ("full load", r"^loaded completely;"), ("part load", r"^loaded partially;"),
         ("dtype", r"^model weight dtype (\S+), manual cast: (\S+)"), ("family", r"^model_type (\w+)"), ("attention", r"^Using .* attention"), ("steps", r"(\d+)/(\d+) \[[^\]]*?([\d.?]+)(s/it|it/s)\]"), ("done", r"^Prompt executed in ([\d.:]+)")]
def read(line):
    for k, p in RULES:
        m = re.search(p, line)
        if m: return k, m.groups()
    return "other", ()
staged = {}; loads = []; rate = None; start = None; end = None
for row in LOG:
    when, l = float(row[:5]), row[6:]
    k, g = read(l); print(f"{when:5.2f}  {k:12s} {l[:74]}")
    if k == "staged": staged[g[0]] = int(g[1])
    if k == "wants model": loads.append(g[0])
    if k == "steps" and g[3] and int(g[0]) == int(g[1]): rate = (int(g[1]), float(g[2]), g[3]); end = when
    if "0/4" in l: start = when
assert loads == ["AutoencoderKL", "Flux2TEModel_", "Flux2"] and staged["Flux2"] == 17316
print(f"\nmodels asked for, in order: {loads}")
print(f"staged in total: {sum(staged.values())} MB, the size set up for loading on demand, not bytes held on the card")
print(f"the bar says {rate[0]} steps at {rate[1]} s/it = {rate[0] * rate[1]:.1f} s. The clock says the bar was open from {start} to {end} = {end - start:.2f} s.")
assert end - start > 3 * rate[0] * rate[1]
print(f"from the first line to the last step: {end - float(LOG[0][:5]):.2f} s, of which sampling steps by the bar's count {100 * rate[0] * rate[1] / (end - float(LOG[0][:5])):.0f}%")
ex = ["loaded completely; 7000.00 MB usable, 4900.00 MB loaded, full load: True", "loaded partially; 5120.00 MB usable, 4890.00 MB loaded, 2377.00 MB offloaded, 128.00 MB buffer reserved, lowvram patches: 0"]
print("\nthe other kind of load line, from the estimate-based path. Numbers here are ours, the wording is the source's")
for l in ex: print(f"{read(l)[0]:12s} {l}")
m = re.search(r"([\d.]+) MB loaded, ([\d.]+) MB offloaded", ex[1]); on, off = float(m.group(1)), float(m.group(2))
print(f"share on the card: {on / (on + off):.0%}")
assert read(ex[0])[0] == "full load" and read(ex[1])[0] == "part load"
print("\nthe two ways tqdm writes speed")
for t in ("1.05s/it", "3.40it/s"):
    v = float(t.split("s/it")[0]) if t.endswith("s/it") else 1 / float(t.split("it/s")[0]); print(f"  {t:10s} is {v:.3f} seconds per step")
