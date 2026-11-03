# SD3 and SD 3.5: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## SD 3.5 Large IP-Adapter: weak, not featured

SD 3.5 Large IP-Adapter (template ipa_sd35_large_instantx) runs InstantX's adapter through Slickytail's InstantX IP-Adapter SD3 nodes, which passed Pack Lab, with the SigLIP patch14 384 vision encoder. Settings: ApplyIPAdapterSD3 at weight 0.6, 1024x1024, 20 steps, euler with sgm_uniform, CFG 4. [code: studio/family_templates/index.json:3321-3352, studio/family_templates/ipa_sd35_large_instantx.json:67, studio/family_templates/ipa_sd35_large_instantx.json:98-99, studio/family_templates/ipa_sd35_large_instantx.json:111-114]

SD 3.5 Large IP-Adapter result was recorded as WEAK after one run on the test machine: the look of the mug reference carried over, its shape did not. The SD 1.5 and SDXL runs on the same mug were not marked weak. [claim: studio commit e162c772, 2026-11-02]

SD 3.5 Large IP-Adapter is kept off the Families page. The run stays in the model map with its WEAK label, and the recorder's NOT_SHOWN list stops a later recording from bringing it back. [code: scripts/record_family_renders.py:12-13] [claim: studio commit 8d3c5141, 2026-11-02]

SD 3.5 InstantX loader quirk: the pack lists the ipadapter folder through ComfyUI's folder paths but opens the file from the instance's own models/ipadapter folder. The SD3 family instance therefore links the family's adapter files there too, and drops stale links when it is regenerated. [code: psn/instances.py:20-21, psn/instances.py:160] [test: tests/test_instances.py]

## SD3 medium and training

SD3 medium has a template now: the SD 3.5 medium graph with sd3_medium.safetensors swapped in, the three shared encoders unchanged. One run: 30.4 s, peak 9.2 GiB, seed 11965092. [code: studio/family_templates/index.json:2702] [run: studio/family_status.json:9236-9250] [claim: studio commit 2792c70f, 2026-11-02]

SD 3.5 medium LoRA training has one recorded run on 2026-11-01: 512 px, rank 16, 300 steps, 0.27 s a step, 23.34 GiB in its own processes against a 78.19 GiB peak for the whole card. Its A/B was clear on a prompt close to the training set. [run: studio/train_measured.json:101-116]
