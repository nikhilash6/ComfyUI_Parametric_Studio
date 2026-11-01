# ComfyUniversity course catalogue

83 lessons in 18 tracks. 47 are checked by hand and 36 are still labelled Draft. Every lesson has a CPU lab with stored output and a quiz. Rebuild with `python studio/university/build.py --labs`.

## Your first graph

Press Queue and know what happened. Nodes, wires, seeds, files, and how to read a workflow.

- **CU-100** (100) [Your first graph, with no model at all](100/CU-100-first-graph-no-model/lesson.md). Three nodes, no model, no GPU. See what a node, a wire and an output node are by making them work in under a second.
- **CU-101** (100) [What generative AI actually is](100/CU-101-what-is-generative-ai/lesson.md). Learn a distribution, then sample from it. Three models on one dataset show the difference between learning and memorising.
- **CU-102** (100) [Anatomy of a ComfyUI graph](100/CU-102-anatomy-of-a-graph/lesson.md). A small engine that follows ComfyUI's rules shows which nodes run, which come from the cache, and why changing the checkpoint re-runs six nodes, not seven.
- **CU-106** (100) [Your first image: checkpoint, sampler, VAE](100/CU-106-first-image-walkthrough/lesson.md). Follow one prompt through checkpoint, text encoder, sampler and VAE: the shape of every hand-off, and the 20 sigma values that the sampler walks down, checked against the ComfyUI documentation. Needs CU-102.
- **CU-110** (100) [Reading a workflow JSON like a map](100/CU-110-reading-workflow-json-like-a-map/lesson.md). The same seven-node graph in the editor's save format and the server's API format, read with one recipe: follow the wire back, check the wiring, and translate between the two. Needs CU-102.
- **CU-103** (100) [Pixels, tensors and shapes](100/CU-103-pixels-tensors-shapes/lesson.md). Why IMAGE is [B, H, W, C] and LATENT is [B, C, H/8, W/8], what the VAE nodes do to cross between them, and where truncating 8-bit levels bites.
- **CU-105** (100) [Seeds, noise and determinism](100/CU-105-seeds-and-noise/lesson.md). A seed is the starting noise and nothing more. A toy sampler with an exact denoiser shows what that does and does not fix when you change steps, samplers or hardware.
- **CU-104** (100) [Prompts become numbers: tokens and embeddings](100/CU-104-prompts-to-embeddings/lesson.md). Follow a prompt to the tensor the sampler gets: byte-pair splitting, an embedding table that does not know its neighbours, and causal attention that does.
- **CU-107** (100) [Models on disk: safetensors and families](100/CU-107-models-on-disk/lesson.md). Build and damage a safetensors file by hand, watch a pickle run code, and see how ComfyUI tells SD 1.x from SDXL by reading three shapes from a header.
- **CU-109** (100) [Resolution, aspect ratio and the pixel budget](100/CU-109-resolution-aspect-ratio-pixel-budget/lesson.md). From an aspect ratio and a pixel budget to a size the VAE accepts: the square-root formula, what ComfyUI's size nodes round to, and how fast attention and VAE costs grow. Needs CU-103.
- **CU-111** (100) [Files and formats: PNG metadata, MP4, WAV, safetensors](100/CU-111-files-formats/lesson.md). Build a PNG that carries a workflow, a WAV file and an MP4-style box stream by hand, and see why a reader walks chunks and boxes, why a flipped bit is caught, and what dropping metadata really removes.

## Samplers, schedulers and CFG

The loop at the heart of ComfyUI, the choices it exposes, and what those choices really change.

- **CU-202** (200) [Diffusion from first principles](200/CU-202-diffusion-from-first-principles/lesson.md). Destroy data with noise on purpose, learn to undo one step, and train a real model on a CPU. Needs CU-101, CU-105.
- **CU-205** (200) [Samplers are ODE solvers](200/CU-205-samplers-as-ode-solvers/lesson.md). Euler, Heun and DPM++ 2M written in five lines each, then measured against the exact answer. Needs CU-203.
- **CU-206** (200) [Sigma schedules: where the steps go](200/CU-206-sigma-schedules/lesson.md). The scheduler chooses which noise levels the solver visits. Same model, same steps, different error. Needs CU-205.
- **CU-207** (200) [Ancestral and SDE samplers: adding noise back](200/CU-207-ancestral-and-sde-samplers/lesson.md). Why a sampler that keeps injecting noise never settles on one image, and when that helps. Needs CU-205.

