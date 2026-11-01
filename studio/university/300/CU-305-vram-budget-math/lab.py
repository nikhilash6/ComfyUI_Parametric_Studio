# CU-305 lab: the three numbers in a VRAM budget, using formulas read from ComfyUI v0.43.0. No GPU.
# Weights are parameters x bytes. Working memory is model_base.memory_required. Room asked for is load_models_gpu's sum.
MB = 1024 ** 2; GB = 1024 ** 3
RESERVED = 400 * MB                                  # EXTRA_RESERVED_VRAM on Linux, without --reserve-vram
def min_inference(): return 0.8 * GB + RESERVED      # minimum_inference_memory: 1024*1024*1024*0.8 + extra reserved
def memory_required(batch, h, w, dtype_bytes, factor, frames=None):
    """model_base.BaseModel.memory_required, the path taken with pytorch or flash attention. Shape is [batch, channels, ...], and channels are not counted."""
    area = batch * h * w * (frames or 1)
    return area * dtype_bytes * 0.01 * factor * MB
def room_asked(weights, required):
    """load_models_gpu: free_memory(total_memory_required * 1.1 + extra_mem), extra_mem = max(inference_memory, memory_required + reserved)."""
    return weights * 1.1 + max(min_inference(), required + RESERVED)
print("weights: parameters x bytes per parameter (parameter counts from Table 1 of the SDXL paper)")
for name, p in (("SD 1.x U-Net, 860M", 860e6), ("SDXL U-Net, 2.6B", 2.6e9)):
    print(f"  {name:20s} " + "  ".join(f"{d} {p * b / GB:5.2f} GB" for d, b in (("fp32", 4), ("fp16", 2), ("fp8", 1))))
assert abs(860e6 * 2 / GB - 1.60) < 0.01
print("\nworking memory estimate, fp16, CFG on (estimate_memory doubles the batch)")
rows = (("SD 1.5  512 px", 64, 64, 1.0), ("SD 1.5  768 px", 96, 96, 1.0), ("SDXL   1024 px", 128, 128, 0.8), ("SD3    1024 px", 128, 128, 1.6))
for name, h, w, f in rows:
    print(f"  {name}  latent {h}x{w}  factor {f}:  {memory_required(2, h, w, 2, f) / MB:7.1f} MB")
a = memory_required(2, 64, 64, 2, 1.0); b = memory_required(2, 128, 128, 2, 1.0); c = memory_required(4, 64, 64, 2, 1.0)
print(f"\ndouble the side: x{b / a:.0f}.  double the batch: x{c / a:.0f}.  channels make no difference to this estimate.")
assert b / a == 4 and c / a == 2
print("\nroom asked for before loading, on a 12 GB card with nothing else loaded")
for name, p, bytes_, h, f in (("SD 1.5 fp16, 512 px", 860e6, 2, 64, 1.0), ("SDXL fp16, 1024 px", 2.6e9, 2, 128, 0.8), ("SDXL fp8, 1024 px", 2.6e9, 1, 128, 0.8)):
    w = p * bytes_; need = room_asked(w, memory_required(2, h, h, 2, f))
    print(f"  {name:21s} weights {w / GB:5.2f} GB  asks for {need / GB:5.2f} GB  left {(12 * GB - need) / GB:6.2f} GB")
assert room_asked(2.6e9 * 2, memory_required(2, 128, 128, 2, 0.8)) < 12 * GB
print("\nwhat a finished result costs in system RAM (node outputs live on intermediate_device, the CPU, unless --gpu-only)")
for name, n in (("latent 128x128, 4 channels, fp32", 128 * 128 * 4 * 4), ("IMAGE 1024x1024, 3 channels, fp32", 1024 * 1024 * 3 * 4), ("IMAGE batch, 81 frames 1280x720", 81 * 1280 * 720 * 3 * 4)):
    print(f"  {name:36s} {n / MB:8.2f} MB")
assert 128 * 128 * 4 * 4 / MB == 0.25
