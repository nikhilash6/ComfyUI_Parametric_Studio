# RES4LYF page: playbook

These RES4LYF notes describe the page as of 2026-11-01, with pack facts from pack commit 56e4475, dated 2026-10-01. [code: studio/web/res4lyf_data.js]

## What the RES4LYF page is

The RES4LYF page is a thank-you and reference page for ClownsharkBatwing's ComfyUI node pack. RES4LYF does not ship with Parametric Studio. The team ran it in a separate ComfyUI to learn it and made the page's renders that way. [code: studio/web/res4lyf.js:1, studio/web/res4lyf.js:165] [test: tests/test_res4lyf_page.py] [docs: PROVENANCE.md]

The RES4LYF page has no Python route and no server side. Its script fetches nothing, which a test holds, and outside links are plain anchors a visitor chooses to open. In the studio server code, only the crew routing names it. [test: tests/test_res4lyf_page.py] [code: studio/crew.py:53, studio/crew.py:61]

RES4LYF page chapters: Story, Plates, The math, Samplers, What it does, Node map, Credits and Licence. A plain licence note sits above the first chapter, and a test holds that it stays near the top. [code: studio/web/res4lyf.js:40, studio/web/res4lyf.js:166] [test: tests/test_res4lyf_look.py]

## RES4LYF counts on the page

RES4LYF counts from reading the source: 118 samplers in its picker, 300 node names registered, 299 of which loaded, 17 noise types, 12 noise modes and 48 example workflows. The pack's README covers an earlier version and gives 69 samplers. [code: studio/web/res4lyf_data.js, studio/web/res4lyf.js:169-176] [test: tests/studio_lanes/test_res4lyf_logic.mjs, tests/test_res4lyf_page.py]

RES4LYF sampler families on the page: Exponential 41, Fully implicit 30, Linear 20, Multistep 10, Hybrid 9, Diagonally implicit 8. The page's search and family buttons filter the list, and the number shown beside each name is stages per step. [code: studio/web/res4lyf_data.js, studio/web/res4lyf.js:101-110] [test: tests/studio_lanes/test_res4lyf_logic.mjs]

The RES4LYF naming rule for cost comes from the README: "2s" runs two stages a step, so two model calls, and "m" samplers reuse earlier steps at one call a step. So res_3s at 20 steps is about 60 model calls against 20 for Euler. The calls field in results.json is worked out from this rule by the script, not counted during the run. [code: studio/web/res4lyf_logic.js:5-11, scripts/res4lyf_graphs.py:171-174] [test: tests/studio_lanes/test_res4lyf_logic.mjs]

## What runs on the RES4LYF page itself

Three RES4LYF page tools run in the browser and do not use the pack or the GPU. The cost lab multiplies steps by stages, the beta lab draws the beta57 curve, and the toy lab compares methods on one number. Nothing on the page queues a job. [code: studio/web/res4lyf.js:76-99, studio/web/res4lyf.js:229, studio/web/res4lyf_feature.js:120] [test: tests/test_res4lyf_page.py]

The RES4LYF beta lab compares beta57 (alpha 0.5, beta 0.7) with ComfyUI's default beta (alpha 0.6, beta 0.6), computed from those settings before rounding to a model's timesteps. It counts how many steps land in the lowest quarter of timesteps. It shows the shape only, not the effect on a picture. [code: studio/web/res4lyf.js:87-99, studio/web/res4lyf_logic.js:61-62] [test: tests/studio_lanes/test_res4lyf_logic.mjs]

The RES4LYF toy lab compares euler, heun_2s and res_2s on a one-number problem with two possible answers, for a budget of model calls, so euler gets twice the steps of the other two. It uses the published formulas, not the pack's code, and the page says it says nothing about pictures. [code: studio/web/res4lyf_logic.js:69, studio/web/res4lyf_logic.js:75-85, studio/web/res4lyf_feature.js:117-120] [test: tests/studio_lanes/test_res4lyf_look.mjs, tests/test_res4lyf_look.py]

## How RES4LYF works, as the page reads it

The RES4LYF page explains exponential samplers. Steps are measured on a log scale of sigma, the walk to the model's guess follows a known curve and is solved exactly, with phi functions as the weights. Extra stages measure how much the guess moves. These are our words from the code at that commit, not the author's. [code: studio/web/res4lyf.js:195-211]

Bongmath on the RES4LYF page: after newer estimates arrive, it re-solves where a step started and where its earlier stages sat, up to 100 rounds, holding the model's predictions fixed, so it makes no extra model calls. Multistep samplers skip it once they settle in. The walk-through on the page is a schematic, not measured values. [code: studio/web/res4lyf.js:18, studio/web/res4lyf_feature.js:161] [test: tests/test_res4lyf_look.py]

The RES4LYF page also explains the sampler state stored in the latent, which lets a Chainsampler pick up mid-schedule, plus unsample and resample modes. Guide modes are epsilon, data, lure, flow, sync and inversion. Regional nodes defer their masks to the sampler, and Re*Patcher nodes swap model block classes. All are our reading of the code. [code: studio/web/res4lyf.js:19-23, studio/web/res4lyf.js:195]

## RES4LYF renders and node check

The RES4LYF gallery has 31 renders made with the pack, on SD 1.5 (DreamShaper 8), SDXL 1.0 base and FLUX.1 schnell. SD 1.5 and SDXL used 20 steps and CFG 6.5, and Flux used 8 steps and CFG 1. All used seed 4242, with no picking, and each has a downloadable graph. [run: studio/web/res4lyf_renders/results.json] [code: studio/web/res4lyf_gallery.js, studio/web/res4lyf.js:117-118] [test: tests/test_res4lyf_page.py]

