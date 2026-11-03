# CU-510 - History 10: From frames to space-time: the road to modern video models

**Objective.** Follow video models from image networks with time added on to networks that attend across space and time at once, test what a causal convolution really promises, and read the frame grid and token count that follow from it. Taught by Reel Rascal.

## The idea

An image model knows nothing about time. Give it a batch of 16 latents and you get 16 unrelated pictures, because nothing passes between them. Every video model is an answer to that. Over about three years the answer changed in three ways.

**Add time to an image network (2022 to 2023).** "Video Diffusion Models" (Ho et al., April 2022) calls its model "a natural extension of the standard image diffusion architecture". "Align your Latents" (Blattmann et al., April 2023) takes this further. It trains an image model first, then introduces "a temporal dimension" and fine-tunes on video, and it shows that those temporal layers can be added to Stable Diffusion itself. "Stable Video Diffusion" (November 2023) describes this as the method of the time: models "turned into generative video models by inserting temporal layers".

**Compress time as well (2024).** An image VAE encodes each frame on its own, so the latent has as many frames as the video. CogVideoX (August 2024) brought in "a 3D Variational Autoencoder (VAE) to compress videos along both spatial and temporal dimensions". Fewer latent frames means fewer tokens.

**Attend to everything at once (2024 onwards).** LTX-Video (December 2024) has a VAE of 32 × 32 × 8 pixels per token, and that compression "enables the transformer to efficiently perform full spatiotemporal self-attention". Wan (March 2025) is "built upon the mainstream diffusion transformer paradigm". Cosmos (January 2025) is a platform that includes video tokenizers.

## The mechanism

**Causal convolution.** A 3D convolution reads neighbours in time as well as in space. A centred one reads the next frame too. A causal one reads only the past. It's the same convolution with all the padding on one side.

```
centred, kernel 3:   output t reads t − 1, t, t + 1
causal, kernel 3:    output t reads t − 2, t − 1, t       pad 2 frames on the past side only
```

This is where people get it wrong. Causal describes the VAE. The sampler does not go frame by frame in most video models. A Wan KSampler updates every latent frame at every step, so the model sees the future frames' tokens all the time. What causal buys is this: a frame's code doesn't depend on later frames, so one frame encodes as an image, and a long video can be processed in pieces with a cache. A model that does generate frame by frame is something else, and CU-503 covers it.

**The grid.** With causal padding and stride 2 in time, the first frame keeps its own latent. After that, each latent frame covers the next group. Two such layers give 4k + 1:

```
latent frames = ((frames − 1) // 4) + 1            Wan and HunyuanVideo families
latent frames = ((frames − 1) // 8) + 1            LTX
```

**Tokens.** Video pays for attention twice. With T latent frames of H × W tokens, a joint model has T·H·W tokens and the square of that many pairs. A factorised model does spatial attention inside each frame and temporal attention across frames at each position, for T·(HW)² + HW·T² pairs. Far cheaper, but information about another place at another time then takes two layers to arrive.

## In ComfyUI

- **Temporal layers added on.** `SVD_img2vid` in `comfy/supported_models.py` is the 2023 design. `SpatialVideoTransformer` in `comfy/ldm/modules/attention.py` keeps its image `transformer_blocks`, adds a `time_stack`, and walks through the pairs together. `VideoResBlock` in `openaimodel.py` does the same for convolution blocks.
- **Causal VAEs.** `CausalConv3d` exists five times, because each family has its own. In `comfy/ldm/wan/vae.py` it pads with zeros. In `comfy/ldm/cosmos/cosmos_tokenizer/layers3d.py` and `comfy/ldm/lightricks/vae/causal_conv3d.py` it repeats the first frame. The LTX one also takes a `causal` flag that can turn this off. `comfy/ldm/cogvideo/vae.py` chooses by `pad_mode`.
- **Joint attention.** `WanModel` in `comfy/ldm/wan/model.py` has `patch_size=(1, 2, 2)`, then flattens everything into one sequence of tokens. `CogVideoXTransformer3DModel` positions its tokens with `get_3d_sincos_pos_embed`. Cosmos uses `VideoRopePosition3DEmb`.
- **The grid in code.** `EmptyHunyuanLatentVideo` makes `((length - 1) // 4) + 1` latent frames. `EmptyLTXVLatentVideo` makes `((length - 1) // 8) + 1` at height // 32. `VAE` in `comfy/sd.py` holds the inverse, such as `a * 4 - 3`.
- **Decoding long clips.** `VAEDecodeTiled` has `temporal_size` and `temporal_overlap`. `AutoencoderKLCogVideoX` has `_decode_rolling`, which runs the expensive high-resolution layers in chunks of 4 frames.

{{video:families/svd_0.mp4|The 2023 design, run here: SVD XT 1.1 through core nodes, one still of a rainy street to a 25-frame clip. The woman in the yellow raincoat takes a few steps and the camera drifts. A web copy at 640 x 360, 6 fps. Peak 27.8 GiB. One seed.|families/svd_0.webp}}

Try the grid. Ask for a frame count and see what you get back.

{{play:frames}}

Two graphs from the joint-attention era.

{{graph:wf_wan22_t2v}}

{{graph:wf_ltx25_t2v}}

## What goes wrong

