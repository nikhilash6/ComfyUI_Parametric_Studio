#!/usr/bin/env python3
"""Runs ComfyUI's own scheduler, solver and prompt-weight code and stores the numbers, so tests can hold the browser ports in studio/web/university_maths.js to them on machines without ComfyUI.
Usage: python scripts/make_university_refs.py --comfy <ComfyUI dir> [--out tests/fixtures/university_refs.json]. CPU only. Imports functions only; no server, no model files."""
import argparse, json, os, sys, types
from pathlib import Path
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--comfy", required=True); ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "university_refs.json")); a = ap.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = ""; sys.path.insert(0, str(Path(a.comfy).resolve())); sys.argv = ["refs"]; os.chdir(a.comfy)
    from comfy.cli_args import args; args.cpu = True
    import torch, comfy.samplers as S, comfy.model_sampling as M, comfy.k_diffusion.sampling as K, comfy.sd1_clip as C
    torch.set_num_threads(2)
    disc = M.ModelSamplingDiscrete(); flow = M.ModelSamplingDiscreteFlow(types.SimpleNamespace(sampling_settings={"shift": 3.0}))
    out = {"sd_sigma_min": float(disc.sigma_min), "sd_sigma_max": float(disc.sigma_max), "flow3_min": float(flow.sigma_min), "flow3_max": float(flow.sigma_max), "schedules": {}, "denoise": {}, "percent": {}, "solvers": {}, "weights": {}, "ancestral": []}
    for mn, ms in (("discrete", disc), ("flow", flow)):
        for sc in ("simple", "normal", "sgm_uniform", "karras", "exponential", "ddim_uniform", "beta", "linear_quadratic", "kl_optimal"):
            for n in (4, 10, 20): out["schedules"][f"{mn}/{sc}/{n}"] = [float(x) for x in S.calculate_sigmas(ms, sc, n)]
        for p in (0.0, 0.25, 0.5, 0.8, 1.0): out["percent"][f"{mn}/{p}"] = float(ms.percent_to_sigma(p))
    for steps, dn in ((20, .6), (20, .5), (14, .5), (10, .33)):
        built = int(steps / dn); sig = S.calculate_sigmas(disc, "karras", built)[-(steps + 1):]; out["denoise"][f"karras/{steps}/{dn}"] = {"built": built, "sigmas": [float(x) for x in sig]}
    # the same mixture and exact denoiser as the page's toy world, through the real solver functions
    comps = [(-2.2, 1.2, .34), (2.2, 1.6, .33), (0., -2.2, .33)]; s = .35
    mu = torch.tensor([[c[0], c[1]] for c in comps], dtype=torch.float64); wt = torch.tensor([c[2] for c in comps], dtype=torch.float64)
    def model(x, sigma, **k):
        sg = float(sigma[0]); v = s * s + sg * sg; d2 = ((x[:, None] - mu[None]) ** 2).sum(-1); r = torch.softmax(wt.log() - d2 / (2 * v), 1)
        return ((r[..., None] * (sg * sg * mu[None] + s * s * x[:, None]) / v)).sum(1)
    sig = torch.tensor(K.get_sigmas_karras(12, 0.0291675, 14.614642).tolist(), dtype=torch.float64); x0 = torch.tensor([[3.0, -4.0]], dtype=torch.float64) * 1.0
    for name, fn in (("euler", K.sample_euler), ("heun", K.sample_heun), ("dpmpp_2m", K.sample_dpmpp_2m)):
        out["solvers"][name] = [float(v) for v in fn(model, x0.clone(), sig, disable=True)[0]]
    out["sigmas_solver"] = sig.tolist()
    for a2, b2 in ((14.6, 10.), (1.0, .5), (.2, .03)): out["ancestral"].append([a2, b2, *[float(v) for v in K.get_ancestral_step(torch.tensor(a2, dtype=torch.float64), torch.tensor(b2, dtype=torch.float64))]])
    for t in ("a cat", "(a cat)", "((a cat))", "(a cat:1.4) on a mat", "photo of (a (red:1.5) cat:0.8), night", "plain (word:notnumber) end"): out["weights"][t] = [[w, float(v)] for w, v in C.token_weights(t, 1.0)]
    Path(a.out).write_text(json.dumps(out, indent=0) + "\n"); print("wrote", a.out)
if __name__ == "__main__": main()