## Noise and latent maths

What a latent is, what noise is doing to it, and the numbers that keep images from breaking.

- **CU-201** (200) [Latent space and the VAE](200/CU-201-latent-space-and-the-vae/lesson.md). Train a tiny VAE on a CPU, and see why the midpoint of two latents is a picture while the midpoint of two images is a ghost. Needs CU-101, CU-103.
- **CU-203** (200) [Score matching, Tweedie and the SDE view](200/CU-203-score-matching-and-sdes/lesson.md). Why predicting noise is the same as learning the gradient of the data density, proved numerically. Needs CU-202.
- **CU-204** (200) [Flow matching and rectified flow](200/CU-204-flow-matching-and-rectified-flow/lesson.md). Each training pair flies straight. The field you actually integrate does not, and that is the whole subject. Needs CU-202, CU-203.
- **CU-314** (300) [Flow-matching losses and velocity targets](300/CU-314-flow-matching-losses-and-velocity-target/lesson.md). Learn how to compute the exact velocity field that guides your diffusion model from noise to data. *Draft.*
- **CU-210** (200) [Precision: fp32, fp16, bf16, fp8](200/CU-210-precision/lesson.md). Where rounding bites: small LoRA deltas vanish, sums stall, and fp16 overflows at 65,504. Needs CU-103.
- **CU-229** (200) [Color spaces, gamma and image math](200/CU-229-color-and-image-math/lesson.md). Half black and half white is not 0.5 in light: what blending and shrinking do to sRGB codes, and why SaveImage truncates. Needs CU-103.

## Guidance

CFG and everything built to fix it: rescale, CFG++, PAG, SAG, Perp-Neg, and embedded guidance.

- **CU-208** (200) [Guidance: CFG and what it really does](200/CU-208-guidance-cfg/lesson.md). One line of arithmetic, and it does not sample the distribution people usually say it does. Needs CU-205.
- **CU-209** (200) [Negative prompts and cfg 1.0](200/CU-209-negative-prompts/lesson.md). A negative prompt is not a subtraction of concepts. It replaces the unconditional branch, and at cfg 1 it does nothing at all. Needs CU-208.

## Conditioning

How a prompt reaches the model, and how to mix, time and place several of them.

- **CU-306** (300) [Text encoders: CLIP, T5 and LLM encoders](300/CU-306-text-encoders-deep/lesson.md). What each encoder gives the model and what it costs. *Draft.* Needs CU-104.
- **CU-310** (300) [Cross-attention versus joint attention](300/CU-310-cross-attention-versus-joint-attention/lesson.md). Discover how ComfyUI's attention mechanisms differ by exploring the mathematical distinction between conditioning on external prompts and self-attending within  *Draft.* Needs CU-301.

## ControlNet, depth and inpainting

Steer shape, depth and regions with a picture, and keep the rest of the image.

- **CU-214** (200) [Conditioning: img2img, inpaint, ControlNet, IP-Adapter](200/CU-214-conditioning-controlnet-ip/lesson.md). Every way of telling the model more than a prompt, placed at the point where it enters: what denoise really sets, what a ControlNet window covers, and why zero is not the same as absent. Needs CU-106.
- **CU-219** (200) [Depth and edge preprocessors: Sobel by hand](200/CU-219-depth-edge-preprocessors-sobel-by/lesson.md). Compute Sobel by hand, see why Canny blurs first and what its thresholds are measured in, and learn how a depth map becomes a grey hint. Needs CU-103.
- **CU-213** (200) [Inpainting masks and edge blending](200/CU-213-inpainting-masks-edge-blending/lesson.md). The sampler sees your mask on a grid eight times coarser than the picture: where a 3-pixel line vanishes, what grow and feather really do, and how the per-step blend works. Needs CU-201, CU-214.

## LoRAs and training

What a LoRA is as maths, how to load it right, and how to train one with core nodes.

