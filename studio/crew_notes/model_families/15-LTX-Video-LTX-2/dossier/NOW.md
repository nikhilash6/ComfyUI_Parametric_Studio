# LTX-Video and LTX-2: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

GUIDE.md holds the prompting rules and the earlier studio's adapter notes. This file records what LTX-2.5 and its IC-LoRAs did on the test machine in the last session. Every time and peak below is one run on a 96 GB card, not a promise for other cards. [docs: studio/crew_notes/model_families/15-LTX-Video-LTX-2/dossier/GUIDE.md] [inference]

## LTX Finish: six repairs, measured against the clean original

LTX Finish runs six of Lightricks' LTX-2.5 IC-LoRAs on LTX-2.5 22B distilled int8: Restore, Deblur, Remove compression, Colorize, an x2 upscale and SDR to HDR. One repair graph switches the LoRA, strength and prompt per effect; SDR to HDR has its own graph. [code: studio/feature_finish.py:1-2, studio/feature_finish.py:20-31]

LTX Finish numbers come from AI-generated clips damaged on purpose with ffmpeg, then compared frame by frame with the clean original by PSNR, SSIM and VMAF. Each effect was also looked at. Clips were 97 frames at 960x544; each run took 14 to 65 s with a peak of 36.4 to 44.3 GiB. [run: studio/finish_proof.json:2, studio/finish_proof.json:5-790]

LTX Finish Deblur is the clearest win. On a fresh clip thrown out of focus, PSNR rose from 29.98 to 32.12 dB, SSIM from 0.89 to 0.94 and VMAF from 7.8 to 66.0, and it was better on all three measures on two older clips too. The card covers lens defocus, not motion blur, so only defocus was tested. [run: studio/finish_proof.json:269-310, studio/finish_proof.json:363, studio/finish_proof.json:413]

LTX Finish Restore re-draws rather than recovers. On a fresh clip with a faded home-movie look it was better on all three measures (VMAF 0.5 to 38.6), but it invented patterned shirts and greener grass. On heavier blur, grain and CRF 40 damage, only VMAF rose; PSNR and SSIM fell, and one jungle clip came back as a different jungle. [run: studio/finish_proof.json:112-160, studio/finish_proof.json:206, studio/finish_proof.json:254]

LTX Finish Remove compression, on H.264 at CRF 45: on a greenhouse clip SSIM and VMAF rose (VMAF 12.7 to 50.5) while PSNR fell 1.65 dB because it adds sharpening the original never had. On dense jungle foliage it was no closer on any measure (VMAF 28.4 to 26.5). [run: studio/finish_proof.json:699-790]

LTX Finish Colorize brings colour back from pure grey, steered by the prompt's colour words, not recovered. On a fresh 1950s street it came out more vivid than the original and moved further from it (colour distance 5.1 to 8.2); on a jungle clip it moved closer (13.9 to 8.2). [run: studio/finish_proof.json:5-40, studio/finish_proof.json:89]

LTX Finish x2 upscale gives exactly twice the guide size (960x512 from 480x256) but invents texture, as its card warns. Against the original, the LTX x2 scored VMAF 14.7 where a plain Lanczos x2 scored 96.4; on a second clip, 5.1 against 84.4. Use it for drafts, not footage that must stay faithful. [run: studio/finish_proof.json:614-625, studio/finish_proof.json:681-692]

The studio's SeedVR2 edit tool, tried on the same half-size clip, handed the input back unchanged, so LTX Finish has no SeedVR2 comparison. That tool needs fixing. [run: studio/finish_proof.json:697]

LTX Finish SDR to HDR takes no prompt: a fixed scene embedding drives it. It writes an HLG BT.2020 10-bit H.264 master, a ProRes 4444 12-bit HLG master and half-float EXR frames, all three checked. The headroom lands in the sun, the sky and glints (6 to 7% of pixels above SDR white on the two clips); on an SDR screen the result looks like the source. [run: studio/finish_proof.json:430-500] [code: studio/feature_finish.py:30-31]

## DubIt on LTX-2.5

