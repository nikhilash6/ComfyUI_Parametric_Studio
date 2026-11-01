# CU-407 - Reading a generative-AI paper in 20 minutes

**Objective.** Read a paper quickly by pulling out its claim, baseline, measure and spread, and spot the three commonest ways a result looks better than it is. Taught by Professor Latent.

## The idea

Most papers aren't worth a slow read for your purpose. A quick pass tells you if one is. You're looking for four things.

1. **The claim**, one sentence in your own words.
2. **The baseline.** Better than what, at the same settings?
3. **The measure.** What number, on what data, with which sample count?
4. **The spread.** How much would that number move on a rerun?

Then ask whether it matters to you. A speed-up on a model you don't run doesn't.

## A 20-minute order

| Minutes | Read | Ask |
|---|---|---|
| 2 | Title and abstract | What's the claim? Is it about my problem? |
| 3 | Figures and captions | Do the pictures show what's claimed, or a best case? |
| 5 | Results tables | Which baseline, which metric, is any spread shown? |
| 5 | Method, skim | What's the change, and what does it cost? |
| 3 | Limits and appendix | What did they leave out? Is code or weight data available? |
| 2 | Your note | One line each: claim, baseline, measure, spread, what to test |

These minutes are our own suggestion, not research. Adjust them.

## A worked example

Here's the abstract of the GQA paper from CU-302, read this way: "We show that uptrained GQA achieves quality close to multi-head attention with comparable speed to MQA."

- **Claim.** Grouped-query attention, retrained from a multi-head checkpoint, keeps most of the quality and gains most of the speed.
- **Baseline.** Two of them: multi-head for quality, multi-query for speed. Good: it says both.
- **Measure.** "Close to" and "comparable to" have no numbers. Go to the tables.
- **Spread.** Not in the abstract.
- **Cost.** The 5% of original pre-training compute it names is for its recipe that retrains into multi-query attention. The abstract gives no figure for GQA itself, so check the paper before you plan on it.
- **My problem?** It's about language models. For image models, it's only a lead.

We read the abstract, not the tables, so this stops there. That's the honest end of a 2-minute read.

## The three traps

**Best of many runs.** If a method was tried many times and the best is reported against a plain baseline, a gain appears from nothing.

{{play:bestof}}

**No spread.** A number without a range can't be judged. A rough check: the difference should be over about twice its standard error.

**Many metrics.** With several measures, one will favour the new method by chance. Look for which were decided on in advance, if that's stated.

## Using the paper in ComfyUI

To test a claim yourself, find the closest graph. For a paper that changes a sampler or a guidance rule, start from a plain graph, and change only that part. Then use CU-470's method: many seeds, and the same seeds for both sides.

{{graph:sd15_txt2img}}

If the code isn't in core, be careful. A pack's implementation may differ from the paper's. Read it before you run it, as the packs track shows.

## What goes wrong

- **Trusting the abstract.** An abstract picks the headline. Check the table.
- **Comparing numbers across papers.** Sample count, data split and resize method change FID (CU-404). Only same-setup comparisons hold.
- **Being fooled by percent.** A −0.1 change on a base of 0.2 is 50%. On a base of 10 it's 1%. Read the absolute change too.
- **Missing the cost.** Lower error can come with more model calls per step. Compare by total calls, not steps (CU-205 and CU-470).
- **Assuming a picture is typical.** Figures are chosen. Ask how they were picked, and whether seeds are shown.

## Lab

All numbers here are made up by the script, and stand for no real paper. First, best of k runs when the true gain is zero:

```text
runs tried, best one reported   average apparent gain, true gain is 0 (noise sd 1)
1                               -0.01
3                               0.84
5                               1.16
10                              1.54
30                              2.04
```

Next, the same difference with different spreads and run counts. The range is two standard errors each way.

```text
new    sd    base   sd    runs  difference  range             verdict
2.30   0.05  2.40   0.05  5     -0.10       -0.163 to -0.037  clear of 0
2.30   0.20  2.40   0.20  5     -0.10       -0.353 to +0.153  includes 0, no claim
2.30   0.20  2.40   0.20  50    -0.10       -0.180 to -0.020  clear of 0
2.30   ?     2.40   ?     1     -0.10       can't tell        no spread given, so no judgement
```

"Two standard errors" is a rule of thumb, and not a full test. It assumes the runs are independent. Then percent, and many metrics.

```text
base  new   change  percent
10.0  9.9   -0.1    -1%
1.0   0.9   -0.1    -10%
0.2   0.1   -0.1    -50%
```

```text
8 unrelated metrics, no true difference: at least one looks 'clear of 0' in 32% of papers
```

## Sources

- [Ainslie et al. 2023. GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints](https://arxiv.org/abs/2305.13245)
- [Heusel et al. 2017. GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium](https://arxiv.org/abs/1706.08500)
