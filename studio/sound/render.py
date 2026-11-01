"""One sound recipe to one audio array: synth layers, each with its chain, mixed, then the mix chain and the master. Only the synth engine came across; a layer that needs a model is refused."""
import numpy as np
from studio.sound import chains as CH, dsp as D, synth as SY
MAX_SECONDS = 30.0
class SoundError(Exception): pass
def clean(raw):
    """A recipe with every field checked against the real sounds and presets. Raises SoundError for anything that cannot be made."""
    layers = raw.get("layers") if isinstance(raw, dict) else None
    if not layers: raise SoundError("a sound recipe needs at least one layer")
    out = []
    for i, l in enumerate(layers):
        if l.get("engine", "synth") != "synth": raise SoundError(f"layer {i + 1}: only the synth engine is available here")
        k = SY.KINDS.get(str(l.get("sound")))
        if not k: raise SoundError(f"layer {i + 1}: unknown sound {l.get('sound')!r}")
        try: p, _ = SY.resolve_params(k, l.get("params")); chain, _ = CH.resolve_chain(l.get("chain"))
        except (SY.SynthError, CH.ChainError) as e: raise SoundError(f"layer {i + 1}: {e}") from None
        out.append({"sound": k.id, "params": p, "chain": chain, "at": float(min(max(float(l.get("at", 0.0)), 0.0), MAX_SECONDS)), "gain_db": float(min(max(float(l.get("gain_db", 0.0)), -30.0), 12.0)), **({"seconds": float(l["seconds"])} if l.get("seconds") is not None else {})})
    try: mix_chain, _ = CH.resolve_chain(raw.get("chain"))
    except CH.ChainError as e: raise SoundError(f"chain: {e}") from None
    master, _ = CH.resolve_master(raw.get("master"))
    return {"title": str(raw.get("title") or "Sound")[:80], "kind": raw.get("kind", "noise"), "seconds": float(min(max(float(raw.get("seconds") or 2.0), 0.3), MAX_SECONDS)), "seed": int(raw.get("seed", 1)) & 0x7FFFFFFF, "layers": out, "chain": mix_chain, "master": master}
def render(recipe):
    """-> (audio array, report). The same recipe and seed give the same sound."""
    r = clean(recipe); parts = []
    for i, l in enumerate(r["layers"]):
        seed = r["seed"] + 101 * i; x, _ = SY.render(l["sound"], l["params"], seconds=l.get("seconds"), seed=seed)
        if l["chain"]["steps"]: x = CH.run_chain(x, l["chain"], seed=seed)
        parts.append((D.to_mono(x) if x.ndim == 2 else x, int(l["at"] * D.SR), l["gain_db"]))
    n = max(D.n_of(r["seconds"]), max(at + len(p) for p, at, _ in parts)); mix = D.mix_at(parts, min(n, D.n_of(MAX_SECONDS)))
    if r["chain"]["steps"]: mix = CH.run_chain(mix, r["chain"], seed=r["seed"] + 7)
    master = {**r["master"], "max_seconds": r["master"].get("max_seconds") or r["seconds"]}; mix = np.nan_to_num(mix)
    if D.peak(mix) < 1e-6: raise SoundError("the sound came out silent")
    audio, rep = CH.finish(mix, master)
    return audio, {"title": r["title"], "master": rep}
def to_wav(recipe, path):
    audio, rep = render(recipe); D.write_wav(path, audio, D.SR, 16); return rep
