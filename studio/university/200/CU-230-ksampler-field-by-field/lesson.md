# CU-230 - KSampler, field by field

**Objective.** Say what each KSampler input controls, predict what changing it costs, and know which ones change the picture only because they change the noise. Taught by Dr. Denoise.

## The idea

KSampler is one node that does the whole loop from noise to latent. It looks like a settings form, and people treat it like one: nudge a number, look at the picture, repeat. That hides the fact that its inputs do very different jobs. Some choose where the run starts. Some choose how many times the model is asked. One only picks which random numbers you get.

Here is the node in its usual place.

{{graph:sd15_txt2img}}

## The fields

Every line below is read from `KSampler.INPUT_TYPES` in `nodes.py` and the code it calls.

- **model.** The denoiser. It also carries its own noise range, so the same scheduler gives different numbers on different families.
- **seed.** A whole number from 0 up to 2^64 − 1. It picks the starting noise, and CU-240 covers exactly how. The editor's "control after generate" setting changes it between runs.
- **steps.** How many jumps the sampler makes down the noise levels. Default 20. It is not the same as the number of model calls.
- **cfg.** How hard to push away from the negative prompt and toward the positive one. Default 8.0. The sum is `uncond + (cond − uncond) × cfg`. CU-208 is the full lesson.
- **sampler_name.** The rule for each jump. 45 names in this version. Some call the model once per step and some about twice or three times. Some add fresh noise on the way down.
- **scheduler.** Which noise levels the jumps land on. 9 names. It makes a list of numbers before the run starts, and you can read that list.
- **positive and negative.** The two conditionings. The types are the same, so nothing stops you crossing them.
- **latent_image.** Where to start. For text to image it is all zeros. For image to image it is your encoded picture. Its shape sets the batch and the size. An all-zero latent is widened to the channel count the model wants, which is why the 4-channel `EmptyLatentImage` can feed a 16-channel model.
- **denoise.** How far down the schedule to start. At 1 the run starts at the top. Below 1 it starts part-way down and adds only that much noise. CU-231 is the full lesson.

## What each one costs

The number that decides your wait is model evaluations, and it comes from three fields multiplied together.

```
evaluations = steps × calls per step × (2 if cfg is not 1, else 1)
```

Denoise is not in that sum. Lowering it does not save time, because KSampler rebuilds a longer schedule and keeps the same number of steps.

{{play:ksbudget}}

## What goes wrong

- **A slow sampler looks better than a fast one.** Compare by evaluations, not by steps. `heun` at 20 steps costs 78 evaluations at CFG 7 where `euler` costs 40. Give `euler` 39 steps before you judge them.
- **CFG 1 and the negative prompt does nothing.** That is correct. At CFG 1 the negative pass is skipped, so its text has no effect. Runs need half the evaluations and the negative prompt stops working. If a model's own notes say to use CFG 1, this is why it is cheap.
- **Denoise below 1 on an empty latent.** There is no picture to keep, and the run starts with far less noise than a full run. In the lab the result moves a long way from the full run even though the seed is the same. Use denoise below 1 only with a real latent.
- **Same settings, a different picture.** Check the seed control. If it says randomize, the seed changed after the last run. CU-102 shows why that also re-runs the node.
- **Changing the seed to test a setting.** Change one field at a time. A new seed changes the whole starting point and swamps most differences you were trying to see.
- **Positive and negative crossed.** The graph validates and runs, and the picture is wrong. Follow both wires back to the text before you blame the sampler.

## Lab

The lab is a small KSampler written from those same formulas, on a one-dimensional toy where the perfect model has a formula. The positive prompt asks for a subject at +1.5 and the negative for a nearby one at +1.2. Each row changes one field from the base setting of seed 42, 20 steps, CFG 7, euler, karras, denoise 1.

```text
field changed            evals  first sigma  last before 0  mean result  change from base
nothing (base)           40     14.615       0.029          +3.236       0.000
seed 42 -> 43            40     14.615       0.029          +3.238       0.384
steps 20 -> 40           80     14.615       0.029          +3.233       0.014
cfg 7 -> 1               20     14.615       0.029          +1.470       1.767
cfg 7 -> 3               40     14.615       0.029          +2.058       1.178
sampler euler -> heun    78     14.615       0.029          +3.229       0.033
scheduler -> simple      40     14.615       0.223          +3.246       0.043
denoise 1 -> 0.5         40     1.182        0.029          +2.524       0.712
same fields again, identical numbers: True
```

Read the columns one at a time.

- **evals.** Doubling the steps doubles the bill. CFG 1 halves it. Heun nearly doubles it. Denoise leaves it alone.
- **first sigma.** Only denoise moves it.
- **last before 0.** Scheduler `simple` stops at 0.223 where `karras` goes on to 0.029. That is a real difference in the last jump.
- **mean result.** The seed barely moves the average. It moves each sample, and the last column shows that. A new seed is a new draw from the same distribution.
- **mean result again.** At CFG 1 the average lands on +1.470, close to the subject asked for at +1.5. At CFG 7 it overshoots to +3.236. That overshoot is the job of the next line.

```text
uncond 0.2, cond 0.5: cfg 0: 0.20   cfg 1: 0.50   cfg 3: 1.10   cfg 7: 2.30   cfg 14: 4.40
```

CFG 0 returns the negative side alone, and CFG 1 the positive side alone. Anything above 1 goes past the positive.

The last check is the promise behind every seed you have saved: the same fields give the same numbers. On a real machine that also needs the same model, the same conditioning and, for samplers that add noise, the same device (CU-240).

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/sample.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sample.py)
- [KSampler - ComfyUI Built-in Node Documentation](https://docs.comfy.org/built-in-nodes/KSampler)
