# CU-371 lab: three launch decisions, ported from ComfyUI v0.43.0. We also ran the real parser from comfy/cli_args.py to confirm which flags refuse each other.
def enables_dynamic_vram(enable=False, disable=False, highvram=False, gpu_only=False, novram=False, cpu=False):
    """comfy/cli_args.py: enables_dynamic_vram."""
    if enable: return True
    return not disable and not highvram and not gpu_only and not novram and not cpu
print("does this set of flags ask for dynamic VRAM?")
for label, kw in (("no flags", {}), ("--lowvram", {}), ("--highvram", {"highvram": True}), ("--gpu-only", {"gpu_only": True}), ("--novram", {"novram": True}), ("--cpu", {"cpu": True}), ("--disable-dynamic-vram", {"disable": True}), ("--highvram --enable-dynamic-vram", {"highvram": True, "enable": True})):
    print(f"  {label:34s} {enables_dynamic_vram(**kw)}")
assert enables_dynamic_vram() and not enables_dynamic_vram(highvram=True) and enables_dynamic_vram(highvram=True, enable=True)
def attention(flag=None, nvidia=True, torch2=True, xformers=False):
    """comfy/model_management.py sets the pytorch default, then comfy/ldm/modules/attention.py picks in this order. Returns the log line."""
    pytorch = flag == "pytorch" or (nvidia and torch2 and flag not in ("split", "quad"))
    line = "sage" if flag == "sage" else "flash" if flag == "flash" else "xformers" if xformers and flag != "pytorch" else "pytorch" if pytorch else "split" if flag == "split" else "sub quadratic"
    return "comfy kitchen" if flag == "ck" else line
print("\nwhich attention runs")
for label, kw in (("NVIDIA, torch 2, no flag", {}), ("NVIDIA, --use-split-cross-attention", {"flag": "split"}), ("NVIDIA, --use-sage-attention", {"flag": "sage"}), ("NVIDIA, --use-flash-attention", {"flag": "flash"}), ("NVIDIA, --use-ck-attention", {"flag": "ck"}), ("no pytorch default, no flag", {"nvidia": False})):
    print(f"  {label:38s} {attention(**kw)}")
assert attention() == "pytorch" and attention(flag="split") == "split" and attention(nvidia=False) == "sub quadratic"
def cache(ram=None, classic=False, lru=0, none=False, total_ram_gb=64):
    """main.py: RAM pressure is the default, and its first threshold is 10% of system RAM, at least 2 GB and at most 10 GB, unless you give one."""
    if classic: return "classic"
    if none: return "none"
    if lru > 0: return f"LRU, {lru} results"
    head = ram if ram is not None else min(10.0, max(2.0, total_ram_gb * 0.10)); return f"RAM pressure, keep {head:g} GB free"
print("\nthe node result cache")
for label, kw in (("no flag, 16 GB RAM", {"total_ram_gb": 16}), ("no flag, 64 GB RAM", {}), ("no flag, 256 GB RAM", {"total_ram_gb": 256}), ("--cache-ram 8", {"ram": 8}), ("--cache-lru 12", {"lru": 12}), ("--cache-classic", {"classic": True}), ("--cache-none", {"none": True})):
    print(f"  {label:24s} {cache(**kw)}")
assert cache(total_ram_gb=16) == "RAM pressure, keep 2 GB free" and cache(total_ram_gb=256) == "RAM pressure, keep 10 GB free"
MB = 1024 ** 2; GB = 1024 ** 3
def reserved(arg=None, windows=False): return arg * GB if arg is not None else (600 if windows else 400) * MB
def min_inf(arg=None): return 0.8 * GB + reserved(arg)
print("\n--reserve-vram changes the room every load asks for, through minimum_inference_memory")
for a in (None, 1, 4): print(f"  --reserve-vram {str(a):5s} reserved {reserved(a) / GB:5.2f} GB   minimum working room {min_inf(a) / GB:5.2f} GB")
assert min_inf(4) == 4.8 * GB
