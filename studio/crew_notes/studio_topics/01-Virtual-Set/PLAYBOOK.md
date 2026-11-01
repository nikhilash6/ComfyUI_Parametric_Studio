# Virtual Set: playbook

## What it is

Virtual Set blocks a shot in a real-scale 3D place from World Kit, moves an exact camera through it, and steers a video model with what Blender renders: depth, pose, shaded and edge passes, plus first and last stills. It opens from the Virtual Set button in the left rail. [code: studio/vset/__init__.py:1] [docs: studio/processes/virtual-set.md]

Virtual Set needs Blender and one approved World Kit place to render passes, and no model, GPU or ComfyUI for that step. A video needs the model files of the chosen mode as well. [code: studio/vset/needs.py:49-52, studio/vset/runner.py:53-55] [test: tests/vset/test_runner.py]

## What has really run

Virtual Set status on 2026-11-01, from its guide: mode A (H3 depth, and LTX-2.5 with raw keyframes), mode B, mode C with raw keyframes and mode D each rendered once on one street shot on the test machine, and QC passed. Wan, a pose pass and the Qwen keyframe steps have not run on these passes. [docs: studio/processes/virtual-set.md]

Virtual Set test shot on H3, mode A: 1344 x 768, 124 frames at 24 fps, seed 4242, flicker 3.2, layout 0.13. It held the camera and layout and looked like a photograph. It invented taller buildings, shop fronts and a yellow road line, and the knot prop came back lumpy. [code: studio/web/vset_example.js:6-9]

Virtual Set test shot on LTX-2.5 with raw keyframes: 1920 x 1088, 121 frames at 24 fps, seed 4242, flicker 2.0, layout 0.33. It kept the set, the lamp posts and the knot in place. It still looks like a CG render, and the rain in the prompt never appeared. [code: studio/web/vset_example.js:12-15]

## The shot

A Virtual Set shot is one shot.json holding the set (a place id and props with transforms), the cast, the marks, the camera, the format, the look, the mode with its settings, the seed and the action. Render state sits beside it in state.json. The default new shot is mode C, 16:9, 5 s, a push-in, seed 4242. [code: studio/vset/shot.py:1-3, studio/vset/shot.py:46-53]

Virtual Set shot limits: action up to 1500 characters, up to 24 props, up to 2 cast members, 1 to 8 marks. A mark may sit up to 1 m outside the place's bounds. Ids are 12 lowercase letters and seeds run from 0 to 4294967295. [code: studio/vset/shot.py:34-38, studio/vset/shot.py:175-176, studio/vset/shot.py:194-195, studio/vset/shot.py:209-211]

Virtual Set marks are the path the camera follows, in metres. With a cast, the first cast member's marks are used. With no cast, the shot's own marks act as an empty point moving through the set. [code: studio/vset/shot.py:78-81] [test: tests/vset/test_passes.py]

## Modes

Virtual Set mode A, guide passes: the exact depth or pose pass drives the video. The H3 engine uses Fun Union 2.0 at strength 1.0. The Wan 2.2 Fun Control engine uses the first shaded still as its reference picture. The LTX-2.5 engine takes a grey clay pass plus a first frame. [code: studio/vset/modes/guide.py:1-3, studio/vset/modes/guide.py:13, studio/vset/modes/guide.py:53] [test: tests/vset/test_modes.py]

Virtual Set mode B, restyle: H3 Fun Union 2.0 repaints the shot from the prompt and follows the exact depth pass. The regeneration mask is solid white, so what steers the picture is the depth pass and the words, not the colours of the shaded render. [code: studio/vset/modes/restyle.py:1-2] [test: tests/vset/test_modes.py]

Virtual Set mode C, keyframes: the first and last shaded frames become the end stills. By default Qwen-Image 2.1 turns each into a photograph at resolution 1024, then H3 first and last frame fills between them. With keyframes set to "raw" the Blender stills go straight to H3, so no image model is needed. [code: studio/vset/modes/keyframes.py:1-2, studio/vset/modes/keyframes.py:13] [test: tests/vset/test_modes.py]

Virtual Set mode D, motion copy: the shaded render is the reference clip of H3 Ref2VA and the first shaded still is the reference picture, so H3 copies the camera move and blocking. The prompt starts with a plain description of the opening shot. [code: studio/vset/modes/motioncopy.py:1-2, studio/vset/modes/motioncopy.py:13-16] [test: tests/vset/test_modes.py]

Virtual Set lengths: modes A and B render 5 s, modes C and D render 5, 8 or 10 s, all at 24 fps in 9:16, 16:9 or 1:1. H3 takes 17k+5 frames, so 5 s is 124, 8 s is 192 and 10 s is 243. H3 sizes are 1344 x 768, 768 x 1344 and 1024 x 1024. [code: studio/vset/shot.py:24-27, studio/vset/shot.py:68-70, studio/goals.py:60]

