# ComfyUniversity course catalogue

162 lessons in 18 tracks. 162 have had an independent second read, which found and fixed 203 errors. 0 are checked by their author, with the second read pending. 0 are labelled Draft. Every lesson has a CPU lab with stored output and a quiz. Rebuild with `python studio/university/build.py --labs`.

## Your first graph

Press Queue and know what happened. Nodes, wires, seeds, files, and how to read a workflow.

- **CU-100** (100) [Your first graph, with no model at all](100/CU-100-first-graph-no-model/lesson.md). Three nodes, no model, no GPU. See what a node, a wire and an output node are by making them work in under a second.
- **CU-101** (100) [What generative AI actually is](100/CU-101-what-is-generative-ai/lesson.md). Learn a distribution, then sample from it. Three models on one dataset show the difference between learning and memorising, and what that means for the file you download.
- **CU-102** (100) [Anatomy of a ComfyUI graph](100/CU-102-anatomy-of-a-graph/lesson.md). A small engine that follows ComfyUI's rules shows which nodes run, which come from the cache, and why changing the checkpoint re-runs six nodes, not seven.
- **CU-106** (100) [Your first image: checkpoint, sampler, VAE](100/CU-106-first-image-walkthrough/lesson.md). Follow one prompt through checkpoint, text encoder, sampler and VAE: the shape of every hand-off, and the 20 sigma values that the sampler walks down, checked against the ComfyUI documentation. Needs CU-102.
- **CU-112** (100) [What Queue really does, and where your picture went](100/CU-112-what-queue-does/lesson.md). Follow one press of Queue from the editor to a file on disk: what is sent, what waits, what history keeps, and how the file gets its name. Needs CU-102.
- **CU-116** (100) [Your own picture: the input folder, LoadImage and its mask](100/CU-116-your-own-picture/lesson.md). Where an uploaded picture lives, the two things LoadImage hands on, and why a picture with no alpha gives a 64 by 64 mask. Needs CU-103, CU-106.
- **CU-110** (100) [Reading a workflow JSON like a map](100/CU-110-reading-workflow-json-like-a-map/lesson.md). The same seven-node graph in the editor's save format and the server's API format, read with one recipe: follow the wire back, check the wiring, and translate between the two. Needs CU-102.
- **CU-113** (100) [Mute, bypass, reroutes and groups: what the server really gets](100/CU-113-mute-bypass-reroute-group/lesson.md). Bypass rewires the graph, Mute cuts it, and reroutes and groups never reach the graph the server runs. See the JSON each one produces. Needs CU-102, CU-110.
- **CU-103** (100) [Pixels, tensors and shapes](100/CU-103-pixels-tensors-shapes/lesson.md). Why IMAGE is [B, H, W, C] and LATENT is [B, C, H/8, W/8], what the VAE nodes do to cross between them, and where truncating 8-bit levels bites.
- **CU-105** (100) [Seeds, noise and determinism](100/CU-105-seeds-and-noise/lesson.md). A seed makes the starting noise, plus the extra noise of an ancestral sampler, and nothing more. A toy sampler with an exact denoiser shows what that does and does not fix when you change steps, samplers or hardware.
- **CU-104** (100) [Prompts become numbers: tokens and embeddings](100/CU-104-prompts-to-embeddings/lesson.md). Follow a prompt to the tensor the sampler gets: byte-pair splitting, an embedding table that does not know its neighbours, and causal attention that does.
- **CU-107** (100) [Models on disk: safetensors and families](100/CU-107-models-on-disk/lesson.md). Build and damage a safetensors file by hand, watch a pickle run code, and see how ComfyUI tells SD 1.x from SDXL by reading three shapes from a header.
- **CU-114** (100) [Which file goes in which loader and folder](100/CU-114-which-file-which-loader/lesson.md). Checkpoint, diffusion model, text encoder, VAE: what each one holds, which folder feeds which menu, and how to tell them apart when the file name tells you nothing. Needs CU-107.
- **CU-109** (100) [Resolution, aspect ratio and the pixel budget](100/CU-109-resolution-aspect-ratio-pixel-budget/lesson.md). From an aspect ratio and a pixel budget to a size the VAE accepts: the square-root formula, what ComfyUI's size nodes round to, and how fast attention and VAE costs grow. Needs CU-103.
- **CU-111** (100) [Files and formats: PNG metadata, MP4, WAV, safetensors](100/CU-111-files-formats/lesson.md). Build a PNG that carries a workflow, a WAV file and an MP4-style box stream by hand, and see why a reader walks chunks and boxes, why a flipped bit is caught, and what dropping metadata really removes.
- **CU-115** (100) [Reading a downloaded workflow before you run it](100/CU-115-read-a-workflow-before-running/lesson.md). A workflow file is data, and it can still cost you. Five things to look for before you press Queue, and where each one hides. Needs CU-110, CU-113.

## Samplers, schedulers and CFG

The loop at the heart of ComfyUI, the choices it exposes, and what those choices really change.

