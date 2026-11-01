# CU-106 - Your first image: checkpoint, sampler, VAE

**Objective.** Follow one prompt through the classic text-to-image graph, naming what each of the three networks in a checkpoint does, the shape of every hand-off, and the sigma list that decides how the sampler walks from noise to a clean latent. Taught by Captain Graph.

## The idea

The classic first graph is the seven-node chart of CU-102: Load Checkpoint, two CLIP Text Encode nodes, Empty Latent Image, KSampler, VAE Decode and Save Image. One file feeds it, and that file holds three networks.

- The denoiser, the MODEL output, is a UNet in SD 1.x. It looks at a noisy latent and predicts what is noise in it.
- The text encoder, the CLIP output, turns the prompt into vectors (CU-104).
- The VAE converts between pixels and the small latent grid the denoiser works on (CU-103).

Here it is. Open it, and every box in this lesson is on your canvas.

{{graph:sd15_txt2img}}

Here is a render from the same graph on our test machine, with a longer prompt and the same seed: one picture, one seed, for scale.

![An SD 1.5 render: euler at 20 steps, karras scheduler, cfg 7, seed 424242](sampling_lab/sampler-euler.jpg)

The sampler is not a network. It is the loop that calls the denoiser again and again. Stable Diffusion runs its diffusion in the latent space of a pretrained autoencoder (Rombach et al. 2021). For SD 1.x the autoencoder has a downsampling factor of 8 and maps an image of shape H × W × 3 to a latent of shape H/8 × W/8 × 4, and the text encoder's output reaches the UNet through cross-attention (the Stable Diffusion v1-4 model card).

## The mechanism

**The sigma list.** The sampler needs noise levels σ, from high to low. At each step it asks the denoiser for its best guess D of the clean latent at the current σ, and moves toward that guess: x_next = x + (x − D) / σ × (σ_next − σ). That is the Euler step of Karras et al. (2022). The list of σ values is the schedule.

For an SD 1.x model, σ comes from the 1000-step training schedule of CU-202, σ = √((1 − ᾱ) / ᾱ), and runs from 0.0292 at the clean end to 14.6146 at the noisiest. The `normal` scheduler spaces the timesteps evenly from 999 down to 0, reads σ off the training list by interpolating between neighbours in log σ, and adds a final 0.

**The denoise setting.** With denoise below 1, ComfyUI builds a longer list with int(steps / denoise) steps and keeps only the last steps + 1 values. The sampler still runs the number of steps you asked for, but it starts at a lower σ, and the start is the encoded input image plus noise of that size.

{{play:denoise}}

**Cost.** One Euler step is one call of the network. Heun's method makes a second call per step, except on the last. With a cfg other than 1 each call evaluates the network for the positive and for the negative prompt and combines them as uncond + (cond − uncond) × cfg.

## In ComfyUI

`CheckpointLoaderSimple` returns MODEL, CLIP and VAE from one file. `load_checkpoint_guess_config` in `comfy/sd.py` opens it with `comfy.utils.load_torch_file`, guesses the family from the weights (CU-107), and builds the three objects. In an SD 1.x file they sit under the key prefixes `model.diffusion_model.`, `cond_stage_model.` and `first_stage_model.`.

`KSampler` in `nodes.py` calls `common_ksampler`, then `comfy.sample.sample`, then `comfy.samplers.KSampler.sample`. That class builds the list with `calculate_sigmas`, one handler per scheduler name. Its widgets default to 20 steps, cfg 8.0 and denoise 1.0. When cfg is exactly 1.0 the negative prompt is not evaluated at all. The preview you watch while sampling is the denoised estimate D, not the noisy x, because the sampler hands the denoised latent to the preview callback.

The `default_workflow.json` in v0.43.0 is a different graph: it uses separate UNETLoader, CLIPLoader and VAELoader nodes for one particular model. The checkpoint loader is still in `nodes.py`, and the classic graph is still the simplest way to see the parts.

## What goes wrong