- **CU-212** (200) [LoRA: low-rank adaptation](200/CU-212-lora-low-rank/lesson.md). Why two skinny matrices can change a giant one, when they cannot, and what rounding does to a small update. Needs CU-210.
- **CU-412** (400) [Dataset curation and captioning for training](400/CU-412-dataset-curation-and-captioning-for-trai/lesson.md). Learn how to transform raw images into high-quality training data by mastering precise captioning and dataset balancing techniques. *Draft.* Needs CU-402.
- **CU-403** (400) [Model merging: weighted, SLERP, task arithmetic](400/CU-403-model-merging-math/lesson.md). Why averaging weights can work and when it fails. *Draft.* Needs CU-212.
- **CU-409** (400) [Distillation math: teacher, student, consistency](400/CU-409-distillation-math-teacher-student/lesson.md). Learn how to compress a complex diffusion model into a fast, few-step generator by mastering the mathematical bridge between teacher guidance and student consis *Draft.* Needs CU-308.

## Video: LTX-2.5, MiniMax H3, Wan

Frames, temporal latents, and the three models this studio runs, node by node.

- **CU-215** (200) [Video basics: frames, fps and temporal latents](200/CU-215-video-basics/lesson.md). Why five seconds at 24 fps comes back as 117 frames, how a video VAE counts, and how attention cost climbs with duration. Needs CU-201.
- **CU-218** (200) [Seeds, batches and variations in video](200/CU-218-seeds-batches-variations-video/lesson.md). The seed fills one block of noise in memory order: why a different frame count is a different video, why batch items can be redone alone, and why a blended noise must be rescaled. Needs CU-105, CU-215.
- **CU-217** (200) [Upscaling and tiling math](200/CU-217-upscaling-tiling-math/lesson.md). How ComfyUI cuts an image into tiles, why a ramp hides the seam, and why tiled decoding saves memory but costs 3.77 times the work. Needs CU-201.
- **CU-315** (300) [Temporal consistency and optical flow basics](300/CU-315-temporal-consistency-optical-flow-basics/lesson.md). Learn how to keep your AI videos from jittering by mastering the math behind motion estimation. *Draft.* Needs CU-215.
- **CU-316** (300) [Video VAEs and receptive fields](300/CU-316-video-vaes-and-receptive-fields/lesson.md). Discover how Video VAEs compress temporal dimensions and why understanding receptive fields is key to controlling motion artifacts. *Draft.* Needs CU-215, CU-201.
- **CU-411** (400) [Evaluating video: a flicker metric](400/CU-411-evaluating-video-flicker-metric/lesson.md). Learn to quantify visual stability by calculating the temporal variance of pixel intensities to detect flicker in generated video sequences. *Draft.* Needs CU-404.

## Audio and Music 3

Waveforms, spectrograms, audio latents, and making songs with MiniMax Music 3.

- **CU-216** (200) [Audio and music basics: waveforms to spectrograms](200/CU-216-audio-basics/lesson.md). Why a 6 kHz tone sampled at 10 kHz is heard at 4 kHz, what a longer frame buys and costs, and how ComfyUI turns seconds into audio latents.
- **CU-511** (300) [History 11: Audio models: WaveNet to autoregressive music to diffusion music](300/CU-511-history-11-audio-models/lesson.md). Trace the evolution of AI audio from sample-by-sample prediction to holistic diffusion synthesis. *Draft.* Needs CU-216.

## 3D

Meshes, splats and NeRFs, how images become 3D, and the core nodes for it.

- **CU-307** (300) [3D generation: meshes, SDFs, voxels and Gaussian splats](300/CU-307-three-d-representations/lesson.md). The shapes a model can output and how they convert. *Draft.* Needs CU-201.
- **CU-513** (300) [History 13: Seeing in 3D: NeRF, Gaussian splats and structured latents](300/CU-513-seeing-in-3d-nerf-gaussian-splats/lesson.md). Explore how modern 3D generation moves from implicit fields to explicit particles and structured latent spaces to render photorealistic scenes. *Draft.* Needs CU-307.

## Writing custom nodes

From your first V3 class to lazy inputs, caching rules, expansion and front-end extensions.

- **CU-401** (400) [Writing a custom node with the V3 API](400/CU-401-custom-nodes-v3/lesson.md). A class with a schema and an execute method. The engine calls your node without making an instance, and that changes how you write it. Needs CU-220, CU-221.
- **CU-222** (200) [Sub-graphs and node expansion](200/CU-222-subgraphs-and-expansion/lesson.md). A sub-graph is a front-end idea that the server never sees. Node expansion is a server idea that the front-end never sees. Needs CU-220.

