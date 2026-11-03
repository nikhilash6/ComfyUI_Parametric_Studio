#!/usr/bin/env python3
"""Pack a routing record into studio/moe/ for the "Inside a mixture of experts" page (studio/feature_moe.py).

The record is made once, outside the studio, by a recorder that loads Qwen3-Omni-30B-A3B-Captioner (AWQ 4-bit) in its own venv, hooks each
layer's router (mlp.gate) and runs invented text through the language model. It writes routing.json (showcase prompts: every token's top-k
experts and weights per layer) and load.json (how often each expert was picked, per text category, plus its most frequent tokens).
This script checks the shapes, keeps only what the page reads, and refuses anything that looks like a path on the recording machine.

usage: pack_moe_routing.py --routing routing.json --load load.json [--out studio/moe]"""
import argparse, gzip, json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BOX = re.compile(r"(?:/home/|/mnt/|/tmp/|~/)")
META_KEYS = ("model", "hf_base", "hf_quant", "license", "layers", "experts", "top_k", "norm_topk_prob", "hidden", "moe_intermediate", "path", "recorded", "load_s", "peak_alloc_gib", "peak_card_gib", "versions", "corpus_tokens")


def check_prompt(p, L, E, K):
    T = len(p["tokens"])
    assert T and len(p["experts"]) == T and len(p["weights"]) == T and len(p["entropy"]) == T, p["id"]
    for t in range(T):
        assert len(p["experts"][t]) == L and len(p["weights"][t]) == L and len(p["entropy"][t]) == L, (p["id"], t)
        for l in range(L):
            e, w = p["experts"][t][l], p["weights"][t][l]
            assert len(e) == K == len(w) and len(set(e)) == K and all(0 <= x < E for x in e), (p["id"], t, l)
            assert abs(sum(w) - 1000) <= K and w == sorted(w, reverse=True), (p["id"], t, l, w)      # renormalised top-k, per mille, largest first


def pack(routing, load, extra_meta=None):
    meta = {k: v for k, v in {**routing["meta"], **load["meta"], **(extra_meta or {})}.items() if k in META_KEYS}
    L, E, K = meta["layers"], meta["experts"], meta["top_k"]
    prompts = {}
    for p in routing["prompts"]:
        check_prompt(p, L, E, K)
        prompts[p["id"]] = {k: p[k] for k in ("id", "label", "text", "tokens", "experts", "weights", "entropy")}
    cats = []
    for name, c in load["categories"].items():
        assert len(c["count"]) == L and all(len(r) == E for r in c["count"]), name
        assert all(sum(r) == c["tokens"] * K for r in c["count"]), name                             # every token fills K slots in every layer
        cats.append({"name": name, "tokens": c["tokens"], "texts": c["texts"], "count": c["count"]})
    tops = load["top_tokens"]; assert len(tops) == L and all(len(r) == E for r in tops)
    index = {"meta": meta, "prompts": [{"id": p["id"], "label": p["label"], "tokens": len(p["tokens"])} for p in prompts.values()],
             "categories": [{"name": c["name"], "tokens": c["tokens"], "texts": c["texts"]} for c in cats]}
    out = {"index.json": json.dumps(index, ensure_ascii=False, separators=(",", ":")),
           "prompts.json.gz": json.dumps(prompts, ensure_ascii=False, separators=(",", ":")),
           "load.json.gz": json.dumps({"categories": cats, "top_tokens": tops}, ensure_ascii=False, separators=(",", ":"))}
    for name, text in out.items():
        if BOX.search(text): raise SystemExit(f"{name} holds something that looks like a path on the recording machine; not packing it")
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--routing", required=True); ap.add_argument("--load", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "studio", "moe")); ap.add_argument("--peak-card-gib", type=float, help="the card memory the recording measured, if it was measured outside the record")
    a = ap.parse_args()
    out = pack(json.load(open(a.routing, encoding="utf8")), json.load(open(a.load, encoding="utf8")), {"peak_card_gib": a.peak_card_gib} if a.peak_card_gib else None)
    os.makedirs(a.out, exist_ok=True)
    for name, text in out.items():
        data = text.encode("utf8"); path = os.path.join(a.out, name)
        with open(path, "wb") as f: f.write(gzip.compress(data, 9, mtime=0) if name.endswith(".gz") else data)
        print(f"wrote {name}: {os.path.getsize(path) / 1024:.0f} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
