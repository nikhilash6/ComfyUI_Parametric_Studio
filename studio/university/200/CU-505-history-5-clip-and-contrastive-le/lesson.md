# CU-505 - History 5: CLIP and contrastive learning

**Objective.** Write CLIP's loss as a cross-entropy over a table of similarities, see what the temperature and the batch size do to it, test zero-shot use on pairs never seen in training, and find the two CLIP towers inside ComfyUI. Taught by Madame Attention.

## The idea

Before CLIP, vision systems were "trained to predict a fixed set of predetermined object categories". Radford et al. posted "Learning Transferable Visual Models From Natural Language Supervision" on 26 February 2021. They trained on 400 million (image, text) pairs collected from the internet to predict which caption goes with which image. Afterwards "natural language is used to reference learned visual concepts", so a new task is a list of captions and needs no new labels. The paper reports 76.2% zero-shot accuracy on ImageNet, matching the original ResNet-50 without using any of its 1.28 million training images, where the earlier Visual N-Grams reached 11.5%.

The loss was not new. The paper says the objective "was first introduced in the area of deep metric learning as the multi-class N-pair loss Sohn (2016), was popularized for contrastive representation learning by Oord et al. (2018) as the InfoNCE loss", and then adapted to text and images in medical imaging by Zhang et al. (2020). What CLIP added was the data, the scale and the zero-shot use.

## The maths

Two encoders turn a batch of N pairs into vectors, which are projected and normalised to unit length. The paper's Figure 3 is nearly all of it:

```
I_e = l2_normalize( I_f · W_i )          T_e = l2_normalize( T_f · W_t )
logits = I_e · T_e^T · exp(t)             an N×N table of scaled cosine similarities
loss = ( cross_entropy(logits, rows) + cross_entropy(logits, columns) ) / 2
```

Row i of the table is image i scored against all N captions, and the right answer is column i. Column j is caption j scored against all N images. The table has N right answers on its diagonal and N² − N wrong ones, and the loss asks each image to find its caption and each caption to find its image. Oord et al. define InfoNCE as the categorical cross-entropy of classifying the positive sample correctly among the negatives, which is this.

exp(t) is 1/τ and is learned. The paper starts τ at 0.07 and clips the logit scale at 100 "to prevent training instability", with a minibatch of 32,768. A model that gives every caption the same score has loss ln N. Because cosines lie in [−1, 1], τ also limits how confident the softmax can get. The best case puts each image on its caption and spreads the N captions as far apart as N unit vectors can be, every pair at cosine −1/(N−1), which gives a loss of ln(1 + (N−1) · exp(−(1 + 1/(N−1)) / τ)).

The text encoder is a transformer with masked self-attention. The top-layer activation at the end-of-text token is layer-normalised and linearly projected into the joint space.

## In ComfyUI

- **Both towers.** `CLIPTextModel_` in `comfy/clip_model.py` builds a causal mask with `triu_(1)`, the paper's masked self-attention, and takes the state at the end-of-text token as `pooled_output`. `CLIPTextModel` then applies `text_projection`, a Linear layer without bias. The image tower is `CLIPVisionModelProjection`, with a `visual_projection`.
- **What the denoiser receives depends on the family.** SD 1.x uses `SD1CheckpointClipModel`: `return_projected_pooled=False`, last layer, so the per-token states reach the U-Net through cross-attention and the contrastive embedding is not used. SDXL's `SDXLClipG` in `comfy/sdxl_clip.py` takes the penultimate layer and sets `return_projected_pooled=True`. `SDXLClipModel.encode_token_weights` concatenates the hidden states of CLIP-L and CLIP-G and returns CLIP-G's projected pooled embedding, and `encode_adm` in `comfy/model_base.py` joins that vector with embeddings of the image size, crop and target size. So SDXL is where CLIP's joint-space text embedding goes straight into the model.
- **Not here.** ComfyUI runs these towers. It never computes the contrastive loss above.

How low can the loss go? Set the batch and the temperature and read the very best case.

{{play:clipfloor}}

SDXL is where the joint-space embedding reaches the denoiser, and this is its plain graph. `encode_adm` is the part you can't see in it.

{{graph:sdxl_txt2img}}

## What goes wrong

