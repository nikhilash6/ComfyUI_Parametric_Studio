"""Which word painted what: cross-attention maps per prompt word, for SD 1.5 and SDXL UNets. Original code, AGPL-3.0-or-later.

PSN_AttentionRecord swaps every UNet cross-attention (attn2) for our own exact computation through ComfyUI's attn2 replace hook,
softmax(q kᵀ / √d) v, and on the way keeps the probabilities that each picture cell gives each prompt token. They are averaged
over heads, over every cross-attention layer (each brought to one grid) and over the sampling steps. Only the positive (cond)
half of the batch is kept. PSN_AttentionMaps turns that into one heatmap per word, sized to the picture.

The patched model draws the same picture as the plain one, up to float rounding: the sum is the same, done in float32.
DiT models (Flux, SD3, Wan) have no attn2 in a UNet, so the record node refuses them rather than return nothing.
Tested on CPU tensors in tests/test_attention_maps.py."""
import base64, io, json, math
import torch
import torch.nn.functional as F

CAT = "ParametricStudio/Attention"
MAX_SIDE = 64                     # maps are kept on a grid at most this many cells on the long side: the finest attention grid of SD 1.5 at 512 and SDXL at 1024
PHASES = ("early", "middle", "late")
START, END = 49406, 49407         # CLIP's start and end tokens; SD 1.5 and SDXL's clip_l pad with the end token


def attend(q, k, v, heads):
    """Exact attention for [b, n, h·d] projections. -> (output [b, n, h·d], probabilities [b, h, n, t]). Softmax in float32."""
    b, n, inner = q.shape; d = inner // heads
    if k.shape[0] != b: k = k.expand(b, -1, -1); v = v.expand(b, -1, -1)
    qh = q.reshape(b, n, heads, d).transpose(1, 2).float(); kh = k.reshape(b, -1, heads, d).transpose(1, 2).float(); vh = v.reshape(b, -1, heads, d).transpose(1, 2).float()
    p = torch.softmax(qh @ kh.transpose(-1, -2) * (d ** -0.5), dim=-1)
    return (p @ vh).transpose(1, 2).reshape(b, n, inner).to(q.dtype), p


def grid_of(n, extra):
    """The (h, w) of a flattened n-cell grid: from the block's own activations shape, or the latent's aspect ratio."""
    a = extra.get("activations_shape")
    if a and len(a) == 4 and a[2] * a[3] == n: return int(a[2]), int(a[3])
    o = extra.get("original_shape") or [1, 4, 64, 64]; H, W = o[-2], o[-1]; f = math.sqrt(H * W / n); h = max(1, round(H / f))
    return h, n // h


def target_of(extra):
    """The grid every layer's map is brought to: the latent grid, shrunk to at most MAX_SIDE on the long side."""
    o = extra.get("original_shape") or [1, 4, 64, 64]; H, W = int(o[-2]), int(o[-1]); f = max(1, math.ceil(max(H, W) / MAX_SIDE))
    return math.ceil(H / f), math.ceil(W / f)


