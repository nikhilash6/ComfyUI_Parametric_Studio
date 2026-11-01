# CU-507 - History 7: Latent diffusion and Stable Diffusion (2022)

**Objective.** Say what the latent diffusion paper changed, count what that does to the cost of a layer, read the price the paper itself reports, and find the three parts of a Stable Diffusion checkpoint in ComfyUI's nodes. Taught by Professor Latent.

## The idea

By 2021 diffusion models gave state-of-the-art images, but "typically operate directly in pixel space", so that "optimization of powerful DMs often consumes hundreds of GPU days and inference is expensive". The introduction of Rombach, Blattmann, Lorenz, Esser and Ommer gives a figure: 150 to 1000 V100 days for the models of Dhariwal and Nichol, and about 5 days on one A100 for 50,000 samples.

Their paper, "High-Resolution Image Synthesis with Latent Diffusion Models", was posted on 20 December 2021 and appeared at CVPR 2022. The paper's Figure 2, with data from the DDPM paper of CU-506, makes the case: "Most bits of a digital image correspond to imperceptible details", yet a pixel-space network still has to be evaluated on all pixels. So the idea has two stages. First train an autoencoder, with the perceptual and adversarial losses described in CU-501, in a "perceptual compression stage which removes high-frequency details but still learns little semantic variation". Then run diffusion "in the latent space of powerful pretrained autoencoders", which, the abstract says, "allows for the first time to reach a near-optimal point between complexity reduction and detail preservation". Cross-attention layers in the U-Net let it take "general conditioning inputs such as text or bounding boxes".

Stable Diffusion "was made possible thanks to a collaboration with Stability AI and Runway and builds upon" this paper, according to the CompVis repository. Its version 1 "uses a downsampling-factor 8 autoencoder with an 860M UNet and CLIP ViT-L/14 text encoder", pretrained on 256×256 images and then finetuned on 512×512. Stability AI announced the public release of Stable Diffusion, "following our release for researchers", under a Creative ML OpenRAIL-M licence. Its page is dated Aug 22, and the Hugging Face post of the same day carries the date 22 August 2022.

## The maths

The autoencoder maps an image x of H×W×3 to a latent z = E(x) of h×w×c with downsampling factor f = H/h = W/w, and D(E(x)) is close to x. Diffusion is then trained on z, with the same noise-prediction loss as CU-202 (eq. 2 of the paper):

```
L_LDM = E_( E(x), ε~N(0,1), t ) [ ‖ ε − ε_θ( z_t, t ) ‖² ]
```

With a prompt y, a text encoder τ_θ turns it into tokens and the U-Net attends to them (eq. 3 and the attention of section 3.3):

```
L_LDM = E [ ‖ ε − ε_θ( z_t, t, τ_θ(y) ) ‖² ]          Attention(Q, K, V) = softmax( Q Kᵀ / √d ) · V,   Q from the image latent, K and V from τ_θ(y)
```

Sampling is the usual loop (CU-205), and then "samples from p(z) can be decoded to image space with a single pass through D".

A factor f cuts the number of positions by f², and the cost of a layer depends on positions. Convolution work grows in proportion to the number of positions. The attention matrix grows with its square.

## In ComfyUI

- **Three parts, one file.** `CheckpointLoaderSimple` in `nodes.py` returns `("MODEL", "CLIP", "VAE")`, with the tooltips "The model used for denoising latents", "The CLIP model used for encoding text prompts" and "The VAE model used for encoding and decoding images to and from latent space". That is the paper's U-Net, τ_θ and autoencoder.
- **The latent.** `EmptyLatentImage` creates `torch.zeros([batch_size, 4, height // 8, width // 8])` and tags it `downscale_ratio_spacial: 8`. A 1024×1024 request is a 4×128×128 tensor.
- **Cross-attention.** `BasicTransformerBlock` in `comfy/ldm/modules/attention.py` builds `attn2` as a `CrossAttention` whose keys and values come from `context`, the text conditioning.

Try the grid yourself. Ask for a size off the grid and see what you really get.

{{play:latent}}

The seven nodes you see every day are this paper's three parts plus a loop.

{{graph:sd15_txt2img}}

## What goes wrong

