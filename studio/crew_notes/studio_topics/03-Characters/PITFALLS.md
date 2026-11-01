# Characters: pitfalls

State of these notes: 2026-11-01. Tests named here use stubs: no test picture shows a person. They were read for these notes, not run. [code: tests/worldkit/test_picturecheck.py:1]

## What the picture check does not do

The Characters picture check cannot tell a real person from an invented one. Nothing can tell whether a finished sheet looks like a real person. The word check catches only plain ways of asking, and a plain name cannot be told from an invented one. [code: studio/worldkit/picturecheck.py:7, studio/worldkit/safety.py:10, studio/worldkit/safety.py:48-50]

The Characters picture check reads apparent age as an estimate with an error of years, from a model trained on photographs. A young adult can be refused. A stylised or drawn face, or a youthful face read as older, can pass. [code: studio/worldkit/picturecheck.py:7-8]

The Characters picture check sees uncovered areas only. It does not judge a pose, a framing or sheer clothes. It looks at the sheet only, not at the mesh and not at any later frame or video. [code: studio/worldkit/picturecheck.py:8]

The Characters picture check's catch rate has never been measured, by design: no test picture of that kind is ever made or sought. Only its rate of refusing harmless pictures was measured, and that figure is not in this repo. [code: studio/worldkit/picturecheck.py:8-9, tests/worldkit/test_picturecheck.py:1]

## What the switch does not cover

The Characters switch is checked when saving a character, building a sheet, creating a character asset, at the maker's sheet step, and when a shot has a cast. It is not checked on Retry, adding clips, Approve, as-prop or export. A build past its sheet step can continue with the switch off. Read from the code, no test covers it. [code: studio/worldkit/characters.py:94-96, studio/worldkit/characters.py:124, studio/worldkit/api.py:118-121, studio/worldkit/api.py:198-237, studio/worldkit/makers/character.py:79-83, studio/vset/shot.py:148-151, studio/worldkit/export.py:133] [inference]

Other character features in the studio do not go through this switch or check. The Recast goal takes a character picture directly. The Character Maker designer on the home page and the character-sheet guide from the earlier studio are separate things and do not write saved characters. [code: studio/goals.py:122-124, studio/goals.py:152, studio/web/app.js:180] [docs: studio/processes/character-sheet.md]

## Getting stuck

A saved character has no retry route. The sheet build starts only when the character is created, so a blocked or failed one must be deleted and made again, which gives a new id and a new seed. A restart during a sheet build appears to leave it at "building" for the same reason. [code: studio/worldkit/api.py:86-92, studio/worldkit/api.py:316-324, studio/worldkit/characters.py:117, studio/worldkit/characters.py:127] [inference]

A saved character's POST route does not check that Krea 2 or the picture check tool is present. With no picture check tool the sheet ends "blocked" with "could not run". With ComfyUI or the model missing it ends "failed". [code: studio/worldkit/api.py:78-87, studio/worldkit/characters.py:128-146] [test: tests/worldkit/test_picturecheck.py]

The Characters word check refuses any word for a young person in a saved character's name or description, and "boy", "girl", "kid" and "baby" count even in a harmless phrase. Reword rather than retry. [code: studio/worldkit/safety.py:18, studio/worldkit/safety.py:21, studio/worldkit/safety.py:40-45] [test: tests/worldkit/test_safety.py]

## Build limits

The Characters maker labels AutoRemesher optional, but its default recipe has remesh on, the step is not optional, and the route check does not list it. The page sends no recipe, so a page build with no AutoRemesher reads ready and then fails at Remesh. The API can send remesh false. [code: studio/worldkit/capabilities.py:46, studio/worldkit/capabilities.py:79, studio/worldkit/makers/character.py:20, studio/worldkit/makers/character.py:106-107, studio/web/worldkit_helpers.js:52] [inference]

The Characters default body has no colour. SAM 3D Body gives an untextured body with proportions, not clothes or hair, and AutoRemesher's quad levels drop UVs and colour. Expect a plain figure in the shaded pass. [code: studio/worldkit/makers/character.py:4-5, studio/worldkit/tools.py:126]

The Characters body graph is not the graph that ran. The recorded SAM 3D Body run took a generated clip and gave a pose file with no peak memory recorded. The maker's own graph takes the sheet and has no recorded run. [code: studio/worldkit/makers/character.py:16] [run: studio/model3d_proof.json]

Characters SkinTokens and AniGen rigs were looked at and called not finished: skin weights tear or stretch in a hard pose on rough meshes. Those runs used a bear mesh, not a person. AniGen is not a route in the character maker. [run: studio/model3d_proof.json] [code: studio/worldkit/makers/character.py:15]

A character can finish with no clips if every motion fails, and it can still be approved, because approval does not ask for clips. A shot then refuses it, since a cast member must name a clip the character has. [code: studio/worldkit/library.py:277-286, studio/vset/shot.py:161-163] [test: tests/worldkit/test_character_maker.py]

## In a render

Characters are not held to a face in video. H3's control has no identity input, mode D's reference picture is the first still, and the face match in QC never runs because no classifier is handed in. Nothing here locks a face between shots. [code: studio/vset/modes/restyle.py:2, studio/vset/modes/motioncopy.py:1, studio/vset/runner.py:30-33] [docs: studio/processes/virtual-set.md]

Characters in frames and videos are not checked by what they show. The safety text states this plainly: the check covers the sheet and the words, and it does not cover a mesh or a later frame. [code: studio/worldkit/safety.py:7-10, studio/worldkit/picturecheck.py:8] [docs: studio/processes/virtual-set.md]

Characters stay off until someone turns them on. The off message says the studio cannot yet check what a character mesh shows, only the words around it. [code: studio/worldkit/safety.py:24-25]
