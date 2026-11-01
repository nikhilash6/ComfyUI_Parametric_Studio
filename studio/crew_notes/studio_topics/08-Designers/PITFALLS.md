# Designers: pitfalls

State of the data: 2026-11-01. [code: studio/packs/packs.json]

## What is not proven

Designer renders on record are only the 13 tile pictures, all on the image goal in quality mode. No stored record shows a designer sheet rendered on anima, product, krea2 or flux3. Those are wired through the menu, never rendered from a designer on record. [run: studio/web/designer_art/art.json] [code: studio/web/extras.js:136]

Designer tests do not render. They check data, the composer and page wording with no GPU. No test runs the Make button through to a picture. [test: tests/test_studio_packs.py, tests/test_look_design.py]

Each designer tile shows our own render, and the page says so: "Our own render from this designer, not yours". Only one view of each designer rendered for its tile, so the other views have no render on record. [code: studio/web/extras.js:160] [run: studio/web/designer_art/art.json]

## Why a sheet can differ from the tile

A designer sheet defaults to a faster build than the tile. The page sends empty options, so the image goal uses its defaults: aspect 1:1, mode fast, which is the distilled build at 4 steps. The tile used mode quality at 20 steps, and many tiles used 2:3. [code: studio/web/extras.js:143, studio/goals.py:16, studio/goals.py:140, studio/goals.py:162] [run: studio/web/designer_art/art.json]

The designer page has no control for aspect, mode, or seed. It sends only goal, prompt and empty options. [code: studio/web/extras.js:143, studio/web/extras.js:158]

Designer views in one sheet are separate jobs, each with its own random seed and no reference picture. The prompts share words, but nothing ties the pictures together, so the same character or product can change from view to view. [code: studio/web/extras.js:140-144, studio/goals.py:163] [inference]

## Wording and licence traps

The designer Model menu labels anything not class "open" as "community licence". The Anima goal row says non-commercial, but its class is community, so the menu just says community licence. Check the goal's licence before commercial use. [code: studio/web/extras.js:158, studio/goals.py:143]

The home page card says "Twelve more designers inside" after naming three. The data has 13 designers in total, so there are ten others. The page wording is off by two. [code: studio/web/app.js:180] [test: tests/test_studio_packs.py] [inference]

Designer "no brands" is a request in the prompt plus a word list on the option data. It is not a check on the picture. A model can still draw a logo or a known shape, so review output before use. [code: studio/packs.py:8] [test: tests/test_studio_packs.py] [inference]

Designer exact words are only a request too. Getting spelling right depends on the model. The krea2 goal describes itself as spelling a few short words right, and we have no designer render on record that tests this. [code: studio/goals.py:145, studio/packs.py:39] [inference]

## Limits and off by default

The Printify connection is off in this edition. Its routes load only when the edition setting is "extended", and the Connect card shows only there. The print-on-demand designer itself is still in the open edition and only makes pictures. [code: studio/server.py:360-362, studio/web/extras.js:150] [docs: EDITIONS.md]

A designer sheet needs a running ComfyUI. Without one, the page lets a user set choices and says no sheet can be made until it is back. [code: studio/web/extras.js:151-152] [test: tests/test_look_design.py]

A designer view gives up after 600 polls at 1.5 s, about 15 minutes, and shows as failed. [code: studio/web/extras.js:116-119]

The designer option lists came from the author's earlier modules by a read-only parse of constants. They were not each tried. An option existing means it is offered, not that it gives a good picture. [code: studio/packs/packs.json] [inference]
