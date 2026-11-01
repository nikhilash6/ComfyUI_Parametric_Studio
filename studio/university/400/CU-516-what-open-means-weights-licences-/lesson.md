# CU-516 - History 16: What open means: weights, licences and the ecosystem

**Objective.** Separate four things people mean by open, and read what each lets you do with what you downloaded. Taught by Captain Graph.

## Four questions under one word

When someone calls a model open, they might mean any of these, and they often don't say which.

1. **Do you have the weights?** Then you can run it yourself. No weights, no running it at home.
2. **Do you have the code?** Then you can read how it works, and change it.
3. **Do you know the data?** Then you could, in principle, build something equivalent.
4. **What does the licence let you do?** Having a thing isn't the same as permission.

The first three are about what you were given, and the fourth is about what you're allowed. A model can have downloadable weights and a licence with a list of banned uses. A project can have a permissive code licence and weights you can't get.

The Open Source Initiative has a written definition for AI systems. It asks for the freedoms to use, study, modify and share, and it asks that weights, code and enough information about the data be available. It's a useful test, and most things people call open weights don't claim to meet it. So "open weights" is the honest phrase when weights are what you have.

## How this reaches your graph

ComfyUI is under the GPL version 3. Your graph can pull in things under other terms at the same moment:

{{graph:sd15_lora}}

In that one small graph there are three separate sets of terms: ComfyUI's, the checkpoint's and the LoRA's. Add a node pack and that's a fourth. Each comes from a different person and travels on its own terms. CU-383 goes through what the common licences say.

A second meaning of open matters here: it doesn't mean safe. `SECURITY.md` in ComfyUI's repository says custom nodes "are arbitrary Python code and are trusted as much as any other software the user chooses to install". Being able to read code is what lets you check it. It doesn't mean anyone has. CU-380 covers how.

## A short timeline, from the texts

| date | what | the idea |
|---|---|---|
| 29 June 2007 | GNU GPL 3 | source must come with copies you pass on |
| 19 November 2007 | GNU AGPL 3 | same, plus users over a network |
| August 22, 2022 | CreativeML Open RAIL-M | free to use, with banned uses you must pass on |

That last one was new for this field: permission is broad, and some uses are written out of it. Whether it counts as open in the older sense is exactly the kind of argument this lesson is about, and we won't settle it. Read the terms that apply to what you have.

{{play:licence}}

## What goes wrong

- **"It's on the internet, so it's free to use."** A public download isn't a licence. See CU-383 for what no licence means.
- **Checking only the main model.** Text encoders, VAEs, LoRAs and packs have their own terms. Check each part you ship.
- **Assuming open means reproducible.** Without data information you can't rebuild it, even with weights and code.
- **Assuming a licence names your use.** Read it. Commercial use may be allowed, restricted or banned, and only the text can tell you.
- **Treating open code as reviewed code.** Nobody may have read it. Read it yourself or sandbox it.

## Lab

The lab sorts what you can do by what you have. The logic is simple, and that's the point: each ability needs specific parts.

```text
                                    run it on your o  read how it work  fine-tune it, a   rebuild somethin
closed API                          no                no                no                no              
weights only, in a binary runner    yes               no                no                no              
weights and code                    yes               yes               yes               no              
weights, code and data details      yes               yes               yes               yes             
```

Then the licences, from the texts we fetched:

```text
and separately, what the licence lets you do. Dates and rules from the texts we fetched
  GNU GPL 3                29 June 2007       source duty when you convey; remote use alone is not conveying
  GNU AGPL 3               19 November 2007   adds an offer of source to remote users of a modified version
  CreativeML Open RAIL-M   August 22, 2022    free use, with a list of banned uses that you must pass on
  MIT                      no version date    keep the notice
```

And one graph's parts:

```text
one graph can carry several of these at once
  ComfyUI itself             GPL 3
  a checkpoint               CreativeML Open RAIL-M
  a LoRA from someone else   its own terms: read them
  a node pack                its own LICENSE file
  your pictures              the Open RAIL-M says the licensor claims no rights in the output, with limits on use
```

## Sources

- [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.txt)
- [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.txt)
- [CreativeML Open RAIL-M, text from CompVis](https://huggingface.co/spaces/CompVis/stable-diffusion-license/raw/main/license.txt)
- [MIT licence text, SPDX](https://raw.githubusercontent.com/spdx/license-list-data/main/text/MIT.txt)
- [The Open Source AI Definition](https://opensource.org/ai/open-source-ai-definition)
- [ComfyUI v0.43.0, SECURITY.md](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/SECURITY.md)
- [ComfyUI v0.43.0, LICENSE](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/LICENSE)
