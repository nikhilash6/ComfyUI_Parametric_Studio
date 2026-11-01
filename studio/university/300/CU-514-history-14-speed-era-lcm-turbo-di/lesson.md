# CU-514 - History 14: The speed era: LCM, turbo and distillation

**Objective.** Say what changed between 2022 and 2024 to take a good picture from dozens of model calls to one or a few, see from an exact teacher what a student learns and what it can't do, and read the speed nodes in ComfyUI. Taught by Dr. Denoise.

## The idea

Nearly all the time in a run goes on model calls (CU-308). Better samplers make the path cheaper to follow, but a good picture still took tens of calls. So people asked a different question. Could a model learn to make the big jump directly? That is distillation: train a slow model first, then train a fast student on its answers.

The same idea came in several forms, in a short time.

- **Progressive distillation** (Salimans and Ho, February 2022). Train a student whose one step does what two teacher steps do. Repeat, and halve the count each time. They report an FID of 3.0 on CIFAR-10 in 4 steps.
- **Guidance distilled** (Meng et al., October 2022). CFG costs two calls a step. They first train one model to match the combined result, then distill that. They report 1 to 4 steps for latent models.
- **Consistency Models** (Song et al., March 2023). A model "directly mapping noise to data", with a rule that every point on one path must give the same answer. Multi-step sampling is still possible, trading compute for quality.
- **Latent Consistency Models** (Luo et al., October 2023). The same aim in latent space, for models like Stable Diffusion, predicting the solution of the guided path. Their abstract says a 2 to 4 step model at 768 takes 32 A100 GPU hours to train.
- **LCM-LoRA** (November 2023). The change stored as a LoRA, usable on fine-tuned models.
- **Adversarial Diffusion Distillation** (Sauer et al., November 2023), behind SDXL Turbo. It uses a teacher plus a GAN loss for "just 1-4 steps", which brings CU-501's game back.
- **SDXL-Lightning** (Lin et al., February 2024). Progressive and adversarial together, released as LoRA and full U-Net.

The teacher's slow path is what's being compressed. It's the path that gets shorter, and the file stays about the same size. CU-409 does the maths for one of these in detail.

## The mechanism

A plain sampler asks the model for a direction, moves a little, and asks again. A student is asked: from here, at this noise level, where does the path end? In the ideal case that answer is the same at every point on one path, and that is the consistency rule.

```
consistency:   f(x_σ, σ) = f(x_σ', σ')    for any two points on the same path
boundary:      f(x, σ → 0) = x            at no noise, the input is the answer
```

The boundary is built into the formula, so no training can break it. `LCM.calculate_denoised` in ComfyUI has this form, with σ_data = 0.5 and the timestep multiplied by 10:

```
c_skip = σ_data² / ( (10t)² + σ_data² )     share taken straight from the input
c_out  = 10t / √( (10t)² + σ_data² )        share taken from the model's clean guess
output = c_out · x0 + c_skip · input
```

More steps mean re-noising and asking again. Take the clean guess, add fresh noise for the next level, and ask again. That is the whole of `sample_lcm`, and each step throws away the last position and keeps only its clean guess.

## In ComfyUI

- **LCM.** `ModelSamplingDiscrete` with sampling set to `lcm` picks the `LCM` class and `ModelSamplingDiscreteDistilled` in `comfy_extras/nodes_model_advanced.py`. That restricts the model to 50 timesteps out of 1000 (`original_timesteps = 50`). The sampler `lcm` in the list runs `sample_lcm`.
- **Turbo.** `SDTurboScheduler` in `comfy_extras/nodes_custom_sampler.py` takes up to 10 steps and picks from a fixed list: 999, 899, 799 and so on.
- **The second call.** `sampling_function` in `comfy/samplers.py` skips the negative branch when cfg is close to 1. So cfg 1 halves the calls, and our `d_lcm` graph uses it. When memory allows, `_calc_cond_batch` runs the two branches as one batch, which is one forward pass doing twice the work. We count each branch as a call.
- **Training.** Core has no node that trains a student. It runs distilled weights.

What does a step really cost? Find out here.

{{play:calls}}

An LCM LoRA on an SD 1.5 model, and a Turbo checkpoint in one call.

{{graph:d_lcm}}

{{graph:h5_sdturbo}}

## What goes wrong

