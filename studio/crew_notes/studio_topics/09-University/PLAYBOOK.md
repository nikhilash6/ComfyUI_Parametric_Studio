# University: playbook

State of the data: 2026-11-01. Every count here is computed by the builder into catalogue.json. [code: studio/university/build.py:165-178] [test: tests/test_university_page.py]

## What it is

ComfyUniversity is the Learn tab: 162 lessons in 18 tracks. By level: 100 has 16, 200 has 65, 300 has 49, 400 has 32. Level names on the page are First steps, Working knowledge, Under the hood and Expert. [run: studio/university/catalogue.json] [code: studio/web/app.js:279, studio/web/university.js:10]

ComfyUniversity tracks, part 1: Your first graph 16. Samplers, schedulers and CFG 10. Noise and latent maths 10. Guidance 8. Conditioning 8. ControlNet, depth and inpainting 8. LoRAs and training 8. Video 11. Audio and Music 3 has 4 lessons. [run: studio/university/catalogue.json] [code: studio/university/tracks.json]

ComfyUniversity tracks, part 2: 3D 5. Writing custom nodes 11. Debugging graphs 9. VRAM and performance 13. Reading and vetting node packs 8. The API, apps and agents 10. Inside the models 7. Measuring and research 4. How we got here 12. [run: studio/university/catalogue.json] [code: studio/university/tracks.json]

A ComfyUniversity lesson is one folder with course.json, lesson.md, lab.py, lab_output.txt and quiz.json. Eight named teacher characters front the lessons. The page estimates 785 minutes of reading in total. [docs: studio/university/AUTHORING.md] [run: studio/university/catalogue.json]

## What is in a lesson

A ComfyUniversity lesson page has an objective, sections including "What goes wrong", browser labs, graphs, a CPU lab, a quiz, a "How we know" list and sources. A test requires this kit on every finished lesson. [code: studio/web/university.js:90-107, studio/university/build.py:150-159] [test: tests/test_university_page.py]

ComfyUniversity browser labs are small interactive pieces that run in the page with no model and no GPU. There are 115 distinct ones, and all 162 lessons embed at least one. Tests compare the page's scheduler, solver and validator code with ComfyUI's own results. [run: studio/university/catalogue.json] [test: tests/test_university_page.py]

A ComfyUniversity CPU lab is plain Python and torch with fixed seeds, under 60 s, at least one assert, and limited imports with no network. The builder runs it twice, requires identical output, and stores it. Run it here sends the stored file to the server; nothing from the request reaches the code. [code: studio/university/build.py:10, studio/university/build.py:63, studio/university/build.py:121-124, studio/university/build.py:193-195, studio/server.py:285-296]

ComfyUniversity quizzes hold 896 questions, 4 to 7 per lesson. Every answer carries a reason, and a test confirms each question marks exactly one option right. Wrong answers can be tried again. [run: studio/university/catalogue.json] [code: studio/university/build.py:125-131, studio/web/university_parts.js:14] [test: tests/test_university.py]

ComfyUniversity graphs number 93, all in API format and all used by a lesson. All 93 pass ComfyUI's own validate_prompt. The 25 that need no model were really executed on a CPU. The 68 that need a model were validated only. None needs a node pack. Recorded against ComfyUI v0.43.0. [run: studio/university/graphs/verified.json] [test: tests/test_university_page.py]

A ComfyUniversity graph can be read node by node on the page, downloaded or copied as JSON. The page does not run it. A graph that needs models lists them under "You will need". [code: studio/web/university_parts.js:33, studio/web/university_parts.js:49-52]

## How a learner uses it

A ComfyUniversity learner starts from "Start here", which is the first unfinished lesson in track order, or opens a track, or searches every lesson with a level filter. A lesson names what it expects you to know and links to it. [code: studio/web/university.js:16, studio/web/university.js:25, studio/web/university.js:53-59, studio/web/university.js:99]

