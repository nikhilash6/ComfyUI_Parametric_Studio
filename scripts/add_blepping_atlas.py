#!/usr/bin/env python3
"""Add Overly Complicated Sampling (blepping) and the rest of Skoogeer-Noise (ttulttul) to the Sampling Lab atlas.

The entries are our own words and equations, written from reading the source at a pinned commit. Every evidence line is checked
against a copy of the pack on disk before anything is written: the symbol must appear on the cited line, or the script stops.
Pack code is only opened as text. It is never imported or run, and none of it is copied into the atlas.
Also marks every provider that belongs to blepping (bleh, Sonar, OCS) so method pages can link to the blepping page.

Usage: BLEPPING_PACKS=<dir holding ComfyUI-bleh, ComfyUI-sonar, comfyui_overly_complicated_sampling, Skoogeer-Noise> add_blepping_atlas.py <repo root>
"""
import json, os, re, sys

ROOT = sys.argv[1]
PACKS = os.environ["BLEPPING_PACKS"].rstrip("/")
ATLAS = os.path.join(ROOT, "studio", "sampling_lab", "atlas.json")
OWNERS = os.path.join(ROOT, "studio", "sampling_lab", "pack_owners.json")
DIRS = {"blepping__comfyui_overly_complicated_sampling": "comfyui_overly_complicated_sampling", "ttulttul__Skoogeer-Noise": "Skoogeer-Noise"}
COMMITS = {"comfyui_overly_complicated_sampling": "d8574ba", "Skoogeer-Noise": "86d3d20"}
BLEPPING = {"ComfyUI-bleh", "ComfyUI-sonar", "comfyui_overly_complicated_sampling", "blepping__ComfyUI-bleh", "blepping__ComfyUI-sonar", "blepping__comfyui_overly_complicated_sampling"}

OCS = {"pack": "comfyui_overly_complicated_sampling", "author": "blepping", "licence": "MIT", "kind": "original", "verdict": "", "risks": [], "res4lyf": False, "blepping": True}
SKO = {"pack": "Skoogeer-Noise", "author": "ttulttul", "licence": "MIT", "kind": "original", "verdict": "TRY", "risks": [], "res4lyf": False}
O = "blepping__comfyui_overly_complicated_sampling/py/"
S = "ttulttul__Skoogeer-Noise/src/"
OCS_NOTE = "Not installed here. We ran it in a separate, throwaway ComfyUI for the blepping page; this entry is from reading the code at commit d8574ba."
SKO_NOTE = "Not installed here. Read at commit 86d3d20; the README calls the pack a set of perturbation tools, not a sampler."


def E(id_, name, family, sub, plain, math, props, evidence, provider, nodes, note="", ported=None):
    p = dict(provider, nodes=nodes, note=note or (OCS_NOTE if provider is OCS else SKO_NOTE))
    if ported: p["kind"] = "port"
    return {"id": id_, "name": name, "family": family, "subfamily": sub, "plain": plain, "math": math, "props": props,
            "evidence": [{"where": w, "symbol": s} for w, s in evidence], "providers": [p], "providers_n": 1, "in_core": False, "live": False,
            "needs_pack": True, "core_ref": {}, "family_fit": [], "claims": [], "label": "from code", "surprise": "", "rendered": False,
            "rendered_ids": [], "risks": [], "flagged_providers": 0, "licences": [p["licence"]], "verdicts": [p["verdict"]] if p["verdict"] else [],
            "audit": None, "run_patch": "", "run_guider": "", "prefer_model": ""}


