# CU-413 lab: a toy text and image embedding, to see what a similarity score can and can't tell. Vectors are made up: no CLIP model runs here.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = 256; names = ["red", "blue", "car", "ball", "dog", "cat", "beach", "city", "night", "day"]; c = {n: torch.nn.functional.normalize(torch.randn(D), dim=0) for n in names}
def enc(words): return torch.nn.functional.normalize(sum(c[w] for w in words), dim=0)
def cos(a, b): return (a @ b).item()
def see(words, noise=.2, seed=0):
    g = torch.Generator().manual_seed(seed); return torch.nn.functional.normalize(sum(c[w] for w in words) + noise * torch.randn(D, generator=g), dim=0)
def clipscore(img, txt): return 2.5 * max(cos(img, txt), 0)                # Hessel et al. 2021: w = 2.5, negative clipped to 0
img = see(["red", "car", "beach"]); caps = {"red car on a beach": ["red", "car", "beach"], "red car": ["red", "car"], "red car in a city": ["red", "car", "city"], "blue ball at night": ["blue", "ball", "night"]}
print("image holds: red, car, beach")
print("caption               cosine   score (w = 2.5)")
sc = {}
for k, w in caps.items(): sc[k] = cos(img, enc(w)); print(f"{k:<21s} {sc[k]:<8.3f} {clipscore(img, enc(w)):.3f}")
assert sc["red car on a beach"] > sc["red car in a city"] > sc["blue ball at night"]
# A short caption can score nearly as well, or better: a score doesn't say what's missing.
print(f"\nimage with one more thing, a dog, against the old caption: {cos(see(['red', 'car', 'beach', 'dog']), enc(caps['red car on a beach'])):.3f}, so extra things only lower it a little")
# Binding: these embeddings ignore which word goes with which object. A real encoder does better, but tests like this are why people use checklists.
a, b = enc(["red", "car", "blue", "ball"]), enc(["blue", "car", "red", "ball"]); print(f"\n'red car, blue ball' against 'blue car, red ball': cosine {cos(a, b):.3f}"); assert cos(a, b) > .999
# Different spaces: a vector from another encoder has random directions, so its cosine is about 0 even for the same concept.
R = torch.linalg.qr(torch.randn(D, D))[0]; print(f"same caption, vector from a different encoder (a random rotation here): cosine {cos(img, R @ enc(caps['red car on a beach'])):.3f}"); assert abs(cos(img, R @ enc(caps['red car on a beach']))) < .3
# Retrieval: only the ranking against other captions means anything, and that needs a good set of wrong ones.
pool = ["red car on a beach"] + [f"{a} {b} {p}" for a in ("red", "blue") for b in ("car", "ball", "dog", "cat") for p in ("beach", "city", "night") if not (a == "red" and b == "car" and p == "beach")]
sc2 = sorted(pool, key=lambda s: -cos(img, enc(s.replace(" on a", "").split()))); print(f"\nrank of the true caption among {len(pool)} captions: {sc2.index('red car on a beach') + 1}"); assert sc2.index("red car on a beach") == 0
# A checklist turns a prompt into questions. Here two renders of one prompt, marked by hand by us from the two pictures on the page.
items = ["brass astrolabe", "oak table", "stack of sea charts", "window light", "shallow depth of field"]
euler = [1, 1, 0, 1, 0]; anc = [1, 0, 1, 0, 1]
print("\nitem                    euler  euler ancestral   (one seed, marked by one reader)")
for i, e, f in zip(items, euler, anc): print(f"{i:<23s} {e:<6d} {f}")
print(f"score                   {sum(euler) / 5:<6.2f} {sum(anc) / 5:.2f}"); assert sum(euler) == sum(anc) == 3
print("the same total hides different failures. each row tells you what to fix")
