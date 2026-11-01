# CU-282 - Telling whether a LoRA works

**Objective.** Set up a fair test of a LoRA with one seed, then a strength sweep and several seeds, and say what the result does and doesn't show. Taught by Tinker Tune.

## The idea

To see what a LoRA does, change only the LoRA. Everything else stays: the prompt, seed, steps, CFG, sampler and scheduler. That's the whole method. Anything looser and you'll be judging the seed.

This graph does it in one go. One latent and one seed, through two samplers. Only the MODEL and CLIP differ.

{{graph:d_lora_compare}}

## Why the same seed

Here's a small stand-in network with a LoRA on one layer. It isn't an image model, but the arithmetic of comparing is the same.

```text
mean absolute difference between two outputs, 200 tries
pair                                difference
same seed, LoRA off against on      0.0869
new seed, LoRA off against on       0.4911
new seed, LoRA off against off      0.4842
at a new seed the LoRA's part is hidden: 0.4911 against 0.4842 with no LoRA at all, while the same-seed pair shows 0.0869
same seed, LoRA off twice: 0.0000  strength 0 is the base exactly, so anything else that moved is your test's fault
```

Change the seed, and the difference is 0.49 with or without the LoRA: the seed's own effect swamps it. Hold the seed, and only the LoRA's part is left, 0.087. And at strength 0, it's the base exactly, so if an off-and-off pair ever differs, something else in your test moved.

## One real pair, read carefully

Here's our own trained LoRA, one prompt, one seed, off and on. CU-281 has how it was trained.

{{wipe:train_art/lighthouse_base.webp|train_art/lighthouse_lora.webp|Off|On|Same prompt, seed 1234, strength 1. One seed.}}

Measuring how much moved is easy. This lab does it on the real pictures, off against on, and also for two unrelated base pictures.

{{play:diffpair}}

We get about 0.13 for the lighthouse and 0.25 for the harbour, against 0.23 for two unrelated pictures. Look at what that says. On the harbour prompt, at the same seed, the LoRA moved the picture about as far as switching to another picture altogether. So strength 1 here isn't a light touch. The number shows how much changed. It can't show whether it's the change you wanted. Only your eyes can do that, so write down what you're looking for before you look.

## Strength sweep

Next, keep the seed and step the strength. The weight moves in a straight line with strength, by the formula in CU-280. The output needn't.

```text
strength sweep, same seeds. The weight moves in a straight line. The output need not
strength   weight change   output change   change per unit of strength
0.0        0.0000          0.0000          0.0000
0.25       0.5534          0.0219          0.0874
0.5        1.1069          0.0435          0.0869
0.75       1.6603          0.0647          0.0862
1.0        2.2138          0.0853          0.0853
1.5        3.3207          0.1247          0.0831
2.0        4.4276          0.1610          0.0805
4.0        8.8551          0.2744          0.0686
-1.0       2.2138          0.0862          0.0862
```

In this tiny network the response is close to a straight line, and it flattens a bit at higher strengths. A real model has many layers and many steps, and its response may be far from straight, so your own sweep is the only way to know. Things to read off yours:

- At what strength does the effect first appear? If nothing shows until 1.5, the LoRA is weak on this prompt.
- Where does the picture start to break? Back off from there.
- Does negative strength do the opposite? The code allows it. It's a quick sanity check, if not always a pretty one.

A good first sweep: 0, 0.25, 0.5, 0.75, 1, 1.25. Six pictures. That's our suggestion, and not a measured rule.

## More than one seed

One seed can flatter a LoRA or sink it. In the stand-in:

```text
one seed can mislead: effect of the LoRA at strength 1, per seed
smallest 0.0151   median 0.0850   largest 0.2104   largest / smallest 13.9
```

The same LoRA's effect differs nearly 14-fold from seed to seed. A real model will differ by another amount, but the lesson holds. Three or four seeds, at your chosen strength, say more than one perfect sample. Our own example is two prompts at one seed each, and we're careful to say so.

## Four pictures for the trigger

If your LoRA has a trigger word, test the word and the LoRA separately.

```text
four pictures to make, one seed, and what each answers
LoRA   trigger   tells you
off    no        the base with this prompt
off    yes       what the word alone does on the base
on     no        what the LoRA does without its word
on     yes       the full effect
```

If "on, no trigger" looks just like "on, trigger", your trigger word isn't doing much, and the LoRA is always on. If "off, trigger" already changes a lot, then your word means something to the base model, and that's worth knowing.

Also try prompts away from your training set. Our harbour prompt is that test: a LoRA that changes a town into brass towers has learned something broader than a lighthouse.

## What goes wrong

- **Two runs differ with the LoRA off.** Something isn't fixed. Check the seed's `control_after_generate`, and any node with its own random input.
- **No change at all.** Read the log (CU-280). Keys may not have loaded, or the loader's outputs may not be wired on.
- **You compare with a different seed.** You're judging the seed. Fix it.
- **You pick the best of twenty seeds as proof.** That shows the best of twenty. Show several in a row.
- **The LoRA was trained on the same prompts you test with.** It'll look better than it is. Test new prompts.
- **You judge from the loss.** It can't tell you this (CU-281).
- **Everything looks burnt at strength 1.** Sweep down. Some files are stored strong (CU-280).

## Lab

The stand-in is a three-layer network with fixed random weights and a rank 4 LoRA on the middle layer, so that every comparison can be repeated exactly. It shows how comparing works, and it says nothing about any real LoRA's quality.

## Sources

- [Hu et al. 2021. LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/lora.py)