ENTRIES = [
    E("ocs-sampler-groups", "OCS sampler groups (switch method by step, percent or sigma)", "sampler", "scheduling",
      "One OCS Sampler holds a chain of groups. Each group says when it applies, by step number, share of the steps or sigma, and which step methods it runs. At every step the first group whose window matches does the work, so euler can run the first few steps and dpmpp_sde the rest inside one sampler.",
      "Symbols: s step index; N steps; σ current sigma.\nGroup g applies when: step mode t0 ≤ s ≤ t1; percent mode t0 ≤ s/N ≤ t1; sigma mode t0 ≥ σ ≥ t1.\nBounds are inclusive. The first matching group in the chain runs the step.",
      {"order": "per step method", "extra_model_calls": "per step method", "params": "merge_method, time_mode, time_start, time_end, substeps"},
      [(O + "utils.py:234", "def check_time"), (O + "substep_merging.py:46", "def check_match")], OCS, ["OCS Sampler", "OCS Group", "OCS Substeps"]),
    E("ocs-substep-merging", "OCS substep merge strategies", "sampler", "substeps",
      "A group can run several substeps per step, from one or more methods, and a merge strategy decides how they combine. simple runs one; supreme_avg averages the substep results and renoises; divide splits the step into smaller sigma steps; overshoot steps past the target and comes back with Restart-style noise; lookahead and pingpong run ahead on a copy and keep part of what they learn.",
      "Symbols: x latent; K substeps; x_k result of substep k.\nsupreme_avg: x' = Σ_k x_k / K, noise scale averaged the same way.\ndivide: the step σ→σ' becomes K linear sub-steps between them (linspace).\novershoot: step to a lower sigma, then add noise back up to σ' (Restart rule).",
      {"merge_methods": "simple, supreme_avg, divide, overshoot, lookahead, pingpong, dynamic", "extra_model_calls": "K−1 or more per step"},
      [(O + "substep_merging.py:164", "class SupremeAvgMergeSubstepsSampler"), (O + "substep_merging.py:377", "class DivideMergeSubstepsSampler"), (O + "substep_merging.py:433", "class OvershootMergeSubstepsSampler"), (O + "substep_merging.py:517", "class LookaheadMergeSubstepsSampler")], OCS, ["OCS Group"]),
    E("ocs-core-ports", "OCS ports of core samplers", "sampler", "ports",
      "OCS carries its own copies of euler, dpmpp_2m, dpmpp_2m_sde, dpmpp_3m_sde, dpmpp_2s, dpmpp_sde, ipndm, ipndm_v, deis, gradient_estimation, heunpp2, dpm_2 and res_multistep, based on ComfyUI's versions. They exist so the groups and merge strategies above can schedule them; on their own they aim to match core.",
      "Same update rules as the core samplers they port (see each core entry).\nThe euler port: d = (x − D)/σ; x' = x + d·(σ_down − σ), then ancestral noise of size σ_up.",
      {"count": 13, "based_on": "ComfyUI core k-diffusion samplers"},
      [(O + "step_samplers/builtins.py:15", "class EulerStep"), (O + "step_samplers/builtins.py:22", "class DPMPP2MStep"), (O + "step_samplers/builtins.py:352", "class DEISStep"), (O + "step_samplers/builtins.py:480", "class RESMultistepStep")], OCS, ["OCS Substeps"], ported=True),
    E("ocs-reversible-heun", "Reversible Heun (and its one-call history form)", "sampler", "second order",
      "A Heun step written as a blend: it predicts at the lower sigma, blends the two clean-image guesses with a weight set by the sigma ratio, and can subtract a reversible correction built from the change in slope. The 1s form reuses the previous step's prediction instead of a new call when it can.",
      "Symbols: σ, σ↓ (down step); D, D₂ clean guesses at σ and σ↓; d slopes.\nr = σ↓/σ; w = 1 − (σ/σ↓)/2.\nD′ = lerp(D₂, D, w); x' = mix(x, D′, r).\nCorrection (scale s): x' −= s·(d₂ − d)/4·Δ², Δ = reversible step size.",
      {"order": 2, "extra_model_calls": 1, "based_on": "Clybius ComfyUI-Extra-Samplers"},
      [(O + "step_samplers/clybius.py:19", "class ReversibleHeunStep"), (O + "step_samplers/clybius.py:33", "def reversible_correction"), (O + "step_samplers/clybius.py:79", "class ReversibleHeun1SStep")], OCS, ["OCS Substeps"], ported=True),
    E("ocs-res-step", "RES (second-order exponential step)", "sampler", "exponential",
      "A two-stage exponential integrator in log-sigma time: one extra model call at the midpoint, with phi-function weights for the two clean-image guesses. It is the same family as RES4LYF's res_2s, in Clybius's version.",
      "Symbols: λ = −ln σ; h = λ' − λ; c₂ = 0.5.\nx₂ = e^(−c₂h)·x + a₂₁·h·D; D₂ = model(x₂, σ₂), σ₂ = e^(−(λ + c₂h)).\nx' = e^(−h)·x + h·(b₁·D + b₂·D₂), with a₂₁, b₁, b₂ from φ₁, φ₂.",
      {"order": 2, "extra_model_calls": 1, "space": "log sigma", "based_on": "Clybius ComfyUI-Extra-Samplers"},
      [(O + "step_samplers/clybius.py:91", "class RESStep"), (O + "step_samplers/res_support.py:1", "")], OCS, ["OCS Substeps"], ported=True),
    E("ocs-runge-kutta", "Runge-Kutta steps: Bogacki-Shampine, RK4, RKF45, dynamic RK", "sampler", "runge-kutta",
      "Classic Runge-Kutta steps applied to the sigma ODE. Bogacki-Shampine uses three slopes (two extra calls) and can add a reversible correction; RK4 uses four; rkf45 uses the six Fehlberg stages but keeps only the fourth-order answer, with no step-size control; rk_dynamic picks its order from how much the prediction changed since the last step.",
      "Symbols: d slope (x − D)/σ; Δ = σ↓ − σ.\nRK4: k₁ = dΔ; k₂ = d(x + k₁/2)Δ; k₃ = d(x + k₂/2)Δ; k₄ = d(x + k₃)Δ; x' = x + (k₁ + 2k₂ + 2k₃ + k₄)/6.\nBogacki: x' = x + 2k₁/9 + k₂/3 + 4k₃/9 (minus a reversible term).\nRKF45: x' = x + 25k₁/216 + 1408k₃/2565 + 2197k₄/4104 − k₅/5.",
      {"order": "3 to 4", "extra_model_calls": "2 (bogacki), 3 (rk4), 5 (rkf45), 0 to 3 (dynamic)", "error_control": "none, fixed steps"},
      [(O + "step_samplers/clybius.py:185", "class BogackiStep"), (O + "step_samplers/clybius.py:231", "class RK4Step"), (O + "step_samplers/clybius.py:255", "class RKF45Step"), (O + "step_samplers/clybius.py:299", "class RKDynamicStep")], OCS, ["OCS Substeps"], ported=True),
    E("ocs-euler-dancing", "Euler Dancing", "sampler", "ancestral",
      "An ancestral Euler step that aims further down the schedule than the next sigma (two steps by default), adds the noise for that leap, then steps back up toward the real next sigma. The current code prints debug lines to the console on every step.",
      "Symbols: σ_L sigma 'leap' steps ahead.\n(σ↓, σ↑) = ancestral(σ → σ_L, η).\nx₁ = x + d·(σ↓ − σ), add noise σ↑.\nThen a second Euler move from σ_L toward σ', with its own ancestral split (deta).",
      {"order": 1, "extra_model_calls": 0, "stochastic": "ancestral", "based_on": "Clybius ComfyUI-Extra-Samplers"},
      [(O + "step_samplers/clybius.py:356", "class EulerDancingStep")], OCS, ["OCS Substeps"], ported=True),
    E("ocs-ttm-jvp", "TTM-JVP (second-order Taylor step with a Jacobian-vector product)", "sampler", "taylor",
      "A truncated Taylor step that asks the model not just for its clean-image guess but for how that guess changes along the step, using a forward-mode derivative through the model. That costs one extra pass with tangents, and more memory than a plain call.",
      "Symbols: h = ln σ − ln σ'; D′ = ∂D along the step (JVP).\nx' = e^(−h)·x + φ₁·D + φ₂·D′, φ₁ = 1 − e^(−h), φ₂ = e^(−h) − 1 + h.",
      {"order": 2, "extra_model_calls": "1 with tangents", "based_on": "Katherine Crowson's method, via Clybius's repo"},
      [(O + "step_samplers/clybius.py:580", "class TTMJVPStep")], OCS, ["OCS Substeps"], ported=True),
    E("ocs-sens", "SENS (DPM++ 2M SDE with reversible terms)", "sampler", "multistep sde",
      "DPM++ 2M SDE with up to two extra reversible correction terms built from the previous one and two predictions. With the corrections at zero it is DPM++ 2M SDE.",
      "Symbols: h = ln(σ/σ'); η.\nx' = (σ'/σ)·e^(−ηh)·x + (1 − e^(−h−ηh))·D + m·(D − D_prev)/r, plus noise σ'·√(1 − e^(−2ηh)).\nReversible terms subtract scaled differences of D and D_prev (and D_prev2).",
      {"order": 2, "history": 2, "stochastic": "sde"},
      [(O + "step_samplers/clybius.py:668", "class ClybiusSENSStep")], OCS, ["OCS Substeps"], ported=True),
    E("ocs-distance", "Distance sampler", "sampler", "resampling",
      "Each step tries several Euler moves (three by default, falling to one near the end), asks the model at the next sigma for each, and blends the slopes with weights that favour the ones closest to the rest. It spends extra model calls to steady the step.",
      "Symbols: d_i slopes from R resamples.\nw_i ∝ (1 − (Σ_j |d_i − d_j| − min)/(max − min))^p, normalised; d = Σ w_i·d_i.\nx' = x + d·(σ↓ − σ).",
      {"extra_model_calls": "R per step (default 3 down to 1)", "based_on": "Extraltodeus DistanceSampler"},
      [(O + "step_samplers/extraltodeus.py:25", "class DistanceStep"), (O + "step_samplers/extraltodeus.py:61", "def distance_weights")], OCS, ["OCS Substeps"], ported=True),
    E("ocs-pingpong", "Ping-pong step", "sampler", "renoise",
      "Inside its window the step jumps straight to the model's clean-image guess and renoises to the next sigma with fresh noise; outside it, plain Euler. Its default window is step 0 only, so it acts like Euler unless the window is widened.",
      "x' = D·(1 − σ') + σ'·ε for flow models (D·1 + σ'·ε otherwise), when start ≤ s ≤ end.\nElse x' = Euler step with η = 0.",
      {"extra_model_calls": 0, "stochastic": "fresh noise each step", "based_on": "ACE-Step"},
      [(O + "step_samplers/misc.py:5", "class PingPongStep")], OCS, ["OCS Substeps"], ported=True),
    E("ocs-blep-cycle", "Cycle steps (euler and trapezoidal)", "sampler", "renoise",
      "blepping's own steps that keep part of the predicted noise and replace the rest with fresh noise at every step, by a fixed share (cycle_pct, 0.25 by default). The trapezoidal form makes one extra call at the next sigma and blends the two guesses first.",
      "keep = 1 − c; add = √(σ'² − (keep·σ')²)·(0.95 + 0.25c).\nx' = D + keep·(predicted noise) + add·ε.",
      {"extra_model_calls": "0 (euler) or 1 (trapezoidal)", "params": "cycle_pct, cycle_adjust_scales"},
      [(O + "step_samplers/blep.py:159", "class CycleSingleStepSampler"), (O + "step_samplers/blep.py:180", "class EulerCycleStep"), (O + "step_samplers/blep.py:196", "class TrapezoidalCycleStep")], OCS, ["OCS Substeps"]),
    E("ocs-blep-experimental", "Batch-augmented and wavelet steps (blep_bas, blep_weoon)", "sampler", "experimental",
      "Two experiments of blepping's. blep_bas runs the model on a larger batch built from the latent for its first few steps (0 to 3 by default) and folds the results back. blep_weoon splits the step in wavelet bands and blends them separately; it needs pytorch_wavelets.",
      "bas: batch ×2 by default for steps 0 to 3, renoise mode restart, simple or restart_noneta.\nweoon: DWT of the update; low band and high bands blended with their own modes, then inverse DWT.",
      {"extra_model_calls": "variable (bas), 1 (weoon)", "needs": "pytorch_wavelets for weoon"},
      [(O + "step_samplers/blep.py:248", "class BASStep"), (O + "step_samplers/blep.py:413", "class WeoonStep")], OCS, ["OCS Substeps"]),
    E("ocs-ode-backends", "ODE and SDE library backends (torchdiffeq, torchsde, torchode, diffrax)", "sampler", "ode solvers",
      "Hands each step to an outside solver library, which picks its own internal steps. tde uses torchdiffeq, tsde torchsde, tode torchode and diffrax the JAX library. Each is optional and only offered when its library is installed. The README advises against SDE mode for now.",
      "Solve dx/dσ = (x − D(x, σ))/σ from σ to σ' with the library's method and tolerances.\nModel calls = whatever the solver needs.",
      {"extra_model_calls": "variable", "needs": "torchdiffeq, torchsde, torchode or diffrax+jax"},
      [(O + "step_samplers/solver_tde.py:16", "class TDEStep"), (O + "step_samplers/solver_tsde.py:16", "class TSDEStep"), (O + "step_samplers/solver_tode.py:17", "class TODEStep"), (O + "step_samplers/solver_diffrax.py:57", "class DiffraxStep")], OCS, ["OCS Substeps"]),
    E("ocs-restart-schedule", "OCS Restart schedule", "scheduler", "restart",
      "Builds a Restart-sampling sigma list from an ordinary schedule and a short text rule, such as 'every 5 steps, jump back 3'. The OCS Sampler sees each jump back up and adds the matching noise. With an empty rule it returns the schedule unchanged.",
      "Rule [n, −k]: after every n steps, append the sigmas from k steps back.\nAt a jump σ_a → σ_b (σ_b > σ_a): add noise √(σ_b² − σ_a²)·s_noise.",
      {"needs": "a sampler that understands Restart segments (OCS Sampler)"},
      [(O + "restart.py:4", "class Restart"), (O + "nodes.py:567", "def go")], OCS, ["OCS SimpleRestartSchedule"]),
    E("ocs-immiscible-noise", "Immiscible noise (assign noise to the latent it is closest to)", "noise", "assignment",
      "Draws a batch of candidate noises and keeps, for each slice of the latent (by channel by default), the candidate nearest a reference such as the positive prediction. The idea comes from a 2024 paper on training; the README notes it was made for training, not sampling.",
      "Symbols: n_i candidates; r reference slice.\ndist_ij = mean((r_i − n_j)²); assignment minimises total distance (maximize flips it).\nOutput keeps the latent's shape.",
      {"based_on": "arxiv 2406.12303 and kohya-ss sd-scripts PR 1395", "default_size": 64},
      [(O + "noise.py:13", "class ImmiscibleNoise"), (O + "noise.py:75", "def immiscible")], OCS, ["OCSNoise OverrideSamplerNoise", "OCSNoise ImmiscibleReference"]),
    E("ocs-perlin-noise", "OCS Perlin noise", "noise", "procedural",
      "Fractal Perlin noise at latent size, with octaves, persistence and lacunarity, and a break_pattern setting that mixes it with ordinary noise. It can be handed to Sonar's noise inputs through a converter node.",
      "p = Σ_o persistence^o · perlin(lacunarity^o · res).\nOutput normalised, then blended with Gaussian by break_pattern.",
      {"distribution": "normalised pattern", "spectrum": "low-frequency heavy"},
      [(O + "custom_noise/noise_perlin.py:50", "def rand_perlin"), (O + "custom_noise/noise_perlin.py:159", "def generate_fractal_noise")], OCS, ["OCSNoise PerlinSimple", "OCSNoise PerlinAdvanced"]),
    E("ocs-expression-language", "OCS expression language and filters", "math", "expressions",
      "Parameters and filters can be written as small expressions in OCS's own language, read by its own parser, not by Python. Calls into torch are off unless an environment variable allows them; with them off, a workflow's expressions can only use the built-in functions.",
      "Pratt parser over the expression text; handlers for arithmetic, comparisons and t_* tensor functions.\nunsafe_tensor_method and unsafe_torch refuse unless COMFYUI_OCS_ALLOW_UNSAFE_EXPRESSIONS or COMFYUI_OCS_ALLOW_ALL_UNSAFE is set.",
      {"safe_by_default": True},
      [(O + "expression/parser.py:6", "class ParserSpec"), (O + "expression_handlers.py:17", "ALLOW_UNSAFE")], OCS, ["OCS ApplyFilterLatent", "OCSNoise ExpressionFilteredNoise"]),
    E("ocs-set-max-sigma", "Set a model's maximum sigma", "patch", "schedule",
      "Gives a copy of the model a different top sigma, by scaling its sigma table, so a scheduler fed from it starts higher or lower. Meant for the scheduler, not the sampler.",
      "m = σ_max_new/σ_max (or |σ_max_new| as a multiplier when negative).\nsigmas' = sigmas·m.",
      {"scope": "the patched model copy only"},
      [(O + "nodes.py:581", "class ModelSetMaxSigmaNode")], OCS, ["OCS ModelSetMaxSigma"]),

    E("skoogeer-mesh-drag", "Mesh drag (warp a latent by dragging random mesh points)", "latent", "warp",
      "Picks random points on a coarse mesh over the latent, drags each a random distance, smooths the displacement with B-spline passes and resamples the latent through it. A seeded, local smear that keeps the latent's values but moves them.",
      "Pick P mesh vertices; drag m ~ U(min, max) at angle θ (fixed or random).\nDisplacement field = smoothed, upsampled vertex drags.\nz'(u) = z(u − disp(u)) by grid sampling.",
      {"keeps_values": "moves values, adds none", "params": "points, drag_min, drag_max, direction, stroke_width"},
      [(S + "latent_mesh_drag.py:178", "def _make_control_displacement"), (S + "latent_mesh_drag.py:277", "def mesh_drag_warp"), (S + "latent_mesh_drag.py:527", "class LatentMeshDrag")], SKO, ["LatentMeshDrag", "ImageMeshDrag"]),
    E("skoogeer-fluid", "Fluid advection and smoke simulation on latents", "latent", "warp",
      "Runs a small fluid simulation over the latent: random forces stir a velocity field, which is damped, diffused and given vorticity, and the latent is carried along it step by step. The smoke version also carries a density field from a random source.",
      "Semi-Lagrangian advection: z_{t+1}(u) = z_t(u − v(u)·dt).\nv gets forces, damping, diffusion and vorticity each step.",
      {"params": "steps, dt, force_count, force_strength, swirl_strength, damping, diffusion, vorticity"},
      [(S + "fluid_advection.py:129", "def _advect_nchw"), (S + "fluid_advection.py:528", "def _simulate_fluid_advection"), (S + "fluid_advection.py:632", "def _simulate_smoke")], SKO, ["FluidLatentAdvection", "LatentSmokeSimulation", "FluidImageAdvection", "ImageSmokeSimulation"]),
    E("skoogeer-conditioning-perturb", "Conditioning noise, blur, frequency split and scale", "guidance", "conditioning",
      "Changes the text conditioning itself rather than the latent: adds seeded noise scaled by the embedding's own spread, blurs it along the token axis, splits it into smooth and detailed parts and merges them, or multiplies it by a factor. The pooled output is treated the same way where there is one.",
      "Noise: c' = c + ε·std(c)·strength.\nBlur: c' = c ∗ G_σ along tokens.\nScale: c' = f·c.",
      {"applies_to": "token embeddings and pooled output", "extra_model_calls": 0},
      [(S + "qwen_noise_nodes.py:3593", "class ConditioningAddNoise"), (S + "qwen_noise_nodes.py:3650", "class ConditioningGaussianBlur"), (S + "qwen_noise_nodes.py:3733", "class ConditioningFrequencySplit"), (S + "qwen_noise_nodes.py:3891", "class ConditioningScale")], SKO, ["ConditioningAddNoise", "ConditioningGaussianBlur", "ConditioningFrequencySplit", "ConditioningFrequencyMerge", "ConditioningScale"]),
    E("skoogeer-quant-attention", "TurboQuant and RotorQuant attention", "patch", "attention",
      "Per-model attention patches that change the numbers attention sees, then call the normal attention. TurboQuant rotates queries and keys by a seeded orthogonal matrix and rounds the keys (and, if asked, the values) to a few bits on a normal-distribution codebook. RotorQuant rotates channels in groups of three and keeps some of each group. Both run ordinary attention on the result, so they model the error of compressed attention rather than saving memory or time; RotorQuant keeping all three components is a pure rotation and changes nothing but rounding.",
      "TurboQuant: R orthogonal; q̃ = qR, k̃ = Q_b(kR) with scale ‖k‖/√d; out = attn(q̃, k̃, v).\nRotorQuant: per triplet rotation r_g; keep the first k of 3 components of q, k, v; attention; rotate back.",
      {"scope": "the patched model only (transformer_options override)", "saves_memory": "no", "bits_default": 8},
      [(S + "turboquant_attention.py:276", "def _quantize_rotated_tensor"), (S + "turboquant_attention.py:315", "def turboquant_attention_override"), (S + "rotorquant_attention.py:134", "def _project_triplets"), (S + "rotorquant_attention.py:197", "def rotorquant_attention_override")], SKO, ["TurboQuantAttentionModelPatch", "RotorQuantAttentionModelPatch"]),
    E("skoogeer-seeded-noise", "Seeded Gaussian noise for latents and images", "noise", "additive",
      "Adds seeded Gaussian noise scaled by the tensor's own spread, so the same strength means the same relative change on any model's latent. Its image node is named ImageAddNoise, the same as a core node, so ComfyUI keeps core's node and drops this one.",
      "z' = z + ε·strength·std(z), ε seeded per batch item.",
      {"distribution": "Gaussian", "normalizes_variance": "no, std rises"},
      [(S + "seeded_noise.py:100", "def add_seeded_noise"), (S + "seeded_noise.py:169", "class LatentNoise"), (S + "qwen_noise_nodes.py:1366", "class LatentAddNoise")], SKO, ["LatentNoise", "ImageNoise", "LatentAddNoise"]),
]


