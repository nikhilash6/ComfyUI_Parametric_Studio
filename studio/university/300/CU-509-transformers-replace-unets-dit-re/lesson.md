# CU-509 - History 9: Transformers replace U-Nets: DiT and rectified flow

**Objective.** Keep apart the two changes that arrived together, a new network shape and a new noise path, see from an exact answer what "straight" does and doesn't give you, and find both in ComfyUI. Taught by Madame Attention.

## The idea

Two papers from 2022 get told as one story. They are separate ideas.

**DiT changes the network.** Peebles and Xie posted "Scalable Diffusion Models with Transformers" on 19 December 2022. They replace "the commonly-used U-Net backbone with a transformer that operates on latent patches". Cut the latent into patches, and each patch is a token that attends to every other (CU-303). Their abstract reports that models with more Gflops "consistently have lower FID", and an FID of 2.27 on ImageNet at 256. Those are still diffusion models, trained the older way.

**Rectified flow changes the path.** Liu, Gong and Liu posted "Flow Straight and Fast" on 7 September 2022. Pick a noise point and a data point, and join them with a straight line. Train a model to give the velocity along the line. It's a plain least-squares problem. Lipman et al. posted "Flow Matching for Generative Modeling" a month later, with Optimal Transport paths as one option, which its abstract says are more efficient than diffusion paths.

**SD3 put them together.** Esser et al. posted "Scaling Rectified Flow Transformers for High-Resolution Image Synthesis" in March 2024. Their abstract still says rectified flow "is not yet decisively established as standard practice", and it reports a large study in its favour, using their new way of sampling noise levels in training. It also brings a transformer with separate weights for image and text. That is the design ComfyUI runs as `MMDiT`.

So a transformer doesn't need flow, and flow doesn't need a transformer. In ComfyUI, HunyuanDiT is a transformer trained to predict v, and PixArt has an old-style beta schedule.

## The mechanism

Pair a noise sample x0 with a data sample x1, and let t run from 0 at noise to 1 at data.

```
x_t = (1 − t) · x0 + t · x1
v   = x1 − x0
loss = ‖ v_θ(x_t, t) − (x1 − x0) ‖²
```

For one pair, the velocity is the same all the way along the line. That part is true by construction.

Now the catch. Pairs are drawn at random, so lines cross. At a crossing point the model sees many different right answers, and least squares gives their average. So the model learns E[x1 − x0 | x_t]. That field has curved paths, and it is not the straight lines you trained on.

The extreme case is t = 0. Noise says nothing about which data point it will meet, so the field there is the mean of the data minus x. One Euler step from noise therefore lands every sample on the mean of the data, whatever the noise was.

**Reflow** is what the paper does about this. Run the trained flow to get pairs (start, where it ended). Those pairs were made by one smooth flow, so they don't cross. Train a new model on them. Its paths are much straighter, and that is when a single step can work. The paper's abstract says "nearly straight flows that give high quality results even with a single Euler discretization step", and it gets there by repeating this rectification.

## In ComfyUI

- **The network.** `MMDiT` in `comfy/ldm/modules/diffusionmodules/mmdit.py` is the SD3 family. `JointBlock` holds a `DismantledBlock` for each of image and text. The conditioning goes in through `adaLN_modulation`, which gives the numbers for `modulate` (CU-504). It scales and shifts the tokens after a norm. It doesn't reach into the attention scores.
- **Other families.** FLUX has its own `Flux` class in `comfy/ldm/flux/model.py`, with `double_blocks` and `single_blocks`. `HunYuanDiT` is in `comfy/ldm/hydit/models.py` and uses rotary embeddings through `apply_rotary_emb`. Audio has `AceStepDiTModel` in `comfy/ldm/ace/ace_step15.py`.
- **The path.** `CONST` in `comfy/model_sampling.py` writes the same line from the other end. Here sigma is 1 − t, so sigma 1 is pure noise. `noise_scaling` returns sigma · noise + (1 − sigma) · latent. `calculate_denoised` returns input − output · sigma. That makes the model's output noise minus data, the opposite sign to the paper's v, which the lab checks.
- **The schedule.** `ModelSamplingDiscreteFlow` bends the steps with `time_snr_shift`, shift · t / (1 + (shift − 1) · t). The `SD3` config sets a shift of 3.0, and `ModelSamplingSD3` lets you change it.

The tokens first. Set a 1024 image with a patch of 2 and see what a DiT has to attend over.

{{play:patches}}

And the graph. The node that says "flow" is `ModelSamplingSD3`, and it is the only thing here that says so.

{{graph:sd35_flow}}

FLUX.2 Klein is the same idea, with the parts laid out as separate nodes.

