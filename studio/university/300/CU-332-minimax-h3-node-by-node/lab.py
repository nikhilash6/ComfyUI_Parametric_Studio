# CU-332 lab: H3's shared timeline for picture and sound, ported from comfy_extras/nodes_minimax_h3.py, comfy/ldm/minimax/model.py and comfy/model_sampling.py (ComfyUI v0.43.0).
import math
FPS, AUDIO_LATENT_FPS = 24, 40
def align_frame_count(n):
    while n % 17 != 5: n += 1
    return n
def video_latent_t(f): return 2 if f <= 5 else ((f - 5) // 17) * 5 + 2
def temporal_shape(length):
    f = align_frame_count(max(5, length)); return f, video_latent_t(f), round(f / FPS * AUDIO_LATENT_FPS)
print("length asked -> frames, seconds, video latent [24, T, H, W], audio latent [32, 2, T]   at 1344 x 768")
for n in (5, 100, 124, 362, 736):
    f, T, A = temporal_shape(n); H, W = 768 // 16, 1344 // 16
    vt = T * (H // 2) * (W // 2); at = 2 * A
    print(f"{n:>5d} -> {f:>4d} frames {f / 24:>7.3f} s   video [24, {T:>3d}, {H}, {W}]   audio [32, 2, {A:>4d}]   tokens: video {vt:>7,d} + audio {at:>5,d}, audio is {at / (vt + at):.1%}")
assert temporal_shape(124) == (124, 37, 207) and temporal_shape(100) == (107, 32, 178)
# The graph's ComfyMathExpression gives the same count as the node's snap.
def expr(a): m = max(5, round(a * 24)); return m + (5 - (m % 17)) % 17
assert all(expr(s) == align_frame_count(max(5, round(s * 24))) for s in (0.1, 1, 2.5, 5, 7.3, 15, 30))
print(f"\nthe graph's expression at 5 s gives {expr(5)}, at 15 s {expr(15)}, at 30 s {expr(30)}")
# The sound: 32000 Hz, hop 800 (comfy/sd.py and audio_vae.py), so 40 latent frames a second, and 5/3 of them per video frame.
print(f"audio: 32000 / 800 = {32000 // 800} latent frames a second; per video frame 40 / 24 = {40 / 24:.4f}, which is FRAME_RESCALE = 5/3")
FRAME_PER_TOKEN = (1, 4, 4, 4, 4)
def span(k): return 5 / 3 * FRAME_PER_TOKEN[k % 5]
t = 0.0
for k in range(7):
    print(f"  video latent frame {k}: covers {FRAME_PER_TOKEN[k % 5]} frames, starts at timeline {t:6.3f}, which is {t / 40:.3f} s"); t += span(k)
assert abs(t - 22 * 5 / 3) < 1e-9
# One schedule for the sampler, two for the model. time_shift_sigma from comfy/ldm/minimax/model.py, audio_scale from ModelSamplingAV.
def time_shift(sigma, a, b): base = sigma / (a + sigma * (1.0 - a)); return b * base / (1.0 + (b - 1.0) * base)
print(f"\nshifts: video 12, audio 3, audio_scale = 12 / 3 = {12 / 3:.1f}")
print("video sigma   audio sigma at the same moment")
for s in (0.99, 0.9, 0.75, 0.5, 0.25, 0.1):
    print(f"{s:<13} {time_shift(s, 12.0, 3.0):.4f}")
assert abs(time_shift(0.75, 12.0, 3.0) - 0.4286) < 1e-3
# The video VAE's own chunk numbers, from comfy/ldm/minimax/vae.py defaults.
clip, drop, ratio_t = 17, 3, 1 * 2 * 2 * 1 * 1 * 1
chunk = math.ceil(clip / ratio_t); over = (-drop) % chunk; print(f"\nvideo VAE: ratio_t {ratio_t}, chunk {chunk} tokens, overlap {over} tokens, chunk_frames {(chunk + over) * ratio_t}")
assert (chunk, over) == (5, 2)