- **CU-230** (200) [KSampler, field by field](200/CU-230-ksampler-field-by-field/lesson.md). Ten inputs, and each one changes something different. Change them one at a time on a toy and read what moved, what it cost, and what stayed. Needs CU-106.
- **CU-231** (200) [Denoise and image to image](200/CU-231-denoise-and-img2img/lesson.md). Denoise is not a strength dial on the model. It picks where on the schedule to start, and how much noise your picture gets first. Needs CU-230.
- **CU-202** (200) [Diffusion from first principles](200/CU-202-diffusion-from-first-principles/lesson.md). Destroy data with noise on purpose, learn to undo one step, and train a real model on a CPU. Needs CU-101, CU-105.
- **CU-205** (200) [Samplers are ODE solvers](200/CU-205-samplers-as-ode-solvers/lesson.md). Euler, Heun and DPM++ 2M written in five lines each, then measured against the exact answer. Needs CU-203.
- **CU-206** (200) [Sigma schedules: where the steps go](200/CU-206-sigma-schedules/lesson.md). The scheduler chooses which noise levels the solver visits. Same model, same steps, different error. Needs CU-205.
- **CU-207** (200) [Ancestral and SDE samplers: adding noise back](200/CU-207-ancestral-and-sde-samplers/lesson.md). Why a sampler that keeps injecting noise never settles on one image, and when that helps. Needs CU-205.
- **CU-232** (200) [KSampler taken apart: SamplerCustomAdvanced](200/CU-232-ksampler-taken-apart/lesson.md). Noise, guider, sampler, sigmas and a latent: the same run as separate parts, so you can change any one of them. Needs CU-230.
- **CU-233** (200) [Two samplers, one schedule: leftover noise](200/CU-233-two-samplers-one-schedule/lesson.md). Stop a run part-way with its noise still in, hand it on, and finish with another sampler or model. Three settings make it work and each one fails differently. Needs CU-230, CU-232.
- **CU-234** (200) [Choosing a sampler from real renders and measures](200/CU-234-choosing-a-sampler/lesson.md). Fifteen real renders on one seed and a bench of 45 sampler names. What they can tell you, what they cannot, and a way to choose that survives both. Needs CU-205, CU-207.
- **CU-235** (200) [Choosing a scheduler from the curves](200/CU-235-choosing-a-scheduler/lesson.md). A schedule is a list you can read before you spend a second of GPU. Two lists warned of the two broken renders in our sweep. Needs CU-206, CU-234.

## Noise and latent maths

What a latent is, what noise is doing to it, and the numbers that keep images from breaking.

