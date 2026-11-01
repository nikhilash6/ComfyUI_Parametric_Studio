#!/usr/bin/env python
"""Numbers for the Sampling Lab, computed by ComfyUI's own code on the CPU, no model and no GPU.

Run with the ComfyUI venv: CUDA_VISIBLE_DEVICES= python scripts/build_sampling_measures.py <ComfyUI dir> <out.json>
Three tables:
  schedules: sigma lists from comfy.samplers.calculate_sigmas and the core scheduler nodes.
  ancestral: how get_ancestral_step splits each step into a down step and fresh noise.
  solvers:   every core sampler run on a toy problem whose exact answer is known (x0 ~ N(0, s^2)), so its model calls,
             determinism and error against steps are measured rather than quoted.
The toy problem says nothing about pictures. It measures how a solver follows an ODE, nothing more.
"""
import json, math, os, sys, time, warnings
warnings.filterwarnings("ignore")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
COMFY, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, COMFY); os.chdir(COMFY); sys.argv = sys.argv[:1]
from comfy.cli_args import args
args.cpu = True
import torch
import comfy.samplers as S, comfy.model_sampling as MS
from comfy.k_diffusion import sampling as K
from comfy.extra_samplers import uni_pc
import numpy as np

class Eps(MS.ModelSamplingDiscrete, MS.EPS): pass
class Flow(MS.ModelSamplingDiscreteFlow, MS.CONST): pass
class Flux(MS.ModelSamplingFlux, MS.CONST): pass
class _Cfg:
    def __init__(self, **k): self.sampling_settings = k
SPACES = {"sd_eps": lambda: Eps(_Cfg()), "sd3_flow_shift3": lambda: Flow(_Cfg(shift=3.0, multiplier=1000)), "flux_shift1_15": lambda: Flux(_Cfg(shift=1.15))}
STEPS = [4, 8, 12, 20, 30, 50]

def curve(t): return [round(float(x), 5) for x in t]
def extras(steps):
    """Core scheduler nodes outside SCHEDULER_HANDLERS, called through their real code."""
    from comfy_extras import nodes_custom_sampler as C, nodes_align_your_steps as A, nodes_gits as G, nodes_optimalsteps as O
    res = {}
    def take(name, fn):
        try:
            r = fn(); res[name] = curve(r[0] if isinstance(r, (tuple, list)) else getattr(r, "result", r)[0])
        except Exception as e: res[name] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    take("polyexponential (0.0292..14.61, rho 1)", lambda: C.PolyexponentialScheduler.execute(steps, 14.614642, 0.0291675, 1.0))
    take("laplace (0.0292..14.61, mu 0, beta 0.5)", lambda: C.LaplaceScheduler.execute(steps, 14.614642, 0.0291675, 0.0, 0.5))
    take("vp (beta_d 19.9, beta_min 0.1, eps_s 0.001)", lambda: C.VPScheduler.execute(steps, 19.9, 0.1, 0.001))
    for m in A.NOISE_LEVELS: take(f"align_your_steps {m}", lambda m=m: A.AlignYourStepsScheduler.execute(m, steps, 1.0))
    take("gits coeff 1.20", lambda: G.GITSScheduler.execute(1.2, steps, 1.0))
    for m in O.NOISE_LEVELS: take(f"optimal_steps {m}", lambda m=m: O.OptimalStepsScheduler.execute(m, steps, 1.0))
    return res

def schedules():
    out = {}
    for space, mk in SPACES.items():
        ms = mk(); out[space] = {"sigma_max": float(ms.sigma_max), "sigma_min": float(ms.sigma_min), "by_steps": {}}
        for n in STEPS:
            row = {}
            for name in S.SCHEDULER_NAMES:
                try: row[name] = curve(S.calculate_sigmas(ms, name, n))
                except Exception as e: row[name] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
            out[space]["by_steps"][n] = row
    out["sd_eps"]["extras_by_steps"] = {n: extras(n) for n in STEPS}
    return out

def ancestral():
    ms = SPACES["sd_eps"](); out = {}
    for name in S.SCHEDULER_NAMES:
        s = S.calculate_sigmas(ms, name, 20); rows = []
        for a, b in zip(s[:-1], s[1:]):
            d, u = K.get_ancestral_step(a, b, eta=1.0); rows.append([round(float(a), 4), round(float(b), 4), round(float(d), 4), round(float(u), 4)])
        out[name] = rows
    return out

# ---- toy problem ----
S2 = 1.0
class _Patcher:
    def __init__(self, ms): self.ms = ms
    def get_model_object(self, name): return self.ms
