# CU-404 - Evaluating outputs: metrics, checks and their limits

**Objective.** Pick a measure that fits your question, know what PSNR, SSIM and FID can and can't tell you, and test it on a pair where a score means something. Taught by Tinker Tune.

## The idea

A metric is a measuring tool for one narrow question. Before you trust a number, ask what it compares.

- **Two pictures that ought to match**, such as a VAE round trip, or a tile seam. Use PSNR or SSIM.
- **Two sets of pictures**, such as this checkpoint against real photos. Use FID or similar, with thousands of samples.
- **A picture and its prompt.** That's CU-413.
- **Which of two pictures a person prefers.** Ask people.

Two renders from different seeds aren't meant to match, so PSNR between them says nothing about quality.

Core ComfyUI has no node for any of these. We searched the source for PSNR, SSIM and LPIPS and found none. So you save files and measure outside, or use a pack you've read.

## The mechanism

**PSNR** is pixel error on a log scale, for values from 0 to 1:

```
MSE  = mean of (a − b)²             PSNR = 10 × log₁₀( 1 ÷ MSE )
```

10 dB more means a tenth of the squared error. It ignores what kind of error it is.

**Pearson correlation** ignores brightness and contrast. Add a constant to one image and r stays at 1.

**SSIM** (structural similarity) compares means, spreads and how the two vary together, window by window, and then averages. The LPIPS paper by Zhang et al. (2018) calls PSNR and SSIM simple, shallow functions that miss many nuances of perception, and tests deep features as a better match to human judgement. We name LPIPS so that you know it exists. The lab doesn't compute it.

**FID** (Fréchet Inception Distance, Heusel et al. 2017) compares clouds rather than pairs. Run many images through a pre-trained network, fit a mean and covariance to each set, and compute:

```
FID = ‖μ₁ − μ₂‖² + Tr( C₁ + C₂ − 2 (C₁ C₂)^½ )
```

Lower is closer. It depends on the sample count, as the lab shows.

{{play:metrics}}

## In ComfyUI

A pair that should match is easy to make. This graph encodes a picture and decodes it, and the only loss is the VAE's. Save the output and compare it to the input with a script.

{{graph:h_vae_roundtrip}}

To gather a set for FID you need many renders at many seeds. `KSampler` takes a seed input, and CU-460 shows how to queue a graph with a new seed from a script. `SaveImage` numbers its files. The measuring has to happen outside.

## What goes wrong

- **Comparing two seeds with PSNR.** They aren't meant to match. Read the lab line about a different picture: it's low for any two unrelated images, however good.
- **A score goes up and the picture looks worse.** Blur scores high on PSNR: 31.60 dB in the lab, above a one-pixel shift that a viewer wouldn't notice. Always look at the images too.
- **FID compared across sample sizes.** It's biased upwards at small sizes. Keep the sample count, the feature network and the resize method the same.
- **FID on 50 images.** The lab's true distance is 0, and 50 samples per side gives 1.74. On real features the size of this effect differs, but it never goes away.
- **Averaging hides a local failure.** A broken face in a large image barely moves a whole-image score. Crop and measure the part you care about.

## Lab

A made-up 64×64 image and five changes. The SSIM uses plain square windows instead of a Gaussian window, so the values won't match a library's exactly.

```text
change                     PSNR dB   Pearson r   SSIM
identical                  inf       1.0000      1.0000
brighter by 0.10           20.00     1.0000      0.9657
shift 1 pixel              27.96     0.9754      0.9236
shift 4 pixels             19.65     0.8329      0.5583
box blur 5x5               31.60     0.9898      0.9621
noise, same MSE as +0.10   20.00     0.8771      0.4430
```

Read two rows against each other. "Brighter" and "noise" have the same PSNR, 20.00, by design. SSIM tells them apart. Pearson calls "brighter" perfect. Now each metric's blind spot: a 5×5 blur beats a 1-pixel shift on both PSNR and SSIM, though most viewers would call the shift the same picture and the blur softer.

```text
a different picture with the same style of content: PSNR 11.02, r -0.2819
```

Now FID on two samples of one 8-dimensional Gaussian. The true distance is zero.

```text
samples per side  FID, both sides from the same distribution
50                1.7364
200               0.3766
1000              0.0829
5000              0.0155
the true distance is 0. a small sample still scores above 0, so only compare FIDs at the same sample size
```

This uses made-up features, not a pre-trained network, so the numbers don't carry over to a real FID. The direction does.

## Sources

- [Heusel et al. 2017. GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium](https://arxiv.org/abs/1706.08500)
- [Zhang et al. 2018. The Unreasonable Effectiveness of Deep Features as a Perceptual Metric](https://arxiv.org/abs/1801.03924)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
