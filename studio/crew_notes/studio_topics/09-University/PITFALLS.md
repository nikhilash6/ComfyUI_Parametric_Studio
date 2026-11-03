# University: pitfalls

State of the data: 2026-11-01. [run: studio/university/catalogue.json]

## What the second-read mark does and does not promise

The ComfyUniversity "Second reader checked" mark is not a proof. The page says the reader tried to prove the lesson wrong against ComfyUI's source and real runs, and sampled the riskiest claims in each lesson. Claims outside the sample were not re-read. [code: studio/web/university.js:44]

ComfyUniversity errors_fixed counts what the second reader found and fixed, not what is left. A lesson with 0 is not error-free, and a lesson with 5 is not worse now. The mark records nothing else: no reader, date or list of claims read. [code: studio/web/university.js:44, studio/web/university.js:60] [run: studio/university/catalogue.json] [inference]

ComfyUniversity lessons with the second read pending are expected to hold a few mistakes. The page says so, because second reads have been finding them: 192 errors across 142 lessons, about 1.35 per lesson. [code: studio/web/university.js:45] [run: studio/university/catalogue.json]

ComfyUniversity "audited" in catalogue.json only means the lesson is not marked draft: all 162 count as audited, including the 20 with the second read pending. Do not read audited as second-read. [code: studio/university/build.py:171, studio/university/build.py:177] [run: studio/university/catalogue.json]

ComfyUniversity lesson codes do not give the level. CU-503 and CU-505 are level 200, and the second read was pending on them. Read the level field, not the number. [run: studio/university/catalogue.json]

## What the labs prove

A ComfyUniversity lab proves its own numbers on a small toy, on a CPU. It does not prove a claim about a full model or a real render. Labs use no GPU, no model and a limited list of imports. [code: studio/university/build.py:63, studio/university/build.py:73-82] [docs: studio/university/AUTHORING.md]

ComfyUniversity lab output can differ on another torch build. Stored output came from torch 2.16.0.dev20261027+cu134. The page then says the output differs from ours while the lab's asserts passed. The exact-match test applies only on that torch version. [code: studio/web/university_parts.js:27] [test: tests/test_university.py] [run: studio/university/graphs/verified.json]

The ComfyUniversity "Run it here" button runs on the studio's server, not in the browser, so it needs torch where the server runs. Only one lab runs at a time, and a second press elsewhere gets a 409 "another lab is running". The hero's "labs in this browser" means the browser labs. [code: studio/server.py:284-296, studio/web/university_parts.js:23, studio/web/university.js:24] [test: tests/test_university_page.py]

A ComfyUniversity lab that takes 60 s or more is stopped and counts as failed. A slow machine could hit that limit. [code: studio/university/build.py:10, studio/university/build.py:75-82] [inference]

## What the graphs prove

ComfyUniversity "Passes ComfyUI's validation" is not "it renders". The 68 graphs that need a model were validated, with model-file menus allowed to fail because those files may be absent, and never executed by the checker. Only the 25 tagged "Ran here on a CPU" were executed. [code: studio/web/university_parts.js:33] [run: studio/university/graphs/verified.json] [code: scripts/verify_university_graphs.py:2-4]

A ComfyUniversity graph's verified mark holds only while its contents match the recorded hash. If a graph changes, its mark drops away, and a test fails until it is verified again. [code: studio/university/build.py:26-27] [test: tests/test_university_page.py]

The ComfyUniversity page tells a learner to drag a graph file onto the canvas. Lesson CU-100 lists this as not checked by hand in the installed version: the front-end code was read, the drop was not tested. [code: studio/web/university_parts.js:52] [docs: studio/university/100/CU-100-first-graph-no-model/course.json]

ComfyUniversity results rest on one ComfyUI version, v0.43.0. A newer ComfyUI can move a function or change a default, so a lesson's source claim can age. Lessons are not re-checked automatically unless the tests are run against a checkout. [run: studio/university/graphs/verified.json] [inference]

## Test limits

Some ComfyUniversity tests skip without their tools. The code_refs lookup and the latent table check skip with no ComfyUI checkout, and the browser maths and validator tests skip without node. A green run on such a machine did not run those. [test: tests/test_university.py, tests/test_university_page.py]

The ComfyUniversity code_refs check proves a name exists in the source. It does not prove the lesson describes that name correctly. [code: studio/university/build.py:45-62] [inference]

The ComfyUniversity source rule says an author must have opened each linked source. A test checks the source list and arXiv titles, but cannot check that the page was read. [docs: studio/university/AUTHORING.md] [test: tests/test_university.py] [inference]

## Progress and scope

ComfyUniversity progress lives only in that browser. Clearing site data, changing browser or changing device loses it, and if storage is blocked it is not saved. A finished lesson is not a certificate: quiz answers can be retried without limit. [code: studio/web/university_logic.js:4-6, studio/web/university_parts.js:14] [test: tests/test_university_page.py]

ComfyUniversity topics_next.txt lists 12 planned topics, such as video VAEs and offloading. They are plans, not lessons, so a crew answer should not cite them as taught. [code: studio/university/topics_next.txt]

## Final session findings, 2026-11-03

ComfyUniversity CU-319 is the one lesson with its second read pending, so the page shows it as "Author-checked, second read pending" and the tutor agent must say so when it cites it. Its course.json lists 5 verified claims and 3 it could not check. [run: studio/university/catalogue.json] [docs: studio/university/300/CU-319-train-a-tiny-network/course.json] [test: tests/test_qwen_agents.py]

ComfyUniversity's FLUX.1 graphs were validated, not executed. c_flux_guidance uses FLUX.1 Kontext dev as a stand-in for FLUX.1 dev, because FLUX.1 dev exists on the test machine only as a diffusers folder that UNETLoader cannot read. c_style_redux runs on schnell without FluxGuidance, so it is not the dev graph a reader may expect. [run: studio/university/graphs/verified.json] [docs: studio/university/200/CU-251-embedded-guidance/lesson.md] [claim: studio commit log, 2026-11-02]

ComfyUniversity's sd15_train_lora graph does not find its dataset on its own: the shipped folder must be copied into ComfyUI's input folder by hand. The graph was validated, not run, so training on that set from this graph has no recorded result. [docs: studio/university/graphs/sd15_train_lora.json] [run: studio/university/graphs/verified.json]
