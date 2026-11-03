# Virtual Set: pitfalls

## What is not proven

Virtual Set Wan 2.2 Fun Control, the pose pass and the Qwen keyframe steps are wired and tested with fakes, but they have not rendered on these passes. Do not promise a result from them. [docs: studio/processes/virtual-set.md] [test: tests/vset/test_modes.py]

Virtual Set modes B, C and D are recorded as rendered once in the guide, but this repo stores result clips only for H3 and LTX-2.5 in mode A. The comment at the top of mode D still says "Not yet run on Blender renders", which disagrees with the guide. Treat one street shot as all the evidence. [docs: studio/processes/virtual-set.md] [code: studio/vset/modes/motioncopy.py:2, studio/web/vset_example.js:1]

Virtual Set "Rendered here, checks passed" means a video exists and the automatic checks found nothing. It does not judge the picture. Passes-only renders do not count toward a video route. The status is read from shots on the user's own disk, so a fresh install shows no proof. [code: studio/vset/api.py:89-114, studio/web/virtualset.js:117] [test: tests/vset/test_api.py]

Virtual Set flicker limit 6.0 and set-consistency limit 0.6 are starting guesses until real videos have been judged. A pass does not mean the video looks good. [code: studio/vset/qc.py:3, studio/vset/qc.py:15-16]

## What the checks do not do

Virtual Set face match does not run. It needs a saved character in the shot and a face classifier handed in, the render never hands one in, and this studio ships none. The result says face_checked is false and the page says so. [code: studio/vset/qc.py:2-3, studio/vset/runner.py:30-33, studio/vset/runner.py:74, studio/web/virtualset.js:156] [test: tests/vset/test_runner.py]

Virtual Set safety reads words only: the shot's name, action and settings, a list's name and script, and the final prompt with words taken from assets. A Blender frame, a generated keyframe and a finished video are not checked by what they show. [code: studio/vset/shot.py:190-192, studio/vset/api.py:228-230, studio/vset/modes/common.py:44-47] [docs: studio/processes/virtual-set.md]

Virtual Set does not lock a face. H3's control has no identity input, and in mode D the reference picture is the first shaded still, not a character's sheet. [code: studio/vset/modes/restyle.py:2, studio/vset/modes/motioncopy.py:1] [docs: studio/processes/virtual-set.md]

## What gets refused

Virtual Set refuses a format outside the route's limits. Modes A and B are 5 s only, and Wan and LTX-2.5 refuse 1:1. The page's Length list always offers 5, 8 and 10 s, then shows the refusal and keeps Render video off. [code: studio/vset/shot.py:122-134, studio/web/virtualset.js:82, studio/web/virtualset.js:130, studio/web/vset_helpers.js:76-81] [test: tests/vset/test_shot.py]

Virtual Set refuses a pose pass with no cast, because the pose pass would be black frames. The cast needs the character switch, which is off by default, so with the default setting mode A can only use depth or the LTX clay pass. [code: studio/vset/shot.py:148-151, studio/vset/shot.py:219-220, studio/worldkit/safety.py:53-58] [test: tests/vset/test_shot.py]

Virtual Set refuses a shot whose place, prop, character or look asset was archived or unapproved after saving, and it names the asset. Approve it again in World Kit, or pick another. A list refuses to start if any of its shots has this problem. [code: studio/vset/shot.py:91-103, studio/vset/runner.py:61-65, studio/vset/api.py:279-286] [test: tests/vset/test_runner.py]

Virtual Set checks marks against the place's bounds, but it does not check where the camera goes. A camera that starts inside a building gives black shaded frames at the start. Use the plan view, then change the marks or the distance. [code: studio/vset/shot.py:114-119, studio/vset/camera.py:115-141] [docs: studio/processes/virtual-set.md]

## Readiness gaps

Virtual Set route readiness reads files, not whether ComfyUI is running. The node check is skipped when ComfyUI does not answer, so a route can read ready and the video step then fails with "ComfyUI is not reachable". [code: studio/vset/needs.py:29-40, studio/worldkit/jobs.py:66-67]

## Render behaviour that surprises people

Virtual Set saves a rerolled seed into the shot, so the seed shown afterwards can be one higher than the seed typed. A video that fails twice ends "failed". A flicker failure twice ends in "review", not failed. QC that cannot run goes to review with no reroll. After a restart, Retry resumes a shot left in "building". [code: studio/vset/runner.py:3, studio/vset/runner.py:84-88] [test: tests/vset/test_runner.py]

Virtual Set lists have no cancel route. While a list renders, its shots are run directly and not registered as running shots, so a shot in the list reads as not running and its Retry and save are not blocked. This comes from reading the code and no test covers it. [code: studio/vset/runner.py:97, studio/vset/runner.py:155-156, studio/vset/api.py:379-385, studio/web/vset_helpers.js:94] [inference]

## Final session findings, 2026-11-03

Virtual Set's older pitfall that "the cast needs the character switch, which is off by default" no longer matches the code. Characters are on unless STUDIO_WORLDKIT_CHARACTERS is "0", so a default install can put a rigged character in a shot and use a pose pass in mode A. The pose pass itself has still not rendered, per the guide's status line. [code: studio/worldkit/safety.py:56-57] [docs: studio/processes/virtual-set.md]

Virtual Set's one cast shot shows the limit of steering by words. The face, some colours and the street's look came from the prompt, not from the character asset or the set. Expect the character's look to drift toward its description, and do not promise that a shot matches the World Kit figure. [docs: studio/processes/virtual-set.md]
