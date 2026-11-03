# LoRAs: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

LoRA recipes: the studio keeps tuned settings for 161 third-party LoRAs, read from each LoRA's own notes by the earlier studio: 75 for MiniMax H3, 48 for Wan 2.2, 12 for Qwen-Image, 9 for LTX, 6 for Wan 2.1 and a few for FLUX.1, FLUX.2, Krea 2, MOSS, Anima and Z-Image. The weights are not in the repository; each row records its licence and its proof level, and a recipe row alone was never rendered. [run: studio/lora_recipes.json] [code: studio/loras.py]

Wan 2.2 14B LoRAs in the official templates: fourteen Wan 2.2 14B LoRAs run inside ComfyUI's own Wan 2.2 image-to-video and text-to-video templates. A speed LoRA takes the place of the template's own 4-step LoRA on the same expert. The Stable Video Infinity LoRAs, made for long chained clips, go in right after it and run one clip on top of the template's 4-step LoRAs. A recipe step can insert one LoRA after a named model node. As recorded, none of the fourteen has been rendered through its recipe: each row still waits on a download and says its LoRA and base files are not on disk; seven were load-tested on the earlier studio, output not judged. [run: studio/lora_recipes.json] [code: studio/recipes.py:486]

LoRA reference cards in family templates: eight LoRAs whose family template already loads them became recipes: FLUX.1 depth (the template makes the depth map itself), Qwen-Image union control (it draws Canny edges itself), MOSS-Image edit, the Wan 2.2 text-to-video and image-to-video speed pairs, and Wan Alpha. Each template was checked against the live node list so that the LoRA node reaches the output. Renders were to follow review; as recorded, these rows still carry the reference-card note and no recipe render. [claim: commit de244ef1, 2026-11-02] [run: studio/lora_recipes.json]

H3 LoRAs that came out garbled: five H3 LoRA recipes got new settings to try again, each with a note saying why. One ran 3 steps though its file name says 8 and came out as noise, so it runs 8. Two smeared on res_multistep and now run Euler at 25 steps like the other H3 LoRAs. Two photoreal image LoRAs laid a dotted mesh over faces on the beta scheduler (their notes ask for beta57, which the studio does not install) and now run on simple. [run: studio/lora_recipes.json]

Music 3 turbo LoRA: a variant of ComfyUI's Music 3 graph puts an 8-step turbo LoRA on the DiT (strength 1.0, 8 steps, CFG 1.6, from its card). One render: 61.0 s at 15.9 GiB for 60 s of music, checked by loudness and spectrum, not by ear. [code: studio/family_templates/index.json] [run: studio/family_status.json] [claim: commit 2099f6d7, 2026-11-02]

DubIt IC-LoRA: Lightricks' LTX-2.3 DubIt IC-LoRA (2.47 GB, gated) runs on LTX-2.5 to redraw the mouth and speak a new line in the speaker's voice. A file under 1 GB is treated as a cache stub. In the proof it said the Spanish line at WER 0 (53.2 s, 43.1 GiB), but its voice likeness to the speaker was only 0.63. It needs a ComfyUI with an fp32 VAE. [code: studio/feature_dub.py:18, studio/feature_dub.py:42-47] [run: studio/dub_proof.json:148-170]

LTX Finish IC-LoRAs: six LTX-2.5 IC-LoRAs (restore, deblur, decompression, colorization, pixel-spatial x2 upscaler, SDR to HDR) run on LTX-2.5 22B distilled int8, under the LTX-2.x Community License (free under US$10M annual revenue). Each was measured on a fresh clip damaged on purpose. [run: studio/finish_proof.json]

Other LTX-2.3 LoRAs on LTX-2.5: the style-transition LoRA (Shot Board transition, 16.5 s, 37.8 GiB) and the Motion-Track-Control IC-LoRA (Camera Paths, 31.8 s, 39.2 GiB) both ran on LTX-2.5 and are recorded as working. The transition proof did not test a run without the LoRA. [run: studio/web/showcase/transition_proof.json, studio/camera_proof.json]

Wan 2.1 LoRAs on Wan 2.2: the earlier studio's key check found Wan 2.1 speed LoRAs left about 290 attention keys unmapped on a 2.2 expert, so they only half apply. Use them only in the stack their author tested. This was not re-checked here. [docs: studio/crew_notes/model_families/30-Wan-2.2/dossier/NOW.md] [claim: earlier studio key-binding check, 2026-10-16]

LoRA Showcase empty state: with no LoRA of the person's own yet, the page says so plainly and shows what a showcase holds using the Train page's example run (the A/B proof, the run's figures and a share bundle), labelled as the studio's example, not theirs. [code: studio/web/lorashow.js:54-61]
