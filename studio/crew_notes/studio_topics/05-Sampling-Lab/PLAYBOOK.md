# Sampling Lab: playbook

These Sampling Lab notes describe the data as of 2026-11-01, the date the atlas was built. [run: studio/sampling_lab/atlas.json]

## What the Sampling Lab is

The Sampling Lab is a page that explains what samplers, schedulers, guidance, noise and latent maths really do, read from the source of ComfyUI and node packs. It says for each method whether it can run and what the proof is. Its data sits in studio/sampling_lab as atlas.json, measures.json and renders.json. Its six views are Atlas, Curves, Bench, Renders, Surprises and Credits. [code: studio/sampling_lab.py:1-3, studio/web/samplinglab.js:161]

## The Sampling Lab atlas in numbers

The Sampling Lab atlas holds 720 methods: 174 guidance, 164 samplers, 114 schedulers, 91 latent operations, 86 model patches, 79 noise methods and 12 maths entries. Each entry has a plain description, the working, evidence and credit. [run: studio/sampling_lab/atlas.json] [test: tests/test_sampling_lab.py]

Where Sampling Lab methods run: 183 are in ComfyUI core, 13 are in a pack that was live on the test machine, and 524 need a pack. Of the 183 core methods, 44 have a proof render and 139 do not. No method outside core has a render. [run: studio/sampling_lab/atlas.json] [test: tests/test_sampling_lab.py]

The Sampling Lab scanned 1890 packs in the sampling sections: 1786 had source, parsed and not run, and the other 104 are not described. 2160 evidence lines were found on disk and none rejected, which proves only that the code exists there. Of the rows readers went through, 236 were read in full and 343 in part, 1451 went by name alone and 2527 were skipped. [run: studio/sampling_lab/atlas.json] [code: studio/web/samplinglab.js:116-117]

## Sampling Lab proof labels

The Sampling Lab atlas uses four proof labels. "From code" means read in the source, with a script finding its file and line on disk; "measured here" means it ran and the numbers were kept. "From pack README claim" is what an author says, not checked; "inference" is our reasoning, not read or measured. [code: studio/web/samplinglab_logic.js:192] [test: tests/test_sampling_lab.py]

Every Sampling Lab entry has one main label for its description. 692 entries are "from code", 26 "inference" and 2 "from pack README claim". No entry has "measured here" as its main label. Measurement shows up as a separate rung: renders, a sigma curve or a bench row. [run: studio/sampling_lab/atlas.json] [code: studio/web/samplinglab_logic.js:193-204]

A second reader checked 378 of the 720 Sampling Lab entries against the code: 296 correct, 68 minor problems, 14 wrong. 69 entries were corrected, and the test requires each wrong one to carry a fix. The other 342 entries had one reader, and the page marks the checked ones with a pill. [run: studio/sampling_lab/atlas.json] [test: tests/test_sampling_lab.py] [code: studio/web/samplinglab_method.js:81, studio/web/samplinglab.js:117]

## Sampling Lab renders

The Sampling Lab has 44 proof renders, all with core nodes only, with one prompt, seed 424242 and 20 steps. By set: 15 samplers on SD 1.5 with karras and CFG 7, 9 schedulers on SDXL with dpmpp_2m, 12 guidance renders on SDXL with euler and normal, and 8 flow renders on SD 3.5. Those 8 were decoded with the small TAESD3 preview VAE, so they are not final quality. [run: studio/sampling_lab/renders.json] [code: studio/sampling_graph.py:8] [test: tests/test_sampling_lab.py]

## Running a graph from the Sampling Lab

POST /api/sampling/run queues one core-only graph, and GET /api/sampling/graph returns the same graph without running it. The proof sweep, the copy button and the run route share one builder, so what the page shows is what ran. It uses SamplerCustomAdvanced with KSamplerSelect and BasicScheduler. [code: studio/sampling_graph.py:1-2, studio/sampling_graph.py:21-47, studio/sampling_lab.py:66-69, studio/sampling_lab.py:94-99] [test: tests/test_sampling_lab.py]

