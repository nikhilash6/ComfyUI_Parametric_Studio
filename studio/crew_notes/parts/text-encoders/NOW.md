# Text encoders: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

Text encoders on the Model Anatomy page: every model file in the studio's list, text encoders included, is opened from its safetensors or GGUF header with no GPU and no weights loaded, showing parameters, blocks, number formats and the attention and MLP split. The cached records cover 1117 files. [code: studio/feature_anatomy.py:10] [run: studio/anatomy/models.json.gz]

LTX-2.5 Gemma encoder: LTX-2.5 reads prompts with an int8 Gemma 4 12B encoder (15.4 GB), beside the 21.5 GB int8 transformer. On a roomy 96 GB card ComfyUI keeps both resident, so a Shot Board VFX job peaks at about 38.5 GiB at every size. [code: studio/feature_dub.py:19] [run: studio/web/showcase/vfx_same_clip.json:121]

LTX-2.5 Gemma encoder sets the low-memory peak: under an emulated 14 GiB budget the first matte job peaked at 19.6 GiB while the Gemma encoder loaded (73.5 s); a second job reused the cached prompt encoding and peaked at 10.4 GiB (56.3 s). Every new prompt needs Gemma, so a 16 GB card is not claimed. This was emulated on the 96 GB card, not run on a smaller one. [run: studio/web/showcase/vfx_same_clip.json:188-215]

Wan 2.2 umt5 encoder: the Wan 2.2 14B text-to-video template on Kijai's fp8 files reads prompts with umt5_xxl_fp8_e4m3fn_scaled. [code: studio/family_templates/wan22_14b_t2v_kj.json:5]

SD 3.5 Large triple encoder: the InstantX IP-Adapter template for SD 3.5 Large loads CLIP-L, CLIP-G and an fp8 T5-XXL. [code: studio/family_templates/ipa_sd35_large_instantx.json:11-13]

HY-Motion Qwen3-8B encoder: HY-Motion 1.0 turns a sentence into a body motion, with Qwen3-8B and CLIP-L reading the words. The Qwen3-8B shards were joined into one bf16 file for the template. One render on the family's own instance: 59.6 s at a 4.9 GiB peak with the text encoder on the CPU. The walk, stop and raised arms matched the words, but it never waved, and two runs with the same seed gave different walks. [code: studio/family_templates/index.json, studio/family_templates/hymotion_t2m_preview.json:12-13] [run: studio/family_status.json] [claim: commit 3da7b6c7, 2026-11-02]

Kolors ChatGLM3 encoder: Kolors reads prompts with ChatGLM3-6B, loaded through kijai's Kolors wrapper. One render on its own instance: 24.8 s, 12.7 GiB, a convincing still life with labelled faults (peaches without fuzz, colour a little hot). [code: studio/family_templates/kolors_t2i.json:10] [run: studio/family_status.json]

Lumina 2 with plain Gemma: a studio template runs Lumina 2 with the plain Gemma 2 2B (fp16) encoder file already on disk; one render, 35.4 s. [code: studio/family_templates/lumina2_gemma2_fp16_t2i.json:86] [run: studio/family_status.json]

Qwen-Image 2.1 turbo nvfp4 encoder: a studio template runs Qwen-Image 2.1 turbo with an nvfp4 Qwen3-VL 8B text encoder; one render, 25.2 s on a Blackwell card. Another NVFP4 model in the studio's notes is marked Blackwell only; whether this encoder runs on older cards was not checked. [code: studio/family_templates/qwen21_turbo_nvfp4te_t2i.json:23] [run: studio/family_status.json, studio/dub_proof.json:3] [docs: studio/processes/video-lightwan.md:52]

SD 1.5 text encoder variants: three studio templates run the same SD 1.5 checkpoint with a different CLIP-L file each (the SD 1.1 encoder, the SD 1.4 encoder, and a community copy of CLIP-L). Each rendered once, 15.1 to 20.2 s. [code: studio/family_templates/sd15_clip_sd11_t2i.json:11, studio/family_templates/sd15_clip_sd14_t2i.json:11, studio/family_templates/sd15_clip_fofr_t2i.json:11] [run: studio/family_status.json]

Iris-3B encoder: Iris-3B rendered on its own instance with the Qwen3-VL 4B encoder (50.1 s, 8.5 GiB peak). [run: studio/family_status.json]