- **You treat it as a normal model at normal settings.** A file distilled for 4 steps at cfg 1 has different settings from its base. Read the notes of your file. At cfg 7 the two calls come back, and LCM's abstract says the student was distilled from a guided model already, so that push would land on top.
- **You raise the steps hoping for better.** Distillation is trained for a small number of steps. In the lab, going from 4 to 8 calls made the student worse, 0.0478 to 0.0712. A real file might differ, so try it on yours.
- **You leave out the sampling type on an LCM LoRA.** `ModelSamplingDiscrete` is what tells ComfyUI to read the output in the LCM form. The `d_lcm` graph has it in node 3. Without it the model is read as an ordinary one.
- **You expect a Turbo schedule to span the noise range.** At 4 steps, `SDTurboScheduler` uses 999, 899, 799, 699 and then jumps to zero. So more steps there don't mean a finer walk down to low noise.
- **You put a student on a different model.** A student copies one teacher. The lab shows 1.37 against 0.14 when the data changes. LCM-LoRA's abstract says it generalises across fine-tuned models of a family. That is its own claim, and it doesn't reach across families.
- **You compare by seconds on one run.** Count calls, and remember that the VAE and the text encoder cost the same.

## Lab

The data is a mix of two Gaussians, so a perfect denoiser has a formula, and we can follow the true path to any accuracy. That is the teacher. The student is a small network that learns where the path from (x, σ) ends. We train it directly on those end points, which is simpler than the consistency loss but aims at the same function. It runs in a loop shaped like `sample_lcm`, on noise levels we picked by hand.

```text
teacher, 30 Heun steps (59 calls): W1 0.0137; two real samples differ by 0.0271
```

```text
model calls   plain Euler, perfect model   student in an LCM loop
1             1.3863                       0.1428
2             1.3849                       0.0678
4             0.7234                       0.0478
8             0.2689                       0.0712
32            0.0666                       -
```

W1 is the average gap between sorted samples and the real data, so lower is better. Plain Euler with a perfect model is useless at one call, 1.39: it lands on an average. The student at one call is 0.1428, about ten times better for the same work. Re-noising helps at first: 0.0678 at 2 calls and 0.0478 at 4. Then 0.0712 at 8, so more calls made it worse. At 32 calls Euler still hasn't caught up with the student's 4. This is one seed with a small student on easy one-dimensional data, so don't read these counts as advice for pictures. The papers above use 1 to 4.

A student only knows its teacher:

```text
student against its own teacher's data 0.1428; against data with the hump weights swapped 1.3692. A student copies one teacher.
```

It has no idea the data moved. Then the arithmetic of calls, from how `sampling_function` treats cfg 1:

```text
steps   cfg   model calls   share of 20 steps at cfg 7
20      7.0   40            1/1
8       7.0   16            2/5
4       1.0   4             1/10
1       1.0   1             1/40
```

Those are model calls. They aren't seconds, because the text encoder and VAE cost the same. Then the two tables read from source. First the `LCM` class, whose boundary is exact at timestep 0 and which is almost entirely the clean guess elsewhere:

```text
timestep   c_skip    c_out   share of the answer taken straight from the input
999        0.000000  1.0000  0.000000
499        0.000000  1.0000  0.000000
99         0.000000  1.0000  0.000000
19         0.000007  1.0000  0.000007
0          1.000000  0.0000  1.000000
```

And the Turbo list:

```text
SDTurboScheduler, steps 1, denoise 1.0: timesteps [999] then sigma 0
SDTurboScheduler, steps 2, denoise 1.0: timesteps [999, 899] then sigma 0
SDTurboScheduler, steps 4, denoise 1.0: timesteps [999, 899, 799, 699] then sigma 0
```

## What is contested

Every paper here reports that it beats the others on its own table. ADD's abstract says it outperforms LCMs in a single step. Consistency Models' abstract says it beats earlier distillation. Compare with care: each one fixes a dataset, a metric and a step count.

Quality against step count is an open trade. Few-step models can lose variety. SDXL-Lightning's abstract names "a balance between quality and mode coverage" as what it is after. We did not measure this on images.

## Sources

- [Salimans, Ho 2022. Progressive Distillation for Fast Sampling of Diffusion Models](https://arxiv.org/abs/2202.00512)
- [Meng et al. 2022. On Distillation of Guided Diffusion Models](https://arxiv.org/abs/2210.03142)
- [Song et al. 2023. Consistency Models](https://arxiv.org/abs/2303.01469)
- [Luo et al. 2023. Latent Consistency Models: Synthesizing High-Resolution Images with Few-Step Inference](https://arxiv.org/abs/2310.04378)
- [Luo et al. 2023. LCM-LoRA: A Universal Stable-Diffusion Acceleration Module](https://arxiv.org/abs/2311.05556)
- [Sauer et al. 2023. Adversarial Diffusion Distillation](https://arxiv.org/abs/2311.17042)
- [Lin et al. 2024. SDXL-Lightning: Progressive Adversarial Diffusion Distillation](https://arxiv.org/abs/2402.13929)
- [ComfyUI v0.43.0, comfy_extras/nodes_model_advanced.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_model_advanced.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_custom_sampler.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
