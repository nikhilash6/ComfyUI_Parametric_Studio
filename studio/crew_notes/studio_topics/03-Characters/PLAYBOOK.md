# Characters: playbook

State of these notes: 2026-11-01, read from the source of this repo. [code: studio/worldkit/characters.py:1-3]

## The switch

Characters are off by default. STUDIO_WORLDKIT_CHARACTERS must be exactly "1", in the environment or the machine's settings file. With it off, nothing can be created or built, and places, props and looks still work. [code: studio/worldkit/safety.py:24-25, studio/worldkit/safety.py:53-58] [test: tests/worldkit/test_character_maker.py]

Characters status on 2026-11-01: the chain is written and tested with stubs. This repo holds no recorded run of a saved character or a built character asset, and no recorded run of the real picture check. Parts ran alone: see the 3D family notes. [test: tests/worldkit/test_character_maker.py, tests/worldkit/test_picturecheck.py] [run: studio/model3d_proof.json]

## Saved characters

A saved character is a folder under the library's _characters, with character.json and body_front.png. It is made from a name of up to 60 characters and a description of up to 400. The route refuses any other field, so no photo or upload can be handed in. [code: studio/worldkit/characters.py:1-2, studio/worldkit/characters.py:20-21, studio/worldkit/characters.py:40-41, studio/worldkit/api.py:78-87] [test: tests/worldkit/test_picturecheck.py]

A saved character has one of five statuses: draft (words saved), building, ready (the sheet passed the picture check), blocked (it did not), failed (it could not be made). Only ready, with a stored pass for that exact file, can become a 3D character. [code: studio/worldkit/characters.py:3, studio/worldkit/characters.py:63-76] [test: tests/worldkit/test_picturecheck.py]

A saved character's sheet is made by Krea 2 Turbo on the main ComfyUI at 832 x 1216, from a fixed prompt around the description: an invented adult, fully clothed, full body in frame, face clearly visible, plain grey background. The seed comes from the character's id. [code: studio/worldkit/characters.py:22-23, studio/worldkit/characters.py:113-117] [test: tests/worldkit/test_picturecheck.py]

A saved character is created through POST /api/worldkit/characters, listed by GET and removed by DELETE. The page has no form that creates one: it only reads the list and offers ready ones in the New asset form, with the reason beside any that cannot be used. [code: studio/worldkit/api.py:311-324, studio/web/worldkit.js:29, studio/web/worldkit.js:53-56]

## The picture check

The Characters picture check is a blunt rule: a sheet must show a readable face that reads as an adult, and nothing unclothed. A sheet that cannot be read, or a check that cannot run, does not pass. [code: studio/worldkit/picturecheck.py:1-2, studio/worldkit/picturecheck.py:95-107] [test: tests/worldkit/test_picturecheck.py]

The Characters picture check numbers: at least one face scoring 0.5 or more, and every such face must read as apparent age 20 or over. Unclothed body areas are refused from per-class scores of 0.2 to 0.5, strict because a sheet is asked for fully clothed. [code: studio/worldkit/picturecheck.py:21-22, studio/worldkit/picturecheck.py:26, studio/worldkit/picturecheck.py:39-52] [test: tests/worldkit/test_picturecheck.py]

The Characters picture check runs run_picturecheck.sh from the tool's own folder (STUDIO_TOOL_PICTURECHECK) on the CPU, with a 300 s limit: InsightFace buffalo_l for faces and apparent age, and a second local detector for unclothed areas. That tool is not shipped in this repo. [code: studio/worldkit/picturecheck.py:4, studio/worldkit/picturecheck.py:23, studio/worldkit/picturecheck.py:55-64, studio/worldkit/capabilities.py:99]

The Characters picture check has an optional second opinion from a local vision model. It is off by default (STUDIO_WORLDKIT_VISION_CHECK=1 turns it on, with a URL and a model setting). When on, its failure, doubt or unanswered question refuses, and it also asks whether the picture shows a real, famous person. [code: studio/worldkit/picturecheck.py:4-5, studio/worldkit/picturecheck.py:27-28, studio/worldkit/picturecheck.py:67-92] [test: tests/worldkit/test_picturecheck.py]

