# CU-413 - Prompt adherence evaluation

**Objective.** Measure whether a picture contains what the prompt asked for, using a similarity score or a checklist, and say what each one misses. Taught by Tinker Tune.

## The idea

"Did it listen?" sounds like one question, but it's many. A prompt lists objects, colours, positions and a style. The usual ways to measure that are:

- **An embedding score.** Run the image and the text through a model trained so that matching pairs end up close, and take a similarity. CLIP (Radford et al. 2021) is the usual choice. CLIPScore (Hessel et al. 2021) applies it to captions.
- **A checklist.** Turn the prompt into questions, and answer each by hand or by a question-answering model. TIFA (Hu et al. 2023) automates this.

You can't measure adherence by comparing a prompt's conditioning with a latent. They live in different spaces. A similarity between them means nothing.

## The mechanism

**Cosine similarity** between vectors u and v from the same model:

```
cos(u, v) = (u · v) ÷ (‖u‖ ‖v‖)            ranges from −1 to 1
CLIPScore = 2.5 × max( cos(image, text), 0 )
```

Hessel et al. chose 2.5 to stretch the range, and report that they saw cosines between about 0 and 0.4 in practice, never negative. So a score of 0.8 from CLIP isn't "80% adherence". It's only useful relative to other scores from the same model, on similar inputs.

**The rule for reading it.** Make comparisons, and don't read an absolute. Compare the true prompt with wrong ones and see its rank, or compare two images on one prompt.

**A checklist**, by hand, needs no model. Split the prompt into items and answer yes or no per item.

{{play:checklist}}

## In ComfyUI

Core has no adherence node. In core, `CLIPTextEncode` makes the model's conditioning, and `CLIPVisionEncode` gives image embeddings for models that use them. These aren't a ready score: a score needs a model's matching text and vision projections, and a formula. To measure, save the images and run a script, or use a pack you've read. Don't assume any pack's number means the same as another's.

To gather a test set, change only the seed, across a fixed prompt list, with a script (CU-460).

{{graph:sd15_txt2img}}

For the real pictures in the play, see the [Sampling Lab](#sampling/renders). Each one is one seed of one prompt, so it's only an example.

## What goes wrong

- **Reading a score as a percentage.** CLIP cosines don't span 0 to 1. Compare with your other scores only.
- **A short prompt scores well.** The lab's "red car" beats the full caption on a picture holding more. A prompt with fewer items is easier to satisfy, and a higher score doesn't mean a better image.
- **Extra things go unnoticed.** A dog nobody asked for barely moves the score in the lab. Add your own checks for what mustn't be there.
- **Wrong attachment.** "Red car, blue ball" and "blue car, red ball" look the same to our toy embedding. Real encoders see more than this one, which adds word vectors. Binding is widely reported as a weak spot of real encoders too, though we did not test that here. So test with a checklist item that names the pairing.
- **Mixed encoders.** A CLIP text vector and an image vector from another model share no directions. The lab shows a cosine near 0 for the same concept.
- **One seed, one rater.** The hand-marked table in the lab is one reader's view of one seed. That's fine as a demonstration, and not enough to rank samplers (CU-470).

## Lab

No CLIP model runs here. The vectors are made up: a caption is a sum of random concept vectors, and an image holds some concepts plus noise. Since these vectors are built to match, their cosines run higher than real CLIP's, so the "scores" pass 1. Ignore the scale, and read the order.

```text
image holds: red, car, beach
caption               cosine   score (w = 2.5)
red car on a beach    0.816    2.040
red car               0.837    2.092
red car in a city     0.689    1.723
blue ball at night    -0.001   0.000
```

The shorter caption scores best here, because it asks for less. Two more limits:

```text
image with one more thing, a dog, against the old caption: 0.805, so extra things only lower it a little
'red car, blue ball' against 'blue car, red ball': cosine 1.000
same caption, vector from a different encoder (a random rotation here): cosine 0.054
```

The useful reading is a rank.

```text
rank of the true caption among 24 captions: 1
```

Now the checklist on two real renders from the Sampling Lab. We looked at both and marked them by hand. Euler shows a large brass dial on a wooden table in front of a window, and no charts. Euler ancestral shows part of a brass instrument resting on paper charts, with no window in view.

```text
item                    euler  euler ancestral   (one seed, marked by one reader)
brass astrolabe         1      1
oak table               1      0
stack of sea charts     0      1
window light            1      0
shallow depth of field  0      1
score                   0.60   0.60
the same total hides different failures. each row tells you what to fix
```

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-euler_ancestral.jpg|euler|euler ancestral|One prompt, one seed, two samplers.}}

## Sources

- [Radford et al. 2021. Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020)
- [Hessel et al. 2021. CLIPScore: A Reference-free Evaluation Metric for Image Captioning](https://arxiv.org/abs/2104.08718)
- [Hu et al. 2023. TIFA: Accurate and Interpretable Text-to-Image Faithfulness Evaluation with Question Answering](https://arxiv.org/abs/2303.11897)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
