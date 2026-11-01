# CU-306 lab: what the mask does, and what shape each encoder hands on. The mask follows CLIPTextModel_.forward and T5Stack.forward in v0.43.0. The chunking follows SDTokenizer.tokenize_with_weights. Random numbers stand in for trained weights.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
DIM = 8; Wq = torch.randn(DIM, DIM); Wk = torch.randn(DIM, DIM); Wv = torch.randn(DIM, DIM)
def attend(x, mask=None):
    s = (x @ Wq) @ (x @ Wk).transpose(-2, -1) / math.sqrt(DIM)
    if mask is not None: s = s + mask
    return torch.softmax(s, -1) @ (x @ Wv)
def causal(n): return torch.full((n, n), -torch.finfo(torch.float32).max).triu_(1)      # clip_model.py: causal_mask, added to the scores
x = torch.randn(1, 6, DIM); y = x.clone(); y[0, 5] = torch.randn(DIM)                  # change only the last token
print("change only the last of 6 tokens. How far does each token's output move?")
print("token   with CLIP's causal mask   with no mask, as in T5")
c1 = attend(x, causal(6)); c2 = attend(y, causal(6)); t1 = attend(x); t2 = attend(y); R = []
for i in range(6): a = (c1[0, i] - c2[0, i]).norm().item(); b = (t1[0, i] - t2[0, i]).norm().item(); R.append((a, b)); print(f"{i:<7} {a:<25.4f} {b:.4f}")
assert all(R[i][0] == 0 for i in range(5)) and R[5][0] > 0 and all(r[1] > 0 for r in R)
print("\nCLIP: where the pooled vector comes from: the row at the end token, the first place its id appears")
ids = torch.tensor([[49406, 320, 1125, 49407, 49407, 49407]]); print("tokens", ids[0].tolist(), "-> row", (ids == 49407).int().argmax(-1).item())
assert (ids == 49407).int().argmax(-1).item() == 3
def clip_chunks(n, per=77):
    """tokenize_with_weights for single-token words: start token, up to 75 tokens, end token, pad."""
    batches = [[0]]; b = batches[0]
    for i in range(n):
        if 1 + len(b) > per - 1:
            b.append(2); b.extend([3] * (per - len(b))); b = [0]; batches.append(b)
        b.append(1)
    b.append(2); b.extend([3] * (per - len(b))); return batches
print("\ntokens in the prompt    chunks   tensor for SD 1.5   tensor for SDXL")
for n in (1, 75, 76, 150, 151):
    k = len(clip_chunks(n)); print(f"{n:<23} {k:<8} {str([1, 77 * k, 768]):<19} {[1, 77 * k, 768 + 1280]}")
assert len(clip_chunks(75)) == 1 and len(clip_chunks(76)) == 2 and all(len(c) == 77 for c in clip_chunks(151))
print("\nhow each family builds its tensor from what the encoders return (token count 77 for CLIP, 256 for T5 on Flux, 512 for Qwen3 on Klein)")
l = torch.zeros(1, 77, 768); g = torch.zeros(1, 77, 1280); t5 = torch.zeros(1, 256, 4096); q = torch.zeros(1, 3, 512, 2560)
sdxl = torch.cat([l, g], dim=-1); print("SDXL        CLIP-L and CLIP-G side by side   ", list(sdxl.shape))
sd3 = torch.cat([torch.nn.functional.pad(sdxl, (0, 4096 - 2048)), t5[:, :77]], dim=-2); print("SD3         padded to 4096, T5 on the end    ", list(sd3.shape))
print("FLUX.1      T5 tokens, CLIP-L's pooled vector", list(t5.shape), "and", [1, 768])
kl = torch.stack((q[:, 0], q[:, 1], q[:, 2]), dim=1).movedim(1, 2); kl = kl.reshape(kl.shape[0], kl.shape[1], -1); print("Klein 4B    three hidden layers side by side ", list(kl.shape))
assert sdxl.shape[-1] == 2048 and sd3.shape[-1] == 4096 and kl.shape[-1] == 7680
