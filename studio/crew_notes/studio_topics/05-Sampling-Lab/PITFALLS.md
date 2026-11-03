# Sampling Lab: pitfalls

These Sampling Lab notes describe the data as of 2026-11-01. [run: studio/sampling_lab/atlas.json]

## What the Sampling Lab bench does not prove

The Sampling Lab bench is a toy problem, not a proof that one method is better. The script says it tells nothing about pictures, and the page says a low number does not mean a better picture. A one-dimensional Gaussian is far easier than a real model. Do not quote bench order as a quality ranking. [code: scripts/build_sampling_measures.py:10, studio/web/samplinglab_bench.js:104] [run: studio/sampling_lab/measures.json]

Sampling Lab bench results depend on the setup, not only the method. dpm_fast at 20 steps has error 0.0021 on eps and 0.1248 on flow, and the two columns differ in schedule too, karras against simple. uni_pc and uni_pc_bh2 run in float32 where the rest run in float64, so their small errors may be near that precision. [run: studio/sampling_lab/measures.json] [code: scripts/build_sampling_measures.py:101, scripts/build_sampling_measures.py:103] [inference]

Sampling Lab bench error need not fall as steps rise. On flow, dpmpp_2m has error 0.0046 at 10 steps and 0.0278 at 20, with a slope of +0.71. On eps, dpm_adaptive ignores the steps setting, with 18 calls and error 0.0282 at every step count, so its slope means little. heunpp2 costs 57 calls at 20 steps and still has error 0.0641, near euler's 0.0768. [run: studio/sampling_lab/measures.json]

## What Sampling Lab renders do not prove

Sampling Lab renders are one seed and one prompt. They show a difference and do not prove a method is better, and the page says so next to them. Times are coarse, polled every 1.5 seconds, and the first render of each model includes loading it, such as 66 seconds for the first SD 1.5 render. [code: studio/web/samplinglab_bench.js:143] [run: studio/sampling_lab/renders.json]

No pack method is proven by a Sampling Lab render. Pack Lab attempted 6 and rendered 0, because the sandbox's control render failed too, with VAEDecode hitting maximum recursion depth. The failure was in the sandbox, so this says nothing against the methods themselves. So 537 methods outside core are unproven. [run: studio/sampling_lab/renders.json, studio/sampling_lab/atlas.json] [test: tests/test_sampling_lab.py] [inference]

Being in core does not make a Sampling Lab method proven. 139 of the 183 core methods have no render and are described from the code. "Live" is also a record of the machine the atlas was built on, so a fresh install may not have those 13 packs. [run: studio/sampling_lab/atlas.json] [code: studio/web/samplinglab_logic.js:205-210] [inference]

## Traps the Sampling Lab atlas found

The Sampling Lab lists 77 surprises in atlas.json: 5 seen in renders and 72 found by readers of the source, 8 in each of 9 groups. The read ones are from code and were not run unless they say so. Some say "inference" or "read, not run" in their own text. Treat them as a reader's finding and check the cited line. [run: studio/sampling_lab/atlas.json] [code: studio/web/samplinglab.js:136]

Sampling Lab rendered trap: the ddim sampler name gives the same pixels as euler on the same seed and graph. Core maps the name to Euler, and only the inpaint noise option differs. The two renders have the same hash, and the test holds it. [run: studio/sampling_lab/renders.json] [test: tests/test_sampling_lab.py]

Sampling Lab rendered trap: CFGNorm at strength 1 with CFG 14 washed an SDXL render to pale grey, contrast 18.9 against 71.0 for plain CFG 14 on this seed. Rescale (57.1) and APG (60.1) at the same CFG stayed usable. [run: studio/sampling_lab/renders.json] [test: tests/test_sampling_lab.py]

Sampling Lab rendered trap: linear_quadratic with dpmpp_2m smeared an SDXL render at 20 steps, with rainbow speckle. Its last non-zero sigma there is 2.67, against 0.03 for karras, so the last step jumps a long way to zero. [run: studio/sampling_lab/renders.json, studio/sampling_lab/measures.json] [test: tests/test_sampling_lab.py]

Sampling Lab rendered trap: ddim_uniform starts at sigma 11.03 at 20 steps on SD and SDXL, where the others start at 14.61, and it rendered brighter with a different layout. Karras at 20 steps broke SD 3.5 Medium with Euler (brown and unfinished), while simple, beta and kl_optimal held on the same seed. [run: studio/sampling_lab/renders.json, studio/sampling_lab/measures.json]

Sampling Lab read trap, core samplers: per the atlas, an unknown sampler name given to KSampler silently becomes euler, and KSampler alone discards the penultimate sigma for dpm_2, dpm_2_ancestral, uni_pc and uni_pc_bh2. dpm_fast and dpm_adaptive throw away the schedule, using only its ends, and stop with no denoise to zero. Read, not run here. [docs: studio/sampling_lab/atlas.json]

Sampling Lab read trap, flow models: handling is uneven in core, per the atlas. Only euler_ancestral, dpm_2_ancestral and dpmpp_2s_ancestral switch to rectified flow code. res_multistep_ancestral and dpmpp_2s_ancestral_cfg_pp run the older ancestral maths on flow sigmas. deis uses fixed EDM constants on every model. [docs: studio/sampling_lab/atlas.json]

