# CU-370 - Reading ComfyUI's console during a run

**Objective.** Read a run from its console: what was asked for, how it loaded, how fast it went and whether it worked. Taught by Bit Bandit.

## The console is a free profiler

Every time you queue something, ComfyUI writes down most of what you would otherwise have to guess: which attention it chose, which format, what it loaded, how fast it stepped. Reading it takes less time than one more experiment.

Run this and watch the terminal, not the canvas.

{{graph:sd15_txt2img}}

## At startup

These come once, before any job. They settle a lot of later arguments.

| line | what it tells you | from |
|---|---|---|
| `Total VRAM ... MB, total RAM ... MB` | what ComfyUI thinks it has | `model_management.py` |
| `Set vram state to: NORMAL_VRAM` | the mode from your flags | `model_management.py` |
| `DynamicVRAM support detected and enabled` | which load path you're on, see CU-402 | `main.py` |
| `Using pytorch attention` | the attention backend, see CU-304 | `ldm/modules/attention.py` |
| `Using RAM pressure cache.` | the node cache mode, see CU-371 | `execution.py` |

And at the end of custom node loading, `Import times for custom nodes`, with any that failed marked. A pack that failed to import starts here.

## During a run

**`got prompt`** means the server accepted a job. It is printed when the job arrives, not when it starts, so it can land in the middle of another job's progress bar. It says nothing about success.

**`Failed to validate prompt for output 7:`** means the graph was refused before anything ran. The next lines name the node and the input. CU-290 goes through these.

**`Requested to load SDXL`** means a model isn't already loaded. It is printed only when a load is needed. So when it's missing on the second run, that absence is good news. If you see it on every run, something is pushing the model out.

**How it loaded.** Without dynamic VRAM you get `loaded completely; ...` or `loaded partially; ...`, with figures. With dynamic VRAM you get `Model X prepared for dynamic VRAM loading. N MB Staged. P patches attached.` `Staged` is the size set up for on-demand loading, not bytes on the card right now, so a large number there isn't alarming on its own. If `patches attached` is 0 when you expected a LoRA, your LoRA may not have reached this model.

**`model weight dtype torch.bfloat16, manual cast: None`** is the weights' format and whether they're cast at run time. **`Using mixed precision operations`** and **`Native ops: ...`** say a quantized file was found and what your card can compute directly. Anything listed as emulated is dequantized for the multiply.

**`Warning: Ran out of memory when regular VAE decoding, retrying with tiled VAE decoding.`** means it recovered. It worked, slowly. Add `VAEDecodeTiled`, or lower the size.

**The bar.** `5/20 [00:41<02:03, 8.21s/it]` is steps done, elapsed, estimate left, then speed. Slow runs show `s/it`, and fast ones show `it/s`. Mind which, because they are upside down from each other.

**`Prompt executed in 32.14 seconds`** is logged when a job ends. It isn't proof of success, because a failed job reaches the same line. Look for `!!! Exception during processing !!!` above it. On an out-of-memory error you also get a memory summary and `Got an OOM, unloading all loaded models.`

To see more, start with `--verbose DEBUG`, or `--verbose DEBUG run.log` to send it to a file.

## Try it

{{play:console}}

## What goes wrong

- **Reading the last line first.** Failures print far above it. Scroll to the first `!!!`, and read down.
- **Believing the bar's estimate on the first step.** The first step can include loading. Wait for step 3.
- **"My LoRA did nothing."** Check for `NOT LOADED` lines, which `comfy/sd.py` prints for LoRA keys that matched nothing, and for the patch count.
- **Warnings you can ignore, or not.** `Missing weight for layer` may be harmless for a part you don't use, and `clip missing:` can be a wrong encoder type. Check one against what you are doing before ignoring or chasing it.
- **A busy console from packs.** Packs print too. A line that isn't in this list may be theirs.

## Lab

These lines are copied from one real job on our test machine. Repeats and file paths are removed, and each starts with seconds past the minute. The lab labels each with patterns that follow the source's log calls.

```text
31.93  attention    Using pytorch attention in VAE
32.11  device       VAE load device: cuda:0, offload device: cpu, dtype: torch.bfloat16
33.09  wants model  Requested to load AutoencoderKL
33.12  staged       Model AutoencoderKL prepared for dynamic VRAM loading. 160MB Staged. 0 pat
34.15  device       CLIP/text encoder model load device: cuda:0, offload device: cpu, current:
34.15  wants model  Requested to load Flux2TEModel_
34.20  staged       Model Flux2TEModel_ prepared for dynamic VRAM loading. 8262MB Staged. 0 pa
36.95  dtype        model weight dtype torch.bfloat16, manual cast: None
36.95  family       model_type FLUX
36.96  wants model  Requested to load Flux2
36.99  staged       Model Flux2 prepared for dynamic VRAM loading. 17316MB Staged. 0 patches a
36.99  steps          0%|          | 0/4 [00:00<?, ?it/s]
47.31  queued       got prompt
51.13  steps        100%|##########| 4/4 [00:04<00:00,  1.05s/it]
```

See the stray `got prompt` at 47.31? That is a different job arriving. Now the arithmetic the lines allow:

```text
models asked for, in order: ['AutoencoderKL', 'Flux2TEModel_', 'Flux2']
staged in total: 25738 MB, the size set up for loading on demand, not bytes held on the card
the bar says 4 steps at 1.05 s/it = 4.2 s. The clock says the bar was open from 36.99 to 51.13 = 14.14 s.
from the first line to the last step: 19.20 s, of which sampling steps by the bar's count 22%
```

The bar says 4.2 seconds and the clock says 14.14. Who is right? Both. `model_trange` in `comfy/utils.py`, used with dynamic VRAM, moves the bar's start time after step 2, on purpose, so the speed it shows leaves out load overhead. That makes the rate a fair per-step speed and the bar a poor measure of how long you waited. Time jobs by the clock.

The estimate-based path's lines, with our own numbers, and the real wording:

```text
the other kind of load line, from the estimate-based path. Numbers here are ours, the wording is the source's
full load    loaded completely; 7000.00 MB usable, 4900.00 MB loaded, full load: True
part load    loaded partially; 5120.00 MB usable, 4890.00 MB loaded, 2377.00 MB offloaded, 128.00 MB buffer reserved, lowvram patches: 0
share on the card: 67%
```

```text
the two ways tqdm writes speed
  1.05s/it   is 1.050 seconds per step
  3.40it/s   is 0.294 seconds per step
```

## Sources

- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ops.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/model_patcher.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_patcher.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, app/logger.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/logger.py)