{{graph:wf_flux2_klein}}

## What goes wrong

- **"Straight, so one step will do."** Not for a model trained on random pairs. The lab's trained first flow scores 1.30 at one step, about the same bad result as the exact field. One step needs reflow or another form of distillation (CU-514), and a file made that way.
- **You read "transformer" as "flow".** They are separate choices. The model's sampling type is what tells ComfyUI how to read its output. Our `b_vpred` graph shows what that setting does, and why it has to match how the model was trained.
- **You treat shift as a quality dial.** It only moves where the steps fall. In our one-dimensional toy, shift 3 is no better than even steps, at 8 steps or at 64. That says nothing about images, so test yours on a real picture.
- **You use the wrong empty latent.** SD3's latent has 16 channels and needs `EmptySD3LatentImage`. `EmptyLatentImage` makes 4.
- **You expect U-Nets to be gone.** ComfyUI still ships them and `sd15_txt2img` runs on one. The history here is about what new families chose, and doesn't say the old models broke.
- **You compare token cost to U-Net cost by feel.** Twice the side means four times the tokens and sixteen times the attention pairs. The `patches` lab above shows this, and a transformer pays it in every block.

## Lab

The data is a mix of two Gaussians, so the true velocity field has a formula and needs no training. First the promise, for one pair, and then the catch.

```text
one pair x0 = -0.7, x1 = 1.3: speed on each quarter of the line [2.0], x1 - x0 = 2.0
one Euler step from t = 0: every one of 20,000 samples lands in [0.4500, 0.4500]; the mean of the data is 0.4500
```

Every one of the 20,000 samples lands on 0.4500, the mean of the data. No picture has ever looked like that. Now more steps. W1 is the average gap between sorted samples and the real data, so lower is better.

```text
error (W1) against the real data, by number of Euler steps. Two real samples differ by 0.0271
steps   even in t   shift 3 (SD3 default)
1       1.4847      1.4847
2       0.6290      0.9033
4       0.3253      0.3253
8       0.1736      0.1785
16      0.0986      0.1032
32      0.0614      0.0646
64      0.0423      0.0441
```

Error nearly halves each time the steps double, until it nears the floor of what two real samples differ by. That is the ordinary behaviour of Euler on a curved path. Shift 3 is no better here. This is one small toy. How straight are those paths really?

```text
exact field: mean squared departure from a straight line 0.7936 (0 would be perfectly straight)
```

Now two small networks with the same training code. The first has independent pairs, which makes it the first flow. The second has the pairs the first flow produced, which is reflow. One seed.

```text
trained model                 departure from straight   W1 at 1 step   2 steps   4 steps   64 steps
first flow, independent pairs 0.7470                    1.2999   0.8678   0.4121     0.0451
reflow, the first flow's pairs 0.0019                    0.0962   0.0620   0.0442     0.0306
one step: reflow's error is 13.5 times smaller
```

The first network behaves like the exact field: 0.7470 against 0.7936 for straightness, and about the same error at one step. Reflow drops straightness to 0.0019, and one step gets to 0.0962, 13.5 times better. The price is that you have to generate all those pairs first, and train a second time. And last, ComfyUI's form of the same line.

```text
CONST: sigma 0.35, input 0.1350, output noise - data -1.9000, calculate_denoised gives 0.8000, the clean value is 0.8000
```

The lab is one-dimensional. It checks the mathematics of paths, and says nothing about image quality or about why any one family made its choices.

## What is contested

"Better" depends on what you hold fixed. The SD3 study compares formulations under its own noise-level sampling, and the abstract reports that its approach beats established diffusion formulations. It doesn't say the straight path alone did that. Flow Matching's abstract reports faster training and sampling for its Optimal Transport paths, and, in a separate sentence, better ImageNet results for training with Flow Matching than for diffusion-based methods. We did not re-run any of these.

Scale is contested too. DiT's abstract ties lower FID to more Gflops within its own family. That doesn't show transformers always beat U-Nets at the same cost, and we don't have a measurement here that could.

## Sources

- [Peebles, Xie 2022. Scalable Diffusion Models with Transformers](https://arxiv.org/abs/2212.09748)
- [Liu, Gong, Liu 2022. Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow](https://arxiv.org/abs/2209.03003)
- [Lipman et al. 2022. Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747)
- [Esser et al. 2024. Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/mmdit.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/mmdit.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/model.py)
- [ComfyUI v0.43.0, comfy/ldm/hydit/models.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/hydit/models.py)
- [ComfyUI v0.43.0, comfy/ldm/ace/ace_step15.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/ace/ace_step15.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy/supported_models.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models.py)