ComfyUniversity marks a lesson finished when it is read to the end, every quiz question is right, and all its browser labs are passed. Progress stays in the browser under one storage key, with a Reset button. There is no account. [code: studio/web/university.js:1, studio/web/university.js:29, studio/web/university.js:83, studio/web/university_logic.js:4-10] [test: tests/test_university_page.py]

## How a lesson records its checks

A ComfyUniversity course.json lists verified claims, each with how it was checked: source, run here, docs or test. Across all lessons: 1,073 claims, of which source 538, run here 354, docs 143, test 38. The page shows them under "How we know". [docs: studio/university/AUTHORING.md] [code: studio/web/university.js:106] [run: studio/university/catalogue.json]

A ComfyUniversity course.json also lists what could not be checked. There are 460 such sentences, and every lesson has at least one. The page labels each "Not checked". [docs: studio/university/AUTHORING.md] [code: studio/web/university.js:106]

ComfyUniversity lessons name 1,196 ComfyUI functions and classes in code_refs, each looked up in the source by a test when a ComfyUI checkout is present. [run: studio/university/catalogue.json] [test: tests/test_university.py] [code: studio/university/build.py:45-62]

## The second-read mark

The ComfyUniversity second_read mark lives in course.json as a record with errors_fixed. 142 lessons have it, and together they found and fixed 192 errors. Per lesson: 35 found 0, 51 found 1, 34 found 2, 17 found 3, 3 found 4, 2 found 5. [run: studio/university/catalogue.json] [test: tests/test_university_page.py]

A ComfyUniversity lesson with no second_read is shown as "Author-checked, second read pending", and with the short label "Second read pending" in lists. 20 lessons are in this state on 2026-11-01. [code: studio/web/university.js:45, studio/web/university.js:60] [test: tests/test_knowledge.py]

The 20 ComfyUniversity lessons with the second read pending are CU-301, 302, 303, 309, 312, 313, 317, 404, 406, 407, 413, 415, 470, 503, 504, 505, 509, 510, 515 and 517. By track: Inside the models 7, How we got here 6, Measuring and research 4, API and agents 3. By level: 300 has 11, 400 has 7, 200 has 2. [run: studio/university/catalogue.json]

The ComfyUniversity tutor agent must flag pending lessons: a test fails it if it cites a lesson with no second read and does not say so. [test: tests/test_qwen_agents.py]

## Writing a lesson

ComfyUniversity authors follow AUTHORING.md and check with build.py. The builder refuses LaTeX, stray asterisks, private paths, unknown sources or embeds, lab lines not in the stored output, and fewer than 3 quiz questions. Only finished lessons reach the catalogue. [docs: studio/university/AUTHORING.md] [code: studio/university/build.py:99-135, studio/university/build.py:165-171]

## Final session findings, 2026-11-03

ComfyUniversity now has 163 lessons, after CU-319 was added on 2026-11-02. By level: 100 has 16, 200 has 65, 300 has 50, 400 has 32. The Inside the models track has 8. The catalogue counts 116 browser labs, 93 graphs (25 ran on a CPU) and 1,199 code_refs, and the lessons' minutes add up to 794. [run: studio/university/catalogue.json]

ComfyUniversity second reads are nearly complete. 162 of 163 lessons carry a second_read mark, together finding and fixing 203 errors. Per lesson: 45 found 0, 60 found 1, 35 found 2, 17 found 3, 3 found 4, 2 found 5. The only lesson still pending is CU-319. The older list of 20 pending lessons is out of date. [run: studio/university/catalogue.json]

ComfyUniversity CU-319, "Train a tiny network", is a level 300 lesson in which a small network learns toy 2D data (spiral, circles, XOR, two blobs) live in the browser, in plain JavaScript with no fetch. It draws the decision boundary with held-out points, the loss curve and every weight as a line, with controls for layers, width, learning rate, activation and noise, plus an in-page gradient check. It ties the network to the FeedForward block in every SD 1.5 transformer. [docs: studio/university/300/CU-319-train-a-tiny-network/lesson.md, studio/university/300/CU-319-train-a-tiny-network/course.json] [code: studio/web/university_mlp.js]

