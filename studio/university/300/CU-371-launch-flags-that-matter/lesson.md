# CU-371 - Launch flags that matter

**Objective.** Pick launch flags from what the source says they do, and tell a real problem from a flag you don't need. Taught by Bit Bandit.

## Start with none

ComfyUI's defaults are its best guess for your machine. Add a flag when you can name the problem it fixes, one at a time. `comfy/cli_args.py` is the complete list, and reading it beats any forum post, because help text changes between versions and posts don't. All of this is v0.43.0.

Flags in one group refuse each other. We ran the real parser: `--highvram --lowvram` exits with `not allowed with argument --highvram`. The same goes for two attention flags, or two cache flags.

## Memory

**`--reserve-vram GB`** tells ComfyUI to leave that much for your OS and other software. Without it, the default is 400 MB on Linux and 600 MB or more on Windows. Setting it also raises the minimum working room for every load, as the lab shows, so don't set it higher than you need.

**`--vram-headroom GB`** is for dynamic VRAM: the help says ComfyUI "will try and keep this much VRAM completely free and unused, even counting VRAM from other apps". We didn't read the code behind it.

**Dynamic VRAM** is on unless you pass `--highvram`, `--gpu-only`, `--novram`, `--cpu` or `--disable-dynamic-vram`. So `--highvram` does more than its help line suggests, because it turns dynamic VRAM off. `main.py` also needs a supported card and PyTorch 2.8 or later, and warns if it falls back. `--disable-dynamic-vram` prints a warning that the argument "will be removed soon".

**`--lowvram`** does nothing with dynamic VRAM on, its help says. **`--novram`** is for when lowvram isn't enough. **`--cpu`** runs everything on the CPU, slowly: this is how you can run the graph below with no GPU at all.

{{graph:nm_first}}

**`--disable-smart-memory`** makes ComfyUI offload to RAM aggressively rather than keep models on the card. It can help a shared card and costs you reloads.

## The node cache

These decide what finished results stay around. They are in one group.

- **`--cache-ram`** is the default, even with no flag: results stay until system RAM runs short. It keeps 10% of RAM free, at least 2 GB and at most 10 GB, unless you give numbers.
- **`--cache-classic`** is the older, aggressive behaviour.
- **`--cache-lru N`** keeps N results, and its help says it "may use more RAM/VRAM".
- **`--cache-none`** uses less memory, and runs every node every time. The price is that you lose everything CU-221 taught you to rely on. It's useful when big models or long videos fill RAM.

## Attention

CU-304 explains these. Here is what the flags do. On an NVIDIA card with PyTorch 2 and no flag, you get PyTorch's attention already, with its flash backend turned on. So:

- **`--use-pytorch-cross-attention`** only states the default on such a card.
- **`--use-split-cross-attention`** and **`--use-quad-cross-attention`** turn that default off. Split slices to fit, and quad is the sub-quadratic one.
- **`--use-sage-attention`** and **`--use-flash-attention`** need those libraries installed.
- **`--use-ck-attention`** uses Comfy Kitchen's, and ComfyUI exits with an error if your build lacks it.
- **`--force-upcast-attention`** has the help "please report if it fixes black images". It exists for a reason.

The console prints the one you got.

## Precision and "fast"

`--fp16-vae`, `--bf16-vae`, `--fp32-vae`, `--bf16-text-enc` and their friends set formats by hand. The help for `--fp16-vae` warns it "might cause black images". `--fast` turns on "untested and potentially quality deteriorating optimizations", and is a good flag to leave off until you are chasing one thing.

## Build one

{{play:flags}}

## What goes wrong

- **Copying a command line from a forum.** Flags are removed and change meaning. Read each one in your version's `cli_args.py`.
- **`--highvram` "to go faster".** It keeps models on the card and turns dynamic VRAM off. On a shared card that can make things worse.
- **`--cache-none` to fix a VRAM error.** It mostly frees system RAM, and costs you every cached result. If the error is on the card, lower the size first.
- **Setting a flag and not checking it took.** Read the startup lines. `Set vram state to:`, the attention line and the cache line say what really happened. `--cache-classic` prints no cache line.
- **A flag "fixes" a problem once.** One run with one seed proves little. Test it twice, with and without.

## Lab

Ports of three functions. We also ran the real parser, separately, to confirm which flags refuse each other.

```text
does this set of flags ask for dynamic VRAM?
  no flags                           True
  --lowvram                          True
  --highvram                         False
  --gpu-only                         False
  --novram                           False
  --cpu                              False
  --disable-dynamic-vram             False
  --highvram --enable-dynamic-vram   True
```

The last row is worth a look: an explicit enable wins. Attention:

```text
which attention runs
  NVIDIA, torch 2, no flag               pytorch
  NVIDIA, --use-split-cross-attention    split
  NVIDIA, --use-sage-attention           sage
  NVIDIA, --use-flash-attention          flash
  NVIDIA, --use-ck-attention             comfy kitchen
  no pytorch default, no flag            sub quadratic
```

The node cache, whose default depends on your RAM:

```text
the node result cache
  no flag, 16 GB RAM       RAM pressure, keep 2 GB free
  no flag, 64 GB RAM       RAM pressure, keep 6.4 GB free
  no flag, 256 GB RAM      RAM pressure, keep 10 GB free
  --cache-ram 8            RAM pressure, keep 8 GB free
  --cache-lru 12           LRU, 12 results
  --cache-classic          classic
  --cache-none             none
```

And the reserve's second effect. Setting 4 GB doesn't only reserve 4 GB: the minimum working room goes up as well.

```text
--reserve-vram changes the room every load asks for, through minimum_inference_memory
  --reserve-vram None  reserved  0.39 GB   minimum working room  1.19 GB
  --reserve-vram 1     reserved  1.00 GB   minimum working room  1.80 GB
  --reserve-vram 4     reserved  4.00 GB   minimum working room  4.80 GB
```

## Sources

- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
