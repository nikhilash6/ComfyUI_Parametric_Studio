# CU-504 - History 4: StyleGAN and style modulation

**Objective.** Write down the two ways StyleGAN lets a style control a feature map, AdaIN in 2018 and weight demodulation in 2019, check what each keeps and forgets, and find the same scale-and-shift idea in ComfyUI's U-Nets and transformer blocks. Taught by Professor Latent.

## The idea

In a traditional GAN the latent code enters at the first layer, and everything about the picture is decided there. In December 2018 Karras, Laine and Aila posted "A Style-Based Generator Architecture for Generative Adversarial Networks", "borrowing from style transfer literature". Their generator starts from a learned constant tensor of 4×4×512. An 8-layer mapping network turns the latent z into a vector w, and a learned affine map turns w into a style for each of the 18 synthesis layers. Single-channel noise images add stochastic detail. The abstract claims an "automatically learned, unsupervised separation of high-level attributes" such as pose and identity "and stochastic variation" such as freckles and hair, with "scale-specific control of the synthesis".

On FFHQ, the 70,000-image face dataset the paper introduced, FID (lower is better) fell from 8.04 for the Progressive GAN baseline to 5.25 with tuning, 4.85 with the mapping network and styles, 4.42 with noise inputs and 4.40 with mixing regularisation (Table 1).

## The maths

A style acts through adaptive instance normalisation. Huang and Belongie introduced AdaIN for style transfer, where the scale and shift are the standard deviation and mean of a style image's features. StyleGAN takes them from the learned affine map of w instead (eq. 1):

```
AdaIN(x_i, y) = y_s,i · ( x_i − μ(x_i) ) / σ(x_i) + y_b,i
```

Each feature map x_i is normalised on its own, then scaled and shifted by two numbers from the style y. Afterwards map i has mean y_b,i and standard deviation y_s,i, whatever it had before, and its spatial pattern is untouched.

In December 2019 the StyleGAN2 paper found blob-shaped "water droplet" artifacts, visible in the intermediate feature maps from about 64×64 up. It pinpoints AdaIN, which normalises each feature map separately and so potentially destroys "any information found in the magnitudes of the features relative to each other". Its hypothesis is that the generator sneaks signal strength past the normalisation, and removing the normalisation made the artifacts disappear. Its replacement scales the convolution weights instead of the activations (eqs. 1 to 3):

```
w'(i,j,k)  = s(i) · w(i,j,k)                         modulation, s(i) is the style for input map i
σ(j)       = sqrt( Σ over i,k of w'(i,j,k)² )        output std, if the inputs are independent with unit std
w''(i,j,k) = w'(i,j,k) / sqrt( Σ w'(i,j,k)² + ε )    demodulation
```

The authors call this "weaker" than instance normalisation, "because it is based on statistical assumptions about the signal instead of actual contents of the feature maps".

## In ComfyUI

There is no StyleGAN generator in ComfyUI. There are two traces of it.

- **StyleGAN2 layers.** `comfy/ldm/wan/model_animate.py` defines `EqualConv2d`, `EqualLinear`, `ConvLayer` and `ResBlock`, each with a comment pointing at the StyleGAN2 file of the BasicSR project. They multiply their weights at run time by 1/√fan-in, the equalised learning rate that the StyleGAN paper says it uses "for all layers". That file has no modulated convolution.
- **The scale-and-shift pattern.** `modulate(x, shift, scale)` in `comfy/ldm/modules/diffusionmodules/mmdit.py` returns shift + x·(1 + scale). `DismantledBlock` is documented as "A DiT block with gated adaptive layer norm (adaLN) conditioning", and it applies `modulate` to the output of a LayerNorm (or RMSNorm) that has no learned affine. In `openaimodel.py`, the U-Net option `use_scale_shift_norm`, documented as "a FiLM-like conditioning mechanism", makes `ResBlock` normalise, multiplies by (1 + scale) and adds shift, with scale and shift as the two halves of the embedding. The DiT paper says its adaLN follows "the widespread usage of adaptive normalization layers" in GANs and in diffusion U-Nets, and FiLM (Perez et al.) names the general idea: a feature-wise affine transformation based on conditioning information.

Compare the two forms yourself on one small feature map.

{{play:adain}}

The modern descendant is in this graph. SD 3.5's blocks are `DismantledBlock`s, so each one scales and shifts its tokens using numbers worked out from the timestep and the pooled text.

{{graph:sd35_flow}}

## What goes wrong

