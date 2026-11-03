# Z-Image: settings and the negative prompt (checked 2026-11-03)

What the Z-Image authors say about settings and negatives, in plain words. Where this file and older notes disagree, this file wins. The same facts are in the studio's prompt kits. [code: studio/prompt_kits.json]

The authors give CFG 3.0 to 5.0, 28 to 50 steps, CFG normalisation off for general style and on for realism, and a total area from 512x512 to 2048x2048. Their demo defaults to 30 steps and CFG 4. The earlier studio ran 50 steps, CFG 4, res_multistep with the simple scheduler and shift 3, inside those ranges. [claim: Z-Image README, github.com/Tongyi-MAI/Z-Image] [claim: Z-Image demo, huggingface.co/spaces/Tongyi-MAI/Z-Image] [claim: earlier studio notes]

Because Z-Image runs above CFG 1, a negative prompt does work. The authors recommend one but publish no wording: every official example sends an empty negative, and their pages disagree on how much it matters ("strongly recommended" in the README, "optional, but would be powerful" on the model card). [claim: Z-Image README] [claim: Z-Image model card, huggingface.co/Tongyi-MAI/Z-Image]

The studio's kit carries its own negative, written by us: blurry, low resolution, jpeg artifacts, deformed anatomy, extra fingers, distorted hands, waxy plastic skin, oversaturated, garbled lettering, watermark. It starts switched off, because no A/B has judged it yet. [code: studio/prompt_kits.json] [inference]
