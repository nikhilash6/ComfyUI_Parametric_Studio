# CU-450 - Installing without breaking anything

**Objective.** Try a new pack with layers of protection, so a bad one costs you an hour at most, and your working setup never moves. Taught by Tinker Tune.

## What can actually go wrong

Installing a pack can do three kinds of damage. Keep them separate, since each needs its own defence.

1. **It moves a package.** A newer `numpy` or an old `torch`, and something else that worked now doesn't. This one needs no bad intent at all.
2. **It changes behaviour.** It replaces a sampler or adds a server route, and your other jobs change with no error.
3. **It does something you didn't want.** It reads files, or reaches out. ComfyUI's policy says custom nodes "are arbitrary Python code".

## The layers

**Layer 1: read it first.** Everything in CU-380. It costs nothing, and it's the only layer that happens before any code runs.

**Layer 2: a dry run, with constraints.** `pip install --dry-run` prints what it would install and installs nothing. It still has to resolve, so it can download packages, and for a package that comes only as source it may run that package's build code to read its metadata. Add `--only-binary :all:` if you want to rule that out. A constraints file pins the versions you depend on: as pip's guide says, constraints "only control which version of a requirement is installed, not whether it is installed or not". So:

```
python -m pip freeze > constraints.txt                  # once, while everything works
pip install --dry-run -c constraints.txt -r pack/requirements.txt
```

If it can't resolve, that's your answer, and nothing in your environment moved. A failure on paper is good news. Packages you truly can't let move are worth keeping as a short list, and checking against the report by name. Be aware that a pack can also call pip from its own code at import, which no dry run will see, and that's why you read first.

**Layer 3: a separate environment.** Don't touch the venv you use every day. A venv gives you "its own independent set of Python packages". So make another and install there. To start from what you have, reinstall your frozen list into it: the venv docs say an environment is "Not considered as movable or copyable", so recreate it and don't copy the folder.

**Layer 4: a sandbox.** Run the test copy in a container, or at least apart from your main install. Good choices:

- **No outside network.** `docker network create --internal` restricts external access. Anything that wants to phone home now fails, and you'll see it.
- **Models and the venv mounted read-only.** A pack can't change your weights if it can't write to them.
- **One writable folder for output**, so you can see what it writes.
- **None of your keys or home folder** inside. If it isn't mounted, it can't be read.
- **A different port**, and `--base-directory` for a separate folder layout.

Load the pack together with the packs you'll use it with, because conflicts only show up then.

**Layer 5: a smoke test, in order.** First see that the import worked: the console lists custom nodes with `IMPORT FAILED` beside any that broke. Then run a graph that uses no model at all, then a real graph with its nodes. It costs seconds.

{{graph:nm_first}}

**Layer 6: copy it across, and write it down.** Note the pack's commit, the date, what you read, and what the test showed. Then an update is a decision, not a surprise. Never blind-update a pack you've changed locally: you'd lose your changes.

Put them in order:

{{play:install}}

## Undoing

Keep it easy. ComfyUI skips a folder whose name ends in `.disabled`, and `--disable-all-custom-nodes` starts with none, so you can tell whether a problem comes from a pack. `--whitelist-custom-nodes` then lets you add them back one at a time, which is the fastest way to find which one is to blame. If you froze your package versions before you began, you can compare against that list.

## What goes wrong

- **Running a pack's `install.py` or a tool's "install" button without reading it.** That's Layer 1 skipped.
- **`--force-reinstall` to clear an error.** That moves packages. Find out why first.
- **A clean dry run, so it must be safe.** A dry run only looks at versions. It says nothing about what the code does.
- **Testing alone and shipping together.** Packs interact. Test with your real set.
- **`failed` in the sandbox means it's bad, or `ok` means it's good.** A failure may be a missing library. Loading proves that it loaded, and no node has run yet.
- **A patched pack updated blind.** A `git pull` on something you've changed can overwrite it or conflict. Read your changes first.

## Lab

A tiny checker: which packages would a pack move, and what does a constraints file do about it? All names and versions are examples. Real resolvers do far more.

```text
dry run with no constraints
  pack A, modest             newlib None -> 1.2.0
  pack B, wants old opencv   opencv-python 5.0.0 -> 4.11.0
  pack C, wants old numpy    numpy 2.1.0 -> 1.26.4 PROTECTED
  pack D, pins torch         torch 2.8.0 -> 2.5.0 PROTECTED
```

```text
dry run with the constraints file
  pack A, modest             newlib None -> 1.2.0
  pack B, wants old opencv   opencv-python 5.0.0 -> 4.11.0
  pack C, wants old numpy    no moves  FAILS: numpy: nothing fits <2 with ==2.1.0
  pack D, pins torch         no moves  FAILS: torch: nothing fits ==2.5.0 with ==2.8.0

a failure in the second list is good news: it happened on paper, not in your environment
```

Pack B moves a package you didn't protect, so it's your call. The lab's constraints file is a short one that pins only torch, numpy and safetensors. A file from `pip freeze` pins everything installed, so it would stop Pack B as well. Packs C and D now fail instead of moving what you need. That failure happened on paper.

```text
what each layer of the method protects against
  read the text first                                a surprise at import
  dry run with constraints                           a version moving under other packs
  a second venv                                      breaking the one you use
  a container, no outside network, read-only models  a pack reaching out, or changing weights
  a no-model graph, then a real graph                a pack that imports but does not work
  --disable-all-custom-nodes                         not knowing whether a pack is to blame
```

## Sources

- [pip user guide, Constraints Files](https://pip.pypa.io/en/stable/user_guide/)
- [pip install reference](https://pip.pypa.io/en/stable/cli/pip_install/)
- [Python docs, venv](https://docs.python.org/3/library/venv.html)
- [Docker, network create](https://docs.docker.com/reference/cli/docker/network/create/)
- [Docker, container run](https://docs.docker.com/reference/cli/docker/container/run/)
- [ComfyUI v0.43.0, SECURITY.md](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/SECURITY.md)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
