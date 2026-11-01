# Designers: playbook

State of the data: 2026-11-01. [code: studio/packs/packs.json]

## What the Design page is

The Design tab holds designers: forms that turn a few choices into one prompt per view, then render those prompts as a sheet of pictures. Rendering is the ordinary /api/generate path, one job per view. [code: studio/packs.py:1-2, studio/web/app.js:279, studio/web/extras.js:137-148]

There are 13 designers. The first three tiles are character, fashion and vehicle. The others are tshirt, mug, printify, setting, animal, plant, hair, nail, furniture and cosplay. [code: studio/packs.py:26-27] [test: tests/test_studio_packs.py]

## Each designer's size

Designer choice groups and views, part 1: T-shirt studio 11 groups, 12 views. Mug studio 10 and 12. Print-on-demand products 5 and 8. Vehicle builder 11 and 14. Setting designer 9 and 11. Animal designer 16 and 10. Plant designer 14 and 10. [code: studio/packs/packs.json, studio/packs.py:15-21]

Designer choice groups and views, part 2: Hair designer 10 and 10. Nail designer 8 and 11. Furniture designer 10 and 14. Original costume designer 11 and 11. Character designer 14 and 10. Fashion designer 7 and 11. Across all 13 the data holds about 3,620 options. [code: studio/packs/packs.json]

The print-on-demand designer stored its views as an option group called swap_views, so it had 0 views. Loading moves those 2 into views and adds 6 generic ones, which gives it a sheet like the others. [code: studio/packs.py:11-14, studio/packs.py:15-21] [test: tests/test_studio_packs.py]

## What each one makes

Designer tile lines on the page: Character makes original characters, headshots to full body. Fashion "Outfits, shoes and accessories as a sheet". T-shirt "Tees and sweats, print by print". Mug "Mugs with your own artwork". Print-on-demand "Art on print-on-demand products". [code: studio/web/extras.js:122]

More designer tile lines: Vehicle "Cars, bikes and wild builds". Setting "Rooms, places and moods". Animal "Any animal, in any light". Plant "Houseplants to whole gardens". Hair "Cuts, colours and textures". Nail "Nail shapes, finishes and art". Furniture "Furniture in any style". Costume "Original costumes, armour to props". [code: studio/web/extras.js:122]

## How the prompt is built

The designer composer joins the view's words, the user's idea, each chosen option as "label: value", and a fixed tail. The tail asks for an original design with no real brand names, logos, badges or watermarks, and no readable text except the exact words given. [code: studio/packs.py:8, studio/packs.py:28-41] [test: tests/test_studio_packs.py]

Designer exact words work only on tshirt, mug and printify. The composer adds them as "The text reads exactly", cut to 80 characters. On other designers the words are ignored and the page shows no box. The idea text is cut to 300 characters. [code: studio/packs.py:9, studio/packs.py:38-39, studio/web/extras.js:155] [test: tests/test_studio_packs.py]

Designer choices are checked against the pack's own list: an unknown option or view returns 400, an unknown designer 404. Requests pass the studio's safe-for-work check first. [code: studio/packs.py:34, studio/packs.py:37, studio/packs.py:52-57] [test: tests/test_studio_packs.py]

## Which goals they use

The designer Model menu lists every goal of kind image that needs no input picture: image (FLUX.2 Klein 4B, the default), anime (Anima), product (FLUX.3 Klein), krea2 (Krea 2) and flux3 (FLUX.3 Klein). Product and flux3 are gated downloads. [code: studio/web/extras.js:131, studio/web/extras.js:136, studio/goals.py:140, studio/goals.py:143-146]

## How a user makes a sheet

Designer steps: open Design, pick a tile, optionally type an idea, set any choices (each defaults to "any"), toggle views (the first 3 start on), pick a model, then press Make. Views appear one by one. A view that fails shows "failed" and the rest carry on. [code: studio/web/extras.js:135, studio/web/extras.js:137-148, studio/web/extras.js:154-161]

The Processes tab can also open a designer: 5 process cards link to one, all marked as the closest match rather than the process itself. [run: studio/processes.json] [code: studio/web/processes.js:76]

## What rendered

Designer tile art is one real render per designer, 13 in all, from the designer's own composer: FLUX.2 Klein 4B base, 20 steps, goal image, mode quality, seed 11, made 2026-10-30, 14.0 to 18.9 s, peak at most 23.0 GiB on the test machine. [run: studio/web/designer_art/art.json]

## Tests

Designer tests check the data has no listed brand names or unsafe words, every group has at least 2 options, every designer has views, the composer rejects bad input, and the character and fashion rules hold. A page test checks labels exist. [test: tests/test_studio_packs.py, tests/test_look_design.py]