The Characters picture check stores a record with the file's sha256 and the rule's version. A pass counts only for that exact file and version, and a swapped file stops counting. A sheet that fails is deleted and only the reason is kept. [code: studio/worldkit/picturecheck.py:110-115, studio/worldkit/characters.py:138-143] [test: tests/worldkit/test_picturecheck.py]

## The word checks

Characters word checks are stricter than the rest of World Kit. A saved character's own words may not contain any word for a young person, on top of the studio's safe-for-work list. Words that plainly ask for a real person's likeness are refused too, such as "looks like" or "based on". [code: studio/worldkit/safety.py:18-22, studio/worldkit/safety.py:40-50] [test: tests/worldkit/test_safety.py, tests/worldkit/test_picturecheck.py]

## From sheet to 3D character

The Characters maker runs: sheet, then SAM 3D Body for the mesh, AutoRemesher, SkinTokens for the rig, one Kimodo motion and one retarget per clip, then Blender assemble, turntable and library. The recipe can use SAM 3D Objects for the mesh, which keeps colour, and can turn remesh off. [code: studio/worldkit/makers/character.py:1-5, studio/worldkit/makers/character.py:15, studio/worldkit/makers/character.py:104-112] [test: tests/worldkit/test_character_maker.py]

The Characters maker defaults to height 1.7 m (1.5 to 2.0 allowed) and three clips: idle, walk and wave, each 5 s. A character takes up to 4 clips with lowercase names. A failed motion or retarget is optional, so that clip is left out and the build goes on. A failed rig stops the build and keeps the mesh. [code: studio/worldkit/makers/character.py:17-23, studio/worldkit/makers/character.py:68-69, studio/worldkit/library.py:251] [test: tests/worldkit/test_character_maker.py]

The Characters route needs Krea 2, the picture check tool, SAM 3D Body, SkinTokens, Kimodo and the retarget tool. GPU gates add the 4 GB floor to 6 GB for SkinTokens and 17 GB for Kimodo, and they never evict anything. [code: studio/worldkit/capabilities.py:79, studio/worldkit/tools.py:15, studio/worldkit/tools.py:26-29, psn/instances.py:13] [test: tests/worldkit/test_picturecheck.py]

A character whose rig failed can become a static prop through "Use as a static prop". It is never a cast member, because a cast member needs a complete rig. [code: studio/worldkit/api.py:185-195, studio/web/worldkit_helpers.js:36-40, studio/vset/shot.py:158-160]

## How characters reach renders and other pages

Characters reach Virtual Set as cast: up to 2 approved, rigged characters, each with a clip and marks. The first one's marks are what the camera follows, and it is hidden in the pov preset. The page shows the Cast section only when the switch is on. [code: studio/vset/shot.py:35, studio/vset/shot.py:78-81, studio/vset/shot.py:147-166, studio/vset/passes.py:109, studio/web/virtualset.js:108-113]

Characters reach the video prompt as words: the saved name and the first 200 characters of the description, in every mode. Mode C and first-frame edits add "The person is" and those words. That final prompt goes through the word check again. [code: studio/vset/modes/common.py:17-24, studio/vset/modes/common.py:32-36, studio/vset/modes/common.py:44-47, studio/vset/modes/keyframes.py:21]

Characters reach the pose pass from the rig's joints, drawn as OpenPose skeletons that can drive mode A on H3 or Wan. A pose pass has not rendered yet. [code: studio/vset/passes.py:40-71, studio/vset/modes/guide.py:21-37] [docs: studio/processes/virtual-set.md]

Characters are also an exported asset type: an approved character's .glb goes into a Godot pack with its AnimationPlayer clips listed in the manifest. The Pro, API and Apps pages list the body graph with a note that the maker is off by default. [code: studio/worldkit/export.py:29-32, studio/worldkit/export.py:121-126, studio/graph_registry.py:1, studio/graph_registry.py:17]

## Final session findings, 2026-11-03

