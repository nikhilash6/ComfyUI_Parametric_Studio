"""Cross-attention maps per word (psn_nodes/attention_maps.py), on CPU tensors: the swapped-in attention is exact, the recorder keeps the cond half,
averages heads, layers and steps, restarts on a new run, words follow CLIP's </w> ends, folded copies add back up, and the nodes refuse what they can't read."""
import base64, json, types
import pytest, torch
import torch.nn.functional as F
from psn_nodes import attention_maps as A

def qkv(b=2, n=16, t=7, heads=4, d=8, seed=0):
    g = torch.Generator().manual_seed(seed)
    return (torch.randn(b, n, heads * d, generator=g), torch.randn(b, t, heads * d, generator=g), torch.randn(b, t, heads * d, generator=g))

def extra(n=16, sigma=10.0, cou=(1, 0), H=4, W=4, heads=4, block=("input", 1)):
    return {"n_heads": heads, "cond_or_uncond": list(cou), "sigmas": torch.tensor([sigma]), "activations_shape": [2, 8, H, W], "original_shape": [1, 4, H, W], "block": block, "block_index": 0}

def test_attend_matches_torch_sdpa_and_probabilities_sum_to_one():
    q, k, v = qkv(); out, p = A.attend(q, k, v, 4)
    ref = F.scaled_dot_product_attention(q.view(2, 16, 4, 8).transpose(1, 2), k.view(2, 7, 4, 8).transpose(1, 2), v.view(2, 7, 4, 8).transpose(1, 2)).transpose(1, 2).reshape(2, 16, 32)
    assert torch.allclose(out, ref, atol=1e-5) and p.shape == (2, 4, 16, 7) and torch.allclose(p.sum(-1), torch.ones(2, 4, 16), atol=1e-6)
    q1, k1, v1 = q.half(), k.half(), v.half(); o1, _ = A.attend(q1, k1[:1], v1[:1], 4); assert o1.dtype == torch.float16 and o1.shape == q1.shape   # a batch-1 context is broadcast

def test_recorder_keeps_the_cond_half_mean_over_heads():
    q, k, v = qkv(); r = A.Recorder(); out = r(q, k, v, extra()); _, p = A.attend(q, k, v, 4)
    assert torch.allclose(out, A.attend(q, k, v, 4)[0])
    total, ph, steps = r.maps(); want = p[1].mean(0).T.reshape(1, 7, 4, 4)      # cond_or_uncond (1, 0): the second chunk is the prompt
    assert steps == 1 and torch.allclose(total, want, atol=1e-6) and r.grid == (4, 4)
    r2 = A.Recorder(); r2(q, k, v, extra(cou=(0, 1))); assert torch.allclose(r2.maps()[0], p[0].mean(0).T.reshape(1, 7, 4, 4), atol=1e-6)
    r3 = A.Recorder(); r3(q, k, v, extra(cou=(1, 1))); r3.steps or None
    with pytest.raises(ValueError, match="No cross-attention"): r3.maps()

def test_layers_of_different_size_meet_on_one_grid_and_steps_are_averaged():
    r = A.Recorder(); g = torch.Generator().manual_seed(3)
    for sigma in (10.0, 5.0, 1.0):
        for n, H in ((64, 8), (16, 4)):
            q = torch.randn(2, n, 32, generator=g); k = torch.randn(2, 7, 32, generator=g); v = torch.randn(2, 7, 32, generator=g)
            e = extra(n=n, sigma=sigma, H=H, W=H); e["original_shape"] = [1, 4, 8, 8]; e["activations_shape"] = [2, 8, H, H]; r(q, k, v, e)
    total, ph, steps = r.maps()
    assert steps == 3 and total.shape == (1, 7, 8, 8) and all(p is not None and p.shape == total.shape for p in ph) and r.calls == 6
    assert torch.allclose(total.sum(1), torch.ones(1, 8, 8), atol=1e-5)          # still a probability over tokens at every cell
    assert torch.allclose(total, sum(ph) / 3, atol=1e-6)                           # three steps, one in each phase, two layers each

def test_a_new_run_starts_from_empty():
    q, k, v = qkv(); r = A.Recorder(); r(q, k, v, extra(sigma=10)); r(q, k, v, extra(sigma=2)); assert r.maps()[2] == 2
    r(q, k, v, extra(sigma=14)); assert r.maps()[2] == 1 and r.calls == 1        # σ went up: the old run is gone

def test_big_latents_shrink_to_the_cap():
    e = {"original_shape": [1, 4, 128, 96]}; assert A.target_of(e) == (64, 48)
    assert A.target_of({"original_shape": [1, 4, 64, 64]}) == (64, 64) and A.grid_of(1024, {"original_shape": [1, 4, 128, 128]}) == (32, 32)

VOCAB = {49406: "<|startoftext|>", 49407: "<|endoftext|>", 1: "a</w>", 2: "red</w>", 3: "astro", 4: "labe</w>", 5: ",</w>", 6: "hat</w>"}
def test_words_follow_clip_word_ends_across_chunks():
    rows = [[(49406, 1.0), (1, 1.0), (2, 1.2), (3, 1.0), (4, 1.0), (5, 1.0), (6, 1.0), (49407, 1.0), (49407, 1.0)], [(49406, 1.0), (2, 1.0), (49407, 1.0)]]
    words, starts, ends, n = A.word_spans(rows, VOCAB)
    assert [(w["word"], w["tokens"], w["punct"]) for w in words] == [("a", [1], False), ("red", [2], False), ("astrolabe", [3, 4], False), (",", [5], True), ("hat", [6], False), ("red", [10], False)]
    assert starts == [0, 9] and ends == [7, 8, 11] and n == 12

