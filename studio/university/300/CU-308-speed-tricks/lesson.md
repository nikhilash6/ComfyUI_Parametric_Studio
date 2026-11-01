# CU-308 - Speed: distillation, caching, compile, fewer steps

**Objective.** Name the four levers on sampling speed, count what each saves in model calls, and say what each costs. Taught by Dr. Denoise.

## Where the seconds go

Nearly all sampling time is calls to the model. So the first number to know is how many calls a run makes:

```
calls = steps × calls per step × (2 if CFG is not 1)
```

Euler makes one call per step, and Heun makes two, except that `sample_heun` makes one on a last step that lands on sigma 0, so 20 steps of Heun on a schedule ending at 0 is 39 calls and this formula is the round figure. CFG needs a prediction for each of two prompts. ComfyUI can run those two as one batch when memory allows, so read "calls" as predictions. In `sampling_function` in `comfy/samplers.py`, when CFG is exactly 1 the second is dropped, so CFG 1 costs half. Some patches turn that shortcut off.

## The four levers

**Fewer steps.** Take bigger strides along the same path. This costs accuracy on a normal model, and the error follows the solver's order, as the lab shows. A higher-order solver buys back some of it for more calls per step, so compare by calls, not by steps.

**Distillation.** A model property, not a ComfyUI feature. Someone trains a model to do in few steps what another did in many. Progressive distillation (Salimans and Ho 2022) trains a student to match two teacher steps in one, and repeats, halving each round. Consistency models (Song et al. 2023) learn to map any point on the path to the path's start, which allows a single step. Core runs such weights and has no node that trains them. Use the steps and CFG the model's makers say, usually low and often 1: a 4-step model at CFG 7 is a different and usually worse thing.

{{graph:d_lcm}}

**Caching.** This word means three different things in ComfyUI.

- The **node cache** skips a node whose class, inputs and ancestors are unchanged. Change the seed and the sampler runs, but the text encoder doesn't. CU-221 has the details. It saves nothing on a first run.
- A **step cache** skips model calls inside one run, by reusing the last change when little is changing. `EasyCache` and `LazyCache` are core nodes, marked experimental. This one trades quality for time: it is an approximation, and you should look at the picture.
- A **prefix cache** is model-specific. In `comfy/ldm/qwen_image21/model.py`, `PrefixCache` keeps attention keys and values for the prompt and reference part, so later calls attend to the stored prefix. That helps that family when the prefix repeats. You don't have to turn it on in the graph, since its default setting is `auto`, and the experimental core node `QwenImage21Cache` can set its device and format or turn it off. Other models don't have it.

{{graph:g_easycache}}

**Compile.** `TorchCompileModel` wraps the model in `torch.compile`. It is a node marked experimental, with `inductor` and `cudagraphs` backends. There is also a separate Comfy model compiler, which `--disable-comfy-compiler` turns off. We did not test what either saves. If you try one, leave the first run out of your timing, because compiling has to happen some time, and compare with the node removed.

{{graph:g_torch_compile}}

## Try the first lever

Fewer steps against a better solver, on a toy with a known answer. Read calls, not steps.

{{play:solvers}}

The node cache has its own lab: predict what runs again when you change one thing.

{{play:cache}}

## What goes wrong

- **A normal model at 4 steps looks unfinished.** It was not trained for that. Use a distilled model or LoRA, with its stated settings.
- **A distilled model at high CFG looks burnt.** They are usually made for CFG near 1. Read the model's page.
- **"The cache did nothing."** Node caching does nothing on a first run or when a random seed changes the sampler's key. Step caches do little at low step counts, since there is little to reuse. Check with `verbose`, which prints each skip.
- **A step cache and a similar pack patch on the same model.** They both change the model's forward path, and results can be wrong without an error. Use one at a time.
- **A timing compares a first run with a second.** The first includes loading. See CU-373.

## Lab

Counting calls:

```text
model calls = steps x calls per step x (2 if CFG is not 1)
  euler, 20 steps, CFG 7                         40
  euler, 20 steps, CFG 1                         20
  heun, 20 steps, CFG 7                          80
  euler, 4 steps, CFG 1 (a distilled model)       4
  euler, 50 steps, CFG 7                        100
```

Stride against accuracy, on an ODE with a known answer. It is a toy and not a model, but it shows the shape: Euler is first order and Heun second order, so halving the step halves one error and quarters the other.

```text
the ODE dx/dt = -x + sin(t) from t = 0 to 1, whose exact answer we know
  steps  euler calls  euler error   heun calls   heun error
      1            1      0.70240            2      0.21833
      2            2      0.21269            4      0.03343
      4            4      0.09090            8      0.00637
      8            8      0.04246           16      0.00140
     16           16      0.02056           32      0.00033
  halve the step: euler error x2.14 smaller, heun x4.57 smaller
```

Compare Heun with 4 steps (8 calls, 0.00637) with Euler with 8 steps (8 calls, 0.04246). Same calls, a much smaller error. A diffusion model is less smooth than this toy, so don't expect that exact ratio.

Now the idea behind a step cache: reuse the last derivative while the input has barely moved.

```text
skipping steps, the idea behind a step cache: reuse the last change when the input barely moved
  threshold 0.00: 40 of 40 calls, error 0.00807
  threshold 0.01: 21 of 40 calls, error 0.04065
  threshold 0.03: 10 of 40 calls, error 0.06260
  threshold 0.10:  5 of 40 calls, error 0.08620
```

Half the calls cost five times the error here. That is the trade, in miniature, and the right threshold is one you find by looking at results.

## Sources

- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_easycache.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_easycache.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_torch_compile.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_torch_compile.py)
- [ComfyUI v0.43.0, comfy_execution/caching.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/caching.py)
- [ComfyUI v0.43.0, comfy/ldm/qwen_image21/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/qwen_image21/model.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_qwen.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_qwen.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [Salimans and Ho 2022. Progressive Distillation for Fast Sampling of Diffusion Models](https://arxiv.org/abs/2202.00512)
- [Song et al. 2023. Consistency Models](https://arxiv.org/abs/2303.01469)