## Debugging graphs

Read validation errors, black images and NaNs, shape mismatches, and find the cause fast.

- **CU-220** (200) [The execution model: what runs, and in what order](200/CU-220-execution-model/lesson.md). ComfyUI starts from the output nodes and works backwards. Build its scheduler in 60 lines and watch a lazy input change the order. Needs CU-102.
- **CU-221** (200) [Caching: why changing the seed does not reload the model](200/CU-221-caching/lesson.md). Each node gets a key built from its whole ancestry. Change one input and only what lies downstream runs again. Needs CU-220.

## VRAM and performance

Budget memory, read what the engine is doing, and make slow graphs fast.

- **CU-305** (300) [VRAM budget math: weights, activations, caches](300/CU-305-vram-budget-math/lesson.md). Predicting whether it fits before you press Queue. *Draft.* Needs CU-210.
- **CU-402** (400) [Memory management: who gets the GPU](400/CU-402-memory-management/lesson.md). Before each sampler run, ComfyUI budgets VRAM and evicts what it must. Replay the arithmetic and read your own logs. Needs CU-220.
- **CU-304** (300) [Why attention is O(n^2) and how Flash/Sage fix the memory](300/CU-304-flash-attention-memory/lesson.md). Tiling, online softmax and the memory wall. *Draft.* Needs CU-301.
- **CU-211** (200) [Quantization: int8, FP8, 4-bit and GGUF](200/CU-211-quantization/lesson.md). Plant a few large weights and watch int8 with one scale fall apart, while a scale per 32 weights and FP8 shrug it off. Needs CU-210.
- **CU-308** (300) [Speed: distillation, caching, compile, fewer steps](300/CU-308-speed-tricks/lesson.md). Where the seconds go and how to get them back. *Draft.*
- **CU-311** (300) [Mixed precision: where accumulation hides](300/CU-311-mixed-precision-accumulation/lesson.md). Discover why your gradients vanish or explode when mixing float16 and float32, and how ComfyUI's scheduler hides the accumulation trap. *Draft.* Needs CU-210.
- **CU-416** (400) [Profiling memory and time on a GPU (with a CPU model of it)](400/CU-416-profiling-memory-and-time-on-a-gpu-with-/lesson.md). Learn to predict GPU memory bottlenecks by simulating tensor lifecycles and operation costs on your CPU. *Draft.* Needs CU-305.
- **CU-410** (400) [Quantization error propagation through layers](400/CU-410-quantization-error-propagation/lesson.md). Discover how tiny rounding errors in low-bit weights can snowball into significant output drift as they pass through deep neural networks. *Draft.* Needs CU-211.

## Reading and vetting node packs

Find what a pack really does before it runs on your machine: code, licences and risks.

- **CU-516** (400) [History 16: What open means: weights, licences and the ecosystem](400/CU-516-what-open-means-weights-licences-/lesson.md). Explore the legal and technical boundaries of open-source AI by dissecting how model weights, licenses, and community contributions shape the ComfyUI ecosystem. *Draft.*

## The API, apps and agents

Drive ComfyUI from code, put a form on a graph, and let an agent queue work safely.

- **CU-224** (200) [The API: queue, watch, fetch](200/CU-224-the-api/lesson.md). Everything the page does, a script can do: POST a prompt, read events from a websocket, fetch the files. Needs CU-109, CU-220.
- **CU-223** (200) [App Mode: a graph with a form on top](200/CU-223-app-mode/lesson.md). App Mode shows chosen inputs and outputs of a workflow as a simple form. The graph underneath does not change. Needs CU-109, CU-220.
- **CU-405** (400) [Agents on ComfyUI: tools, verification, side-effect safety](400/CU-405-agents-on-comfyui/lesson.md). Letting a model drive the graph without letting it break things. *Draft.* Needs CU-102, CU-401.
- **CU-406** (400) [Scaling: sharding, batching and serving](400/CU-406-scaling-and-serving/lesson.md). From one GPU to many, and what throughput really means. *Draft.* Needs CU-305.
- **CU-415** (400) [Reproducibility and provenance: hashing graphs and seeds](400/CU-415-reproducibility-and-provenance/lesson.md). Learn how to cryptographically fingerprint your ComfyUI workflows and seeds to ensure bit-perfect reproducibility across different machines and sessions. *Draft.* Needs CU-105, CU-405.
- **CU-517** (400) [History 17: Studios and agents: when models became pipelines](400/CU-517-studios-and-agents/lesson.md). Discover how ComfyUI transforms static model calls into dynamic, agent-driven pipelines that orchestrate complex creative workflows. *Draft.* Needs CU-405.

