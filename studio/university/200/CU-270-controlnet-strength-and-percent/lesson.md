# CU-270 - ControlNet strength, start and end percent

**Objective.** Predict which of your steps a ControlNet runs on, and say what strength multiplies. Taught by Captain Graph.

## The idea

The Apply ControlNet node has three numbers: `strength`, `start_percent` and `end_percent`. Most people read the percents as "percent of my steps". They are not. They are places on the model's own noise scale. Your steps then land wherever your scheduler puts them, and each step checks for itself whether it is inside the window.

That one difference explains why the same setting does different things on different schedulers, and why a ControlNet can quietly do nothing on an img2img run.

{{graph:sd15_controlnet}}

## How a percent becomes a noise level

Before sampling, `pre_run_control` in `comfy/samplers.py` turns both percents into noise levels with `percent_to_sigma`. On an SD 1.x model the timestep runs from 999 at full noise to 0 at none, so percent p means the noise level at timestep (1 − p) × 999.

Then, at every step, `get_control` in `comfy/controlnet.py` does this test, with sigma the step's noise level:

```
skip the ControlNet if  sigma > level(start_percent)  or  sigma < level(end_percent)
```

Percent 0 is a level above every step, and percent 1 is 0, below every step.

```text
percent to noise level, SD 1.x
percent  timestep  sigma
0.0      999.0     above every step
0.25     749.2     4.086
0.5      499.5     1.616
0.75     249.8     0.695
0.8      199.8     0.571
1.0      0.0       0.000
```

Note what is not in that table: your step count. Now count steps for the same windows, on four schedulers.

```text
20 steps, start_percent 0: steps with the ControlNet on
end_percent   normal   karras   exponential   simple
0.25          5        6        4             5
0.5           10       9        7             10
0.75          15       12       10            15
0.8           16       12       10            16
1.0           20       20       20            20
```

An end of 0.5 is 10 of 20 steps on `normal` and `simple`, 9 on `karras` and 7 on `exponential`. The last two spend more of their steps at low noise, below the end level, where the ControlNet is already off. The step count hardly matters, as the next table shows: the share stays about the same.

```text
same window, start 0 end 0.8, different step counts, karras
steps   on   share
8       5    0.62
20      12   0.60
40      25   0.62
```

Try it. The bar shows each step lit or dark, on the karras scheduler. Change the step count and the model kind, and watch the window move.

{{play:range}}

Other windows work the same way. A start after the end is not refused. It just never fires:

```text
other windows, 20 steps, normal
start   end   steps on
0.0     0.5   10
0.2     0.8   12
0.5     1.0   10
0.8     0.2   0
```

## The trap: low denoise

`denoise` picks where on a longer schedule the sampler starts (CU-214). The window does not move with it, because it is on the model's scale, not on your run. So img2img slides your whole run down, out from under the window.

```text
the window is on the model's scale, so denoise moves your steps under it. 20 steps, normal, start 0
denoise  first sigma   end 0.25   end 0.5   end 0.8
1.0      14.615        5          10        16
0.8      4.904         2          8         15
0.5      1.548         0          0         12
0.3      0.810         0          0         7
```

At denoise 0.5 the first step's sigma is 1.548. An end_percent of 0.5 means level 1.616, which is above it. Every step is below the end level, so the ControlNet runs on none of them. Nothing warns you. You get a plain img2img and may blame the ControlNet.

The fix: raise `end_percent`, or check by the table. To keep the control for the first half of a run at denoise 0.5, you need an end well past 0.5, because the run starts at about that point on the scale.

A flow model has a different scale again. The same percent lands somewhere else, and with a shift the first half of the scale is spent at high noise:

```text
same percent on a flow model, shift 3
percent  sigma on SD 1.x   sigma on flow
0.25     4.086             0.900
0.5      1.616             0.750
0.75     0.695             0.500
```

## What strength does

`control_merge` multiplies every residual by `strength`. That is all. It does not change when the ControlNet runs, and it does not change the hint. If you chain two nodes, each one's residuals get its own strength and then they are added. They are not averaged, so two nodes at 1.0 add two full sets of residuals, where an average would give the size of one.

```text
strength multiplies the residuals: |0.5 x| / |x| = 0.5   chained: difference from 0.5 r1 + 0.5 r2 = 0.0
```

The widget goes from 0 to 10. At exactly 0 the node returns the conditioning untouched, so no ControlNet runs at all.

Start at 1.0 with the window open, and see what it does. Then shorten the window if the control is too stiff. The usual reason to end early is to let the last steps add detail with no control pulling on them. That is common advice, and we have not measured it. Our example graph uses strength 0.9 and end 0.8 as a starting point, not a result.

## What goes wrong

- **The ControlNet seems to do nothing on img2img.** Your run starts below the end level. Spot it by comparing the first sigma with the level in the table. Fix by raising `end_percent` to 1.0, then lowering it again.
- **The result changed when you changed the scheduler.** Same percents, different steps inside the window. Count them with the bar above.
- **You set start above end.** No error, no control. The node does not check. Spot it by reading the two numbers.
- **Only the positive wire goes through the node.** It writes `control` into each conditioning you give it. Pass both outputs on, positive to positive and negative to negative, or the negative pass runs with none. We did not measure what that does to a picture.
- **You use the old node.** `ControlNetApply`, marked deprecated, has no percents at all.
- **Two ControlNets at 1.0 are too much.** They add. Lower both.

## Lab

The lab rebuilds the noise levels and the on/off test, and its step counts match ComfyUI's own functions. All of its tables are above, in the sections they belong to. It runs no ControlNet model.

## Sources

- [Zhang, Rao, Agrawala 2023. Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.05543)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/controlnet.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/controlnet.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