Characters are on by default in the current code. The older notes say STUDIO_WORLDKIT_CHARACTERS must be exactly "1"; now characters are off only when that setting is "0". Every check still runs: the word checks, the young-person rule, the likeness refusal, the picture check, and no upload route. [code: studio/worldkit/safety.py:24, studio/worldkit/safety.py:56-57] [test: tests/worldkit/test_character_maker.py, tests/worldkit/test_picturecheck.py]

The Characters maker's default mesh is TRELLIS.2, which gives a textured mesh of the whole figure with clothes, hair and colour. The default recipe is mesh trellis2, remesh off and height 1.7 m. A recipe can still ask for sam3d_body, a plain untextured body baked to a surface first, or sam3d_objects, which keeps colour but needs a cut-out sheet and has not run. This replaces the older paragraph that names SAM 3D Body and AutoRemesher as the default chain. [code: studio/worldkit/makers/character.py:1-5, studio/worldkit/makers/character.py:15, studio/worldkit/makers/character.py:21] [test: tests/worldkit/test_character_maker.py]

The Characters route now needs Krea 2, the picture check tool, TRELLIS.2 on the main ComfyUI (its model, two VAEs, DINOv3 and BiRefNet), SkinTokens, Kimodo and the retarget tool. A sheet alone needs only Krea 2 and the picture check. [code: studio/worldkit/capabilities.py:41, studio/worldkit/capabilities.py:80]

Characters have an "Another take" route: POST /api/worldkit/characters/<id>/again. It makes a new sheet from the same words with the next seed (the id's seed plus the take number), and every check runs again on the new picture. The old sheet stays until the new one has passed or failed. The older notes say a saved character has no retry route; that is out of date. [code: studio/worldkit/api.py:98-113, studio/worldkit/api.py:370-372, studio/worldkit/characters.py:118, studio/worldkit/characters.py:150-151] [test: tests/worldkit/test_picturecheck.py]

Characters cut off by a restart now read "interrupted": a sheet marked building with no thread behind it is listed that way, and it can be tried again. The list also carries the plain limits text of what the checks cannot catch. [code: studio/worldkit/api.py:68-77] [test: tests/worldkit/test_picturecheck.py]

Characters refuse at the door when the picture model or the picture check tool is missing: the create and again routes answer 409 with the reason and nothing is made. The older pitfall that the POST route does not check for them is out of date. [code: studio/worldkit/api.py:80-96] [docs: studio/processes/world-kit.md]

Characters ran end to end on real models, per the World Kit guide: from words to a rigged, moving, textured figure in the sheet's clothes, hair and colour, with three motions. The back and sides are the model's guess. The page lists what is still rough: clothes can pull when it moves, trouser legs can stay joined near the ankles, and feet stay flat and only turn. No run record for it is stored in the repo; the guide and README are the evidence. [docs: studio/processes/world-kit.md, README.md]

Characters in a Virtual Set shot reach the prompt as the whole saved description plus the line "Fully clothed exactly as described, from start to finish", not the first 200 characters. One cast shot rendered (mode A, H3, depth pass): the face, some colours and the street's look came from the words, not the character. [code: studio/vset/modes/common.py:11, studio/vset/modes/common.py:18-33] [docs: studio/processes/virtual-set.md]

Characters' licence note on the form, added 2026-11-02: the sheet is drawn by Krea 2, which allows commercial use, outputs included, only for companies under US$1,000,000 yearly revenue. The picture check reads age with InsightFace buffalo_l, whose weights are for non-commercial research only, and the page says to replace it before any commercial use. [code: studio/web/worldkit.js:76, studio/worldkit/api.py:23]

Characters and try-on are separate things. The try-on panel on the Fashion designer dresses a person picture in a garment picture; its default, when ready, is FLUX.2 Klein 4B with a try-on LoRA (template klein4b_tryon), recorded once at 66.2 s and 21.2 GiB. It takes uploaded pictures, writes no saved character, and has no identity input. [code: studio/tryon.py:1-2, studio/tryon.py:12, studio/tryon.py:46-48] [run: studio/family_status.json] [docs: studio/family_templates/klein4b_tryon.json]