## Inside the models

Attention, transformers, positions and flows: the machinery under every node.

- **CU-301** (300) [Attention from scratch](300/CU-301-attention-from-scratch/lesson.md). Scaled dot-product attention in six lines, why the square root of d is there, and how a prompt reaches a pixel. Needs CU-103, CU-104.
- **CU-302** (300) [Multi-head, GQA and RoPE](300/CU-302-heads-gqa-rope/lesson.md). Splitting attention, sharing keys, and rotating positions. *Draft.* Needs CU-301.
- **CU-303** (300) [DiT and MM-DiT blocks](300/CU-303-dit-and-mmdit/lesson.md). How a transformer replaces the U-Net: patches, adaLN, joint text-image attention. *Draft.* Needs CU-301.
- **CU-309** (300) [Positional encodings in 2D and 3D](300/CU-309-positional-encodings-2d-3d/lesson.md). Discover how we inject spatial awareness into neural networks by transforming grid coordinates into rich frequency signals. *Draft.* Needs CU-302.
- **CU-313** (300) [Mixture of experts routing](300/CU-313-mixture-of-experts-routing/lesson.md). Discover how ComfyUI's advanced diffusion models intelligently select the right expert for each token to boost efficiency and quality. *Draft.* Needs CU-301.
- **CU-312** (300) [KV cache and autoregressive decoding](300/CU-312-kv-cache-autoregressive-decoding/lesson.md). Discover how ComfyUI's text encoders and diffusion schedulers leverage caching to speed up sequential generation without sacrificing quality. *Draft.* Needs CU-301.
- **CU-317** (300) [Sparse and windowed attention](300/CU-317-sparse-windowed-attention/lesson.md). Discover how limiting attention to local windows and sparse patterns drastically reduces computational cost while preserving spatial context. *Draft.* Needs CU-304.

## Measuring and research

Evaluate outputs honestly, read papers, and keep results you can reproduce.

- **CU-404** (400) [Evaluating outputs: metrics, checks and their limits](400/CU-404-evaluating-outputs/lesson.md). What PSNR, SSIM-style and embedding scores tell you, and what they cannot. *Draft.* Needs CU-106.
- **CU-413** (400) [Prompt adherence evaluation](400/CU-413-prompt-adherence-evaluation/lesson.md). Learn to quantify how well your generated images actually match the text prompts using deterministic CPU-based metrics. *Draft.* Needs CU-404.
- **CU-407** (400) [Reading a generative-AI paper in 20 minutes](400/CU-407-reading-papers/lesson.md). A method for extracting claims, assumptions and what to check. *Draft.*

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
- **CU-509** (300) [History 9: Transformers replace U-Nets: DiT and rectified flow](300/CU-509-transformers-replace-unets-dit-re/lesson.md). Discover how Diffusion Transformers (DiT) and rectified flow are reshaping the landscape of generative AI by moving away from traditional U-Net architectures. *Draft.* Needs CU-303.
- **CU-510** (300) [History 10: From frames to space-time: the road to modern video models](300/CU-510-history-10-frames-to-space-time/lesson.md). Discover how video generation evolved from static image sequences to coherent space-time volumes. *Draft.* Needs CU-215.
- **CU-514** (300) [History 14: The speed era: LCM, turbo and distillation](300/CU-514-history-14-speed-era-lcm-turbo-di/lesson.md). Discover how we tricked diffusion models into thinking they were already finished, slashing generation time from minutes to seconds. *Draft.* Needs CU-308.
- **CU-515** (300) [History 15: The size era: FP8, GGUF and 4-bit formats arrive](300/CU-515-history-15-size-era-fp8-gguf-4bit/lesson.md). Discover how quantization formats like FP8 and GGUF revolutionized local AI by shrinking model sizes without sacrificing too much quality. *Draft.* Needs CU-211.
