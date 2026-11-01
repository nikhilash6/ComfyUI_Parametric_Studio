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