class Toy:
    """The exact denoiser for x0 ~ N(0, S2), wrapped the way KSampler wraps a model."""
    def __init__(self, ms, flow):
        self.flow = flow; self.calls = 0; self.batches = 0
        inner = type("I", (), {})(); inner.model_sampling = ms; inner.model_patcher = _Patcher(ms)
        inner.inner_model = type("M", (), {"model_sampling": ms})()
        self.inner_model = inner; self.sigmas = None
    def __call__(self, x, sigma, **kw):
        self.calls += 1
        s = sigma.reshape(-1, *([1] * (x.ndim - 1))) if torch.is_tensor(sigma) else torch.tensor(sigma)
        if self.flow: v = (1 - s) ** 2 * S2 + s ** 2; d = x * (1 - s) * S2 / v
        else: v = S2 + s ** 2; d = x * S2 / v
        o = kw.get("model_options") or {}
        for f in o.get("sampler_post_cfg_function", []):
            f({"denoised": d, "cond_denoised": d, "uncond_denoised": d, "model": None, "uncond": None, "cond": None, "sigma": sigma, "model_options": o, "input": x})
        return d

def sampler_fn(name):
    if name == "uni_pc": return uni_pc.sample_unipc, {}
    if name == "uni_pc_bh2": return uni_pc.sample_unipc_bh2, {}
    if name == "ddim": k = S.ksampler("euler"); return k.sampler_function, k.extra_options
    k = S.ksampler(name); return k.sampler_function, k.extra_options

def run(name, flow, steps, seed):
    dtype = torch.float32 if name.startswith("uni_pc") else torch.float64   # uni_pc mixes in float32 tensors of its own
    ms = SPACES["sd3_flow_shift3" if flow else "sd_eps"]()
    sigmas = S.calculate_sigmas(ms, "simple" if flow else "karras", steps).to(dtype)
    if flow: sigmas[0] = min(float(sigmas[0]), 0.999)
    N = 4096; g = torch.Generator().manual_seed(42)      # the start z never changes; only the sampler's noise seed does
    z = torch.randn(N, 1, 1, 1, generator=g, dtype=dtype)
    s0 = sigmas[0]; v0 = ((1 - s0) ** 2 * S2 + s0 ** 2) if flow else (S2 + s0 ** 2)
    x = z * v0.sqrt(); exact = z * math.sqrt(S2)            # the probability flow ODE keeps z, so the exact end is z * s
    m = Toy(ms, flow); fn, extra = sampler_fn(name); torch.manual_seed(seed)
    t = time.perf_counter()
    out = fn(m, x, sigmas, extra_args={"seed": seed, "model_options": {}}, callback=None, disable=True, **extra)
    return {"calls": m.calls, "out": out, "exact": exact, "secs": time.perf_counter() - t}

def solvers():
    res = {}
    for name in S.SAMPLER_NAMES:
        row = {"eps": {}, "flow": {}}
        for flow, key in ((False, "eps"), (True, "flow")):
            try:
                errs = {}; varerr = {}; calls = {}
                for n in (5, 10, 20, 40):
                    r = run(name, flow, n, 42)
                    errs[n] = float(((r["out"] - r["exact"]) ** 2).mean().sqrt()); varerr[n] = abs(float(r["out"].var()) - S2); calls[n] = r["calls"]
                same = bool(torch.allclose(run(name, flow, 20, 42)["out"], run(name, flow, 20, 43)["out"], atol=1e-6))
                row[key] = {"calls": calls, "rmse_to_exact": {k: round(v, 7) for k, v in errs.items()}, "variance_error": {k: round(v, 6) for k, v in varerr.items()}, "same_answer_with_other_noise_seed": same}
                ys = [math.log(max(errs[n], 1e-14)) for n in (10, 20, 40)]; xs = [math.log(calls[n]) for n in (10, 20, 40)]
                row[key]["slope_vs_calls"] = round(float(np.polyfit(xs, ys, 1)[0]), 2)
            except Exception as e:
                row[key] = {"error": f"{type(e).__name__}: {str(e)[:160]}"}
        res[name] = row
    return res

def spectra():
    """Radial power of the noise core samples really inject: flat for both, which is the point."""
    out = {}
    g = torch.Generator().manual_seed(7); white = torch.randn(1, 4, 256, 256, generator=g)
    bt = K.BrownianTreeNoiseSampler(torch.zeros(1, 4, 256, 256), 0.03, 14.6, seed=7)(torch.tensor(5.0), torch.tensor(4.0))
    for name, x in (("default_noise_sampler (torch.randn)", white), ("BrownianTreeNoiseSampler increment", bt)):
        f = torch.fft.fftshift(torch.fft.fft2(x.float()), dim=(-2, -1)); p = (f.abs() ** 2).mean(1)[0]
        yy, xx = torch.meshgrid(torch.arange(256) - 128, torch.arange(256) - 128, indexing="ij"); r = (xx ** 2 + yy ** 2).float().sqrt().long()
        bins = [float(p[(r >= i) & (r < i + 8)].mean()) for i in range(0, 128, 8)]; m = sum(bins) / len(bins)
        out[name] = {"radial_power_relative": [round(b / m, 3) for b in bins], "std": round(float(x.std()), 4), "mean": round(float(x.mean()), 4)}
    return out

data = {"made_by": "scripts/build_sampling_measures.py", "torch": torch.__version__, "label": "measured here", "schedules": schedules(), "ancestral_sd_eps_20": ancestral(), "solvers": solvers(), "noise_spectra": spectra()}
json.dump(data, open(OUT, "w"), separators=(",", ":"))
print("wrote", OUT, os.path.getsize(OUT))