ComfyUniversity CU-319's maths is tested under node: forward, loss and backward match PyTorch autograd for ReLU, tanh, sigmoid and linear, and finite differences catch a backward pass with the tanh derivative left out. Its CPU lab's stored output: a 2-8-8-1 tanh network at rate 0.3 for 2500 steps got 97.8% of training points and 98.3% of held-out points right, while the same shape with linear activations got 45.0% held out. The browser network has 105 weights and biases; an SD 1.5 FeedForward at width 320 has 1,231,680. [test: tests/test_university_mlp.py] [run: studio/university/300/CU-319-train-a-tiny-network/lab_output.txt]

The ComfyUniversity knowledge index counts 163 lessons, CU-319 included, and its test was updated to match. [test: tests/test_knowledge.py]

ComfyUniversity lessons now embed all 27 videos of the studio's showcase gallery, up from 6, each where the lesson teaches its graph, with a caption written after watching it. Among them: four H3 clips, two of them Director takes, in CU-332, four LTX clips in CU-331, three Wan 2.2 clips in CU-333, the LTX IC-LoRA effects on one source clip in CU-213, CU-214, CU-273, CU-280 and CU-334, Recast in CU-265 and the music video pipeline in CU-517. [run: studio/web/showcase/showcase.json] [docs: studio/university/300/CU-332-minimax-h3-node-by-node/lesson.md]

ComfyUniversity lessons also show the studio's own family, recipe and pipeline renders where the text discusses them, added 2026-11-02: for example SD 3.5, Klein, Lumina 2, Z-Image, RIFE, SVD, AnimateDiff Lightning, Qwen3-VL captions, GFPGAN, IP-Adapter, TRELLIS.2 and Hunyuan3D 2.1, a style LoRA recipe in CU-212, a CPU-made sound in CU-216, and the drawing-to-figure, song-to-video and world-flood pipelines in CU-307, CU-350 and CU-334. [docs: studio/university/200/CU-212-lora-low-rank/lesson.md, studio/university/300/CU-307-three-d-representations/lesson.md] [claim: studio commit log, 2026-11-02]

ComfyUniversity video embeds take an optional poster since 2026-11-02, written {{video:clip|caption|poster}}. A video with a poster shows that still before play and loads nothing until asked; one without preloads metadata so the browser shows its first frame. The builder checks the poster path like any other media, and tall clips are capped at 72% of the screen height. [code: studio/university/build.py:37, studio/web/university_logic.js:35, studio/web/university_parts.js:80, studio/web/university.css:73] [test: tests/test_university.py, tests/test_university_page.py]

ComfyUniversity's two FLUX.1 graphs now point at files the test machine has. c_flux_guidance in CU-251 runs on FLUX.1 Kontext dev fp8, whose header has the same guidance_in layer as FLUX.1 dev, and the lesson says it stands in. c_style_redux runs on FLUX.1 schnell at 4 steps with FluxGuidance removed, since schnell takes no guidance; its needs note says to add it back for dev. Both pass ComfyUI's validation. [docs: studio/university/200/CU-251-embedded-guidance/lesson.md, studio/university/graphs/c_flux_guidance.json, studio/university/graphs/c_style_redux.json] [run: studio/university/graphs/verified.json]

ComfyUniversity's sd15_train_lora graph ships a small captioned set: studio/datasets/university_astrolabe, six 512 x 512 pictures of an invented brass astrolabe that the studio's own SD 1.5 lessons drew, each with a .txt caption. The graph's "You will need" note says to copy the folder into ComfyUI's input folder, and the graph audit accepts a shipped dataset folder instead of calling it a bad value. [docs: studio/university/graphs/sd15_train_lora.json] [code: studio/graph_audit.py:13-16, studio/graph_audit.py:117-118]

The Learn page's wall of renders comes up tile by tile, 40 ms apart, and its tracks lift on hover since 2026-11-02, off under prefers-reduced-motion. [code: studio/web/polish.css:113-125]
