# CU-385 - How to pick between packs, and when core already does it

**Objective.** Decide between core, a pack and writing your own, for a real need, in a way you could explain to someone else. Taught by Captain Graph.

## Start by not installing anything

Each pack you add is more code running at every start, more things that can break on an update, and more to read. So a pack has to earn its place. Most of this lesson is how to find out it doesn't need to.

## The ladder

**1. Does core already do it?** Core has grown a lot. Search your node list first, by what the thing does, since names differ. Read the description. Several guidance methods, step caches, grids and mesh tools are built in, and an old guide may not know that.

{{graph:sd15_pag}}

**2. If core is close, what exactly is missing?** Write the gap down as one sentence. "I want a grid" is met by `ImageGrid`. "I want a labelled grid with two sweep axes, and video cells" isn't. If you can't name what core lacks, you don't need a pack yet.

**3. Find candidates, and read them.** Use CU-380's method. Read for what the code does, and not what the page says. Check that the name means what you think (CU-382). Drop copies: if one pack is a fork of another, use the original unless the fork has a fix you can name.

**4. Check the costs.** Would it run at start, change other jobs, or move a package? Which licence does it have (CU-383)? How much of it do you need? A huge toolkit for one node carries all the rest of its risk and its import time.

**5. Pick one of three answers.**

- **Candidate:** test it in a sandbox (CU-450), then decide.
- **Borrow the idea:** the method is good, but the side effects or the licence aren't. Write your own, in your own words, from the idea or the paper.
- **Read it and leave it:** it taught you something. That's still a good result.

## Three worked cases

These are real, and we read the code as text. None was run for this lesson.

**Perturbed-attention guidance.** Core has `PerturbedAttentionGuidance`. Start there. sd-perturbed-attention (MIT) has it too, along with methods core doesn't have, such as token perturbation guidance in `tpg_nodes.py`. So it answers a different question: you'd reach for it for those, not for plain PAG.

**A step cache.** Core has `EasyCache` and `LazyCache`. Try them, and time them. ComfyUI-MiniMaxH3-FirstBlockCache (MIT) decides from one real block's output, for one model family. Its README reports 1.44× to 1.49× and says plainly that it's an approximation. That's the author's number, and only useful once you have your own baseline from core's cache. Don't stack step caches, because they patch the same forward path.

{{graph:g_easycache}}

**A comparison grid.** Core has `ImageGrid` and `ImageCompare`, which handle images with no axes. ComfyUI-SweepGrid (MIT) adds sweep combinations and video grids, so here's a real gap. Worth reading, then testing.

Being on our list means someone read it. It isn't a promise that it works for you.

## Try it

{{play:pick}}

## What goes wrong

- **Installing from an old guide.** Core may have caught up. Search first.
- **Picking by stars or by name.** Stars measure attention, and new packs for new models have few. A name doesn't tell you the maths.
- **A toolkit for one node.** You take on everything in it. Weigh the whole pack.
- **Two packs patching the same thing.** Results change with no error. Use one at a time and test it alone first.
- **Taking an author's speed number as yours.** Measure on your graph (CU-373).
- **A pack with no licence, for a project you'll ship.** Take the idea if that's allowed, and write your own (CU-383).

## Lab

A small version of the ladder as code. The rows about real packs use facts we read. The last two rows are made up, to show the other outcomes.

```text
perturbed-attention guidance                 core: PerturbedAttentionGuidance  
  -> use core, and measure before looking further
token perturbation guidance                  core: None                        
  -> read it, test it in a sandbox, then decide
a step cache                                 core: EasyCache, LazyCache        
  -> use core, and measure before looking further
a labelled sweep grid with video             core: ImageGrid, ImageCompare     
  -> read it, test it in a sandbox, then decide
an idea from a pack that patches every job   core: None                        
  -> borrow the idea, not the pack
code from a pack with no licence             core: None                        
  -> do not copy. Write your own from the idea
```

And why fewer packs is the default:

```text
cost of a dependency: packs multiply what must keep working
   1 packs, each with a 2% chance of breaking per ComfyUI update:  2.0% chance something breaks. The 2% is an example, not a measurement.
   5 packs, each with a 2% chance of breaking per ComfyUI update:  9.6% chance something breaks. The 2% is an example, not a measurement.
  20 packs, each with a 2% chance of breaking per ComfyUI update: 33.2% chance something breaks. The 2% is an example, not a measurement.
```

The 2% is made up, for the arithmetic. Small chances add up across many packs. And before a speed claim counts:

```text
what speed claims need before they count
  whose number is it
  same graph and seed with and without
  first run left out
  picture compared, not just the clock
```

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_pag.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_pag.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_easycache.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_easycache.py)
- [pamparamm/sd-perturbed-attention](https://github.com/pamparamm/sd-perturbed-attention)
- [duckyshell/ComfyUI-MiniMaxH3-FirstBlockCache](https://github.com/duckyshell/ComfyUI-MiniMaxH3-FirstBlockCache)
- [embedding-shapes/ComfyUI-SweepGrid](https://github.com/embedding-shapes/ComfyUI-SweepGrid)