- **You compare loss numbers across batch sizes.** A model with no idea scores ln N: 2.0794 at 8 and 4.6052 at 100. Loss alone can't say which run is better across those.
- **You copy a "clip skip" between families.** SD 1.x uses the last layer by default and `SDXLClipG` uses the penultimate one. What the model was trained on differs by family, and `CLIPSetLastLayer` moves you off it.
- **Your long prompt behaves oddly.** The SD 1.x text model takes 77 positions, and two of them are the start and end tokens. Longer text is split into chunks. The `chunks` lab in the conditioning track shows where.
- **You put a CLIP Vision file in a text loader.** The two towers come in separate files with separate loaders, `CLIPLoader` and `CLIPVisionLoader`.
- **You expect SD 1.x to use the contrastive embedding.** `return_projected_pooled=False` there, so only the per-token states go in. The pooled embedding matters in SDXL.
- **You use zero-shot numbers from our toy to judge a real model.** The toy is built so images split neatly into parts. Real pictures don't.

## Lab

The world has 12 shapes and 10 colours, so 120 concepts. An image is a 64-number vector made of a shape part, a colour part and noise. A caption names the shape and the colour. Twenty combinations are never used in training, so classifying them is zero-shot. First what a model with no idea scores:

```text
batch size N   loss of a model with no idea, ln N
8              2.0794
32             3.4657
100            4.6052
```

Then one run with the temperature learned as in CLIP, and a test: classify fresh images among all 120 captions.

```text
learned temperature: tau started at 0.0700 and ended at 0.0579; loss over the last 100 steps 0.1380
zero-shot, 1 correct caption among 120: images of the 100 combinations used in training 0.900, of the 20 never used 0.845, chance 0.008
```

The unused combinations come out at 0.845 against 0.900 for the used ones, and chance is 0.008. The encoders learned parts, not 120 labels. The toy is built so that an image is a sum of a shape part and a colour part, which is what lets two linear encoders do this. Real images are not that tidy.

Now the temperature, fixed at four values. Each row is the mean of 3 seeds, with a batch of 32.

```text
tau     best case at N = 32   loss after 600 steps   zero-shot on the 20 unused combinations
1.00    2.4884                2.7143                 0.760
0.30    0.6897                1.4099                 0.876
0.07    0.0000                0.1597                 0.862
0.01    0.0000                0.4510                 0.799
```

At τ = 1 even the best arrangement cannot get below 2.4884, barely a nat under the 3.4657 of no idea, and training ends at 2.7143, with the worst zero-shot score. At τ = 0.01 the loss ends at 0.4510 although it could reach 0, and the score is 0.799. Between 0.30 and 0.07 the two are within what 3 seeds can separate (0.876 and 0.862). The learned τ ended at 0.0579, just below that band. The lab does not show that 0.07 is special.

Last, the batch size, with the temperature learned and again 3 seeds. More captions in the batch means more wrong answers to rule out.

```text
batch N   chance loss ln N   loss after 600 steps   zero-shot on the 20 unused combinations
8         2.0794             0.1050                 0.741
32        3.4657             0.1346                 0.863
100       4.6052             0.2405                 0.902
```

The zero-shot score rises with N, 0.741 to 0.902, which is the direction the paper's 32,768 points in.

## What is contested

The softmax over the whole batch is a choice. Zhai et al. (SigLIP, 2023) use a sigmoid loss that "operates solely on image-text pairs and does not require a global view of the pairwise similarities for normalization", and find that "the benefits of growing batch size quickly diminish, with a more reasonable batch size of 32k being sufficient".

What the lab cannot say is how much of CLIP's zero-shot ability comes from the loss and how much from 400 million web pairs. The paper credits the loss to earlier work, which suggests the data and the scale mattered, but the lab does not measure it.

## Sources

- [Radford et al. 2021. Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020)
- [van den Oord, Li, Vinyals 2018. Representation Learning with Contrastive Predictive Coding](https://arxiv.org/abs/1807.03748)
- [Zhai et al. 2023. Sigmoid Loss for Language Image Pre-Training](https://arxiv.org/abs/2303.15343)
- [ComfyUI v0.43.0, comfy/clip_model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/clip_model.py)
- [ComfyUI v0.43.0, comfy/sd1_clip.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd1_clip.py)
- [ComfyUI v0.43.0, comfy/sdxl_clip.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sdxl_clip.py)
- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