- **You write AdaIN as content × (1 + style).** That is `modulate`, a different thing. AdaIN throws away the input's mean and spread first. The lab shows the difference: 3.6e-15 against 42.1.
- **You think Apply Style Model is StyleGAN.** The name misleads. `StyleModelApply` in `nodes.py` encodes the reference and adds it to the conditioning tokens, so it changes what the model reads. Nothing about it modulates feature maps.
- **You look for a StyleGAN node.** Core has no StyleGAN generator. Two traces are listed above.
- **You trust one number.** The droplets survived FID: 4.40 to 4.39, with the artifact gone. Look at intermediate maps, or at a lot of images, before you say a flaw is absent.
- **You normalise features inside your own node.** You have then thrown away anything the layer knew about its own magnitudes, which is what StyleGAN2 blames for its droplets. Keep a "do nothing" setting that really does nothing.
- **You trust demodulation on smooth inputs.** Its promise of unit spread assumes independent inputs. Blurred ones gave 0.661 to 1.326 in the lab.

## Lab

Part one gives AdaIN four feature maps whose means run from −2 to 40 and whose standard deviations run from 0.07 to 1.9, with four different styles.

```text
channel  input mean  input std   style y_b  style y_s   output mean  output std  correlation with input
0          -0.029      0.288      +1.00       0.50       +1.000       0.500      +1.0000
1          +6.910      1.872      -1.00       2.00       -1.000       2.000      +1.0000
2          -1.983      0.070      +0.00       1.00       +0.000       1.000      +1.0000
3         +40.136      0.950      +4.00       3.00       +4.000       3.000      +1.0000
```

Each output has exactly the style's mean and standard deviation, and its correlation with the input is +1.0000: the spatial pattern survives, the statistics do not.

Part two asks what is forgotten. Give AdaIN and the (1 + scale) form two inputs with the same pattern and different per-channel scale and offset:

```text
inputs that differ only by a per-channel scale and offset: largest output difference  AdaIN 3.6e-15   shift + x(1 + scale) 42.1
style set to 'do nothing' (scale 0, shift 0, or y_s 1, y_b 0): largest change to the input  shift + x(1 + scale) 0.0   AdaIN 40.3
```

AdaIN cannot tell the two inputs apart, which is what makes style control clean, and it also means it cannot pass on anything the layer knew about its own magnitudes. The (1 + scale) form keeps the incoming scale and offset, so the outputs differ by 42.1, and it can do nothing exactly. AdaIN cannot: even its "do nothing" setting rewrites the map. A common mistake is to write AdaIN as content × (1 + style). That is the form in `modulate`, not AdaIN.

Part three is StyleGAN2. The styles differ by 40 times (0.2 to 8), the weights are random, and the inputs are independent with unit variance.

```text
modulating activations against modulating weights: largest difference 2.8e-14
output map j          0       1       2       3       4       5       6       7
predicted std       30.59   27.31   29.88   27.60   24.83   32.39   22.46   23.68
measured std        30.61   27.33   29.89   27.62   24.84   32.41   22.53   23.71
after demodulation  1.001   1.001   1.000   1.001   1.001   1.001   1.003   1.002
```

Scaling the activations or scaling the weights gives the same output to 2.8e-14, and the predicted standard deviation from the formula matches the measured one, for example 30.59 against 30.61. Without demodulation the outputs have a standard deviation of 22 to 32 instead of 1. After demodulation every map is within 0.003 of 1.

Part four breaks the assumption. Same demodulated weights, inputs blurred with a 3×3 box and rescaled to unit variance:

```text
demodulated outputs for smooth inputs: smallest std 0.661, largest 1.326  (independent inputs gave 1.000 to 1.003)
```

Demodulation promises unit standard deviation only for independent inputs. That is the "weaker" in the quotation above, as a number.

## What is contested

The droplet explanation is a hypothesis. The StyleGAN2 authors support it with the finding that the artifacts vanish when normalisation is removed, not with a proof.

FID did not see the problem. With weight demodulation FID went from 4.40 to 4.39 (StyleGAN2 Table 1, rows A and B), and the paper says it "remains largely unaffected", although the artifacts were gone. A single quality number can miss a systematic flaw.

"Diffusion beat GANs" is also a statement about particular tables. In the DiT paper's Table 2 for class-conditional ImageNet 256×256, StyleGAN-XL has FID 2.30 and the best DiT 2.27. A gap of 0.03 is not a verdict.

## Sources

- [Karras, Laine, Aila 2018. A Style-Based Generator Architecture for Generative Adversarial Networks](https://arxiv.org/abs/1812.04948)
- [Karras et al. 2019. Analyzing and Improving the Image Quality of StyleGAN](https://arxiv.org/abs/1912.04958)
- [Huang, Belongie 2017. Arbitrary Style Transfer in Real-time with Adaptive Instance Normalization](https://arxiv.org/abs/1703.06868)
- [Perez et al. 2017. FiLM: Visual Reasoning with a General Conditioning Layer](https://arxiv.org/abs/1709.07871)
- [Peebles, Xie 2022. Scalable Diffusion Models with Transformers](https://arxiv.org/abs/2212.09748)
- [ComfyUI v0.43.0, comfy/ldm/wan/model_animate.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/wan/model_animate.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/mmdit.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/mmdit.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/openaimodel.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/openaimodel.py)
