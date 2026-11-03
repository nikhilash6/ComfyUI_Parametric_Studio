# SD 1.5: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## IP-Adapter now runs on SD 1.5

SD 1.5 IP-Adapter has six studio templates on DreamShaper 8: ip-adapter_sd15, ip-adapter_sd15_light, ip-adapter-plus_sd15, ip-adapter_sd15_vit-G, ip-adapter-full-face_sd15 and ip-adapter-plus-face_sd15. They run through pamparamm's IPAdapter_plus, which passed Pack Lab, loaded on the SD 1.5 family instance. The vit-G adapter takes clip_vision_g; the others take CLIP-ViT-H. [code: studio/family_templates/index.json, psn/instances.py:22]

SD 1.5 IP-Adapter settings in every template: IPAdapterAdvanced at weight 0.8, linear, embeds scaling V only, 512x512, 25 steps, dpmpp_2m with karras, CFG 6. [code: studio/family_templates/ipa_ip_adapter_plus_sd15.json:30, studio/family_templates/ipa_ip_adapter_plus_sd15.json:48, studio/family_templates/ipa_ip_adapter_plus_sd15.json:82-83, studio/family_templates/ipa_ip_adapter_plus_sd15.json:107-110]

SD 1.5 IP-Adapter runs on the test machine, one each: plus 25.3 s at 4.4 GiB, plain 20.3 s at 3.2 GiB, light 25.3 s at 4.4 GiB, vit-G 25.3 s at 6.6 GiB, full-face 25.3 s at 4.0 GiB, plus-face 30.4 s at 4.4 GiB. A mug reference steered colour and finish on a prompt that names neither; the face references used an invented person. Each was looked at. [run: studio/family_status.json] [claim: studio commit e162c772, 2026-11-02]

SD 1.5 face references come with a rule in the template text: use only invented people or yourself, never a real person without consent. [code: studio/family_templates/index.json]

SD 1.5 IP-Adapter correction: the older PITFALLS note says IP-Adapter cannot be used here because IPAdapterApply and the CLIP Vision file are missing. That is out of date. The family instance now loads IPAdapter_plus, and its templates use IPAdapterModelLoader, CLIPVisionLoader and IPAdapterAdvanced, not IPAdapterApply. [docs: studio/crew_notes/model_families/22-SD-1.5/dossier/PITFALLS.md:20-21, studio/crew_notes/model_families/22-SD-1.5/dossier/PITFALLS.md:67-69] [code: studio/family_templates/ipa_ip_adapter_plus_sd15.json:9, studio/family_templates/ipa_ip_adapter_plus_sd15.json:15, studio/family_templates/ipa_ip_adapter_plus_sd15.json:30]

## File variants

SD 1.5 file variants each have one recorded run, to prove a file loads and steers: the original v1-5 pruned EMA checkpoint, DreamShaper 8 with three swapped text encoders (fofr's CLIP-L copy, the SD 1.1 encoder, the SD 1.4 encoder) and the diffusers-layout UNet. Times 15.1 to 20.2 s. Recorded peaks are 0.5 GiB for four of them and 3.0 GiB for the SD 1.1 encoder; those small peaks are as recorded and were not checked further. [code: studio/family_templates/index.json] [run: studio/family_status.json] [claim: studio commit 2792c70f, 2026-11-02]

## Training and relighting

SD 1.5 LoRA training has one recorded run on 2026-11-01: 512 px, rank 16, 300 steps, 0.17 s a step, a card peak of 18.38 GiB and 7.57 GiB in its own processes. Its A/B was strong on a prompt close to the training set. [run: studio/train_measured.json:152-167]

IC-Light, recorded as its own family, relights a foreground cut-out on SD 1.5 (DreamShaper 8) through kijai's IC-Light nodes, following a light map and words. One run: 20.1 s, peak 5.0 GiB, seed 328850001. Its code is Apache-2.0; the weights' own card names no licence. [code: studio/family_templates/index.json, psn/instances.py:22] [run: studio/family_status.json]