Sampling Lab read trap, numbers that mislead, per the atlas: Flux "shift" is the log of SD3 "shift", so the same number gives very different curves. BasicScheduler stretches for "denoise" and keeps the step count, while AYS, GITS and Optimal Steps cut steps. ddim_uniform can return more steps than asked, beta can return fewer, and core's Laplace has no trailing zero, so it stops with noise left. [docs: studio/sampling_lab/atlas.json]

Sampling Lab read trap, same name and different maths: NAG scale differs by one between camps, so one number is not one strength. Pack schedulers named ays, beta or simple can be different curves from core's. Noise names can mislead too: the atlas says PowerNoiseSuite's "blue" has a 1/f squared power spectrum, the reverse of real blue noise. [docs: studio/sampling_lab/atlas.json]

Sampling Lab read trap, pack side effects: the atlas lists pack controls its readers found to have no effect, such as a churn term that is always zero and a FreeU middle-block option on a hook core never reads. It also lists packs that replace core functions at import, changing every job once installed. Each cites its file and line, and none was run here. [docs: studio/sampling_lab/atlas.json]

## Sampling Lab safety and licence limits

The Sampling Lab's risk flags are a keyword scan plus a local model's reading, not a safety guarantee, and the page says so. 348 entries have a provider flagged. Across credited packs the flags read: paid or partner API 103, global patching 95, decoded or dynamic code 93, downloads models 73, runtime installs 67, credential paths 5. [run: studio/sampling_lab/atlas.json] [code: studio/web/samplinglab.js:154]

The Sampling Lab atlas records security notes among its surprises. A static scan found eval or exec in 103 of 865 packs in one section, with some false positives, and one pack holds an encrypted blob it passes to exec. The atlas files that one as a security note, not a method. Treat a shared workflow using such nodes like a script from a stranger. [docs: studio/sampling_lab/atlas.json] [inference]

## Sampling Lab run and test limits

Sampling Lab refuses what is not core, so a run cannot name a pack, and it refuses SkipLayerGuidanceSD3 except on the flow model. It will not swap a missing model: the run stops and names the checkpoint. If the /object_info call itself fails, the file list counts as empty, so the message says "not installed" even when the real cause was that call. [code: studio/sampling_lab.py:49-50, studio/sampling_lab.py:59, studio/sampling_lab.py:76-87] [test: tests/test_sampling_lab.py]

Sampling Lab tests stub ComfyUI, with no GPU and no real queue, so they prove routes and data, not a render. The check that the core name lists match ComfyUI's source is skipped unless COMFYUI_DIR points at a checkout. The numbers in measures.json came from one torch build, 2.16.0.dev20261027. [test: tests/test_sampling_lab.py] [run: studio/sampling_lab/measures.json]

## Final session findings, 2026-11-03

Sampling Lab Walk is not core-only, unlike the Sampling Lab run route. Its graphs use KJNodes GenerateNoise and the studio's own PSN latent nodes. The walk's end frames are not pixel-identical to an ordinary KSampler on the same seeds: mean differences of 0.99 and 0.93 of 255. [run: studio/sampling_lab/walk.json]

Sampling Lab Walk is one model, one prompt per walk and one seed pair, on SD 1.5 only. It shows what slerp and a straight blend do there; it does not show how other models behave. [run: studio/sampling_lab/walk.json] [inference]

The 24 atlas entries added on 2026-11-02 for OCS and Skoogeer-Noise did not go through the full atlas build or its second reader. They carry no second-reader pill and none has a render in the atlas. [run: studio/sampling_lab/atlas.json]

Which Word's recorder does not give exactly the plain picture. Its source says it draws the same picture up to float rounding, but on the SDXL red-hat render the largest pixel difference was 119 of 255 and 2.1% of pixels moved by more than 10. On SD 1.5 the largest was 16. [code: psn_nodes/attention_maps.py:8] [run: studio/sampling_lab/attention.json]

Which Word's colour-region checks are stored with failures included. "teacup" failed on both models, "red" failed by plain lift on both, and SDXL "hat" failed by plain lift while passing once the map's floor was removed. A heatmap is a mean over heads, layers and steps, so read it as a hint, not a segmentation. [run: studio/sampling_lab/attention.json] [inference]

Which Word refuses DiT models such as Flux, SD3 and Wan, because they have no UNet cross-attention for it to record. It works on SD 1.5 and SDXL UNets only. [code: psn_nodes/attention_maps.py:9]

Model Anatomy reads headers only. It does not open pickles, because listing their tensors means running an unpickler that can run code: 248 pickle files and 32 others were listed but not read. Quantized layers count the weights they stand for from their descriptor or scale shapes, so counts there are derived, not read directly. [run: studio/anatomy/index.json] [code: studio/anatomy.py]

The mixture-of-experts page is one recording of one 4-bit quantized model, text only, on invented prompts. Routing in the 4-bit build may differ from the full-precision model, and nothing on the page measures that. [run: studio/moe/index.json] [inference]

Detail Daemon, one of the node packs added to the main ComfyUI on 2026-11-03, was tried once on SDXL at 1024 x 1024 and 25 steps: at 0.15 it added fine detail and kept the picture; at 0.5 it overcooked it into a stipple. It is not in the Sampling Lab atlas yet, so treat strengths above about 0.2 as untested. [claim: studio install record 2026-11-03] [inference]