def check(entries):
    bad = []
    for e in entries:
        for ev in e["evidence"]:
            where, sym = ev["where"].rsplit(":", 1)[0], ev["symbol"]
            pack, rel = where.split("/", 1)
            path = os.path.join(PACKS, DIRS[pack], rel); line = int(ev["where"].rsplit(":", 1)[1])
            try: text = open(path, encoding="utf8").read().splitlines()
            except OSError: bad.append((e["id"], ev["where"], "no file")); continue
            if not 1 <= line <= len(text) or (sym and sym not in text[line - 1]): bad.append((e["id"], ev["where"], sym, text[line - 1][:80] if 1 <= line <= len(text) else "past end"))
        if re.search(r"^\s*(def |class \w+\(|import \w+|from \w+ import )", e["math"], re.M): bad.append((e["id"], "code in math"))
    return bad


def main():
    bad = check(ENTRIES)
    if bad: print("\n".join(map(str, bad))); sys.exit(1)
    a = json.load(open(ATLAS))
    ids = {e["id"] for e in ENTRIES}
    a["entries"] = [e for e in a["entries"] if e["id"] not in ids] + ENTRIES
    for e in a["entries"]:
        for p in e["providers"]:
            if p.get("pack") in BLEPPING: p["blepping"] = True
    order = ["sampler", "scheduler", "guidance", "noise", "latent", "math", "patch"]
    a["counts"] = {f: sum(1 for e in a["entries"] if e["family"] == f) for f in order}
    credits = {c["pack"]: c for c in a["credits"]}
    for pack, author, lic, verdict in (("comfyui_overly_complicated_sampling", "blepping", "MIT", ""), ("Skoogeer-Noise", "ttulttul", "MIT", "TRY")):
        n = sum(1 for e in a["entries"] for p in e["providers"] if p["pack"] == pack)
        c = credits.get(pack) or {"pack": pack, "author": author, "licence": lic, "verdict": verdict, "risks": []}
        c["methods"] = n; credits[pack] = c
    a["credits"] = sorted(credits.values(), key=lambda c: (-c["methods"], c["pack"]))
    a.setdefault("additions", []); a["additions"] = [x for x in a["additions"] if x.get("by") != "add_blepping_atlas.py"] + [{"by": "add_blepping_atlas.py", "date": "2026-11-02", "entries": sorted(ids), "commits": COMMITS, "note": "Read as text at the pinned commits, evidence lines checked on disk. Not run through the full atlas build or its second reader."}]
    json.dump(a, open(ATLAS, "w"), ensure_ascii=False, indent=None, separators=(",", ":"))
    o = json.load(open(OWNERS)); o["owners"]["comfyui_overly_complicated_sampling"] = "blepping"; o["owners"] = dict(sorted(o["owners"].items())); open(OWNERS, "w").write(json.dumps(o, indent=0, ensure_ascii=False))
    print(len(ENTRIES), "entries;", a["counts"])


if __name__ == "__main__":
    main()
