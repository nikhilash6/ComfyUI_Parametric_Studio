# World Kit: playbook

## What it is

World Kit is a shared library of real-scale 3D assets of four types: place, prop, character and look. Each asset gets a .glb where it has geometry, a turntable and a thumbnail. It opens from the World Kit button in the left rail. [code: studio/worldkit/__init__.py:1, studio/worldkit/library.py:20, studio/worldkit/preview.py:1-2] [docs: studio/processes/world-kit.md]

World Kit status from its guide: the place maker, looks, the library, approve, archive and the Godot pack ran on the test machine on the CPU with Blender. The prop maker ran from a mesh. Every maker step that needs a model is written and tested with fakes, and has not run on a real model through World Kit. [docs: studio/processes/world-kit.md]

World Kit sample builds shown on an empty shelf are the project's own tests, marked as such: a 40 x 24 m street, a 40 x 30 m boardwalk, a 10 x 8 m cafe, a 1.2 m knot sculpture and a golden hour look. They are not in a user's library. [code: studio/web/wk_example.js:1-7, studio/web/worldkit.js:170]

## Using the page

World Kit flow: New asset, pick the type, fill the form, Make it. The asset starts as a draft. Open it for the 3D viewer, turntable and step list, then Approve for sets. Approved assets can be used in Virtual Set or exported for a game. [code: studio/web/worldkit.js:47-76, studio/web/worldkit.js:118-125, studio/worldkit/library.py:59] [docs: studio/processes/world-kit.md]

## Library

World Kit keeps one folder per asset at root/type/id, holding asset.glb, preview.mp4, thumb.jpg and meta.json. Ids are 12 lowercase letters with no digits, because a digit run in a file name can read as an age to a text check. Search works by type, tag, name and status. [code: studio/worldkit/library.py:1-3, studio/worldkit/library.py:40-43, studio/worldkit/library.py:178-197] [test: tests/worldkit/test_library.py]

World Kit Approve works only on a finished build that passes validation. A character must be 1.5 to 2.0 m tall with a skin, at least 15 bones and all 17 humanoid slots. A prop must be 0.02 to 30 m across with a collider. A place must be at least 4 m across with a collider. A look needs a known preset. [code: studio/worldkit/library.py:239-248, studio/worldkit/library.py:251-254, studio/worldkit/library.py:257-298] [test: tests/worldkit/test_glb_rigmap_validate.py]

World Kit Archive moves the whole folder to _archive/type/id-stamp and deletes nothing. Unapprove sets the asset back to draft. [code: studio/worldkit/library.py:229-237, studio/worldkit/api.py:216-219] [test: tests/worldkit/test_library.py]

## Places

World Kit place maker turns a brief into a kit recipe by keywords: street, interior or beach, with time, weather, size, materials and seed. The same brief gives the same seed. Default sizes are 40 x 24 m, 10 x 8 m and 40 x 30 m, and each side may be 4 to 200 m. [code: studio/worldkit/makers/place.py:16-31, studio/worldkit/makers/place.py:44-67] [test: tests/worldkit/test_place_maker.py]

World Kit place build is procedural Blender: every solid gets a box collider named with -colonly, small parts are merged per material with no collider, and the same recipe builds the same place. It also makes four overview stills at 512 px, with a 2400 s limit. A place needs Blender and nothing else. [code: studio/worldkit/blender_scripts/wk_place.py:1-6, studio/worldkit/makers/place.py:37, studio/worldkit/makers/place.py:141-143, studio/worldkit/capabilities.py:78]

World Kit place textures are set by recipe "textures". "auto" uses the Image goal when its model is present and ComfyUI answers, otherwise procedural. "generated" always asks ComfyUI, and a failed picture falls back to procedural. "procedural" never asks a model. [code: studio/worldkit/makers/place.py:5-6, studio/worldkit/makers/place.py:90-94, studio/worldkit/capabilities.py:236-238] [test: tests/worldkit/test_place_maker.py]

World Kit texture code has two ways. make_tileable shifts a picture by half and cross-fades it to hide seams. procedural makes brick, planks, paving, tarmac, sand or plaster from numbers alone, and it wraps at the edges by construction. [code: studio/worldkit/textures.py:1-4, studio/worldkit/textures.py:13-24] [test: tests/worldkit/test_place_maker.py]

## Looks

World Kit looks are seven presets: day_clear, golden_hour, overcast, rainy, night_city, interior_day and interior_night. Time can be day, golden or night, and weather can be clear, overcast or rain. Worlds are Blender's bundled studio-light HDRIs, so nothing is downloaded. [code: studio/worldkit/looks.py:1-4, studio/worldkit/looks.py:9-10, studio/worldkit/looks.py:14-30]

## Props

World Kit props come from a studio 3D result, a picture or words. Words make a picture first, then a BiRefNet cut-out, then a mesh, then Blender cleanup. A picture with its own transparency skips the cut-out. A mesh goes straight to cleanup. Shap-E goes from words to a mesh with no picture. [code: studio/worldkit/makers/prop.py:1-3, studio/worldkit/makers/prop.py:107, studio/worldkit/makers/prop.py:125-131, studio/worldkit/makers/prop.py:157-160] [test: tests/worldkit/test_prop_maker.py, tests/worldkit/test_model3d.py]