def test_fold_adds_the_repeated_copies_back():
    m = torch.rand(1, 6, 2, 2); assert torch.equal(A.fold(m, 6), m)
    two = torch.cat([m, m], 1) / 2; assert torch.allclose(A.fold(two, 6), m)
    with pytest.raises(ValueError, match="same prompt"): A.fold(torch.rand(1, 7, 2, 2), 6)

def test_summary_shares_peaks_and_maps_round_trip():
    g = torch.Generator().manual_seed(1); total = torch.softmax(torch.randn(1, 12, 8, 8, generator=g), 1)
    words, starts, ends, n = A.word_spans([[(49406, 1.0), (1, 1.0), (2, 1.0), (3, 1.0), (4, 1.0), (6, 1.0), (49407, 1.0)] + [(49407, 1.0)] * 5], VOCAB)
    d = A.summarize(total, [total, total, None], 3, words, starts, ends, n)
    assert d["map_size"] == [8, 8] and [w["word"] for w in d["words"]] == ["a", "red", "astrolabe", "hat"] and d["words"][2]["tokens"] == [3, 4]
    s = sum(w["share"] for w in d["words"]) + d["start_share"] + d["end_share"]; assert abs(s - 1) < 1e-4    # every bit of attention is accounted for
    w = d["words"][2]; m = total[0, 3] + total[0, 4]; u8 = torch.tensor(list(base64.b64decode(w["map"])), dtype=torch.float32).view(8, 8)
    assert abs(w["peak"] - float(m.max())) < 1e-5 and abs(w["floor"] - float(m.min())) < 1e-5 and u8.min() == 0 and u8.max() == 255
    assert torch.allclose(w["floor"] + u8 / 255 * (w["peak"] - w["floor"]), m, atol=(w["peak"] - w["floor"]) / 255) and w["phases"][2] is None
    json.dumps(d)

def test_heat_overlay_and_sheet_shapes():
    x = torch.linspace(0, 1, 20).view(4, 5); h = A.heat(x); assert h.shape == (4, 5, 3) and h.min() >= 0 and h.max() <= 1
    assert torch.allclose(h[0, 0], torch.tensor(A.STOPS[0][1])) and torch.allclose(h[-1, -1], torch.tensor(A.STOPS[-1][1]))
    img = torch.rand(16, 16, 3); o = A.overlay(img, torch.zeros(16, 16)); assert torch.allclose(o, img * 0.3)                 # where nobody looked, the picture is dimmed
    s = A.sheet(img, [o, o, o], ["red", "hat", "table"], cols=2); assert s.shape == (1, 2 * (16 + 22), 32, 3)
    u = A.upsample(torch.rand(4, 4) * 0.1 + 0.8, (16, 16)); assert u.shape == (16, 16) and abs(float(u.max()) - 1) < 1e-6 and float(u.min()) < 1e-6     # a high floor is stretched away
    assert torch.equal(A.stretch(torch.full((3, 3), 0.4)), torch.zeros(3, 3))

class FakeTok: inv_vocab = VOCAB
class FakeClip:
    tokenizer = types.SimpleNamespace(clip_l=FakeTok())
    def tokenize(self, text): return {"l": [[(49406, 1.0), (2, 1.0), (6, 1.0), (49407, 1.0)]]}

def test_nodes_wire_up_and_refuse_what_they_cannot_read():
    assert set(A.NODE_CLASS_MAPPINGS) == {"PSN_AttentionRecord", "PSN_AttentionMaps"} and all(c.FUNCTION == "run" for c in A.NODE_CLASS_MAPPINGS.values())
    dit = types.SimpleNamespace(model=types.SimpleNamespace(diffusion_model=types.SimpleNamespace()))
    with pytest.raises(ValueError, match="SD 1.5 or SDXL"): A.PSN_AttentionRecord().run(dit)
    class UNetModel: pass
    calls = []
    class MP:
        model = types.SimpleNamespace(diffusion_model=UNetModel())
        def clone(self): return self
        def set_model_attn2_replace(self, fn, name, i): calls.append((name, i, fn))
    m, rec = A.PSN_AttentionRecord().run(MP()); assert len(calls) == 25 and all(c[2] is rec for c in calls)
    q, k, v = qkv(t=4); rec(q, k, v, extra())
    out = A.PSN_AttentionMaps().run(rec, FakeClip(), "red hat", torch.rand(1, 32, 32, 3))
    sheet, masks, js = out["result"]; d = json.loads(js)
    assert [w["word"] for w in d["words"]] == ["red", "hat"] and masks.shape == (2, 32, 32) and sheet.shape[-1] == 3 and out["ui"]["psn_attention"][0]["steps"] == 1
    with pytest.raises(ValueError, match="CLIP-L"): A.PSN_AttentionMaps().run(rec, types.SimpleNamespace(tokenizer=object(), tokenize=lambda t: {"t5xxl": []}), "x", torch.rand(1, 8, 8, 3))
