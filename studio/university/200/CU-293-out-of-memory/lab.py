# CU-293 lab: the decisions ComfyUI makes about memory, with the same formulas, on made-up sizes. Nothing allocates real memory, and an out of memory error is simulated with a Python exception.
import math
GB = 1024 ** 3
# minimum_inference_memory and maximum_vram_for_weights in comfy/model_management.py (Linux default reserve of 400 MB)
reserve = 400 * 1024 ** 2; min_inf = GB * 0.8 + reserve
print(f"minimum_inference_memory: {min_inf / GB:.2f} GB")
for total in (8, 12, 24): print(f"card {total:2} GB: maximum_vram_for_weights {(total * GB * 0.88 - min_inf) / GB:5.2f} GB")
assert abs(min_inf / GB - 1.1906) < 0.001
# VAE.decode: split a batch into what fits.
print("\nVAE decode: batch_number = int(free / memory_used), at least 1")
for free, used in ((8, 1.5), (8, 3.0), (2, 3.0)):
    print(f"free {free} GB, {used} GB per latent: {max(1, int(free / used))} at a time")
assert max(1, int(2 / 3.0)) == 1
class OOM(Exception): pass
# VAE.decode: the retry. It catches only out of memory, and retries in tiles.
def decode(fits_whole, tile_fits=True):
    log = []
    try:
        log.append("whole decode")
        if not fits_whole: raise OOM()
    except OOM:
        log.append("Warning: Ran out of memory when regular VAE decoding, retrying with tiled VAE decoding.")
        log.append("tiled decode")
        if not tile_fits: log.append("error reaches the node, no further retry")
    return log
print(); [print(" ", l) for l in decode(False)]
assert decode(True) == ["whole decode"]
# Upscale model: halve the tile until it fits, give up under 128. ImageUpscaleWithModel in comfy_extras/nodes_upscale_model.py.
def upscale(need):
    tile = 512; tried = []
    while True:
        tried.append(tile)
        if tile <= need: return tried, "ok"
        tile //= 2
        if tile < 128: return tried, "raises the error"
print("\nupscale model, the largest tile that fits is 128:", upscale(128)); print("nothing fits:", upscale(64))
assert upscale(128) == ([512, 256, 128], "ok") and upscale(64)[1] == "raises the error"
# Tile count, as in get_tiled_scale_steps in comfy/utils.py. A tiled decode runs three passes.
def steps(w, h, tx, ty, o):
    rows = 1 if h <= ty else math.ceil((h - o) / (ty - o)); cols = 1 if w <= tx else math.ceil((w - o) / (tx - o)); return rows * cols
w, h = 128, 128      # a 1024 by 1024 picture in SD latent cells
a, b, c = steps(w, h, 64, 64, 16), steps(w, h, 32, 128, 16), steps(w, h, 128, 32, 16)
print(f"\ntiled decode of a 1024 by 1024 image, default tiles: {a} + {b} + {c} = {a + b + c} tile decodes")
assert (a, b, c) == (9, 7, 7)
d, e, f = steps(w, h, 64, 64, 8), steps(w, h, 32, 128, 8), steps(w, h, 128, 32, 8)
print(f"VAEDecodeTiled at its defaults, 512 and 64 pixels, so tile 64 and overlap 8: {d} + {e} + {f} = {d + e + f} tile decodes")
assert (d, e, f) == (9, 5, 5)
# Sampling: how many conds go in one model call. calc_cond_batch in comfy/samplers.py: needs 1.5 times the estimate free.
def batch_conds(n, each, free):
    for i in range(1, n + 1):
        k = n // i
        if k * each * 1.5 < free: return k
    return 1
print("\ncond and uncond in one call or two: 2 conds at 3 GB each")
for free in (12, 8, 4): print(f"free {free:2} GB: {batch_conds(2, 3, free)} at a time")
assert batch_conds(2, 3, 12) == 2 and batch_conds(2, 3, 8) == 1
