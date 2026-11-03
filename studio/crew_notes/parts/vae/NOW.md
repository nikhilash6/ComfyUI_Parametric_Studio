# VAEs: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

LTX-2.5 video VAE, conv against diffusion decoder: the same four Shot Board jobs (same seed and settings, so identical sampling) were decoded with the convolutional video VAE the studio ships (ltx-2.5-video-vae-conv-bf16) and with Lightricks' diffusion decoder (ltx-2.5-video-vae-bf16, 1.47 GB), at 960x544, 121 frames, one run each on the test machine. [run: studio/web/showcase/vfx_same_clip.json:216-220]

LTX-2.5 video VAE results: the conv decoder was sharper on every job (water 987 against 533 mean Laplacian variance, night 479 against 293, clean plate 573 against 354). The diffusion decoder flickered a little less on the still wall, took 1 to 6 s longer to decode, and peaked about 1.2 GiB higher (39.7 against 38.5 GiB). On the clean plate the conv decoder also stayed closer to the source wall (26.2 against 24.4 dB PSNR). [run: studio/web/showcase/vfx_same_clip.json:216-289]

LTX-2.5 video VAE verdict: the conv decoder stays the default and no best-quality option was added. Side by side the frames are near-identical; the diffusion decoder is slightly smoother, with less fine stone and mortar detail. The test ran on the first source clip and was not repeated on the new one. [run: studio/web/showcase/vfx_same_clip.json:289-290]

LTX audio VAE and precision: DubIt keeps a speaker's voice by encoding the clip's sound through the LTX audio VAE. ComfyUI 0.43.0's audio encoder stops with a bf16/float mismatch when the VAE is forced to half precision (--bf16-vae or --fp16-vae). A ComfyUI started with --fp32-vae runs it. The Dub page checks the server's launch flags and refuses DubIt with that message instead of failing mid-render. [code: studio/feature_dub.py:52-64] [test: tests/test_feature_dub.py]

LTX audio VAE proof: the DubIt run that worked used a ComfyUI lane started with --fp32-vae (WER 0 on the Spanish line, 53.2 s, 43.1 GiB). With the half-precision VAE flag the audio encoder stopped. [run: studio/dub_proof.json:148-170]

VAE precision and H3 voices: the half-precision VAE was first suspected of garbling MiniMax H3's speech. That was not the cause: talking templates gave H3 no written words. Clips with exact words inside the d tag measured 0 to 6% WER on the same half-precision lanes. [code: studio/recipe_library/video_templates.json:61] [claim: commit b60c9e34, 2026-11-02]

SDXL fp16-fix VAE: a studio template runs SDXL base with madebyollin's fp16-fix VAE for decoding. One recorded render: 30.4 s, 7.3 GiB peak. [code: studio/family_templates/index.json:3045-3047] [run: studio/family_status.json:9504-9506]

Music 3 full DAV decoder: a variant of ComfyUI's Music 3 graph decodes with minimax_music3_dav_full (292 MB, origin not identified) in place of the 207 MB DAV decoder. It made 60 s of music in 55.6 s at 14.7 GiB, checked by loudness and spectrum (steady beat, harmonic content, no silence), not by ear. [code: studio/family_templates/index.json:3495-3497] [run: studio/family_status.json:6110] [claim: commit 2099f6d7, 2026-11-02]

VAE and black pictures: when the latent looks fine and the picture is black, the University lesson says to try --fp32-vae first; --fp16-vae warns it may cause black images. [docs: studio/university/200/CU-291-black-images-nan-grey/lesson.md:54-55]
