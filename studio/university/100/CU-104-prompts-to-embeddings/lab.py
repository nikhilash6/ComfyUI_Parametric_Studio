# CU-104 lab: how text becomes numbers. Standard library only, well under a second.
# Run: python lab.py
# Part 1 learns byte-pair merges (Sennrich et al. 2015, Algorithm 1) on their tiny vocabulary and splits unseen words with them.
# Part 2 shows that an embedding is a table row, and that one layer of causal self-attention (the kind CLIP's text encoder uses) makes the output depend on context.
# Part 3 does the arithmetic of ComfyUI's 77-token chunks. The weights are random, so only properties that hold for any weights are claimed.
import math, random

# Part 1. Byte-pair merges on the vocabulary of the paper's listing: low x5, lower x2, newest x6, widest x3.
def learn_bpe(vocab, n_merges):
    vocab = {tuple(w.split()): f for w, f in vocab.items()}
    merges = []
    for _ in range(n_merges):
        pairs = {}
        for word, f in vocab.items():
            for a, b in zip(word, word[1:]): pairs[(a, b)] = pairs.get((a, b), 0) + f
        best = max(pairs, key=pairs.get); merges.append(best)       # the most frequent neighbouring pair; the first one counted wins a tie
        new = {}
        for word, f in vocab.items():
            out, i = [], 0
            while i < len(word):
                if i < len(word) - 1 and (word[i], word[i + 1]) == best: out.append(word[i] + word[i + 1]); i += 2
                else: out.append(word[i]); i += 1
            new[tuple(out)] = f
        vocab = new
    return merges

def split_word(word, merges):                                       # apply the merges in the order they were learned
    symbols = list(word) + ["</w>"]
    for a, b in merges:
        i = 0
        while i < len(symbols) - 1:
            if symbols[i] == a and symbols[i + 1] == b: symbols[i:i + 2] = [a + b]
            else: i += 1
    return symbols

merges = learn_bpe({"l o w </w>": 5, "l o w e r </w>": 2, "n e w e s t </w>": 6, "w i d e s t </w>": 3}, 10)
print("merges learned, in order:", ", ".join("+".join(m) for m in merges))
print("\nword      pieces")
for w in ("low", "newest", "lowest", "wider", "newer", "slow"):
    print(f"{w:<9} {' '.join(split_word(w, merges))}")
assert merges[0] == ("e", "s") and merges[4] == ("lo", "w") and split_word("lowest", merges) == ["low", "est</w>"]

# Part 2. Token ids index a table of vectors; the table row does not know its neighbours, the attention layer does.
rng = random.Random(0)
VOCAB = ["<s>", "</s>", "a", "river", "money", "bank", "sat", "by"]
D = 8
def table(rows, cols, scale): return [[rng.gauss(0, scale) for _ in range(cols)] for _ in range(rows)]
E, POS = table(len(VOCAB), D, 1.0), table(8, D, 0.5)               # one row per token id, one row per position
WQ, WK, WV = table(D, D, D ** -0.5), table(D, D, D ** -0.5), table(D, D, D ** -0.5)
def matvec(v, W): return [sum(v[i] * W[i][j] for i in range(len(v))) for j in range(len(W[0]))]
def ids(words): return [VOCAB.index(w) for w in words]
one_hot = lambda i: [1.0 if j == i else 0.0 for j in range(len(VOCAB))]
gap = lambda u, v: max(abs(a - b) for a, b in zip(u, v))

def attend(words, causal=True):
    """One head of scaled dot-product attention, softmax(Q K^T / sqrt(D)) V, plus the residual connection; returns one vector per token."""
    x = [[e + p for e, p in zip(E[i], POS[pos])] for pos, i in enumerate(ids(words))]    # token embedding + position embedding
    q, k, v = [matvec(r, WQ) for r in x], [matvec(r, WK) for r in x], [matvec(r, WV) for r in x]
    out = []
    for i in range(len(x)):
        scores = [sum(a * b for a, b in zip(q[i], k[j])) / math.sqrt(D) if (j <= i or not causal) else float("-inf") for j in range(len(x))]
        top = max(scores); w = [math.exp(s - top) for s in scores]; z = sum(w)
        out.append([x[i][c] + sum(w[j] / z * v[j][c] for j in range(len(x))) for c in range(D)])
    return x, out

print("\nlookup: one-hot vector times the table, against reading the row; largest difference over all ids:",
      max(gap(matvec(one_hot(i), E), E[i]) for i in range(len(VOCAB))))
A, B, C = ["<s>", "river", "bank", "</s>"], ["<s>", "money", "bank", "</s>"], ["<s>", "river", "sat", "</s>"]
xa, ya = attend(A); xb, yb = attend(B); xc, yc = attend(C)
_, ya_open = attend(A, causal=False); _, yc_open = attend(C, causal=False)
print(f"'bank' after 'river' against 'bank' after 'money':")
print(f"  table row plus position, before attention: largest difference {gap(xa[2], xb[2]):.6f}")
print(f"  output of one causal attention layer:      largest difference {gap(ya[2], yb[2]):.6f}")
print(f"'river' in 'river bank' against 'river sat' (only the next word differs):")
print(f"  with the causal mask:    largest difference {gap(ya[1], yc[1]):.6f}")
print(f"  without the mask:        largest difference {gap(ya_open[1], yc_open[1]):.6f}")
print(f"output at the end marker, 'river bank' against 'money bank': largest difference {gap(ya[3], yb[3]):.6f}")
assert gap(xa[2], xb[2]) == 0 and gap(ya[2], yb[2]) > 0.01 and gap(ya[1], yc[1]) == 0 and gap(ya_open[1], yc_open[1]) > 0.01

# Part 3. ComfyUI's chunking for one-token words: start marker, up to 75 tokens, end marker, padded to 77, each chunk encoded alone and joined.
CTX, CLIP_L, CLIP_G = 77, 768, 1280                                  # comfy/sd1_clip_config.json, comfy/clip_config_bigg.json
print(f"\n{'tokens in prompt':<18}{'chunks':<9}{'SD 1.x conditioning':<24}SDXL conditioning (768 + 1280 wide)")
for n in (5, 75, 76, 100, 150):
    k = max(1, -(-n // (CTX - 2)))
    print(f"{n:<18}{k:<9}{f'[1, {CTX * k}, {CLIP_L}]':<24}[1, {CTX * k}, {CLIP_L + CLIP_G}]")