class Recorder:
    """The attn2 replacement. Called by ComfyUI with q, k, v already projected; returns the attention output and keeps the maps.
    A new sampling run is spotted when σ goes up again, and starts from empty, so a cached record node is safe to reuse."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.steps = []           # per distinct σ: [sum tensor [B, T, h, w] or None, layer calls]
        self.sigma = None; self.calls = 0; self.grid = None; self.latent = None; self.layers = set()

    def __call__(self, q, k, v, extra_options):
        out, p = attend(q, k, v, int(extra_options["n_heads"]))
        self.observe(p, extra_options)
        return out

    def _step(self, extra):
        s = extra.get("sigmas")
        s = float(s.max()) if torch.is_tensor(s) and s.numel() else (float(s) if s is not None else None)
        if s is None: s = self.sigma if self.sigma is not None else 0.0
        if self.sigma is not None and s > self.sigma + 1e-6: self.reset()
        if self.sigma is None or s < self.sigma - 1e-6 or not self.steps: self.steps.append([None, 0])
        self.sigma = s
        return self.steps[-1]

    def observe(self, p, extra):
        """p: [b, heads, n, t]. Keeps the mean over heads of the first cond chunk, brought to the target grid."""
        b, _, n, t = p.shape; cou = list(extra.get("cond_or_uncond") or [0]); per = max(1, b // max(1, len(cou)))
        if 0 not in cou: return                      # an uncond-only pass: nothing of the prompt to see
        j = cou.index(0); m = p[j * per:(j + 1) * per].mean(1)        # [per, n, t]
        h, w = grid_of(n, extra); th, tw = target_of(extra)
        m = m.transpose(1, 2).reshape(per, t, h, w)
        if (h, w) != (th, tw): m = F.interpolate(m, size=(th, tw), mode="area" if h > th else "bilinear", **({} if h > th else {"align_corners": False}))
        st = self._step(extra)
        if st[0] is not None and st[0].shape != m.shape: self.reset(); st = self._step(extra)
        st[0] = m if st[0] is None else st[0] + m; st[1] += 1; self.calls += 1; self.grid = (th, tw)
        self.latent = tuple(int(x) for x in (extra.get("original_shape") or [0, 0, th, tw])[-2:]); blk = extra.get("block")
        if blk is not None: self.layers.add((tuple(blk), int(extra.get("block_index", 0))))

    def maps(self):
        """-> (overall [B, T, h, w], [early, middle, late] each [B, T, h, w] or None, steps). Each is a mean over the layer calls it holds."""
        rows = [(s, c) for s, c in self.steps if s is not None and c]
        if not rows: raise ValueError("No cross-attention was recorded. Wire the record node's MODEL into the sampler, and use an SD 1.5 or SDXL checkpoint.")
        total = sum(s for s, _ in rows) / sum(c for _, c in rows); n = len(rows); ph = []
        for i in range(3):
            part = rows[i * n // 3:(i + 1) * n // 3]
            ph.append(sum(s for s, _ in part) / sum(c for _, c in part) if part else None)
        return total, ph, n


def word_spans(rows, inv_vocab):
    """rows: the tokenizer's chunks of (token, weight, ...) for clip_l. -> (words, start positions, end and pad positions, length).
    A word is a run of BPE pieces up to the one ending in </w>, which is where CLIP's own tokenizer ends a word. Positions index the
    concatenated context, chunk c at c·77."""
    words, starts, ends, pos, cur = [], [], [], 0, None
    for chunk in rows:
        for tok in chunk:
            t = tok[0]
            if not isinstance(t, int): words.append({"word": "<embedding>", "tokens": [pos], "punct": False}); pos += 1; continue
            if t == START: starts.append(pos)
            elif t == END: ends.append(pos)
            else:
                piece = str(inv_vocab.get(t, "?")); done = piece.endswith("</w>"); piece = piece[:-4] if done else piece
                if cur is None: cur = {"word": "", "tokens": []}
                cur["word"] += piece; cur["tokens"].append(pos)
                if done: cur["punct"] = not any(ch.isalnum() for ch in cur["word"]); words.append(cur); cur = None
            pos += 1
    if cur is not None: cur["punct"] = not any(ch.isalnum() for ch in cur["word"]); words.append(cur)
    return words, starts, ends, pos


def fold(m, length):
    """ComfyUI repeats a shorter prompt to the batch's common length, so its keys appear several times. Summing the copies gives back
    the attention each real position got. m: [B, T, h, w]."""
    T = m.shape[1]
    if T == length: return m
    if T % length: raise ValueError(f"The text here has {length} tokens but the sampler saw {T}. Wire the same prompt into both.")
    return m.reshape(m.shape[0], T // length, length, *m.shape[2:]).sum(1)


def stretch(x):
    """A map stretched between its own lowest and highest value, 0..1. SDXL puts most of a word's attention evenly over the whole picture,
    so its maps sit on a high floor; the shape is what rises above it."""
    x = x.float(); lo, hi = float(x.min()), float(x.max())
    return (x - lo) / (hi - lo) if hi > lo else x * 0


def b64u8(x):
    """A [h, w] map stretched to 0..255 between its own floor and peak, as base64 bytes, row by row."""
    return base64.b64encode((stretch(x) * 255).round().clamp(0, 255).to(torch.uint8).cpu().numpy().tobytes()).decode()


def summarize(total, phases, steps, words, starts, ends, length, item=0):
    """The maps of one picture of the batch as plain data. share: the mean over the picture of the attention the word got.
    floor and peak: its lowest and highest values, so a reader can bring the 0 to 255 maps back to real attention: floor + byte / 255 · (peak - floor)."""
    tot = fold(total, length)[item]; ph = [fold(p, length)[item] if p is not None else None for p in phases]
    out = {"version": 1, "map_size": list(tot.shape[-2:]), "steps": steps, "tokens": length, "words": []}
    for w in words:
        m = tot[w["tokens"]].sum(0)
        out["words"].append({"word": w["word"], "tokens": w["tokens"], "punct": bool(w.get("punct")), "share": round(float(m.mean()), 6), "floor": round(float(m.min()), 6), "peak": round(float(m.max()), 6), "map": b64u8(m),
                             "phases": [b64u8(p[w["tokens"]].sum(0)) if p is not None else None for p in ph]})
    out["start_share"] = round(float(tot[starts].sum(0).mean()), 6) if starts else 0.0
    out["end_share"] = round(float(tot[ends].sum(0).mean()), 6) if ends else 0.0
    return out


def upsample(m, hw):
    """[h, w] -> [H, W], bilinear, stretched to 0..1 between its own floor and peak."""
    return stretch(F.interpolate(m[None, None].float(), size=hw, mode="bilinear", align_corners=False)[0, 0]).clamp(0, 1)


STOPS = ((0.0, (0.02, 0.02, 0.10)), (0.3, (0.35, 0.05, 0.45)), (0.6, (0.85, 0.25, 0.20)), (0.85, (0.98, 0.65, 0.10)), (1.0, (1.0, 0.98, 0.75)))
def heat(x):
    """[H, W] in 0..1 -> [H, W, 3] colours, dark violet through red to pale yellow. Our own ramp."""
    out = torch.zeros(*x.shape, 3)
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        t = ((x - a) / (b - a)).clamp(0, 1)[..., None]; inside = ((x >= a) & (x <= b))[..., None]
        out = torch.where(inside, torch.tensor(ca) * (1 - t) + torch.tensor(cb) * t, out)
    return out


def overlay(img, m, alpha=0.6):
    """img [H, W, 3] in 0..1, m [H, W] in 0..1 -> the picture dimmed where the word did not look, coloured where it did."""
    a = (alpha * m)[..., None]; dim = img * (0.3 + 0.7 * m[..., None])
    return (dim * (1 - a) + heat(m) * a).clamp(0, 1)


def sheet(img, tiles, labels, cols=4):
    """A grid of the picture and its overlays, each with a label, as one IMAGE [1, H', W', 3]."""
    from PIL import Image, ImageDraw
    import numpy as np
    H, W = img.shape[:2]; items = [img] + tiles; names = ["picture"] + labels; cols = max(1, min(cols, len(items))); rows = math.ceil(len(items) / cols); bar = 22
    canvas = Image.new("RGB", (cols * W, rows * (H + bar)), (12, 12, 14)); d = ImageDraw.Draw(canvas)
    for i, (t, name) in enumerate(zip(items, names)):
        x, y = (i % cols) * W, (i // cols) * (H + bar)
        canvas.paste(Image.fromarray((t.clamp(0, 1) * 255).round().to(torch.uint8).cpu().numpy()), (x, y + bar)); d.text((x + 6, y + 5), name[:48], fill=(235, 235, 235))
    return torch.from_numpy(np.asarray(canvas).astype("float32") / 255.0)[None]


class PSN_AttentionRecord:
    """Record cross-attention while sampling, for SD 1.5 and SDXL UNets. Wire its MODEL into the sampler and its ATTENTION into Attention Maps.
    The picture is the same as without it, up to float rounding; sampling is a little slower because attention runs unfused in float32."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"model": ("MODEL",)}}
    RETURN_TYPES = ("MODEL", "PSN_ATTENTION"); RETURN_NAMES = ("model", "attention"); FUNCTION = "run"; CATEGORY = CAT

    def run(self, model):
        dm = getattr(getattr(model, "model", None), "diffusion_model", None)
        if dm is None or type(dm).__name__ != "UNetModel": raise ValueError("Attention maps need a UNet with cross-attention: SD 1.5 or SDXL. This model has none.")
        rec = Recorder(); m = model.clone()
        for name, count in (("input", 12), ("middle", 1), ("output", 12)):
            for i in range(count): m.set_model_attn2_replace(rec, name, i)
        return (m, rec)


