# CU-409 - Distillation math: teacher, student, consistency

**Objective.** Explain how a many-step sampler's work can be compressed into few model calls, say what a student inherits from its teacher, and run distilled weights in core. Taught by Tinker Tune.

## The idea

A sampler takes many small steps because each one is only right for a small move. Distillation trains a second model, the student, to make the big move in one go. The target for that big move comes from the slow model, the teacher. Training costs a lot and runs once. After that, generating is cheap.

Note what's being compressed: the path, not the file. A student usually has the same architecture and size as its teacher. Merging doesn't make things faster, but distillation can.

## A problem with an exact answer

To see the method clearly, take data with an exact solution: numbers drawn from a Gaussian with spread 1. For that data, the perfect denoiser is D(x, σ) = x / (1 + σ²), and the probability-flow path from σa to σb has an exact form: multiply x by √(1 + σb²) / √(1 + σa²). So we can measure any sampler's error exactly.

Plain Euler, with the Karras schedule from 80 down to 0.002:

```text
plain Euler. Model calls, error against the exact path, and the std of the result (should be 1.000)
calls   error    std
1       0.9858   0.012
2       0.9838   0.014
4       0.5338   0.464
8       0.3076   0.691
16      0.1574   0.841
32      0.0795   0.919
64      0.0400   0.958
128     0.0200   0.978
```

One call is worthless, as the std of 0.012 shows: a single step lands on the denoiser's mean, which is nearly zero. Going from one call to two gains almost nothing. After that the error falls by 1.7 to 2 times each time you double the calls, and from 8 calls on it halves. That's the slow road.

## Progressive distillation

Salimans and Ho's method is simple. Take a teacher with N steps. Train a student so that its one step does what two teacher steps do. That student, with N/2 steps, then becomes the new teacher. Repeat. Each round halves the calls.

On this problem each step just multiplies by a number, so a student here is a list of numbers fitted to samples.

```text
progressive distillation from a 64-step teacher. Each round halves the steps
student calls   student error   Euler at the same calls   std of student
64              0.0400          0.0400                    0.958
32              0.0400          0.0795                    0.958
16              0.0400          0.1574                    0.958
8               0.0400          0.3076                    0.958
4               0.0400          0.5338                    0.958
2               0.0400          0.9838                    0.958
1               0.0400          0.9858                    0.958
```

The student's error stays at 0.04 all the way down to one call, where Euler at one call is useless. That's what the method promises.

Two warnings about that column. First, it's flat because this problem is too easy: a step here is a multiplication, and a product of two numbers is one number, so the student copies exactly. A real network can't copy two steps perfectly, and each round adds some error. Second, the student matches its teacher, not the truth. Nothing in its training points at what the teacher got wrong, and here its error lands exactly on the teacher's:

```text
the student copies the teacher, errors included. One-step student from each teacher, against the teacher's own error
teacher steps   teacher error   one-step student error
4               0.5338          0.5338
16              0.1574          0.1574
64              0.0400          0.0400
```

A 4-step teacher makes a one-step student with exactly its 0.5338 error. A bad teacher gets you a fast bad student.

## Consistency

Song et al. come at it differently. Instead of halving rounds, they ask for one function f(x, σ) with a single property: any point on a path, at any noise level, should give the same answer, the path's end. Enforce two things. At the smallest noise level, f returns its input. And neighbouring levels on a path agree. Train with those, and the answer spreads back from low noise to high.

In this toy f is x times a number c(σ). We fit c level by level, from the smallest noise up, with the teacher's Euler step linking neighbours.

```text
consistency: fit c(sigma) so that f(x, sigma) = c x agrees across neighbouring levels of an Euler teacher
levels   c at sigma max   exact c   one-call error   Euler one-call error
8        0.00865          0.01250   0.3076           0.9858
32       0.01150          0.01250   0.0795           0.9858
128      0.01225          0.01250   0.0200           0.9858
```

With more levels (a finer teacher) the one-call error falls to about 0.02, again the size of the error in the Euler teacher at 128 steps. And here's the property itself: one path, predictions read at five noise levels, all the same.

```text
self-consistency on one path, 128 levels: the answer read from different points on it. Exact end value of this path is the first column
exact end 1.0000   predictions from levels 80.000 17.295 2.428 0.157 0.002
  0.9799 0.9799 0.9799 0.9799 0.9799
```

They agree to the last digit. They're also 2% off the exact end, 1.0000: that's the teacher's error again.

The paper's abstract also says that consistency models support multistep sampling, to trade compute for quality, and that they can be trained by distilling a diffusion model, or alone with no teacher. We did only the distilling form.

Try the cost side of this: count model calls, not steps, on a toy where the true end is known.

{{play:solvers}}

## In ComfyUI

Core runs distilled weights, and has no node that trains them. `TrainLoraNode`'s loss compares with the clean latent, not with a teacher's steps.

To run them:

- **LCM.** The Latent Consistency Models paper applies the idea in latent space, and reports 2 to 4 steps. Core has an `LCM` sampling type in `comfy_extras/nodes_model_advanced.py`, chosen by `ModelSamplingDiscrete` with `sampling` set to `lcm`, and a `lcm` sampler (`sample_lcm`).
- **Turbo.** `SDTurboScheduler` in `comfy_extras/nodes_custom_sampler.py` is a scheduler for such models.
- **A distilled LoRA.** It's the student's difference, stored as a LoRA. Load it like any other, and set the sampler for it.

{{graph:d_lcm}}

Our graph uses 4 steps and CFG 1. That's the usual way for LCM files, and we haven't tested it here. The maker's notes for your file come first.

{{video:families/animatediff_0.mp4|A distilled student, run here: AnimateDiff Lightning, distilled from AnimateDiff SD 1.5 v2, on the DreamShaper 8 checkpoint through a custom pack. 4 steps at cfg 1. 16 frames at 512 x 512, 8 fps: the waves move and the lighthouse holds. Peak 3.7 GiB. One seed.|families/animatediff_0.webp}}

## What goes wrong

- **Ordinary settings on a distilled model.** 30 steps at CFG 7 is what you'd use for its teacher. Read its notes: few steps, and CFG often at or near 1.
- **A distilled model with no `ModelSamplingDiscrete` set up.** LCM has its own prediction form. Without it, or the lcm sampler, you're running the wrong sums.
- **Expecting a distilled file to be smaller or to need less memory.** It usually isn't. The cost saved is in model calls, and memory depends on the network.
- **One step when more are allowed.** Consistency models support multistep sampling. Try two or four.
- **Teaching from a poor teacher.** The student inherits it, as the table above shows.
- **Merging a distilled model with its base.** It was trained for a different path, and there's no reason for the blend to work at either's step count. We have not tested it.

## Lab

No network is trained in this lab: a student is a list of numbers, fitted by least squares on samples from an exact problem. It's built to show where the error goes, and it runs in seconds. It leaves out what makes real distillation hard: a network that can't copy exactly, an EMA target, and data that isn't Gaussian. We rewrote this lab, because the earlier draft's "student" was a fixed formula tested against a noisy stand-in that wasn't a teacher, and its result proved nothing.

## Sources

- [Progressive Distillation for Fast Sampling of Diffusion Models](https://arxiv.org/abs/2202.00512)
- [Consistency Models](https://arxiv.org/abs/2303.01469)
- [Latent Consistency Models: Synthesizing High-Resolution Images with Few-Step Inference](https://arxiv.org/abs/2310.04378)
- [Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364)
- [ComfyUI v0.43.0, comfy_extras/nodes_model_advanced.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_model_advanced.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_custom_sampler.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_train.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_train.py)
