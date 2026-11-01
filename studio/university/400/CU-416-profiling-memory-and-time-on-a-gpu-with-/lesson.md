# CU-416 - Profiling memory and time on a GPU (with a CPU model of it)

**Objective.** Find where a run's time and peak memory really went, with tools you already have, before changing anything. Taught by Tinker Tune.

## Two questions, two answers

"It's slow" and "it ran out of memory" are different problems, and they have different cures. A model can fit and crawl. A small model can run out of memory on a large batch. Profiling means getting a number for each before you touch anything.

## Memory: what was alive at the peak

The bytes in one tensor are easy: elements times bytes each. The peak is harder, because it depends on what is alive at the same moment. It isn't the sum of all tensors, since some die before others are born, and it isn't the largest one either. The order of work can change it.

So a useful memory question is never "how big is it?". It's "what was alive when it peaked?".

On a real card there are three readings, and they disagree for good reasons. The PyTorch documentation explains this: it keeps freed memory in a cache for speed, and that memory still shows as used in `nvidia-smi`.

| reading | what it counts |
|---|---|
| `torch.cuda.memory_allocated()` and `max_memory_allocated()` | memory occupied by tensors, now and at the peak |
| `torch.cuda.memory_reserved()` | everything PyTorch's allocator holds, including its cache |
| `nvidia-smi` | what the whole card has given out, to every process |

So a high `nvidia-smi` number doesn't mean you are out of room. `GET /system_stats` on ComfyUI reports `vram_total`, `vram_free`, `torch_vram_total` and `torch_vram_free` for each device, which you can poll while a job runs. If a job does run out of memory, ComfyUI logs a memory summary above the line `Got an OOM, unloading all loaded models.`

## Time: where it really went

Use the clock you have first. ComfyUI prints `Prompt executed in N seconds`, the sampler bar gives time per step, and the server's log keeps a timestamp for each write. CU-370 shows how to read them, including a case where the bar and the clock disagree.

Split a run into loading, text encoding, sampling and decoding. Then ask how much a speed-up can possibly save. A tenfold speed-up of something that takes 2% of the run saves less than 2%. Use the lab to feel this.

{{play:amdahl}}

For code you wrote, there is a trap: GPU work is asynchronous by default. A call can return before the work is done, so a stopwatch around it may measure almost nothing. Call `torch.cuda.synchronize()` before reading the time. For a per-operation breakdown, `torch.profiler` exists, and we don't cover it here.

Work counts help when you have no GPU to measure on. A matmul of M rows, K inputs and N outputs takes about 2 M N K operations. That tells you how things scale, and it can't tell you seconds.

Here is a graph with a probe on its latent, a good thing to run while you watch the readings:

{{graph:f_txt2img_probe}}

## What goes wrong

- **Timing the first run.** It includes loading. Run twice, and time the second.
- **Reading `nvidia-smi` as tensors.** Reserved and cached memory counts there. Use `max_memory_allocated` for tensors, in your own code.
- **Changing several things at once.** You won't know which one helped. Change one, and keep the seed.
- **A faster GPU for a memory error, or more VRAM for a slow graph.** More memory doesn't speed up a job that already fits, unless it was swapping layers in and out. Check the console for `loaded partially` first.
- **Polling too slowly.** A short peak can fall between two readings. A reading taken every second can miss it, so treat a low reading as a lower limit.
- **Trusting an average when a stray load is in it.** Use the median, as the lab shows.

## Lab

No GPU here. The arithmetic is real, and the sizes and times are examples we chose.

```text
a tensor's bytes = elements x bytes each: (2, 3, 8, 8) fp32 = 1536 bytes
  SD latent, 64x64                 0.06 MB
  IMAGE 1024x1024                 12.00 MB
  16 channel latent, 128x128       0.50 MB
```

The peak walk:

```text
the peak is not the sum, and not the biggest tensor. Four tensors, in MB: {'a': 300, 'b': 500, 'c': 200, 'd': 100}
  each freed after the next one is made: peak 800 MB, alive ['a', 'b']
  nothing freed: peak 1100 MB, alive ['a', 'b', 'c', 'd']
  sum of all = 1100, biggest alone = 500
```

Same four tensors, 800 MB or 1100 MB, depending only on when they die. Reserved against allocated, in a toy allocator. Peak allocated is what you'd want when sizing a job.

```text
allocated, reserved and what nvidia-smi shows: a toy caching allocator
  after freeing: allocated 1000  reserved 6000  peak allocated 6000
  after empty_cache: allocated 1000  reserved 1000  peak allocated 6000
```

Work grows with the number of tokens. These are one linear layer's operations, with sizes picked as an example:

```text
work in a matmul. y = x W for M rows, K inputs and N outputs is 2 M N K operations, and doubling the side changes M
  512 px, 4096 tokens           838,860,800
  1024 px, 16384 tokens       3,355,443,200
```

The time split, and why the biggest slice is the one to attack:

```text
where the time went, example numbers
  load models   40.0 s   36.4%
  text encode    2.0 s    1.8%
  sampling      60.0 s   54.5%
  VAE decode     8.0 s    7.3%
  text encode 10 times faster: 108.2 s.  sampling 2 times faster: 80.0 s
```

And why one timing lies:

```text
why one timing lies: the first run includes loading. Same example, median of five runs
  runs [66.0, 1.5, 1.5, 1.5, 1.5]  mean 14.4 s  median 1.5 s
```

## Sources

- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, app/logger.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/logger.py)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [PyTorch 2.15, CUDA semantics](https://docs.pytorch.org/docs/2.15/notes/cuda.html)
