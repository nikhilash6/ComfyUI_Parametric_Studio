# Upscalers, restorers and frame interpolation: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

LTX Finish x2 upscale: LTX-2.5 22B distilled int8 with the LTX-2.5 Pixel-Spatial-Upscaler IC-LoRA doubles a clip. On a fresh tapestry clip shrunk on purpose it gave exactly twice the guide (960x512 from 480x256) in 14.4 s at 39.8 GiB, with every thread and fern leaflet crisp, one run on the test machine. [run: studio/finish_proof.json:569-596]

LTX Finish x2 upscale redraws detail: the gold pattern and the stitches came out new, not the original's. Against the clean original a plain Lanczos x2 scored PSNR 34.4 dB, SSIM 0.969 and VMAF 96.4; the LTX x2 scored 19.0 dB, 0.421 and VMAF 14.7. It invents texture rather than recovering it, as its card warns: use it on drafts, not on footage that must stay faithful. [run: studio/finish_proof.json:583, studio/finish_proof.json:614-625]

LTX Finish restore and deblur as upscale neighbours: Restore lifted VMAF from 0.5 to 38.6 on a faded home-movie copy but invented what the fade destroyed. Deblur lifted VMAF from 8 to 66 and PSNR by 2.1 dB, with the far background left a little soft. Remove compression raised VMAF from 12.7 to 50.5 but cost 1.7 dB PSNR by adding sharpening the original never had. [run: studio/finish_proof.json]

SeedVR2 3B int8: ComfyUI's SeedVR2 templates have recorded renders: a picture upscale in 36.7 s at 7.1 GiB, and a video upscale in 258.8 s at 29.9 GiB, one run each. [run: studio/family_status.json:9792-9831]

CCSR x2: a studio template upscales a picture 2x with kijai's CCSR nodes (real-world CCSR, fp16), using tiles; one render, 55.5 s at 4.5 GiB. [code: studio/family_templates/index.json:2361-2363] [run: studio/family_status.json:13354-13376]

GFPGAN 1.4 face restore: a studio template runs comfyorg's GFPGAN node with facexlib's detector and parsers. On an invented adult's face shrunk to 160 px, blurred and saved at JPEG quality 30, eyes, brows, lips and hair edges came back sharp and it still read as the same person, a little rounder and younger; only the face is redrawn (3.1 s warm, 0.5 GiB). On a harsher test (100 px, JPEG quality 18) it redrew the face as a visibly different person, and the template warns about that. Apache-2.0 (GFPGAN), MIT (facexlib). [code: studio/family_templates/index.json:153-155] [run: studio/family_status.json:1211-1232]

RIFE frame interpolation: studio templates swap RIFE 4.25 (and its heavy and lite versions) into ComfyUI's frame interpolation graph in place of FILM. Recorded renders: RIFE 4.25 50.8 s at 1.2 GiB, heavy 50.7 s at 1.2 GiB, lite 35.4 s at 0.8 GiB. [code: studio/family_templates/index.json:2857-2859] [run: studio/family_status.json:3031, studio/family_status.json:3057]

H3-native video upscale chains: three latent and VAE upscale chains for MiniMax H3 clips exist in the earlier studio's notes as an answer to SeedVR2 not taking an H3-size clip. They have no recorded pass, there or here, and are not in the studio. [claim: ComfyCopilot knowledge harvest, 2026-11-03]
