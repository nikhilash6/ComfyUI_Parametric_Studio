# Depth, normals and pose: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## Depth and pose models outside this folder's three families

Lotus, recorded as its own family, turns one picture into a depth map in a single step (template image_lotus_depth_v1_1, lotus-depth-d-v1-1). One run on 2026-11-01: 20.1 s, seed 1367146187. No peak is recorded. Apache-2.0. [run: studio/family_status.json:12998-13054]

SDPose, recorded as its own family, gives a whole-body pose from a picture (template utility_sdpose_ood_image_to_pose, sdpose_wholebody_fp16). One run on 2026-11-01: 20.1 s, seed 1270234353. No peak is recorded. MIT for the ComfyUI repackage. [run: studio/family_status.json:13055-13107]

## How depth and pose maps are used downstream

SDXL depth control now works from a depth map: the xinsir depth ControlNet kept the street, the cars and the figure where a rainy-street depth map put them while the words turned it into a snowy evening. See the SDXL notes. [run: studio/family_status.json:9578-9592] [code: studio/family_templates/sdxl_controlnet_depth.json:37, studio/family_templates/sdxl_controlnet_depth.json:68] [claim: studio commit af5a42cb, 2026-11-02]

SDXL pose control followed the pose only loosely and cropped the legs when its skeleton was enlarged from a small SDPose picture. A clean full-size skeleton has not been tried. Feed pose ControlNets a skeleton drawn at the output size. [code: studio/family_templates/index.json:1628] [inference]

## This folder's own families today

FitDiT is still not rendered (checked 2026-11-02). Both FitDiT transformers, the VAE, DWPose and the parsers are on disk. The pose guider, the repo's config files and the two CLIP vision towers the pack loads (ViT-L/14 and ViT-bigG/14) are missing. CC BY-NC-SA 4.0, so non-commercial. [run: studio/family_status.json:1430]

dwpose and LDM3D-4C are unchanged since 2026-11-01: dwpose's record is a WanVideo UniAnimate DWPose detector run on the main ComfyUI (27.7 s), and LDM3D-4C's is a diffusers StableDiffusionLDM3DPipeline run (11.1 s). Neither has a new run. [run: studio/family_status.json:1047, studio/family_status.json:4637]

Marigold v2 runs as LoRAs on Qwen-Image-Edit 2509 (int8), from ComfyUI's own templates, each recorded once on 2026-11-03 and looked at: surface normals 30.4 s at 16.4 GiB, albedo 40.6 s at 20.4 GiB, and depth 33.4 s at 17.8 GiB. The depth run on a Kolors still life took one step with no noise: sharp edges on the jug's handle, every peach separate, the table falling away cleanly; its fault is that the window bars barely stand apart from the glass behind them. The records sit under the Qwen-Image-2.1 family because the base is a Qwen edit model. [run: studio/family_status.json:7831-7870]