World Kit prop mesh routes are tried in this order when the studio picks: SAM 3D Objects, TRELLIS.2, Pixal3D, Hunyuan3D 2, TripoSR. A user can choose one instead. Words to a picture use FLUX.2 Klein 4B, or Krea 2 Turbo when Klein is not there. [code: studio/worldkit/capabilities.py:80-82, studio/worldkit/capabilities.py:188-195, studio/worldkit/makers/prop.py:139] [test: tests/worldkit/test_model3d.py]

World Kit prop cleanup joins every mesh into one static object, drops armatures, scales the longest side to size_m, puts the pivot at the bottom centre and adds a box collider. Size comes from the recipe, or a hint word in the name such as car 4.5 m or chair 0.9 m, otherwise 1.0 m. [code: studio/worldkit/blender_scripts/wk_cleanup.py:1-6, studio/worldkit/makers/prop.py:24-38] [test: tests/worldkit/test_prop_maker.py]

## Characters in World Kit

World Kit characters are off by default behind STUDIO_WORLDKIT_CHARACTERS and come only from saved characters. See the Characters notes for what that chain does and what the picture check covers. [code: studio/worldkit/safety.py:53-58, studio/worldkit/api.py:118-126]

World Kit rigmap finds 17 humanoid slots from a rig's rest pose by geometry alone, because an auto-rigger may name bones bone_0 and so on. It trusts only bone heads. Virtual Set's pose pass and approval both use it. [code: studio/worldkit/rigmap.py:1-4, studio/worldkit/rigmap.py:10-12] [test: tests/worldkit/test_glb_rigmap_validate.py]

World Kit runners are two small scripts in worldkit/runners, Shap-E and TripoSR, run in their own process. The data folder holds one file, soma77_slots.json, the slot map the retarget tool uses for a Kimodo BVH, because its leg names differ from Mixamo's. [code: studio/model3d.py:72-78, studio/worldkit/tools.py:144-150, studio/worldkit/data/soma77_slots.json:2]

## Steps, jobs and retries

World Kit builds are ordered steps, each a ComfyUI job or a local step, with state in meta["build"]. A failed rig keeps the mesh, the error names the step, and Retry reruns only what did not finish. An optional step that fails is noted and the build continues. [code: studio/worldkit/steps.py:1-6, studio/worldkit/steps.py:151-160] [test: tests/worldkit/test_steps.py]

World Kit jobs come in three kinds: a goal (the same call as POST /api/generate), a graph from workflows/ on the main ComfyUI, and a family template on its own instance. Waiting polls every 3 s up to 6 hours. A job missing from queue and history for 90 s counts as interrupted. [code: studio/worldkit/jobs.py:1-5, studio/worldkit/jobs.py:22-24, studio/worldkit/jobs.py:181-184] [test: tests/worldkit/test_jobs.py]

Every World Kit asset ends with two steps: a turntable of 72 frames at 24 fps and 512 px with a 384 px thumbnail, then ingest, which copies the files into the library and records scale, rig, clips and colliders. Props and characters are shown under the day_clear look. [code: studio/worldkit/preview.py:9-14, studio/worldkit/preview.py:18-19, studio/worldkit/preview.py:28, studio/worldkit/preview.py:58-76] [test: tests/worldkit/test_preview.py]

## Blender

World Kit runs Blender headless with --factory-startup, using half the cores unless told otherwise. A script prints one PPWK result line. A run past its timeout or a cancel is killed through its own process group by pid, first SIGTERM and then SIGKILL. [code: studio/worldkit/blender.py:1-3, studio/worldkit/blender.py:38-43, studio/worldkit/blender.py:122-132] [test: tests/worldkit/test_blender_runner.py]

World Kit forces CPU three ways: the GPU is hidden from the process, Cycles is told to use the CPU, and the scripts set the device. STUDIO_WORLDKIT_GPU is off by default. With it set to 1, a render tries EEVEE when 2.5 GiB plus the 4 GB floor is free, and falls back to CPU Cycles if EEVEE fails. [code: studio/worldkit/blender.py:5-7, studio/worldkit/blender.py:27, studio/worldkit/blender.py:189-209, psn/instances.py:13] [test: tests/worldkit/test_blender_runner.py]

## What each maker needs

World Kit capabilities read the disk on every call, so a model that lands shows up with no restart. A file counts only at its smallest believable size, and a partial file reads as downloading. Each need answers ready, downloading, missing or tool, in a sentence the page shows as it stands. [code: studio/worldkit/capabilities.py:1-3, studio/worldkit/capabilities.py:122-136, studio/worldkit/capabilities.py:152-185] [test: tests/worldkit/test_capabilities.py]

World Kit third-party tools each keep their own folder and environment, found through STUDIO_TOOL_NAME settings, and run as a subprocess with a timeout. Nothing from them is imported. GPU tools ask for room above the VRAM floor first and never evict anything. The check also reads a launcher to catch a weights folder that is gone. [code: studio/worldkit/tools.py:1-3, studio/worldkit/capabilities.py:90-95, studio/worldkit/capabilities.py:105-119] [test: tests/worldkit/test_tools.py, tests/worldkit/test_capabilities.py]