Sampling Lab run limits: model sd15, sdxl or sd35 (default SDXL), 45 core sampler names (default euler), 9 core scheduler names (default normal), steps 1 to 60 (default 20), CFG 0 to 30. The prompt is at most 1000 characters and passes the safe-for-work check, and the negative prompt is the builder's fixed one. Only one core patch can be chosen, with optional PerpNegGuider, and 77 core entries map to something a method page can run. [code: studio/sampling_lab.py:44-65, studio/sampling_graph.py:4, studio/sampling_graph.py:10-19, studio/web/samplinglab_logic.js:82] [run: studio/sampling_lab/atlas.json] [test: tests/test_sampling_lab.py]

## Sampling Lab solver bench, on a toy problem

The Sampling Lab bench runs ComfyUI's own solver code on the CPU, on a toy problem whose exact answer is known. The data is a plain Gaussian, so the perfect denoiser can be written down. There is no neural network and no picture. It measures how a solver follows the equation and how many model calls that costs. [code: scripts/build_sampling_measures.py:1-10, scripts/build_sampling_measures.py:77-78, studio/web/samplinglab_bench.js:104]

The Sampling Lab bench holds 45 samplers, each in two spaces (eps with karras, flow with simple) at 5, 10, 20 and 40 steps, with 4096 samples. It keeps model calls, error to the exact answer, variance error and a slope. Running with a second noise seed splits them into 22 deterministic and 23 stochastic on eps. None errored. [run: studio/sampling_lab/measures.json] [code: scripts/build_sampling_measures.py:100-127]

Sampling Lab bench on eps at 20 steps, given as sampler, model calls, error: euler 20, 0.0768; dpmpp_2m 20, 0.0119; heun 39, 0.0114; dpm_2 39, 0.0064; lms 20, 0.0059; ipndm 20, 0.0035; deis 20, 0.0020; uni_pc 20, 0.0016. These are toy numbers and do not rank pictures. [run: studio/sampling_lab/measures.json] [test: tests/test_sampling_lab.py]

Sampling Lab bench on flow at 20 steps, given as sampler, model calls, error: euler 20, 0.0863; dpmpp_2m 20, 0.0278; heun 39, 0.0146; dpm_2 39, 0.0079; lms 20, 0.0132; ipndm 20, 0.0133; deis 20, 0.0107; uni_pc 20, 0.0085; uni_pc_bh2 20, 0.0010. The order differs from eps. [run: studio/sampling_lab/measures.json]

Stochastic Sampling Lab solvers have no single exact path, so the bench gives them a variance error against a target variance of 1. At 20 steps on eps: seeds_3 0.0049, sa_solver 0.0068, dpmpp_sde 0.0241, er_sde 0.0254, euler_ancestral 0.2914, lcm 0.5913. Their error to the exact answer sits near 1 or above and is not a score, and the page does not draw it. [run: studio/sampling_lab/measures.json] [code: studio/web/samplinglab_bench.js:104, studio/web/samplinglab_logic.js:60-67, scripts/build_sampling_measures.py:73]

## Other Sampling Lab measures

The Sampling Lab Curves view draws sigma lists computed by core's code for SD eps, SD3 flow with shift 3 and Flux with shift 1.15, at 4, 8, 12, 20, 30 and 50 steps, with nine core schedulers in each. A curve shows the schedule, not how a picture looks. Also stored are how ancestral steps split, and noise spectra that came out flat with standard deviation near 1. [run: studio/sampling_lab/measures.json] [code: studio/web/samplinglab_bench.js:54]

## Sampling Lab credits

The Sampling Lab credits 457 packs with licences as found, so check them before shipping anything. Counts: MIT 127, no licence file found 101, GPL 83, not recorded 69, Apache-2.0 57, AGPL-3.0 14. 23 packs have no recorded author and are credited by name, and pack_owners.json fills in authors only where a folder name has one clear match. [run: studio/sampling_lab/atlas.json, studio/sampling_lab/pack_owners.json] [code: studio/web/samplinglab.js:152] [test: tests/test_sampling_lab.py]

RES4LYF appears in the Sampling Lab atlas as 20 credited methods, with short entries, and none of them is in core or has a render. The Credits view points to the RES4LYF page because of its licence. Sampling Lab will not run a RES4LYF sampler or scheduler such as res_2m or beta57. [run: studio/sampling_lab/atlas.json] [code: studio/web/samplinglab.js:152] [test: tests/test_sampling_lab.py]
