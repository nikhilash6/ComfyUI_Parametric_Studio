# CU-274 lab: ImagePadForOutpaint, line by line (nodes.py), and what VAEEncodeForInpaint does to its mask afterwards.
import torch
def expand_image(image, left, top, right, bottom, feathering):
    d1, d2, d3, d4 = image.size()
    new = torch.ones((d1, d2 + top + bottom, d3 + left + right, d4)) * 0.5; new[:, top:top + d2, left:left + d3, :] = image
    mask = torch.ones((d2 + top + bottom, d3 + left + right)); t = torch.zeros((d2, d3))
    if feathering > 0 and feathering * 2 < d2 and feathering * 2 < d3:
        for i in range(d2):
            for j in range(d3):
                dt = i if top != 0 else d2; db = d2 - i if bottom != 0 else d2; dl = j if left != 0 else d3; dr = d3 - j if right != 0 else d3
                d = min(dt, db, dl, dr)
                if d >= feathering: continue
                v = (feathering - d) / feathering; t[i, j] = v * v
    mask[top:top + d2, left:left + d3] = t
    return new, mask
def grow(mask, n=6):
    k = torch.ones(1, 1, n, n); pad = -(-(n - 1) // 2)
    return torch.clamp(torch.nn.functional.conv2d(mask.round()[None, None], k, padding=pad), 0, 1)[0, 0, :mask.shape[0], :mask.shape[1]].round()
img = torch.full((1, 512, 512, 3), 0.8)
new, m = expand_image(img, 0, 0, 128, 0, 40)
print("512 x 512 picture, 128 added on the right, feathering 40 (the default)")
print("output size", tuple(new.shape[1:3]), "  new pixels hold", new[0, 0, 600, 0].item(), "(mid grey)")
col = lambda a: " ".join(f"{a[100, c].item():.2f}" for c in (440, 472, 482, 492, 502, 508, 511, 512, 600))
print("columns                 440  472  482  492  502  508  511  512  600")
print("mask                   ", col(m))
print("rounded (VAE route)    ", col(m.round()))
print("rounded and grown by 6 ", col(grow(m)))
reach = lambda a: (512 - (a[100, :512] > 0.5).float().argmax().item()) if (a[100, :512] > 0.5).any() else 0
print("\npixels of your own picture that get repainted, counted from the join")
print("feathering   soft mask above 0   rounded   rounded, grown by 6   feather on?")
rows = {}
for f in (0, 8, 16, 40, 80, 255, 256):
    _, q = expand_image(img[:, :, :, :], 0, 0, 128, 0, f)
    soft = (q[100, :512] > 0).sum().item(); rd = (q.round()[100, :512] > 0).sum().item(); gr = (grow(q)[100, :512] > 0).sum().item(); rows[f] = (soft, rd, gr)
    print(f"{f:<12} {soft:<19} {rd:<9} {gr:<21} {'yes' if f > 0 and f * 2 < 512 else 'no: hard edge'}")
assert rows[0] == (0, 0, 2) and rows[40] == (39, 11, 13)
assert rows[256][0] == 0 and rows[255][0] > 200
print("\nthe feather switches off without warning: feathering x 2 must be smaller than both sides of the picture")
print("picture       feathering 40")
for h, w in ((512, 512), (96, 96), (80, 512), (64, 64)):
    _, q = expand_image(torch.full((1, h, w, 3), 0.8), 0, 0, 32, 0, 40); print(f"{h} x {w:<8} {'feathered' if (q[h // 2, :w] > 0).any() else 'hard edge'}")
print("\nonly padded sides feather. 64 added on the left only, feathering 16: first and last rows and columns of the old picture")
_, q = expand_image(torch.full((1, 128, 128, 3), 0.8), 64, 0, 0, 0, 16)
print("join column value", q[64, 64].item(), "  far right column", q[64, 191].item(), "  top row, middle", q[0, 128].item())
assert q[64, 64].item() == 1.0 and q[64, 191].item() == 0.0 and q[0, 128].item() == 0.0
print("\nthe grid: pad widgets step by 8, but the picture need not. VAE routes crop to a multiple of 8, from the centre")
print("size after padding   kept after the crop   pixels lost")
for w in (640, 644, 767):
    k = (w // 8) * 8; print(f"{w:<20} {k:<21} {w - k}")
