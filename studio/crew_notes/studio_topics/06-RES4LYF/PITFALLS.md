# RES4LYF page: pitfalls

These RES4LYF notes describe the page as of 2026-11-01, with pack facts from pack commit 56e4475. [code: studio/web/res4lyf_data.js]

## The RES4LYF licence point

The RES4LYF LICENSE file opens with a condition: using the software or a derivative to provide a commercial service, such as an AI image generation service, is prohibited without permission and/or a separate commercial licence from the copyright holder. The full GNU AGPL v3 text follows. [code: studio/web/res4lyf.js:25, studio/web/res4lyf.js:259-260] [docs: THIRD_PARTY_NOTICES.md] [test: tests/test_res4lyf_page.py]

The RES4LYF licence condition, in the page's plain terms: a paid service built on the pack or a derivative needs permission first, even if it charges indirectly or only uses the pack inside a larger product. So it reaches further than a service sold under the pack's name. [code: studio/web/res4lyf.js:25, studio/web/res4lyf.js:261]

RES4LYF's own files disagree. Its pyproject.toml says license = "MIT", while its LICENSE file has the commercial condition and AGPL text. The page shows LICENSE as the stricter of the two and tells readers to ask the author if it matters. This is a reading of the files, not legal advice. [code: studio/web/res4lyf.js:262] [test: tests/test_res4lyf_page.py]

The studio links to RES4LYF and does not bundle it, because of that licence. The page holds names, counts, short credited quotes, our notes, and our own graphs and renders, with no pack code. The page itself is under the studio's AGPL-3.0. Tests check no pack files were copied in. [code: studio/web/res4lyf.js:166, studio/web/res4lyf.js:263] [docs: THIRD_PARTY_NOTICES.md, PROVENANCE.md] [test: tests/test_res4lyf_page.py]

The RES4LYF licence applies to you if you install it, whatever the studio's own licence says. Running the pack's graphs from this page in a paid service is the case the condition names. Downloadable graphs need the pack to run, and they do not grant any permission. [code: studio/web/res4lyf.js:118, studio/web/res4lyf.js:261] [inference]

The tests that compare the RES4LYF licence words, sampler data and README quotes with the pack itself only run with a local copy named by RES4LYF_PACK, and are skipped otherwise. So on a plain checkout those facts are not re-checked. Licence wording could also have changed upstream after commit 56e4475. [test: tests/test_res4lyf_page.py] [inference]

## What needs the RES4LYF pack

Every RES4LYF node, sampler and render graph on the page needs the pack, which the studio installer does not install. The studio cannot run them: nothing on the page queues a job. Sampling Lab refuses res_2m and beta57 too, as they are not core names. [test: tests/test_res4lyf_page.py, tests/test_sampling_lab.py] [code: studio/sampling_lab.py:49-50, studio/web/res4lyf.js:165]

A studio node with RES4LYF in its description is not the pack. PSN_Fast_Sampler_Plan only validates names and steps and builds a plan with plain maths, and its docstring says it runs none of the pack and does no sampling. Its "RES4LYF" and "BongMath" solver names are labels only. [code: psn_nodes/gen/n_3_fast_sampling_with_res4lyf.py:1-17, psn_nodes/gen/n_3_fast_sampling_with_res4lyf.py:25] [test: tests/gen/test_n_3_fast_sampling_with_res4lyf.py]

## What the RES4LYF renders and checks do not prove

RES4LYF renders are not a quality test. The page says they show the nodes working, and that its settings are starting points, not the author's best. Comparing control with res_3s changes several things at once, so it says to read that as the nodes at work and not as a ranking. [code: studio/web/res4lyf.js:189, studio/web/res4lyf_feature.js:23] [test: tests/test_res4lyf_look.py]

The author's RES4LYF speed claim was not tested: the README says RES samplers typically need only 20 steps where Uni-PC needs far more and still does not reach the same quality. The page marks that as the author's claim. The studio has no comparison of its own. [claim: RES4LYF README] [code: studio/web/res4lyf.js:184]

Not all 299 RES4LYF nodes were tried. The page's section text reads as if each one went into a graph, but the stored check holds 154 nodes and 145 are marked "Not tested", including SharkSampler_Beta, ReFluxPatcher and Sigmas Math1. Trust the per-node state and the counts, not that sentence. [code: studio/web/res4lyf.js:242, studio/web/res4lyf_nodes.js] [run: studio/web/res4lyf_node_check.json] [docs: README.md]

A RES4LYF node "rendered" only means the graph ran end to end with default inputs on SD 1.5. It does not mean those settings suit the node, and a strange image is often a poor default. The check used the simplest inputs a node's types allow, with one seed and no re-rolls. [code: scripts/res4lyf_node_check.py:2-10, studio/web/res4lyf.js:243]

A RES4LYF node "failed in our test" is not a verdict on the node. 44 failed, and many need a particular model, video latents or a partner node. ClownsharkChainsampler_Beta failed alone with a KeyError on state_info, yet the chain graphs ran with it behind another sampler. [run: studio/web/res4lyf_node_check.json, studio/web/res4lyf_renders/results.json] [code: studio/web/res4lyf.js:243]

Some RES4LYF renders are not plain pack results. control is plain KSampler, style_ref is an input, and redux uses ComfyUI's own StyleModelApply with the pack's sampler. The unsample renders are marked as a second try, because the first, with a guide on the resample, mostly returned the source, and the Flux one came out flat and blocky. [code: studio/web/res4lyf.js:15, studio/web/res4lyf_feature.js:29, studio/web/res4lyf_feature.js:31]

One RES4LYF graph failed and is not in the gallery: flux_redux_style, with "list index out of range". results.json holds 32 attempts, of which 31 succeeded. That graph used the pack's ReReduxPatcher and StyleModelApplyStyle, so the pack's own Redux path has no render here. [run: studio/web/res4lyf_renders/results.json]

The RES4LYF cost lab is close, not exact. It reads stages from the name, multistep samplers spend extra on their first steps, and implicit steps cost more on top. The count for hybrid names is an inference, and it says nothing about quality. [code: studio/web/res4lyf.js:83]

The RES4LYF toy lab and Bongmath walk-through are teaching tools. The toy's ranking moves as you change the sliders and uses our arithmetic, not pack code. The walk-through shows the order of the work and has no measured values. Neither shows what the pack does to a picture. [code: studio/web/res4lyf_feature.js:120, studio/web/res4lyf_feature.js:161, studio/web/res4lyf_logic.js:69] [test: tests/test_res4lyf_look.py]

## RES4LYF safety and staleness

RES4LYF's Sigmas Math nodes run their formula text through Python's eval. The page says to treat a shared workflow using them like a script from a stranger, and that this is sound advice for any custom node workflow. Sigmas Math1 was not run in the node check. [code: studio/web/res4lyf.js:264] [run: docs/res4lyf/node_notes.json, studio/web/res4lyf_nodes.js]

The Sampling Lab credits list flags RES4LYF for runtime installs, decoded or dynamic code, a paid or partner API, and global patching of torch or ComfyUI. Those come from a keyword scan and a local model's reading, not a check by hand, and they are not a safety guarantee. [run: studio/sampling_lab/atlas.json] [code: studio/web/samplinglab.js:154]

RES4LYF page facts are pinned to commit 56e4475 of 2026-10-01, so names and counts can drift from the live repo. The author calls the work experimental and subject to further changes. Some node notes mention options that look unfinished. Check the source link before relying on a detail. [code: studio/web/res4lyf.js:176, studio/web/res4lyf.js:186, studio/web/res4lyf.js:243]
