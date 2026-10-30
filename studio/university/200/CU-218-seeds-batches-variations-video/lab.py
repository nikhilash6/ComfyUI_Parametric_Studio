# CU-218 lab: where a seed goes in ComfyUI (comfy/sample.py, prepare_noise), and what that means for batches, video latents and "variations".
# Run: python lab.py  (CPU only, a few seconds). Prints the same numbers every time. The noise is drawn on the CPU, as in ComfyUI.
import math, torch
torch.set_num_threads(1)

def prepare_noise(shape, seed, noise_inds=None):
    """comfy/sample.py prepare_noise_inner for a float32 latent: seed the CPU generator, then one randn for the whole latent.
    With noise_inds (the latent's batch_index) it draws one item at a time and keeps the ones asked for."""
    g = torch.manual_seed(seed)
    if noise_inds is None: return torch.randn(shape, dtype=torch.float32, generator=g, device="cpu")
    uniq = sorted(set(noise_inds)); kept = {}
    for i in range(uniq[-1] + 1):
        n = torch.randn([1] + list(shape[1:]), dtype=torch.float32, generator=g, device="cpu")
        if i in uniq: kept[i] = n
    return torch.cat([kept[i] for i in noise_inds], 0)
def share(a, b): return (a == b).float().mean().item()

# 1. One draw for the whole latent. A Wan-sized video latent: 16 channels, 21 latent frames, 60 x 104.
wan = [1, 16, 21, 60, 104]; z = prepare_noise(wan, 42)
print(f"latent {wan}: {z.numel():,d} numbers, mean {z.mean():.4f}, std {z.std():.4f}")

# 2. The seed widget accepts up to 2^64 - 1. The CPU generator seems to keep 32 bits of it.
a = prepare_noise([1, 4, 64, 64], 5)
print("\nseed 5 against seed 5 + 2^32: identical noise " + str(torch.equal(a, prepare_noise([1, 4, 64, 64], 5 + 2 ** 32))) + ";  against 5 + 2^63: " + str(torch.equal(a, prepare_noise([1, 4, 64, 64], 5 + 2 ** 63))) + ";  against 6: " + str(torch.equal(a, prepare_noise([1, 4, 64, 64], 6))))

# 3. Batches. Item i of a batch should be the i-th draw, so item 0 does not depend on the batch size, and batch_index can redo one item alone.
print("\nbatch of 4, same seed 7:   item 0 equals the noise of a batch of 1   item 1 equals the second draw   one item redone with batch_index [2] equals item 2")
for shape in ([4, 4, 64, 64], [4, 16, 5, 8, 8], [4, 3, 5, 7, 7], [4, 4, 9, 9]):
    full = prepare_noise(shape, 7); one = prepare_noise([1] + shape[1:], 7); redo = prepare_noise([1] + shape[1:], 7, [2])
    second = prepare_noise([2] + shape[1:], 7, [0, 1])[1:2]
    print(f"  {str(shape):18s} {math.prod(shape[1:]):>6d} numbers per item   {str(torch.equal(full[0:1], one)):<42s}{str(torch.equal(full[1:2], second)):<30s}{torch.equal(full[2:3], redo)}")
fixed = prepare_noise([4, 4, 64, 64], 7, [0, 0, 0, 0])
print(f"LatentBatchSeedBehavior 'fixed' sets batch_index to [0, 0, 0, 0]: all four items identical: {all(torch.equal(fixed[0], fixed[i]) for i in range(4))}")

# 4. Video. The noise is laid out channel by channel, then frame by frame. Change the number of frames, and every channel after the first moves.
z21 = prepare_noise([1, 16, 21, 60, 104], 3); z41 = prepare_noise([1, 16, 41, 60, 104], 3); zw = prepare_noise([1, 16, 21, 60, 112], 3)
print(f"\nsame seed, 21 latent frames against 41: share of the 21-frame noise found unchanged in the 41-frame noise {share(z21, z41[:, :, :21]):.4f}  (channel 0 alone: {share(z21[:, 0], z41[:, 0, :21]):.4f})")
print(f"same seed, width 104 against 112: share unchanged {share(z21, zw[..., :104]):.4f}")

# 5. Is the noise of one frame related to the next? Correlation of adjacent latent frames, over all channels and positions.
cs = []
for t in range(20):
    u, v = z21[0, :, t].flatten(), z21[0, :, t + 1].flatten(); cs.append(((u * v).mean() / (u.std() * v.std())).item())
print(f"correlation between the noise of adjacent frames, 20 pairs: mean {sum(cs) / 20:+.4f}, largest in size {max(abs(c) for c in cs):.4f}")
assert max(abs(c) for c in cs) < 0.02

# 6. A related noise by interpolating two noises a and b (flattened, 16,384 numbers each). Std is how noisy the start would be.
a = prepare_noise([1, 4, 64, 64], 1).flatten(); b = prepare_noise([1, 4, 64, 64], 2).flatten(); th = math.acos(((a * b).sum() / (a.norm() * b.norm())).item())
print(f"\nangle between the two noises {math.degrees(th):.1f} degrees.   t      lerp: std  corr with a      slerp: std  corr with a")
for t in (0.1, 0.25, 0.5):
    lerp = (1 - t) * a + t * b; slerp = (math.sin((1 - t) * th) * a + math.sin(t * th) * b) / math.sin(th)
    c = lambda y: ((y * a).sum() / (y.norm() * a.norm())).item()
    print(f"                                          {t:<6} {lerp.std():.3f}      {c(lerp):.3f}            {slerp.std():.3f}       {c(slerp):.3f}")