- **Your size gets quietly rounded down.** `EmptyLatentImage` divides by 8 with floor division. So 1000 stays 125 cells, but 1003 also becomes 125, and the picture is 1000 wide.
- **You use `EmptyLatentImage` with a 16-channel family.** It always makes 4 channels. SD 3.5 has its own node, `EmptySD3LatentImage`, as the `sd35_flow` graph shows.
- **You expect 64 times the speed.** The lab's 64 and 4096 are per layer. The paper's whole-model figure is 3 to 5 times.
- **You ask SD 1.x for 1024.** The attention layer costs 16 times more, as the lab shows, and version 1 was finetuned on 512 × 512. Start at the size the file was trained at and upscale after that (the `sd15_hires` graph).
- **You think a checkpoint's VAE is the only choice.** It is just the third output of the loader. `VAELoader` replaces it. Never mix families.
- **You assume a detail the decoder can't produce will appear.** Reach is limited by the autoencoder, however good the denoiser. Round-trip a picture first, with `h_vae_roundtrip`.

## Lab

PyTorch has a FLOP counter, which sums the cost of every operation that runs under it. It also works on tensors that have a shape and no data, so the lab can count a 3×3 convolution (64 to 64 channels) and an attention layer (320 dimensions, 8 heads) on a 512×512 pixel grid without ever computing one. A multiply-add counts as 2 FLOPs, and the lab asserts that the counter agrees with the textbook formulas 2·9·64·64·n and 4·n²·320.

```text
grid                     values    positions   conv GFLOPs   attention GFLOPs   attention matrix entries
pixels 512x512x3         786,432   262,144     19.33         87960.9            68,719,476,736
latent 64x64x4 (f = 8)   16,384    4,096       0.30          21.5               16,777,216
ratio                    48        64          64            4096               4096
```

The pixel image has 48 times more values than the latent and 64 times more positions. A convolution costs 64 times more on the pixel grid, and the attention matrix has 4096 times more entries and costs 4096 times more. That is 8×8 = 64 for positions, and 64² = 4096 for the square of it.

The same latent layers at other image sizes, as ComfyUI would shape them:

```text
image size    latent shape        positions   attention GFLOPs   relative to 512x512   conv GFLOPs
512x512       [1, 4, 64, 64]      4,096       21.5               1.00                  0.30  (1.00x)
768x768       [1, 4, 96, 96]      9,216       108.7              5.06                  0.68  (2.25x)
1024x1024     [1, 4, 128, 128]    16,384      343.6              16.00                 1.21  (4.00x)
2048x2048     [1, 4, 256, 256]    65,536      5497.6             256.00                4.83  (16.00x)
```

Doubling the side of the image quadruples the positions, quadruples the convolution cost and multiplies the attention cost by 16. At 2048×2048 the latent attention layer costs 256 times the 512×512 one. A latent grid is cheap but not free.

## What is contested

The lab is per layer, at equal widths, so it is arithmetic and not a speed-up. A whole network mixes many layers, and the latent diffusion paper measures the end-to-end difference itself, in its efficiency table (Table 6, on its inpainting setup): LDM-1, the pixel-space model, trains at 0.11 samples per second and LDM-4 at 0.32, which is 2.9 times as fast. Sampling at 256 goes from 0.26 to 0.97 samples per second (3.7 times) and at 512 from 0.07 to 0.34 (4.9 times). That is 3 to 5 times, not 64 and not 4096. The paper also reports "a significant FID gap of 38 between pixel-based diffusion (LDM-1) and LDM-8 after 2M training steps", and concludes that "LDM-4 and -8 offer the best conditions for achieving high-quality synthesis results".

The price is a lossy autoencoder. In the paper's autoencoder zoo, trained on OpenImages and evaluated on ImageNet validation images (Table 8), the f = 8 KL model with 4 channels, the shape of SD 1.x's, scores a PSNR of 24.19 and an rFID of 0.90, and the f = 4 model with 3 channels 27.53 and 0.27. Images that the decoder cannot produce are out of the diffusion model's reach.

Version 1 of Stable Diffusion is a configuration of that architecture, not the only possible one. The same paper shows other factors, and CU-201 lists the 16-channel latents that later families use.

## Sources

- [Rombach et al. 2021. High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)
- [CompVis. stable-diffusion repository README](https://github.com/CompVis/stable-diffusion)
- [Stability AI. Stable Diffusion Public Release](http://stability.ai/news-updates/stable-diffusion-public-release)
- [Hugging Face. Stable Diffusion with Diffusers](https://huggingface.co/blog/stable_diffusion)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
