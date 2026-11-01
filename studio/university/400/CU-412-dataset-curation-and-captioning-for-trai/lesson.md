# CU-412 - Dataset curation and captioning for training

**Objective.** Prepare a folder that core's training nodes read the way you intend, see how often each picture is really used, and write captions knowing what they do to a trigger word. Taught by Tinker Tune.

## The idea

A LoRA learns from pairs: a picture and its text. Nothing else teaches it. So there are two questions. Does the trainer see what you think it sees? And what will it learn from the words you wrote?

The first can be read in the source. The second is partly a matter of experience, and we'll say which parts are which.

{{graph:sd15_train_lora}}

## What the nodes do with your folder

`LoadImageTextDataSetFromFolder` lists a subfolder of input. Pictures are PNG, JPG, JPEG or WEBP. A caption is a `.txt` with the same name. Missing means an empty caption, with no error. A folder inside it whose name starts with a number and an underscore repeats its pictures.

```text
files                                     pictures in the list
['a.png', 'b.png']                        ['a.png', 'b.png']
['5_lamp/a.png', 'b.png']                 ['a.png', 'a.png', 'a.png', 'a.png', 'a.png', 'b.png']
['lamp/a.png', 'b.png']                   ['a.png', 'b.png']
```

So `5_lamp` means five copies. That's the kohya-style layout, and a comment in the source says so.

`MakeTrainingDataset` encodes each picture with the VAE and each caption with the text encoder, once, ahead of training. Nothing changes after that. So the same caption is used every time: there's no word shuffling and no caption dropout in this path. If you want those, you need a different trainer. And no cropping or resizing happens unless you add a node for it. Core has `ResizeImagesByLongerEdge`, `ResizeImagesByShorterEdge`, `CenterCropImages`, `RandomCropImages`, `ImageDeduplication`, and text nodes such as `AddTextPrefix` and `ReplaceText`, all in `comfy_extras/nodes_dataset.py`. We have read their names and not tested each.

Pictures of different shapes are allowed. `_prepare_latents_and_count` notices, and the trainer then handles the pictures of a step one at a time. `ResolutionBucket` is the other choice.

## How often each picture is seen

There's no such thing as an epoch here. Each step draws a fresh random subset. So the counts aren't even.

```text
sightings per picture, one seeded run. Each step draws afresh, so the counts are uneven
pictures   steps   batch   average   fewest   most
12         300     1       25.0      16       38
12         100     1       8.3       0        12
12         25      1       2.1       0        4
40         300     1       7.5       1        15
200        300     1       1.5       0        6
12         300     4       100.0     82       123
```

With 12 pictures and 300 steps, the average is 25, and this run's rarest picture gets 16 and its commonest 38. At 25 steps some pictures are never seen. At 200 pictures and 300 steps, about a quarter of them are never used at all:

```text
pictures never seen: 200 pictures at 300 steps 48   formula n (1 - 1/n)^steps = 44.5
```

That's the formula for picking with replacement, and it's a good check. So a big dataset needs more steps than you might think, and the average number of sightings is the number to work out first: steps × batch ÷ pictures.

{{play:coverage}}

## Long captions

Our Train page warns when a caption is over 65 words, because the encoder's window is about 75 tokens. The end of a long caption isn't dropped in ComfyUI, though. The tokenizer starts another group of 77, and all the groups are joined:

```text
tokens in the caption   groups sent to the encoder (SD 1.5)   shape of the conditioning
10                      1                                     1 x 77 x 768
75                      1                                     1 x 77 x 768
76                      2                                     1 x 154 x 768
150                     2                                     1 x 154 x 768
151                     3                                     1 x 231 x 768
```

We checked the groups on the real tokenizer, and the shape on the real `encode_token_weights` with a stub encoder. So it's not cut, but the words after the split are encoded apart from the words before, without seeing them, which changes how they read. Keep captions under the window where you can. And a word isn't always one token.

## What a caption does

Now the part you can't read in a source file. Here's a toy, which we made for this: a linear model learns what each caption word adds to a picture. The pictures hold a new thing (a lamp) that's in all of them, and 90% are on a beach and 10% in a forest. The model is asked for the smallest weights that explain the data. It's linear algebra, not a diffusion model, but it shows the mechanism.

```text
the toy. Prompt: the trigger alone. What the model then produces: lamp, beach, forest (1 = fully present)
captions                                  lamp    beach   forest
trigger only                              1.00    0.92    0.08
trigger + place words                     0.67    0.33    0.33
trigger + place words, asking for forest  1.00    -0.00   1.00
```

Row 1: captions hold only the trigger. Then the trigger has to carry everything the pictures have in common, so asking for the trigger brings you the lamp and most of a beach. Row 2: captions name the place too. Now the place words carry the place, and the bare trigger brings much less beach. The lamp falls too (0.67), because in this data each picture has exactly one place, so the place words and the trigger can trade weight. Row 3: with the place word you asked for, you get what you asked for, a forest and a lamp.

The rule that comes out of it: **what's in every picture and not in the caption gets attached to the trigger.**

```text
share of pictures on the beach, and how much beach the bare trigger brings when place is never captioned
beach share   beach from trigger alone
0.5           0.50
0.75          0.75
0.9           0.90
1.0           1.00
```

Practical advice, and this part is common practice and not something we measured:

- Name what should vary: background, lighting, pose, clothing. Don't name what the LoRA should learn: then the trigger takes it.
- Vary what shouldn't stick. If every picture has the same background and you don't want it, change it, or name it.
- Use a trigger word that means nothing to the model already. Check with the "off, trigger" picture from CU-282.
- Cull. Blurry or near-duplicate pictures use up sightings. `ImageDeduplication` can help with duplicates.
- Check the caption by reading it next to its picture. It's the only feedback you get before spending the run.

## What goes wrong

- **Empty captions, no warning.** A `.txt` with the wrong name counts as none. Our Train page's check blocks this. In a bare graph, read the `texts` output with a preview node first.
- **The same picture counted several times.** A `5_` folder repeats it, and so can a copy under another name.
- **The LoRA paints the same background everywhere.** It's in all your pictures and not in your captions. Vary it, or caption it.
- **The trigger does nothing.** Your captions may spell it differently, or your word may split into tokens that mean other things. Check with CU-282's four pictures.
- **Some pictures hardly matter.** Too many pictures for the steps. Work out the average sightings.
- **Out of memory on one large picture.** Pictures aren't resized for you here. Add a resize node.

## Lab

The lab copies the folder rule and the sampling rule, so its counts have the same pattern as a real run, though not the same numbers, because a real run's random state is different. The token table was checked against the real tokenizer in a side script. The caption section is a toy, and says so. This lesson's earlier draft had a frequency table of identical captions, which we removed: the core path has no feature that uses it, and its claims about synonyms had no evidence.

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_dataset.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_dataset.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_train.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_train.py)
- [ComfyUI v0.43.0, comfy/sd1_clip.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd1_clip.py)