Virtual Set mode A on Wan renders 81 frames at 16 fps at 832 x 480 or 480 x 832. Mode A on LTX-2.5 renders 121 frames at 24 fps, with stage 1 at 960 x 544 or 544 x 960 and stage 2 doubling it. Both engines refuse 1:1. [code: studio/vset/shot.py:30-32, studio/vset/shot.py:128-129]

## What each route needs

Virtual Set checks eight routes on every call, by real file size: A, A_wan, A_ltx, A_ltx_raw, B, C, C_raw and D. Route A_ltx adds the Qwen-Image 2.1 files to the LTX ones. C_raw needs only H3 first and last frame files. D needs H3 Ref2VA and the common H3 files. [code: studio/vset/needs.py:7-12]

## Camera

Virtual Set camera presets are push_in, orbit, walk_along, pov, handheld, static and custom. Each has defaults: push_in goes 4.0 m to 1.8 m, orbit is 2.6 m radius and a 90 degree sweep, walk_along stays 2.2 m to the side. Custom needs start and end. Preview camera only does sums and renders nothing. [code: studio/vset/camera.py:14-23, studio/vset/camera.py:134-140] [test: tests/vset/test_camera.py]

## Passes

Virtual Set passes are depth, pose, edges and shaded as videos, first and last as stills, and clay as a video only for a shot on LTX-2.5. They stay with the shot under its passes folder, so a shot can go through a different model later. [code: studio/vset/passes.py:1-3, studio/vset/passes.py:153-156] [test: tests/vset/test_passes.py]

Virtual Set depth pass: near is white, far and sky are black, linear from 0.3 m to the farthest corner of the place seen from any camera position, capped at 80 m. Depth and ids use one sample, no denoiser and no dither. [code: studio/vset/passes.py:19-20, studio/vset/passes.py:30-33, studio/worldkit/blender_scripts/vs_scene.py:3-4]

Virtual Set pose pass: OpenPose BODY_18 skeletons are drawn from the rig's joints with the same camera maths as the render. Nose, eyes and ears are placed on the head with fixed adult proportions. With no cast the pose pass is black frames. [code: studio/vset/passes.py:23-27, studio/vset/passes.py:40-57, studio/vset/passes.py:3] [test: tests/vset/test_passes.py]

Virtual Set passes run on CPU Cycles at 16 samples by default, with a 6 hour limit. On the test machine a 5 s shot at 1344 x 768 took about 19 minutes on 16 threads with other jobs running. [code: studio/vset/passes.py:21-22, studio/worldkit/blender.py:189-209] [docs: studio/processes/virtual-set.md]

## Rendering and retries

Virtual Set rendering runs the scene step, then the mode's ComfyUI jobs, then QC on the CPU. A failed video or a failed QC gets one automatic reroll with the seed plus one. Passes and keyframes are kept, and shot.json records the seed that made the final video. [code: studio/vset/runner.py:1-2, studio/vset/runner.py:17, studio/vset/runner.py:84-89] [test: tests/vset/test_runner.py]

Virtual Set Render video keeps finished passes because saving a changed shot clears its state. Render passes clears the state and rerenders them. Retry resumes from the step that did not finish. Cancel stops a render and kills Blender through its own process group. [code: studio/vset/api.py:153, studio/vset/api.py:157-162, studio/vset/api.py:175-184, studio/vset/api.py:190-208, studio/worldkit/blender.py:139-147]

## Quality check

Virtual Set QC scores flicker on 24 consecutive frames from the middle of the video: second-order frame difference, so smooth motion scores near 0 and strobing scores high. Above 6.0 fails. Layout is edge overlap with the Blender edge pass, a number for review that never fails a shot. [code: studio/vset/qc.py:1-3, studio/vset/qc.py:15, studio/vset/qc.py:18, studio/vset/qc.py:55-59, studio/vset/qc.py:112-113, studio/vset/qc.py:123-136] [test: tests/vset/test_qc.py]

## Shot lists

Virtual Set shot lists turn a script into up to 12 shots, one per line, in one set under one look. Numbering is stripped. Camera words pick the move, for example "orbit" or "tracking", otherwise moves rotate through push_in, walk_along and orbit. Seeds step by 101. [code: studio/vset/shotlist.py:15-23, studio/vset/shotlist.py:27-41, studio/vset/shotlist.py:44-53] [test: tests/vset/test_shotlist.py]

## API and storage

Virtual Set routes: GET meta and capabilities, POST camera, GET and POST shots, GET one shot and its files by a fixed name, POST a shot's render, passes, retry or cancel, GET and POST lists, POST a list's order or render. All sit under /api/vset. [code: studio/vset/api.py:311-385]

Virtual Set stores shots and lists under the STUDIO_VSET_ROOT setting. The default is a parametric-studio/vset folder under the home folder's .local/share, so a missing ComfyUI never moves them. [code: studio/vset/__init__.py:8-13]