- **The picture is mush at a low `denoise` with an empty latent.** `denoise` below 1 expects a real picture to start from (CU-116). With `EmptyLatentImage` the start is an all-zero latent with a little noise. We reason this from the formula and did not test how it looks.
- **The negative prompt seems to do nothing.** At a cfg of exactly 1.0 ComfyUI doesn't evaluate it at all. Raise cfg.
- **A size far from what the model trained on.** The SD 1.x model card lists training at 512 by 512. You can ask for any size, because nothing refuses it, but this is a request outside its training. CU-109 has the numbers.
- **The preview looks different from the result.** The preview shows the estimate D, usually through a small approximate decoder, and the final picture goes through the real VAE.
- **`clip input is invalid: None`.** The file isn't a whole checkpoint. CU-114 shows how to tell, and which loaders to use.
- **Queue again gives nothing new.** The seed was fixed and nothing changed, so it's all from the cache (CU-112).
- **Positive and negative crossed.** Both have the same type. Follow each wire from the sampler back to its text.

## Lab

First the hand-offs for a 512 by 512 image.

```text
node                       output       shape                numbers
CLIPTextEncode             CONDITIONING [1, 77, 768]         59,136
EmptyLatentImage           LATENT       [1, 4, 64, 64]       16,384
KSampler                   LATENT       [1, 4, 64, 64]       16,384
VAEDecode                  IMAGE        [1, 512, 512, 3]     786,432
the sampler works on 16,384 numbers, the picture has 786,432: 48x more
```

Then the sigma list, rebuilt from the training schedule. The ComfyUI documentation prints the 20-step `normal` list for SDXL, which shares this schedule, and the lab checks its own list against it.

```text
sigma_max 14.6146, sigma_min 0.0292
20-step normal schedule: 14.6146 10.7468 8.0815 6.2049 4.8557 3.8654 3.1238 2.5572 2.1157 1.7648 1.4806 1.2458 1.0481 0.8784 0.7297 0.5964 0.4736 0.3555 0.2322 0.0292 0.0000
same as the 20-step list in the documentation to four decimals: True
```

The 20 values are spaced evenly in timestep, not in σ, and the last step lands on 0. Now what `denoise` does to the list.

```text
denoise   steps run   list built with   first sigma
1.0       20          20 steps          14.6146
0.75      20          26 steps          4.2650
0.5       20          40 steps          1.5482
0.25      20          80 steps          0.6708
```

With denoise 0.5 the sampler still runs 20 steps, but it begins at σ = 1.5482, so much of the input image survives. Last, a toy sampler walks down the 20-step list. The data is two blobs, an exact denoiser stands in for the network, and the numbers are averaged over 400 starting noises.

```text
step  sigma     x to final   denoised estimate to final
0     14.6146   38.975       2.065
2     8.0815    20.889       1.891
4     4.8557    12.021       1.651
6     3.1238    7.327        1.364
8     2.1157    4.657        1.071
12    1.0481    1.948        0.627
16    0.4736    0.642        0.240
19    0.0292    0.004        0.000
```

At the first step x is 38.975 away from its final value, while the denoised estimate is only 2.065 away, so a preview built from the estimate shows far more of the final picture than x would. Both columns are close to 0 by the last step.

```text
network evaluations for 20 steps: Euler 20, Heun 39
```

## What is contested

The toy has an exact denoiser, and a trained network can only approximate it, so its estimate at each step will be worse than the toy's. The lab says nothing about how much worse. Which sampler and scheduler give the best picture for a given model is an empirical question that nothing here tests. The check against the documentation is for the sigma list alone.

## Sources

- [Rombach et al. 2021. High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)
- [Karras et al. 2022. Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364)
- [CompVis/stable-diffusion-v1-4, model card](https://huggingface.co/CompVis/stable-diffusion-v1-4)
- [ComfyUI Custom Node Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy/model_detection.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_detection.py)
- [ComfyUI v0.43.0, comfy/supported_models_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models_base.py)
- [ComfyUI v0.43.0, latent_preview.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/latent_preview.py)
- [ComfyUI v0.43.0, default_workflow.json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/default_workflow.json)