class PSN_AttentionMaps:
    """One heatmap per prompt word: where in the picture that word was attended to, averaged over heads, layers and steps.
    Outputs a sheet of the picture with one overlay per word, the maps as a MASK batch in word order (each stretched between its own floor and peak), and the data as JSON."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"attention": ("PSN_ATTENTION",), "clip": ("CLIP",), "text": ("STRING", {"multiline": True, "default": "a red hat on a wooden table"}), "image": ("IMAGE",),
                                               "skip_punctuation": ("BOOLEAN", {"default": True})}}
    RETURN_TYPES = ("IMAGE", "MASK", "STRING"); RETURN_NAMES = ("sheet", "maps", "json"); FUNCTION = "run"; CATEGORY = CAT; OUTPUT_NODE = True

    def run(self, attention, clip, text, image, skip_punctuation=True):
        tk = getattr(clip.tokenizer, "clip_l", None); rows = clip.tokenize(text).get("l")
        if tk is None or rows is None or not hasattr(tk, "inv_vocab"): raise ValueError("Attention maps read CLIP-L tokens, which SD 1.5 and SDXL use. This text encoder has none.")
        words, starts, ends, length = word_spans(rows, tk.inv_vocab)
        total, phases, steps = attention.maps()
        data = summarize(total, phases, steps, words, starts, ends, length)
        data["latent"] = list(attention.latent or ()); data["layers"] = len(attention.layers); data["calls"] = attention.calls
        shown = [i for i, w in enumerate(data["words"]) if not (skip_punctuation and w["punct"])]
        H, W = image.shape[1], image.shape[2]; tot = fold(total, length)[0]
        ups = [upsample(tot[words[i]["tokens"]].sum(0), (H, W)) for i in shown]
        img = image[0, ..., :3].float().cpu()
        grid = sheet(img, [overlay(img, u.cpu()) for u in ups], [f"{data['words'][i]['word']}  {data['words'][i]['share'] * 100:.1f}%" for i in shown])
        masks = torch.stack(ups).cpu() if ups else torch.zeros(1, H, W)
        js = json.dumps(data)
        return {"ui": {"psn_attention": [data]}, "result": (grid, masks, js)}


NODE_CLASS_MAPPINGS = {"PSN_AttentionRecord": PSN_AttentionRecord, "PSN_AttentionMaps": PSN_AttentionMaps}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_AttentionRecord": "Attention Record (which word painted what)", "PSN_AttentionMaps": "Attention Maps per word"}