## Export for a game

World Kit export writes a folder and a .zip under _exports: the approved .glb files, manifest.json (worldkit-pack/1), scenes/main.tscn for Godot 4 and IMPORT.txt. With no placements, the first place sits at the origin and props and characters stand in a row. Blender (x, y, z) becomes Godot (x, z, -y). [code: studio/worldkit/export.py:1-10, studio/worldkit/export.py:41-44, studio/worldkit/export.py:85-98, studio/worldkit/export.py:133-193] [test: tests/worldkit/test_export.py]

## API and settings

World Kit routes sit under /api/worldkit: assets (list, create, get, a fixed list of files, and retry, cancel, approve, unapprove, archive, as-prop, clips), looks, characters, capabilities, meshes, export and exports. [code: studio/worldkit/api.py:278-359]

World Kit settings: STUDIO_WORLDKIT_ROOT for the library (default a parametric-studio/worldkit folder under the home folder's .local/share), STUDIO_WORLDKIT_WORK for scratch, STUDIO_BLENDER, STUDIO_WORLDKIT_THREADS, STUDIO_WORLDKIT_GPU (off) and STUDIO_WORLDKIT_CHARACTERS (off). [code: studio/worldkit/__init__.py:8-19, studio/worldkit/blender.py:30-43, studio/worldkit/safety.py:53-54]

## Final session findings, 2026-11-03

World Kit turntables frame every asset that is not a place by its bounding sphere, since 2026-11-02. The sphere is centred on the bounds' centre with the farthest vertex as its radius, and the camera stands where the sphere plus a 12% margin just fits the narrower field of view. A sphere looks the same from every side, so the fit holds through the whole orbit, for a 5 cm ring and a 40 m tower alike. [code: studio/worldkit/blender_scripts/_fit.py:1-7, studio/worldkit/blender_scripts/_fit.py:10, studio/worldkit/blender_scripts/_fit.py:25-28] [test: tests/worldkit/test_turntable_fit.py]

World Kit turntable details from the same change: an asset whose height is under a quarter of its longest side is looked down on at least about 42 degrees, so its top shows. The near clip follows the camera distance, because Blender's 10 cm default would cut off a small ring. Places and interiors keep their own framing. [code: studio/worldkit/blender_scripts/_fit.py:12-13, studio/worldkit/blender_scripts/_fit.py:40-49, studio/worldkit/blender_scripts/wk_turntable.py:117-127] [test: tests/worldkit/test_turntable_fit.py]

World Kit turntable frames no longer hint at size: a ring and an anchor both fill the frame. The page's "Real scale" tag gives the asset's longest side instead. [code: studio/worldkit/blender_scripts/wk_turntable.py:6-7, studio/web/worldkit.js:159]

World Kit look previews show a small lit street corner since 2026-11-02. A look has no geometry of its own, and the old tiny test set gave a plain sky card for golden hour and overcast and pure black for night and rain. The set is now ground whose roughness follows the look's wetness, three blocks of different heights and colours, a matte ball and a mirror ball. Night looks get three street lamps, and fog sits in a 40 m box around the set instead of in the world. [code: studio/worldkit/blender_scripts/wk_turntable.py:36-79, studio/worldkit/blender_scripts/wk_turntable.py:102]

World Kit look preview camera: it swings to and fro in front of the blocks at 1.5 m height, 6.5 m out, so the sky and the light both show and the clip loops. In the merged script this branch comes before the bounding-sphere branch, so a look never reaches the sphere fit even though that branch's comment still mentions a look's test scene. [code: studio/worldkit/blender_scripts/wk_turntable.py:128-136] [inference]

World Kit look recipes were re-rendered after that fix. Six of the seven look renders in recipe_renders.json are dated 2026-11-02 (golden hour, overcast, rainy, night city, interior day, interior night), from 50.0 to 161.1 s each, with no GPU peak because Blender runs on the CPU. [run: studio/recipe_renders.json]

World Kit characters are on by default in the current code, and their mesh step is TRELLIS.2, not SAM 3D Body. See the Characters notes for the whole change. The older paragraph saying World Kit characters are off by default is out of date. [code: studio/worldkit/safety.py:56-57, studio/worldkit/makers/character.py:1-5] [docs: studio/processes/world-kit.md]

World Kit shows licence limits where models are picked since 2026-11-02. The character form says Krea 2 allows commercial use only for companies under US$1,000,000 yearly revenue and that the picture check's InsightFace buffalo_l weights are for non-commercial research. The prop licence line now notes that Hunyuan3D is not for use in the EU, UK or South Korea. [code: studio/web/worldkit.js:76, studio/worldkit/api.py:23-24]

World Kit text links, small buttons, selects, inputs and disclosure summaries reach a 40 px tap area since 2026-11-02, and the World Kit showpiece carries the shared hero light. No wording or data changed. [code: studio/web/worldkit.css:167-170, studio/web/polish.css:74-83]
