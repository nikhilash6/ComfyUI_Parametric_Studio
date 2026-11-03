# World Kit: pitfalls

## What is not proven

World Kit model steps are written and tested with fakes, but they have not run on a real model through World Kit. Some of the same models ran on the 3D page, which is separate evidence about the model and not about the maker's chain. [docs: studio/processes/world-kit.md] [run: studio/model3d_proof.json]

World Kit's Godot scene has not been opened in Godot. The pack's files and text format are tested. Whether it imports cleanly is not proven. [docs: studio/processes/world-kit.md] [test: tests/worldkit/test_export.py]

World Kit look numbers are starting points chosen by eye, not measured. The licence of Blender's bundled HDRIs was not checked. Licence notes on assets are informational and never a gate. [code: studio/worldkit/looks.py:3-4, studio/worldkit/api.py:21-27]

World Kit's guide lags the code in places. It names SAM 3D Objects, Pixal3D and Hunyuan3D for picture to mesh, while the code also has TRELLIS.2 and TripoSR. It says there is no character builder, while routes for one now exist. Trust the code. [docs: studio/processes/world-kit.md] [code: studio/worldkit/capabilities.py:80, studio/worldkit/api.py:316-319]

## What the checks do not see

World Kit reads words only for places, props and looks: names, tags, briefs, prompts and clip text. A picture added for a prop, a generated prop picture and a finished mesh are not checked by what they show. [code: studio/worldkit/safety.py:3-8, studio/worldkit/api.py:115-117]

## Choices that surprise people

World Kit "the studio picks" takes the first ready mesh route, and SAM 3D Objects comes first although it has no recorded run. On a machine with its files, an unproven model is used by default. Pick a model by hand if a proven one matters. [code: studio/worldkit/capabilities.py:80, studio/worldkit/capabilities.py:188-190] [run: studio/model3d_proof.json]

World Kit prop size is guessed from a word in the name, and it falls back to 1.0 m. A prop named "statue" comes out 1.0 m long on its longest side. Check the scale tag or type a size. [code: studio/worldkit/makers/prop.py:29-38, studio/web/worldkit.js:127]

World Kit cleanup drops armatures, so a rigged mesh made into a prop loses its rig. A Hunyuan3D prop has shape and no colour. [code: studio/worldkit/blender_scripts/wk_cleanup.py:3-4, studio/model3d.py:13]

World Kit place planning is keyword only. A brief with no kit word falls back to the street kit with a note in the recipe. "Rainy" picks the rainy look before any time word, so a rainy night brief gets the rainy preset with time set to night. [code: studio/worldkit/makers/place.py:47-48, studio/worldkit/makers/place.py:57-58, studio/worldkit/makers/place.py:62]

World Kit's list of 3D results reads only the main output folder and shows at most 50 files, newest first. A .glb that a family template left in its own instance folder is not offered as a prop source. Models run from the 3D page land in the output folder, so they are offered. [code: studio/worldkit/api.py:333-341, studio/glb.py:360, studio/model3d.py:50-52, studio/server.py:364-367]

## Failures and how they read

World Kit GPU tools stop with a sentence rather than evict: "Nothing was evicted; press Retry when there is room." Blender defaults to one fixed program path, so on another machine set STUDIO_BLENDER, or the page says Blender is not installed. [code: studio/worldkit/tools.py:26-29, studio/worldkit/blender.py:30-31, studio/worldkit/capabilities.py:221-225]

World Kit lists UniRig as a need but does not wire it. Its weights can be present and nothing runs them, because the maker rigs with SkinTokens. [code: studio/worldkit/capabilities.py:45] [docs: studio/processes/world-kit.md]

## Final session findings, 2026-11-03

World Kit's older pitfall that the guide "says there is no character builder" is resolved. The guide now describes the character route (Krea 2 sheet, picture check, TRELLIS.2, SkinTokens, a motion per clip) and says a character ran from words to a rigged, textured figure with three motions on real models. [docs: studio/processes/world-kit.md]

World Kit's new turntable and look preview framing is covered by a maths test that needs no Blender, but no stored turntable in the repo was filmed and compared before and after it. The six look recipe renders dated 2026-11-02 are the only render evidence. [test: tests/worldkit/test_turntable_fit.py] [run: studio/recipe_renders.json] [inference]
