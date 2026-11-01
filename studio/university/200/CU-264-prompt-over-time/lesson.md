# CU-264 - Changing the prompt over time

**Objective.** Make one prompt run early and another late, work out how many steps each gets, and avoid leaving a gap. Taught by Madame Attention.

## The idea

Early steps work at high noise and decide the broad layout. Later steps work at low noise and decide detail. So you can use one prompt to lay things out and another to finish them.

`ConditioningSetTimestepRange` takes `start` and `end`, and does almost nothing itself. It writes two keys into the dict. Then you `ConditioningCombine` the two prompts, and the sampler picks by noise level at every step.

{{graph:sd15_cond_time}}

## What percent means

This is the part that surprises people. **It isn't percent of your steps.** It's a point on the model's own noise scale. `percent_to_sigma` turns each percent into a sigma, and each step compares its own sigma against that.

```python
if timestep_in[0] > timestep_start: return None     # not started yet
if timestep_in[0] < timestep_end:   return None     # already over
```

So 0.5 on SD 1.5 means sigma 1.616, whichever scheduler you use. How many of your steps fall above that depends on the schedule. On 20 steps, that's 9 steps on Karras, 7 on an even log spacing and 17 on an even linear spacing, as the lab shows.

ControlNet's start and end percent go through the same `percent_to_sigma`, so everything here applies to both.

{{play:range word=prompt}}

On a flow model the scale differs. With shift 3, percent 0.5 is sigma 0.75, not the middle of the range.

## What goes wrong

- **"I set 0.5 but it wasn't half my steps."** Expected. Count in the play, or use the lab's method for your scheduler.
- **A gap between ranges.** With 0 to 0.4 and 0.6 to 1, some steps have no positive entry at all. Their positive prediction becomes zero, so make ranges meet exactly.
- **Two range nodes in a row.** The second overwrites the first. They don't intersect. Check the dict (CU-260).
- **The second prompt seems to do nothing.** It only runs at low noise, when the layout is already fixed. Start it earlier.
- **Range on only the positive.** The negative keeps running through the whole schedule. That's fine, but know that it is doing so.
- **Forgetting the Combine.** Two range nodes need to be one list before the sampler. Otherwise one of them isn't wired in at all.

A related trick is using a zeroed negative for part of the schedule, with a range. Our Sampling Lab doesn't test it, so we don't describe its effect.

## Lab

Ports of `percent_to_sigma` and the check above, matched against the real functions on a CPU.

```text
SD 1.5 sigmas run from 14.615 down to 0.0292
percent   sigma     flow model with shift 3
0.1       8.307     0.964
0.25      4.086     0.900
0.5       1.616     0.750
0.75      0.695     0.500
0.9       0.344     0.250
```

```text
end_percent 0.5 on 20 Karras steps: first prompt runs 9 steps, the second 11
the same split on an even log spacing: 7 and 13    on an even linear spacing: 17 and 3
```

Same percent, three schedules, and very different step counts. Next, the gap.

```text
steps with no prompt at all: ranges 0 to 0.4 and 0.6 to 1
uncovered steps: [8, 9]
what an uncovered step's positive prediction becomes: [0.0, 0.0, 0.0, 0.0]
```

Those are steps 8 and 9 of 20 counting from zero, in the middle of the run. With a zero positive prediction, the cfg sum is `uncond − uncond · cfg`, which is nothing like what you asked for.

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
