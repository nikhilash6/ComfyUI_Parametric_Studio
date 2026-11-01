# CU-242 - eps, v-prediction and flow: how a model's output is read

**Objective.** Say what a model's output means for each prediction type, read how ComfyUI converts it, and fix a model loaded as the wrong type. Taught by Dr. Denoise.

## The idea

A diffusion network takes a noisy latent and returns a tensor the same size. That tensor is not a picture. What it means depends on how the model was trained. Three common answers:

- **eps.** "Here is the noise I think is in there."
- **v.** "Here is a mix of the noise and the picture."
- **flow.** "Here is the direction from the picture to the noise."

Samplers don't want to know about this. They only want one thing: the model's estimate of the clean latent. So each kind of model has a small class in `comfy/model_sampling.py` that turns its output into that estimate. Get the class wrong and the network is fine, the sampler is fine, and the picture is ruined.

## The three classes

Each has a few small jobs. `noise_scaling` mixes noise with a latent. `calculate_input` prepares what the network sees. `calculate_denoised` turns its output into the clean estimate.

```
EPS           mix     x = latent + σ · noise
              input   x / √(σ² + 1)
              clean   x − σ · output

V_PREDICTION  mix and input as EPS
              clean   x / (σ² + 1) − σ · output / √(σ² + 1)

CONST (flow)  mix     x = (1 − σ) · latent + σ · noise
              input   x, unchanged
              clean   x − σ · output
```

At the very top of the schedule, EPS and V use √(1 + σ²) in place of σ in the mix line (`max_denoise`). Notice two things. In EPS, x has spread near √(1 + σ²), which is 14.6 at the top, so the input step divides that back to about 1. In flow, x is already a weighted average, so nothing needs dividing. And EPS and CONST have the same "clean" line, with different meanings of σ and of output.

A perfect v output, by the same formulas, is a blend that changes with σ. At low σ it is mostly the noise. At high σ it is mostly the negative of the picture. Salimans and Ho (2022) brought in parameterizations of this kind for stability at few steps.

Try the two mixing formulas on a real picture.

{{play:noise}}

## The class that holds the table

The other half is the table of noise levels.

- **`ModelSamplingDiscrete`** builds 1000 sigmas from betas (CU-202). Finding a step's timestep means finding the nearest table entry. With `zsnr` on, it rescales the table so that the top has almost no signal left, using `rescale_zero_terminal_snr_sigmas`. That is from Lin et al. (2023). The top sigma then goes from 14.6 to about 4519.
- **`ModelSamplingDiscreteFlow`** has σ from near 0 to 1. A timestep is σ × 1000. A `shift` bends the table with `time_snr_shift`.
- **`ModelSamplingFlux`** bends its table in the same way, with `flux_time_shift`, whose number is the logarithm of the same kind of shift. Its timestep is σ itself, not σ × 1000.

ComfyUI picks a class when it detects the model. Three nodes let you override that, each by making a new object and patching it onto the model.

{{graph:b_vpred}}

- `ModelSamplingDiscrete` chooses among `eps`, `v_prediction`, `lcm`, `x0`, `img_to_img` and `img_to_img_flow`, with a `zsnr` switch.
- `ModelSamplingSD3` sets the flow shift, default 3.0.
- `ModelSamplingFlux` works out its shift from image size, using `base_shift` and `max_shift`.

{{graph:sd35_flow}}

## What shift does

Shift bends where the steps go, without changing the ends. `σ' = a t / (1 + (a − 1) t)`. Higher shift keeps σ high for longer, so more steps are spent at high noise. Esser et al. (2024) and CU-206 discuss why that can help at higher resolutions.

Don't move numbers between the nodes. Flux's number is a log. So 1.15 is a mild bend in `ModelSamplingSD3` and a strong one as `max_shift` in `ModelSamplingFlux`. The lab gives 0.535 against 0.760 at the middle of the schedule.

## What goes wrong

- **A v model detected as eps, or forced to the wrong type.** The picture comes out wrong at every seed. We did not render this, so we can't show you what it looks like. Set `ModelSamplingDiscrete` to the type the model's notes state.
- **Trying v_prediction on an eps model to see what happens.** The class is a statement of fact about training. Changing it doesn't change the model's behaviour, it just misreads the output.
- **`zsnr` on a model not trained for it.** The first step's σ jumps to about 4519, and the model has never seen that. Use it only when the model's notes say so.
- **Shift on the wrong branch of a graph.** With the custom sampler parts, send the patched model to the scheduler and to the guider. Otherwise the sigmas belong to the old shift.
- **A shift of 1 and flat results.** Shift 1 is no bend at all. `time_snr_shift` returns t unchanged.
- **Comparing losses across prediction types.** The same network error means a different size in each. See CU-314.

## Lab

Give each class its perfect output: does the clean latent come back? It does, to rounding, at all three noise levels.

```text
kind   sigma    largest error of the recovered clean latent   spread of what the model sees   spread of its perfect output
eps    14.6     3.6e-15                                       1.013                           1.013
v      14.6     8.9e-16                                       1.013                           1.007
flow   0.5      4.4e-16                                       0.714                           1.430
```

The input spread is near 1 for eps and v. Flow at σ 0.5 is 0.714, and its target is larger, because it is the difference of two things.

Now misread a model. The output is perfect and only the formula that reads it is wrong.

```text
sigma   right kind  v model read as eps  eps model read as v
0.03    0.000       0.001                0.001
0.3     0.000       0.088                0.084
1.0     0.000       0.771                0.545
3.0     0.000       3.539                1.119
14.6    0.000       20.119               1.375
```

At low noise the two kinds are nearly the same, and that's the sneaky part: late steps don't suffer, and the early steps have the huge errors. Reading v as eps is off by 20 at the top, on data with a spread of 1.

```text
sigma_min 0.02917   sigma_max 14.61464   signal left at the top: sqrt(alphabar) 0.06826
with zsnr: sigma_min 0.02917   sigma_max 4518.76   signal left at the top: 0.000221
```

The shift table: t is the plain position, and the columns are σ after the bend.

```text
shift   t=0.9   t=0.75  t=0.5   t=0.25  t=0.1
1.0     0.900   0.750   0.500   0.250   0.100
1.15    0.912   0.775   0.535   0.277   0.113
3.0     0.964   0.900   0.750   0.500   0.250
6.0     0.982   0.947   0.857   0.667   0.400
the number 1.15 at t=0.5: as ModelSamplingSD3 shift 0.535; as ModelSamplingFlux max_shift at 1024x1024 0.760
ModelSamplingFlux at 1024x1024: tokens 4096, mu 1.150, the same bend as SD3 shift 3.158
```

The second line below is what percent means, for nodes that use start and end percents. It is percent of the model's table, not of your steps.

```text
sigma 1.0, discrete: index 354; flow sigma 0.5 with multiplier 1000: 500
percent_to_sigma(0.5): SD table 1.6156; flow shift 3 0.7500
```

## Sources

- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_model_advanced.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_model_advanced.py)
- [Salimans, Ho 2022. Progressive Distillation for Fast Sampling of Diffusion Models](https://arxiv.org/abs/2202.00512)
- [Lin, Liu, Li, Yang 2023. Common Diffusion Noise Schedules and Sample Steps are Flawed](https://arxiv.org/abs/2305.08891)
- [Esser et al. 2024. Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206)