RES4LYF gallery graphs are: control (plain KSampler, not the pack), beta57, res_2m, res_2s, res_3s, chain, style_ref, style, unsample and regional, plus redux on Flux. A test checks that each picture credited to the pack went through ClownsharKSampler_Beta or ClownsharkChainsampler_Beta. [code: studio/web/res4lyf_gallery.js] [test: tests/test_res4lyf_page.py, tests/test_res4lyf_look.py]

The RES4LYF node check tried 154 of the 299 nodes, each in its own graph on SD 1.5 with default settings and one seed. Results: 92 rendered, 14 ran with text output, 44 failed in the test, 2 not run alone, 1 rejected by ComfyUI and 1 needing a partner node. The other 145 are marked not tested. [run: studio/web/res4lyf_node_check.json] [code: studio/web/res4lyf_nodes.js, scripts/res4lyf_node_check.py:2-12] [docs: README.md]

Every RES4LYF node has a note written from reading its source: what it does, when to use it and the file and line it comes from. All 299 are in docs/res4lyf/node_notes.json, and the page shows them in 38 groups with a filter by test result. A source link goes to that exact commit. [run: docs/res4lyf/node_notes.json] [code: studio/web/res4lyf.js:128, studio/web/res4lyf.js:132-147, studio/web/res4lyf_logic.js:26] [test: tests/test_res4lyf_page.py]

## Getting RES4LYF yourself

To use RES4LYF you install it yourself in your own ComfyUI. The page gives the README's steps: clone the repo into custom_nodes, then pip install its requirements (opencv-python, matplotlib, pywavelets, numpy 1.26.4 or newer) in ComfyUI's environment. The README also recommends rgthree-comfy. Read the licence first. [code: studio/web/res4lyf.js:26-29, studio/web/res4lyf.js:255]

The RES4LYF "What it can do" section is taken from the README and links to the author's example workflows: style transfer, anti-blur, regional conditioning, temporal conditioning, unsampling and video to video. Those feature and model lists are the author's and were not all tried here. [code: studio/web/res4lyf.js:31-38, studio/web/res4lyf.js:231] [claim: RES4LYF README]

## Final session findings, 2026-11-03

RES4LYF page chapter 07 is "More from ClownsharkBatwing" since 2026-11-02, and its entry in the chapter list reads "More". The chapters are now Story, Plates, The math, Samplers, What it does, Node map, More and Licence. [code: studio/web/res4lyf.js:40, studio/web/res4lyf.js:256] [test: tests/test_res4lyf_page.py, tests/test_res4lyf_look.py]

RES4LYF chapter 07 lists the author's other public work as read on 2 November 2026: UltraCascade (a native ComfyUI version of UltraPixel for Stable Cascade, 38 stars, no licence file), the ComfyUI-UltraPixel fork, and three Hugging Face model repos (CSBW_Style, Cascade_Stage_B_CSBW_Refined, ultrapixel_convert). Each line comes from that project's own README or model card, and the page says plainly that none of them was run. [code: studio/web/res4lyf.js:41-48, studio/web/res4lyf.js:256]

RES4LYF chapter 07 names, but does not describe, the forks that are not separate projects (ComfyUI-Manager, ComfyUI_LayerStyle and WAS Node Suite) and three Hugging Face repos with no model card. Its links may only point at the author's GitHub or Hugging Face, which a test holds. [code: studio/web/res4lyf.js:258] [test: tests/test_res4lyf_page.py]

The blepping page is a thank-you page in the RES4LYF page's style, added 2026-11-02, for blepping's Sonar (MIT, 54 nodes, commit 6c4ae67), Overly Complicated Sampling (MIT, 16 nodes, commit d8574ba) and bleh (Apache-2.0, 32 nodes, commit 1c2bc62), with Skoogeer-Noise (MIT, 62 nodes) run beside them. Its chapters are Story, First check, Sonar, OCS, bleh, Together, What didn't and Licences. No pack code is bundled or copied. [code: studio/web/blepping_data.js, studio/web/blepping.js:15] [test: tests/test_blepping_page.py]

The blepping page's pictures come from a throwaway ComfyUI with only those four packs, against core renders made the same way with no packs: one prompt, seed 424242, 20 steps, no re-rolls, and the graph for each. It holds 78 render records: 23 core, 55 pack. Of the pack graphs, 52 made a picture, 2 failed and 1 was refused as expected. [code: studio/web/blepping_data.js, studio/web/blepping_logic.js:16-20] [run: studio/web/blepping_renders/graphs]

The blepping page's first check, stage 0, loads the packs and runs the core graphs again: SD 1.5, SDXL and SD 3.5 all came out pixel-identical, so loading the packs changed nothing on its own. Pixels are compared after decoding, because each PNG embeds its own graph. [code: studio/web/blepping_data.js, studio/web/blepping_logic.js:21-26]

Blepping page results worth quoting, from notes written after looking at each picture: OCS euler at eta 0 lands almost exactly on core euler, the sanity check. bleh's HyperTile at 1536 px is pixel for pixel the same as core HyperTile. Sonar's dpmpp_sde with default settings gave a flat brown field on SD 1.5 with karras, untuned. Sonar pyramid noise at full ancestral strength swamped an SDXL picture. [code: studio/web/blepping.js:21-32]

Blepping providers are marked in the Sampling Lab atlas, so OCS, Sonar and bleh method pages link to the blepping page. [code: studio/web/samplinglab_method.js:91] [run: studio/sampling_lab/atlas.json]

RES4LYF page sliders keep a thin track with a 40 px touch height since 2026-11-02, and other small controls and card links reach 40 px. Its cover carries the shared hero light. No wording or data changed. [code: studio/web/res4lyf.css:197, studio/web/res4lyf.css:318-322, studio/web/polish.css:74-83]