- **You ask for 48 frames and get 45.** Floor division, and then the inverse: 48 becomes 12 latent frames, which decode to 45. The lab prints this. Ask for a count on the grid, such as 49 or 81.
- **You make a video by batching an image model.** It has no layer that connects the frames, so you get separate pictures. Flicker here is no bug in your settings.
- **You think causal means the model can't see later frames.** That is only the VAE. Most samplers denoise all latent frames at once. So you can't stop a Wan run midway and keep the "finished" early frames.
- **Sampling fits and decoding runs out of memory.** The decoder has to produce every pixel of every frame. Use `VAEDecodeTiled`, and lower `temporal_size` if needed.
- **A longer clip costs much more than you expected.** Joint pairs grow with the square of the tokens: 3.81 times for about twice the frames, in the lab. Count the tokens before you queue.
- **Long clips break at the seams.** Chunking with too little overlap shows. The `longchunks` lab plans this, and CU-215 has the frame rules.

## Lab

First, a real convolution with random weights, tested by differentiating output frame 4 with respect to every input frame, and then by changing the future.

```text
output frame 4 reads input frames
centred convolution       [3, 4, 5]
causal, zero padding       [2, 3, 4]
causal, first frame copied [2, 3, 4]
change frames 6 to 8: outputs 0 to 5 move by 0.0 with causal padding, 2.38 with centred
```

The causal forms read frames 2, 3 and 4 and nothing later, and changing frames 6 to 8 moves earlier outputs by exactly 0.0. Note the third line. Repeating the first frame instead of padding with zeros keeps the same reach. They differ only in what they feed the very first frames.

Next, stride, with real strided convolutions run for shape. This is where 4k + 1 comes from.

```text
frames in   latent frames, two stride-2 layers   ((T - 1) // 4) + 1   decoded back, 4 L - 3
1           1                                    1                    1
5           2                                    2                    5
17          5                                    5                    17
48          12                                   12                   45
49          13                                   13                   49
81          21                                   21                   81
82          21                                   21                   81
```

The real convolutions give the same numbers as the formula in the source, for every row. Frames 81 and 82 give the same result, so the 82nd is cut. Then tokens, for sizes we worked out from the formulas above and the patch sizes in the source.

```text
clip                     latent grid after patching   tokens    joint pairs     spatial + temporal pairs   joint / factorised
Wan 832x480, 81 frames   21 x 30 x 52                  32,760    1.073e+09       5.179e+07                  20.7
Wan 832x480, 161 frames  41 x 30 x 52                  63,960    4.091e+09       1.024e+08                  40.0
LTX 768x512, 121 frames  16 x 16 x 24                  6,144     3.775e+07       2.458e+06                  15.4
double the frames, joint pairs grow 3.81 times; the same clip at twice the side grows them 16 times
```

On the grid of `WanImageToVideo`, a clip of 81 frames at 832 × 480 is 32,760 tokens. The Wan 2.2 5B graph above uses a coarser grid, and the frames lab shows it. Joint attention is 20.7 times the pairs of factorised, and 40.0 times at 161 frames. So factorising saves more the longer the clip. Those are counts of pairs in one attention layer, not seconds. Real models slice the attention, use faster kernels, and differ in other layers.

## What is contested

Whether joint attention gives better video than factorised attention at equal cost is not something this lab can say. The LTX paper calls full spatiotemporal attention "essential" for temporal consistency. That is its own claim, and we did not test it. Most of these abstracts claim a lead. Video Diffusion Models, Align your Latents and CogVideoX say state-of-the-art, LTX-Video says it outperforms models of similar scale, and Wan says it beats open and commercial ones. Stable Video Diffusion says its text-to-video model is competitive with closed-source ones, and the Cosmos abstract makes no such claim. We did not re-run any.

We also can't say how much of the improvement between 2023 and 2025 came from architecture. The Stable Video Diffusion abstract puts weight on dataset curation, and the Wan abstract credits data and scale as well.

## Sources

- [Ho et al. 2022. Video Diffusion Models](https://arxiv.org/abs/2204.03458)
- [Blattmann et al. 2023. Align your Latents: High-Resolution Video Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2304.08818)
- [Blattmann et al. 2023. Stable Video Diffusion: Scaling Latent Video Diffusion Models to Large Datasets](https://arxiv.org/abs/2311.15127)
- [Yang et al. 2024. CogVideoX: Text-to-Video Diffusion Models with An Expert Transformer](https://arxiv.org/abs/2408.06072)
- [HaCohen et al. 2024. LTX-Video: Realtime Video Latent Diffusion](https://arxiv.org/abs/2501.00103)
- [NVIDIA 2025. Cosmos World Foundation Model Platform for Physical AI](https://arxiv.org/abs/2501.03575)
- [Team Wan 2025. Wan: Open and Advanced Large-Scale Video Generative Models](https://arxiv.org/abs/2503.20314)
- [ComfyUI v0.43.0, comfy/ldm/wan/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/wan/vae.py)
- [ComfyUI v0.43.0, comfy/ldm/wan/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/wan/model.py)
- [ComfyUI v0.43.0, comfy/ldm/lightricks/vae/causal_conv3d.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/vae/causal_conv3d.py)
- [ComfyUI v0.43.0, comfy/ldm/cosmos/cosmos_tokenizer/layers3d.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/cosmos/cosmos_tokenizer/layers3d.py)
- [ComfyUI v0.43.0, comfy/ldm/cosmos/position_embedding.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/cosmos/position_embedding.py)
- [ComfyUI v0.43.0, comfy/ldm/cogvideo/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/cogvideo/vae.py)
- [ComfyUI v0.43.0, comfy/ldm/cogvideo/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/cogvideo/model.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
- [ComfyUI v0.43.0, comfy/supported_models.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_hunyuan.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_hunyuan.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_lt.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lt.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