- **CU-240** (200) [What a seed does](200/CU-240-what-a-seed-does/lesson.md). A seed picks one block of random numbers, on the CPU. What that does and does not guarantee, how batches share it, and what colour means in noise. Needs CU-105.
- **CU-201** (200) [Latent space and the VAE](200/CU-201-latent-space-and-the-vae/lesson.md). Train a tiny VAE on a CPU, and see when the midpoint of two latents is a picture, and why the midpoint of two images is a ghost. Needs CU-101, CU-103.
- **CU-241** (200) [Latent operations, and why multiplying changes the picture](200/CU-241-latent-operations/lesson.md). A latent is just numbers, so you can add and multiply them. Why that does nothing to an empty latent, a little early in a run, and a lot at the end. Needs CU-201, CU-240.
- **CU-203** (200) [Score matching, Tweedie and the SDE view](200/CU-203-score-matching-and-sdes/lesson.md). Why predicting noise is the same as learning the gradient of the noised data density, checked numerically. Needs CU-202.
- **CU-204** (200) [Flow matching and rectified flow](200/CU-204-flow-matching-and-rectified-flow/lesson.md). Each training pair flies straight. The field you actually integrate does not, and that is the whole subject. Needs CU-202, CU-203.
- **CU-242** (200) [eps, v-prediction and flow: how a model's output is read](200/CU-242-eps-v-and-flow/lesson.md). The same network output means different things to different models. model_sampling.py is where ComfyUI says which, and what happens when it says wrong. Needs CU-202, CU-204.
- **CU-314** (300) [Flow-matching losses and velocity targets](300/CU-314-flow-matching-losses-and-velocity-target/lesson.md). The target for each training pair is simple. Why the loss never reaches zero, why the same error looks different in other units, and what ComfyUI's own trainer really minimises. Needs CU-204.
- **CU-210** (200) [Precision: fp32, fp16, bf16, fp8](200/CU-210-precision/lesson.md). Where rounding bites: small LoRA deltas turn to noise, sums stall, and fp16 tops out at 65,504. Needs CU-103.
- **CU-229** (200) [Color spaces, gamma and image math](200/CU-229-color-and-image-math/lesson.md). Half black and half white is not 0.5 in light: what blending and shrinking do to sRGB codes, and why SaveImage truncates. Needs CU-103.
- **CU-243** (200) [Reading the Sampling Lab](200/CU-243-reading-the-sampling-lab/lesson.md). 720 methods, four kinds of proof, curves, a bench and renders. What each label promises, and how to use the page to answer a real question. Needs CU-234, CU-235.

## Guidance

CFG and everything built to fix it: rescale, CFG++, PAG, SAG, Perp-Neg, and embedded guidance.

- **CU-208** (200) [Guidance: CFG and what it really does](200/CU-208-guidance-cfg/lesson.md). One line of arithmetic, and it does not sample the distribution people usually say it does. Needs CU-205.
- **CU-250** (200) [CFG overshoot, measured on real renders](200/CU-250-cfg-overshoot/lesson.md). Same seed, cfg 7 against cfg 14, with the numbers. Higher cfg moved the layout and raised the contrast. It did not add edge detail. Needs CU-208.
- **CU-209** (200) [Negative prompts and cfg 1.0](200/CU-209-negative-prompts/lesson.md). A negative prompt is not a subtraction of concepts. It replaces the unconditional branch, and with an ordinary sampler at cfg 1 it does nothing at all. Needs CU-208.
- **CU-251** (200) [Embedded guidance against CFG](200/CU-251-embedded-guidance/lesson.md). Cfg is a sum done outside the model. FluxGuidance is a number handed to it. Why some flux-family graphs run at cfg 1, and why not all of them do. Needs CU-208, CU-209.
- **CU-320** (300) [RescaleCFG, CFGNorm, APG and CFG-Zero-Star](300/CU-320-cfg-fixes/lesson.md). Four nodes that try to fix high cfg, each read from source, each on the same seed. One washed the picture grey, one barely touched it, and one's default setting skips its main idea. Needs CU-208, CU-250.
- **CU-321** (300) [CFG++ samplers, and why cfg is near 1 there](300/CU-321-cfgpp-samplers/lesson.md). One swap inside the sampler: re-noise with the unconditional prediction. That moves cfg to a different scale, and it means cfg 1 still costs two predictions. Needs CU-208, CU-205.
- **CU-322** (300) [PAG, SAG and TCFG: what the extra guidance costs](300/CU-322-pag-sag-tcfg/lesson.md). Three ways to add guidance without a prompt. Two pay with a whole extra prediction each step, and the third with one SVD. Read from source, with our renders. Needs CU-208, CU-301.
- **CU-323** (300) [Perp-Neg: negatives that do not fight the prompt](300/CU-323-perp-neg/lesson.md). Plain cfg cancels whatever your two prompts share. Perp-Neg removes only the part of the negative at right angles to the positive, for one more prediction per step. Needs CU-208, CU-209.

## Conditioning

How a prompt reaches the model, and how to mix, time and place several of them.

- **CU-260** (200) [What CONDITIONING really is](200/CU-260-what-conditioning-is/lesson.md). A plain Python list. Each entry is a tensor and a dict. Nearly every conditioning node just changes one of those, and that explains what they can and can't do. Needs CU-104.
- **CU-261** (200) [Prompt weights: what the brackets really do](200/CU-261-prompt-weights/lesson.md). Brackets don't multiply a word's embedding. They push it away from what the empty prompt has at that position. And some text encoders ignore them completely. Needs CU-260.
- **CU-262** (200) [Combine, Concat and Average](200/CU-262-combine-concat-average/lesson.md). Three ways to use two prompts, read from nodes.py. One blends the model's answers, one makes one long prompt, and one blends the embeddings. They cost different amounts, and they give different pictures. Needs CU-260.
- **CU-263** (200) [Regions: ConditioningSetArea and ConditioningSetMask](200/CU-263-regions-area-and-mask/lesson.md). A boxed prompt is a real crop: the model sees only that part of the latent. A mask is a share of the blend, with the model looking at everything. Strength is relative, and bare cells get nothing. Needs CU-260, CU-262.
- **CU-264** (200) [Changing the prompt over time](200/CU-264-prompt-over-time/lesson.md). start and end percent are not percent of your steps. They are points on the model's noise scale, so end 0.5 can be 9 of 20 steps, or 17. And a gap in your ranges leaves steps with no prompt at all. Needs CU-260, CU-206.
- **CU-306** (300) [Text encoders: CLIP, T5 and LLM encoders](300/CU-306-text-encoders-deep/lesson.md). What each encoder gives the model and what it costs. CLIP in ComfyUI is causal, T5 isn't, and neither of them hands over only the last token. Needs CU-104.
- **CU-310** (300) [Cross-attention versus joint attention](300/CU-310-cross-attention-versus-joint-attention/lesson.md). How the picture reads the prompt in a U-Net and in a transformer. In one the text never changes. In the other the text is updated too, and image tokens see each other in the same step. Needs CU-301.
- **CU-265** (200) [Reference images: CLIP vision, unCLIP and style models](200/CU-265-reference-images/lesson.md). Two general doors in core for a picture. A style model adds tokens to the prompt. unCLIP changes the model's global vector. CLIP vision makes the numbers for both, and it isn't a model that generates anything. Needs CU-260, CU-262.

## ControlNet, depth and inpainting

Steer shape, depth and regions with a picture, and keep the rest of the image.

- **CU-214** (200) [Conditioning: img2img, inpaint, ControlNet, IP-Adapter](200/CU-214-conditioning-controlnet-ip/lesson.md). Every way of telling the model more than a prompt, placed at the point where it enters: what denoise really sets, what a ControlNet window covers, and why zero is not the same as absent. Needs CU-106.
- **CU-270** (200) [ControlNet strength, start and end percent](200/CU-270-controlnet-strength-and-percent/lesson.md). Why end_percent 0.5 is not half your steps, why a ControlNet can switch off completely at low denoise, and what strength really multiplies. Needs CU-214.
- **CU-219** (200) [Depth and edge preprocessors: Sobel by hand](200/CU-219-depth-edge-preprocessors-sobel-by/lesson.md). Compute Sobel by hand, see why Canny blurs first and what its thresholds are measured in, and learn how a depth map becomes a grey hint. Needs CU-103.
- **CU-271** (200) [Preprocessors: Canny in core, and looking at your map](200/CU-271-preprocessors-canny-preview/lesson.md). Canny's thresholds aren't fractions of white. Learn what they are measured in, how to preview a control image, and what a bad map does. Needs CU-219, CU-270.
- **CU-272** (200) [Depth: conventions and core's depth nodes](200/CU-272-depth-conventions-core-nodes/lesson.md). Which end is white, what the grey steps mean, and which depth nodes core really has: Lotus, MoGe and Depth Anything 3, read from the source. Needs CU-219, CU-270.
- **CU-213** (200) [Inpainting masks and edge blending](200/CU-213-inpainting-masks-edge-blending/lesson.md). The sampler sees your mask on a grid eight times coarser than the picture: where a 3-pixel line vanishes, what grow and feather really do, and how the per-step blend works. Needs CU-201, CU-214.
- **CU-273** (200) [Choosing an inpaint route](200/CU-273-choosing-an-inpaint-route/lesson.md). SetLatentNoiseMask, VAEEncodeForInpaint or InpaintModelConditioning: read what each one really does to your picture and your mask, then choose by model and denoise. Needs CU-213.
- **CU-274** (200) [Outpainting with ImagePadForOutpaint](200/CU-274-outpainting/lesson.md). Add canvas beyond the edge. Read what the pad node makes, why its feather can switch itself off, and how much of your picture gets repainted. Needs CU-273.

## LoRAs and training

What a LoRA is as maths, how to load it right, and how to train one with core nodes.

- **CU-212** (200) [LoRA: low-rank adaptation](200/CU-212-lora-low-rank/lesson.md). Why two skinny matrices can change a giant one, when they cannot, and what rounding does to a small update. Needs CU-210.
- **CU-280** (200) [Loading a LoRA right](200/CU-280-loading-a-lora-right/lesson.md). LoraLoader or LoraLoaderModelOnly, two strengths, chains, and the one log line that tells you the file didn't fit your model. Needs CU-212.
- **CU-282** (200) [Telling whether a LoRA works](200/CU-282-telling-whether-a-lora-works/lesson.md). Same seed, off and on. Then a strength sweep and more than one seed. How to get an answer you can trust from a few renders. Needs CU-280.
- **CU-420** (400) [Rank, alpha, DoRA, LoKr and the other adapters](400/CU-420-rank-alpha-dora-lokr/lesson.md). Every patch format in comfy/weight_adapter, as a sum you can check: what it stores, what it can reach, and what alpha means in each. Needs CU-212.
- **CU-412** (400) [Dataset curation and captioning for training](400/CU-412-dataset-curation-and-captioning-for-trai/lesson.md). What core's training path really does with your pictures and captions, how often it sees each one, and why a caption decides what a trigger word learns. Needs CU-281.
- **CU-281** (200) [Train a LoRA with core nodes](200/CU-281-train-a-lora-with-core-nodes/lesson.md). Six core nodes, and our real 300-step run with its real loss curve. What the nodes do at each step, what the run shows, and what it can't. Needs CU-280.
- **CU-403** (400) [Model merging: weighted, SLERP, task arithmetic](400/CU-403-model-merging-math/lesson.md). Why averaging weights can work, what ModelMergeSimple's ratio really is, and the sums behind the rule: merge unquantized files, quantize after. Needs CU-212, CU-211.
- **CU-409** (400) [Distillation math: teacher, student, consistency](400/CU-409-distillation-math-teacher-student/lesson.md). How a slow sampler's work becomes one model call, on a problem with an exact answer. What a student can copy, what it can't, and what core runs. Needs CU-205.

## Video: LTX-2.5, MiniMax H3, Wan

Frames, temporal latents, and the three models this studio runs, node by node.

- **CU-215** (200) [Video basics: frames, fps and temporal latents](200/CU-215-video-basics/lesson.md). Why five seconds at 24 fps comes back as 117 frames, how a video VAE counts, and how attention cost climbs with duration. Needs CU-201.
- **CU-330** (300) [How video latents work, and each model's frame grid](300/CU-330-video-latents-frame-grids/lesson.md). Ask three models for 120 frames and get 113, 117 and 124. Why, and how to ask so you get what you typed. Needs CU-215.
- **CU-218** (200) [Seeds, batches and variations in video](200/CU-218-seeds-batches-variations-video/lesson.md). The seed fills one block of noise in memory order: why a different frame count is a different video, why batch items can be redone alone, and why a blended noise must be rescaled. Needs CU-105, CU-215.
- **CU-331** (300) [LTX-2.5, node by node](300/CU-331-ltx25-node-by-node/lesson.md). Eight model calls, a fixed noise list, video and sound in one latent: read the real graph one node at a time. Needs CU-330.
- **CU-332** (300) [MiniMax H3, node by node, with sound in the same latent](300/CU-332-minimax-h3-node-by-node/lesson.md). One sampler, one latent, picture and sound on one clock. How a video model writes its own soundtrack, read from the source. Needs CU-330.
- **CU-333** (300) [Wan 2.2 5B, node by node, and how it differs from the 14B pair](300/CU-333-wan22-5b-node-by-node/lesson.md). One small model with a stronger VAE, or two big ones that hand over mid-run. What the configs say, and what our graph changes. Needs CU-330.
- **CU-217** (200) [Upscaling and tiling math](200/CU-217-upscaling-tiling-math/lesson.md). How ComfyUI cuts an image into tiles, why a ramp hides the seam, and why tiled decoding saves memory but costs 3.77 times the work. Needs CU-201.
- **CU-315** (300) [Temporal consistency and optical flow basics](300/CU-315-temporal-consistency-optical-flow-basics/lesson.md). What optical flow really measures, how to tell motion from flicker, and what core ComfyUI does with both. Needs CU-215.
- **CU-316** (300) [Video VAEs and receptive fields](300/CU-316-video-vaes-and-receptive-fields/lesson.md). How far one latent can see, measured by experiment, and why that sets the first-frame rule and the overlap your tiles need. Needs CU-215, CU-201.
- **CU-334** (300) [Long video and memory: chunks, tiled decode, and what truly helps](300/CU-334-long-video-and-memory/lesson.md). Tiled decode can't save a sampler that's out of memory, and H3 ignores it anyway. Match each fix to the cost it really touches. Needs CU-330, CU-217.
- **CU-411** (400) [Evaluating video: a flicker metric](400/CU-411-evaluating-video-flicker-metric/lesson.md). Two simple flicker scores, tested on clips where we know the answer. Both are fooled by a pan, and one step fixes that. Needs CU-404, CU-315.

## Audio and Music 3

Waveforms, spectrograms, audio latents, and making songs with MiniMax Music 3.

- **CU-216** (200) [Audio and music basics: waveforms to spectrograms](200/CU-216-audio-basics/lesson.md). Why a 6 kHz tone sampled at 10 kHz is heard at 4 kHz, what a longer frame buys and costs, and how ComfyUI turns seconds into audio latents.
- **CU-351** (300) [Waveform, sample rate and spectrograms: ComfyUI's AUDIO type](300/CU-351-audio-type-waveform-spectrogram/lesson.md). An AUDIO value is a tensor and a number. Most audio bugs in graphs come from forgetting the number. Needs CU-216.
- **CU-350** (300) [MiniMax Music 3, node by node](300/CU-350-music3-node-by-node/lesson.md). The text encoder writes the song. Then a diffusion model performs it. Caption, lyrics, seconds and the 128-channel latent, from the source. Needs CU-216.
- **CU-511** (300) [History 11: Audio models: WaveNet to autoregressive music to diffusion music](300/CU-511-history-11-audio-models/lesson.md). From one call per sample to one model call per step, then a model that does both. Where the time goes in each era. Needs CU-216.

## 3D

Meshes, splats and NeRFs, how images become 3D, and the core nodes for it.

- **CU-307** (300) [3D generation: meshes, SDFs, voxels and Gaussian splats](300/CU-307-three-d-representations/lesson.md). Voxels, SDFs, meshes and splats: what each stores, what it costs, and why blocks never reach the right area. Needs CU-201.
- **CU-361** (300) [Meshes, points and Gaussian splats](300/CU-361-meshes-points-splats/lesson.md). What each one really stores, why a splat has no surface, and what SplatToMesh has to invent to get one. Needs CU-307.
- **CU-360** (300) [Image to mesh with core nodes](300/CU-360-image-to-mesh-core-nodes/lesson.md). A sampler again, with a very strange latent, then a step that turns a grid of numbers into triangles. Why one option makes cubes. Needs CU-307.
- **CU-362** (300) [Mesh tools in core: decimate, remesh, unwrap](300/CU-362-mesh-tools-in-core/lesson.md). A generated mesh is messy, huge and has no UVs. Three core nodes fix that, if you run them in the right order. Needs CU-360.
- **CU-513** (300) [History 13: Seeing in 3D: NeRF, Gaussian splats and structured latents](300/CU-513-seeing-in-3d-nerf-gaussian-splats/lesson.md). Ask a network for every point on every ray, or just draw blobs? How 3D went from one to the other, then to sparse latents. Needs CU-307.

## Writing custom nodes

From your first V3 class to lazy inputs, caching rules, expansion and front-end extensions.

- **CU-430** (400) [Your first node, in V1 and in V3](400/CU-430-first-node-v1-v3/lesson.md). The same node written both ways, run through the real engine on a CPU. They look different, and the validator can't tell them apart. Needs CU-102.
- **CU-431** (400) [Node inputs: widgets, optional, hidden, force_input](400/CU-431-node-inputs/lesson.md). The string "false" reaches your node as True. A default in the schema doesn't reach your function at all. Inputs promise less than they seem to. Needs CU-430.
- **CU-401** (400) [Writing a custom node with the V3 API](400/CU-401-custom-nodes-v3/lesson.md). A class with a schema and an execute method. The engine calls your node on a locked copy of the class, and that changes how you write it. Needs CU-220, CU-221.
- **CU-432** (400) [Lazy inputs and check_lazy_status](400/CU-432-lazy-inputs/lesson.md). A switch with two expensive branches should only pay for one. Lazy inputs make that happen, at the cost of visiting your node twice. Needs CU-431, CU-220.
- **CU-433** (400) [When a node re-runs: fingerprints, the NaN trick, not_idempotent](400/CU-433-when-a-node-reruns/lesson.md). float("NaN") makes a node run every time, and math.nan doesn't. Three hooks decide if your node runs and if your graph is allowed to start. Needs CU-430, CU-221.
- **CU-434** (400) [Lists and batches: INPUT_IS_LIST, OUTPUT_IS_LIST](400/CU-434-lists-and-batches/lesson.md). A batch is one thing to the engine. A list is many, and your node gets called once for each. Mix them up and you get strange pairs or a stuck queue. Needs CU-431.
- **CU-222** (200) [Sub-graphs and node expansion](200/CU-222-subgraphs-and-expansion/lesson.md). A sub-graph is a front-end idea that the executor never sees. Node expansion is a server idea that the front-end never sees. Needs CU-220.
- **CU-435** (400) [Writing a node that expands into a subgraph](400/CU-435-node-expansion/lesson.md). A node can answer with new nodes rather than a result. That is how a graph with no cycles gets loops. Here is one you can write, and how it fails. Needs CU-430, CU-222.
- **CU-436** (400) [A front-end extension: WEB_DIRECTORY and registerExtension](400/CU-436-frontend-extension/lesson.md). One line of Python and one JavaScript file put your code in the editor. Here is what gets served, what gets loaded, and which hook to use. Needs CU-430.
- **CU-437** (400) [Packaging a pack without breaking anyone's install](400/CU-437-packaging-dependencies/lesson.md). All packs share one Python. One careless pin moves a library under every other pack. Here is the layout, the pyproject, and how to stay out of trouble. Needs CU-430.
- **CU-438** (400) [Testing your node without a GPU](400/CU-438-testing-without-gpu/lesson.md). Your node's bugs mostly don't need a card to show up. Three levels of test, from calling the function to running the real engine in one process. Needs CU-430.

## Debugging graphs

Read validation errors, black images and NaNs, shape mismatches, and find the cause fast.

- **CU-220** (200) [The execution model: what runs, and in what order](200/CU-220-execution-model/lesson.md). ComfyUI starts from the output nodes and works backwards. Build its scheduler in 60 lines and watch a lazy input change the order. Needs CU-102.
- **CU-290** (200) [Every validation error, and what to do about it](200/CU-290-every-validation-error/lesson.md). Before a node runs, the server checks the whole graph. It can refuse in seventeen ways. Each one, with its real text and its fix. Needs CU-100.
- **CU-221** (200) [Caching: why changing the seed does not reload the model](200/CU-221-caching/lesson.md). Each node gets a key built from its whole ancestry. Change one input and only what lies downstream runs again. Needs CU-220.
- **CU-292** (200) [Shape and size errors: reading a traceback](200/CU-292-shape-and-size-errors/lesson.md). Core nodes often resize without telling you, and then a model refuses the result. Read the numbers in the error, and it usually says which two things disagree. Needs CU-103.
- **CU-291** (200) [Black images, NaN and grey mush](200/CU-291-black-images-nan-grey/lesson.md). One bad number can turn a whole picture black, and nothing tells you. How NaN gets in, why it spreads, and the flags that really exist. Needs CU-201, CU-210.
- **CU-293** (200) [Out of memory: what ComfyUI tries first](200/CU-293-out-of-memory/lesson.md). An out of memory error means ComfyUI already tried several things. Know what it tried, and you know what's left for you to change. Needs CU-220.
- **CU-294** (200) [Missing nodes and missing models, and how to fix them safely](200/CU-294-missing-nodes-and-models/lesson.md). A graph from the internet fails. Is the node missing, the file missing, the file broken, or the file the wrong kind? Each has a different error and a different safe fix. Needs CU-107.
- **CU-295** (200) [Bisecting a broken graph: previews are your print statement](200/CU-295-bisecting-a-graph/lesson.md). Something is wrong and nothing errors. Put a preview in the middle and throw away half the graph. Four previews find one bad node out of sixteen. Needs CU-100.
- **CU-296** (200) [A result that doesn't match: reproducing someone's image](200/CU-296-reproducing-an-image/lesson.md). Same prompt, same seed, different picture. A checklist in the order that matters, and a test for each item. Needs CU-105.

## VRAM and performance

Budget memory, read what the engine is doing, and make slow graphs fast.

- **CU-370** (300) [Reading ComfyUI's console during a run](300/CU-370-reading-the-console/lesson.md). Which backend, which format, how much loaded, how fast, and why the progress bar may understate the wait. It's all printed. Learn to read it. Needs CU-102.
- **CU-371** (300) [Launch flags that matter](300/CU-371-launch-flags-that-matter/lesson.md). There are over a hundred flags. A handful decide your memory, your cache and your attention. Read what each really does in the source, and leave the rest alone. Needs CU-402.
- **CU-305** (300) [VRAM budget math: weights, activations, caches](300/CU-305-vram-budget-math/lesson.md). Three different things want room on your card. Each has its own formula, and only one of them is the size of the file. Needs CU-210.
- **CU-372** (300) [Budgeting VRAM before you press Queue](300/CU-372-budgeting-vram-before-queue/lesson.md). Read a file's parameter count from its header without loading it, add up the parts, and know before you queue whether a graph will fit. Needs CU-305.
- **CU-402** (400) [Memory management: who gets the GPU](400/CU-402-memory-management/lesson.md). Before each sampler run, ComfyUI budgets VRAM and evicts what it must. Replay the arithmetic and read your own logs. Needs CU-220.
- **CU-304** (300) [Why attention is O(n^2), and what Flash and Sage change](300/CU-304-flash-attention-memory/lesson.md). Score every token against every token and the table grows with the square. Slicing and online softmax hold less of it at once, with the same answer. Low precision is a different bargain. Needs CU-301.
- **CU-211** (200) [Quantization: int8, FP8, 4-bit and GGUF](200/CU-211-quantization/lesson.md). Plant a few large weights and watch int8 with one scale fall apart, while a scale per 32 weights and FP8 shrug it off. Needs CU-210.
- **CU-374** (300) [Quantized files: fp8, GGUF, and how loaders treat them](300/CU-374-quantized-files-fp8-gguf-and-loaders/lesson.md). Same model, three kinds of file, three different roads through the loader. And why you merge first and quantize after, measured. Needs CU-211.
- **CU-308** (300) [Speed: distillation, caching, compile, fewer steps](300/CU-308-speed-tricks/lesson.md). Four levers, four different mechanisms. Count what each one saves, and what it asks in return. Needs CU-203.
- **CU-373** (300) [What really makes a graph faster](300/CU-373-what-really-makes-a-graph-faster/lesson.md). Distilled models, cached conditioning, tiled VAE, smaller latents: count what each buys, then keep only what you measured on your own graph. Needs CU-308.
- **CU-311** (300) [Mixed precision: where accumulation hides](300/CU-311-mixed-precision-accumulation/lesson.md). Add a small number to a big one in fp16 and nothing happens. Watch a running sum stall at 0.25, and find the same sum inside every matmul. Needs CU-210.
- **CU-416** (400) [Profiling memory and time on a GPU (with a CPU model of it)](400/CU-416-profiling-memory-and-time-on-a-gpu-with-/lesson.md). A peak isn't the sum of your tensors, and the slowest thing isn't always where you look. Learn to read both before you change anything. Needs CU-305.
- **CU-410** (400) [Quantization error propagation through layers](400/CU-410-quantization-error-propagation/lesson.md). Round every layer's weights and measure what reaches the end: with depth it grows more like a square root than an avalanche, until layers start to amplify. Needs CU-211.

## Reading and vetting node packs

Find what a pack really does before it runs on your machine: code, licences and risks.

- **CU-516** (400) [History 16: What open means: weights, licences and the ecosystem](400/CU-516-what-open-means-weights-licences-/lesson.md). Open code, open weights, open data and an open licence are four different things. Sort out which one you have, because one graph can carry several licences.
- **CU-380** (300) [Finding out what a pack really does before you install it](300/CU-380-what-a-pack-really-does/lesson.md). A custom node is Python that runs with your rights as soon as ComfyUI starts. Learn to read one first: the order to read files, what runs when, and what to write down. Needs CU-430.
- **CU-381** (300) [What scans can and can't tell you](300/CU-381-what-scans-can-and-cant-tell-you/lesson.md). A scanner shouts at a picture decoder and says nothing about a harmful line built at run time. Learn what a hit means, what silence means, and why neither is a verdict. Needs CU-380.
- **CU-382** (300) [Same name, different maths](300/CU-382-same-name-different-maths/lesson.md). Two nodes called NAG differ by one on the same slider. Blue noise isn't always blue. Our reading of packs' source found names you can't trust, so read the formula. Needs CU-208.
- **CU-383** (300) [Licences in practice: AGPL, GPL, MIT, OpenRAIL](300/CU-383-licences-in-practice/lesson.md). Most of the time nothing is triggered until you hand over a copy or put it on a website. Read what four real licences ask in five ordinary cases. Not legal advice. Needs CU-516.
- **CU-384** (300) [Weights that can run code: pickle, safetensors, torch.load](300/CU-384-weights-that-can-run-code/lesson.md). A .ckpt can hold a program that runs when you load it. See it happen, safely, and learn what stops it in ComfyUI, and what doesn't in a pack. Needs CU-380.
- **CU-385** (300) [How to pick between packs, and when core already does it](300/CU-385-choosing-between-packs/lesson.md). Most searches for a pack should end in core. A short ladder: does core do it, what does the gap really need, is the code what you think, and can you live with its side effects? Needs CU-380.
- **CU-450** (400) [Installing without breaking anything](400/CU-450-installing-without-breaking-anything/lesson.md). Venvs, constraints, dry runs, a container with no way out, and a smoke test. How to try a pack so that a bad one costs you nothing. Needs CU-380.

## The API, apps and agents

Drive ComfyUI from code, put a form on a graph, and let an agent queue work safely.

- **CU-224** (200) [The API: queue, watch, fetch](200/CU-224-the-api/lesson.md). Everything the page does, a script can do: POST a prompt, read events from a websocket, fetch the files. Needs CU-110, CU-220.
- **CU-460** (400) [Queue a graph from a script](400/CU-460-queue-from-a-script/lesson.md). Five steps and a short script: set values, post, wait, check the status, and download the right file, with the traps each step avoids. Needs CU-224.
- **CU-461** (400) [Progress and errors over the websocket](400/CU-461-progress-and-errors-on-the-websocket/lesson.md). Every message a job sends, who receives it, and the one message that means stop waiting, from captures of the real executor. Needs CU-224, CU-460.
- **CU-462** (400) [From a UI workflow to API format, and setting values by node id](400/CU-462-ui-workflow-to-api/lesson.md). Let the editor export it, then change values with guard rails. Find out why widgets_values shifts by one, and why a mistyped input name fails silently. Needs CU-110, CU-224.
- **CU-463** (400) [Running ComfyUI safely on a network](400/CU-463-running-on-a-network/lesson.md). ComfyUI has no login. What --listen, CORS, TLS and --multi-user each really do, tested against the real middleware. Needs CU-224.
- **CU-223** (200) [App Mode: a graph with a form on top](200/CU-223-app-mode/lesson.md). App Mode shows chosen inputs and outputs of a workflow as a simple form. The graph underneath does not change. Needs CU-110, CU-220.
- **CU-405** (400) [Agents on ComfyUI: tools, verification, side-effect safety](400/CU-405-agents-on-comfyui/lesson.md). The model proposes, plain code checks, and limits live outside the model. Before, gate, and after. Needs CU-102, CU-224.
- **CU-406** (400) [Scaling: sharding, batching and serving](400/CU-406-scaling-and-serving/lesson.md). One process runs one job at a time. Batches, busy time, and routing that keeps models in place. Needs CU-305.
- **CU-415** (400) [Reproducibility and provenance: hashing graphs and seeds](400/CU-415-reproducibility-and-provenance/lesson.md). A seed fixes one input. Hash the graph, the files and the versions, and find out why two runs differ. Needs CU-105, CU-405.
- **CU-517** (400) [History 17: Studios and agents: when models became pipelines](400/CU-517-studios-and-agents/lesson.md). From one model call to pipelines of graphs driven by programs, and the ledger that keeps a pipeline honest. Needs CU-405.

## Inside the models

Attention, transformers, positions and flows: the machinery under every node.

- **CU-301** (300) [Attention from scratch](300/CU-301-attention-from-scratch/lesson.md). Scaled dot-product attention in six lines, why the square root of d is there, and how a prompt reaches a pixel. Needs CU-103, CU-104.
- **CU-302** (300) [Multi-head, GQA and RoPE](300/CU-302-heads-gqa-rope/lesson.md). Split attention into heads, share keys to save memory, and rotate by position so only the gap between tokens counts. Needs CU-301.
- **CU-303** (300) [DiT and MM-DiT blocks](300/CU-303-dit-and-mmdit/lesson.md). How a transformer replaces the U-Net: patches become tokens, a time vector scales each block, text and image share attention. Needs CU-301.
- **CU-309** (300) [Positional encodings in 2D and 3D](300/CU-309-positional-encodings-2d-3d/lesson.md). Attention can't see order. Sine tables added to tokens and rotations from coordinates are how a token learns where it is. Needs CU-302.
- **CU-313** (300) [Mixture of experts routing](300/CU-313-mixture-of-experts-routing/lesson.md). A gate picks a few feed-forward networks per token, so storage grows with experts while work grows only with how many each token uses. Needs CU-301.
- **CU-312** (300) [KV cache and autoregressive decoding](300/CU-312-kv-cache-autoregressive-decoding/lesson.md). Old tokens don't change, so keep their keys and values. The same answer for far less work, paid for in memory. Needs CU-301.
- **CU-317** (300) [Sparse and windowed attention](300/CU-317-sparse-windowed-attention/lesson.md). Limit who attends to whom. Cost falls from tokens squared to tokens times a constant, and reach is what you pay with. Needs CU-304.

## Measuring and research

Evaluate outputs honestly, read papers, and keep results you can reproduce.

- **CU-404** (400) [Evaluating outputs: metrics, checks and their limits](400/CU-404-evaluating-outputs/lesson.md). What PSNR, SSIM and FID compare, what each misses, and how to test them on a pair where a score means something. Needs CU-106.
- **CU-413** (400) [Prompt adherence evaluation](400/CU-413-prompt-adherence-evaluation/lesson.md). Did it listen? What a CLIP-style score says, what a checklist says, and why the two pictures here tie on a total and differ on everything else. Needs CU-404.
- **CU-407** (400) [Reading a generative-AI paper in 20 minutes](400/CU-407-reading-papers/lesson.md). Claim, baseline, measure, spread. A way to read fast, and three ways a result looks better than it is.
- **CU-470** (400) [Comparing two samplers fairly](400/CU-470-comparing-samplers-fairly/lesson.md). One render can name either winner. The same seeds, enough of them, a measure chosen first, and cost in model calls. Needs CU-205, CU-404.

## How we got here

From GANs to this year's video models, told by the idea each era added.

- **CU-501** (200) [History 1: GANs, the adversarial game (2014)](200/CU-501-history-1-gans-adversarial-game-2/lesson.md). Two networks play a game whose exact answer is a density ratio and a value of minus log 4. Then a real GAN trained on a CPU shows how far training gets from the theory. Needs CU-101.
- **CU-502** (200) [History 2: Variational autoencoders and the latent idea (2013)](200/CU-502-history-2-variational-autoencoder/lesson.md). The 2013 paper in three checks on a model with a known answer: the exact gap in the lower bound, a gradient estimator with far lower variance, and an encoder that learns the posterior. Needs CU-101.
- **CU-503** (200) [History 3: Pixel by pixel, autoregressive image models](200/CU-503-history-3-autoregressive-image-mo/lesson.md). An image as a product of conditionals: check the chain rule exactly, watch a causal mask make the future invisible, and count what sampling one pixel at a time costs. Needs CU-101.
- **CU-504** (300) [History 4: StyleGAN and style modulation](300/CU-504-history-4-stylegan-style-modulati/lesson.md). How a style vector controls a feature map in StyleGAN, AdaIN then weight demodulation, checked with numbers, and where the same scale-and-shift idea lives in ComfyUI today. Needs CU-501.
- **CU-505** (200) [History 5: CLIP and contrastive learning](200/CU-505-history-5-clip-and-contrastive-le/lesson.md). CLIP's loss as a table of similarities: what chance scores, how the temperature caps confidence, why more captions help, and zero-shot use on pairs never seen in training. Needs CU-104.
- **CU-506** (200) [History 6: Denoising diffusion arrives (DDPM, 2020)](200/CU-506-history-6-denoising-diffusion-arr/lesson.md). The DDPM paper checked against exact answers: the posterior of a forward step, the weights the simplified loss drops, and why the two reverse variances barely differ. Plus which one ComfyUI's ddpm sampler uses. Needs CU-202.
- **CU-507** (200) [History 7: Latent diffusion and Stable Diffusion (2022)](200/CU-507-latent-diffusion-stable-diffusion/lesson.md). What a factor-8 latent grid does to the cost of a layer, counted by PyTorch's FLOP counter, what the paper measured end to end, and the price it admits. Plus the three parts of a checkpoint in ComfyUI. Needs CU-201.
- **CU-508** (200) [History 8: Adapters era: LoRA and ControlNet](200/CU-508-history-8-adapters-era-lora-contr/lesson.md). What a rank can and cannot follow, measured against the best possible matrix, and how LoRA and ControlNet both start as the base model and then begin to learn. With the matching ComfyUI code. Needs CU-212.
- **CU-509** (300) [History 9: Transformers replace U-Nets: DiT and rectified flow](300/CU-509-transformers-replace-unets-dit-re/lesson.md). DiT swapped the network and rectified flow swapped the path. One step from noise lands every sample on the mean, and what fixes that is a second round of training, not the straight line. Needs CU-303.
- **CU-510** (300) [History 10: From frames to space-time: the road to modern video models](300/CU-510-history-10-frames-to-space-time/lesson.md). Time is added on, then compressed, then attended to all at once. Causal describes the VAE and not the sampler, and it is where the 4k + 1 frame grid comes from. Needs CU-215.
- **CU-514** (300) [History 14: The speed era: LCM, turbo and distillation](300/CU-514-history-14-speed-era-lcm-turbo-di/lesson.md). A student learns where the slow path ends. From an exact teacher: 1.39 for Euler at one call against 0.14 for the student, and what happens when the data isn't what it copied. Needs CU-308.
- **CU-515** (300) [History 15: The size era: FP8, GGUF and 4-bit formats arrive](300/CU-515-history-15-size-era-fp8-gguf-4bit/lesson.md). Each format answers one question: what do the weights share? The same test across all of them shows why int4 with one scale is ruined, and why fp8 hardly notices an outlier. Needs CU-211.