The LTX-2.3 DubIt IC-LoRA 0.9 runs on LTX-2.5 distilled int8. On a Spanish line over an invented woman's clip, 121 frames at 768x768, it took 53.2 s at 43.1 GiB, and Whisper heard the Spanish line exactly (word error rate 0.0). The voice is only a little like hers: likeness 0.63 to the source voice, against 0.87 for a Qwen3-TTS clone and about 0.60 for an unrelated voice. Hair curls shift between frames, and the sound comes out unmastered at -11.5 LUFS and -0.6 dBTP. Nobody has listened. [run: studio/dub_proof.json:148-171]

DubIt needs a full-precision VAE. LTX's audio encoder stops with a bf16/float mismatch when ComfyUI is started with --bf16-vae or --fp16-vae, so the studio refuses DubIt on such a ComfyUI and offers --fp32-vae or the LatentSync route instead. [code: studio/feature_dub.py:52-65] [test: tests/test_feature_dub.py]

## Shot Board and VFX on LTX-2.5

LTX-2.5 transition: the LTX-2.3 style-transition LoRA (trigger zhuanchang) runs on LTX-2.5 distilled int8. The output is clip A, a 49-frame bridge from A's last frame to B's first, then clip B: 291 frames at 960x544, 16.5 s and a 37.8 GiB lane peak with the default prompt. Both seams were continuous and the person stayed whole. Extra day-to-night words made a moon rise in the bridge and vanish in clip B, so the default prompt ships. No run without the LoRA was made, so what the LoRA adds over plain first- and last-frame guidance is not measured. [run: studio/web/showcase/transition_proof.json] [code: studio/goals.py:73]

LTX-2.5 video VAE A/B: the same four VFX jobs decoded with the conv VAE the studio ships and with Lightricks' diffusion decoder. The diffusion decoder was slightly smoother, took 1 to 6 s more to decode and peaked about 1.2 GiB higher (39.7 against 38.5 GiB). It was not clearly better, so the conv decoder stays the default. Measured on one source clip only. [run: studio/web/showcase/vfx_same_clip.json:216-290]

LTX-2.5 VFX auto strength: water defaults to natural (1.0) and day to night to strong (1.3). In same-clip renders, strong water turned dark trousers red while natural kept them, and natural night stayed dusk-bright while strong read as night and kept the clothes. The VFX page and the Shot Board start on auto. [code: studio/goals.py:70-71]

LTX-2.5 VRAM per VFX effect on a 96 GB card with every weight resident: 37.5 to 38.5 GiB at draft and standard sizes and 39.5 GiB at 1280x704; the 5 s clips took 23 to 37 s at draft and standard sizes. Under an emulated 14 GiB budget the peak was 19.6 GiB while the Gemma text encoder loaded, and 10.4 GiB with the prompt encoding cached. So 48 GB cards fit (measured), 24 GB likely fit (emulated only), and 16 GB is not claimed. [run: studio/web/showcase/vfx_same_clip.json:118-213]

## Camera Paths motion track

LTX-2.5 with the LTX-2.3 Motion-Track-Control IC-LoRA draws an object along a line. It renders at 960x576, because the LoRA works on a half-size grid and both sides must be multiples of 64; 121 frames at 24 fps. A red paper boat on a stream took 31.8 s at 39.2 GiB and stayed within 24.9 px of the line on average (40.1 px at most) over 121 frames, followed by colour. Looked at frame by frame. [code: studio/feature_camera.py:19] [run: studio/camera_proof.json:259-310]

The first object follower (Lucas-Kanade on points around the start) stayed on the pebbles and reported 274 px. It was replaced by template matching; the render was not repeated. [run: studio/camera_proof.json:6]

## Other LTX renders

LTX-Video 13B 0.9.8 distilled fp8 rendered through ComfyUI's LTX-Video text-to-video graph, with transformer and VAE in one file: 8 steps at CFG 1, 97 frames at 768x512, 30.3 s and a 23.1 GiB peak, one run, viewed. [run: studio/family_status.json:4910-4922] [code: studio/family_templates/ltxv13b_098_distilled_t2v.json]

LTX-2.5 in one-click effects: Qwen-Image-Edit 2511 makes the edited still, then LTX-2.5 starts in place on the photo with a guide only on the last frame, so the photo swells into the edit; a guide on both ends cross-faded instead. Unloading Qwen before LTX loads cut the peak from 66.0 to 38.9 GiB. A 5 s still-plus-clip run took 69.4 s; the face drifts a little toward the edited still by the end. [run: studio/web/oneclick_art/index.json:53-80] [code: studio/feature_oneclick.py:84]
